from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, Company, Country, ScrapeTarget


def test_openapi_is_available() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Compust API"
    assert "/api/v1/companies/{company_id}" in response.json()["paths"]
    assert "/api/v1/countries/{code}" in response.json()["paths"]
    assert "/api/v1/scrape-targets" in response.json()["paths"]
    assert "/api/v1/scrape-targets/{target_id}" in response.json()["paths"]
    assert "/api/v1/scrape-targets/{target_id}/inspect" in response.json()["paths"]
    assert "/api/v1/scrape-targets/{target_id}/parse" in response.json()["paths"]
    assert "/api/v1/scrape-targets/{target_id}/sync" in response.json()["paths"]


def test_health_endpoint_uses_database_dependency(monkeypatch) -> None:
    class FakeResult:
        def execute(self, statement):
            assert str(statement) == "SELECT 1"

    def fake_db():
        yield FakeResult()

    app.dependency_overrides.clear()
    from src.app.database import get_db

    app.dependency_overrides[get_db] = fake_db
    client = TestClient(app)

    response = client.get("/health")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"
    assert "latency_ms" in response.json()


def test_scrape_target_endpoints() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        country = Country(name="Morocco", code="MA")
        company = Company(
            name="Example",
            website_url="https://example.test",
            careers_url="https://example.test/careers",
            active=True,
            countries=[country],
        )
        session.add(company)
        session.flush()
        company_id = company.id
        session.add(
            ScrapeTarget(
                company_id=company.id,
                url=company.careers_url,
                type="careers",
                active=True,
            )
        )
        session.commit()

    def fake_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = fake_db
    client = TestClient(app)
    response = client.get("/api/v1/scrape-targets")
    detail = client.get("/api/v1/scrape-targets/1")
    app.dependency_overrides.clear()
    engine.dispose()

    assert response.status_code == 200
    assert response.json()[0]["url"] == "https://example.test/careers"
    assert detail.status_code == 200
    assert detail.json()["company_id"] == company_id
