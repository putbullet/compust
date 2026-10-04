"""
Unit tests for the Deterministic Mock Interview Engine (src/app/services/mock_interview_engine.py).
Tests question allocation, time budgeting, adaptive rescheduling, and follow-up constraints
WITHOUT requiring LLM, Ollama, database, or audio hardware.
"""

import pytest
from src.app.services.mock_interview_engine import (
    InterviewState,
    QuestionSlot,
    build_interview_plan,
    pop_next_question,
    record_answer,
    can_add_follow_up,
    build_follow_up_slot,
    plan_summary,
    _allocate_slots,
    _trim_to_budget,
    _estimate_question_seconds,
)


def _make_dummy_questions(counts_per_category: dict) -> list[dict]:
    """Helper to create dummy question bank with known distribution."""
    questions = []
    idx = 1
    for cat_id, count in counts_per_category.items():
        for i in range(count):
            diff = ["Fundamental", "Intermediate", "Advanced"][i % 3]
            questions.append({
                "id": f"q_{idx}",
                "slug": f"question-{idx}",
                "title": f"Question {idx} in {cat_id}",
                "domain_id": "data_engineering",
                "category_id": cat_id,
                "category_name": cat_id.replace("_", " ").title(),
                "topic": f"Topic {i % 5}",
                "difficulty": diff,
                "content": f"Answer content for question {idx}",
                "tags": [cat_id, diff.lower(), "python" if i % 2 == 0 else "sql"],
            })
            idx += 1
    return questions


class TestDeterministicInterviewEngine:

    def test_time_budget_calculation(self):
        """Test that interview budget is calculated accurately from minutes."""
        questions = _make_dummy_questions({"sql": 50, "spark": 30})
        state_10 = build_interview_plan(questions, "data_engineering", "Mixed", duration_minutes=10)
        state_20 = build_interview_plan(questions, "data_engineering", "Mixed", duration_minutes=20)
        state_45 = build_interview_plan(questions, "data_engineering", "Mixed", duration_minutes=45)

        assert state_10.total_budget_seconds == 600
        assert state_20.total_budget_seconds == 1200
        assert state_45.total_budget_seconds == 2700

    def test_subdomain_proportional_allocation_with_floor(self):
        """
        Verify that subdomains are allocated proportionally, but every subdomain
        gets at least 1 slot (floor=1) if the budget allows.
        """
        category_counts = {
            "massive_category": 200,
            "medium_category": 50,
            "tiny_category": 5,
        }
        questions = _make_dummy_questions(category_counts)
        state = build_interview_plan(questions, "data_engineering", "Mixed", duration_minutes=30)

        assigned_categories = {slot.category_id for slot in state.question_queue}
        # Floor guarantee: tiny_category must get at least 1 question
        assert "tiny_category" in assigned_categories
        assert "medium_category" in assigned_categories
        assert "massive_category" in assigned_categories

        # Massive category should have significantly more slots than tiny category
        massive_count = sum(1 for s in state.question_queue if s.category_id == "massive_category")
        tiny_count = sum(1 for s in state.question_queue if s.category_id == "tiny_category")
        assert massive_count >= tiny_count

    def test_difficulty_filtering(self):
        """Verify questions match requested difficulty level."""
        questions = _make_dummy_questions({"cat1": 30, "cat2": 30})

        state_fund = build_interview_plan(questions, "data_engineering", "Fundamental", duration_minutes=15)
        for slot in state_fund.question_queue:
            assert slot.difficulty == "Fundamental"

        state_adv = build_interview_plan(questions, "data_engineering", "Advanced", duration_minutes=15)
        for slot in state_adv.question_queue:
            assert slot.difficulty == "Advanced"

    def test_spaced_repetition_avoidance(self):
        """Verify that previously asked question IDs are excluded when possible."""
        questions = _make_dummy_questions({"cat1": 20, "cat2": 20})
        prev_asked = {"q_1", "q_2", "q_3", "q_4", "q_5"}

        state = build_interview_plan(
            questions,
            "data_engineering",
            "Mixed",
            duration_minutes=15,
            previously_asked_ids=prev_asked,
        )

        queued_ids = {s.question_id for s in state.question_queue}
        # None of the previously asked questions should be in the queue
        assert queued_ids.isdisjoint(prev_asked)

    def test_weak_area_biasing(self):
        """Verify that weak categories receive higher allocation weights."""
        counts = {"cat_weak": 30, "cat_strong": 30}
        questions = _make_dummy_questions(counts)

        # Baseline without weak areas
        state_neutral = build_interview_plan(questions, "data_engineering", "Mixed", duration_minutes=20)
        # Biased towards cat_weak
        state_biased = build_interview_plan(
            questions,
            "data_engineering",
            "Mixed",
            duration_minutes=20,
            weak_category_ids={"cat_weak"},
        )

        weak_count_neutral = sum(1 for s in state_neutral.question_queue if s.category_id == "cat_weak")
        weak_count_biased = sum(1 for s in state_biased.question_queue if s.category_id == "cat_weak")

        assert weak_count_biased >= weak_count_neutral

    def test_follow_up_capping_rules(self):
        """
        Verify strict bounds on adaptive follow-ups:
        - Max 1 follow-up per primary question
        - Max 3 follow-ups per session total
        - No follow-ups if time remaining is too low
        """
        slot = QuestionSlot(
            question_id="q_1",
            domain_id="data_engineering",
            category_id="cat1",
            category_name="Cat 1",
            topic="Topic 1",
            title="Q1 Title",
            difficulty="Intermediate",
            estimated_seconds=120,
        )
        state = InterviewState(
            session_id=1,
            domain_id="data_engineering",
            difficulty="Mixed",
            duration_minutes=20,
            total_budget_seconds=1200,
            elapsed_seconds=100.0,
            current_question_slot=slot,
            follow_up_count_this_question=0,
            follow_up_count_total=0,
        )

        # Initially allowed
        assert can_add_follow_up(state) is True

        # Rule 1: Question already had follow-up -> False
        state.follow_up_count_this_question = 1
        assert can_add_follow_up(state) is False

        # Reset question follow-up
        state.follow_up_count_this_question = 0

        # Rule 2: Session cap reached (3) -> False
        state.follow_up_count_total = 3
        assert can_add_follow_up(state) is False

        # Rule 3: Less than follow-up budget remaining -> False
        state.follow_up_count_total = 1
        state.elapsed_seconds = 1170.0  # only 30s remaining
        assert can_add_follow_up(state) is False

    def test_build_follow_up_slot_preserves_parent_context(self):
        """Verify follow up question slot properly references parent question."""
        parent_slot = QuestionSlot(
            question_id="parent_101",
            domain_id="data_engineering",
            category_id="distributed_systems",
            category_name="Distributed Systems",
            topic="Hadoop",
            title="Explain MapReduce architecture",
            difficulty="Intermediate",
            estimated_seconds=120,
        )
        state = InterviewState(
            session_id=1,
            domain_id="data_engineering",
            difficulty="Mixed",
            duration_minutes=20,
            total_budget_seconds=1200,
            current_question_slot=parent_slot,
        )

        follow_up = build_follow_up_slot(state, follow_up_focus="Explain shuffle phase bottleneck")

        assert follow_up.is_follow_up is True
        assert follow_up.question_id == "parent_101"
        assert follow_up.category_id == "distributed_systems"
        assert follow_up.follow_up_focus == "Explain shuffle phase bottleneck"
        assert "shuffle phase bottleneck" in follow_up.title

    def test_pop_and_record_answer_progress(self):
        """Test pop_next_question and record_answer state updates."""
        questions = _make_dummy_questions({"cat1": 10, "cat2": 10})
        state = build_interview_plan(questions, "data_engineering", "Fundamental", duration_minutes=10)

        initial_count = len(state.question_queue)
        first_q = pop_next_question(state)

        assert first_q is not None
        assert state.current_question_slot == first_q
        assert first_q.question_id in state.asked_question_ids
        assert len(state.question_queue) == initial_count - 1

        # Record answer (takes 90s + 15s overhead = 105s elapsed)
        record_answer(state, answer_duration_seconds=90.0, is_follow_up=False)

        assert state.elapsed_seconds == 105.0
        assert state.remaining_seconds == 600.0 - 105.0
        assert state.questions_asked == 1

    def test_state_serialization_round_trip(self):
        """Test that InterviewState to_dict() and from_dict() maintain 100% fidelity."""
        questions = _make_dummy_questions({"sql": 10, "spark": 10})
        original = build_interview_plan(questions, "data_engineering", "Intermediate", duration_minutes=20)
        pop_next_question(original)
        record_answer(original, 75.0, is_follow_up=False)

        data = original.to_dict()
        restored = InterviewState.from_dict(data)

        assert restored.session_id == original.session_id
        assert restored.domain_id == original.domain_id
        assert restored.difficulty == original.difficulty
        assert restored.total_budget_seconds == original.total_budget_seconds
        assert restored.elapsed_seconds == original.elapsed_seconds
        assert restored.remaining_seconds == original.remaining_seconds
        assert restored.questions_asked == original.questions_asked
        assert restored.asked_question_ids == original.asked_question_ids
        assert len(restored.question_queue) == len(original.question_queue)
