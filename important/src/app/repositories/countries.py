from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Country


def list_countries(db: Session) -> list[Country]:
    return list(db.scalars(select(Country).order_by(Country.name)).all())


def get_country_by_code(db: Session, code: str) -> Country | None:
    return db.scalar(select(Country).where(Country.code == code.upper()))
