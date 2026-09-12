from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from src.app.models import Base, Company, Country, Job, ScrapeTarget, ScrapingRun
from src.app.repositories.jobs import persist_candidates
from src.app.scraper.orange_parser import JobCandidate
from src.app.services.stale_lifecycle import (
    evaluate_target_stale_jobs,
    is_safe_for_stale_evaluation,
)


@pytest.fixture
def lifecycle_env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as db:
        country = Country(name="Morocco", code="MA")
        company = Company(name="Orange Maroc", website_url="https://orange.ma", active=True, countries=[country])
        db.add(company)
        db.flush()
        target = ScrapeTarget(company_id=company.id, url="https://orange.jobs/fr/fr/search", type="careers", active=True)
        db.add(target)
        db.commit()

        # Seed initial job
        c1 = JobCandidate(
            title="Senior Network Architect",
            job_url="https://orange.jobs/fr/fr/job/101",
            external_job_id="ORG-101",
            location="Casablanca",
            description="Core telecom network planning and operations.",
        )
        persist_candidates(
            db,
            company_id=company.id,
            country_id=country.id,
            source="orange",
            candidates=[c1],
            scrape_target_id=target.id,
        )

        class Env:
            pass
        env = Env()
        env.db = db
        env.company_id = company.id
        env.country_id = country.id
        env.target_id = target.id
        yield env
    engine.dispose()


def test_safety_check_guards(lifecycle_env):
    """Verify is_safe_for_stale_evaluation strictly gates on full clean success."""
    # 1. Scraper failure or partial
    assert is_safe_for_stale_evaluation(is_full_success=False, jobs_found=10) is False

    # 2. Scraper threw parser errors
    assert is_safe_for_stale_evaluation(is_full_success=True, parser_errors=["Parse error at line 40"], jobs_found=5) is False

    # 3. Empty discovery (e.g. anti-bot/CAPTCHA or blocked page returned 0 jobs)
    assert is_safe_for_stale_evaluation(is_full_success=True, parser_errors=[], jobs_found=0) is False

    # 4. Verified complete clean run
    assert is_safe_for_stale_evaluation(is_full_success=True, parser_errors=[], jobs_found=12) is True


def test_successful_scrape_job_found_refreshes_last_seen(lifecycle_env):
    """Successful scrape where job is found -> stays active, last_seen_at refreshed."""
    db = lifecycle_env.db
    job_before = db.scalar(select(Job).where(Job.external_job_id == "ORG-101"))
    assert job_before.active is True
    initial_last_seen = job_before.last_seen_at

    # Ingest same job in subsequent run
    c1 = JobCandidate(
        title="Senior Network Architect",
        job_url="https://orange.jobs/fr/fr/job/101",
        external_job_id="ORG-101",
        location="Casablanca",
        description="Core telecom network planning and operations.",
    )
    added, updated = persist_candidates(
        db,
        company_id=lifecycle_env.company_id,
        country_id=lifecycle_env.country_id,
        source="orange",
        candidates=[c1],
        scrape_target_id=lifecycle_env.target_id,
    )
    assert added == 0
    assert updated == 1

    job_after = db.scalar(select(Job).where(Job.external_job_id == "ORG-101"))
    assert job_after.active is True
    assert job_after.last_seen_at >= initial_last_seen


def test_failed_scrape_does_not_deactivate(lifecycle_env):
    """Scraper failed (HTTP 500 or network error) -> job remains active."""
    db = lifecycle_env.db
    # Scrape failed: is_full_success = False
    closed = evaluate_target_stale_jobs(
        db,
        company_id=lifecycle_env.company_id,
        scrape_target_id=lifecycle_env.target_id,
        seen_external_ids=set(),
        seen_urls=set(),
        is_full_success=False,
    )
    assert closed == 0

    job = db.scalar(select(Job).where(Job.external_job_id == "ORG-101"))
    assert job.active is True


def test_rate_limited_or_blocked_scrape_does_not_deactivate(lifecycle_env):
    """Source returned HTTP 429/403 -> job remains active."""
    db = lifecycle_env.db
    closed = evaluate_target_stale_jobs(
        db,
        company_id=lifecycle_env.company_id,
        scrape_target_id=lifecycle_env.target_id,
        seen_external_ids=set(),
        seen_urls=set(),
        is_full_success=False,
    )
    assert closed == 0

    job = db.scalar(select(Job).where(Job.external_job_id == "ORG-101"))
    assert job.active is True


def test_repeated_confirmed_absence_transitions_to_inactive(lifecycle_env):
    """Repeated confirmed absence over consecutive successful runs -> mark inactive."""
    db = lifecycle_env.db
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Simulate 3 successful runs in the past that completed without ORG-101
    for i in range(3):
        run = ScrapingRun(
            company_id=lifecycle_env.company_id,
            status="success",
            started_at=now + timedelta(hours=i + 1),
            finished_at=now + timedelta(hours=i + 1, minutes=5),
            jobs_found=5,
        )
        db.add(run)
    db.commit()

    # Now evaluate target stale jobs with confirmed clean success, threshold 3
    closed = evaluate_target_stale_jobs(
        db,
        company_id=lifecycle_env.company_id,
        scrape_target_id=lifecycle_env.target_id,
        seen_external_ids={"OTHER-JOB-1"},
        seen_urls={"https://orange.jobs/fr/fr/job/999"},
        is_full_success=True,
        max_missed_runs=3,
    )
    assert closed == 1

    job = db.scalar(select(Job).where(Job.external_job_id == "ORG-101"))
    assert job.active is False  # softly closed!


def test_resurrection_and_new_job_import(lifecycle_env):
    """Inactive job is resurrected if re-discovered, and new jobs import normally."""
    db = lifecycle_env.db
    # Soft-deactivate ORG-101
    job1 = db.scalar(select(Job).where(Job.external_job_id == "ORG-101"))
    job1.active = False
    db.commit()

    # Next scrape discovers both ORG-101 again AND a new job ORG-102
    c1 = JobCandidate(
        title="Senior Network Architect",
        job_url="https://orange.jobs/fr/fr/job/101",
        external_job_id="ORG-101",
        location="Casablanca",
        description="Core telecom network planning and operations.",
    )
    c2 = JobCandidate(
        title="Security Operations Lead",
        job_url="https://orange.jobs/fr/fr/job/102",
        external_job_id="ORG-102",
        location="Casablanca",
        description="SOC monitoring and incident triage.",
    )

    added, updated = persist_candidates(
        db,
        company_id=lifecycle_env.company_id,
        country_id=lifecycle_env.country_id,
        source="orange",
        candidates=[c1, c2],
        scrape_target_id=lifecycle_env.target_id,
    )
    assert added == 1   # ORG-102 added
    assert updated == 1 # ORG-101 updated and resurrected

    j1 = db.scalar(select(Job).where(Job.external_job_id == "ORG-101"))
    assert j1.active is True  # Resurrected to active!

    j2 = db.scalar(select(Job).where(Job.external_job_id == "ORG-102"))
    assert j2.active is True  # New job imported normally!
