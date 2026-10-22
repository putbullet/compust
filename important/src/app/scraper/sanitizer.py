import html
import logging
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


SAFE_SVG_TAGS = [
    "svg",
    "g",
    "path",
    "circle",
    "rect",
    "line",
    "polyline",
    "polygon",
    "text",
    "tspan",
    "defs",
    "marker",
    "lineargradient",
    "linearGradient",
    "radialgradient",
    "radialGradient",
    "stop",
    "ellipse",
]
SAFE_SVG_TAGS_LOWER = {t.lower() for t in SAFE_SVG_TAGS}

SAFE_SVG_ATTRIBUTES = {
    "*": [
        "id",
        "class",
        "viewBox",
        "xmlns",
        "xmlns:xlink",
        "width",
        "height",
        "d",
        "fill",
        "stroke",
        "stroke-width",
        "stroke-dasharray",
        "stroke-linecap",
        "stroke-linejoin",
        "stroke-opacity",
        "fill-opacity",
        "opacity",
        "transform",
        "points",
        "x",
        "y",
        "x1",
        "y1",
        "x2",
        "y2",
        "cx",
        "cy",
        "r",
        "rx",
        "ry",
        "font-size",
        "font-family",
        "font-weight",
        "text-anchor",
        "dominant-baseline",
        "offset",
        "stop-color",
        "stop-opacity",
        "refX",
        "refY",
        "markerWidth",
        "markerHeight",
        "orient",
        "markerUnits",
        "marker-start",
        "marker-mid",
        "marker-end",
    ],
}

import xml.etree.ElementTree as ET
ET.register_namespace("", "http://www.w3.org/2000/svg")
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

logger = logging.getLogger("compust.sanitizer")


def sanitize_svg(raw_svg: str | None) -> str | None:
    """
    Sanitizes untrusted, LLM-generated SVG diagram markup.
    
    Guarantees:
    1. Strict well-formed XML parsing without external DTD or entity expansion.
    2. Elements are strictly restricted to safe, purely visual SVG tags
       (decomposing <script>, <foreignObject>, <iframe>, <object>, <embed>, <style>, etc.).
    3. All event handler attributes ('on*') are strictly stripped.
    4. href and xlink:href are restricted exclusively to internal fragment identifiers ('#...').
    5. Payload size and element complexity are capped to prevent DoS.
    6. On any parsing failure or unrecoverable malformation, degrades gracefully to None (no visible error).
    """
    if not raw_svg or not isinstance(raw_svg, str):
        return None

    # Reject entity expansion / DTD attacks across the entire payload
    raw_upper = raw_svg.upper()
    if "<!DOCTYPE" in raw_upper or "<!ENTITY" in raw_upper:
        logger.warning("SVG payload rejected: contains DTD / entity definitions")
        return None

    cleaned = raw_svg.strip()

    # Extract <svg ... </svg> if wrapped in markdown code fences or conversational prose
    if "```" in cleaned:
        svg_match = re.search(r"```(?:xml|svg)?\s*(<svg[\s\S]*?</svg>)\s*```", cleaned, re.IGNORECASE)
        if svg_match:
            cleaned = svg_match.group(1).strip()

    start_idx = cleaned.find("<svg")
    end_idx = cleaned.rfind("</svg>")
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        return None

    cleaned = cleaned[start_idx : end_idx + 6].strip()

    # Size cap: max 64KB
    if len(cleaned.encode("utf-8")) > 65536:
        logger.debug("SVG payload rejected: exceeds 64KB size limit")
        return None

    try:
        # Pre-filter using BeautifulSoup to decompose dangerous nodes and attributes
        soup = BeautifulSoup(cleaned, "html.parser")
        dangerous_tags = [
            "script",
            "foreignobject",
            "iframe",
            "object",
            "embed",
            "style",
            "audio",
            "video",
            "meta",
            "link",
            "base",
            "use",
        ]
        for dangerous in soup.find_all(dangerous_tags):
            dangerous.decompose()

        for el in soup.find_all():
            for attr in list(el.attrs.keys()):
                al = attr.lower()
                if al.startswith("on") or ("href" in al and not str(el.attrs[attr]).startswith("#")):
                    del el.attrs[attr]

        # Bleach clean pass with strict SVG allowlist
        cleaned = bleach.clean(
            str(soup),
            tags=SAFE_SVG_TAGS,
            attributes=SAFE_SVG_ATTRIBUTES,
            strip=True,
        )

        # XML Structure Validation via ElementTree
        root = ET.fromstring(cleaned)
        elements = list(root.iter())
        if len(elements) > 300:
            logger.debug("SVG payload rejected: exceeds 300 element complexity cap")
            return None

        # Verify element allowlist and clean attributes
        for el in elements:
            tag_name = el.tag.split("}")[-1].lower() if "}" in el.tag else el.tag.lower()
            if tag_name not in SAFE_SVG_TAGS_LOWER:
                return None

            for attr_name, attr_val in list(el.attrib.items()):
                al = attr_name.split("}")[-1].lower() if "}" in attr_name else attr_name.lower()
                if al.startswith("on"):
                    del el.attrib[attr_name]
                elif "href" in al and not attr_val.startswith("#"):
                    del el.attrib[attr_name]
                elif al == "style":
                    val_lower = attr_val.lower()
                    if "url(" in val_lower or "javascript:" in val_lower or "expression(" in val_lower:
                        del el.attrib[attr_name]

        return ET.tostring(root, encoding="utf-8").decode("utf-8")
    except Exception as exc:
        logger.debug(f"SVG sanitization rejected malformed markup: {exc}")
        return None
