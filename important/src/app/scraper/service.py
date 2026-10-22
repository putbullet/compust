"""
src/app/scraper/service.py
==========================
Unified scraper service facade combining crawler, registry, cooldown,
compliance checking, and run lifecycle management.
"""
from __future__ import annotations

from .robots_checker import verify_target_robots_compliance
from .cooldown import is_in_cooldown, apply_target_outcome
from .registry import get_strategy_for_target
from .crawler import crawl_pages
from .run_service import start_scraping_run, finish_scraping_run
from ..repositories.jobs import persist_candidates
from ..logging import ScrapingRunScope

__all__ = [
    "verify_target_robots_compliance",
    "is_in_cooldown",
    "apply_target_outcome",
    "get_strategy_for_target",
    "crawl_pages",
    "start_scraping_run",
    "finish_scraping_run",
    "persist_candidates",
    "ScrapingRunScope",
]
