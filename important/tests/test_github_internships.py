import pytest
from fastapi.testclient import TestClient
from src.app.main import app
from src.app.services.github_internships_service import GitHubInternshipsService, guess_company_domain, get_logo_url


client = TestClient(app)


def test_guess_company_domain():
    assert guess_company_domain("Google") == "google.com"
    assert guess_company_domain("Microsoft") == "microsoft.com"
    assert guess_company_domain("Amazon") == "amazon.com"
    assert guess_company_domain("NVIDIA") == "nvidia.com"
    assert guess_company_domain("Walt Disney", "https://jobs.disneycareers.com/123") == "disney.com"


def test_get_logo_url():
    url = get_logo_url("nvidia.com")
    assert "nvidia.com" in url
    assert url.startswith("https://t1.gstatic.com/faviconV2")


def test_service_curated_internships():
    service = GitHubInternshipsService()
    response = service.get_curated_internships()
    assert response.stats.total_listings > 0
    assert len(response.repositories) == 7
    assert len(response.items) > 0

    first = response.items[0]
    assert first.company
    assert first.role
    assert first.visa_status in [
        "sponsors_visa",
        "no_sponsorship",
        "us_citizen_only",
        "canada_authorized",
        "not_specified",
        "closed",
    ]


def test_api_curated_internships_endpoint():
    res = client.get("/api/v1/internships/github-repos")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "stats" in data
    assert "repositories" in data
    assert data["stats"]["total_listings"] > 0
    assert len(data["repositories"]) == 7


def test_api_curated_internships_filters():
    # Filter by Visa status
    res = client.get("/api/v1/internships/github-repos?visa_status=sponsors_visa")
    assert res.status_code == 200
    data = res.json()
    for it in data["items"][:20]:
        assert it["visa_status"] == "sponsors_visa"

    # Filter by repository
    res_repo = client.get("/api/v1/internships/github-repos?repo_id=zapply-2027")
    assert res_repo.status_code == 200
    data_repo = res_repo.json()
    for it in data_repo["items"][:20]:
        assert it["source_repo_id"] == "zapply-2027"


def test_category_normalization_and_no_html_in_categories():
    service = GitHubInternshipsService()
    response = service.get_curated_internships()
    for it in response.items:
        if it.category:
            assert "<details>" not in it.category
            assert "</summary>" not in it.category
            assert "<br>" not in it.category

