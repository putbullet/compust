import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .http_client import FetchedSource
from .orange_parser import JobCandidate, ParseResult
from .platforms.ashby import AshbyAdapter
from .platforms.greenhouse import GreenhouseAdapter
from .platforms.lever import LeverAdapter
from .platforms.smartrecruiters import SmartRecruitersAdapter
from .platforms.workday import WorkdayAdapter
from .platforms.workable import WorkableAdapter
from .platforms.teamtailor import TeamtailorAdapter
from .sanitizer import sanitize_html, sanitize_plain_text
from .url_normalizer import normalize_url
from .vocabulary import normalize_employment_type, normalize_remote_type, SKILL_SYNONYMS

# Multilingual keywords for non-job link filtering
DISALLOWED_LINK_PATTERNS = [
    r"privacy[-_ ]?policy",
    r"terms[-_ ]?(?:of[-_ ]?service|conditions|use)",
    r"cookie[-_ ]?(?:policy|settings|notice)",
    r"contact[-_ ]?(?:us)?",
    r"about[-_ ]?(?:us|our\s+company)?",
    r"login|sign[-_ ]?in|register|auth",
    r"mentions[-_ ]?l[eé]gales",
    r"politique[-_ ]?de[-_ ]?confidentialit[eé]",
    r"donn[eé]es[-_ ]?personnelles",
    r"qui[-_ ]?sommes[-_ ]?nous",
    r"impressum|datenschutz|kontakt",
    r"aviso[-_ ]?legal|sobre[-_ ]?nosotros",
    r"formation[-_ ]?et[-_ ]?[eé]volution",
    r"[eé]voluer[-_ ]?au[-_ ]?sein",
    r"life[-_ ]?at|deloitte[-_ ]?life",
    r"notre[-_ ]?(?:engagement|culture|vision|histoire)",
    r"development/|cmp-teaser",
    r"/departments?/",
    r"/categories?/",
    r"/teams?/",
    r"/locations?/",
    r"/connect(?:/|\b)",
]

# Section headings to exclude from job candidate titles
EXCLUDED_SECTION_HEADINGS = [
    r"join\s+(?:our\s+)?team",
    r"why\s+(?:join|work\s+with)\s+us",
    r"don'?t\s+see\s+(?:your\s+)?(?:role|position|opening)",
    r"our\s+values|our\s+mission|our\s+culture|who\s+we\s+are",
    r"about\s+us|about\s+the\s+company|life\s+at",
    r"benefits\s+(?:&|and)?\s+perks|working\s+here",
    r"open\s+positions|current\s+openings|career\s+opportunities",
    r"frequently\s+asked\s+questions|faq",
    r"equal\s+opportunity|diversity\s+(?:&|and)\s+inclusion",
    r"^\s*\d+\s+(?:open\s+)?(?:jobs?|positions?|vacancies|openings?|roles?|opportunities)",
    r"all\s+(?:jobs?|positions?|vacancies|openings?|roles?)",
    r"filter\s+by",
]

CAREER_PATH_INDICATORS = [
    r"jobs?", r"careers?", r"vacanc(?:y|ies)", r"openings?", r"positions?", r"opportunit(?:y|ies)",
    r"emplois?", r"offres?", r"recrutements?", r"postes?",
    r"karriere", r"stellen?",
]

COMMON_SKILLS = sorted(list(set(SKILL_SYNONYMS.values())))


def is_plausible_job_link(href: str, text: str) -> bool:
    """Validate that an anchor link is plausibly a job detail link and not a policy/nav link."""
    if not href or href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
        return False

    parsed_href = urlparse(href)
    norm_path = parsed_href.path.rstrip("/").lower()
    if norm_path in ("", "/jobs", "/careers", "/openings", "/positions", "/vacancies", "/emploi", "/offres"):
        return False

    combined = f"{href} {text}".lower()

    # Reject obvious boilerplate / legal / navigation links
    for pattern in DISALLOWED_LINK_PATTERNS:
        if re.search(pattern, combined):
            return False

    # Title / link text length check
    cleaned_text = re.sub(r"\s+", " ", text).strip()
    if len(cleaned_text) < 3 or len(cleaned_text) > 160:
        return False

    # Check if text is just navigation numbers or arrows
    if re.match(r"^[\d\s><»«\-\|\.]+$", cleaned_text):
        return False

    # Reject number counter headers such as "5 jobs"
    if re.match(r"^\d+\s+(?:jobs?|positions?|vacancies|openings?|roles?)$", cleaned_text, re.I):
        return False

    return True


def extract_json_ld_jobs(soup: BeautifulSoup, source_url: str) -> list[JobCandidate]:
    """Extract Schema.org JobPosting structured data from JSON-LD script tags."""
    candidates: list[JobCandidate] = []
    scripts = soup.select("script[type='application/ld+json']")

    for script in scripts:
        raw_content = script.get_text().strip()
        if not raw_content:
            continue
        try:
            data = json.loads(raw_content)
        except Exception:
            continue

        items = data if isinstance(data, list) else [data]
        # Handle @graph wrapper
        expanded_items: list[dict] = []
        for it in items:
            if isinstance(it, dict):
                if "@graph" in it and isinstance(it["@graph"], list):
                    expanded_items.extend([g for g in it["@graph"] if isinstance(g, dict)])
                else:
                    expanded_items.append(it)

        for item in expanded_items:
            item_type = item.get("@type")
            if item_type != "JobPosting" and not (isinstance(item_type, list) and "JobPosting" in item_type):
                continue

            title = sanitize_plain_text(item.get("title") or "")
            if not title or len(title) < 3:
                continue

            raw_url = item.get("url") or item.get("sameAs") or source_url
            job_url = normalize_url(urljoin(source_url, raw_url))
            ext_id = str(item.get("identifier") or item.get("jobImmediateHire") or item.get("id") or "")
            if not ext_id or ext_id == "None":
                ext_id = re.sub(r"\W+", "_", urlparse(job_url).path.strip("/")) or title[:30]

            desc = sanitize_html(item.get("description") or "")
            location = None
            job_loc = item.get("jobLocation")
            if isinstance(job_loc, dict):
                addr = job_loc.get("address")
                if isinstance(addr, dict):
                    loc_parts = [addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry")]
                    location = ", ".join([str(p) for p in loc_parts if p])
                elif isinstance(addr, str):
                    location = addr

            emp_type = item.get("employmentType")
            if isinstance(emp_type, list):
                emp_type = emp_type[0] if emp_type else None
            clean_emp = normalize_employment_type(str(emp_type)) if emp_type else None

            posted_at = None
            date_str = item.get("datePosted")
            if isinstance(date_str, str):
                try:
                    posted_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            remote_type = None
            loc_type = str(item.get("jobLocationType") or "")
            if "telecommute" in loc_type.lower() or "remote" in loc_type.lower():
                remote_type = "remote"
            elif desc:
                remote_type = normalize_remote_type(desc)

            sal_min: float | None = None
            sal_max: float | None = None
            sal_curr: str | None = None
            sal_period: str | None = None

            base_sal = item.get("baseSalary")
            if isinstance(base_sal, dict):
                sal_curr = base_sal.get("currency")
                val = base_sal.get("value")
                if isinstance(val, dict):
                    sal_min = float(val["minValue"]) if val.get("minValue") is not None else None
                    sal_max = float(val["maxValue"]) if val.get("maxValue") is not None else None
                    sal_period = val.get("unitText")
                elif val is not None:
                    try:
                        sal_min = float(val)
                    except (ValueError, TypeError):
                        pass

            detected_skills = []
            if desc:
                desc_lower = desc.lower()
                for skill in COMMON_SKILLS:
                    if re.search(rf"\b{re.escape(skill.lower())}\b", desc_lower):
                        detected_skills.append(skill)

            candidates.append(
                JobCandidate(
                    title=title,
                    job_url=job_url,
                    external_job_id=ext_id,
                    location=location,
                    description=desc,
                    employment_type=clean_emp,
                    remote_type=remote_type,
                    posted_at=posted_at,
                    skills=detected_skills,
                    salary_min=sal_min,
                    salary_max=sal_max,
                    salary_currency=sal_curr,
                    salary_period=sal_period,
                )
            )

    return candidates


def extract_semantic_cards_jobs(soup: BeautifulSoup, source_url: str) -> list[JobCandidate]:
    """
    Extract jobs from semantic card containers containing headings (h2, h3, h4)
    paired with employment signals (Remote, Full-time, etc.) and an application action.
    This resolves company-hosted career pages like Rankly Media.
    """
    candidates: list[JobCandidate] = []
    seen_titles: set[str] = set()

    # Find card-like containers containing headings and employment/action signals
    potential_cards = soup.find_all(lambda el: el.name in ("div", "article", "section", "li") and (
        el.find(["h2", "h3", "h4", "h5"]) is not None and (
            el.find("a", string=re.compile(r"apply|postuler|view|details|contact|rejoindre|candidater", re.I)) is not None or
            el.find(class_=re.compile(r"btn|button|link|action|apply", re.I)) is not None or
            re.search(r"\b(remote|hybrid|full[- ]?time|part[- ]?time|contract|cdi|cdd|internship|stage|freelance)\b", el.get_text(), re.I)
        )
    ))

    # Keep only leaf cards (skip ancestors containing other candidate cards)
    leaf_cards = []
    for c in potential_cards:
        has_child = any(other != c and other in c.descendants for other in potential_cards)
        if not has_child:
            leaf_cards.append(c)

    for card in leaf_cards:
        heading = card.find(["h2", "h3", "h4", "h5"])
        if not heading:
            continue
        title = sanitize_plain_text(heading.get_text(" ", strip=True))
        if not title or len(title) < 3:
            continue

        # Skip non-job section headings
        if any(re.search(pat, title, re.I) for pat in EXCLUDED_SECTION_HEADINGS):
            continue

        title_norm = title.lower().strip()
        if title_norm in seen_titles:
            continue

        raw_text = card.get_text(" ", strip=True)
        has_emp_signal = bool(re.search(r"\b(remote|hybrid|full[- ]?time|part[- ]?time|contract|freelance|cdi|cdd|internship|stage)\b", raw_text, re.I))
        link = card.find("a", href=True)
        has_apply_link = bool(link and re.search(r"apply|postuler|contact|join|rejoindre|candidater", link.get_text(" ", strip=True), re.I))

        # Must have at least one strong job indicator (employment signal or explicit apply action)
        if not (has_emp_signal or has_apply_link):
            continue

        seen_titles.add(title_norm)
        slug = re.sub(r"\W+", "-", title.lower()).strip("-")
        href = link["href"] if link else ""

        # Determine job URL:
        # If the card links to a generic contact or apply anchor, anchor to the card position
        if not href or "/contact" in href.lower() or href.startswith("#") or href.startswith("mailto:"):
            job_url = normalize_url(f"{source_url.split('#')[0]}#{slug}")
        else:
            job_url = normalize_url(urljoin(source_url, href))

        ext_id = slug or re.sub(r"\W+", "_", urlparse(job_url).path.strip("/")) or title[:30]

        # Location hint
        location = None
        loc_el = card.select_one("[class*='location'], [class*='city'], [class*='place'], [class*='lieu']")
        if loc_el:
            location = sanitize_plain_text(loc_el.get_text(" ", strip=True))
        elif re.search(r"\b(remote|t[eé]l[eé]travail)\b", raw_text, re.I):
            location = "Remote"

        emp_type = normalize_employment_type(raw_text)
        rem_type = normalize_remote_type(raw_text)

        # Department hint
        dept_el = card.select_one("[class*='dept'], [class*='department'], [class*='team']")
        dept = sanitize_plain_text(dept_el.get_text(" ", strip=True)) if dept_el else None

        # Skills detection
        detected_skills = []
        raw_lower = raw_text.lower()
        for skill in COMMON_SKILLS:
            if re.search(rf"\b{re.escape(skill.lower())}\b", raw_lower):
                detected_skills.append(skill)

        # Build clean description
        desc_html = card.decode_contents() if hasattr(card, "decode_contents") else f"<p>{raw_text}</p>"

        candidates.append(
            JobCandidate(
                title=title,
                job_url=job_url,
                external_job_id=ext_id,
                location=location,
                description=sanitize_html(desc_html),
                employment_type=emp_type,
                remote_type=rem_type,
                department=dept,
                skills=detected_skills,
            )
        )

    return candidates


def extract_embedded_state_jobs(soup: BeautifulSoup, source_url: str) -> list[JobCandidate]:
    """Inspect scripts and serialized application state (Next.js __NEXT_DATA__, window.__INITIAL_STATE__, etc.)."""
    candidates: list[JobCandidate] = []
    seen_ids: set[str] = set()

    for sc in soup.find_all("script"):
        txt = sc.get_text().strip()
        if not txt:
            continue

        # Next.js __NEXT_DATA__
        if sc.get("id") == "__NEXT_DATA__":
            try:
                data = json.loads(txt)
                # Search pageProps for jobs list
                page_props = data.get("props", {}).get("pageProps", {})
                raw_list = page_props.get("jobs") or page_props.get("postings") or page_props.get("openings") or []
                if isinstance(raw_list, list):
                    for j in raw_list:
                        if isinstance(j, dict) and (j.get("title") or j.get("jobTitle")):
                            title = sanitize_plain_text(j.get("title") or j.get("jobTitle") or "")
                            jid = str(j.get("id") or j.get("slug") or title[:30])
                            if jid in seen_ids or not title:
                                continue
                            seen_ids.add(jid)
                            job_url = normalize_url(urljoin(source_url, j.get("url") or j.get("absolute_url") or f"#{jid}"))
                            candidates.append(
                                JobCandidate(
                                    title=title,
                                    job_url=job_url,
                                    external_job_id=jid,
                                    location=j.get("location"),
                                    description=sanitize_html(j.get("description") or f"<p>{title}</p>"),
                                    employment_type=normalize_employment_type(str(j.get("employmentType") or "")),
                                    remote_type=normalize_remote_type(str(j.get("workplaceType") or j.get("location") or "")),
                                )
                            )
            except Exception:
                pass

        # Generic JSON state assignments (e.g. window.__STATE__ = { ... })
        if "window." in txt and ("jobs" in txt.lower() or "postings" in txt.lower()):
            m = re.search(r"window\.[a-zA-Z0-9_]+\s*=\s*(\{.+?\});", txt, re.DOTALL)
            if m:
                try:
                    obj = json.loads(m.group(1))
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and ("title" in v[0] or "jobTitle" in v[0]):
                                for item in v:
                                    t = sanitize_plain_text(item.get("title") or item.get("jobTitle") or "")
                                    if t and len(t) >= 3:
                                        jid = str(item.get("id") or item.get("shortcode") or t[:30])
                                        if jid in seen_ids:
                                            continue
                                        seen_ids.add(jid)
                                        jurl = normalize_url(urljoin(source_url, item.get("url") or f"#{jid}"))
                                        candidates.append(
                                            JobCandidate(
                                                title=t,
                                                job_url=jurl,
                                                external_job_id=jid,
                                                location=item.get("location"),
                                                description=f"<p>{t}</p>",
                                            )
                                        )
                except Exception:
                    pass

    return candidates


def extract_html_card_jobs(soup: BeautifulSoup, source_url: str) -> list[JobCandidate]:
    """
    Extract job candidates from repeated semantic job card elements
    using heuristics across CSS classes, article tags, and anchor links.
    """
    candidates: list[JobCandidate] = []
    seen_urls: set[str] = set()

    card_selectors = [
        "article",
        "li[class*='job']", "li[class*='career']", "li[class*='vacancy']", "li[class*='posting']",
        "div[class*='job-item']", "div[class*='job-card']", "div[class*='job_card']",
        "div[class*='vacancy']", "div[class*='career-card']", "div[class*='position-card']",
        "tr[class*='job']", "tr[class*='posting']",
    ]

    cards = []
    for sel in card_selectors:
        found = soup.select(sel)
        if len(found) >= 2:
            cards = found
            break

    # If standard class-based card selectors didn't match, look for list containers (li, tr)
    # that each enclose a distinctive job URL anchor (/jobs/<id>, /careers/<slug>, etc.)
    if not cards:
        job_pattern = re.compile(r"/(?:jobs?|positions?|vacanc(?:y|ies)|careers?)/[a-zA-Z0-9_\-]+", re.I)
        matched_containers = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            p = urlparse(href).path.rstrip("/")
            if p.lower() in ("", "/jobs", "/careers", "/openings", "/positions", "/vacancies"):
                continue
            if re.search(r"/(?:departments?|categories?|teams?|locations?)/", p, re.I):
                continue
            if job_pattern.search(p):
                container = a.find_parent("li") or a.find_parent("tr")
                if container and container not in matched_containers:
                    matched_containers.append(container)
        if len(matched_containers) >= 2:
            cards = matched_containers

    if cards:
        for card in cards:
            link = card.select_one("a[href]")
            if not link:
                continue
            href = link.get("href", "")
            raw_text = card.get_text(" ", strip=True)
            link_text = link.get_text(" ", strip=True)
            title = link_text or (card.select_one("h1, h2, h3, h4, h5, [class*='title']") or link).get_text(" ", strip=True)

            classes_str = " ".join(card.get("class", [])) if hasattr(card, "get") else ""
            if "cmp-teaser" in classes_str or "teaser" in classes_str or "editorial" in classes_str:
                continue

            if not is_plausible_job_link(href, title):
                continue

            if any(bad in title.lower() for bad in ["évoluer au sein", "qui sommes-nous", "deloitte-life", "formation et évolution"]):
                continue

            full_url = normalize_url(urljoin(source_url, href))
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            location = None
            loc_el = card.select_one("[class*='location'], [class*='city'], [class*='place'], [class*='lieu'], div.text-md, [class*='text-sm'], [class*='sub']")
            if loc_el and loc_el != link:
                loc_cand = sanitize_plain_text(loc_el.get_text(" ", strip=True))
                if loc_cand and loc_cand != title:
                    location = loc_cand

            dept = None
            dept_el = card.select_one("[class*='dept'], [class*='department'], [class*='service'], [class*='team']")
            if dept_el:
                dept = sanitize_plain_text(dept_el.get_text(" ", strip=True))

            id_match = re.search(r"/(?:job|jobs|position|vacancy|offre|postes?)/([a-zA-Z0-9_\-]+)", href)
            if id_match:
                ext_id = id_match.group(1)
            else:
                ext_id = re.sub(r"\W+", "_", urlparse(full_url).path.strip("/")) or title[:30]

            clean_title = sanitize_plain_text(title)
            emp_type = normalize_employment_type(raw_text)
            rem_type = normalize_remote_type(raw_text)

            found_skills = []
            raw_lower = raw_text.lower()
            for skill in COMMON_SKILLS:
                if re.search(rf"\b{re.escape(skill.lower())}\b", raw_lower):
                    found_skills.append(skill)

            candidates.append(
                JobCandidate(
                    title=clean_title,
                    job_url=full_url,
                    external_job_id=ext_id,
                    location=location,
                    description=sanitize_html(card.decode_contents() if hasattr(card, 'decode_contents') else raw_text),
                    employment_type=emp_type,
                    remote_type=rem_type,
                    department=dept,
                    skills=found_skills,
                )
            )

    # Fallback to direct anchor links
    if not candidates:
        all_links = soup.select("a[href]")
        for a in all_links:
            href = a.get("href", "")
            text = a.get_text(" ", strip=True)

            path_lower = urlparse(href).path.lower()
            has_career_path = any(re.search(rf"\b{re.escape(p)}\b", path_lower) for p in CAREER_PATH_INDICATORS)
            if not has_career_path:
                continue

            if not is_plausible_job_link(href, text):
                continue

            full_url = normalize_url(urljoin(source_url, href))
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            ext_id = re.sub(r"\W+", "_", urlparse(full_url).path.strip("/")) or text[:30]
            clean_title = sanitize_plain_text(text)

            parent_text = (a.find_parent("li") or a.find_parent("tr") or a).get_text(" ", strip=True)
            emp_type = normalize_employment_type(parent_text)
            rem_type = normalize_remote_type(parent_text)

            candidates.append(
                JobCandidate(
                    title=clean_title,
                    job_url=full_url,
                    external_job_id=ext_id,
                    location=None,
                    description=f"<p>{clean_title}</p>",
                    employment_type=emp_type,
                    remote_type=rem_type,
                    skills=[],
                )
            )

    return candidates


def find_universal_next_page_url(soup: BeautifulSoup, current_url: str) -> str | None:
    """Discover next page pagination link using semantic tags, rel='next', and pagination anchors."""
    # 1. Standard rel="next"
    next_link = soup.select_one("a[rel*='next'], link[rel*='next']")
    if next_link and next_link.get("href"):
        return urljoin(current_url, next_link["href"])

    # 2. Text-based pagination buttons
    next_patterns = [
        r"^(?:next|suivant|suivante|weiter|siguiente|suivant\s*»|next\s*>|»|>)$",
        r"\b(?:next\s+page|page\s+suivante|n[aä]chste\s+seite)\b",
    ]

    for a in soup.select("a[href]"):
        text = a.get_text(" ", strip=True).lower()
        aria = (a.get("aria-label") or "").lower()
        combined = f"{text} {aria}".strip()
        for pat in next_patterns:
            if re.search(pat, combined):
                href = a.get("href")
                if href and not href.startswith("#") and not href.startswith("javascript:"):
                    return urljoin(current_url, href)

    # 3. Numeric pagination: find active page and take the next number
    active_page = soup.select_one(".active, .current, [aria-current='page']")
    if active_page:
        parent = active_page.find_parent("ul") or active_page.find_parent("nav") or active_page.parent
        if parent:
            all_page_links = parent.select("a[href]")
            for a in all_page_links:
                href = a.get("href", "")
                text = a.get_text(strip=True)
                if text.isdigit() and active_page.get_text(strip=True).isdigit():
                    if int(text) == int(active_page.get_text(strip=True)) + 1:
                        return urljoin(current_url, href)

    return None


def parse_universal_jobs(source: FetchedSource) -> ParseResult:
    """
    Main Universal Discovery + Extraction Entrypoint.
    Executes layered progressive discovery:
    1. Direct ATS platform auto-delegation (Ashby, Workable, Greenhouse, Lever, SmartRecruiters, Workday)
    2. Direct JSON API payload detection
    3. Schema.org JSON-LD structured data (@graph & JobPosting)
    4. Embedded application state (Next.js __NEXT_DATA__, window.__INITIAL_STATE__)
    5. Semantic heading + action card heuristics (resolves custom company sites like Rankly Media)
    6. Repeated container HTML card heuristics
    """
    errors: list[str] = []
    target_url = source.requested_url or source.final_url

    # Layer 1: Platform delegation
    if AshbyAdapter.can_handle_url(target_url):
        return AshbyAdapter().parse(source)
    if WorkableAdapter.can_handle_url(target_url):
        return WorkableAdapter().parse(source)
    if GreenhouseAdapter.can_handle_url(target_url):
        return GreenhouseAdapter().parse(source)
    if LeverAdapter.can_handle_url(target_url):
        return LeverAdapter().parse(source)
    if SmartRecruitersAdapter.can_handle_url(target_url):
        return SmartRecruitersAdapter().parse(source)
    if WorkdayAdapter.can_handle_url(target_url):
        return WorkdayAdapter().parse(source)
    if TeamtailorAdapter.can_handle_source(source):
        return TeamtailorAdapter().parse(source)

    # Layer 2: Direct JSON response
    body_stripped = (source.body or "").strip()
    if body_stripped.startswith("{") and body_stripped.endswith("}"):
        try:
            data = json.loads(body_stripped)
            candidates: list[JobCandidate] = []
            raw_list = data.get("jobs") or data.get("results") or data.get("postings") or []
            if isinstance(raw_list, list):
                for item in raw_list:
                    if isinstance(item, dict):
                        t = sanitize_plain_text(item.get("title") or item.get("jobTitle") or "")
                        if t and len(t) >= 3:
                            jid = str(item.get("id") or item.get("shortcode") or t[:30])
                            jurl = normalize_url(urljoin(source.final_url, item.get("url") or f"#{jid}"))
                            candidates.append(
                                JobCandidate(
                                    title=t,
                                    job_url=jurl,
                                    external_job_id=jid,
                                    location=item.get("location"),
                                    description=sanitize_html(item.get("description") or f"<p>{t}</p>"),
                                    employment_type=normalize_employment_type(str(item.get("employmentType") or "")),
                                    remote_type=normalize_remote_type(str(item.get("workplaceType") or item.get("location") or "")),
                                )
                            )
            if candidates:
                return ParseResult(jobs=candidates, errors=errors)
        except Exception:
            pass

    # Parse HTML DOM
    soup = BeautifulSoup(source.body, "html.parser")

    # Layer 3: Schema.org JSON-LD
    jobs = extract_json_ld_jobs(soup, source.final_url)

    # Layer 4: Embedded state scripts (__NEXT_DATA__, window.__INITIAL_STATE__)
    if not jobs:
        jobs = extract_embedded_state_jobs(soup, source.final_url)

    # Layer 5: Repeated container HTML cards (for explicitly tagged job-item/career cards)
    if not jobs:
        jobs = extract_html_card_jobs(soup, source.final_url)

    # Layer 6: Semantic heading + metadata cards (Rankly Media pattern where containers have custom non-job classes)
    if not jobs:
        jobs = extract_semantic_cards_jobs(soup, source.final_url)

    # Quality and Confidence Validation: filter out invalid entries
    validated_jobs: list[JobCandidate] = []
    for job in jobs:
        if not job.title or len(job.title.strip()) < 3:
            errors.append(f"Rejected candidate with empty/too short title: {job.job_url}")
            continue
        if any(re.search(p, job.title.lower()) for p in EXCLUDED_SECTION_HEADINGS):
            errors.append(f"Rejected boilerplate section heading masquerading as job: '{job.title}'")
            continue
        validated_jobs.append(job)

    # Provide explicit diagnostic explanation if zero jobs were discovered
    if not validated_jobs:
        html_lower = source.body.lower()
        if "enable javascript" in html_lower or (soup.find(id="app") and not soup.find(id="app").find_all()):
            errors.append("Client-rendered SPA shell detected ('enable JavaScript' or empty container). Static response contains no rendered job cards or embedded state.")
        else:
            errors.append("Static HTML received. Evaluated JSON-LD, embedded state, semantic heading cards, and anchor links, but 0 qualifying job candidates were discovered.")

    return ParseResult(jobs=validated_jobs, errors=errors)
