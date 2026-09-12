from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Country


def list_countries(db: Session) -> list[Country]:
    return list(db.scalars(select(Country).order_by(Country.name)).all())


def get_country_by_code(db: Session, code: str) -> Country | None:
    return db.scalar(select(Country).where(Country.code == code.upper()))


def get_country_by_name_or_code(db: Session, identifier: str) -> Country | None:
    if not identifier or not identifier.strip():
        return None
    clean = identifier.strip()
    return db.scalar(
        select(Country).where(
            (Country.name.ilike(clean)) | (Country.code.ilike(clean))
        )
    )


def resolve_country_by_location(db: Session, location: str | None) -> Country | None:
    """
    Given a free-text location (e.g. 'Berlin, Germany', 'London, UK', 'New York, US'),
    extracts the country hint and matches against the database countries table.
    """
    if not location or not location.strip():
        return None
    from ..scraper.vocabulary import normalize_location
    parsed = normalize_location(location)
    country_name = parsed.get("country") if isinstance(parsed, dict) else getattr(parsed, "country", None)
    if country_name:
        country = get_country_by_name_or_code(db, country_name)
        if country:
            return country
    return None
