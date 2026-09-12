import io
import re
from typing import Any
from pypdf import PdfReader


class ResumeParseError(Exception):
    pass


class ScannedPdfError(ResumeParseError):
    pass


SECTION_PATTERNS: dict[str, list[str]] = {
    "summary": [
        r"summary",
        r"professional\s+summary",
        r"profile",
        r"about\s+me",
        r"objective",
        r"career\s+objective",
    ],
    "experience": [
        r"experience",
        r"work\s+experience",
        r"professional\s+experience",
        r"employment\s+history",
        r"career\s+history",
        r"expériences\s+professionnelles",
        r"expérience",
    ],
    "education": [
        r"education",
        r"academic\s+background",
        r"academic\s+history",
        r"formation",
        r"études",
        r"diplômes",
    ],
    "skills": [
        r"skills",
        r"technical\s+skills",
        r"competencies",
        r"core\s+competencies",
        r"technologies",
        r"compétences",
        r"outils",
    ],
    "projects": [
        r"projects",
        r"personal\s+projects",
        r"key\s+projects",
        r"projets",
        r"réalisations",
    ],
    "certifications": [
        r"certifications",
        r"certificates",
        r"licenses",
        r"certificats",
        r"formations",
    ],
    "languages": [
        r"languages",
        r"langues",
    ],
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
        "languages": [l.strip() for l in sections["languages"] if l.strip()],
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
