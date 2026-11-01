"""
services/resume_prompt_builder.py
=================================
Deterministic server-side builder for tailored resume generation prompts.

Architecture:
- 100% deterministic template population: NO LLM CALL is made or permitted.
  Consumes zero API quota and operates completely offline with any provider configured or none.
- Reuses canonical building blocks:
    - normalize_description from app.scraper.sanitizer
    - get_unified_profile from app.services.profile_fusion
    - get_job_skills from app.repositories.jobs
- Prompt injection defense:
    - Wraps untrusted text in strict XML-style delimiters (<job_posting>, <candidate_profile>).
    - Neutralizes closing delimiters within data to prevent breakout.
    - Explicitly instructs the LLM that content within data blocks is strictly data, never instructions.
- Privacy & data minimization:
    - Allows candidate to toggle contact details on/off.
    - Excludes all internal IDs, application notes, API keys, and other users' data.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from ..logging import get_logger
from ..scraper.sanitizer import normalize_description
from ..scraper.vocabulary import SKILL_SYNONYMS

logger = get_logger(__name__)

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "resume_prompt_template.md"
MAX_DESCRIPTION_CHARS = 15_000

COMMON_TECH_KEYWORDS = {
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust", "kotlin", "ruby", "php", "swift",
    "react", "vue", "angular", "node", "nodejs", "django", "fastapi", "flask", "spring", "express", "next.js",
    "docker", "kubernetes", "terraform", "ansible", "jenkins", "ci/cd", "helm", "argo",
    "aws", "azure", "gcp", "cloud", "linux", "bash", "sql", "postgresql", "mysql", "mongodb", "redis",
    "kafka", "spark", "hadoop", "flink", "iceberg", "snowflake", "bigquery", "databricks", "dbt", "airflow",
    "machine learning", "deep learning", "pytorch", "tensorflow", "llm", "nlp", "rag", "langchain", "transformers",
    "graphql", "rest", "grpc", "microservices", "git", "agile", "scrum", "jira",
}

PREFERRED_SECTION_PATTERNS = [
    r"(?:preferred|nice to have|plus|bonus|pluses|good to have|desired|optional|preferable)\s*(?:qualifications|skills|requirements|experience)?:?",
    r"(?:atouts|souhait[eé]s?|un plus|comp[eé]tences souhait[eé]es?|profil souhait[eé]|serait un plus):?",
    r"(?:gewenste|pluspunten|mooi meegenomen|bij voorkeur):?",
    r"(?:von vorteil|w[uü]nschenswert|idealerweise):?",
]


def _neutralize_all_delimiters(text: str) -> str:
    """Neutralize occurrences of all prompt boundary delimiters within untrusted content."""
    if not text:
        return ""
    for tag in ("job_posting", "candidate_profile"):
        text = re.sub(rf"</\s*{re.escape(tag)}\s*>", f"&lt;/{tag}&gt;", text, flags=re.IGNORECASE)
        text = re.sub(rf"<\s*{re.escape(tag)}\s*>", f"&lt;{tag}&gt;", text, flags=re.IGNORECASE)
    return text


def extract_skills_deterministic(description: str, explicit_skills: list[str] | None = None) -> tuple[list[str], list[str]]:
    """Deterministically segment required vs preferred skills from job posting.
    
    Returns:
        (required_skills, preferred_skills)
    """
    explicit = [s.strip() for s in (explicit_skills or []) if s and s.strip()]
    if not description:
        return (explicit if explicit else ["None explicitly specified"], ["None explicitly specified"])

    desc_lower = description.lower()

    # Split into general vs preferred text if preferred section detected
    preferred_text = ""
    required_text = desc_lower

    for pat in PREFERRED_SECTION_PATTERNS:
        match = re.search(pat, desc_lower, flags=re.IGNORECASE)
        if match:
            split_idx = match.start()
            required_text = desc_lower[:split_idx]
            preferred_text = desc_lower[split_idx:]
            break

    # Extract tech keywords
    detected_req: list[str] = []
    detected_pref: list[str] = []

    # Include explicit skills first
    for s in explicit:
        s_clean = s.strip()
        if preferred_text and re.search(rf"\b{re.escape(s_clean.lower())}\b", preferred_text):
            if s_clean not in detected_pref:
                detected_pref.append(s_clean)
        else:
            if s_clean not in detected_req:
                detected_req.append(s_clean)

    # Search keyword vocabulary
    combined_vocab = sorted(list(COMMON_TECH_KEYWORDS.union(set(SKILL_SYNONYMS.values()))), key=lambda x: -len(x))
    for kw in combined_vocab:
        kw_pattern = rf"\b{re.escape(kw)}\b"
        if re.search(kw_pattern, required_text):
            display = kw.title() if len(kw) > 3 else kw.upper()
            if display not in detected_req and display not in detected_pref:
                detected_req.append(display)
        elif preferred_text and re.search(kw_pattern, preferred_text):
            display = kw.title() if len(kw) > 3 else kw.upper()
            if display not in detected_pref and display not in detected_req:
                detected_pref.append(display)

    if not detected_req:
        detected_req = ["None explicitly specified"]
    if not detected_pref:
        detected_pref = ["None explicitly specified"]

    return detected_req[:15], detected_pref[:10]


def render_candidate_profile_markdown(unified_profile: dict[str, Any], include_contact: bool = True) -> tuple[str, bool]:
    """Render unified profile dictionary into clean, deduplicated, ATS-ready Markdown.
    
    Returns:
        (profile_markdown, has_profile)
    """
    contact = unified_profile.get("contact") or {}
    skills = unified_profile.get("skills") or []
    experience = unified_profile.get("experience") or []
    education = unified_profile.get("education") or []
    certifications = unified_profile.get("certifications") or []
    languages = unified_profile.get("languages") or []
    projects = unified_profile.get("projects") or []
    honors = unified_profile.get("honors") or []
    courses = unified_profile.get("courses") or []

    # Determine whether profile has substantial content
    has_experience = any(e.get("title") or e.get("company") for e in experience if isinstance(e, dict))
    has_skills = any(s.get("name") for s in skills if isinstance(s, dict) and not s.get("hidden"))
    has_education = any(ed.get("school") or ed.get("degree") for ed in education if isinstance(ed, dict))
    has_summary = bool(contact.get("summary"))
    has_projects = any(p.get("name") for p in projects if isinstance(p, dict))

    has_profile = has_experience or has_skills or has_education or has_summary or has_projects

    lines: list[str] = []

    # 1. Contact / Identity
    full_name = contact.get("full_name") or "Candidate"
    lines.append(f"## {full_name}")
    if contact.get("headline"):
        lines.append(f"*{contact.get('headline')}*\n")

    if include_contact:
        contact_parts: list[str] = []
        if contact.get("email"):
            contact_parts.append(f"Email: {contact['email']}")
        if contact.get("phone"):
            contact_parts.append(f"Phone: {contact['phone']}")
        if contact.get("location"):
            contact_parts.append(f"Location: {contact['location']}")
        if contact_parts:
            lines.append(" | ".join(contact_parts) + "\n")
    else:
        lines.append("*[Contact details omitted by candidate preference]*\n")

    # 2. Professional Summary
    lines.append("### Professional Summary")
    if contact.get("summary"):
        lines.append(f"{contact['summary']}\n")
    else:
        lines.append("*[No professional summary provided in profile]*\n")

    # 3. Experience (Deduplicated, Chronological)
    lines.append("### Work Experience")
    valid_exp = [e for e in experience if isinstance(e, dict) and not e.get("hidden")]
    if valid_exp:
        for exp in valid_exp:
            title = exp.get("title") or "Position"
            company = exp.get("company") or "Company"
            start = exp.get("start_date") or ""
            end = exp.get("end_date") or "Present"
            date_str = f"{start} – {end}" if start else end
            loc = exp.get("location") or ""
            meta_str = f"{date_str} | {loc}" if loc else date_str

            lines.append(f"**{title}** — {company}")
            if meta_str.strip():
                lines.append(f"*{meta_str}*")
            if exp.get("description"):
                lines.append(f"{exp['description']}")
            highlights = exp.get("highlights") or []
            if isinstance(highlights, list) and highlights:
                for h in highlights:
                    if h and str(h).strip():
                        lines.append(f"• {str(h).strip()}")
            lines.append("")
    else:
        lines.append("*[No work experience recorded in profile]*\n")

    # 4. Education
    lines.append("### Education")
    valid_edu = [ed for ed in education if isinstance(ed, dict) and not ed.get("hidden")]
    if valid_edu:
        for edu in valid_edu:
            degree = edu.get("degree") or ""
            field = edu.get("field_of_study") or ""
            school = edu.get("school") or "Institution"
            degree_str = f"{degree} in {field}" if (degree and field) else (degree or field or "Degree")
            start = edu.get("start_date") or ""
            end = edu.get("end_date") or ""
            date_str = f"{start} – {end}" if (start and end) else (end or start)

            lines.append(f"**{degree_str}** — {school}")
            if date_str:
                lines.append(f"*{date_str}*")
            if edu.get("grade"):
                lines.append(f"Grade / Distinction: {edu['grade']}")
            lines.append("")
    else:
        lines.append("*[No formal education recorded in profile]*\n")

    # 5. Skills (Deduplicated across resume + LinkedIn)
    lines.append("### Skills & Core Competencies")
    seen_skills: set[str] = set()
    unique_skills: list[str] = []
    for s in skills:
        if not isinstance(s, dict) or s.get("hidden"):
            continue
        s_name = s.get("name") or s.get("canonical_name") or ""
        s_canon = (s.get("canonical_name") or s_name).strip().lower()
        if s_canon and s_canon not in seen_skills:
            seen_skills.add(s_canon)
            unique_skills.append(s_name.strip())

    if unique_skills:
        lines.append(", ".join(sorted(unique_skills, key=str.casefold)))
        lines.append("")
    else:
        lines.append("*[No skills listed in profile]*\n")

    # 6. Certifications
    lines.append("### Certifications")
    valid_certs = [c for c in certifications if isinstance(c, dict) and not c.get("hidden")]
    if valid_certs:
        for c in valid_certs:
            name = c.get("name") or "Certification"
            issuer = c.get("issuer") or ""
            date_val = c.get("issue_date") or ""
            extra = f" — {issuer}" if issuer else ""
            extra += f" ({date_val})" if date_val else ""
            lines.append(f"• **{name}**{extra}")
        lines.append("")
    else:
        lines.append("*[No certifications listed in profile]*\n")

    # 7. Languages
    lines.append("### Languages")
    valid_langs = [l for l in languages if isinstance(l, dict) and not l.get("hidden")]
    if valid_langs:
        for l in valid_langs:
            lname = l.get("language") or ""
            prof = l.get("proficiency") or ""
            prof_str = f" ({prof})" if prof else ""
            lines.append(f"• {lname}{prof_str}")
        lines.append("")
    else:
        lines.append("*[No languages listed in profile]*\n")

    # 8. Projects
    lines.append("### Projects")
    valid_projs = [p for p in projects if isinstance(p, dict) and not p.get("hidden")]
    if valid_projs:
        for p in valid_projs:
            pname = p.get("name") or "Project"
            pdesc = p.get("description") or ""
            techs = p.get("technologies") or []
            tech_str = ", ".join(techs) if isinstance(techs, list) else str(techs)

            lines.append(f"**{pname}**")
            if pdesc:
                lines.append(f"{pdesc}")
            if tech_str:
                lines.append(f"*Technologies:* {tech_str}")
            lines.append("")
    else:
        lines.append("*[No standalone projects listed in profile]*\n")

    # 9. Additional Honors or Courses
    if honors:
        lines.append("### Honors & Awards")
        for h in honors:
            lines.append(f"• {h}")
        lines.append("")

    if courses:
        lines.append("### Relevant Coursework")
        for crs in courses:
            lines.append(f"• {crs}")
        lines.append("")

    profile_text = "\n".join(lines).strip()
    return profile_text, has_profile


def build_tailored_resume_prompt(
    job_data: dict[str, Any],
    unified_profile: dict[str, Any],
    include_contact: bool = True,
) -> tuple[str, bool, int]:
    """Assemble the complete ready-to-paste markdown prompt.
    
    Returns:
        (prompt_text, has_profile, char_count)
    """
    # 1. Load template
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Resume prompt template not found at {TEMPLATE_PATH}")
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    # 2. Clean & normalize job details
    title = str(job_data.get("title") or "Position Not Specified").strip()
    company = str(job_data.get("company") or "Company Not Specified").strip()
    location = str(job_data.get("location") or "Location Not Specified").strip()
    job_type = str(job_data.get("type") or job_data.get("employment_type") or "Full-time").strip()
    remote_type = str(job_data.get("remote_type") or "").strip()
    if remote_type and remote_type.lower() not in job_type.lower():
        type_str = f"{job_type} / {remote_type}"
    else:
        type_str = job_type
    url = str(job_data.get("url") or job_data.get("job_url") or "Not provided").strip()

    # Normalize description using canonical normalizer
    raw_desc = job_data.get("description") or job_data.get("description_text") or ""
    clean_desc = normalize_description(raw_desc)

    # Cap description at 15,000 characters
    if len(clean_desc) > MAX_DESCRIPTION_CHARS:
        clean_desc = clean_desc[:MAX_DESCRIPTION_CHARS].rstrip() + "\n\n[description truncated at 15,000 characters]"

    # Deterministic skill extraction
    explicit_skills = job_data.get("skills") or []
    req_skills, pref_skills = extract_skills_deterministic(clean_desc, explicit_skills)

    # 3. Render Profile
    profile_md, has_profile = render_candidate_profile_markdown(unified_profile, include_contact=include_contact)

    # 4. Injection Safety & Neutralization
    safe_title = _neutralize_all_delimiters(title)
    safe_company = _neutralize_all_delimiters(company)
    safe_location = _neutralize_all_delimiters(location)
    safe_type = _neutralize_all_delimiters(type_str)
    safe_url = _neutralize_all_delimiters(url)
    safe_req = _neutralize_all_delimiters(", ".join(req_skills))
    safe_pref = _neutralize_all_delimiters(", ".join(pref_skills))
    safe_desc = _neutralize_all_delimiters(clean_desc)

    safe_profile = _neutralize_all_delimiters(profile_md)

    # 5. Populate Template
    populated = template
    populated = populated.replace("{{title}}", safe_title)
    populated = populated.replace("{{company}}", safe_company)
    populated = populated.replace("{{location}}", safe_location)
    populated = populated.replace("{{type}}", safe_type)
    populated = populated.replace("{{url}}", safe_url)
    populated = populated.replace("{{required_skills}}", safe_req)
    populated = populated.replace("{{preferred_skills}}", safe_pref)
    populated = populated.replace("{{description}}", safe_desc)
    populated = populated.replace("{{profile_markdown}}", safe_profile)

    return populated, has_profile, len(populated)
