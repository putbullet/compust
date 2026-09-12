from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from src.app.models import Base, Company, Country, Job, JobSkill, ScrapeTarget
from src.app.repositories.jobs import persist_candidates
from src.app.scraper.orange_parser import JobCandidate


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as db:
        country = Country(name="Morocco", code="MA")
        company = Company(name="TestCorp", website_url="https://testcorp.ma", active=True, countries=[country])
        db.add(company)
        db.flush()
        target = ScrapeTarget(company_id=company.id, url="https://testcorp.ma/careers", type="careers", active=True)
        db.add(target)
        db.commit()
        db_session.company_id = company.id
        db_session.country_id = country.id
        db_session.target_id = target.id
        db.company_id = company.id
        db.country_id = country.id
        db.target_id = target.id
        yield db
    engine.dispose()


def test_scenario_a_identical_job_data(db_session):
    """Scenario A: Same job, identical data -> one database record."""
    c1 = JobCandidate(
        title="Senior Python Engineer",
        job_url="https://testcorp.ma/job/101",
        external_job_id="CORP-101",
        location="Casablanca",
        description="Developing scalable backend systems.",
    )
    added1, updated1 = persist_candidates(
        db_session,
        company_id=db_session.company_id,
        country_id=db_session.country_id,
        source="testcorp",
        candidates=[c1],
    )
    assert added1 == 1
    assert updated1 == 0

    # Ingest identical data again in same batch or subsequent call
    added2, updated2 = persist_candidates(
        db_session,
        company_id=db_session.company_id,
        country_id=db_session.country_id,
        source="testcorp",
        candidates=[c1],
    )
    assert added2 == 0
    assert updated2 == 1

    jobs = list(db_session.scalars(select(Job)).all())
    assert len(jobs) == 1
    assert jobs[0].external_job_id == "CORP-101"


def test_scenario_b_same_job_different_scrape(db_session):
    """Scenario B: Same job, different scrape -> still one record, updated last_seen_at."""
    c1 = JobCandidate(
        title="DevOps Engineer",
        job_url="https://testcorp.ma/job/102",
        external_job_id="CORP-102",
        location="Rabat",
        description="Kubernetes, Terraform, CI/CD.",
    )
    persist_candidates(
        db_session,
        company_id=db_session.company_id,
        country_id=db_session.country_id,
        source="testcorp",
        candidates=[c1],
    )
    job_before = db_session.scalar(select(Job).where(Job.external_job_id == "CORP-102"))
    orig_id = job_before.id
    orig_created = job_before.created_at

    # Second scrape with updated description and skills
    c1_updated = JobCandidate(
        title="DevOps Engineer",
        job_url="https://testcorp.ma/job/102",
        external_job_id="CORP-102",
        location="Rabat",
        description="Kubernetes, Terraform, CI/CD, and AWS.",
        skills=["AWS", "Terraform", "Kubernetes"],
    )
    added, updated = persist_candidates(
        db_session,
        company_id=db_session.company_id,
        country_id=db_session.country_id,
        source="testcorp",
        candidates=[c1_updated],
    )
    assert added == 0
    assert updated == 1

    job_after = db_session.scalar(select(Job).where(Job.external_job_id == "CORP-102"))
    assert job_after.id == orig_id
    assert job_after.created_at == orig_created
    assert "AWS" in job_after.description


def test_scenario_c_tracking_parameters_in_url(db_session):
    """Scenario C: Same job, URL contains tracking parameters -> recognized as same job."""
    c1 = JobCandidate(
        title="Data Analyst",
        job_url="https://testcorp.ma/job/103?utm_source=linkedin&utm_campaign=hiring_2026",
        external_job_id="CORP-103",
        location="Casablanca",
        description="SQL, Tableau, Data Warehousing.",
    )
    persist_candidates(
        db_session,
        company_id=db_session.company_id,
        country_id=db_session.country_id,
        source="testcorp",
        candidates=[c1],
    )

    # Scraped from Twitter/X with different tracking parameters
    c2 = JobCandidate(
        title="Data Analyst",
        job_url="https://testcorp.ma/job/103?utm_source=twitter&ref=social_feed&trk=post_2",
        external_job_id="CORP-103",
        location="Casablanca",
        description="SQL, Tableau, Data Warehousing.",
    )
    added, updated = persist_candidates(
        db_session,
        company_id=db_session.company_id,
        country_id=db_session.country_id,
        source="testcorp",
        candidates=[c2],
    )
    assert added == 0
    assert updated == 1
    assert len(list(db_session.scalars(select(Job)).all())) == 1


def test_scenario_d_html_formatting_differs(db_session):
    """Scenario D: Same job, HTML formatting differs -> recognized as the same job."""
    c1 = JobCandidate(
        title="Frontend Architect",
        job_url="https://testcorp.ma/careers/offer?ref=R-9001",
        external_job_id="R-9001",
        location="Casablanca",
        description="<p>Looking for a <strong>Frontend Architect</strong> with <em>React</em> expertise.</p>",
    )
    persist_candidates(
        db_session,
        company_id=db_session.company_id,
        country_id=db_session.country_id,
        source="testcorp",
        candidates=[c1],
    )

    # Different HTML tags in description (e.g. divs and spans instead of p and strong)
    c2 = JobCandidate(
        title="  Frontend Architect  ",
        job_url="https://testcorp.ma/careers/offer?ref=R-9001",
        external_job_id="R-9001",
        location=" Casablanca ",
        description="<div>Looking for a Frontend Architect with React expertise.</div>",
    )
    added, updated = persist_candidates(
        db_session,
        company_id=db_session.company_id,
        country_id=db_session.country_id,
        source="testcorp",
        candidates=[c2],
    )
    assert added == 0
    assert updated == 1
    assert len(list(db_session.scalars(select(Job)).all())) == 1


def test_scenario_e_same_title_different_job_ids(db_session):
    """Scenario E: Same title but different job IDs -> must remain separate."""
    c1 = JobCandidate(
        title="Senior Consultant",
        job_url="https://testcorp.ma/jobs/201",
        external_job_id="CONS-201",
        location="Casablanca",
        department="Advisory",
        description="Risk advisory consultant.",
    )
    c2 = JobCandidate(
        title="Senior Consultant",
        job_url="https://testcorp.ma/jobs/202",
        external_job_id="CONS-202",
        location="Casablanca",
        department="Technology",
        description="Cloud transformation consultant.",
    )
    added, updated = persist_candidates(
        db_session,
        company_id=db_session.company_id,
        country_id=db_session.country_id,
        source="testcorp",
        candidates=[c1, c2],
    )
    assert added == 2
    assert updated == 0

    jobs = list(db_session.scalars(select(Job).where(Job.title == "Senior Consultant")).all())
    assert len(jobs) == 2
    ext_ids = {j.external_job_id for j in jobs}
    assert ext_ids == {"CONS-201", "CONS-202"}


def test_scenario_f_same_title_different_locations(db_session):
    """Scenario F: Same title but different locations -> must remain separate when distinct postings."""
    c1 = JobCandidate(
        title="Branch Manager",
        job_url="https://testcorp.ma/job/casablanca-manager",
        external_job_id="MGR-CASA",
        location="Casablanca",
        description="Managing Casablanca regional operations.",
    )
    c2 = JobCandidate(
        title="Branch Manager",
        job_url="https://testcorp.ma/job/tangier-manager",
        external_job_id="MGR-TNG",
        location="Tangier",
        description="Managing Tangier regional operations.",
    )
    added, updated = persist_candidates(
        db_session,
        company_id=db_session.company_id,
        country_id=db_session.country_id,
        source="testcorp",
        candidates=[c1, c2],
    )
    assert added == 2
    jobs = list(db_session.scalars(select(Job).where(Job.title == "Branch Manager")).all())
    assert len(jobs) == 2
    locations = {j.location for j in jobs}
    assert locations == {"Casablanca", "Tangier"}


def test_scenario_g_same_company_title_different_posting_dates(db_session):
    """Scenario G: Same company and title but different seasonal posting dates -> kept separate."""
    date_spring = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
    date_autumn = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)

    c1 = JobCandidate(
        title="Summer Intern - Software Engineering",
        job_url="https://testcorp.ma/careers/intern-spring",
        external_job_id="INT-2026-S",
        location="Casablanca",
        posted_at=date_spring,
        description="Internship program spring intake.",
    )
    c2 = JobCandidate(
        title="Summer Intern - Software Engineering",
        job_url="https://testcorp.ma/careers/intern-autumn",
        external_job_id="INT-2026-A",
        location="Casablanca",
        posted_at=date_autumn,
        description="Internship program autumn intake.",
    )
    added, updated = persist_candidates(
        db_session,
        company_id=db_session.company_id,
        country_id=db_session.country_id,
        source="testcorp",
        candidates=[c1, c2],
    )
    assert added == 2
    assert len(list(db_session.scalars(select(Job)).all())) == 2


def test_scenario_h_two_genuinely_different_jobs(db_session):
    """Scenario H: Two genuinely different jobs -> both stored."""
    c1 = JobCandidate(
        title="Legal Counsel",
        job_url="https://testcorp.ma/jobs/legal-01",
        external_job_id="LEG-01",
        location="Casablanca",
        description="Corporate contract law and compliance.",
    )
    c2 = JobCandidate(
        title="Site Reliability Engineer",
        job_url="https://testcorp.ma/jobs/sre-01",
        external_job_id="SRE-01",
        location="Casablanca",
        description="Infrastructure monitoring, SLA, Linux.",
    )
    added, updated = persist_candidates(
        db_session,
        company_id=db_session.company_id,
        country_id=db_session.country_id,
        source="testcorp",
        candidates=[c1, c2],
    )
    assert added == 2
    assert updated == 0
    assert len(list(db_session.scalars(select(Job)).all())) == 2


def test_scenario_i_duplicate_discovery_paths(db_session):
    """Scenario I: Same job discovered through pagination and search filter -> only one record."""
    # Discovered on page 1
    c_page1 = JobCandidate(
        title="Security Engineer",
        job_url="https://testcorp.ma/jobs/sec-100",
        external_job_id="SEC-100",
        location="Casablanca",
        description="Application security, penetration testing.",
    )
    persist_candidates(
        db_session,
        company_id=db_session.company_id,
        country_id=db_session.country_id,
        source="testcorp",
        candidates=[c_page1],
    )

    # Discovered via filter query URL
    c_filtered = JobCandidate(
        title="Security Engineer",
        job_url="https://testcorp.ma/jobs/sec-100?dept=security&level=senior",
        external_job_id="SEC-100",
        location="Casablanca",
        description="Application security, penetration testing.",
    )
    added, updated = persist_candidates(
        db_session,
        company_id=db_session.company_id,
        country_id=db_session.country_id,
        source="testcorp",
        candidates=[c_filtered],
    )
    assert added == 0
    assert updated == 1
    assert len(list(db_session.scalars(select(Job)).all())) == 1


def test_scenario_j_rescrape_updates_existing_record(db_session):
    """Scenario J: Re-scraping an existing job should update the existing record rather than create a duplicate."""
    c1 = JobCandidate(
        title="Machine Learning Engineer",
        job_url="https://testcorp.ma/jobs/ml-500",
        external_job_id="ML-500",
        location="Casablanca",
        salary_min=15000.0,
        salary_max=25000.0,
        salary_currency="MAD",
        salary_period="month",
        skills=["Python", "PyTorch"],
    )
    persist_candidates(
        db_session,
        company_id=db_session.company_id,
        country_id=db_session.country_id,
        source="testcorp",
        candidates=[c1],
    )
    initial_job = db_session.scalar(select(Job).where(Job.external_job_id == "ML-500"))
    assert initial_job.salary_max == 25000.0
    initial_skills = list(db_session.scalars(select(JobSkill.skill).where(JobSkill.job_id == initial_job.id)).all())
    assert set(initial_skills) == {"Python", "PyTorch"}

    # Rescrape with salary raise and new skill
    c1_new = JobCandidate(
        title="Machine Learning Engineer",
        job_url="https://testcorp.ma/jobs/ml-500",
        external_job_id="ML-500",
        location="Casablanca",
        salary_min=18000.0,
        salary_max=30000.0,
        salary_currency="MAD",
        salary_period="month",
        skills=["Python", "PyTorch", "Transformers", "MLOps"],
    )
    added, updated = persist_candidates(
        db_session,
        company_id=db_session.company_id,
        country_id=db_session.country_id,
        source="testcorp",
        candidates=[c1_new],
    )
    assert added == 0
    assert updated == 1

    updated_job = db_session.scalar(select(Job).where(Job.external_job_id == "ML-500"))
    assert updated_job.id == initial_job.id
    assert updated_job.salary_max == 30000.0
    updated_skills = list(db_session.scalars(select(JobSkill.skill).where(JobSkill.job_id == updated_job.id)).all())
    assert set(updated_skills) == {"Python", "PyTorch", "Transformers", "MLOps"}
