from datetime import datetime, timezone
import uuid
from typing import Any
from sqlalchemy import select, update, desc
from sqlalchemy.orm import Session

from ..models import Resume, User, UserSkill, UserExperience, UserEducation, UserLanguage


DEFAULT_SETTINGS = {
    "template": "modern",
    "theme_color": "#2563eb",
    "font_family": "Inter",
    "font_size": "10.5",
    "document_size": "A4",
    "section_order": [
        "summary",
        "experience",
        "education",
        "skills",
        "projects",
        "certifications",
        "languages",
        "custom_sections",
    ],
    "section_visibility": {
        "profile": True,
        "summary": True,
        "experience": True,
        "education": True,
        "skills": True,
        "projects": True,
        "certifications": True,
        "languages": True,
        "custom_sections": True,
    },
}


def build_default_structured_data(user: User | None = None) -> dict[str, Any]:
    full_name = ""
    email = ""
    phone = ""
    location = ""
    if user:
        name_parts = [p for p in [user.first_name, user.last_name] if p]
        full_name = " ".join(name_parts) if name_parts else (user.email.split("@")[0].title() if user.email else "")
        email = user.email or ""
        phone = user.phone or ""
        if user.preferences and user.preferences.preferred_location:
            location = user.preferences.preferred_location

    return {
        "profile": {
            "full_name": full_name,
            "headline": "Software Engineer",
            "email": email,
            "phone": phone,
            "location": location,
            "website": "",
            "github": "",
            "linkedin": "",
            "summary": "Results-driven professional with a proven track record in software engineering, system architecture, and building robust, maintainable solutions.",
        },
        "experience": [],
        "education": [],
        "skills": [],
        "projects": [],
        "certifications": [],
        "languages": [],
        "custom_sections": [],
    }


def build_parsed_sections_from_structured_data(data: dict[str, Any] | None) -> dict[str, Any]:
    """Derive canonical parsed_sections dictionary from structured resume data."""
    if not data:
        return {
            "summary": "",
            "experience": "",
            "education": "",
            "skills": [],
            "skills_raw": "",
            "projects": "",
            "certifications": "",
            "languages": [],
        }

    profile = data.get("profile") or {}
    summary = profile.get("summary") or ""

    # Skills: extract names
    skills_raw_list = data.get("skills") or []
    skills: list[str] = []
    for s in skills_raw_list:
        if isinstance(s, dict) and s.get("name"):
            name = s["name"].strip()
            if name and name not in skills:
                skills.append(name)
        elif isinstance(s, str) and s.strip():
            name = s.strip()
            if name not in skills:
                skills.append(name)

    # Languages: extract language names or formatted with proficiency
    languages_raw_list = data.get("languages") or []
    languages: list[str] = []
    for l in languages_raw_list:
        if isinstance(l, dict) and l.get("language"):
            lang = l["language"].strip()
            prof = (l.get("proficiency") or "").strip()
            entry = f"{lang} ({prof})" if prof else lang
            if entry not in languages:
                languages.append(entry)
        elif isinstance(l, str) and l.strip():
            lang = l.strip()
            if lang not in languages:
                languages.append(lang)

    # Experience: format into string
    experience_list = data.get("experience") or []
    exp_parts: list[str] = []
    for exp in experience_list:
        if not isinstance(exp, dict):
            continue
        company = exp.get("company") or ""
        title = exp.get("title") or ""
        start = exp.get("start_date") or ""
        end = exp.get("end_date") or ""
        desc = exp.get("description") or ""
        highlights = exp.get("highlights") or []
        header = f"{title} at {company}".strip(" at ")
        date_str = f" ({start} - {end})" if start or end else ""
        body = desc
        if highlights:
            bullet_str = "\n".join(f"- {h}" for h in highlights if h)
            body = f"{body}\n{bullet_str}".strip() if body else bullet_str
        exp_parts.append(f"{header}{date_str}\n{body}".strip())
    experience_text = "\n\n".join(p for p in exp_parts if p)

    # Education: format into string
    education_list = data.get("education") or []
    edu_parts: list[str] = []
    for edu in education_list:
        if not isinstance(edu, dict):
            continue
        inst = edu.get("institution") or ""
        degree = edu.get("degree") or ""
        field = edu.get("field_of_study") or ""
        start = edu.get("start_date") or ""
        end = edu.get("end_date") or ""
        deg_str = f"{degree} in {field}".strip(" in ") if field else degree
        header = f"{deg_str} at {inst}".strip(" at ")
        date_str = f" ({start} - {end})" if start or end else ""
        edu_parts.append(f"{header}{date_str}".strip())
    education_text = "\n\n".join(p for p in edu_parts if p)

    # Projects
    projects_list = data.get("projects") or []
    proj_parts: list[str] = []
    for proj in projects_list:
        if not isinstance(proj, dict):
            continue
        name = proj.get("name") or ""
        role = proj.get("role") or ""
        desc = proj.get("description") or ""
        tools = ", ".join(proj.get("technologies") or [])
        proj_header = f"{name} ({role})" if role else name
        extra = f"Technologies: {tools}" if tools else ""
        proj_parts.append(f"{proj_header}\n{desc}\n{extra}".strip())
    projects_text = "\n\n".join(p for p in proj_parts if p)

    # Certifications
    certs_list = data.get("certifications") or []
    cert_parts: list[str] = []
    for c in certs_list:
        if not isinstance(c, dict):
            continue
        name = c.get("name") or ""
        issuer = c.get("issuer") or ""
        date = c.get("issue_date") or ""
        line = f"{name} - {issuer}".strip(" - ")
        if date:
            line += f" ({date})"
        cert_parts.append(line)
    cert_text = "\n".join(cert_parts)

    return {
        "summary": summary,
        "experience": experience_text,
        "education": education_text,
        "skills": skills,
        "skills_raw": ", ".join(skills),
        "projects": projects_text,
        "certifications": cert_text,
        "languages": languages,
    }


def build_raw_text_from_structured_data(data: dict[str, Any] | None) -> str:
    """Generate plain text search layer from structured resume data."""
    if not data:
        return ""
    parsed = build_parsed_sections_from_structured_data(data)
    profile = data.get("profile") or {}
    name = profile.get("full_name") or ""
    email = profile.get("email") or ""
    phone = profile.get("phone") or ""
    location = profile.get("location") or ""
    headline = profile.get("headline") or ""

    lines = [
        name,
        headline,
        f"{email} | {phone} | {location}".strip(" |"),
        parsed.get("summary", ""),
        "Experience:",
        parsed.get("experience", ""),
        "Education:",
        parsed.get("education", ""),
        "Skills:",
        parsed.get("skills_raw", ""),
        "Projects:",
        parsed.get("projects", ""),
        "Certifications:",
        parsed.get("certifications", ""),
        "Languages:",
        ", ".join(parsed.get("languages", [])),
    ]
    return "\n\n".join(line for line in lines if line.strip())


def get_canonical_resume_sections(resume: Resume) -> dict[str, Any]:
    """Return canonical sections dict, synthesizing from structured_data or raw_text if needed."""
    parsed = dict(resume.parsed_sections or {})
    structured = resume.structured_data or {}

    # If parsed_sections lacks essential sections, derive from structured_data
    if structured and (not parsed or not parsed.get("skills") or not parsed.get("experience")):
        derived = build_parsed_sections_from_structured_data(structured)
        for k, v in derived.items():
            if not parsed.get(k):
                parsed[k] = v

    # If skills are still missing, try raw_text parsing
    if not parsed.get("skills") and resume.raw_text:
        from ..services.resume_parser import structure_resume_text
        raw_parsed = structure_resume_text(resume.raw_text)
        if raw_parsed.get("skills"):
            parsed["skills"] = raw_parsed["skills"]
        if not parsed.get("languages") and raw_parsed.get("languages"):
            parsed["languages"] = raw_parsed["languages"]

    return parsed


def extract_canonical_skills_map(
    resume: Resume | None,
    user: User | None = None,
) -> tuple[set[str], dict[str, str], list[str]]:
    """Single source of truth for extracting canonical candidate skills.

    Returns:
      (canonical_skills_set, canonical_to_display_map, raw_skills_list)
    """
    import unicodedata
    from ..scraper.vocabulary import SKILL_SYNONYMS

    def _canonical(s: str) -> str:
        cleaned = s.strip().lower()
        unacc = unicodedata.normalize("NFKD", cleaned).encode("ASCII", "ignore").decode("utf-8")
        if cleaned in SKILL_SYNONYMS:
            return SKILL_SYNONYMS[cleaned].lower()
        if unacc in SKILL_SYNONYMS:
            return SKILL_SYNONYMS[unacc].lower()
        return unacc

    raw_skills: list[str] = []
    seen_raw = set()

    def _add_raw(name: str):
        cleaned = name.strip()
        if cleaned and cleaned.lower() not in seen_raw:
            seen_raw.add(cleaned.lower())
            raw_skills.append(cleaned)

    # 1. From active resume parsed_sections
    if resume:
        sections = resume.parsed_sections or {}
        for s in sections.get("skills") or []:
            if isinstance(s, str):
                _add_raw(s)
            elif isinstance(s, dict) and (s.get("name") or s.get("skill")):
                _add_raw(s.get("name") or s.get("skill"))

        # 2. From resume structured_data
        sdata = resume.structured_data or {}
        for s in sdata.get("skills") or []:
            if isinstance(s, str):
                _add_raw(s)
            elif isinstance(s, dict) and (s.get("name") or s.get("skill")):
                _add_raw(s.get("name") or s.get("skill"))

        # 3. If raw text fallback needed
        if not raw_skills and resume.raw_text:
            from ..services.resume_parser import structure_resume_text
            for s in structure_resume_text(resume.raw_text).get("skills", []):
                _add_raw(s)

    # 4. From user profile skills
    effective_user = user or (getattr(resume, "user", None) if resume else None)
    if effective_user and getattr(effective_user, "skills", None):
        for us in effective_user.skills:
            if getattr(us, "skill", None):
                _add_raw(us.skill)

    canonical_set: set[str] = set()
    display_map: dict[str, str] = {}
    for r in raw_skills:
        c = _canonical(r)
        if c:
            canonical_set.add(c)
            if c not in display_map:
                display_map[c] = r

    return canonical_set, display_map, raw_skills


def get_canonical_resume_skills(
    resume: Resume | None,
    user: User | None = None,
) -> list[str]:
    """Return deduplicated list of candidate skill display names."""
    _, _, raw_skills = extract_canonical_skills_map(resume, user)
    return raw_skills


def get_canonical_resume_languages(
    resume: Resume | None,
    user: User | None = None,
) -> list[str]:
    """Return deduplicated list of candidate language names."""
    languages: list[str] = []
    seen = set()

    def _add_lang(name: str):
        cleaned = name.strip()
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            languages.append(cleaned)

    if resume:
        sections = resume.parsed_sections or {}
        for l in sections.get("languages") or []:
            if isinstance(l, str):
                _add_lang(l)
            elif isinstance(l, dict) and l.get("language"):
                _add_lang(l.get("language"))

        sdata = resume.structured_data or {}
        for l in sdata.get("languages") or []:
            if isinstance(l, str):
                _add_lang(l)
            elif isinstance(l, dict) and l.get("language"):
                _add_lang(l.get("language"))

    return languages




def import_profile_into_structured_data(
    db: Session,
    user_id: int,
    existing_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        return existing_data or build_default_structured_data()

    import copy
    data = copy.deepcopy(existing_data) if existing_data else build_default_structured_data(user)
    profile = data.get("profile", {})
    if not profile.get("full_name"):
        name_parts = [p for p in [user.first_name, user.last_name] if p]
        profile["full_name"] = " ".join(name_parts) if name_parts else user.email.split("@")[0].title()
    if not profile.get("email"):
        profile["email"] = user.email or ""
    if not profile.get("phone") and user.phone:
        profile["phone"] = user.phone
    if not profile.get("location") and user.preferences and user.preferences.preferred_location:
        profile["location"] = user.preferences.preferred_location
    data["profile"] = profile

    # Import skills from profile if not already in resume
    existing_skill_names = {s.get("name", "").lower() for s in data.get("skills", [])}
    user_skills = list(db.scalars(select(UserSkill).where(UserSkill.user_id == user_id)).all())
    for us in user_skills:
        if us.skill and us.skill.lower() not in existing_skill_names:
            data.setdefault("skills", []).append({
                "id": str(uuid.uuid4())[:8],
                "name": us.skill,
                "category": "Core & Technical",
                "proficiency": us.proficiency or "Intermediate",
            })
            existing_skill_names.add(us.skill.lower())

    # Import experience
    existing_exp_companies = {e.get("company", "").lower() for e in data.get("experience", [])}
    user_experience = list(db.scalars(select(UserExperience).where(UserExperience.user_id == user_id)).all())
    for exp in user_experience:
        if exp.company_name and exp.company_name.lower() not in existing_exp_companies:
            start_d = exp.start_date.isoformat() if exp.start_date else ""
            end_d = exp.end_date.isoformat() if exp.end_date else ("Present" if start_d else "")
            data.setdefault("experience", []).append({
                "id": str(uuid.uuid4())[:8],
                "company": exp.company_name,
                "title": exp.title,
                "location": "",
                "employment_type": exp.experience_type or "full_time",
                "start_date": start_d,
                "end_date": end_d,
                "is_current": exp.end_date is None,
                "description": exp.description or "",
                "highlights": [line.strip("-•* ") for line in (exp.description or "").splitlines() if line.strip()][:3],
            })
            existing_exp_companies.add(exp.company_name.lower())

    # Import education
    existing_edu_inst = {e.get("institution", "").lower() for e in data.get("education", [])}
    user_education = list(db.scalars(select(UserEducation).where(UserEducation.user_id == user_id)).all())
    for edu in user_education:
        if edu.institution and edu.institution.lower() not in existing_edu_inst:
            data.setdefault("education", []).append({
                "id": str(uuid.uuid4())[:8],
                "institution": edu.institution,
                "degree": edu.degree or "",
                "field": edu.field_of_study or "",
                "location": "",
                "start_date": edu.start_date.isoformat() if edu.start_date else "",
                "end_date": edu.end_date.isoformat() if edu.end_date else "",
                "gpa": "",
                "description": edu.description or "",
            })
            existing_edu_inst.add(edu.institution.lower())

    # Import languages
    existing_langs = {l.get("language", "").lower() for l in data.get("languages", [])}
    user_languages = list(db.scalars(select(UserLanguage).where(UserLanguage.user_id == user_id)).all())
    for lang in user_languages:
        if lang.language and lang.language.lower() not in existing_langs:
            data.setdefault("languages", []).append({
                "id": str(uuid.uuid4())[:8],
                "language": lang.language,
                "proficiency": lang.proficiency or "Fluent",
            })
            existing_langs.add(lang.language.lower())

    return data


# --- Structured Resume Operations ---

def create_structured_resume(
    db: Session,
    user_id: int,
    title: str = "My Resume",
    is_default: bool = False,
    structured_data: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
    target_job_id: int | None = None,
    source_resume_id: int | None = None,
) -> Resume:
    now = datetime.now(timezone.utc)
    user = db.scalar(select(User).where(User.id == user_id))

    # If first resume or requested is_default, clear other default flags
    count = db.scalar(select(Resume.id).where(Resume.user_id == user_id).limit(1))
    if count is None or is_default:
        is_default = True
        db.execute(
            update(Resume)
            .where(Resume.user_id == user_id)
            .values(is_default=False, updated_at=now)
        )

    final_structured_data = structured_data or build_default_structured_data(user)
    final_settings = settings or DEFAULT_SETTINGS.copy()
    parsed_sections = build_parsed_sections_from_structured_data(final_structured_data)
    raw_text = build_raw_text_from_structured_data(final_structured_data)

    resume = Resume(
        user_id=user_id,
        title=title,
        filename=f"{title.lower().replace(' ', '_')}.json",
        raw_text=raw_text,
        parsed_sections=parsed_sections,
        structured_data=final_structured_data,
        settings=final_settings,
        is_active=True,
        is_default=is_default,
        target_job_id=target_job_id,
        source_resume_id=source_resume_id,
        created_at=now,
        updated_at=now,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def get_user_resume(db: Session, user_id: int, resume_id: int) -> Resume | None:
    resume = db.scalar(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    )
    if resume and resume.structured_data and (not resume.parsed_sections or not resume.parsed_sections.get("skills")):
        resume.parsed_sections = build_parsed_sections_from_structured_data(resume.structured_data)
        resume.raw_text = build_raw_text_from_structured_data(resume.structured_data)
        db.commit()
    return resume


def list_user_structured_resumes(db: Session, user_id: int) -> list[Resume]:
    return list(
        db.scalars(
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(desc(Resume.is_default), desc(Resume.updated_at))
        ).all()
    )


def update_structured_resume(
    db: Session,
    user_id: int,
    resume_id: int,
    title: str | None = None,
    is_default: bool | None = None,
    structured_data: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
) -> Resume | None:
    now = datetime.now(timezone.utc)
    resume = get_user_resume(db, user_id, resume_id)
    if not resume:
        return None

    if is_default:
        db.execute(
            update(Resume)
            .where(Resume.user_id == user_id)
            .values(is_default=False, updated_at=now)
        )
        resume.is_default = True
    elif is_default is False and resume.is_default:
        # Don't unset default if it's the only resume
        resume.is_default = False

    if title is not None:
        resume.title = title
    if structured_data is not None:
        import copy
        from sqlalchemy.orm.attributes import flag_modified
        resume.structured_data = copy.deepcopy(structured_data)
        flag_modified(resume, "structured_data")
        resume.parsed_sections = build_parsed_sections_from_structured_data(resume.structured_data)
        flag_modified(resume, "parsed_sections")
        resume.raw_text = build_raw_text_from_structured_data(resume.structured_data)
    if settings is not None:
        import copy
        from sqlalchemy.orm.attributes import flag_modified
        resume.settings = copy.deepcopy(settings)
        flag_modified(resume, "settings")

    resume.updated_at = now
    db.commit()
    db.refresh(resume)
    return resume



def duplicate_structured_resume(
    db: Session,
    user_id: int,
    resume_id: int,
    new_title: str | None = None,
) -> Resume | None:
    original = get_user_resume(db, user_id, resume_id)
    if not original:
        return None

    title = new_title or f"{original.title} (Copy)"
    structured_copy = (original.structured_data.copy() if original.structured_data else build_default_structured_data())
    settings_copy = (original.settings.copy() if original.settings else DEFAULT_SETTINGS.copy())

    return create_structured_resume(
        db=db,
        user_id=user_id,
        title=title,
        is_default=False,
        structured_data=structured_copy,
        settings=settings_copy,
        source_resume_id=original.id,
    )


def delete_structured_resume(db: Session, user_id: int, resume_id: int) -> bool:
    resume = get_user_resume(db, user_id, resume_id)
    if not resume:
        return False

    was_default = resume.is_default
    db.delete(resume)
    db.commit()

    if was_default:
        next_resume = db.scalar(
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(desc(Resume.updated_at))
        )
        if next_resume:
            next_resume.is_default = True
            db.commit()

    return True


def set_default_structured_resume(db: Session, user_id: int, resume_id: int) -> Resume | None:
    now = datetime.now(timezone.utc)
    resume = get_user_resume(db, user_id, resume_id)
    if not resume:
        return None

    db.execute(
        update(Resume)
        .where(Resume.user_id == user_id)
        .values(is_default=False, updated_at=now)
    )
    resume.is_default = True
    resume.updated_at = now
    db.commit()
    db.refresh(resume)
    return resume


def create_studio_copy(
    db: Session,
    user_id: int,
    resume_id: int,
    new_title: str | None = None,
) -> Resume | None:
    """Create an editable Studio copy of a resume, preserving original upload untouched."""
    original = get_user_resume(db, user_id, resume_id)
    if not original:
        return None

    import copy
    title = new_title or f"{original.title} (Studio Version)"
    structured_copy = copy.deepcopy(original.structured_data) if original.structured_data else build_default_structured_data()
    settings_copy = copy.deepcopy(original.settings) if original.settings else DEFAULT_SETTINGS.copy()

    return create_structured_resume(
        db=db,
        user_id=user_id,
        title=title,
        is_default=False,
        structured_data=structured_copy,
        settings=settings_copy,
        source_resume_id=original.id,
    )


# --- Backwards Compatibility & Upload Helpers ---

def save_resume(
    db: Session,
    user_id: int,
    filename: str,
    raw_text: str,
    parsed_sections: dict,
) -> Resume:
    """Save an uploaded PDF resume, preserving its original status and extracting all sections into structured data."""
    now = datetime.now(timezone.utc)
    db.execute(
        update(Resume)
        .where(Resume.user_id == user_id)
        .values(is_active=False, updated_at=now)
    )

    user = db.scalar(select(User).where(User.id == user_id))
    structured_data = build_default_structured_data(user)
    if parsed_sections:
        if parsed_sections.get("summary"):
            structured_data["profile"]["summary"] = parsed_sections["summary"]
        
        # B4: Skills are plain keywords, no proficiency levels
        if parsed_sections.get("skills"):
            structured_data["skills"] = [
                {"id": str(uuid.uuid4())[:8], "name": s.strip(), "category": "Core & Technical"}
                for s in parsed_sections["skills"] if s and s.strip()
            ]

        # B1/B3: Map Experience sections so content is never dropped
        if parsed_sections.get("experience"):
            exp_val = parsed_sections["experience"]
            if isinstance(exp_val, list):
                for item in exp_val:
                    if isinstance(item, dict):
                        structured_data["experience"].append({
                            "id": str(uuid.uuid4())[:8],
                            "company": item.get("company", ""),
                            "title": item.get("title", ""),
                            "location": item.get("location", ""),
                            "employment_type": item.get("employment_type", "full_time"),
                            "start_date": item.get("start_date", ""),
                            "end_date": item.get("end_date", ""),
                            "is_current": item.get("is_current", False),
                            "description": item.get("description", ""),
                            "highlights": item.get("highlights", []),
                        })
            elif isinstance(exp_val, str) and exp_val.strip():
                blocks = [b.strip() for b in exp_val.split("\n\n") if b.strip()]
                for b in blocks:
                    lines = b.splitlines()
                    title_line = lines[0].strip() if lines else "Experience"
                    desc_lines = lines[1:] if len(lines) > 1 else []
                    structured_data["experience"].append({
                        "id": str(uuid.uuid4())[:8],
                        "company": "",
                        "title": title_line,
                        "location": "",
                        "employment_type": "full_time",
                        "start_date": "",
                        "end_date": "",
                        "is_current": False,
                        "description": "\n".join(desc_lines).strip() or title_line,
                        "highlights": [l.strip("-•* ") for l in desc_lines if l.strip("-•* ")],
                    })

        # B1/B3: Map Education sections so content is never dropped
        if parsed_sections.get("education"):
            edu_val = parsed_sections["education"]
            if isinstance(edu_val, list):
                for item in edu_val:
                    if isinstance(item, dict):
                        structured_data["education"].append({
                            "id": str(uuid.uuid4())[:8],
                            "institution": item.get("institution", ""),
                            "degree": item.get("degree", ""),
                            "field": item.get("field", item.get("field_of_study", "")),
                            "location": item.get("location", ""),
                            "start_date": item.get("start_date", ""),
                            "end_date": item.get("end_date", ""),
                            "gpa": item.get("gpa", ""),
                            "description": item.get("description", ""),
                        })
            elif isinstance(edu_val, str) and edu_val.strip():
                blocks = [b.strip() for b in edu_val.split("\n\n") if b.strip()]
                for b in blocks:
                    lines = b.splitlines()
                    first_line = lines[0].strip() if lines else "Education"
                    rest = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
                    structured_data["education"].append({
                        "id": str(uuid.uuid4())[:8],
                        "institution": first_line,
                        "degree": "",
                        "field": "",
                        "location": "",
                        "start_date": "",
                        "end_date": "",
                        "gpa": "",
                        "description": rest,
                    })

        # B1/B3: Map Languages so content is never dropped
        if parsed_sections.get("languages"):
            for l in parsed_sections["languages"]:
                if isinstance(l, str) and l.strip():
                    structured_data["languages"].append({
                        "id": str(uuid.uuid4())[:8],
                        "language": l.strip(),
                        "proficiency": "Fluent",
                    })
                elif isinstance(l, dict) and l.get("language"):
                    structured_data["languages"].append({
                        "id": str(uuid.uuid4())[:8],
                        "language": l["language"].strip(),
                        "proficiency": l.get("proficiency", "Fluent"),
                    })

        # B1/B3: Map Projects
        if parsed_sections.get("projects"):
            proj_val = parsed_sections["projects"]
            if isinstance(proj_val, list):
                for item in proj_val:
                    if isinstance(item, dict):
                        structured_data["projects"].append({
                            "id": str(uuid.uuid4())[:8],
                            "name": item.get("name", ""),
                            "description": item.get("description", ""),
                            "technologies": item.get("technologies", ""),
                            "url": item.get("url", ""),
                            "start_date": item.get("start_date", ""),
                            "end_date": item.get("end_date", ""),
                        })
            elif isinstance(proj_val, str) and proj_val.strip():
                for b in [p.strip() for p in proj_val.split("\n\n") if p.strip()]:
                    structured_data["projects"].append({
                        "id": str(uuid.uuid4())[:8],
                        "name": b.splitlines()[0][:80],
                        "description": b,
                        "technologies": "",
                        "url": "",
                        "start_date": "",
                        "end_date": "",
                    })

        # B1/B3: Map Certifications
        if parsed_sections.get("certifications"):
            cert_val = parsed_sections["certifications"]
            if isinstance(cert_val, list):
                for item in cert_val:
                    if isinstance(item, dict):
                        structured_data["certifications"].append({
                            "id": str(uuid.uuid4())[:8],
                            "name": item.get("name", ""),
                            "issuer": item.get("issuer", ""),
                            "issue_date": item.get("issue_date", ""),
                            "expiration_date": item.get("expiration_date", ""),
                            "url": item.get("url", ""),
                        })
            elif isinstance(cert_val, str) and cert_val.strip():
                for line in [c.strip() for c in cert_val.splitlines() if c.strip()]:
                    structured_data["certifications"].append({
                        "id": str(uuid.uuid4())[:8],
                        "name": line,
                        "issuer": "",
                        "issue_date": "",
                        "expiration_date": "",
                        "url": "",
                    })

    title = filename.rsplit(".", 1)[0].replace("_", " ").title() if filename else "Uploaded Resume"

    resume = Resume(
        user_id=user_id,
        title=title,
        filename=filename,
        raw_text=raw_text,
        parsed_sections=parsed_sections,
        structured_data=structured_data,
        settings=DEFAULT_SETTINGS.copy(),
        is_active=True,
        is_default=True,
        is_original_upload=True,
        created_at=now,
        updated_at=now,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def get_active_resume(db: Session, user_id: int) -> Resume | None:
    # Prefer default structured resume; fallback to most recent active
    resume = db.scalar(
        select(Resume)
        .where(Resume.user_id == user_id, Resume.is_default.is_(True))
        .order_by(desc(Resume.updated_at))
    )
    if not resume:
        resume = db.scalar(
            select(Resume)
            .where(Resume.user_id == user_id, Resume.is_active.is_(True))
            .order_by(desc(Resume.updated_at))
        )
    if resume and resume.structured_data and (not resume.parsed_sections or not resume.parsed_sections.get("skills")):
        resume.parsed_sections = build_parsed_sections_from_structured_data(resume.structured_data)
        resume.raw_text = build_raw_text_from_structured_data(resume.structured_data)
        db.commit()
    return resume



def list_user_resumes(db: Session, user_id: int) -> list[Resume]:
    return list_user_structured_resumes(db, user_id)


def set_active_resume(db: Session, user_id: int, resume_id: int) -> Resume | None:
    return set_default_structured_resume(db, user_id, resume_id)


def delete_resume(db: Session, user_id: int, resume_id: int) -> bool:
    return delete_structured_resume(db, user_id, resume_id)
