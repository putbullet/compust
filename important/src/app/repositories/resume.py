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

    resume = Resume(
        user_id=user_id,
        title=title,
        filename=f"{title.lower().replace(' ', '_')}.json",
        raw_text="",
        parsed_sections=None,
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
    return db.scalar(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    )


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


# --- Backwards Compatibility Helpers ---

def save_resume(
    db: Session,
    user_id: int,
    filename: str,
    raw_text: str,
    parsed_sections: dict,
) -> Resume:
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
        if parsed_sections.get("skills"):
            structured_data["skills"] = [
                {"id": str(uuid.uuid4())[:8], "name": s, "category": "General", "proficiency": "Intermediate"}
                for s in parsed_sections["skills"] if s
            ]

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
    return resume


def list_user_resumes(db: Session, user_id: int) -> list[Resume]:
    return list_user_structured_resumes(db, user_id)


def set_active_resume(db: Session, user_id: int, resume_id: int) -> Resume | None:
    return set_default_structured_resume(db, user_id, resume_id)


def delete_resume(db: Session, user_id: int, resume_id: int) -> bool:
    return delete_structured_resume(db, user_id, resume_id)
