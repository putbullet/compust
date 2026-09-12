from datetime import datetime, timezone, date
import re
from typing import Any
from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session

from ..models import Company, Country, Job, ScrapingRun, UserApplication, ScrapeTarget
from .ai_service import generate_completion, check_ollama_runtime


def count_new_jobs_today(db: Session) -> dict[str, Any]:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    # also handle naive datetime stored in DB
    naive_start = datetime.combine(date.today(), datetime.min.time())
    count = db.scalar(
        select(func.count(Job.id)).where(
            (Job.discovered_at >= naive_start) | (Job.discovered_at >= today_start)
        )
    ) or 0
    return {"metric": "new_jobs_today", "count": count, "date": date.today().isoformat()}


def count_total_jobs(db: Session) -> dict[str, Any]:
    active_count = db.scalar(select(func.count(Job.id)).where(Job.active.is_(True))) or 0
    total_count = db.scalar(select(func.count(Job.id))) or 0
    return {"metric": "total_jobs", "active_jobs": active_count, "total_jobs": total_count}


def count_active_companies(db: Session) -> dict[str, Any]:
    active_count = db.scalar(select(func.count(Company.id)).where(Company.active.is_(True))) or 0
    total_count = db.scalar(select(func.count(Company.id))) or 0
    return {"metric": "active_companies", "active_count": active_count, "total_count": total_count}


def count_jobs_by_country(db: Session, query: str) -> dict[str, Any]:
    clean_q = query.strip()
    country = db.scalar(
        select(Country).where(
            (func.lower(Country.name) == clean_q.lower()) |
            (func.lower(Country.code) == clean_q.lower())
        )
    )
    if not country:
        # Partial match
        country = db.scalar(
            select(Country).where(func.lower(Country.name).like(f"%{clean_q.lower()}%"))
        )
    if not country:
        return {"metric": "jobs_by_country", "found": False, "query": clean_q, "count": 0}

    count = db.scalar(
        select(func.count(Job.id)).where(Job.country_id == country.id, Job.active.is_(True))
    ) or 0
    return {
        "metric": "jobs_by_country",
        "found": True,
        "country_name": country.name,
        "country_code": country.code,
        "active_jobs_count": count,
    }


def count_jobs_by_company(db: Session, query: str) -> dict[str, Any]:
    clean_q = query.strip()
    company = db.scalar(
        select(Company).where(func.lower(Company.name) == clean_q.lower())
    )
    if not company:
        company = db.scalar(
            select(Company).where(func.lower(Company.name).like(f"%{clean_q.lower()}%"))
        )
    if not company:
        return {"metric": "jobs_by_company", "found": False, "query": clean_q, "count": 0}

    count = db.scalar(
        select(func.count(Job.id)).where(Job.company_id == company.id, Job.active.is_(True))
    ) or 0
    return {
        "metric": "jobs_by_company",
        "found": True,
        "company_name": company.name,
        "active_jobs_count": count,
    }


def count_applied_jobs(db: Session, user_id: int | None = None) -> dict[str, Any]:
    stmt = select(func.count(UserApplication.id))
    if user_id:
        stmt = stmt.where(UserApplication.user_id == user_id)
        applied_stmt = select(func.count(UserApplication.id)).where(
            UserApplication.user_id == user_id, UserApplication.status == "applied"
        )
        applied_count = db.scalar(applied_stmt) or 0
        total_tracked = db.scalar(stmt) or 0
        return {
            "metric": "applied_jobs",
            "applied_count": applied_count,
            "total_tracked": total_tracked,
            "user_id": user_id,
        }

    total_tracked = db.scalar(stmt) or 0
    applied_count = db.scalar(select(func.count(UserApplication.id)).where(UserApplication.status == "applied")) or 0
    return {
        "metric": "applied_jobs",
        "applied_count": applied_count,
        "total_tracked": total_tracked,
        "user_id": None,
    }


def get_recent_jobs(db: Session, limit: int = 5) -> dict[str, Any]:
    items = list(
        db.scalars(
            select(Job).where(Job.active.is_(True)).order_by(desc(Job.discovered_at)).limit(limit)
        ).all()
    )
    jobs_data = []
    for j in items:
        company = db.scalar(select(Company).where(Company.id == j.company_id))
        jobs_data.append({
            "title": j.title,
            "company": company.name if company else "Unknown",
            "location": j.location,
            "discovered_at": j.discovered_at.isoformat() if j.discovered_at else None,
        })
    return {"metric": "recent_jobs", "jobs": jobs_data, "count": len(jobs_data)}


def get_recent_scraping_runs(db: Session, limit: int = 5) -> dict[str, Any]:
    runs = list(
        db.scalars(
            select(ScrapingRun).order_by(desc(ScrapingRun.started_at)).limit(limit)
        ).all()
    )
    runs_data = []
    for r in runs:
        company = db.scalar(select(Company).where(Company.id == r.company_id))
        runs_data.append({
            "company": company.name if company else f"Company #{r.company_id}",
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "jobs_found": r.jobs_found,
            "jobs_added": r.jobs_added,
        })
    return {"metric": "recent_scraping_runs", "runs": runs_data}


def get_country_with_most_jobs(db: Session) -> dict[str, Any]:
    row = db.execute(
        select(Country.name, Country.code, func.count(Job.id).label("job_count"))
        .join(Job, Job.country_id == Country.id)
        .where(Job.active.is_(True))
        .group_by(Country.id)
        .order_by(desc("job_count"))
        .limit(1)
    ).first()
    if not row:
        return {"metric": "country_with_most_jobs", "found": False}
    return {
        "metric": "country_with_most_jobs",
        "found": True,
        "country_name": row[0],
        "country_code": row[1],
        "active_jobs_count": row[2],
    }


# Deterministic Natural Language Question Matcher
def match_and_execute_tool(query: str, db: Session, user_id: int | None = None) -> tuple[dict[str, Any], str]:
    q = query.strip().lower()

    # 1. New jobs today / what appeared today
    if any(k in q for k in ["new jobs", "added today", "jobs today", "appeared today", "nouveaux jobs", "aujourd'hui"]):
        data = count_new_jobs_today(db)
        fallback = f"{data['count']} new job(s) were added today in COMPUST."
        return data, fallback

    # 2. Country with most jobs
    if any(k in q for k in ["most jobs", "plus d'emplois", "highest jobs"]):
        data = get_country_with_most_jobs(db)
        if data.get("found"):
            fallback = f"{data['country_name']} has the most jobs in COMPUST with {data['active_jobs_count']} active listings."
        else:
            fallback = "No jobs found in any country yet."
        return data, fallback

    # 3. Jobs in a country
    country_match = re.search(r"(?:in|au|en|pour)\s+([a-zA-Z\s]+)", q)
    if ("country" in q or "pays" in q or country_match) and not ("company" in q or "entreprise" in q):
        # Extract country candidate
        c_query = "morocco"
        if country_match:
            c_query = country_match.group(1).strip()
        elif "morocco" in q or "maroc" in q:
            c_query = "Morocco"
        elif "france" in q:
            c_query = "France"
        elif "germany" in q or "allemagne" in q:
            c_query = "Germany"

        data = count_jobs_by_country(db, c_query)
        if data.get("found"):
            fallback = f"There are {data['active_jobs_count']} active job(s) listed for {data['country_name']}."
        else:
            fallback = f"No country matching '{c_query}' was found in the database."
        return data, fallback

    # 4. Jobs by company
    company_match = re.search(r"(?:by|company|entreprise|chez|société)\s+([a-zA-Z0-9\s]+)", q)
    if "company" in q or "entreprise" in q or "publish" in q or "publié" in q or company_match:
        comp_candidate = ""
        for name in ["orange", "capgemini", "inwi"]:
            if name in q:
                comp_candidate = name
                break
        if not comp_candidate and company_match:
            comp_candidate = company_match.group(1).strip()

        if comp_candidate:
            data = count_jobs_by_company(db, comp_candidate)
            if data.get("found"):
                fallback = f"{data['company_name']} currently has {data['active_jobs_count']} active job posting(s)."
            else:
                fallback = f"No company matching '{comp_candidate}' was found."
            return data, fallback

    # 5. Active companies count
    if any(k in q for k in ["active companies", "entreprises actives", "how many companies"]):
        data = count_active_companies(db)
        fallback = f"There are currently {data['active_count']} active companies out of {data['total_count']} registered companies."
        return data, fallback

    # 6. User applications
    if any(k in q for k in ["applied", "candidatures", "postulé", "mes candidatures", "my applications"]):
        data = count_applied_jobs(db, user_id=user_id)
        fallback = f"You have {data['applied_count']} job(s) marked as applied ({data['total_tracked']} total tracked in your pipeline)."
        return data, fallback

    # 7. Recent scraping runs
    if any(k in q for k in ["scraped", "scraping", "recent runs", "derniers scrapes", "scraper"]):
        data = get_recent_scraping_runs(db, limit=5)
        runs = data.get("runs", [])
        if runs:
            summary_list = [f"{r['company']} ({r['status']}, +{r['jobs_added']} jobs)" for r in runs[:3]]
            fallback = f"Recent scraping runs: {', '.join(summary_list)}."
        else:
            fallback = "No recent scraping runs recorded."
        return data, fallback

    # 8. Total jobs count
    if any(k in q for k in ["total jobs", "how many jobs", "combien d'emplois", "all jobs"]):
        data = count_total_jobs(db)
        fallback = f"COMPUST currently has {data['active_jobs']} active jobs ({data['total_jobs']} total in directory)."
        return data, fallback

    # Default fallback: Recent jobs overview
    data = get_recent_jobs(db, limit=3)
    jobs_summary = [f"'{j['title']}' at {j['company']}" for j in data.get("jobs", [])]
    fallback = (
        f"COMPUST career assistant here! Recent vacancies include: {', '.join(jobs_summary) if jobs_summary else 'no jobs yet'}. "
        f"You can ask me about new jobs today, jobs by country, company postings, or your applications."
    )
    return data, fallback


# Concise Local LLM System Prompt specifically optimized for 0.8B models
COMPUST_ASSISTANT_SYSTEM_PROMPT = """You are COMPUST AI, a concise and friendly career assistant running locally.
RULES:
1. Answer in 1 or 2 short sentences.
2. Use ONLY the provided verified database facts.
3. NEVER invent numbers, dates, or companies.
4. NEVER attempt or claim to execute SQL or code.
5. If no data exists, state so clearly."""


def answer_user_query(
    query: str,
    db: Session,
    user_id: int | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    # Phase 1: Deterministic retrieval from database
    tool_data, deterministic_fallback = match_and_execute_tool(query, db, user_id=user_id)

    # Phase 2: Check Ollama availability
    runtime = check_ollama_runtime()
    if runtime["status"] != "connected" or not runtime["models"]:
        return {
            "answer": deterministic_fallback,
            "facts": tool_data,
            "provider": "offline_deterministic",
            "model": None,
            "ollama_available": False,
        }

    # Phase 3: Format prompt for local 0.8B model
    prompt = f"User question: {query}\nVerified database facts: {tool_data}\nConcise answer:"

    try:
        llm_response = generate_completion(
            prompt=prompt,
            system_prompt=COMPUST_ASSISTANT_SYSTEM_PROMPT,
            model=model or runtime.get("selected_model"),
            temperature=0.1,
            timeout_seconds=8.0,
        )
        final_answer = llm_response if llm_response else deterministic_fallback
        return {
            "answer": final_answer,
            "facts": tool_data,
            "provider": "ollama",
            "model": model or runtime.get("selected_model"),
            "ollama_available": True,
        }
    except Exception:
        # Graceful fallback to deterministic response if Ollama times out or errors
        return {
            "answer": deterministic_fallback,
            "facts": tool_data,
            "provider": "deterministic_fallback",
            "model": model or runtime.get("selected_model"),
            "ollama_available": True,
        }
