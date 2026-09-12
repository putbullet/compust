from datetime import date
import re
from typing import Any
from ..models import Job, User, UserExperience, UserLanguage
from ..schemas_auth import JobMatchExplanation

COMMON_LANGUAGES: dict[str, list[str]] = {
    "english": ["english", "anglais", "englisch"],
    "french": ["french", "français", "francais", "französisch"],
    "arabic": ["arabic", "arabe", "arabisch"],
    "spanish": ["spanish", "espagnol", "spanisch"],
    "german": ["german", "allemand", "deutsch"],
    "italian": ["italian", "italien", "italienisch"],
    "portuguese": ["portuguese", "portugais", "portugiesisch"],
    "dutch": ["dutch", "néerlandais", "nederlands", "holländisch"],
}

SKILL_SYNONYMS: dict[str, str] = {
    "react": "react",
    "react.js": "react",
    "reactjs": "react",
    "node": "nodejs",
    "node.js": "nodejs",
    "nodejs": "nodejs",
    "vue": "vue",
    "vue.js": "vue",
    "vuejs": "vue",
    "angular": "angular",
    "angularjs": "angular",
    "ts": "typescript",
    "typescript": "typescript",
    "js": "javascript",
    "javascript": "javascript",
    "py": "python",
    "python": "python",
    "python3": "python",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "docker": "docker",
    "aws": "aws",
    "amazon web services": "aws",
    "gcp": "gcp",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "azure": "azure",
    "microsoft azure": "azure",
    "fastapi": "fastapi",
    "django": "django",
    "flask": "flask",
    "spring": "spring",
    "spring boot": "spring",
    "golang": "go",
    "go": "go",
    "c#": "csharp",
    "csharp": "csharp",
    ".net": "dotnet",
    "dotnet": "dotnet",
}


def _canonical_skill(skill: str) -> str:
    cleaned = skill.strip().lower()
    return SKILL_SYNONYMS.get(cleaned, cleaned)


def _estimate_experience_months(exp: Any) -> int:
    if isinstance(exp, dict):
        start = exp.get("start_date")
        end = exp.get("end_date")
        if not start:
            return 6
        if isinstance(start, str):
            try:
                parts = [int(p) for p in start.split("-") if p.isdigit()]
                start = date(parts[0], parts[1] if len(parts) > 1 else 1, 1)
            except Exception:
                return 6
        if isinstance(end, str):
            try:
                parts = [int(p) for p in end.split("-") if p.isdigit()]
                end = date(parts[0], parts[1] if len(parts) > 1 else 1, 1)
            except Exception:
                end = date.today()
        elif not end:
            end = date.today()
        months = (end.year - start.year) * 12 + (end.month - start.month)
        return max(months, 1)

    if not getattr(exp, "start_date", None):
        return 6
    end = getattr(exp, "end_date", None) or date.today()
    start_date = exp.start_date
    months = (end.year - start_date.year) * 12 + (end.month - start_date.month)
    return max(months, 1)


def _get_active_resume(user: User) -> Any | None:
    resumes = getattr(user, "resumes", None) or []
    if not resumes:
        return None
    for r in resumes:
        if getattr(r, "is_active", False) or getattr(r, "is_default", False):
            return r
    return resumes[0]


def _extract_all_user_skills(user: User) -> tuple[set[str], dict[str, str]]:
    """Returns (canonical_skills_set, canonical_to_original_display_map)."""
    raw_skills: list[str] = []
    if user.skills:
        raw_skills.extend(s.skill for s in user.skills if s.skill)

    resume = _get_active_resume(user)
    if resume and getattr(resume, "structured_data", None):
        sdata = resume.structured_data or {}
        r_skills = sdata.get("skills", [])
        for item in r_skills:
            if isinstance(item, str) and item.strip():
                raw_skills.append(item.strip())
            elif isinstance(item, dict):
                val = item.get("name") or item.get("skill")
                if val and isinstance(val, str) and val.strip():
                    raw_skills.append(val.strip())

    canonical_set: set[str] = set()
    display_map: dict[str, str] = {}
    for raw in raw_skills:
        c = _canonical_skill(raw)
        if c:
            canonical_set.add(c)
            if c not in display_map:
                display_map[c] = raw
    return canonical_set, display_map


def calculate_job_match(
    job: Job,
    job_skills: list[str],
    user: User,
) -> JobMatchExplanation:
    """Compute an explainable, deterministic multi-factor match score (0-100%)

    Categories & weights:
    - Skills (35%)
    - Experience (25%)
    - Education (15%)
    - Location & Preferences (15%)
    - Languages (10%)
    """
    positive_factors: list[str] = []
    missing_factors: list[str] = []

    job_title = job.title or ""
    job_desc = job.description or ""
    job_full_text = (job_title + " " + job_desc).lower()
    job_loc = (job.location or "").strip()
    job_loc_lower = job_loc.lower()

    # -------------------------------------------------------------
    # 1. Skill Matching (Weight: 35%)
    # -------------------------------------------------------------
    user_skills_set, user_skills_display = _extract_all_user_skills(user)
    job_skills_cleaned = [s.strip() for s in job_skills if s and s.strip()]

    skills_score = 0
    if job_skills_cleaned:
        canonical_job_skills: dict[str, str] = {}
        for s in job_skills_cleaned:
            canonical_job_skills[_canonical_skill(s)] = s

        matched_canon = user_skills_set.intersection(canonical_job_skills.keys())
        missing_canon = set(canonical_job_skills.keys()).difference(user_skills_set)

        if matched_canon:
            matched_display = [canonical_job_skills[c] for c in matched_canon]
            ratio = len(matched_canon) / len(canonical_job_skills)
            skills_score = int(round(ratio * 100))
            positive_factors.append(f"Matched skills: {', '.join(sorted(matched_display))}")
        else:
            skills_score = 0

        if missing_canon:
            missing_display = [canonical_job_skills[c] for c in missing_canon]
            missing_factors.append(f"Missing job skills: {', '.join(sorted(missing_display)[:3])}")
    elif user_skills_set:
        # Fallback keyword match in description/title
        found_canon = [c for c in user_skills_set if c in job_full_text or user_skills_display.get(c, "").lower() in job_full_text]
        if found_canon:
            found_display = [user_skills_display[c] for c in found_canon]
            skills_score = min(len(found_canon) * 25, 100)
            positive_factors.append(f"Relevant skills in description: {', '.join(found_display[:3])}")
        else:
            skills_score = 40
    else:
        # Neutral baseline if neither side has declared specific skills
        skills_score = 60

    # -------------------------------------------------------------
    # 2. Experience Matching (Weight: 25%)
    # -------------------------------------------------------------
    user_experiences = list(getattr(user, "experience", []) or [])
    resume = _get_active_resume(user)
    if resume and getattr(resume, "structured_data", None):
        r_exp = (resume.structured_data or {}).get("experience", [])
        if isinstance(r_exp, list):
            user_experiences.extend(r_exp)

    is_senior_role = any(w in job_full_text[:300] for w in ["senior", "lead", "principal", "head", "director", "architect"])
    is_junior_role = any(w in job_full_text[:300] for w in ["intern", "stage", "junior", "entry", "trainee", "alternance"])

    exp_score = 0
    if user_experiences:
        prof_exps = [e for e in user_experiences if (getattr(e, "experience_type", None) or (isinstance(e, dict) and e.get("type")) or "professional") == "professional"]
        intern_exps = [e for e in user_experiences if (getattr(e, "experience_type", None) or (isinstance(e, dict) and e.get("type"))) == "internship"]
        project_exps = [e for e in user_experiences if (getattr(e, "experience_type", None) or (isinstance(e, dict) and e.get("type"))) == "project"]
        transferable_exps = [e for e in user_experiences if (getattr(e, "experience_type", None) or (isinstance(e, dict) and e.get("type"))) == "transferable"]

        # Calculate tenure
        prof_months = sum(_estimate_experience_months(e) for e in prof_exps) if prof_exps else 0
        prof_years = round(prof_months / 12, 1)

        # Keyword matching on job title
        job_keywords = [w for w in re.findall(r"\w+", job_title.lower()) if len(w) > 3 and w not in ["senior", "junior", "lead", "developer", "engineer"]]
        relevant_titles = []
        for e in user_experiences:
            title = getattr(e, "title", None) or (isinstance(e, dict) and e.get("title")) or ""
            if title and any(kw in title.lower() for kw in job_keywords):
                relevant_titles.append(title)

        if relevant_titles:
            positive_factors.append(f"Direct professional experience in role: {relevant_titles[0]}")

        if prof_exps:
            if is_senior_role:
                if prof_months >= 36:
                    exp_score = 100
                    positive_factors.append(f"Meets seniority requirement ({prof_years} yrs professional tenure)")
                else:
                    exp_score = 30
                    missing_factors.append(f"Senior role typically requires 3+ yrs of full-time professional experience ({prof_years} yrs recorded)")
            elif is_junior_role:
                exp_score = 90
                positive_factors.append("Substantive background aligns well with position")
            else:
                if relevant_titles:
                    if prof_months >= 24:
                        exp_score = 95
                    elif prof_months >= 12:
                        exp_score = 80
                    else:
                        exp_score = 65
                else:
                    exp_score = 45
        elif intern_exps or project_exps:
            if is_junior_role:
                exp_score = 100
                positive_factors.append("Internship / project portfolio strongly aligns with entry-level position")
            elif is_senior_role:
                exp_score = 25
                missing_factors.append("Senior roles require substantive professional career tenure beyond internships/projects")
            else:
                exp_score = 70
                positive_factors.append("Internship and project experience demonstrates domain familiarity")
        elif transferable_exps:
            exp_score = 65
            positive_factors.append("Transferable experience provides valuable cross-functional background")
        else:
            exp_score = 60
    else:
        if is_senior_role:
            exp_score = 50
            missing_factors.append("Senior role typically requires 3+ yrs of full-time professional experience")
        elif is_junior_role:
            exp_score = 85
        else:
            exp_score = 65

    # -------------------------------------------------------------
    # 3. Education Matching (Weight: 15%)
    # Critical Rule: Do NOT penalize unmentioned requirements!
    # -------------------------------------------------------------
    edu_req_terms = ["bachelor", "master", "phd", "doctorate", "bac+5", "bac+3", "licence", "master's", "bachelor's", "degree in", "diplôme d'ingénieur", "engineering degree"]
    requires_education = any(term in job_full_text for term in edu_req_terms)

    user_educations = list(getattr(user, "education", []) or [])
    if resume and getattr(resume, "structured_data", None):
        r_edu = (resume.structured_data or {}).get("education", [])
        if isinstance(r_edu, list):
            user_educations.extend(r_edu)

    edu_score = 100  # default 100 if unmentioned
    if requires_education:
        if user_educations:
            deg_names = []
            for edu in user_educations:
                deg = getattr(edu, "degree", None) or (isinstance(edu, dict) and edu.get("degree")) or ""
                if deg:
                    deg_names.append(deg)
            if deg_names:
                edu_score = 100
                positive_factors.append(f"Meets education requirement ({deg_names[0]})")
            else:
                edu_score = 70
        else:
            edu_score = 40
            missing_factors.append("Job posting requests a relevant degree not found in profile")
    else:
        # Job does not require a degree: full marks
        edu_score = 100
        if user_educations:
            deg = getattr(user_educations[0], "degree", None) or (isinstance(user_educations[0], dict) and user_educations[0].get("degree"))
            if deg:
                positive_factors.append(f"Education credential: {deg}")

    # -------------------------------------------------------------
    # 4. Location & Preferences Matching (Weight: 15%)
    # -------------------------------------------------------------
    prefs = getattr(user, "preferences", None)
    target_countries = getattr(user, "country_preferences", None) or []
    target_country_ids = {c.id for c in target_countries if getattr(c, "id", None)}
    target_country_names = {c.name.lower() for c in target_countries if getattr(c, "name", None)}
    target_country_codes = {c.code.lower() for c in target_countries if getattr(c, "code", None)}

    is_job_remote = (
        (job.remote_type and "remote" in job.remote_type.lower()) or
        "remote" in job_loc_lower or
        "télétravail" in job_loc_lower
    )

    loc_score = 100
    if is_job_remote:
        loc_score = 100
        if prefs and prefs.preferred_work_mode and "remote" in prefs.preferred_work_mode.lower():
            positive_factors.append(f"Matches work mode preference: {prefs.preferred_work_mode}")
        else:
            positive_factors.append("Remote job matches flexible location criteria")
    else:
        # Check target countries & preferred location
        has_location_criteria = bool(target_country_ids or (prefs and (prefs.preferred_location or prefs.preferred_work_mode)))
        if not has_location_criteria:
            loc_score = 100
            positive_factors.append("No restrictive location constraints specified")
        else:
            matches_country = False
            if target_country_ids and job.country_id in target_country_ids:
                matches_country = True
            elif any(c_name in job_loc_lower for c_name in target_country_names):
                matches_country = True
            elif any(c_code in job_loc_lower for c_code in target_country_codes):
                matches_country = True

            matches_pref_loc = False
            if prefs and prefs.preferred_location:
                p_loc = prefs.preferred_location.strip().lower()
                if p_loc in job_loc_lower or job_loc_lower in p_loc:
                    matches_pref_loc = True

            matches_mode = True
            if prefs and prefs.preferred_work_mode:
                p_mode = prefs.preferred_work_mode.strip().lower()
                j_mode = (job.remote_type or "").strip().lower()
                if j_mode and p_mode not in j_mode and j_mode not in p_mode:
                    matches_mode = False

            if matches_country or matches_pref_loc:
                loc_score = 100 if matches_mode else 80
                if matches_pref_loc:
                    positive_factors.append(f"Matches location: {prefs.preferred_location}")
                elif matches_country:
                    matched_c = next((c.name for c in target_countries if c.id == job.country_id or c.name.lower() in job_loc_lower), "Target country")
                    positive_factors.append(f"Matches target country: {matched_c}")

                if prefs and prefs.preferred_work_mode:
                    if matches_mode:
                        positive_factors.append(f"Matches work mode preference: {prefs.preferred_work_mode}")
                    elif job.remote_type:
                        missing_factors.append(f"Job is {job.remote_type} while you prefer {prefs.preferred_work_mode}")
            else:
                loc_score = 25
                if prefs and prefs.preferred_location:
                    missing_factors.append(f"Located in {job.location or 'other area'} (preferred: {prefs.preferred_location})")
                elif target_country_names:
                    missing_factors.append(f"Located in {job.location or 'other area'} (outside target countries)")
                if prefs and prefs.preferred_work_mode and job.remote_type and not matches_mode:
                    missing_factors.append(f"Job is {job.remote_type} while you prefer {prefs.preferred_work_mode}")

    # Salary evaluation
    if prefs and prefs.min_salary is not None and job.salary_min is not None:
        if float(job.salary_min) >= float(prefs.min_salary):
            positive_factors.append("Salary satisfies or exceeds minimum requirement")
        else:
            missing_factors.append("Job starting salary is below your preferred minimum")

    # -------------------------------------------------------------
    # 5. Language Proficiency Alignment (Weight: 10%)
    # -------------------------------------------------------------
    user_languages = list(getattr(user, "languages", []) or [])
    if resume and getattr(resume, "structured_data", None):
        r_lang = (resume.structured_data or {}).get("languages", [])
        if isinstance(r_lang, list):
            user_languages.extend(r_lang)

    user_lang_map: dict[str, str] = {}
    for l in user_languages:
        name = getattr(l, "language", None) or (isinstance(l, dict) and l.get("language")) or ""
        prof = getattr(l, "proficiency", None) or (isinstance(l, dict) and l.get("proficiency")) or "fluent"
        if name:
            user_lang_map[name.strip().lower()] = prof.strip().lower()

    # Detect if job requires specific languages
    required_canon_langs = []
    for canonical, aliases in COMMON_LANGUAGES.items():
        if any(alias in job_full_text for alias in aliases):
            # Check context: require/fluent/bilingual/anglais requis/etc.
            if any(req_w in job_full_text for req_w in ["fluent", "native", "requis", "required", "exigé", "mandatory", "speaking", "parlé", "fließend"]):
                required_canon_langs.append(canonical)

    lang_score = 100
    if required_canon_langs:
        matched_required_langs = []
        missing_required_langs = []
        for req in required_canon_langs:
            if req in user_lang_map:
                prof = user_lang_map[req]
                matched_required_langs.append(f"{req.capitalize()} ({prof})")
            else:
                missing_required_langs.append(req.capitalize())

        if matched_required_langs:
            lang_score = 100 if not missing_required_langs else 60
            positive_factors.append(f"Satisfies language requirement: {', '.join(matched_required_langs)}")
        else:
            lang_score = 30

        if missing_required_langs:
            missing_factors.append(f"Job specifies required language: {', '.join(missing_required_langs)}")
    else:
        # Job has no explicit language requirement
        lang_score = 100
        if user_languages:
            positive_factors.append(f"Multilingual profile ({len(user_languages)} languages recorded)")

    # -------------------------------------------------------------
    # Final Multi-Factor Weighted Aggregation
    # -------------------------------------------------------------
    category_scores = {
        "skills": min(max(skills_score, 0), 100),
        "experience": min(max(exp_score, 0), 100),
        "education": min(max(edu_score, 0), 100),
        "location": min(max(loc_score, 0), 100),
        "languages": min(max(lang_score, 0), 100),
    }

    final_score = int(round(
        category_scores["skills"] * 0.35 +
        category_scores["experience"] * 0.25 +
        category_scores["education"] * 0.15 +
        category_scores["location"] * 0.15 +
        category_scores["languages"] * 0.10
    ))
    final_score = min(max(final_score, 0), 100)

    return JobMatchExplanation(
        job_id=job.id,
        score=final_score,
        positive_factors=positive_factors,
        missing_factors=missing_factors,
        category_scores=category_scores,
    )
