"""
Deterministic Interview Engine for AI Mock Interview & Skills Assessment.

DESIGN PRINCIPLE: This module contains ZERO LLM calls, ZERO STT/TTS, ZERO I/O.
All scheduling, timing, and state management is pure deterministic Python.
The AI layer (follow-up classification, post-interview evaluation) lives in
mock_interview_ai.py and is called by the API layer — not here.

This separation means:
  - Unit tests require no mocks of Ollama, faster-whisper, or DB
  - The transport layer (turn-based voice, future Pipecat) can be swapped freely
  - The engine's behavior is fully reproducible and testable from test inputs alone
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("compust.mock_interview.engine")


# ---------------------------------------------------------------------------
# Time budget constants (seconds per difficulty)
# Derived from question bank's content length heuristic (Phase 0 confirmed:
# no explicit question-type field, so we use difficulty as proxy).
# ---------------------------------------------------------------------------

DIFFICULTY_TIME_BUDGET: Dict[str, int] = {
    "Fundamental": 90,
    "Intermediate": 120,
    "Advanced": 180,
    "Mixed": 120,   # fallback average
}

# Buffer added per question for transition, clarification, etc.
PER_QUESTION_OVERHEAD_SECONDS = 15

# Maximum follow-ups: 1 per question, 3 per session total
MAX_FOLLOW_UPS_PER_QUESTION = 1
MAX_FOLLOW_UPS_PER_SESSION = 3

# Difficulty levels (for filter and mixed-mode selection)
DIFFICULTY_LEVELS = ["Fundamental", "Intermediate", "Advanced"]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class QuestionSlot:
    """A single scheduled question slot in the interview plan."""
    question_id: str
    domain_id: str
    category_id: str
    category_name: str
    topic: str
    title: str
    difficulty: str
    estimated_seconds: int
    is_follow_up: bool = False
    follow_up_focus: Optional[str] = None
    question_type: str = "technical"   # "introductory" | "technical" | "behavioral" | "scenario"
    tts_text: Optional[str] = None
    parent_question_id: Optional[str] = None


@dataclass
class InterviewState:
    """
    Single source of truth for a live interview session.
    Stored serialized in MockInterviewSession.interview_plan (JSON).
    """
    session_id: int
    domain_id: str
    difficulty: str
    duration_minutes: int
    total_budget_seconds: int

    # Planned queue — slots not yet asked
    question_queue: List[QuestionSlot] = field(default_factory=list)

    # Completed turns
    asked_question_ids: List[str] = field(default_factory=list)
    covered_category_ids: Set[str] = field(default_factory=set)

    # Timing
    started_at: Optional[datetime] = None
    elapsed_seconds: float = 0.0

    # Adaptive counters
    follow_up_count_this_question: int = 0
    follow_up_count_total: int = 0
    current_question_slot: Optional[QuestionSlot] = None

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self.total_budget_seconds - self.elapsed_seconds)

    @property
    def is_time_expired(self) -> bool:
        return self.remaining_seconds <= 0

    @property
    def questions_asked(self) -> int:
        return len(self.asked_question_ids)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dict for DB storage."""
        return {
            "session_id": self.session_id,
            "domain_id": self.domain_id,
            "difficulty": self.difficulty,
            "duration_minutes": self.duration_minutes,
            "total_budget_seconds": self.total_budget_seconds,
            "question_queue": [_slot_to_dict(s) for s in self.question_queue],
            "asked_question_ids": self.asked_question_ids,
            "covered_category_ids": list(self.covered_category_ids),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "elapsed_seconds": self.elapsed_seconds,
            "follow_up_count_this_question": self.follow_up_count_this_question,
            "follow_up_count_total": self.follow_up_count_total,
            "current_question_slot": _slot_to_dict(self.current_question_slot) if self.current_question_slot else None,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "InterviewState":
        """Deserialize from DB JSON storage."""
        state = cls(
            session_id=d["session_id"],
            domain_id=d["domain_id"],
            difficulty=d["difficulty"],
            duration_minutes=d["duration_minutes"],
            total_budget_seconds=d["total_budget_seconds"],
        )
        state.question_queue = [_dict_to_slot(s) for s in d.get("question_queue", [])]
        state.asked_question_ids = d.get("asked_question_ids", [])
        state.covered_category_ids = set(d.get("covered_category_ids", []))
        raw_started = d.get("started_at")
        state.started_at = datetime.fromisoformat(raw_started) if raw_started else None
        state.elapsed_seconds = d.get("elapsed_seconds", 0.0)
        state.follow_up_count_this_question = d.get("follow_up_count_this_question", 0)
        state.follow_up_count_total = d.get("follow_up_count_total", 0)
        raw_current = d.get("current_question_slot")
        state.current_question_slot = _dict_to_slot(raw_current) if raw_current else None
        return state


def _slot_to_dict(slot: QuestionSlot) -> Dict[str, Any]:
    return {
        "question_id": slot.question_id,
        "domain_id": slot.domain_id,
        "category_id": slot.category_id,
        "category_name": slot.category_name,
        "topic": slot.topic,
        "title": slot.title,
        "difficulty": slot.difficulty,
        "estimated_seconds": slot.estimated_seconds,
        "is_follow_up": slot.is_follow_up,
        "follow_up_focus": slot.follow_up_focus,
        "question_type": getattr(slot, "question_type", "technical"),
        "tts_text": getattr(slot, "tts_text", None),
        "parent_question_id": getattr(slot, "parent_question_id", None),
    }


def _dict_to_slot(d: Dict[str, Any]) -> QuestionSlot:
    return QuestionSlot(
        question_id=d["question_id"],
        domain_id=d["domain_id"],
        category_id=d["category_id"],
        category_name=d["category_name"],
        topic=d["topic"],
        title=d["title"],
        difficulty=d["difficulty"],
        estimated_seconds=d["estimated_seconds"],
        is_follow_up=d.get("is_follow_up", False),
        follow_up_focus=d.get("follow_up_focus"),
        question_type=d.get("question_type", "technical"),
        tts_text=d.get("tts_text"),
        parent_question_id=d.get("parent_question_id"),
    )


# ---------------------------------------------------------------------------
# Default curated behavioral questions pool
# ---------------------------------------------------------------------------

DEFAULT_BEHAVIORAL_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "beh_conflict_1",
        "category_id": "behavioral_teamwork",
        "category_name": "Teamwork & Conflict Resolution",
        "topic": "Technical Disagreements",
        "title": "Tell me about a time you had a technical disagreement with a teammate or engineering manager. How did you resolve it?",
        "estimated_seconds": 120,
    },
    {
        "id": "beh_failure_1",
        "category_id": "behavioral_failure",
        "category_name": "Failure & Blameless Learning",
        "topic": "Production Incidents",
        "title": "Describe a time when you caused or had to resolve a severe production outage or unexpected bug. What did you learn and what safeguards did you put in place?",
        "estimated_seconds": 120,
    },
    {
        "id": "beh_initiative_1",
        "category_id": "behavioral_initiative",
        "category_name": "Leadership & Initiative",
        "topic": "Technical Debt",
        "title": "Tell me about a time you proactively took the initiative to eliminate technical debt or improve system reliability without being asked.",
        "estimated_seconds": 120,
    },
    {
        "id": "beh_problem_solving_1",
        "category_id": "behavioral_problem_solving",
        "category_name": "Problem Solving & Architecture",
        "topic": "Complex Engineering",
        "title": "Walk me through a technically difficult engineering problem you encountered recently. What was your role and what architectural alternatives did you consider?",
        "estimated_seconds": 120,
    },
    {
        "id": "beh_adaptability_1",
        "category_id": "behavioral_adaptability",
        "category_name": "Adaptability & Fast Ramp-up",
        "topic": "Rapid Learning",
        "title": "Tell me about a time you had to learn a completely new framework, language, or system architecture under tight deadlines. How did you approach the learning curve?",
        "estimated_seconds": 120,
    },
    {
        "id": "beh_communication_1",
        "category_id": "behavioral_communication",
        "category_name": "Technical Communication",
        "topic": "Stakeholder Explanations",
        "title": "Can you describe a situation where you had to explain a complex technical architectural decision or trade-off to non-technical stakeholders or executives?",
        "estimated_seconds": 120,
    },
    {
        "id": "beh_project_1",
        "category_id": "behavioral_execution",
        "category_name": "Project Execution & Ownership",
        "topic": "End-to-End Ownership",
        "title": "Walk me through a complex engineering project you led or contributed significantly to. What was your personal responsibility, what trade-offs did you make, and what was the outcome?",
        "estimated_seconds": 120,
    },
    {
        "id": "beh_sec_incident_1",
        "category_id": "behavioral_security",
        "category_name": "Security Ownership & Incident Awareness",
        "topic": "Vulnerability Discovery",
        "title": "Tell me about a time when you identified a security issue or potential vulnerability. What did you do?",
        "estimated_seconds": 120,
    },
    {
        "id": "beh_intro_1",
        "category_id": "introduction",
        "category_name": "Introduction & Background",
        "topic": "Career Introduction",
        "title": "Could you tell me a little about yourself, your background, and what brings you to this interview?",
        "estimated_seconds": 75,
    },
]


def build_introductory_tts(
    domain_title: str,
    domain_id: str,
    role: Optional[str] = None,
    difficulty: str = "Intermediate",
) -> str:
    """Generate a realistic, professional interviewer introduction with natural variation."""
    clean_role = role.strip() if (role and isinstance(role, str) and role.strip()) else None
    role_str = f" for the {clean_role} position" if clean_role else ""
    domain_desc = {
        "data_engineering": "data engineering, including SQL, distributed systems, pipeline design, and data modeling",
        "security_engineering": "security engineering, including threat modeling, networking, application security, and incident response",
        "ai_tech_interview": "AI engineering, including machine learning foundations, RAG architectures, model evaluation, and LLM system design",
    }.get(domain_id, f"{domain_title} concepts and practical engineering scenarios")

    templates = [
        (
            f"Hello, welcome! It's good to have you here today. "
            f"We'll be doing a technical interview focused on {domain_title}{role_str}. "
            f"We'll cover {domain_desc}, along with practical engineering scenarios and behavioral experiences. "
            f"Some questions may include follow-ups depending on your answers. "
            f"There isn't anything you need to click while we're talking. "
            f"When I finish a question, the microphone will automatically listen for your response. "
            f"Let's get started. Could you begin by telling me a little about yourself and your background?"
        ),
        (
            f"Hi there, and welcome. Thank you for taking the time to speak with me today. "
            f"Our interview session will focus on {domain_title}{role_str} at the {difficulty} level. "
            f"We'll explore core technical concepts in {domain_desc}, as well as real-world engineering problem solving. "
            f"The microphone will activate automatically whenever I complete a question, so you can answer naturally at your own pace. "
            f"Let's begin: could you walk me through your background and what led you toward this path?"
        ),
        (
            f"Welcome! It's great to connect with you today. "
            f"Today's interview is centered on {domain_title}{role_str}. "
            f"We'll balance technical architecture, practical trade-offs, and behavioral engineering questions. "
            f"Whenever I finish speaking, the system will automatically start listening for your thoughts. "
            f"Let's get started: could you briefly introduce yourself and share the highlights of your technical journey?"
        ),
    ]

    return random.choice(templates)


def build_conversational_tts(
    title: str,
    question_type: str = "technical",
    is_follow_up: bool = False,
    focus: Optional[str] = None,
    turn_index: int = 1,
) -> str:
    """Build natural, conversational spoken text for the AI interviewer."""
    if is_follow_up and focus:
        return f"Thanks for explaining that. Let me probe a bit further on {focus}. How would you address that?"

    import re
    clean_title = re.sub(r"[*`#_]", "", title).strip()

    if question_type == "introductory":
        return clean_title

    if question_type == "behavioral":
        lead_ins = [
            "Let's shift gears to how you collaborate and solve problems in engineering teams. ",
            "I'd like to explore your practical engineering experiences. ",
            "Let's talk about real-world scenarios you've navigated in your career. ",
        ]
        lead_in = lead_ins[turn_index % len(lead_ins)]
        return f"{lead_in}{clean_title}"

    # Technical question lead-in
    lead_ins = [
        "Let's move on to the next topic. ",
        "Turning to another key area. ",
        "Let's discuss this technical scenario. ",
        "Here is our next technical question. ",
    ]
    lead_in = lead_ins[turn_index % len(lead_ins)] if turn_index > 1 else ""
    return f"{lead_in}{clean_title}"


# ---------------------------------------------------------------------------
# Core engine functions (pure logic — no I/O, no AI, no DB)
# ---------------------------------------------------------------------------

def build_interview_plan(
    domain_questions: List[Dict[str, Any]],
    domain_id: str,
    difficulty: str,
    duration_minutes: int,
    previously_asked_ids: Optional[Set[str]] = None,
    job_skill_tags: Optional[Set[str]] = None,
    weak_category_ids: Optional[Set[str]] = None,
    session_id: int = 0,
    role: Optional[str] = None,
    domain_title: Optional[str] = None,
    behavioral_questions: Optional[List[Dict[str, Any]]] = None,
    include_intro: bool = True,
    include_behavioral: bool = True,
) -> InterviewState:
    """
    Build a fully-scheduled interview plan with balanced technical & behavioral coverage.

    Algorithm:
    1. Filter questions by difficulty (or keep all for "Mixed")
    2. Compute per-category weights proportional to actual question count
    3. Allocate slots using proportional coverage with floor=1
    4. Select fresh questions avoiding previously_asked_ids
    5. Integrate natural introductory turn (Slot 0)
    6. Integrate behavioral question (Slot N-1)
    7. Assemble conversational TTS speech for each turn
    8. Trim queue to budget while preserving opening turn
    """
    previously_asked = previously_asked_ids or set()
    job_tags = {t.lower() for t in (job_skill_tags or set())}
    weak_cats = weak_category_ids or set()

    total_budget = duration_minutes * 60

    # Step 1: Filter questions by difficulty
    filtered = _filter_by_difficulty(domain_questions, difficulty)
    if not filtered:
        # Graceful degradation: if no questions match, use all
        filtered = domain_questions
        logger.warning(
            f"No questions matched difficulty '{difficulty}' in domain '{domain_id}'. "
            f"Using full bank ({len(domain_questions)} questions)."
        )

    # Step 2: Group by category and compute base weights
    category_groups: Dict[str, List[Dict[str, Any]]] = {}
    for q in filtered:
        cat_id = q.get("category_id") or q.get("category", "general")
        if cat_id not in category_groups:
            category_groups[cat_id] = []
        category_groups[cat_id].append(q)

    if not category_groups:
        return _empty_state(session_id, domain_id, difficulty, duration_minutes, total_budget)

    # Step 3: Calculate dedicated technical budget taking reserved intro and behavioral slots into account
    intro_budget = (75 + PER_QUESTION_OVERHEAD_SECONDS) if include_intro else 0
    beh_budget = (120 + PER_QUESTION_OVERHEAD_SECONDS) if (include_behavioral and duration_minutes >= 10) else 0
    tech_budget = max(60, total_budget - intro_budget - beh_budget)

    # Weighted allocation using dedicated tech_budget
    slots = _allocate_slots(
        category_groups,
        tech_budget,
        difficulty,
        job_tags,
        weak_cats,
    )

    # Step 4: Build technical question queue
    queue: List[QuestionSlot] = []
    for cat_id, num_slots in slots.items():
        pool = category_groups[cat_id]
        selected = _select_questions(pool, num_slots, previously_asked)
        for q in selected:
            est_seconds = _estimate_question_seconds(q)
            queue.append(QuestionSlot(
                question_id=q["id"],
                domain_id=domain_id,
                category_id=cat_id,
                category_name=q.get("category_name") or q.get("category", cat_id),
                topic=q.get("topic", "Core Concepts"),
                title=q["title"],
                difficulty=q.get("difficulty", difficulty),
                estimated_seconds=est_seconds,
                question_type="technical",
            ))

    # Shuffle so consecutive technical categories vary
    random.shuffle(queue)

    # Step 5: Integrate behavioral component
    if include_behavioral and duration_minutes >= 10:
        beh_pool = behavioral_questions or DEFAULT_BEHAVIORAL_QUESTIONS
        fresh_beh = [b for b in beh_pool if b["id"] not in previously_asked]
        selected_beh = random.choice(fresh_beh if fresh_beh else beh_pool)
        beh_slot = QuestionSlot(
            question_id=selected_beh["id"],
            domain_id=domain_id,
            category_id=selected_beh.get("category_id", "behavioral_experience"),
            category_name=selected_beh.get("category_name", "Behavioral & Communication"),
            topic=selected_beh.get("topic", "Engineering Experience"),
            title=selected_beh["title"],
            difficulty=difficulty,
            estimated_seconds=selected_beh.get("estimated_seconds", 120),
            question_type="behavioral",
            tts_text=build_conversational_tts(selected_beh["title"], question_type="behavioral", turn_index=len(queue)),
        )
        if len(queue) > 1:
            queue.insert(len(queue) - 1, beh_slot)
        else:
            queue.append(beh_slot)

    # Step 6: Integrate natural introductory turn at Slot 0
    if include_intro:
        intro_tts = build_introductory_tts(
            domain_title=domain_title or domain_id.replace("_", " ").title(),
            domain_id=domain_id,
            role=role,
            difficulty=difficulty,
        )
        intro_slot = QuestionSlot(
            question_id=f"intro_{domain_id}",
            domain_id=domain_id,
            category_id="introduction",
            category_name="Introduction & Background",
            topic="Career & Background",
            title="Could you start by telling me a little about yourself, your background, and what brings you to this interview?",
            difficulty=difficulty,
            estimated_seconds=75,
            question_type="introductory",
            tts_text=intro_tts,
        )
        queue.insert(0, intro_slot)

    # Step 7: Populate conversational TTS for any remaining slots
    for idx, slot in enumerate(queue):
        if not slot.tts_text:
            slot.tts_text = build_conversational_tts(
                slot.title,
                question_type=slot.question_type,
                turn_index=idx + 1,
            )

    # Step 8: Trim to time budget while preserving intro
    queue = _trim_to_budget(queue, total_budget)

    state = InterviewState(
        session_id=session_id,
        domain_id=domain_id,
        difficulty=difficulty,
        duration_minutes=duration_minutes,
        total_budget_seconds=total_budget,
    )
    state.question_queue = queue
    return state



def pop_next_question(state: InterviewState) -> Optional[QuestionSlot]:
    """
    Advance the interview: pop the next question from the queue,
    accounting for real elapsed time vs. budget.

    Returns None if the interview is complete (time expired or queue empty).
    """
    if state.is_time_expired:
        return None
    if not state.question_queue:
        return None

    # Adaptive: if we're running behind, drop lowest-priority (last) category slot
    next_slot = state.question_queue[0]

    # Check if there's enough time for this question
    if next_slot.estimated_seconds > state.remaining_seconds:
        # Only skip if we're really tight — allow going slightly over for last question
        if state.questions_asked > 0 and next_slot.estimated_seconds > state.remaining_seconds * 1.5:
            # Drop remaining queue items until we find one that fits, or give up
            state.question_queue.pop(0)
            return pop_next_question(state)

    state.question_queue.pop(0)
    state.current_question_slot = next_slot
    state.follow_up_count_this_question = 0
    state.asked_question_ids.append(next_slot.question_id)
    state.covered_category_ids.add(next_slot.category_id)
    return next_slot


def record_answer(
    state: InterviewState,
    answer_duration_seconds: float,
    is_follow_up: bool = False,
) -> None:
    """
    Update elapsed time after an answer is received.
    Dynamically recomputes remaining budget.
    """
    actual = answer_duration_seconds + PER_QUESTION_OVERHEAD_SECONDS
    state.elapsed_seconds += actual

    if is_follow_up:
        state.follow_up_count_total += 1
        state.follow_up_count_this_question += 1


def can_add_follow_up(state: InterviewState) -> bool:
    """
    Deterministic check: can a follow-up be asked for the current question?
    Caps: 1 follow-up per question, 3 per session total.
    """
    if state.follow_up_count_this_question >= MAX_FOLLOW_UPS_PER_QUESTION:
        return False
    if state.follow_up_count_total >= MAX_FOLLOW_UPS_PER_SESSION:
        return False
    # Also need enough time for a follow-up
    follow_up_budget = DIFFICULTY_TIME_BUDGET.get(
        state.current_question_slot.difficulty if state.current_question_slot else "Intermediate",
        120
    ) * 0.6   # follow-ups are typically shorter
    return state.remaining_seconds >= follow_up_budget


def build_follow_up_slot(
    state: InterviewState,
    follow_up_focus: str,
) -> QuestionSlot:
    """Build a synthetic follow-up slot from the current question context."""
    if not state.current_question_slot:
        raise ValueError("No current question to build follow-up from")
    parent = state.current_question_slot
    return QuestionSlot(
        question_id=parent.question_id,   # same question, different angle
        domain_id=parent.domain_id,
        category_id=parent.category_id,
        category_name=parent.category_name,
        topic=parent.topic,
        title=f"Follow-up: {follow_up_focus[:80]}",
        difficulty=parent.difficulty,
        estimated_seconds=int(DIFFICULTY_TIME_BUDGET.get(parent.difficulty, 120) * 0.6),
        is_follow_up=True,
        follow_up_focus=follow_up_focus,
        question_type=parent.question_type,
        tts_text=f"Thanks for explaining that. Let me probe a bit further on {follow_up_focus}: how would you approach that?",
        parent_question_id=parent.question_id,
    )


def compute_category_distribution(state: InterviewState) -> Dict[str, int]:
    """Return planned question count per category (for setup preview)."""
    dist: Dict[str, int] = {}
    for slot in state.question_queue:
        cat = slot.category_name
        dist[cat] = dist.get(cat, 0) + 1
    return dist


def plan_summary(state: InterviewState) -> Dict[str, Any]:
    """Human-readable summary of the interview plan."""
    return {
        "planned_question_count": len(state.question_queue),
        "estimated_duration_minutes": round(
            sum(s.estimated_seconds + PER_QUESTION_OVERHEAD_SECONDS for s in state.question_queue) / 60, 1
        ),
        "category_distribution": compute_category_distribution(state),
        "difficulty": state.difficulty,
        "domain_id": state.domain_id,
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _filter_by_difficulty(
    questions: List[Dict[str, Any]],
    difficulty: str,
) -> List[Dict[str, Any]]:
    if difficulty == "Mixed":
        return questions
    return [q for q in questions if q.get("difficulty", "Intermediate") == difficulty]


def _allocate_slots(
    category_groups: Dict[str, List[Dict[str, Any]]],
    total_budget: int,
    difficulty: str,
    job_tags: Set[str],
    weak_cats: Set[str],
) -> Dict[str, int]:
    """
    Duration-aware proportional slot allocation.

    If total_budget allows fewer questions than there are categories (e.g. 10-minute interview),
    selects a balanced subset of categories based on weights (weak areas, job tags, variety)
    without forcing all categories into a short interview.

    If total_budget allows >= len(categories) questions, ensures every category gets at least 1 (floor=1),
    and distributes remainder proportionally.
    """
    avg_q_time = DIFFICULTY_TIME_BUDGET.get(difficulty, 120) + PER_QUESTION_OVERHEAD_SECONDS
    max_questions = max(1, int(total_budget / avg_q_time))

    # Calculate weights
    weights: Dict[str, float] = {}
    for cat_id, questions in category_groups.items():
        base = math.sqrt(len(questions))
        if job_tags:
            cat_tags = set()
            for q in questions[:20]:
                cat_tags.update(t.lower() for t in q.get("tags", []))
            if cat_tags & job_tags:
                base *= 1.5
        if cat_id in weak_cats:
            base *= 2.0
        weights[cat_id] = base

    categories = list(category_groups.keys())
    # Sort categories deterministically: highest weight first, then category name
    categories.sort(key=lambda c: (weights.get(c, 0.0), c), reverse=True)

    slots: Dict[str, int] = {c: 0 for c in categories}

    if max_questions < len(categories):
        # Subset allocation: select the top max_questions categories with highest weight
        for cat_id in categories[:max_questions]:
            slots[cat_id] = 1
        return {k: v for k, v in slots.items() if v > 0}

    # Every category gets at least 1
    for cat_id in categories:
        slots[cat_id] = 1

    remaining = max_questions - len(categories)
    if remaining > 0:
        total_weight = sum(weights.values()) or 1.0
        for cat_id in categories:
            add_count = math.floor((weights[cat_id] / total_weight) * remaining)
            slots[cat_id] += add_count

        diff = max_questions - sum(slots.values())
        idx = 0
        while diff > 0 and idx < len(categories):
            slots[categories[idx % len(categories)]] += 1
            diff -= 1
            idx += 1

    return {k: v for k, v in slots.items() if v > 0}


def _select_questions(
    pool: List[Dict[str, Any]],
    count: int,
    previously_asked: Set[str],
) -> List[Dict[str, Any]]:
    """
    Select `count` questions from pool.
    Prefers questions NOT in previously_asked (spaced-repetition variety).
    Falls back to previously-asked questions if pool is small.
    """
    fresh = [q for q in pool if q["id"] not in previously_asked]
    seen = [q for q in pool if q["id"] in previously_asked]

    random.shuffle(fresh)
    random.shuffle(seen)

    combined = fresh + seen
    return combined[:count]


def _estimate_question_seconds(q: Dict[str, Any]) -> int:
    """
    Estimate expected answer time for a question.
    Uses difficulty tag as primary signal (confirmed in Phase 0: no explicit type tag).
    Secondary signal: content length as a complexity proxy.
    """
    difficulty = q.get("difficulty", "Intermediate")
    base = DIFFICULTY_TIME_BUDGET.get(difficulty, 120)

    # Secondary signal: long content suggests complex answer
    content = q.get("content") or q.get("markdown_content") or ""
    word_count = len(content.split())
    if word_count > 300:
        base = min(base + 30, 240)
    elif word_count < 80:
        base = max(base - 20, 60)

    return base


def _trim_to_budget(
    queue: List[QuestionSlot],
    total_budget: int,
) -> List[QuestionSlot]:
    """Trim queue to fit the time budget, preserving the opening turn."""
    result = []
    accumulated = 0
    for idx, slot in enumerate(queue):
        cost = slot.estimated_seconds + PER_QUESTION_OVERHEAD_SECONDS
        if accumulated + cost <= total_budget or idx == 0:
            result.append(slot)
            accumulated += cost
        else:
            break
    return result


def _empty_state(session_id, domain_id, difficulty, duration_minutes, total_budget):
    return InterviewState(
        session_id=session_id,
        domain_id=domain_id,
        difficulty=difficulty,
        duration_minutes=duration_minutes,
        total_budget_seconds=total_budget,
    )
