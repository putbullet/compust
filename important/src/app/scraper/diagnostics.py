import time
from dataclasses import dataclass, field
from typing import Any

from ..models import Company, ScrapeTarget
from .crawler import crawl_pages
from .http_client import fetch_source, SourceFetchError
from .registry import get_strategy_for_target, get_strategy_by_name, ScraperStrategy


@dataclass(frozen=True)
class DiagnosticReport:
    target_url: str
    strategy_used: str
    platform_detected: str | None
    execution_time_seconds: float
    jobs_discovered: int
    jobs_accepted: int
    jobs_rejected: int
    confidence_score: float  # 0.0 to 1.0
    status: str              # SUCCESS, PARTIAL_SUCCESS, NO_JOBS_FOUND, SCRAPE_FAILED
    errors: list[str] = field(default_factory=list)
    sample_jobs: list[dict[str, Any]] = field(default_factory=list)
    http_status: int | None = None
    content_type: str | None = None
    rendering_mode: str | None = None
    discovery_method: str | None = None
    failure_reason: str | None = None


def detect_target_platform(url: str) -> str:
    """Heuristically identify the ATS or platform hosting the job URL."""
    url_lower = (url or "").lower()
    if "ashbyhq.com" in url_lower or "jobs.ashby" in url_lower:
        return "ashby"
    if "workable.com" in url_lower or "apply.workable" in url_lower:
        return "workable"
    if "greenhouse.io" in url_lower or "boards.greenhouse" in url_lower:
        return "greenhouse"
    if "lever.co" in url_lower:
        return "lever"
    if "smartrecruiters.com" in url_lower:
        return "smartrecruiters"
    if "myworkdayjobs.com" in url_lower or "workday" in url_lower:
        return "workday"
    if "orange.jobs" in url_lower:
        return "orange"
    if "capgemini.com" in url_lower:
        return "capgemini"
    if "inwi.ma" in url_lower:
        return "inwi"
    if "deloitte.com" in url_lower:
        return "deloitte"
    if "teamtailor.com" in url_lower or "teamtailor" in url_lower:
        return "teamtailor"
    return "unknown"


def run_scraper_diagnostics(
    url: str,
    strategy_override: str | None = None,
    max_pages: int = 1,
) -> DiagnosticReport:
    """
    Dry-run diagnostic test for a scrape target or career URL.
    Executes discovery and parsing without writing to the database.
    """
    start_time = time.time()
    errors: list[str] = []
    platform = detect_target_platform(url)
    if strategy_override and platform != "unknown" and strategy_override != platform:
        errors.append(f"Notice: The selected strategy '{strategy_override}' does not match the detected platform '{platform}'. This portal is hosted on {platform.title()}, not {strategy_override.title()}.")

    # Construct lightweight mock target
    target = ScrapeTarget(id=0, company_id=0, url=url, type=platform if platform != "unknown" else "careers", active=True)
    strategy = get_strategy_for_target(target, preferred_strategy=strategy_override)

    if not strategy:
        duration = round(time.time() - start_time, 3)
        return DiagnosticReport(
            target_url=url,
            strategy_used="none",
            platform_detected=platform,
            execution_time_seconds=duration,
            jobs_discovered=0,
            jobs_accepted=0,
            jobs_rejected=0,
            confidence_score=0.0,
            status="SCRAPE_FAILED",
            errors=["Unable to resolve a scraper strategy for this URL."],
            failure_reason="Unable to resolve a scraper strategy for this URL.",
        )

    try:
        crawl_res = crawl_pages(url, strategy, max_pages=max_pages)
        errors.extend(crawl_res.errors)
        discovered = len(crawl_res.jobs)

        # Validate candidates
        accepted = []
        rejected = 0
        for job in crawl_res.jobs:
            if job.title and len(job.title) >= 3 and job.job_url:
                accepted.append(job)
            else:
                rejected += 1

        duration = round(time.time() - start_time, 3)

        if len(accepted) > 0:
            confidence = 1.0 if not errors else 0.75
            status = "SUCCESS" if not errors else "PARTIAL_SUCCESS"
        else:
            confidence = 0.0
            status = "NO_JOBS_FOUND"

        samples = [
            {
                "title": j.title,
                "location": j.location,
                "job_url": j.job_url,
                "employment_type": j.employment_type,
                "skills_count": len(j.skills),
            }
            for j in accepted[:5]
        ]

        http_status = crawl_res.initial_source.status_code if crawl_res.initial_source else None
        content_type = crawl_res.initial_source.content_type if crawl_res.initial_source else None

        rendering_mode = "static_html"
        if content_type and "json" in content_type.lower():
            rendering_mode = "json_api"
        elif crawl_res.initial_source and any(
            m in crawl_res.initial_source.body.lower()
            for m in (
                "you need to enable javascript",
                "enable javascript to run this app",
                "javascript is required",
                "__next_data__",
                "window.__initial_state__",
            )
        ):
            rendering_mode = "spa_client_rendered"

        discovery_method = None
        if len(accepted) > 0:
            if strategy.name in ("ashby", "workable", "greenhouse", "lever", "smartrecruiters", "workday", "orange", "capgemini", "inwi", "deloitte"):
                discovery_method = f"{strategy.name}_platform_adapter"
            elif strategy.name == "universal":
                if content_type and "json" in content_type.lower():
                    discovery_method = "direct_json"
                elif crawl_res.initial_source and ('itemtype="http://schema.org/JobPosting"' in crawl_res.initial_source.body or 'application/ld+json' in crawl_res.initial_source.body):
                    discovery_method = "json_ld_or_microdata"
                else:
                    discovery_method = "semantic_cards_or_heuristics"

        failure_reason = None
        if status in ("NO_JOBS_FOUND", "SCRAPE_FAILED"):
            for err in errors:
                if "Client-rendered SPA shell" in err:
                    failure_reason = "Client-rendered SPA shell detected. The page requires JavaScript rendering or uses a client-side API/widget. Consider checking for public ATS endpoints or rendering with a headless browser."
                    break
                elif "Iframe detected" in err:
                    failure_reason = "Iframe detected on page. Job listings might be embedded in an external frame or ATS widget."
                    break
            if not failure_reason and errors:
                failure_reason = errors[0]
            elif not failure_reason:
                failure_reason = "Universal parser found 0 job listings matching semantic structures or cards in static HTML."

        return DiagnosticReport(
            target_url=url,
            strategy_used=strategy.name,
            platform_detected=platform,
            execution_time_seconds=duration,
            jobs_discovered=discovered,
            jobs_accepted=len(accepted),
            jobs_rejected=rejected,
            confidence_score=confidence,
            status=status,
            errors=errors,
            sample_jobs=samples,
            http_status=http_status,
            content_type=content_type,
            rendering_mode=rendering_mode,
            discovery_method=discovery_method,
            failure_reason=failure_reason,
        )
    except SourceFetchError as exc:
        duration = round(time.time() - start_time, 3)
        return DiagnosticReport(
            target_url=url,
            strategy_used=strategy.name,
            platform_detected=platform,
            execution_time_seconds=duration,
            jobs_discovered=0,
            jobs_accepted=0,
            jobs_rejected=0,
            confidence_score=0.0,
            status="SCRAPE_FAILED",
            errors=[f"Network fetch error: {exc}"],
            failure_reason=f"Network fetch error: {exc}",
        )
    except Exception as exc:
        duration = round(time.time() - start_time, 3)
        return DiagnosticReport(
            target_url=url,
            strategy_used=strategy.name,
            platform_detected=platform,
            execution_time_seconds=duration,
            jobs_discovered=0,
            jobs_accepted=0,
            jobs_rejected=0,
            confidence_score=0.0,
            status="SCRAPE_FAILED",
            errors=[f"Execution exception: {exc}"],
            failure_reason=f"Execution exception: {exc}",
        )
