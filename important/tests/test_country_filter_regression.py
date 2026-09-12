import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.app.models import Base, Company, Country, Job
from src.app.repositories.companies import update_company
from src.app.repositories.jobs import persist_candidates, list_jobs
from src.app.repositories.countries import resolve_country_by_location, get_country_by_code
from src.app.schemas import CompanyUpdate
from src.app.scraper.orange_parser import JobCandidate
from src.app.scraper.vocabulary import normalize_location


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed countries matching canonical IDs
    countries = [
        Country(id=1, code="FR", name="France"),
        Country(id=2, code="MA", name="Morocco"),
        Country(id=3, code="DE", name="Germany"),
        Country(id=4, code="ES", name="Spain"),
        Country(id=5, code="BE", name="Belgium"),
        Country(id=6, code="NL", name="Netherlands"),
        Country(id=7, code="GB", name="United Kingdom"),
        Country(id=8, code="CA", name="Canada"),
        Country(id=9, code="US", name="United States"),
        Country(id=10, code="AE", name="United Arab Emirates"),
        Country(id=11, code="SA", name="Saudi Arabia"),
    ]
    session.add_all(countries)
    session.commit()

    yield session
    session.close()


def test_location_normalization_vocabulary():
    """Verify vocabulary normalizer extracts correct canonical countries and cities."""
    assert normalize_location("Berlin, Germany")["country"] == "Germany"
    assert normalize_location("Frankfurt, Hessen")["country"] == "Germany"
    assert normalize_location("London, UK")["country"] == "United Kingdom"
    assert normalize_location("New York, NY, US")["country"] == "United States"
    assert normalize_location("Paris, France")["country"] == "France"
    assert normalize_location("Casablanca, Grand Casablanca")["country"] == "Morocco"
    assert normalize_location("Dubai, United Arab Emirates")["country"] == "United Arab Emirates"
    assert normalize_location("Riyadh, KSA")["country"] == "Saudi Arabia"


def test_resolve_country_by_location(test_db):
    """Verify repository resolves Country entities from location strings."""
    c_de = resolve_country_by_location(test_db, "Berlin, Germany")
    assert c_de is not None
    assert c_de.code == "DE"

    c_uk = resolve_country_by_location(test_db, "London, United Kingdom")
    assert c_uk is not None
    assert c_uk.code == "GB"

    c_sa = resolve_country_by_location(test_db, "Riyadh, Saudi Arabia")
    assert c_sa is not None
    assert c_sa.code == "SA"

    c_ae = resolve_country_by_location(test_db, "Dubai, UAE")
    assert c_ae is not None
    assert c_ae.code == "AE"


def test_country_filter_decoupled_from_company_country(test_db):
    """Test Case: Company headquartered in France recruiting internationally in France, Germany, UK.

    Scraped jobs in Paris, Berlin, London, Frankfurt must be assigned their actual country,
    and filtering by Germany (DE=3) must only return German jobs.
    """
    france = test_db.query(Country).filter_by(code="FR").first()
    germany = test_db.query(Country).filter_by(code="DE").first()
    uk = test_db.query(Country).filter_by(code="GB").first()

    company = Company(
        name="Global Tech Solutions",
        website_url="https://globaltech.example",
        active=True,
    )
    company.countries = [france, germany, uk]
    test_db.add(company)
    test_db.commit()

    candidates = [
        JobCandidate(
            external_job_id="job-1",
            title="Backend Engineer",
            job_url="https://globaltech.example/jobs/1",
            location="Paris, France",
        ),
        JobCandidate(
            external_job_id="job-2",
            title="Senior DevOps Engineer",
            job_url="https://globaltech.example/jobs/2",
            location="Berlin, Germany",
        ),
        JobCandidate(
            external_job_id="job-3",
            title="Cloud Architect",
            job_url="https://globaltech.example/jobs/3",
            location="Frankfurt",
        ),
        JobCandidate(
            external_job_id="job-4",
            title="Frontend Developer",
            job_url="https://globaltech.example/jobs/4",
            location="London, UK",
        ),
    ]

    # Primary company country ID is France (1)
    added, updated = persist_candidates(
        db=test_db,
        company_id=company.id,
        country_id=france.id,
        candidates=candidates,
        source="career_site",
    )
    assert added == 4

    # Verify Germany filter returns exactly 2 German jobs (Berlin and Frankfurt)
    de_jobs, de_count = list_jobs(test_db, country_id=germany.id)
    assert de_count == 2
    de_titles = {j.title for j in de_jobs}
    assert "Senior DevOps Engineer" in de_titles
    assert "Cloud Architect" in de_titles
    for j in de_jobs:
        assert j.country_id == germany.id

    # Verify France filter returns exactly 1 France job (Paris)
    fr_jobs, fr_count = list_jobs(test_db, country_id=france.id)
    assert fr_count == 1
    assert fr_jobs[0].title == "Backend Engineer"
    assert fr_jobs[0].country_id == france.id

    # Verify UK filter returns exactly 1 UK job (London)
    uk_jobs, uk_count = list_jobs(test_db, country_id=uk.id)
    assert uk_count == 1
    assert uk_jobs[0].title == "Frontend Developer"
    assert uk_jobs[0].country_id == uk.id


def test_company_update_re_evaluates_job_countries(test_db):
    """When a company is initially configured with France and has Munich jobs fallback-stamped,

    updating company countries or re-evaluating automatically re-aligns job countries.
    """
    france = test_db.query(Country).filter_by(code="FR").first()
    germany = test_db.query(Country).filter_by(code="DE").first()

    company = Company(
        name="Euro Logistics",
        website_url="https://eurolog.example",
        active=True,
    )
    company.countries = [france]
    test_db.add(company)
    test_db.commit()

    # Job created in Munich
    job = Job(
        company_id=company.id,
        country_id=france.id,  # Initially stamped with France
        title="Munich Operations Manager",
        location="Munich, Germany",
        job_url="https://eurolog.example/munich-ops",
        active=True,
        discovered_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(job)
    test_db.commit()

    # User realizes company recruits in Germany and adds Germany
    update_company(test_db, company_id=company.id, country_ids=[france.id, germany.id])

    test_db.refresh(job)
    # The Munich job's country_id must be updated to Germany (3)
    assert job.country_id == germany.id
