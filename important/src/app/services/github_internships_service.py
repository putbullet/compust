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

STORAGE_DIR = Path(__file__).resolve().parents[3] / "storage"
CACHE_FILE = STORAGE_DIR / "github_internships_cache.json"

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


class GitHubInternshipsService:
    """Service to fetch, parse, cache, and serve opportunities from active GitHub repos."""

    def __init__(self) -> None:
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    def get_curated_internships(
        self,
        repo_id: str | None = None,
        visa_status: str | None = None,
        category: str | None = None,
        search: str | None = None,
        open_only: bool = False,
    ) -> GitHubInternshipsResponse:
        """Return curated internships from cache (or parse/fetch if cache absent)."""
        cached_data = self._load_cache()
        if not cached_data:
            cached_data = self.sync_all_repos()

        items = cached_data.items

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
        """Synchronize all 7 repositories live from GitHub and update cache."""
        all_items: list[GitHubInternshipItem] = []
        repo_metas: list[GitHubRepoMeta] = []
        categories_set: set[str] = set()

        for config in REPO_CONFIGS:
            try:
                content = self._fetch_repo_content(config)
                items = self._parse_repo(config, content)
                all_items.extend(items)
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
                for it in items:
                    if it.category:
                        categories_set.add(it.category)
            except Exception as exc:
                logger.error("Failed to parse repo %s: %s", config['id'], exc)

        categories = sorted(list(categories_set))
        stats = self._compute_stats(all_items)

        response = GitHubInternshipsResponse(
            items=all_items,
            stats=stats,
            repositories=repo_metas,
            categories=categories,
        )

        self._save_cache(response)
        return response

    def _fetch_repo_content(self, config: dict[str, str]) -> str:
        """Fetch raw content from GitHub raw URL with timeout and fallback."""
        url = config["raw_url"]
        logger.info("Fetching repo content: %s", url)
        try:
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                resp = client.get(url, headers={"User-Agent": "Compust-CareerEngine/2.0"})
                resp.raise_for_status()
                return resp.text
        except Exception as err:
            logger.warning("Live fetch failed for %s (%s). Attempting local scratch fallback.", url, err)
            # Try to read from local scratch if available
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
        total = len(items)
        active = sum(1 for it in items if not it.is_closed)
        closed = sum(1 for it in items if it.is_closed)

        sponsored = sum(1 for it in items if it.visa_status == "sponsors_visa")
        no_spon = sum(1 for it in items if it.visa_status == "no_sponsorship")
        us_cit = sum(1 for it in items if it.visa_status == "us_citizen_only")
        ca_auth = sum(1 for it in items if it.visa_status == "canada_authorized")
        not_spec = sum(1 for it in items if it.visa_status == "not_specified")

        by_repo: dict[str, int] = {}
        by_cat: dict[str, int] = {}
        for it in items:
            by_repo[it.source_repo_id] = by_repo.get(it.source_repo_id, 0) + 1
            by_cat[it.category] = by_cat.get(it.category, 0) + 1

        return GitHubInternshipStats(
            total_listings=total,
            active_listings=active,
            closed_listings=closed,
            visa_sponsored_count=sponsored,
            no_sponsorship_count=no_spon,
            us_citizens_count=us_cit,
            canada_authorized_count=ca_auth,
            not_specified_count=not_spec,
            repos_count=len(REPO_CONFIGS),
            last_synced_at=datetime.now(timezone.utc).isoformat(),
            by_repo=by_repo,
            by_category=by_cat,
        )

    def _load_cache(self) -> GitHubInternshipsResponse | None:
        if not CACHE_FILE.exists():
            return None
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return GitHubInternshipsResponse.model_validate(data)
        except Exception as err:
            logger.warning("Failed to load internships cache: %s", err)
            return None

    def _save_cache(self, resp: GitHubInternshipsResponse) -> None:
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                f.write(resp.model_dump_json(indent=2))
            logger.info("Saved internships cache to %s (%d items)", CACHE_FILE, len(resp.items))
        except Exception as err:
            logger.error("Failed to save internships cache: %s", err)
