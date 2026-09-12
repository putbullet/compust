"""Decoupled Job Translation Service.

Preserves original employer text in `jobs.title` and `jobs.description` as the
unmodified ground truth, while maintaining localized translations in `job_translations`.
Provides a 100% offline, deterministic fallback translation engine without external AI dependencies.
"""

from datetime import datetime, timezone
import re
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models import Job, JobTranslation


class TranslationProvider(Protocol):
    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        ...


class DeterministicTranslationProvider:
    """Zero-dependency, offline deterministic translator for job postings."""

    # Lexical title mappings (French -> English)
    FR_EN_TITLES: dict[str, str] = {
        "developpeur": "Developer",
        "développeur": "Developer",
        "developpeuse": "Developer",
        "développeuse": "Developer",
        "ingenieur": "Engineer",
        "ingénieur": "Engineer",
        "ingenieure": "Engineer",
        "ingénieure": "Engineer",
        "stage": "Internship",
        "stagiaire": "Intern",
        "alternance": "Work-study / Apprenticeship",
        "alternant": "Work-study Apprentice",
        "alternante": "Work-study Apprentice",
        "chef de projet": "Project Manager",
        "directeur": "Director",
        "responsable": "Lead / Manager",
        "consultant": "Consultant",
        "consultante": "Consultant",
        "administrateur": "Administrator",
        "analyste": "Analyst",
        "technicien": "Technician",
        "technicienne": "Technician",
        "architecte": "Architect",
        "donnees": "Data",
        "données": "Data",
        "logiciel": "Software",
        "systemes": "Systems",
        "systèmes": "Systems",
        "reseau": "Network",
        "réseau": "Network",
        "securite": "Security",
        "sécurité": "Security",
    }

    # Common job description section headings (French -> English)
    FR_EN_SECTIONS: list[tuple[str, str]] = [
        (r"\bMissions?\s*:", "Responsibilities:"),
        (r"\bVos missions?\s*:", "Your responsibilities:"),
        (r"\bProfil recherch[eé]\s*:", "Candidate profile:"),
        (r"\bComp[eé]tences requises?\s*:", "Required skills:"),
        (r"\bPr[eé]requis\s*:", "Prerequisites:"),
        (r"\bT[eé]l[eé]travail\s*:", "Remote work:"),
        (r"\bAvantages\s*:", "Benefits:"),
        (r"\bLocalisation\s*:", "Location:"),
        (r"\bR[eé]mun[eé]ration\s*:", "Compensation:"),
        (r"\bNiveau d'[eé]tudes?\s*:", "Education level:"),
        (r"\bExp[eé]rience souhait[eé]e\s*:", "Desired experience:"),
        (r"\bA propos de nous\s*:", "About us:"),
        (r"\bÀ propos de nous\s*:", "About us:"),
    ]

    # English -> French basic mappings
    EN_FR_TITLES: dict[str, str] = {
        "developer": "Développeur",
        "engineer": "Ingénieur",
        "internship": "Stage",
        "intern": "Stagiaire",
        "software": "Logiciel",
        "manager": "Responsable / Manager",
        "project manager": "Chef de projet",
        "data": "Données",
        "lead": "Lead",
        "architect": "Architecte",
    }

    EN_FR_SECTIONS: list[tuple[str, str]] = [
        (r"\bResponsibilities\s*:", "Missions :"),
        (r"\bRequirements\s*:", "Profil recherché :"),
        (r"\bRequired [Ss]kills\s*:", "Compétences requises :"),
        (r"\bRemote [Ww]ork\s*:", "Télétravail :"),
        (r"\bBenefits\s*:", "Avantages :"),
        (r"\bLocation\s*:", "Localisation :"),
        (r"\bAbout [Uu]s\s*:", "À propos :"),
    ]

    def detect_language(self, text: str) -> str:
        """Heuristic language detection based on common stop words."""
        sample = text.lower()
        fr_markers = [" et ", " de ", " pour ", " avec ", " dans ", " le ", " la ", " les ", " des ", " nous "]
        en_markers = [" and ", " of ", " for ", " with ", " in ", " the ", " to ", " our ", " you ", " we "]

        fr_score = sum(sample.count(m) for m in fr_markers)
        en_score = sum(sample.count(m) for m in en_markers)

        if fr_score > en_score:
            return "fr"
        if en_score > fr_score:
            return "en"
        return "auto"

    def translate_title(self, title: str, source_lang: str, target_lang: str) -> str:
        if source_lang == target_lang:
            return title

        if target_lang == "en":
            # Translate French terms to English
            translated = title
            for fr_term, en_term in self.FR_EN_TITLES.items():
                pattern = re.compile(rf"\b{re.escape(fr_term)}\b", re.IGNORECASE)
                translated = pattern.sub(en_term, translated)
            return translated
        elif target_lang == "fr":
            # Translate English terms to French
            translated = title
            for en_term, fr_term in self.EN_FR_TITLES.items():
                pattern = re.compile(rf"\b{re.escape(en_term)}\b", re.IGNORECASE)
                translated = pattern.sub(fr_term, translated)
            return translated

        return title

    def translate_description(self, description: str, source_lang: str, target_lang: str) -> str:
        if not description or source_lang == target_lang:
            return description

        translated = description
        if target_lang == "en":
            for pattern, replacement in self.FR_EN_SECTIONS:
                translated = re.sub(pattern, replacement, translated, flags=re.IGNORECASE)
        elif target_lang == "fr":
            for pattern, replacement in self.EN_FR_SECTIONS:
                translated = re.sub(pattern, replacement, translated, flags=re.IGNORECASE)

        return translated


class JobTranslationService:
    def __init__(self, provider: TranslationProvider | None = None) -> None:
        self.provider = provider or DeterministicTranslationProvider()

    def get_translations(self, session: Session, job_id: int) -> list[JobTranslation]:
        """Fetch all stored translations for a job."""
        stmt = select(JobTranslation).where(JobTranslation.job_id == job_id).order_by(JobTranslation.language)
        return list(session.execute(stmt).scalars().all())

    def get_translation(self, session: Session, job_id: int, language: str) -> JobTranslation | None:
        """Fetch a specific language translation for a job."""
        stmt = select(JobTranslation).where(
            JobTranslation.job_id == job_id,
            JobTranslation.language == language.lower(),
        )
        return session.execute(stmt).scalar_one_or_none()

    def create_or_update_translation(
        self,
        session: Session,
        job_id: int,
        language: str,
        title: str,
        description: str | None = None,
        source_language: str = "auto",
    ) -> JobTranslation:
        """Upsert a translation without modifying the original Job row."""
        now = datetime.now(timezone.utc)
        lang_code = language.strip().lower()

        existing = self.get_translation(session, job_id, lang_code)
        if existing:
            existing.title = title
            existing.description = description
            existing.source_language = source_language
            existing.updated_at = now
            session.commit()
            session.refresh(existing)
            return existing

        translation = JobTranslation(
            job_id=job_id,
            language=lang_code,
            title=title,
            description=description,
            source_language=source_language,
            created_at=now,
            updated_at=now,
        )
        session.add(translation)
        session.commit()
        session.refresh(translation)
        return translation

    def auto_translate_job(
        self,
        session: Session,
        job: Job,
        target_language: str,
    ) -> JobTranslation:
        """Generate a translation using the deterministic engine and persist it decoupled."""
        target_lang = target_language.strip().lower()

        # Check if already exists
        existing = self.get_translation(session, job.id, target_lang)
        if existing:
            return existing

        source_lang = "auto"
        if isinstance(self.provider, DeterministicTranslationProvider):
            detected = self.provider.detect_language(f"{job.title} {job.description or ''}")
            source_lang = detected if detected != "auto" else "fr"
            translated_title = self.provider.translate_title(job.title, source_lang, target_lang)
            translated_desc = (
                self.provider.translate_description(job.description, source_lang, target_lang)
                if job.description
                else None
            )
        else:
            translated_title = self.provider.translate_text(job.title, source_lang, target_lang)
            translated_desc = (
                self.provider.translate_text(job.description, source_lang, target_lang)
                if job.description
                else None
            )

        return self.create_or_update_translation(
            session=session,
            job_id=job.id,
            language=target_lang,
            title=translated_title,
            description=translated_desc,
            source_language=source_lang,
        )
