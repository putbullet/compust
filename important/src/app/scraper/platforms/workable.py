import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from ..http_client import FetchedSource
from ..orange_parser import JobCandidate, ParseResult
from ..sanitizer import sanitize_html, sanitize_plain_text
from ..url_normalizer import normalize_url
from ..vocabulary import normalize_employment_type, normalize_remote_type, SKILL_SYNONYMS

COMMON_SKILLS = sorted(list(set(SKILL_SYNONYMS.values())))


class WorkableAdapter:
    name: str = "workable"
    source_name: str = "apply.workable.com"

    @classmethod
    def can_handle_url(cls, url: str) -> bool:
        url_lower = (url or "").lower()
        return "workable.com" in url_lower or "apply.workable" in url_lower

    @classmethod
    def extract_account(cls, url: str) -> str | None:
        parsed = urlparse(url)
        # Check API path: /api/v1/widget/accounts/{acc} or /api/v3/accounts/{acc}
        acc_match = re.search(r"/accounts/([a-zA-Z0-9_\-]+)", parsed.path)
        if acc_match:
            return acc_match.group(1)

        # Standard job board: /riot or /riot/
        parts = [p for p in parsed.path.strip("/").split("/") if p and p not in ("api", "j", "widget")]
        if parts:
            return parts[0]
        return None

    extract_account_name = extract_account

    @classmethod
    def resolve_fetch_url(cls, url: str) -> str:
        """Resolve web page URL to Workable public widget JSON API."""
        account = cls.extract_account(url)
        if account and "/api/" not in url:
            # Widget endpoint returns all published jobs in a single, high-fidelity GET response
            return f"https://apply.workable.com/api/v1/widget/accounts/{account}"
        return url

    @classmethod
    def parse(cls, source: FetchedSource) -> ParseResult:
        body = (source.body or "").strip()
        jobs: list[JobCandidate] = []
        errors: list[str] = []
        account = cls.extract_account(source.requested_url) or cls.extract_account(source.final_url) or "company"

        # 1. Direct JSON API parsing (Widget or v3 API)
        if body.startswith("{") and body.endswith("}"):
            try:
                data = json.loads(body)

                # Format A: Widget endpoint format ({ "jobs": [...] })
                if "jobs" in data and isinstance(data["jobs"], list):
                    for wj in data["jobs"]:
                        title = sanitize_plain_text(wj.get("title") or "")
                        if not title or len(title) < 3:
                            continue

                        shortcode = wj.get("shortcode") or str(wj.get("id") or "")
                        raw_url = wj.get("url") or f"https://apply.workable.com/{account}/j/{shortcode}/"
                        job_url = normalize_url(raw_url)

                        # Location
                        loc_parts = [wj.get("city"), wj.get("state"), wj.get("country")]
                        location = ", ".join([str(p).strip() for p in loc_parts if p]) or None
                        location = sanitize_plain_text(location) if location else None

                        # Remote
                        remote_type = None
                        if wj.get("telecommuting") or wj.get("workplace") == "remote":
                            remote_type = "remote"
                        elif wj.get("workplace") == "hybrid":
                            remote_type = "hybrid"
                        elif wj.get("workplace") == "on_site":
                            remote_type = "on_site"
                        elif location:
                            remote_type = normalize_remote_type(f"{title} {location}")

                        # Employment type
                        raw_emp = wj.get("employment_type") or wj.get("type")
                        emp_type = normalize_employment_type(str(raw_emp)) if raw_emp else None

                        # Department
                        dept = sanitize_plain_text(wj.get("department") or "") or None

                        # Posted at
                        posted_at = None
                        pub_str = wj.get("published_on") or wj.get("published")
                        if pub_str and isinstance(pub_str, str):
                            try:
                                posted_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                            except Exception:
                                pass

                        # Description
                        desc_raw = wj.get("description")
                        description = sanitize_html(desc_raw) if desc_raw else f"<p>{title}</p>"

                        detected_skills = []
                        if description:
                            desc_lower = description.lower()
                            for skill in COMMON_SKILLS:
                                if re.search(rf"\b{re.escape(skill.lower())}\b", desc_lower):
                                    detected_skills.append(skill)

                        jobs.append(
                            JobCandidate(
                                title=title,
                                job_url=job_url,
                                external_job_id=shortcode or title[:30],
                                location=location,
                                description=description,
                                employment_type=emp_type,
                                remote_type=remote_type,
                                department=dept,
                                posted_at=posted_at,
                                skills=detected_skills,
                            )
                        )
                    return ParseResult(jobs=jobs, errors=errors)

                # Format B: v3 API format ({ "results": [...] })
                elif "results" in data and isinstance(data["results"], list):
                    for rj in data["results"]:
                        title = sanitize_plain_text(rj.get("title") or "")
                        if not title or len(title) < 3:
                            continue

                        shortcode = rj.get("shortcode") or str(rj.get("id") or "")
                        job_url = normalize_url(f"https://apply.workable.com/{account}/j/{shortcode}/")

                        # Location
                        loc = rj.get("location", {})
                        if isinstance(loc, dict):
                            loc_parts = [loc.get("city"), loc.get("region"), loc.get("country")]
                            location = ", ".join([str(p).strip() for p in loc_parts if p]) or None
                        else:
                            location = str(loc) if loc else None
                        location = sanitize_plain_text(location) if location else None

                        # Remote
                        remote_type = None
                        if rj.get("remote") or rj.get("workplace") == "remote":
                            remote_type = "remote"
                        elif rj.get("workplace") == "hybrid":
                            remote_type = "hybrid"
                        elif rj.get("workplace") == "on_site":
                            remote_type = "on_site"
                        elif location:
                            remote_type = normalize_remote_type(f"{title} {location}")

                        # Employment type
                        raw_emp = rj.get("type")
                        emp_type = normalize_employment_type(str(raw_emp)) if raw_emp else None

                        # Department
                        dept_val = rj.get("department")
                        dept = dept_val[0] if isinstance(dept_val, list) and dept_val else str(dept_val or "")
                        dept = sanitize_plain_text(dept) if dept else None

                        # Posted at
                        posted_at = None
                        pub_str = rj.get("published")
                        if pub_str and isinstance(pub_str, str):
                            try:
                                posted_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                            except Exception:
                                pass

                        jobs.append(
                            JobCandidate(
                                title=title,
                                job_url=job_url,
                                external_job_id=shortcode or str(rj.get("id") or title[:30]),
                                location=location,
                                description=f"<p>{title}</p>",
                                employment_type=emp_type,
                                remote_type=remote_type,
                                department=dept,
                                posted_at=posted_at,
                                skills=[],
                            )
                        )
                    return ParseResult(jobs=jobs, errors=errors)

            except Exception as exc:
                errors.append(f"Failed to parse Workable JSON response: {exc}")

        # 2. Fallback: Parse HTML shell if JSON not returned
        soup = BeautifulSoup(source.body, "html.parser")
        for sc in soup.find_all("script"):
            txt = sc.get_text()
            if "window.careers" in txt:
                # Configuration found
                pass

        if not jobs and not errors:
            errors.append("Workable HTML shell received without job data. Consider using resolved widget API URL.")

        return ParseResult(jobs=jobs, errors=errors)

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        # Widget endpoint returns all jobs.
        # For v3 API with nextPage token, we can construct query if needed
        try:
            body = (source.body or "").strip()
            if body.startswith("{") and body.endswith("}"):
                data = json.loads(body)
                next_token = data.get("nextPage")
                if next_token:
                    account = self.extract_account(source.requested_url) or "account"
                    return f"https://apply.workable.com/api/v3/accounts/{account}/jobs?token={next_token}"
        except Exception:
            pass
        return None
