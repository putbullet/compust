import json
from datetime import datetime, timezone
import pytest
from src.app.scraper.http_client import FetchedSource
from src.app.scraper.platforms.greenhouse import GreenhouseAdapter
from src.app.scraper.platforms.lever import LeverAdapter
from src.app.scraper.platforms.smartrecruiters import SmartRecruitersAdapter
from src.app.scraper.platforms.workday import WorkdayAdapter


def make_source(url: str, body: str, content_type: str = "application/json") -> FetchedSource:
    return FetchedSource(
        requested_url=url,
        final_url=url,
        status_code=200,
        content_type=content_type,
        body=body,
        fetched_at=datetime.now(timezone.utc),
    )


def test_greenhouse_adapter_detection():
    assert GreenhouseAdapter.can_handle_url("https://boards.greenhouse.io/stripe")
    assert GreenhouseAdapter.can_handle_url("https://job-boards.greenhouse.io/airbnb/jobs/123")
    assert not GreenhouseAdapter.can_handle_url("https://jobs.lever.co/netflix")


def test_greenhouse_token_extraction():
    assert GreenhouseAdapter.extract_board_token("https://boards.greenhouse.io/acme-corp") == "acme-corp"
    assert GreenhouseAdapter.extract_board_token("https://boards.greenhouse.io/embed/job_board?for=fintech") == "fintech"


def test_greenhouse_api_parse():
    adapter = GreenhouseAdapter()
    data = {
        "jobs": [
            {
                "id": 12345,
                "title": "Lead Site Reliability Engineer",
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/12345",
                "location": {"name": "Casablanca, Morocco"},
                "departments": [{"name": "Platform Infrastructure"}],
                "updated_at": "2026-03-10T12:00:00Z"
            }
        ]
    }
    source = make_source("https://boards-api.greenhouse.io/v1/boards/acme/jobs", json.dumps(data))
    result = adapter.parse(source)

    assert len(result.errors) == 0
    assert len(result.jobs) == 1
    job = result.jobs[0]
    assert job.title == "Lead Site Reliability Engineer"
    assert job.job_url == "https://boards.greenhouse.io/acme/jobs/12345"
    assert job.department == "Platform Infrastructure"
    assert job.location == "Casablanca, Morocco"


def test_lever_adapter_detection():
    assert LeverAdapter.can_handle_url("https://jobs.lever.co/spotify")
    assert LeverAdapter.can_handle_url("https://lever.co/careers/stripe")
    assert not LeverAdapter.can_handle_url("https://boards.greenhouse.io/spotify")


def test_lever_api_parse():
    adapter = LeverAdapter()
    data = [
        {
            "id": "abc-789",
            "text": "Senior Machine Learning Engineer",
            "hostedUrl": "https://jobs.lever.co/spotify/abc-789",
            "categories": {
                "location": "Paris, France",
                "department": "AI Research",
                "commitment": "Full-time"
            },
            "workplaceType": "hybrid"
        }
    ]
    source = make_source("https://api.lever.co/v0/postings/spotify", json.dumps(data))
    result = adapter.parse(source)

    assert len(result.errors) == 0
    assert len(result.jobs) == 1
    job = result.jobs[0]
    assert job.title == "Senior Machine Learning Engineer"
    assert job.remote_type == "hybrid"
    assert job.employment_type == "full_time"


def test_smartrecruiters_adapter_detection():
    assert SmartRecruitersAdapter.can_handle_url("https://careers.smartrecruiters.com/AcmeCorp")
    assert SmartRecruitersAdapter.can_handle_url("https://jobs.smartrecruiters.com/Visa")
    assert not SmartRecruitersAdapter.can_handle_url("https://jobs.lever.co/visa")


def test_smartrecruiters_api_parse():
    adapter = SmartRecruitersAdapter()
    data = {
        "content": [
            {
                "id": "sr-111",
                "name": "Solutions Architect",
                "refNumber": "REF111A",
                "location": {"city": "Tangier", "region": "North", "country": "Morocco"},
                "typeOfEmployment": {"label": "Permanent"},
                "department": {"label": "Cloud Services"}
            }
        ]
    }
    source = make_source("https://api.smartrecruiters.com/v1/companies/AcmeCorp/postings", json.dumps(data))
    result = adapter.parse(source)

    assert len(result.errors) == 0
    assert len(result.jobs) == 1
    job = result.jobs[0]
    assert job.title == "Solutions Architect"
    assert "Tangier" in (job.location or "")
    assert job.external_job_id == "sr-111"


def test_workday_adapter_detection():
    assert WorkdayAdapter.can_handle_url("https://wd3.myworkdayjobs.com/Amazon_Jobs")
    assert WorkdayAdapter.can_handle_url("https://walmart.wd5.myworkdayjobs.com/en-US/WalmartExternal")
    assert not WorkdayAdapter.can_handle_url("https://jobs.lever.co/walmart")


def test_workday_cxs_parse():
    adapter = WorkdayAdapter()
    data = {
        "jobPostings": [
            {
                "title": "Principal Distributed Systems Architect",
                "externalPath": "/job/123",
                "jobPostingId": "JR-12345",
                "locationsText": "Remote - Morocco"
            }
        ]
    }
    source = make_source("https://wd3.myworkdayjobs.com/wday/cxs/company/jobs", json.dumps(data))
    result = adapter.parse(source)

    assert len(result.jobs) == 1
    assert result.jobs[0].title == "Principal Distributed Systems Architect"
    assert result.jobs[0].location == "Remote - Morocco"
