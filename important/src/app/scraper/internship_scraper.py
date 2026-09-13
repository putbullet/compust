import json
import re
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from ..logging import get_logger
from .http_client import fetch_source, SourceFetchError
from .internship_terminology import expand_internship_queries, get_languages_for_country, strip_diacritics
from .job_title_intelligence.index import get_job_title_index
from .robots_checker import is_path_allowed_by_robots
from .sanitizer import sanitize_html, sanitize_plain_text
from .search_provider import DuckDuckGoHtmlSearchProvider, SearchProvider
from .ssrf_validator import SSRFValidationError, validate_safe_url
from .universal_parser import extract_json_ld_jobs
from .url_normalizer import normalize_url

logger = get_logger("scraper.internship_scraper")


class InternshipOpportunity(BaseModel):
    id: str
    title: str
    company: str
    location: str = "Unspecified"
    country: str = ""
    description: str = ""
    requirements: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    internship_type: str = "Internship"
    duration: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    application_deadline: str | None = None
    publication_date: str | None = None
    source_url: str
    application_url: str
    source_domain: str
    language: str = "en"
    confidence_score: int = Field(default=75, ge=0, le=100)
    is_year_match: bool = False


class InternshipSearchDiagnostics(BaseModel):
    queries_executed: list[str] = Field(default_factory=list)
    sources_discovered: int = 0
    sources_checked: int = 0
    sources_unavailable: int = 0
    sources_rejected_non_job: int = 0
    valid_opportunities_found: int = 0
    execution_time_ms: float = 0.0


class InternshipSearchResponse(BaseModel):
    opportunities: list[InternshipOpportunity] = Field(default_factory=list)
    diagnostics: InternshipSearchDiagnostics
    related_titles: list[str] = Field(default_factory=list)


# Negative patterns indicating non-job pages (blogs, guides, general overviews)
NEGATIVE_PAGE_PATTERNS = [
    r"how\s+to\s+get\s+(?:an?\s+)?internship",
    r"tips\s+for\s+(?:applying|interviews|interns)",
    r"top\s+\d+\s+internships",
    r"welcome\s+to\s+our\s+internship\s+portal",
    r"internship\s+program\s+overview",
    r"about\s+our\s+internship\s+program",
    r"life\s+as\s+an\s+intern",
    r"why\s+intern\s+at",
    r"guide\s+to\s+internships?",
    r"blog|article|news|stories",
    r"university\s+relations|campus\s+recruiting\s+overview",
    r"student\s+faq|frequently\s+asked\s+questions",
    r"all\s+openings|search\s+results|filter\s+jobs",
]

# Positive internship markers in titles or headings
POSITIVE_INTERNSHIP_TITLE_PATTERNS = [
    r"\b(intern|internship|interns)\b",
    r"\b(stage|stagiaire|pfe)\b",
    r"\b(praktik|praktikum|praktikant|praktikantin|werkstudent)\b",
    r"\b(practicas|becario|becaria|pasantia|pasante)\b",
    r"\b(tirocinio|stagista|tirocinante)\b",
    r"\b(apprentice|apprenticeship|alternance)\b",
    r"\b(trainee|graduate\s+trainee)\b",
]

# Date/Year extraction helpers
YEAR_PATTERN = re.compile(r"\b(202[5-9]|203[0-5])\b")
DEADLINE_PATTERNS = [
    re.compile(r"(?:deadline|apply\s+by|closing\s+date|date\s+limite|bewerbungsfrist)[:\s]+([^\n<]+)", re.I),
    re.compile(r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})", re.I),
    re.compile(r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+202[5-9])", re.I),
]


class InternshipIntelligenceScraper:
    """End-to-end intelligent internship discovery and structured extraction engine."""

    def __init__(self, search_provider: SearchProvider | None = None) -> None:
        self.search_provider = search_provider or DuckDuckGoHtmlSearchProvider()
        self.title_index = get_job_title_index()

    def search_and_extract(
        self,
        field: str,
        country: str | None = None,
        year: int | str | None = None,
        max_results: int = 20,
    ) -> InternshipSearchResponse:
        """Discover, classify, extract, deduplicate, and rank internships."""
        t0 = time.perf_counter()
        diagnostics = InternshipSearchDiagnostics()

        # 1. Title Intelligence from job-titles.json
        related_titles = self.title_index.find_related_internship_titles(field, limit=12)

        # 2. Query expansion
        queries = expand_internship_queries(field, country=country, year=year, limit=6)
        diagnostics.queries_executed = queries

        # 3. Discovery of candidate URLs
        candidate_urls: list[str] = []
        seen_candidate_urls: set[str] = set()

        for q in queries:
            discovered = self.search_provider.search(q, limit=6)
            for u in discovered:
                norm_u = normalize_url(u)
                if norm_u and norm_u not in seen_candidate_urls:
                    seen_candidate_urls.add(norm_u)
                    candidate_urls.append(norm_u)
            if len(candidate_urls) >= 25:
                break

        diagnostics.sources_discovered = len(candidate_urls)

        # 4. Ingest and classify candidate pages
        raw_opportunities: list[InternshipOpportunity] = []

        for candidate_url in candidate_urls:
            diagnostics.sources_checked += 1

            # SSRF Protection
            try:
                validate_safe_url(candidate_url)
            except SSRFValidationError as ssrf_err:
                logger.warning(f"SSRF blocked URL '{candidate_url}': {ssrf_err}")
                diagnostics.sources_unavailable += 1
                continue

            # Robots check
            try:
                if not is_path_allowed_by_robots(candidate_url):
                    logger.info(f"URL disallowed by robots.txt: {candidate_url}")
                    diagnostics.sources_unavailable += 1
                    continue
            except Exception:
                pass

            # Safe HTTP fetch with timeout and error resilience
            try:
                fetched = fetch_source(candidate_url, timeout_seconds=10.0)
                if fetched.status_code in (403, 429):
                    diagnostics.sources_unavailable += 1
                    continue
                html = fetched.body
            except SourceFetchError:
                diagnostics.sources_unavailable += 1
                continue
            except Exception as exc:
                logger.warning(f"Fetch failed for '{candidate_url}': {exc}")
                diagnostics.sources_unavailable += 1
                continue

            # Extract opportunities from page
            extracted_items = self.extract_page_internships(
                candidate_url,
                html,
                target_field=field,
                target_country=country,
                target_year=year,
            )

            if not extracted_items:
                diagnostics.sources_rejected_non_job += 1
            else:
                raw_opportunities.extend(extracted_items)

        # 5. Deduplication
        deduped = self.deduplicate_opportunities(raw_opportunities)

        # 6. Ranking by relevance, confidence, and target criteria
        ranked = self.rank_opportunities(deduped, target_field=field, target_country=country, target_year=year)

        final_list = ranked[:max_results]
        diagnostics.valid_opportunities_found = len(final_list)
        diagnostics.execution_time_ms = round((time.perf_counter() - t0) * 1000, 2)

        return InternshipSearchResponse(
            opportunities=final_list,
            diagnostics=diagnostics,
            related_titles=related_titles,
        )

    def extract_page_internships(
        self,
        url: str,
        html: str,
        target_field: str,
        target_country: str | None = None,
        target_year: int | str | None = None,
    ) -> list[InternshipOpportunity]:
        """Classify page and extract structured internship information."""
        if not html or len(html.strip()) < 150:
            return []

        soup = BeautifulSoup(html, "html.parser")
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()

        # Step A: Check for structured JSON-LD JobPosting first
        json_ld_jobs = extract_json_ld_jobs(soup, url)
        if json_ld_jobs:
            inferred_company = ""
            for script in soup.select("script[type='application/ld+json']"):
                try:
                    data = json.loads(script.get_text().strip())
                    items = data if isinstance(data, list) else [data]
                    for it in items:
                        if isinstance(it, dict):
                            hiring_org = it.get("hiringOrganization")
                            if isinstance(hiring_org, dict) and hiring_org.get("name"):
                                inferred_company = str(hiring_org["name"]).strip()
                                break
                            elif isinstance(hiring_org, str) and hiring_org.strip():
                                inferred_company = hiring_org.strip()
                                break
                    if inferred_company:
                        break
                except Exception:
                    pass

            if not inferred_company:
                meta_site = soup.find("meta", property="og:site_name")
                if meta_site and meta_site.get("content"):
                    inferred_company = meta_site["content"].strip()

            results = []
            for jc in json_ld_jobs:
                opp = self._build_opportunity_from_candidate(
                    jc,
                    source_url=url,
                    domain=domain,
                    target_field=target_field,
                    target_country=target_country,
                    target_year=target_year,
                    has_json_ld=True,
                    inferred_company=inferred_company,
                )
                if opp and opp.confidence_score >= 50:
                    results.append(opp)
            if results:
                return results

        # Step B: Classify whether this HTML page is an internship opening vs generic portal
        page_text = soup.get_text(" ", strip=True)
        page_title = sanitize_plain_text(soup.title.string if soup.title else "")

        h1 = soup.find("h1")
        h1_text = sanitize_plain_text(h1.get_text(" ", strip=True)) if h1 else ""

        # Negative Signals Evaluation
        combined_header = f"{page_title} {h1_text}".lower()
        for neg_pat in NEGATIVE_PAGE_PATTERNS:
            if re.search(neg_pat, combined_header):
                # Informational page, blog, or portal landing page without specific job
                return []

        # Positive Internship Signal Check
        has_intern_signal = any(
            re.search(pat, combined_header, re.IGNORECASE) for pat in POSITIVE_INTERNSHIP_TITLE_PATTERNS
        ) or any(
            re.search(pat, url.lower(), re.IGNORECASE) for pat in POSITIVE_INTERNSHIP_TITLE_PATTERNS
        )
        if not has_intern_signal:
            # If neither title nor URL has internship keywords, check first 500 chars of body
            body_start = page_text[:800].lower()
            if not any(re.search(pat, body_start) for pat in POSITIVE_INTERNSHIP_TITLE_PATTERNS):
                return []

        # Step C: Extract structured fields
        extracted_title = h1_text or page_title
        # Strip noisy suffix (e.g. " - Careers at Google")
        clean_title = re.sub(r"\s*[-|–—]\s*(?:Careers|Jobs|Company|Recruitment).*$", "", extracted_title, flags=re.IGNORECASE).strip()
        if not clean_title or len(clean_title) < 3:
            clean_title = page_title[:60]

        # Extract Company
        company = ""
        meta_site = soup.find("meta", property="og:site_name")
        if meta_site and meta_site.get("content"):
            company = meta_site["content"].strip()
        if not company:
            # Try domain heuristics (e.g. careers.deloitte.com -> Deloitte)
            parts = domain.split(".")
            for part in parts:
                if part not in ("www", "careers", "jobs", "apply", "com", "org", "net", "io", "co", "ma", "de", "fr"):
                    company = part.capitalize()
                    break
        if not company:
            company = "Verified Employer"

        # Extract Location / Country
        location = "Unspecified"
        loc_el = soup.select_one("[class*='location'], [class*='city'], [class*='place'], [class*='lieu'], [itemprop='jobLocation']")
        if loc_el:
            loc_candidate = sanitize_plain_text(loc_el.get_text(" ", strip=True))
            if len(loc_candidate) < 50:
                location = loc_candidate
        elif target_country:
            location = target_country

        detected_country = target_country or ""
        if not detected_country:
            # Infer from location or domain
            if domain.endswith(".de"):
                detected_country = "Germany"
            elif domain.endswith(".fr"):
                detected_country = "France"
            elif domain.endswith(".ma"):
                detected_country = "Morocco"
            elif domain.endswith(".es"):
                detected_country = "Spain"
            elif domain.endswith(".it"):
                detected_country = "Italy"
            elif domain.endswith(".uk"):
                detected_country = "United Kingdom"

        # Extract Description & Requirements
        desc_el = soup.select_one("[class*='description'], [class*='details'], [class*='content'], article, main")
        description_text = desc_el.get_text("\n", strip=True) if desc_el else page_text
        # Truncate clean description for display
        short_desc = sanitize_plain_text(description_text[:500])

        requirements: list[str] = []
        for ul in soup.select("ul, ol"):
            prev = ul.find_previous(["h2", "h3", "h4", "p", "strong"])
            prev_text = prev.get_text(" ", strip=True).lower() if prev else ""
            if any(k in prev_text for k in ["requirement", "qualification", "responsibilit", "profil", "competence", "skills", "anforderung"]):
                for li in ul.find_all("li"):
                    txt = sanitize_plain_text(li.get_text(" ", strip=True))
                    if txt and len(txt) > 5 and len(txt) < 180:
                        requirements.append(txt)
                if requirements:
                    break

        # Application URL
        apply_el = soup.find("a", href=True, string=re.compile(r"apply|postuler|bewerben|solicitar|candidat", re.I))
        app_url = url
        if apply_el and apply_el.get("href"):
            from urllib.parse import urljoin
            cand_href = apply_el["href"].strip()
            if not cand_href.startswith(("#", "javascript:", "mailto:")):
                app_url = urljoin(url, cand_href)

        # Dates / Year signals
        is_year_match = False
        target_year_str = str(target_year).strip() if target_year else ""
        if target_year_str and target_year_str in f"{clean_title} {page_text[:1200]}":
            is_year_match = True

        # Compute Confidence Score
        score = 40  # Base score for passing negative checks and having internship title
        if any(re.search(pat, clean_title, re.I) for pat in POSITIVE_INTERNSHIP_TITLE_PATTERNS):
            score += 25
        if company and company != "Verified Employer":
            score += 10
        if requirements:
            score += 15
        if is_year_match:
            score += 10
        if location and location != "Unspecified":
            score += 10

        score = min(100, max(0, score))
        if score < 50:
            return []

        opp_id = f"int-{abs(hash((url, clean_title))) % 100000000}"
        return [
            InternshipOpportunity(
                id=opp_id,
                title=clean_title,
                company=company,
                location=location,
                country=detected_country,
                description=short_desc,
                requirements=requirements[:6],
                qualifications=requirements[:4],
                internship_type="Internship",
                source_url=url,
                application_url=app_url,
                source_domain=domain,
                language="en",
                confidence_score=score,
                is_year_match=is_year_match,
            )
        ]

    def _build_opportunity_from_candidate(
        self,
        jc: Any,
        source_url: str,
        domain: str,
        target_field: str,
        target_country: str | None,
        target_year: int | str | None,
        has_json_ld: bool = False,
        inferred_company: str = "",
    ) -> InternshipOpportunity | None:
        title = jc.title or ""
        clean_title = sanitize_plain_text(title)

        # Check negative signals
        for neg_pat in NEGATIVE_PAGE_PATTERNS:
            if re.search(neg_pat, clean_title, re.IGNORECASE):
                return None

        # Check positive internship signals
        is_intern = any(re.search(pat, clean_title, re.IGNORECASE) for pat in POSITIVE_INTERNSHIP_TITLE_PATTERNS)
        if not is_intern and (jc.employment_type and "intern" in jc.employment_type.lower()):
            is_intern = True

        if not is_intern:
            # If not explicitly internship in title or type, skip
            return None

        company = inferred_company or getattr(jc, "company_name", "") or "Verified Employer"
        location = jc.location or target_country or "Unspecified"

        target_year_str = str(target_year).strip() if target_year else ""
        is_year_match = bool(target_year_str and (target_year_str in clean_title or (jc.description and target_year_str in jc.description)))

        score = 65 if has_json_ld else 45
        if is_intern:
            score += 20
        if is_year_match:
            score += 10
        if company != "Verified Employer":
            score += 5
        score = min(100, score)

        opp_id = f"int-{abs(hash((source_url, clean_title))) % 100000000}"
        return InternshipOpportunity(
            id=opp_id,
            title=clean_title,
            company=company,
            location=location,
            country=target_country or "",
            description=sanitize_plain_text(jc.description[:400]) if jc.description else "",
            requirements=jc.skills[:6] if hasattr(jc, "skills") else [],
            internship_type=jc.employment_type or "Internship",
            source_url=source_url,
            application_url=jc.job_url or source_url,
            source_domain=domain,
            confidence_score=score,
            is_year_match=is_year_match,
        )

    def deduplicate_opportunities(self, opportunities: list[InternshipOpportunity]) -> list[InternshipOpportunity]:
        """Conservative deduplication using normalized URL and (company, title, location) hashing."""
        seen_keys: set[str] = set()
        deduped: list[InternshipOpportunity] = []

        for opp in opportunities:
            norm_url = normalize_url(opp.source_url)
            norm_app_url = normalize_url(opp.application_url)

            # Title & company key
            norm_title = strip_diacritics(opp.title.lower().strip())
            norm_company = strip_diacritics(opp.company.lower().strip())
            norm_title_clean = re.sub(r"\W+", "", norm_title)
            norm_comp_clean = re.sub(r"\W+", "", norm_company)

            url_key = f"url:{norm_url}"
            app_url_key = f"app:{norm_app_url}" if norm_app_url else ""
            content_key = f"item:{norm_comp_clean}:{norm_title_clean}"

            if url_key in seen_keys or (app_url_key and app_url_key in seen_keys) or (norm_comp_clean and content_key in seen_keys):
                continue

            seen_keys.add(url_key)
            if app_url_key:
                seen_keys.add(app_url_key)
            if norm_comp_clean:
                seen_keys.add(content_key)

            deduped.append(opp)

        return deduped

    def rank_opportunities(
        self,
        opportunities: list[InternshipOpportunity],
        target_field: str,
        target_country: str | None = None,
        target_year: int | str | None = None,
    ) -> list[InternshipOpportunity]:
        """Rank opportunities by relevance: field tokens, year match, country match, confidence."""
        norm_field_tokens = set(re.findall(r"\b[a-z0-9]{3,}\b", strip_diacritics(target_field.lower())))
        norm_country = strip_diacritics(target_country.lower().strip()) if target_country else ""
        year_str = str(target_year).strip() if target_year else ""

        def calculate_rank(opp: InternshipOpportunity) -> float:
            rank = float(opp.confidence_score)

            # Field keyword overlap in title
            title_tokens = set(re.findall(r"\b[a-z0-9]{3,}\b", strip_diacritics(opp.title.lower())))
            overlap = len(norm_field_tokens & title_tokens)
            rank += overlap * 15.0

            # Year match bonus
            if opp.is_year_match or (year_str and year_str in opp.title):
                rank += 25.0

            # Country match bonus
            if norm_country and (norm_country in opp.location.lower() or norm_country in opp.country.lower()):
                rank += 20.0

            return rank

        return sorted(opportunities, key=calculate_rank, reverse=True)
