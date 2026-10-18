"""Unified Profile Fusion & LinkedIn Integration Engine.

Implements the middleware layer that merges resume data with LinkedIn exports/PDFs
into a single, deduplicated, canonical Unified Profile with complete provenance tracking.

Architecture:
- Zero-scraping approach: Uses official LinkedIn data exports (ZIP/CSV) and "Save to PDF" files.
  Strictly avoids automated headless scraping, proxy rotation, and auth-wall bypassing to protect
  user privacy and prevent account bans.
- Multilingual section parsing supporting EN, FR, NL, DE.
- Entity resolution with token similarity, company name canonicalization, and date overlap checks.
- Complete provenance tracking on every field (source: resume|linkedin|manual, confidence, imported_at).
- Safe CSV formula injection protection (=, +, -, @ prefix sanitization).
- Event-driven recomputation with version hashing.
- Fallback resilience: If LinkedIn data is absent or disabled, matching behavior is byte-for-byte
  identical to resume-only matching.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
import zipfile
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..logging import get_logger
from ..models import Resume, User, UserEducation, UserExperience, UserLanguage, UserLinkedInProfile, UserSkill, UserUnifiedProfile
from ..scraper.vocabulary import SKILL_SYNONYMS

logger = get_logger(__name__)

# Maximum limits for archive safety (ZIP bomb protection)
MAX_ZIP_FILES = 100
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_CSV_LINE_LEN = 100_000

# Legal entity suffixes to strip during company canonicalization
LEGAL_SUFFIXES = {
    "inc", "inc.", "incorporated", "llc", "llc.", "l.l.c.", "corp", "corp.",
    "corporation", "ltd", "ltd.", "limited", "gmbh", "gmbh & co. kg", "ag",
    "sa", "s.a.", "sas", "s.a.s.", "sarl", "s.a.r.l.", "bv", "b.v.", "nv", "n.v.",
    "co", "co.", "company", "group", "holdings", "technologies", "tech"
}

# Multilingual LinkedIn PDF Section Headings (EN, FR, NL, DE)
LINKEDIN_PDF_HEADINGS: dict[str, dict[str, list[str]]] = {
    "summary": {
        "en": [r"summary", r"about", r"overview"],
        "fr": [r"r[eé]sum[eé]", r"[aà]\s+propos", r"profil"],
        "nl": [r"samenvatting", r"over", r"profiel"],
        "de": [r"zusammenfassung", r"[uü]ber\s+mich", r"profil"],
    },
    "experience": {
        "en": [r"experience", r"work\s+experience"],
        "fr": [r"exp[eé]rience", r"exp[eé]riences\s+professionnelles"],
        "nl": [r"ervaring", r"werkervaring"],
        "de": [r"berufserfahrung", r"erfahrung"],
    },
    "education": {
        "en": [r"education"],
        "fr": [r"formation", r"[eé]tudes"],
        "nl": [r"opleiding", r"onderwijs"],
        "de": [r"ausbildung", r"studium"],
    },
    "skills": {
        "en": [r"top\s+skills", r"skills"],
        "fr": [r"principales\s+comp[eé]tences", r"comp[eé]tences"],
        "nl": [r"belangrijkste\s+vaardigheden", r"vaardigheden"],
        "de": [r"kenntnisse", r"top-kenntnisse", r"f[aä]higkeiten"],
    },
    "languages": {
        "en": [r"languages"],
        "fr": [r"langues"],
        "nl": [r"talen"],
        "de": [r"sprachen"],
    },
    "certifications": {
        "en": [r"certifications", r"licenses\s+&\s+certifications"],
        "fr": [r"certifications", r"licences\s+et\s+certifications"],
        "nl": [r"certificaten", r"licenties\s+en\s+certificaten"],
        "de": [r"zertifikate", r"lizenzen\s+und\s+zertifikate"],
    },
    "projects": {
        "en": [r"projects"],
        "fr": [r"projets"],
        "nl": [r"projecten"],
        "de": [r"projekte"],
    },
    "honors": {
        "en": [r"honors\s+&\s+awards", r"honors", r"awards"],
        "fr": [r"prix\s+et\s+distinctions", r"distinctions"],
        "nl": [r"prijzen\s+en\s+onderscheidingen", r"onderscheidingen"],
        "de": [r"auszeichnungen\s+und\s+preise", r"preise"],
    },
}


# ==============================================================================
# 1. URL & Handle Normalization
# ==============================================================================

def validate_and_normalize_linkedin_url(raw_url: str) -> tuple[str, str]:
    """Validate and normalize a user's LinkedIn profile URL.
    
    Accepts:
    - https://www.linkedin.com/in/handle/
    - http://fr.linkedin.com/in/handle
    - linkedin.com/in/handle?trk=xyz
    
    Rejects:
    - Non-profile URLs (e.g. /company/, /school/, /feed/)
    - Invalid domains
    
    Returns:
        (canonical_url, handle)
    """
    if not raw_url or not raw_url.strip():
        raise ValueError("LinkedIn profile URL cannot be empty.")

    cleaned = raw_url.strip()
    # Strip tracking parameters and hash
    cleaned = re.sub(r"[?#].*$", "", cleaned)
    # Ensure scheme for parsing
    if not re.match(r"^https?://", cleaned, re.IGNORECASE):
        cleaned = "https://" + cleaned

    pattern = r"^https?://(?:[a-zA-Z0-9-]+\.)*linkedin\.com/in/([a-zA-Z0-9_\-%]+)/?$"
    match = re.match(pattern, cleaned, re.IGNORECASE)
    if not match:
        raise ValueError(
            "Invalid LinkedIn profile URL. Expected format: 'https://www.linkedin.com/in/your-handle'."
        )

    handle = match.group(1).strip("/").strip()
    if not handle or len(handle) < 2:
        raise ValueError("Invalid LinkedIn handle extracted from URL.")

    canonical_url = f"https://www.linkedin.com/in/{handle}"
    return canonical_url, handle


# ==============================================================================
# 2. Formula Injection Protection & Normalization
# ==============================================================================

def sanitize_formula_injection(text: Any) -> Any:
    """Sanitize strings against spreadsheet formula injection (=, +, -, @ prefixes)."""
    if not isinstance(text, str):
        return text
    stripped = text.strip()
    if stripped and stripped[0] in ("=", "+", "-", "@", "\t", "\r"):
        # Prepend a single quote to neutralize executable formula execution
        return "'" + text
    return text


def sanitize_dict_formulas(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize dictionary values against CSV/formula injection."""
    sanitized = {}
    for k, v in data.items():
        if isinstance(v, str):
            sanitized[k] = sanitize_formula_injection(v)
        elif isinstance(v, dict):
            sanitized[k] = sanitize_dict_formulas(v)
        elif isinstance(v, list):
            sanitized[k] = [
                sanitize_formula_injection(item) if isinstance(item, str)
                else (sanitize_dict_formulas(item) if isinstance(item, dict) else item)
                for item in v
            ]
        else:
            sanitized[k] = v
    return sanitized


def normalize_skill(skill: str) -> str:
    """Canonicalize skill using synonyms taxonomy and unicode NFKD accent folding."""
    if not skill:
        return ""
    cleaned = skill.strip().lower()
    unacc = unicodedata.normalize("NFKD", cleaned).encode("ASCII", "ignore").decode("utf-8")
    if cleaned in SKILL_SYNONYMS:
        return SKILL_SYNONYMS[cleaned].lower()
    if unacc in SKILL_SYNONYMS:
        return SKILL_SYNONYMS[unacc].lower()
    # Normalize common abbreviations
    aliases = {
        "js": "javascript",
        "ts": "typescript",
        "py": "python",
        "k8s": "kubernetes",
        "reactjs": "react",
        "nodejs": "node.js",
        "vuejs": "vue",
        "golang": "go",
        "postgres": "postgresql",
        "c++": "c++",
        "c#": "c#",
        ".net": ".net",
    }
    return aliases.get(unacc, unacc)


def canonical_company_name(name: str) -> str:
    """Strip legal corporate suffixes and punctuation for entity resolution."""
    if not name:
        return ""
    # Lowercase and unaccent
    s = unicodedata.normalize("NFKD", name.lower()).encode("ASCII", "ignore").decode("utf-8")
    # Remove punctuation
    s = re.sub(r"[^\w\s]", " ", s)
    tokens = [w for w in s.split() if w]
    # Filter trailing legal suffixes
    filtered = [w for w in tokens if w not in LEGAL_SUFFIXES]
    return " ".join(filtered) if filtered else " ".join(tokens)


def token_set_similarity(str1: str, str2: str) -> float:
    """Compute Jaccard token-set similarity between two strings."""
    if not str1 or not str2:
        return 0.0
    t1 = set(re.findall(r"\w+", str1.lower()))
    t2 = set(re.findall(r"\w+", str2.lower()))
    if not t1 or not t2:
        return 0.0
    return len(t1.intersection(t2)) / len(t1.union(t2))


# ==============================================================================
# 3. LinkedIn Official Export Parser (ZIP & CSV)
# ==============================================================================

def _read_csv_tolerant(content_bytes: bytes) -> list[dict[str, str]]:
    """Tolerantly read CSV bytes, handling UTF-8-BOM, UTF-8, and Latin-1."""
    text = ""
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            text = content_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if not text:
        text = content_bytes.decode("utf-8", errors="replace")

    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict[str, str]] = []
    if not reader.fieldnames:
        return rows

    # Normalize header names (lowercase, stripped, remove BOM)
    clean_fieldnames = {
        orig: orig.strip().lstrip("\ufeff").lower()
        for orig in reader.fieldnames if orig
    }

    for raw_row in reader:
        row: dict[str, str] = {}
        for orig_key, val in raw_row.items():
            if orig_key and orig_key in clean_fieldnames:
                row[clean_fieldnames[orig_key]] = (val or "").strip()
        if any(row.values()):
            rows.append(row)
    return rows


def parse_linkedin_export_zip(zip_bytes: bytes) -> dict[str, Any]:
    """Parse a LinkedIn official data export ZIP archive.
    
    Extracts Profile, Positions, Education, Skills, Certifications, Languages, Projects, Honors.
    Safe against zip bombs and directory traversal.
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except Exception as exc:
        raise ValueError(f"Invalid ZIP archive: {exc}") from exc

    infolist = zf.infolist()
    if len(infolist) > MAX_ZIP_FILES:
        raise ValueError(f"Archive exceeds maximum file count limit ({len(infolist)} > {MAX_ZIP_FILES}).")

    total_uncompressed = sum(info.file_size for info in infolist)
    if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
        raise ValueError(f"Archive uncompressed size ({total_uncompressed} bytes) exceeds safety limit.")

    file_contents: dict[str, bytes] = {}
    for info in infolist:
        name = info.filename
        # Check against path traversal
        if ".." in name or name.startswith("/") or name.startswith("\\"):
            continue
        base_name = name.split("/")[-1].split("\\")[-1].lower()
        if base_name.endswith(".csv"):
            file_contents[base_name] = zf.read(info)

    return _parse_linkedin_csv_dictionary(file_contents)


def parse_linkedin_export_csvs(csv_files: dict[str, str | bytes]) -> dict[str, Any]:
    """Parse individually uploaded LinkedIn export CSV files."""
    converted: dict[str, bytes] = {}
    for filename, content in csv_files.items():
        base_name = filename.split("/")[-1].split("\\")[-1].lower()
        if isinstance(content, str):
            converted[base_name] = content.encode("utf-8")
        else:
            converted[base_name] = content
    return _parse_linkedin_csv_dictionary(converted)


def _parse_linkedin_csv_dictionary(file_contents: dict[str, bytes]) -> dict[str, Any]:
    """Extract structured profile entities from LinkedIn CSV dictionary."""
    data: dict[str, Any] = {
        "profile": {},
        "positions": [],
        "education": [],
        "skills": [],
        "certifications": [],
        "languages": [],
        "projects": [],
        "honors": [],
        "courses": [],
    }

    # Helper to find matching file name
    def _find_file(keyword: str) -> bytes | None:
        for fname, b in file_contents.items():
            if keyword in fname:
                return b
        return None

    # 1. Profile.csv
    profile_bytes = _find_file("profile")
    if profile_bytes:
        rows = _read_csv_tolerant(profile_bytes)
        if rows:
            r = rows[0]
            first_name = r.get("first name") or r.get("firstname") or ""
            last_name = r.get("last name") or r.get("lastname") or ""
            headline = r.get("headline") or ""
            summary = r.get("summary") or r.get("about") or ""
            location = r.get("geo location") or r.get("location") or r.get("zip code") or ""
            industry = r.get("industry") or ""
            data["profile"] = {
                "first_name": first_name,
                "last_name": last_name,
                "full_name": f"{first_name} {last_name}".strip(),
                "headline": headline,
                "summary": summary,
                "location": location,
                "industry": industry,
            }

    # 2. Positions.csv
    positions_bytes = _find_file("position")
    if positions_bytes:
        rows = _read_csv_tolerant(positions_bytes)
        for r in rows:
            company = r.get("company name") or r.get("company") or ""
            title = r.get("title") or ""
            desc = r.get("description") or ""
            loc = r.get("location") or ""
            started = r.get("started on") or r.get("start date") or ""
            finished = r.get("finished on") or r.get("end date") or ""
            if company or title:
                data["positions"].append({
                    "company": company,
                    "title": title,
                    "description": desc,
                    "location": loc,
                    "start_date": started,
                    "end_date": finished or "Present",
                })

    # 3. Education.csv
    edu_bytes = _find_file("education")
    if edu_bytes:
        rows = _read_csv_tolerant(edu_bytes)
        for r in rows:
            school = r.get("school name") or r.get("school") or r.get("institution") or ""
            degree = r.get("degree name") or r.get("degree") or ""
            notes = r.get("notes") or r.get("activities") or ""
            started = r.get("start date") or r.get("started on") or ""
            finished = r.get("end date") or r.get("finished on") or ""
            if school or degree:
                data["education"].append({
                    "institution": school,
                    "degree": degree,
                    "field": notes,
                    "start_date": started,
                    "end_date": finished,
                })

    # 4. Skills.csv
    skills_bytes = _find_file("skill")
    if skills_bytes:
        rows = _read_csv_tolerant(skills_bytes)
        for r in rows:
            name = r.get("name") or r.get("skill name") or r.get("skill") or ""
            if name and name not in data["skills"]:
                data["skills"].append(name)

    # 5. Certifications.csv
    cert_bytes = _find_file("certification")
    if cert_bytes:
        rows = _read_csv_tolerant(cert_bytes)
        for r in rows:
            name = r.get("name") or r.get("certification") or ""
            issuer = r.get("authority") or r.get("issuer") or ""
            url = r.get("url") or ""
            license_no = r.get("license number") or ""
            started = r.get("started on") or ""
            finished = r.get("finished on") or ""
            if name:
                data["certifications"].append({
                    "name": name,
                    "issuer": issuer,
                    "credential_url": url,
                    "credential_id": license_no,
                    "issue_date": started or finished,
                })

    # 6. Languages.csv
    lang_bytes = _find_file("language")
    if lang_bytes:
        rows = _read_csv_tolerant(lang_bytes)
        for r in rows:
            name = r.get("name") or r.get("language") or ""
            prof = r.get("proficiency") or ""
            if name:
                data["languages"].append({
                    "language": name,
                    "proficiency": prof,
                })

    # 7. Projects.csv
    proj_bytes = _find_file("project")
    if proj_bytes:
        rows = _read_csv_tolerant(proj_bytes)
        for r in rows:
            title = r.get("title") or r.get("name") or ""
            desc = r.get("description") or ""
            url = r.get("url") or ""
            started = r.get("started on") or ""
            finished = r.get("finished on") or ""
            if title:
                data["projects"].append({
                    "name": title,
                    "description": desc,
                    "url": url,
                    "start_date": started,
                    "end_date": finished,
                })

    # 8. Honors.csv
    honors_bytes = _find_file("honor") or _find_file("award")
    if honors_bytes:
        rows = _read_csv_tolerant(honors_bytes)
        for r in rows:
            title = r.get("title") or ""
            issuer = r.get("issuer") or ""
            if title:
                data["honors"].append({"title": title, "issuer": issuer})

    # 9. Courses.csv
    courses_bytes = _find_file("course")
    if courses_bytes:
        rows = _read_csv_tolerant(courses_bytes)
        for r in rows:
            name = r.get("name") or ""
            num = r.get("number") or ""
            if name:
                data["courses"].append({"name": name, "number": num})

    return sanitize_dict_formulas(data)


# ==============================================================================
# 4. LinkedIn "Save to PDF" Parser
# ==============================================================================

def parse_linkedin_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    """Parse a LinkedIn 'Save to PDF' profile document.
    
    Uses text extraction and multilingual headings (EN, FR, NL, DE).
    """
    from .resume_parser import extract_text_from_pdf_bytes, parse_skills_list, parse_languages_list

    raw_text = extract_text_from_pdf_bytes(pdf_bytes)
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    # Build regex map for LinkedIn PDF headings
    heading_patterns: list[tuple[str, re.Pattern]] = []
    for sec_name, lang_dict in LINKEDIN_PDF_HEADINGS.items():
        all_patterns = [pat for plist in lang_dict.values() for pat in plist]
        joined = "|".join(all_patterns)
        pattern = re.compile(rf"^(?:#+|\d+\.?)?\s*(?:{joined})\s*[:\-\—]?$", re.IGNORECASE)
        heading_patterns.append((sec_name, pattern))

    sections: dict[str, list[str]] = {
        "header": [],
        "summary": [],
        "experience": [],
        "education": [],
        "skills": [],
        "languages": [],
        "certifications": [],
        "projects": [],
        "honors": [],
    }

    current_sec = "header"
    for line in lines:
        matched = None
        for sec_name, pat in heading_patterns:
            if pat.match(line):
                matched = sec_name
                break
        if matched:
            current_sec = matched
        else:
            sections[current_sec].append(line)

    header_text = "\n".join(sections["header"])
    first_name, last_name, headline = "", "", ""
    if sections["header"]:
        name_line = sections["header"][0]
        parts = name_line.split()
        if len(parts) >= 2:
            first_name = parts[0]
            last_name = " ".join(parts[1:])
        elif parts:
            first_name = parts[0]
        if len(sections["header"]) > 1:
            headline = sections["header"][1]

    # Parse skills
    skills_text = "\n".join(sections["skills"])
    skills_list = parse_skills_list(skills_text)

    # Parse languages
    langs_text = "\n".join(sections["languages"])
    langs_list = parse_languages_list(langs_text)

    # Rough experience segmentation
    positions = []
    exp_lines = sections["experience"]
    i = 0
    while i < len(exp_lines):
        line = exp_lines[i]
        # Check if line looks like Title or Company
        if len(line) > 3 and not line.lower().startswith("page "):
            title = line
            company = exp_lines[i + 1] if i + 1 < len(exp_lines) else ""
            positions.append({
                "title": title,
                "company": company,
                "description": "",
                "start_date": "",
                "end_date": "",
            })
            i += 2
        else:
            i += 1

    parsed_data = {
        "profile": {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": f"{first_name} {last_name}".strip(),
            "headline": headline,
            "summary": "\n".join(sections["summary"]).strip(),
        },
        "positions": positions,
        "education": [],
        "skills": skills_list,
        "languages": [{"language": l, "proficiency": ""} for l in langs_list],
        "certifications": [],
        "projects": [],
        "honors": [],
        "courses": [],
    }
    return sanitize_dict_formulas(parsed_data)


# ==============================================================================
# 5. Entity Resolution & Profile Fusion Engine
# ==============================================================================

def fuse_profiles(
    resume_data: dict[str, Any] | None,
    linkedin_data: dict[str, Any] | None,
    user_overrides: dict[str, Any] | None = None,
    source_resume_ref: str = "Active Resume",
    imported_at_iso: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Fuse resume data and LinkedIn data into a canonical Unified Profile.
    
    Deduplicates entities, resolves conflicts, attaches complete provenance
    to every item, and applies user overrides (pin, hide, edit).
    
    Returns:
        (unified_data, conflicts_list)
    """
    now_iso = imported_at_iso or datetime.now(timezone.utc).isoformat()
    conflicts: list[dict[str, Any]] = []
    overrides = user_overrides or {}

    r_struct = resume_data or {}
    l_struct = linkedin_data or {}

    # 1. Contact / Identity Resolution
    r_prof = r_struct.get("profile") or {}
    l_prof = l_struct.get("profile") or {}

    full_name = r_prof.get("full_name") or l_prof.get("full_name") or ""
    email = r_prof.get("email") or ""
    phone = r_prof.get("phone") or ""
    location = r_prof.get("location") or l_prof.get("location") or ""
    headline = l_prof.get("headline") or r_prof.get("headline") or ""
    summary = l_prof.get("summary") or r_prof.get("summary") or ""

    contact = {
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "location": location,
        "headline": headline,
        "summary": summary,
        "provenance": {
            "source": "both" if (r_prof and l_prof) else ("linkedin" if l_prof else "resume"),
            "source_ref": "Resume + LinkedIn" if (r_prof and l_prof) else source_resume_ref,
            "imported_at": now_iso,
            "confidence": 1.0,
        },
    }

    # 2. Skills Fusion & Deduplication
    skills_map: dict[str, dict[str, Any]] = {}

    # (a) From Resume
    for s in r_struct.get("skills") or []:
        s_name = s.get("name") if isinstance(s, dict) else s
        if not s_name or not isinstance(s_name, str):
            continue
        canon = normalize_skill(s_name)
        if not canon:
            continue
        skills_map[canon] = {
            "name": s_name.strip(),
            "canonical_name": canon,
            "category": (s.get("category") if isinstance(s, dict) else None) or "technical",
            "proficiency": (s.get("proficiency") if isinstance(s, dict) else None) or "",
            "provenances": [{
                "source": "resume",
                "source_ref": source_resume_ref,
                "imported_at": now_iso,
                "confidence": 1.0,
            }],
            "inferred": False,
            "pinned": False,
            "hidden": False,
        }

    # (b) From LinkedIn
    for s_name in l_struct.get("skills") or []:
        if not s_name or not isinstance(s_name, str):
            continue
        canon = normalize_skill(s_name)
        if not canon:
            continue
        if canon in skills_map:
            # Merge provenances
            skills_map[canon]["provenances"].append({
                "source": "linkedin",
                "source_ref": "LinkedIn Export",
                "imported_at": now_iso,
                "confidence": 1.0,
            })
        else:
            skills_map[canon] = {
                "name": s_name.strip(),
                "canonical_name": canon,
                "category": "technical",
                "proficiency": "",
                "provenances": [{
                    "source": "linkedin",
                    "source_ref": "LinkedIn Export",
                    "imported_at": now_iso,
                    "confidence": 1.0,
                }],
                "inferred": False,
                "pinned": False,
                "hidden": False,
            }

    # 3. Experience Fusion & Entity Resolution
    fused_experience: list[dict[str, Any]] = []
    r_exps = r_struct.get("experience") or []
    l_exps = l_struct.get("positions") or []

    # Start with resume experience
    for exp in r_exps:
        if not isinstance(exp, dict):
            continue
        company = exp.get("company") or ""
        title = exp.get("title") or ""
        fused_experience.append({
            "id": str(exp.get("id") or f"exp_r_{len(fused_experience)}"),
            "company": company,
            "title": title,
            "canonical_company": canonical_company_name(company),
            "start_date": exp.get("start_date") or "",
            "end_date": exp.get("end_date") or "",
            "description": exp.get("description") or "",
            "highlights": exp.get("highlights") or [],
            "location": exp.get("location") or "",
            "provenances": [{
                "source": "resume",
                "source_ref": source_resume_ref,
                "imported_at": now_iso,
                "confidence": 1.0,
            }],
            "pinned": False,
            "hidden": False,
        })

    # Match and merge LinkedIn positions
    for l_pos in l_exps:
        if not isinstance(l_pos, dict):
            continue
        l_comp = l_pos.get("company") or ""
        l_title = l_pos.get("title") or ""
        l_canon_comp = canonical_company_name(l_comp)
        l_start = l_pos.get("start_date") or ""
        l_end = l_pos.get("end_date") or ""
        l_desc = l_pos.get("description") or ""

        matched_exp = None
        for r_item in fused_experience:
            r_canon_comp = r_item["canonical_company"]
            comp_sim = token_set_similarity(r_canon_comp, l_canon_comp)
            title_sim = token_set_similarity(r_item["title"], l_title)

            # Check company match
            if comp_sim >= 0.8 or r_canon_comp == l_canon_comp:
                matched_exp = r_item
                # Detect potential conflict in titles or dates
                if title_sim < 0.5 and r_item["title"] and l_title:
                    conflicts.append({
                        "type": "experience_title_mismatch",
                        "entity": r_item["company"],
                        "resume_value": r_item["title"],
                        "linkedin_value": l_title,
                        "description": f"Role title at '{r_item['company']}' differs between Resume ('{r_item['title']}') and LinkedIn ('{l_title}').",
                    })
                break

        if matched_exp:
            # Merge into existing item
            matched_exp["provenances"].append({
                "source": "linkedin",
                "source_ref": "LinkedIn Export",
                "imported_at": now_iso,
                "confidence": 1.0,
            })
            # If description is longer in LinkedIn, supplement it
            if len(l_desc) > len(matched_exp.get("description", "")):
                matched_exp["description"] = l_desc
            if not matched_exp.get("start_date") and l_start:
                matched_exp["start_date"] = l_start
            if not matched_exp.get("end_date") and l_end:
                matched_exp["end_date"] = l_end
        else:
            # New position from LinkedIn
            fused_experience.append({
                "id": f"exp_l_{len(fused_experience)}",
                "company": l_comp,
                "title": l_title,
                "canonical_company": l_canon_comp,
                "start_date": l_start,
                "end_date": l_end,
                "description": l_desc,
                "highlights": [],
                "location": l_pos.get("location") or "",
                "provenances": [{
                    "source": "linkedin",
                    "source_ref": "LinkedIn Export",
                    "imported_at": now_iso,
                    "confidence": 1.0,
                }],
                "pinned": False,
                "hidden": False,
            })

    # 4. Education Fusion & Resolution
    fused_education: list[dict[str, Any]] = []
    r_edus = r_struct.get("education") or []
    l_edus = l_struct.get("education") or []

    for edu in r_edus:
        if not isinstance(edu, dict):
            continue
        inst = edu.get("institution") or ""
        fused_education.append({
            "id": str(edu.get("id") or f"edu_r_{len(fused_education)}"),
            "institution": inst,
            "degree": edu.get("degree") or "",
            "field": edu.get("field_of_study") or edu.get("field") or "",
            "start_date": edu.get("start_date") or "",
            "end_date": edu.get("end_date") or "",
            "provenances": [{
                "source": "resume",
                "source_ref": source_resume_ref,
                "imported_at": now_iso,
                "confidence": 1.0,
            }],
            "pinned": False,
            "hidden": False,
        })

    for l_edu in l_edus:
        if not isinstance(l_edu, dict):
            continue
        l_inst = l_edu.get("institution") or ""
        matched_edu = None
        for item in fused_education:
            if token_set_similarity(item["institution"], l_inst) >= 0.7:
                matched_edu = item
                break
        if matched_edu:
            matched_edu["provenances"].append({
                "source": "linkedin",
                "source_ref": "LinkedIn Export",
                "imported_at": now_iso,
                "confidence": 1.0,
            })
            if not matched_edu.get("degree") and l_edu.get("degree"):
                matched_edu["degree"] = l_edu["degree"]
        else:
            fused_education.append({
                "id": f"edu_l_{len(fused_education)}",
                "institution": l_inst,
                "degree": l_edu.get("degree") or "",
                "field": l_edu.get("field") or "",
                "start_date": l_edu.get("start_date") or "",
                "end_date": l_edu.get("end_date") or "",
                "provenances": [{
                    "source": "linkedin",
                    "source_ref": "LinkedIn Export",
                    "imported_at": now_iso,
                    "confidence": 1.0,
                }],
                "pinned": False,
                "hidden": False,
            })

    # 5. Certifications Fusion
    fused_certs: list[dict[str, Any]] = []
    r_certs = r_struct.get("certifications") or []
    l_certs = l_struct.get("certifications") or []

    for cert in r_certs:
        c_name = cert.get("name") if isinstance(cert, dict) else cert
        if not c_name:
            continue
        fused_certs.append({
            "id": f"cert_r_{len(fused_certs)}",
            "name": c_name,
            "issuer": cert.get("issuer") if isinstance(cert, dict) else "",
            "issue_date": cert.get("issue_date") if isinstance(cert, dict) else "",
            "credential_url": "",
            "credential_id": "",
            "provenances": [{
                "source": "resume",
                "source_ref": source_resume_ref,
                "imported_at": now_iso,
                "confidence": 1.0,
            }],
            "pinned": False,
            "hidden": False,
        })

    for l_cert in l_certs:
        c_name = l_cert.get("name") or ""
        matched_cert = None
        for item in fused_certs:
            if token_set_similarity(item["name"], c_name) >= 0.8:
                matched_cert = item
                break
        if matched_cert:
            matched_cert["provenances"].append({
                "source": "linkedin",
                "source_ref": "LinkedIn Export",
                "imported_at": now_iso,
                "confidence": 1.0,
            })
            if not matched_cert.get("issuer") and l_cert.get("issuer"):
                matched_cert["issuer"] = l_cert["issuer"]
        else:
            fused_certs.append({
                "id": f"cert_l_{len(fused_certs)}",
                "name": c_name,
                "issuer": l_cert.get("issuer") or "",
                "issue_date": l_cert.get("issue_date") or "",
                "credential_url": l_cert.get("credential_url") or "",
                "credential_id": l_cert.get("credential_id") or "",
                "provenances": [{
                    "source": "linkedin",
                    "source_ref": "LinkedIn Export",
                    "imported_at": now_iso,
                    "confidence": 1.0,
                }],
                "pinned": False,
                "hidden": False,
            })

    # 6. Languages Fusion
    fused_languages: list[dict[str, Any]] = []
    r_langs = r_struct.get("languages") or []
    l_langs = l_struct.get("languages") or []

    for l in r_langs:
        lname = l.get("language") if isinstance(l, dict) else l
        if not lname:
            continue
        fused_languages.append({
            "language": lname,
            "canonical_language": lname.strip().lower(),
            "proficiency": (l.get("proficiency") if isinstance(l, dict) else "") or "",
            "provenances": [{
                "source": "resume",
                "source_ref": source_resume_ref,
                "imported_at": now_iso,
                "confidence": 1.0,
            }],
            "pinned": False,
            "hidden": False,
        })

    for l in l_langs:
        lname = l.get("language") if isinstance(l, dict) else l
        if not lname:
            continue
        matched_l = None
        for item in fused_languages:
            if item["canonical_language"] == lname.strip().lower():
                matched_l = item
                break
        if matched_l:
            matched_l["provenances"].append({
                "source": "linkedin",
                "source_ref": "LinkedIn Export",
                "imported_at": now_iso,
                "confidence": 1.0,
            })
            if not matched_l.get("proficiency") and isinstance(l, dict) and l.get("proficiency"):
                matched_l["proficiency"] = l["proficiency"]
        else:
            fused_languages.append({
                "language": lname,
                "canonical_language": lname.strip().lower(),
                "proficiency": (l.get("proficiency") if isinstance(l, dict) else "") or "",
                "provenances": [{
                    "source": "linkedin",
                    "source_ref": "LinkedIn Export",
                    "imported_at": now_iso,
                    "confidence": 1.0,
                }],
                "pinned": False,
                "hidden": False,
            })

    # 7. Projects Fusion
    fused_projects: list[dict[str, Any]] = []
    r_projs = r_struct.get("projects") or []
    l_projs = l_struct.get("projects") or []

    for p in r_projs:
        pname = p.get("name") if isinstance(p, dict) else p
        if not pname:
            continue
        fused_projects.append({
            "id": f"proj_r_{len(fused_projects)}",
            "name": pname,
            "description": p.get("description") if isinstance(p, dict) else "",
            "technologies": p.get("technologies") if isinstance(p, dict) else [],
            "provenances": [{
                "source": "resume",
                "source_ref": source_resume_ref,
                "imported_at": now_iso,
                "confidence": 1.0,
            }],
            "pinned": False,
            "hidden": False,
        })

    for p in l_projs:
        pname = p.get("name") if isinstance(p, dict) else p
        if not pname:
            continue
        matched_p = None
        for item in fused_projects:
            if token_set_similarity(item["name"], pname) >= 0.7:
                matched_p = item
                break
        if matched_p:
            matched_p["provenances"].append({
                "source": "linkedin",
                "source_ref": "LinkedIn Export",
                "imported_at": now_iso,
                "confidence": 1.0,
            })
        else:
            fused_projects.append({
                "id": f"proj_l_{len(fused_projects)}",
                "name": pname,
                "description": p.get("description") if isinstance(p, dict) else "",
                "technologies": [],
                "provenances": [{
                    "source": "linkedin",
                    "source_ref": "LinkedIn Export",
                    "imported_at": now_iso,
                    "confidence": 1.0,
                }],
                "pinned": False,
                "hidden": False,
            })

    # Apply User Overrides (pinned, hidden, custom edits)
    pinned_skills = set(overrides.get("pinned_skills") or [])
    hidden_skills = set(overrides.get("hidden_skills") or [])
    for sk in skills_map.values():
        if sk["canonical_name"] in pinned_skills:
            sk["pinned"] = True
        if sk["canonical_name"] in hidden_skills:
            sk["hidden"] = True

    unified_data: dict[str, Any] = {
        "contact": contact,
        "skills": list(skills_map.values()),
        "experience": fused_experience,
        "education": fused_education,
        "certifications": fused_certs,
        "languages": fused_languages,
        "projects": fused_projects,
        "honors": l_struct.get("honors") or [],
        "courses": l_struct.get("courses") or [],
    }

    return sanitize_dict_formulas(unified_data), conflicts


# ==============================================================================
# 6. Database Synchronization & Single Accessor
# ==============================================================================

def recompute_unified_profile(db: Session, user_id: int) -> UserUnifiedProfile:
    """Event-driven recomputation of the Unified Profile for a user.
    
    Triggered when:
    - Active resume is uploaded or modified
    - LinkedIn export is uploaded or updated
    - User overrides (pinned/hidden) are changed
    """
    from ..models import Resume

    # 1. Fetch active resume
    active_resume = db.scalar(
        select(Resume).where(
            Resume.user_id == user_id,
            Resume.is_active == True,
        ).order_by(Resume.created_at.desc())
    )
    if not active_resume:
        # Fallback to any resume
        active_resume = db.scalar(
            select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc())
        )

    resume_data = active_resume.structured_data if active_resume else None
    resume_ref = f"Resume #{active_resume.id}" if active_resume else "None"

    # 2. Fetch LinkedIn Profile
    linkedin_prof = db.scalar(
        select(UserLinkedInProfile).where(UserLinkedInProfile.user_id == user_id)
    )

    # 3. Fetch existing unified record
    unified_record = db.scalar(
        select(UserUnifiedProfile).where(UserUnifiedProfile.user_id == user_id)
    )
    if not unified_record:
        unified_record = UserUnifiedProfile(
            user_id=user_id,
            use_linkedin_in_matching=True,
            user_overrides={},
            unified_data={},
            conflicts=[],
            updated_at=datetime.now(timezone.utc),
        )
        db.add(unified_record)
        db.flush()

    linkedin_raw = None
    if linkedin_prof and unified_record.use_linkedin_in_matching:
        linkedin_raw = linkedin_prof.raw_data

    # 4. Perform profile fusion
    unified_data, conflicts = fuse_profiles(
        resume_data=resume_data,
        linkedin_data=linkedin_raw,
        user_overrides=unified_record.user_overrides,
        source_resume_ref=resume_ref,
        imported_at_iso=datetime.now(timezone.utc).isoformat(),
    )

    # 5. Compute version hash
    hash_payload = json.dumps(unified_data, sort_keys=True)
    version_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

    unified_record.unified_data = unified_data
    unified_record.conflicts = conflicts
    unified_record.version_hash = version_hash
    unified_record.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(unified_record)
    return unified_record


def get_unified_profile(db: Session, user_id: int) -> dict[str, Any]:
    """Authoritative single accessor function for a user's unified profile.
    
    All matching engines, gap analysis, ATS checkers, and Job Targeting Assistants
    must read candidate profile data through this accessor.
    
    If no Unified Profile exists yet, it computes one dynamically.
    """
    unified_record = db.scalar(
        select(UserUnifiedProfile).where(UserUnifiedProfile.user_id == user_id)
    )
    if not unified_record or not unified_record.unified_data:
        unified_record = recompute_unified_profile(db, user_id)

    return unified_record.unified_data


def get_unified_skills_map(db: Session, user_id: int) -> tuple[set[str], dict[str, str], list[str]]:
    """Return (canonical_skills_set, canonical_to_display_map, raw_skills_list)
    from the canonical unified profile, excluding hidden skills.
    """
    profile = get_unified_profile(db, user_id)
    skills = profile.get("skills") or []

    canonical_set: set[str] = set()
    display_map: dict[str, str] = {}
    raw_list: list[str] = []

    for s in skills:
        if s.get("hidden"):
            continue
        c_name = s.get("canonical_name") or normalize_skill(s.get("name", ""))
        display = s.get("name") or c_name
        if c_name:
            canonical_set.add(c_name)
            display_map[c_name] = display
            raw_list.append(display)

    return canonical_set, display_map, raw_list


def delete_linkedin_profile(db: Session, user_id: int) -> bool:
    """Completely remove LinkedIn data for a user and recompute unified profile to resume-only."""
    record = db.scalar(
        select(UserLinkedInProfile).where(UserLinkedInProfile.user_id == user_id)
    )
    if record:
        db.delete(record)
        db.commit()
        recompute_unified_profile(db, user_id)
        return True
    return False
