from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, Company, Country, Job
from src.app.repositories.jobs import list_jobs
from src.app.scraper.search import expand_search_query


def test_expand_search_query() -> None:
    # French query expands to English synonyms
    french_res = expand_search_query("développeur python")
    assert "developer" in french_res or any("developer" in t for t in french_res)

    # English query expands to French synonyms
    english_res = expand_search_query("internship")
    assert "stage" in english_res or any("stage" in t for t in english_res)

    # Remote workplace terms
    remote_res = expand_search_query("télétravail")
    assert "remote" in remote_res or any("remote" in t for t in remote_res)


def test_list_jobs_multilingual_search() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        country = Country(id=1, name="Morocco", code="MA")
        company = Company(id=1, name="Test Corp", website_url="https://test.corp", active=True)
        session.add_all([country, company])
        session.flush()

        # Job in English
        job_en = Job(
            id=1,
            company_id=1,
            country_id=1,
            title="Senior Python Developer",
            job_url="https://test.corp/job/1",
            active=True,
            discovered_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        # Job in French
        job_fr = Job(
            id=2,
            company_id=1,
            country_id=1,
            title="Ingénieur Logiciel Fullstack",
            job_url="https://test.corp/job/2",
            active=True,
            discovered_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        session.add_all([job_en, job_fr])
        session.commit()

        # Search in French: "développeur" should find "Senior Python Developer"
        found_en, total_en = list_jobs(session, search="développeur")
        assert total_en >= 1
        assert any(j.id == 1 for j in found_en)

        # Search in English: "engineer" should find "Ingénieur Logiciel Fullstack"
        found_fr, total_fr = list_jobs(session, search="engineer")
        assert total_fr >= 1
        assert any(j.id == 2 for j in found_fr)


def test_user_country_preferences_endpoint() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        c1 = Country(id=1, name="Morocco", code="MA")
        c2 = Country(id=2, name="France", code="FR")
        session.add_all([c1, c2])
        session.commit()

    def fake_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = fake_db
    client = TestClient(app)

    # Register
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "multinational@example.com", "password": "Password123!"},
    )
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Set country preferences
    put_resp = client.put("/api/v1/profile/countries", headers=headers, json={"country_ids": [1, 2]})
    assert put_resp.status_code == 200
    user_data = put_resp.json()
    country_codes = {c["code"] for c in user_data["country_preferences"]}
    assert country_codes == {"MA", "FR"}

    # Update to only 1 country
    put_resp2 = client.put("/api/v1/profile/countries", headers=headers, json={"country_ids": [1]})
    assert put_resp2.status_code == 200
    assert len(put_resp2.json()["country_preferences"]) == 1
    assert put_resp2.json()["country_preferences"][0]["code"] == "MA"
