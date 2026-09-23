"""Service for extracting structured job posting data from arbitrary generic HTML pages.

Combines:
1. Platform adapters (Workday, Greenhouse, Lever, SmartRecruiters, Ashby, Workable, Teamtailor).
2. Schema.org JSON-LD (`JobPosting`).
3. OpenGraph / Twitter / standard meta tags.
4. DOM semantic heading extraction with multilingual label heuristics (Phase 2).
5. Structured field-grid extraction (dt/dd pairs, label+value ATS layouts).
6. ~73,000-title corpus validation & normalization via JobTitleMatcher.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from ..logging import get_logger
from ..schemas import GenericExtractResponse
from ..scraper.http_client import FetchedSource
from ..scraper.job_title_intelligence.matcher import JobTitleMatcher
from ..scraper.job_title_intelligence.normalizer import strip_title_noise
from ..scraper.platforms.ashby import AshbyAdapter
from ..scraper.platforms.greenhouse import GreenhouseAdapter
from ..scraper.platforms.lever import LeverAdapter
from ..scraper.platforms.smartrecruiters import SmartRecruitersAdapter
from ..scraper.platforms.teamtailor import TeamtailorAdapter
from ..scraper.platforms.workable import WorkableAdapter
from ..scraper.platforms.workday import WorkdayAdapter
from ..scraper.sanitizer import sanitize_html, sanitize_plain_text
from ..scraper.vocabulary import normalize_employment_type, normalize_remote_type

logger = get_logger(__name__)

PLATFORM_ADAPTERS = [
    WorkdayAdapter(),
    GreenhouseAdapter(),
    LeverAdapter(),
    SmartRecruitersAdapter(),
    AshbyAdapter(),
    WorkableAdapter(),
    TeamtailorAdapter(),
]


def _clean_company_from_domain(url: str) -> str:
    try:
        domain = urlparse(url).netloc.lower()
        domain = re.sub(r"^(?:www\.|careers?\.|jobs?\.)+", "", domain)
        parts = domain.split(".")
        if parts:
            name = parts[0]
            if name not in ("workday", "greenhouse", "lever", "smartrecruiters", "ashbyhq", "workable", "teamtailor"):
                return name.capitalize()
    except Exception:
        pass
    return ""


def _extract_from_json_ld(soup: BeautifulSoup) -> dict[str, Any] | None:
    for tag in soup.find_all("script", type=re.compile(r"application/(?:ld\+)?json", re.IGNORECASE)):
        try:
            content = tag.string or tag.get_text()
            if not content:
                continue
            data = json.loads(content)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                # Support @graph
                graph = item.get("@graph")
                sub_items = graph if isinstance(graph, list) else [item]
                for sub in sub_items:
                    if not isinstance(sub, dict):
                        continue
                    item_type = sub.get("@type") or ""
                    if isinstance(item_type, list):
                        item_type = " ".join(item_type)
                    if "JobPosting" in item_type:
                        return sub
        except Exception:
            continue
    return None


def _format_json_ld_location(loc_data: Any) -> str | None:
    if not loc_data:
        return None
    if isinstance(loc_data, str):
        return loc_data.strip()
    if isinstance(loc_data, dict):
        address = loc_data.get("address")
        if isinstance(address, str):
            return address.strip()
        if isinstance(address, dict):
            parts = [
                address.get("addressLocality"),
                address.get("addressRegion"),
                address.get("addressCountry"),
            ]
            valid = [p for p in parts if p and isinstance(p, str)]
            if valid:
                return ", ".join(valid)
        name = loc_data.get("name")
        if name and isinstance(name, str):
            return name.strip()
    if isinstance(loc_data, list) and loc_data:
        return _format_json_ld_location(loc_data[0])
    return None


# ---------------------------------------------------------------------------
# Multilingual label dictionaries for heuristic section detection (Phase 2).
# All labels are stored pre-normalized (lowercase, accent-stripped approximations).
# ---------------------------------------------------------------------------

_DESCRIPTION_LABELS: frozenset[str] = frozenset({
    # English
    "job description", "position description", "about the role", "about this role",
    "about the position", "role description", "role overview", "job overview",
    "the role", "what you'll do", "what you will do", "responsibilities",
    "your responsibilities", "key responsibilities", "main responsibilities",
    "duties and responsibilities", "role & responsibilities", "role and responsibilities",
    # French
    "description du poste", "description de l'offre", "a propos du poste",
    "vos responsabilites", "responsabilites", "le poste", "missions principales",
    "missions", "votre role", "ce que vous ferez", "description de l'emploi",
    # German
    "stellenbeschreibung", "aufgaben", "ihre aufgaben", "deine aufgaben",
    "was sie erwartet", "was dich erwartet", "tatigkeiten", "jobbeschreibung",
    "aufgabenbereich", "das machst du",
    # Spanish
    "descripcion del puesto", "descripcion del trabajo", "descripcion",
    "responsabilidades", "tus responsabilidades", "sobre el puesto",
    "lo que haras", "que haras",
    # Portuguese
    "descricao da vaga", "descricao do cargo", "sobre a vaga", "o que voce vai fazer",
    # Italian
    "descrizione del ruolo", "responsabilita", "la posizione",
    # Dutch
    "functieomschrijving", "over de functie", "wat ga je doen",
})

_LOCATION_LABELS: frozenset[str] = frozenset({
    "location", "job location", "work location", "place of work", "office location",
    "lieu de travail", "localisation", "lieu",
    "standort", "arbeitsort", "ort",
    "ubicacion", "lugar de trabajo",
    "localizacao", "local de trabalho",
    "sede", "luogo di lavoro",
    "locatie", "werklocatie",
})

_EMPLOYMENT_TYPE_LABELS: frozenset[str] = frozenset({
    "employment type", "job type", "contract type", "type of employment",
    "type de contrat", "type d'emploi",
    "vertragsart", "anstellungsart", "beschaftigungsart",
    "tipo de contrato", "tipo de empleo",
    "tipo de vaga", "regime de trabalho",
    "tipo di contratto",
    "soort dienstverband",
})

_REMOTE_LABELS: frozenset[str] = frozenset({
    "work mode", "remote", "work arrangement", "workplace type",
    "teletravail", "mode de travail",
    "arbeitsmodell", "home office", "homeoffice",
    "modalidad de trabajo", "teletrabajo",
    "modelo de trabalho",
})

_COMPANY_LABELS: frozenset[str] = frozenset({
    "company", "employer", "organization", "organisation", "about the company",
    "entreprise", "societe", "employeur",
    "unternehmen", "arbeitgeber",
    "empresa", "empleador",
    "azienda",
    "bedrijf",
})

_RESPONSIBILITY_LABELS: frozenset[str] = frozenset({
    "responsibilities", "your responsibilities", "key responsibilities",
    "what you'll do", "what you will do", "main responsibilities",
    "responsabilites", "vos responsabilites", "missions",
    "aufgaben", "ihre aufgaben", "deine aufgaben",
    "responsabilidades", "tus responsabilidades",
})

_REQUIREMENT_LABELS: frozenset[str] = frozenset({
    "requirements", "qualifications", "what we're looking for", "what we are looking for",
    "what you bring", "what you need", "skills required",
    "minimum qualifications", "preferred qualifications",
    "exigences", "qualifications requises", "profil recherche",
    "anforderungen", "ihr profil", "dein profil", "voraussetzungen",
    "requisitos", "perfil buscado",
})


def _norm(text: str) -> str:
    """Normalize label text: lowercase, ASCII-fold accents, strip trailing colon, collapse whitespace."""
    text = (text or "").lower().strip()
    # Best-effort ASCII folding for common European diacritics
    text = re.sub(r"[àáâãäå]", "a", text)
    text = re.sub(r"[èéêë]", "e", text)
    text = re.sub(r"[ìíîï]", "i", text)
    text = re.sub(r"[òóôõö]", "o", text)
    text = re.sub(r"[ùúûü]", "u", text)
    text = re.sub(r"[ñ]", "n", text)
    text = re.sub(r"[ç]", "c", text)
    text = re.sub(r"\s+", " ", text)
    # Remove trailing colon, asterisk, or other punctuation common in ATS label fields
    text = re.sub(r"[:\*\u2022\u2013\u2014]+$", "", text).strip()
    return text


def _label_in(text: str, label_set: frozenset[str]) -> bool:
    return _norm(text) in label_set


def _extract_dt_dd_fields(soup: BeautifulSoup) -> dict[str, str]:
    """Extract structured field data from <dl>/<dt>/<dd> pairs common in ATS layouts
    (Workday, iCIMS, SAP SuccessFactors, Oracle Taleo, etc.)."""
    result: dict[str, str] = {}
    for dl in soup.find_all("dl"):
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        for dt, dd in zip(dts, dds):
            label = _norm(dt.get_text(" ", strip=True))
            value = sanitize_plain_text(dd.get_text(" ", strip=True))
            if label and value:
                result[label] = value
    return result


def _extract_label_value_pairs(soup: BeautifulSoup) -> dict[str, str]:
    """
    Extract label→value pairs from common ATS field-row layouts using sibling heuristics.
    Handles patterns like <span class="label">Location</span><span class="value">Paris</span>.
    """
    result: dict[str, str] = {}
    candidate_labels = _LOCATION_LABELS | _EMPLOYMENT_TYPE_LABELS | _REMOTE_LABELS | _COMPANY_LABELS

    for tag in soup.find_all(["span", "div", "p", "td", "th", "label"]):
        text = tag.get_text(" ", strip=True)
        if not text or len(text) > 80:
            continue
        if not _label_in(text, candidate_labels):
            continue

        # Try next sibling
        sib = tag.find_next_sibling()
        if sib:
            val = sanitize_plain_text(sib.get_text(" ", strip=True))
            if val and len(val) <= 200:
                result[_norm(text)] = val
                continue

        # Try parent's next sibling
        if tag.parent:
            parent_sib = tag.parent.find_next_sibling()
            if parent_sib:
                val = sanitize_plain_text(parent_sib.get_text(" ", strip=True))
                if val and len(val) <= 200:
                    result[_norm(text)] = val

    return result


def _extract_section_by_label(
    soup: BeautifulSoup,
    labels: frozenset[str],
    min_chars: int = 100,
    max_chars: int = 50_000,
) -> str | None:
    """
    Find a section whose heading/label text matches `labels`, then return
    the following body text.

    Strategy A: Heading elements (h1-h5, strong, dt, label) with matching text
                — then captures sibling content until the next heading.
    Strategy B: id/class/aria-label attributes matching label set.
    """
    heading_tags = ["h1", "h2", "h3", "h4", "h5", "strong", "b", "dt", "label"]

    def _text_after_heading(start_el) -> str:
        parts: list[str] = []
        for sib in start_el.find_next_siblings():
            if sib.name in ("h1", "h2", "h3", "h4", "h5", "hr"):
                break
            text = sanitize_plain_text(sib.get_text(" ", strip=True))
            if text:
                parts.append(text)
        return " ".join(parts).strip()

    # Strategy A: Heading elements
    for tag_name in heading_tags:
        for el in soup.find_all(tag_name):
            raw_text = el.get_text(" ", strip=True)
            if not _label_in(raw_text, labels):
                continue

            # Try parent container body (strip the heading itself)
            parent = el.parent
            if parent:
                inner = parent.get_text(" ", strip=True)
                heading_text = raw_text.strip()
                if inner.lower().startswith(heading_text.lower()):
                    body = sanitize_plain_text(inner[len(heading_text):].strip()) or ""
                    if min_chars <= len(body) <= max_chars:
                        return body

            # Try siblings after heading
            body = _text_after_heading(el)
            if min_chars <= len(body) <= max_chars:
                return body

    # Strategy B: id/class/aria-label attribute matching (ASCII labels only)
    ascii_labels = [lbl for lbl in labels if lbl.isascii()]
    if ascii_labels:
        pattern = re.compile(
            "|".join(
                r"[-_]?".join(re.escape(word) for word in lbl.split(" "))
                for lbl in ascii_labels
            ),
            re.IGNORECASE,
        )
        for el in soup.find_all(True):
            cls_raw = el.get("class") or []
            cls_str = " ".join(cls_raw) if isinstance(cls_raw, list) else (cls_raw or "")
            attrs_text = " ".join(filter(None, [
                el.get("id", ""),
                cls_str,
                el.get("aria-label", ""),
                el.get("data-label", ""),
                el.get("data-section", ""),
            ]))
            if pattern.search(attrs_text):
                body = sanitize_plain_text(el.get_text(" ", strip=True)) or ""
                if min_chars <= len(body) <= max_chars:
                    return body

    return None


def extract_job_from_html(html: str, url: str) -> GenericExtractResponse:
    soup = BeautifulSoup(html, "html.parser")
    matcher = JobTitleMatcher()

    title: str | None = None
    company: str | None = None
    location: str | None = None
    description: str | None = None
    employment_type: str | None = None
    remote_type: str | None = None
    confidence: str = "low"
    normalized_title: str | None = None
    message: str | None = None

    # Step 1: Check Platform Adapters
    from datetime import datetime, timezone
    source = FetchedSource(
        requested_url=url,
        final_url=url,
        status_code=200,
        content_type="text/html",
        body=html,
        fetched_at=datetime.now(timezone.utc),
    )

    for adapter in PLATFORM_ADAPTERS:
        try:
            if adapter.is_job_detail_page(source):
                candidate = adapter.parse_job_detail(source)
                if candidate and candidate.title:
                    title = candidate.title
                    company = candidate.company or ""
                    location = candidate.location
                    description = candidate.description
                    employment_type = candidate.employment_type
                    remote_type = candidate.remote_type
                    confidence = "high"
                    break
        except Exception as exc:
            logger.debug(f"Platform adapter {adapter.name} failed on {url}: {exc}")

    # Step 2: Check Schema.org JobPosting JSON-LD
    if not title:
        json_ld = _extract_from_json_ld(soup)
        if json_ld:
            title = sanitize_plain_text(json_ld.get("title") or "")
            org = json_ld.get("hiringOrganization")
            if isinstance(org, dict):
                company = sanitize_plain_text(org.get("name") or "")
            elif isinstance(org, str):
                company = sanitize_plain_text(org)

            location = _format_json_ld_location(json_ld.get("jobLocation"))
            desc_raw = json_ld.get("description")
            if desc_raw:
                description = sanitize_html(str(desc_raw))
            emp_raw = json_ld.get("employmentType")
            if emp_raw:
                employment_type = normalize_employment_type(str(emp_raw))
            loc_type = json_ld.get("jobLocationType")
            if loc_type and "TELECOMMUTE" in str(loc_type).upper():
                remote_type = "Remote"

            confidence = "high"

    # Step 3: Check OpenGraph / Twitter meta tags
    og_title = ""
    og_desc = ""
    og_site = ""

    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or meta.get("name") or "").lower()
        val = meta.get("content") or ""
        if not val:
            continue
        if prop in ("og:title", "twitter:title") and not og_title:
            og_title = val.strip()
        elif prop in ("og:description", "twitter:description", "description") and not og_desc:
            og_desc = val.strip()
        elif prop in ("og:site_name", "author") and not og_site:
            og_site = val.strip()

    if not company and og_site:
        company = og_site

    # Step 4: Structured field-grid extraction (dt/dd + label/value sibling pairs).
    # Handles Workday, iCIMS, SAP SuccessFactors, Oracle Taleo, and other ATS layouts.
    if not location or not employment_type:
        dt_dd = _extract_dt_dd_fields(soup)
        lv_pairs = _extract_label_value_pairs(soup)
        all_fields = {**dt_dd, **lv_pairs}

        for field_label, field_value in all_fields.items():
            if not location and _label_in(field_label, _LOCATION_LABELS):
                location = field_value
            if not employment_type and _label_in(field_label, _EMPLOYMENT_TYPE_LABELS):
                employment_type = normalize_employment_type(field_value)
            if not remote_type and _label_in(field_label, _REMOTE_LABELS):
                norm_val = field_value.lower()
                if "remote" in norm_val or "teletravail" in norm_val or "teletrabajo" in norm_val:
                    remote_type = "Remote"
                elif "hybrid" in norm_val or "hybride" in norm_val:
                    remote_type = "Hybrid"
                elif "on-site" in norm_val or "onsite" in norm_val or "presentiel" in norm_val:
                    remote_type = "On-site"
            if not company and _label_in(field_label, _COMPANY_LABELS):
                company = field_value

    # Step 5: DOM Heading Extraction if title still not found
    if not title:
        # Check h1 tags
        h1s = soup.find_all("h1")
        for h1 in h1s:
            text = sanitize_plain_text(h1.get_text(" ", strip=True))
            if text and 3 <= len(text) <= 120:
                title = text
                break

        # If still not found, check title tag
        if not title and soup.title:
            title = sanitize_plain_text(soup.title.get_text(strip=True))

        if not title and og_title:
            title = sanitize_plain_text(og_title)

    # Step 6: Multilingual description section label detection
    if not description:
        description = _extract_section_by_label(soup, _DESCRIPTION_LABELS, min_chars=100)

    # Step 7: Compose description from responsibilities + requirements sections
    if not description:
        resp = _extract_section_by_label(soup, _RESPONSIBILITY_LABELS, min_chars=50)
        req = _extract_section_by_label(soup, _REQUIREMENT_LABELS, min_chars=50)
        parts = [p for p in [resp, req] if p]
        if parts:
            description = "\n\n".join(parts)

    # Step 8: Fallback description extraction
    if not description:
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find(id=re.compile(r"job[-_]?desc|content|main", re.IGNORECASE))
            or soup.find(class_=re.compile(r"job[-_]?desc|posting|content", re.IGNORECASE))
        )
        if main_content:
            description = sanitize_html(str(main_content))
        elif og_desc:
            description = f"<p>{sanitize_plain_text(og_desc)}</p>"
        else:
            # Fallback to body text snippet
            body_text = sanitize_plain_text(soup.body.get_text(" ", strip=True) if soup.body else "")
            description = f"<p>{body_text[:1500]}</p>" if body_text else ""

    # Step 9: Fallback company from domain
    if not company:
        company = _clean_company_from_domain(url) or "Company"


    # Step 10: Title validation and normalization using 73k-title corpus
    if title:
        stripped_title = strip_title_noise(title)
        match = matcher.match_raw_title(stripped_title) or matcher.match_raw_title(title)
        if match:
            normalized_title = match.matched_title.title()
            # If we matched the 73k-title index with high specificity, upgrade confidence
            if match.specificity >= 0.70:
                confidence = "high"
            elif confidence == "low":
                confidence = "medium"
        else:
            # Title was not in 73k taxonomy
            if confidence == "high":
                confidence = "medium"
            else:
                confidence = "low"
                message = "Job title could not be confidently verified against Compust's taxonomy. Please check and edit before saving."
    else:
        confidence = "low"
        title = "Untitled Position"
        message = "No job title detected. Please enter the job title manually."

    return GenericExtractResponse(
        title=title,
        company=company or "Company",
        location=location,
        description=description,
        employment_type=employment_type,
        remote_type=remote_type,
        confidence=confidence,
        normalized_title=normalized_title,
        message=message,
    )
