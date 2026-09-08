from fastapi import Depends, FastAPI, HTTPException, Path
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import Company, Country, ScrapeTarget
from .repositories.companies import get_company, list_companies as query_companies
from .repositories.countries import get_country_by_code, list_countries as query_countries
from .repositories.scrape_targets import (
    get_scrape_target,
    list_scrape_targets as query_scrape_targets,
)
from .repositories.jobs import persist_candidates
from .schemas import (
    CompanyRead,
    CountryRead,
    HealthRead,
    ScrapeTargetRead,
    SourceInspectionRead,
)
from .scraper.http_client import SourceFetchError
from .scraper.http_client import fetch_source
from .scraper.orange_parser import parse_orange_jobs
from .schemas_parser import JobCandidateRead, JobSyncRead, ParseResultRead
from .scraper.source_service import inspect_url

settings = get_settings()
app = FastAPI(title=settings.app_name, debug=settings.debug)


@app.get("/health", response_model=HealthRead, tags=["system"])
def health(db: Session = Depends(get_db)) -> HealthRead:
    db.execute(text("SELECT 1"))
    return HealthRead(status="ok", database="ok")


@app.get("/api/v1/countries", response_model=list[CountryRead], tags=["countries"])
def list_countries(db: Session = Depends(get_db)) -> list[Country]:
    return query_countries(db)


@app.get(
    "/api/v1/countries/{code}",
    response_model=CountryRead,
    tags=["countries"],
)
def read_country(
    code: str = Path(min_length=2, max_length=2),
    db: Session = Depends(get_db),
) -> Country:
    country = get_country_by_code(db, code)
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    return country


@app.get("/api/v1/companies", response_model=list[CompanyRead], tags=["companies"])
def list_companies(db: Session = Depends(get_db)) -> list[Company]:
    return query_companies(db)


@app.get(
    "/api/v1/companies/{company_id}",
    response_model=CompanyRead,
    tags=["companies"],
)
def read_company(
    company_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> Company:
    company = get_company(db, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@app.get(
    "/api/v1/scrape-targets",
    response_model=list[ScrapeTargetRead],
    tags=["scrape-targets"],
)
def list_scrape_targets(
    company_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[ScrapeTarget]:
    return query_scrape_targets(db, company_id)


@app.get(
    "/api/v1/scrape-targets/{target_id}",
    response_model=ScrapeTargetRead,
    tags=["scrape-targets"],
)
def read_scrape_target(
    target_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> ScrapeTarget:
    target = get_scrape_target(db, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Scrape target not found")
    return target


@app.post(
    "/api/v1/scrape-targets/{target_id}/inspect",
    response_model=SourceInspectionRead,
    tags=["scrape-targets"],
)
def inspect_scrape_target(
    target_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> SourceInspectionRead:
    target = get_scrape_target(db, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Scrape target not found")
    try:
        return inspect_url(target.url)
    except SourceFetchError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error


@app.post(
    "/api/v1/scrape-targets/{target_id}/parse",
    response_model=ParseResultRead,
    tags=["scrape-targets"],
)
def parse_scrape_target(
    target_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> ParseResultRead:
    target = get_scrape_target(db, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Scrape target not found")
    if target.company_id != 1:
        raise HTTPException(
            status_code=422,
            detail="No source parser is configured for this scrape target",
        )
    try:
        result = parse_orange_jobs(fetch_source(target.url))
    except SourceFetchError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return ParseResultRead(
        jobs=[JobCandidateRead.model_validate(job, from_attributes=True) for job in result.jobs],
        errors=result.errors,
    )


@app.post(
    "/api/v1/scrape-targets/{target_id}/sync",
    response_model=JobSyncRead,
    tags=["scrape-targets"],
)
def sync_scrape_target(
    target_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> JobSyncRead:
    target = get_scrape_target(db, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Scrape target not found")
    if target.company_id != 1:
        raise HTTPException(status_code=422, detail="No source parser is configured")
    company = get_company(db, target.company_id)
    if company is None or not company.countries:
        raise HTTPException(status_code=422, detail="Scrape target has no country")
    try:
        result = parse_orange_jobs(fetch_source(target.url))
        added, updated = persist_candidates(
            db,
            company_id=target.company_id,
            country_id=company.countries[0].id,
            source="orange.jobs",
            candidates=result.jobs,
        )
    except SourceFetchError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return JobSyncRead(
        jobs_found=len(result.jobs),
        jobs_added=added,
        jobs_updated=updated,
        parser_errors=result.errors,
    )
