import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .http_client import FetchedSource


@dataclass(frozen=True)
class JobCandidate:
    title: str
    job_url: str
    external_job_id: str
    location: str | None
    description: str | None
    employment_type: str | None
    remote_type: str | None
    department: str | None
    posted_at: datetime | None
    skills: list[str]


@dataclass(frozen=True)
class ParseResult:
    jobs: list[JobCandidate]
    errors: list[str]


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
        parsed.append(
            JobCandidate(
                title=title.strip(),
                job_url=urljoin(source.final_url, job_url),
                external_job_id=job_id.strip(),
                location=job.get("location") or job.get("address"),
                description=job.get("descriptionTeaser"),
                employment_type=job.get("contractType") or job.get("type"),
                remote_type=job.get("workModel"),
                department=job.get("category"),
                posted_at=_parse_date(job.get("postedDate")),
                skills=[
                    skill.strip()
                    for skill in job.get("ml_skills", [])
                    if isinstance(skill, str) and skill.strip()
                ],
            )
        )
    return ParseResult(parsed, errors)
