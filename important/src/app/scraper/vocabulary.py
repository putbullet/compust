import re
from typing import TypedDict


class ParsedLocation(TypedDict):
    city: str | None
    country: str | None
    raw: str | None


# Canonical mappings for employment types
EMPLOYMENT_TYPE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(cdi|full[- ]?time|permanent|temps plein|regular|ind[eé]termin[eé]\w*|vollzeit|festanstellung|unbefristet\w*)\b", re.IGNORECASE), "full_time"),
    (re.compile(r"\b(cdd|contract|fixed[- ]?term|temporaire|temporary|d[eé]termin[eé]\w*|befristet\w*|zeitarbeit)\b", re.IGNORECASE), "contract"),
    (re.compile(r"\b(stage|internship|intern|pfe|alternance|apprentissage|stagiaire|apprenti[e]?|praktikum|praktikant(?:in)?|werkstudent(?:in)?|ausbildung|trainee|berufseinsteiger|training)\b", re.IGNORECASE), "internship"),
    (re.compile(r"\b(temps partiel|part[- ]?time|teilzeit)\b", re.IGNORECASE), "part_time"),
    (re.compile(r"\b(freelance|ind[eé]pendant|contractor|consultant|freiberufler|freiberuflich)\b", re.IGNORECASE), "freelance"),
]

# Canonical mappings for work / remote modes
REMOTE_TYPE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(hybrid|hybride|partiel|flexible|teilweise homeoffice|home[- ]?office\s+m[oö]glich|t[eé]l[eé]travail\s+partiel|remote\s+partiel|partial\s+remote)\b", re.IGNORECASE), "hybrid"),
    (re.compile(r"\b(remote|t[eé]l[eé]travail( complet| total)?|100% remote|distanciel|work from home|wfh|home[- ]?office|mobiles arbeiten)\b", re.IGNORECASE), "remote"),
    (re.compile(r"\b(on[- ]?site|sur site|pr[eé]sentiel|office|in[- ]?office|vor ort)\b", re.IGNORECASE), "onsite"),
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
    "api rest": "REST API",
    "apis rest": "REST API",
    "linux": "Linux",
    "ubuntu": "Linux",
    "debian": "Linux",
    "java": "Java",
    "spring": "Spring Boot",
    "spring boot": "Spring Boot",
    "c#": "C#",
    ".net": ".NET",
    "golang": "Go",
    "go": "Go",
    "c": "C",
    "c++": "C++",
    "cpp": "C++",
    "php": "PHP",
    "laravel": "Laravel",
    "symfony": "Symfony",
    "nginx": "Nginx",
    "apache": "Apache",
    # Cybersecurity & Infrastructure & Networking
    "sécurité des systèmes": "System Security",
    "securite des systemes": "System Security",
    "system security": "System Security",
    "sécurité": "Cybersecurity",
    "securite": "Cybersecurity",
    "cybersécurité": "Cybersecurity",
    "cybersecurite": "Cybersecurity",
    "cybersecurity": "Cybersecurity",
    "analyse des vulnérabilités": "Vulnerability Analysis",
    "analyse des vulnerabilites": "Vulnerability Analysis",
    "vulnerability analysis": "Vulnerability Analysis",
    "gestion des vulnérabilités": "Vulnerability Analysis",
    "vulnerability management": "Vulnerability Analysis",
    "tests de sécurité": "Security Testing",
    "tests de securite": "Security Testing",
    "security testing": "Security Testing",
    "penetration testing": "Security Testing",
    "pentest": "Security Testing",
    "audit": "Security Audit",
    "audit de sécurité": "Security Audit",
    "audit de securite": "Security Audit",
    "bash / shell scripting": "Bash",
    "bash": "Bash",
    "shell": "Bash",
    "shell scripting": "Bash",
    "notions de réseaux": "Networking",
    "notions de reseaux": "Networking",
    "réseautage ip": "Networking",
    "reseautage ip": "Networking",
    "réseau": "Networking",
    "reseau": "Networking",
    "réseaux": "Networking",
    "reseaux": "Networking",
    "networking": "Networking",
    "network": "Networking",
    "tcp/ip": "Networking",
    "cloud computing": "Cloud Computing",
    "environnements cloud": "Cloud Computing",
    "environnement cloud": "Cloud Computing",
    "cloud": "Cloud Computing",
    "principes devops": "DevOps",
    "devops": "DevOps",
    "conception d'infrastructure": "Infrastructure Design",
    "infrastructure design": "Infrastructure Design",
    "infrastructure": "Infrastructure Design",
    "technologies de virtualisation": "Virtualization",
    "virtualisation": "Virtualization",
    "virtualization": "Virtualization",
    "vmware": "Virtualization",
    "déploiement sdn pop": "SDN",
    "sdn": "SDN",
    "yara": "YARA",
    "threat intelligence": "Threat Intelligence",
    "owasp": "OWASP",
    "cryptographie": "Cryptography",
    "cryptography": "Cryptography",
    "siem": "SIEM",
    "soc": "SOC",
    "outils soc": "SOC",
    "wazuh": "Wazuh",
    "yolo": "YOLO",
    "llm": "LLM",
    "onnx": "ONNX",
    "intelligence artificielle": "AI",
    "artificial intelligence": "AI",
    "ia": "AI",
    # Soft skills & Professional competencies
    "communication": "Communication",
    "collaboration": "Collaboration",
    "résolution de problèmes": "Problem Solving",
    "resolution de problemes": "Problem Solving",
    "problem solving": "Problem Solving",
    "adaptabilité": "Adaptability",
    "adaptabilite": "Adaptability",
    "adaptability": "Adaptability",
    "esprit d'équipe": "Teamwork",
    "esprit d'equipe": "Teamwork",
    "travail en équipe": "Teamwork",
    "travail en equipe": "Teamwork",
    "teamwork": "Teamwork",
    "autonomie": "Autonomy",
    "autonomy": "Autonomy",
    "esprit analytique": "Analytical Thinking",
    "esprit synthétique et analytique": "Analytical Thinking",
    "esprit analytique et synthétique": "Analytical Thinking",
    "analytical thinking": "Analytical Thinking",
}

# Country Aliases & Identifiers (canonical country name -> list of aliases/regex keywords)
COUNTRY_ALIASES: list[tuple[str, str, list[str]]] = [
    # (Canonical Name, ISO-2 Code, [aliases / keywords])
    ("Morocco", "MA", ["morocco", "maroc", "al-maghrib", "marruecos", "ma"]),
    ("France", "FR", ["france", "francia", "fr"]),
    ("Germany", "DE", ["germany", "deutschland", "allemagne", "alemania", "de"]),
    ("United Kingdom", "GB", ["united kingdom", "uk", "great britain", "u.k.", "england", "scotland", "wales", "gb"]),
    ("United States", "US", ["united states", "united states of america", "usa", "u.s.a.", "u.s.", "us"]),
    ("United Arab Emirates", "AE", ["united arab emirates", "uae", "u.a.e.", "emirates", "émirats arabes unis", "ae"]),
    ("Saudi Arabia", "SA", ["saudi arabia", "saudi", "ksa", "k.s.a.", "arabie saoudite", "sa"]),
    ("Spain", "ES", ["spain", "españa", "espagne", "es"]),
    ("Belgium", "BE", ["belgium", "belgique", "belgië", "be"]),
    ("Netherlands", "NL", ["netherlands", "pays-bas", "nederland", "holland", "nl"]),
    ("Canada", "CA", ["canada", "ca"]),
    ("Switzerland", "CH", ["switzerland", "suisse", "schweiz", "svizzera", "ch"]),
    ("Italy", "IT", ["italy", "italia", "italie", "it"]),
    ("Ireland", "IE", ["ireland", "irlande", "ie"]),
    ("Sweden", "SE", ["sweden", "suède", "sverige", "se"]),
    ("Portugal", "PT", ["portugal", "pt"]),
    ("Poland", "PL", ["poland", "pologne", "polska", "pl"]),
    ("Singapore", "SG", ["singapore", "singapour", "sg"]),
    ("Australia", "AU", ["australia", "australie", "au"]),
    ("Japan", "JP", ["japan", "japon", "nihon", "jp"]),
    ("Brazil", "BR", ["brazil", "brésil", "brasil", "br"]),
    ("India", "IN", ["india", "inde", "in"]),
    ("Egypt", "EG", ["egypt", "égypte", "misr", "eg"]),
    ("Tunisia", "TN", ["tunisia", "tunisie", "tounes", "tn"]),
    ("Qatar", "QA", ["qatar", "qa"]),
    ("Kuwait", "KW", ["kuwait", "koweit", "kw"]),
    ("Bahrain", "BH", ["bahrain", "bahreïn", "bh"]),
    ("Oman", "OM", ["oman", "om"]),
    ("Luxembourg", "LU", ["luxembourg", "lu"]),
    ("Austria", "AT", ["austria", "autriche", "österreich", "at"]),
    ("Denmark", "DK", ["denmark", "danemark", "danmark", "dk"]),
    ("Norway", "NO", ["norway", "norvège", "norge", "no"]),
    ("Finland", "FI", ["finland", "finlande", "suomi", "fi"]),
    ("South Korea", "KR", ["south korea", "corée du sud", "korea", "kr"]),
    ("China", "CN", ["china", "chine", "cn"]),
    ("Mexico", "MX", ["mexico", "mexique", "méxico", "mx"]),
    ("Turkey", "TR", ["turkey", "turquie", "türkiye", "tr"]),
    ("South Africa", "ZA", ["south africa", "afrique du sud", "za"]),
    ("New Zealand", "NZ", ["new zealand", "nouvelle-zélande", "nz"]),
]

# Major city-to-country mapping (city -> Canonical Country Name)
CITY_TO_COUNTRY: dict[str, str] = {
    # Morocco
    "Casablanca": "Morocco", "Rabat": "Morocco", "Marrakech": "Morocco", "Fès": "Morocco",
    "Fes": "Morocco", "Tanger": "Morocco", "Tangier": "Morocco", "Agadir": "Morocco",
    "Salé": "Morocco", "Sale": "Morocco", "Kénitra": "Morocco", "Kenitra": "Morocco",
    "Oujda": "Morocco", "Tétouan": "Morocco", "Tetouan": "Morocco", "Mohammédia": "Morocco",
    "Mohammedia": "Morocco", "Technopolis": "Morocco", "Sidi Maarouf": "Morocco",
    # Germany
    "Berlin": "Germany", "Munich": "Germany", "München": "Germany", "Frankfurt": "Germany",
    "Hamburg": "Germany", "Cologne": "Germany", "Köln": "Germany", "Stuttgart": "Germany",
    "Düsseldorf": "Germany", "Dusseldorf": "Germany", "Dortmund": "Germany", "Essen": "Germany",
    "Leipzig": "Germany", "Bremen": "Germany", "Dresden": "Germany", "Hanover": "Germany",
    "Hannover": "Germany", "Nuremberg": "Germany", "Nürnberg": "Germany", "Bonn": "Germany",
    "Karlsruhe": "Germany", "Mannheim": "Germany", "Heidelberg": "Germany", "Wiesbaden": "Germany",
    "Darmstadt": "Germany", "Freiburg": "Germany", "Ulm": "Germany",
    # United Kingdom
    "London": "United Kingdom", "Manchester": "United Kingdom", "Birmingham": "United Kingdom",
    "Leeds": "United Kingdom", "Glasgow": "United Kingdom", "Edinburgh": "United Kingdom",
    "Bristol": "United Kingdom", "Liverpool": "United Kingdom", "Sheffield": "United Kingdom",
    "Belfast": "United Kingdom", "Cambridge": "United Kingdom", "Oxford": "United Kingdom",
    # United States
    "New York": "United States", "San Francisco": "United States", "Los Angeles": "United States",
    "Chicago": "United States", "Seattle": "United States", "Austin": "United States",
    "Boston": "United States", "Atlanta": "United States", "Denver": "United States",
    "Dallas": "United States", "Houston": "United States", "Miami": "United States",
    "San Jose": "United States", "San Diego": "United States", "Washington": "United States",
    # UAE
    "Dubai": "United Arab Emirates", "Abu Dhabi": "United Arab Emirates", "Sharjah": "United Arab Emirates",
    # Saudi Arabia
    "Riyadh": "Saudi Arabia", "Jeddah": "Saudi Arabia", "Dammam": "Saudi Arabia",
    "Khobar": "Saudi Arabia", "Dhahran": "Saudi Arabia", "Mecca": "Saudi Arabia", "Medina": "Saudi Arabia",
    # France
    "Paris": "France", "Lyon": "France", "Marseille": "France", "Toulouse": "France",
    "Nantes": "France", "Lille": "France", "Bordeaux": "France", "Strasbourg": "France",
    "Rennes": "France", "Nice": "France", "Montpellier": "France", "Grenoble": "France",
    "Colomiers": "France", "Courbevoie": "France", "Le Plessis-Robinson": "France",
    "Montreuil": "France", "Cesson-Sévigné": "France", "Cesson-Sevigne": "France",
    "Villeneuve-d'Ascq": "France", "Aix-en-Provence": "France", "Sophia Antipolis": "France",
    # Spain
    "Madrid": "Spain", "Barcelona": "Spain", "Valencia": "Spain", "Seville": "Spain",
    "Sevilla": "Spain", "Malaga": "Spain", "Málaga": "Spain", "Bilbao": "Spain",
    # Belgium
    "Brussels": "Belgium", "Bruxelles": "Belgium", "Antwerp": "Belgium", "Ghent": "Belgium", "Gent": "Belgium", "Liège": "Belgium",
    # Netherlands
    "Amsterdam": "Netherlands", "Rotterdam": "Netherlands", "The Hague": "Netherlands", "Utrecht": "Netherlands", "Eindhoven": "Netherlands",
    # Canada
    "Toronto": "Canada", "Vancouver": "Canada", "Montreal": "Canada", "Montréal": "Canada", "Ottawa": "Canada", "Calgary": "Canada",
    # Switzerland
    "Zurich": "Switzerland", "Zürich": "Switzerland", "Geneva": "Switzerland", "Genève": "Switzerland", "Basel": "Switzerland", "Lausanne": "Switzerland",
    # Italy
    "Rome": "Italy", "Roma": "Italy", "Milan": "Italy", "Milano": "Italy", "Turin": "Italy", "Torino": "Italy",
    # Ireland
    "Dublin": "Ireland", "Cork": "Ireland", "Galway": "Ireland",
    # Sweden
    "Stockholm": "Sweden", "Gothenburg": "Sweden", "Göteborg": "Sweden", "Malmö": "Sweden",
    # Portugal
    "Lisbon": "Portugal", "Lisboa": "Portugal", "Porto": "Portugal",
    # Poland
    "Warsaw": "Poland", "Warszawa": "Poland", "Krakow": "Poland", "Kraków": "Poland", "Wrocław": "Poland",
    # Singapore
    "Singapore": "Singapore",
    # Australia
    "Sydney": "Australia", "Melbourne": "Australia", "Brisbane": "Australia", "Perth": "Australia",
    # Japan
    "Tokyo": "Japan", "Osaka": "Japan", "Kyoto": "Japan",
    # India
    "Bangalore": "India", "Bengaluru": "India", "Mumbai": "India", "Delhi": "India", "New Delhi": "India", "Hyderabad": "India", "Pune": "India",
    # Egypt
    "Cairo": "Egypt", "Alexandria": "Egypt", "Giza": "Egypt",
    # Tunisia
    "Tunis": "Tunisia", "Sfax": "Tunisia", "Sousse": "Tunisia",
    # Qatar
    "Doha": "Qatar",
}

KNOWN_CITIES = list(CITY_TO_COUNTRY.keys())


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

    # 1. Check for city matches
    for city, mapped_country in CITY_TO_COUNTRY.items():
        if re.search(rf"\b{re.escape(city)}\b", raw_clean, re.IGNORECASE):
            city_match = city
            country_match = mapped_country
            break

    # 2. Check explicit country matches (country takes precedence if explicit, or fills if city didn't match)
    for c_name, c_code, aliases in COUNTRY_ALIASES:
        # Check aliases with word boundary
        for alias in aliases:
            # If alias is 2 letters (ISO code like DE, FR, US), ensure strict boundary/capitalization or separator
            if len(alias) == 2:
                pattern = rf"(?:^|[\s,/\(\)\-\|\.]{{1}}){re.escape(alias.upper())}(?:$|[\s,/\(\)\-\|\.]{{1}})"
                if re.search(pattern, raw_clean):
                    country_match = c_name
                    break
            else:
                if re.search(rf"\b{re.escape(alias)}\b", raw_clean, re.IGNORECASE):
                    country_match = c_name
                    break
        if country_match and country_match == c_name:
            break

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
