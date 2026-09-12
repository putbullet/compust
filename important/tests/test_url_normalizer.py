import pytest
from src.app.scraper.url_normalizer import normalize_url, is_tracking_param


def test_lowercase_scheme_and_domain() -> None:
    assert (
        normalize_url("HTTPS://Orange.Jobs:443/fr/fr/careers")
        == "https://orange.jobs/fr/fr/careers"
    )
    assert (
        normalize_url("HTTP://EXAMPLE.COM:80/path")
        == "http://example.com/path"
    )


def test_preserves_non_default_ports() -> None:
    assert (
        normalize_url("https://example.com:8443/jobs")
        == "https://example.com:8443/jobs"
    )


def test_strips_fragments() -> None:
    assert (
        normalize_url("https://orange.jobs/fr/fr/job/123#apply-now")
        == "https://orange.jobs/fr/fr/job/123"
    )


def test_removes_tracking_parameters_and_preserves_application_parameters() -> None:
    raw = (
        "https://orange.jobs/fr/fr/search-results"
        "?utm_source=google&s=1&ref=linkedin&from=10&utm_medium=cpc&jobId=456&trk=direct"
    )
    expected = (
        "https://orange.jobs/fr/fr/search-results?from=10&jobId=456&s=1"
    )
    assert normalize_url(raw) == expected


def test_path_normalization_resolves_dot_segments() -> None:
    raw = "https://orange.jobs/fr/fr/search/../job/./123"
    assert normalize_url(raw) == "https://orange.jobs/fr/fr/job/123"


def test_empty_or_whitespace_url() -> None:
    assert normalize_url("") == ""
    assert normalize_url("   ") == ""


def test_is_tracking_param() -> None:
    assert is_tracking_param("utm_campaign") is True
    assert is_tracking_param("fbclid") is True
    assert is_tracking_param("gclid") is True
    assert is_tracking_param("from") is False
    assert is_tracking_param("s") is False
    assert is_tracking_param("ref", "linkedin") is True
    assert is_tracking_param("ref", "R-5673") is False


def test_preserves_job_reference_ref_param() -> None:
    url = "https://www.deloitte.com/fr/fr/careers/content/job/results/offer.html?ref=R-5673"
    assert normalize_url(url) == "https://www.deloitte.com/fr/fr/careers/content/job/results/offer.html?ref=R-5673"
