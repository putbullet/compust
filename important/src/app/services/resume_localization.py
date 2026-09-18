"""Resume localization services for multilingual skills, languages, and section titles."""

from typing import Literal

ResumeLanguage = Literal["en", "fr", "de"]

# ---------------------------------------------------------------------------
# Canonical Skill Tokens & Localized Labels
# ---------------------------------------------------------------------------
SKILL_PROFICIENCY_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "BEGINNER": "Beginner",
        "INTERMEDIATE": "Intermediate",
        "ADVANCED": "Advanced",
        "EXPERT": "Expert",
        "NONE": "",
    },
    "fr": {
        "BEGINNER": "Débutant",
        "INTERMEDIATE": "Intermédiaire",
        "ADVANCED": "Avancé",
        "EXPERT": "Expert",
        "NONE": "",
    },
    "de": {
        "BEGINNER": "Anfänger",
        "INTERMEDIATE": "Fortgeschritten",
        "ADVANCED": "Sehr gute Kenntnisse",
        "EXPERT": "Experte",
        "NONE": "",
    },
}

# ---------------------------------------------------------------------------
# Canonical Spoken Language Tokens & Localized Labels
# ---------------------------------------------------------------------------
LANGUAGE_PROFICIENCY_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "NATIVE": "Native",
        "BILINGUAL": "Bilingual",
        "FLUENT": "Fluent",
        "PROFESSIONAL": "Professional Working",
        "INTERMEDIATE": "Intermediate",
        "BASIC": "Basic",
        "NONE": "",
    },
    "fr": {
        "NATIVE": "Langue maternelle",
        "BILINGUAL": "Bilingue",
        "FLUENT": "Courant",
        "PROFESSIONAL": "Professionnel",
        "INTERMEDIATE": "Intermédiaire",
        "BASIC": "Notions / Débutant",
        "NONE": "",
    },
    "de": {
        "NATIVE": "Muttersprache",
        "BILINGUAL": "Zweisprachig",
        "FLUENT": "Fließend",
        "PROFESSIONAL": "Verhandlungssicher",
        "INTERMEDIATE": "Gute Kenntnisse",
        "BASIC": "Grundkenntnisse",
        "NONE": "",
    },
}

# ---------------------------------------------------------------------------
# Default Section Titles by Resume Language
# ---------------------------------------------------------------------------
DEFAULT_SECTION_TITLES_BY_LANG: dict[str, dict[str, str]] = {
    "en": {
        "summary": "Professional Summary",
        "experience": "Professional Experience",
        "education": "Education & Academic Background",
        "skills": "Technical & Core Skills",
        "projects": "Featured Projects",
        "certifications": "Certifications & Accreditations",
        "languages": "Languages",
        "custom_sections": "Additional Information",
    },
    "fr": {
        "summary": "Profil Professionnel",
        "experience": "Expérience Professionnelle",
        "education": "Formation & Diplômes",
        "skills": "Compétences",
        "projects": "Projets Réalisés",
        "certifications": "Certifications",
        "languages": "Langues",
        "custom_sections": "Informations Complémentaires",
    },
    "de": {
        "summary": "Kurzprofil",
        "experience": "Berufserfahrung",
        "education": "Ausbildung",
        "skills": "Kenntnisse & Fähigkeiten",
        "projects": "Projekte",
        "certifications": "Zertifikate",
        "languages": "Sprachen",
        "custom_sections": "Zusätzliche Informationen",
    },
}


def normalize_skill_proficiency(raw: str | None) -> str:
    """Normalize raw skill proficiency string to a canonical token."""
    if not raw:
        return "NONE"
    clean = str(raw).strip().upper()
    if clean in ("", "NONE", "NO_LABEL", "NO LABEL", "BLANK", "NULL", "UNDEFINED"):
        return "NONE"
    if "BEGINNER" in clean or "DEBUTANT" in clean or "DÉBUTANT" in clean or "ANFÄNGER" in clean or "ANFANGER" in clean:
        return "BEGINNER"
    if "INTERMEDIATE" in clean or "INTERMEDIAIRE" in clean or "INTERMÉDIAIRE" in clean or "MITTEL" in clean:
        return "INTERMEDIATE"
    if "ADVANCED" in clean or "AVANCE" in clean or "AVANCÉ" in clean or "FORTGESCHRITTEN" in clean:
        return "ADVANCED"
    if "EXPERT" in clean:
        return "EXPERT"
    return clean


def normalize_language_proficiency(raw: str | None) -> str:
    """Normalize raw spoken language proficiency string to a canonical token."""
    if not raw:
        return "NONE"
    clean = str(raw).strip().upper()
    if clean in ("", "NONE", "NO_LABEL", "NO LABEL", "BLANK", "NULL", "UNDEFINED"):
        return "NONE"
    if "NATIVE" in clean or "MATERNELLE" in clean or "MUTTERSPRACHE" in clean:
        return "NATIVE"
    if "BILINGUAL" in clean or "BILINGUE" in clean or "ZWEISPRACHIG" in clean:
        return "BILINGUAL"
    if "FLUENT" in clean or "COURANT" in clean or "FLIEẞEND" in clean or "FLIESSEND" in clean:
        return "FLUENT"
    if "PROFESSIONAL" in clean or "PROFESSIONNEL" in clean or "VERHANDLUNGSSICHER" in clean:
        return "PROFESSIONAL"
    if "INTERMEDIATE" in clean or "INTERMEDIAIRE" in clean or "INTERMÉDIAIRE" in clean or "GUTE KENNTNISSE" in clean:
        return "INTERMEDIATE"
    if "BASIC" in clean or "NOTION" in clean or "GRUNDKENNTNISSE" in clean:
        return "BASIC"
    return clean


def get_localized_skill_label(proficiency: str | None, lang: str = "en") -> str:
    """Return the display label for a skill proficiency in the specified language."""
    token = normalize_skill_proficiency(proficiency)
    if token == "NONE":
        return ""
    lang_key = lang.lower() if lang else "en"
    labels = SKILL_PROFICIENCY_LABELS.get(lang_key, SKILL_PROFICIENCY_LABELS["en"])
    return labels.get(token, SKILL_PROFICIENCY_LABELS["en"].get(token, token))


def get_localized_language_label(proficiency: str | None, lang: str = "en") -> str:
    """Return the display label for a spoken language proficiency in the specified language."""
    token = normalize_language_proficiency(proficiency)
    if token == "NONE":
        return ""
    lang_key = lang.lower() if lang else "en"
    labels = LANGUAGE_PROFICIENCY_LABELS.get(lang_key, LANGUAGE_PROFICIENCY_LABELS["en"])
    return labels.get(token, LANGUAGE_PROFICIENCY_LABELS["en"].get(token, token))


def format_skill_display(name: str, proficiency: str | None, lang: str = "en") -> str:
    """Format skill for display.
    
    If proficiency is None / NONE / blank, returns only name (e.g. "Python").
    If proficiency is set, returns "Python — Advanced" (or localized equivalent).
    Never returns "Python — None", "Python — Basic", or "null".
    """
    clean_name = (name or "").strip()
    if not clean_name:
        return ""
    label = get_localized_skill_label(proficiency, lang)
    if label:
        return f"{clean_name} — {label}"
    return clean_name


def format_language_display(language: str, proficiency: str | None, lang: str = "en") -> str:
    """Format spoken language for display.
    
    If proficiency is None / NONE / blank, returns only language (e.g. "French").
    If proficiency is set, returns "French (Fluent)" (or localized equivalent).
    Never returns "French (None)" or "French (null)".
    """
    clean_lang = (language or "").strip()
    if not clean_lang:
        return ""
    label = get_localized_language_label(proficiency, lang)
    if label:
        return f"{clean_lang} ({label})"
    return clean_lang


def resolve_localized_section_title(section_id: str, custom_title: str | None = None, lang: str = "en") -> str:
    """Resolve section title with language awareness and custom title fallback."""
    if custom_title and isinstance(custom_title, str) and custom_title.strip():
        return custom_title.strip()
    lang_key = lang.lower() if lang else "en"
    lang_defaults = DEFAULT_SECTION_TITLES_BY_LANG.get(lang_key, DEFAULT_SECTION_TITLES_BY_LANG["en"])
    return lang_defaults.get(section_id, DEFAULT_SECTION_TITLES_BY_LANG["en"].get(section_id, section_id.replace("_", " ").title()))
