import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from src.app.main import app

client = TestClient(app)


def test_ai_engineering_track_hero_banner_asset_exists():
    """Verify AI track hero illustration exists and resolves properly."""
    res = client.get("/api/v1/interview-prep/domains")
    assert res.status_code == 200
    domains = res.json()
    ai_domain = next((d for d in domains if d["id"] == "ai_tech_interview"), None)
    assert ai_domain is not None
    assert ai_domain["hero_illustration"] in [
        "/illustrations/ai_tech_hero.png",
        "/illustrations/ai_engineering_banner.png",
    ]

    # Verify both physical files exist in frontend/public/illustrations
    illustrations_dir = (
        Path(__file__).resolve().parent.parent / "frontend" / "public" / "illustrations"
    )
    assert (illustrations_dir / "ai_tech_hero.png").is_file()
    assert (illustrations_dir / "ai_engineering_banner.png").is_file()


def test_interview_prep_math_formulas_present_in_ai_questions():
    """Verify LaTeX math formulas (KaTeX targets) are present in question content."""
    res = client.get(
        "/api/v1/interview-prep/questions/ai_tech_interview/ai-what-is-the-transformer-architecture-and-how-does-self-attention-work"
    )
    assert res.status_code == 200
    q = res.json()
    assert "\\text{Attention}" in q["markdown_content"]
    assert "\\sqrt{d_k}" in q["markdown_content"]
    assert "$$\\text{Attention}" in q["markdown_content"] or "$$" in q["markdown_content"]


def test_interview_prep_next_prev_navigation_longest_title():
    """Verify Next/Previous navigation links exist and carry full titles for UI truncation."""
    res = client.get("/api/v1/interview-prep/domains/ai_tech_interview/tree")
    assert res.status_code == 200
    tree = res.json()
    assert len(tree["categories"]) > 0
    first_q_slug = tree["categories"][0]["topics"][0]["questions"][0]["slug"]

    detail_res = client.get(
        f"/api/v1/interview-prep/questions/ai_tech_interview/{first_q_slug}"
    )
    assert detail_res.status_code == 200
    detail = detail_res.json()
    if detail.get("next_question"):
        assert len(detail["next_question"]["title"]) > 0
        assert "slug" in detail["next_question"]
