from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ScrapeTarget


def list_scrape_targets(
    db: Session,
    company_id: int | None = None,
) -> list[ScrapeTarget]:
    statement = select(ScrapeTarget).order_by(ScrapeTarget.id)
    if company_id is not None:
        statement = statement.where(ScrapeTarget.company_id == company_id)
    return list(db.scalars(statement).all())


def get_scrape_target(db: Session, target_id: int) -> ScrapeTarget | None:
    return db.scalar(select(ScrapeTarget).where(ScrapeTarget.id == target_id))


def create_scrape_target(
    db: Session,
    company_id: int,
    url: str,
    target_type: str | None = "generic_html",
    active: bool = True,
) -> ScrapeTarget:
    target = ScrapeTarget(
        company_id=company_id,
        url=url.strip(),
        type=target_type.strip() if target_type else "generic_html",
        active=active,
        status="pending",
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


def update_scrape_target(
    db: Session,
    target_id: int,
    url: str | None = None,
    target_type: str | None = None,
    active: bool | None = None,
) -> ScrapeTarget | None:
    target = get_scrape_target(db, target_id)
    if not target:
        return None

    if url is not None:
        target.url = url.strip()
    if target_type is not None:
        target.type = target_type.strip()
    if active is not None:
        target.active = active

    db.commit()
    db.refresh(target)
    return target


def toggle_scrape_target_active(db: Session, target_id: int) -> ScrapeTarget | None:
    target = get_scrape_target(db, target_id)
    if not target:
        return None
    target.active = not target.active
    db.commit()
    db.refresh(target)
    return target


def delete_scrape_target(db: Session, target_id: int) -> bool:
    target = get_scrape_target(db, target_id)
    if not target:
        return False
    db.delete(target)
    db.commit()
    return True
