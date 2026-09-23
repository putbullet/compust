import io
import re
from typing import Any
from pypdf import PdfReader


class ResumeParseError(Exception):
    pass


class ScannedPdfError(ResumeParseError):
    pass


# ==============================================================================
# Multilingual Section Headers Definition
# Extensible dictionary mapping canonical section names -> language code -> list of regex/keyword patterns.
# Supported out-of-the-box: English (en), French (fr), German (de).
# Adding a new language is purely a data addition to this dictionary.
# ==============================================================================
MULTILINGUAL_SECTION_HEADERS: dict[str, dict[str, list[str]]] = {
    "summary": {
        "en": [
            r"summary",
            r"professional\s+summary",
            r"profile",
            r"personal\s+profile",
            r"about\s+me",
            r"objective",
            r"career\s+objective",
            r"executive\s+summary",
            r"personal\s+statement",
        ],
        "fr": [
            r"r[eé]sum[eé]",
            r"profil(?:\s+professionnel)?",
            r"[aà]\s+propos(?:\s+de\s+moi)?",
            r"objectif(?:\s+professionnel)?",
            r"synth[eè]se",
            r"pr[eé]sentation",
        ],
        "de": [
            r"zusammenfassung",
            r"[uü]ber\s+mich",
            r"profil",
            r"kurzprofil",
            r"berufliches\s+profil",
            r"pers[oö]nliches\s+profil",
            r"(?:karriere)?ziel",
        ],
    },
    "experience": {
        "en": [
            r"experience",
            r"work\s+experience",
            r"professional\s+experience",
            r"employment\s+history",
            r"career\s+history",
            r"work\s+history",
            r"relevant\s+experience",
        ],
        "fr": [
            r"exp[eé]rience(?:s)?(?:\s+professionnelle(?:s)?)?",
            r"parcours\s+professionnel",
            r"historique\s+professionnel",
            r"postes\s+occup[eé]s",
            r"ant[eé]c[eé]dents\s+professionnels",
        ],
        "de": [
            r"berufserfahrung",
            r"beruflicher\s+werdegang",
            r"arbeitserfahrung",
            r"praktische\s+erfahrung",
            r"berufspraxis",
            r"werdegang",
            r"t[aä]tigkeiten",
            r"anstellungen",
        ],
    },
    "education": {
        "en": [
            r"education",
            r"academic\s+background",
            r"academic\s+history",
            r"educational\s+background",
            r"degrees",
            r"qualifications",
        ],
        "fr": [
            r"formation(?:s)?",
            r"[eé]tudes",
            r"dipl[oô]mes",
            r"cursus(?:\s+acad[eé]mique)?",
            r"parcours\s+acad[eé]mique",
        ],
        "de": [
            r"ausbildung",
            r"bildungsweg",
            r"studium",
            r"schulausbildung",
            r"akademischer\s+werdegang",
            r"bildung",
            r"hochschulbildung",
            r"abschluss",
        ],
    },
    "skills": {
        "en": [
            r"skills",
            r"technical\s+skills",
            r"competencies",
            r"core\s+competencies",
            r"technologies",
            r"hard\s+skills",
            r"soft\s+skills",
            r"key\s+skills",
            r"areas\s+of\s+expertise",
            r"tools",
        ],
        "fr": [
            r"comp[eé]tences(?:\s+techniques)?",
            r"outils(?:\s+et\s+technologies)?",
            r"technologies",
            r"savoir[- ]faire",
            r"domaines\s+de\s+comp[eé]tences",
            r"expertises",
            r"connaissances\s+techniques",
        ],
        "de": [
            r"f[aä]higkeiten",
            r"kenntnisse",
            r"fachkenntnisse",
            r"it[- ]kenntnisse",
            r"kompetenzen",
            r"qualifikationen",
            r"technologien",
            r"fachliche\s+kenntnisse",
            r"fertigkeiten",
            r"schwerpunkte",
        ],
    },
    "projects": {
        "en": [
            r"projects",
            r"personal\s+projects",
            r"key\s+projects",
            r"academic\s+projects",
            r"selected\s+projects",
            r"portfolio",
        ],
        "fr": [
            r"projets(?:\s+personnels|\s+acad[eé]miques|\s+cl[eé]s)?",
            r"r[eé]alisations(?:\s+cl[eé]s)?",
            r"travaux",
        ],
        "de": [
            r"projekte",
            r"projektarbeit",
            r"pers[oö]nliche\s+projekte",
            r"ausgew[aä]hlte\s+projekte",
        ],
    },
    "certifications": {
        "en": [
            r"certifications",
            r"certificates",
            r"licenses",
            r"courses",
            r"accreditations",
        ],
        "fr": [
            r"certifications",
            r"certificats",
            r"attestations",
            r"licences",
            r"accr[eé]ditations",
        ],
        "de": [
            r"zertifikate",
            r"zertifizierungen",
            r"weiterbildung(?:en)?",
            r"lehrg[aä]nge",
            r"lizenzen",
        ],
    },
    "languages": {
        "en": [
            r"languages",
            r"language\s+skills",
            r"languages\s+spoken",
        ],
        "fr": [
            r"langues(?:\s+parl[eé]es|\s+vivantes)?",
            r"comp[eé]tences\s+linguistiques",
        ],
        "de": [
            r"sprachen",
            r"sprachkenntnisse",
            r"fremdsprachen",
        ],
    },
}

# Flatten for backward compatibility and regex compilation
SECTION_PATTERNS: dict[str, list[str]] = {
    section: [pattern for lang_patterns in lang_dict.values() for pattern in lang_patterns]
    for section, lang_dict in MULTILINGUAL_SECTION_HEADERS.items()
}



def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract raw text from PDF bytes using text layer. Strictly NO OCR."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception as exc:
        raise ResumeParseError(f"Failed to read PDF file: {exc}") from exc

    if len(reader.pages) == 0:
        raise ScannedPdfError("This PDF does not contain extractable text. Please upload a text-based PDF.")

    text_parts = []
    for page in reader.pages:
        try:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        except Exception:
            continue

    combined_text = "\n".join(text_parts).strip()
    # If less than 20 characters of extractable text, treat as scanned/image PDF
    if len(combined_text) < 20 or not any(c.isalnum() for c in combined_text):
        raise ScannedPdfError("This PDF does not contain extractable text. Please upload a text-based PDF.")

    return combined_text


def parse_skills_list(skills_text: str) -> list[str]:
    """Parse comma/bullet/newline separated skill items into clean list."""
    if not skills_text:
        return []
    # Replace bullets and delimiters
    cleaned = re.sub(r"[•·\|\*\(\)]", ",", skills_text)
    items = []
    for line in cleaned.splitlines():
        parts = line.split(",")
        for p in parts:
            item = p.strip(" \t\n-:,.")
            if 1 < len(item) < 40 and not item.lower().startswith("http"):
                items.append(item)
    # Deduplicate preserving order
    seen = set()
    result = []
    for item in items:
        lower = item.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(item)
    return result


def parse_languages_list(languages_text: str) -> list[str]:
    """Parse comma/bullet/newline separated language items into a clean list."""
    if not languages_text:
        return []

    items = []
    for raw_line in languages_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Split by comma or semicolon
        parts = re.split(r"[,;]+", line)
        for part in parts:
            p = part.strip(" \t\n-•*·:–—")
            if not p:
                continue
            # Remove parenthetical level notes (e.g. '(native)', '(courant)', '(B2)')
            clean_name = re.sub(r"\s*[\(\[].*?[\)\]]", "", p).strip()
            # If formatted like "Français : langue maternelle" or "English - Fluent"
            if ":" in clean_name or " - " in clean_name:
                clean_name = re.split(r"[:\-]", clean_name)[0].strip()
            
            chosen = clean_name if 1 < len(clean_name) <= 30 else p[:30].strip()
            if 1 < len(chosen) <= 35 and not chosen.lower().startswith("http"):
                items.append(chosen)

    # Deduplicate preserving order
    seen = set()
    result = []
    for item in items:
        lower = item.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(item)
    return result


def structure_resume_text(raw_text: str) -> dict[str, Any]:
    """Split raw resume text into logical sections based on common headings."""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    # Build regex matching any section heading line
    heading_map: list[tuple[str, re.Pattern]] = []
    for section_name, patterns in SECTION_PATTERNS.items():
        joined = "|".join(patterns)
        pattern = re.compile(rf"^(?:#+|\d+\.?)?\s*(?:{joined})\s*[:\-\—]?$", re.IGNORECASE)
        heading_map.append((section_name, pattern))

    sections: dict[str, list[str]] = {
        "summary": [],
        "experience": [],
        "education": [],
        "skills": [],
        "projects": [],
        "certifications": [],
        "languages": [],
        "other": [],
    }

    current_section = "summary"
    for line in lines:
        matched_section = None
        for sec, pat in heading_map:
            if pat.match(line):
                matched_section = sec
                break

        if matched_section:
            current_section = matched_section
        else:
            sections[current_section].append(line)

    structured: dict[str, Any] = {
        "summary": "\n".join(sections["summary"]).strip(),
        "experience": "\n".join(sections["experience"]).strip(),
        "education": "\n".join(sections["education"]).strip(),
        "skills": parse_skills_list("\n".join(sections["skills"])),
        "skills_raw": "\n".join(sections["skills"]).strip(),
        "projects": "\n".join(sections["projects"]).strip(),
        "certifications": "\n".join(sections["certifications"]).strip(),
        "languages": parse_languages_list("\n".join(sections["languages"])),
    }

    # If skills list was empty from section heading, scan for known technical skills in raw text
    if not structured["skills"]:
        from ..scraper.vocabulary import SKILL_SYNONYMS
        extracted = []
        raw_lower = raw_text.lower()
        unique_skills = sorted(list(set(SKILL_SYNONYMS.values())))
        for skill in unique_skills:
            if re.search(rf"\b{re.escape(skill.lower())}\b", raw_lower):
                extracted.append(skill)
        structured["skills"] = extracted

    return structured

