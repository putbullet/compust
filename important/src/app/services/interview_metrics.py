"""
Deterministic Speech & Delivery Metrics Calculator for Mock Interview.

DESIGN PRINCIPLE:
This module contains ZERO LLM calls, ZERO external I/O.
All metrics are computed in pure Python using deterministic algorithms,
language-aware tokenization, and regex matching.
"""

from __future__ import annotations

import re
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


# Language-specific filler word dictionaries
FILLER_WORDS_BY_LANG: Dict[str, List[str]] = {
    "en": [
        "um",
        "uh",
        "er",
        "ah",
        "like",
        "you know",
        "sort of",
        "kind of",
        "actually",
        "basically",
        "literally",
        "i mean",
        "right",
        "so yeah",
        "to be honest",
    ],
    "fr": [
        "euh",
        "hum",
        "ben",
        "bon",
        "en fait",
        "du coup",
        "genre",
        "voilà",
        "comment dire",
        "tu vois",
        "en gros",
        "au final",
    ],
    "nl": [
        "eh",
        "ehm",
        "nou",
        "nou ja",
        "eigenlijk",
        "zeg maar",
        "dus",
        "weet je",
        "gewoon",
        "als het ware",
    ],
}

# Pronouns for personal ownership analysis ("I" vs "We")
SINGULAR_PRONOUNS_BY_LANG: Dict[str, Set[str]] = {
    "en": {"i", "me", "my", "mine", "myself"},
    "fr": {"je", "moi", "mon", "ma", "mes", "m'"},
    "nl": {"ik", "mij", "me", "mijn", "mijzelf"},
}

PLURAL_PRONOUNS_BY_LANG: Dict[str, Set[str]] = {
    "en": {"we", "us", "our", "ours", "ourselves"},
    "fr": {"nous", "notre", "nos"},
    "nl": {"wij", "we", "ons", "onze", "onszelf"},
}


@dataclass
class TurnDeliveryMetrics:
    """Calculated delivery metrics for a single interview answer turn."""
    duration_seconds: float
    word_count: int
    wpm: float
    filler_word_count: int
    filler_words: Dict[str, int]
    filler_rate_percent: float
    singular_pronoun_count: int
    plural_pronoun_count: int
    i_vs_we_ratio: float
    longest_pause_seconds: float
    time_to_first_word_seconds: float
    pace_assessment: str  # "slow" | "optimal" | "fast" | "very_fast"
    filler_assessment: str  # "clean" | "moderate" | "high"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "duration_seconds": self.duration_seconds,
            "word_count": self.word_count,
            "wpm": self.wpm,
            "filler_word_count": self.filler_word_count,
            "filler_words": self.filler_words,
            "filler_rate_percent": self.filler_rate_percent,
            "singular_pronoun_count": self.singular_pronoun_count,
            "plural_pronoun_count": self.plural_pronoun_count,
            "i_vs_we_ratio": self.i_vs_we_ratio,
            "longest_pause_seconds": self.longest_pause_seconds,
            "time_to_first_word_seconds": self.time_to_first_word_seconds,
            "pace_assessment": self.pace_assessment,
            "filler_assessment": self.filler_assessment,
        }

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


def calculate_wpm(text: str, duration_seconds: float) -> float:
    """Compute words per minute from text and duration in seconds."""
    if duration_seconds <= 0 or not text:
        return 0.0
    words = tokenize_words(text)
    minutes = duration_seconds / 60.0
    return round(len(words) / minutes, 1)


def tokenize_words(text: str) -> List[str]:
    """Extract lowercase word tokens from transcript."""
    cleaned = re.sub(r"[^\w\s\'-]", " ", text.lower())
    words = [w.strip("'- ") for w in cleaned.split() if w.strip("'- ")]
    return words


def count_filler_words(text: str, language: str = "en") -> Dict[str, Any]:
    """
    Count occurrences of filler words and phrases for the given language.
    Returns {"filler_count": total, "filler_words": dict}.
    """
    lang_key = language.lower() if language.lower() in FILLER_WORDS_BY_LANG else "en"
    fillers = FILLER_WORDS_BY_LANG[lang_key]
    text_lower = f" {text.lower()} "

    counts: Dict[str, int] = {}
    total = 0

    for filler in fillers:
        pattern = r"\b" + re.escape(filler) + r"\b"
        matches = len(re.findall(pattern, text_lower))
        if matches > 0:
            counts[filler] = matches
            total += matches

    return {"filler_count": total, "filler_words": counts}


def calculate_pronoun_ratio(text: str, language: str = "en") -> Tuple[int, int, float]:
    """
    Calculate singular vs plural first-person pronoun ratio.
    Returns (singular_count, plural_count, ratio).
    """
    lang_key = language.lower() if language.lower() in SINGULAR_PRONOUNS_BY_LANG else "en"
    singular_set = SINGULAR_PRONOUNS_BY_LANG[lang_key]
    plural_set = PLURAL_PRONOUNS_BY_LANG[lang_key]

    words = tokenize_words(text)
    sing_count = sum(1 for w in words if w in singular_set)
    plur_count = sum(1 for w in words if w in plural_set)

    ratio = round(sing_count / max(1, plur_count), 2)
    return sing_count, plur_count, ratio


def compute_pronoun_ratio(text: str, language: str = "en") -> Dict[str, Any]:
    """
    Convenience wrapper returning dictionary with i_count, we_count, and ratio.
    """
    sing, plur, ratio = calculate_pronoun_ratio(text, language)
    return {"i_count": sing, "we_count": plur, "ratio": ratio}


def assess_pace(wpm: float) -> str:
    """Classify speaking pace based on standard speech therapy ranges."""
    if wpm <= 0:
        return "unmeasured"
    if wpm < 110:
        return "slow"
    if wpm <= 165:
        return "optimal"
    if wpm <= 195:
        return "fast"
    return "very_fast"


def assess_filler_rate(filler_rate_percent: float) -> str:
    """Classify filler word rate."""
    if filler_rate_percent <= 2.5:
        return "clean"
    if filler_rate_percent <= 5.5:
        return "moderate"
    return "high"


def compute_turn_metrics(
    transcript: str = "",
    duration_seconds: float = 0.0,
    language: str = "en",
    longest_pause: Optional[float] = None,
    time_to_first_word: Optional[float] = None,
    **kwargs: Any,
) -> TurnDeliveryMetrics:
    """
    Compute comprehensive deterministic delivery metrics for a single answer.
    """
    input_text = kwargs.get("text", transcript) or ""
    calc_pause = kwargs.get("longest_pause_seconds", longest_pause)
    calc_ttfw = kwargs.get("time_to_first_word_seconds", time_to_first_word)
    safe_duration = max(0.1, float(duration_seconds or 0.0))
    words = tokenize_words(input_text)
    word_count = len(words)

    # Words Per Minute
    duration_minutes = safe_duration / 60.0
    wpm = round(word_count / duration_minutes, 1) if duration_minutes > 0.05 and word_count > 0 else 0.0

    # Filler words
    f_res = count_filler_words(input_text, language=language)
    if isinstance(f_res, dict):
        filler_count = f_res.get("filler_count", 0)
        filler_dict = f_res.get("filler_words", {})
    else:
        filler_count, filler_dict = f_res
    filler_rate = round((filler_count / max(1, word_count)) * 100.0, 1) if word_count > 0 else 0.0

    # Pronoun ratio
    sing_count, plur_count, ratio = calculate_pronoun_ratio(input_text, language=language)

    # Pauses and time to first word
    calc_pause_val = float(calc_pause) if calc_pause is not None else 0.0
    calc_ttfw_val = float(calc_ttfw) if calc_ttfw is not None else 0.0

    return TurnDeliveryMetrics(
        duration_seconds=round(safe_duration, 1),
        word_count=word_count,
        wpm=wpm,
        filler_word_count=filler_count,
        filler_words=filler_dict,
        filler_rate_percent=filler_rate,
        singular_pronoun_count=sing_count,
        plural_pronoun_count=plur_count,
        i_vs_we_ratio=ratio,
        longest_pause_seconds=round(calc_pause_val, 1),
        time_to_first_word_seconds=round(calc_ttfw_val, 1),
        pace_assessment=assess_pace(wpm),
        filler_assessment=assess_filler_rate(filler_rate),
    )


def aggregate_session_delivery(turns_metrics: List[Any]) -> Dict[str, Any]:
    """
    Aggregate delivery metrics across all completed turns in an interview.
    Accepts TurnDeliveryMetrics instances or dicts.
    """
    if not turns_metrics:
        return {
            "avg_wpm": 0.0,
            "average_wpm": 0.0,
            "overall_pace": "unmeasured",
            "pace_assessment": "Unmeasured",
            "total_words": 0,
            "total_filler_words": 0,
            "overall_filler_rate": 0.0,
            "overall_filler_assessment": "clean",
            "overall_i_vs_we_ratio": 1.0,
            "total_speaking_seconds": 0.0,
            "max_pause_seconds": 0.0,
            "max_longest_pause": 0.0,
        }

    def _val(item: Any, key: str, default: Any = 0) -> Any:
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)

    valid_turns = [m for m in turns_metrics if _val(m, "wpm", 0.0) > 0 or _val(m, "word_count", 0) > 0]
    total_words = sum(_val(m, "word_count", 0) for m in turns_metrics)
    total_duration = sum(_val(m, "duration_seconds", 0.0) for m in turns_metrics)
    total_fillers = sum(_val(m, "filler_word_count", 0) for m in turns_metrics)

    avg_wpm = round(sum(_val(m, "wpm", 0.0) for m in valid_turns) / len(valid_turns), 1) if valid_turns else 0.0
    overall_filler_rate = round((total_fillers / max(1, total_words)) * 100.0, 1)

    total_singular = sum(_val(m, "singular_pronoun_count", 0) for m in turns_metrics)
    total_plural = sum(_val(m, "plural_pronoun_count", 0) for m in turns_metrics)
    overall_ratio = round(total_singular / max(1, total_plural), 2) if total_plural > 0 else float(total_singular or 1.0)

    max_pause = max((_val(m, "longest_pause_seconds", 0.0) for m in turns_metrics), default=0.0)
    pace_text = assess_pace(avg_wpm)

    return {
        "avg_wpm": avg_wpm,
        "average_wpm": avg_wpm,
        "overall_pace": pace_text,
        "pace_assessment": "Ideal speaking pace" if pace_text == "optimal" else ("Speaking slightly fast" if pace_text in ("fast", "very_fast") else "Speaking slightly slow"),
        "total_words": total_words,
        "total_filler_words": total_fillers,
        "overall_filler_rate": overall_filler_rate,
        "overall_filler_assessment": assess_filler_rate(overall_filler_rate),
        "overall_i_vs_we_ratio": overall_ratio,
        "total_speaking_seconds": round(total_duration, 1),
        "max_pause_seconds": round(max_pause, 1),
        "max_longest_pause": round(max_pause, 1),
    }
