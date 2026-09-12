import re
from typing import TypedDict


class ParsedLocation(TypedDict):
    city: str | None
    country: str | None
    raw: str | None


# Canonical mappings for employment types
EMPLOYMENT_TYPE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(cdi|full[- ]?time|permanent|temps plein|regular|indéterminée)\b", re.IGNORECASE), "full_time"),
    (re.compile(r"\b(cdd|contract|fixed[- ]?term|temporaire|temporary|déterminée)\b", re.IGNORECASE), "contract"),
    (re.compile(r"\b(stage|internship|intern|pfe|alternance|apprentissage|stagiaire)\b", re.IGNORECASE), "internship"),
    (re.compile(r"\b(temps partiel|part[- ]?time)\b", re.IGNORECASE), "part_time"),
    (re.compile(r"\b(freelance|ind[eé]pendant|contractor|consultant)\b", re.IGNORECASE), "freelance"),
]

# Canonical mappings for work / remote modes
REMOTE_TYPE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(remote|t[eé]l[eé]travail( complet| total)?|100% remote|distanciel|work from home|wfh)\b", re.IGNORECASE), "remote"),
    (re.compile(r"\b(hybrid|hybride|partiel|flexible)\b", re.IGNORECASE), "hybrid"),
    (re.compile(r"\b(on[- ]?site|sur site|pr[eé]sentiel|office|in[- ]?office)\b", re.IGNORECASE), "onsite"),
]

# Tech skill canonicalization dictionary
SKILL_SYNONYMS: dict[str, str] = {
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "react native": "React Native",
    "python": "Python",
    "python3": "Python",
    "py": "Python",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "docker": "Docker",
    "docker-compose": "Docker",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",
    "angular": "Angular",
    "angularjs": "Angular",
    "aws": "AWS",
    "amazon web services": "AWS",
    "azure": "Azure",
    "microsoft azure": "Azure",
    "gcp": "GCP",
    "google cloud": "GCP",
    "sql": "SQL",
    "mysql": "MySQL",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "ci/cd": "CI/CD",
    "graphql": "GraphQL",
    "rest": "REST API",
    "rest api": "REST API",
    "linux": "Linux",
    "java": "Java",
    "spring": "Spring Boot",
    "spring boot": "Spring Boot",
    "c#": "C#",
    ".net": ".NET",
    "golang": "Go",
    "go": "Go",
}

# Common cities in Morocco and target markets
KNOWN_CITIES = [
    "Casablanca", "Rabat", "Marrakech", "Fès", "Tanger", "Agadir", "Salé",
    "Kénitra", "Oujda", "Tétouan", "Mohammédia", "Technopolis", "Sidi Maarouf",
    "Paris", "Lyon", "Toulouse", "Nantes", "Lille", "Bordeaux", "Dubai", "Madrid",
]


def normalize_employment_type(raw: str | None) -> str | None:
    """Normalizes unstructured employment string to canonical token."""
    if not raw or not raw.strip():
        return None
    cleaned = raw.strip()
    for pattern, canonical in EMPLOYMENT_TYPE_PATTERNS:
        if pattern.search(cleaned):
            return canonical
    if len(cleaned) <= 25 and not any(tag in cleaned for tag in ("<", ">", "{", "}", "\n")):
        return cleaned.lower()
    return None


def normalize_remote_type(raw: str | None) -> str | None:
    """Normalizes unstructured workplace/remote mode string to canonical token."""
    if not raw or not raw.strip():
        return None
    cleaned = raw.strip()
    for pattern, canonical in REMOTE_TYPE_PATTERNS:
        if pattern.search(cleaned):
            return canonical
    if len(cleaned) <= 25 and not any(tag in cleaned for tag in ("<", ">", "{", "}", "\n")):
        return cleaned.lower()
    return None


def normalize_location(raw: str | None) -> ParsedLocation:
    """Extracts standardized city and country hints from free-text locations."""
    if not raw or not raw.strip():
        return ParsedLocation(city=None, country=None, raw=None)

    raw_clean = raw.strip()
    city_match: str | None = None
    country_match: str | None = None

    for city in KNOWN_CITIES:
        if re.search(rf"\b{re.escape(city)}\b", raw_clean, re.IGNORECASE):
            city_match = city
            break

    # Country detection
    if re.search(r"\b(maroc|morocco|ma)\b", raw_clean, re.IGNORECASE):
        country_match = "Morocco"
    elif re.search(r"\b(france|fr)\b", raw_clean, re.IGNORECASE):
        country_match = "France"

    # If city is in Morocco and no country was explicit, default to Morocco
    if city_match in ["Casablanca", "Rabat", "Marrakech", "Fès", "Tanger", "Agadir", "Salé", "Kénitra", "Technopolis", "Sidi Maarouf"] and not country_match:
        country_match = "Morocco"

    return ParsedLocation(
        city=city_match,
        country=country_match,
        raw=raw_clean,
    )


def normalize_skills(skills: list[str] | None) -> list[str]:
    """Canonicalizes, deduplicates, and formats technical skill tags."""
    if not skills:
        return []

    normalized_set: dict[str, str] = {}
    for s in skills:
        if not s or not s.strip():
            continue
        cleaned = s.strip()
        key = cleaned.lower()
        canonical = SKILL_SYNONYMS.get(key, cleaned)
        normalized_set[canonical.lower()] = canonical

    return list(normalized_set.values())
