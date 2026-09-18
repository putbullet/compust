import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .http_client import FetchedSource
from .url_normalizer import normalize_url


@dataclass(frozen=True)
class JobCandidate:
    title: str
    job_url: str
    external_job_id: str
    location: str | None = None
    description: str | None = None
    employment_type: str | None = None
    remote_type: str | None = None
    department: str | None = None
    posted_at: datetime | None = None
    skills: list[str] = field(default_factory=list)
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_period: str | None = None
    discovery_source: str | None = None


@dataclass(frozen=True)
class ParseResult:
    jobs: list[JobCandidate]
    errors: list[str]
    detected_result_count: int | None = None


def _parse_date(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_ddo(soup: BeautifulSoup) -> dict[str, Any] | None:
    for script in soup.select("script"):
        text = script.get_text()
        marker = "phApp.ddo = "
        start = text.find(marker)
        if start < 0:
            continue
        try:
            value, _ = json.JSONDecoder().raw_decode(text[start + len(marker) :])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def find_orange_next_page_url(source: FetchedSource) -> str | None:
    """Extract next page URL by following rel='next' (e.g. from/s pattern)."""
    soup = BeautifulSoup(source.body, "html.parser")
    for link in soup.select("a[rel*='next'], link[rel*='next']"):
        href = link.get("href")
        if href and isinstance(href, str) and href.strip():
            absolute = urljoin(source.final_url, href.strip())
            return normalize_url(absolute)
    return None


def parse_orange_jobs(source: FetchedSource) -> ParseResult:
    soup = BeautifulSoup(source.body, "html.parser")
    ddo = _extract_ddo(soup)
    if ddo is None:
        return ParseResult([], ["Orange structured data object was not found"])

    jobs = (
        ddo.get("eagerLoadRefineSearch", {})
        .get("data", {})
        .get("jobs", [])
    )
    if not isinstance(jobs, list):
        return ParseResult([], ["Orange jobs payload is not a list"])

    parsed: list[JobCandidate] = []
    errors: list[str] = []
    for index, job in enumerate(jobs):
        if not isinstance(job, dict):
            errors.append(f"job[{index}]: record is not an object")
            continue
        title = job.get("title")
        job_id = job.get("jobId")
        job_url = job.get("applyUrl")
        if not all(isinstance(value, str) and value.strip() for value in (title, job_id, job_url)):
            errors.append(f"job[{index}]: missing title, jobId, or applyUrl")
            continue
        full_url = normalize_url(urljoin(source.final_url, job_url.strip()))
        from .sanitizer import sanitize_html, sanitize_plain_text
        from .vocabulary import normalize_employment_type, normalize_remote_type, normalize_skills

        raw_contract = sanitize_plain_text(job.get("contractType") or job.get("type"))
        raw_work_model = sanitize_plain_text(job.get("workModel"))
        raw_skills = (
            job.get("ml_skills")
            if isinstance(job.get("ml_skills"), list)
            else (job.get("skills") if isinstance(job.get("skills"), list) else [])
        )

        parsed.append(
            JobCandidate(
                title=sanitize_plain_text(title) or title.strip(),
                job_url=full_url,
                external_job_id=job_id.strip(),
                location=sanitize_plain_text(job.get("location") or job.get("address")),
                description=sanitize_html(job.get("descriptionTeaser")),
                employment_type=normalize_employment_type(raw_contract) or raw_contract,
                remote_type=normalize_remote_type(raw_work_model) or raw_work_model,
                department=sanitize_plain_text(job.get("category")),
                posted_at=_parse_date(job.get("dateCreated") or job.get("postedDate")),
                skills=normalize_skills(raw_skills),
            )
        )
    return ParseResult(parsed, errors)
