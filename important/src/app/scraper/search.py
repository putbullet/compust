import re
import unicodedata

SYNONYMS_MAP: dict[str, list[str]] = {
    "developpeur": ["developer", "dev", "ingenieur logiciel", "software engineer"],
    "developer": ["developpeur", "développeur", "dev", "software engineer"],
    "ingenieur": ["engineer"],
    "engineer": ["ingenieur", "ingénieur"],
    "stage": ["internship", "intern", "stagiaire"],
    "stagiaire": ["intern", "internship", "stage"],
    "internship": ["stage", "stagiaire", "intern"],
    "intern": ["stage", "stagiaire", "internship"],
    "chef de projet": ["project manager", "product manager", "pm"],
    "project manager": ["chef de projet", "pm"],
    "architecte": ["architect"],
    "architect": ["architecte"],
    "analyste": ["analyst"],
    "analyst": ["analyste"],
    "consultant": ["consultant"],
    "administrateur": ["administrator", "admin"],
    "administrator": ["administrateur", "admin"],
    "teletravail": ["remote", "distanciel"],
    "distanciel": ["remote", "teletravail", "télétravail"],
    "remote": ["teletravail", "télétravail", "distanciel"],
    "hybride": ["hybrid"],
    "hybrid": ["hybride"],
    "presentiel": ["on-site", "onsite"],
    "donnees": ["data"],
    "data": ["donnees", "données"],
    "securite": ["security"],
    "security": ["securite", "sécurité"],
    "reseau": ["network"],
    "network": ["reseau", "réseau"],
    "alternance": ["apprenticeship", "apprentice"],
    "apprenticeship": ["alternance"],
}


def strip_accents(text: str) -> str:
    """Normalize and strip diacritics/accents from text for consistent matching."""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def expand_search_query(query: str) -> list[str]:
    """Expands a search query with multilingual French/German/English technical and job-title synonyms.

    Returns a deduplicated list of search terms starting with the original query.
    """
    cleaned = query.strip()
    if not cleaned:
        return []

    try:
        from ..services.opportunities_search import prepare_search_plan
        plan = prepare_search_plan(cleaned)
        if plan.all_matching_terms:
            # Ensure any legacy SYNONYMS_MAP terms are also included as fallback
            terms = list(plan.all_matching_terms)
            norm = strip_accents(cleaned.lower())
            if norm in SYNONYMS_MAP:
                for syn in SYNONYMS_MAP[norm]:
                    if syn not in terms:
                        terms.append(syn)
            return list(dict.fromkeys(terms))
    except Exception:
        pass

    # Fallback implementation
    terms = [cleaned]
    normalized = strip_accents(cleaned.lower())

    if normalized in SYNONYMS_MAP:
        for syn in SYNONYMS_MAP[normalized]:
            if syn not in terms:
                terms.append(syn)

    tokens = re.findall(r"\b\w+\b", normalized)
    for token in tokens:
        if token in SYNONYMS_MAP:
            for syn in SYNONYMS_MAP[token]:
                expanded_phrase = re.sub(rf"\b{re.escape(token)}\b", syn, normalized)
                if expanded_phrase not in terms:
                    terms.append(expanded_phrase)
                if syn not in terms:
                    terms.append(syn)

    return list(dict.fromkeys(terms))
