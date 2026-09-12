from bs4 import BeautifulSoup
import re

_JS_REQUIRED_PATTERNS = (
    "enable javascript to run this app",
    "you need to enable javascript",
    "javascript is required",
    "javascript must be enabled",
    "please enable javascript",
    "requires javascript to work",
)

_SPA_ROOT_IDS = ("root", "app", "__next", "main-app", "career-app", "careers-app", "application")

_SCRIPT_CHUNK_REGEX = re.compile(
    r"(bundle|main|app|chunk|vendor|runtime|vite|webpack|entry)[._a-zA-Z0-9-]*\.js",
    re.IGNORECASE,
)


def is_spa_shell(content: str | BeautifulSoup) -> bool:
    """
    Heuristically determine if an HTML document is an unhydrated SPA shell
    that requires client-side JavaScript rendering to display career content.
    """
    if not content:
        return False

    if isinstance(content, str):
        html_lower = content.lower()
        # Fast string scan for noscript / JS requirements
        if any(pat in html_lower for pat in _JS_REQUIRED_PATTERNS):
            return True
        soup = BeautifulSoup(content, "html.parser")
    else:
        soup = content
        html_lower = soup.get_text(separator=" ", strip=True).lower()
        if any(pat in html_lower for pat in _JS_REQUIRED_PATTERNS):
            return True

    # 1. Check for known SPA root containers that are empty or contain only spinners/noscript
    for root_id in _SPA_ROOT_IDS:
        elem = soup.find(id=root_id)
        if elem:
            # Strip noscript, scripts, styles inside the root element
            direct_text = elem.get_text(strip=True)
            child_tags = [c.name for c in elem.find_all(recursive=False) if c.name not in ("noscript", "script", "style")]
            if not direct_text or len(child_tags) == 0:
                return True
            # If text is extremely short (e.g., "Loading...", "Chargement...")
            if len(direct_text) < 30 and any(kw in direct_text.lower() for kw in ("loading", "chargement", "wird geladen", "please wait")):
                return True

    # 2. Check for data-reactroot or ng-version on near-empty container
    react_root = soup.find(attrs={"data-reactroot": True})
    if react_root and len(react_root.get_text(strip=True)) < 50:
        return True

    # 3. Check for low-content HTML dominated by JS application bundles
    body = soup.find("body")
    if body:
        scripts = soup.find_all("script", src=True)
        bundle_scripts = [
            s["src"] for s in scripts if _SCRIPT_CHUNK_REGEX.search(s.get("src", ""))
        ]
        if len(bundle_scripts) >= 1:
            # Check visible non-script text length
            text_nodes = [
                text for text in body.stripped_strings
                if text.parent and text.parent.name not in ("script", "style", "noscript")
            ]
            visible_text = " ".join(text_nodes)
            if len(visible_text) < 350:
                return True

    return False

