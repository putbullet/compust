"""
Deterministic Behavioral Interview Engine for Compust.

DESIGN PRINCIPLES:
1. Zero LLM calls in this module. All scheduling, timing, competency coverage,
   and conversational transitions are pure deterministic Python.
2. Behavioral & HR focus: introduction, motivation, strengths/weaknesses, teamwork,
   conflict, leadership, failure/mistakes, pressure/time management, adaptability,
   problem solving, communication, feedback, ethics, and questions for interviewer.
3. Multilingual: native EN, FR, and NL support loaded from static JSON question banks.
4. Deterministic state machine: bounds follow-up probes (max 1 per question, max 2 per session),
   guarantees duration fit, and prevents repeat questions.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("compust.mock_interview.engine")

QUESTION_BANK_DIR = Path(__file__).resolve().parent.parent / "content" / "behavioral_questions"

# Buffer added per question for speech transitions, acknowledgments, etc.
PER_QUESTION_OVERHEAD_SECONDS = 15

# Strict limits on follow-ups
MAX_FOLLOW_UPS_PER_QUESTION = 1
MAX_FOLLOW_UPS_PER_SESSION = 2

# Target question counts based on interview duration
DURATION_QUESTION_TARGETS: Dict[int, int] = {
    5: 3,    # Intro + 1 STAR core + Wrap-up / Questions for Us
    10: 5,   # Intro + 3 diverse STAR + Wrap-up
    15: 7,   # Intro + 5 diverse STAR + Wrap-up
    20: 9,   # Intro + 7 diverse STAR + Wrap-up
}

# Conversational acknowledgments varied between turns (not repetitive/scripted)
TRANSITIONS_BY_LANG: Dict[str, List[str]] = {
    "en": [
        "Thank you for sharing that context.",
        "Thanks, that gives me a clear picture of how you approach things.",
        "Understood, that's very helpful context.",
        "Thank you for walking me through that example.",
        "Great, let's explore another aspect of your experience.",
        "Appreciate that breakdown.",
    ],
    "fr": [
        "Merci d'avoir partagé ce contexte.",
        "Merci, cela me donne une image claire de votre approche.",
        "C'est très clair et instructif, merci.",
        "Merci de m'avoir détaillé cet exemple.",
        "Très bien, explorons maintenant un autre aspect de votre parcours.",
        "Parfait, passons au point suivant.",
    ],
    "nl": [
        "Dank u voor het delen van die context.",
        "Dank u, dat geeft een helder beeld van uw aanpak.",
        "Begrepen, dat is zeer waardevolle toelichting.",
        "Bedankt voor het toelichten van dit voorbeeld.",
        "Mooi, laten we naar een ander aspect van uw ervaring kijken.",
        "Prima, laten we doorgaan naar de volgende vraag.",
    ],
}

# Warm greetings prefixed to the self-introduction opening turn
GREETINGS_BY_LANG: Dict[str, str] = {
    "en": "Hello and welcome! Thank you for taking the time to speak with me today. To get started, ",
    "fr": "Bonjour et bienvenue ! Merci d'avoir pris le temps d'échanger avec moi aujourd'hui. Pour commencer, ",
    "nl": "Hallo en welkom! Bedankt dat u vandaag de tijd neemt voor dit gesprek. Laten we beginnen: ",
}

# Wrap-up text for closing
WRAPUP_BY_LANG: Dict[str, str] = {
    "en": "Thank you so much for your time and for sharing your experiences today. That concludes our interview session, and your detailed assessment report is now being prepared.",
    "fr": "Merci beaucoup pour votre temps et pour le partage de vos expériences. Notre entretien est maintenant terminé, et votre rapport d'évaluation détaillé est en cours de préparation.",
    "nl": "Hartelijk dank voor uw tijd en voor het delen van uw ervaringen vandaag. Hiermee is ons interviewgesprek afgerond, en uw evaluatierapport wordt nu voorbereid.",
}

# Role keyword mappings to prioritize relevant competencies
ROLE_KEYWORD_COMPETENCIES: Dict[str, List[str]] = {
    "lead": ["leadership", "conflict", "decision_making", "feedback", "teamwork"],
    "manager": ["leadership", "conflict", "decision_making", "feedback", "pressure"],
    "director": ["leadership", "decision_making", "planning", "ethics", "communication"],
    "engineer": ["problem_solving", "teamwork", "adaptability", "failure", "growth_mindset"],
    "developer": ["problem_solving", "teamwork", "adaptability", "failure", "growth_mindset"],
    "data": ["problem_solving", "decision_making", "communication", "adaptability"],
    "product": ["planning", "communication", "decision_making", "teamwork", "creativity"],
    "scrum": ["teamwork", "conflict", "communication", "adaptability"],
    "sales": ["customer_focus", "communication", "resilience", "pressure"],
    "customer": ["customer_focus", "communication", "resilience", "conflict"],
    "support": ["customer_focus", "communication", "problem_solving", "pressure"],
}


# In-memory question bank cache: lang -> List[Dict]
_QUESTION_BANK_CACHE: Dict[str, List[Dict[str, Any]]] = {}


def load_behavioral_questions(language: str = "en") -> List[Dict[str, Any]]:
    """
    Load the behavioral question bank for the specified language.
    Falls back to English if language file does not exist.
    """
    lang_code = language.lower() if language else "en"
    if lang_code not in ("en", "fr", "nl"):
        lang_code = "en"

    if lang_code in _QUESTION_BANK_CACHE:
        return _QUESTION_BANK_CACHE[lang_code]

    file_path = QUESTION_BANK_DIR / f"{lang_code}.json"
    if not file_path.exists():
        file_path = QUESTION_BANK_DIR / "en.json"

    try:
        data = json.loads(file_path.read_text(encoding="utf-8-sig"))
        _QUESTION_BANK_CACHE[lang_code] = data
        return data
    except Exception as exc:
        logger.error(f"Failed to load behavioral question bank for {lang_code}: {exc}")
        if lang_code != "en":
            return load_behavioral_questions("en")
        return []


@dataclass
class QuestionSlot:
    """A single scheduled question slot in the behavioral interview plan."""
    question_id: str
    competency: str
    competency_label: str
    title: str
    signals: List[str] = field(default_factory=list)
    follow_up_probes: List[str] = field(default_factory=list)
    expected_duration_seconds: int = 90
    star_applicable: bool = True
    is_follow_up: bool = False
    follow_up_focus: Optional[str] = None
    parent_question_id: Optional[str] = None
    tts_text: Optional[str] = None

    # Compatibility attributes for existing views & API
    domain_id: str = "behavioral"
    category_id: str = ""
    category_name: str = ""
    topic: str = "Behavioral"
    difficulty: str = "Standard"
    question_type: str = "behavioral"
    estimated_seconds: int = 90

    def __post_init__(self):
        if not self.category_id:
            self.category_id = self.competency
        if not self.category_name:
            self.category_name = self.competency_label
        if not self.estimated_seconds:
            self.estimated_seconds = self.expected_duration_seconds


@dataclass
class InterviewState:
    """Single source of truth for a live behavioral interview session."""
    session_id: int
    duration_minutes: int
    total_budget_seconds: int
    language: str = "en"
    target_role: Optional[str] = None
    role: Optional[str] = None

    # Planned question queue
    question_queue: List[QuestionSlot] = field(default_factory=list)

    # Completed progress
    asked_question_ids: List[str] = field(default_factory=list)
    covered_competencies: Set[str] = field(default_factory=set)

    # Timing
    started_at: Optional[datetime] = None
    elapsed_seconds: float = 0.0

    # Follow-up tracking
    follow_up_count_this_question: int = 0
    follow_up_count_total: int = 0
    current_question_slot: Optional[QuestionSlot] = None

    # Compatibility attributes
    domain_id: str = "behavioral"
    difficulty: str = "Standard"

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self.total_budget_seconds - self.elapsed_seconds)

    @property
    def is_time_expired(self) -> bool:
        return self.remaining_seconds <= 0.0

    @property
    def questions_asked(self) -> int:
        return len(self.asked_question_ids)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state for JSON storage in DB."""
        return {
            "session_id": self.session_id,
            "duration_minutes": self.duration_minutes,
            "total_budget_seconds": self.total_budget_seconds,
            "language": self.language,
            "target_role": self.target_role or self.role,
            "role": self.role or self.target_role,
            "domain_id": self.domain_id,
            "difficulty": self.difficulty,
            "elapsed_seconds": self.elapsed_seconds,
            "asked_question_ids": self.asked_question_ids,
            "covered_competencies": list(self.covered_competencies),
            "follow_up_count_total": self.follow_up_count_total,
            "follow_up_count_this_question": self.follow_up_count_this_question,
            "current_question_slot": self._slot_to_dict(self.current_question_slot) if self.current_question_slot else None,
            "question_queue": [self._slot_to_dict(s) for s in self.question_queue],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterviewState":
        """Deserialize from stored JSON."""
        state = cls(
            session_id=data.get("session_id", 0),
            duration_minutes=data.get("duration_minutes", 15),
            total_budget_seconds=data.get("total_budget_seconds", 900),
            language=data.get("language", "en"),
            target_role=data.get("target_role") or data.get("role"),
            role=data.get("role") or data.get("target_role"),
        )
        state.elapsed_seconds = data.get("elapsed_seconds", 0.0)
        state.asked_question_ids = data.get("asked_question_ids", [])
        state.covered_competencies = set(data.get("covered_competencies", []))
        state.follow_up_count_total = data.get("follow_up_count_total", 0)
        state.follow_up_count_this_question = data.get("follow_up_count_this_question", 0)

        cur_data = data.get("current_question_slot")
        if cur_data:
            state.current_question_slot = cls._dict_to_slot(cur_data)

        q_list = data.get("question_queue", [])
        state.question_queue = [cls._dict_to_slot(q) for q in q_list]
        return state

    @staticmethod
    def _slot_to_dict(slot: QuestionSlot) -> Dict[str, Any]:
        return {
            "question_id": slot.question_id,
            "competency": slot.competency,
            "competency_label": slot.competency_label,
            "title": slot.title,
            "signals": slot.signals,
            "follow_up_probes": slot.follow_up_probes,
            "expected_duration_seconds": slot.expected_duration_seconds,
            "estimated_seconds": slot.estimated_seconds,
            "star_applicable": slot.star_applicable,
            "is_follow_up": slot.is_follow_up,
            "follow_up_focus": slot.follow_up_focus,
            "parent_question_id": slot.parent_question_id,
            "tts_text": slot.tts_text,
            "domain_id": slot.domain_id,
            "category_id": slot.category_id,
            "category_name": slot.category_name,
            "topic": slot.topic,
            "difficulty": slot.difficulty,
            "question_type": slot.question_type,
        }

    @staticmethod
    def _dict_to_slot(d: Dict[str, Any]) -> QuestionSlot:
        return QuestionSlot(
            question_id=d.get("question_id", ""),
            competency=d.get("competency", "behavioral"),
            competency_label=d.get("competency_label", "Behavioral"),
            title=d.get("title", ""),
            signals=d.get("signals", []),
            follow_up_probes=d.get("follow_up_probes", []),
            expected_duration_seconds=d.get("expected_duration_seconds", 90),
            estimated_seconds=d.get("estimated_seconds", 90),
            star_applicable=d.get("star_applicable", True),
            is_follow_up=d.get("is_follow_up", False),
            follow_up_focus=d.get("follow_up_focus"),
            parent_question_id=d.get("parent_question_id"),
            tts_text=d.get("tts_text"),
            domain_id=d.get("domain_id", "behavioral"),
            category_id=d.get("category_id", d.get("competency", "behavioral")),
            category_name=d.get("category_name", d.get("competency_label", "Behavioral")),
            topic=d.get("topic", "Behavioral"),
            difficulty=d.get("difficulty", "Standard"),
            question_type=d.get("question_type", "behavioral"),
        )


def _determine_target_question_count(duration_minutes: int) -> int:
    """Return target question count based on duration."""
    for threshold in sorted(DURATION_QUESTION_TARGETS.keys(), reverse=True):
        if duration_minutes >= threshold:
            return DURATION_QUESTION_TARGETS[threshold]
    return 3


def _score_question_for_role(q: Dict[str, Any], role_clean: Optional[str]) -> float:
    """Score question relevance based on target role keywords."""
    if not role_clean:
        return 1.0

    score = 1.0
    role_words = role_clean.lower().split()
    comp = q.get("competency", "")

    for kw, preferred_comps in ROLE_KEYWORD_COMPETENCIES.items():
        if any(kw in rw for rw in role_words):
            if comp in preferred_comps:
                score += 2.0

    tags = [t.lower() for t in q.get("role_relevance_tags", [])]
    for rw in role_words:
        if rw in tags:
            score += 1.5

    return score


def build_interview_plan(
    duration_minutes: int,
    session_id: int = 0,
    language: str = "en",
    role: Optional[str] = None,
    domain_name: Optional[str] = None,
    job_skill_tags: Optional[Set[str]] = None,
    previously_asked_ids: Optional[Set[str]] = None,
    **kwargs: Any,  # Absorbs legacy parameters
) -> InterviewState:
    """
    Build a deterministic behavioral interview question plan.
    Selection is duration-aware, random without repeats, biased away from
    recently answered questions, and weighted by target role when provided.
    """
    safe_duration = max(5, min(duration_minutes, 60))
    total_budget = safe_duration * 60
    target_count = _determine_target_question_count(safe_duration)
    lang = language.lower() if language in ("en", "fr", "nl") else "en"
    clean_role = role.strip() if role and isinstance(role, str) and role.strip() else None
    seen_ids = set(previously_asked_ids or [])

    questions = load_behavioral_questions(lang)
    if not questions:
        raise ValueError(f"No behavioral questions available for language {lang}")

    state = InterviewState(
        session_id=session_id,
        duration_minutes=safe_duration,
        total_budget_seconds=total_budget,
        language=lang,
        target_role=clean_role,
        role=clean_role,
    )

    # Segregate question pools
    intro_pool = [q for q in questions if q.get("competency") == "introduction"]
    wrapup_pool = [q for q in questions if q.get("competency") == "questions_for_interviewer"]
    behavioral_pool = [q for q in questions if q.get("competency") not in ("introduction", "questions_for_interviewer")]

    # 1. Select opening question (Introduction)
    intro_candidates = [q for q in intro_pool if q["id"] not in seen_ids] or intro_pool
    chosen_intro = random.choice(intro_candidates) if intro_candidates else intro_pool[0]

    # Format role/domain for human greeting if available
    display_role = None
    if clean_role and domain_name and domain_name.lower() not in clean_role.lower():
        display_role = f"{clean_role} ({domain_name})"
    elif clean_role:
        display_role = clean_role
    elif domain_name and domain_name.lower() != "behavioral":
        display_role = domain_name

    if display_role:
        if lang == "fr":
            greeting_prefix = f"Bonjour et bienvenue ! Merci d'avoir pris le temps d'échanger avec moi aujourd'hui pour le poste de {display_role}. Pour commencer, "
        elif lang == "nl":
            greeting_prefix = f"Hallo en welkom! Bedankt dat u vandaag de tijd neemt voor dit gesprek voor de functie van {display_role}. Laten we beginnen: "
        else:
            greeting_prefix = f"Hello and welcome! Thank you for taking the time to speak with me today for the {display_role} role. To get started, "
    else:
        greeting_prefix = GREETINGS_BY_LANG.get(lang, GREETINGS_BY_LANG["en"])

    intro_tts = f"{greeting_prefix}{chosen_intro['question']}"

    intro_slot = QuestionSlot(
        question_id=chosen_intro["id"],
        competency=chosen_intro["competency"],
        competency_label=chosen_intro["competency_label"],
        title=chosen_intro["question"],
        signals=chosen_intro.get("signals", []),
        follow_up_probes=chosen_intro.get("follow_up_probes", []),
        expected_duration_seconds=chosen_intro.get("expected_duration_seconds", 90),
        star_applicable=False,
        tts_text=intro_tts,
        question_type="introductory",
    )

    # 2. Select closing question (Questions for Interviewer)
    wrapup_candidates = [q for q in wrapup_pool if q["id"] not in seen_ids] or wrapup_pool
    chosen_wrapup = random.choice(wrapup_candidates) if wrapup_candidates else wrapup_pool[0]

    closing_slot = QuestionSlot(
        question_id=chosen_wrapup["id"],
        competency=chosen_wrapup["competency"],
        competency_label=chosen_wrapup["competency_label"],
        title=chosen_wrapup["question"],
        signals=chosen_wrapup.get("signals", []),
        follow_up_probes=[],
        expected_duration_seconds=chosen_wrapup.get("expected_duration_seconds", 90),
        star_applicable=False,
        tts_text=chosen_wrapup["question"],
        question_type="wrap_up",
    )

    # 3. Select middle competency questions
    # We need (target_count - 2) middle questions
    needed_middle = max(1, target_count - 2)

    # Group pool by competency
    comp_groups: Dict[str, List[Dict[str, Any]]] = {}
    for q in behavioral_pool:
        comp = q.get("competency", "general")
        comp_groups.setdefault(comp, []).append(q)

    # Score competencies
    competency_scores: List[Tuple[str, float]] = []
    for comp, q_list in comp_groups.items():
        base_score = 1.0
        # Check role relevance
        if clean_role:
            sample_q = q_list[0]
            base_score = _score_question_for_role(sample_q, clean_role)

        # Freshness bonus: favor competencies where candidate hasn't answered recent questions
        fresh_count = sum(1 for q in q_list if q["id"] not in seen_ids)
        if fresh_count > 0:
            base_score += 0.5

        # Add slight jitter for natural variety
        jitter = random.uniform(0.0, 0.4)
        competency_scores.append((comp, base_score + jitter))

    # Sort competencies by score descending
    competency_scores.sort(key=lambda x: x[1], reverse=True)

    selected_middle_slots: List[QuestionSlot] = []
    transitions = TRANSITIONS_BY_LANG.get(lang, TRANSITIONS_BY_LANG["en"])

    for comp, _score in competency_scores:
        if len(selected_middle_slots) >= needed_middle:
            break

        q_list = comp_groups[comp]
        # Choose fresh questions first
        fresh_qs = [q for q in q_list if q["id"] not in seen_ids]
        candidate_q = random.choice(fresh_qs) if fresh_qs else random.choice(q_list)

        # Transition acknowledgment phrase
        trans_phrase = transitions[len(selected_middle_slots) % len(transitions)]
        tts_text = f"{trans_phrase} {candidate_q['question']}"

        slot = QuestionSlot(
            question_id=candidate_q["id"],
            competency=candidate_q["competency"],
            competency_label=candidate_q["competency_label"],
            title=candidate_q["question"],
            signals=candidate_q.get("signals", []),
            follow_up_probes=candidate_q.get("follow_up_probes", []),
            expected_duration_seconds=candidate_q.get("expected_duration_seconds", 120),
            star_applicable=candidate_q.get("star_applicable", True),
            tts_text=tts_text,
            question_type="behavioral",
        )
        selected_middle_slots.append(slot)

    # Assemble full queue
    full_queue: List[QuestionSlot] = [intro_slot] + selected_middle_slots + [closing_slot]
    state.question_queue = full_queue

    return state


def pop_next_question(state: InterviewState) -> Optional[QuestionSlot]:
    """
    Advance the interview: pop the next question from the queue.
    Returns None if the interview is complete (time expired or queue empty).
    """
    if state.is_time_expired:
        return None
    if not state.question_queue:
        return None

    next_slot = state.question_queue.pop(0)
    state.current_question_slot = next_slot
    state.follow_up_count_this_question = 0
    state.asked_question_ids.append(next_slot.question_id)
    state.covered_competencies.add(next_slot.competency)

    return next_slot


def record_answer(
    state: InterviewState,
    answer_duration_seconds: float,
    is_follow_up: bool = False,
) -> None:
    """
    Update elapsed time after an answer is received.
    Dynamically tracks remaining budget.
    """
    actual = max(1.0, float(answer_duration_seconds or 0.0)) + PER_QUESTION_OVERHEAD_SECONDS
    state.elapsed_seconds += actual

    if is_follow_up:
        state.follow_up_count_total += 1
        state.follow_up_count_this_question += 1


def can_add_follow_up(state: InterviewState) -> bool:
    """
    Deterministic check: can a follow-up probe be triggered?
    Enforces strict bounds:
    - At most 1 follow-up per question
    - At most 2 follow-ups per session total
    - Current question must have configured follow-up probes
    - Remaining budget must have at least 90s left
    """
    if state.follow_up_count_this_question >= MAX_FOLLOW_UPS_PER_QUESTION:
        return False
    if state.follow_up_count_total >= MAX_FOLLOW_UPS_PER_SESSION:
        return False
    if not state.current_question_slot or not state.current_question_slot.follow_up_probes:
        return False
    # Check remaining time
    return state.remaining_seconds >= 90.0


def build_follow_up_slot(
    state: InterviewState,
    follow_up_focus: Optional[str] = None,
) -> QuestionSlot:
    """
    Build a follow-up slot using the parent question's configured probes.
    """
    parent = state.current_question_slot
    if not parent:
        raise ValueError("No current question to build follow-up from")

    lang = state.language or "en"
    probe_text = follow_up_focus
    if not probe_text and parent.follow_up_probes:
        probe_text = parent.follow_up_probes[0]
    if not probe_text:
        probe_text = "Could you walk me through the specific outcome or result of that situation?"

    # Natural prefix
    if lang == "fr":
        tts_text = f"Merci. Pourriez-vous préciser un peu plus : {probe_text}"
    elif lang == "nl":
        tts_text = f"Dank u. Kunt u daar iets specifieker op ingaan: {probe_text}"
    else:
        tts_text = f"Thanks for sharing that. Could you tell me a bit more specifically: {probe_text}"

    return QuestionSlot(
        question_id=f"{parent.question_id}_followup",
        competency=parent.competency,
        competency_label=parent.competency_label,
        title=probe_text,
        signals=parent.signals,
        follow_up_probes=[],
        expected_duration_seconds=75,
        star_applicable=parent.star_applicable,
        is_follow_up=True,
        follow_up_focus=probe_text,
        parent_question_id=parent.question_id,
        tts_text=tts_text,
        question_type="follow_up",
    )


def plan_summary(state: InterviewState) -> Dict[str, Any]:
    """Human-readable summary of the interview plan."""
    cat_dist: Dict[str, int] = {}
    for slot in state.question_queue:
        cat = slot.competency_label
        cat_dist[cat] = cat_dist.get(cat, 0) + 1

    return {
        "planned_question_count": len(state.question_queue),
        "estimated_duration_minutes": round(
            sum(s.expected_duration_seconds + PER_QUESTION_OVERHEAD_SECONDS for s in state.question_queue) / 60, 1
        ),
        "category_distribution": cat_dist,
        "difficulty": state.difficulty,
        "domain_id": state.domain_id,
        "language": state.language,
        "target_role": state.target_role or state.role,
    }
