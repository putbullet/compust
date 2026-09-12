from typing import Protocol, runtime_checkable
from bs4 import BeautifulSoup

from ..models import Company, ScrapeTarget
from .capgemini_parser import (
    find_capgemini_next_page_url,
    parse_capgemini_jobs,
    resolve_capgemini_fetch_url,
)
from .custom.deloitte_parser import DeloitteScraperStrategy
from .http_client import FetchedSource
from .inwi_parser import find_inwi_next_page_url, parse_inwi_jobs
from .orange_parser import ParseResult, find_orange_next_page_url, parse_orange_jobs
from .platforms.ashby import AshbyAdapter
from .platforms.greenhouse import GreenhouseAdapter
from .platforms.lever import LeverAdapter
from .platforms.smartrecruiters import SmartRecruitersAdapter
from .platforms.teamtailor import TeamtailorAdapter
from .platforms.workday import WorkdayAdapter
from .platforms.workable import WorkableAdapter
from .source_config import SourceConfig, load_source_configs
from .universal_parser import find_universal_next_page_url, parse_universal_jobs

# Load declarative source registry configurations
_SOURCE_CONFIGS: dict[str, SourceConfig] = {c.strategy_name: c for c in load_source_configs()}


@runtime_checkable
class ScraperStrategy(Protocol):
    name: str
    source_name: str

    def can_handle(self, target: ScrapeTarget, company: Company | None = None) -> bool:
        ...

    def parse(self, source: FetchedSource) -> ParseResult:
        ...

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        ...


class OrangeScraperStrategy:
    name: str = "orange"
    source_name: str = "orange.jobs"

    def can_handle(self, target: ScrapeTarget, company: Company | None = None) -> bool:
        cfg = _SOURCE_CONFIGS.get(self.name)
        if cfg and cfg.matches(target.type, target.url):
            return True
        if cfg and company and company.careers_url and cfg.matches(target.type, company.careers_url):
            return True
        return False

    def parse(self, source: FetchedSource) -> ParseResult:
        return parse_orange_jobs(source)

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        return find_orange_next_page_url(source)


class CapgeminiScraperStrategy:
    name: str = "capgemini"
    source_name: str = "capgemini.com"

    def can_handle(self, target: ScrapeTarget, company: Company | None = None) -> bool:
        cfg = _SOURCE_CONFIGS.get(self.name)
        if cfg and cfg.matches(target.type, target.url):
            return True
        if cfg and company and company.careers_url and cfg.matches(target.type, company.careers_url):
            return True
        return False

    def resolve_fetch_url(self, url: str) -> str:
        return resolve_capgemini_fetch_url(url)

    def parse(self, source: FetchedSource) -> ParseResult:
        return parse_capgemini_jobs(source)

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        return find_capgemini_next_page_url(source)


class InwiScraperStrategy:
    name: str = "inwi"
    source_name: str = "jobs.inwi.ma"

    def can_handle(self, target: ScrapeTarget, company: Company | None = None) -> bool:
        cfg = _SOURCE_CONFIGS.get(self.name)
        if cfg and cfg.matches(target.type, target.url):
            return True
        if cfg and company and company.careers_url and cfg.matches(target.type, company.careers_url):
            return True
        return False

    def parse(self, source: FetchedSource) -> ParseResult:
        return parse_inwi_jobs(source)

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        return find_inwi_next_page_url(source)


# Platform Strategy Wrappers
class GreenhouseScraperStrategy:
    name: str = "greenhouse"
    source_name: str = "boards.greenhouse.io"

    def __init__(self):
        self.adapter = GreenhouseAdapter()

    def can_handle(self, target: ScrapeTarget, company: Company | None = None) -> bool:
        target_type = (target.type or "").lower()
        if target_type == "greenhouse":
            return True
        target_url = target.url or (company.careers_url if company else "") or ""
        return GreenhouseAdapter.can_handle_url(target_url)

    def parse(self, source: FetchedSource) -> ParseResult:
        return self.adapter.parse(source)

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        return self.adapter.find_next_page_url(source)


class LeverScraperStrategy:
    name: str = "lever"
    source_name: str = "jobs.lever.co"

    def __init__(self):
        self.adapter = LeverAdapter()

    def can_handle(self, target: ScrapeTarget, company: Company | None = None) -> bool:
        target_type = (target.type or "").lower()
        if target_type == "lever":
            return True
        target_url = target.url or (company.careers_url if company else "") or ""
        return LeverAdapter.can_handle_url(target_url)

    def parse(self, source: FetchedSource) -> ParseResult:
        return self.adapter.parse(source)

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        return self.adapter.find_next_page_url(source)


class SmartRecruitersScraperStrategy:
    name: str = "smartrecruiters"
    source_name: str = "jobs.smartrecruiters.com"

    def __init__(self):
        self.adapter = SmartRecruitersAdapter()

    def can_handle(self, target: ScrapeTarget, company: Company | None = None) -> bool:
        target_type = (target.type or "").lower()
        if target_type == "smartrecruiters":
            return True
        target_url = target.url or (company.careers_url if company else "") or ""
        return SmartRecruitersAdapter.can_handle_url(target_url)

    def parse(self, source: FetchedSource) -> ParseResult:
        return self.adapter.parse(source)

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        return self.adapter.find_next_page_url(source)


class WorkdayScraperStrategy:
    name: str = "workday"
    source_name: str = "myworkdayjobs.com"

    def __init__(self):
        self.adapter = WorkdayAdapter()

    def can_handle(self, target: ScrapeTarget, company: Company | None = None) -> bool:
        target_type = (target.type or "").lower()
        if target_type == "workday":
            return True
        target_url = target.url or (company.careers_url if company else "") or ""
        return WorkdayAdapter.can_handle_url(target_url)

    def parse(self, source: FetchedSource) -> ParseResult:
        return self.adapter.parse(source)

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        return self.adapter.find_next_page_url(source)


class AshbyScraperStrategy:
    name: str = "ashby"
    source_name: str = "jobs.ashbyhq.com"

    def __init__(self):
        self.adapter = AshbyAdapter()

    def can_handle(self, target: ScrapeTarget, company: Company | None = None) -> bool:
        target_type = (target.type or "").lower()
        if target_type == "ashby":
            return True
        target_url = target.url or (company.careers_url if company else "") or ""
        return AshbyAdapter.can_handle_url(target_url)

    def resolve_fetch_url(self, url: str) -> str:
        return self.adapter.resolve_fetch_url(url)

    def parse(self, source: FetchedSource) -> ParseResult:
        return self.adapter.parse(source)

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        return self.adapter.find_next_page_url(source)


class WorkableScraperStrategy:
    name: str = "workable"
    source_name: str = "apply.workable.com"

    def __init__(self):
        self.adapter = WorkableAdapter()

    def can_handle(self, target: ScrapeTarget, company: Company | None = None) -> bool:
        target_type = (target.type or "").lower()
        if target_type == "workable":
            return True
        target_url = target.url or (company.careers_url if company else "") or ""
        return WorkableAdapter.can_handle_url(target_url)

    def resolve_fetch_url(self, url: str) -> str:
        return self.adapter.resolve_fetch_url(url)

    def parse(self, source: FetchedSource) -> ParseResult:
        return self.adapter.parse(source)

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        return self.adapter.find_next_page_url(source)


class TeamtailorScraperStrategy:
    name: str = "teamtailor"
    source_name: str = "teamtailor.com"

    def __init__(self):
        self.adapter = TeamtailorAdapter()

    def can_handle(self, target: ScrapeTarget, company: Company | None = None) -> bool:
        target_type = (target.type or "").lower()
        if target_type in ("teamtailor", "teamtailor_rss"):
            return True
        target_url = target.url or (company.careers_url if company else "") or ""
        return TeamtailorAdapter.can_handle_url(target_url)

    def parse(self, source: FetchedSource) -> ParseResult:
        return self.adapter.parse(source)

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        return None


class UniversalScraperStrategy:
    name: str = "universal"
    source_name: str = "universal"

    def can_handle(self, target: ScrapeTarget, company: Company | None = None) -> bool:
        # Universal can handle any target as long as URL is present
        return bool(target.url or (company and company.careers_url))

    def resolve_fetch_url(self, url: str) -> str:
        url_lower = (url or "").lower()
        if "ashbyhq.com" in url_lower or "jobs.ashby" in url_lower:
            from .platforms import AshbyAdapter
            return AshbyAdapter.resolve_fetch_url(url)
        if "workable.com" in url_lower or "apply.workable" in url_lower:
            from .platforms import WorkableAdapter
            return WorkableAdapter.resolve_fetch_url(url)
        return url

    def parse(self, source: FetchedSource) -> ParseResult:
        return parse_universal_jobs(source)

    def find_next_page_url(self, source: FetchedSource) -> str | None:
        soup = BeautifulSoup(source.body, "html.parser")
        return find_universal_next_page_url(soup, source.final_url)


# Strategy Registries: Custom, Platform, Universal
_CUSTOM_STRATEGIES: list[ScraperStrategy] = [
    OrangeScraperStrategy(),
    CapgeminiScraperStrategy(),
    InwiScraperStrategy(),
    DeloitteScraperStrategy(),
]

_PLATFORM_STRATEGIES: list[ScraperStrategy] = [
    AshbyScraperStrategy(),
    WorkableScraperStrategy(),
    GreenhouseScraperStrategy(),
    LeverScraperStrategy(),
    SmartRecruitersScraperStrategy(),
    WorkdayScraperStrategy(),
    TeamtailorScraperStrategy(),
]

_UNIVERSAL_STRATEGY = UniversalScraperStrategy()


def register_strategy(strategy: ScraperStrategy) -> None:
    _CUSTOM_STRATEGIES.insert(0, strategy)


def get_strategy_by_name(name: str) -> ScraperStrategy | None:
    target_name = name.strip().lower()
    if target_name in ("universal", "generic", "generic_html", "auto"):
        return _UNIVERSAL_STRATEGY
    for strat in _CUSTOM_STRATEGIES + _PLATFORM_STRATEGIES:
        if strat.name.lower() == target_name:
            return strat
    return None


def get_strategy_for_target(
    target: ScrapeTarget,
    company: Company | None = None,
    preferred_strategy: str | None = None,
) -> ScraperStrategy | None:
    """
    Tiered strategy resolver:
    1. Explicit preferred override (e.g. from test or manual user selection).
    2. Explicit target.type match against custom or platform strategies.
    3. Platform detection based on URL / domain.
    4. Custom company parsers.
    5. Universal parser as automatic universal fallback.
    """
    if preferred_strategy:
        strat = get_strategy_by_name(preferred_strategy)
        if strat:
            return strat

    target_type = (target.type or "").strip().lower()

    # If user explicitly selected a known custom/platform strategy in target.type
    if target_type and target_type not in ("careers", "career", "generic_html", "unknown", "auto"):
        strat = get_strategy_by_name(target_type)
        if strat and strat.can_handle(target, company):
            return strat

    # 2. Check Custom parsers (Orange, Capgemini, Inwi, Deloitte)
    for strategy in _CUSTOM_STRATEGIES:
        if strategy.can_handle(target, company):
            return strategy

    # 3. Check Platform adapters (Greenhouse, Lever, SmartRecruiters, Workday)
    for strategy in _PLATFORM_STRATEGIES:
        if strategy.can_handle(target, company):
            return strategy

    # 4. Universal parser fallback: never fail with 'No source parser is configured'
    if _UNIVERSAL_STRATEGY.can_handle(target, company):
        return _UNIVERSAL_STRATEGY

    return None
