from datetime import datetime, timezone
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import Job, User, UserApplication
from ..schemas_applications import ApplicationCreate, ApplicationUpdate


def save_or_update_application(
    db: Session,
    user: User,
    job_id: int,
    data: ApplicationCreate,
) -> UserApplication:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    existing = db.scalar(
        select(UserApplication).where(
            UserApplication.user_id == user.id,
            UserApplication.job_id == job_id,
        )
    )

    if existing:
        existing.status = data.status
        if data.notes is not None:
            existing.notes = data.notes
        if data.status == "applied" and not existing.applied_at:
            existing.applied_at = now
        existing.updated_at = now
        db.commit()
        db.refresh(existing)
        return existing

    applied_at = now if data.status == "applied" else None
    app = UserApplication(
        user_id=user.id,
        job_id=job_id,
        status=data.status,
        notes=data.notes,
        applied_at=applied_at,
        created_at=now,
        updated_at=now,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


def get_user_applications(
    db: Session,
    user_id: int,
    status: str | None = None,
) -> list[UserApplication]:
    query = select(UserApplication).where(UserApplication.user_id == user_id)
    if status:
        query = query.where(UserApplication.status == status)
    query = query.order_by(UserApplication.updated_at.desc())
    return list(db.scalars(query).all())


def get_application(
    db: Session,
    user_id: int,
    application_id: int,
) -> UserApplication | None:
    return db.scalar(
        select(UserApplication).where(
            UserApplication.id == application_id,
            UserApplication.user_id == user_id,
        )
    )


def update_application(
    db: Session,
    user: User,
    application_id: int,
    data: ApplicationUpdate,
) -> UserApplication | None:
    app = get_application(db, user.id, application_id)
    if not app:
        return None

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if data.status is not None:
        app.status = data.status
        if data.status == "applied" and not app.applied_at:
            app.applied_at = now
    if data.notes is not None:
        app.notes = data.notes
    if data.applied_at is not None:
        app.applied_at = data.applied_at

    app.updated_at = now
    db.commit()
    db.refresh(app)
    return app


def delete_application(db: Session, user: User, application_id: int) -> bool:
    res = db.execute(
        delete(UserApplication).where(
            UserApplication.id == application_id,
            UserApplication.user_id == user.id,
        )
    )
    db.commit()
    return res.rowcount > 0


def delete_application_by_job_id(db: Session, user: User, job_id: int) -> bool:
    res = db.execute(
        delete(UserApplication).where(
            UserApplication.job_id == job_id,
            UserApplication.user_id == user.id,
        )
    )
    db.commit()
    return res.rowcount > 0
