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
    DeleteSessionResponse,
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
from .interview_metrics import (
    compute_turn_metrics,
    aggregate_session_delivery,
)
from .mock_interview_engine import (
    InterviewState,
    QuestionSlot,
    build_interview_plan,
    build_follow_up_slot,
    can_add_follow_up,
    load_behavioral_questions,
    plan_summary,
    pop_next_question,
    record_answer,
    WRAPUP_BY_LANG,
)
from .mock_interview_ai import (
    build_session_timeline_data,
    classify_follow_up,
    compute_skill_matrix as ai_compute_skill_matrix,
    detect_domain_from_resume,
    evaluate_answer,
    extract_key_concepts_heuristic,
    generate_behavioral_action_plan,
    generate_recommendations,
)
from .transcript_normalizer import transcript_normalizer

logger = logging.getLogger("compust.mock_interview.service")

# Constants
PRIVACY_NOTICE = (
    "Your microphone audio is processed locally by faster-whisper (open source, runs on your device). "
    "Raw audio is immediately discarded after transcription — only the text transcript is stored. "
    "AI evaluation uses your configured AI provider (Ollama is local; Gemini/OpenAI send text to their cloud). "
    "No audio data leaves your device."
)
LOCAL_PROCESSING_NOTE = (
    "✓ Speech recognition: local (faster-whisper) "
    "✓ AI evaluation: configured AI provider (Ollama=local / Gemini,OpenAI=cloud) "
    "✓ Text-to-speech: browser-native (SpeechSynthesis API) "
    "✗ No audio data sent to external servers"
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
        domain_id: Optional[str] = "behavioral",
        difficulty: str = "Standard",
        duration_minutes: int = 15,
        role: Optional[str] = None,
        language: str = "en",
        personalize_resume: bool = True,
        voice_id: Optional[str] = None,
        avatar_mode: str = "voice_avatar",
        job_id: Optional[int] = None,
        resume_id: Optional[int] = None,
    ) -> MockInterviewSetupResponse:
        """
        Create a new behavioral interview session with deterministic question planning.
        Supports EN/FR/NL, role-weighting, and resume personalization.
        """
        effective_domain_id = domain_id or "behavioral"
        known_domains = {"behavioral", *(d["id"] for d in DOMAIN_DEFINITIONS)}
        if effective_domain_id not in known_domains:
            raise ValueError(f"Unknown domain '{effective_domain_id}'")
        lang = language.lower() if language in ("en", "fr", "nl") else "en"
        clean_role = role.strip() if (role and isinstance(role, str) and role.strip()) else None

        # Previous questions asked for this user (for variety without repeats)
        prev_asked = self._get_user_previous_question_ids(db, user_id, effective_domain_id)

        # Job-specific skill tags for biasing
        job_skill_tags: Set[str] = set()
        if job_id:
            job_skill_tags = self._get_job_skill_tags(db, job_id)

        # If personalize_resume is enabled and resume_id not explicitly given, try to find active resume
        if personalize_resume and not resume_id:
            active_res = get_active_resume(db, user_id)
            if active_res:
                resume_id = active_res.id

        domain_name = None
        if effective_domain_id != "behavioral":
            d_def = next((d for d in DOMAIN_DEFINITIONS if d["id"] == effective_domain_id), None)
            domain_name = d_def["title"] if d_def else effective_domain_id.replace("_", " ").title()

        # Build deterministic behavioral plan
        state = build_interview_plan(
            duration_minutes=duration_minutes,
            session_id=0,
            language=lang,
            role=clean_role,
            domain_name=domain_name,
            job_skill_tags=job_skill_tags,
            previously_asked_ids=prev_asked,
        )

        summary = plan_summary(state)

        # Persist session
        session = MockInterviewSession(
            user_id=user_id,
            domain_id=effective_domain_id,
            role=clean_role,
            difficulty=difficulty or "Standard",
            duration_minutes=duration_minutes,
            language=lang,
            interview_type="behavioral",
            personalize_resume=personalize_resume,
            voice_id=voice_id,
            avatar_mode=avatar_mode or "voice_avatar",
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

        # Localized domain title
        if lang == "fr":
            domain_title = "Entretien Comportemental & RH"
        elif lang == "nl":
            domain_title = "Gedrags- & HR-Interview"
        else:
            domain_title = "Behavioral & HR Mock Interview"

        return MockInterviewSetupResponse(
            session_id=session.id,
            domain_id=effective_domain_id,
            domain_title=domain_title,
            difficulty=difficulty or "Standard",
            duration_minutes=duration_minutes,
            language=lang,
            avatar_mode=session.avatar_mode,
            voice_id=session.voice_id,
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
        longest_pause_seconds: Optional[float] = None,
        time_to_first_word_seconds: Optional[float] = None,
    ) -> TurnSubmitResponse:
        """
        Process a submitted answer and determine the next action:
        1. Record the answer on the current turn with deterministic delivery metrics
        2. Run realtime follow-up classification (small LLM call or rubric check)
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

        # Context-aware acoustic normalization
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

        # Compute deterministic delivery metrics in code (not LLM)
        turn_metrics = compute_turn_metrics(
            text=canonical or transcript or "",
            duration_seconds=answer_dur,
            language=session.language or "en",
            longest_pause_seconds=longest_pause_seconds,
            time_to_first_word_seconds=time_to_first_word_seconds,
        )
        current_turn.wpm = turn_metrics.get("wpm")
        current_turn.filler_word_count = turn_metrics.get("filler_word_count")
        current_turn.longest_pause_seconds = turn_metrics.get("longest_pause_seconds")
        current_turn.time_to_first_word_seconds = turn_metrics.get("time_to_first_word_seconds")
        current_turn.i_vs_we_ratio = turn_metrics.get("i_vs_we_ratio")
        current_turn.delivery_metrics = turn_metrics

        record_answer(state, answer_dur, is_follow_up=current_turn.is_follow_up)

        # Realtime follow-up classification
        follow_up_triggered = False
        follow_up_verdict = {"strength": "adequate", "follow_up_suggested": False, "follow_up_focus": ""}

        if not current_turn.is_follow_up:  # At most 1 follow-up probe per question
            rubric = self._get_or_create_rubric(db, current_turn.question_id, current_turn.question_domain_id, session.language or "en")
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

        wrap_msg = WRAPUP_BY_LANG.get(session.language or "en", WRAPUP_BY_LANG["en"])

        # Check time budget or empty queue
        if state.is_time_expired or not state.question_queue:
            self._end_session_flow(db, session, state, "time_expired" if state.is_time_expired else "no_more_questions")
            return TurnSubmitResponse(
                turn_id=0,
                session_id=session.id,
                elapsed_seconds=state.elapsed_seconds,
                remaining_seconds=0.0,
                questions_asked=state.questions_asked,
                interview_complete=True,
                next_question=None,
                follow_up_triggered=False,
                message=wrap_msg,
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
                message=wrap_msg,
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
            next_question=self._slot_to_next_question(next_slot, session.voice_id),
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

            evaluation_records: List[Dict[str, Any]] = []
            turn_metrics_list: List[Dict[str, Any]] = []

            # Personalization context from resume if enabled
            resume_text = None
            if getattr(session, "personalize_resume", True) and session.resume_id:
                res_obj = db.query(Resume).filter(Resume.id == session.resume_id).first()
                if res_obj:
                    resume_text = res_obj.raw_text

            for turn in turns:
                is_intro = turn.question_id.startswith("intro_") or "introduction" in (turn.question_category or "").lower()
                is_wrapup = "wrapup" in turn.question_id.lower() or "questions_for_interviewer" in (turn.question_category or "").lower()
                q_type = "introductory" if is_intro else ("wrap_up" if is_wrapup else "behavioral")
                true_cat_id = (turn.question_category or "general").lower().replace(" ", "_")
                true_cat_name = turn.question_category or "Behavioral"

                canonical_text = turn.canonical_transcript or turn.transcript_text
                if not turn.transcript_text and not canonical_text:
                    eval_record = MockAnswerEvaluation(
                        turn_id=turn.id,
                        evaluation_error="No answer provided — turn was skipped",
                    )
                    db.add(eval_record)
                    evaluation_records.append({
                        "question_id": turn.question_id,
                        "category_id": true_cat_id,
                        "category_name": true_cat_name,
                        "topic": turn.question_topic,
                        "question_title": turn.question_title,
                        "question_type": q_type,
                        "turn_index": turn.turn_index,
                        "correctness": 0.0,
                        "completeness": 0.0,
                        "relevance": 0.0,
                        "clarity": 0.0,
                        "demonstrated_status": "not_demonstrated",
                        "evaluation_error": "No answer provided — turn was skipped",
                    })
                    continue

                rubric = self._get_or_create_rubric(db, turn.question_id, turn.question_domain_id, session.language or "en")
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
                    signals=key_concepts,
                    resume_text=resume_text,
                )

                # Ensure delivery metrics are collected
                if getattr(turn, "delivery_metrics", None):
                    turn_metrics_list.append(turn.delivery_metrics)
                else:
                    tm = compute_turn_metrics(
                        canonical_text or "",
                        turn.answer_duration_seconds or 60.0,
                        session.language or "en",
                        turn.longest_pause_seconds,
                        turn.time_to_first_word_seconds,
                    )
                    turn_metrics_list.append(tm)

                eval_obj = MockAnswerEvaluation(
                    turn_id=turn.id,
                    correctness=result.get("correctness"),
                    completeness=result.get("completeness"),
                    relevance=result.get("relevance"),
                    technical_depth=result.get("technical_depth"),
                    clarity=result.get("clarity"),
                    star_breakdown=result.get("star_breakdown"),
                    star_situation=result.get("star_situation") or (result.get("star_breakdown") or {}).get("situation"),
                    star_task=result.get("star_task") or (result.get("star_breakdown") or {}).get("task"),
                    star_action=result.get("star_action") or (result.get("star_breakdown") or {}).get("action"),
                    star_result=result.get("star_result") or (result.get("star_breakdown") or {}).get("result"),
                    star_evidence=result.get("star_evidence"),
                    stronger_version=result.get("stronger_version") or result.get("better_answer_notes"),
                    specificity_score=result.get("specificity_score"),
                    ownership_score=result.get("ownership_score"),
                    measurable_outcome_score=result.get("measurable_outcome_score"),
                    missing_concepts=result.get("missing_concepts", []),
                    incorrect_claims=result.get("incorrect_claims", []),
                    positive_points=result.get("positive_points", []),
                    improvement_points=result.get("improvement_points", []),
                    better_answer_notes=result.get("better_answer_notes"),
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

            # Aggregate scores deterministically
            categories_map = {rec["category_id"]: rec["category_name"] for rec in evaluation_records}
            sm_result = ai_compute_skill_matrix(
                evaluation_records,
                categories_map,
            )
            (
                skill_matrix,
                weak_areas,
                strengths,
                overall_score,
                tech_score,
                beh_score,
            ) = sm_result

            # Delivery snapshot across all answers
            delivery_snapshot = aggregate_session_delivery(turn_metrics_list)

            # Timeline data
            timeline_turns = []
            for turn in turns:
                t_eval = turn.evaluation
                timeline_turns.append({
                    "turn_index": turn.turn_index,
                    "question_id": turn.question_id,
                    "question_title": turn.question_title,
                    "competency": turn.question_category or "Behavioral",
                    "transcript": turn.canonical_transcript or turn.transcript_text or "",
                    "answer_duration_seconds": turn.answer_duration_seconds or 60.0,
                    "wpm": getattr(turn, "wpm", None),
                    "filler_word_count": getattr(turn, "filler_word_count", 0) or 0,
                    "longest_pause_seconds": getattr(turn, "longest_pause_seconds", 0.0) or 0.0,
                    "score": t_eval.correctness if t_eval and t_eval.correctness is not None else 0.5,
                    "star_verdict": getattr(t_eval, "star_verdict", None) if t_eval else None,
                    "positive_points": t_eval.positive_points if t_eval else [],
                    "improvement_points": t_eval.improvement_points if t_eval else [],
                })
            timeline = build_session_timeline_data(timeline_turns, total_duration_minutes=session.duration_minutes)

            # Action plan linking to HR prep
            action_plan = generate_behavioral_action_plan(weak_areas, language=session.language or "en")

            # Recommendations
            recommendations = generate_recommendations(
                weak_areas,
                session.domain_id,
                {"categories": [{"id": k, "name": v} for k, v in categories_map.items()]},
                weak_area_details=sm_result.weak_area_details,
            )

            # Headline strengths and improvements
            headline_strengths = strengths[:3]
            headline_improvements = weak_areas[:3]
            competency_scores = {
                (entry.get("category_id") or entry.get("category_name")): entry.get("score")
                for entry in skill_matrix
                if isinstance(entry, dict)
            }

            assessment = MockInterviewAssessment(
                session_id=session_id,
                overall_score=overall_score,
                skill_matrix={
                    "entries": skill_matrix,
                    "behavioral_score": overall_score,
                    "strengths": strengths,
                    "weak_areas": weak_areas,
                    "weak_area_details": sm_result.weak_area_details,
                    "strength_details": sm_result.strength_details,
                    "questions_asked": sm_result.questions_asked,
                    "questions_answered": sm_result.questions_answered,
                },
                weak_areas=weak_areas,
                recommendations=recommendations,
                delivery_summary=delivery_snapshot,
                competency_scores=competency_scores,
                timeline_data=timeline,
                action_plan=action_plan,
                summary_text=self._build_summary_text(
                    overall_score=overall_score,
                    weak_areas=weak_areas,
                    question_count=sm_result.questions_answered,
                    technical_score=None,
                    behavioral_score=overall_score,
                    unassessed_domains=None,
                ),
                ai_model_used=evaluation_records[0].get("ai_model_used") if evaluation_records else "deterministic",
            )
            db.add(assessment)

            session.evaluation_status = "completed"
            db.commit()
            logger.info(f"Post-interview behavioral evaluation complete for session {session_id}: overall={overall_score}")

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
            is_intro = turn.question_id.startswith("intro_") or "introduction" in (turn.question_category or "").lower()
            is_wrapup = "wrapup" in turn.question_id.lower() or "questions_for_interviewer" in (turn.question_category or "").lower()
            q_type = "introductory" if is_intro else ("wrap_up" if is_wrapup else "behavioral")

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
                category=turn.question_category or "Behavioral",
                topic=turn.question_topic or "Behavioral",
                difficulty=turn.question_difficulty or "Standard",
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
                star_evidence=getattr(ev, "star_evidence", None) if ev else None,
                star_verdict=getattr(ev, "star_verdict", None) if ev else None,
                wpm=getattr(turn, "wpm", None),
                filler_word_count=getattr(turn, "filler_word_count", None),
                longest_pause_seconds=getattr(turn, "longest_pause_seconds", None),
                i_vs_we_ratio=getattr(turn, "i_vs_we_ratio", None),
                missing_concepts=ev.missing_concepts or [] if ev else [],
                incorrect_claims=ev.incorrect_claims or [] if ev else [],
                positive_points=ev.positive_points or [] if ev else [],
                improvement_points=ev.improvement_points or [] if ev else [],
                better_answer_notes=getattr(ev, "stronger_version", None) or (ev.better_answer_notes if ev else None),
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
            technical_score=tech_score,
            behavioral_score=beh_score if beh_score is not None else (assessment.overall_score or 0.0),
            evaluation_status=session.evaluation_status,
            summary_text=assessment.summary_text,
            headline_strengths=getattr(assessment, "headline_strengths", None) or strengths[:3],
            headline_improvements=getattr(assessment, "headline_improvements", None) or (assessment.weak_areas or [])[:3],
            delivery_snapshot=getattr(assessment, "delivery_snapshot", None),
            timeline_data=getattr(assessment, "timeline_data", None) or [],
            action_plan=getattr(assessment, "action_plan", None) or [],
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
            is_intro = current_turn.question_id.startswith("intro_") or "introduction" in (current_turn.question_category or "").lower()
            is_wrapup = "wrapup" in current_turn.question_id.lower() or "questions_for_interviewer" in (current_turn.question_category or "").lower()
            q_type = "introductory" if is_intro else ("wrap_up" if is_wrapup else "behavioral")
            tts = self._build_tts_text(current_turn.question_title, current_turn.is_follow_up, current_turn.follow_up_focus)

            current_question = NextQuestionItem(
                question_id=current_turn.question_id,
                question_title=current_turn.question_title,
                domain_id=current_turn.question_domain_id,
                category=current_turn.question_category or "Behavioral",
                topic=current_turn.question_topic or "Behavioral",
                difficulty=current_turn.question_difficulty or "Standard",
                is_follow_up=current_turn.is_follow_up,
                follow_up_focus=current_turn.follow_up_focus,
                question_type=q_type,
                expected_duration_seconds=getattr(current_turn, "expected_duration_seconds", 90) or 90,
                tts_text=tts,
                interviewer_name="Alex Mercer",
            )

        title = "Behavioral & HR Interview" if session.domain_id == "behavioral" else domain_def.get("title", session.domain_id)

        return SessionStateResponse(
            session_id=session_id,
            status=session.status,
            domain_id=session.domain_id,
            domain_title=title,
            difficulty=session.difficulty,
            duration_minutes=session.duration_minutes,
            language=session.language or "en",
            avatar_mode=session.avatar_mode or "voice_avatar",
            voice_id=session.voice_id,
            elapsed_seconds=state.elapsed_seconds,
            remaining_seconds=state.remaining_seconds,
            questions_asked=len([t for t in session.turns if t.answered_at]),
            current_question=current_question,
            evaluation_status=session.evaluation_status,
            started_at=session.started_at,
            ended_at=session.ended_at,
        )

    # ------------------------------------------------------------------
    # Delete Session
    # ------------------------------------------------------------------

    def delete_session(
        self,
        db: Session,
        session_id: int,
        user_id: int,
    ) -> bool:
        """Permanently delete an interview session and all associated turns/evaluations."""
        session = self._get_session_for_user(db, session_id, user_id)
        for turn in list(session.turns):
            if turn.evaluation:
                db.delete(turn.evaluation)
            db.delete(turn)
        if session.assessment:
            db.delete(session.assessment)
        db.delete(session)
        db.commit()
        return True

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

    def _slot_to_next_question(self, slot: QuestionSlot, voice_id: Optional[str] = None) -> NextQuestionItem:
        tts = slot.tts_text or self._build_tts_text(slot.title, slot.is_follow_up, slot.follow_up_focus)

        return NextQuestionItem(
            question_id=slot.question_id,
            question_title=slot.title,
            domain_id=getattr(slot, "domain_id", "behavioral"),
            category=getattr(slot, "category_name", getattr(slot, "competency_label", "Behavioral")),
            topic=getattr(slot, "topic", getattr(slot, "competency_label", "Behavioral")),
            difficulty=getattr(slot, "difficulty", "Standard"),
            competency=getattr(slot, "competency", None),
            competency_label=getattr(slot, "competency_label", None),
            is_follow_up=slot.is_follow_up,
            follow_up_focus=slot.follow_up_focus,
            question_type=getattr(slot, "question_type", "behavioral"),
            expected_duration_seconds=getattr(slot, "expected_duration_seconds", getattr(slot, "estimated_seconds", 90)),
            tts_text=tts,
            interviewer_name="Alex Mercer",
        )

    def _build_tts_text(self, title: str, is_follow_up: bool, focus: Optional[str]) -> str:
        """Build natural-sounding text for TTS playback."""
        if is_follow_up and focus:
            return f"Thank you. Let me follow up on that. Could you share more about {focus}?"
        # Clean markdown from title for TTS
        clean = title.replace("**", "").replace("*", "").replace("`", "").replace("#", "")
        return clean

    def _get_or_create_rubric(
        self,
        db: Session,
        question_id: str,
        domain_id: str,
        language: str = "en",
    ) -> MockQuestionRubric:
        """Get cached rubric or create it from question content (signals / heuristic extraction)."""
        existing = db.query(MockQuestionRubric).filter(
            MockQuestionRubric.question_id == question_id,
            MockQuestionRubric.domain_id == domain_id,
        ).first()
        if existing:
            return existing

        key_concepts = []
        extraction_method = "signals"

        # Check behavioral question bank first
        try:
            beh_questions = load_behavioral_questions(language)
            b_match = next((q for q in beh_questions if q.get("id") == question_id), None)
            if b_match and b_match.get("signals"):
                key_concepts = b_match.get("signals", [])
        except Exception as e:
            logger.warning(f"Could not load behavioral rubric from question bank: {e}")

        if not key_concepts:
            # Fallback to domain questions if applicable
            try:
                questions = interview_prep_service._load_domain_questions(domain_id)
                q_data = next((q for q in questions if q.get("id") == question_id), None)
                if q_data:
                    content = q_data.get("content") or q_data.get("markdown_content") or ""
                    key_concepts = extract_key_concepts_heuristic(q_data.get("title", ""), content)
                    extraction_method = "heuristic"
            except Exception:
                pass

        rubric = MockQuestionRubric(
            question_id=question_id,
            domain_id=domain_id,
            key_concepts=key_concepts,
            extraction_method=extraction_method,
        )
        db.add(rubric)
        try:
            db.flush()
        except Exception:
            db.rollback()
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
