"""
test_job_assistant_service.py
=============================
Unit tests for the job assistant service layer.
Ollama is mocked in all tests - no network calls.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.models import Base, Resume, User, UserSkill, UserLanguage
from src.app.schemas_job_assistant import (
    CandidateContext,
    ExternalJobInput,
    MatchAnalysis,
    MatchStatus,
    RecommendationType,
    SupportedLanguage,
)
from src.app.services.job_assistant import (
    _extract_corpus_tokens,
    _fallback_extract_requirements,
    _fallback_recommendations,
    apply_recommendations_to_resume_data,
    build_candidate_context,
    deterministic_match,
    deterministic_score,
    normalize_skill,
)


@pytest.fixture
def mem_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        yield session


@pytest.fixture
def base_user(mem_db):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user = User(
        id=1, email="test@compust.ai", password_hash="pw",
        is_active=True, first_name="Yasmine", last_name="Zahra",
        created_at=now, updated_at=now,
    )
    mem_db.add(user)
    mem_db.commit()
    return user


@pytest.fixture
def resume_with_data(mem_db, base_user):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    r = Resume(
        id=10, user_id=1,
        title="Software Engineer Resume",
        is_active=True, is_default=True,
        structured_data={
            "profile": {
                "full_name": "Yasmine Zahra",
                "headline": "Full-Stack Software Engineer",
                "email": "yasmine@compust.ai",
                "summary": "Experienced engineer specializing in Python and React.",
            },
            "skills": [
                {"id": "sk1", "name": "Python", "category": "Backend", "proficiency": "Expert"},
                {"id": "sk2", "name": "React", "category": "Frontend", "proficiency": "Advanced"},
                {"id": "sk3", "name": "Docker", "category": "DevOps", "proficiency": "Intermediate"},
            ],
            "experience": [
                {
                    "id": "exp1",
                    "company": "TechCorp",
                    "title": "Software Engineer",
                    "description": "Built Python microservices and React dashboards. Used Docker for deployment.",
                    "highlights": ["Reduced API latency by 30%"],
                    "start_date": "2022-01", "end_date": "Present",
                }
            ],
            "education": [
                {
                    "id": "edu1", "institution": "UM6P", "degree": "MSc",
                    "field": "Computer Science", "start_date": "2020", "end_date": "2022",
                }
            ],
            "projects": [
                {
                    "id": "proj1", "name": "AuthAPI",
                    "description": "JWT authentication service using FastAPI and PostgreSQL",
                    "technologies": "Python, FastAPI, PostgreSQL",
                }
            ],
            "languages": [
                {"id": "l1", "language": "English", "proficiency": "Fluent"},
                {"id": "l2", "language": "French", "proficiency": "Native"},
            ],
            "certifications": [],
            "custom_sections": [],
        },
        settings={"template": "modern", "theme_color": "#2563eb"},
        created_at=now, updated_at=now,
    )
    mem_db.add(r)
    mem_db.commit()
    return r


@pytest.fixture
def job_input_python():
    return ExternalJobInput(
        target_role="Senior Python Engineer",
        job_description=(
            "We are looking for a Senior Python Engineer with experience in Docker, "
            "Kubernetes, and FastAPI. The candidate must have strong SQL skills and "
            "experience with PostgreSQL. Agile experience is a plus. "
            "Terraform knowledge is required for infrastructure management. " * 5
        ),
        language=SupportedLanguage.EN,
    )


# ---------------------------------------------------------------------------
# normalize_skill
# ---------------------------------------------------------------------------

def test_normalize_skill_basic():
    assert normalize_skill("  Python  ") == "python"
    assert normalize_skill("Machine-Learning") == "machine learning"
    assert normalize_skill("Node_JS") == "node js"


# ---------------------------------------------------------------------------
# build_candidate_context
# ---------------------------------------------------------------------------

def test_build_candidate_context_from_resume_only(mem_db, base_user, resume_with_data):
    ctx = build_candidate_context(mem_db, base_user.id, resume_with_data)
    assert ctx.profile.full_name == "Yasmine Zahra"
    assert len(ctx.skills) >= 3
    skill_names = [s.name for s in ctx.skills]
    assert "Python" in skill_names
    assert "React" in skill_names
    assert "Docker" in skill_names
    assert len(ctx.experience) == 1
    assert ctx.experience[0].company == "TechCorp"
    assert len(ctx.education) == 1
    assert len(ctx.projects) == 1
    assert len(ctx.languages) == 2


def test_build_candidate_context_adds_profile_skills(mem_db, base_user, resume_with_data):
    """Profile skills not in resume should be added as source='profile'."""
    mem_db.add(UserSkill(user_id=1, skill="Ansible", proficiency="Intermediate"))
    mem_db.commit()
    ctx = build_candidate_context(mem_db, base_user.id, resume_with_data)
    profile_skills = [s for s in ctx.skills if s.source == "profile"]
    assert any(s.name == "Ansible" for s in profile_skills), "Ansible from profile should be added"


def test_build_candidate_context_detects_proficiency_conflict(mem_db, base_user, resume_with_data):
    """Conflicting proficiency between profile and resume should be flagged."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Resume says Python=Expert, profile says Python=Beginner
    mem_db.add(UserSkill(user_id=1, skill="Python", proficiency="Beginner"))
    mem_db.commit()
    ctx = build_candidate_context(mem_db, base_user.id, resume_with_data)
    assert len(ctx.conflicts) >= 1
    assert "Python" in ctx.conflicts[0]


def test_build_candidate_context_adds_profile_languages(mem_db, base_user, resume_with_data):
    """Profile languages not in resume should be added."""
    mem_db.add(UserLanguage(user_id=1, language="Arabic", proficiency="Native"))
    mem_db.commit()
    ctx = build_candidate_context(mem_db, base_user.id, resume_with_data)
    lang_names = [l.language for l in ctx.languages]
    assert "Arabic" in lang_names


# ---------------------------------------------------------------------------
# deterministic_score
# ---------------------------------------------------------------------------

def test_deterministic_score_has_values(resume_with_data, mem_db, base_user, job_input_python):
    ctx = build_candidate_context(mem_db, base_user.id, resume_with_data)
    score = deterministic_score(ctx, job_input_python)
    assert 0.0 <= score.overall <= 10.0
    assert 0.0 <= score.technical_skills <= 10.0
    assert score.experience_alignment > 0.0  # candidate has experience with python/software


def test_deterministic_score_no_experience_gives_zero_exp_score(mem_db, base_user):
    """A resume with no experience entries should give experience_alignment=0."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    resume = Resume(
        id=99, user_id=1, title="Empty", is_active=True, is_default=False,
        structured_data={"profile": {}, "skills": [], "experience": [], "education": [], "projects": [], "languages": [], "certifications": [], "custom_sections": []},
        settings={}, created_at=now, updated_at=now,
    )
    mem_db.add(resume)
    mem_db.commit()
    ctx = build_candidate_context(mem_db, base_user.id, resume)
    job = ExternalJobInput(target_role="Engineer", job_description="Python Docker Kubernetes experience needed for this role at our company." * 4)
    score = deterministic_score(ctx, job)
    assert score.experience_alignment == 0.0


# ---------------------------------------------------------------------------
# deterministic_match
# ---------------------------------------------------------------------------

def test_deterministic_match_finds_known_skills(resume_with_data, mem_db, base_user, job_input_python):
    ctx = build_candidate_context(mem_db, base_user.id, resume_with_data)
    analysis = deterministic_match(ctx, job_input_python)
    strong_reqs = [m.requirement for m in analysis.strong_matches]
    # Python and Docker are in candidate data and job description
    assert any("python" in r.lower() for r in strong_reqs)
    assert any("docker" in r.lower() for r in strong_reqs)


def test_deterministic_match_flags_missing_skills(resume_with_data, mem_db, base_user, job_input_python):
    ctx = build_candidate_context(mem_db, base_user.id, resume_with_data)
    analysis = deterministic_match(ctx, job_input_python)
    missing_reqs = [m.requirement for m in analysis.missing_or_unconfirmed]
    # Kubernetes and Terraform are not in candidate data
    assert any("kubernetes" in r.lower() for r in missing_reqs)
    assert any("terraform" in r.lower() for r in missing_reqs)


# ---------------------------------------------------------------------------
# Fallback extraction
# ---------------------------------------------------------------------------

def test_fallback_extract_requirements_finds_keywords(job_input_python):
    reqs = _fallback_extract_requirements(job_input_python)
    names = [r.text.lower() for r in reqs]
    assert any("python" in n for n in names)
    assert any("docker" in n for n in names)


# ---------------------------------------------------------------------------
# Fallback recommendations
# ---------------------------------------------------------------------------

def test_fallback_recommendations_structure(resume_with_data, mem_db, base_user, job_input_python):
    ctx = build_candidate_context(mem_db, base_user.id, resume_with_data)
    analysis = deterministic_match(ctx, job_input_python)
    recs = _fallback_recommendations(analysis, ctx, job_input_python)
    for rec in recs:
        assert rec.id
        assert rec.rec_type is not None
        # MISSING recs must not have suggested_text
        if rec.rec_type == RecommendationType.MISSING:
            assert rec.suggested_text == ""


def test_fallback_recommendations_no_hallucination(resume_with_data, mem_db, base_user, job_input_python):
    """MISSING recommendations must not invent or add skills to the resume."""
    ctx = build_candidate_context(mem_db, base_user.id, resume_with_data)
    analysis = deterministic_match(ctx, job_input_python)
    recs = _fallback_recommendations(analysis, ctx, job_input_python)
    missing_recs = [r for r in recs if r.rec_type == RecommendationType.MISSING]
    for rec in missing_recs:
        assert "Only add if you genuinely" in rec.reason, f"MISSING rec must warn about hallucination: {rec.reason}"
        assert not rec.suggested_text, "MISSING recs must not have suggested_text"


# ---------------------------------------------------------------------------
# apply_recommendations_to_resume_data - non-destructive
# ---------------------------------------------------------------------------

def test_apply_recs_summary_rewrite(resume_with_data):
    from src.app.schemas_job_assistant import ResumeRecommendation, RecommendationType
    base = resume_with_data.structured_data.copy()
    original_summary = base["profile"]["summary"]
    new_summary = "Experienced Python engineer with expertise in cloud infrastructure and microservices."
    recs = [ResumeRecommendation(
        id="r1", rec_type=RecommendationType.REWRITE,
        section="summary", suggested_text=new_summary,
        reason="Job requires cloud focus", grounded=True,
    )]
    result = apply_recommendations_to_resume_data(base, recs)
    # New copy has new summary
    assert result["profile"]["summary"] == new_summary
    # Original is unchanged
    assert base["profile"]["summary"] == original_summary


def test_apply_recs_missing_are_never_applied(resume_with_data):
    """MISSING recommendations must NEVER modify the resume data."""
    from src.app.schemas_job_assistant import ResumeRecommendation, RecommendationType
    base = resume_with_data.structured_data.copy()
    recs = [ResumeRecommendation(
        id="r1", rec_type=RecommendationType.MISSING,
        section="skills", item_label="Kubernetes",
        reason="Not in candidate data", grounded=True,
    )]
    result = apply_recommendations_to_resume_data(base, recs)
    skill_names = [s.get("name", "") for s in result.get("skills", [])]
    assert "Kubernetes" not in skill_names, "MISSING recs must not add skills"


def test_apply_recs_skill_emphasize(resume_with_data):
    """EMPHASIZE on skills should move skill to front."""
    from src.app.schemas_job_assistant import ResumeRecommendation, RecommendationType
    base = resume_with_data.structured_data.copy()
    # Docker is 3rd in list - emphasize it
    recs = [ResumeRecommendation(
        id="r1", rec_type=RecommendationType.EMPHASIZE,
        section="skills", item_label="Docker",
        reason="Job requires Docker expertise", grounded=True,
    )]
    result = apply_recommendations_to_resume_data(base, recs)
    assert result["skills"][0]["name"] == "Docker", "Emphasized skill should move to first position"


def test_apply_recs_ungrounded_is_skipped(resume_with_data):
    """Ungrounded recommendations must be skipped."""
    from src.app.schemas_job_assistant import ResumeRecommendation, RecommendationType
    base = resume_with_data.structured_data.copy()
    original_summary = base["profile"]["summary"]
    recs = [ResumeRecommendation(
        id="r1", rec_type=RecommendationType.REWRITE,
        section="summary", suggested_text="Fake invented content about skills I never had.",
        reason="AI hallucination", grounded=False,  # explicitly ungrounded
    )]
    result = apply_recommendations_to_resume_data(base, recs)
    assert result["profile"]["summary"] == original_summary, "Ungrounded recs must not modify data"


# ---------------------------------------------------------------------------
# corpus token extraction
# ---------------------------------------------------------------------------

def test_extract_corpus_tokens_includes_skills(resume_with_data, mem_db, base_user):
    ctx = build_candidate_context(mem_db, base_user.id, resume_with_data)
    tokens = _extract_corpus_tokens(ctx)
    assert "python" in tokens
    assert "react" in tokens
    assert "docker" in tokens


# ---------------------------------------------------------------------------
# Prompt language tests (verify language instruction is included)
# ---------------------------------------------------------------------------

def test_stage1_prompt_includes_language_instruction_fr():
    from src.app.services.job_assistant import STAGE1_TEMPLATE, LANG_INSTRUCTION
    lang = "fr"
    prompt = STAGE1_TEMPLATE.format(
        title="Ingenieur Python", description="Nous recherchons un ingenieur Python." * 5,
        additional="", lang_instruction=LANG_INSTRUCTION[lang],
    )
    assert "francais" in prompt.lower() or "français" in prompt.lower() or "Reponds" in prompt


def test_stage1_prompt_includes_language_instruction_de():
    from src.app.services.job_assistant import STAGE1_TEMPLATE, LANG_INSTRUCTION
    lang = "de"
    prompt = STAGE1_TEMPLATE.format(
        title="Python Entwickler", description="Wir suchen einen erfahrenen Python Entwickler." * 5,
        additional="", lang_instruction=LANG_INSTRUCTION[lang],
    )
    assert "Deutsch" in prompt or "deutsch" in prompt


def test_stage1_prompt_includes_language_instruction_en():
    from src.app.services.job_assistant import STAGE1_TEMPLATE, LANG_INSTRUCTION
    lang = "en"
    prompt = STAGE1_TEMPLATE.format(
        title="Python Developer", description="We are looking for a Python developer." * 5,
        additional="", lang_instruction=LANG_INSTRUCTION[lang],
    )
    assert "English" in prompt


# ---------------------------------------------------------------------------
# Stage 5 - Interview & STAR Prep tests
# ---------------------------------------------------------------------------

def test_fallback_interview_prep_generates_grounded_questions():
    from src.app.services.job_assistant import _fallback_interview_prep
    from src.app.schemas_job_assistant import (
        CandidateContext,
        CandidateContextExperience,
        CandidateContextSkill,
        ExternalJobInput,
        MatchAnalysis,
        CandidateEvidenceMatch,
        MatchStatus,
        RequirementCategory,
        InterviewQuestionType,
    )

    ctx = CandidateContext()
    ctx.skills.append(CandidateContextSkill(name="FastAPI", proficiency="Expert"))
    ctx.experience.append(CandidateContextExperience(
        id="1", title="Backend Engineer", company="TechCorp",
        description="Built resilient microservices in FastAPI.",
        highlights=["Scaled throughput by 30%"],
    ))

    job = ExternalJobInput(
        target_role="Senior Python Engineer",
        job_description="We need an expert in FastAPI, Docker and Kubernetes." * 3,
    )

    match_analysis = MatchAnalysis()
    match_analysis.strong_matches.append(CandidateEvidenceMatch(
        requirement="FastAPI",
        requirement_category=RequirementCategory.TECHNICAL_SKILL,
        match_status=MatchStatus.STRONG,
    ))
    match_analysis.missing_or_unconfirmed.append(CandidateEvidenceMatch(
        requirement="Kubernetes",
        requirement_category=RequirementCategory.TECHNICAL_SKILL,
        match_status=MatchStatus.MISSING,
    ))

    prep = _fallback_interview_prep(ctx, job, match_analysis)
    assert len(prep.questions) >= 2
    assert len(prep.key_focus_areas) >= 1
    assert prep.confidence_tip

    # Check behavioral question
    beh_q = next((q for q in prep.questions if q.question_type == InterviewQuestionType.BEHAVIORAL), None)
    assert beh_q is not None
    assert "TechCorp" in beh_q.question
    assert beh_q.suggested_star.situation
    assert beh_q.suggested_star.action

    # Check gap question
    gap_q = next((q for q in prep.questions if q.question_type == InterviewQuestionType.QUALIFICATION_GAP), None)
    assert gap_q is not None
    assert "Kubernetes" in gap_q.question
    assert "bluff" in gap_q.handling_missing_skill.lower()
    assert "foundation" in gap_q.suggested_star.action.lower()

