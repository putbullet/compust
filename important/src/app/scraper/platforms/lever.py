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


class LeverAdapter:
    name: str = "lever"
    source_name: str = "jobs.lever.co"

    @classmethod
    def can_handle_url(cls, url: str) -> bool:
        return "jobs.lever.co" in url.lower() or "lever.co" in url.lower()

    def parse(self, source: FetchedSource) -> ParseResult:
        body = source.body.strip()
        jobs: list[JobCandidate] = []
        errors: list[str] = []

        # 1. API JSON response
        if body.startswith("[") and body.endswith("]"):
            try:
                raw_list = json.loads(body)
                for item in raw_list:
                    title = sanitize_plain_text(item.get("text") or "")
                    if not title:
                        continue
                    job_url = normalize_url(item.get("hostedUrl") or item.get("applyUrl") or "")
                    ext_id = str(item.get("id") or "")
                    categories = item.get("categories", {})
                    loc = categories.get("location") if isinstance(categories, dict) else None
                    dept = categories.get("department") if isinstance(categories, dict) else None
                    emp_type = normalize_employment_type(categories.get("commitment")) if isinstance(categories, dict) else None
                    desc = sanitize_html(item.get("descriptionPlain") or item.get("description") or "")

                    posted_at = None
                    created_at_ms = item.get("createdAt")
                    if isinstance(created_at_ms, (int, float)):
                        try:
                            posted_at = datetime.fromtimestamp(created_at_ms / 1000.0)
                        except Exception:
                            pass

                    workplace = item.get("workplaceType")
                    remote_type = normalize_remote_type(str(workplace)) if workplace else normalize_remote_type(f"{title} {loc or ''} {desc}")

                    jobs.append(
                        JobCandidate(
                            title=title,
                            job_url=job_url,
                            external_job_id=ext_id,
                            location=loc,
                            department=dept,
                            employment_type=emp_type,
                            remote_type=remote_type,
                            description=desc,
                            posted_at=posted_at,
                        )
                    )
                return ParseResult(jobs=jobs, errors=errors)
            except Exception as exc:
                errors.append(f"Lever JSON parse error: {exc}")

        # 2. HTML postings
        soup = BeautifulSoup(source.body, "html.parser")
        postings = soup.select(".posting")

        for p in postings:
            link = p.select_one("a.posting-title, a[data-qa='posting-name']") or p.select_one("a[href]")
            if not link:
                continue
            href = link.get("href", "")
            title = sanitize_plain_text((link.select_one("h5") or link).get_text(" ", strip=True))
            if not title:
                continue

            loc_el = p.select_one(".posting-categories .location, .sort-by-location")
            loc = sanitize_plain_text(loc_el.get_text(" ", strip=True)) if loc_el else None
            dept_el = p.select_one(".posting-categories .department, .sort-by-team")
            dept = sanitize_plain_text(dept_el.get_text(" ", strip=True)) if dept_el else None
            commit_el = p.select_one(".posting-categories .commitment, .sort-by-commitment")
            emp_type = normalize_employment_type(commit_el.get_text(" ", strip=True)) if commit_el else None

            ext_id = re.sub(r"\W+", "_", urlparse(href).path.strip("/")) or title[:30]

            jobs.append(
                JobCandidate(
                    title=title,
                    job_url=normalize_url(href),
                    external_job_id=ext_id,
                    location=loc,
                    department=dept,
                    employment_type=emp_type,
                    remote_type=normalize_remote_type(f"{title} {loc or ''}"),
                    description=f"<p>{title}</p>",
                )
            )

        return ParseResult(jobs=jobs, errors=errors)

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        return None
