from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, Country, Company, Job


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Seed standard test country and company
    c_ma = Country(id=1, name="Morocco", code="MA")
    c_fr = Country(id=2, name="France", code="FR")
    comp = Company(id=1, name="Orange", website_url="https://orange.ma", active=True)
    comp.countries = [c_ma]
    job = Job(
        id=1,
        company_id=1,
        country_id=1,
        title="Python Engineer",
        job_url="https://orange.ma/jobs/1",
        description="We are looking for a Python developer with Docker and FastAPI experience.",
        discovered_at=now,
        created_at=now,
        updated_at=now,
        active=True,
    )
    session.add_all([c_ma, c_fr, comp, job])
    session.commit()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
