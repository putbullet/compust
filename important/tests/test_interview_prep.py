"""
Comprehensive tests for Interview Prep platform:
- Multilingual behavioral preparation (STAR method, common questions in EN/FR/DE).
- Technical domain trees (Data Engineering, Security Engineering, AI / Technology).
- Markdown question rendering, code blocks, difficulty rating, and source attribution.
- Search functionality across technical domains.
- Importer engine: Markdown parsing, relative image resolution, license detection, and Chinese->English translation fixture.
- Security: HTML / script tag sanitization.
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from src.app.main import app
from src.app.services.interview_prep_importer import (
    InterviewPrepImporter,
    detect_chinese_text,
    preserve_tech_terms_translation,
    sanitize_markdown_text,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_behavioral_prep_multilingual_en(client):
    """Verify behavioral prep in English includes STAR method and common HR questions."""
    resp = client.get("/api/v1/interview-prep/behavioral?lang=en")
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "en"
    assert "star_guide" in data
    star = data["star_guide"]
    assert "Situation" in [s["step"] for s in star["steps"]]
    assert "Task" in [s["step"] for s in star["steps"]]
    assert "Action" in [s["step"] for s in star["steps"]]
    assert "Result" in [s["step"] for s in star["steps"]]

    questions = data["questions"]
    assert len(questions) >= 5
    q_titles = [q["question"] for q in questions]
    assert any("yourself" in q.lower() for q in q_titles)
    assert any("strengths" in q.lower() for q in q_titles)


def test_behavioral_prep_multilingual_fr(client):
    """Verify behavioral prep in French has natural professional French terminology."""
    resp = client.get("/api/v1/interview-prep/behavioral?lang=fr")
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "fr"
    star = data["star_guide"]
    assert "STAR" in star["title"]
    assert len(data["questions"]) >= 3
    q_titles = [q["question"] for q in data["questions"]]
    assert any("présenter" in q.lower() for q in q_titles)


def test_behavioral_prep_multilingual_de(client):
    """Verify behavioral prep in German has natural professional German terminology."""
    resp = client.get("/api/v1/interview-prep/behavioral?lang=de")
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "de"
    star = data["star_guide"]
    assert "STAR" in star["title"]
    assert len(data["questions"]) >= 2
    q_titles = [q["question"] for q in data["questions"]]
    assert any("vorstellung" in q.lower() or "erzählen" in q.lower() for q in q_titles)


def test_list_domains(client):
    """Verify exactly the 3 technical tracks are returned with rich metadata."""
    resp = client.get("/api/v1/interview-prep/domains")
    assert resp.status_code == 200
    domains = resp.json()
    domain_ids = [d["id"] for d in domains]
    assert "data_engineering" in domain_ids
    assert "security_engineering" in domain_ids
    assert "ai_tech_interview" in domain_ids

    for d in domains:
        assert d["total_questions"] > 0
        assert d["total_categories"] > 0
        assert d["hero_illustration"]
        assert d["source_repository"]
        assert d["source_license"]


def test_get_domain_tree(client):
    """Verify domain tree contains categories, topics, and questions."""
    resp = client.get("/api/v1/interview-prep/domains/security_engineering/tree")
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"]["id"] == "security_engineering"
    categories = data["categories"]
    assert len(categories) >= 2

    # Check question summaries inside topics
    all_questions = []
    for cat in categories:
        for topic in cat["topics"]:
            all_questions.extend(topic["questions"])

    assert len(all_questions) >= 3
    assert any("oauth" in q["slug"].lower() for q in all_questions)


def test_get_question_detail(client):
    """Verify question detail contains full markdown, code flags, tags, and attribution."""
    resp = client.get("/api/v1/interview-prep/questions/security_engineering/oauth2-pkce-architecture")
    assert resp.status_code == 200
    q = resp.json()
    assert q["slug"] == "oauth2-pkce-architecture"
    assert "OAuth 2.0" in q["title"]
    assert "code_verifier" in q["markdown_content"]
    assert q["has_code"] is True
    assert q["source"]["repository_url"]
    assert q["source"]["license_name"]


def test_search_questions(client):
    """Verify search returns matching questions across domains."""
    resp = client.get("/api/v1/interview-prep/search?q=OAuth")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    assert any("oauth" in r["title"].lower() or "oauth" in r["slug"].lower() for r in results)


def test_markdown_sanitization():
    """Verify malicious script and iframe tags are neutralized."""
    malicious = "## Safe Title\n<script>alert('xss')</script>\nClick [here](javascript:stealCookies())\n<iframe src='bad.html'></iframe>"
    sanitized = sanitize_markdown_text(malicious)
    assert "<script>" not in sanitized
    assert "<iframe>" not in sanitized
    assert "javascript:" not in sanitized
    assert "## Safe Title" in sanitized


def test_chinese_detection_and_translation_pipeline(tmp_path):
    """
    Verify Chinese -> English translation fixture maintains technical terminology
    and generates valid normalized questions.
    """
    chinese_md = tmp_path / "oauth_chinese.md"
    chinese_content = (
        "# 什么是 OAuth 2.0 授权码模式？\n\n"
        "## 核心概念\n"
        "OAuth 2.0 是目前广泛采用的权限认证框架。\n"
        "在微服务和分布式系统中，单点登录（SSO）通常采用 OAuth 2.0 与 JWT 结合。\n\n"
        "### 工作原理\n"
        "客户端通过重定向将用户引导至授权服务器，用户完成登录后返回 Authorization Code。\n"
        "然后客户端携带 Code 和 client_secret 向服务器换取 Access Token。\n\n"
        "```python\n"
        "# 示例代码\n"
        "import requests\n"
        "token_url = 'https://auth.example.com/oauth/token'\n"
        "```\n"
    )
    chinese_md.write_text(chinese_content, encoding="utf-8")

    assert detect_chinese_text(chinese_content) is True

    importer = InterviewPrepImporter(
        content_root=tmp_path / "content",
        public_assets_root=tmp_path / "assets",
    )

    result = importer.process_markdown_file(
        file_path=chinese_md,
        repo_root=tmp_path,
        domain_id="security_engineering",
        domain_title="Security Engineering",
        repo_url="https://github.com/mock/repo",
        license_name="MIT",
        license_notice="MIT License",
        translate_chinese=True,
    )

    assert result is not None
    assert result["was_translated"] is True
    # Verify established technical terms remained in English
    assert "OAuth" in result["markdown_content"]
    assert "JWT" in result["markdown_content"]
    assert "Question" in result["markdown_content"] or "Core Concepts" in result["markdown_content"]
    assert result["source"]["license_name"] == "MIT"


def test_explain_with_ai_smart_fields(client):
    """Verify Explain with AI returns real-world scenario, code sample, and key interview takeaways."""
    resp = client.post(
        "/api/v1/interview-prep/questions/security_engineering/oauth2-pkce-architecture/ai-explain",
        json={
            "mode": "simplify",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_ai_generated"] is True
    assert data["real_world_scenario"] and len(data["real_world_scenario"]) > 20
    assert data["code_sample"] and len(data["code_sample"]) > 10
    assert len(data["key_interview_takeaways"]) >= 2


def test_question_roles_and_experience_levels(client):
    """Verify questions have experience_level and target_roles properly populated."""
    resp = client.get("/api/v1/interview-prep/questions/security_engineering/oauth2-pkce-architecture")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("experience_level")
    assert isinstance(data.get("target_roles"), list)
    assert len(data["target_roles"]) > 0


def test_explain_with_ai_narrative_case_scenario(client):
    """Verify Explain with AI generates a concrete narrative case scenario with named actors (Alice, Bob)."""
    resp = client.post(
        "/api/v1/interview-prep/questions/security_engineering/sec-what-is-a-social-engineering-attack-and-how-can-organizations-defend-against-it/ai-explain",
        json={
            "mode": "simplify",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    scenario = data["real_world_scenario"]
    assert "Case Scenario" in scenario
    assert "Alice" in scenario
    assert "Bob" in scenario
    assert data["code_sample"]
    assert len(data["key_interview_takeaways"]) >= 3
