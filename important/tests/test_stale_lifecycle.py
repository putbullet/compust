from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.models import Base, Company, Country, Job, ScrapeTarget, ScrapingRun
from src.app.repositories.jobs import persist_candidates
from src.app.scraper.orange_parser import JobCandidate
from src.app.services.stale_lifecycle import evaluate_target_stale_jobs


def test_stale_job_lifecycle_and_provenance() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        country = Country(name="Morocco", code="MA")
        company = Company(
            name="Inwi",
            website_url="https://inwi.ma",
            careers_url="https://recrutement.inwi.ma",
            active=True,
            countries=[country],
        )
        db.add(company)
        db.flush()

        target = ScrapeTarget(
            company_id=company.id,
            url="https://recrutement.inwi.ma/jobs",
            type="turbostream_html",
            active=True,
        )
        db.add(target)
        db.commit()

        company_id = company.id
        country_id = country.id
        target_id = target.id

    # 1. Ingest initial candidates with scrape_target_id provenance
    with session_factory() as db:
        c1 = JobCandidate(
            title="Senior Network Architect",
            job_url="https://recrutement.inwi.ma/jobs/101",
            external_job_id="INWI-101",
            location="Casablanca",
            employment_type="CDI",
        )
        c2 = JobCandidate(
            title="Junior DevOps Engineer",
            job_url="https://recrutement.inwi.ma/jobs/102",
            external_job_id="INWI-102",
            location="Casablanca",
            employment_type="CDI",
        )
        added, updated = persist_candidates(
            db,
            company_id=company_id,
            country_id=country_id,
            source="inwi",
            candidates=[c1, c2],
            scrape_target_id=target_id,
        )
        assert added == 2

        jobs = list(db.scalars(select(Job)).all())
        assert len(jobs) == 2
        for j in jobs:
            assert j.scrape_target_id == target_id
            assert j.active is True
            assert j.last_seen_at is not None

    # 2. Incomplete / Partial scrape: Job 102 missing, but is_full_success is False
    # Verify guardrail: must NOT mark inactive!
    with session_factory() as db:
        closed = evaluate_target_stale_jobs(
            db,
            company_id=company_id,
            scrape_target_id=target_id,
            seen_external_ids={"INWI-101"},
            seen_urls={"https://recrutement.inwi.ma/jobs/101"},
            is_full_success=False,  # partial run
        )
        assert closed == 0

        j2 = db.scalar(select(Job).where(Job.external_job_id == "INWI-102"))
        assert j2.active is True  # preserved active!

    # 3. Consecutive clean runs where Job 102 remains absent
    # Simulate 3 successful runs in the past
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with session_factory() as db:
        for i in range(3):
            run = ScrapingRun(
                company_id=company_id,
                status="success",
                started_at=now + timedelta(hours=i + 1),
                finished_at=now + timedelta(hours=i + 1, minutes=10),
                jobs_found=1,
            )
            db.add(run)
        db.commit()

    # Now evaluate target stale jobs on verified full clean success
    with session_factory() as db:
        closed = evaluate_target_stale_jobs(
            db,
            company_id=company_id,
            scrape_target_id=target_id,
            seen_external_ids={"INWI-101"},
            seen_urls={"https://recrutement.inwi.ma/jobs/101"},
            is_full_success=True,
            max_missed_runs=3,
        )
        assert closed == 1

        j2 = db.scalar(select(Job).where(Job.external_job_id == "INWI-102"))
        assert j2.active is False  # successfully transitioned to inactive

    # 4. Job 102 is reposted/reappears in a future scrape -> resurrected to active
    with session_factory() as db:
        added, updated = persist_candidates(
            db,
            company_id=company_id,
            country_id=country_id,
            source="inwi",
            candidates=[c2],
            scrape_target_id=target_id,
        )
        assert updated == 1
        j2 = db.scalar(select(Job).where(Job.external_job_id == "INWI-102"))
        assert j2.active is True  # resurrected!

    engine.dispose()
