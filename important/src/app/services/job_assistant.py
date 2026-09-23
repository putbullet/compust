"""
services/job_assistant.py
=========================
Job-Specific Resume & Career Assistant - Core Service.

Architecture:
  - Deterministic layer (always runs, provides reliable fallback)
  - 4-stage LLM pipeline (each stage has focused task + constrained JSON)
  - Anti-hallucination validation (strips LLM output not grounded in candidate data)
  - JSON recovery (regex extraction -> correction retry -> deterministic fallback)

All prompts live in this file, NOT in React components.
"""
from __future__ import annotations

import json
import re
import uuid
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import User, UserSkill, UserExperience, UserEducation, UserLanguage, Resume
from ..services.ai_service import generate_completion, check_ollama_runtime, OllamaUnavailableError, OllamaError
from ..schemas_job_assistant import (
    ApplicationMaterial,
    CandidateContext,
    CandidateContextCertification,
    CandidateContextEducation,
    CandidateContextExperience,
    CandidateContextLanguage,
    CandidateContextProfile,
    CandidateContextProject,
    CandidateContextSkill,
    CandidateEvidenceMatch,
    DeterministicScore,
    ExternalJobInput,
    JobRequirement,
    JobTargetAnalysisResult,
    MatchAnalysis,
    MatchStatus,
    MaterialType,
    RequirementCategory,
    RequirementImportance,
    ResumeRecommendation,
    RecommendationType,
    RegenerateMaterialRequest,
    STARResponse,
    InterviewQuestionType,
    InterviewQuestion,
    InterviewPrep,
)
from ..logging import get_logger

logger = get_logger(__name__)

LANG_NAMES = {"en": "English", "fr": "French", "de": "German", "es": "Spanish"}
LANG_INSTRUCTION = {
    "en": "Respond entirely in English.",
    "fr": "Reponds entierement en francais. Utilise un vocabulaire professionnel naturel.",
    "de": "Antworte vollstaendig auf Deutsch. Verwende professionelle Bewerbungssprache.",
    "es": "Responde completamente en espanol. Usa vocabulario profesional de reclutamiento.",
}

COMMON_TECH_KEYWORDS = {
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust", "kotlin",
    "react", "vue", "angular", "node", "django", "fastapi", "flask", "spring",
    "docker", "kubernetes", "terraform", "ansible", "jenkins", "ci/cd",
    "aws", "azure", "gcp", "cloud", "linux", "bash", "sql", "postgresql", "mysql",
    "mongodb", "redis", "kafka", "rabbitmq", "graphql", "rest", "api", "microservices",
    "machine learning", "deep learning", "pytorch", "tensorflow", "scikit-learn", "nlp",
    "cybersecurity", "security", "penetration testing", "siem", "soc", "splunk",
    "network", "wireshark", "nmap", "metasploit", "owasp", "iso 27001", "gdpr",
    "agile", "scrum", "kanban", "jira", "confluence", "git",
}


import unicodedata

def unaccent(text: str) -> str:
    """Strip accents and diacritics for cross-lingual matching (e.g. développeur -> developpeur)."""
    if not text:
        return ""
    s = text.replace("ß", "ss")
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


ROLE_WORD_CANONICAL: dict[str, str] = {
    # Engineer
    "ingenieur": "engineer", "ingenieure": "engineer", "ingenieurin": "engineer",
    "ingeniero": "engineer", "ingeniera": "engineer", "ingenieure": "engineer", "engineer": "engineer",
    # Developer
    "developpeur": "developer", "developpeuse": "developer", "developpeurs": "developer",
    "entwickler": "developer", "entwicklerin": "developer",
    "desarrollador": "developer", "desarrolladora": "developer", "developer": "developer",
    # Intern / Internship
    "stage": "intern", "stagiaire": "intern", "praktikum": "intern", "praktikant": "intern",
    "praktikantin": "intern", "intern": "intern", "internship": "intern", "pasante": "intern", "pasantia": "intern",
    # Cybersecurity & Security
    "cybersecurite": "cybersecurity", "ciberseguridad": "cybersecurity", "cybersecurity": "cybersecurity",
    "securite": "security", "sicherheit": "security", "seguridad": "security", "security": "security",
    # Software & Systems
    "logiciel": "software", "software": "software",
    "donnees": "data", "daten": "data", "datos": "data", "data": "data",
    "systeme": "system", "system": "system", "sistema": "system",
    "reseau": "network", "netzwerk": "network", "red": "network", "network": "network",
    "architecte": "architect", "architekt": "architect", "arquitecto": "architect", "architect": "architect",
    # Analyst & Consultant
    "analyste": "analyst", "analyst": "analyst", "analista": "analyst",
    "consultant": "consultant", "berater": "consultant", "beraterin": "consultant", "consultor": "consultant", "consultora": "consultant",
    # Manager & Lead
    "manager": "manager", "leiter": "manager", "leiterin": "manager", "gerente": "manager",
    "lead": "lead", "responsable": "lead",
}

ROLE_STOP_WORDS: set[str] = {
    "als", "pour", "with", "and", "und", "para", "les", "des", "the", "ein",
    "eine", "einen", "un", "une", "del", "de", "la", "le", "en", "in", "at", "sur", "von", "zu", "fur", "fuer",
}


def canonicalize_role_token(word: str) -> str:
    clean = unaccent(word.lower().strip())
    return ROLE_WORD_CANONICAL.get(clean, clean)


def canonicalize_role_tokens(title: str) -> set[str]:
    """Tokenize and canonicalize multilingual role titles into normalized concepts."""
    raw_words = [unaccent(w) for w in re.findall(r"\b\w{3,}\b", (title or "").lower())]
    return {canonicalize_role_token(w) for w in raw_words if len(w) > 2 and w not in ROLE_STOP_WORDS}


def normalize_skill(skill: str) -> str:
    return unaccent(skill.strip().lower()).replace("-", " ").replace("_", " ")


def _try_extract_json(text: str) -> dict | list | None:
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    for pattern in [
        r"```json\s*([\s\S]+?)\s*```",
        r"```\s*([\s\S]+?)\s*```",
        r"(\{[\s\S]+\})",
        r"(\[[\s\S]+\])",
    ]:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                continue
    return None


def _safe_str(v: Any) -> str:
    return str(v).strip() if v is not None else ""


# ---------------------------------------------------------------------------
# Candidate context builder
# ---------------------------------------------------------------------------

def build_candidate_context(db: Session, user_id: int, resume: Resume) -> CandidateContext:
    """Merge resume + profile into a validated CandidateContext. Conflicts flagged."""
    from ..repositories.resume import get_canonical_resume_sections
    ctx = CandidateContext()
    structured = resume.structured_data or {}
    canonical_sections = get_canonical_resume_sections(resume)
    res_profile = structured.get("profile", {})

    ctx.profile = CandidateContextProfile(
        full_name=res_profile.get("full_name", ""),
        headline=res_profile.get("headline", ""),
        email=res_profile.get("email", ""),
        phone=res_profile.get("phone", ""),
        location=res_profile.get("location", ""),
        summary=res_profile.get("summary", "") or canonical_sections.get("summary", ""),
        linkedin=res_profile.get("linkedin", ""),
        github=res_profile.get("github", ""),
        website=res_profile.get("website", ""),
    )

    resume_skill_names: set[str] = set()
    raw_skills_source = structured.get("skills") or canonical_sections.get("skills") or []
    for s in raw_skills_source:
        if isinstance(s, dict):
            name = (s.get("name") or s.get("skill") or "").strip()
            cat = s.get("category", "")
            prof = s.get("proficiency") or ""
        elif isinstance(s, str):
            name = s.strip()
            cat = ""
            prof = ""
        else:
            continue
        if name:
            ctx.skills.append(CandidateContextSkill(
                name=name,
                category=cat,
                proficiency=prof,
                source="resume",
            ))
            resume_skill_names.add(normalize_skill(name))

    for exp in structured.get("experience", []):
        ctx.experience.append(CandidateContextExperience(
            id=str(exp.get("id", "")),
            title=exp.get("title", ""),
            company=exp.get("company", ""),
            description=exp.get("description", ""),
            highlights=exp.get("highlights", []),
            start_date=exp.get("start_date", ""),
            end_date=exp.get("end_date", ""),
            source="resume",
        ))

    for edu in structured.get("education", []):
        ctx.education.append(CandidateContextEducation(
            id=str(edu.get("id", "")),
            institution=edu.get("institution", ""),
            degree=edu.get("degree", ""),
            field=edu.get("field", ""),
            description=edu.get("description", ""),
            start_date=edu.get("start_date", ""),
            end_date=edu.get("end_date", ""),
            source="resume",
        ))

    for proj in structured.get("projects", []):
        ctx.projects.append(CandidateContextProject(
            id=str(proj.get("id", "")),
            name=proj.get("name", ""),
            description=proj.get("description", ""),
            technologies=proj.get("technologies", ""),
            source="resume",
        ))

    resume_lang_names: set[str] = set()
    raw_langs_source = structured.get("languages") or canonical_sections.get("languages") or []
    for lang in raw_langs_source:
        if isinstance(lang, dict):
            lname = (lang.get("language") or "").strip()
            lprof = lang.get("proficiency") or ""
        elif isinstance(lang, str):
            lname = lang.strip()
            lprof = ""
        else:
            continue
        if lname:
            ctx.languages.append(CandidateContextLanguage(
                language=lname,
                proficiency=lprof,
                source="resume",
            ))
            resume_lang_names.add(lname.lower())

    for cert in structured.get("certifications", []):
        ctx.certifications.append(CandidateContextCertification(
            id=str(cert.get("id", "")),
            name=cert.get("name", ""),
            issuer=cert.get("issuer", ""),
            source="resume",
        ))

    # Fill gaps from user profile
    user = db.scalar(select(User).where(User.id == user_id))
    if user:
        if not ctx.profile.full_name:
            parts = [p for p in [user.first_name, user.last_name] if p]
            ctx.profile.full_name = " ".join(parts) if parts else (user.email or "")
        if not ctx.profile.email:
            ctx.profile.email = user.email or ""
        if not ctx.profile.phone and user.phone:
            ctx.profile.phone = user.phone

        profile_skills = list(db.scalars(select(UserSkill).where(UserSkill.user_id == user_id)).all())
        for ps in profile_skills:
            norm = normalize_skill(ps.skill or "")
            if not norm:
                continue
            if norm not in resume_skill_names:
                ctx.skills.append(CandidateContextSkill(
                    name=ps.skill,
                    proficiency=ps.proficiency or "",
                    source="profile",
                ))
            else:
                for existing in ctx.skills:
                    if normalize_skill(existing.name) == norm and existing.source == "resume":
                        if ps.proficiency and existing.proficiency and ps.proficiency.lower() != existing.proficiency.lower():
                            ctx.conflicts.append(
                                f"Skill '{ps.skill}': Profile='{ps.proficiency}', Resume='{existing.proficiency}'. Please verify."
                            )
                        elif ps.proficiency and not existing.proficiency:
                            existing.proficiency = ps.proficiency
                        existing.source = "both"

        profile_langs = list(db.scalars(select(UserLanguage).where(UserLanguage.user_id == user_id)).all())
        for pl in profile_langs:
            if pl.language and pl.language.lower() not in resume_lang_names:
                ctx.languages.append(CandidateContextLanguage(
                    language=pl.language,
                    proficiency=pl.proficiency or "",
                    source="profile",
                ))

    return ctx


def _extract_corpus_tokens(ctx: CandidateContext) -> set[str]:
    tokens: set[str] = set()
    for s in ctx.skills:
        tokens.add(normalize_skill(s.name))
        for word in s.name.lower().split():
            tokens.add(word)
    for e in ctx.experience:
        for word in (e.title + " " + e.company + " " + e.description).lower().split():
            tokens.add(word)
        for hl in e.highlights:
            for word in hl.lower().split():
                tokens.add(word)
    for edu in ctx.education:
        for word in (edu.degree + " " + edu.field + " " + edu.institution).lower().split():
            tokens.add(word)
    for p in ctx.projects:
        for word in (p.name + " " + p.description + " " + p.technologies).lower().split():
            tokens.add(word)
    for l in ctx.languages:
        tokens.add(l.language.lower())
    return tokens


def _extract_text_corpus(ctx: CandidateContext) -> str:
    parts = [
        ctx.profile.summary, ctx.profile.headline,
        " ".join(s.name for s in ctx.skills),
        " ".join(f"{e.title} {e.company} {e.description} {' '.join(e.highlights)}" for e in ctx.experience),
        " ".join(f"{edu.degree} {edu.field} {edu.institution}" for edu in ctx.education),
        " ".join(f"{p.name} {p.description} {p.technologies}" for p in ctx.projects),
        " ".join(c.name for c in ctx.certifications),
    ]
    return " ".join(p for p in parts if p).lower()


# ---------------------------------------------------------------------------
# Deterministic scoring
# ---------------------------------------------------------------------------

def deterministic_score(ctx: CandidateContext, job_input: ExternalJobInput) -> DeterministicScore:
    """Reproducible 0-10 category scores. No LLM involved."""
    job_lower = (job_input.job_description + " " + job_input.target_role).lower()
    candidate_text = _extract_text_corpus(ctx)

    job_tech = {w for w in COMMON_TECH_KEYWORDS if w in job_lower}
    if job_tech:
        matched_tech = sum(1 for t in job_tech if t in candidate_text)
        tech_score = round(min(10, (matched_tech / len(job_tech)) * 10), 1)
    else:
        tech_score = 7.0

    # Multilingual-aware role keyword extraction
    job_canonical_tokens = canonicalize_role_tokens(job_input.target_role)

    if ctx.experience and job_canonical_tokens:
        exp_full_text = " ".join(f"{e.title} {e.description} {' '.join(e.highlights)}" for e in ctx.experience).lower()
        exp_raw_words = [unaccent(w) for w in re.findall(r"\b\w{3,}\b", exp_full_text)]
        exp_canonical_tokens = {canonicalize_role_token(w) for w in exp_raw_words if w not in ROLE_STOP_WORDS}
        matched_exp = sum(
            1 for tok in job_canonical_tokens
            if tok in exp_canonical_tokens or any(tok in ew for ew in exp_canonical_tokens)
        )
        exp_score = round(min(10, (matched_exp / len(job_canonical_tokens)) * 10), 1)
    elif ctx.experience:
        exp_score = 5.0
    else:
        exp_score = 0.0

    edu_score = 8.0 if ctx.education else 3.0

    lang_keywords = {
        "english", "french", "german", "spanish", "arabic", "mandarin",
        "anglais", "francais", "allemand", "espagnol",
        "englisch", "deutsch", "spanisch",
    }
    job_langs = {w for w in lang_keywords if w in job_lower}
    if job_langs:
        candidate_langs_norm = {l.language.lower() for l in ctx.languages}
        matched_langs = sum(1 for jl in job_langs if any(jl in cl or cl in jl for cl in candidate_langs_norm))
        lang_score = round(min(10, (matched_langs / len(job_langs)) * 10 + 4), 1)
    else:
        lang_score = 7.0 if ctx.languages else 5.0

    ats_in_job = {w for w in COMMON_TECH_KEYWORDS if w in job_lower}
    if ats_in_job:
        ats_matched = sum(1 for k in ats_in_job if k in candidate_text)
        ats_score = round(min(10, (ats_matched / len(ats_in_job)) * 10), 1)
    else:
        ats_score = 6.0

    overall = round(tech_score * 0.35 + exp_score * 0.25 + edu_score * 0.15 + lang_score * 0.1 + ats_score * 0.15, 1)
    return DeterministicScore(
        technical_skills=tech_score,
        experience_alignment=exp_score,
        education=edu_score,
        languages=lang_score,
        ats_keywords=ats_score,
        overall=overall,
    )


def deterministic_match(ctx: CandidateContext, job_input: ExternalJobInput) -> MatchAnalysis:
    """Fallback match analysis using keyword matching."""
    job_lower = (job_input.job_description + " " + job_input.target_role).lower()
    candidate_text = _extract_text_corpus(ctx)
    candidate_skills_norm = {normalize_skill(s.name): s for s in ctx.skills}
    analysis = MatchAnalysis()
    job_tech = {w for w in COMMON_TECH_KEYWORDS if w in job_lower}
    for tech in sorted(job_tech):
        if tech in candidate_text:
            matching = [s for norm, s in candidate_skills_norm.items() if tech in norm or norm in tech]
            sources = [f"Resume -> Skills -> {s.name}" for s in matching[:2]]
            if not sources:
                sources = ["Resume -> Experience (mentioned in description)"]
            analysis.strong_matches.append(CandidateEvidenceMatch(
                requirement=tech,
                requirement_category=RequirementCategory.TECHNICAL_SKILL,
                match_status=MatchStatus.STRONG,
                evidence_sources=sources,
            ))
        else:
            analysis.missing_or_unconfirmed.append(CandidateEvidenceMatch(
                requirement=tech,
                requirement_category=RequirementCategory.TECHNICAL_SKILL,
                match_status=MatchStatus.MISSING,
                note="Not found in your current Compust data.",
            ))
    return analysis


def _fallback_extract_requirements(job_input: ExternalJobInput) -> list[JobRequirement]:
    """Deterministic keyword-based requirement extraction."""
    job_lower = (job_input.job_description + " " + job_input.target_role).lower()
    requirements = []
    for tech in sorted(COMMON_TECH_KEYWORDS):
        if re.search(rf"\b{re.escape(tech)}\b", job_lower):
            requirements.append(JobRequirement(
                text=tech.title(),
                category=RequirementCategory.TECHNICAL_SKILL,
                importance=RequirementImportance.REQUIRED,
                raw_keyword=tech,
            ))
    return requirements[:25]


def _build_candidate_text_sections(ctx: CandidateContext) -> dict[str, str]:
    skills_text = ", ".join(
        f"{s.name} ({s.proficiency})" if s.proficiency else s.name
        for s in ctx.skills
    )
    exp_text = "\n".join(
        f"- {e.title} at {e.company} ({e.start_date}-{e.end_date}): {e.description[:200]}"
        for e in ctx.experience
    )
    edu_text = "\n".join(
        f"- {e.degree} in {e.field} at {e.institution}" for e in ctx.education
    )
    proj_text = "\n".join(
        f"- {p.name}: {p.description[:150]} [{p.technologies}]" for p in ctx.projects
    )
    lang_text = ", ".join(
        f"{l.language} ({l.proficiency})" if l.proficiency else l.language
        for l in ctx.languages
    )
    cert_text = ", ".join(c.name for c in ctx.certifications)
    return {
        "skills": skills_text or "None listed",
        "experience": exp_text or "None listed",
        "education": edu_text or "None listed",
        "projects": proj_text or "None listed",
        "languages": lang_text or "None listed",
        "certifications": cert_text or "None listed",
    }


# ---------------------------------------------------------------------------
# Stage 1 - Extract job requirements
# ---------------------------------------------------------------------------

STAGE1_SYSTEM = (
    "You are a precise job requirements extractor.\n"
    "RULES:\n"
    "1. Read the job description carefully.\n"
    "2. Extract ALL requirements: skills, tools, education, experience, languages, certifications.\n"
    "3. Return ONLY valid JSON. No explanation. No markdown.\n"
    "4. NEVER invent requirements not stated in the job description.\n"
    "5. Classify each: technical_skill, tool, methodology, education, experience, language, certification, domain, soft_skill, ats_keyword, other\n"
    "6. Classify importance: required, preferred, nice_to_have"
)

STAGE1_TEMPLATE = (
    "=== TARGET JOB ===\n"
    "TITLE: {title}\n"
    "DESCRIPTION:\n{description}\n\n"
    "{additional}\n\n"
    "{lang_instruction}\n\n"
    'Return JSON with this exact structure:\n'
    '{{"requirements": [{{"text": "skill name", "category": "technical_skill", "importance": "required", "raw_keyword": "keyword"}}]}}'
)


def _stage1_extract_requirements(job_input: ExternalJobInput, model: str | None = None) -> list[JobRequirement]:
    lang = job_input.language.value
    additional = f"ADDITIONAL INFORMATION:\n{job_input.additional_information}" if job_input.additional_information else ""
    prompt = STAGE1_TEMPLATE.format(
        title=job_input.target_role,
        description=job_input.job_description[:4000],
        additional=additional,
        lang_instruction=LANG_INSTRUCTION.get(lang, LANG_INSTRUCTION["en"]),
    )
    raw = generate_completion(prompt, system_prompt=STAGE1_SYSTEM, model=model, temperature=0.05, timeout_seconds=30.0)
    data = _try_extract_json(raw)
    requirements: list[JobRequirement] = []
    if isinstance(data, dict) and "requirements" in data:
        for item in data["requirements"]:
            if not isinstance(item, dict):
                continue
            text = _safe_str(item.get("text"))
            if not text:
                continue
            try:
                cat = RequirementCategory(item.get("category", "other"))
            except ValueError:
                cat = RequirementCategory.OTHER
            try:
                imp = RequirementImportance(item.get("importance", "required"))
            except ValueError:
                imp = RequirementImportance.REQUIRED
            requirements.append(JobRequirement(
                text=text, category=cat, importance=imp,
                raw_keyword=_safe_str(item.get("raw_keyword", text)),
            ))
    if not requirements:
        requirements = _fallback_extract_requirements(job_input)
    return requirements[:40]


# ---------------------------------------------------------------------------
# Stage 2 - Match candidate to requirements
# ---------------------------------------------------------------------------

STAGE2_SYSTEM = (
    "You are a precise CV analyst. You compare job requirements against ONLY the provided candidate data.\n"
    "RULES:\n"
    "1. Use ONLY the candidate information provided. NEVER invent skills, experience, or qualifications.\n"
    "2. For each requirement: strong (clearly evidenced), partial (partially mentioned), missing (not found), verify (ambiguous).\n"
    "3. If not mentioned anywhere in candidate data, it is MISSING.\n"
    "4. Quote the specific evidence from the candidate data.\n"
    "5. Return ONLY valid JSON."
)

STAGE2_TEMPLATE = (
    "=== REQUIREMENTS TO MATCH ===\n{requirements_json}\n\n"
    "=== CANDIDATE DATA ===\n"
    "NAME: {name}\nSUMMARY: {summary}\nSKILLS: {skills}\n"
    "EXPERIENCE:\n{experience}\nEDUCATION:\n{education}\n"
    "PROJECTS:\n{projects}\nLANGUAGES: {languages}\nCERTIFICATIONS: {certifications}\n\n"
    "{lang_instruction}\n\n"
    'Return JSON:\n{{"matches": [{{"requirement": "text", "match_status": "strong|partial|missing|verify", "evidence_sources": ["source"], "note": "explanation"}}]}}'
)


def _stage2_match_candidate(
    requirements: list[JobRequirement],
    ctx: CandidateContext,
    lang: str,
    model: str | None = None,
) -> MatchAnalysis:
    if not requirements:
        return deterministic_match(ctx, ExternalJobInput(target_role="", job_description="x" * 50))
    sections = _build_candidate_text_sections(ctx)
    req_json = json.dumps([{"requirement": r.text, "category": r.category.value} for r in requirements[:20]], ensure_ascii=False)
    prompt = STAGE2_TEMPLATE.format(
        requirements_json=req_json,
        name=ctx.profile.full_name,
        summary=ctx.profile.summary[:400] or "No summary",
        skills=sections["skills"][:600],
        experience=sections["experience"][:800],
        education=sections["education"][:400],
        projects=sections["projects"][:400],
        languages=sections["languages"][:200],
        certifications=sections["certifications"][:200],
        lang_instruction=LANG_INSTRUCTION.get(lang, LANG_INSTRUCTION["en"]),
    )
    raw = generate_completion(prompt, system_prompt=STAGE2_SYSTEM, model=model, temperature=0.05, timeout_seconds=35.0)
    data = _try_extract_json(raw)
    analysis = MatchAnalysis()
    candidate_corpus = _extract_corpus_tokens(ctx)
    if isinstance(data, dict) and "matches" in data:
        for item in data["matches"]:
            if not isinstance(item, dict):
                continue
            req_text = _safe_str(item.get("requirement"))
            try:
                status = MatchStatus(item.get("match_status", "unknown"))
            except ValueError:
                status = MatchStatus.UNKNOWN
            evidence = item.get("evidence_sources") or []
            if isinstance(evidence, str):
                evidence = [evidence]
            evidence = [str(e) for e in evidence][:4]
            # Anti-hallucination: downgrade unverifiable strong/partial to VERIFY
            req_lower = req_text.lower()
            if status in (MatchStatus.STRONG, MatchStatus.PARTIAL):
                found = any(req_lower in t or t in req_lower for t in candidate_corpus if len(t) > 2)
                if not found:
                    status = MatchStatus.VERIFY
            match = CandidateEvidenceMatch(
                requirement=req_text, match_status=status,
                evidence_sources=evidence, note=_safe_str(item.get("note", "")),
            )
            if status == MatchStatus.STRONG:
                analysis.strong_matches.append(match)
            elif status == MatchStatus.PARTIAL:
                analysis.partial_matches.append(match)
            elif status == MatchStatus.MISSING:
                analysis.missing_or_unconfirmed.append(match)
            else:
                analysis.verify_items.append(match)
    # Ensure all requirements are accounted for
    accounted = {
        m.requirement.lower()
        for m in analysis.strong_matches + analysis.partial_matches + analysis.missing_or_unconfirmed + analysis.verify_items
    }
    for req in requirements:
        if req.text.lower() not in accounted:
            found = any(req.text.lower() in t or t in req.text.lower() for t in candidate_corpus if len(t) > 2)
            analysis.missing_or_unconfirmed.append(CandidateEvidenceMatch(
                requirement=req.text,
                match_status=MatchStatus.STRONG if found else MatchStatus.MISSING,
                note="" if found else "Not found in your current Compust data.",
            ))
    return analysis


# ---------------------------------------------------------------------------
# Stage 3 - Resume recommendations
# ---------------------------------------------------------------------------

STAGE3_SYSTEM = (
    "You are an expert career coach and resume consultant.\n"
    "RULES:\n"
    "1. Use ONLY the candidate data provided. NEVER invent skills, experience, jobs, or qualifications.\n"
    "2. If a recommendation adds new content, it must be sourced from the candidate data.\n"
    "3. For MISSING requirements: say 'Not found in your current Compust data.' Do NOT add them to the resume.\n"
    "4. Be specific and actionable. Do not say 'Improve your resume' without specifics.\n"
    "5. Return ONLY valid JSON."
)

STAGE3_TEMPLATE = (
    "=== TARGET JOB ===\nROLE: {role}\nDESCRIPTION EXCERPT: {desc_excerpt}\n\n"
    "=== MATCH SUMMARY ===\nSTRONG MATCHES: {strong}\nPARTIAL MATCHES: {partial}\nMISSING: {missing}\n\n"
    "=== CANDIDATE RESUME ===\nSUMMARY: {summary}\nSKILLS: {skills}\nEXPERIENCE:\n{experience}\nPROJECTS:\n{projects}\nEDUCATION: {education}\n\n"
    "{lang_instruction}\n\n"
    'Generate resume recommendations. Return JSON:\n'
    '{{"recommendations": [{{"rec_type": "emphasize|rewrite|keep|move|missing|verify|add|reduce|remove", "section": "summary|skills|experience|projects|education", "item_id": "id or empty", "item_label": "label", "current_text": "current", "suggested_text": "improved text", "reason": "why", "evidence_sources": ["source"]}}]}}'
)


def _stage3_recommendations(
    requirements: list[JobRequirement],
    match_analysis: MatchAnalysis,
    ctx: CandidateContext,
    job_input: ExternalJobInput,
    model: str | None = None,
) -> list[ResumeRecommendation]:
    lang = job_input.language.value
    sections = _build_candidate_text_sections(ctx)
    strong_str = ", ".join(m.requirement for m in match_analysis.strong_matches[:10])
    partial_str = ", ".join(m.requirement for m in match_analysis.partial_matches[:8])
    missing_str = ", ".join(m.requirement for m in match_analysis.missing_or_unconfirmed[:8])
    exp_detail = "\n".join(f"[ID:{e.id}] {e.title} at {e.company}: {e.description[:250]}" for e in ctx.experience)
    proj_detail = "\n".join(f"[ID:{p.id}] {p.name}: {p.description[:200]} [{p.technologies}]" for p in ctx.projects)
    edu_detail = " | ".join(f"{e.degree} in {e.field} at {e.institution}" for e in ctx.education)
    prompt = STAGE3_TEMPLATE.format(
        role=job_input.target_role, desc_excerpt=job_input.job_description[:1500],
        strong=strong_str or "None", partial=partial_str or "None", missing=missing_str or "None",
        summary=ctx.profile.summary[:500] or "No summary", skills=sections["skills"][:500],
        experience=exp_detail[:800], projects=proj_detail[:600], education=edu_detail[:300],
        lang_instruction=LANG_INSTRUCTION.get(lang, LANG_INSTRUCTION["en"]),
    )
    raw = generate_completion(prompt, system_prompt=STAGE3_SYSTEM, model=model, temperature=0.1, timeout_seconds=40.0)
    data = _try_extract_json(raw)
    recommendations: list[ResumeRecommendation] = []
    candidate_corpus = _extract_corpus_tokens(ctx)
    if isinstance(data, dict) and "recommendations" in data:
        for item in data["recommendations"]:
            if not isinstance(item, dict):
                continue
            try:
                rec_type = RecommendationType(item.get("rec_type", "verify"))
            except ValueError:
                rec_type = RecommendationType.VERIFY
            suggested_text = _safe_str(item.get("suggested_text", ""))
            reason = _safe_str(item.get("reason", ""))
            grounded = True
            if rec_type in (RecommendationType.ADD, RecommendationType.REWRITE, RecommendationType.EMPHASIZE) and suggested_text:
                sug_words = {w for w in suggested_text.lower().split() if len(w) > 3}
                overlap = sug_words & candidate_corpus
                if len(overlap) < min(2, max(1, len(sug_words) // 3)):
                    grounded = False
                    rec_type = RecommendationType.VERIFY
                    reason += " [Verify: suggested content could not be confirmed in your data.]"
            evidence = item.get("evidence_sources") or []
            if isinstance(evidence, str):
                evidence = [evidence]
            recommendations.append(ResumeRecommendation(
                id=str(uuid.uuid4())[:8],
                rec_type=rec_type,
                section=_safe_str(item.get("section", "")),
                item_id=_safe_str(item.get("item_id", "")),
                item_label=_safe_str(item.get("item_label", "")),
                current_text=_safe_str(item.get("current_text", "")),
                suggested_text=suggested_text,
                reason=reason,
                evidence_sources=[str(e) for e in evidence][:4],
                grounded=grounded,
            ))
    # Always add missing as MISSING recs
    for match in match_analysis.missing_or_unconfirmed:
        recommendations.append(ResumeRecommendation(
            id=str(uuid.uuid4())[:8],
            rec_type=RecommendationType.MISSING,
            section="skills", item_label=match.requirement,
            reason=f"Not found in your current Compust data. Only add if you genuinely have experience with {match.requirement}.",
        ))
    return recommendations[:25]


def _fallback_recommendations(match_analysis: MatchAnalysis, ctx: CandidateContext, job_input: ExternalJobInput) -> list[ResumeRecommendation]:
    recs: list[ResumeRecommendation] = []
    for match in match_analysis.strong_matches[:5]:
        recs.append(ResumeRecommendation(
            id=str(uuid.uuid4())[:8], rec_type=RecommendationType.EMPHASIZE,
            section="skills", item_label=match.requirement,
            reason=f"Your existing {match.requirement} experience is relevant to this role.",
            evidence_sources=match.evidence_sources,
        ))
    for match in match_analysis.missing_or_unconfirmed:
        recs.append(ResumeRecommendation(
            id=str(uuid.uuid4())[:8], rec_type=RecommendationType.MISSING,
            section="skills", item_label=match.requirement,
            reason=f"Not found in your current Compust data. Only add if you genuinely have experience with {match.requirement}.",
        ))
    return recs[:15]


# ---------------------------------------------------------------------------
# Stage 4 - Application materials
# ---------------------------------------------------------------------------

STAGE4_SYSTEM = (
    "You are a professional job application writer.\n"
    "RULES:\n"
    "1. Use ONLY the candidate information provided. NEVER invent companies, titles, skills, or achievements.\n"
    "2. Do NOT fabricate knowledge about the target company if not provided.\n"
    "3. Use clear placeholder brackets for unknowns: [RECRUITER NAME], [COMPANY NAME], etc.\n"
    "4. Be professional, concise, and specific.\n"
    "5. Return ONLY valid JSON."
)

STAGE4_TEMPLATE = (
    "=== TARGET JOB ===\nROLE: {role}\nCOMPANY INFO: {company_info}\n\n"
    "=== CANDIDATE ===\nNAME: {name}\nHEADLINE: {headline}\nSUMMARY: {summary}\n"
    "KEY SKILLS: {top_skills}\nRELEVANT EXPERIENCE:\n{top_experience}\nEDUCATION: {education}\nLANGUAGES: {languages}\n\n"
    "{lang_instruction}\n\n"
    'Generate three materials. Use [PLACEHOLDER] for unknowns.\n'
    'Return JSON: {{"cold_email": {{"subject": "...", "body": "...", "placeholders": ["..."]}}, '
    '"short_message": {{"body": "under 100 words", "placeholders": ["..."]}}, '
    '"motivation_letter": {{"body": "4 paragraphs", "placeholders": ["..."]}}}}'
)


def _stage4_materials(ctx: CandidateContext, job_input: ExternalJobInput, model: str | None = None):
    lang = job_input.language.value
    top_skills = ", ".join(s.name for s in ctx.skills[:10])
    top_exp = "\n".join(f"- {e.title} at {e.company}" for e in ctx.experience[:3]) or "No experience listed"
    edu_str = ", ".join(f"{e.degree} in {e.field} at {e.institution}" for e in ctx.education[:2]) or "Not listed"
    lang_str = ", ".join(l.language for l in ctx.languages) or ""
    company_info = job_input.additional_information or "[Company details not provided]"
    prompt = STAGE4_TEMPLATE.format(
        role=job_input.target_role,
        company_info=company_info[:400],
        name=ctx.profile.full_name or "[YOUR NAME]",
        headline=ctx.profile.headline or "",
        summary=ctx.profile.summary[:400] or "",
        top_skills=top_skills[:400],
        top_experience=top_exp[:500],
        education=edu_str[:300],
        languages=lang_str[:200],
        lang_instruction=LANG_INSTRUCTION.get(lang, LANG_INSTRUCTION["en"]),
    )
    raw = generate_completion(prompt, system_prompt=STAGE4_SYSTEM, model=model, temperature=0.2, timeout_seconds=45.0)
    data = _try_extract_json(raw)

    def _make(mtype: MaterialType, d) -> ApplicationMaterial:
        if not d or not isinstance(d, dict):
            return ApplicationMaterial(material_type=mtype, language=lang, generated=False, error="Generation failed")
        body = _safe_str(d.get("body", ""))
        subject = _safe_str(d.get("subject", ""))
        phs = d.get("placeholders") or []
        if isinstance(phs, str):
            phs = [phs]
        auto_phs = re.findall(r"\[[A-Z ]{3,}\]", body)
        all_phs = list(dict.fromkeys([str(p) for p in phs] + auto_phs))
        return ApplicationMaterial(
            material_type=mtype, subject=subject, body=body,
            placeholders=all_phs, language=lang, generated=bool(body),
            error="" if body else "No content generated",
        )

    if isinstance(data, dict):
        return (
            _make(MaterialType.COLD_EMAIL, data.get("cold_email")),
            _make(MaterialType.SHORT_MESSAGE, data.get("short_message")),
            _make(MaterialType.MOTIVATION_LETTER, data.get("motivation_letter")),
        )
    err_msg = "LLM returned invalid output"
    return (
        ApplicationMaterial(material_type=MaterialType.COLD_EMAIL, language=lang, generated=False, error=err_msg),
        ApplicationMaterial(material_type=MaterialType.SHORT_MESSAGE, language=lang, generated=False, error=err_msg),
        ApplicationMaterial(material_type=MaterialType.MOTIVATION_LETTER, language=lang, generated=False, error=err_msg),
    )


STAGE4_SINGLE_TEMPLATES = {
    MaterialType.COLD_EMAIL: (
        "=== TARGET JOB ===\nROLE: {role}\nCOMPANY INFO: {company_info}\n\n"
        "=== CANDIDATE ===\nNAME: {name}\nHEADLINE: {headline}\nSUMMARY: {summary}\n"
        "KEY SKILLS: {top_skills}\nRELEVANT EXPERIENCE:\n{top_experience}\nEDUCATION: {education}\nLANGUAGES: {languages}\n\n"
        "{lang_instruction}\n\n"
        "Generate a targeted cold outreach email from candidate to hiring manager/recruiter. Use [PLACEHOLDER] for unknowns.\n"
        'Return JSON: {{"cold_email": {{"subject": "...", "body": "...", "placeholders": ["..."]}}}}'
    ),
    MaterialType.SHORT_MESSAGE: (
        "=== TARGET JOB ===\nROLE: {role}\nCOMPANY INFO: {company_info}\n\n"
        "=== CANDIDATE ===\nNAME: {name}\nHEADLINE: {headline}\nSUMMARY: {summary}\n"
        "KEY SKILLS: {top_skills}\nRELEVANT EXPERIENCE:\n{top_experience}\nEDUCATION: {education}\nLANGUAGES: {languages}\n\n"
        "{lang_instruction}\n\n"
        "Generate a concise networking direct message (under 100 words) for LinkedIn or email. Use [PLACEHOLDER] for unknowns.\n"
        'Return JSON: {{"short_message": {{"body": "under 100 words", "placeholders": ["..."]}}}}'
    ),
    MaterialType.MOTIVATION_LETTER: (
        "=== TARGET JOB ===\nROLE: {role}\nCOMPANY INFO: {company_info}\n\n"
        "=== CANDIDATE ===\nNAME: {name}\nHEADLINE: {headline}\nSUMMARY: {summary}\n"
        "KEY SKILLS: {top_skills}\nRELEVANT EXPERIENCE:\n{top_experience}\nEDUCATION: {education}\nLANGUAGES: {languages}\n\n"
        "{lang_instruction}\n\n"
        "Generate a formal 4-paragraph cover/motivation letter. Use [PLACEHOLDER] for unknowns.\n"
        'Return JSON: {{"motivation_letter": {{"subject": "...", "body": "4 paragraphs", "placeholders": ["..."]}}}}'
    ),
}


def regenerate_single_material(
    db: Session,
    user_id: int,
    resume: Resume,
    request: RegenerateMaterialRequest,
) -> ApplicationMaterial:
    """
    Regenerate a single application material (Cold Email, Short DM, or Motivation Letter).
    Extracts candidate context and prompts the local LLM with high efficiency.
    """
    lang = request.language.value
    runtime = check_ollama_runtime()
    ollama_available = runtime.get("status") == "connected" and bool(runtime.get("models"))
    model = runtime.get("selected_model")

    if not ollama_available:
        return ApplicationMaterial(
            material_type=request.material_type,
            language=lang,
            generated=False,
            error="Local AI unavailable. Start Ollama to generate application materials.",
        )

    ctx = build_candidate_context(db, user_id, resume)
    top_skills = ", ".join(s.name for s in ctx.skills[:10])
    top_exp = "\n".join(f"- {e.title} at {e.company}" for e in ctx.experience[:3]) or "No experience listed"
    edu_str = ", ".join(f"{e.degree} in {e.field} at {e.institution}" for e in ctx.education[:2]) or "Not listed"
    lang_str = ", ".join(l.language for l in ctx.languages) or ""
    company_info = request.additional_information or "[Company details not provided]"

    template = STAGE4_SINGLE_TEMPLATES.get(request.material_type, STAGE4_SINGLE_TEMPLATES[MaterialType.COLD_EMAIL])
    prompt = template.format(
        role=request.target_role,
        company_info=company_info[:400],
        name=ctx.profile.full_name or "[YOUR NAME]",
        headline=ctx.profile.headline or "",
        summary=ctx.profile.summary[:400] or "",
        top_skills=top_skills[:400],
        top_experience=top_exp[:500],
        education=edu_str[:300],
        languages=lang_str[:200],
        lang_instruction=LANG_INSTRUCTION.get(lang, LANG_INSTRUCTION["en"]),
    )

    try:
        raw = generate_completion(prompt, system_prompt=STAGE4_SYSTEM, model=model, temperature=0.25, timeout_seconds=45.0)
        data = _try_extract_json(raw)
        m_data = None
        if isinstance(data, dict):
            m_data = data.get(request.material_type.value) or data.get("material") or data

        if isinstance(m_data, dict):
            body = _safe_str(m_data.get("body", ""))
            subject = _safe_str(m_data.get("subject", ""))
            phs = m_data.get("placeholders") or []
            if isinstance(phs, str):
                phs = [phs]
            auto_phs = re.findall(r"\[[A-Z ]{3,}\]", body)
            all_phs = list(dict.fromkeys([str(p) for p in phs] + auto_phs))
            return ApplicationMaterial(
                material_type=request.material_type,
                subject=subject,
                body=body,
                placeholders=all_phs,
                language=lang,
                generated=bool(body),
                error="" if body else "No content generated",
            )
        return ApplicationMaterial(
            material_type=request.material_type,
            language=lang,
            generated=False,
            error="LLM returned invalid output format",
        )
    except Exception as exc:
        logger.error(f"Failed to regenerate single material: {exc}")
        return ApplicationMaterial(
            material_type=request.material_type,
            language=lang,
            generated=False,
            error=f"Generation failed: {exc}",
        )


# ---------------------------------------------------------------------------
# Stage 5 - Interview & STAR Prep
# ---------------------------------------------------------------------------

STAGE5_SYSTEM = (
    "You are an executive career coach and technical interviewer.\n"
    "RULES:\n"
    "1. Ground all behavioral examples in the candidate's actual projects and experience.\n"
    "2. NEVER invent experience or companies the candidate did not work at.\n"
    "3. For missing requirements, give honest, constructive advice on how to answer questions about gaps without bluffing.\n"
    "4. Format STAR responses clearly: Situation, Task, Action, Result.\n"
    "5. Return ONLY valid JSON."
)

STAGE5_TEMPLATE = (
    "=== TARGET ROLE ===\n{role}\n\n"
    "=== JOB REQUIREMENTS ===\n{requirements}\n\n"
    "=== CANDIDATE PROFILE ===\nNAME: {name}\nHEADLINE: {headline}\n"
    "SKILLS: {skills}\n"
    "EXPERIENCE:\n{experience}\n"
    "PROJECTS:\n{projects}\n\n"
    "=== MISSING OR UNCONFIRMED REQUIREMENTS ===\n{missing}\n\n"
    "{lang_instruction}\n\n"
    "Generate 3 to 5 high-yield interview questions (technical, behavioral, and gap-handling).\n"
    "Return JSON format:\n"
    '{{\n'
    '  "key_focus_areas": ["focus 1", "focus 2"],\n'
    '  "confidence_tip": "One concise encouraging tip",\n'
    '  "questions": [\n'
    '    {{\n'
    '      "question": "Tell me about a time you...",\n'
    '      "question_type": "behavioral|technical|qualification_gap|domain",\n'
    '      "category": "Architecture|Leadership|FastAPI|...",\n'
    '      "context_reason": "Why the interviewer will ask this",\n'
    '      "suggested_star": {{\n'
    '        "situation": "...",\n'
    '        "task": "...",\n'
    '        "action": "...",\n'
    '        "result": "..."\n'
    '      }},\n'
    '      "handling_missing_skill": "Advice on addressing this gap honestly if applicable, or empty"\n'
    '    }}\n'
    '  ]\n'
    '}}'
)


def _fallback_interview_prep(
    ctx: CandidateContext,
    job_input: ExternalJobInput,
    match_analysis: MatchAnalysis,
) -> InterviewPrep:
    questions: list[InterviewQuestion] = []

    # 1. Behavioral Question from experience
    if ctx.experience:
        top_exp = ctx.experience[0]
        desc_snippet = (top_exp.description or "").split(".")[0]
        questions.append(InterviewQuestion(
            id=str(uuid.uuid4())[:8],
            question=f"Can you walk me through your time as {top_exp.title} at {top_exp.company}, specifically a key challenge you solved?",
            question_type=InterviewQuestionType.BEHAVIORAL,
            category="Experience",
            context_reason=f"Directly relevant to your background at {top_exp.company}.",
            suggested_star=STARResponse(
                situation=f"While serving as {top_exp.title} at {top_exp.company}.",
                task=f"Handling key responsibilities including {desc_snippet or 'core system implementation'}.",
                action="Applied structured problem-solving, collaborated across teams, and iteratively verified delivery quality.",
                result=top_exp.highlights[0] if top_exp.highlights else "Delivered the initiative on schedule with positive stakeholder feedback.",
            ),
        ))

    # 2. Technical Question from matched requirements
    matched_tech = [m.requirement for m in match_analysis.strong_matches if m.requirement_category == RequirementCategory.TECHNICAL_SKILL]
    if matched_tech:
        primary_tech = matched_tech[0]
        questions.append(InterviewQuestion(
            id=str(uuid.uuid4())[:8],
            question=f"How do you ensure reliability, performance, and maintainability when working with {primary_tech}?",
            question_type=InterviewQuestionType.TECHNICAL,
            category=primary_tech,
            context_reason=f"{primary_tech} is a verified requirement for the {job_input.target_role} role.",
            suggested_star=STARResponse(
                situation=f"When building software components requiring {primary_tech}.",
                task="Ensure high availability, test coverage, and clean modular architecture.",
                action=f"Adopt idiomatic {primary_tech} best practices, write comprehensive unit tests, and monitor critical paths.",
                result="Resilient system architecture that performs reliably in production.",
            ),
        ))

    # 3. Qualification Gap / Missing Skill Handling
    if match_analysis.missing_or_unconfirmed:
        missing_req = match_analysis.missing_or_unconfirmed[0].requirement
        questions.append(InterviewQuestion(
            id=str(uuid.uuid4())[:8],
            question=f"The job requires experience with {missing_req}. How familiar are you with this and how would you approach it?",
            question_type=InterviewQuestionType.QUALIFICATION_GAP,
            category=missing_req,
            context_reason=f"{missing_req} was not confirmed in your current Compust profile data.",
            suggested_star=STARResponse(
                situation="When asked about a framework or tool you haven't deployed in enterprise production yet.",
                task="Maintain total honesty while highlighting rapid ramp-up capability.",
                action=f"Acknowledge: 'While I have not utilized {missing_req} extensively in production, my deep foundation in {matched_tech[0] if matched_tech else 'related software primitives'} enables me to quickly master new toolchains. I have reviewed its documentation and standard design patterns.'",
                result="Builds immediate interviewer trust and demonstrates learning agility.",
            ),
            handling_missing_skill=f"Never bluff about {missing_req}. Highlight your related technical skills and demonstrate enthusiasm to learn.",
        ))

    focus_areas = [m.requirement for m in match_analysis.strong_matches[:3]]
    if not focus_areas:
        focus_areas = [job_input.target_role, "Problem Solving"]

    return InterviewPrep(
        questions=questions,
        key_focus_areas=focus_areas,
        confidence_tip=f"Your verified background gives you a concrete foundation for {job_input.target_role}. Stay concise and quantify your achievements with data.",
    )


def _stage5_interview_prep(
    ctx: CandidateContext,
    job_input: ExternalJobInput,
    match_analysis: MatchAnalysis,
    model: str | None = None,
) -> InterviewPrep:
    lang = job_input.language.value
    sections = _build_candidate_text_sections(ctx)
    strong_str = ", ".join(m.requirement for m in match_analysis.strong_matches[:8])
    missing_str = ", ".join(m.requirement for m in match_analysis.missing_or_unconfirmed[:5])
    exp_detail = "\n".join(f"- {e.title} at {e.company}: {e.description[:200]}" for e in ctx.experience[:3]) or "None"
    proj_detail = "\n".join(f"- {p.name}: {p.description[:150]}" for p in ctx.projects[:2]) or "None"

    prompt = STAGE5_TEMPLATE.format(
        role=job_input.target_role,
        requirements=strong_str or job_input.target_role,
        name=ctx.profile.full_name or "Candidate",
        headline=ctx.profile.headline or "",
        skills=sections["skills"][:400],
        experience=exp_detail[:600],
        projects=proj_detail[:400],
        missing=missing_str or "None identified",
        lang_instruction=LANG_INSTRUCTION.get(lang, LANG_INSTRUCTION["en"]),
    )

    try:
        raw = generate_completion(prompt, system_prompt=STAGE5_SYSTEM, model=model, temperature=0.2, timeout_seconds=40.0)
        data = _try_extract_json(raw)
        if isinstance(data, dict) and "questions" in data and isinstance(data["questions"], list):
            parsed_questions: list[InterviewQuestion] = []
            for q in data["questions"]:
                if not isinstance(q, dict):
                    continue
                q_type_str = str(q.get("question_type", "behavioral")).lower()
                try:
                    q_type = InterviewQuestionType(q_type_str)
                except ValueError:
                    q_type = InterviewQuestionType.BEHAVIORAL

                star_data = q.get("suggested_star") or {}
                star = STARResponse(
                    situation=_safe_str(star_data.get("situation", "")),
                    task=_safe_str(star_data.get("task", "")),
                    action=_safe_str(star_data.get("action", "")),
                    result=_safe_str(star_data.get("result", "")),
                )
                parsed_questions.append(InterviewQuestion(
                    id=str(uuid.uuid4())[:8],
                    question=_safe_str(q.get("question", "")),
                    question_type=q_type,
                    category=_safe_str(q.get("category", "")),
                    context_reason=_safe_str(q.get("context_reason", "")),
                    suggested_star=star,
                    handling_missing_skill=_safe_str(q.get("handling_missing_skill", "")),
                ))
            if parsed_questions:
                focus = data.get("key_focus_areas") or []
                if isinstance(focus, str):
                    focus = [focus]
                tip = _safe_str(data.get("confidence_tip", ""))
                return InterviewPrep(
                    questions=parsed_questions[:6],
                    key_focus_areas=[str(f) for f in focus][:5],
                    confidence_tip=tip or f"Ground your answers in concrete metrics and communicate with enthusiasm.",
                )
    except Exception as exc:
        logger.warning(f"Stage 5 LLM generation failed: {exc}")

    return _fallback_interview_prep(ctx, job_input, match_analysis)


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

def run_job_target_analysis(
    db: Session,
    user_id: int,
    resume: Resume,
    job_input: ExternalJobInput,
) -> JobTargetAnalysisResult:
    """
    Full 4-stage analysis pipeline.
    Deterministic layer always runs.
    LLM stages run if Ollama is available.
    Partial failures handled gracefully.
    """
    lang = job_input.language.value
    ctx = build_candidate_context(db, user_id, resume)
    det_score = deterministic_score(ctx, job_input)

    runtime = check_ollama_runtime()
    ollama_available = runtime.get("status") == "connected" and bool(runtime.get("models"))
    model = runtime.get("selected_model")

    result = JobTargetAnalysisResult(
        resume_id=resume.id,
        target_role=job_input.target_role,
        language=lang,
        deterministic_score=det_score,
        data_conflicts=ctx.conflicts,
        ollama_used=ollama_available,
        ollama_model=model if ollama_available else None,
    )

    # Stage 1
    try:
        if ollama_available:
            requirements = _stage1_extract_requirements(job_input, model=model)
        else:
            requirements = _fallback_extract_requirements(job_input)
        result.job_requirements = requirements
    except (OllamaError, OllamaUnavailableError, Exception) as exc:
        logger.warning(f"Stage 1 failed: {exc}")
        requirements = _fallback_extract_requirements(job_input)
        result.job_requirements = requirements
        result.ollama_used = False

    # Stage 2
    try:
        if ollama_available and requirements:
            match_analysis = _stage2_match_candidate(requirements, ctx, lang, model=model)
        else:
            match_analysis = deterministic_match(ctx, job_input)
        result.match_analysis = match_analysis
    except (OllamaError, OllamaUnavailableError, Exception) as exc:
        logger.warning(f"Stage 2 failed: {exc}")
        result.match_analysis = deterministic_match(ctx, job_input)

    match_analysis = result.match_analysis

    # Stage 3
    try:
        if ollama_available:
            recs = _stage3_recommendations(requirements, match_analysis, ctx, job_input, model=model)
        else:
            recs = _fallback_recommendations(match_analysis, ctx, job_input)
        result.resume_recommendations = recs
    except (OllamaError, OllamaUnavailableError, Exception) as exc:
        logger.warning(f"Stage 3 failed: {exc}")
        result.resume_recommendations = _fallback_recommendations(match_analysis, ctx, job_input)

    # Stage 4
    no_ai_msg = "Local AI unavailable. Start Ollama to generate application materials."
    try:
        if ollama_available:
            email, dm, letter = _stage4_materials(ctx, job_input, model=model)
        else:
            email = ApplicationMaterial(material_type=MaterialType.COLD_EMAIL, language=lang, generated=False, error=no_ai_msg)
            dm = ApplicationMaterial(material_type=MaterialType.SHORT_MESSAGE, language=lang, generated=False, error=no_ai_msg)
            letter = ApplicationMaterial(material_type=MaterialType.MOTIVATION_LETTER, language=lang, generated=False, error=no_ai_msg)
        result.cold_email = email
        result.short_message = dm
        result.motivation_letter = letter
    except (OllamaError, OllamaUnavailableError) as exc:
        logger.warning(f"Stage 4 failed: {exc}")
        result.partial_failure = True
        result.partial_failure_detail = "Application materials could not be generated (AI unavailable). Resume analysis completed."
        for mtype, attr in [(MaterialType.COLD_EMAIL, "cold_email"), (MaterialType.SHORT_MESSAGE, "short_message"), (MaterialType.MOTIVATION_LETTER, "motivation_letter")]:
            setattr(result, attr, ApplicationMaterial(material_type=mtype, language=lang, generated=False, error=str(exc)))
    except Exception as exc:
        logger.error(f"Stage 4 unexpected error: {exc}")
        result.partial_failure = True
        result.partial_failure_detail = f"Application materials generation failed: {exc}. Resume analysis is complete."

    # Stage 5 - Interview & STAR Prep
    try:
        if ollama_available:
            result.interview_prep = _stage5_interview_prep(ctx, job_input, match_analysis, model=model)
        else:
            result.interview_prep = _fallback_interview_prep(ctx, job_input, match_analysis)
    except Exception as exc:
        logger.warning(f"Stage 5 failed, using fallback: {exc}")
        result.interview_prep = _fallback_interview_prep(ctx, job_input, match_analysis)

    return result


# ---------------------------------------------------------------------------
# Apply accepted recommendations to resume data (non-destructive copy)
# ---------------------------------------------------------------------------

def apply_recommendations_to_resume_data(
    base_structured_data: dict,
    recommendations: list[ResumeRecommendation],
) -> dict:
    """
    Apply accepted recommendations to a DEEP COPY of the resume data.
    The original is NEVER mutated. Only grounded, non-MISSING recs are applied.
    """
    import copy
    data = copy.deepcopy(base_structured_data)
    for rec in recommendations:
        if rec.rec_type == RecommendationType.MISSING or not rec.grounded:
            continue
        if rec.rec_type == RecommendationType.REWRITE and rec.section == "summary" and rec.suggested_text:
            data.setdefault("profile", {})["summary"] = rec.suggested_text
        elif rec.rec_type == RecommendationType.EMPHASIZE and rec.section == "skills" and rec.item_label:
            skills = data.get("skills", [])
            for i, s in enumerate(skills):
                if s.get("name", "").lower() == rec.item_label.lower() and i > 0:
                    skills.insert(0, skills.pop(i))
                    data["skills"] = skills
                    break
        elif rec.rec_type == RecommendationType.REWRITE and rec.item_id and rec.suggested_text:
            for exp in data.get("experience", []):
                if str(exp.get("id", "")) == rec.item_id:
                    exp["description"] = rec.suggested_text
                    break
            for proj in data.get("projects", []):
                if str(proj.get("id", "")) == rec.item_id:
                    proj["description"] = rec.suggested_text
                    break
        elif rec.rec_type == RecommendationType.MOVE and rec.section == "experience" and rec.item_id:
            exps = data.get("experience", [])
            for i, e in enumerate(exps):
                if str(e.get("id", "")) == rec.item_id and i > 0:
                    exps.insert(0, exps.pop(i))
                    data["experience"] = exps
                    break
    return data
