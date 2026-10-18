"""
tests/test_ai_gateway_structural.py
====================================
Structural and integration enforcement tests for the Unified AI Gateway.

Enforces:
1. Architectural purity: No module outside `src/app/services/ai_gateway.py` and `src/app/services/ai_service.py`
   may import `OllamaProvider`, `GeminiProvider`, or `OpenAIProvider` directly, nor hardcode '11434'.
2. Gateway spy tests: All AI features route their LLM requests through `generate_completion` / the Gateway:
   - AI Assistant (answer_user_query)
   - Job Targeting Assistant (_stage1_extract_requirements, _stage4_materials)
   - Suggested Resume Customization (get_ai_resume_customization with cache)
   - ATS Checker (evaluate_resume_ats)
   - Scraper Diagnostics Assistant (explain_scraper_run)
   - Mock Interview Analysis (evaluate_answer)
3. Provider isolation: When Gemini is selected, Gemini receives requests and Ollama receives zero.
   When switched back to Ollama, Ollama receives requests and Gemini receives zero.
"""

import ast
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from src.app.services.ai_gateway import (
    AIProviderType,
    generate_completion,
)


# ─── 1. Structural Purity Test ───────────────────────────────────────────────

def test_no_direct_provider_imports_outside_gateway() -> None:
    """Ensure no application module imports provider implementations directly."""
    src_dir = Path(__file__).resolve().parent.parent / "src" / "app"
    forbidden_symbols = {"OllamaProvider", "GeminiProvider", "OpenAIProvider"}
    allowed_rel_paths = {
        Path("services/ai_gateway.py"),
        Path("services/ai_service.py"),  # Backwards-compat re-export shim
    }

    violations = []

    for py_file in src_dir.rglob("*.py"):
        rel_path = py_file.relative_to(src_dir)
        if rel_path in allowed_rel_paths:
            continue

        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in forbidden_symbols:
                        violations.append(f"{rel_path}:{node.lineno} imports '{alias.name}' directly")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in forbidden_symbols:
                        violations.append(f"{rel_path}:{node.lineno} imports '{alias.name}' directly")

    assert not violations, "Direct provider imports found outside ai_gateway:\n" + "\n".join(violations)


def test_no_hardcoded_ollama_port_outside_config() -> None:
    """Ensure '11434' is not hardcoded in application logic outside config/gateway."""
    src_dir = Path(__file__).resolve().parent.parent / "src" / "app"
    allowed_rel_paths = {
        Path("config.py"),
        Path("services/ai_gateway.py"),
        Path("services/ai_service.py"),
    }

    violations = []
    for py_file in src_dir.rglob("*.py"):
        rel_path = py_file.relative_to(src_dir)
        if rel_path in allowed_rel_paths:
            continue

        content = py_file.read_text(encoding="utf-8")
        if "11434" in content:
            violations.append(f"{rel_path} contains hardcoded '11434'")

    assert not violations, "Hardcoded '11434' port found in:\n" + "\n".join(violations)


# ─── 2. Feature Spy Tests (Routing through Gateway) ──────────────────────────

def test_ai_assistant_routes_through_gateway() -> None:
    """AI Assistant (answer_user_query) must route through generate_completion."""
    from src.app.services.ai_tools import answer_user_query

    mock_db = MagicMock()
    mock_prov = MagicMock()
    mock_prov.is_available.return_value = True
    mock_prov.get_active_model.return_value = "mock-model"
    with patch("src.app.services.ai_tools.generate_completion", return_value="Test answer from gateway") as mock_gc:
        with patch("src.app.services.ai_tools.get_provider", return_value=mock_prov):
            with patch("src.app.services.ai_tools.check_ollama_runtime", return_value=True):
                res = answer_user_query("What jobs do I have?", db=mock_db)
                assert mock_gc.called
                assert res["answer"] == "Test answer from gateway"


def test_job_assistant_routes_through_gateway() -> None:
    """Job targeting assistant functions must route through generate_completion."""
    from src.app.services.job_assistant import (
        _stage1_extract_requirements,
        _stage4_materials,
        CandidateContext,
        CandidateContextSkill,
        ExternalJobInput,
    )

    job_input = ExternalJobInput(
        target_role="Software Engineer",
        job_description="We are seeking a Backend Engineer with strong Python and FastAPI experience.",
        company="Acme",
    )
    candidate_ctx = CandidateContext(
        user_id=1,
        full_name="Alex Doe",
        email="alex@example.com",
        headline="Full Stack Engineer",
        skills=[
            CandidateContextSkill(name="Python", category="technical"),
            CandidateContextSkill(name="FastAPI", category="technical"),
        ],
    )

    with patch("src.app.services.job_assistant.generate_completion", return_value='[{"title": "Python skill", "importance": "critical", "category": "technical", "rationale": "Core"}]') as mock_gc:
        with patch("src.app.services.job_assistant.check_ollama_runtime", return_value=True):
            reqs = _stage1_extract_requirements(job_input)
            assert mock_gc.called
            assert len(reqs) >= 1

    materials_json = (
        '{"cold_email": {"subject": "Application", "body": "Cold Email body..."}, '
        '"short_message": {"body": "DM body..."}, '
        '"motivation_letter": {"subject": "Cover Letter", "body": "Letter body..."}}'
    )
    with patch("src.app.services.job_assistant.generate_completion", return_value=materials_json) as mock_gc:
        with patch("src.app.services.job_assistant.check_ollama_runtime", return_value=True):
            materials = _stage4_materials(candidate_ctx, job_input)
            assert mock_gc.called
            assert len(materials) == 3
            assert materials[0].generated is True


def test_resume_customization_routes_and_caches() -> None:
    """Suggested resume customization must route through gateway and cache results."""
    from src.app.services.resume_customization import (
        get_ai_resume_customization,
        clear_resume_customization_cache,
    )

    clear_resume_customization_cache()

    mock_db = MagicMock()
    mock_job = MagicMock()
    mock_job.id = 999
    mock_job.title = "Backend Engineer"
    mock_job.description = "Python and SQL required"

    mock_resume = MagicMock()
    mock_resume.id = 123
    mock_resume.raw_text = "Experienced in Python."
    mock_resume.parsed_sections = {"skills": ["Python"]}
    mock_resume.structured_data = {}
    mock_resume.updated_at = "2026-10-17T00:00:00"

    fake_resp = "• Emphasize your 5 years of building microservices in Python\n• Highlight PostgreSQL optimization experience"

    with patch("src.app.services.resume_customization.get_job_skills", return_value=["Python", "PostgreSQL"]):
        with patch("src.app.services.resume_customization.is_ai_available", return_value=True):
            with patch("src.app.services.resume_customization.get_provider") as mock_gp:
                prov = MagicMock()
                prov.is_available.return_value = True
                prov.get_active_model.return_value = "qwen3.5:0.8b"
                mock_gp.return_value = prov

                with patch("src.app.services.resume_customization.generate_completion", return_value=fake_resp) as mock_gc:
                    # First call: triggers LLM
                    res1 = get_ai_resume_customization(mock_db, mock_job, mock_resume)
                    assert mock_gc.call_count == 1
                    assert len(res1.get("suggestions", [])) >= 1

                    # Second call with same job, resume, version, provider, model: MUST use cache
                    res2 = get_ai_resume_customization(mock_db, mock_job, mock_resume)
                    assert mock_gc.call_count == 1  # Cache hit, zero extra LLM call
                    assert res2 == res1


def test_ats_checker_routes_through_gateway() -> None:
    """ATS Checker must route through generate_completion."""
    from src.app.services.ats_checker import evaluate_resume_ats

    sample_resume = (
        "Alex Doe\nSenior Backend Engineer\nEmail: alex@example.com\nPhone: +1 555-0100\n\n"
        "Experience:\n- Built resilient distributed systems with Python and FastAPI.\n"
        "- Optimized PostgreSQL queries reducing latency by 40%.\n\n"
        "Skills: Python, FastAPI, Docker, PostgreSQL, React."
    )

    fake_ats_json = (
        '{"overall_score": 88, "verdict": "Competitive", "categories": [], '
        '"feedback": [], "keywords_found": ["Python"], "keywords_missing": [], '
        '"recommended_action_verbs": ["Spearheaded"], "provider": "ollama"}'
    )

    with patch("src.app.services.ats_checker.generate_completion", return_value=fake_ats_json) as mock_gc:
        with patch("src.app.services.ats_checker.get_active_provider", return_value=AIProviderType.OLLAMA):
            res = evaluate_resume_ats(sample_resume, job_description="Looking for Python developer")
            assert mock_gc.called
            assert res.overall_score == 88


def test_scraper_diagnostics_routes_through_gateway() -> None:
    """Scraper diagnostics assistant must route through generate_completion."""
    from src.app.services.scraper_assistant import explain_scraper_run

    sample_report = {
        "company_name": "TestCorp",
        "target_url": "https://careers.testcorp.com",
        "http_status": 403,
        "raw_response_snippet": "Cloudflare Access Denied",
        "jobs_found": 0,
    }

    fake_expl_json = '{"summary": "Cloudflare challenge encountered", "reasons_breakdown": {}, "discrepancy_explanation": null, "recommendations": ["Enable headless browser fallback"]}'

    with patch("src.app.services.scraper_assistant.get_provider") as mock_gp:
        prov = MagicMock()
        prov.is_available.return_value = True
        prov.get_active_model.return_value = "gemini-2.5-flash"
        mock_gp.return_value = prov

        with patch("src.app.services.scraper_assistant.generate_completion", return_value=fake_expl_json) as mock_gc:
            res = explain_scraper_run(sample_report)
            assert mock_gc.called
            assert "Cloudflare" in res.get("summary", "")


def test_mock_interview_routes_through_gateway() -> None:
    """Behavioral mock interview analysis must route through generate_completion."""
    from src.app.services.mock_interview_ai import evaluate_answer

    fake_eval_json = '{"score": 85, "strengths": ["Clear communication"], "improvements": ["Provide more context"], "rubric_breakdown": {}}'

    with patch("src.app.services.mock_interview_ai.generate_completion", return_value=fake_eval_json) as mock_gc:
        res = evaluate_answer(
            question_title="Handling tight deadlines",
            key_concepts=["Prioritization", "Communication"],
            transcript="I prioritized core features, communicated proactively with stakeholders, and delivered on time.",
            question_type="behavioral",
        )
        assert mock_gc.called
        assert res["score"] == 85


# ─── 3. Provider Isolation Verification ──────────────────────────────────────

def test_gemini_active_calls_gemini_only() -> None:
    """When Gemini is selected, Gemini receives requests and Ollama receives zero."""
    with patch("src.app.services.ai_gateway.get_active_provider", return_value=AIProviderType.GEMINI):
        with patch("src.app.services.ai_gateway.get_selected_model", return_value="gemini-2.5-flash"):
            with patch("src.app.services.ai_gateway.load_ai_config", return_value={"gemini_consent_given": True}):
                with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyTestKeyEnforcement123"}):
                    with patch("src.app.services.ai_gateway.GeminiProvider.generate", return_value="Gemini response") as mock_gemini:
                        with patch("src.app.services.ai_gateway.OllamaProvider.generate") as mock_ollama:
                            resp = generate_completion("Explain microservices")
                            assert resp == "Gemini response"
                            assert mock_gemini.call_count == 1
                            assert mock_ollama.call_count == 0


def test_ollama_active_calls_ollama_only() -> None:
    """When Ollama is selected, Ollama receives requests and Gemini receives zero."""
    with patch("src.app.services.ai_gateway.get_active_provider", return_value=AIProviderType.OLLAMA):
        with patch("src.app.services.ai_gateway.get_selected_model", return_value="qwen3.5:0.8b"):
            with patch("src.app.services.ai_gateway.OllamaProvider.generate", return_value="Ollama response") as mock_ollama:
                with patch("src.app.services.ai_gateway.GeminiProvider.generate") as mock_gemini:
                    resp = generate_completion("Explain microservices")
                    assert resp == "Ollama response"
                    assert mock_ollama.call_count == 1
                    assert mock_gemini.call_count == 0
