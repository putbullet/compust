"""
Unit tests for the Behavioral Mock Interview Engine, Metrics, and Evaluation.
Tests question selection, competency coverage, role weighting, time budgeting,
pure-Python delivery metrics, grounded STAR evaluation fixtures, and timeline data generation.
Zero external dependencies required (no LLM, no GPU, no audio hardware).
"""

import pytest
from src.app.services.mock_interview_engine import (
    InterviewState,
    QuestionSlot,
    build_interview_plan,
    load_behavioral_questions,
    pop_next_question,
    record_answer,
    can_add_follow_up,
    build_follow_up_slot,
    plan_summary,
    GREETINGS_BY_LANG,
    WRAPUP_BY_LANG,
)
from src.app.services.interview_metrics import (
    compute_turn_metrics,
    count_filler_words,
    calculate_wpm,
    compute_pronoun_ratio,
    aggregate_session_delivery,
)
from src.app.services.mock_interview_ai import (
    heuristic_star_evaluation,
    build_session_timeline_data,
    generate_behavioral_action_plan,
)


class TestBehavioralInterviewEngine:

    def test_question_bank_loading_multilingual(self):
        """Verify question banks load with at least 60 questions for EN, FR, NL."""
        en_questions = load_behavioral_questions("en")
        fr_questions = load_behavioral_questions("fr")
        nl_questions = load_behavioral_questions("nl")

        assert len(en_questions) >= 60, f"Expected >=60 questions for EN, got {len(en_questions)}"
        assert len(fr_questions) >= 60, f"Expected >=60 questions for FR, got {len(fr_questions)}"
        assert len(nl_questions) >= 60, f"Expected >=60 questions for NL, got {len(nl_questions)}"

        # Verify key metadata exists on all questions
        for q in en_questions:
            assert "id" in q
            assert "competency" in q
            assert "question" in q
            assert "signals" in q
            assert "expected_duration_seconds" in q

    def test_duration_budget_and_question_count(self):
        """Verify that question count scales appropriately with duration (5/10/15/20 min)."""
        plan_5 = build_interview_plan(duration_minutes=5, language="en")
        plan_10 = build_interview_plan(duration_minutes=10, language="en")
        plan_15 = build_interview_plan(duration_minutes=15, language="en")
        plan_20 = build_interview_plan(duration_minutes=20, language="en")

        assert plan_5.total_budget_seconds == 300
        assert plan_10.total_budget_seconds == 600
        assert plan_15.total_budget_seconds == 900
        assert plan_20.total_budget_seconds == 1200

        # Question counts should increase monotonically
        count_5 = len(plan_5.question_queue)
        count_10 = len(plan_10.question_queue)
        count_15 = len(plan_15.question_queue)
        count_20 = len(plan_20.question_queue)

        assert 3 <= count_5 <= 4
        assert count_5 <= count_10 <= count_15 <= count_20

    def test_opening_and_closing_structure(self):
        """Verify that every interview starts with an introduction and ends with questions for interviewer."""
        for lang in ("en", "fr", "nl"):
            plan = build_interview_plan(duration_minutes=15, language=lang)
            slots = plan.question_queue

            # First slot must be introductory
            assert slots[0].competency == "introduction"
            assert slots[0].question_type == "introductory"
            assert GREETINGS_BY_LANG[lang] in slots[0].tts_text

            # Last slot must be wrap up
            assert slots[-1].competency == "questions_for_interviewer"
            assert slots[-1].question_type == "wrap_up"

    def test_role_weighting(self):
        """Verify that providing a target role weights competencies toward that role."""
        leadership_role = "Engineering Manager"
        plan_lead = build_interview_plan(duration_minutes=20, role=leadership_role)

        lead_competencies = {"leadership", "conflict", "feedback", "pressure", "decision_making"}
        lead_slots = [s for s in plan_lead.question_queue if s.competency in lead_competencies]

        assert len(lead_slots) >= 2, "Expected leadership competencies to be prioritized for Engineering Manager role"

    def test_blank_role_first_class_path(self):
        """Verify that leaving target role blank is a first-class path with a balanced mix."""
        plan_none = build_interview_plan(duration_minutes=15, role=None)
        plan_empty = build_interview_plan(duration_minutes=15, role="   ")

        assert plan_none.target_role is None
        assert plan_empty.target_role is None
        assert len(plan_none.question_queue) >= 4
        assert len(plan_empty.question_queue) >= 4

    def test_no_repeats_in_session(self):
        """Verify no duplicate question IDs exist in a single interview plan."""
        plan = build_interview_plan(duration_minutes=20)
        q_ids = [s.question_id for s in plan.question_queue]
        assert len(q_ids) == len(set(q_ids)), "Duplicate question IDs found in interview plan"

    def test_spaced_repetition_avoidance(self):
        """Verify that recently asked question IDs are biased away from selection."""
        seen = {"beh_intro_01", "beh_lead_01", "beh_team_01", "beh_prob_01"}
        plan = build_interview_plan(duration_minutes=15, previously_asked_ids=seen)
        selected_ids = {s.question_id for s in plan.question_queue}

        # Should not select previously asked questions when plenty of alternatives exist
        assert "beh_lead_01" not in selected_ids
        assert "beh_team_01" not in selected_ids

    def test_follow_up_capping_and_bounds(self):
        """Verify that follow-up probes are bounded to at most 1 per primary question."""
        slot = QuestionSlot(
            question_id="beh_team_01",
            competency="teamwork",
            competency_label="Teamwork & Collaboration",
            title="Tell me about a time you collaborated with a difficult stakeholder.",
            follow_up_probes=["Could you share more about the specific steps you took?"],
            expected_duration_seconds=90,
        )
        state = InterviewState(
            session_id=1,
            duration_minutes=15,
            total_budget_seconds=900,
            elapsed_seconds=120.0,
            current_question_slot=slot,
            follow_up_count_this_question=0,
            follow_up_count_total=0,
        )

        assert can_add_follow_up(state) is True

        # Once a follow-up is added, question cannot have another
        state.follow_up_count_this_question = 1
        assert can_add_follow_up(state) is False

    def test_state_serialization_round_trip(self):
        """Verify InterviewState to_dict() and from_dict() round trip losslessly."""
        plan = build_interview_plan(duration_minutes=10, language="fr", role="Tech Lead")
        pop_next_question(plan)
        record_answer(plan, answer_duration_seconds=80.0)

        data = plan.to_dict()
        restored = InterviewState.from_dict(data)

        assert restored.session_id == plan.session_id
        assert restored.duration_minutes == plan.duration_minutes
        assert restored.language == plan.language
        assert restored.target_role == plan.target_role
        assert restored.elapsed_seconds == plan.elapsed_seconds
        assert len(restored.question_queue) == len(plan.question_queue)
        assert len(restored.asked_question_ids) == len(plan.asked_question_ids)


class TestDeliveryMetricsCalculators:

    def test_wpm_calculation(self):
        """Verify words-per-minute calculator handles normal, fast, and edge cases."""
        text_120_words = "word " * 120
        # 120 words in 60 seconds = 120 WPM
        wpm = calculate_wpm(text_120_words, duration_seconds=60.0)
        assert 118 <= wpm <= 122

        # 0 seconds or empty text
        assert calculate_wpm("", 60.0) == 0.0
        assert calculate_wpm(text_120_words, 0.0) == 0.0

    def test_multilingual_filler_words(self):
        """Verify language-aware filler word counting for EN, FR, and NL."""
        en_text = "Um, so basically like I think we should, you know, deploy this."
        fr_text = "Euh, ben en fait du coup je pense que genre c'est bon."
        nl_text = "Nou, zeg maar eigenlijk denk ik dat we dus wel kunnen starten."

        en_fillers = count_filler_words(en_text, language="en")
        fr_fillers = count_filler_words(fr_text, language="fr")
        nl_fillers = count_filler_words(nl_text, language="nl")

        assert en_fillers["filler_count"] >= 3
        assert fr_fillers["filler_count"] >= 3
        assert nl_fillers["filler_count"] >= 3

    def test_pronoun_ratio(self):
        """Verify first-person singular 'I' vs collective 'we' ratio calculation."""
        team_focused = "We planned the release together, and our team delivered it on schedule."
        ownership_focused = "I designed the architecture, wrote the code, and I deployed the service."

        ratio_team = compute_pronoun_ratio(team_focused, language="en")
        ratio_owner = compute_pronoun_ratio(ownership_focused, language="en")

        assert ratio_team["we_count"] > ratio_team["i_count"]
        assert ratio_owner["i_count"] > ratio_owner["we_count"]

    def test_aggregate_session_delivery(self):
        """Verify aggregation of delivery metrics across an entire session."""
        turn_metrics = [
            {"wpm": 130.0, "filler_word_count": 2, "filler_rate_pct": 1.5, "longest_pause_seconds": 1.2, "i_vs_we_ratio": 1.5},
            {"wpm": 140.0, "filler_word_count": 4, "filler_rate_pct": 2.2, "longest_pause_seconds": 2.0, "i_vs_we_ratio": 2.0},
        ]
        agg = aggregate_session_delivery(turn_metrics)

        assert agg["average_wpm"] == 135.0
        assert agg["total_filler_words"] == 6
        assert agg["max_longest_pause"] == 2.0
        assert agg["pace_assessment"] in ("Ideal speaking pace", "Speaking slightly fast", "Speaking slightly slow")


class TestGroundedSTAREvaluation:

    def test_strong_star_answer(self):
        """Verify heuristic STAR evaluation identifies S, T, A, R with grounded transcript evidence."""
        strong_answer = (
            "In my previous role at Acme Corp, we experienced frequent database timeouts during peak hours. "
            "My responsibility was to resolve the query bottlenecks and stabilize performance within two weeks. "
            "I investigated the slow query logs, identified missing indexes on the users table, and refactored the ORM queries. "
            "As a result, API response times improved by 45%, and server CPU usage decreased by 30% without any further downtime."
        )
        res = heuristic_star_evaluation(
            question_title="Tell me about a challenging technical problem you solved.",
            transcript=strong_answer,
            signals=["concrete situation", "ownership of actions", "measurable outcome"],
        )

        breakdown = res["star_breakdown"]
        evidence = res["star_evidence"]

        assert breakdown["situation"] in ("present", "partial")
        assert breakdown["task"] in ("present", "partial")
        assert breakdown["action"] in ("present", "partial")
        assert breakdown["result"] == "present"

        # Evidence quotes must be grounded verbatim substrings of the transcript
        assert evidence["result"] in strong_answer
        assert res["correctness"] >= 0.70

    def test_rambling_answer_missing_result(self):
        """Verify answer without a measurable result is flagged as missing result."""
        answer_without_result = (
            "Well, once we had an issue with customer onboarding. It was really complicated and everyone was talking about it. "
            "I attended a lot of meetings and tried to talk to different people about what we might do."
        )
        res = heuristic_star_evaluation(
            question_title="Describe a project where you took initiative.",
            transcript=answer_without_result,
            signals=["clear result", "metrics", "resolution"],
        )

        breakdown = res["star_breakdown"]
        assert breakdown["result"] == "missing"
        assert len(res["improvement_points"]) >= 1

    def test_stronger_version_contains_placeholders_never_fabricates(self):
        """Verify stronger version suggestions use explicit [placeholders] for missing data without fabricating facts."""
        thin_answer = "I fixed the bug when production went down."
        res = heuristic_star_evaluation(
            question_title="How do you handle production incidents?",
            transcript=thin_answer,
            signals=["root cause analysis", "prevention"],
        )

        stronger = res["better_answer_notes"]
        assert "[" in stronger and "]" in stronger, "Expected bracketed placeholders for missing details"


class TestTimelineAndActionPlan:

    def test_timeline_chart_generation(self):
        """Verify minute-by-minute timeline generation with segment positions, scores, and pause markers."""
        turns = [
            {
                "turn_index": 0,
                "question_id": "beh_intro_01",
                "question_title": "Tell me about yourself.",
                "competency": "Introduction",
                "transcript": "Hello, I am a software engineer with 5 years experience.",
                "answer_duration_seconds": 60.0,
                "wpm": 125.0,
                "filler_word_count": 1,
                "longest_pause_seconds": 1.2,
                "score": 0.85,
                "star_verdict": "Complete STAR",
            },
            {
                "turn_index": 1,
                "question_id": "beh_lead_01",
                "question_title": "Describe a leadership experience.",
                "competency": "Leadership",
                "transcript": "I led a cross-functional team to deliver our quarterly release.",
                "answer_duration_seconds": 120.0,
                "wpm": 115.0,
                "filler_word_count": 3,
                "longest_pause_seconds": 3.8,  # Long pause marker
                "score": 0.70,
                "star_verdict": "Action-Heavy",
            },
        ]

        timeline = build_session_timeline_data(turns, total_duration_minutes=15)
        assert len(timeline) == 2

        # Check turn 0
        t0 = timeline[0]
        assert t0["minute_start"] == 0.0
        assert t0["quality_band"].lower() in ("strong", "moderate")
        assert t0["has_long_pause"] is False

        # Check turn 1
        t1 = timeline[1]
        assert t1["minute_start"] >= 1.0
        assert t1["has_long_pause"] is True  # 3.8s > 2.5s threshold

    def test_behavioral_action_plan_links(self):
        """Verify action plan provides actionable practice recommendations with links to Interview Prep."""
        weak_areas = ["Conflict Resolution", "Receiving Feedback"]
        plan = generate_behavioral_action_plan(weak_areas, language="en")

        assert len(plan) == 2
        for item in plan:
            assert "competency" in item
            assert "action" in item
            assert "prep_link" in item
            assert item["prep_link"].startswith("/interview-prep")
