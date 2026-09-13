import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

from ...config import get_settings
from ...logging import get_logger
from .normalizer import generate_normalized_variants, normalize_title

logger = get_logger("scraper.job_title_intelligence.index")

# Generic single-word titles that frequently appear in non-job contexts (team bios, articles)
GENERIC_SINGLE_WORD_TITLES: set[str] = {
    "engineer",
    "manager",
    "director",
    "developer",
    "technician",
    "lead",
    "officer",
    "assistant",
    "specialist",
    "coordinator",
    "analyst",
    "consultant",
    "operator",
    "administrator",
    "associate",
    "worker",
    "mechanic",
    "teacher",
    "supervisor",
    "intern",
    "designer",
    "architect",
    "representative",
    "executive",
    "president",
    "founder",
    "co-founder",
    "partner",
    "author",
    "editor",
    "contributor",
}


class JobTitleIndex:
    """
    In-memory indexed representation of the 73,000+ job title dictionary.
    Loaded once as a thread-safe process-level singleton.
    """

    def __init__(self, json_path: str | Path | None = None) -> None:
        self.json_path = self._resolve_path(json_path)
        self.exact_titles: set[str] = set()
        self.first_word_index: dict[str, set[str]] = {}
        self.internship_titles: list[str] = []
        self.token_to_intern_titles: dict[str, set[str]] = {}
        self.token_to_titles: dict[str, set[str]] = {}
        self.total_titles: int = 0
        self.unique_titles: int = 0
        self.load_time_ms: float = 0.0
        self._load_and_index()


    @staticmethod
    def _resolve_path(custom_path: str | Path | None = None) -> Path:
        if custom_path:
            p = Path(custom_path)
            if p.exists():
                return p

        # 1. Check application settings or environment variable
        env_path = os.environ.get("COMPUST_JOB_TITLES_PATH")
        if env_path and Path(env_path).exists():
            return Path(env_path)

        try:
            settings_path = get_settings().job_titles_path
            if settings_path and Path(settings_path).exists():
                return Path(settings_path)
        except Exception:
            pass

        # 2. Candidate relative paths across project structure
        module_file = Path(__file__).resolve()
        candidate_paths = [
            # Relative to this file: .../important/src/app/scraper/job_title_intelligence/
            module_file.parents[4] / "job-titles.json",
            module_file.parents[3] / "job-titles.json",
            module_file.parents[4] / "important" / "job-titles.json",
            Path.cwd() / "important" / "job-titles.json",
            Path.cwd() / "job-titles.json",
        ]

        for cand in candidate_paths:
            if cand.exists():
                return cand

        # Fallback to default expected path even if non-existent yet (e.g. for testing mocks)
        return candidate_paths[0]

    def _load_and_index(self) -> None:
        t0 = time.perf_counter()
        if not self.json_path.exists():
            logger.warning(
                f"Job title dictionary file not found at: {self.json_path}. Index remains empty.",
                extra={"event": "JOB_TITLES_FILE_MISSING", "path": str(self.json_path)},
            )
            return

        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_list = data.get("job-titles", [])
        if not isinstance(raw_list, list):
            logger.error(f"Unexpected JSON structure in {self.json_path}: 'job-titles' is not a list.")
            return

        self.total_titles = len(raw_list)

        for item in raw_list:
            if not isinstance(item, str):
                continue
            norm = normalize_title(item)
            if not norm:
                continue
            self.exact_titles.add(norm)
            words = norm.split()
            if words:
                first = words[0]
                if first not in self.first_word_index:
                    self.first_word_index[first] = set()
                self.first_word_index[first].add(norm)

            # Token indexing
            tokens = set(re.findall(r"\b[a-z0-9]{3,}\b", norm))
            for tok in tokens:
                if tok not in self.token_to_titles:
                    self.token_to_titles[tok] = set()
                self.token_to_titles[tok].add(norm)

            is_intern = bool(re.search(r"\b(intern|internship|trainee|apprentice|co-op)\b", norm))
            if is_intern:
                self.internship_titles.append(norm)
                for tok in tokens:
                    if tok not in self.token_to_intern_titles:
                        self.token_to_intern_titles[tok] = set()
                    self.token_to_intern_titles[tok].add(norm)

            # Also index variants like 'front end' <-> 'frontend'
            for variant in generate_normalized_variants(item):
                self.exact_titles.add(variant)
                v_words = variant.split()
                if v_words:
                    v_first = v_words[0]
                    if v_first not in self.first_word_index:
                        self.first_word_index[v_first] = set()
                    self.first_word_index[v_first].add(variant)

        self.unique_titles = len(self.exact_titles)
        self.load_time_ms = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(
            f"Job title intelligence index built in {self.load_time_ms}ms with {self.unique_titles} unique normalized titles ({len(self.internship_titles)} internship titles).",
            extra={
                "event": "JOB_TITLES_INDEX_READY",
                "load_time_ms": self.load_time_ms,
                "total_titles": self.total_titles,
                "unique_titles": self.unique_titles,
                "internship_titles": len(self.internship_titles),
            },
        )

    def is_known_title(self, normalized_text: str) -> bool:
        """Check whether normalized_text is in the title index."""
        return normalized_text in self.exact_titles

    def find_related_internship_titles(self, field_or_keyword: str, limit: int = 20) -> list[str]:
        """
        Identify job titles from the dataset that relate to the given field or query.
        Returns a ranked list of relevant internship and domain titles.
        """
        if not field_or_keyword:
            return []

        norm_query = normalize_title(field_or_keyword)
        query_tokens = [t for t in re.findall(r"\b[a-z0-9]{3,}\b", norm_query) if t not in {"intern", "internship", "job", "jobs", "summer"}]

        matched_intern_titles: dict[str, float] = {}

        # Search in pre-indexed internship titles
        for tok in query_tokens:
            for title in self.token_to_intern_titles.get(tok, set()):
                title_tokens = set(title.split())
                overlap = len(set(query_tokens) & title_tokens)
                matched_intern_titles[title] = max(matched_intern_titles.get(title, 0.0), overlap * 2.0)

        # Additional semantic handles for security/cyber
        if "cyber" in norm_query or "security" in norm_query:
            for t in ["cyber", "security"]:
                for title in self.token_to_intern_titles.get(t, set()):
                    matched_intern_titles[title] = max(matched_intern_titles.get(title, 0.0), 1.5)

        # Domain title fallback for technical roles
        domain_titles: dict[str, float] = {}
        for tok in query_tokens:
            for title in self.token_to_titles.get(tok, set()):
                if len(title.split()) <= 4:
                    overlap = len(set(query_tokens) & set(title.split()))
                    domain_titles[title] = max(domain_titles.get(title, 0.0), float(overlap))

        sorted_intern = sorted(matched_intern_titles.items(), key=lambda x: (-x[1], len(x[0])))
        results = [t[0].title() for t in sorted_intern]

        if len(results) < limit:
            sorted_domain = sorted(domain_titles.items(), key=lambda x: (-x[1], len(x[0])))
            for dt, score in sorted_domain:
                if score >= 1.0:
                    cand = f"{dt.title()} Intern"
                    if cand not in results and dt.title() not in results:
                        results.append(cand)
                if len(results) >= limit:
                    break

        return results[:limit]


    def get_specificity(self, title: str) -> float:
        """
        Compute specificity score (0.0 to 1.0) for a title.
        Single-word generic titles get 0.25 (weak evidence).
        2-word titles get 0.70.
        3+ word titles or specialized titles get 1.0.
        """
        norm = normalize_title(title)
        words = norm.split()
        word_count = len(words)

        if word_count <= 1:
            if norm in GENERIC_SINGLE_WORD_TITLES:
                return 0.25
            return 0.40
        elif word_count == 2:
            return 0.70
        else:
            return 1.0

    def stats(self) -> dict[str, Any]:
        return {
            "path": str(self.json_path),
            "total_titles": self.total_titles,
            "unique_titles": self.unique_titles,
            "load_time_ms": self.load_time_ms,
            "first_word_keys": len(self.first_word_index),
        }


_GLOBAL_INDEX: JobTitleIndex | None = None
_INDEX_LOCK = threading.Lock()


def get_job_title_index(custom_path: str | Path | None = None) -> JobTitleIndex:
    """Retrieve or initialize the thread-safe global JobTitleIndex singleton."""
    global _GLOBAL_INDEX
    if _GLOBAL_INDEX is None:
        with _INDEX_LOCK:
            if _GLOBAL_INDEX is None:
                _GLOBAL_INDEX = JobTitleIndex(json_path=custom_path)
    return _GLOBAL_INDEX


def reset_job_title_index() -> None:
    """Reset the singleton instance (useful in test teardown/fixtures)."""
    global _GLOBAL_INDEX
    with _INDEX_LOCK:
        _GLOBAL_INDEX = None
