import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

from ..logging import get_logger
from ..schemas_github_internships import (
    GitHubInternshipItem,
    GitHubInternshipsResponse,
    GitHubInternshipStats,
    GitHubRepoMeta,
    VisaStatusType,
)

logger = get_logger("services.github_internships")

from ..paths import get_storage_dir

def get_internships_cache_file() -> Path:
    return get_storage_dir() / "github_internships_cache.json"

SEED_FILE = Path(__file__).resolve().parent.parent / "content" / "github_internships_seed.json"

REPO_CONFIGS = [
    {
        "id": "simplify-2027",
        "name": "SimplifyJobs: Summer 2027 Internships",
        "url": "https://github.com/SimplifyJobs/Summer2027-Internships",
        "raw_url": "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README.md",
        "region": "US & Global",
        "year": "2027",
        "description": "Pitt CSC & Simplify tech internship directory for SWE, AI/ML, PM, Quant, and Hardware.",
    },
    {
        "id": "zapply-2027",
        "name": "Zapply: Internships 2027",
        "url": "https://github.com/zapplyjobs/Internships-2027",
        "raw_url": "https://raw.githubusercontent.com/zapplyjobs/Internships-2027/main/README.md",
        "region": "US & Global",
        "year": "2027",
        "description": "Continuous auto-tracked tech, engineering, and product internships with explicit visa data.",
    },
    {
        "id": "vansh-2027",
        "name": "Vansh & Ouckah: Summer 2027 Internships",
        "url": "https://github.com/vanshb03/Summer2027-Internships",
        "raw_url": "https://raw.githubusercontent.com/vanshb03/Summer2027-Internships/main/README.md",
        "region": "US, Canada & Remote",
        "year": "2027",
        "description": "Collaborative CSCareers community list of Summer 2027 tech internships.",
    },
    {
        "id": "negar-canadian-2027",
        "name": "Negar: Canadian Tech Internships 2027",
        "url": "https://github.com/negarprh/Canadian-Tech-Internships-2027",
        "raw_url": "https://raw.githubusercontent.com/negarprh/Canadian-Tech-Internships-2027/main/README.md",
        "region": "Canada & Remote",
        "year": "2027",
        "description": "Curated Canadian tech internships in Toronto, Vancouver, Montreal, Waterloo, and Ottawa.",
    },
    {
        "id": "lucian-canadian-2026",
        "name": "Luka & Ali: Canada Tech Internships Summer 2026",
        "url": "https://github.com/lucianlavric/CanadaTechInternships-Summer2026",
        "raw_url": "https://raw.githubusercontent.com/lucianlavric/CanadaTechInternships-Summer2026/master/README.md",
        "region": "Canada & Remote",
        "year": "2026",
        "description": "Canadian and remote tech internships for summer 2026.",
    },
    {
        "id": "speedyapply-intl-2027",
        "name": "SpeedyApply: 2027 International SWE Internships",
        "url": "https://github.com/speedyapply/2027-SWE-College-Jobs",
        "raw_url": "https://raw.githubusercontent.com/speedyapply/2027-SWE-College-Jobs/main/INTERN_INTL.md",
        "region": "International / Global",
        "year": "2027",
        "description": "Global software engineering internships across FAANG, Quant, Europe, and Asia-Pacific.",
    },
    {
        "id": "hackedrico-cyber-2027",
        "name": "HackedRico: 2027 Cyber Jobs & Internships",
        "url": "https://github.com/HackedRico/2027-cyber-jobs",
        "raw_url": "https://raw.githubusercontent.com/HackedRico/2027-cyber-jobs/main/README.md",
        "region": "US & Remote",
        "year": "2027",
        "description": "Cybersecurity internships, security engineering, AppSec, GRC, and early-career defense roles.",
    },
]

# Well-known company name to domain mapping for crisp logos
COMPANY_DOMAIN_MAP: dict[str, str] = {
    "google": "google.com",
    "microsoft": "microsoft.com",
    "amazon": "amazon.com",
    "meta": "meta.com",
    "apple": "apple.com",
    "netflix": "netflix.com",
    "nvidia": "nvidia.com",
    "nividia": "nvidia.com",
    "disney": "disney.com",
    "cisco": "cisco.com",
    "qualcomm": "qualcomm.com",
    "intel": "intel.com",
    "intel corporation": "intel.com",
    "adobe": "adobe.com",
    "salesforce": "salesforce.com",
    "ibm": "ibm.com",
    "oracle": "oracle.com",
    "stripe": "stripe.com",
    "doordash": "doordash.com",
    "figma": "figma.com",
    "lyft": "lyft.com",
    "uber": "uber.com",
    "datadog": "datadoghq.com",
    "tiktok": "tiktok.com",
    "rivian": "rivian.com",
    "waymo": "waymo.com",
    "replit": "replit.com",
    "notion": "notion.com",
    "okta": "okta.com",
    "paypal": "paypal.com",
    "deloitte": "deloitte.com",
    "robinhood": "robinhood.com",
    "motorola solutions": "motorolasolutions.com",
    "northrop grumman": "northropgrumman.com",
    "rtx": "rtx.com",
    "raytheon": "rtx.com",
    "general motors": "gm.com",
    "philips": "philips.com",
    "autodesk": "autodesk.com",
    "sap": "sap.com",
    "sap canada": "sap.com",
    "nokia": "nokia.com",
    "rbc": "rbc.com",
    "sun life": "sunlife.com",
    "manulife": "manulife.com",
    "manulife financial": "manulife.com",
    "guidehouse": "guidehouse.com",
    "singlestore": "singlestore.com",
    "zipline": "flyzipline.com",
    "together ai": "together.ai",
    "rubrik": "rubrik.com",
    "jpmorgan chase": "jpmorganchase.com",
    "jpmorgan": "jpmorganchase.com",
    "american express": "americanexpress.com",
    "epic games": "epicgames.com",
    "humana": "humana.com",
    "crowdstrike": "crowdstrike.com",
    "appian": "appian.com",
    "anduril": "anduril.com",
    "cme group": "cmegroup.com",
    "cadence": "cadence.com",
    "marvell": "marvell.com",
    "ge healthcare": "gehealthcare.com",
    "booz allen hamilton": "boozallen.com",
    "tyler technologies": "tylertech.com",
    "wellmark": "wellmark.com",
    "wellmark, inc.": "wellmark.com",
    "lazard": "lazard.com",
    "autozone": "autozone.com",
    "upbound group": "upbound.com",
    "oshkosh": "oshkoshcorp.com",
    "micron technology": "micron.com",
    "leidos": "leidos.com",
    "nasdaq": "nasdaq.com",
    "kbr": "kbr.com",
    "kinaxis": "kinaxis.com",
    "visier": "visier.com",
    "rockwell automation": "rockwellautomation.com",
    "standardaero": "standardaero.com",
    "spartan controls": "spartancontrols.com",
    "trc companies": "trccompanies.com",
    "alayacare": "alayacare.com",
    "equitable bank": "eqbank.ca",
    "rakuten": "rakuten.com",
    "moody's": "moodys.com",
    "ericsson": "ericsson.com",
    "cn": "cn.ca",
    "vertiv": "vertiv.com",
    "bmo": "bmo.com",
    "astranis": "astranis.com",
    "daimler truck": "daimlertruck.com",
    "visa": "visa.com",
    "f5": "f5.com",
    "johnson & johnson": "jnj.com",
    "formlabs": "formlabs.com",
    "avis budget group": "avisbudgetgroup.com",
    "labcorp": "labcorp.com",
    "insulet corporation": "insulet.com",
    "tower research capital": "tower-research.com",
    "rocket lab": "rocketlabusa.com",
    "nelnet": "nelnet.com",
    "aerovironment": "avav.com",
}


def guess_company_domain(company_name: str, apply_url: str = "") -> str:
    """Resolve likely company domain name for high-resolution logo resolution."""
    normalized = company_name.strip().lower()
    # Check manual map
    if normalized in COMPANY_DOMAIN_MAP:
        return COMPANY_DOMAIN_MAP[normalized]
    for key, dom in COMPANY_DOMAIN_MAP.items():
        if key in normalized or normalized in key:
            return dom

    # Parse from application link if possible
    if apply_url:
        try:
            # Check for patterns like workday, greenhouse, lever, ashby
            m = re.search(r'(?:greenhouse\.io|lever\.co|ashbyhq\.com|jobvite\.com|smartrecruiters\.com)/([a-zA-Z0-9_-]+)', apply_url)
            if m:
                slug = m.group(1).lower()
                if slug not in ("jobs", "apply", "careers", "job", "candidate"):
                    return f"{slug}.com"

            m2 = re.search(r'https?://(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', apply_url)
            if m2:
                host = m2.group(1).lower()
                # filter out generic hosts
                if not any(gh in host for gh in ["myworkdayjobs", "oraclecloud", "github", "imgur", "zapply", "simplify", "shields"]):
                    return host
        except Exception:
            pass

    # Clean company name slug
    clean = re.sub(r'[^a-zA-Z0-9]', '', company_name).lower()
    if clean:
        return f"{clean}.com"
    return ""


def get_logo_url(domain: str) -> str:
    """Generate high-res favicon/logo API URL with fallback."""
    if not domain:
        return ""
    return f"https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://{domain}&size=128"


def clean_text(text: str) -> str:
    """Clean markdown artifacts, emoji markers, and html tags."""
    t = re.sub(r'<[^>]+>', ' ', text)
    t = t.replace('&amp;', '&').replace('&nbsp;', ' ')
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


from .clock import get_clock


def parse_age_days(dp: str | None) -> int:
    """Parse relative age strings like '4d', '2w', '1mo', 'Aug 16' into approximate day counts."""
    if not dp:
        return 0
    s = str(dp).strip().lower()
    m = re.match(r"^(\d+)\s*d", s)
    if m:
        return int(m.group(1))
    m = re.match(r"^(\d+)\s*w", s)
    if m:
        return int(m.group(1)) * 7
    m = re.match(r"^(\d+)\s*mo", s)
    if m:
        return int(m.group(1)) * 30
    for mo, days_ago in [
        ("jan", 270), ("feb", 240), ("mar", 210), ("apr", 180),
        ("may", 150), ("jun", 120), ("jul", 90), ("aug", 60), ("sep", 30)
    ]:
        if mo in s:
            return days_ago
    return 0


def canonical_internship_key(company: str, role: str, location: str) -> str:
    """Compute uniform canonical deduplication key across disparate GitHub repositories."""
    norm_comp = re.sub(r"[^a-z0-9]", "", (company or "").lower())
    norm_role = re.sub(r"[^a-z0-9]", "", (role or "").lower())
    norm_loc = re.sub(r"[^a-z0-9]", "", (location or "").lower())
    return f"{norm_comp}#{norm_role}#{norm_loc}"


def get_user_tracked_internships() -> tuple[set[str], set[tuple[str, str]]]:
    """
    Retrieve user-saved/tracked applications to guarantee zero data loss.
    Internships touched by users are strictly exempt from automated retirement.
    """
    tracked_urls: set[str] = set()
    tracked_pairs: set[tuple[str, str]] = set()
    try:
        from ..database import SessionLocal
        from ..models import UserApplication
        with SessionLocal() as db:
            apps = db.query(
                UserApplication.custom_job_url,
                UserApplication.custom_company_name,
                UserApplication.custom_job_title
            ).all()
            for url, comp, title in apps:
                if url and url.strip():
                    tracked_urls.add(url.strip().lower())
                if comp and title:
                    norm_comp = re.sub(r"[^a-z0-9]", "", comp.lower())
                    norm_role = re.sub(r"[^a-z0-9]", "", title.lower())
                    tracked_pairs.add((norm_comp, norm_role))
    except Exception as exc:
        logger.warning("Could not query user applications for internship protection: %s", exc)
    return tracked_urls, tracked_pairs


def is_internship_user_tracked(
    item: GitHubInternshipItem,
    tracked_urls: set[str],
    tracked_pairs: set[tuple[str, str]],
) -> bool:
    """Check if an internship item has been saved or tracked by any user."""
    if item.apply_url and item.apply_url.strip().lower() in tracked_urls:
        return True
    norm_comp = re.sub(r"[^a-z0-9]", "", (item.company or "").lower())
    norm_role = re.sub(r"[^a-z0-9]", "", (item.role or "").lower())
    if (norm_comp, norm_role) in tracked_pairs:
        return True
    return False


def merge_internships(existing: GitHubInternshipItem, incoming: GitHubInternshipItem) -> GitHubInternshipItem:
    """Merge cross-repository duplicates into a single high-fidelity listing."""
    is_closed = existing.is_closed and incoming.is_closed

    visa_status = existing.visa_status
    visa_text = existing.visa_text
    if visa_status in ("not_specified", "") and incoming.visa_status not in ("not_specified", ""):
        visa_status = incoming.visa_status
        visa_text = incoming.visa_text

    apply_url = existing.apply_url or incoming.apply_url
    domain = existing.company_domain or incoming.company_domain
    logo = existing.logo_url or incoming.logo_url
    date_posted = existing.date_posted or incoming.date_posted
    season = max(existing.season or "2027", incoming.season or "2027")

    return GitHubInternshipItem(
        id=existing.id,
        company=existing.company,
        company_domain=domain,
        logo_url=logo,
        role=existing.role,
        location=existing.location,
        country=existing.country or incoming.country,
        category=existing.category or incoming.category,
        season=season,
        source_repo_id=existing.source_repo_id,
        source_repo_name=existing.source_repo_name,
        source_repo_url=existing.source_repo_url,
        apply_url=apply_url,
        date_posted=date_posted,
        visa_status=visa_status,
        visa_text=visa_text,
        is_closed=is_closed,
        notes=existing.notes or incoming.notes,
        is_archived=existing.is_archived and incoming.is_archived,
        archived_at=existing.archived_at,
        archived_reason=existing.archived_reason,
    )


class GitHubInternshipsService:
    """Service to fetch, parse, cache, and serve opportunities from active GitHub repos."""

    def __init__(self) -> None:
        get_storage_dir().mkdir(parents=True, exist_ok=True)

    def get_curated_internships(
        self,
        repo_id: str | None = None,
        visa_status: str | None = None,
        category: str | None = None,
        search: str | None = None,
        open_only: bool = False,
        include_archived: bool = False,
    ) -> GitHubInternshipsResponse:
        """Return curated internships from cache or bundled seed. Never blocks synchronously on external fetch."""
        cached_data = self._load_cache()
        if not cached_data:
            logger.warning("No internships cache or seed available; returning empty response.")
            return GitHubInternshipsResponse(
                items=[],
                stats=GitHubInternshipStats(
                    total_listings=0,
                    active_listings=0,
                    closed_listings=0,
                    archived_listings=0,
                    visa_sponsored_count=0,
                    no_sponsorship_count=0,
                    us_citizens_count=0,
                    canada_authorized_count=0,
                    not_specified_count=0,
                    repos_count=len(REPO_CONFIGS),
                    last_synced_at="",
                    by_repo={},
                    by_category={},
                ),
                repositories=[
                    GitHubRepoMeta(
                        id=cfg["id"],
                        name=cfg["name"],
                        url=cfg["url"],
                        region=cfg["region"],
                        year=cfg["year"],
                        description=cfg["description"],
                    )
                    for cfg in REPO_CONFIGS
                ],
                categories=[],
            )

        items = cached_data.items

        # Front-facing view: default to active, non-archived listings only
        if not include_archived:
            items = [it for it in items if not it.is_archived]

        # Apply filters
        if repo_id and repo_id.strip() and repo_id != "all":
            items = [it for it in items if it.source_repo_id == repo_id.strip()]

        if visa_status and visa_status.strip() and visa_status != "all":
            items = [it for it in items if it.visa_status == visa_status.strip()]

        if category and category.strip() and category != "all":
            cat_norm = category.strip().lower()
            items = [it for it in items if cat_norm in it.category.lower()]

        if open_only:
            items = [it for it in items if not it.is_closed]

        if search and search.strip():
            terms = [q.lower() for q in search.strip().split() if q]
            filtered = []
            for it in items:
                searchable = f"{it.company} {it.role} {it.location} {it.category} {it.visa_text} {it.notes or ''}".lower()
                if all(t in searchable for t in terms):
                    filtered.append(it)
            items = filtered

        # Compute dynamic stats for response
        stats = self._compute_stats(cached_data.items)

        return GitHubInternshipsResponse(
            items=items,
            stats=stats,
            repositories=cached_data.repositories,
            categories=cached_data.categories,
        )

    def sync_all_repos(self) -> GitHubInternshipsResponse:
        """Synchronize all repositories live from GitHub, deduplicate canonically, retire stale, and update cache."""
        all_raw_items: list[GitHubInternshipItem] = []
        repo_metas: list[GitHubRepoMeta] = []

        for config in REPO_CONFIGS:
            try:
                content = self._fetch_repo_content(config)
                items = self._parse_repo(config, content)
                all_raw_items.extend(items)
                repo_metas.append(
                    GitHubRepoMeta(
                        id=config["id"],
                        name=config["name"],
                        url=config["url"],
                        raw_url=config["raw_url"],
                        region=config["region"],
                        year=config["year"],
                        description=config["description"],
                        item_count=len(items),
                    )
                )
            except Exception as exc:
                logger.error("Failed to parse repo %s: %s", config['id'], exc)

        # 1. Deduplicate cross-repo duplicates into canonical keys
        current_by_key: dict[str, GitHubInternshipItem] = {}
        for it in all_raw_items:
            k = canonical_internship_key(it.company, it.role, it.location)
            if k in current_by_key:
                current_by_key[k] = merge_internships(current_by_key[k], it)
            else:
                current_by_key[k] = it

        # 2. Get user tracked applications (URL + company/role) for strict protection
        tracked_urls, tracked_pairs = get_user_tracked_internships()

        # 3. Load existing cached items to handle retirement of listings no longer present
        cached_data = self._load_cache()
        existing_items = cached_data.items if cached_data else []

        now_iso = get_clock().now().isoformat()
        final_items_by_key: dict[str, GitHubInternshipItem] = {}

        # First add all current listings with lifecycle assessment
        for k, it in current_by_key.items():
            is_tracked = is_internship_user_tracked(it, tracked_urls, tracked_pairs)
            if not is_tracked:
                # Past season (e.g. Summer 2026) -> archive
                if it.season and it.season <= "2026":
                    it.is_archived = True
                    it.archived_at = it.archived_at or now_iso
                    it.archived_reason = f"Past season ({it.season})"
                # Closed listing older than 30 days -> archive
                elif it.is_closed and parse_age_days(it.date_posted) >= 30:
                    it.is_archived = True
                    it.archived_at = it.archived_at or now_iso
                    it.archived_reason = "Closed listing older than 30 days"
            else:
                # User touched/tracked -> strictly protected
                it.is_archived = False
            final_items_by_key[k] = it

        # Next check previous cache items for retirement
        for old in existing_items:
            k = canonical_internship_key(old.company, old.role, old.location)
            if k not in final_items_by_key:
                # Listing was in cache but is NO LONGER present in upstream fetch
                is_tracked = is_internship_user_tracked(old, tracked_urls, tracked_pairs)
                if is_tracked:
                    # User touched/saved/applied -> strictly protect, keep active!
                    old.is_archived = False
                    final_items_by_key[k] = old
                else:
                    # Not in source anymore -> move to archived if older than 30 days or closed or past season
                    if old.is_closed or (old.season and old.season <= "2026") or parse_age_days(old.date_posted) >= 30 or old.is_archived:
                        old.is_archived = True
                        old.archived_at = old.archived_at or now_iso
                        old.archived_reason = old.archived_reason or "No longer present in upstream repository source"
                        final_items_by_key[k] = old

        all_final_items = list(final_items_by_key.values())
        categories_set = {it.category for it in all_final_items if it.category and not it.is_archived}
        categories = sorted(list(categories_set))
        stats = self._compute_stats(all_final_items)

        response = GitHubInternshipsResponse(
            items=all_final_items,
            stats=stats,
            repositories=repo_metas,
            categories=categories,
        )

        self._save_cache(response)
        return response

    def _fetch_repo_content(self, config: dict[str, str]) -> str:
        """Fetch raw content from GitHub raw URL with conditional ETag headers and local persistent caching."""
        url = config["raw_url"]
        logger.info("Fetching repo content: %s", url)

        raw_cache_dir = get_storage_dir() / "github_raw_repos"
        raw_cache_dir.mkdir(parents=True, exist_ok=True)
        local_raw_path = raw_cache_dir / f"{config['id']}.md"

        etags_file = get_storage_dir() / "github_internships_etags.json"
        etags: dict[str, str] = {}
        if etags_file.exists():
            try:
                etags = json.loads(etags_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        headers = {"User-Agent": "Compust-CareerEngine/2.0"}
        cached_etag = etags.get(url)
        # Only use If-None-Match if we actually have the cached content saved locally!
        if cached_etag and local_raw_path.exists() and local_raw_path.stat().st_size > 0:
            headers["If-None-Match"] = cached_etag

        try:
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 304:
                    logger.info("Repo content not modified (304): %s, using local cache", url)
                    if local_raw_path.exists() and local_raw_path.stat().st_size > 0:
                        return local_raw_path.read_text(encoding="utf-8")
                    # If local file was missing, fall back to re-fetching without If-None-Match
                    resp = client.get(url, headers={"User-Agent": "Compust-CareerEngine/2.0"})

                resp.raise_for_status()
                text = resp.text
                if text.strip():
                    local_raw_path.write_text(text, encoding="utf-8")
                new_etag = resp.headers.get("etag")
                if new_etag:
                    etags[url] = new_etag
                    try:
                        etags_file.write_text(json.dumps(etags, indent=2), encoding="utf-8")
                    except Exception:
                        pass
                return text
        except Exception as err:
            logger.warning("Live fetch failed for %s (%s). Attempting local cached raw fallback.", url, err)
            if local_raw_path.exists() and local_raw_path.stat().st_size > 0:
                return local_raw_path.read_text(encoding="utf-8")
            scratch_path = self._get_scratch_path(config["id"])
            if scratch_path and os.path.exists(scratch_path):
                with open(scratch_path, "r", encoding="utf-8") as f:
                    return f.read()
            raise

    def _get_scratch_path(self, repo_id: str) -> str | None:
        """Check for pre-downloaded content files in system logs if network is unavailable."""
        mapping = {
            "simplify-2027": r"C:\Users\soula\.gemini\antigravity-ide\brain\95801ca4-f87d-40a6-bdb0-d248cbd183e4\.system_generated\steps\19\content.md",
            "zapply-2027": r"C:\Users\soula\.gemini\antigravity-ide\brain\95801ca4-f87d-40a6-bdb0-d248cbd183e4\.system_generated\steps\29\content.md",
            "vansh-2027": r"C:\Users\soula\.gemini\antigravity-ide\brain\95801ca4-f87d-40a6-bdb0-d248cbd183e4\.system_generated\steps\35\content.md",
            "negar-canadian-2027": r"C:\Users\soula\.gemini\antigravity-ide\brain\95801ca4-f87d-40a6-bdb0-d248cbd183e4\.system_generated\steps\39\content.md",
            "lucian-canadian-2026": r"C:\Users\soula\.gemini\antigravity-ide\brain\95801ca4-f87d-40a6-bdb0-d248cbd183e4\.system_generated\steps\45\content.md",
            "speedyapply-intl-2027": r"C:\Users\soula\.gemini\antigravity-ide\brain\95801ca4-f87d-40a6-bdb0-d248cbd183e4\.system_generated\steps\119\content.md",
            "hackedrico-cyber-2027": r"C:\Users\soula\.gemini\antigravity-ide\brain\95801ca4-f87d-40a6-bdb0-d248cbd183e4\.system_generated\steps\121\content.md",
        }
        return mapping.get(repo_id)

    def _parse_repo(self, config: dict[str, str], text: str) -> list[GitHubInternshipItem]:
        repo_id = config["id"]
        if repo_id == "simplify-2027":
            return self._parse_simplify(config, text)
        elif repo_id == "zapply-2027":
            return self._parse_zapply(config, text)
        elif repo_id == "vansh-2027":
            return self._parse_vansh(config, text)
        elif repo_id == "negar-canadian-2027":
            return self._parse_negar(config, text)
        elif repo_id == "lucian-canadian-2026":
            return self._parse_lucian(config, text)
        elif repo_id == "speedyapply-intl-2027":
            return self._parse_speedyapply(config, text)
        elif repo_id == "hackedrico-cyber-2027":
            return self._parse_hackedrico(config, text)
        return []

    def _parse_simplify(self, config: dict[str, str], text: str) -> list[GitHubInternshipItem]:
        soup = BeautifulSoup(text, "html.parser")
        tables = soup.find_all("table")
        items: list[GitHubInternshipItem] = []

        for table in tables:
            curr = table
            category = "Software Engineering"
            while curr:
                curr = curr.find_previous_sibling()
                if curr and curr.name in ("h2", "h1"):
                    raw_cat = curr.get_text(strip=True)
                    raw_cat = re.sub(r'^[💻📱🤖📈🔧\s]+', '', raw_cat)
                    raw_cat = re.sub(r'\s+Internship Roles.*$', '', raw_cat)
                    if raw_cat:
                        category = raw_cat
                    break

            rows = table.find_all("tr")
            last_company = ""
            for tr in rows[1:]:
                cols = tr.find_all("td")
                if len(cols) < 4:
                    continue
                comp_raw = cols[0].get_text(strip=True)
                if comp_raw == "↳":
                    company = last_company
                else:
                    company = comp_raw
                    last_company = comp_raw

                role = cols[1].get_text(strip=True)
                location = cols[2].get_text(separator=" ", strip=True)

                apply_url = ""
                for a in cols[3].find_all("a", href=True):
                    href = a["href"]
                    if "simplify.jobs/p/" not in href or not apply_url:
                        apply_url = href
                        if "simplify.jobs/p/" not in href:
                            break

                date_posted = cols[4].get_text(strip=True) if len(cols) > 4 else None

                raw_combo = f"{company} {role} {cols[0]} {cols[1]}"
                visa_status: VisaStatusType = "not_specified"
                visa_text = "Not Specified"
                if "🛂" in raw_combo:
                    visa_status = "no_sponsorship"
                    visa_text = "No Sponsorship"
                elif "🇺🇸" in raw_combo:
                    visa_status = "us_citizen_only"
                    visa_text = "US Citizens Only"
                elif "🔒" in raw_combo:
                    visa_status = "closed"
                    visa_text = "Closed"

                clean_company = re.sub(r"[🛂🇺🇸🔒🔥🎓]", "", company).strip()
                clean_role = re.sub(r"[🛂🇺🇸🔒🔥🎓]", "", role).strip()
                if not clean_company or not clean_role:
                    continue

                domain = guess_company_domain(clean_company, apply_url)
                item_id = hashlib.md5(f"{config['id']}_{clean_company}_{clean_role}_{location}".encode()).hexdigest()[:12]

                items.append(
                    GitHubInternshipItem(
                        id=item_id,
                        company=clean_company,
                        company_domain=domain,
                        logo_url=get_logo_url(domain),
                        role=clean_role,
                        location=clean_text(location),
                        category=category,
                        season=config["year"],
                        source_repo_id=config["id"],
                        source_repo_name=config["name"],
                        source_repo_url=config["url"],
                        apply_url=apply_url,
                        date_posted=date_posted,
                        visa_status=visa_status,
                        visa_text=visa_text,
                        is_closed="🔒" in raw_combo,
                    )
                )
        return items

    def _parse_zapply(self, config: dict[str, str], text: str) -> list[GitHubInternshipItem]:
        lines = text.splitlines()
        items: list[GitHubInternshipItem] = []
        current_category = "Software Engineering"
        last_company = ""

        for line in lines:
            line_s = line.strip()
            if "###" in line_s and "<summary>" in line_s:
                clean_cat = re.sub(r'<[^>]+>', '', line_s).replace('#', '').strip()
                clean_cat = re.sub(r'^[💻📱🤖📈🔧\s]+', '', clean_cat)
                if clean_cat:
                    current_category = clean_cat
            if not line_s.startswith('|'):
                continue
            parts = [p.strip() for p in line_s.split('|')]
            if len(parts) < 6:
                continue
            comp_part = parts[1]
            if comp_part in ("Company", "---", ":---", "") or comp_part.startswith('---'):
                continue

            company = comp_part.replace('**', '').strip()
            if company == "↳":
                company = last_company
            else:
                last_company = company

            role = parts[2].replace('**', '').strip()
            location = parts[3]
            posted = parts[4]
            visa_col = parts[5] if len(parts) > 6 else ""
            apply_col = parts[6] if len(parts) > 6 else parts[5]

            apply_match = re.search(r'\]\((https?://[^\)]+)\)', apply_col)
            apply_url = apply_match.group(1) if apply_match else ""

            visa_status: VisaStatusType = "not_specified"
            visa_text = "Not Specified"
            if "Sponsor" in visa_col or "✅" in visa_col:
                visa_status = "sponsors_visa"
                visa_text = "Offers Visa Sponsorship"
            elif "🛂" in visa_col or "No" in visa_col:
                visa_status = "no_sponsorship"
                visa_text = "No Sponsorship"
            elif "🇺🇸" in visa_col:
                visa_status = "us_citizen_only"
                visa_text = "US Citizens Only"

            if not company or not role:
                continue

            domain = guess_company_domain(company, apply_url)
            item_id = hashlib.md5(f"{config['id']}_{company}_{role}_{location}".encode()).hexdigest()[:12]

            items.append(
                GitHubInternshipItem(
                    id=item_id,
                    company=company,
                    company_domain=domain,
                    logo_url=get_logo_url(domain),
                    role=role,
                    location=clean_text(location),
                    category=current_category,
                    season=config["year"],
                    source_repo_id=config["id"],
                    source_repo_name=config["name"],
                    source_repo_url=config["url"],
                    apply_url=apply_url,
                    date_posted=posted,
                    visa_status=visa_status,
                    visa_text=visa_text,
                    is_closed=False,
                )
            )
        return items

    def _parse_vansh(self, config: dict[str, str], text: str) -> list[GitHubInternshipItem]:
        lines = text.splitlines()
        items: list[GitHubInternshipItem] = []
        last_company = ""

        for line in lines:
            line_s = line.strip()
            if not line_s.startswith('|'):
                continue
            parts = [p.strip() for p in line_s.split('|')]
            if len(parts) < 5:
                continue
            comp_part = parts[1]
            if comp_part in ("Company", "-------", "") or comp_part.startswith('---'):
                continue
            company = comp_part.replace('**', '').strip()
            if company == "↳":
                company = last_company
            else:
                last_company = company

            role = parts[2]
            location = parts[3]
            apply_col = parts[4]
            date_posted = parts[5] if len(parts) > 5 else None

            apply_match = re.search(r'href=[\'"]([^\'"]+)[\'"]', apply_col)
            apply_url = apply_match.group(1) if apply_match else ""

            visa_status: VisaStatusType = "not_specified"
            visa_text = "Not Specified"
            full_combo = f"{role} {company}"
            if "🛂" in full_combo:
                visa_status = "no_sponsorship"
                visa_text = "No Sponsorship"
            elif "🇺🇸" in full_combo:
                visa_status = "us_citizen_only"
                visa_text = "US Citizens Only"
            elif "🔒" in full_combo:
                visa_status = "closed"
                visa_text = "Closed"

            clean_company = re.sub(r'[🛂🇺🇸🔒]', '', company).strip()
            clean_role = re.sub(r'[🛂🇺🇸🔒]', '', role).strip()
            if not clean_company or not clean_role:
                continue

            category = "Software Engineering"
            if any(w in clean_role.lower() for w in ["ai", "machine learning", "data", "ml"]):
                category = "Data Science, AI & ML"
            elif "product management" in clean_role.lower() or "pm" in clean_role.lower():
                category = "Product Management"
            elif any(w in clean_role.lower() for w in ["quant", "trader"]):
                category = "Quantitative Finance"
            elif "hardware" in clean_role.lower():
                category = "Hardware Engineering"

            domain = guess_company_domain(clean_company, apply_url)
            item_id = hashlib.md5(f"{config['id']}_{clean_company}_{clean_role}_{location}".encode()).hexdigest()[:12]

            items.append(
                GitHubInternshipItem(
                    id=item_id,
                    company=clean_company,
                    company_domain=domain,
                    logo_url=get_logo_url(domain),
                    role=clean_role,
                    location=clean_text(location),
                    category=category,
                    season=config["year"],
                    source_repo_id=config["id"],
                    source_repo_name=config["name"],
                    source_repo_url=config["url"],
                    apply_url=apply_url,
                    date_posted=date_posted,
                    visa_status=visa_status,
                    visa_text=visa_text,
                    is_closed="🔒" in full_combo,
                )
            )
        return items

    def _parse_negar(self, config: dict[str, str], text: str) -> list[GitHubInternshipItem]:
        lines = text.splitlines()
        items: list[GitHubInternshipItem] = []
        last_company = ""

        for line in lines:
            line_s = line.strip()
            if not line_s.startswith('|'):
                continue
            parts = [p.strip() for p in line_s.split('|')]
            if len(parts) < 5:
                continue
            comp_part = parts[1]
            if comp_part in ("Company", "--------", "") or comp_part.startswith('---'):
                continue
            company = comp_part.replace('**', '').strip()
            if company == "↳":
                company = last_company
            else:
                last_company = company
            role = parts[2].strip()
            location = parts[3].strip()
            apply_col = parts[4]
            date_posted = parts[5].strip() if len(parts) > 5 else None

            is_closed = "Closed" in apply_col or "🔒" in apply_col or "Closed" in role
            urls = re.findall(r'https?://[^\s\)"\'>]+', apply_col)
            target_urls = [u for u in urls if "shields.io" not in u and "imgur.com" not in u and not u.endswith(('.png', '.jpg', '.svg'))]
            apply_url = target_urls[0] if target_urls else (urls[-1] if urls else "")

            visa_status: VisaStatusType = "canada_authorized"
            visa_text = "Canada Eligible / Students in CA"
            if is_closed:
                visa_status = "closed"
                visa_text = "Closed"

            category = "Software Engineering"
            if any(w in role.lower() for w in ["ai", "machine learning", "data", "robotics"]):
                category = "Data Science, AI & ML"
            elif any(w in role.lower() for w in ["silicon", "hardware", "analog", "firmware"]):
                category = "Hardware Engineering"

            domain = guess_company_domain(company, apply_url)
            item_id = hashlib.md5(f"{config['id']}_{company}_{role}_{location}".encode()).hexdigest()[:12]

            items.append(
                GitHubInternshipItem(
                    id=item_id,
                    company=company,
                    company_domain=domain,
                    logo_url=get_logo_url(domain),
                    role=role,
                    location=clean_text(location),
                    country="Canada",
                    category=category,
                    season=config["year"],
                    source_repo_id=config["id"],
                    source_repo_name=config["name"],
                    source_repo_url=config["url"],
                    apply_url=apply_url,
                    date_posted=date_posted,
                    visa_status=visa_status,
                    visa_text=visa_text,
                    is_closed=is_closed,
                )
            )
        return items

    def _parse_lucian(self, config: dict[str, str], text: str) -> list[GitHubInternshipItem]:
        lines = text.splitlines()
        items: list[GitHubInternshipItem] = []
        last_company = ""

        for line in lines:
            line_s = line.strip()
            if not line_s.startswith('|'):
                continue
            parts = [p.strip() for p in line_s.split('|')]
            if len(parts) < 5:
                continue
            comp_part = parts[1]
            if comp_part in ("Company", "-------", "") or comp_part.startswith('---'):
                continue
            company = comp_part.replace('**', '').strip()
            if company == "↳":
                company = last_company
            else:
                last_company = company
            role = parts[2].strip()
            location = parts[3].strip()
            apply_col = parts[4]
            date_posted = parts[5].strip() if len(parts) > 5 else None

            is_closed = "Closed" in apply_col or "🔒" in apply_col or "Closed" in role
            apply_match = re.search(r'href=[\'"]([^\'"]+)[\'"]', apply_col)
            apply_url = apply_match.group(1) if apply_match else ""

            visa_status: VisaStatusType = "canada_authorized"
            visa_text = "Canada Eligible"
            if is_closed:
                visa_status = "closed"
                visa_text = "Closed"

            category = "Software Engineering"
            if any(w in role.lower() for w in ["data", "machine learning", "ai", "analyst"]):
                category = "Data Science, AI & ML"
            elif any(w in role.lower() for w in ["hardware", "silicon", "compiler"]):
                category = "Hardware Engineering"

            domain = guess_company_domain(company, apply_url)
            item_id = hashlib.md5(f"{config['id']}_{company}_{role}_{location}".encode()).hexdigest()[:12]

            items.append(
                GitHubInternshipItem(
                    id=item_id,
                    company=company,
                    company_domain=domain,
                    logo_url=get_logo_url(domain),
                    role=role,
                    location=clean_text(location),
                    country="Canada",
                    category=category,
                    season=config["year"],
                    source_repo_id=config["id"],
                    source_repo_name=config["name"],
                    source_repo_url=config["url"],
                    apply_url=apply_url,
                    date_posted=date_posted,
                    visa_status=visa_status,
                    visa_text=visa_text,
                    is_closed=is_closed,
                )
            )
        return items

    def _parse_speedyapply(self, config: dict[str, str], text: str) -> list[GitHubInternshipItem]:
        lines = text.splitlines()
        items: list[GitHubInternshipItem] = []
        current_category = "Software Engineering (International)"
        last_company = ""

        for line in lines:
            line_s = line.strip()
            if line_s.startswith('### '):
                clean_h = line_s.replace('###', '').strip()
                if clean_h:
                    current_category = clean_h
            if not line_s.startswith('|'):
                continue
            parts = [p.strip() for p in line_s.split('|')]
            if len(parts) < 5:
                continue
            comp_col = parts[1]
            if comp_col in ("Company", "---", "") or comp_col.startswith('---'):
                continue

            dom_match = re.search(r'href=[\'"]https?://(?:www\.)?([^\'"/]+)', comp_col)
            comp_domain = dom_match.group(1) if dom_match else ""
            clean_company = re.sub(r'<[^>]+>', '', comp_col).strip()

            if clean_company == "↳":
                clean_company = last_company
            else:
                last_company = clean_company

            role = parts[2].strip()
            location = parts[3]
            apply_col = parts[4]
            age = parts[5].strip() if len(parts) > 5 else None

            urls = re.findall(r'href=[\'"]([^\'"]+)[\'"]', apply_col)
            apply_url = urls[0] if urls else ""

            if not comp_domain:
                comp_domain = guess_company_domain(clean_company, apply_url)

            domain = comp_domain
            item_id = hashlib.md5(f"{config['id']}_{clean_company}_{role}_{location}".encode()).hexdigest()[:12]

            items.append(
                GitHubInternshipItem(
                    id=item_id,
                    company=clean_company,
                    company_domain=domain,
                    logo_url=get_logo_url(domain),
                    role=role,
                    location=clean_text(location),
                    category=current_category,
                    season=config["year"],
                    source_repo_id=config["id"],
                    source_repo_name=config["name"],
                    source_repo_url=config["url"],
                    apply_url=apply_url,
                    date_posted=age,
                    visa_status="not_specified",
                    visa_text="International / See Listing",
                    is_closed=False,
                )
            )
        return items

    def _parse_hackedrico(self, config: dict[str, str], text: str) -> list[GitHubInternshipItem]:
        lines = text.splitlines()
        items: list[GitHubInternshipItem] = []
        current_section = "Cybersecurity"
        last_company = ""

        for line in lines:
            line_s = line.strip()
            if line_s.startswith('## ') or line_s.startswith('### '):
                clean_sec = re.sub(r'[#🎓🎒🌱🛡️]', '', line_s).strip()
                if clean_sec:
                    current_section = clean_sec
            if not line_s.startswith('|'):
                continue
            parts = [p.strip() for p in line_s.split('|')]
            if len(parts) < 6:
                continue
            comp_col = parts[1]
            if comp_col in ("Company", "-------", "") or comp_col.startswith('---'):
                continue

            has_us_flag = "🇺🇸" in comp_col or "🇺🇸" in parts[2]
            is_closed = "🔒" in parts[5] or "🔒" in parts[2] or "🔒" in comp_col

            clean_company = comp_col.replace('🇺🇸', '').replace('**', '').replace('↳', '').strip()
            if not clean_company or comp_col.strip().startswith('↳'):
                clean_company = last_company
            else:
                last_company = clean_company

            role = parts[2].replace('🇺🇸', '').strip()
            location = parts[3]
            role_cat = parts[4]
            apply_col = parts[5]
            date_added = parts[6].strip() if len(parts) > 6 else None

            urls = re.findall(r'href=[\'"]([^\'"]+)[\'"]', apply_col)
            apply_url = urls[0] if urls else ""

            visa_status: VisaStatusType = "us_citizen_only" if has_us_flag else "not_specified"
            visa_text = "US Citizenship / Clearance" if has_us_flag else "Not Specified"
            if is_closed:
                visa_status = "closed"
                visa_text = "Closed"

            clean_role_cat = clean_text(role_cat).replace('&amp;', '&').strip()
            if any(bad in clean_role_cat.lower() for bad in ['<details', 'summary', 'locations', '</', 'remote,', ', ']):
                clean_role_cat = "Security Engineering"
            final_category = f"Cybersecurity - {clean_role_cat}" if clean_role_cat else "Cybersecurity"

            domain = guess_company_domain(clean_company, apply_url)
            item_id = hashlib.md5(f"{config['id']}_{clean_company}_{role}_{location}".encode()).hexdigest()[:12]

            items.append(
                GitHubInternshipItem(
                    id=item_id,
                    company=clean_company,
                    company_domain=domain,
                    logo_url=get_logo_url(domain),
                    role=role,
                    location=clean_text(location),
                    category=final_category,
                    season=config["year"],
                    source_repo_id=config["id"],
                    source_repo_name=config["name"],
                    source_repo_url=config["url"],
                    apply_url=apply_url,
                    date_posted=date_added,
                    visa_status=visa_status,
                    visa_text=visa_text,
                    is_closed=is_closed,
                    notes=current_section,
                )
            )
        return items

    def _compute_stats(self, items: list[GitHubInternshipItem]) -> GitHubInternshipStats:
        non_archived = [it for it in items if not it.is_archived]
        total = len(non_archived)
        active = sum(1 for it in non_archived if not it.is_closed)
        closed = sum(1 for it in non_archived if it.is_closed)
        archived = sum(1 for it in items if it.is_archived)

        sponsored = sum(1 for it in non_archived if it.visa_status == "sponsors_visa")
        no_spon = sum(1 for it in non_archived if it.visa_status == "no_sponsorship")
        us_cit = sum(1 for it in non_archived if it.visa_status == "us_citizen_only")
        ca_auth = sum(1 for it in non_archived if it.visa_status == "canada_authorized")
        not_spec = sum(1 for it in non_archived if it.visa_status == "not_specified")

        by_repo: dict[str, int] = {}
        by_cat: dict[str, int] = {}
        for it in non_archived:
            by_repo[it.source_repo_id] = by_repo.get(it.source_repo_id, 0) + 1
            by_cat[it.category] = by_cat.get(it.category, 0) + 1

        return GitHubInternshipStats(
            total_listings=total,
            active_listings=active,
            closed_listings=closed,
            archived_listings=archived,
            visa_sponsored_count=sponsored,
            no_sponsorship_count=no_spon,
            us_citizens_count=us_cit,
            canada_authorized_count=ca_auth,
            not_specified_count=not_spec,
            repos_count=len(REPO_CONFIGS),
            last_synced_at=get_clock().now().isoformat(),
            by_repo=by_repo,
            by_category=by_cat,
        )

    def _load_cache(self) -> GitHubInternshipsResponse | None:
        cache_path = get_internships_cache_file()
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return GitHubInternshipsResponse.model_validate(data)
            except Exception as err:
                logger.warning("Failed to load user internships cache (%s): %s", cache_path, err)

        # Fallback to bundled seed if user cache is absent or corrupt
        if SEED_FILE.exists():
            try:
                logger.info("Loading bundled internships seed from %s", SEED_FILE)
                with open(SEED_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    resp = GitHubInternshipsResponse.model_validate(data)
                    # Try copying/saving to user cache for fast subsequent loads
                    try:
                        self._save_cache(resp)
                    except Exception:
                        pass
                    return resp
            except Exception as err:
                logger.warning("Failed to load bundled internships seed (%s): %s", SEED_FILE, err)

        return None

    def _save_cache(self, resp: GitHubInternshipsResponse) -> None:
        cache_path = get_internships_cache_file()
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(resp.model_dump_json(indent=2))
            logger.info("Saved internships cache to %s (%d items)", cache_path, len(resp.items))
        except Exception as err:
            logger.error("Failed to save internships cache (%s): %s", cache_path, err)


def cleanup_internships_file(target_file: Path) -> dict[str, Any]:
    """
    Run one-time cleanup migration against specified internships json file:
    1. Deduplicates cross-repository identical listings.
    2. Protects user-saved/tracked applications.
    3. Archives stale (past season e.g. 2026, closed > 30 days).
    4. Computes accurate stats.
    """
    if not target_file.exists():
        return {"error": "file_not_found"}

    with open(target_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_items = [GitHubInternshipItem.model_validate(it) for it in data.get("items", [])]
    before_count = len(raw_items)

    # 1. Deduplicate by canonical key
    deduped_by_key: dict[str, GitHubInternshipItem] = {}
    for it in raw_items:
        k = canonical_internship_key(it.company, it.role, it.location)
        if k in deduped_by_key:
            deduped_by_key[k] = merge_internships(deduped_by_key[k], it)
        else:
            deduped_by_key[k] = it

    # 2. User tracking protection
    tracked_urls, tracked_pairs = get_user_tracked_internships()

    now_iso = get_clock().now().isoformat()
    for k, it in deduped_by_key.items():
        is_tracked = is_internship_user_tracked(it, tracked_urls, tracked_pairs)
        if not is_tracked:
            if it.season and it.season <= "2026":
                it.is_archived = True
                it.archived_at = it.archived_at or now_iso
                it.archived_reason = f"Past season ({it.season})"
            elif it.is_closed and parse_age_days(it.date_posted) >= 30:
                it.is_archived = True
                it.archived_at = it.archived_at or now_iso
                it.archived_reason = "Closed listing older than 30 days"
        else:
            it.is_archived = False

    cleaned_items = list(deduped_by_key.values())
    service = GitHubInternshipsService()
    stats = service._compute_stats(cleaned_items)

    repo_metas = [GitHubRepoMeta.model_validate(r) for r in data.get("repositories", [])]
    if not repo_metas:
        repo_metas = [
            GitHubRepoMeta(
                id=cfg["id"],
                name=cfg["name"],
                url=cfg["url"],
                region=cfg["region"],
                year=cfg["year"],
                description=cfg["description"],
            )
            for cfg in REPO_CONFIGS
        ]

    categories_set = {it.category for it in cleaned_items if it.category and not it.is_archived}
    categories = sorted(list(categories_set))

    resp = GitHubInternshipsResponse(
        items=cleaned_items,
        stats=stats,
        repositories=repo_metas,
        categories=categories,
    )

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(resp.model_dump_json(indent=2))

    return {
        "file": str(target_file),
        "before_count": before_count,
        "after_total_count": len(cleaned_items),
        "active_non_archived_count": stats.total_listings,
        "archived_count": stats.archived_listings,
        "closed_count": stats.closed_listings,
    }
