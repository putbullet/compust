from datetime import datetime
import json
import re
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from .http_client import FetchedSource
from .orange_parser import JobCandidate, ParseResult
from .url_normalizer import normalize_url

CAPGEMINI_API_HOST = "https://cg-jobstream-api.azurewebsites.net/api/job-search"


def resolve_capgemini_fetch_url(url: str) -> str:
    """If given the web portal search URL, translate to the backing public API endpoint."""
    parsed = urlsplit(url)
    if "capgemini.com" in parsed.netloc and "job-search" in parsed.path:
        query_dict = dict(parse_qs(parsed.query))
        # Keep clean scalar query parameters
        clean_params = {k: v[0] for k, v in query_dict.items() if v}
        if "page" not in clean_params:
            clean_params["page"] = "1"
        if "size" not in clean_params:
            clean_params["size"] = "11"
        if "country_code" not in clean_params:
            clean_params["country_code"] = "ma-en"
        return f"{CAPGEMINI_API_HOST}?{urlencode(clean_params)}"
    return url


def _parse_iso_date(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_capgemini_jobs(source: FetchedSource) -> ParseResult:
    body = source.body.strip()
    errors: list[str] = []
    data_dict: dict[str, Any] | None = None

    if body.startswith("{") and body.endswith("}"):
        try:
            data_dict = json.loads(body)
        except json.JSONDecodeError as exc:
            return ParseResult([], [f"Capgemini JSON parse error: {exc}"])
    else:
        # Check for embedded script data or schema.org JSON-LD
        soup = BeautifulSoup(source.body, "html.parser")
        for s in soup.select("script[type='application/ld+json']"):
            try:
                ld = json.loads(s.get_text())
                if isinstance(ld, dict) and "@graph" in ld:
                    # Found page metadata
                    pass
            except Exception:
                continue

    if not data_dict or not isinstance(data_dict, dict):
        return ParseResult([], ["Capgemini jobs response is not a valid JSON object"])

    raw_jobs = data_dict.get("data") or data_dict.get("jobs") or []
    if not isinstance(raw_jobs, list):
        return ParseResult([], ["Capgemini data payload is not a list"])

    candidates: list[JobCandidate] = []
    for index, job in enumerate(raw_jobs):
        if not isinstance(job, dict):
            errors.append(f"job[{index}]: record is not an object")
            continue

        title = job.get("title")
        job_id = str(job.get("ref") or job.get("id") or "").strip()
        job_url = job.get("apply_job_url") or job.get("url")

        if not title or not job_id:
            errors.append(f"job[{index}]: missing title or job identifier")
            continue

        if not job_url:
            job_url = f"https://careers.capgemini.com/job/{job_id}"

        from .sanitizer import sanitize_html, sanitize_plain_text
        from .vocabulary import normalize_employment_type
        clean_title = sanitize_plain_text(str(title)) or str(title).strip()
        raw_desc = job.get("description") or job.get("description_stripped")
        clean_desc = sanitize_html(str(raw_desc)) if raw_desc else None

        location = job.get("location") or job.get("country_name")
        department = job.get("department") or job.get("brand") or job.get("sbu") or job.get("professional_communities")
        contract_type = job.get("contract_type")
        posted_at = _parse_iso_date(job.get("updated_at") or job.get("indexed_at"))

        candidates.append(
            JobCandidate(
                title=clean_title,
                job_url=normalize_url(str(job_url)),
                external_job_id=job_id,
                location=sanitize_plain_text(str(location)) if location else None,
                description=clean_desc,
                employment_type=normalize_employment_type(str(contract_type)) if contract_type else None,
                remote_type=None,
                department=sanitize_plain_text(str(department)) if department else None,
                posted_at=posted_at,
                skills=[],
            )
        )

    return ParseResult(candidates, errors)


def find_capgemini_next_page_url(source: FetchedSource) -> str | None:
    """Inspect Capgemini API response or URL to determine if more pages exist."""
    body = source.body.strip()
    if not (body.startswith("{") and body.endswith("}")):
        return None

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None

    total = data.get("total", 0)
    count = data.get("count", 0)

    parsed = urlsplit(source.requested_url)
    query = parse_qs(parsed.query)

    try:
        current_page = int(query.get("page", ["1"])[0])
        page_size = int(query.get("size", [str(count or 11)])[0])
    except (ValueError, IndexError):
        current_page = 1
        page_size = 11

    if current_page * page_size < total:
        next_params = {k: v[0] for k, v in query.items()}
        next_params["page"] = str(current_page + 1)
        next_query = urlencode(next_params)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, next_query, ""))

    return None
