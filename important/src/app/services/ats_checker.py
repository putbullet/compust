"""ATS Checker service for Compust Resume Studio.

Evaluates resumes across 6 key ATS pillars:
1. Parseability & Text Extraction
2. Keyword & Competency Alignment
3. Section Standardization (multilingual: EN, FR, DE, ES)
4. Quantifiable Impact & Action Verbs
5. Formatting & Length Conventions
6. Contact & Identity Detectability

Supports local Ollama LLM evaluation with resilient deterministic fallback.
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any
from pydantic import BaseModel, Field

from ..logging import get_logger
from .ai_service import generate_completion, OllamaError, get_selected_model

logger = get_logger(__name__)


# ----------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------

class ATSCategoryScore(BaseModel):
    category: str  # "parseability", "keywords", "sections", "impact", "formatting", "contact"
    name: str
    score: int = Field(..., ge=0, le=100)
    max_score: int = 100
    status: str  # "pass", "warning", "critical"
    notes: str


class ATSFeedbackItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    category: str
    severity: str  # "critical", "warning", "tip", "pass"
    title: str
    message: str
    recommendation: str
    grounded_quote: str | None = None


class ATSCheckResult(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    verdict: str  # "Strong Match", "Competitive", "Needs Optimization", "High ATS Rejection Risk"
    categories: list[ATSCategoryScore]
    feedback: list[ATSFeedbackItem]
    keywords_found: list[str]
    keywords_missing: list[str]
    recommended_action_verbs: list[str]
    provider: str  # "ollama" | "deterministic"
    model: str | None = None


# ----------------------------------------------------------------------
# Deterministic Rules & Constants
# ----------------------------------------------------------------------

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,9}")
LINK_REGEX = re.compile(r"(?:https?://|www\.|linkedin\.com|github\.com)[^\s,]+", re.IGNORECASE)
METRIC_REGEX = re.compile(
    r"(?:\b\d+(?:\.\d+)?%|\$\s*\d+(?:,\d+)*(?:\.\d+)?|\b\d+\s*(?:users|clients|customers|team members|developers|engineers|projects|ms|seconds|minutes|hours|x|k|m|b)\b)",
    re.IGNORECASE,
)

STRONG_ACTION_VERBS = {
    # English
    "accelerated", "achieved", "analyzed", "architected", "automated", "built",
    "coached", "collaborated", "constructed", "created", "decreased", "delivered",
    "designed", "developed", "devised", "directed", "doubled", "engineered",
    "enhanced", "established", "executed", "expanded", "expedited", "generated",
    "guided", "implemented", "improved", "increased", "initiated", "innovated",
    "integrated", "launched", "lead", "led", "managed", "maximized", "mentored",
    "migrated", "minimized", "modeled", "modernized", "negotiated", "optimized",
    "orchestrated", "overhauled", "pioneered", "planned", "produced", "reduced",
    "refactored", "resolved", "restructured", "revamped", "saved", "scaled",
    "spearheaded", "standardized", "streamlined", "strengthened", "supervised",
    "trained", "transformed", "upgraded", "validated",
    # French
    "accéléré", "accompli", "amélioré", "analysé", "architecturé", "automatisé",
    "conçu", "construit", "créé", "déployé", "développé", "dirigé", "encadré",
    "établi", "exécuté", "géré", "implémenté", "initié", "innové", "intégré",
    "lancé", "mené", "migré", "modélisé", "modernisé", "optimisé", "orchestré",
    "piloté", "planifié", "réduit", "refactorisé", "résolu", "restructuré",
    "simplifié", "supervisé", "transformé",
    # German
    "aufgebaut", "automatisiert", "beschleunigt", "entwickelt", "entworfen",
    "erhöht", "erstellt", "geführt", "gestaltet", "implementiert", "integriert",
    "konzipiert", "koordiniert", "geleitet", "optimiert", "organisiert",
    "reduziert", "realisiert", "skaliert", "standardisiert", "transformiert",
    "verbessert", "vergrößert",
}

SECTION_KEYWORD_PATTERNS = {
    "experience": re.compile(r"\b(experience|work history|employment|expérience|berufserfahrung|erfahrung|experiencia)\b", re.I),
    "education": re.compile(r"\b(education|formation|ausbildung|studium|educación|academic)\b", re.I),
    "skills": re.compile(r"\b(skills|technical skills|compétences|kenntnisse|fähigkeiten|habilidades)\b", re.I),
    "summary": re.compile(r"\b(summary|profile|about|profil|résumé|über mich|resumen|objective)\b", re.I),
    "projects": re.compile(r"\b(projects|projets|projekte|proyectos)\b", re.I),
    "certifications": re.compile(r"\b(certifications|certificats|zertifikate|certificaciones|credentials)\b", re.I),
}


# ----------------------------------------------------------------------
# Deterministic Evaluator
# ----------------------------------------------------------------------

def calculate_deterministic_ats_score(
    resume_text: str,
    structured_data: dict[str, Any] | None = None,
    role: str | None = None,
    field: str | None = None,
    job_description: str | None = None,
) -> ATSCheckResult:
    """Calculates a deterministic ATS evaluation grounded in real text analysis."""
    feedback: list[ATSFeedbackItem] = []
    text_lower = resume_text.lower()
    raw_lines = [l.strip() for l in resume_text.splitlines() if l.strip()]
    raw_words = re.findall(r"\b\w+\b", text_lower)
    word_count = len(raw_words)

    # 1. Contact Detectability (Weight: 15%)
    profile = (structured_data or {}).get("profile") or {}
    has_email = bool(EMAIL_REGEX.search(resume_text)) or bool(profile.get("email"))
    has_phone = bool(PHONE_REGEX.search(resume_text)) or bool(profile.get("phone"))
    has_location = bool(profile.get("location")) or bool(re.search(r"\b[A-Z][a-zA-Z\s]+,\s*[A-Z]{2}\b|\b[A-Za-z\s]+,\s*(?:France|Germany|United States|USA|UK|Canada|Spain)\b", resume_text, re.I))
    has_link = bool(LINK_REGEX.search(resume_text)) or bool(profile.get("website")) or bool(profile.get("linkedin")) or bool(profile.get("github"))

    contact_pts = 0
    if has_email:
        contact_pts += 35
    else:
        feedback.append(ATSFeedbackItem(
            category="contact",
            severity="critical",
            title="Missing or Unparseable Email",
            message="No standard email address could be extracted.",
            recommendation="Place your primary professional email clearly at the top of your resume.",
        ))

    if has_phone:
        contact_pts += 25
    else:
        feedback.append(ATSFeedbackItem(
            category="contact",
            severity="warning",
            title="Missing Phone Number",
            message="No phone number was identified by the parser.",
            recommendation="Include an international or local telephone number in your header.",
        ))

    if has_location:
        contact_pts += 20
    else:
        feedback.append(ATSFeedbackItem(
            category="contact",
            severity="tip",
            title="Location Undetected",
            message="City or geographic region was not prominently detected.",
            recommendation="Add City, Country or City, State to assist location-filtered ATS queries.",
        ))

    if has_link:
        contact_pts += 20

    contact_score = min(100, contact_pts)
    contact_status = "pass" if contact_score >= 80 else ("warning" if contact_score >= 50 else "critical")
    if contact_score >= 80:
        feedback.append(ATSFeedbackItem(
            category="contact",
            severity="pass",
            title="Contact Information Detected",
            message="ATS contact scrapers can reliably extract your identity and communication channels.",
            recommendation="Keep contact info in standard unformatted text at the very top.",
        ))

    # 2. Section Standardization (Weight: 20%)
    sections_found = []
    sections_missing = []

    for sec_name, pattern in SECTION_KEYWORD_PATTERNS.items():
        # Check structured_data first
        has_in_struct = False
        if structured_data:
            if sec_name == "experience" and structured_data.get("experience"):
                has_in_struct = True
            elif sec_name == "education" and structured_data.get("education"):
                has_in_struct = True
            elif sec_name == "skills" and (structured_data.get("skills") or structured_data.get("skills_raw")):
                has_in_struct = True
            elif sec_name == "summary" and (structured_data.get("summary") or structured_data.get("profile", {}).get("summary")):
                has_in_struct = True
            elif sec_name == "projects" and structured_data.get("projects"):
                has_in_struct = True
            elif sec_name == "certifications" and structured_data.get("certifications"):
                has_in_struct = True

        if has_in_struct or pattern.search(resume_text):
            sections_found.append(sec_name)
        else:
            sections_missing.append(sec_name)

    sec_score = 0
    if "experience" in sections_found:
        sec_score += 35
    else:
        feedback.append(ATSFeedbackItem(
            category="sections",
            severity="critical",
            title="Work Experience Section Missing",
            message="No standard Experience or Work History heading was detected.",
            recommendation="Use conventional headings: 'Work Experience', 'Professional Experience', or 'Expérience Professionnelle'.",
        ))

    if "skills" in sections_found:
        sec_score += 25
    else:
        feedback.append(ATSFeedbackItem(
            category="sections",
            severity="warning",
            title="Skills Section Missing",
            message="A dedicated Skills section was not detected.",
            recommendation="Add a clearly labeled 'Skills' or 'Compétences' section to group your technical proficiencies.",
        ))

    if "education" in sections_found:
        sec_score += 25
    else:
        feedback.append(ATSFeedbackItem(
            category="sections",
            severity="warning",
            title="Education Section Missing",
            message="No Education or Degree section recognized.",
            recommendation="Add an 'Education' or 'Formation' section with institution, degree, and graduation year.",
        ))

    if "summary" in sections_found or "projects" in sections_found:
        sec_score += 15

    sec_score = min(100, sec_score)
    sec_status = "pass" if sec_score >= 80 else ("warning" if sec_score >= 50 else "critical")
    if sec_score >= 80:
        feedback.append(ATSFeedbackItem(
            category="sections",
            severity="pass",
            title="Standard Section Taxonomy",
            message=f"Recognized key structural sections ({', '.join(sections_found)}). ATS hierarchy parsers will accurately segment your background.",
            recommendation="Maintain clean, standard section headings.",
        ))

    # 3. Parseability & Cleanliness (Weight: 15%)
    parse_pts = 100
    if word_count < 100:
        parse_pts -= 40
        feedback.append(ATSFeedbackItem(
            category="parseability",
            severity="critical",
            title="Extremely Sparse Resume Text",
            message=f"Only {word_count} words detected. This resume is too brief to trigger ATS candidate match thresholds.",
            recommendation="Expand your experience with detailed bullet points and achievements.",
        ))
    elif word_count > 1200:
        parse_pts -= 15
        feedback.append(ATSFeedbackItem(
            category="parseability",
            severity="warning",
            title="High Word Count / Dense Content",
            message=f"Resume has {word_count} words. Dense multi-page content often suffers keyword dilution in ATS scoring.",
            recommendation="Condense to high-impact highlights, aiming for 450-800 words for 1-2 pages.",
        ))

    # Check for excessive special symbols or corrupt text
    weird_chars = re.findall(r"[\uFFFD\u0000-\u0008\u000B\u000C\u000E-\u001F]", resume_text)
    if weird_chars:
        parse_pts -= 20
        feedback.append(ATSFeedbackItem(
            category="parseability",
            severity="warning",
            title="Non-Standard Unicode Glyphs",
            message="Detected unusual control characters or replacement characters that can break ATS text extractors.",
            recommendation="Ensure bullets use standard ASCII hyphens or clean bullet glyphs.",
        ))

    parse_score = max(0, min(100, parse_pts))
    parse_status = "pass" if parse_score >= 80 else ("warning" if parse_score >= 50 else "critical")
    if parse_score >= 80:
        feedback.append(ATSFeedbackItem(
            category="parseability",
            severity="pass",
            title="Clean Text Extractability",
            message="Plain-text extraction succeeds cleanly without structural artifacts or character corruption.",
            recommendation="RenderCV Typst engine provides ATS-grade searchable text layers.",
        ))

    # 4. Quantifiable Impact & Action Verbs (Weight: 20%)
    metrics_matches = METRIC_REGEX.findall(resume_text)
    metrics_count = len(metrics_matches)

    found_action_verbs = [v for v in STRONG_ACTION_VERBS if re.search(rf"\b{re.escape(v)}\b", text_lower)]
    verbs_count = len(found_action_verbs)

    impact_pts = 0
    if metrics_count >= 5:
        impact_pts += 50
    elif metrics_count >= 2:
        impact_pts += 30
    elif metrics_count >= 1:
        impact_pts += 15
    else:
        feedback.append(ATSFeedbackItem(
            category="impact",
            severity="critical",
            title="Lack of Quantifiable Metrics",
            message="No percentage improvements, revenue figures, time reductions, or scale metrics were detected.",
            recommendation="Transform responsibility statements into metric-driven outcomes (e.g., 'reduced latency by 35%', 'managed team of 6').",
        ))

    if verbs_count >= 8:
        impact_pts += 50
    elif verbs_count >= 4:
        impact_pts += 35
    elif verbs_count >= 1:
        impact_pts += 20
    else:
        feedback.append(ATSFeedbackItem(
            category="impact",
            severity="warning",
            title="Weak Action Verb Density",
            message="Few dynamic action verbs were found. ATS semantic analyzers rate passive language ('Responsible for', 'Helped with') lower.",
            recommendation="Begin every bullet point with a vigorous action verb (e.g., 'Engineered', 'Orchestrated', 'Delivered').",
        ))

    impact_score = min(100, impact_pts)
    impact_status = "pass" if impact_score >= 75 else ("warning" if impact_score >= 45 else "critical")
    if impact_score >= 75:
        feedback.append(ATSFeedbackItem(
            category="impact",
            severity="pass",
            title="High Measurable Impact",
            message=f"Detected {metrics_count} quantifiable metrics and {verbs_count} strong action verbs.",
            recommendation="Continue demonstrating business and engineering outcomes with specific data.",
        ))

    # 5. Formatting & Cleanliness Conventions (Weight: 15%)
    format_pts = 100
    # Check skill ratings (graphic dots/bars)
    if "beginner" in text_lower or "intermediate" in text_lower:
        format_pts -= 10
        feedback.append(ATSFeedbackItem(
            category="formatting",
            severity="tip",
            title="Subjective Skill Levels Present",
            message="Self-assessed skill levels ('Beginner', 'Intermediate') add subjective noise that ATS systems disregard.",
            recommendation="Group skills by category (e.g., Languages, Frameworks, Cloud) without arbitrary self-ratings.",
        ))

    # Check bullet structure
    bullet_lines = [l for l in raw_lines if l.startswith(("-", "•", "*", "–"))]
    if raw_lines and len(bullet_lines) < 3 and "experience" in sections_found:
        format_pts -= 15
        feedback.append(ATSFeedbackItem(
            category="formatting",
            severity="warning",
            title="Paragraph-Heavy Experience",
            message="Few bullet points detected. ATS readability algorithms favor concise 1-2 line bulleted accomplishment statements.",
            recommendation="Break down paragraph blocks into crisp, bulleted outcome statements.",
        ))

    format_score = max(0, min(100, format_pts))
    format_status = "pass" if format_score >= 80 else ("warning" if format_score >= 50 else "critical")

    # 6. Keyword & Competency Alignment (Weight: 15%)
    target_terms: set[str] = set()
    if role:
        target_terms.update(re.findall(r"\b[a-zA-Z]{3,}\b", role.lower()))
    if field:
        target_terms.update(re.findall(r"\b[a-zA-Z]{3,}\b", field.lower()))
    if job_description:
        # Extract meaningful nouns/keywords
        jd_words = re.findall(r"\b[a-zA-Z]{4,}\b", job_description.lower())
        stopwords = {"with", "that", "this", "from", "have", "will", "your", "their", "about", "would", "which", "could"}
        target_terms.update(w for w in jd_words if w not in stopwords)[:30]

    # Baseline core technical terms
    if not target_terms:
        target_terms = {"python", "javascript", "react", "sql", "api", "docker", "git", "ci/cd", "agile", "testing"}

    found_kw = sorted(list({t for t in target_terms if t in text_lower}))
    missing_kw = sorted(list({t for t in target_terms if t not in text_lower}))

    if target_terms:
        kw_ratio = len(found_kw) / len(target_terms)
        kw_score = min(100, max(20, int(kw_ratio * 100)))
    else:
        kw_score = 75

    if missing_kw:
        feedback.append(ATSFeedbackItem(
            category="keywords",
            severity="warning" if len(missing_kw) > 3 else "tip",
            title=f"Missing Target Keywords ({len(missing_kw)})",
            message=f"Keywords aligned with your target profile were not detected: {', '.join(missing_kw[:8])}.",
            recommendation="Incorporate these keywords naturally into your experience bullet points and skills section.",
        ))
    if found_kw:
        feedback.append(ATSFeedbackItem(
            category="keywords",
            severity="pass",
            title="Matched Target Keywords",
            message=f"Successfully matched core target keywords: {', '.join(found_kw[:8])}.",
            recommendation="Ensure keywords are paired with context showing how you applied them.",
        ))

    kw_status = "pass" if kw_score >= 70 else ("warning" if kw_score >= 45 else "critical")

    # Overall Weighted Score
    # Weights: contact (15), sections (20), parseability (15), impact (20), formatting (15), keywords (15)
    overall = int(
        contact_score * 0.15
        + sec_score * 0.20
        + parse_score * 0.15
        + impact_score * 0.20
        + format_score * 0.15
        + kw_score * 0.15
    )
    overall = max(0, min(100, overall))

    if overall >= 85:
        verdict = "Strong Match"
    elif overall >= 70:
        verdict = "Competitive"
    elif overall >= 50:
        verdict = "Needs Optimization"
    else:
        verdict = "High ATS Rejection Risk"

    categories = [
        ATSCategoryScore(
            category="parseability",
            name="ATS Parseability & Hygiene",
            score=parse_score,
            status=parse_status,
            notes=f"{word_count} words extracted cleanly.",
        ),
        ATSCategoryScore(
            category="sections",
            name="Section Standardization",
            score=sec_score,
            status=sec_status,
            notes=f"Found: {', '.join(sections_found)}.",
        ),
        ATSCategoryScore(
            category="contact",
            name="Contact Detectability",
            score=contact_score,
            status=contact_status,
            notes="Email, phone, and profile links detectability.",
        ),
        ATSCategoryScore(
            category="impact",
            name="Quantifiable Impact & Verbs",
            score=impact_score,
            status=impact_status,
            notes=f"{metrics_count} metrics, {verbs_count} action verbs.",
        ),
        ATSCategoryScore(
            category="formatting",
            name="Formatting & Layout Norms",
            score=format_score,
            status=format_status,
            notes="Bullet hierarchy and length balance.",
        ),
        ATSCategoryScore(
            category="keywords",
            name="Keyword & Competency Alignment",
            score=kw_score,
            status=kw_status,
            notes=f"{len(found_kw)} matched out of {len(target_terms)} targeted.",
        ),
    ]

    recommended_verbs = [
        v.capitalize() for v in [
            "Architected", "Spearheaded", "Streamlined", "Engineered",
            "Accelerated", "Delivered", "Optimized", "Modernized"
        ] if v.lower() not in found_action_verbs
    ][:6]

    return ATSCheckResult(
        overall_score=overall,
        verdict=verdict,
        categories=categories,
        feedback=feedback,
        keywords_found=found_kw,
        keywords_missing=missing_kw[:12],
        recommended_action_verbs=recommended_verbs,
        provider="deterministic",
        model=None,
    )


# ----------------------------------------------------------------------
# LLM Prompt & Parser
# ----------------------------------------------------------------------

ATS_SYSTEM_PROMPT = """You are an elite, battle-tested Applicant Tracking System (ATS) auditing engine and executive resume reviewer.
You evaluate resumes with strict adherence to real-world corporate ATS mechanics (Workday, Taleo, Greenhouse, Lever, iCIMS).

CRITICAL ANTI-HALLUCINATION RULES:
1. Grounding: You must evaluate ONLY what is present in the provided resume text. Never hallucinate missing sections if their content or standard heading exists (including multilingual headings like "Expérience Professionnelle", "Formation", "Compétences", "Berufserfahrung").
2. No Fake Quotes: If you provide a 'grounded_quote', it must be a verbatim substring from the resume. If not quoting directly, omit or set to null.
3. Scoring Calibration (0-100):
   - 85-100: Top 5% ATS parseability, strong metric-driven accomplishments (%, $, scale), comprehensive keywords.
   - 70-84: Solid, pass-rate competitive, minor keyword gaps or occasional weak action verbs.
   - 50-69: Noticeable deficiencies: missing key metrics, vague bullets, or non-standard formatting.
   - 0-49: Fatal ATS flaws: missing core sections, missing contact info, unparseable walls of text.

OUTPUT FORMAT:
You must respond with ONLY a single, valid JSON object conforming exactly to this structure:
{
  "overall_score": 78,
  "verdict": "Competitive",
  "categories": [
    {
      "category": "parseability",
      "name": "ATS Parseability & Hygiene",
      "score": 85,
      "max_score": 100,
      "status": "pass",
      "notes": "..."
    },
    {
      "category": "keywords",
      "name": "Keyword & Competency Alignment",
      "score": 70,
      "max_score": 100,
      "status": "warning",
      "notes": "..."
    },
    {
      "category": "sections",
      "name": "Section Standardization",
      "score": 90,
      "max_score": 100,
      "status": "pass",
      "notes": "..."
    },
    {
      "category": "impact",
      "name": "Quantifiable Impact & Verbs",
      "score": 65,
      "max_score": 100,
      "status": "warning",
      "notes": "..."
    },
    {
      "category": "formatting",
      "name": "Formatting & Layout Norms",
      "score": 80,
      "max_score": 100,
      "status": "pass",
      "notes": "..."
    },
    {
      "category": "contact",
      "name": "Contact Detectability",
      "score": 95,
      "max_score": 100,
      "status": "pass",
      "notes": "..."
    }
  ],
  "feedback": [
    {
      "category": "impact",
      "severity": "critical",
      "title": "Missing Quantifiable Results in Recent Role",
      "message": "Bullet points describe duties rather than measurable business impact.",
      "recommendation": "Add specific metrics such as latency reduced, revenue generated, or team size managed.",
      "grounded_quote": "Responsible for developing microservices"
    }
  ],
  "keywords_found": ["Python", "FastAPI", "PostgreSQL"],
  "keywords_missing": ["Docker", "CI/CD", "Kubernetes"],
  "recommended_action_verbs": ["Architected", "Spearheaded", "Streamlined", "Engineered"]
}
"""


def _extract_json_block(text: str) -> str:
    """Extracts JSON object from potential markdown code fences or raw output."""
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback to finding the first { and last }
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return cleaned[first_brace : last_brace + 1].strip()
    return cleaned


def evaluate_resume_ats(
    resume_text: str,
    structured_data: dict[str, Any] | None = None,
    role: str | None = None,
    field: str | None = None,
    job_description: str | None = None,
    use_llm: bool = True,
) -> ATSCheckResult:
    """Evaluates a resume for ATS compliance.

    Attempts local Ollama evaluation first, falling back cleanly to the
    deterministic engine if Ollama is offline, times out, or errors.
    """
    if not resume_text or len(resume_text.strip()) < 20:
        # Trivial or empty resume -> deterministic fast fail
        return calculate_deterministic_ats_score(
            resume_text=resume_text or "",
            structured_data=structured_data,
            role=role,
            field=field,
            job_description=job_description,
        )

    if not use_llm:
        return calculate_deterministic_ats_score(
            resume_text=resume_text,
            structured_data=structured_data,
            role=role,
            field=field,
            job_description=job_description,
        )

    # Prepare prompt for Ollama
    role_ctx = f"Target Role: {role}\n" if role else ""
    field_ctx = f"Target Industry/Field: {field}\n" if field else ""
    jd_ctx = f"\n--- Target Job Description ---\n{job_description[:1500]}\n" if job_description else ""

    user_prompt = f"""Evaluate this candidate resume for ATS compatibility and alignment.

{role_ctx}{field_ctx}{jd_ctx}
--- Resume Content (Search Layer) ---
{resume_text[:4000]}

Provide the comprehensive JSON ATS audit strictly conforming to the requested schema.
"""

    selected_model = get_selected_model()

    try:
        raw_response = generate_completion(
            prompt=user_prompt,
            system_prompt=ATS_SYSTEM_PROMPT,
            model=selected_model,
            temperature=0.1,
            timeout_seconds=30.0,
        )

        json_str = _extract_json_block(raw_response)
        parsed_data = json.loads(json_str)

        # Validate with Pydantic
        categories = [ATSCategoryScore(**cat) for cat in parsed_data.get("categories", [])]
        feedback = [ATSFeedbackItem(**item) for item in parsed_data.get("feedback", [])]

        overall_score = int(parsed_data.get("overall_score", 70))
        overall_score = max(0, min(100, overall_score))

        verdict = parsed_data.get("verdict")
        if not verdict:
            if overall_score >= 85:
                verdict = "Strong Match"
            elif overall_score >= 70:
                verdict = "Competitive"
            elif overall_score >= 50:
                verdict = "Needs Optimization"
            else:
                verdict = "High ATS Rejection Risk"

        return ATSCheckResult(
            overall_score=overall_score,
            verdict=verdict,
            categories=categories,
            feedback=feedback,
            keywords_found=parsed_data.get("keywords_found", []),
            keywords_missing=parsed_data.get("keywords_missing", []),
            recommended_action_verbs=parsed_data.get("recommended_action_verbs", []),
            provider="ollama",
            model=selected_model,
        )

    except (OllamaError, json.JSONDecodeError, Exception) as exc:
        logger.warning(
            "Ollama ATS evaluation unavailable or failed (%s). Falling back to deterministic engine.",
            exc,
        )
        fallback_result = calculate_deterministic_ats_score(
            resume_text=resume_text,
            structured_data=structured_data,
            role=role,
            field=field,
            job_description=job_description,
        )
        return fallback_result
