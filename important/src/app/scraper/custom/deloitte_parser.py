from datetime import datetime
import json
import re
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup
import httpx

from ..http_client import FetchedSource
from ...models import Company, ScrapeTarget
from ..orange_parser import JobCandidate, ParseResult
from ..sanitizer import sanitize_html, sanitize_plain_text
from ..url_normalizer import normalize_url
from ..vocabulary import normalize_employment_type, normalize_remote_type, SKILL_SYNONYMS

COMMON_SKILLS = sorted(list(set(SKILL_SYNONYMS.values())))

DELOITTE_FR_API_ENDPOINT = "https://f6nv82mofd.execute-api.eu-west-1.amazonaws.com/prod/offres_v2"
DELOITTE_FR_API_KEY = "JKT2pdDzG35s3MoPXwmy3TjLcCALbuj9SP6bTPt1"


def parse_deloitte_fr_api(url: str) -> list[JobCandidate]:
    """Directly fetch and parse vacancies from the Deloitte France AWS API Gateway."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    city_name = qs.get("city_name", [None])[0]

    headers = {
        "Content-Type": "application/json",
        "x-api-key": DELOITTE_FR_API_KEY,
        "Referer": "https://www.deloitte.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    payload = {
        "size": 100,
        "from": 0,
        "fields": [
            "id", "jobname", "city_name", "city", "country",
            "activity_title", "activity", "contract_type", "link",
            "job_category_title", "last_posting_date", "reference",
            "description", "remote_type"
        ],
    }
    if city_name:
        payload["location"] = {"city_name_and_around": [city_name]}

    resp = httpx.post(DELOITTE_FR_API_ENDPOINT, headers=headers, json=payload, timeout=20.0)
    if resp.status_code != 200:
        return []

    data = resp.json()
    results = data.get("results", [])
    candidates: list[JobCandidate] = []

    for item in results:
        title = sanitize_plain_text(item.get("jobname") or "")
        if not title:
            continue

        ref = str(item.get("reference") or item.get("id") or "")
        # Canonical portal URL
        job_url = f"https://www.deloitte.com/fr/fr/careers/content/job/results/offer.html?ref={ref}" if ref else (item.get("link") or url)
        loc = sanitize_plain_text(item.get("city") or item.get("city_name") or item.get("country") or "")
        dept = sanitize_plain_text(item.get("activity_title") or item.get("activity") or "")
        desc = sanitize_html(item.get("description") or "")
        emp_type = normalize_employment_type(item.get("contract_type"))
        rem_type = normalize_remote_type(item.get("remote_type") or desc)

        posted_at = None
        date_str = item.get("last_posting_date")
        if date_str:
            try:
                posted_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except Exception:
                pass

        # Skills
        found_skills = []
        desc_lower = desc.lower()
        for skill in COMMON_SKILLS:
            if re.search(rf"\b{re.escape(skill.lower())}\b", desc_lower):
                found_skills.append(skill)

        candidates.append(
            JobCandidate(
                title=title,
                job_url=job_url,
                external_job_id=ref,
                location=loc or None,
                department=dept or None,
                employment_type=emp_type,
                remote_type=rem_type,
                description=desc,
                posted_at=posted_at,
                skills=found_skills,
            )
        )

    return candidates


def parse_deloitte_jobs(source: FetchedSource) -> ParseResult:
    """Custom parser for Deloitte career portals."""
    target_url = source.final_url or source.requested_url or ""

    # 1. Check if Deloitte France API endpoint applies
    if "deloitte.com/fr" in target_url.lower() or "results.html" in target_url.lower() or "city_name" in target_url.lower():
        try:
            api_jobs = parse_deloitte_fr_api(target_url)
            if api_jobs:
                return ParseResult(jobs=api_jobs, errors=[])
        except Exception as exc:
            pass  # Fall back to HTML parsing

    # 2. HTML parsing for static / server-rendered pages (e.g., jobs.deloitte.com)
    soup = BeautifulSoup(source.body, "html.parser")
    candidates: list[JobCandidate] = []
    errors: list[str] = []
    seen_ids: set[str] = set()

    # Exclude institutional/editorial teaser cards (e.g. .cmp-teaser, "Évoluer au sein de...")
    cards = soup.select(".job-tile, .card--job, .card-job, [data-job-id], li.job-item, tr.job-result")
    if not cards:
        cards = soup.select("article, a[href*='/careers/job/'], a[href*='/job/']")

    for card in cards:
        # Ignore promotional / editorial teaser widgets
        card_classes = " ".join(card.get("class", [])) if hasattr(card, "get") else ""
        if "cmp-teaser" in card_classes or "editorial" in card_classes:
            continue

        link = card if card.name == "a" else card.select_one("a[href]")
        if not link:
            continue
        href = link.get("href", "")
        if not href or href.startswith("#") or "javascript:" in href:
            continue

        # Ignore institutional articles / life at deloitte links
        if any(bad in href.lower() for bad in ["deloitte-life", "formation-et-evolution", "development/", "cmp-teaser"]):
            continue

        title_el = card.select_one(".title, .job-title, h1, h2, h3, h4") or link
        raw_title = title_el.get_text(" ", strip=True)
        title = sanitize_plain_text(raw_title)
        if not title or len(title) < 3 or any(w in title.lower() for w in ["cookie", "privacy", "évoluer au sein", "qui sommes-nous"]):
            continue

        full_url = normalize_url(urljoin(source.final_url, href))

        # Job ID extraction
        job_id = None
        id_attr = card.get("data-job-id") if hasattr(card, "get") else None
        if id_attr:
            job_id = str(id_attr)
        else:
            match = re.search(r"/(?:job|requisition|posting|id)/([a-zA-Z0-9_\-]+)", href, re.IGNORECASE)
            if match:
                job_id = match.group(1)
            else:
                job_id = re.sub(r"\W+", "_", urlparse(full_url).path.strip("/")) or title[:30]

        if job_id in seen_ids:
            continue
        seen_ids.add(job_id)

        # Location, department, employment metadata
        card_text = card.get_text(" ", strip=True)
        loc_el = card.select_one(".job-location, .job__location, .location, .city, [data-location]")
        location = sanitize_plain_text(loc_el.get_text(" ", strip=True)) if loc_el else None

        dept_el = card.select_one(".department, .service-line, .business")
        dept = sanitize_plain_text(dept_el.get_text(" ", strip=True)) if dept_el else None

        emp_type = normalize_employment_type(card_text)
        rem_type = normalize_remote_type(card_text)

        # Detect skills
        found_skills = []
        lower_text = card_text.lower()
        for skill in COMMON_SKILLS:
            if re.search(rf"\b{re.escape(skill.lower())}\b", lower_text):
                found_skills.append(skill)

        candidates.append(
            JobCandidate(
                title=title,
                job_url=full_url,
                external_job_id=job_id,
                location=location,
                department=dept,
                employment_type=emp_type,
                remote_type=rem_type,
                description=sanitize_html(f"<h3>{title}</h3><p>{card_text}</p>"),
                skills=found_skills,
            )
        )

    return ParseResult(jobs=candidates, errors=errors)


def find_deloitte_next_page_url(source: FetchedSource) -> str | None:
    soup = BeautifulSoup(source.body, "html.parser")
    next_link = soup.select_one("a[rel='next'], a.next-page, a.pagination__next, a[aria-label*='Next']")
    if next_link and next_link.get("href"):
        return urljoin(source.final_url, next_link["href"])
    return None


class DeloitteScraperStrategy:
    name: str = "deloitte"
    source_name: str = "deloitte.com"

    def can_handle(self, target: ScrapeTarget, company: Company | None = None) -> bool:
        target_url = (target.url or "").lower()
        company_careers = (company.careers_url or "").lower() if company else ""
        target_type = (target.type or "").lower()

        if target_type in ("deloitte", "deloitte_careers"):
            return True
        if "deloitte.com" in target_url or "deloitte.com" in company_careers:
            return True
        return False

    def parse(self, source: FetchedSource) -> ParseResult:
        return parse_deloitte_jobs(source)

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        return find_deloitte_next_page_url(source)
