from datetime import datetime, timezone
from src.app.models import Job, User, UserSkill, UserExperience
from src.app.matching.semantic_adapter import (
    RuleBasedSemanticFallback,
    SemanticAdapterRegistry,
    semantic_service,
)
from src.app.matching.matcher import calculate_job_match


def test_rule_based_semantic_fallback_similarity() -> None:
    adapter = RuleBasedSemanticFallback()

    # Similar tech profile and job
    profile_text = "Python FastAPI Docker PostgreSQL Backend Engineer"
    job_text = "Looking for a Backend Python Engineer with Docker and FastAPI experience"
    sim = adapter.compute_similarity(profile_text, job_text)
    assert 0.0 < sim <= 1.0

    # Unrelated texts
    unrelated_job = "Nurse Practitioner healthcare clinical cardiology"
    unrelated_sim = adapter.compute_similarity(profile_text, unrelated_job)
    assert unrelated_sim < sim


def test_semantic_enrichment_and_fault_tolerance() -> None:
    now = datetime.now(timezone.utc)
    job = Job(
        id=42,
        company_id=1,
        country_id=1,
        title="Python Data Engineer",
        description="We require strong Python, SQL, and data pipeline ETL skills.",
        job_url="https://test.corp/42",
        active=True,
        discovered_at=now,
        created_at=now,
        updated_at=now,
    )
    user = User(
        id=1,
        email="dev@test.corp",
        password_hash="hash",
        created_at=now,
        updated_at=now,
    )
    user.skills = [UserSkill(id=1, user_id=1, skill="Python"), UserSkill(id=2, user_id=1, skill="SQL")]
    user.experience = [
        UserExperience(
            id=1,
            user_id=1,
            title="Data Pipeline Developer",
            company_name="Acme",
            experience_type="professional",
        )
    ]

    # Baseline deterministic match
    base_match = calculate_job_match(job, ["Python", "SQL"], user)
    assert base_match.score > 0

    # Enriched match via semantic service
    enriched = semantic_service.compute_match(job, ["Python", "SQL"], user, enable_enrichment=True)
    assert enriched.score >= base_match.score
    assert any("Semantic" in f for f in enriched.positive_factors)

    # Enrichment disabled returns base match
    un_enriched = semantic_service.compute_match(job, ["Python", "SQL"], user, enable_enrichment=False)
    assert un_enriched.score == base_match.score

    # Fault tolerance: Faulty adapter raising exception
    class BrokenAdapter:
        def compute_similarity(self, text_a: str, text_b: str) -> float:
            raise RuntimeError("External AI service unreachable / offline")

        def enrich_match(self, base_match, job, user):
            raise ConnectionError("Timeout contacting remote embedding API")

    custom_registry = SemanticAdapterRegistry(adapter=BrokenAdapter())
    safe_result = custom_registry.compute_match(job, ["Python", "SQL"], user, enable_enrichment=True)
    # Must not raise, returns safe deterministic result
    assert safe_result.score == base_match.score
