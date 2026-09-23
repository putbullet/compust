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
    browser_rendered: bool = False
    detected_result_count: int | None = None
    pages_crawled: int = 1
    total_jobs_detected: int = 0
    rejection_reasons: dict[str, int] = field(default_factory=dict)
    rejected_items: list[dict[str, Any]] = field(default_factory=list)
    max_pages: int = 3
    stop_reason: str = "completed"
    content_signal_count: int = 0
    discrepancy_detected: bool = False
    discrepancy_details: str | None = None
    explanation: str | None = None
    suggested_action: str | None = None


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
    max_pages: int = 3,
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

        # Validate candidates with granular rejection reasons (C1)
        accepted = []
        rejected_items = []
        rejection_reasons: dict[str, int] = {}
        seen_keys = set()

        generic_titles = {
            "careers", "career", "about", "about us", "contact", "contact us",
            "privacy", "privacy policy", "terms", "terms of service", "home",
            "search", "all jobs", "jobs", "login", "sign in", "apply", "menu",
        }

        for job in crawl_res.jobs:
            title_clean = (job.title or "").strip()
            job_comp = getattr(job, "company", None)
            comp_clean = (job_comp or "").strip()
            loc_clean = (job.location or "").strip()
            dedup_key = f"{title_clean.lower()}|{comp_clean.lower()}|{loc_clean.lower()}"

            if dedup_key in seen_keys:
                rejection_reasons["dedup_hash_match"] = rejection_reasons.get("dedup_hash_match", 0) + 1
                rejected_items.append({
                    "title": job.title,
                    "company": job_comp,
                    "location": job.location,
                    "job_url": job.job_url,
                    "reason": "dedup_hash_match",
                    "details": "Normalized title, company, and location matched an already seen listing in this run.",
                })
                continue
            seen_keys.add(dedup_key)

            if not title_clean or len(title_clean) < 3:
                rejection_reasons["missing_title"] = rejection_reasons.get("missing_title", 0) + 1
                rejected_items.append({
                    "title": job.title or "<Empty>",
                    "company": job_comp,
                    "location": job.location,
                    "job_url": job.job_url,
                    "reason": "missing_title",
                    "details": "Job title was missing or shorter than 3 characters.",
                })
            elif title_clean.lower() in generic_titles:
                rejection_reasons["generic_title"] = rejection_reasons.get("generic_title", 0) + 1
                rejected_items.append({
                    "title": job.title,
                    "company": job_comp,
                    "location": job.location,
                    "job_url": job.job_url,
                    "reason": "generic_title",
                    "details": f"Job title '{job.title}' matched generic navigation or boilerplate label.",
                })
            elif not job.job_url:
                rejection_reasons["missing_job_url"] = rejection_reasons.get("missing_job_url", 0) + 1
                rejected_items.append({
                    "title": job.title,
                    "company": job_comp,
                    "location": job.location,
                    "job_url": job.job_url,
                    "reason": "missing_job_url",
                    "details": "No direct or canonical apply URL was extracted for this listing.",
                })
            else:
                accepted.append(job)

        rejected_count = len(rejected_items)
        duration = round(time.time() - start_time, 3)

        if len(accepted) > 0:
            confidence = 1.0 if not errors else 0.75
            status = "SUCCESS" if not errors else "PARTIAL_SUCCESS"
        else:
            confidence = 0.0
            status = "NO_JOBS_FOUND"

        total_detected = len(crawl_res.jobs)
        content_signal = getattr(crawl_res, "content_signal_count", 0)
        discrepancy = False
        discrepancy_details = None

        if content_signal >= 10 and total_detected <= content_signal // 3:
            discrepancy = True
            discrepancy_details = (
                f"Page content signal detected ~{content_signal} potential job cards in the HTML, "
                f"but parser only extracted {total_detected} structured candidate(s). "
                f"Some listings may be in custom or non-standard container elements."
            )
        elif crawl_res.detected_result_count and crawl_res.detected_result_count >= 10 and total_detected <= crawl_res.detected_result_count // 3:
            discrepancy = True
            discrepancy_details = (
                f"Target page stated {crawl_res.detected_result_count} available jobs, "
                f"but parser only extracted {total_detected} candidate(s)."
            )

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

        is_browser_rendered = (
            getattr(crawl_res.initial_source, "is_rendered", False)
            or any("[Browser Fallback]" in e for e in crawl_res.errors)
        )

        rendering_mode = "static_html"
        if is_browser_rendered:
            rendering_mode = "spa_client_rendered"
        elif content_type and "json" in content_type.lower():
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
                if any(getattr(j, "discovery_source", None) == "job_title_intelligence" for j in accepted):
                    discovery_method = "job_title_intelligence_discovery"
                elif content_type and "json" in content_type.lower():
                    discovery_method = "direct_json"
                elif crawl_res.initial_source and ('itemtype="http://schema.org/JobPosting"' in crawl_res.initial_source.body or 'application/ld+json' in crawl_res.initial_source.body):
                    discovery_method = "json_ld_or_microdata"
                else:
                    discovery_method = "semantic_cards_or_heuristics"

            if is_browser_rendered and discovery_method:
                discovery_method = f"{discovery_method} (browser_rendered)"

        failure_reason = None
        if status in ("NO_JOBS_FOUND", "SCRAPE_FAILED"):
            for err in errors:
                if "Client-rendered SPA shell" in err:
                    failure_reason = "Client-rendered SPA shell detected. The page requires JavaScript rendering or uses a client-side API/widget. Consider checking for public ATS endpoints or rendering with a headless browser."
                    break
                elif "Iframe detected" in err:
                    failure_reason = "Iframe detected on page. Job listings might be embedded in an external frame or ATS widget."
                    break
                elif "Cloudflare WAF challenge" in err:
                    failure_reason = (
                        "Cloudflare anti-bot protection is active on this page. The site requires "
                        "JavaScript execution in a real browser (challenge-response) to access job listings. "
                        "Standard HTTP scraping is permanently blocked by the WAF. "
                        "Suggestion: check whether the company hosts an ATS on a separate subdomain "
                        "(e.g., jobs.ashbyhq.com, boards.greenhouse.io, apply.workable.com) and add "
                        "that URL as the scrape target instead."
                    )
                    break
                elif "HTTP 403" in err or "source restricted" in err:
                    failure_reason = (
                        "HTTP 403 Forbidden. The server is blocking automated requests. "
                        "The site may enforce bot protection, require authentication, or use a WAF. "
                        "Try adding a direct ATS link (e.g., Greenhouse, Lever, Workable, Ashby) instead of the company's own careers page."
                    )
                    break
            if not failure_reason and errors:
                failure_reason = errors[0]
            elif not failure_reason:
                if crawl_res.detected_result_count is not None:
                    if crawl_res.detected_result_count == 0:
                        failure_reason = "Career page explicitly reported 0 matching results for the current search or filters."
                    else:
                        failure_reason = (
                            f"Career page indicated {crawl_res.detected_result_count} available results, but universal "
                            "parser could not extract job cards (possible client-rendered listing or dynamic DOM structure)."
                        )
                else:
                    failure_reason = "Universal parser found 0 job listings matching semantic structures or cards in static HTML."

        return DiagnosticReport(
            target_url=url,
            strategy_used=strategy.name,
            platform_detected=platform,
            execution_time_seconds=duration,
            jobs_discovered=discovered,
            jobs_accepted=len(accepted),
            jobs_rejected=rejected_count,
            confidence_score=confidence,
            status=status,
            errors=errors,
            sample_jobs=samples,
            http_status=http_status,
            content_type=content_type,
            rendering_mode=rendering_mode,
            discovery_method=discovery_method,
            failure_reason=failure_reason,
            browser_rendered=is_browser_rendered,
            detected_result_count=crawl_res.detected_result_count,
            pages_crawled=crawl_res.pages_crawled,
            total_jobs_detected=total_detected,
            rejection_reasons=rejection_reasons,
            rejected_items=rejected_items[:10],
            max_pages=max_pages,
            stop_reason=getattr(crawl_res, "stop_reason", "completed"),
            content_signal_count=content_signal,
            discrepancy_detected=discrepancy,
            discrepancy_details=discrepancy_details,
        )

    except SourceFetchError as exc:
        duration = round(time.time() - start_time, 3)
        exc_msg = str(exc)
        # Derive a helpful failure_reason from the error text
        if "Cloudflare WAF challenge" in exc_msg:
            fetch_failure_reason = (
                "Cloudflare anti-bot protection is active on this page. The site requires "
                "JavaScript execution in a real browser (challenge-response) to access job listings. "
                "Standard HTTP scraping is permanently blocked by the WAF. "
                "Suggestion: check whether the company hosts an ATS on a separate subdomain "
                "(e.g., jobs.ashbyhq.com, boards.greenhouse.io, apply.workable.com) and add "
                "that URL as the scrape target instead."
            )
        elif exc.status_code == 403 or "403" in exc_msg or "source restricted" in exc_msg:
            fetch_failure_reason = (
                "HTTP 403 Forbidden. The server is blocking automated requests. "
                "The site may enforce bot protection, require authentication, or use a WAF. "
                "Try adding a direct ATS link (e.g., Greenhouse, Lever, Workable, Ashby) instead of the company's own careers page."
            )
        else:
            fetch_failure_reason = f"Network fetch error: {exc_msg}"
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
            errors=[f"Network fetch error: {exc_msg}"],
            failure_reason=fetch_failure_reason,
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
