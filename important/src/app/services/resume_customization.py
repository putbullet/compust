import re
from typing import Any
from sqlalchemy.orm import Session

from ..models import Job, Resume
from ..repositories.jobs import get_job_skills
from .ai_service import generate_completion, check_ollama_runtime


def analyze_ats_formatting(resume: Resume) -> list[str]:
    """Inspect structured resume characteristics and detect ATS compatibility improvements."""
    improvements = []
    parsed = resume.parsed_sections or {}
    if (not parsed or not parsed.get("skills")) and resume.structured_data:
        from ..repositories.resume import build_parsed_sections_from_structured_data
        parsed = build_parsed_sections_from_structured_data(resume.structured_data)

    raw = resume.raw_text or ""
    if not raw and resume.structured_data:
        from ..repositories.resume import build_raw_text_from_structured_data
        raw = build_raw_text_from_structured_data(resume.structured_data)

    # 1. Check section presence
    essential_sections = ["experience", "education", "skills"]
    for sec in essential_sections:
        if not parsed.get(sec):
            improvements.append(
                f"Missing standard '{sec.capitalize()}' section heading. Standardize section headers for ATS scanners."
            )

    # 2. Check contact info / phone / email
    has_email = bool(re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", raw))
    if not has_email:
        improvements.append("No explicit contact email detected in the text layer. Ensure your email is in plain text header.")

    has_phone = bool(re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,4}", raw))
    if not has_phone:
        improvements.append("No standard phone number recognized. Ensure your contact telephone number is clearly formatted.")

    # 3. Check date consistency in experience
    dates_found = re.findall(r"\b(19\d\d|20\d\d)\b", raw)
    if not dates_found:
        improvements.append("Timeline dates (years) are not clearly detectable. Include explicit start and end dates (e.g., 2022 - 2024).")

    # 4. Check bullet points vs long paragraphs
    exp_text = parsed.get("experience", "")
    if exp_text and not any(bullet in exp_text for bullet in ["•", "-", "*", "·"]):
        improvements.append("Work experience appears in paragraph blocks. Use bullet points for key achievements to improve ATS readability.")

    if not improvements:
        improvements.append("Section layout and headers comply with standard ATS parsing conventions.")

    return improvements


def analyze_resume_alignment(
    job: Job,
    job_skills: list[str],
    resume: Resume,
    user: Any | None = None,
) -> dict[str, Any]:
    """Compare job skills/description with structured resume deterministically with actionable recommendations."""
    import unicodedata
    from ..repositories.resume import (
        extract_canonical_skills_map,
        get_canonical_resume_sections,
        build_raw_text_from_structured_data,
    )
    from ..scraper.vocabulary import SKILL_SYNONYMS

    def _canonical(s: str) -> str:
        cleaned = s.strip().lower()
        unacc = unicodedata.normalize("NFKD", cleaned).encode("ASCII", "ignore").decode("utf-8")
        if cleaned in SKILL_SYNONYMS:
            return SKILL_SYNONYMS[cleaned].lower()
        if unacc in SKILL_SYNONYMS:
            return SKILL_SYNONYMS[unacc].lower()
        return unacc

    canonical_candidate_skills, candidate_display_map, raw_candidate_skills = extract_canonical_skills_map(resume, user)

    resume_raw_lower = (resume.raw_text or "").lower()
    if not resume_raw_lower and resume.structured_data:
        resume_raw_lower = build_raw_text_from_structured_data(resume.structured_data).lower()

    # Job requirements
    req_skills = [s.strip() for s in job_skills if s and s.strip()]

    # If no explicit job skills in DB, extract from job description & title
    if not req_skills and (job.description or job.title):
        full_text = f"{job.title or ''} {job.description or ''}".lower()
        full_text_unacc = unicodedata.normalize("NFKD", full_text).encode("ASCII", "ignore").decode("utf-8")

        extracted_from_desc = []
        for alias, canon in SKILL_SYNONYMS.items():
            pattern = rf"\b{re.escape(alias.lower())}\b"
            if re.search(pattern, full_text) or re.search(pattern, full_text_unacc):
                if canon not in extracted_from_desc:
                    extracted_from_desc.append(canon)

        req_skills = extracted_from_desc

    already_demonstrated = []
    missing_or_weak = []
    recommendations_list = []

    for req in req_skills:
        req_clean = req.strip()
        req_canon = _canonical(req_clean)
        req_unacc = unicodedata.normalize("NFKD", req_clean.lower()).encode("ASCII", "ignore").decode("utf-8")

        is_candidate_skill = (
            req_canon in canonical_candidate_skills
            or any(
                req_canon == _canonical(r)
                or req_unacc in unicodedata.normalize("NFKD", r.lower()).encode("ASCII", "ignore").decode("utf-8")
                or unicodedata.normalize("NFKD", r.lower()).encode("ASCII", "ignore").decode("utf-8") in req_unacc
                for r in raw_candidate_skills
            )
        )

        in_raw = (
            bool(re.search(rf"\b{re.escape(req_clean.lower())}\b", resume_raw_lower))
            or bool(re.search(rf"\b{re.escape(req_unacc)}\b", resume_raw_lower))
            or (req_canon in candidate_display_map and bool(re.search(rf"\b{re.escape(candidate_display_map[req_canon].lower())}\b", resume_raw_lower)))
        )

        if is_candidate_skill or in_raw:
            already_demonstrated.append(req_clean)
            if not in_raw:
                recommendations_list.append({
                    "requirement": req_clean,
                    "status": "Demonstrated (Reinforce in Experience)",
                    "weakness": f"'{req_clean}' is declared in your skills profile. To pass strict ATS work-history filters, substantiate it with a concrete achievement in your Experience or Projects section.",
                    "suggested_action": f"Add an achievement or task highlighting your hands-on use of {req_clean} in your Experience or Projects.",
                    "location": "Experience or Projects section",
                })
        else:
            missing_or_weak.append(req_clean)
            recommendations_list.append({
                "requirement": req_clean,
                "status": "Missing",
                "weakness": f"'{req_clean}' is not mentioned in your resume or profile.",
                "suggested_action": f"Do not invent experience. If you have legitimate project or lab exposure to {req_clean}, consider incorporating it.",
                "location": "Skills or Projects section",
            })

    # ATS Formatting analysis
    ats_improvements = analyze_ats_formatting(resume)

    # General suggestions
    suggestions = []
    if already_demonstrated:
        shown = ", ".join(already_demonstrated[:4])
        suggestions.append(f"Your resume already demonstrates key requirements: {shown}.")

    if missing_or_weak:
        for missing in missing_or_weak[:3]:
            suggestions.append(
                f"The job requires '{missing}', which is not explicitly highlighted in your resume. "
                f"If you have experience with {missing}, consider detailing it in your experience or projects section."
            )
    else:
        suggestions.append("Your resume aligns closely with all extracted technical requirements for this vacancy.")

    suggestions.append("Note: Always ensure experience you add reflects genuine past projects or skills.")

    return {
        "job_id": job.id,
        "job_title": job.title,
        "already_demonstrated": already_demonstrated,
        "missing_or_weak": missing_or_weak,
        "ats_improvements": ats_improvements,
        "actionable_recommendations": recommendations_list,
        "suggestions": suggestions,
        "requirements_status": "COMPLETE" if req_skills else "PARSER_INCOMPLETE",
    }


CUSTOMIZATION_SYSTEM_PROMPT = """You are COMPUST's Career Advisory Assistant.
Compare the user's resume against the target job vacancy.
RULES:
1. Identify already demonstrated qualifications.
2. Identify missing or weak requirements.
3. Provide ethical suggestions to tailor the resume without inventing experience.
4. NEVER advise the candidate to claim skills or years of experience they do not possess.
5. Keep the tone concise, encouraging, and professional."""


def get_ai_resume_customization(
    db: Session,
    job: Job,
    resume: Resume,
    user: Any | None = None,
) -> dict[str, Any]:
    skills = get_job_skills(db, job.id)
    analysis = analyze_resume_alignment(job, skills, resume, user=user)

    runtime = check_ollama_runtime()
    if runtime["status"] != "connected" or not runtime["models"]:
        return {
            **analysis,
            "ai_enhanced": False,
            "provider": "deterministic",
        }

    # Format concise prompt for local 0.8B model
    prompt = (
        f"Job Title: {job.title}\n"
        f"Requirements: {', '.join(skills) if skills else 'Not specified'}\n"
        f"Demonstrated: {', '.join(analysis['already_demonstrated']) if analysis['already_demonstrated'] else 'None'}\n"
        f"Missing or weak: {', '.join(analysis['missing_or_weak']) if analysis['missing_or_weak'] else 'None'}\n"
        f"Provide 2-3 tailored, ethical bullet points on positioning genuine experience:"
    )

    try:
        response = generate_completion(
            prompt=prompt,
            system_prompt=CUSTOMIZATION_SYSTEM_PROMPT,
            model=runtime.get("selected_model"),
            temperature=0.2,
            timeout_seconds=12.0,
        )
        if response:
            ai_suggestions = [line.strip(" -*•") for line in response.splitlines() if len(line.strip()) > 10]
            if ai_suggestions:
                analysis["suggestions"] = ai_suggestions
                analysis["ai_enhanced"] = True
                analysis["provider"] = "ollama"
    except Exception:
        pass

    return analysis
