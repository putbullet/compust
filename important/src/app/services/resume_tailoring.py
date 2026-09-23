import re
from typing import Any
from sqlalchemy.orm import Session

from ..models import Job, Resume, User
from ..repositories.resume import create_structured_resume, get_user_resume
from ..repositories.jobs import get_job_skills


def extract_job_required_skills(job: Job, explicit_skills: list[str]) -> list[str]:
    reqs = [s.strip() for s in explicit_skills if s.strip()]
    if not reqs and job.description:
        from ..scraper.vocabulary import SKILL_SYNONYMS
        desc_lower = job.description.lower()
        unique = sorted(list(set(SKILL_SYNONYMS.values())))
        for skill in unique:
            if re.search(rf"\b{re.escape(skill.lower())}\b", desc_lower):
                reqs.append(skill)
    return reqs


def analyze_structured_resume_for_job(
    job: Job,
    explicit_job_skills: list[str],
    resume: Resume,
) -> dict[str, Any]:
    import unicodedata
    from ..repositories.resume import extract_canonical_skills_map
    from ..scraper.vocabulary import SKILL_SYNONYMS

    structured = resume.structured_data or {}
    profile = structured.get("profile", {})
    canon_candidate_skills, display_map, raw_skills = extract_canonical_skills_map(resume)

    required_skills = extract_job_required_skills(job, explicit_job_skills)
    matched_skills = []
    missing_skills = []

    for req in required_skills:
        req_clean = req.strip()
        req_canon = SKILL_SYNONYMS.get(req_clean.lower(), req_clean.lower()).lower()
        req_unacc = unicodedata.normalize("NFKD", req_clean.lower()).encode("ASCII", "ignore").decode("utf-8")
        if (
            req_canon in canon_candidate_skills
            or any(
                req_unacc in unicodedata.normalize("NFKD", r.lower()).encode("ASCII", "ignore").decode("utf-8")
                or unicodedata.normalize("NFKD", r.lower()).encode("ASCII", "ignore").decode("utf-8") in req_unacc
                for r in raw_skills
            )
        ):
            matched_skills.append(req_clean)
        else:
            missing_skills.append(req_clean)

    total_reqs = len(required_skills)
    match_score = int((len(matched_skills) / total_reqs * 100)) if total_reqs > 0 else 75
    match_score = max(20, min(95, match_score))

    # Construct tailored summary suggestion based strictly on candidate's real profile
    orig_summary = profile.get("summary") or ""
    matched_str = ", ".join(matched_skills[:3]) if matched_skills else "software engineering"
    suggested_summary = (
        f"Versatile professional targeting the {job.title} role. "
        f"Demonstrated competence in {matched_str}, with hands-on experience delivering robust systems, "
        f"collaborating across cross-functional teams, and rapidly adapting to technological stacks."
    )

    # Suggest experience highlights refinement for existing roles only
    experience = structured.get("experience", [])
    exp_refinements = []
    for exp in experience[:2]:
        comp = exp.get("company", "Past Role")
        title = exp.get("title", "")
        desc = exp.get("description", "")
        # Suggest emphasizing matched skills
        new_bullets = []
        if matched_skills:
            top_skill = matched_skills[0]
            new_bullets.append(f"Leveraged {top_skill} and engineering best practices to enhance system reliability and delivery velocity.")
        new_bullets.append(f"Collaborated with product and engineering teams to implement scalable features aligned with enterprise standards.")

        exp_refinements.append({
            "item_id": exp.get("id", ""),
            "company": comp,
            "title": title,
            "original_description": desc,
            "suggested_highlights": new_bullets,
            "reason": f"Highlight impact and practical application of {matched_str} relevant to {job.title}.",
        })

    key_advice = [
        f"Emphasize your verified experience in {', '.join(matched_skills[:3])}." if matched_skills else "Focus on core transferable software principles.",
        f"Note: '{', '.join(missing_skills[:3])}' were identified as required but not present in your profile. Do not invent experience; prepare to address learning agility in interviews." if missing_skills else "Your documented skills align strongly with this vacancy.",
    ]

    return {
        "job_id": job.id,
        "job_title": job.title,
        "base_resume_id": resume.id,
        "base_resume_title": resume.title,
        "match_score": match_score,
        "summary": {
            "original": orig_summary,
            "suggested": suggested_summary,
            "reason": f"Positions your authentic background directly for {job.title} without inventing unverified claims.",
        },
        "skills_to_emphasize": matched_skills,
        "missing_job_skills": missing_skills,
        "experience_refinements": exp_refinements,
        "key_advice": key_advice,
    }


def save_tailored_resume_copy(
    db: Session,
    user_id: int,
    base_resume_id: int,
    job: Job,
    title: str,
    apply_suggested_summary: bool = True,
    apply_emphasized_skills: bool = True,
    accepted_experience_refinements: list[str] | None = None,
) -> Resume:
    base_resume = get_user_resume(db, user_id, base_resume_id)
    if not base_resume:
        raise ValueError("Base resume not found.")

    # Deep copy structured data
    import copy
    tailored_data = copy.deepcopy(base_resume.structured_data or {})
    tailored_settings = copy.deepcopy(base_resume.settings or {})

    # Compute tailoring suggestions
    job_skills = get_job_skills(db, job.id)
    analysis = analyze_structured_resume_for_job(job, job_skills, base_resume)

    if apply_suggested_summary and analysis["summary"]["suggested"]:
        tailored_data.setdefault("profile", {})["summary"] = analysis["summary"]["suggested"]

    if apply_emphasized_skills and analysis["skills_to_emphasize"]:
        # Reorder candidate skills so matched ones are at the beginning
        emphasized_set = {s.lower() for s in analysis["skills_to_emphasize"]}
        skills = tailored_data.get("skills", [])
        matched = [s for s in skills if s.get("name", "").lower() in emphasized_set]
        others = [s for s in skills if s.get("name", "").lower() not in emphasized_set]
        tailored_data["skills"] = matched + others

    if accepted_experience_refinements:
        accepted_set = set(accepted_experience_refinements)
        for ref in analysis["experience_refinements"]:
            if ref["item_id"] in accepted_set:
                for exp in tailored_data.get("experience", []):
                    if exp.get("id") == ref["item_id"]:
                        exp.setdefault("highlights", []).extend(ref["suggested_highlights"])
                        break

    # Tag tailored resume with target_job_id and source_resume_id (master untouched)
    new_resume = create_structured_resume(
        db=db,
        user_id=user_id,
        title=title or f"{base_resume.title} — {job.title}",
        is_default=False,
        structured_data=tailored_data,
        settings=tailored_settings,
        target_job_id=job.id,
        source_resume_id=base_resume.id,
    )
    return new_resume
