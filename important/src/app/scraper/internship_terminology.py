import re
import unicodedata
from typing import NamedTuple


def strip_diacritics(text: str) -> str:
    """Normalize and strip diacritics/accents from text for consistent matching."""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


class LanguageTerminology(NamedTuple):
    lang_code: str
    internship_terms: list[str]
    student_terms: list[str]
    apprentice_terms: list[str]


# Multilingual terminology mappings for internship discovery
INTERNSHIP_TERMINOLOGY_BY_LANG: dict[str, LanguageTerminology] = {
    "en": LanguageTerminology(
        lang_code="en",
        internship_terms=["internship", "intern", "summer intern", "co-op", "trainee"],
        student_terms=["graduate intern", "student intern"],
        apprentice_terms=["apprentice", "apprenticeship"],
    ),
    "fr": LanguageTerminology(
        lang_code="fr",
        internship_terms=["stage", "stagiaire", "stage de fin d'etudes", "pfe"],
        student_terms=["etudiant stagiaire", "stage etudiant"],
        apprentice_terms=["alternance", "apprenti", "apprentissage", "contrat de professionnalisation"],
    ),
    "de": LanguageTerminology(
        lang_code="de",
        internship_terms=["Praktikum", "Praktikant", "Praktikantin", "Werkstudent", "Werkstudentenjob"],
        student_terms=["Abschlussarbeit", "Bachelorarbeit", "Masterarbeit"],
        apprentice_terms=["Ausbildung", "Auszubildender", "Trainee"],
    ),
    "es": LanguageTerminology(
        lang_code="es",
        internship_terms=["practicas", "practicas profesionales", "becario", "becaria", "pasantia", "pasante"],
        student_terms=["estudiante en practicas"],
        apprentice_terms=["aprendiz", "aprendizaje"],
    ),
    "it": LanguageTerminology(
        lang_code="it",
        internship_terms=["tirocinio", "stage", "tirocinante", "stagista"],
        student_terms=["tirocinio curriculare", "tirocinio extracurriculare"],
        apprentice_terms=["apprendistato", "apprendista"],
    ),
}

# Country code or name mapping to primary local languages
COUNTRY_TO_LANGUAGES: dict[str, list[str]] = {
    "germany": ["de", "en"],
    "deutschland": ["de", "en"],
    "austria": ["de", "en"],
    "switzerland": ["de", "fr", "en"],
    "france": ["fr", "en"],
    "morocco": ["fr", "en"],
    "maroc": ["fr", "en"],
    "tunisia": ["fr", "en"],
    "algeria": ["fr", "en"],
    "belgium": ["fr", "en", "de"],
    "spain": ["es", "en"],
    "espana": ["es", "en"],
    "mexico": ["es", "en"],
    "italy": ["it", "en"],
    "italia": ["it", "en"],
    "united kingdom": ["en"],
    "uk": ["en"],
    "united states": ["en"],
    "usa": ["en"],
    "canada": ["en", "fr"],
    "netherlands": ["en"],
    "sweden": ["en"],
}

# Common technical field translations/synonyms across EN / FR / DE / ES
FIELD_TRANSLATIONS: dict[str, dict[str, list[str]]] = {
    "cybersecurity": {
        "fr": ["cybersecurite", "securite informatique", "securite des systemes d'information"],
        "de": ["Cybersicherheit", "IT-Sicherheit", "Informationssicherheit"],
        "es": ["ciberseguridad", "seguridad informatica"],
        "it": ["sicurezza informatica", "cyber security"],
    },
    "software engineering": {
        "fr": ["genie logiciel", "developpement logiciel", "developpeur"],
        "de": ["Softwareentwicklung", "Software Engineer", "Softwareentwickler"],
        "es": ["ingenieria de software", "desarrollo de software"],
        "it": ["ingegneria del software", "sviluppo software"],
    },
    "data science": {
        "fr": ["science des donnees", "data science"],
        "de": ["Data Science", "Datenanalyse"],
        "es": ["ciencia de datos"],
        "it": ["scienza dei dati"],
    },
    "machine learning": {
        "fr": ["apprentissage automatique", "machine learning", "ia"],
        "de": ["Machine Learning", "Maschinelles Lernen", "KI"],
        "es": ["aprendizaje automatico", "inteligencia artificial"],
        "it": ["apprendimento automatico", "intelligenza artificiale"],
    },
    "cloud": {
        "fr": ["cloud computing", "ingenieur cloud"],
        "de": ["Cloud Computing", "Cloud Engineer"],
        "es": ["computacion en la nube"],
        "it": ["cloud computing"],
    },
    "devops": {
        "fr": ["devops", "cloud devops"],
        "de": ["DevOps"],
        "es": ["devops"],
        "it": ["devops"],
    },
    "web development": {
        "fr": ["developpement web", "developpeur web"],
        "de": ["Webentwicklung", "Webentwickler"],
        "es": ["desarrollo web"],
        "it": ["sviluppo web"],
    },
}


def normalize_keyword(kw: str) -> str:
    """Strip accents and lower for lookup."""
    return strip_diacritics(kw.strip().lower())


def get_languages_for_country(country: str | None) -> list[str]:
    """Determine relevant languages given country or worldwide mode."""
    if not country or not country.strip():
        # Worldwide mode: prioritize English, French, German, Spanish
        return ["en", "fr", "de", "es"]

    norm_country = normalize_keyword(country)
    for c_key, langs in COUNTRY_TO_LANGUAGES.items():
        if c_key in norm_country or norm_country in c_key:
            return langs

    # Default fallback: English + original query context
    return ["en"]


def expand_internship_queries(
    field_or_keyword: str,
    country: str | None = None,
    year: int | str | None = None,
    limit: int = 8,
) -> list[str]:
    """Intelligently generate focused search queries for internship discovery.

    Handles natural language queries, multilingual terms (stage, Praktikum,
    prácticas), country context, and optional target internship year.
    """
    cleaned_input = field_or_keyword.strip()
    if not cleaned_input:
        return []

    norm_input = normalize_keyword(cleaned_input)

    # Detect if user already included internship keywords
    has_intern_word = bool(
        re.search(r"\b(intern|internship|stage|stagiaire|praktik|praktikum|practicas|becari|pasant|tirocini|apprentice)\b", norm_input)
    )

    # Strip internship keyword from base domain if present to isolate technical field
    clean_field = re.sub(
        r"\b(internship|interns?|summer intern|stage|stagiaire|pfe|praktikum|praktikant|practicas|pasantia|tirocinio)\b",
        "",
        cleaned_input,
        flags=re.IGNORECASE,
    ).strip()
    if not clean_field:
        clean_field = cleaned_input

    languages = get_languages_for_country(country)
    year_str = str(year).strip() if year else ""

    queries: list[str] = []

    # 1. Base user query + country + year
    base_query_parts = [cleaned_input]
    if country and country.strip().lower() not in norm_input:
        base_query_parts.append(country.strip())
    if year_str and year_str not in norm_input:
        base_query_parts.append(year_str)
    queries.append(" ".join(base_query_parts))

    # 2. If the user didn't include "internship", create an explicit English query
    if not has_intern_word:
        eq_parts = [f'"{clean_field}" internship']
        if country and country.strip().lower() not in norm_input:
            eq_parts.append(country.strip())
        if year_str:
            eq_parts.append(year_str)
        queries.append(" ".join(eq_parts))

    # 3. Multilingual expansion based on target country / languages
    norm_clean_field = normalize_keyword(clean_field)
    translations_for_field: dict[str, list[str]] = {}
    for canonical_field, trans_dict in FIELD_TRANSLATIONS.items():
        if canonical_field in norm_clean_field or norm_clean_field in canonical_field:
            translations_for_field = trans_dict
            break

    for lang in languages:
        terms_obj = INTERNSHIP_TERMINOLOGY_BY_LANG.get(lang)
        if not terms_obj:
            continue

        local_intern_terms = terms_obj.internship_terms
        primary_term = local_intern_terms[0]

        # Check if we have a translated domain term for this language
        translated_field_terms = translations_for_field.get(lang, [clean_field])
        chosen_field = translated_field_terms[0]

        # Local language pattern (e.g. "Cybersicherheit Praktikum Deutschland 2027" or "stage cybersécurité France")
        if lang == "de":
            query_str = f"{chosen_field} {primary_term}"
        elif lang == "fr":
            query_str = f"{primary_term} {chosen_field}"
        elif lang == "es":
            query_str = f"{primary_term} {chosen_field}"
        else:
            query_str = f"{chosen_field} {primary_term}"

        if country and country.strip().lower() not in query_str.lower():
            query_str += f" {country.strip()}"
        if year_str and year_str not in query_str:
            query_str += f" {year_str}"

        queries.append(query_str)

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for q in queries:
        norm_q = " ".join(q.lower().split())
        if norm_q not in seen:
            seen.add(norm_q)
            deduped.append(q)
        if len(deduped) >= limit:
            break

    return deduped
