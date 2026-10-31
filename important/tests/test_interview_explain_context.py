"""
Unit tests for Item 6: Per-Question "Explain with AI" Context Packs and Safe SVG.
Verifies:
1. ExplainContextPack loading across all 3 tracks (AI Tech, Security Engineering, Data Engineering).
2. Domain isolation: Data and AI context packs contain zero security leakage ("attacker", "exploit", "attack blocked").
3. Question detail schema includes explain_context.
4. Deterministic structured fallback generates valid payloads tailored to question content.
5. Dynamic SVG diagrams generate valid SVG with viewBox and semantic shapes, and diagram_type='none' produces no diagram.
6. SVG sanitization neutralizes malicious scripts/foreignObjects.
7. Database caching adheres to SCHEMA_VERSION = 3.
8. Explain with AI returns fallback_reason and can_retry=True when AI provider is unavailable.
"""

import asyncio
import pytest
from unittest.mock import patch

from src.app.schemas_interview_prep import (
    ExplainContextPack,
    StructuredAIExplanationPayload,
    QuestionAIExplainResponse,
)
from src.app.services.interview_prep import interview_prep_service, SCHEMA_VERSION
from src.app.scraper.sanitizer import sanitize_svg


def test_schema_version_is_3():
    """Verify that schema version is bumped to 3 to invalidate outdated static templates."""
    assert SCHEMA_VERSION == 3


def test_context_packs_loaded_across_all_tracks():
    """Verify context packs are loaded for AI, Security, and Data tracks."""
    # Data Engineering question
    q_data = interview_prep_service.get_question_detail(
        "data_engineering",
        "spark-what-are-the-main-features-of-apache-spark"
    )
    assert q_data is not None
    assert q_data.explain_context is not None
    assert len(q_data.explain_context.key_concepts) >= 2
    assert q_data.explain_context.analogy_seed

    # AI Tech question
    q_ai = interview_prep_service.get_question_detail(
        "ai_tech_interview",
        "ai-what-is-the-transformer-architecture-and-how-does-self-attention-work"
    )
    assert q_ai is not None
    assert q_ai.explain_context is not None
    assert len(q_ai.explain_context.key_concepts) >= 2
    assert q_ai.explain_context.analogy_seed

    # Security Engineering question
    q_sec = interview_prep_service.get_question_detail(
        "security_engineering",
        "sec-what-is-two-factor-authentication-2fa-and-what-factors-compose-it"
    )
    assert q_sec is not None
    assert q_sec.explain_context is not None
    assert len(q_sec.explain_context.key_concepts) >= 2


def test_domain_isolation_no_security_leakage_in_data_and_ai():
    """Verify that Data and AI engineering context packs have no security/attacker terms."""
    forbidden = ["attacker", "exploit", "attack blocked", "adversary", "threat actor"]

    # Check Data Engineering question fallback
    q_data = interview_prep_service.get_question_detail(
        "data_engineering",
        "spark-what-are-the-main-features-of-apache-spark"
    )
    assert q_data is not None
    payload_data = interview_prep_service._build_structured_fallback_payload(q_data, lang="en")
    text_data = (
        payload_data.concept_summary + " " +
        payload_data.analogy + " " +
        " ".join(payload_data.takeaways) + " " +
        " ".join(payload_data.common_mistakes) + " " +
        " ".join(a.label + " " + a.description for a in payload_data.actors)
    ).lower()

    for term in forbidden:
        assert term not in text_data, f"Forbidden term '{term}' leaked into Data Engineering fallback!"

    # Check AI question fallback
    q_ai = interview_prep_service.get_question_detail(
        "ai_tech_interview",
        "ai-what-is-the-transformer-architecture-and-how-does-self-attention-work"
    )
    assert q_ai is not None
    payload_ai = interview_prep_service._build_structured_fallback_payload(q_ai, lang="en")
    text_ai = (
        payload_ai.concept_summary + " " +
        payload_ai.analogy + " " +
        " ".join(payload_ai.takeaways) + " " +
        " ".join(payload_ai.common_mistakes) + " " +
        " ".join(a.label + " " + a.description for a in payload_ai.actors)
    ).lower()

    for term in forbidden:
        assert term not in text_ai, f"Forbidden term '{term}' leaked into AI Engineering fallback!"


def test_dynamic_svg_diagram_generation_and_omission():
    """Verify dynamic SVG is generated when required and omitted when diagram_type is 'none'."""
    # Question with diagram
    q_data = interview_prep_service.get_question_detail(
        "data_engineering",
        "spark-what-are-the-main-features-of-apache-spark"
    )
    assert q_data is not None
    pack_data = interview_prep_service._get_explain_pack(q_data.domain_id, q_data.slug)
    pack_data.diagram_type = "flow"
    pack_data.diagram_brief = "Ingestion -> Stream Engine -> Storage"
    payload = interview_prep_service._build_structured_fallback_payload(q_data, lang="en")
    assert payload.has_diagram is True
    assert payload.svg_diagram is not None
    assert "<svg" in payload.svg_diagram
    assert "viewBox" in payload.svg_diagram

    # Question with diagram_type='none'
    q_definitional = interview_prep_service.get_question_detail(
        "security_engineering",
        "sec-what-is-a-social-engineering-attack-and-how-can-organizations-defend-against-it"
    )
    assert q_definitional is not None
    pack_none = ExplainContextPack(
        key_concepts=["Social Engineering", "Human Factor"],
        common_misconceptions=["Thinking tech alone prevents phishing"],
        analogy_seed="Like a fraudster impersonating a building superintendent.",
        diagram_type="none",
        diagram_brief=None,
        summary_seed="Explains non-technical human manipulation vectors.",
    )
    with patch.object(interview_prep_service, "_get_explain_pack", return_value=pack_none):
        payload_none = interview_prep_service._build_structured_fallback_payload(q_definitional, lang="en")
        assert payload_none.has_diagram is False
        assert payload_none.svg_diagram is None


def test_svg_sanitization_removes_dangerous_markup():
    """Verify sanitize_svg strips scripts, inline javascript, and foreignObject."""
    dangerous = (
        '<svg viewBox="0 0 640 200">'
        '<rect x="10" y="10" width="100" height="50" onclick="alert(1)"/>'
        '<script>alert("xss")</script>'
        '<foreignObject width="100" height="50"><iframe src="evil.com"></iframe></foreignObject>'
        '<text x="20" y="30">Safe Node</text>'
        '</svg>'
    )
    clean = sanitize_svg(dangerous)
    assert "<script" not in clean.lower()
    assert "onclick" not in clean.lower()
    assert "foreignobject" not in clean.lower()
    assert "iframe" not in clean.lower()
    assert "Safe Node" in clean


def test_explain_with_ai_fallback_metadata_when_offline():
    """Verify fallback response contains fallback_reason, can_retry=True, and is_ai_generated=False."""
    with patch("src.app.services.ai_gateway.generate_completion", side_effect=Exception("Ollama unreachable on port 11434")):
        res = asyncio.run(interview_prep_service.explain_with_ai(
            domain_id="data_engineering",
            question_slug="spark-what-are-the-main-features-of-apache-spark",
            force_regenerate=True,
        ))

        assert res is not None
        assert res.is_ai_generated is False
        assert res.can_retry is True
        assert res.fallback_reason is not None
        assert "Ollama unreachable" in res.fallback_reason
        assert res.structured_payload is not None
        assert len(res.structured_payload.actors) >= 2
        assert len(res.structured_payload.takeaways) >= 2
