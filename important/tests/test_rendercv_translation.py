"""test_rendercv_translation.py
Tests for RenderCV translation layer, Typst compilation, and exact pagination.
"""

from pathlib import Path
import pytest
from pypdf import PdfReader

from src.app.services.rendercv_service import (
    build_rendercv_yaml_dict,
    dict_to_yaml_string,
    render_rendercv_artifacts,
    render_rendercv_preview_payload,
)


@pytest.fixture
def sample_resume_data():
    return {
        "profile": {
            "full_name": "Soulaimane Ettabaa",
            "headline": "Ingénieur Sécurité & Systèmes",
            "email": "soulaimane@example.com",
            "phone": "+33 6 12 34 56 78",
            "location": "Paris, France",
            "linkedin": "https://linkedin.com/in/soulaimane",
            "github": "https://github.com/soulaimane",
            "summary": "Élève ingénieur en Sécurité des SI passionné par le DevSecOps.",
        },
        "skills": [
            {"id": "s1", "name": "Python", "category": "Languages", "proficiency": None},
            {"id": "s2", "name": "C++", "category": "Languages", "proficiency": "ADVANCED"},
            {"id": "s3", "name": "Linux", "category": "Systems", "proficiency": "EXPERT"},
            {"id": "s4", "name": "Docker", "category": "DevOps", "proficiency": None},
        ],
        "languages": [
            {"id": "l1", "language": "Français", "proficiency": "native"},
            {"id": "l2", "language": "Anglais", "proficiency": "fluent"},
        ],
        "experience": [
            {
                "id": "e1",
                "company": "CyberSec SAS",
                "title": "Analyste SOC",
                "location": "Paris, France",
                "start_date": "2023-01",
                "end_date": "2024-01",
                "is_current": False,
                "description": "Analyse d'incidents de sécurité.",
                "highlights": [
                    "Détection des menaces avec Wazuh et YARA.",
                    "Automatisation des workflows en Python.",
                ],
            },
            {
                "id": "e2",
                "company": "CloudTech",
                "title": "Lead DevSecOps",
                "location": "Remote",
                "start_date": "2024-02",
                "end_date": "",
                "is_current": True,
                "description": "Gestion des clusters Kubernetes sécurisés.",
                "highlights": ["Mise en place de CI/CD sécurisé."],
            },
        ],
        "education": [
            {
                "id": "ed1",
                "institution": "ENSIMAG",
                "degree": "Diplôme d'Ingénieur",
                "field": "Cybersécurité",
                "location": "Grenoble, France",
                "start_date": "2022-09",
                "end_date": "2025-06",
                "gpa": "Mention Très Bien",
                "description": "Spécialisation en sécurité des architectures distribuées.",
            }
        ],
        "projects": [
            {
                "id": "p1",
                "name": "AuditScanner",
                "technologies": "Python, Django, PostgreSQL",
                "url": "https://github.com/soulaimane/audit-scanner",
                "start_date": "2023",
                "end_date": "2024",
                "description": "Scanner de vulnérabilités statique pour code source.",
                "highlights": ["Plus de 200 règles OWASP implémentées."],
            }
        ],
        "certifications": [
            {
                "id": "c1",
                "name": "Security+",
                "issuer": "CompTIA",
                "issue_date": "2023-05",
            }
        ],
        "custom_sections": [
            {
                "id": "cs1",
                "title": "Centres d'intérêt",
                "items": ["CTF / HackTheBox", "Open Source Contribution"],
            }
        ],
    }


def test_build_rendercv_yaml_dict_french(sample_resume_data):
    """Test translating a French resume into RenderCV YAML dictionary."""
    settings = {
        "template": "modern",
        "language": "fr",
        "theme_color": "#0ea5e9",
        "document_size": "A4",
    }
    yaml_dict = build_rendercv_yaml_dict(sample_resume_data, settings)

    assert yaml_dict["cv"]["name"] == "Soulaimane Ettabaa"
    assert yaml_dict["cv"]["headline"] == "Ingénieur Sécurité & Systèmes"
    assert yaml_dict["locale"]["language"] == "french"
    assert yaml_dict["design"]["page"]["size"] == "a4"
    assert "rgb(14, 165, 233)" in yaml_dict["design"]["colors"]["section_titles"]

    sections = yaml_dict["cv"]["sections"]
    # Check that French headings are used
    assert any("compétences" in k.lower() or "competences" in k.lower() for k in sections.keys())
    assert any("expérience" in k.lower() or "experience" in k.lower() for k in sections.keys())

    # Check skills format: plain keywords without proficiency suffix (B4)
    skills_sec = next(v for k, v in sections.items() if "compétences" in k.lower() or "competences" in k.lower())
    assert len(skills_sec) >= 1
    lang_cat = next(cat for cat in skills_sec if cat["label"] == "Languages")
    assert "Python" in lang_cat["details"]
    assert "C++" in lang_cat["details"]
    assert "None" not in lang_cat["details"]
    assert "Avancé" not in lang_cat["details"]
    assert "Advanced" not in lang_cat["details"]


def test_build_rendercv_yaml_dict_german(sample_resume_data):
    """Test translating to German locale."""
    settings = {
        "template": "classic",
        "language": "de",
        "theme_color": "#dc2626",
        "document_size": "A4",
    }
    yaml_dict = build_rendercv_yaml_dict(sample_resume_data, settings)
    assert yaml_dict["locale"]["language"] == "german"

    sections = yaml_dict["cv"]["sections"]
    assert any("berufserfahrung" in k.lower() for k in sections.keys())
    assert any("kenntnisse" in k.lower() for k in sections.keys())


def test_skill_proficiency_elimination():
    """Verify that all skills render as plain keywords without any proficiency strings (B4)."""
    data = {
        "profile": {"full_name": "Plain Skills User"},
        "skills": [
            {"id": "1", "name": "React", "proficiency": None},
            {"id": "2", "name": "TypeScript", "proficiency": ""},
            {"id": "3", "name": "Tailwind", "proficiency": "NONE"},
            {"id": "4", "name": "GraphQL", "proficiency": "ADVANCED"},
        ],
    }
    settings = {"language": "en"}
    yaml_dict = build_rendercv_yaml_dict(data, settings)
    sections = yaml_dict["cv"]["sections"]
    skills_sec = next(v for k, v in sections.items() if "skills" in k.lower())
    details = skills_sec[0]["details"]
    assert "React" in details
    assert "TypeScript" in details
    assert "Tailwind" in details
    assert "GraphQL" in details
    assert "None" not in details
    assert "Advanced" not in details
    assert "—" not in details


def test_candidate_name_hierarchy_and_fallbacks():
    """Verify B1 regression fix: candidate name is never missing regardless of profile/structured_data format."""
    # 1. Profile with full_name
    d1 = {"profile": {"full_name": "Alice Dupont"}}
    assert build_rendercv_yaml_dict(d1)["cv"]["name"] == "Alice Dupont"

    # 2. Profile with name
    d2 = {"profile": {"name": "Bob Martin"}}
    assert build_rendercv_yaml_dict(d2)["cv"]["name"] == "Bob Martin"

    # 3. Root structured_data name
    d3 = {"name": "Charlie Chaplin"}
    assert build_rendercv_yaml_dict(d3)["cv"]["name"] == "Charlie Chaplin"

    # 4. Profile first_name / last_name
    d4 = {"profile": {"first_name": "David", "last_name": "Beckham"}}
    assert build_rendercv_yaml_dict(d4)["cv"]["name"] == "David Beckham"

    # 5. Completely empty profile defaults cleanly
    d5 = {"profile": {}}
    assert build_rendercv_yaml_dict(d5)["cv"]["name"] == "Candidate Name"


def test_render_rendercv_preview_and_exact_pagination(sample_resume_data, tmp_path):
    """Integration test: RenderCV compiles real Typst PDF and page images matching exactly."""
    settings = {
        "template": "classic",
        "language": "fr",
        "theme_color": "#1e40af",
        "document_size": "A4",
    }

    # 1. Generate live preview payload
    preview_res = render_rendercv_preview_payload(sample_resume_data, settings)
    assert preview_res["engine"] == "rendercv-typst"
    assert preview_res["page_count"] >= 1
    assert len(preview_res["pages"]) == preview_res["page_count"]
    for p in preview_res["pages"]:
        assert p.startswith("data:image/png;base64,")

    # 2. Generate actual PDF
    dest_pdf = tmp_path / "exported_resume.pdf"
    artifacts = render_rendercv_artifacts(sample_resume_data, settings, dest_pdf_path=dest_pdf)

    assert dest_pdf.exists()
    assert dest_pdf.stat().st_size > 1000

    # 3. Verify that PDF page count matches preview page count EXACTLY (solving the pagination bug)
    reader = PdfReader(str(dest_pdf))
    actual_pdf_pages = len(reader.pages)
    assert actual_pdf_pages == preview_res["page_count"], (
        f"Mismatch: Live preview has {preview_res['page_count']} pages, "
        f"but exported PDF has {actual_pdf_pages} pages!"
    )
    assert len(artifacts["png_paths"]) == actual_pdf_pages


def test_multipage_resume_exact_pagination_matching(tmp_path):
    """Integration test: Long resume spanning 2+ pages has matching page breaks in preview and PDF."""
    long_resume = {
        "profile": {
            "full_name": "Dr. Alexander von Humboldt",
            "headline": "Distinguished Research Scientist & Distributed Systems Architect",
            "email": "alexander.humboldt@university.de",
            "phone": "+49 30 1234567",
            "location": "Berlin, Germany",
            "summary": "Pioneering researcher and systems engineer with over 15 years of experience leading high-performance computing initiatives across European research networks.",
        },
        "skills": [
            {"id": "s1", "name": "Distributed Systems", "category": "Core Architecture", "proficiency": "EXPERT"},
            {"id": "s2", "name": "C++20", "category": "Core Architecture", "proficiency": "EXPERT"},
            {"id": "s3", "name": "Rust", "category": "Core Architecture", "proficiency": "ADVANCED"},
            {"id": "s4", "name": "Kubernetes", "category": "Infrastructure", "proficiency": "EXPERT"},
            {"id": "s5", "name": "MPI / OpenMP", "category": "High Performance Computing", "proficiency": None},
            {"id": "s6", "name": "RDMA InfiniBand", "category": "High Performance Computing", "proficiency": None},
        ],
        "languages": [
            {"id": "l1", "language": "Deutsch", "proficiency": "native"},
            {"id": "l2", "language": "English", "proficiency": "fluent"},
            {"id": "l3", "language": "Français", "proficiency": "intermediate"},
        ],
        "experience": [
            {
                "id": f"e{i}",
                "company": f"Research Lab Europe {i}",
                "title": f"Principal Systems Architect {i}",
                "location": "Berlin / Munich",
                "start_date": f"201{i}-01",
                "end_date": f"201{i+1}-12",
                "is_current": False,
                "description": f"Architected high-throughput parallel compute cluster for astronomical data analysis across tier-1 data centers.",
                "highlights": [
                    f"Optimized memory bus saturation reducing compute cycle bottlenecks by 3{i}%.",
                    f"Implemented lock-free asynchronous queue topologies handling 40M events/sec.",
                    f"Co-authored patent on distributed zero-copy network buffer management.",
                ],
            }
            for i in range(1, 6)
        ],
        "education": [
            {
                "id": f"ed{i}",
                "institution": f"Technical University of Berlin {i}",
                "degree": "Doctor of Science" if i == 1 else "Master of Science",
                "field": "Computer Science & Parallel Architectures",
                "location": "Berlin, Germany",
                "start_date": f"200{i}-10",
                "end_date": f"200{i+3}-07",
                "gpa": "Summa Cum Laude",
                "description": "Dissertation on deterministic latency guarantees in multi-tenant cloud fabrics.",
            }
            for i in range(1, 3)
        ],
        "projects": [
            {
                "id": f"pr{i}",
                "name": f"HPC-Orchestrator-{i}",
                "technologies": "Rust, Tokio, gRPC, eBPF",
                "url": "https://github.com/hpc/orchestrator",
                "start_date": "2021",
                "end_date": "2023",
                "description": "Kernel-bypass networking scheduler for heterogeneous accelerator nodes.",
                "highlights": ["Deployed across 4,000 GPU nodes with zero scheduler downtime."],
            }
            for i in range(1, 4)
        ],
    }

    settings = {
        "template": "classic",
        "language": "de",
        "theme_color": "#059669",
        "document_size": "A4",
    }

    dest_pdf = tmp_path / "multipage_resume.pdf"
    artifacts = render_rendercv_artifacts(long_resume, settings, dest_pdf_path=dest_pdf)
    preview = render_rendercv_preview_payload(long_resume, settings)

    reader = PdfReader(str(dest_pdf))
    num_pages_pdf = len(reader.pages)

    assert num_pages_pdf >= 2, f"Expected multi-page resume (>=2 pages), got {num_pages_pdf}"
    assert preview["page_count"] == num_pages_pdf, (
        f"Pagination mismatch: Preview says {preview['page_count']} pages, "
        f"real PDF has {num_pages_pdf} pages!"
    )
    assert len(preview["pages"]) == num_pages_pdf
    assert len(artifacts["png_paths"]) == num_pages_pdf

