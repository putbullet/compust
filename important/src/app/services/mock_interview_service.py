"""
Mock Interview Orchestrator Service.

Coordinates between:
- InterviewPrepService (question bank access)
- MockInterviewEngine (deterministic scheduling)
- MockInterviewAI (Ollama calls — follow-up classification + evaluation)
- DB (session persistence via SQLAlchemy)

This is the service layer called by the FastAPI route handlers.
All DB writes happen here — route handlers are thin.
"""

from __future__ import annotations

import asyncio
import logging
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from ..models_mock_interview import (
    MockInterviewSession,
    MockInterviewTurn,
    MockAnswerEvaluation,
    MockInterviewAssessment,
    MockQuestionRubric,
)
from ..models import Resume, Job
from ..repositories.resume import get_active_resume, list_user_resumes
from ..schemas_mock_interview import (
    EndSessionResponse,
    MockInterviewAssessmentResponse,
    MockInterviewSetupResponse,
    NextQuestionItem,
    RepracticeResponse,
    ResumeDomainDetectResponse,
    SessionHistoryResponse,
    SessionHistorySummary,
    SessionStateResponse,
    TurnSubmitResponse,
)
from .interview_prep import interview_prep_service, DOMAIN_DEFINITIONS
from .mock_interview_engine import (
    InterviewState,
    QuestionSlot,
    build_interview_plan,
    build_follow_up_slot,
    can_add_follow_up,
    plan_summary,
    pop_next_question,
    record_answer,
)
from .mock_interview_ai import (
    classify_follow_up,
    compute_skill_matrix as ai_compute_skill_matrix,
    detect_domain_from_resume,
    evaluate_answer,
    extract_key_concepts_heuristic,
    generate_recommendations,
)
from .transcript_normalizer import transcript_normalizer

logger = logging.getLogger("compust.mock_interview.service")

# Constants
PRIVACY_NOTICE = (
    "Your microphone audio is processed locally by faster-whisper (open source, runs on your device). "
    "Raw audio is immediately discarded after transcription — only the text transcript is stored. "
    "AI evaluation uses your local Ollama installation. "
    "No audio or transcript data leaves your device."
)
LOCAL_PROCESSING_NOTE = (
    "✓ Speech recognition: local (faster-whisper) "
    "✓ AI evaluation: local (Ollama) "
    "✓ Text-to-speech: browser-native (SpeechSynthesis API) "
    "✗ No data sent to external servers"
)


class MockInterviewService:
    def __init__(self):
        self._content_root = Path(__file__).resolve().parent.parent / "content" / "interview_prep"
        self._domain_metadata_cache: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Session Setup
    # ------------------------------------------------------------------

    def create_session(
        self,
        db: Session,
        user_id: int,
        domain_id: str,
        difficulty: str,
        duration_minutes: int,
        role: Optional[str] = None,
        job_id: Optional[int] = None,
        resume_id: Optional[int] = None,
    ) -> MockInterviewSetupResponse:
        """
        Create a new interview session with a planned question queue.
        Returns setup info including the planned distribution (not a fixed promise).
        """
        # Validate domain
        domain_def = next((d for d in DOMAIN_DEFINITIONS if d["id"] == domain_id), None)
        if not domain_def:
            raise ValueError(f"Unknown domain '{domain_id}'")

        # Load question bank
        questions = interview_prep_service._load_domain_questions(domain_id)
        if not questions:
            raise ValueError(f"No questions found for domain '{domain_id}'")

        # Get previously asked question IDs for this user (spaced-repetition)
        prev_asked = self._get_user_previous_question_ids(db, user_id, domain_id)

        # Job-specific skill tags for biasing
        job_skill_tags: Set[str] = set()
        if job_id:
            job_tags = self._get_job_skill_tags(db, job_id)
            job_skill_tags = job_tags

        # Weak area category IDs (from most recent session with poor performance)
        weak_cat_ids: Set[str] = set()

        # Load behavioral questions from interview_prep_service if available
        beh_questions = []
        try:
            beh_prep = interview_prep_service.get_behavioral_prep("en")
            if beh_prep and getattr(beh_prep, "questions", None):
                for bq in beh_prep.questions:
                    beh_questions.append({
                        "id": getattr(bq, "id", f"beh_{len(beh_questions)}"),
                        "category_id": "behavioral_" + getattr(bq, "category", "general"),
                        "category_name": "Behavioral (" + getattr(bq, "category", "general").replace("_", " ").title() + ")",
                        "topic": getattr(bq, "category", "Behavioral").replace("_", " ").title(),
                        "title": getattr(bq, "question", ""),
                        "difficulty": difficulty,
                        "estimated_seconds": 120,
                    })
        except Exception as e:
            logger.warning(f"Could not load behavioral questions: {e}")

        # Normalize and sanitize optional role (handles "", "   ", None)
        clean_role = role.strip() if (role and isinstance(role, str) and role.strip()) else None

        # Build plan with natural introduction and behavioral integration
        state = build_interview_plan(
            domain_questions=questions,
            domain_id=domain_id,
            difficulty=difficulty,
            duration_minutes=duration_minutes,
            previously_asked_ids=prev_asked,
            job_skill_tags=job_skill_tags,
            weak_category_ids=weak_cat_ids,
            session_id=0,  # will be updated after DB insert
            role=clean_role,
            domain_title=domain_def["title"],
            behavioral_questions=beh_questions,
            include_intro=True,
            include_behavioral=True,
        )

        summary = plan_summary(state)

        # Persist session
        session = MockInterviewSession(
            user_id=user_id,
            domain_id=domain_id,
            role=clean_role,
            difficulty=difficulty,
            duration_minutes=duration_minutes,
            job_id=job_id,
            resume_id=resume_id,
            status="setup",
            evaluation_status="pending",
        )
        db.add(session)
        db.flush()

        # Update state with real session_id and persist plan
        state.session_id = session.id
        session.interview_plan = state.to_dict()
        db.commit()
        db.refresh(session)

        return MockInterviewSetupResponse(
            session_id=session.id,
            domain_id=domain_id,
            domain_title=domain_def["title"],
            difficulty=difficulty,
            duration_minutes=duration_minutes,
            planned_question_count=summary["planned_question_count"],
            category_distribution=summary["category_distribution"],
            privacy_notice=PRIVACY_NOTICE,
            requires_microphone=True,
            local_processing_note=LOCAL_PROCESSING_NOTE,
        )

    # ------------------------------------------------------------------
    # Session Start (first question)
    # ------------------------------------------------------------------

    def start_session(
        self,
        db: Session,
        session_id: int,
        user_id: int,
    ) -> TurnSubmitResponse:
        """
        Transition session to in_progress and deliver the first question.
        """
        session = self._get_session_for_user(db, session_id, user_id)
        if session.status != "setup":
            raise ValueError(f"Session {session_id} is not in setup state (status: {session.status})")

        state = InterviewState.from_dict(session.interview_plan)
        state.started_at = datetime.now(timezone.utc)
        state.elapsed_seconds = 0.0

        session.status = "in_progress"
        session.started_at = state.started_at

        next_slot = pop_next_question(state)
        if not next_slot:
            raise ValueError("No questions available in session plan")

        # Create turn record
        turn = self._create_turn(db, session, state, next_slot)

        session.interview_plan = state.to_dict()
        db.commit()
        db.refresh(turn)

        return TurnSubmitResponse(
            turn_id=turn.id,
            session_id=session_id,
            elapsed_seconds=0.0,
            remaining_seconds=float(state.total_budget_seconds),
            questions_asked=1,
            interview_complete=False,
            next_question=self._slot_to_next_question(next_slot),
            follow_up_triggered=False,
        )

    # ------------------------------------------------------------------
    # Submit Answer & Get Next Question
    # ------------------------------------------------------------------

    def submit_turn(
        self,
        db: Session,
        session_id: int,
        user_id: int,
        transcript: str,
        stt_engine: str,
        stt_confidence: Optional[float],
        answer_duration_seconds: Optional[float],
    ) -> TurnSubmitResponse:
        """
        Process a submitted answer and determine the next action:
        1. Record the answer on the current turn
        2. Run realtime follow-up classification (small LLM call)
        3. If follow-up warranted and bounded: insert follow-up slot
        4. Pop next question from queue or end interview
        """
        session = self._get_session_for_user(db, session_id, user_id)
        if session.status != "in_progress":
            raise ValueError(f"Session {session_id} is not in_progress (status: {session.status})")

        state = InterviewState.from_dict(session.interview_plan)

        # Find current (most recent unanswered) turn
        current_turn = self._get_current_unanswered_turn(session)
        if not current_turn:
            raise ValueError("No active turn found for this session")

        # Record answer
        now = datetime.now(timezone.utc)
        answer_dur = answer_duration_seconds or 60.0
        current_turn.transcript_text = transcript

        # Context-aware acoustic normalization (ASR error correction without over-correction)
        canonical, applied_corrections = transcript_normalizer.normalize(
            raw_text=transcript,
            domain_id=current_turn.question_domain_id,
            category_name=current_turn.question_category,
            topic=current_turn.question_topic,
            question_title=current_turn.question_title,
        )
        current_turn.canonical_transcript = canonical
        current_turn.stt_engine = stt_engine
        current_turn.stt_confidence = stt_confidence
        current_turn.answered_at = now
        current_turn.answer_duration_seconds = answer_dur

        record_answer(state, answer_dur, is_follow_up=current_turn.is_follow_up)

        # Realtime follow-up classification
        follow_up_triggered = False
        follow_up_verdict = {"strength": "adequate", "follow_up_suggested": False, "follow_up_focus": ""}

        if not current_turn.is_follow_up:  # Don't do follow-up of follow-up
            rubric = self._get_or_create_rubric(db, current_turn.question_id, current_turn.question_domain_id)
            key_concepts = rubric.key_concepts or []

            if can_add_follow_up(state) and (canonical or transcript).strip():
                follow_up_verdict = classify_follow_up(
                    question_title=current_turn.question_title,
                    key_concepts=key_concepts,
                    transcript=canonical or transcript,
                )
                current_turn.followup_verdict = follow_up_verdict

                if follow_up_verdict.get("follow_up_suggested") and follow_up_verdict.get("follow_up_focus"):
                    # Insert follow-up slot at front of queue
                    focus = follow_up_verdict["follow_up_focus"]
                    follow_up_slot = build_follow_up_slot(state, focus)
                    state.question_queue.insert(0, follow_up_slot)
                    follow_up_triggered = True
            else:
                current_turn.followup_verdict = follow_up_verdict

        db.flush()

        # Check time budget
        if state.is_time_expired or not state.question_queue:
            self._end_session_flow(db, session, state, "time_expired")
            return TurnSubmitResponse(
                turn_id=0,
                session_id=session.id,
                elapsed_seconds=state.elapsed_seconds,
                remaining_seconds=0.0,
                questions_asked=state.questions_asked,
                interview_complete=True,
                next_question=None,
                follow_up_triggered=False,
                message=(
                    "That brings us to the end of our interview today. "
                    "Thank you for your time and thoughtful responses. "
                    "I will now compile your practice assessment report."
                ),
            )

        # Pop next question
        next_slot = pop_next_question(state)
        if not next_slot:
            self._end_session_flow(db, session, state, "no_more_questions")
            return TurnSubmitResponse(
                turn_id=0,
                session_id=session.id,
                elapsed_seconds=state.elapsed_seconds,
                remaining_seconds=0.0,
                questions_asked=state.questions_asked,
                interview_complete=True,
                next_question=None,
                follow_up_triggered=False,
                message=(
                    "That brings us to the end of our interview today. "
                    "Thank you for your time and thoughtful responses. "
                    "I will now compile your practice assessment report."
                ),
            )

        next_turn = self._create_turn(db, session, state, next_slot)
        session.interview_plan = state.to_dict()
        db.commit()
        db.refresh(next_turn)

        return TurnSubmitResponse(
            turn_id=next_turn.id,
            session_id=session_id,
            elapsed_seconds=state.elapsed_seconds,
            remaining_seconds=state.remaining_seconds,
            questions_asked=state.questions_asked,
            interview_complete=False,
            next_question=self._slot_to_next_question(next_slot),
            follow_up_triggered=follow_up_triggered,
        )

    # ------------------------------------------------------------------
    # End Session (early or natural)
    # ------------------------------------------------------------------

    def end_session(
        self,
        db: Session,
        session_id: int,
        user_id: int,
        reason: str = "user_ended",
    ) -> EndSessionResponse:
        session = self._get_session_for_user(db, session_id, user_id)
        if session.status not in ("setup", "in_progress"):
            return EndSessionResponse(
                session_id=session_id,
                status=session.status,
                evaluation_status=session.evaluation_status,
                message="Session already ended.",
            )

        state = InterviewState.from_dict(session.interview_plan or {})
        return self._end_session_flow(db, session, state, reason)

    def _end_session_flow(
        self,
        db: Session,
        session: MockInterviewSession,
        state: InterviewState,
        reason: str,
    ) -> EndSessionResponse:
        """Common end-session logic."""
        # Prune any trailing unanswered turn created when previous turn finished
        unanswered = self._get_current_unanswered_turn(session)
        if unanswered and unanswered.answered_at is None and not unanswered.transcript_text:
            db.delete(unanswered)
            db.flush()

        session.status = "completed"
        session.ended_at = datetime.now(timezone.utc)
        session.interview_plan = state.to_dict()
        db.flush()

        # Trigger background evaluation (non-blocking)
        self._trigger_background_evaluation(db, session.id, session.user_id)

        db.commit()

        return EndSessionResponse(
            session_id=session.id,
            status="completed",
            evaluation_status=session.evaluation_status,
            message="Interview complete. Generating your assessment in the background...",
        )

    # ------------------------------------------------------------------
    # Background Evaluation (post-interview batch)
    # ------------------------------------------------------------------

    def _trigger_background_evaluation(self, db: Session, session_id: int, user_id: int) -> None:
        """
        Mark session as 'processing' and queue evaluation.
        In this MVP, evaluation runs synchronously in a background thread
        (FastAPI's background task system, triggered from the route handler).
        The session.evaluation_status is set here; actual evaluation work
        happens in run_post_interview_evaluation().
        """
        session = db.query(MockInterviewSession).filter(MockInterviewSession.id == session_id).first()
        if session:
            session.evaluation_status = "processing"
            db.commit()

    def run_post_interview_evaluation(self, db: Session, session_id: int) -> None:
        """
        Full post-interview evaluation batch. Runs off the realtime critical path.
        Called by FastAPI BackgroundTask after session completion.
        """
        session = db.query(MockInterviewSession).filter(MockInterviewSession.id == session_id).first()
        if not session:
            logger.error(f"Evaluation: session {session_id} not found")
            return

        try:
            session.evaluation_status = "processing"
            db.commit()

            # Clean up trailing turns that were created for next question but never reached/answered
            for t in list(session.turns):
                if t.answered_at is None and not t.transcript_text:
                    db.delete(t)
            db.flush()
            db.refresh(session)

            turns = session.turns
            if not turns:
                session.evaluation_status = "completed"
                db.commit()
                return

            domain_meta = self._load_domain_metadata(session.domain_id)
            categories = domain_meta.get("categories", [])
            cat_name_to_id = {c["name"].lower(): c["id"] for c in categories}
            cat_id_to_name = {c["id"]: c["name"] for c in categories}

            evaluation_records: List[Dict[str, Any]] = []

            # Evaluate each turn
            for turn in turns:
                is_intro = turn.question_id.startswith("intro_") or turn.question_category.lower() == "introduction & background"
                is_beh = "behavioral" in turn.question_category.lower() or "behavioral" in turn.question_id.lower() or is_intro
                q_type = "introductory" if is_intro else ("behavioral" if is_beh else "technical")

                if is_intro:
                    true_cat_id = "introduction"
                    true_cat_name = "Introduction & Background"
                elif is_beh:
                    true_cat_id = "behavioral"
                    true_cat_name = "Behavioral & Communication"
                else:
                    true_cat_id = cat_name_to_id.get(turn.question_category.lower())
                    if not true_cat_id and turn.question_category in cat_id_to_name:
                        true_cat_id = turn.question_category
                    if not true_cat_id:
                        true_cat_id = turn.question_domain_id
                    true_cat_name = cat_id_to_name.get(true_cat_id, turn.question_category)

                canonical_text = turn.canonical_transcript or turn.transcript_text
                if not turn.transcript_text and not canonical_text:
                    # Turn was explicitly reached and skipped
                    eval_record = MockAnswerEvaluation(
                        turn_id=turn.id,
                        evaluation_error="No answer provided — turn was skipped",
                    )
                    db.add(eval_record)
                    evaluation_records.append({
                        "question_id": turn.question_id,
                        "parent_question_id": getattr(turn, "parent_question_id", None),
                        "category_id": true_cat_id,
                        "category_name": true_cat_name,
                        "topic": turn.question_topic,
                        "question_title": turn.question_title,
                        "question_type": q_type,
                        "turn_index": turn.turn_index,
                        "correctness": 0.0,
                        "completeness": 0.0,
                        "relevance": 0.0,
                        "technical_depth": 0.0,
                        "clarity": 0.0,
                        "demonstrated_status": "not_demonstrated",
                        "evaluation_error": "No answer provided — turn was skipped",
                    })
                    continue

                rubric = self._get_or_create_rubric(db, turn.question_id, turn.question_domain_id)
                key_concepts = rubric.key_concepts or []

                result = evaluate_answer(
                    question_title=turn.question_title,
                    key_concepts=key_concepts,
                    transcript=canonical_text or "",
                    question_type=q_type,
                    domain_id=turn.question_domain_id,
                    category_name=true_cat_name,
                    topic=turn.question_topic,
                    raw_transcript=turn.transcript_text,
                    canonical_transcript=canonical_text,
                )

                star_notes = ""
                if result.get("star_breakdown"):
                    sb = result["star_breakdown"]
                    star_notes = f" [STAR Coverage - S: {int((sb.get('situation') or 0)*100)}%, T: {int((sb.get('task') or 0)*100)}%, A: {int((sb.get('action') or 0)*100)}%, R: {int((sb.get('result') or 0)*100)}%]"

                eval_obj = MockAnswerEvaluation(
                    turn_id=turn.id,
                    correctness=result.get("correctness"),
                    completeness=result.get("completeness"),
                    relevance=result.get("relevance"),
                    technical_depth=result.get("technical_depth"),
                    clarity=result.get("clarity"),
                    star_breakdown=result.get("star_breakdown"),
                    missing_concepts=result.get("missing_concepts", []),
                    incorrect_claims=result.get("incorrect_claims", []),
                    positive_points=result.get("positive_points", []),
                    improvement_points=result.get("improvement_points", []),
                    better_answer_notes=(result.get("better_answer_notes", "") or "") + star_notes,
                    ai_model_used=result.get("ai_model_used"),
                    evaluation_error=result.get("evaluation_error"),
                )
                db.add(eval_obj)
                evaluation_records.append({
                    "question_id": turn.question_id,
                    "parent_question_id": getattr(turn, "parent_question_id", None),
                    "category_id": true_cat_id,
                    "category_name": true_cat_name,
                    "topic": turn.question_topic,
                    "question_title": turn.question_title,
                    "question_type": q_type,
                    "turn_index": turn.turn_index,
                    "raw_transcript": turn.transcript_text,
                    "canonical_transcript": canonical_text,
                    **result,
                })

            db.flush()

            # Compute skill matrix & scores (deterministic aggregation — no LLM)
            sm_result = ai_compute_skill_matrix(
                evaluation_records,
                {cat["id"]: cat["name"] for cat in categories},
            )
            (
                skill_matrix,
                weak_areas,
                strengths,
                overall_score,
                tech_score,
                beh_score,
            ) = sm_result

            recommendations = generate_recommendations(
                weak_areas,
                session.domain_id,
                domain_meta,
                weak_area_details=sm_result.weak_area_details,
            )

            # Persist assessment with separate technical & behavioral breakdown
            assessment = MockInterviewAssessment(
                session_id=session_id,
                overall_score=overall_score,
                skill_matrix={
                    "entries": skill_matrix,
                    "technical_score": tech_score,
                    "behavioral_score": beh_score,
                    "strengths": strengths,
                    "assessed_domains": sm_result.assessed_domains,
                    "unassessed_domains": sm_result.unassessed_domains,
                    "weak_area_details": sm_result.weak_area_details,
                    "strength_details": sm_result.strength_details,
                    "questions_asked": sm_result.questions_asked,
                    "questions_answered": sm_result.questions_answered,
                    "unassessed_disclaimer": sm_result.unassessed_disclaimer,
                },
                weak_areas=weak_areas,
                recommendations=recommendations,
                summary_text=self._build_summary_text(
                    overall_score=overall_score,
                    weak_areas=weak_areas,
                    question_count=sm_result.questions_answered,
                    technical_score=tech_score,
                    behavioral_score=beh_score,
                    unassessed_domains=sm_result.unassessed_domains,
                ),
                ai_model_used=evaluation_records[0].get("ai_model_used") if evaluation_records else None,
            )
            db.add(assessment)

            session.evaluation_status = "completed"
            db.commit()
            logger.info(f"Post-interview evaluation complete for session {session_id}: overall={overall_score}, tech={tech_score}, beh={beh_score}")

        except Exception as e:
            logger.error(f"Post-interview evaluation failed for session {session_id}: {e}", exc_info=True)
            try:
                session.evaluation_status = "failed"
                db.commit()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Assessment retrieval
    # ------------------------------------------------------------------

    def get_assessment(
        self,
        db: Session,
        session_id: int,
        user_id: int,
    ) -> MockInterviewAssessmentResponse:
        session = self._get_session_for_user(db, session_id, user_id)

        turns = session.turns
        assessment = session.assessment

        if not assessment:
            # Return in-progress state
            return MockInterviewAssessmentResponse(
                session_id=session_id,
                overall_score=0.0,
                technical_score=0.0,
                behavioral_score=0.0,
                evaluation_status=session.evaluation_status,
                summary_text="Your assessment is being generated. Please wait...",
                skill_matrix=[],
                weak_areas=[],
                strengths=[],
                answer_details=[],
                recommendations=[],
            )

        from ..schemas_mock_interview import (
            AnswerEvaluationDetail,
            AssessmentEvidenceItem,
            AssessmentRecommendation,
            SkillMatrixEntry,
        )

        answer_details = []
        for turn in turns:
            ev = turn.evaluation
            is_intro = turn.question_id.startswith("intro_") or turn.question_category.lower() == "introduction & background"
            is_beh = "behavioral" in turn.question_category.lower() or "behavioral" in turn.question_id.lower() or is_intro
            q_type = "introductory" if is_intro else ("behavioral" if is_beh else "technical")

            ans_score = None
            if ev:
                dims = [ev.correctness, ev.completeness, ev.relevance, ev.technical_depth]
                vdims = [d for d in dims if d is not None]
                if vdims:
                    ans_score = sum(vdims) / len(vdims)

            if not turn.transcript_text:
                dem_status = "not_demonstrated"
            elif ans_score is not None:
                if ans_score >= 0.75:
                    dem_status = "demonstrated"
                elif ans_score >= 0.45:
                    dem_status = "partially_demonstrated"
                else:
                    dem_status = "not_demonstrated"
            else:
                dem_status = "not_demonstrated"

            raw_t = turn.transcript_text
            canon_t = getattr(turn, "canonical_transcript", None) or raw_t

            answer_details.append(AnswerEvaluationDetail(
                turn_id=turn.id,
                turn_index=turn.turn_index,
                question_id=turn.question_id,
                parent_question_id=getattr(turn, "parent_question_id", None),
                question_title=turn.question_title,
                category=turn.question_category,
                topic=turn.question_topic,
                difficulty=turn.question_difficulty,
                is_follow_up=turn.is_follow_up,
                question_type=q_type,
                transcript=raw_t,
                raw_transcript=raw_t,
                canonical_transcript=canon_t,
                demonstrated_status=dem_status,
                correctness=ev.correctness if ev else None,
                completeness=ev.completeness if ev else None,
                relevance=ev.relevance if ev else None,
                technical_depth=ev.technical_depth if ev else None,
                clarity=ev.clarity if ev else None,
                star_breakdown=getattr(ev, "star_breakdown", None) if ev else None,
                missing_concepts=ev.missing_concepts or [] if ev else [],
                incorrect_claims=ev.incorrect_claims or [] if ev else [],
                positive_points=ev.positive_points or [] if ev else [],
                improvement_points=ev.improvement_points or [] if ev else [],
                better_answer_notes=ev.better_answer_notes if ev else None,
                evaluation_error=ev.evaluation_error if ev else None,
            ))

        raw_sm = assessment.skill_matrix
        tech_score = None
        beh_score = None
        strengths = []
        assessed_domains = []
        unassessed_domains = []
        unassessed_disclaimer = (
            "These topics were not assessed during this interview, "
            "so no conclusion about proficiency can be drawn from this session."
        )
        weak_area_details = []
        strength_details = []
        questions_asked = len(turns)
        questions_answered = len([t for t in turns if t.answered_at or t.transcript_text])

        if isinstance(raw_sm, dict):
            matrix_list = raw_sm.get("entries", [])
            tech_score = raw_sm.get("technical_score")
            beh_score = raw_sm.get("behavioral_score")
            strengths = raw_sm.get("strengths", [])
            assessed_domains = raw_sm.get("assessed_domains", [])
            unassessed_domains = raw_sm.get("unassessed_domains", [])
            unassessed_disclaimer = raw_sm.get("unassessed_disclaimer", unassessed_disclaimer)
            weak_area_details = raw_sm.get("weak_area_details", [])
            strength_details = raw_sm.get("strength_details", [])
            questions_asked = raw_sm.get("questions_asked", questions_asked)
            questions_answered = raw_sm.get("questions_answered", questions_answered)
        elif isinstance(raw_sm, list):
            matrix_list = raw_sm
        else:
            matrix_list = []

        skill_matrix = [
            SkillMatrixEntry(
                category_name=sm["category_name"],
                category_id=sm.get("category_id", ""),
                rating=sm["rating"],
                score=sm.get("score"),
                question_count=sm["question_count"],
                basis=sm["basis"],
                status=sm.get("status", "not_assessed" if sm.get("rating") == "Not Assessed" else "demonstrated"),
            )
            for sm in matrix_list
        ]

        recommendations = [
            AssessmentRecommendation(
                area=r["area"],
                action=r["action"],
                domain_id=r["domain_id"],
                category_id=r.get("category_id"),
                priority=r.get("priority", "medium"),
                source_question_id=r.get("source_question_id"),
            )
            for r in (assessment.recommendations or [])
        ]

        return MockInterviewAssessmentResponse(
            session_id=session_id,
            overall_score=assessment.overall_score or 0.0,
            technical_score=tech_score if tech_score is not None else (assessment.overall_score or 0.0),
            behavioral_score=beh_score if beh_score is not None else (assessment.overall_score or 0.0),
            evaluation_status=session.evaluation_status,
            summary_text=assessment.summary_text,
            questions_asked=questions_asked,
            questions_answered=questions_answered,
            assessed_domains=assessed_domains,
            unassessed_domains=unassessed_domains,
            unassessed_disclaimer=unassessed_disclaimer,
            skill_matrix=skill_matrix,
            weak_areas=assessment.weak_areas or [],
            weak_area_details=[AssessmentEvidenceItem(**item) for item in weak_area_details] if weak_area_details else [],
            strengths=strengths,
            strength_details=[AssessmentEvidenceItem(**item) for item in strength_details] if strength_details else [],
            answer_details=answer_details,
            recommendations=recommendations,
            ai_model_used=assessment.ai_model_used,
            generated_at=assessment.generated_at,
        )

    # ------------------------------------------------------------------
    # Session State (for reconnect)
    # ------------------------------------------------------------------

    def get_session_state(
        self,
        db: Session,
        session_id: int,
        user_id: int,
    ) -> SessionStateResponse:
        session = self._get_session_for_user(db, session_id, user_id)
        state = InterviewState.from_dict(session.interview_plan or {})

        domain_def = next((d for d in DOMAIN_DEFINITIONS if d["id"] == session.domain_id), {})
        current_turn = self._get_current_unanswered_turn(session)
        current_question = None
        if current_turn and session.status == "in_progress":
            is_intro = current_turn.question_id.startswith("intro_") or current_turn.question_category.lower() == "introduction & background"
            is_beh = "behavioral" in current_turn.question_category.lower() or "behavioral" in current_turn.question_id.lower() or is_intro
            q_type = "introductory" if is_intro else ("behavioral" if is_beh else "technical")
            tts = self._build_tts_text(current_turn.question_title, current_turn.is_follow_up, current_turn.follow_up_focus)
            video_info = None
            try:
                from .alex_video_service import alex_video_service
                video_info = alex_video_service.get_video_for_question(
                    question_id=current_turn.question_id,
                    question_text=tts or current_turn.question_title,
                    domain_id=current_turn.question_domain_id,
                )
            except Exception as e:
                logger.warning(f"Error querying Alex video service for recovery turn '{current_turn.question_id}': {e}")

            video_url = video_info.get("video_path") if video_info else None
            audio_url = video_info.get("audio_path") if video_info else None

            current_question = NextQuestionItem(
                question_id=current_turn.question_id,
                question_title=current_turn.question_title,
                domain_id=current_turn.question_domain_id,
                category=current_turn.question_category,
                topic=current_turn.question_topic,
                difficulty=current_turn.question_difficulty,
                is_follow_up=current_turn.is_follow_up,
                follow_up_focus=current_turn.follow_up_focus,
                question_type=q_type,
                expected_duration_seconds=60 if is_intro else (100 if is_beh else 90),
                tts_text=tts,
                interviewer_name="Alex",
                interviewer_video_url=video_url,
                interviewer_audio_url=audio_url,
            )

        return SessionStateResponse(
            session_id=session_id,
            status=session.status,
            domain_id=session.domain_id,
            domain_title=domain_def.get("title", session.domain_id),
            difficulty=session.difficulty,
            duration_minutes=session.duration_minutes,
            elapsed_seconds=state.elapsed_seconds,
            remaining_seconds=state.remaining_seconds,
            questions_asked=len([t for t in session.turns if t.answered_at]),
            current_question=current_question,
            evaluation_status=session.evaluation_status,
            started_at=session.started_at,
            ended_at=session.ended_at,
        )

    # ------------------------------------------------------------------
    # Session History
    # ------------------------------------------------------------------

    def get_session_history(
        self,
        db: Session,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> SessionHistoryResponse:
        sessions = (
            db.query(MockInterviewSession)
            .filter(MockInterviewSession.user_id == user_id)
            .order_by(MockInterviewSession.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        total = db.query(MockInterviewSession).filter(MockInterviewSession.user_id == user_id).count()

        domain_titles = {d["id"]: d["title"] for d in DOMAIN_DEFINITIONS}
        summaries = []
        for s in sessions:
            assessment = s.assessment
            summaries.append(SessionHistorySummary(
                session_id=s.id,
                domain_id=s.domain_id,
                domain_title=domain_titles.get(s.domain_id, s.domain_id),
                difficulty=s.difficulty,
                duration_minutes=s.duration_minutes,
                status=s.status,
                evaluation_status=s.evaluation_status,
                overall_score=assessment.overall_score if assessment else None,
                weak_areas=assessment.weak_areas or [] if assessment else [],
                questions_asked=len(s.turns),
                started_at=s.started_at,
                ended_at=s.ended_at,
                created_at=s.created_at,
            ))

        return SessionHistoryResponse(sessions=summaries, total=total)

    # ------------------------------------------------------------------
    # Domain detection from resume
    # ------------------------------------------------------------------

    def detect_domain_from_user_resume(
        self,
        db: Session,
        user_id: int,
        resume_id: Optional[int] = None,
    ) -> ResumeDomainDetectResponse:
        """Suggest a domain based on the user's resume. Always returns suggestion for user to override."""
        resume = None
        if resume_id:
            from sqlalchemy import select
            resume = db.execute(
                select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
            ).scalar_one_or_none()
        if not resume:
            resume = get_active_resume(db, user_id)
        if not resume:
            resumes = list_user_resumes(db, user_id)
            if resumes:
                resume = resumes[0]

        if not resume or not resume.raw_text:
            return ResumeDomainDetectResponse(
                suggested_domain_id="data_engineering",
                suggested_domain_title="Data Engineering",
                confidence="low",
                reasoning="No resume found — showing default suggestion.",
                suggested_difficulty="Intermediate",
                is_ai_suggested=True,
            )

        domain_titles = {d["id"]: d["title"] for d in DOMAIN_DEFINITIONS}
        result = detect_domain_from_resume(resume.raw_text)

        return ResumeDomainDetectResponse(
            suggested_domain_id=result.get("domain_id", "data_engineering"),
            suggested_domain_title=domain_titles.get(result.get("domain_id", ""), "Data Engineering"),
            confidence=result.get("confidence", "low"),
            reasoning=result.get("reasoning", ""),
            suggested_difficulty=result.get("suggested_difficulty", "Intermediate"),
            is_ai_suggested=True,
        )

    # ------------------------------------------------------------------
    # Re-practice weak areas
    # ------------------------------------------------------------------

    def create_repractice_session(
        self,
        db: Session,
        user_id: int,
        source_session_id: int,
        duration_minutes: int,
    ) -> RepracticeResponse:
        """Create a new session weighted toward the weak areas from a prior session."""
        source = self._get_session_for_user(db, source_session_id, user_id)
        assessment = source.assessment

        if not assessment:
            raise ValueError("Source session assessment not yet complete")

        weak_areas = assessment.weak_areas or []
        domain_meta = self._load_domain_metadata(source.domain_id)

        # Map weak area names back to category IDs
        weak_cat_ids: Set[str] = set()
        for cat in domain_meta.get("categories", []):
            if cat.get("name") in weak_areas:
                weak_cat_ids.add(cat["id"])

        setup = self.create_session(
            db=db,
            user_id=user_id,
            domain_id=source.domain_id,
            difficulty=source.difficulty,
            duration_minutes=duration_minutes,
            role=source.role,
            job_id=source.job_id,
            resume_id=source.resume_id,
        )

        # Re-run plan with weak area boost
        questions = interview_prep_service._load_domain_questions(source.domain_id)
        prev_asked = self._get_user_previous_question_ids(db, user_id, source.domain_id)

        new_session = db.query(MockInterviewSession).filter(MockInterviewSession.id == setup.session_id).first()
        state = build_interview_plan(
            domain_questions=questions,
            domain_id=source.domain_id,
            difficulty=source.difficulty,
            duration_minutes=duration_minutes,
            previously_asked_ids=prev_asked,
            weak_category_ids=weak_cat_ids,
            session_id=setup.session_id,
        )
        new_session.interview_plan = state.to_dict()
        db.commit()

        return RepracticeResponse(
            new_session_id=setup.session_id,
            domain_id=source.domain_id,
            difficulty=source.difficulty,
            duration_minutes=duration_minutes,
            weak_areas_targeted=weak_areas,
            message=f"New session created with focus on: {', '.join(weak_areas[:3]) or 'all areas'}",
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_session_for_user(self, db: Session, session_id: int, user_id: int) -> MockInterviewSession:
        session = db.query(MockInterviewSession).filter(
            MockInterviewSession.id == session_id,
            MockInterviewSession.user_id == user_id,
        ).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")
        return session

    def _get_current_unanswered_turn(self, session: MockInterviewSession) -> Optional[MockInterviewTurn]:
        """Get the most recent turn that hasn't been answered yet."""
        for turn in reversed(session.turns):
            if turn.answered_at is None:
                return turn
        return None

    def _create_turn(
        self,
        db: Session,
        session: MockInterviewSession,
        state: InterviewState,
        slot: QuestionSlot,
    ) -> MockInterviewTurn:
        turn = MockInterviewTurn(
            session_id=session.id,
            turn_index=len(session.turns),
            question_id=slot.question_id,
            question_domain_id=slot.domain_id,
            question_title=slot.title,
            question_category=slot.category_name,
            question_topic=slot.topic,
            question_difficulty=slot.difficulty,
            is_follow_up=slot.is_follow_up,
            follow_up_focus=slot.follow_up_focus,
            asked_at=datetime.now(timezone.utc),
        )
        db.add(turn)
        db.flush()
        return turn

    def _slot_to_next_question(self, slot: QuestionSlot) -> NextQuestionItem:
        tts = slot.tts_text or self._build_tts_text(slot.title, slot.is_follow_up, slot.follow_up_focus)

        # Check Alex video registry for pre-generated video
        video_info = None
        try:
            from .alex_video_service import alex_video_service
            video_info = alex_video_service.get_video_for_question(
                question_id=slot.question_id,
                question_text=slot.tts_text or slot.title,
                domain_id=slot.domain_id,
            )
        except Exception as e:
            logger.warning(f"Error querying Alex video service for '{slot.question_id}': {e}")

        video_url = video_info.get("video_path") if video_info else None
        audio_url = video_info.get("audio_path") if video_info else None

        return NextQuestionItem(
            question_id=slot.question_id,
            question_title=slot.title,
            domain_id=slot.domain_id,
            category=slot.category_name,
            topic=slot.topic,
            difficulty=slot.difficulty,
            is_follow_up=slot.is_follow_up,
            follow_up_focus=slot.follow_up_focus,
            question_type=getattr(slot, "question_type", "technical"),
            expected_duration_seconds=getattr(slot, "estimated_seconds", 90),
            tts_text=tts,
            interviewer_name="Alex",
            interviewer_video_url=video_url,
            interviewer_audio_url=audio_url,
        )

    def _build_tts_text(self, title: str, is_follow_up: bool, focus: Optional[str]) -> str:
        """Build natural-sounding text for TTS playback."""
        if is_follow_up and focus:
            return f"Good. Let me follow up on that. Can you elaborate on {focus}?"
        # Clean markdown from title for TTS
        clean = title.replace("**", "").replace("*", "").replace("`", "").replace("#", "")
        return clean

    def _get_or_create_rubric(
        self,
        db: Session,
        question_id: str,
        domain_id: str,
    ) -> MockQuestionRubric:
        """Get cached rubric or create it from question content (heuristic extraction)."""
        existing = db.query(MockQuestionRubric).filter(
            MockQuestionRubric.question_id == question_id,
            MockQuestionRubric.domain_id == domain_id,
        ).first()
        if existing:
            return existing

        # Extract key concepts from question bank content
        questions = interview_prep_service._load_domain_questions(domain_id)
        q_data = next((q for q in questions if q.get("id") == question_id), None)

        key_concepts = []
        if q_data:
            content = q_data.get("content") or q_data.get("markdown_content") or ""
            key_concepts = extract_key_concepts_heuristic(q_data.get("title", ""), content)

        rubric = MockQuestionRubric(
            question_id=question_id,
            domain_id=domain_id,
            key_concepts=key_concepts,
            extraction_method="heuristic",
        )
        db.add(rubric)
        try:
            db.flush()
        except Exception:
            db.rollback()
            # Race condition: another request created it — fetch it
            existing = db.query(MockQuestionRubric).filter(
                MockQuestionRubric.question_id == question_id,
                MockQuestionRubric.domain_id == domain_id,
            ).first()
            return existing or rubric

        return rubric

    def _get_user_previous_question_ids(
        self,
        db: Session,
        user_id: int,
        domain_id: str,
        lookback_sessions: int = 5,
    ) -> Set[str]:
        """Get question IDs asked in recent sessions (for spaced-repetition variety)."""
        recent_sessions = (
            db.query(MockInterviewSession)
            .filter(
                MockInterviewSession.user_id == user_id,
                MockInterviewSession.domain_id == domain_id,
                MockInterviewSession.status == "completed",
            )
            .order_by(MockInterviewSession.created_at.desc())
            .limit(lookback_sessions)
            .all()
        )

        asked_ids: Set[str] = set()
        for s in recent_sessions:
            for turn in s.turns:
                asked_ids.add(turn.question_id)
        return asked_ids

    def _get_job_skill_tags(self, db: Session, job_id: int) -> Set[str]:
        """Get skill tags for a job from job_skills table."""
        from sqlalchemy import text
        try:
            result = db.execute(
                text("SELECT skill FROM job_skills WHERE job_id = :job_id"),
                {"job_id": job_id},
            ).fetchall()
            return {row[0].lower() for row in result}
        except Exception:
            return set()

    def _load_domain_metadata(self, domain_id: str) -> Dict[str, Any]:
        if domain_id in self._domain_metadata_cache:
            return self._domain_metadata_cache[domain_id]
        meta_path = self._content_root / domain_id / "metadata.json"
        if meta_path.exists():
            import json as _json
            with open(meta_path, "r", encoding="utf-8") as f:
                data = _json.load(f)
            self._domain_metadata_cache[domain_id] = data
            return data
        return {}

    def _build_summary_text(
        self,
        overall_score: float,
        weak_areas: List[str],
        question_count: int,
        technical_score: Optional[float] = None,
        behavioral_score: Optional[float] = None,
        unassessed_domains: Optional[List[str]] = None,
    ) -> str:
        if overall_score >= 75:
            quality = "strong"
        elif overall_score >= 50:
            quality = "moderate"
        else:
            quality = "developing"

        breakdown_str = ""
        if technical_score is not None and behavioral_score is not None:
            breakdown_str = f" (Technical: {technical_score:.0f}/100, Behavioral & Communication: {behavioral_score:.0f}/100)"

        summary = (
            f"You completed {question_count} question{'s' if question_count != 1 else ''} "
            f"with an overall practice score of {overall_score:.0f}/100{breakdown_str}, "
            f"reflecting a {quality} overall performance on the material assessed. "
        )
        if weak_areas:
            summary += (
                f"Demonstrated areas to focus on: {', '.join(weak_areas[:3])}. "
            )
        if unassessed_domains:
            summary += (
                f"Topics not assessed in this session: {', '.join(unassessed_domains)}. "
                "These topics were not assessed during this interview, so no conclusion about proficiency can be drawn from this session. "
            )
        summary += "Based on this practice interview, your performance currently reflects the configured practice criteria. This is an AI-generated practice assessment only — not a prediction of real employer decisions."
        return summary


# Module-level singleton
mock_interview_service = MockInterviewService()
