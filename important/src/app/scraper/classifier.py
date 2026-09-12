from datetime import datetime, timezone
import re
from urllib.parse import urlparse

from ..schemas_onboarding import PortalClassification
from .http_client import fetch_source, SourceFetchError
from .robots_checker import is_path_allowed_by_robots


def classify_portal(
    target_url: str,
    html: str | None = None,
    user_agent: str = "CompustBot/1.0",
) -> PortalClassification:
    """
    Lightweight heuristic classifier to inspect a target URL and its HTML structure,
    determine ATS / portal type, pagination pattern, and initial robots.txt compliance.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    # 1. Robots.txt check
    robots_ok = is_path_allowed_by_robots(target_url, user_agent=user_agent)
    robots_checked = now

    # 2. Acquire HTML if not provided
    if html is None:
        try:
            fetch_res = fetch_source(target_url, user_agent=user_agent)
            html = fetch_res.body
        except SourceFetchError:
            html = ""

    parsed = urlparse(target_url)
    domain_and_path = (parsed.netloc + parsed.path).lower()
    html_lower = html.lower() if html else ""

    portal_type = "unknown"
    pagination_style = "unknown"
    api_endpoints: list[str] = []
    suggested_strategy = "custom_html"
    recommendation = "Inspect DOM selectors and verify job cards."

    # Heuristic ATS detection
    if "myworkdayjobs.com" in domain_and_path or "workday" in html_lower and "wd3" in html_lower:
        portal_type = "workday"
        pagination_style = "offset_limit"
        suggested_strategy = "workday_json"
        recommendation = "Target uses Workday ATS. Utilize Workday JSON API endpoints with pagination offset/limit."
        # Extract potential API endpoints
        api_endpoints.append(f"{parsed.scheme}://{parsed.netloc}/wday/cxs/{parsed.path.strip('/')}/jobs")
    elif "smartrecruiters.com" in domain_and_path or "smartrecruiters" in html_lower:
        portal_type = "smartrecruiters"
        pagination_style = "offset_limit"
        suggested_strategy = "smartrecruiters_api"
        recommendation = "Target uses SmartRecruiters. Use public company postings API: https://api.smartrecruiters.com/v1/companies/{company}/postings"
        api_endpoints.append("https://api.smartrecruiters.com/v1/companies/{company}/postings")
    elif "ashbyhq.com" in domain_and_path or ("ashby" in html_lower and ("jobboard" in html_lower or "__appdata" in html_lower)):
        portal_type = "ashby"
        pagination_style = "single_page"
        suggested_strategy = "ashby_api"
        recommendation = "Target uses Ashby ATS. Utilize public Ashby job board API: https://api.ashbyhq.com/posting-api/job-board/{organization}"
        api_endpoints.append(f"https://api.ashbyhq.com/posting-api/job-board/{parsed.path.strip('/')}")
    elif "workable.com" in domain_and_path or "apply.workable" in domain_and_path or "window.careers" in html_lower:
        portal_type = "workable"
        pagination_style = "single_page"
        suggested_strategy = "workable_widget_api"
        recommendation = "Target uses Workable ATS. Utilize Workable public widget API: https://apply.workable.com/api/v1/widget/accounts/{account}"
        api_endpoints.append(f"https://apply.workable.com/api/v1/widget/accounts/{parsed.path.strip('/')}")
    elif "greenhouse.io" in domain_and_path or "greenhouse" in html_lower:
        portal_type = "greenhouse"
        pagination_style = "single_page"
        suggested_strategy = "greenhouse_api"
        recommendation = "Target uses Greenhouse. Use Greenhouse Job Board API: https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
        api_endpoints.append("https://boards-api.greenhouse.io/v1/boards/{board}/jobs")
    elif "taleo.net" in domain_and_path or "taleo" in html_lower:
        portal_type = "taleo"
        pagination_style = "page_param"
        suggested_strategy = "taleo_session"
        recommendation = "Target uses Oracle Taleo. Requires session cookie handshake and career section pagination."
    elif "turbo-stream" in html_lower or "turbo-frame" in html_lower:
        portal_type = "turbostream_html"
        pagination_style = "show_more_button"
        suggested_strategy = "inwi_like_turbostream"
        recommendation = "Target uses Hotwire/TurboStream partial updates. Follow show_more turbo-stream responses."
    elif "jobstream-api" in domain_and_path or "application/json" in html_lower:
        portal_type = "json_api"
        pagination_style = "page_param"
        suggested_strategy = "capgemini_like_api"
        recommendation = "Target exposes direct JSON vacancies API. Ingest candidates via structured REST payload."
    else:
        portal_type = "server_rendered_html"
        suggested_strategy = "orange_like_rel_next"

    # Heuristic pagination detection if not already pinned
    if pagination_style == "unknown":
        if 'rel="next"' in html_lower or "rel='next'" in html_lower:
            pagination_style = "rel_next"
        elif re.search(r"[?&](page|p|from)=\d+", html_lower) or "pagination" in html_lower:
            pagination_style = "page_param"
        elif "show_more" in html_lower or "load-more" in html_lower or "btn-more" in html_lower:
            pagination_style = "show_more_button"
        elif "offset=" in html_lower or "start=" in html_lower:
            pagination_style = "offset_limit"
        else:
            pagination_style = "single_page"

    # API hints scan
    found_api_hints = re.findall(r'["\'](/api/v\d+/[a-z0-9_\-/]+)["\']', html or "")
    if found_api_hints:
        api_endpoints.extend(list(dict.fromkeys(found_api_hints))[:5])

    return PortalClassification(
        portal_type=portal_type,
        pagination_style=pagination_style,
        api_endpoints_detected=api_endpoints,
        robots_txt_allowed=robots_ok,
        robots_txt_checked_at=robots_checked,
        recommendation=recommendation,
        suggested_strategy_type=suggested_strategy,
    )
