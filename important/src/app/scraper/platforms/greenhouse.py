import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from ..http_client import FetchedSource
from ..orange_parser import JobCandidate, ParseResult
from ..sanitizer import sanitize_html, sanitize_plain_text
from ..url_normalizer import normalize_url
from ..vocabulary import normalize_employment_type, normalize_remote_type


class GreenhouseAdapter:
    name: str = "greenhouse"
    source_name: str = "boards.greenhouse.io"

    @classmethod
    def can_handle_url(cls, url: str) -> bool:
        url_lower = url.lower()
        return "greenhouse.io" in url_lower or "boards.greenhouse" in url_lower or "grnh.se" in url_lower

    @classmethod
    def extract_board_token(cls, url: str) -> str | None:
        parsed = urlparse(url)
        # 1. check query params first (e.g. ?for=token)
        if "for=" in parsed.query:
            query_match = re.search(r"(?:^|[?&])for=([a-zA-Z0-9_\-]+)", parsed.query)
            if query_match:
                return query_match.group(1)

        # 2. boards.greenhouse.io/{token} or job-boards.greenhouse.io/{token}
        parts = [p for p in parsed.path.strip("/").split("/") if p and p not in ("embed", "job_board", "v1", "boards", "jobs")]
        if parts:
            return parts[0]
        return None

    def parse(self, source: FetchedSource) -> ParseResult:
        body = source.body.strip()
        jobs: list[JobCandidate] = []
        errors: list[str] = []

        # 1. Check if direct JSON API response
        if body.startswith("{") and body.endswith("}"):
            try:
                data = json.loads(body)
                raw_jobs = data.get("jobs", [])
                for rj in raw_jobs:
                    title = sanitize_plain_text(rj.get("title") or "")
                    if not title:
                        continue
                    job_url = normalize_url(rj.get("absolute_url") or "")
                    ext_id = str(rj.get("id") or "")
                    loc = rj.get("location", {}).get("name") if isinstance(rj.get("location"), dict) else None
                    desc = sanitize_html(rj.get("content") or "")

                    posted_at = None
                    updated_at_str = rj.get("updated_at")
                    if updated_at_str:
                        try:
                            posted_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                        except Exception:
                            pass

                    dept = None
                    depts = rj.get("departments")
                    if isinstance(depts, list) and depts:
                        dept = depts[0].get("name") if isinstance(depts[0], dict) else str(depts[0])

                    jobs.append(
                        JobCandidate(
                            title=title,
                            job_url=job_url,
                            external_job_id=ext_id,
                            location=loc,
                            department=dept,
                            description=desc,
                            posted_at=posted_at,
                            employment_type=None,
                            remote_type=normalize_remote_type(f"{title} {loc or ''} {desc}"),
                        )
                    )
                return ParseResult(jobs=jobs, errors=errors)
            except Exception as exc:
                errors.append(f"Greenhouse JSON parse error: {exc}")

        # 2. HTML embedded board parsing
        soup = BeautifulSoup(source.body, "html.parser")
        postings = soup.select(".opening, .job-post, [data-mapped='true'], tr.job")
        if not postings:
            # Fallback to any greenhouse job link
            postings = soup.select("a[href*='/jobs/']")

        for p in postings:
            link = p if p.name == "a" else p.select_one("a[href]")
            if not link:
                continue
            href = link.get("href", "")
            title = sanitize_plain_text(link.get_text(" ", strip=True))
            if not title or len(title) < 3:
                continue

            id_match = re.search(r"/jobs/(\d+)", href)
            ext_id = id_match.group(1) if id_match else title[:30]
            loc_el = p.select_one(".location, .city")
            loc = sanitize_plain_text(loc_el.get_text(" ", strip=True)) if loc_el else None

            jobs.append(
                JobCandidate(
                    title=title,
                    job_url=normalize_url(href),
                    external_job_id=ext_id,
                    location=loc,
                    description=f"<p>{title}</p>",
                    employment_type=None,
                    remote_type=normalize_remote_type(f"{title} {loc or ''}"),
                )
            )

        return ParseResult(jobs=jobs, errors=errors)

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        return None
