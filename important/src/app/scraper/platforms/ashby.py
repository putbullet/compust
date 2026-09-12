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


class AshbyAdapter:
    name: str = "ashby"
    source_name: str = "jobs.ashbyhq.com"

    @classmethod
    def can_handle_url(cls, url: str) -> bool:
        url_lower = (url or "").lower()
        return "ashbyhq.com" in url_lower or "jobs.ashby" in url_lower

    @classmethod
    def extract_organization(cls, url: str) -> str | None:
        parsed = urlparse(url)
        # Check api path pattern: /posting-api/job-board/{org}
        api_match = re.search(r"/posting-api/job-board/([a-zA-Z0-9_\-]+)", parsed.path)
        if api_match:
            return api_match.group(1)

        # Standard job board: /secfix or /secfix/
        parts = [p for p in parsed.path.strip("/").split("/") if p and p not in ("api", "jobs", "embed")]
        if parts:
            return parts[0]
        return None

    @classmethod
    def resolve_fetch_url(cls, url: str) -> str:
        """Resolve web page URL to Ashby public posting JSON API."""
        org = cls.extract_organization(url)
        if org and "api.ashbyhq.com/posting-api/job-board" not in url:
            return f"https://api.ashbyhq.com/posting-api/job-board/{org}"
        return url

    @classmethod
    def parse(cls, source: FetchedSource) -> ParseResult:
        body = (source.body or "").strip()
        jobs: list[JobCandidate] = []
        errors: list[str] = []

        # 1. Direct JSON API parsing (standard for Ashby)
        if body.startswith("{") and body.endswith("}"):
            try:
                data = json.loads(body)
                raw_jobs = data.get("jobs", [])
                for rj in raw_jobs:
                    # Skip unlisted talent pools/jobs if explicitly marked False
                    if rj.get("isListed") is False:
                        continue

                    title = sanitize_plain_text(rj.get("title") or "")
                    if not title or len(title) < 3:
                        continue

                    ext_id = str(rj.get("id") or "")
                    job_url = rj.get("jobUrl")
                    if not job_url:
                        org = self.extract_organization(source.requested_url) or "org"
                        job_url = f"https://jobs.ashbyhq.com/{org}/{ext_id}"
                    job_url = normalize_url(job_url)

                    # Location
                    location = rj.get("location")
                    if not location:
                        addr = rj.get("address", {}).get("postalAddress", {})
                        if isinstance(addr, dict):
                            loc_parts = [addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry")]
                            location = ", ".join([str(p) for p in loc_parts if p])
                    if not location and rj.get("secondaryLocations"):
                        sec = rj["secondaryLocations"][0]
                        location = sec.get("locationName") or sec.get("location")

                    location = sanitize_plain_text(location) if location else None

                    # Remote type
                    remote_type = None
                    workplace = str(rj.get("workplaceType") or "").lower()
                    if "remote" in workplace or rj.get("isRemote"):
                        remote_type = "remote"
                    elif "hybrid" in workplace:
                        remote_type = "hybrid"
                    elif "onsite" in workplace or "on_site" in workplace:
                        remote_type = "on_site"
                    elif location:
                        remote_type = normalize_remote_type(f"{title} {location}")

                    # Employment type
                    raw_emp = rj.get("employmentType")
                    emp_type = normalize_employment_type(str(raw_emp)) if raw_emp else None

                    # Department
                    dept = sanitize_plain_text(rj.get("department") or rj.get("team") or "") or None

                    # Posted at
                    posted_at = None
                    pub_str = rj.get("publishedAt")
                    if pub_str and isinstance(pub_str, str):
                        try:
                            posted_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                        except Exception:
                            pass

                    # Description
                    desc_html = rj.get("descriptionHtml")
                    desc_plain = rj.get("descriptionPlain")
                    description = sanitize_html(desc_html) if desc_html else (f"<p>{desc_plain}</p>" if desc_plain else f"<p>{title}</p>")

                    # Skills detection
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
                            external_job_id=ext_id or title[:30],
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
            except Exception as exc:
                errors.append(f"Failed to parse Ashby JSON response: {exc}")

        # 2. Fallback: Parse HTML if response was HTML (e.g. from SSR or embedded JSON)
        soup = BeautifulSoup(source.body, "html.parser")
        # Check window.__appData script
        for sc in soup.find_all("script"):
            txt = sc.get_text()
            if "window.__appData" in txt:
                m = re.search(r"window\.__appData\s*=\s*(\{.+?\});", txt, re.DOTALL)
                if m:
                    try:
                        app_data = json.loads(m.group(1))
                        # Some Ashby builds include preloaded jobBoard
                        job_board = app_data.get("jobBoard") or app_data.get("organization", {}).get("jobBoard")
                        if job_board and isinstance(job_board, dict):
                            postings = job_board.get("jobPostings", [])
                            # Re-run candidate extraction on postings
                            for p in postings:
                                t = sanitize_plain_text(p.get("title") or "")
                                if t:
                                    jid = str(p.get("id") or "")
                                    jobs.append(
                                        JobCandidate(
                                            title=t,
                                            job_url=normalize_url(f"https://jobs.ashbyhq.com/{self.extract_organization(source.requested_url) or 'org'}/{jid}"),
                                            external_job_id=jid,
                                            location=p.get("locationName"),
                                            description=f"<p>{t}</p>",
                                        )
                                    )
                    except Exception as e:
                        errors.append(f"Error parsing window.__appData in Ashby HTML: {e}")

        if not jobs and not errors:
            errors.append("Ashby HTML shell received without job data. Consider using resolved API URL.")

        return ParseResult(jobs=jobs, errors=errors)

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        # Ashby posting API returns complete list for the board in single response
        return None
