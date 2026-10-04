"""
SQLAlchemy models for the AI Mock Interview & Skills Assessment module.

Design decisions:
- question_ref is a string ID pointing at the existing static JSON question bank
  (e.g. "de_spark_2"). No question content is duplicated here.
- Raw audio is never persisted (privacy default). transcript_text is kept.
- All new tables use standard Compust conventions: DateTime, Integer PK,
  JSON for flexible structured fields, cascade delete from session.
"""

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, Float, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .models import Base

# MySQL requires INT UNSIGNED for primary keys and foreign keys referencing
# users.id, jobs.id, resumes.id (which are created as INT UNSIGNED in migrations).
UnsignedInt = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")


class MockInterviewSession(Base):
    """Represents one complete mock interview session."""
    __tablename__ = "mock_interview_sessions"

    id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(UnsignedInt, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Configuration
    domain_id: Mapped[str] = mapped_column(String(100), default="behavioral")
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)  # optional target role
    difficulty: Mapped[str] = mapped_column(String(50), default="Standard")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=15)
    language: Mapped[str] = mapped_column(String(10), default="en")
    interview_type: Mapped[str] = mapped_column(String(50), default="behavioral")
    personalize_resume: Mapped[bool] = mapped_column(Boolean, default=True)
    voice_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_mode: Mapped[str] = mapped_column(String(50), default="voice_avatar")

    # Job-linked context (optional)
    job_id: Mapped[int | None] = mapped_column(UnsignedInt, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    resume_id: Mapped[int | None] = mapped_column(UnsignedInt, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)

    # Status lifecycle
    status: Mapped[str] = mapped_column(String(50), default="setup")
    # setup → in_progress → completed | abandoned

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Serialized interview plan (selected question IDs in order, competency distribution)
    interview_plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Evaluation status
    evaluation_status: Mapped[str] = mapped_column(String(50), default="pending")
    # pending → processing → completed | failed

    # Relationships
    turns: Mapped[list["MockInterviewTurn"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="MockInterviewTurn.turn_index",
        lazy="selectin",
    )
    assessment: Mapped["MockInterviewAssessment | None"] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )


class MockInterviewTurn(Base):
    """Represents a single question-answer exchange within a session."""
    __tablename__ = "mock_interview_turns"

    id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True)
    session_id: Mapped[int] = mapped_column(UnsignedInt, ForeignKey("mock_interview_sessions.id", ondelete="CASCADE"), index=True)
    turn_index: Mapped[int] = mapped_column(Integer)               # 0-based position in session

    # Question reference — points at static JSON question bank
    question_id: Mapped[str] = mapped_column(String(100))          # e.g. "teamwork_1"
    question_domain_id: Mapped[str] = mapped_column(String(100), default="behavioral")
    question_title: Mapped[str] = mapped_column(String(500))       # denormalized for display
    question_category: Mapped[str] = mapped_column(String(255))    # competency_label
    question_topic: Mapped[str] = mapped_column(String(255), default="behavioral")
    question_difficulty: Mapped[str] = mapped_column(String(50), default="Standard")
    competency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_follow_up: Mapped[bool] = mapped_column(Boolean, default=False)
    follow_up_focus: Mapped[str | None] = mapped_column(String(500), nullable=True)  # from classification
    parent_question_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Answer — raw audio is NEVER stored (privacy default)
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # Raw ASR transcript
    canonical_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)  # Normalized transcript
    stt_engine: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "faster-whisper"|"web-speech-api"
    stt_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    @property
    def raw_transcript(self) -> str | None:
        """Alias for transcript_text representing the original raw ASR speech recognition output."""
        return self.transcript_text

    # Timing & Timeline Anchors
    asked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    answer_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_time_offset_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_time_offset_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Deterministic delivery metrics computed in pure Python
    wpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    filler_word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filler_words: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    longest_pause_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_to_first_word_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    i_vs_we_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Follow-up classification verdict (compact JSON from realtime gate)
    followup_verdict: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # {"strength": "weak|adequate|strong", "follow_up_suggested": bool, "follow_up_focus": str}

    # Relationships
    session: Mapped[MockInterviewSession] = relationship(back_populates="turns")
    evaluation: Mapped["MockAnswerEvaluation | None"] = relationship(
        back_populates="turn",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )


class MockAnswerEvaluation(Base):
    """Post-interview AI evaluation for a single answer turn."""
    __tablename__ = "mock_answer_evaluations"

    id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True)
    turn_id: Mapped[int] = mapped_column(UnsignedInt, ForeignKey("mock_interview_turns.id", ondelete="CASCADE"), unique=True, index=True)

    # Dimension scores 0.0–1.0
    correctness: Mapped[float | None] = mapped_column(Float, nullable=True)
    completeness: Mapped[float | None] = mapped_column(Float, nullable=True)
    relevance: Mapped[float | None] = mapped_column(Float, nullable=True)
    technical_depth: Mapped[float | None] = mapped_column(Float, nullable=True)
    clarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    star_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Grounded STAR Evaluation fields
    star_situation: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "present" | "partial" | "missing"
    star_task: Mapped[str | None] = mapped_column(String(50), nullable=True)
    star_action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    star_result: Mapped[str | None] = mapped_column(String(50), nullable=True)
    star_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"situation": "...", "task": "...", ...}
    stronger_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    specificity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ownership_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    measurable_outcome_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Structured feedback
    missing_concepts: Mapped[list | None] = mapped_column(JSON, nullable=True)
    incorrect_claims: Mapped[list | None] = mapped_column(JSON, nullable=True)
    positive_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    improvement_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    better_answer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    ai_model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    evaluation_error: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationship
    turn: Mapped[MockInterviewTurn] = relationship(back_populates="evaluation")


class MockInterviewAssessment(Base):
    """Aggregated post-interview assessment for a completed session."""
    __tablename__ = "mock_interview_assessments"

    id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True)
    session_id: Mapped[int] = mapped_column(UnsignedInt, ForeignKey("mock_interview_sessions.id", ondelete="CASCADE"), unique=True, index=True)

    # Overall score 0–100
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Competency matrix & Timeline chart
    skill_matrix: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    competency_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timeline_data: Mapped[list | None] = mapped_column(JSON, nullable=True)
    delivery_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    action_plan: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Detected weak areas (competencies needing focus)
    weak_areas: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Recommendations tied back to behavioral question bank / HR prep
    recommendations: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Summary text
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ai_model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationship
    session: Mapped[MockInterviewSession] = relationship(back_populates="assessment")


class MockQuestionRubric(Base):
    """Cached per-question rubric (key concepts) extracted once, not per interview."""
    __tablename__ = "mock_question_rubrics"

    id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True)
    question_id: Mapped[str] = mapped_column(String(100), index=True)
    domain_id: Mapped[str] = mapped_column(String(100))

    # Extracted key concepts from the question's content field
    key_concepts: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # ["RDD", "lazy evaluation", "transformations vs actions", ...]

    # Source info
    extraction_method: Mapped[str] = mapped_column(String(50), default="heuristic")
    # "heuristic" | "ollama"
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("question_id", "domain_id", name="uq_mock_rubric_q_domain"),
    )
