from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Company


def list_companies(db: Session) -> list[Company]:
    return list(db.scalars(select(Company).order_by(Company.name)).all())


def get_company(db: Session, company_id: int) -> Company | None:
    return db.scalar(select(Company).where(Company.id == company_id))
