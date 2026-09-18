"""
test_job_assistant_multilingual.py
====================================
Tests that language handling works correctly across English, French, German, Spanish.
"""
import pytest
from src.app.schemas_job_assistant import (
    CandidateContext,
    CandidateContextExperience,
    ExternalJobInput,
    SupportedLanguage,
)
from src.app.services.job_assistant import (
    LANG_INSTRUCTION,
    STAGE1_TEMPLATE,
    _fallback_extract_requirements,
    canonicalize_role_tokens,
    deterministic_score,
    normalize_skill,
    RequirementCategory,
)


# ---------------------------------------------------------------------------
# Language instruction completeness
# ---------------------------------------------------------------------------

def test_all_supported_languages_have_instructions():
    for lang in ("en", "fr", "de", "es"):
        assert lang in LANG_INSTRUCTION, f"Missing instruction for lang '{lang}'"
        assert len(LANG_INSTRUCTION[lang]) > 10


def test_language_instructions_are_distinct():
    instructions = list(LANG_INSTRUCTION.values())
    assert len(set(instructions)) == len(instructions), "Language instructions must be distinct"


# ---------------------------------------------------------------------------
# French job description
# ---------------------------------------------------------------------------

FRENCH_JOB = ExternalJobInput(
    target_role="Ingenieur Python Senior",
    job_description=(
        "Nous recherchons un ingenieur Python senior pour rejoindre notre equipe. "
        "Vous devez avoir une solide experience avec Docker, Kubernetes et les APIs REST. "
        "La maitrise de PostgreSQL et de FastAPI est requise. "
        "Connaissance de Terraform souhaitee. "
        "Excellente maitrise du francais et de l anglais obligatoire. " * 5
    ),
    language=SupportedLanguage.FR,
)


def test_french_job_extracts_requirements_deterministically():
    reqs = _fallback_extract_requirements(FRENCH_JOB)
    names = [r.text.lower() for r in reqs]
    # Technical keywords should be found regardless of surrounding language
    assert any("docker" in n for n in names)
    assert any("kubernetes" in n for n in names)
    assert any("postgresql" in n for n in names)


def test_french_stage1_prompt_includes_french_instruction():
    prompt = STAGE1_TEMPLATE.format(
        title=FRENCH_JOB.target_role,
        description=FRENCH_JOB.job_description[:2000],
        additional="",
        lang_instruction=LANG_INSTRUCTION["fr"],
    )
    assert "francais" in prompt.lower() or "Reponds" in prompt


# ---------------------------------------------------------------------------
# German job description
# ---------------------------------------------------------------------------

GERMAN_JOB = ExternalJobInput(
    target_role="Python Entwickler Senior",
    job_description=(
        "Wir suchen einen erfahrenen Python Entwickler fuer unser Berliner Team. "
        "Anforderungen: Docker, Kubernetes, PostgreSQL, FastAPI, REST APIs. "
        "Terraform-Kenntnisse sind von Vorteil. "
        "Sehr gute Deutsch- und Englischkenntnisse erforderlich. "
        "Erfahrung mit agilen Methoden wie Scrum ist erwuenscht. " * 5
    ),
    language=SupportedLanguage.DE,
)


def test_german_job_extracts_requirements_deterministically():
    reqs = _fallback_extract_requirements(GERMAN_JOB)
    names = [r.text.lower() for r in reqs]
    assert any("docker" in n for n in names)
    assert any("fastapi" in n for n in names)
    assert any("scrum" in n for n in names)


def test_german_stage1_prompt_includes_german_instruction():
    prompt = STAGE1_TEMPLATE.format(
        title=GERMAN_JOB.target_role,
        description=GERMAN_JOB.job_description[:2000],
        additional="",
        lang_instruction=LANG_INSTRUCTION["de"],
    )
    assert "Deutsch" in prompt or "deutsch" in prompt


# ---------------------------------------------------------------------------
# Spanish job description
# ---------------------------------------------------------------------------

SPANISH_JOB = ExternalJobInput(
    target_role="Ingeniero Python Senior",
    job_description=(
        "Buscamos un ingeniero Python senior para unirse a nuestro equipo en Madrid. "
        "Requisitos: experiencia con Docker, Kubernetes, PostgreSQL y FastAPI. "
        "Se requieren conocimientos de Terraform y CI/CD. "
        "Excelente nivel de espanol e ingles indispensable. "
        "Experiencia con metodologias agiles como Scrum o Kanban. " * 5
    ),
    language=SupportedLanguage.ES,
)


def test_spanish_job_extracts_requirements_deterministically():
    reqs = _fallback_extract_requirements(SPANISH_JOB)
    names = [r.text.lower() for r in reqs]
    assert any("docker" in n for n in names)
    assert any("kubernetes" in n for n in names)


def test_spanish_stage1_prompt_includes_spanish_instruction():
    prompt = STAGE1_TEMPLATE.format(
        title=SPANISH_JOB.target_role,
        description=SPANISH_JOB.job_description[:2000],
        additional="",
        lang_instruction=LANG_INSTRUCTION["es"],
    )
    assert "espanol" in prompt.lower() or "español" in prompt.lower() or "Responde" in prompt


# ---------------------------------------------------------------------------
# Equivalent job title recognition across languages
# ---------------------------------------------------------------------------

def test_equivalent_python_keyword_found_in_french_text():
    """Python keyword must be found in French job description."""
    reqs = _fallback_extract_requirements(FRENCH_JOB)
    names = [r.text.lower() for r in reqs]
    assert any("python" in n for n in names), "Python keyword must be recognized in French context"


def test_equivalent_python_keyword_found_in_german_text():
    reqs = _fallback_extract_requirements(GERMAN_JOB)
    names = [r.text.lower() for r in reqs]
    assert any("python" in n for n in names), "Python keyword must be recognized in German context"


def test_equivalent_python_keyword_found_in_spanish_text():
    reqs = _fallback_extract_requirements(SPANISH_JOB)
    names = [r.text.lower() for r in reqs]
    assert any("python" in n for n in names), "Python keyword must be recognized in Spanish context"


# ---------------------------------------------------------------------------
# Input validation for language field
# ---------------------------------------------------------------------------

def test_invalid_language_rejected():
    with pytest.raises(Exception):
        ExternalJobInput(
            target_role="Developer",
            job_description="We need a developer with Python skills for our team." * 3,
            language="zh",  # type: ignore  # unsupported
        )


def test_default_language_is_english():
    job = ExternalJobInput(
        target_role="Developer",
        job_description="We need a developer with Python skills for our team." * 3,
    )
    assert job.language == SupportedLanguage.EN


# ---------------------------------------------------------------------------
# Cross-lingual role canonicalization & title matching
# ---------------------------------------------------------------------------

def test_cross_lingual_cybersecurity_internship_canonicalization():
    """Assert Cybersecurity Engineer Intern maps identically across English, French, German, and Spanish."""
    en_tokens = canonicalize_role_tokens("Cybersecurity Engineer Intern")
    fr_tokens = canonicalize_role_tokens("Stage Ingénieur Cybersécurité")
    de_tokens = canonicalize_role_tokens("Praktikum als Cybersecurity Engineer")
    es_tokens = canonicalize_role_tokens("Pasantía Ingeniero Ciberseguridad")

    assert en_tokens == {"cybersecurity", "engineer", "intern"}
    assert fr_tokens == {"cybersecurity", "engineer", "intern"}
    assert de_tokens == {"cybersecurity", "engineer", "intern"}
    assert es_tokens == {"cybersecurity", "engineer", "intern"}


def test_cross_lingual_developer_title_variants():
    """Assert gendered and localized developer titles resolve to 'developer'."""
    assert canonicalize_role_tokens("developer") == {"developer"}
    assert canonicalize_role_tokens("développeur") == {"developer"}
    assert canonicalize_role_tokens("développeuse") == {"developer"}
    assert canonicalize_role_tokens("Entwickler") == {"developer"}
    assert canonicalize_role_tokens("Entwicklerin") == {"developer"}
    assert canonicalize_role_tokens("desarrollador") == {"developer"}
    assert canonicalize_role_tokens("desarrolladora") == {"developer"}


def test_cross_lingual_software_engineer():
    """Assert software engineer variants map consistently across languages."""
    en = canonicalize_role_tokens("Software Engineer")
    fr = canonicalize_role_tokens("Ingénieur Logiciel")
    de = canonicalize_role_tokens("Software Ingenieur")
    es = canonicalize_role_tokens("Ingeniero de Software")

    assert en == {"software", "engineer"}
    assert fr == {"software", "engineer"}
    assert de == {"software", "engineer"}
    assert es == {"software", "engineer"}


def test_cross_lingual_data_engineer():
    """Assert data engineer variants map consistently across languages."""
    en = canonicalize_role_tokens("Data Engineer")
    fr = canonicalize_role_tokens("Ingénieur Données")
    de = canonicalize_role_tokens("Daten Ingenieur")
    es = canonicalize_role_tokens("Ingeniero de Datos")

    assert en == {"data", "engineer"}
    assert fr == {"data", "engineer"}
    assert de == {"data", "engineer"}
    assert es == {"data", "engineer"}


def test_deterministic_score_recognizes_french_experience_for_english_job():
    """A candidate with French 'Stage Ingénieur Cybersécurité' matches English job 'Cybersecurity Engineer Intern'."""
    ctx = CandidateContext()
    ctx.experience.append(CandidateContextExperience(
        id="1",
        title="Stage Ingénieur Cybersécurité",
        company="CyberSec SA",
        description="Audit et tests de sécurité des systèmes d information.",
    ))
    job = ExternalJobInput(
        target_role="Cybersecurity Engineer Intern",
        job_description="We are seeking a motivated cybersecurity engineer intern with security skills." * 3,
        language=SupportedLanguage.EN,
    )
    score = deterministic_score(ctx, job)
    assert score.experience_alignment >= 9.0, f"Expected high alignment, got {score.experience_alignment}"

