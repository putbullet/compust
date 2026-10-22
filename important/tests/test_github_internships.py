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


def test_canonical_deduplication_and_repeated_sync_stability(tmp_path, monkeypatch):
    """Proves repeated syncs of the same source listings do not continuously balloon the count."""
    from src.app.schemas_github_internships import GitHubInternshipItem, GitHubInternshipsResponse
    from src.app.services.github_internships_service import (
        canonical_internship_key,
        merge_internships,
        get_internships_cache_file,
    )

    test_cache = tmp_path / "test_internships_cache.json"
    monkeypatch.setattr(
        "src.app.services.github_internships_service.get_internships_cache_file",
        lambda: test_cache,
    )
    monkeypatch.setattr(
        "src.app.services.github_internships_service.SEED_FILE",
        tmp_path / "nonexistent_seed.json",
    )

    service = GitHubInternshipsService()

    # Create dummy mock raw items that simulate duplicate listings across 3 repos
    mock_items = [
        GitHubInternshipItem(
            id="sim_1",
            company="Acme Corp",
            role="Software Engineer Intern",
            location="San Francisco, CA",
            category="Software Engineering",
            season="2027",
            source_repo_id="simplify-2027",
            source_repo_name="SimplifyJobs",
            source_repo_url="https://github.com/...",
            apply_url="https://acme.com/apply",
            visa_status="sponsors_visa",
            visa_text="Sponsors Visa",
            is_closed=False,
        ),
        GitHubInternshipItem(
            id="zap_1",
            company="Acme Corp",
            role="Software Engineer Intern",
            location="San Francisco, CA",
            category="Software Engineering",
            season="2027",
            source_repo_id="zapply-2027",
            source_repo_name="Zapply",
            source_repo_url="https://github.com/...",
            apply_url="https://acme.com/apply",
            visa_status="not_specified",
            visa_text="Not Specified",
            is_closed=False,
        ),
        GitHubInternshipItem(
            id="van_1",
            company="Acme Corp",
            role="Software Engineer Intern",
            location="San Francisco, CA",
            category="Software Engineering",
            season="2027",
            source_repo_id="vansh-2027",
            source_repo_name="Vansh",
            source_repo_url="https://github.com/...",
            apply_url="https://acme.com/apply",
            visa_status="sponsors_visa",
            visa_text="Sponsors Visa",
            is_closed=False,
        ),
        GitHubInternshipItem(
            id="zap_2",
            company="Beta Dynamics",
            role="Machine Learning Intern",
            location="Remote",
            category="Data Science, AI & ML",
            season="2027",
            source_repo_id="zapply-2027",
            source_repo_name="Zapply",
            source_repo_url="https://github.com/...",
            apply_url="https://beta.ai/jobs",
            visa_status="us_citizen_only",
            visa_text="US Citizen Only",
            is_closed=False,
        ),
    ]

    # Mock fetch and parse to return our 4 raw items (representing 2 unique roles)
    monkeypatch.setattr(service, "_fetch_repo_content", lambda cfg: "dummy")
    monkeypatch.setattr(service, "_parse_repo", lambda cfg, content: mock_items if cfg["id"] == "simplify-2027" else [])

    # First sync
    res1 = service.sync_all_repos()
    count_run_1 = len(res1.items)
    active_run_1 = res1.stats.active_listings
    assert count_run_1 == 2, f"Expected 2 canonical deduplicated items, got {count_run_1}"
    assert active_run_1 == 2

    # Second sync with exact same source data
    res2 = service.sync_all_repos()
    count_run_2 = len(res2.items)
    active_run_2 = res2.stats.active_listings

    # Verify count does NOT balloon on subsequent syncs
    assert count_run_2 == count_run_1 == 2
    assert active_run_2 == active_run_1 == 2


def test_user_tracked_internship_protected_from_retirement(tmp_path, monkeypatch):
    """Proves user-tracked internships are strictly preserved active even when removed from source."""
    from src.app.schemas_github_internships import GitHubInternshipItem
    from src.app.services.github_internships_service import (
        is_internship_user_tracked,
        get_user_tracked_internships,
    )

    tracked_item = GitHubInternshipItem(
        id="tracked_1",
        company="Special Saved Corp",
        role="Security Engineer Intern",
        location="Remote",
        category="Cybersecurity",
        season="2026",  # Past season would normally be archived!
        source_repo_id="speedyapply-intl-2027",
        source_repo_name="SpeedyApply",
        source_repo_url="https://github.com/...",
        apply_url="https://specialcorp.com/careers/internship",
        visa_status="sponsors_visa",
        visa_text="Sponsors Visa",
        is_closed=False,
    )

    # Simulate user having tracked this via URL
    tracked_urls = {"https://specialcorp.com/careers/internship"}
    tracked_pairs = set()

    assert is_internship_user_tracked(tracked_item, tracked_urls, tracked_pairs) is True


