import posixpath
import re
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

TRACKING_PARAM_PREFIXES = ("utm_", "mc_")
TRACKING_PARAM_NAMES = {
    "fbclid",
    "gclid",
    "gclsrc",
    "dclid",
    "msclkid",
    "zanpid",
    "wickedid",
    "trk",
    "_hsenc",
    "_hsmi",
    "ref_",
    "source",
}

KNOWN_REFERRAL_SOURCES = {
    "linkedin",
    "twitter",
    "facebook",
    "google",
    "instagram",
    "github",
    "direct",
    "share",
    "banner",
    "social",
    "email",
    "newsletter",
    "feed",
    "feedly",
    "producthunt",
    "reddit",
    "t.co",
    "link",
}


def is_tracking_param(name: str, value: str = "") -> bool:
    lower_name = name.lower()
    if any(lower_name.startswith(prefix) for prefix in TRACKING_PARAM_PREFIXES):
        return True
    if lower_name == "ref":
        val = value.strip().lower()
        # Job requisition identifiers (e.g. 'R-5673', 'REQ-1234', or numeric IDs) are NOT tracking params
        if re.match(r"^[a-z]{0,4}-?\d+", val) or (val.isdigit() and len(val) >= 3):
            return False
        return True
    return lower_name in TRACKING_PARAM_NAMES


def normalize_path(path: str) -> str:
    if not path:
        return "/"

    # Normalize dot segments
    trailing_slash = path.endswith("/") and path != "/"
    
    # Unquote and re-quote unreserved chars
    # First unquote unreserved characters
    unreserved = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~/")
    
    parts = []
    for segment in path.split("/"):
        if segment == "." or segment == "":
            continue
        elif segment == "..":
            if parts:
                parts.pop()
        else:
            # Decode percent-encoded unreserved chars
            decoded = unquote(segment)
            # Re-encode only reserved/unsafe characters
            reencoded = quote(decoded, safe="-_.~!$&'()*+,;=:@")
            parts.append(reencoded)

    normalized = "/" + "/".join(parts)
    if trailing_slash and not normalized.endswith("/"):
        normalized += "/"
    return normalized


def normalize_url(url: str) -> str:
    """
    Canonicalize a URL:
    - Lowercase scheme and domain (netloc)
    - Remove default ports (80 for http, 443 for https)
    - Remove fragment
    - Remove tracking / marketing parameters
    - Sort remaining application query parameters deterministically
    - Canonicalize path encoding and dot-segments
    """
    if not url or not url.strip():
        return ""

    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.lower()

    netloc = parsed.netloc.lower()
    # Strip standard default ports
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    # Normalize path
    path = normalize_path(parsed.path)

    # Normalize and filter query parameters
    query_params = parse_qsl(parsed.query, keep_blank_values=True)
    filtered_params = [
        (k, v) for k, v in query_params if not is_tracking_param(k, v)
    ]
    # Sort deterministically
    filtered_params.sort(key=lambda item: (item[0], item[1]))
    query = urlencode(filtered_params, doseq=True) if filtered_params else ""

    # Fragment is stripped
    fragment = ""

    return urlunsplit((scheme, netloc, path, query, fragment))
