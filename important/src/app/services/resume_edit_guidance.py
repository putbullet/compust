"""Service for generating actionable, structured resume-edit guidance for Compust Capture.

Grounded in real candidate resume content and target job requirements:
- What to add (missing or weak skill/qualification)
- Where to add it (section: Skills, Experience with specific role, Summary)
- How to phrase it (concrete achievement bullet or line)
- Strict anti-hallucination: clearly flags when a skill is absent rather than fabricating experience.
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any
from pydantic import BaseModel, Field

from ..logging import get_logger
from .ai_service import generate_completion, check_ollama_runtime, get_selected_model

logger = get_logger(__name__)


class ResumeEditSuggestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    section: str  # "skills", "experience", "summary", "projects"
    item_label: str  # e.g., "Docker", "FastAPI"
    action: str  # "add", "emphasize", "clarify", "missing"
    where: str  # e.g., "Skills > Technical", "Experience at TechCorp (Senior Developer)"
    suggested_text: str
    reason: str
    grounded: bool = True  # False if absent from candidate context (anti-hallucination flag)


def _extract_candidate_corpus(resume_text: str, structured_data: dict[str, Any] | None) -> set[str]:
    """Extract lowercase significant words (>3 chars) from resume text and structured data."""
    corpus: set[str] = set()
    if resume_text:
        words = re.findall(r"\b[a-zA-Z]{3,}\b", resume_text.lower())
        corpus.update(words)

    if structured_data:
        profile = structured_data.get("profile") or {}
        if profile.get("summary"):
            corpus.update(re.findall(r"\b[a-zA-Z]{3,}\b", profile["summary"].lower()))

        for exp in (structured_data.get("experience") or []):
            if exp.get("company"):
                corpus.update(re.findall(r"\b[a-zA-Z]{3,}\b", exp["company"].lower()))
            if exp.get("title"):
                corpus.update(re.findall(r"\b[a-zA-Z]{3,}\b", exp["title"].lower()))
            for b in (exp.get("bullets") or []):
                corpus.update(re.findall(r"\b[a-zA-Z]{3,}\b", b.lower()))

        for sk in (structured_data.get("skills") or []):
            name = sk.get("name") if isinstance(sk, dict) else str(sk)
            if name:
                corpus.update(re.findall(r"\b[a-zA-Z]{3,}\b", name.lower()))

    return corpus


def generate_deterministic_resume_guidance(
    job_title: str,
    job_description: str,
    missing_skills: list[str],
    demonstrated_skills: list[str],
    resume_text: str,
    structured_data: dict[str, Any] | None = None,
) -> list[ResumeEditSuggestion]:
    """Generates deterministic, grounded resume-edit suggestions without LLM."""
    suggestions: list[ResumeEditSuggestion] = []
    corpus = _extract_candidate_corpus(resume_text, structured_data)

    # Find the most recent experience company/title if available
    recent_role = None
    if structured_data and structured_data.get("experience"):
        first_exp = structured_data["experience"][0]
        recent_role = f"{first_exp.get('title', 'Role')} at {first_exp.get('company', 'Previous Company')}"

    # 1. For demonstrated skills that appear in skills list but not in experience bullets
    resume_lower = resume_text.lower()
    for skill in demonstrated_skills[:3]:
        skill_clean = skill.strip()
        if skill_clean.lower() not in resume_lower or len(re.findall(rf"\b{re.escape(skill_clean.lower())}\b", resume_lower)) <= 1:
            target_loc = f"Experience: {recent_role}" if recent_role else "Experience section"
            suggestions.append(ResumeEditSuggestion(
                section="experience",
                item_label=skill_clean,
                action="emphasize",
                where=target_loc,
                suggested_text=f"- Leveraged {skill_clean} to engineer reliable services, improving workflow efficiency.",
                reason=f"'{skill_clean}' is listed in your skills, but substantiating it with a quantifiable bullet in your work history strengthens ATS relevance.",
                grounded=True,
            ))

    # 2. For missing skills
    for skill in missing_skills[:6]:
        skill_clean = skill.strip()
        skill_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", skill_clean.lower()))
        is_plausible = bool(skill_words & corpus)

        if is_plausible and recent_role:
            # Candidate has related vocabulary in corpus
            suggestions.append(ResumeEditSuggestion(
                section="experience",
                item_label=skill_clean,
                action="add",
                where=f"Experience: {recent_role}",
                suggested_text=f"- Integrated {skill_clean} solutions to align systems with technical specifications.",
                reason=f"Target role specifically lists '{skill_clean}'. You have related background; highlight how you applied it.",
                grounded=True,
            ))
        else:
            # Skill is genuinely missing / unconfirmed -> Anti-hallucination guidance
            suggestions.append(ResumeEditSuggestion(
                section="skills",
                item_label=skill_clean,
                action="missing",
                where="Skills section (if verified)",
                suggested_text=f"Add '{skill_clean}' to Technical Skills ONLY if you possess genuine hands-on experience.",
                reason=f"Required for '{job_title}' but absent from your resume. Do not fabricate experience; if you have worked with this technology, add it to your skills profile.",
                grounded=False,
            ))

    # 3. Summary alignment if missing skills are prominent
    if missing_skills and structured_data:
        suggestions.append(ResumeEditSuggestion(
            section="summary",
            item_label=job_title,
            action="clarify",
            where="Professional Summary",
            suggested_text=f"Tailor summary headline towards '{job_title}' with focus on {', '.join(demonstrated_skills[:2]) if demonstrated_skills else 'core strengths'}.",
            reason=f"Aligning your summary with the exact title '{job_title}' improves recruiter scan rate and ATS title matching.",
            grounded=True,
        ))

    return suggestions


GUIDANCE_SYSTEM_PROMPT = """You are an elite career coach and resume strategist.
Generate structured, grounded resume-edit recommendations for a candidate applying to a target job.

CRITICAL ANTI-HALLUCINATION RULES:
1. Grounding: You must inspect the candidate's actual resume content.
2. If a skill/requirement is present in their background, suggest a concrete phrased bullet point for a specific past role or skills category.
3. If a skill/requirement is completely absent from their background, set grounded=false, action="missing", and explicitly state:
   "Not found in your resume. Only claim this if you have genuine experience with {skill}."
4. DO NOT invent fake past employers, fake projects, or fake metrics.

OUTPUT FORMAT:
Respond with ONLY a single valid JSON object:
{
  "suggestions": [
    {
      "section": "experience",
      "item_label": "Docker",
      "action": "add",
      "where": "Experience: Senior Engineer at TechCorp",
      "suggested_text": "- Containerized microservices using Docker and automated CI deployment.",
      "reason": "Docker is a core requirement in the job description.",
      "grounded": true
    },
    {
      "section": "skills",
      "item_label": "Kubernetes",
      "action": "missing",
      "where": "Skills section (if verified)",
      "suggested_text": "Add 'Kubernetes' only if you have genuine hands-on experience.",
      "reason": "Required for target role but absent from resume background.",
      "grounded": false
    }
  ]
}
"""


def generate_actionable_resume_suggestions(
    job_title: str,
    job_description: str,
    missing_skills: list[str],
    demonstrated_skills: list[str],
    resume_text: str,
    structured_data: dict[str, Any] | None = None,
    use_llm: bool = True,
) -> list[ResumeEditSuggestion]:
    """Generates structured, section-grouped resume-edit guidance."""
    if not use_llm:
        return generate_deterministic_resume_guidance(
            job_title=job_title,
            job_description=job_description,
            missing_skills=missing_skills,
            demonstrated_skills=demonstrated_skills,
            resume_text=resume_text,
            structured_data=structured_data,
        )

    runtime = check_ollama_runtime()
    if runtime["status"] != "connected" or not runtime["models"]:
        return generate_deterministic_resume_guidance(
            job_title=job_title,
            job_description=job_description,
            missing_skills=missing_skills,
            demonstrated_skills=demonstrated_skills,
            resume_text=resume_text,
            structured_data=structured_data,
        )

    prompt = f"""Target Job Title: {job_title}
Key Missing/Weak Requirements: {', '.join(missing_skills[:8]) if missing_skills else 'None'}
Demonstrated Skills: {', '.join(demonstrated_skills[:8]) if demonstrated_skills else 'None'}

--- Resume Search Layer ---
{resume_text[:2500]}

Generate 4-6 specific, actionable, grounded suggestions for incorporating or addressing missing requirements.
"""

    try:
        raw = generate_completion(
            prompt=prompt,
            system_prompt=GUIDANCE_SYSTEM_PROMPT,
            model=runtime.get("selected_model"),
            temperature=0.1,
            timeout_seconds=20.0,
        )

        # Parse JSON
        cleaned = raw.strip()
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1)
        else:
            first_brace = cleaned.find("{")
            last_brace = cleaned.rfind("}")
            if first_brace != -1 and last_brace != -1:
                cleaned = cleaned[first_brace : last_brace + 1]

        data = json.loads(cleaned)
        items = data.get("suggestions", [])
        results = [ResumeEditSuggestion(**item) for item in items if isinstance(item, dict)]
        if results:
            return results
    except Exception as exc:
        logger.warning(f"Ollama resume guidance error ({exc}). Falling back to deterministic guidance.")

    return generate_deterministic_resume_guidance(
        job_title=job_title,
        job_description=job_description,
        missing_skills=missing_skills,
        demonstrated_skills=demonstrated_skills,
        resume_text=resume_text,
        structured_data=structured_data,
    )
