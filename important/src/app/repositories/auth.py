from datetime import datetime, timezone
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import User, UserPreference, UserSkill
from ..schemas_auth import (
    UserPreferencesUpdate,
    UserProfileResponse,
    UserRegisterRequest,
    UserPreferenceSchema,
)
from ..security import hash_password, verify_password


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def create_user(db: Session, data: UserRegisterRequest) -> User:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    hashed_pwd = hash_password(data.password)

    user = User(
        email=data.email.strip().lower(),
        password_hash=hashed_pwd,
        first_name=data.first_name.strip() if data.first_name else None,
        last_name=data.last_name.strip() if data.last_name else None,
        email_verified=False,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.flush()

    # Create empty preferences
    prefs = UserPreference(
        user_id=user.id,
        preferred_job_type=None,
        preferred_work_mode=None,
        preferred_location=None,
        min_salary=None,
        max_salary=None,
        salary_currency="MAD",
    )
    db.add(prefs)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


def update_user_preferences(
    db: Session,
    user: User,
    data: UserPreferencesUpdate,
) -> UserPreference:
    prefs = user.preferences
    if not prefs:
        prefs = UserPreference(user_id=user.id)
        db.add(prefs)
        db.flush()

    if data.preferred_job_type is not None:
        prefs.preferred_job_type = data.preferred_job_type
    if data.preferred_work_mode is not None:
        prefs.preferred_work_mode = data.preferred_work_mode
    if data.preferred_location is not None:
        prefs.preferred_location = data.preferred_location
    if data.min_salary is not None:
        prefs.min_salary = data.min_salary
    if data.max_salary is not None:
        prefs.max_salary = data.max_salary
    if data.salary_currency is not None:
        prefs.salary_currency = data.salary_currency

    db.commit()
    db.refresh(prefs)
    return prefs


def set_user_skills(db: Session, user: User, skills: list[str]) -> list[str]:
    clean_skills = [s.strip() for s in skills if s.strip()]
    clean_skills = list(dict.fromkeys(clean_skills))

    db.execute(delete(UserSkill).where(UserSkill.user_id == user.id))
    db.add_all([UserSkill(user_id=user.id, skill=s) for s in clean_skills])
    db.commit()
    return clean_skills


from ..models import Country
from ..schemas import CountryRead
from ..schemas_profile import (
    UserEducationRead,
    UserExperienceRead,
    UserLanguageRead,
)


def set_user_country_preferences(
    db: Session,
    user: User,
    country_ids: list[int],
) -> list[Country]:
    if not country_ids:
        user.country_preferences = []
    else:
        countries = list(db.scalars(select(Country).where(Country.id.in_(country_ids))).all())
        user.country_preferences = countries
    db.commit()
    db.refresh(user)
    return user.country_preferences


def build_user_profile(user: User) -> UserProfileResponse:
    skills = [s.skill for s in user.skills] if user.skills else []
    prefs_schema = (
        UserPreferenceSchema.model_validate(user.preferences)
        if user.preferences
        else None
    )
    experience = (
        [UserExperienceRead.model_validate(e) for e in user.experience]
        if user.experience
        else []
    )
    education = (
        [UserEducationRead.model_validate(ed) for ed in user.education]
        if user.education
        else []
    )
    languages = (
        [UserLanguageRead.model_validate(l) for l in user.languages]
        if user.languages
        else []
    )
    country_preferences = (
        [CountryRead.model_validate(c) for c in user.country_preferences]
        if user.country_preferences
        else []
    )
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        email_verified=user.email_verified,
        preferences=prefs_schema,
        skills=skills,
        experience=experience,
        education=education,
        languages=languages,
        country_preferences=country_preferences,
    )
