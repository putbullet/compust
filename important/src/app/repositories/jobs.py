from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import Company, Country, Job, JobSkill
from ..scraper.orange_parser import JobCandidate
from ..scraper.sanitizer import sanitize_html, sanitize_plain_text
from ..scraper.url_normalizer import normalize_url


import re

def normalize_job_text(text: str | None) -> str:
    """Normalize text for semantic comparison (strip HTML, collapse whitespace, lowercase)."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"[\s\-_/]+", " ", clean).strip().lower()
    return clean


def resolve_or_create_company(
    db: Session,
    name: str,
    default_country_id: int | None = None,
) -> Company:
    clean_name = sanitize_plain_text(name) or "Unknown Company"
    company = db.scalar(
        select(Company).where(Company.name.ilike(clean_name))
    )
    if not company:
        company = Company(
            name=clean_name,
            website_url="",
            active=True,
        )
        if default_country_id:
            country = db.scalar(select(Country).where(Country.id == default_country_id))
            if country:
                company.countries = [country]
        db.add(company)
        db.flush()
        db.commit()
        db.refresh(company)
    return company


def persist_candidate(
    db: Session,
    *,
    company_id: int,
    country_id: int,
    source: str,
    candidate: JobCandidate,
    scrape_target_id: int | None = None,
    commit: bool = False,
) -> tuple[Job, bool]:
    from .countries import resolve_country_by_location

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    norm_url = normalize_url(candidate.job_url)
    clean_title = sanitize_plain_text(candidate.title) or "Untitled Position"
    clean_description = sanitize_html(candidate.description)
    clean_location = sanitize_plain_text(candidate.location)
    clean_department = sanitize_plain_text(candidate.department)
    clean_employment = sanitize_plain_text(candidate.employment_type)
    clean_remote = sanitize_plain_text(candidate.remote_type)

    # Resolve actual job country from location, falling back to company country
    actual_country = resolve_country_by_location(db, clean_location)
    effective_country_id = actual_country.id if actual_country else country_id

    job = None
    # Tier 1: Match by Company + External Job ID (highest confidence)
    if candidate.external_job_id:
        job = db.scalar(
            select(Job).where(
                Job.company_id == company_id,
                Job.external_job_id == candidate.external_job_id,
            )
        )

    # Tier 2: Match by Company + Normalized Canonical URL
    if job is None and norm_url:
        matched_by_url = db.scalar(
            select(Job).where(
                Job.company_id == company_id,
                Job.job_url == norm_url,
            )
        )
        # Guard: Only reuse matched job if external_job_ids do not conflict
        if matched_by_url:
            if not candidate.external_job_id or not matched_by_url.external_job_id or candidate.external_job_id == matched_by_url.external_job_id:
                job = matched_by_url

    # Tier 3: Content Fingerprint & Composite Match (for jobs lacking unique external IDs or URLs)
    if job is None:
        cand_norm_title = normalize_job_text(candidate.title)
        cand_norm_loc = normalize_job_text(candidate.location)
        cand_norm_desc = normalize_job_text(candidate.description)[:200]

        # Look up candidates in same company with matching title
        potential_matches = list(
            db.scalars(
                select(Job).where(
                    Job.company_id == company_id,
                    Job.active == True,
                )
            ).all()
        )
        for existing in potential_matches:
            # Must have identical normalized title
            if normalize_job_text(existing.title) != cand_norm_title:
                continue

            # Guard against conflicting external job IDs
            if candidate.external_job_id and existing.external_job_id and candidate.external_job_id != existing.external_job_id:
                continue

            # Guard against conflicting locations (e.g. Casablanca vs Rabat)
            exist_norm_loc = normalize_job_text(existing.location)
            if cand_norm_loc and exist_norm_loc and cand_norm_loc != exist_norm_loc:
                continue

            # Guard against different posting dates (e.g. spring posting vs fall posting)
            if candidate.posted_at and existing.posted_at:
                c_dt = candidate.posted_at.replace(tzinfo=None)
                e_dt = existing.posted_at.replace(tzinfo=None)
                if abs((c_dt - e_dt).days) > 14:
                    continue

            # Compare description plain-text fingerprint
            exist_norm_desc = normalize_job_text(existing.description)[:200]
            if cand_norm_desc and exist_norm_desc:
                if cand_norm_desc == exist_norm_desc or cand_norm_desc.startswith(exist_norm_desc[:100]) or exist_norm_desc.startswith(cand_norm_desc[:100]):
                    job = existing
                    break
            elif not cand_norm_desc and not exist_norm_desc:
                job = existing
                break

    is_created = False
    if job is None:
        job = Job(
            company_id=company_id,
            country_id=effective_country_id,
            title=clean_title,
            location=clean_location,
            job_url=norm_url,
            description=clean_description,
            employment_type=clean_employment,
            remote_type=clean_remote,
            department=clean_department,
            source=source,
            external_job_id=candidate.external_job_id,
            posted_at=candidate.posted_at.replace(tzinfo=None) if candidate.posted_at else None,
            discovered_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
            active=True,
            salary_min=candidate.salary_min,
            salary_max=candidate.salary_max,
            salary_currency=candidate.salary_currency,
            salary_period=candidate.salary_period,
            scrape_target_id=scrape_target_id,
        )
        db.add(job)
        db.flush()
        is_created = True
    else:
        if scrape_target_id is not None:
            job.scrape_target_id = scrape_target_id

    job.country_id = effective_country_id
    job.title = clean_title
    job.location = clean_location
    job.job_url = norm_url
    job.description = clean_description
    job.employment_type = clean_employment
    job.remote_type = clean_remote
    job.department = clean_department
    job.source = source
    job.external_job_id = candidate.external_job_id
    job.posted_at = candidate.posted_at.replace(tzinfo=None) if candidate.posted_at else None
    job.last_seen_at = now
    job.active = True
    job.updated_at = now
    job.salary_min = candidate.salary_min
    job.salary_max = candidate.salary_max
    job.salary_currency = candidate.salary_currency
    job.salary_period = candidate.salary_period
    db.execute(delete(JobSkill).where(JobSkill.job_id == job.id))
    db.add_all(
        [
            JobSkill(job_id=job.id, skill=sanitize_plain_text(skill) or skill)
            for skill in dict.fromkeys(candidate.skills)
            if skill
        ]
    )
    if commit:
        db.commit()
        db.refresh(job)
    return job, is_created


def persist_candidates(
    db: Session,
    *,
    company_id: int,
    country_id: int,
    source: str,
    candidates: list[JobCandidate],
    scrape_target_id: int | None = None,
) -> tuple[int, int]:
    added = 0
    updated = 0
    for candidate in candidates:
        _, is_created = persist_candidate(
            db,
            company_id=company_id,
            country_id=country_id,
            source=source,
            candidate=candidate,
            scrape_target_id=scrape_target_id,
            commit=False,
        )
        if is_created:
            added += 1
        else:
            updated += 1
    db.commit()
    return added, updated


def list_jobs(
    db: Session,
    *,
    country_id: int | None = None,
    company_id: int | None = None,
    remote_type: str | None = None,
    employment_type: str | None = None,
    search: str | None = None,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Job], int]:
    from sqlalchemy import func, or_
    from ..services.opportunities_search import prepare_search_plan, calculate_job_relevance

    filters = []
    if active_only:
        filters.append(Job.active == True)
    if country_id is not None:
        filters.append(Job.country_id == country_id)
    if company_id is not None:
        filters.append(Job.company_id == company_id)
    if remote_type:
        filters.append(Job.remote_type.ilike(f"%{remote_type}%"))
    if employment_type:
        filters.append(Job.employment_type.ilike(f"%{employment_type}%"))

    # When NO search query is present, use fast direct SQL pagination ordered by date
    if not search or not search.strip():
        query = select(Job)
        count_query = select(func.count(Job.id))
        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)

        total = db.scalar(count_query) or 0
        items = list(
            db.scalars(
                query.order_by(Job.posted_at.desc(), Job.id.desc())
                .offset(skip)
                .limit(limit)
            ).all()
        )
        return items, total

    # When search IS present, execute intelligent relevance-ranked search
    raw_search = search.strip()
    plan = prepare_search_plan(raw_search)

    search_clauses = []
    for term in plan.all_matching_terms:
        if not term or len(term.strip()) == 0:
            continue
        pattern = f"%{term.strip()}%"
        search_clauses.extend(
            [
                Job.title.ilike(pattern),
                Job.description.ilike(pattern),
                Job.location.ilike(pattern),
                Job.department.ilike(pattern),
                Job.employment_type.ilike(pattern),
                Job.company_id.in_(select(Company.id).where(Company.name.ilike(pattern))),
            ]
        )

    if plan.is_internship_query:
        search_clauses.append(Job.employment_type.ilike("%intern%"))
        search_clauses.append(Job.employment_type.ilike("%stage%"))
        search_clauses.append(Job.employment_type.ilike("%praktik%"))

    if search_clauses:
        filters.append(or_(*search_clauses))

    query = select(Job).where(*filters)
    candidates = list(db.scalars(query).all())

    # Calculate deterministic relevance score for each candidate
    scored_candidates: list[tuple[Job, float, float, int]] = []
    for job in candidates:
        rel = calculate_job_relevance(job, plan)
        if rel.total_score > 0:
            posted_ts = (
                job.posted_at.timestamp()
                if job.posted_at
                else (job.discovered_at.timestamp() if job.discovered_at else 0.0)
            )
            scored_candidates.append((job, rel.total_score, posted_ts, job.id))

    # Rank before pagination: primary sort by relevance score descending,
    # secondary sort by posted_at timestamp descending, tertiary by job ID descending
    scored_candidates.sort(key=lambda x: (-x[1], -x[2], -x[3]))

    total = len(scored_candidates)
    paginated_slice = scored_candidates[skip : skip + limit]
    items = [item[0] for item in paginated_slice]
    return items, total


def get_job(db: Session, job_id: int) -> Job | None:
    return db.scalar(select(Job).where(Job.id == job_id))


def get_job_skills(db: Session, job_id: int) -> list[str]:
    return list(db.scalars(select(JobSkill.skill).where(JobSkill.job_id == job_id)).all())

