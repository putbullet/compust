"""
Unit tests for Phase 21: Interview Prep Knowledge Center · Structured & Visual 'Explain with AI'.
Verifies strict JSON schema validation, actor reference resolution, non-duplication value test,
graceful degradation when Ollama is offline, and STAR draft evaluation.
"""

import json
import pytest
from unittest.mock import patch, AsyncMock
from pathlib import Path

from src.app.schemas_interview_prep import (
    Actor,
    ScenarioStep,
    ScenarioVariant,
    Scenario,
    CodeSample,
    ComparisonRow,
    StructuredAIExplanationPayload,
    STAREvaluationResponse,
)
from src.app.services.interview_prep import interview_prep_service, SCHEMA_VERSION


def test_valid_structured_explanation_schema():
    """Verify that a well-formed JSON object validates completely into StructuredAIExplanationPayload."""
    valid_payload = {
        "concept_summary": "Two-Factor Authentication requires two distinct evidence categories.",
        "analogy": "Like needing both a key and a combination lock to open a safe.",
        "actors": [
            {"id": "alice", "role": "legitimate_user", "label": "Alice", "description": "Employee logging in"},
            {"id": "auth_server", "role": "system", "label": "Auth Server", "description": "Identity verification"}
        ],
        "scenario": {
            "title": "2FA Factor Category Separation",
            "variants": [
                {
                    "label": "Without Category Separation",
                    "outcome": "failure",
                    "steps": [
                        {
                            "order": 1,
                            "from": "alice",
                            "to": "auth_server",
                            "action": "Submits password and pet name",
                            "payload": "password + security question",
                            "annotation": "Both are knowledge",
                            "status": "normal"
                        },
                        {
                            "order": 2,
                            "from": "auth_server",
                            "to": "alice",
                            "action": "Rejects session due to duplicate category",
                            "payload": "401 Unauthorized",
                            "annotation": "Rejected: Same factor type",
                            "status": "blocked"
                        }
                    ]
                },
                {
                    "label": "With True 2FA",
                    "outcome": "success",
                    "steps": [
                        {
                            "order": 1,
                            "from": "alice",
                            "to": "auth_server",
                            "action": "Submits password and hardware key signature",
                            "payload": "password + FIDO2",
                            "annotation": "Knowledge + Possession",
                            "status": "secure"
                        }
                    ]
                }
            ]
        },
        "code_sample": {
            "language": "python",
            "code": "def verify(user, factors): return len({f.type for f in factors}) >= 2",
            "explanation_lines": [{"line": 1, "note": "Validates distinct categories"}]
        },
        "comparison_table": [
            {"criterion": "Knowledge", "option_a": "Something you know", "option_b": "Password, PIN"},
            {"criterion": "Possession", "option_a": "Something you have", "option_b": "FIDO2 key, TOTP"}
        ],
        "takeaways": ["Requires distinct categories.", "Two passwords do not make 2FA."],
        "common_mistakes": ["Confusing 2-step with multi-factor.", "Using SMS OTP without considering SIM swap."]
    }

    obj = StructuredAIExplanationPayload(**valid_payload)
    assert len(obj.actors) == 2
    assert len(obj.scenario.variants) == 2
    assert obj.scenario.variants[0].steps[1].status == "blocked"
    assert obj.code_sample is not None


def test_schema_rejects_unregistered_actor_reference():
    """Verify that steps referencing an undeclared actor ID trigger a validation failure."""
    invalid_payload = {
        "concept_summary": "Test summary",
        "analogy": "Test analogy",
        "actors": [
            {"id": "alice", "role": "legitimate_user", "label": "Alice", "description": "User"}
        ],
        "scenario": {
            "title": "Broken Flow",
            "variants": [
                {
                    "label": "Invalid Reference",
                    "outcome": "failure",
                    "steps": [
                        {
                            "order": 1,
                            "from": "alice",
                            "to": "phantom_server",  # phantom_server not in actors!
                            "action": "Sends request to unknown server",
                            "status": "normal"
                        }
                    ]
                }
            ]
        },
        "code_sample": None,
        "comparison_table": [],
        "takeaways": [],
        "common_mistakes": []
    }

    with pytest.raises(ValueError, match="not in declared actors"):
        StructuredAIExplanationPayload(**invalid_payload)


def test_code_sample_nullable():
    """Verify that conceptual topics without code have code_sample: None without schema errors."""
    payload = {
        "concept_summary": "Conceptual summary",
        "analogy": "Everyday comparison",
        "actors": [
            {"id": "system_a", "role": "system", "label": "System A", "description": "Core"},
            {"id": "system_b", "role": "system", "label": "System B", "description": "Peer"}
        ],
        "scenario": {
            "title": "Conceptual Flow",
            "variants": [
                {
                    "label": "Definitional Variant",
                    "outcome": "success",
                    "steps": [
                        {"order": 1, "from": "system_a", "to": "system_b", "action": "Syncs state", "status": "normal"}
                    ]
                }
            ]
        },
        "code_sample": None,
        "comparison_table": [{"criterion": "Trade-off", "option_a": "Option A", "option_b": "Option B"}],
        "takeaways": ["Point 1", "Point 2"],
        "common_mistakes": ["Mistake 1"]
    }

    obj = StructuredAIExplanationPayload(**payload)
    assert obj.code_sample is None
    assert len(obj.scenario.variants) == 1


def test_value_test_non_duplication_regression():
    """
    The Value Test (§0 & §1):
    Assert that the generated scenario steps add an actor-based interactive flow
    rather than being a near-duplicate rephrasing of the source answer text.
    """
    question = interview_prep_service.get_question_detail(
        "security_engineering",
        "sec-what-is-two-factor-authentication-2fa-and-what-factors-compose-it"
    )
    assert question is not None

    payload = interview_prep_service._build_structured_fallback_payload(question, lang="en")
    assert payload.scenario is not None
    assert len(payload.scenario.variants) >= 2

    # Extract all step actions and annotations
    step_texts = []
    for variant in payload.scenario.variants:
        for s in variant.steps:
            step_texts.append(s.action.lower())
            if s.annotation:
                step_texts.append(s.annotation.lower())

    step_combined = " ".join(step_texts)
    source_words = set(question.markdown_content.lower().split())
    step_words = set(step_combined.split())

    # Calculate Jaccard similarity: intersection / union
    intersection = source_words.intersection(step_words)
    union = source_words.union(step_words)
    jaccard_similarity = len(intersection) / len(union) if union else 0.0

    # The scenario must introduce new actor dynamics and actions (Jaccard < 0.35)
    assert jaccard_similarity < 0.35, f"Scenario steps are too similar to answer text (Jaccard: {jaccard_similarity:.2f})"
    # The scenario must contain distinct actor IDs
    actor_ids = [a.id for a in payload.actors]
    assert "alice" in actor_ids or "auth_server" in actor_ids


def test_explain_with_ai_offline_degradation():
    """
    Verify that when local Ollama is offline or times out, explain_with_ai gracefully returns
    a fully-formed, schema-validated structured payload with no raw prose dumping.
    """
    import asyncio
    with patch("httpx.AsyncClient.post", side_effect=Exception("Connection refused (Ollama offline)")):
        res = asyncio.run(interview_prep_service.explain_with_ai(
            domain_id="security_engineering",
            question_slug="sec-what-is-two-factor-authentication-2fa-and-what-factors-compose-it",
            mode="simplify",
            language="en"
        ))
        assert res.structured_payload is not None
        assert isinstance(res.structured_payload, StructuredAIExplanationPayload)
        assert len(res.structured_payload.actors) >= 2
        assert len(res.structured_payload.scenario.variants) >= 2
        assert res.ai_model_used == "deterministic-smart-ai"


def test_star_draft_evaluation_metrics_and_ownership():
    """
    Verify STAR draft answer evaluation detects coverage, metrics, and 'I' vs 'We' ratio.
    """
    # 1. Strong candidate answer with high 'I' ownership and metrics
    strong_answer = (
        "In my previous fintech role, our reconciliation pipeline dropped transactions during Black Friday surges (Situation). "
        "As tech lead, I was tasked with bringing p99 latency under 200ms within 3 weeks (Task). "
        "I profiled the database queries, replaced synchronous writes with an Apache Kafka queue with transactional outbox, "
        "and I configured horizontal pod autoscaling in Kubernetes (Action). "
        "As a result, we processed 15,000 req/s with zero dropped transactions, and I reduced p99 latency by 85% from 800ms down to 120ms (Result)."
    )

    eval_result = interview_prep_service.evaluate_star_draft(strong_answer, language="en")
    assert isinstance(eval_result, STAREvaluationResponse)
    assert eval_result.star_coverage["situation"] is True
    assert eval_result.star_coverage["task"] is True
    assert eval_result.star_coverage["action"] is True
    assert eval_result.star_coverage["result"] is True
    assert eval_result.quantified_metrics_score >= 6
    assert eval_result.ownership_ratio["i_count"] >= 3
    assert eval_result.ownership_ratio["i_percentage"] > 50.0

    # 2. Weak candidate answer with missing metrics and heavy 'we' usage
    weak_answer = (
        "We had a project at work where we needed to improve our web app. We discussed with the team and we decided to build some new microservices. We worked together and the client was happy."
    )
    eval_weak = interview_prep_service.evaluate_star_draft(weak_answer, language="en")
    assert eval_weak.quantified_metrics_score < 4
    assert eval_weak.ownership_ratio["we_count"] > eval_weak.ownership_ratio["i_count"]
    assert any("we" in r.lower() for r in eval_weak.recommendations)
