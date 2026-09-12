import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .http_client import FetchedSource
from .orange_parser import JobCandidate, ParseResult
from .url_normalizer import normalize_url


def parse_inwi_jobs(source: FetchedSource) -> ParseResult:
    # Unwrap template and turbo-stream tags so bs4 treats contents as standard elements
    clean_body = re.sub(r"</?(?:template|turbo-stream)[^>]*>", "", source.body)
    soup = BeautifulSoup(clean_body, "html.parser")
    candidates: list[JobCandidate] = []
    errors: list[str] = []
    seen_ids: set[str] = set()

    links = soup.select("a[href*='/jobs/']")
    for index, link in enumerate(links):
        href = link.get("href", "")
        match = re.search(r"/jobs/(\d+)-([^/?#]+)", href)
        if not match:
            continue

        job_id = match.group(1)
        if job_id in seen_ids:
            continue
        seen_ids.add(job_id)

        card = link.find_parent("li") or link
        text_blocks = [t.strip() for t in card.stripped_strings if t.strip()]

        title_el = card.select_one("[title]")
        if title_el and title_el.get("title"):
            title = title_el["title"].strip()
        elif text_blocks:
            title = text_blocks[0]
        else:
            title = match.group(2).replace("-", " ").strip().title()

        title = re.sub(r"\s+", " ", title).strip()

        # Parse department and location from additional text blocks
        department: str | None = None
        location: str | None = None
        for block in text_blocks[1:]:
            cleaned_block = block.strip(" •·-\n\t\r")
            if not cleaned_block:
                continue
            if any(loc_hint in cleaned_block.lower() for loc_hint in ("marina", "casablanca", "rabat", "oujda", "tanger", "fès", "marrakech")):
                location = cleaned_block
            elif not department:
                department = cleaned_block

        full_url = normalize_url(urljoin(source.final_url, href))
        from .sanitizer import sanitize_plain_text
        from .vocabulary import normalize_employment_type

        clean_title = sanitize_plain_text(title) or title
        candidates.append(
            JobCandidate(
                title=clean_title,
                job_url=full_url,
                external_job_id=job_id,
                location=sanitize_plain_text(location) if location else None,
                description=None,
                employment_type=normalize_employment_type(clean_title),
                remote_type=None,
                department=sanitize_plain_text(department) if department else None,
                posted_at=None,
                skills=[],
            )
        )

    return ParseResult(candidates, errors)


def find_inwi_next_page_url(source: FetchedSource) -> str | None:
    """Find next page in Inwi portal (e.g. /jobs/show_more?page=2)."""
    soup = BeautifulSoup(source.body, "html.parser")
    next_link = soup.select_one("a[href*='show_more'], a[rel*='next'], link[rel*='next']")
    if next_link:
        href = next_link.get("href")
        if href and isinstance(href, str) and href.strip():
            return normalize_url(urljoin(source.final_url, href.strip()))
    return None
