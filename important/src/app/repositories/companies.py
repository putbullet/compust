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

    if company.careers_url:
        target = ScrapeTarget(
            company_id=company.id,
            url=company.careers_url,
            type="generic_html",
            active=company.active,
            status="pending",
        )
        db.add(target)
        db.commit()

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

        # Re-evaluate existing jobs under this company based on their location text
        from .countries import resolve_country_by_location
        from ..models import Job
        jobs = list(db.scalars(select(Job).where(Job.company_id == company_id)).all())
        for j in jobs:
            if j.location:
                resolved = resolve_country_by_location(db, j.location)
                if resolved:
                    j.country_id = resolved.id
                elif company.countries and j.country_id not in [c.id for c in company.countries]:
                    j.country_id = company.countries[0].id

    # Synchronize primary scrape target with company careers_url
    if company.careers_url:
        existing_targets = list(db.scalars(select(ScrapeTarget).where(ScrapeTarget.company_id == company.id)).all())
        matching = [t for t in existing_targets if t.url.strip() == company.careers_url]
        if not matching:
            if existing_targets:
                existing_targets[0].url = company.careers_url
                existing_targets[0].active = company.active
            else:
                new_target = ScrapeTarget(
                    company_id=company.id,
                    url=company.careers_url,
                    type="generic_html",
                    active=company.active,
                    status="pending",
                )
                db.add(new_target)
        else:
            for t in matching:
                t.active = company.active

    db.commit()
    db.refresh(company)
    return company


# Re-export scrape_targets functions for backward compatibility
from .scrape_targets import list_scrape_targets, get_scrape_target  # noqa: E402


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
