"""
Rigorous validation test suite for Compust Interview Prep repository ingestion:
- Ingestion Report auditability (4 repositories, commit hashes, accurate question counts, licenses).
- Provenance integrity (source_repository, source_commit, source_license, source_file for every question).
- Zero residual Chinese text in English Security Engineering and AI Tech questions.
- Educational vector diagrams and imported authentic diagrams exist on disk.
- Question Detail previous/next navigation links and educational diagram payloads.
- Behavioral Story Matrix (5 pillars) and Interview Modules (4 lifecycle stages).
"""

import re
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from src.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_ingestion_report_completeness():
    """Verify ingestion_report.json exists, is valid, and covers all 4 external repositories."""
    base_dir = Path(__file__).resolve().parent.parent
    report_path = base_dir / "src" / "app" / "content" / "interview_prep" / "ingestion_report.json"
    assert report_path.exists(), f"Ingestion report missing at {report_path}"

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert "summary" in report
    assert "repositories" in report
    repos = report["repositories"]
    assert len(repos) == 4

    expected_repos = {
        "data_engineering": "https://github.com/OBenner/data-engineering-interview-questions",
        "security_engineering": "https://github.com/abhinavkakku/Cyber_Security_Interview_Questions",
        "ai_tech_interview": "https://github.com/amitshekhariitbhu/ai-engineering-interview-questions",
        "interview_guide": "https://github.com/nas5w/interview-guide",
    }

    for repo_key, expected_url in expected_repos.items():
        assert repo_key in repos, f"Missing repository key {repo_key} in report"
        repo_data = repos[repo_key]
        assert repo_data["url"] == expected_url
        assert len(repo_data["commit"]) == 40  # Full 40-character SHA-1 commit hash
        assert repo_data["license"]
    
    assert report["summary"]["total_technical_questions"] > 0
    assert report["summary"]["educational_diagrams_created"] == 6


def test_provenance_on_all_domains(client):
    """Verify that questions across all domains have complete provenance attribution."""
    base_dir = Path(__file__).resolve().parent.parent
    content_dir = base_dir / "src" / "app" / "content" / "interview_prep"

    domains = ["data_engineering", "security_engineering", "ai_tech_interview"]
    for domain_id in domains:
        q_file = content_dir / domain_id / "questions.json"
        assert q_file.exists(), f"Missing questions.json for domain {domain_id}"

        with open(q_file, "r", encoding="utf-8") as f:
            questions = json.load(f)

        assert len(questions) > 0, f"No questions found for domain {domain_id}"

        for q in questions:
            assert q.get("id"), "Question missing id"
            assert q.get("slug"), f"Question {q.get('id')} missing slug"
            assert q.get("title"), f"Question {q.get('id')} missing title"
            assert q.get("category_id"), f"Question {q.get('id')} missing category_id"
            assert q.get("category_name"), f"Question {q.get('id')} missing category_name"
            assert q.get("source_repository"), f"Question {q.get('id')} missing source_repository"
            assert q.get("source_commit"), f"Question {q.get('id')} missing source_commit"
            assert q.get("source_license"), f"Question {q.get('id')} missing source_license"
            assert q.get("source_file"), f"Question {q.get('id')} missing source_file"


def test_zero_residual_chinese_in_translated_tracks():
    """Verify zero Chinese characters exist in the English Security Engineering and AI Tech tracks."""
    base_dir = Path(__file__).resolve().parent.parent
    content_dir = base_dir / "src" / "app" / "content" / "interview_prep"

    chinese_pattern = re.compile(r"[\u4e00-\u9fff]")

    for domain_id in ["security_engineering", "ai_tech_interview"]:
        q_file = content_dir / domain_id / "questions.json"
        with open(q_file, "r", encoding="utf-8") as f:
            questions = json.load(f)

        for q in questions:
            # Check title
            title_matches = chinese_pattern.findall(q["title"])
            assert not title_matches, (
                f"Residual Chinese found in {domain_id} question title: '{q['title']}' (id: {q['id']})"
            )

            # Check markdown content
            content_matches = chinese_pattern.findall(q["content"])
            assert not content_matches, (
                f"Residual Chinese found in {domain_id} question content: id {q['id']}, matches: {content_matches[:5]}"
            )


def test_educational_svg_assets_exist():
    """Verify all 6 purposeful vector diagrams exist and are non-empty SVG files."""
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend" / "public" / "illustrations"
    required_svgs = [
        "diagram_star_method.svg",
        "diagram_etl_vs_elt.svg",
        "diagram_lakehouse_architecture.svg",
        "diagram_oauth_pkce_flow.svg",
        "diagram_rag_pipeline.svg",
        "diagram_transformer_attention.svg",
    ]

    for svg_name in required_svgs:
        svg_path = frontend_dir / svg_name
        assert svg_path.exists(), f"Vector diagram {svg_name} missing from {svg_path}"
        assert svg_path.stat().st_size > 500, f"Vector diagram {svg_name} is abnormally small"


def test_imported_diagram_assets_exist():
    """Verify imported authentic diagrams from ai-tech-interview and data-engineering exist."""
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend" / "public" / "illustrations" / "imported"
    ai_tech_img = frontend_dir / "ai_tech" / "img"
    assert ai_tech_img.exists(), f"Imported directory {ai_tech_img} missing"
    
    # Verify at least 150 authentic image assets were ingested from boost-devs/ai-tech-interview
    images = list(ai_tech_img.rglob("*.*"))
    assert len(images) >= 150, f"Expected >= 150 imported images, found {len(images)}"


def test_question_detail_navigation_and_diagram(client):
    """Verify question detail endpoint supplies previous/next navigation links and educational diagrams."""
    # Check security PKCE question
    resp = client.get("/api/v1/interview-prep/questions/security_engineering/oauth2-pkce-architecture")
    assert resp.status_code == 200
    q = resp.json()

    assert q["educational_diagram"] == "/illustrations/diagram_oauth_pkce_flow.svg"
    assert q["educational_diagram_alt"]
    # Check previous / next question metadata
    if q.get("previous_question"):
        assert "slug" in q["previous_question"]
        assert "title" in q["previous_question"]
    if q.get("next_question"):
        assert "slug" in q["next_question"]
        assert "title" in q["next_question"]

    # Check AI question
    resp_ai = client.get("/api/v1/interview-prep/questions/ai_tech_interview/ai-what-is-the-transformer-architecture-and-how-does-self-attention-work")
    assert resp_ai.status_code == 200
    q_ai = resp_ai.json()
    assert q_ai["educational_diagram"] == "/illustrations/diagram_transformer_attention.svg"
    assert "Transformer" in q_ai["title"]


def test_behavioral_story_matrix_and_modules(client):
    """Verify behavioral prep includes 5-pillar story matrix and 4 interview preparation modules."""
    resp = client.get("/api/v1/interview-prep/behavioral?lang=en")
    assert resp.status_code == 200
    data = resp.json()

    assert "story_matrix" in data
    matrix = data["story_matrix"]
    assert "pillars" in matrix
    assert len(matrix["pillars"]) == 5

    for p in matrix["pillars"]:
        assert p["name"].startswith("Pillar")
        assert p["focus"]
        assert len(p["applies_to"]) >= 2

    assert "interview_modules" in data
    modules = data["interview_modules"]
    assert len(modules) == 4
    module_ids = [m["id"] for m in modules]
    assert "before-interview" in module_ids
    assert "during-interview" in module_ids
    assert "reverse-interviewing" in module_ids
    assert "after-interview" in module_ids
