from datetime import datetime, timezone
import time
from fastapi import Body, Depends, FastAPI, File, HTTPException, Path, Query, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .logging import ScrapingRunScope, get_logger
from .matching.matcher import calculate_job_match
from .matching.semantic_adapter import semantic_service
from .models import Company, Country, ScrapeTarget, ScrapingRun, User, Resume, CustomizedResume
from .services.translation import JobTranslationService
from .repositories.applications import (
    create_manual_application,
    delete_application,
    delete_application_by_job_id,
    export_applications_xlsx,
    get_application,
    get_application_statistics,
    get_sankey_pipeline,
    get_user_applications,
    save_or_update_application,
    update_application,
)
from .repositories.auth import (
    authenticate_user,
    build_user_profile,
    create_user,
    get_user_by_email,
    set_user_country_preferences,
    set_user_skills,
    update_user_preferences,
)
from .repositories.companies import (
    create_company,
    delete_company,
    get_company,
    list_companies as query_companies,
    toggle_company_active,
    update_company,
)
from .repositories.countries import get_country_by_code, list_countries as query_countries
from .repositories.profile import (
    add_education,
    add_experience,
    add_language,
    delete_education,
    delete_experience,
    delete_language,
)
from .repositories.scrape_targets import (
    create_scrape_target,
    delete_scrape_target,
    get_scrape_target,
    list_scrape_targets as query_scrape_targets,
    toggle_scrape_target_active,
    update_scrape_target,
)
from .repositories.jobs import get_job, get_job_skills, list_jobs, persist_candidates
from .repositories.resume import (
    delete_resume,
    get_active_resume,
    list_user_resumes,
    save_resume,
    set_active_resume,
)
from .schemas import (
    CompanyCreate,
    CompanyDetailRead,
    CompanyRead,
    CompanyUpdate,
    CountryRead,
    HealthRead,
    JobDetailRead,
    JobListResponse,
    JobRead,
    JobTranslationCreate,
    JobTranslationRead,
    ScrapeTargetCreate,
    ScrapeTargetRead,
    ScrapeTargetUpdate,
    ScrapingRunRead,
    SourceInspectionRead,
)
from .schemas_ai_resume import (
    AIChatRequest,
    AIChatResponse,
    AIProviderRead,
    AISettingsUpdate,
    AIStatusResponse,
    CustomizedResumeRead,
    JobSupervisionUpdate,
    ResumeRead,
    ResumeSuggestionResponse,
    ScraperDiagnosticRequest,
    ScraperDiagnosticResponse,
)
from .schemas_applications import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationStatsRead,
    ApplicationUpdate,
    ManualApplicationCreate,
    SankeyDataRead,
)
from .schemas_metrics import ScraperTelemetryRead
from .schemas_auth import (
    TokenResponse,
    UserCountryUpdate,
    UserLoginRequest,
    UserPreferencesUpdate,
    UserProfileResponse,
    UserRegisterRequest,
    UserSkillUpdate,
)
from .schemas_profile import (
    UserEducationCreate,
    UserExperienceCreate,
    UserLanguageCreate,
)
from .schemas_resume import (
    ResumeDuplicateRequest,
    ResumeSaveTailoredCopyRequest,
    ResumeTailorSuggestions,
    StructuredResumeCreate,
    StructuredResumeRead,
    StructuredResumeUpdate,
)
from .security import (
    create_access_token,
    get_current_user,
    get_optional_current_user,
)
from .scraper.http_client import SourceFetchError, fetch_source
from .scraper.crawler import crawl_pages
from .scraper.registry import get_strategy_for_target
from .scraper.cooldown import apply_target_outcome, is_in_cooldown
from .scraper.robots_checker import verify_target_robots_compliance
from .scraper.run_service import (
    finish_scraping_run,
    list_scraping_runs,
    start_scraping_run,
)
from .schemas_parser import JobCandidateRead, JobSyncRead, ParseResultRead
from .schemas_onboarding import CompanyOnboardRequest, CompanyOnboardResponse
from .services.onboarding_service import onboard_company_and_target
from .scraper.source_service import inspect_url
from .services.ai_service import (
    check_ollama_runtime,
    get_providers_list,
    set_selected_model,
)
from .services.ai_tools import answer_user_query
from .services.resume_parser import (
    ResumeParseError,
    ScannedPdfError,
    extract_text_from_pdf_bytes,
    structure_resume_text,
)
from .services.resume_customization import get_ai_resume_customization
from .services.resume_export import (
    render_template_docx,
    render_template_pdf,
)
from .services.resume_tailoring import (
    analyze_structured_resume_for_job,
    save_tailored_resume_copy,
)
from .repositories.resume import (
    create_structured_resume,
    delete_structured_resume,
    duplicate_structured_resume,
    get_user_resume,
    import_profile_into_structured_data,
    list_user_structured_resumes,
    set_default_structured_resume,
    update_structured_resume,
)

settings = get_settings()
app = FastAPI(title=settings.app_name, debug=settings.debug)
translation_service = JobTranslationService()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type", "Content-Length"],
)


@app.get("/health", response_model=HealthRead, tags=["system"])
def health(db: Session = Depends(get_db)) -> HealthRead:
    start = time.perf_counter()
    db.execute(text("SELECT 1"))
    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    return HealthRead(status="ok", database="ok", latency_ms=latency_ms)


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


@app.post(
    "/api/v1/companies",
    response_model=CompanyRead,
    status_code=status.HTTP_201_CREATED,
    tags=["companies"],
)
def add_company(
    req: CompanyCreate,
    db: Session = Depends(get_db),
) -> Company:
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Company name cannot be empty")
    return create_company(
        db,
        name=req.name,
        website_url=req.website_url,
        careers_url=req.careers_url,
        active=req.active,
        country_ids=req.country_ids,
    )


@app.put(
    "/api/v1/companies/{company_id}",
    response_model=CompanyRead,
    tags=["companies"],
)
def edit_company(
    req: CompanyUpdate,
    company_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> Company:
    company = update_company(
        db,
        company_id=company_id,
        name=req.name,
        website_url=req.website_url,
        careers_url=req.careers_url,
        active=req.active,
        country_ids=req.country_ids,
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@app.patch(
    "/api/v1/companies/{company_id}/toggle",
    response_model=CompanyRead,
    tags=["companies"],
)
def toggle_company(
    company_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> Company:
    company = toggle_company_active(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@app.delete(
    "/api/v1/companies/{company_id}",
    tags=["companies"],
)
def remove_company(
    company_id: int = Path(gt=0),
    confirm_hard_delete: bool = Query(default=False, description="Set true to permanently delete company and all historical data"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    company = get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    deleted = delete_company(db, company_id, hard_delete=confirm_hard_delete)
    if not deleted:
        raise HTTPException(status_code=404, detail="Company not found")

    return {
        "status": "permanently_deleted" if confirm_hard_delete else "deactivated",
        "company_id": company_id,
        "message": "Company permanently deleted." if confirm_hard_delete else "Company deactivated safely. Historical data preserved.",
    }


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
    "/api/v1/scrape-targets",
    response_model=ScrapeTargetRead,
    status_code=status.HTTP_201_CREATED,
    tags=["scrape-targets"],
)
def add_scrape_target(
    req: ScrapeTargetCreate,
    db: Session = Depends(get_db),
) -> ScrapeTarget:
    company = get_company(db, req.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return create_scrape_target(
        db,
        company_id=req.company_id,
        url=req.url,
        target_type=req.type,
        active=req.active,
    )


@app.put(
    "/api/v1/scrape-targets/{target_id}",
    response_model=ScrapeTargetRead,
    tags=["scrape-targets"],
)
def edit_scrape_target(
    req: ScrapeTargetUpdate,
    target_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> ScrapeTarget:
    target = update_scrape_target(
        db,
        target_id=target_id,
        url=req.url,
        target_type=req.type,
        active=req.active,
    )
    if not target:
        raise HTTPException(status_code=404, detail="Scrape target not found")
    return target


@app.patch(
    "/api/v1/scrape-targets/{target_id}/toggle",
    response_model=ScrapeTargetRead,
    tags=["scrape-targets"],
)
def toggle_target(
    target_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> ScrapeTarget:
    target = toggle_scrape_target_active(db, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Scrape target not found")
    return target


@app.delete(
    "/api/v1/scrape-targets/{target_id}",
    tags=["scrape-targets"],
)
def remove_scrape_target(
    target_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    target = get_scrape_target(db, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Scrape target not found")
    delete_scrape_target(db, target_id)
    return {"status": "deleted", "target_id": target_id}


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

    if not verify_target_robots_compliance(db, target):
        raise HTTPException(
            status_code=403,
            detail=f"Scraping is disallowed by robots.txt for target {target_id} (SOURCE_DISALLOWED)",
        )

    try:
        return inspect_url(target.url)
    except SourceFetchError as error:
        outcome = "rate_limited" if error.status_code == 429 else ("restricted" if error.status_code == 403 else "failed")
        apply_target_outcome(db, target, outcome)
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
    max_pages: int = Query(default=1, ge=1, le=20),
    db: Session = Depends(get_db),
) -> ParseResultRead:
    target = get_scrape_target(db, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Scrape target not found")

    if not verify_target_robots_compliance(db, target):
        raise HTTPException(
            status_code=403,
            detail=f"Scraping is disallowed by robots.txt for target {target_id} (SOURCE_DISALLOWED)",
        )

    in_cooldown, cooldown_msg = is_in_cooldown(target)
    if in_cooldown:
        raise HTTPException(status_code=429, detail=cooldown_msg)

    company = get_company(db, target.company_id)
    strategy = get_strategy_for_target(target, company)
    if strategy is None:
        raise HTTPException(
            status_code=422,
            detail="No source parser is configured for this scrape target",
        )

    try:
        if max_pages > 1:
            crawl_result = crawl_pages(target.url, strategy, max_pages=max_pages)
            return ParseResultRead(
                jobs=[JobCandidateRead.model_validate(job, from_attributes=True) for job in crawl_result.jobs],
                errors=crawl_result.errors,
            )
        else:
            fetch_url = target.url
            if hasattr(strategy, "resolve_fetch_url"):
                fetch_url = strategy.resolve_fetch_url(target.url)
            source = fetch_source(fetch_url)
            result = strategy.parse(source)
            return ParseResultRead(
                jobs=[JobCandidateRead.model_validate(job, from_attributes=True) for job in result.jobs],
                errors=result.errors,
            )
    except SourceFetchError as error:
        outcome = "rate_limited" if error.status_code == 429 else ("restricted" if error.status_code == 403 else "failed")
        apply_target_outcome(db, target, outcome)
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post(
    "/api/v1/scrape-targets/{target_id}/sync",
    response_model=JobSyncRead,
    tags=["scrape-targets"],
)
def sync_scrape_target(
    target_id: int = Path(gt=0),
    max_pages: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> JobSyncRead:
    target = get_scrape_target(db, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Scrape target not found")

    if not verify_target_robots_compliance(db, target):
        raise HTTPException(
            status_code=403,
            detail=f"Scraping is disallowed by robots.txt for target {target_id} (SOURCE_DISALLOWED)",
        )

    in_cooldown, cooldown_msg = is_in_cooldown(target)
    if in_cooldown:
        raise HTTPException(status_code=429, detail=cooldown_msg)

    company = get_company(db, target.company_id)
    strategy = get_strategy_for_target(target, company)
    if strategy is None:
        raise HTTPException(status_code=422, detail="No source parser is configured")
    if company is None or not company.countries:
        raise HTTPException(status_code=422, detail="Scrape target has no country")

    run = start_scraping_run(db, target.company_id)

    with ScrapingRunScope(scraping_run_id=run.id, company_id=target.company_id, target_id=target.id):
        try:
            crawl_result = crawl_pages(target.url, strategy, max_pages=max_pages)
            added, updated = persist_candidates(
                db,
                company_id=target.company_id,
                country_id=company.countries[0].id,
                source=strategy.source_name,
                candidates=crawl_result.jobs,
                scrape_target_id=target.id,
            )
            finish_scraping_run(
                db,
                run,
                jobs_found=len(crawl_result.jobs),
                jobs_added=added,
                jobs_updated=updated,
                parser_errors=crawl_result.errors,
            )
            target_outcome = "partial" if crawl_result.errors else "success"
            apply_target_outcome(db, target, target_outcome)

            if not crawl_result.errors and len(crawl_result.jobs) > 0:
                from .services.stale_lifecycle import evaluate_target_stale_jobs
                seen_ext = {c.external_job_id for c in crawl_result.jobs if c.external_job_id}
                seen_urls = {c.job_url for c in crawl_result.jobs if c.job_url}
                evaluate_target_stale_jobs(
                    db,
                    company_id=target.company_id,
                    scrape_target_id=target.id,
                    seen_external_ids=seen_ext,
                    seen_urls=seen_urls,
                    is_full_success=True,
                )

            return JobSyncRead(
                jobs_found=len(crawl_result.jobs),
                jobs_added=added,
                jobs_updated=updated,
                parser_errors=crawl_result.errors,
            )
        except SourceFetchError as error:
            finish_scraping_run(
                db,
                run,
                request_error=str(error),
                forced_status="failed",
            )
            outcome = "rate_limited" if error.status_code == 429 else ("restricted" if error.status_code == 403 else "failed")
            apply_target_outcome(db, target, outcome)
            raise HTTPException(status_code=502, detail=str(error)) from error
        except Exception as exc:
            finish_scraping_run(
                db,
                run,
                request_error=str(exc),
                forced_status="failed",
            )
            apply_target_outcome(db, target, "failed")
            raise


@app.get(
    "/api/v1/scrape-targets/{target_id}/runs",
    response_model=list[ScrapingRunRead],
    tags=["scrape-targets"],
)
def list_target_runs(
    target_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> list[ScrapingRun]:
    target = get_scrape_target(db, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Scrape target not found")
    return list_scraping_runs(db, target.company_id)


@app.get(
    "/api/v1/companies/{company_id}/runs",
    response_model=list[ScrapingRunRead],
    tags=["companies"],
)
def list_company_runs(
    company_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> list[ScrapingRun]:
    company = get_company(db, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return list_scraping_runs(db, company_id)


@app.get(
    "/api/v1/admin/scraping-runs",
    response_model=list[ScrapingRunRead],
    tags=["admin"],
)
def list_all_scraping_runs(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[ScrapingRun]:
    return list(
        db.scalars(
            select(ScrapingRun).order_by(ScrapingRun.started_at.desc()).limit(limit)
        ).all()
    )


@app.get("/api/v1/jobs", response_model=JobListResponse, tags=["jobs"])
def get_jobs(
    country_id: int | None = Query(default=None, gt=0),
    company_id: int | None = Query(default=None, gt=0),
    remote_type: str | None = Query(default=None),
    employment_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
) -> JobListResponse:
    skip = (page - 1) * page_size
    items, total = list_jobs(
        db,
        country_id=country_id,
        company_id=company_id,
        remote_type=remote_type,
        employment_type=employment_type,
        search=search,
        active_only=active_only,
        skip=skip,
        limit=page_size,
    )
    pages = (total + page_size - 1) // page_size if total > 0 else 0

    read_items = []
    for j in items:
        item = JobRead.model_validate(j)
        if user:
            skills = get_job_skills(db, j.id)
            match_res = calculate_job_match(j, skills, user)
            item.match_score = match_res.score
        read_items.append(item)

    return JobListResponse(
        items=read_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@app.get("/api/v1/jobs/{job_id}", response_model=JobDetailRead, tags=["jobs"])
def get_job_detail(
    job_id: int = Path(gt=0),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
) -> JobDetailRead:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    skills = get_job_skills(db, job_id)
    detail = JobDetailRead.model_validate(job)
    detail.skills = skills
    if user:
        match_res = semantic_service.compute_match(job, skills, user)
        detail.match_score = match_res.score
        detail.positive_factors = match_res.positive_factors
        detail.missing_factors = match_res.missing_factors
        detail.category_scores = match_res.category_scores
    return detail


@app.get("/api/v1/jobs/{job_id}/translations", response_model=list[JobTranslationRead], tags=["jobs"])
def get_job_translations(
    job_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> list[JobTranslationRead]:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    translations = translation_service.get_translations(db, job_id)
    return [JobTranslationRead.model_validate(t) for t in translations]


@app.post("/api/v1/jobs/{job_id}/translations", response_model=JobTranslationRead, tags=["jobs"])
def create_job_translation(
    req: JobTranslationCreate,
    job_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> JobTranslationRead:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if req.title:
        translation = translation_service.create_or_update_translation(
            session=db,
            job_id=job_id,
            language=req.language,
            title=req.title,
            description=req.description,
            source_language=req.source_language,
        )
    else:
        translation = translation_service.auto_translate_job(
            session=db,
            job=job,
            target_language=req.language,
        )
    return JobTranslationRead.model_validate(translation)


# --- Auth & Profile Endpoints ---


@app.post("/api/v1/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, tags=["auth"])
def register_user(
    req: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    existing = get_user_by_email(db, req.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = create_user(db, req)
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return TokenResponse(access_token=token, user=build_user_profile(user))


@app.post("/api/v1/auth/login", response_model=TokenResponse, tags=["auth"])
def login_user(
    req: UserLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = authenticate_user(db, req.email, req.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return TokenResponse(access_token=token, user=build_user_profile(user))


@app.get("/api/v1/auth/me", response_model=UserProfileResponse, tags=["auth"])
def get_me(user: User = Depends(get_current_user)) -> UserProfileResponse:
    return build_user_profile(user)


@app.get("/api/v1/profile", response_model=UserProfileResponse, tags=["profile"])
def read_profile(user: User = Depends(get_current_user)) -> UserProfileResponse:
    return build_user_profile(user)


@app.put("/api/v1/profile/preferences", response_model=UserProfileResponse, tags=["profile"])
def set_preferences(
    prefs: UserPreferencesUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    update_user_preferences(db, user, prefs)
    db.refresh(user)
    return build_user_profile(user)


@app.put("/api/v1/profile/skills", response_model=UserProfileResponse, tags=["profile"])
def set_skills(
    skills_req: UserSkillUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    set_user_skills(db, user, skills_req.skills)
    db.refresh(user)
    return build_user_profile(user)


@app.put("/api/v1/profile/countries", response_model=UserProfileResponse, tags=["profile"])
def set_countries(
    country_req: UserCountryUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    set_user_country_preferences(db, user, country_req.country_ids)
    db.refresh(user)
    return build_user_profile(user)


@app.post("/api/v1/profile/experiences", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED, tags=["profile"])
def create_experience(
    exp_req: UserExperienceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    add_experience(db, user, exp_req)
    db.refresh(user)
    return build_user_profile(user)


@app.delete("/api/v1/profile/experiences/{experience_id}", response_model=UserProfileResponse, tags=["profile"])
def remove_experience(
    experience_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    if not delete_experience(db, user, experience_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience record not found")
    db.refresh(user)
    return build_user_profile(user)


@app.post("/api/v1/profile/educations", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED, tags=["profile"])
def create_education(
    edu_req: UserEducationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    add_education(db, user, edu_req)
    db.refresh(user)
    return build_user_profile(user)


@app.delete("/api/v1/profile/educations/{education_id}", response_model=UserProfileResponse, tags=["profile"])
def remove_education(
    education_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    if not delete_education(db, user, education_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Education record not found")
    db.refresh(user)
    return build_user_profile(user)


@app.post("/api/v1/profile/languages", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED, tags=["profile"])
def create_language(
    lang_req: UserLanguageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    add_language(db, user, lang_req)
    db.refresh(user)
    return build_user_profile(user)


@app.delete("/api/v1/profile/languages/{language_id}", response_model=UserProfileResponse, tags=["profile"])
def remove_language(
    language_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    if not delete_language(db, user, language_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Language record not found")
    db.refresh(user)
    return build_user_profile(user)


# User Job Applications & Pipeline Tracking
@app.get("/api/v1/applications/stats", response_model=ApplicationStatsRead, tags=["applications"])
def get_my_application_stats(
    start_date: datetime | None = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: datetime | None = Query(None, description="End date filter (YYYY-MM-DD)"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationStatsRead:
    return get_application_statistics(db, user.id, start_date=start_date, end_date=end_date)


@app.get("/api/v1/applications/pipeline", response_model=SankeyDataRead, tags=["applications"])
def get_my_application_pipeline(
    source: str | None = Query(None, description="Filter pipeline by source"),
    country: str | None = Query(None, description="Filter pipeline by country"),
    start_date: datetime | None = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: datetime | None = Query(None, description="End date filter (YYYY-MM-DD)"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SankeyDataRead:
    return get_sankey_pipeline(
        db,
        user.id,
        source=source,
        country=country,
        start_date=start_date,
        end_date=end_date,
    )


@app.get("/api/v1/applications/export", tags=["applications"])
def export_my_applications_to_excel(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    xlsx_bytes = export_applications_xlsx(db, user.id)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    filename = f"compust_applications_{timestamp}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/v1/applications", response_model=list[ApplicationRead], tags=["applications"])
def list_my_applications(
    status: str | None = Query(None, description="Filter by status"),
    source: str | None = Query(None, description="Filter by source"),
    country: str | None = Query(None, description="Filter by country"),
    search: str | None = Query(None, description="Search by title, company, notes, contact, etc."),
    start_date: datetime | None = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: datetime | None = Query(None, description="End date filter (YYYY-MM-DD)"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ApplicationRead]:
    apps = get_user_applications(
        db,
        user.id,
        status=status,
        source=source,
        country=country,
        search=search,
        start_date=start_date,
        end_date=end_date,
    )
    return [ApplicationRead.model_validate(a) for a in apps]


@app.post("/api/v1/applications", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED, tags=["applications"])
def create_manual_tracked_application(
    data: ManualApplicationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationRead:
    app_record = create_manual_application(db, user, data)
    return ApplicationRead.model_validate(app_record)


@app.post("/api/v1/applications/{job_id}", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED, tags=["applications"])
def track_job_application(
    job_id: int,
    data: ApplicationCreate | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationRead:
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    app_data = data or ApplicationCreate(status="saved")
    app_record = save_or_update_application(db, user, job_id, app_data)
    return ApplicationRead.model_validate(app_record)


@app.patch("/api/v1/applications/{application_id}", response_model=ApplicationRead, tags=["applications"])
def modify_application_stage(
    application_id: int,
    data: ApplicationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationRead:
    updated = update_application(db, user, application_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return ApplicationRead.model_validate(updated)


@app.delete("/api/v1/applications/{application_id}", tags=["applications"])
def remove_application(
    application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not delete_application(db, user, application_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return {"status": "deleted"}


@app.delete("/api/v1/applications/jobs/{job_id}", tags=["applications"])
def remove_application_by_job(
    job_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not delete_application_by_job_id(db, user, job_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved application for job not found")
    return {"status": "deleted"}


@app.post(
    "/api/v1/admin/onboard",
    response_model=CompanyOnboardResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["admin"],
)
def admin_onboard_company(
    req: CompanyOnboardRequest,
    db: Session = Depends(get_db),
) -> CompanyOnboardResponse:
    return onboard_company_and_target(db, req)


@app.get(
    "/api/v1/admin/metrics",
    response_model=ScraperTelemetryRead,
    tags=["admin"],
)
def admin_scraper_metrics(
    db: Session = Depends(get_db),
) -> ScraperTelemetryRead:
    from .repositories.metrics import get_scraper_telemetry

    return get_scraper_telemetry(db)


# --- AI Endpoints ---


@app.get("/api/v1/ai/status", response_model=AIStatusResponse, tags=["ai"])
def get_ai_status() -> AIStatusResponse:
    return AIStatusResponse.model_validate(check_ollama_runtime())


@app.get("/api/v1/ai/providers", response_model=list[AIProviderRead], tags=["ai"])
def list_ai_providers() -> list[AIProviderRead]:
    return [AIProviderRead.model_validate(p) for p in get_providers_list()]


@app.post("/api/v1/ai/settings", response_model=AIStatusResponse, tags=["ai"])
def update_ai_settings(req: AISettingsUpdate) -> AIStatusResponse:
    set_selected_model(req.selected_model)
    return AIStatusResponse.model_validate(check_ollama_runtime())


@app.post("/api/v1/ai/chat", response_model=AIChatResponse, tags=["ai"])
def ai_chat(
    req: AIChatRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
) -> AIChatResponse:
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    user_id = user.id if user else None
    result = answer_user_query(req.query, db, user_id=user_id, model=req.model)
    return AIChatResponse(
        answer=result["answer"],
        facts=result["facts"],
        provider=result["provider"],
        model=result.get("model"),
        ollama_available=result.get("ollama_available", False),
    )


# --- Resume Management Endpoints (NO OCR) ---


@app.post("/api/v1/profile/resume", response_model=ResumeRead, status_code=status.HTTP_201_CREATED, tags=["profile"])
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Resume:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF documents are supported for resume upload.")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit.")

    try:
        raw_text = extract_text_from_pdf_bytes(pdf_bytes)
    except ScannedPdfError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except ResumeParseError as err:
        raise HTTPException(status_code=422, detail=str(err))

    parsed_sections = structure_resume_text(raw_text)
    resume = save_resume(
        db,
        user_id=user.id,
        filename=file.filename,
        raw_text=raw_text,
        parsed_sections=parsed_sections,
    )
    return resume


@app.get("/api/v1/profile/resume", response_model=ResumeRead, tags=["profile"])
def get_user_active_resume(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Resume:
    resume = get_active_resume(db, user.id)
    if not resume:
        raise HTTPException(status_code=404, detail="No active resume found. Please upload a resume first.")
    return resume


@app.get("/api/v1/profile/resumes", response_model=list[ResumeRead], tags=["profile"])
def list_user_all_resumes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Resume]:
    return list_user_resumes(db, user.id)


@app.put("/api/v1/profile/resume/{resume_id}/activate", response_model=ResumeRead, tags=["profile"])
def activate_user_resume(
    resume_id: int = Path(gt=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Resume:
    resume = set_active_resume(db, user.id, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume record not found.")
    return resume


@app.delete("/api/v1/profile/resume/{resume_id}", tags=["profile"])
def remove_user_resume(
    resume_id: int = Path(gt=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    deleted = delete_resume(db, user.id, resume_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resume record not found.")
    return {"status": "deleted", "resume_id": resume_id}


# --- First-Class Structured Resume Builder Endpoints ---


@app.get("/api/v1/resumes", response_model=list[StructuredResumeRead], tags=["resume-builder"])
def list_structured_resumes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Resume]:
    return list_user_structured_resumes(db, user.id)


@app.post("/api/v1/resumes", response_model=StructuredResumeRead, tags=["resume-builder"])
def create_new_structured_resume(
    payload: StructuredResumeCreate = Body(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Resume:
    structured_data_dict = payload.structured_data.model_dump() if payload.structured_data else None
    settings_dict = payload.settings.model_dump() if payload.settings else None
    return create_structured_resume(
        db=db,
        user_id=user.id,
        title=payload.title,
        is_default=payload.is_default,
        structured_data=structured_data_dict,
        settings=settings_dict,
        target_job_id=payload.target_job_id,
        source_resume_id=payload.source_resume_id,
    )


@app.get("/api/v1/resumes/{resume_id}", response_model=StructuredResumeRead, tags=["resume-builder"])
def get_single_structured_resume(
    resume_id: int = Path(gt=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Resume:
    resume = get_user_resume(db, user.id, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return resume


@app.put("/api/v1/resumes/{resume_id}", response_model=StructuredResumeRead, tags=["resume-builder"])
def update_single_structured_resume(
    resume_id: int = Path(gt=0),
    payload: StructuredResumeUpdate = Body(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Resume:
    structured_data_dict = payload.structured_data.model_dump() if payload.structured_data else None
    settings_dict = payload.settings.model_dump() if payload.settings else None
    updated = update_structured_resume(
        db=db,
        user_id=user.id,
        resume_id=resume_id,
        title=payload.title,
        is_default=payload.is_default,
        structured_data=structured_data_dict,
        settings=settings_dict,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return updated


@app.post("/api/v1/resumes/{resume_id}/duplicate", response_model=StructuredResumeRead, tags=["resume-builder"])
def duplicate_single_structured_resume(
    resume_id: int = Path(gt=0),
    payload: ResumeDuplicateRequest = Body(default_factory=ResumeDuplicateRequest),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Resume:
    copy_resume = duplicate_structured_resume(db, user.id, resume_id, payload.new_title)
    if not copy_resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return copy_resume


@app.delete("/api/v1/resumes/{resume_id}", tags=["resume-builder"])
def delete_single_structured_resume(
    resume_id: int = Path(gt=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    deleted = delete_structured_resume(db, user.id, resume_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return {"status": "deleted", "id": resume_id}


@app.post("/api/v1/resumes/{resume_id}/set-default", response_model=StructuredResumeRead, tags=["resume-builder"])
def set_default_single_resume(
    resume_id: int = Path(gt=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Resume:
    res = set_default_structured_resume(db, user.id, resume_id)
    if not res:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return res


@app.post("/api/v1/resumes/{resume_id}/import-profile", response_model=StructuredResumeRead, tags=["resume-builder"])
def import_profile_to_resume_endpoint(
    resume_id: int = Path(gt=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Resume:
    resume = get_user_resume(db, user.id, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    merged = import_profile_into_structured_data(db, user.id, resume.structured_data)
    updated = update_structured_resume(db, user.id, resume_id, structured_data=merged)
    return updated or resume


@app.get("/api/v1/resumes/{resume_id}/export/{file_format}", tags=["resume-builder"])
def export_structured_resume_file(
    resume_id: int = Path(gt=0),
    file_format: str = Path(pattern="^(pdf|docx)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from fastapi.responses import FileResponse
    resume = get_user_resume(db, user.id, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    structured_data = resume.structured_data or {}
    settings_data = resume.settings or {}

    import pathlib
    storage_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "storage" / "exported_resumes"
    storage_dir.mkdir(parents=True, exist_ok=True)

    safe_title = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in resume.title).strip("_") or "resume"
    out_fname = f"{safe_title}_{user.id}_{resume.id}.{file_format}"
    dest_path = storage_dir / out_fname

    if file_format == "pdf":
        render_template_pdf(structured_data, settings_data, dest_path)
        media_type = "application/pdf"
    else:
        render_template_docx(structured_data, settings_data, dest_path)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return FileResponse(
        path=str(dest_path),
        media_type=media_type,
        filename=out_fname,
        content_disposition_type="attachment",
        headers={
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


# --- Resume Customization Assistant Endpoint ---


@app.post("/api/v1/jobs/{job_id}/resume-suggestions", response_model=ResumeSuggestionResponse, tags=["jobs"])
def get_resume_suggestions_for_job(
    job_id: int = Path(gt=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeSuggestionResponse:
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job vacancy not found.")

    active_resume = get_active_resume(db, user.id)
    if not active_resume:
        raise HTTPException(status_code=400, detail="Please upload a resume first.")

    analysis = get_ai_resume_customization(db, job, active_resume)
    return ResumeSuggestionResponse(
        job_id=job.id,
        job_title=job.title,
        already_demonstrated=analysis["already_demonstrated"],
        missing_or_weak=analysis["missing_or_weak"],
        ats_improvements=analysis.get("ats_improvements", []),
        actionable_recommendations=analysis.get("actionable_recommendations", []),
        suggestions=analysis["suggestions"],
        requirements_status=analysis.get("requirements_status", "COMPLETE"),
        ai_enhanced=analysis.get("ai_enhanced", False),
        provider=analysis.get("provider", "deterministic"),
    )


@app.get("/api/v1/jobs/{job_id}/resumes/{resume_id}/tailor", response_model=ResumeTailorSuggestions, tags=["resume-tailoring"])
def get_structured_tailor_suggestions(
    job_id: int = Path(gt=0),
    resume_id: int = Path(gt=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeTailorSuggestions:
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job vacancy not found.")

    resume = get_user_resume(db, user.id, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    from .repositories.jobs import get_job_skills
    job_skills = get_job_skills(db, job.id)
    analysis = analyze_structured_resume_for_job(job, job_skills, resume)
    return ResumeTailorSuggestions(**analysis)


@app.post("/api/v1/jobs/{job_id}/resumes/{resume_id}/tailor/save-copy", response_model=StructuredResumeRead, tags=["resume-tailoring"])
def save_tailored_resume_copy_endpoint(
    job_id: int = Path(gt=0),
    resume_id: int = Path(gt=0),
    payload: ResumeSaveTailoredCopyRequest = Body(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Resume:
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job vacancy not found.")

    resume = get_user_resume(db, user.id, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    try:
        new_resume = save_tailored_resume_copy(
            db=db,
            user_id=user.id,
            base_resume_id=resume.id,
            job=job,
            title=payload.title,
            apply_suggested_summary=payload.apply_suggested_summary,
            apply_emphasized_skills=payload.apply_emphasized_skills,
            accepted_experience_refinements=payload.accepted_experience_refinements,
        )
        return new_resume
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create tailored resume copy: {exc}")


# --- Resume Recreation & Output Endpoints ---


@app.post("/api/v1/jobs/{job_id}/resume-customizations/recreate", response_model=CustomizedResumeRead, tags=["jobs"])
def recreate_job_customized_resume(
    job_id: int = Path(gt=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CustomizedResume:
    from .services.resume_recreator import recreate_customized_resume_for_job

    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job vacancy not found.")

    active_resume = get_active_resume(db, user.id)
    if not active_resume:
        raise HTTPException(status_code=400, detail="Please upload a base resume first.")

    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email.split('@')[0].title()
    try:
        custom_res = recreate_customized_resume_for_job(db, user.id, active_resume, job, user_name=name)
        return custom_res
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate customized resume: {exc}")


@app.get("/api/v1/customized-resumes/{resume_id}/download/{file_format}", tags=["jobs"])
def download_customized_resume_file(
    resume_id: int = Path(gt=0),
    file_format: str = Path(pattern="^(pdf|docx)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from fastapi.responses import FileResponse
    from .services.resume_recreator import get_customized_resume_file_path

    record = db.scalar(
        select(CustomizedResume).where(CustomizedResume.id == resume_id, CustomizedResume.user_id == user.id)
    )
    if not record:
        raise HTTPException(status_code=404, detail="Customized resume not found.")

    target_fname = record.pdf_filename if file_format == "pdf" else record.docx_filename
    if not target_fname:
        raise HTTPException(status_code=404, detail=f"No {file_format.upper()} file generated for this record.")

    path = get_customized_resume_file_path(target_fname)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk.")

    media_type = "application/pdf" if file_format == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(
        path=str(path),
        media_type=media_type,
        filename=target_fname,
        content_disposition_type="attachment",
        headers={
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@app.get("/api/v1/jobs/{job_id}/customized-resumes", response_model=list[CustomizedResumeRead], tags=["jobs"])
def list_job_customized_resumes(
    job_id: int = Path(gt=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CustomizedResume]:
    return list(
        db.scalars(
            select(CustomizedResume)
            .where(CustomizedResume.user_id == user.id, CustomizedResume.job_id == job_id)
            .order_by(CustomizedResume.created_at.desc())
        ).all()
    )


# --- Local User Job Supervision Endpoints ---


@app.patch("/api/v1/admin/jobs/{job_id}", response_model=JobRead, tags=["admin"])
def supervise_update_job(
    job_id: int = Path(gt=0),
    req: JobSupervisionUpdate = Body(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Job:
    from .repositories.job_supervision import update_job_supervision

    updated = update_job_supervision(
        db,
        job_id,
        title=req.title,
        description=req.description,
        location=req.location,
        department=req.department,
        employment_type=req.employment_type,
        remote_type=req.remote_type,
        job_url=req.job_url,
        active=req.active,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Job not found.")
    return updated


@app.delete("/api/v1/admin/jobs/{job_id}", tags=["admin"])
def supervise_delete_job(
    job_id: int = Path(gt=0),
    force: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from .repositories.job_supervision import delete_job_safely

    deleted = delete_job_safely(db, job_id, force=force)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {"status": "deleted", "job_id": job_id, "forced": force}


# --- Scraper Diagnostic Testing Endpoints ---


@app.post("/api/v1/admin/scraper/test", response_model=ScraperDiagnosticResponse, tags=["admin"])
def test_scraper_target_diagnostic(
    req: ScraperDiagnosticRequest,
    user: User = Depends(get_current_user),
) -> ScraperDiagnosticResponse:
    from .scraper.diagnostics import run_scraper_diagnostics

    report = run_scraper_diagnostics(
        url=req.url,
        strategy_override=req.strategy,
        max_pages=req.max_pages,
    )
    return ScraperDiagnosticResponse(
        target_url=report.target_url,
        strategy_used=report.strategy_used,
        platform_detected=report.platform_detected,
        execution_time_seconds=report.execution_time_seconds,
        jobs_discovered=report.jobs_discovered,
        jobs_accepted=report.jobs_accepted,
        jobs_rejected=report.jobs_rejected,
        confidence_score=report.confidence_score,
        status=report.status,
        errors=report.errors,
        sample_jobs=report.sample_jobs,
        http_status=report.http_status,
        content_type=report.content_type,
        rendering_mode=report.rendering_mode,
        discovery_method=report.discovery_method,
        failure_reason=report.failure_reason,
    )



