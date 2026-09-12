from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, Company, Country, Job, JobTranslation
from src.app.services.translation import DeterministicTranslationProvider, JobTranslationService


def test_deterministic_translation_provider() -> None:
    provider = DeterministicTranslationProvider()

    # Title translations
    fr_title = "Stage Ingénieur Développeur Full Stack"
    en_title = provider.translate_title(fr_title, source_lang="fr", target_lang="en")
    assert "Internship" in en_title
    assert "Engineer" in en_title
    assert "Developer" in en_title

    # Section headings translation
    fr_desc = "Missions : Concevoir des API. Profil recherché : Passionné de code. Télétravail : Hybride."
    en_desc = provider.translate_description(fr_desc, source_lang="fr", target_lang="en")
    assert "Responsibilities:" in en_desc
    assert "Candidate profile:" in en_desc
    assert "Remote work:" in en_desc

    # Same language returns untouched
    assert provider.translate_title("Software Engineer", "en", "en") == "Software Engineer"


def test_translations_service_and_api_endpoints() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    original_title = "Développeur Python Backend"
    original_description = "Missions : Développer des microservices. Compétences requises : Python, SQL."

    with session_factory() as session:
        country = Country(id=1, name="Morocco", code="MA")
        company = Company(id=1, name="Inwi", website_url="https://inwi.ma", active=True)
        session.add_all([country, company])
        session.flush()

        now = datetime.now(timezone.utc)
        job = Job(
            id=101,
            company_id=1,
            country_id=1,
            title=original_title,
            description=original_description,
            job_url="https://inwi.ma/careers/101",
            active=True,
            discovered_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(job)
        session.commit()

    def fake_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = fake_db
    client = TestClient(app)

    # 1. Verify translations are initially empty
    resp = client.get("/api/v1/jobs/101/translations")
    assert resp.status_code == 200
    assert resp.json() == []

    # 2. Trigger automated translation to English via POST
    auto_resp = client.post("/api/v1/jobs/101/translations", json={"language": "en"})
    assert auto_resp.status_code == 200
    auto_data = auto_resp.json()
    assert auto_data["language"] == "en"
    assert "Developer Python Backend" in auto_data["title"]
    assert "Responsibilities:" in auto_data["description"]

    # 3. Ensure employer source text in jobs table is NOT modified
    job_detail_resp = client.get("/api/v1/jobs/101")
    assert job_detail_resp.status_code == 200
    job_data = job_detail_resp.json()
    assert job_data["title"] == original_title
    assert job_data["description"] == original_description

    # 4. Add manual/custom translation (e.g. Arabic or tailored English)
    custom_resp = client.post(
        "/api/v1/jobs/101/translations",
        json={
            "language": "en",
            "title": "Senior Backend Python Engineer",
            "description": "Responsibilities: Architect high-throughput distributed systems.",
            "source_language": "fr",
        },
    )
    assert custom_resp.status_code == 200
    custom_data = custom_resp.json()
    assert custom_data["title"] == "Senior Backend Python Engineer"

    # 5. List translations now returns the persisted translation
    list_resp = client.get("/api/v1/jobs/101/translations")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["language"] == "en"
    assert items[0]["title"] == "Senior Backend Python Engineer"

    # 6. Non-existent job returns 404
    missing_resp = client.get("/api/v1/jobs/9999/translations")
    assert missing_resp.status_code == 404
