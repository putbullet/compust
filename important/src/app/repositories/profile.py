from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import User, UserEducation, UserExperience, UserLanguage
from ..schemas_profile import (
    UserEducationCreate,
    UserExperienceCreate,
    UserLanguageCreate,
)


def add_experience(
    db: Session,
    user: User,
    data: UserExperienceCreate,
) -> UserExperience:
    exp = UserExperience(
        user_id=user.id,
        title=data.title.strip(),
        company_name=data.company_name.strip(),
        experience_type=data.experience_type,
        start_date=data.start_date,
        end_date=data.end_date,
        description=data.description.strip() if data.description else None,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp


def delete_experience(db: Session, user: User, experience_id: int) -> bool:
    res = db.execute(
        delete(UserExperience).where(
            UserExperience.id == experience_id,
            UserExperience.user_id == user.id,
        )
    )
    db.commit()
    return res.rowcount > 0


def add_education(
    db: Session,
    user: User,
    data: UserEducationCreate,
) -> UserEducation:
    edu = UserEducation(
        user_id=user.id,
        institution=data.institution.strip(),
        degree=data.degree.strip() if data.degree else None,
        field_of_study=data.field_of_study.strip() if data.field_of_study else None,
        start_date=data.start_date,
        end_date=data.end_date,
        description=data.description.strip() if data.description else None,
    )
    db.add(edu)
    db.commit()
    db.refresh(edu)
    return edu


def delete_education(db: Session, user: User, education_id: int) -> bool:
    res = db.execute(
        delete(UserEducation).where(
            UserEducation.id == education_id,
            UserEducation.user_id == user.id,
        )
    )
    db.commit()
    return res.rowcount > 0


def add_language(
    db: Session,
    user: User,
    data: UserLanguageCreate,
) -> UserLanguage:
    # Check if language already exists for user; if so, update proficiency
    existing = db.scalar(
        select(UserLanguage).where(
            UserLanguage.user_id == user.id,
            UserLanguage.language == data.language.strip().lower(),
        )
    )
    if existing:
        existing.proficiency = data.proficiency
        db.commit()
        db.refresh(existing)
        return existing

    lang = UserLanguage(
        user_id=user.id,
        language=data.language.strip().lower(),
        proficiency=data.proficiency,
    )
    db.add(lang)
    db.commit()
    db.refresh(lang)
    return lang


def delete_language(db: Session, user: User, language_id: int) -> bool:
    res = db.execute(
        delete(UserLanguage).where(
            UserLanguage.id == language_id,
            UserLanguage.user_id == user.id,
        )
    )
    db.commit()
    return res.rowcount > 0
