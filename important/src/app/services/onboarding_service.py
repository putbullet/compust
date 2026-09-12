from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Company, Country, ScrapeTarget
from ..schemas_onboarding import CompanyOnboardRequest, CompanyOnboardResponse
from ..scraper.classifier import classify_portal
from ..logging import get_logger

logger = get_logger("onboarding")


def onboard_company_and_target(
    db: Session,
    request: CompanyOnboardRequest,
    html: str | None = None,
) -> CompanyOnboardResponse:
    """
    Onboard a company and its initial scrape target, performing automatic
    portal classification, pagination discovery, and robots.txt check.
    """
    country_code = request.country_code.upper()
    country = db.scalar(select(Country).where(Country.code == country_code))
    if not country:
        # Fallback to MA or create if needed
        country = db.scalar(select(Country).where(Country.code == "MA"))
        if not country:
            country = Country(name="Morocco", code="MA")
            db.add(country)
            db.commit()
            db.refresh(country)

    # Find or create company
    company = db.scalar(
        select(Company).where(
            (Company.name == request.name) | (Company.website_url == request.website_url)
        )
    )
    if not company:
        company = Company(
            name=request.name,
            website_url=request.website_url,
            careers_url=request.careers_url,
            active=True,
        )
        company.countries.append(country)
        db.add(company)
        db.commit()
        db.refresh(company)
        logger.info(f"Created company: {company.name} (id={company.id})")
    else:
        if country not in company.countries:
            company.countries.append(country)
            db.commit()

    target_url = request.scrape_target_url or request.careers_url

    # Classify portal
    classification = classify_portal(target_url, html=html)

    # Find or create scrape target
    target = db.scalar(
        select(ScrapeTarget).where(
            ScrapeTarget.company_id == company.id,
            ScrapeTarget.url == target_url,
        )
    )
    if not target:
        status_val = "active" if classification.robots_txt_allowed else "SOURCE_DISALLOWED"
        target = ScrapeTarget(
            company_id=company.id,
            url=target_url,
            type=classification.portal_type,
            active=True,
            status=status_val,
            robots_txt_allowed=classification.robots_txt_allowed,
            robots_txt_checked_at=classification.robots_txt_checked_at,
        )
        db.add(target)
        db.commit()
        db.refresh(target)
        logger.info(
            f"Created scrape target #{target.id} for {company.name}: type={target.type}, status={target.status}"
        )
    else:
        # Update classification & robots metadata
        target.type = classification.portal_type
        target.robots_txt_allowed = classification.robots_txt_allowed
        target.robots_txt_checked_at = classification.robots_txt_checked_at
        if not classification.robots_txt_allowed:
            target.status = "SOURCE_DISALLOWED"
        db.commit()
        db.refresh(target)

    return CompanyOnboardResponse(
        company_id=company.id,
        company_name=company.name,
        country_code=country.code,
        scrape_target_id=target.id,
        scrape_target_url=target.url,
        scrape_target_status=target.status or "active",
        classification=classification,
    )
