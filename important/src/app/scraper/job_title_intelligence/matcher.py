import re
from dataclasses import dataclass
from typing import Any

from bs4 import Tag

from ..universal_parser import EXCLUDED_SECTION_HEADINGS
from .index import JobTitleIndex, get_job_title_index
from .normalizer import (
    generate_normalized_variants,
    normalize_title,
    strip_title_noise,
)


@dataclass(frozen=True)
class TitleMatch:
    raw_text: str
    matched_title: str
    specificity: float
    element: Tag


# Common employment / workplace tags that should not be matched as job titles
EMPLOYMENT_MODALITY_TAGS = {
    "full time",
    "part time",
    "permanent",
    "temporary",
    "contract",
    "contractor",
    "freelance",
    "internship",
    "intern",
    "stage",
    "cdi",
    "cdd",
    "pfe",
    "alternance",
    "remote",
    "hybrid",
    "on site",
    "onsite",
    "telework",
    "wfh",
    "work from home",
}


class JobTitleMatcher:
    """
    Context-aware matcher that evaluates DOM elements against the JobTitleIndex.
    Applies exact normalized matching, noise stripping, variant matching,
    and conservative multi-token window matching.
    """

    def __init__(self, index: JobTitleIndex | None = None) -> None:
        self.index = index or get_job_title_index()

    def match_text(self, text: str, element: Tag) -> TitleMatch | None:
        """
        Evaluate if a text snippet represents a legitimate job title.
        Returns a TitleMatch object or None.
        """
        if not text:
            return None

        clean = text.strip()
        if len(clean) < 3 or len(clean) > 140:
            return None

        # Exclude boilerplate section headings (e.g. "Open Positions", "Join our team")
        clean_lower = clean.lower()
        if any(re.search(pat, clean_lower) for pat in EXCLUDED_SECTION_HEADINGS):
            return None

        norm = normalize_title(clean)
        if norm in EMPLOYMENT_MODALITY_TAGS:
            return None

        # Step 1: Direct normalized match
        if self.index.is_known_title(norm):
            return TitleMatch(
                raw_text=clean,
                matched_title=norm,
                specificity=self.index.get_specificity(norm),
                element=element,
            )

        # Step 2: Variant match (compound word expansion/contraction)
        variants = generate_normalized_variants(clean)
        for v in variants:
            if self.index.is_known_title(v):
                return TitleMatch(
                    raw_text=clean,
                    matched_title=v,
                    specificity=self.index.get_specificity(v),
                    element=element,
                )

        # Step 3: Noise stripped match
        stripped = strip_title_noise(clean)
        if stripped and stripped != clean:
            norm_stripped = normalize_title(stripped)
            if self.index.is_known_title(norm_stripped):
                return TitleMatch(
                    raw_text=clean,
                    matched_title=norm_stripped,
                    specificity=self.index.get_specificity(norm_stripped),
                    element=element,
                )
            for v in generate_normalized_variants(stripped):
                if self.index.is_known_title(v):
                    return TitleMatch(
                        raw_text=clean,
                        matched_title=v,
                        specificity=self.index.get_specificity(v),
                        element=element,
                    )

        # Step 4: Token-aware multi-token window matching
        # Only search windows if text contains 2 to 8 words (not long paragraphs)
        words = norm.split()
        if 2 <= len(words) <= 8:
            # Check substrings from length len(words) down to 2
            for window_len in range(min(len(words), 5), 1, -1):
                for start in range(len(words) - window_len + 1):
                    window = " ".join(words[start : start + window_len])
                    if window in EMPLOYMENT_MODALITY_TAGS:
                        continue
                    if self.index.is_known_title(window):
                        # Multi-token titles only, ensure high specificity
                        spec = self.index.get_specificity(window)
                        if spec >= 0.70:
                            return TitleMatch(
                                raw_text=clean,
                                matched_title=window,
                                specificity=spec,
                                element=element,
                            )

        return None
