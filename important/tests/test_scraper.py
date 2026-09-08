from pathlib import Path

import httpx
import pytest

from src.app.database import get_db
from src.app.main import app
from src.app.scraper.http_client import SourceFetchError, fetch_source
from src.app.scraper.inspection import inspect_source
from src.app.scraper.orange_parser import parse_orange_jobs
from fastapi.testclient import TestClient


FIXTURE = Path(__file__).parent / "fixtures" / "orange_search_results.html"
STRUCTURED_FIXTURE = Path(__file__).parent / "fixtures" / "orange_search_results_structured.html"


def test_inspection_discovers_pagination_and_structured_data() -> None:
    source = fetch_source(
        "https://orange.jobs/fr/fr/search-results",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    headers={"content-type": "text/html"},
                    content=FIXTURE.read_bytes(),
                    request=request,
                )
            )
        ),
    )

    inspection = inspect_source(source)

    assert inspection.title == "Orange jobs"
    assert inspection.forms_count == 1
    assert inspection.has_next_link is True
    assert inspection.pagination_urls == [
        "https://orange.jobs/fr/fr/search-results?page=2"
    ]
    assert inspection.structured_data_blocks == 1


def test_orange_parser_extracts_normalized_job_candidate() -> None:
    source = fetch_source(
        "https://orange.jobs/fr/fr/search-results",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    headers={"content-type": "text/html"},
                    content=STRUCTURED_FIXTURE.read_bytes(),
                    request=request,
                )
            )
        ),
    )

    result = parse_orange_jobs(source)

    assert result.errors == []
    assert len(result.jobs) == 1
    job = result.jobs[0]
    assert job.external_job_id == "ICM-123"
    assert job.title == "Ingénieur réseau"
    assert job.job_url == "https://orange.jobs/fr/fr/job/123/apply"
    assert job.skills == ["Python", "réseau"]
    assert job.posted_at is not None


@pytest.mark.parametrize("status_code", [403, 404, 429, 500])
def test_fetch_source_surfaces_non_success_status(status_code: int) -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status_code, request=request)
        )
    )

    with pytest.raises(SourceFetchError) as error:
        fetch_source("https://example.test/careers", client=client)

    assert error.value.status_code == status_code


def test_inspection_endpoint_reports_fetch_failure(monkeypatch) -> None:
    def fail(_: str):
        raise SourceFetchError("source rate limited", status_code=429)

    monkeypatch.setattr("src.app.main.inspect_url", fail)
    target = type("Target", (), {"id": 1, "url": "https://example.test/careers"})()

    def fake_db():
        class FakeSession:
            def scalar(self, _):
                return target

        yield FakeSession()

    app.dependency_overrides[get_db] = fake_db
    response = TestClient(app).post("/api/v1/scrape-targets/1/inspect")
    app.dependency_overrides.clear()

    assert response.status_code == 502
    assert "source rate limited" in response.json()["detail"]
