import os
import re
import pytest

FRONTEND_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "src"))

def get_frontend_files():
    file_list = []
    for root, dirs, files in os.walk(FRONTEND_SRC):
        for f in files:
            if f.endswith((".ts", ".tsx", ".js", ".jsx", ".html")):
                file_list.append(os.path.join(root, f))
    return file_list

def test_no_hardcoded_backend_ports_in_api_client():
    """Ensure frontend API client uses relative base path, not hardcoded localhost:8000."""
    client_ts = os.path.join(FRONTEND_SRC, "api", "client.ts")
    assert os.path.exists(client_ts), f"Missing client.ts at {client_ts}"
    with open(client_ts, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify API_BASE_URL is relative /api/v1
    assert "return '/api/v1';" in content or "'/api/v1'" in content
    # Ensure no hardcoded http://localhost:8000 in api calls
    assert "http://localhost:8000" not in content
    assert "http://127.0.0.1:8000" not in content

def test_no_forbidden_gmail_word():
    """Ensure the word 'Gmail' is never used in the UI (Google Gemini must be used)."""
    for file_path in get_frontend_files():
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for idx, line in enumerate(f, 1):
                # Allow user email soulaimanettabaas@gmail.com in test mocks if any, but no UI references
                if "soulaimanettabaas@gmail.com" in line:
                    continue
                assert "gmail" not in line.lower(), f"Forbidden word 'gmail' found in {file_path}:{idx}: {line.strip()}"

def test_no_hardcoded_api_keys():
    """Ensure no live Gemini or secret API keys are committed in frontend source."""
    gemini_key_regex = re.compile(r"AIza[0-9A-Za-z-_]{35}")
    for file_path in get_frontend_files():
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            # Exclude placeholder texts like 'AIza...'
            matches = gemini_key_regex.findall(content)
            assert len(matches) == 0, f"Potential hardcoded API key in {file_path}: {matches}"
