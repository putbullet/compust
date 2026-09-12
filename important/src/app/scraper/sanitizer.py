import html
import re
import bleach
from bs4 import BeautifulSoup


ALLOWED_TAGS = [
    "p",
    "br",
    "span",
    "strong",
    "em",
    "b",
    "i",
    "u",
    "ul",
    "ol",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "blockquote",
    "hr",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "a",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target"],
    "*": ["class"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]
DANGEROUS_TAGS = ["script", "style", "iframe", "noscript", "object", "embed", "frame", "frameset"]


def sanitize_html(raw_html: str | None) -> str | None:
    """Sanitize raw HTML content (e.g. job descriptions) to strip executable scripts,

    iframes, event handlers, and dangerous protocols while preserving safe formatting tags.
    """
    if raw_html is None:
        return None

    if not raw_html.strip():
        return ""

    # Pre-parse with BeautifulSoup to completely decompose dangerous tags and their content
    soup = BeautifulSoup(raw_html, "html.parser")
    for dangerous in soup.find_all(DANGEROUS_TAGS):
        dangerous.decompose()

    cleaned = bleach.clean(
        str(soup),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    return cleaned.strip()


def sanitize_plain_text(text: str | None) -> str | None:
    """Strip all HTML tags, scripts, and entities from plain-text fields like titles and locations."""
    if text is None:
        return None

    if not text.strip():
        return ""

    # Pre-parse to decompose script/style nodes
    soup = BeautifulSoup(text, "html.parser")
    for dangerous in soup.find_all(DANGEROUS_TAGS):
        dangerous.decompose()

    cleaned = bleach.clean(
        str(soup),
        tags=[],
        attributes={},
        strip=True,
    )
    unescaped = html.unescape(cleaned)
    return re.sub(r"\s+", " ", unescaped).strip()
