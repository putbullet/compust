import html
import re
import unicodedata

# Common compound variants mapped to canonical space-separated or standard forms
COMPOUND_REPLACEMENTS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bfront[-_ ]?end\b", re.IGNORECASE), "front end"),
    (re.compile(r"\bback[-_ ]?end\b", re.IGNORECASE), "back end"),
    (re.compile(r"\bfull[-_ ]?stack\b", re.IGNORECASE), "full stack"),
    (re.compile(r"\bdev[-_ ]?ops\b", re.IGNORECASE), "devops"),
    (re.compile(r"\bcyber[-_ ]?security\b", re.IGNORECASE), "cyber security"),
    (re.compile(r"\bdata[-_ ]?base\b", re.IGNORECASE), "database"),
    (re.compile(r"\bcloud[-_ ]?native\b", re.IGNORECASE), "cloud native"),
    (re.compile(r"\bquality[-_ ]?assurance\b", re.IGNORECASE), "quality assurance"),
    (re.compile(r"\bmachine[-_ ]?learning\b", re.IGNORECASE), "machine learning"),
    (re.compile(r"\bdeep[-_ ]?learning\b", re.IGNORECASE), "deep learning"),
    (re.compile(r"\bopen[-_ ]?source\b", re.IGNORECASE), "open source"),
    (re.compile(r"\bsys[-_ ]?admin\b", re.IGNORECASE), "sysadmin"),
]

# Patterns for parenthetical or suffixed noise commonly attached to job titles
NOISE_PATTERNS: list[re.Pattern] = [
    # Gender tags e.g. (m/f/d), (h/f), (m/w/d), (all genders)
    re.compile(r"\s*[\(\[\{]\s*(?:m/f/d|h/f|m/w/d|f/m/d|all\s+genders|w/m/d|h/f/x|m/f)\s*[\)\]\}]", re.IGNORECASE),
    # Work mode tags e.g. (remote), [hybrid], (on-site), (wfh)
    re.compile(r"\s*[\(\[\{]\s*(?:remote|hybrid|on[- ]?site|telework|t[eé]l[eé]travail|wfh)\s*[\)\]\}]", re.IGNORECASE),
    # Contract type tags e.g. (full-time), (cdi), (cdd), (internship), (stage)
    re.compile(r"\s*[\(\[\{]\s*(?:full[- ]?time|part[- ]?time|contract|permanent|cdi|cdd|internship|stage|pfe|freelance)\s*[\)\]\}]", re.IGNORECASE),
    # Job requisition IDs e.g. (#1234), (req-1234), (id: 4321)
    re.compile(r"\s*[\(\[\{]\s*(?:req(?:uisition)?|id|ref)?[- :]*\d+\s*[\)\]\}]", re.IGNORECASE),
    # Leading requisition numbers e.g. "REQ-1234: ", "#1234 - "
    re.compile(r"^\s*(?:req(?:uisition)?|ref)?[- :]*\d+\s*[-:–—]\s*", re.IGNORECASE),
]

# Suffixes after dash or pipe specifying locations or job types
LOCATION_OR_MODE_SUFFIX = re.compile(
    r"\s*[-–—|/]\s*(?:remote|hybrid|on[- ]?site|cdi|cdd|full[- ]?time|part[- ]?time|contract|morocco|maroc|casablanca|rabat|paris|london|france|uk|usa?|dubai|berlin|new york)\s*$",
    re.IGNORECASE,
)


def clean_unicode_and_whitespace(text: str) -> str:
    """Normalize Unicode (NFKC), decode HTML entities, and collapse whitespace."""
    if not text:
        return ""
    # Decode HTML entities like &amp;, &#39;, &nbsp;
    decoded = html.unescape(text)
    # NFKC normalizes compatibility characters, ligature, non-breaking spaces
    normalized = unicodedata.normalize("NFKC", decoded)
    # Replace non-breaking spaces and unicode dashes
    normalized = re.sub(r"[\u00a0\u2000-\u200b\u202f\u205f\u3000]", " ", normalized)
    normalized = re.sub(r"[\u2010-\u2015\u2212]", "-", normalized)
    normalized = re.sub(r"[\u2018\u2019\u201b]", "'", normalized)
    normalized = re.sub(r"[\u201c\u201d\u201f]", '"', normalized)
    # Collapse multiple whitespaces and trim
    return re.sub(r"\s+", " ", normalized).strip()


def strip_title_noise(text: str) -> str:
    """Strip common boilerplate prefixes/suffixes like (m/f/d), (Remote), or ' - Casablanca'."""
    cleaned = text
    for pat in NOISE_PATTERNS:
        cleaned = pat.sub("", cleaned)
    # Strip trailing location/mode suffix if present
    cleaned = LOCATION_OR_MODE_SUFFIX.sub("", cleaned)
    # Strip leading/trailing non-alphanumeric punctuation
    cleaned = re.sub(r"^[\s\-_–—|/:,;.]+|[\s\-_–—|/:,;.]+$", "", cleaned)
    return cleaned.strip()


def normalize_title(text: str, apply_compound_canonicalization: bool = True) -> str:
    """
    Produce a canonical, normalized string for title comparison.
    1. Clean unicode, unescape html, collapse whitespace
    2. Strip leading/trailing surrounding noise
    3. Lowercase
    4. Canonicalize compound tokens (e.g. front-end -> front end)
    5. Strip residual outer punctuation
    """
    cleaned = clean_unicode_and_whitespace(text)
    cleaned = strip_title_noise(cleaned)
    lowered = cleaned.lower()

    if apply_compound_canonicalization:
        for pat, repl in COMPOUND_REPLACEMENTS:
            lowered = pat.sub(repl, lowered)

    # Hyphens between words become spaces (e.g. Senior Software-Engineer -> senior software engineer)
    lowered = re.sub(r"(?<=\w)-(?=\w)", " ", lowered)

    # Clean punctuation except inner slashes and apostrophes that are part of words
    lowered = re.sub(r"[^\w\s/']", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def generate_normalized_variants(text: str) -> list[str]:
    """
    Generate the primary normalized title and common spelling/compound variants
    to ensure matching regardless of whether the page uses 'front end', 'frontend', or 'front-end'.
    """
    base = normalize_title(text, apply_compound_canonicalization=True)
    if not base:
        return []

    variants = [base]

    # Also generate raw normalized without compound substitution
    raw_norm = normalize_title(text, apply_compound_canonicalization=False)
    if raw_norm and raw_norm not in variants:
        variants.append(raw_norm)

    # For compound variations, ensure both separated, fused and hyphenated variants are present
    for canonical, fused, hyphenated in [
        ("front end", "frontend", "front-end"),
        ("back end", "backend", "back-end"),
        ("full stack", "fullstack", "full-stack"),
        ("cyber security", "cybersecurity", "cyber-security"),
        ("cloud native", "cloudnative", "cloud-native"),
        ("quality assurance", "qa", "quality-assurance"),
    ]:
        for v in list(variants):
            if canonical in v:
                f = v.replace(canonical, fused)
                h = v.replace(canonical, hyphenated)
                if f not in variants:
                    variants.append(f)
                if h not in variants:
                    variants.append(h)
            elif fused in v:
                c = v.replace(fused, canonical)
                h = v.replace(fused, hyphenated)
                if c not in variants:
                    variants.append(c)
                if h not in variants:
                    variants.append(h)

    return variants


def tokenize_title(normalized_title: str) -> list[str]:
    """Split a normalized title into alphanumeric tokens."""
    return [tok for tok in re.split(r"[\s\-_/]+", normalized_title) if tok]
