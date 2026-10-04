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
    domain_id: Mapped[str] = mapped_column(String(100))           # "data_engineering"
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)  # optional role filter
    difficulty: Mapped[str] = mapped_column(String(50))            # "Fundamental"|"Intermediate"|"Advanced"|"Mixed"
    duration_minutes: Mapped[int] = mapped_column(Integer)         # 10|20|30|45

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

    # Serialized interview plan (selected question IDs in order, per-subdomain weights)
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
    question_id: Mapped[str] = mapped_column(String(100))          # e.g. "de_spark_2"
    question_domain_id: Mapped[str] = mapped_column(String(100))   # e.g. "data_engineering"
    question_title: Mapped[str] = mapped_column(String(500))       # denormalized for display
    question_category: Mapped[str] = mapped_column(String(255))    # category_name
    question_topic: Mapped[str] = mapped_column(String(255))       # topic
    question_difficulty: Mapped[str] = mapped_column(String(50))   # difficulty
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

    # Timing
    asked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    answer_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Follow-up classification verdict (compact JSON from realtime LLM call)
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

    # Skill matrix: per-category/topic ratings
    # {"category_name": {"rating": "Strong|Moderate|Weak", "score": 0.0-1.0, "question_count": int}}
    skill_matrix: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Detected weak areas (category/topic names needing focus)
    weak_areas: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Recommendations tied back to question bank content
    recommendations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # [{"area": "Streaming & Event Messaging", "action": "Revisit Kafka consumer groups subdomain", "domain_id": "data_engineering", "category_id": "streaming-messaging"}]

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
