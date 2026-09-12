"""Pluggable Semantic Enrichment Adapter.

Provides a clean adapter interface for optional semantic similarity and LLM/embedding
enrichment layered on top of the deterministic matching engine.
Maintains a 100% offline, zero-dependency fallback (RuleBasedSemanticFallback)
ensuring all core scraping, parsing, persistence, and matching remain fully functional
without AI or external API keys.
"""

from typing import Protocol
import re

from src.app.models import Job, User
from src.app.schemas_auth import JobMatchExplanation
from src.app.matching.matcher import calculate_job_match


class SemanticEnrichmentAdapter(Protocol):
    """Protocol for semantic enrichment adapters."""

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """Compute a similarity score between two texts in the range [0.0, 1.0]."""
        ...

    def enrich_match(
        self,
        base_match: JobMatchExplanation,
        job: Job,
        user: User,
    ) -> JobMatchExplanation:
        """Layer semantic insights onto an existing deterministic match result."""
        ...


class RuleBasedSemanticFallback:
    """Deterministic, zero-dependency semantic fallback adapter.

    Uses tokenized lexical overlap, n-gram Jaccard similarity, and keyword affinity
    to compute similarity without requiring any external network or machine learning runtime.
    """

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        words = re.findall(r"\b[a-zA-Z0-9_\-\+]{3,}\b", text.lower())
        stopwords = {
            "the", "and", "for", "with", "this", "that", "from", "have", "are",
            "pour", "avec", "dans", "nous", "vous", "sur", "une", "des", "les",
        }
        return {w for w in words if w not in stopwords}

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """Compute Jaccard token similarity between two text snippets."""
        tokens_a = self._tokenize(text_a)
        tokens_b = self._tokenize(text_b)

        if not tokens_a or not tokens_b:
            return 0.0

        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)
        return len(intersection) / len(union) if union else 0.0

    def enrich_match(
        self,
        base_match: JobMatchExplanation,
        job: Job,
        user: User,
    ) -> JobMatchExplanation:
        """Refines match explanation with deterministic profile-to-job semantic cohesion."""
        # Aggregate user textual profile
        user_parts: list[str] = []
        if user.skills:
            user_parts.extend(s.skill for s in user.skills)
        if getattr(user, "experience", None):
            for exp in user.experience:
                user_parts.append(exp.title)
                if exp.description:
                    user_parts.append(exp.description)
        if getattr(user, "education", None):
            for edu in user.education:
                if edu.degree:
                    user_parts.append(edu.degree)
                if edu.field_of_study:
                    user_parts.append(edu.field_of_study)

        user_corpus = " ".join(user_parts)
        job_corpus = f"{job.title} {job.description or ''}"

        similarity = self.compute_similarity(user_corpus, job_corpus)

        # Build enriched factors list without mutating original object in place
        positive_factors = list(base_match.positive_factors)
        missing_factors = list(base_match.missing_factors)
        score = base_match.score

        if similarity >= 0.15:
            affinity_pct = int(similarity * 100)
            positive_factors.append(f"Semantic profile cohesion: ~{affinity_pct}% keyword/domain affinity")
            # Subtle bounded calibration boost (max +5 pts)
            score = min(score + min(int(similarity * 10), 5), 100)

        return JobMatchExplanation(
            job_id=base_match.job_id,
            score=score,
            positive_factors=positive_factors,
            missing_factors=missing_factors,
            category_scores=base_match.category_scores,
        )


class SemanticAdapterRegistry:
    """Manager for pluggable semantic adapters."""

    def __init__(self, adapter: SemanticEnrichmentAdapter | None = None) -> None:
        self._adapter: SemanticEnrichmentAdapter = adapter or RuleBasedSemanticFallback()

    def set_adapter(self, adapter: SemanticEnrichmentAdapter) -> None:
        self._adapter = adapter

    def get_adapter(self) -> SemanticEnrichmentAdapter:
        return self._adapter

    def compute_match(
        self,
        job: Job,
        job_skills: list[str],
        user: User,
        enable_enrichment: bool = True,
    ) -> JobMatchExplanation:
        """Run the core deterministic match, optionally layering semantic enrichment safely."""
        # 1. Deterministic baseline (Always succeeds)
        base_match = calculate_job_match(job, job_skills, user)

        if not enable_enrichment:
            return base_match

        # 2. Safe semantic layer (falls back on exception)
        try:
            return self._adapter.enrich_match(base_match, job, user)
        except Exception:
            # Under any external adapter fault, return pure deterministic baseline
            return base_match


# Global singleton instance
semantic_service = SemanticAdapterRegistry()
