import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..http_client import FetchedSource
from ..orange_parser import JobCandidate, ParseResult
from ..sanitizer import sanitize_html, sanitize_plain_text
from ..url_normalizer import normalize_url
from ..vocabulary import normalize_employment_type, normalize_remote_type


class WorkdayAdapter:
    name: str = "workday"
    source_name: str = "myworkdayjobs.com"

    @classmethod
    def can_handle_url(cls, url: str) -> bool:
        return "myworkdayjobs.com" in url.lower() or "workday" in url.lower()

    def parse(self, source: FetchedSource) -> ParseResult:
        body = source.body.strip()
        jobs: list[JobCandidate] = []
        errors: list[str] = []

        # 1. Workday CXS JSON endpoint response
        if body.startswith("{") and body.endswith("}"):
            try:
                data = json.loads(body)
                postings = data.get("jobPostings", [])
                for p in postings:
                    title = sanitize_plain_text(p.get("title") or "")
                    if not title:
                        continue
                    ext_id = str(p.get("bulletFields", [None])[0] or p.get("jobPostingId") or "")
                    external_path = p.get("externalPath") or ""
                    job_url = normalize_url(urljoin(source.final_url, external_path)) if external_path else source.final_url
                    loc = p.get("locationsText")
                    posted_on = p.get("postedOn")

                    jobs.append(
                        JobCandidate(
                            title=title,
                            job_url=job_url,
                            external_job_id=ext_id or title[:30],
                            location=loc,
                            employment_type=normalize_employment_type(p.get("timeType")),
                            remote_type=normalize_remote_type(f"{title} {loc or ''}"),
                            description=f"<p>{title}</p>",
                        )
                    )
                return ParseResult(jobs=jobs, errors=errors)
            except Exception as exc:
                errors.append(f"Workday JSON error: {exc}")

        # 2. HTML embedded fallback
        soup = BeautifulSoup(source.body, "html.parser")
        postings = soup.select("[data-automation-id='jobResults'] li, ul[role='list'] li, a[data-automation-id='jobTitle']")

        for p in postings:
            link = p if p.name == "a" else p.select_one("a[data-automation-id='jobTitle'], a[href]")
            if not link:
                continue
            href = link.get("href", "")
            title = sanitize_plain_text(link.get_text(" ", strip=True))
            if not title or len(title) < 3:
                continue

            full_url = normalize_url(urljoin(source.final_url, href))
            ext_id = re.sub(r"\W+", "_", urlparse(full_url).path.strip("/")) or title[:30]

            jobs.append(
                JobCandidate(
                    title=title,
                    job_url=full_url,
                    external_job_id=ext_id,
                    location=None,
                    description=f"<p>{title}</p>",
                )
            )

        return ParseResult(jobs=jobs, errors=errors)

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        return None
