from datetime import date
from typing import Any
from ..models import Job, User, UserExperience, UserLanguage
from ..schemas_auth import JobMatchExplanation

COMMON_LANGUAGES: dict[str, list[str]] = {
    "english": ["english", "anglais"],
    "french": ["french", "français", "francais"],
    "arabic": ["arabic", "arabe"],
    "spanish": ["spanish", "espagnol"],
    "german": ["german", "allemand"],
}


def _estimate_experience_months(exp: UserExperience) -> int:
    if not exp.start_date:
        return 6
    end = exp.end_date or date.today()
    months = (end.year - exp.start_date.year) * 12 + (end.month - exp.start_date.month)
    return max(months, 1)


def calculate_job_match(
    job: Job,
    job_skills: list[str],
    user: User,
) -> JobMatchExplanation:
    """Compute an explainable, multi-dimensional match score (0-100%) and factor breakdown

    comparing a job against a user's profile:
    - Skills (up to 40 points)
    - Preferences (work mode, location, salary - up to 30 points)
    - Experience tenure & relevance with type distinction (up to 15 points)
    - Language proficiency alignment (up to 15 points)
    """
    score = 0
    positive_factors: list[str] = []
    missing_factors: list[str] = []

    user_skills_set = {s.skill.lower().strip() for s in user.skills} if user.skills else set()
    job_skills_set = {s.lower().strip() for s in job_skills}

    # 1. Skill Matching (up to 40 points)
    if job_skills_set:
        matched_skills = user_skills_set.intersection(job_skills_set)
        if matched_skills:
            ratio = len(matched_skills) / len(job_skills_set)
            points = int(ratio * 40)
            score += max(points, 10)
            positive_factors.append(f"Matched skills: {', '.join(sorted(matched_skills))}")
        unmatched = job_skills_set.difference(user_skills_set)
        if unmatched:
            missing_factors.append(f"Missing job skills: {', '.join(sorted(list(unmatched)[:3]))}")
    elif user_skills_set:
        # Fallback keyword match in description/title
        desc = (job.description or "") + " " + (job.title or "")
        desc_lower = desc.lower()
        found = [s for s in user_skills_set if s in desc_lower]
        if found:
            score += min(len(found) * 10, 35)
            positive_factors.append(f"Relevant skills in description: {', '.join(found[:3])}")
    else:
        # Baseline score if no skills declared yet
        score += 15

    # 2. Preferences Matching (up to 30 points: 10 work mode + 10 location + 10 salary)
    prefs = user.preferences
    if prefs:
        # Work mode
        if prefs.preferred_work_mode:
            pref_mode = prefs.preferred_work_mode.lower()
            job_mode = (job.remote_type or "").lower()
            if pref_mode in job_mode or job_mode in pref_mode:
                score += 10
                positive_factors.append(f"Matches work mode preference: {prefs.preferred_work_mode}")
            elif job.remote_type:
                missing_factors.append(f"Job is {job.remote_type} while you prefer {prefs.preferred_work_mode}")
        else:
            score += 5

        # Location
        if prefs.preferred_location:
            pref_loc = prefs.preferred_location.lower()
            job_loc = (job.location or "").lower()
            if pref_loc in job_loc or job_loc in pref_loc:
                score += 10
                positive_factors.append(f"Matches location: {prefs.preferred_location}")
            elif job.location:
                missing_factors.append(f"Located in {job.location} (preferred: {prefs.preferred_location})")
        else:
            score += 5

        # Salary
        if prefs.min_salary is not None and job.salary_min is not None:
            if float(job.salary_min) >= float(prefs.min_salary):
                score += 10
                positive_factors.append("Salary satisfies or exceeds minimum requirement")
            else:
                missing_factors.append("Job starting salary is below your preferred minimum")
        else:
            score += 5
    else:
        score += 15

    # 3. Experience Matching with Type Distinction (up to 15 points)
    user_experiences = getattr(user, "experience", []) or []
    if user_experiences:
        prof_exps = [e for e in user_experiences if (e.experience_type or "professional") == "professional"]
        intern_exps = [e for e in user_experiences if e.experience_type == "internship"]
        project_exps = [e for e in user_experiences if e.experience_type == "project"]
        transferable_exps = [e for e in user_experiences if e.experience_type == "transferable"]

        job_title_lower = (job.title or "").lower()
        is_senior_role = any(w in job_title_lower for w in ["senior", "lead", "principal", "head", "director"])
        is_junior_role = any(w in job_title_lower for w in ["intern", "stage", "junior", "entry"])

        exp_points = 0
        if prof_exps:
            prof_months = sum(_estimate_experience_months(e) for e in prof_exps)
            prof_years = round(prof_months / 12, 1)

            # Check for title keyword relevance
            relevant_roles = [
                e.title for e in prof_exps
                if any(kw in e.title.lower() for kw in job_title_lower.split() if len(kw) > 3)
            ]
            if relevant_roles:
                positive_factors.append(f"Direct professional experience in role: {relevant_roles[0]}")
                exp_points += 8
            else:
                exp_points += 5

            if is_senior_role:
                if prof_months >= 36:
                    exp_points += 7
                    positive_factors.append(f"Meets seniority requirement ({prof_years} yrs professional tenure)")
                else:
                    missing_factors.append(f"Senior role typically requires 3+ yrs of full-time professional experience ({prof_years} yrs recorded)")
            elif is_junior_role:
                exp_points += 5
            else:
                exp_points += min(int(prof_years * 2), 7)
        elif intern_exps or project_exps:
            # Candidate has internship/project experience without full-time professional
            if is_junior_role:
                exp_points += 12
                positive_factors.append("Internship / project portfolio strongly aligns with entry-level position")
            elif is_senior_role:
                exp_points += 2
                missing_factors.append("Senior roles require substantive professional career tenure beyond internships/projects")
            else:
                exp_points += 6
                positive_factors.append("Internship and project experience demonstrates domain familiarity")
        elif transferable_exps:
            exp_points += 5
            positive_factors.append("Transferable experience provides valuable cross-functional background")

        score += min(exp_points, 15)
    else:
        # Neutral baseline points for unconfigured experience
        score += 8

    # 4. Language Proficiency Alignment (up to 15 points)
    user_languages = getattr(user, "languages", []) or []
    job_text = ((job.description or "") + " " + (job.title or "")).lower()

    if user_languages:
        lang_points = 0
        user_lang_map = {l.language.lower().strip(): (l.proficiency or "fluent").lower() for l in user_languages}

        # Check detected language requirements in job posting
        matched_required_langs = []
        for canonical, aliases in COMMON_LANGUAGES.items():
            if any(alias in job_text for alias in aliases):
                if canonical in user_lang_map:
                    prof = user_lang_map[canonical]
                    matched_required_langs.append(f"{canonical.capitalize()} ({prof})")
                    if prof in ["native", "fluent"]:
                        lang_points += 8
                    else:
                        lang_points += 4

        if matched_required_langs:
            positive_factors.append(f"Satisfies language requirement: {', '.join(matched_required_langs)}")
        else:
            # Baseline profile strength for multilingual candidates
            lang_points += min(len(user_languages) * 4, 10)
            positive_factors.append(f"Multilingual profile ({len(user_languages)} languages recorded)")

        score += min(lang_points, 15)
    else:
        # Neutral baseline points for unconfigured languages
        score += 7

    final_score = min(max(score, 0), 100)
    return JobMatchExplanation(
        job_id=job.id,
        score=final_score,
        positive_factors=positive_factors,
        missing_factors=missing_factors,
    )
