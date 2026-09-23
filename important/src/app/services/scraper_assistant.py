import json
import re
from typing import Any
from urllib.parse import urlparse
from sqlalchemy.orm import Session

from ..logging import get_logger
from ..models import Country
from ..repositories.jobs import resolve_or_create_company, persist_candidate
from ..scraper.orange_parser import JobCandidate
from .ai_service import generate_completion, check_ollama_runtime, OllamaError, OllamaUnavailableError

logger = get_logger("scraper.assistant")

COMPUST_SCRAPER_RULES_GROUNDING = """
Compust Scraper System Architecture & Heuristic Rules:
1. Universal 7-Layer Parser:
   - Layer 1: Platform-specific adapters (Ashby, Workable, Greenhouse, Lever, SmartRecruiters, Workday, Orange, Capgemini, Inwi, Deloitte)
   - Layer 2: Direct JSON / JSON API detection
   - Layer 3: Semantic schema.org/JobPosting microdata and JSON-LD
   - Layer 4: Job Title Intelligence (regex & multilingual keywords in heading/anchor hierarchy)
   - Layer 5: Semantic DOM cards with attributes (data-jk, data-job-id, role="article", class*="job-card")
   - Layer 6: Static anchor link heuristics with job path classification
   - Layer 7: Headless browser rendering fallback for SPA client-side rendering (React/Vue/Angular shells)

2. Candidate Validation & Filtering Rules:
   - generic_title: Excludes navigation/footer/utility links such as 'Careers', 'About Us', 'Contact', 'Privacy Policy', 'Search', 'All Jobs', 'Terms', 'Login'.
   - missing_title: Excludes candidate items where title is empty, null, or shorter than 3 characters.
   - non_job_link: Excludes URLs that link to departments, company blogs, generic homepages, or social media.
   - duplicate: Excludes positions matching fingerprint (title, normalized URL, company) already processed in the run or existing in the database.
   - invalid_url: Excludes unparseable, relative without base host, or javascript: void links.

3. Discrepancy & Content Signals:
   - content_signal_count measures raw job card markers in static HTML (e.g. data-jk, data-job-id, job-card classes).
   - When content_signal_count is high (>= 10) but accepted jobs or total detected is low (<= 1/3), a discrepancy is flagged indicating DOM listings exist but parser heuristics missed or filtered them.

4. Administrative Corrective Actions:
   - Keep Accepted Only: Proceed with cleanly validated jobs.
   - Force-Integrate All: Override heuristic rejection filters and persist rejected items with fallback metadata into the job directory.
"""


def _generate_deterministic_explanation(report_dict: dict[str, Any]) -> dict[str, Any]:
    """Generates a structured, domain-grounded explanation when Ollama is offline or times out."""
    target_url = report_dict.get("target_url", "")
    strategy = report_dict.get("strategy_used", "universal")
    platform = report_dict.get("platform_detected", "unknown")
    status = report_dict.get("status", "UNKNOWN")
    total_detected = report_dict.get("total_jobs_detected", 0)
    accepted = report_dict.get("jobs_accepted", 0)
    rejected = report_dict.get("jobs_rejected", 0)
    pages = report_dict.get("pages_crawled", 1)
    stop_reason = report_dict.get("stop_reason", "completed")
    content_signals = report_dict.get("content_signal_count", 0)
    discrepancy = report_dict.get("discrepancy_detected", False)
    discrepancy_details = report_dict.get("discrepancy_details")
    rejection_reasons = report_dict.get("rejection_reasons", {})

    # Build summary
    summary_parts = [
        f"Scraper executed in '{strategy}' strategy mode across {pages} crawled page(s)."
    ]
    if platform != "unknown":
        summary_parts.append(f"Target is hosted on {platform.title()} platform.")
    
    if total_detected > 0:
        summary_parts.append(
            f"Detected {total_detected} candidate listings: {accepted} accepted and {rejected} rejected (crawl stopped: {stop_reason})."
        )
    elif status == "SCRAPE_FAILED":
        failure = report_dict.get("failure_reason") or "Network fetch or parser error occurred."
        summary_parts.append(f"Scrape failed: {failure}")
    else:
        summary_parts.append("No candidate job elements were discovered on the target page.")

    summary = " ".join(summary_parts)

    # Rejection breakdown in human terms
    reasons_breakdown: dict[str, str] = {}
    explanation_map = {
        "generic_title": "Excluded utility/navigation links matching generic words (e.g., 'About', 'Careers', 'Contact').",
        "missing_title": "Excluded items with missing, empty, or sub-3-character job titles.",
        "non_job_link": "Excluded anchor links pointing to non-job sections or external portals.",
        "duplicate": "Excluded duplicate listings previously indexed in this run or database.",
        "invalid_url": "Excluded malformed or unresolvable job links.",
    }
    for reason, count in rejection_reasons.items():
        desc = explanation_map.get(reason, "Excluded by semantic validation filter.")
        reasons_breakdown[reason] = f"{count} item(s): {desc}"

    # Discrepancy explanation
    discrepancy_explanation: str | None = None
    if discrepancy:
        discrepancy_explanation = (
            f"Discrepancy Warning: {discrepancy_details or 'High HTML signal count vs low accepted rate'}. "
            f"Raw HTML contains {content_signals} job card markers, but only {total_detected} candidate cards "
            "were parsed. The page may use client-side rendering (SPA), custom component attributes, or shadow DOM."
        )

    # Recommendations
    recommendations: list[str] = []
    if discrepancy:
        recommendations.append(
            "Inspect raw DOM: If listings are rendered dynamically via JavaScript, switch to headless browser rendering."
        )
    if platform != "unknown" and strategy != platform:
        recommendations.append(
            f"Switch Strategy Mode to '{platform}' platform adapter for structured extraction."
        )
    if rejected > 0 and accepted == 0 and total_detected > 0:
        recommendations.append(
            "Review rejected candidates: If valid jobs were rejected by strict title filters, use 'Force-Integrate All' to override."
        )
    elif accepted > 0:
        recommendations.append(
            f"Proceed with 'Keep Accepted Only' to retain the {accepted} cleanly validated opportunities."
        )
    if not recommendations:
        recommendations.append("Verify target URL and check robots.txt / bot protection rules.")

    return {
        "summary": summary,
        "reasons_breakdown": reasons_breakdown,
        "discrepancy_explanation": discrepancy_explanation,
        "recommendations": recommendations,
        "provider": "deterministic",
    }


def explain_scraper_run(report_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Produces an LLM-assisted explanation of a scraper run, grounded in Compust scraper mechanics.
    Falls back gracefully to deterministic explanation if Ollama is unavailable or times out.
    """
    runtime = check_ollama_runtime()
    ollama_available = runtime.get("status") == "connected" and bool(runtime.get("models"))

    if not ollama_available:
        logger.info("Ollama is not available. Using deterministic scraper diagnostics explanation.")
        return _generate_deterministic_explanation(report_dict)

    # Prepare grounding prompt for Ollama
    system_prompt = (
        "You are the Compust Career & Scraper Diagnostics Assistant. "
        "Analyze the provided scraper run diagnostic report and explain the results clearly to an admin engineer. "
        "Adhere strictly to Compust scraper rules:\n"
        f"{COMPUST_SCRAPER_RULES_GROUNDING}\n\n"
        "Return ONLY a valid JSON object with the following structure:\n"
        "{\n"
        '  "summary": "Brief 2-3 sentence overview of the crawl outcome, strategy, and counts.",\n'
        '  "reasons_breakdown": {\n'
        '    "reason_code": "Concise human explanation of why items were rejected under this code"\n'
        "  },\n"
        '  "discrepancy_explanation": "Explanation of discrepancy between HTML card signals and parsed count, or null if none.",\n'
        '  "recommendations": ["Actionable next step 1", "Actionable next step 2"]\n'
        "}"
    )

    user_prompt = (
        f"Scraper Run Report:\n"
        f"- Target URL: {report_dict.get('target_url')}\n"
        f"- Strategy Used: {report_dict.get('strategy_used')}\n"
        f"- Platform Detected: {report_dict.get('platform_detected')}\n"
        f"- Crawl Status: {report_dict.get('status')}\n"
        f"- Pages Crawled: {report_dict.get('pages_crawled')} (Max: {report_dict.get('max_pages')})\n"
        f"- Stop Reason: {report_dict.get('stop_reason')}\n"
        f"- Content Signal Count: {report_dict.get('content_signal_count')}\n"
        f"- Total Jobs Detected: {report_dict.get('total_jobs_detected')}\n"
        f"- Jobs Accepted: {report_dict.get('jobs_accepted')}\n"
        f"- Jobs Rejected: {report_dict.get('jobs_rejected')}\n"
        f"- Rejection Reasons Breakdown: {json.dumps(report_dict.get('rejection_reasons', {}))}\n"
        f"- Discrepancy Detected: {report_dict.get('discrepancy_detected')}\n"
        f"- Discrepancy Details: {report_dict.get('discrepancy_details')}\n"
        f"- Errors / Warnings: {report_dict.get('errors')}\n"
        f"- Sample Rejected Items: {json.dumps(report_dict.get('rejected_items', [])[:5])}\n"
    )

    try:
        raw_output = generate_completion(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            timeout_seconds=20.0,
        )
        # Extract JSON from code block if enclosed
        match = re.search(r"\{.*\}", raw_output, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            return {
                "summary": parsed.get("summary") or "Scraper analysis completed.",
                "reasons_breakdown": parsed.get("reasons_breakdown") or {},
                "discrepancy_explanation": parsed.get("discrepancy_explanation"),
                "recommendations": parsed.get("recommendations") or [],
                "provider": "ollama",
            }
        else:
            logger.warning("Ollama output did not contain valid JSON. Falling back to deterministic explanation.")
            return _generate_deterministic_explanation(report_dict)

    except (OllamaError, OllamaUnavailableError, json.JSONDecodeError, Exception) as exc:
        logger.warning(f"Ollama scraper explanation failed ({exc}). Falling back to deterministic explanation.")
        return _generate_deterministic_explanation(report_dict)


def apply_scraper_decision(
    db: Session,
    target_url: str,
    decision: str,
    rejected_items: list[dict[str, Any]],
    user_id: int | None = None,
) -> dict[str, Any]:
    """
    Applies the administrative decision for a scraper run:
    - 'keep_accepted': Confirms accepted jobs only, discarding rejected candidates.
    - 'force_integrate_all': Overrides heuristic rejection filters and persists rejected items into Job records.
    """
    clean_decision = (decision or "").strip().lower()

    if clean_decision == "keep_accepted":
        return {
            "status": "success",
            "action": "keep_accepted",
            "integrated_count": 0,
            "message": "Retained cleanly accepted jobs only. Rejected candidate items were not imported.",
        }

    if clean_decision == "force_integrate_all":
        if not rejected_items:
            return {
                "status": "success",
                "action": "force_integrate_all",
                "integrated_count": 0,
                "message": "No rejected candidate items to integrate.",
            }

        # Derive fallback company name from domain if missing
        parsed_target = urlparse(target_url)
        domain_name = parsed_target.netloc.replace("www.", "").split(".")[0].title() or "Target Organization"

        # Resolve default country
        default_country = db.query(Country).first()
        default_country_id = default_country.id if default_country else 1

        integrated_count = 0
        for item in rejected_items:
            title = (item.get("title") or "").strip()
            if not title:
                title = "Candidate Job Posting"

            raw_url = item.get("url") or item.get("job_url") or target_url
            company_name = item.get("company") or domain_name
            location = item.get("location") or "Unspecified Location"
            description = (
                item.get("description")
                or f"<p>Candidate job posting imported via administrative force-integration override from {target_url}.</p>"
            )

            company = resolve_or_create_company(db, name=company_name, default_country_id=default_country_id)
            
            cand = JobCandidate(
                title=title,
                job_url=raw_url,
                external_job_id=str(item.get("external_job_id") or abs(hash(f"{title}_{raw_url}"))),
                location=location,
                description=description,
            )

            try:
                persist_candidate(
                    db,
                    company_id=company.id,
                    country_id=default_country_id,
                    source="admin_scraper_override",
                    candidate=cand,
                    commit=False,
                )
                integrated_count += 1
            except Exception as exc:
                logger.warning(f"Could not force-integrate item {title}: {exc}")

        if hasattr(db, "commit"):
            db.commit()

        return {
            "status": "success",
            "action": "force_integrate_all",
            "integrated_count": integrated_count,
            "message": f"Successfully force-integrated {integrated_count} candidate item(s) into the job directory.",
        }

    raise ValueError(f"Unknown scraper decision: {decision}. Must be 'keep_accepted' or 'force_integrate_all'.")
