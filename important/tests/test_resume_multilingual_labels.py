import io
from pathlib import Path
from datetime import datetime, timezone
import pytest
from docx import Document
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, User, Resume
from src.app.security import create_access_token
from src.app.schemas_resume import (
    ResumeSkillItem,
    ResumeLanguageItem,
    ResumeSettings,
    resolve_section_title,
)
from src.app.services.resume_localization import (
    normalize_skill_proficiency,
    normalize_language_proficiency,
    get_localized_skill_label,
    get_localized_language_label,
    format_skill_display,
    format_language_display,
    resolve_localized_section_title,
)
from src.app.services.resume_export import render_template_pdf, render_template_docx


# ===========================================================================
# 1. Normalization & Token Tests
# ===========================================================================

def test_normalize_skill_proficiency_neutral_and_legacy():
    # Empty, None, or blank
    assert normalize_skill_proficiency(None) == "NONE"
    assert normalize_skill_proficiency("") == "NONE"
    assert normalize_skill_proficiency("  ") == "NONE"
    assert normalize_skill_proficiency("NONE") == "NONE"
    assert normalize_skill_proficiency("no_label") == "NONE"
    assert normalize_skill_proficiency("No Label") == "NONE"
    assert normalize_skill_proficiency("null") == "NONE"
    assert normalize_skill_proficiency("undefined") == "NONE"

    # Standard English / Canonical
    assert normalize_skill_proficiency("Beginner") == "BEGINNER"
    assert normalize_skill_proficiency("INTERMEDIATE") == "INTERMEDIATE"
    assert normalize_skill_proficiency("advanced") == "ADVANCED"
    assert normalize_skill_proficiency("Expert") == "EXPERT"

    # Multilingual / legacy aliases
    assert normalize_skill_proficiency("Débutant") == "BEGINNER"
    assert normalize_skill_proficiency("Anfänger") == "BEGINNER"
    assert normalize_skill_proficiency("Intermédiaire") == "INTERMEDIATE"
    assert normalize_skill_proficiency("Fortgeschritten") == "ADVANCED"
    assert normalize_skill_proficiency("Avancé") == "ADVANCED"


def test_normalize_language_proficiency_neutral_and_legacy():
    # Blank / None
    assert normalize_language_proficiency(None) == "NONE"
    assert normalize_language_proficiency("") == "NONE"
    assert normalize_language_proficiency("NONE") == "NONE"
    assert normalize_language_proficiency("no label") == "NONE"

    # Standard English
    assert normalize_language_proficiency("Native") == "NATIVE"
    assert normalize_language_proficiency("Native / Bilingual") == "NATIVE"
    assert normalize_language_proficiency("Bilingual") == "BILINGUAL"
    assert normalize_language_proficiency("Fluent") == "FLUENT"
    assert normalize_language_proficiency("Professional") == "PROFESSIONAL"
    assert normalize_language_proficiency("Professional Working") == "PROFESSIONAL"
    assert normalize_language_proficiency("Intermediate") == "INTERMEDIATE"
    assert normalize_language_proficiency("Basic") == "BASIC"

    # French & German
    assert normalize_language_proficiency("Langue maternelle") == "NATIVE"
    assert normalize_language_proficiency("Muttersprache") == "NATIVE"
    assert normalize_language_proficiency("Courant") == "FLUENT"
    assert normalize_language_proficiency("Fließend") == "FLUENT"
    assert normalize_language_proficiency("Verhandlungssicher") == "PROFESSIONAL"


# ===========================================================================
# 2. Skill Multilingual Display & "No label" Tests
# ===========================================================================

def test_skill_labels_english():
    assert get_localized_skill_label("BEGINNER", "en") == "Beginner"
    assert get_localized_skill_label("INTERMEDIATE", "en") == "Intermediate"
    assert get_localized_skill_label("ADVANCED", "en") == "Advanced"
    assert get_localized_skill_label("EXPERT", "en") == "Expert"
    assert get_localized_skill_label("NONE", "en") == ""


def test_skill_labels_french():
    assert get_localized_skill_label("BEGINNER", "fr") == "Débutant"
    assert get_localized_skill_label("INTERMEDIATE", "fr") == "Intermédiaire"
    assert get_localized_skill_label("ADVANCED", "fr") == "Avancé"
    assert get_localized_skill_label("EXPERT", "fr") == "Expert"
    assert get_localized_skill_label("NONE", "fr") == ""


def test_skill_labels_german():
    assert get_localized_skill_label("BEGINNER", "de") == "Anfänger"
    assert get_localized_skill_label("INTERMEDIATE", "de") == "Fortgeschritten"
    assert get_localized_skill_label("ADVANCED", "de") == "Sehr gute Kenntnisse"
    assert get_localized_skill_label("EXPERT", "de") == "Experte"
    assert get_localized_skill_label("NONE", "de") == ""


def test_skill_format_display_with_and_without_proficiency():
    # Skill with proficiency
    assert format_skill_display("Python", "ADVANCED", "en") == "Python — Advanced"
    assert format_skill_display("Python", "ADVANCED", "fr") == "Python — Avancé"
    assert format_skill_display("Python", "ADVANCED", "de") == "Python — Sehr gute Kenntnisse"
    assert format_skill_display("Linux", "INTERMEDIATE", "en") == "Linux — Intermediate"
    assert format_skill_display("Linux", "INTERMEDIATE", "fr") == "Linux — Intermédiaire"
    assert format_skill_display("Linux", "INTERMEDIATE", "de") == "Linux — Fortgeschritten"

    # Skill WITHOUT proficiency ("No label") - transversal / soft skills
    assert format_skill_display("Communication", "NONE", "en") == "Communication"
    assert format_skill_display("Communication", None, "en") == "Communication"
    assert format_skill_display("Teamwork", "", "fr") == "Teamwork"
    assert format_skill_display("Problem Solving", "no_label", "de") == "Problem Solving"

    # Verify NO forbidden labels appear
    for no_label_val in [None, "", "NONE", "no_label", "null", "undefined"]:
        res = format_skill_display("Python", no_label_val, "en")
        assert res == "Python"
        assert "None" not in res
        assert "null" not in res
        assert "undefined" not in res
        assert "No proficiency" not in res
        assert "—" not in res


# ===========================================================================
# 3. Spoken Language Multilingual Display & "No label" Tests
# ===========================================================================

def test_language_labels_english():
    assert get_localized_language_label("NATIVE", "en") == "Native"
    assert get_localized_language_label("BILINGUAL", "en") == "Bilingual"
    assert get_localized_language_label("FLUENT", "en") == "Fluent"
    assert get_localized_language_label("PROFESSIONAL", "en") == "Professional Working"
    assert get_localized_language_label("INTERMEDIATE", "en") == "Intermediate"
    assert get_localized_language_label("BASIC", "en") == "Basic"
    assert get_localized_language_label("NONE", "en") == ""


def test_language_labels_french():
    assert get_localized_language_label("NATIVE", "fr") == "Langue maternelle"
    assert get_localized_language_label("BILINGUAL", "fr") == "Bilingue"
    assert get_localized_language_label("FLUENT", "fr") == "Courant"
    assert get_localized_language_label("PROFESSIONAL", "fr") == "Professionnel"
    assert get_localized_language_label("INTERMEDIATE", "fr") == "Intermédiaire"
    assert get_localized_language_label("BASIC", "fr") == "Notions / Débutant"
    assert get_localized_language_label("NONE", "fr") == ""


def test_language_labels_german():
    assert get_localized_language_label("NATIVE", "de") == "Muttersprache"
    assert get_localized_language_label("BILINGUAL", "de") == "Zweisprachig"
    assert get_localized_language_label("FLUENT", "de") == "Fließend"
    assert get_localized_language_label("PROFESSIONAL", "de") == "Verhandlungssicher"
    assert get_localized_language_label("INTERMEDIATE", "de") == "Gute Kenntnisse"
    assert get_localized_language_label("BASIC", "de") == "Grundkenntnisse"
    assert get_localized_language_label("NONE", "de") == ""


def test_language_format_display_with_and_without_proficiency():
    # Language with proficiency
    assert format_language_display("French", "FLUENT", "en") == "French (Fluent)"
    assert format_language_display("Français", "FLUENT", "fr") == "Français (Courant)"
    assert format_language_display("Französisch", "FLUENT", "de") == "Französisch (Fließend)"
    assert format_language_display("English", "NATIVE", "fr") == "English (Langue maternelle)"
    assert format_language_display("German", "PROFESSIONAL", "de") == "German (Verhandlungssicher)"

    # Language without proficiency
    assert format_language_display("Spanish", "NONE", "en") == "Spanish"
    assert format_language_display("Spanish", None, "en") == "Spanish"
    assert format_language_display("Espagnol", "", "fr") == "Espagnol"

    # Verify forbidden substrings
    for no_label_val in [None, "", "NONE", "no_label", "null"]:
        res = format_language_display("Arabic", no_label_val, "en")
        assert res == "Arabic"
        assert "None" not in res
        assert "null" not in res
        assert "undefined" not in res
        assert "No proficiency" not in res
        assert "(" not in res


# ===========================================================================
# 4. Section Title Resolution with Language Switching
# ===========================================================================

def test_resolve_section_title_multilingual_defaults():
    # English
    assert resolve_section_title("skills", lang="en") == "Technical & Core Skills"
    assert resolve_section_title("languages", lang="en") == "Languages"
    assert resolve_section_title("experience", lang="en") == "Professional Experience"

    # French
    assert resolve_section_title("skills", lang="fr") == "Compétences"
    assert resolve_section_title("languages", lang="fr") == "Langues"
    assert resolve_section_title("experience", lang="fr") == "Expérience Professionnelle"

    # German
    assert resolve_section_title("skills", lang="de") == "Kenntnisse & Fähigkeiten"
    assert resolve_section_title("languages", lang="de") == "Sprachen"
    assert resolve_section_title("experience", lang="de") == "Berufserfahrung"

    # Custom title override always takes precedence regardless of language
    assert resolve_section_title("skills", "Mes Super Compétences", lang="fr") == "Mes Super Compétences"
    assert resolve_section_title("skills", "Meine Kenntnisse", lang="de") == "Meine Kenntnisse"


# ===========================================================================
# 5. Schema & Legacy Compatibility Tests
# ===========================================================================

def test_schemas_optional_proficiency():
    # Skill without proficiency defaults to None
    sk_none = ResumeSkillItem(id="s1", name="Docker")
    assert sk_none.proficiency is None

    # Skill with proficiency
    sk_prof = ResumeSkillItem(id="s2", name="Python", proficiency="ADVANCED")
    assert sk_prof.proficiency == "ADVANCED"

    # Language without proficiency defaults to None
    lang_none = ResumeLanguageItem(id="l1", language="English")
    assert lang_none.proficiency is None

    # Settings language default is "en"
    settings = ResumeSettings()
    assert settings.language == "en"

    # Settings with French or German language
    settings_fr = ResumeSettings(language="fr")
    assert settings_fr.language == "fr"


# ===========================================================================
# 6. PDF and DOCX Multilingual Export Integration Tests
# ===========================================================================

@pytest.fixture
def resume_multilingual_env(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        user = User(
            id=1,
            email="candidate@compust.ai",
            password_hash="pw",
            is_active=True,
            first_name="Sophie",
            last_name="Martin",
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.flush()

        # Resume with mixed skills (some with proficiency, some "No label")
        # and mixed spoken languages
        resume_french = Resume(
            id=101,
            user_id=1,
            title="French Resume",
            is_active=True,
            is_default=True,
            structured_data={
                "profile": {
                    "full_name": "Sophie Martin",
                    "headline": "Ingénieure Logiciel",
                    "email": "candidate@compust.ai",
                    "summary": "Développeuse backend expérimentée.",
                },
                "skills": [
                    {"id": "s1", "name": "Python", "category": "Backend", "proficiency": "ADVANCED"},
                    {"id": "s2", "name": "PostgreSQL", "category": "Backend", "proficiency": "INTERMEDIATE"},
                    {"id": "s3", "name": "Team Leadership", "category": "Soft Skills", "proficiency": "NONE"},
                    {"id": "s4", "name": "Communication", "category": "Soft Skills", "proficiency": None},
                ],
                "languages": [
                    {"id": "l1", "language": "Français", "proficiency": "NATIVE"},
                    {"id": "l2", "language": "Anglais", "proficiency": "FLUENT"},
                    {"id": "l3", "language": "Espagnol", "proficiency": "NONE"},
                ],
            },
            settings={
                "template": "modern",
                "language": "fr",
                "theme_color": "#2563eb",
                "font_family": "Inter",
                "font_size": "10.5",
                "document_size": "A4",
            },
            created_at=now,
            updated_at=now,
        )

        # German Resume
        resume_german = Resume(
            id=102,
            user_id=1,
            title="German Resume",
            is_active=True,
            is_default=False,
            structured_data={
                "profile": {
                    "full_name": "Sophie Martin",
                    "summary": "Softwareentwicklerin mit Fokus auf Cloud.",
                },
                "skills": [
                    {"id": "s1", "name": "Python", "category": "Backend", "proficiency": "EXPERT"},
                    {"id": "s2", "name": "Teamwork", "category": "Kompetenzen", "proficiency": "NONE"},
                ],
                "languages": [
                    {"id": "l1", "language": "Deutsch", "proficiency": "PROFESSIONAL"},
                    {"id": "l2", "language": "Latein", "proficiency": None},
                ],
            },
            settings={
                "template": "classic",
                "language": "de",
                "theme_color": "#059669",
                "font_family": "Inter",
                "font_size": "10.5",
                "document_size": "A4",
            },
            created_at=now,
            updated_at=now,
        )

        # Legacy Resume from existing DB (English strings, no language field)
        resume_legacy = Resume(
            id=103,
            user_id=1,
            title="Legacy Resume",
            is_active=True,
            is_default=False,
            structured_data={
                "profile": {
                    "full_name": "Sophie Martin",
                    "summary": "Software engineer.",
                },
                "skills": [
                    {"id": "s1", "name": "Python", "proficiency": "Intermediate"},
                    {"id": "s2", "name": "Problem Solving"},
                ],
                "languages": [
                    {"id": "l1", "language": "English", "proficiency": "Fluent"},
                    {"id": "l2", "language": "French"},
                ],
            },
            settings={
                "template": "minimal",
                # No language key
            },
            created_at=now,
            updated_at=now,
        )

        session.add_all([resume_french, resume_german, resume_legacy])
        session.commit()

    return {"session_factory": session_factory, "tmp_path": tmp_path}


def test_pdf_export_french_multilingual(resume_multilingual_env):
    session_factory = resume_multilingual_env["session_factory"]
    tmp_path = resume_multilingual_env["tmp_path"]

    with session_factory() as session:
        r = session.query(Resume).filter_by(id=101).first()
        pdf_file = tmp_path / "resume_fr.pdf"
        render_template_pdf(r.structured_data, r.settings, pdf_file)

        assert pdf_file.exists()
        assert pdf_file.stat().st_size > 0

        reader = PdfReader(str(pdf_file))
        pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)

        # French section title
        assert "COMPÉTENCES" in pdf_text or "LANGUES" in pdf_text
        # French skill labels
        assert "Python — Avancé" in pdf_text
        assert "PostgreSQL — Intermédiaire" in pdf_text
        # No label transversal skills: ONLY name, no dashes or "None"
        assert "Team Leadership" in pdf_text
        assert "Communication" in pdf_text
        assert "Team Leadership —" not in pdf_text
        assert "Communication —" not in pdf_text
        # French language labels
        assert "Français (Langue maternelle)" in pdf_text
        assert "Anglais (Courant)" in pdf_text
        assert "Espagnol" in pdf_text
        assert "Espagnol (" not in pdf_text

        # Verify NO forbidden labels anywhere in PDF
        assert "None" not in pdf_text
        assert "null" not in pdf_text
        assert "undefined" not in pdf_text
        assert "No proficiency" not in pdf_text


def test_docx_export_german_multilingual(resume_multilingual_env):
    session_factory = resume_multilingual_env["session_factory"]
    tmp_path = resume_multilingual_env["tmp_path"]

    with session_factory() as session:
        r = session.query(Resume).filter_by(id=102).first()
        docx_file = tmp_path / "resume_de.docx"
        render_template_docx(r.structured_data, r.settings, docx_file)

        assert docx_file.exists()
        assert docx_file.stat().st_size > 0

        doc = Document(str(docx_file))
        doc_text = "\n".join(p.text for p in doc.paragraphs)

        # German section titles
        assert "KENNTNISSE & FÄHIGKEITEN" in doc_text or "SPRACHEN" in doc_text
        # German skill labels
        assert "Python — Experte" in doc_text
        assert "Teamwork" in doc_text
        assert "Teamwork —" not in doc_text
        # German language labels
        assert "Deutsch (Verhandlungssicher)" in doc_text
        assert "Latein" in doc_text
        assert "Latein (" not in doc_text

        # Verify NO forbidden strings
        assert "None" not in doc_text
        assert "null" not in doc_text
        assert "undefined" not in doc_text


def test_legacy_resume_export_backward_compatibility(resume_multilingual_env):
    session_factory = resume_multilingual_env["session_factory"]
    tmp_path = resume_multilingual_env["tmp_path"]

    with session_factory() as session:
        r = session.query(Resume).filter_by(id=103).first()
        pdf_file = tmp_path / "resume_legacy.pdf"
        render_template_pdf(r.structured_data, r.settings, pdf_file)

        assert pdf_file.exists()
        reader = PdfReader(str(pdf_file))
        pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)

        # Legacy skill with "Intermediate" formatted cleanly
        assert "Python — Intermediate" in pdf_text
        # Legacy skill without proficiency formatted cleanly
        assert "Problem Solving" in pdf_text
        assert "Problem Solving —" not in pdf_text
        # Spoken language
        assert "English (Fluent)" in pdf_text
        assert "French" in pdf_text
        assert "French (" not in pdf_text

        assert "None" not in pdf_text
        assert "null" not in pdf_text


# ===========================================================================
# 7. FastAPI Endpoint Integration (Save & Reload Structured Values)
# ===========================================================================

def test_api_resume_multilingual_crud(resume_multilingual_env):
    session_factory = resume_multilingual_env["session_factory"]

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    token = create_access_token(data={"sub": "1"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a structured resume with optional skills & languages
    payload = {
        "title": "Cloud Architect Resume",
        "is_default": False,
        "structured_data": {
            "profile": {"full_name": "Sophie Martin", "summary": "Cloud Engineer."},
            "skills": [
                {"id": "sk1", "name": "Kubernetes", "proficiency": "ADVANCED"},
                {"id": "sk2", "name": "Problem Solving", "proficiency": "NONE"},
            ],
            "languages": [
                {"id": "l1", "language": "French", "proficiency": "NATIVE"},
                {"id": "l2", "language": "Japanese", "proficiency": None},
            ],
        },
        "settings": {
            "template": "modern",
            "language": "fr",
        },
    }

    resp = client.post("/api/v1/resumes", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    created = resp.json()
    resume_id = created["id"]
    assert created["settings"]["language"] == "fr"

    # 2. Get resume and verify stored structured values
    resp_get = client.get(f"/api/v1/resumes/{resume_id}", headers=headers)
    assert resp_get.status_code == 200
    res_data = resp_get.json()
    skills = res_data["structured_data"]["skills"]
    assert len(skills) == 2
    assert skills[0]["name"] == "Kubernetes"
    assert skills[0]["proficiency"] == "ADVANCED"
    assert skills[1]["name"] == "Problem Solving"
    assert skills[1]["proficiency"] in ("NONE", None, "")

    # 3. Switch resume language to German in settings and update
    update_payload = {
        "settings": {
            "template": "modern",
            "language": "de",
        },
    }
    resp_up = client.put(f"/api/v1/resumes/{resume_id}", json=update_payload, headers=headers)
    assert resp_up.status_code == 200
    assert resp_up.json()["settings"]["language"] == "de"

    # 4. Download PDF export in German
    resp_pdf = client.get(f"/api/v1/resumes/{resume_id}/export/pdf", headers=headers)
    assert resp_pdf.status_code == 200
    assert resp_pdf.headers["content-type"] == "application/pdf"
    pdf_reader = PdfReader(io.BytesIO(resp_pdf.content))
    pdf_text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
    assert "Kubernetes — Sehr gute Kenntnisse" in pdf_text
    assert "Problem Solving" in pdf_text
    assert "Problem Solving —" not in pdf_text
    assert "None" not in pdf_text
    # 5. Test updating with "No label" (proficiency=None and proficiency="NONE"), integer IDs, and nullable fields
    no_label_update = {
        "title": "Cloud Architect Resume (Updated)",
        "structured_data": {
            "profile": {"full_name": "Sophie Martin", "summary": "Cloud Engineer.", "phone": None, "location": None},
            "skills": [
                {"id": 101, "name": "Python", "proficiency": None},
                {"id": "sk2", "name": "Docker", "proficiency": "NONE"},
                {"id": "sk3", "name": "Cybersecurity", "proficiency": "NO_LABEL"},
            ],
            "experience": [
                {
                    "id": 1,
                    "company": "Tech Corp",
                    "title": "Engineer",
                    "location": None,
                    "highlights": None,
                    "is_current": None,
                }
            ],
            "education": [
                {
                    "id": 2,
                    "institution": "University",
                    "degree": None,
                    "field": None,
                }
            ],
            "languages": [
                {"id": 3, "language": "French", "proficiency": None},
            ],
        },
        "settings": {
            "template": "modern",
            "language": "fr",
            "document_size": "A4",
            "font_size": "10.0",
        },
    }
    resp_no_label = client.put(f"/api/v1/resumes/{resume_id}", json=no_label_update, headers=headers)
    assert resp_no_label.status_code == 200, resp_no_label.text
    saved = resp_no_label.json()
    saved_skills = saved["structured_data"]["skills"]
    assert len(saved_skills) == 3
    # All 3 skills with No label should have proficiency normalized to None
    for s in saved_skills:
        assert s["proficiency"] in (None, "")
        assert isinstance(s["id"], str)

    app.dependency_overrides.clear()

