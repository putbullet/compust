import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from ..http_client import FetchedSource
from ..orange_parser import JobCandidate, ParseResult
from ..sanitizer import sanitize_html, sanitize_plain_text
from ..url_normalizer import normalize_url
from ..vocabulary import normalize_employment_type, normalize_remote_type, SKILL_SYNONYMS

COMMON_SKILLS = sorted(list(set(SKILL_SYNONYMS.values())))


class WorkdayAdapter:
    name: str = "workday"
    source_name: str = "myworkdayjobs.com"

    @classmethod
    def can_handle_url(cls, url: str) -> bool:
        url_lower = (url or "").lower()
        return "myworkdayjobs.com" in url_lower or "workday" in url_lower

    @classmethod
    def extract_cxs_endpoint(cls, url: str) -> tuple[str, str, str] | None:
        """
        Extracts (cxs_jobs_api_url, tenant, site) from any Workday URL.
        Example:
          https://darktrace.wd3.myworkdayjobs.com/DarktaceExternal
          -> ('https://darktrace.wd3.myworkdayjobs.com/wday/cxs/darktrace/DarktaceExternal/jobs', 'darktrace', 'DarktaceExternal')
        """
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if "myworkdayjobs.com" not in netloc and "workday" not in netloc:
            return None

        # Extract tenant from subdomain: {tenant}.wd3.myworkdayjobs.com
        sub_parts = netloc.split(".")
        tenant = sub_parts[0] if len(sub_parts) > 2 and sub_parts[0] != "www" else None

        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        # Remove language prefix if present (e.g. en-US, fr-FR)
        if path_parts and re.match(r"^[a-z]{2}(?:-[a-z]{2,4})?$", path_parts[0], re.I):
            path_parts.pop(0)

        # Remove leading 'wday' / 'cxs' if already pointing to API
        if len(path_parts) >= 2 and path_parts[0].lower() == "wday" and path_parts[1].lower() == "cxs":
            path_parts = path_parts[2:]
            if len(path_parts) >= 2:
                tenant = path_parts[0]
                site = path_parts[1]
                return f"{parsed.scheme}://{parsed.netloc}/wday/cxs/{tenant}/{site}/jobs", tenant, site

        if not path_parts:
            return None

        site = path_parts[0]
        if (site.lower() == "job" or site.lower() == "jobs") and len(path_parts) > 1:
            site = path_parts[1]

        if not tenant:
            tenant = path_parts[0]
            site = path_parts[1] if len(path_parts) > 1 else "External"

        cxs_url = f"{parsed.scheme}://{parsed.netloc}/wday/cxs/{tenant}/{site}/jobs"
        return cxs_url, tenant, site

    @classmethod
    def parse_job_postings_json(
        cls,
        postings: list[dict[str, Any]],
        base_origin: str,
        site: str,
    ) -> list[JobCandidate]:
        candidates: list[JobCandidate] = []
        for p in postings:
            title = sanitize_plain_text(p.get("title") or "")
            if not title:
                continue

            bullet_fields = p.get("bulletFields") or []
            ext_id = str(bullet_fields[0] if bullet_fields else p.get("jobPostingId") or "")

            external_path = p.get("externalPath") or ""
            if external_path:
                job_url = normalize_url(f"{base_origin}/{site}{external_path}")
            else:
                job_url = normalize_url(base_origin)

            loc = p.get("locationsText")
            emp_type = normalize_employment_type(p.get("timeType"))
            rem_type = normalize_remote_type(f"{title} {loc or ''}")

            desc_parts = [f"<p><strong>{title}</strong></p>"]
            if loc:
                desc_parts.append(f"<p>Location: {loc}</p>")
            if p.get("postedOn"):
                desc_parts.append(f"<p>Posted: {p.get('postedOn')}</p>")
            if ext_id:
                desc_parts.append(f"<p>Requisition ID: {ext_id}</p>")

            skills = []
            title_loc_lower = f"{title} {loc or ''}".lower()
            for skill in COMMON_SKILLS:
                if re.search(rf"\b{re.escape(skill.lower())}\b", title_loc_lower):
                    skills.append(skill)

            candidates.append(
                JobCandidate(
                    title=title,
                    job_url=job_url,
                    external_job_id=ext_id or title[:30],
                    location=loc,
                    employment_type=emp_type,
                    remote_type=rem_type,
                    description="".join(desc_parts),
                    skills=skills,
                )
            )
        return candidates

    def parse(self, source: FetchedSource) -> ParseResult:
        body = (source.body or "").strip()
        jobs: list[JobCandidate] = []
        errors: list[str] = []
        target_url = source.requested_url or source.final_url
        parsed_target = urlparse(target_url)
        base_origin = f"{parsed_target.scheme}://{parsed_target.netloc}"

        # 1. Direct CXS JSON response payload (e.g. from fixture or API)
        if body.startswith("{") and body.endswith("}"):
            try:
                data = json.loads(body)
                postings = data.get("jobPostings", [])
                cxs_meta = self.extract_cxs_endpoint(target_url)
                site = cxs_meta[2] if cxs_meta else "jobs"
                candidates = self.parse_job_postings_json(postings, base_origin, site)
                return ParseResult(jobs=candidates, errors=errors)
            except Exception as exc:
                errors.append(f"Workday JSON parse error: {exc}")

        # 2. Query Workday CXS POST API directly for dynamic SPA portals
        cxs_meta = self.extract_cxs_endpoint(target_url)
        if cxs_meta:
            cxs_url, tenant, site = cxs_meta
            qs = parse_qs(parsed_target.query)
            requested_offset = int(qs["offset"][0]) if "offset" in qs and qs["offset"][0].isdigit() else None

            try:
                all_postings: list[dict[str, Any]] = []
                offset = requested_offset or 0
                limit = 20
                total = None
                max_pages_to_fetch = 1 if requested_offset is not None else 10

                pages_fetched = 0
                while pages_fetched < max_pages_to_fetch:
                    payload = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}
                    resp = httpx.post(
                        cxs_url,
                        json=payload,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"},
                        timeout=12.0,
                    )
                    if resp.status_code != 200:
                        errors.append(f"Workday CXS API returned HTTP {resp.status_code} for {cxs_url}")
                        break

                    data = resp.json()
                    postings = data.get("jobPostings", [])
                    if not postings:
                        break

                    all_postings.extend(postings)
                    if total is None:
                        total = data.get("total")

                    offset += len(postings)
                    pages_fetched += 1

                    if total is not None and offset >= total:
                        break

                if all_postings:
                    candidates = self.parse_job_postings_json(all_postings, base_origin, site)
                    return ParseResult(jobs=candidates, errors=errors)
            except Exception as exc:
                errors.append(f"Workday CXS API request failed: {exc}")

        # 3. HTML DOM fallback (if static SSR exists or mock HTML)
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
