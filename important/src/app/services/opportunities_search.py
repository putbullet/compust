"""Opportunities Search Engine: Intelligent, multilingual, and relevance-ranked search."""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Text Normalization & Accent Stripping
# ---------------------------------------------------------------------------

def unaccent(text: str) -> str:
    """Normalize text and strip diacritics/accents (e.g. développeur -> developpeur, Cybersicherheit -> cybersicherheit)."""
    if not text:
        return ""
    s = text.replace("ß", "ss")
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_search_token(word: str) -> str:
    """Normalize an individual word token: lowercase, unaccent, strip punctuation, handle plurals/gender."""
    if not word:
        return ""
    clean = unaccent(word.strip().lower())
    clean = re.sub(r"^[^\w]+|[^\w]+$", "", clean)

    # Common English plurals (internships -> internship, developers -> developer)
    if clean.endswith("ies") and len(clean) > 4:
        clean = clean[:-3] + "y"
    elif clean.endswith("ses") and len(clean) > 4:
        clean = clean[:-2]
    elif clean.endswith("s") and len(clean) > 3 and not clean.endswith(("ss", "us", "is", "os")):
        clean = clean[:-1]

    # Common French feminine/gendered endings (developpeuse -> developpeur, ingenieure -> ingenieur)
    if clean.endswith("euse") and len(clean) > 5:
        clean = clean[:-4] + "eur"
    elif clean.endswith("trice") and len(clean) > 6:
        clean = clean[:-5] + "teur"
    elif clean.endswith("ere") and len(clean) > 4:
        clean = clean[:-3] + "er"
    elif clean.endswith("ienne") and len(clean) > 6:
        clean = clean[:-5] + "ien"

    # Common German gendered suffixes (entwicklerin -> entwickler, prakticantin -> praktikant)
    if clean.endswith("innen") and len(clean) > 6:
        clean = clean[:-5]
    elif clean.endswith("in") and len(clean) > 4 and not clean.endswith(("admin", "main", "join")):
        clean = clean[:-2]

    return clean


def normalize_search_text(text: str) -> str:
    """Normalize search text: decode HTML, unaccent, collapse hyphens/punctuation, collapse whitespace."""
    if not text:
        return ""
    decoded = html.unescape(text)
    nfkc = unicodedata.normalize("NFKC", decoded)
    unacc = unaccent(nfkc).lower()

    # Hyphenated compounds become space-separated (front-end -> front end, cyber-security -> cyber security)
    unacc = re.sub(r"(?<=\w)[-_/](?=\w)", " ", unacc)
    # Remove non-alphanumeric characters
    unacc = re.sub(r"[^\w\s]", " ", unacc)
    # Collapse multiple whitespaces
    return re.sub(r"\s+", " ", unacc).strip()


# ---------------------------------------------------------------------------
# Multilingual Concept Groups & Semantic Mappings
# ---------------------------------------------------------------------------

# Concept definitions mapping canonical concept to multilingual equivalent phrases (EN, FR, DE)
CONCEPT_SYNONYMS: dict[str, list[str]] = {
    # Internships / Entry Level
    "internship": [
        "internship", "intern", "trainee", "co op", "apprentice", "apprenticeship",
        "stage", "stagiaire", "alternance", "apprentissage", "pfe",
        "praktikum", "praktikant", "praktikantin", "werkstudent", "werkstudentin", "ausbildung",
    ],
    "stage": [
        "stage", "stagiaire", "pfe", "alternance", "apprentissage",
        "internship", "intern", "trainee", "apprenticeship",
        "praktikum", "praktikant", "praktikantin", "werkstudent",
    ],
    "stagiaire": [
        "stagiaire", "stage", "pfe", "alternance",
        "intern", "internship", "trainee",
        "praktikant", "praktikantin", "praktikum",
    ],
    "praktikum": [
        "praktikum", "praktikant", "praktikantin", "werkstudent", "ausbildung",
        "internship", "intern", "trainee",
        "stage", "stagiaire", "alternance",
    ],
    "praktikant": [
        "praktikant", "praktikantin", "praktikum", "werkstudent",
        "intern", "internship", "trainee",
        "stagiaire", "stage",
    ],
    "werkstudent": [
        "werkstudent", "werkstudentin", "praktikum", "praktikant",
        "working student", "intern", "internship",
        "alternance", "stage",
    ],
    "alternance": [
        "alternance", "apprentissage", "apprenti", "apprentie", "contrat pro",
        "apprenticeship", "apprentice", "work study", "internship",
        "duales studium", "ausbildung", "werkstudent",
    ],

    # Software Engineering / Development
    "developer": [
        "developer", "dev", "software engineer", "programmer", "coder",
        "developpeur", "développeur", "developpeuse", "développeuse",
        "ingenieur logiciel", "ingénieur logiciel", "concepteur developpeur",
        "entwickler", "entwicklerin", "softwareentwickler", "software entwickler", "programmierer",
    ],
    "developpeur": [
        "developpeur", "développeur", "developpeuse", "développeuse", "ingenieur logiciel", "ingénieur logiciel", "dev",
        "developer", "software engineer", "programmer",
        "entwickler", "entwicklerin", "softwareentwickler",
    ],
    "developpeuse": [
        "developpeuse", "développeuse", "developpeur", "développeur", "ingenieur logiciel",
        "developer", "software engineer",
        "entwicklerin", "entwickler",
    ],
    "entwickler": [
        "entwickler", "entwicklerin", "softwareentwickler", "software entwickler", "programmierer",
        "developer", "software engineer", "dev",
        "developpeur", "développeur", "developpeuse", "ingenieur logiciel",
    ],
    "entwicklerin": [
        "entwicklerin", "entwickler", "softwareentwickler",
        "developer", "software engineer",
        "developpeuse", "développeur",
    ],
    "software engineer": [
        "software engineer", "developer", "swe", "software developer",
        "ingenieur logiciel", "ingénieur logiciel", "developpeur", "développeur", "developpeuse",
        "softwareentwickler", "software entwickler", "entwickler",
    ],
    "ingenieur": [
        "ingenieur", "ingénieur", "ingenieure", "ingénieure",
        "engineer", "engineering",
        "ingenieurin",
    ],
    "engineer": [
        "engineer", "engineering",
        "ingenieur", "ingénieur", "ingenieure", "ingénieure",
        "ingenieurin",
    ],

    # Cybersecurity
    "cybersecurity": [
        "cybersecurity", "cyber security", "infosec", "information security", "security analyst",
        "cybersecurite", "cybersécurité", "cyber securite", "cyber sécurité", "securite informatique", "sécurité informatique", "securite des systemes", "sécurité des systèmes", "securite", "sécurité",
        "cybersicherheit", "it sicherheit", "it-sicherheit", "sicherheit", "informationssicherheit", "datensicherheit",
    ],
    "cybersecurite": [
        "cybersecurite", "cybersécurité", "cyber securite", "cyber sécurité", "securite informatique", "sécurité informatique", "securite", "sécurité",
        "cybersecurity", "cyber security", "information security", "infosec",
        "cybersicherheit", "it sicherheit", "it-sicherheit", "sicherheit",
    ],
    "cybersicherheit": [
        "cybersicherheit", "it sicherheit", "it-sicherheit", "sicherheit", "informationssicherheit", "datensicherheit",
        "cybersecurity", "cyber security", "infosec",
        "cybersecurite", "cybersécurité", "securite informatique", "sécurité informatique", "securite", "sécurité",
    ],
    "security": [
        "security", "infosec", "cybersecurity",
        "securite", "sécurité", "cybersecurite", "cybersécurité",
        "sicherheit", "cybersicherheit", "it sicherheit", "it-sicherheit",
    ],
    "securite": [
        "securite", "sécurité", "cybersecurite", "cybersécurité", "securite informatique", "sécurité informatique",
        "security", "cybersecurity", "infosec",
        "sicherheit", "cybersicherheit", "it sicherheit", "it-sicherheit",
    ],
    "sicherheit": [
        "sicherheit", "it-sicherheit", "it sicherheit", "cybersicherheit", "informationssicherheit",
        "security", "cybersecurity", "infosec",
        "securite", "sécurité", "cybersecurite", "cybersécurité",
    ],

    # Data
    "data": [
        "data", "data scientist", "data analyst", "data engineer",
        "donnees", "données", "analyste donnees", "ingenieur donnees",
        "daten", "datenanalyst", "datenbank",
    ],
    "donnees": [
        "donnees", "data", "daten",
    ],
    "daten": [
        "daten", "data", "donnees",
    ],

    # Work Arrangement
    "remote": [
        "remote", "telework", "wfh", "work from home",
        "teletravail", "distanciel", "en teletravail", "a distance",
        "homeoffice", "home office", "mobiles arbeiten", "fernarbeit",
    ],
    "teletravail": [
        "teletravail", "distanciel",
        "remote", "telework", "wfh",
        "homeoffice", "home office", "mobiles arbeiten",
    ],
    "homeoffice": [
        "homeoffice", "home office", "mobiles arbeiten",
        "remote", "telework",
        "teletravail", "distanciel",
    ],
    "hybrid": [
        "hybrid", "partially remote",
        "hybride", "teletravail partiel",
        "hybrid", "teilweise homeoffice",
    ],
    "hybride": [
        "hybride", "teletravail partiel",
        "hybrid", "partially remote",
    ],

    # Roles & Hierarchy
    "architect": [
        "architect", "software architect", "cloud architect",
        "architecte", "architecte logiciel", "architecte cloud",
        "architekt", "architektin", "softwarearchitekt",
    ],
    "architecte": [
        "architecte", "architect", "architekt",
    ],
    "architekt": [
        "architekt", "architektin", "architect", "architecte",
    ],
    "project manager": [
        "project manager", "pm", "scrum master", "product owner",
        "chef de projet", "responsable de projet", "directeur de projet",
        "projektleiter", "projektmanager", "projektleiterin",
    ],
    "chef de projet": [
        "chef de projet", "responsable de projet",
        "project manager", "pm",
        "projektleiter", "projektmanager",
    ],
    "consultant": [
        "consultant", "consultante", "advisory",
        "berater", "beraterin", "consultant",
    ],
    "administrator": [
        "administrator", "admin", "system administrator", "sysadmin",
        "administrateur", "administratrice",
        "administrator", "administratorin", "systemadministrator",
    ],
}


ACCENT_AND_VARIANT_EXPANSIONS: dict[str, list[str]] = {
    "cybersecurite": ["cybersécurité", "cyber-sécurité", "cyber securite", "cyber sécurité"],
    "securite": ["sécurité"],
    "sicherheit": ["it-sicherheit", "it sicherheit"],
    "it sicherheit": ["it-sicherheit"],
    "developpeur": ["développeur"],
    "developpeurs": ["développeurs"],
    "developpeuse": ["développeuse"],
    "developpeuses": ["développeuses"],
    "ingenieur": ["ingénieur"],
    "ingenieurs": ["ingénieurs"],
    "ingenieure": ["ingénieure"],
    "ingenieures": ["ingénieures"],
    "ingenierie": ["ingénierie"],
    "donnees": ["données"],
    "teletravail": ["télétravail"],
    "systeme": ["système"],
    "systemes": ["systèmes"],
    "reseau": ["réseau"],
    "reseaux": ["réseaux"],
    "etudiant": ["étudiant"],
    "etudiante": ["étudiante"],
    "general": ["général"],
    "generale": ["générale"],
    "preparatoire": ["préparatoire"],
    "numerique": ["numérique"],
}


# ---------------------------------------------------------------------------
# Search Plan Data Structure
# ---------------------------------------------------------------------------

@dataclass
class SearchQueryPlan:
    raw_query: str
    normalized_query: str
    tokens: list[str] = field(default_factory=list)
    normalized_tokens: list[str] = field(default_factory=list)
    synonym_phrases: list[str] = field(default_factory=list)
    all_matching_terms: list[str] = field(default_factory=list)
    is_internship_query: bool = False
    is_developer_query: bool = False
    is_security_query: bool = False


def prepare_search_plan(query: str) -> SearchQueryPlan:
    """Analyze, normalize, and expand search query into an actionable multi-tier search plan."""
    cleaned = (query or "").strip()
    norm_query = normalize_search_text(cleaned)
    if not norm_query:
        return SearchQueryPlan(raw_query="", normalized_query="")

    tokens = [t for t in re.findall(r"\b\w+\b", norm_query) if len(t) > 0]
    norm_tokens = [normalize_search_token(t) for t in tokens if len(t) > 0]

    synonyms: list[str] = []
    all_terms: list[str] = [cleaned, norm_query]

    # 1. Whole query match in concept synonyms
    if norm_query in CONCEPT_SYNONYMS:
        for s in CONCEPT_SYNONYMS[norm_query]:
            if s not in synonyms:
                synonyms.append(s)
            if s not in all_terms:
                all_terms.append(s)

    # 2. Token-level concept expansion
    for token in norm_tokens:
        if token in CONCEPT_SYNONYMS:
            for s in CONCEPT_SYNONYMS[token]:
                if s not in synonyms:
                    synonyms.append(s)
                if s not in all_terms:
                    all_terms.append(s)
                # If multi-token query, create substituted phrase (e.g. "python internship" -> "python stage")
                if len(tokens) > 1 and len(token) > 2:
                    subbed = re.sub(rf"\b{re.escape(token)}\b", s, norm_query)
                    if subbed != norm_query and subbed not in synonyms:
                        synonyms.append(subbed)
                        all_terms.append(subbed)

    # 3. Add individual tokens to terms for broad matching
    for t in tokens:
        if len(t) > 1 and t not in all_terms:
            all_terms.append(t)
    for nt in norm_tokens:
        if len(nt) > 1 and nt not in all_terms:
            all_terms.append(nt)

    # 4. Expand terms with accented forms and hyphen variations for DB matching
    expanded_terms: list[str] = []
    for term in all_terms:
        expanded_terms.append(term)
        norm_t = normalize_search_text(term)
        if norm_t in ACCENT_AND_VARIANT_EXPANSIONS:
            for exp in ACCENT_AND_VARIANT_EXPANSIONS[norm_t]:
                if exp not in expanded_terms:
                    expanded_terms.append(exp)
        if " " in term:
            hyphenated = term.replace(" ", "-")
            if hyphenated not in expanded_terms:
                expanded_terms.append(hyphenated)
        if "-" in term:
            spaced = term.replace("-", " ")
            if spaced not in expanded_terms:
                expanded_terms.append(spaced)

    # Deduplicate terms while preserving order
    all_terms = list(dict.fromkeys(expanded_terms))
    synonyms = list(dict.fromkeys(synonyms))

    # Detect high-value career concepts
    internship_tokens = {"intern", "internship", "stage", "stagiaire", "pfe", "alternance", "praktikum", "praktikant", "werkstudent", "trainee"}
    developer_tokens = {"dev", "developer", "developpeur", "developpeuse", "software", "entwickler", "entwicklerin", "engineer", "ingenieur"}
    security_tokens = {"security", "cybersecurity", "securite", "cybersecurite", "sicherheit", "cybersicherheit", "infosec"}

    is_intern = any(t in internship_tokens for t in norm_tokens) or any(t in norm_query for t in ["intern", "stage", "praktik"])
    is_dev = any(t in developer_tokens for t in norm_tokens)
    is_sec = any(t in security_tokens for t in norm_tokens)

    return SearchQueryPlan(
        raw_query=cleaned,
        normalized_query=norm_query,
        tokens=tokens,
        normalized_tokens=norm_tokens,
        synonym_phrases=synonyms,
        all_matching_terms=all_terms,
        is_internship_query=is_intern,
        is_developer_query=is_dev,
        is_security_query=is_sec,
    )


# ---------------------------------------------------------------------------
# Relevance Scoring Engine
# ---------------------------------------------------------------------------

@dataclass
class RelevanceScore:
    total_score: float
    title_score: float = 0.0
    metadata_score: float = 0.0
    description_score: float = 0.0
    match_reasons: list[str] = field(default_factory=list)


def calculate_job_relevance(job: Any, plan: SearchQueryPlan) -> RelevanceScore:
    """
    Calculate explainable deterministic relevance score for a job against a SearchQueryPlan.
    
    Tiers:
    - Title matches: 800 - 1300+ points
    - Metadata matches: 150 - 350 points
    - Description matches: 10 - 75 points
    
    A job with the query in its title will ALWAYS rank higher than a job matching
    only in the description.
    """
    if not plan.normalized_query:
        return RelevanceScore(total_score=0.0)

    title_raw = (getattr(job, "title", "") or "").strip()
    norm_title = normalize_search_text(title_raw)
    title_tokens = [normalize_search_token(t) for t in re.findall(r"\b\w+\b", norm_title)]
    title_token_set = set(title_tokens)

    title_score = 0.0
    metadata_score = 0.0
    desc_score = 0.0
    reasons: list[str] = []

    q_norm = plan.normalized_query
    q_tokens = plan.normalized_tokens

    # =========================================================================
    # 1. Title Evaluation (Highest Weight)
    # =========================================================================

    # 1.1 Exact normalized title match
    if norm_title == q_norm:
        title_score += 1200.0
        reasons.append("exact_title_match")
    # 1.2 Title contains exact query as phrase
    elif re.search(rf"\b{re.escape(q_norm)}\b", norm_title):
        title_score += 900.0
        reasons.append("title_contains_query_phrase")
        # Leading position bonus (query phrase appears in the first 3 words)
        words = norm_title.split()
        if words and q_norm in " ".join(words[:3]):
            title_score += 100.0
            reasons.append("title_leading_position_bonus")
    # 1.3 Title contains a multilingual synonym phrase (e.g. "stage" or "praktikum" for "internship")
    else:
        syn_matched = False
        for syn in plan.synonym_phrases:
            norm_syn = normalize_search_text(syn)
            if not norm_syn:
                continue
            if norm_title == norm_syn:
                title_score += 1050.0
                reasons.append(f"title_exact_synonym_match:{syn}")
                syn_matched = True
                break
            elif re.search(rf"\b{re.escape(norm_syn)}\b", norm_title):
                title_score += 800.0
                reasons.append(f"title_contains_synonym:{syn}")
                words = norm_title.split()
                if words and norm_syn in " ".join(words[:3]):
                    title_score += 100.0
                    reasons.append("title_leading_position_bonus")
                syn_matched = True
                break

        # 1.4 Token-level matching in title
        if not syn_matched and q_tokens:
            matched_q_tokens = [qt for qt in q_tokens if qt in title_token_set]
            if matched_q_tokens:
                ratio = len(matched_q_tokens) / max(len(q_tokens), 1)
                # Base score: up to 600 points depending on token coverage
                tok_score = 500.0 * ratio + (100.0 if ratio == 1.0 else 0.0)
                title_score += tok_score
                reasons.append(f"title_token_match:{len(matched_q_tokens)}/{len(q_tokens)}")
            else:
                # Check if any synonym token appears in title
                for syn in plan.synonym_phrases:
                    syn_toks = [normalize_search_token(st) for st in re.findall(r"\b\w+\b", syn)]
                    m = [st for st in syn_toks if st in title_token_set]
                    if m:
                        title_score += 450.0 * (len(m) / max(len(syn_toks), 1))
                        reasons.append(f"title_synonym_token_match:{m[0]}")
                        break

    # =========================================================================
    # 2. Metadata Evaluation
    # =========================================================================

    emp_type = (getattr(job, "employment_type", "") or "").lower()
    department = (getattr(job, "department", "") or "").lower()
    company_name = (getattr(job, "company_name", "") or "").lower()
    if not company_name and hasattr(job, "company") and job.company:
        company_name = (getattr(job.company, "name", "") or "").lower()
    location = (getattr(job, "location", "") or "").lower()

    # 2.1 Employment type concept match (e.g. searching "internship" and employment_type="internship")
    if plan.is_internship_query:
        if emp_type in ("internship", "stage", "praktikum", "alternance", "apprenticeship"):
            metadata_score += 350.0
            reasons.append("metadata_employment_type_internship_match")

    # 2.2 Department / Category match
    norm_dept = normalize_search_text(department)
    if norm_dept:
        if q_norm in norm_dept:
            metadata_score += 150.0
            reasons.append("metadata_department_match")
        elif any(syn in norm_dept for syn in plan.synonym_phrases[:5]):
            metadata_score += 100.0
            reasons.append("metadata_department_synonym_match")

    # 2.3 Company Name match
    norm_comp = normalize_search_text(company_name)
    if norm_comp and (q_norm in norm_comp or any(qt in norm_comp for qt in q_tokens if len(qt) > 2)):
        metadata_score += 150.0
        reasons.append("metadata_company_match")

    # 2.4 Location match
    norm_loc = normalize_search_text(location)
    if norm_loc and (q_norm in norm_loc or any(qt in norm_loc for qt in q_tokens if len(qt) > 2)):
        metadata_score += 80.0
        reasons.append("metadata_location_match")

    # =========================================================================
    # 3. Description Evaluation (Low Weight, Never Overrides Title)
    # =========================================================================

    desc_raw = getattr(job, "description", "") or ""
    if desc_raw:
        norm_desc = normalize_search_text(desc_raw)
        if norm_desc:
            # 3.1 Exact query phrase in description
            if re.search(rf"\b{re.escape(q_norm)}\b", norm_desc):
                desc_score += 60.0
                reasons.append("desc_phrase_match")
                # Multiple occurrences bonus (capped)
                occurrences = len(re.findall(rf"\b{re.escape(q_norm)}\b", norm_desc))
                if occurrences > 1:
                    desc_score += min(occurrences * 3.0, 15.0)
            # 3.2 Synonym phrase in description
            else:
                for syn in plan.synonym_phrases[:8]:
                    norm_syn = normalize_search_text(syn)
                    if norm_syn and re.search(rf"\b{re.escape(norm_syn)}\b", norm_desc):
                        desc_score += 40.0
                        reasons.append(f"desc_synonym_match:{syn}")
                        break

            # 3.3 Token matches in description (capped)
            if q_tokens:
                desc_tokens_matched = sum(1 for qt in q_tokens if len(qt) > 2 and re.search(rf"\b{re.escape(qt)}\b", norm_desc))
                if desc_tokens_matched > 0:
                    desc_score += min(desc_tokens_matched * 10.0, 30.0)
                    reasons.append(f"desc_token_matches:{desc_tokens_matched}")

    total_score = round(title_score + metadata_score + desc_score, 2)
    return RelevanceScore(
        total_score=total_score,
        title_score=title_score,
        metadata_score=metadata_score,
        description_score=desc_score,
        match_reasons=reasons,
    )
