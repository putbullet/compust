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


class SmartRecruitersAdapter:
    name: str = "smartrecruiters"
    source_name: str = "jobs.smartrecruiters.com"

    @classmethod
    def can_handle_url(cls, url: str) -> bool:
        return "smartrecruiters.com" in url.lower()

    def parse(self, source: FetchedSource) -> ParseResult:
        body = source.body.strip()
        jobs: list[JobCandidate] = []
        errors: list[str] = []

        # 1. Direct postings API response
        if body.startswith("{") and body.endswith("}"):
            try:
                data = json.loads(body)
                content = data.get("content", [])
                for item in content:
                    title = sanitize_plain_text(item.get("name") or "")
                    if not title:
                        continue
                    ext_id = str(item.get("id") or "")
                    job_url = normalize_url(item.get("actions", {}).get("public", {}).get("url") or f"https://jobs.smartrecruiters.com/{ext_id}")
                    loc_dict = item.get("location", {})
                    loc_parts = [loc_dict.get("city"), loc_dict.get("region"), loc_dict.get("country")]
                    loc = ", ".join([str(p) for p in loc_parts if p]) or None
                    dept = item.get("department", {}).get("label") if isinstance(item.get("department"), dict) else None
                    emp_type = normalize_employment_type(item.get("typeOfEmployment", {}).get("label")) if isinstance(item.get("typeOfEmployment"), dict) else None

                    posted_at = None
                    released_date = item.get("releasedDate")
                    if released_date:
                        try:
                            posted_at = datetime.fromisoformat(released_date.replace("Z", "+00:00"))
                        except Exception:
                            pass

                    jobs.append(
                        JobCandidate(
                            title=title,
                            job_url=job_url,
                            external_job_id=ext_id,
                            location=loc,
                            department=dept,
                            employment_type=emp_type,
                            remote_type=normalize_remote_type(f"{title} {loc or ''}"),
                            description=f"<p>{title}</p>",
                            posted_at=posted_at,
                        )
                    )
                return ParseResult(jobs=jobs, errors=errors)
            except Exception as exc:
                errors.append(f"SmartRecruiters JSON error: {exc}")

        # 2. HTML job listings
        soup = BeautifulSoup(source.body, "html.parser")
        postings = soup.select(".opening-job, .js-job-item, li[class*='opening'], a.link--block")

        for p in postings:
            link = p if p.name == "a" else p.select_one("a[href]")
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
