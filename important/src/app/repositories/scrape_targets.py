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
