from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, Company, Country, Job


def test_user_applications_crud_and_lifecycle() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        country = Country(id=1, name="Morocco", code="MA")
        company = Company(id=1, name="Acme", website_url="https://acme.test", active=True)
        session.add_all([country, company])
        session.flush()

        job1 = Job(
            id=10,
            company_id=1,
            country_id=1,
            title="Backend Dev",
            job_url="https://acme.test/job/10",
            active=True,
            discovered_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        job2 = Job(
            id=20,
            company_id=1,
            country_id=1,
            title="Frontend Dev",
            job_url="https://acme.test/job/20",
            active=True,
            discovered_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        session.add_all([job1, job2])
        session.commit()

    def fake_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = fake_db
    client = TestClient(app)

    # 1. Register candidate
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "applicant@test.com", "password": "Password123!"},
    )
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Initially empty applications
    apps_resp = client.get("/api/v1/applications", headers=headers)
    assert apps_resp.status_code == 200
    assert apps_resp.json() == []

    # 3. Bookmark/save job 10
    save_resp = client.post("/api/v1/applications/10", headers=headers, json={"status": "saved", "notes": "Looks interesting"})
    assert save_resp.status_code == 201
    saved_app = save_resp.json()
    assert saved_app["job_id"] == 10
    assert saved_app["status"] == "saved"
    assert saved_app["notes"] == "Looks interesting"
    app_id = saved_app["id"]

    # 4. Advance application stage to 'applied'
    patch_resp = client.patch(f"/api/v1/applications/{app_id}", headers=headers, json={"status": "applied", "notes": "Applied on portal"})
    assert patch_resp.status_code == 200
    patched_data = patch_resp.json()
    assert patched_data["status"] == "applied"
    assert patched_data["applied_at"] is not None

    # 5. Filter applications by status
    filter_applied = client.get("/api/v1/applications?status=applied", headers=headers)
    assert len(filter_applied.json()) == 1

    filter_saved = client.get("/api/v1/applications?status=saved", headers=headers)
    assert len(filter_saved.json()) == 0

    # 6. Save second job 20
    client.post("/api/v1/applications/20", headers=headers, json={"status": "interviewing"})
    all_apps = client.get("/api/v1/applications", headers=headers).json()
    assert len(all_apps) == 2

    # 7. Delete application by job id
    del_job_resp = client.delete("/api/v1/applications/jobs/20", headers=headers)
    assert del_job_resp.status_code == 200

    remaining = client.get("/api/v1/applications", headers=headers).json()
    assert len(remaining) == 1
    assert remaining[0]["job_id"] == 10

    # 8. Delete application by app id
    del_app_resp = client.delete(f"/api/v1/applications/{app_id}", headers=headers)
    assert del_app_resp.status_code == 200
    assert client.get("/api/v1/applications", headers=headers).json() == []
