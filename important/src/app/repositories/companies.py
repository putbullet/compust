from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from ..models import Company, Country, ScrapeTarget, Job, ScrapingRun


def list_companies(db: Session, include_inactive: bool = True) -> list[Company]:
    stmt = select(Company).order_by(Company.name)
    if not include_inactive:
        stmt = stmt.where(Company.active.is_(True))
    return list(db.scalars(stmt).all())


def get_company(db: Session, company_id: int) -> Company | None:
    return db.scalar(select(Company).where(Company.id == company_id))


def create_company(
    db: Session,
    name: str,
    website_url: str,
    careers_url: str | None = None,
    active: bool = True,
    country_ids: list[int] | None = None,
) -> Company:
    company = Company(
        name=name.strip(),
        website_url=website_url.strip(),
        careers_url=careers_url.strip() if careers_url else None,
        active=active,
    )
    if country_ids:
        countries = list(db.scalars(select(Country).where(Country.id.in_(country_ids))).all())
        company.countries = countries

    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def update_company(
    db: Session,
    company_id: int,
    name: str | None = None,
    website_url: str | None = None,
    careers_url: str | None = None,
    active: bool | None = None,
    country_ids: list[int] | None = None,
) -> Company | None:
    company = get_company(db, company_id)
    if not company:
        return None

    if name is not None:
        company.name = name.strip()
    if website_url is not None:
        company.website_url = website_url.strip()
    if careers_url is not None:
        company.careers_url = careers_url.strip() if careers_url else None
    if active is not None:
        company.active = active
    if country_ids is not None:
        countries = list(db.scalars(select(Country).where(Country.id.in_(country_ids))).all())
        company.countries = countries

    db.commit()
    db.refresh(company)
    return company


def toggle_company_active(db: Session, company_id: int) -> Company | None:
    company = get_company(db, company_id)
    if not company:
        return None
    company.active = not company.active
    db.commit()
    db.refresh(company)
    return company


def delete_company(db: Session, company_id: int, hard_delete: bool = False) -> bool:
    company = get_company(db, company_id)
    if not company:
        return False

    if not hard_delete:
        # Safe deactivation
        company.active = False
        db.commit()
        return True

    # Hard deletion: explicitly confirm destruction of company, targets, runs, jobs
    # Delete related jobs first
    db.execute(delete(Job).where(Job.company_id == company_id))
    db.execute(delete(ScrapeTarget).where(ScrapeTarget.company_id == company_id))
    db.execute(delete(ScrapingRun).where(ScrapingRun.company_id == company_id))
    company.countries.clear()
    db.delete(company)
    db.commit()
    return True
