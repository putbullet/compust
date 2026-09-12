import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..http_client import FetchedSource, fetch_source
from ..orange_parser import JobCandidate, ParseResult
from ..sanitizer import sanitize_html, sanitize_plain_text
from ..url_normalizer import normalize_url
from ..vocabulary import normalize_employment_type, normalize_remote_type, SKILL_SYNONYMS

COMMON_SKILLS = sorted(list(set(SKILL_SYNONYMS.values())))


class TeamtailorAdapter:
    name: str = "teamtailor"
    source_name: str = "teamtailor.com"

    @classmethod
    def can_handle_url(cls, url: str) -> bool:
        url_lower = (url or "").lower()
        return "teamtailor.com" in url_lower

    @classmethod
    def can_handle_source(cls, source: FetchedSource) -> bool:
        target_url = (source.requested_url or source.final_url or "").lower()
        if cls.can_handle_url(target_url):
            return True
        body = source.body or ""
        body_lower = body.lower()
        if "teamtailor-cdn.com" in body_lower or "app.teamtailor.com" in body_lower:
            return True
        if 'data-controller="careersite' in body_lower or "careersite--" in body_lower:
            return True
        if 'href="https://www.teamtailor.com' in body_lower or "powered by teamtailor" in body_lower:
            return True
        if 'type="application/rss+xml"' in body_lower and "/jobs.rss" in body_lower:
            return True
        return False

    @classmethod
    def parse_rss(cls, rss_text: str, source_url: str) -> list[JobCandidate]:
        """Parse Teamtailor standard jobs.rss XML feed."""
        soup = BeautifulSoup(rss_text, "xml")
        items = soup.find_all("item")
        if not items:
            return []

        candidates: list[JobCandidate] = []
        for item in items:
            title_el = item.find("title")
            title = sanitize_plain_text(title_el.get_text() if title_el else "")
            if not title:
                continue

            link_el = item.find("link")
            job_url = normalize_url(link_el.get_text().strip() if link_el else source_url)

            guid_el = item.find("guid")
            ext_id = guid_el.get_text().strip() if guid_el else re.sub(r"\W+", "_", urlparse(job_url).path.strip("/"))

            desc_el = item.find("description")
            desc_html = sanitize_html(desc_el.get_text() if desc_el else f"<p>{title}</p>")

            loc_el = item.find("locations") or item.find("location")
            loc = sanitize_plain_text(loc_el.get_text(" ", strip=True)) if loc_el else None

            remote_el = item.find("remoteStatus") or item.find("remote")
            remote_val = remote_el.get_text().strip() if remote_el else ""
            remote_type = normalize_remote_type(remote_val or (loc or ""))

            dept_el = item.find("department")
            dept = sanitize_plain_text(dept_el.get_text().strip()) if dept_el else None

            role_el = item.find("role") or item.find("roleType")
            emp_val = role_el.get_text().strip() if role_el else ""
            emp_type = normalize_employment_type(emp_val)

            pub_date_el = item.find("pubDate")
            posted_at = None
            if pub_date_el:
                try:
                    from email.utils import parsedate_to_datetime
                    posted_at = parsedate_to_datetime(pub_date_el.get_text().strip()).replace(tzinfo=None)
                except Exception:
                    posted_at = None

            skills = []
            desc_lower = (desc_html or "").lower()
            for skill in COMMON_SKILLS:
                if re.search(rf"\b{re.escape(skill.lower())}\b", desc_lower):
                    skills.append(skill)

            candidates.append(
                JobCandidate(
                    title=title,
                    job_url=job_url,
                    external_job_id=ext_id,
                    location=loc,
                    department=dept,
                    employment_type=emp_type,
                    remote_type=remote_type,
                    description=desc_html,
                    posted_at=posted_at,
                    skills=skills,
                )
            )

        return candidates

    @classmethod
    def parse_html(cls, soup: BeautifulSoup, source_url: str) -> list[JobCandidate]:
        """Parse Teamtailor HTML job list with high fidelity."""
        candidates: list[JobCandidate] = []
        seen_urls: set[str] = set()

        job_links = [
            a for a in soup.find_all("a", href=True)
            if re.search(r"/jobs/\d+", a["href"])
        ]

        for link in job_links:
            href = link["href"]
            full_url = normalize_url(urljoin(source_url, href))
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            title = sanitize_plain_text(link.get_text(" ", strip=True))
            if not title or len(title) < 3:
                continue

            id_match = re.search(r"/jobs/(\d+)", href)
            ext_id = id_match.group(1) if id_match else re.sub(r"\W+", "_", urlparse(full_url).path.strip("/"))

            card = link.find_parent("li") or link.find_parent("div")
            card_text = card.get_text(" ", strip=True) if card else ""

            location = None
            dept = None
            if card:
                meta_div = card.select_one("div.text-md, [class*='text-sm'], [class*='sub'], [class*='location']")
                if meta_div and meta_div != link:
                    meta_text = sanitize_plain_text(meta_div.get_text(" ", strip=True))
                    parts = [p.strip() for p in re.split(r"[•·\|\-]", meta_text) if p.strip()]
                    if parts:
                        location = parts[-1] if len(parts) > 1 else parts[0]
                        if len(parts) > 1:
                            dept = parts[0]

            emp_type = normalize_employment_type(card_text)
            rem_type = normalize_remote_type(card_text)

            candidates.append(
                JobCandidate(
                    title=title,
                    job_url=full_url,
                    external_job_id=ext_id,
                    location=location,
                    department=dept,
                    employment_type=emp_type,
                    remote_type=rem_type,
                    description=f"<p>{title}</p>",
                    skills=[],
                )
            )

        return candidates

    def parse(self, source: FetchedSource) -> ParseResult:
        errors: list[str] = []
        target_url = source.requested_url or source.final_url
        body = (source.body or "").strip()

        # 1. If body is already RSS XML
        if body.startswith("<?xml") or "<rss" in body:
            jobs = self.parse_rss(body, target_url)
            if jobs:
                return ParseResult(jobs=jobs, errors=errors)

        soup = BeautifulSoup(source.body, "html.parser")

        # 2. Try RSS feed if linked in HTML or standard /jobs.rss path
        rss_link = soup.select_one("link[type='application/rss+xml'][href*='jobs']")
        rss_url = None
        if rss_link and rss_link.get("href"):
            rss_url = urljoin(target_url, rss_link["href"])
        else:
            parsed = urlparse(target_url)
            rss_url = f"{parsed.scheme}://{parsed.netloc}/jobs.rss"

        if rss_url:
            try:
                rss_source = fetch_source(rss_url, timeout_seconds=6.0)
                if rss_source.status_code == 200 and ("<rss" in rss_source.body or "<?xml" in rss_source.body):
                    jobs = self.parse_rss(rss_source.body, target_url)
                    if jobs:
                        return ParseResult(jobs=jobs, errors=errors)
            except Exception as e:
                errors.append(f"Teamtailor RSS fetch attempt failed: {str(e)}")

        # 3. Fallback to HTML DOM extraction
        jobs = self.parse_html(soup, target_url)
        if not jobs:
            errors.append("Teamtailor detected but no job cards found via RSS or DOM.")

        return ParseResult(jobs=jobs, errors=errors)
