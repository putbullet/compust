from pathlib import Path
from src.app.scraper.sanitizer import sanitize_html, sanitize_plain_text


def test_sanitize_html_strips_scripts_and_event_handlers() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "xss_job_description.html"
    raw_html = fixture_path.read_text(encoding="utf-8")

    cleaned = sanitize_html(raw_html)
    assert cleaned is not None

    # Dangerous elements and scripts must be stripped
    assert "<script" not in cleaned.lower()
    assert "alert(" not in cleaned
    assert "malicious-attacker" not in cleaned
    assert "<iframe" not in cleaned.lower()
    assert "onerror" not in cleaned.lower()
    assert "onclick" not in cleaned.lower()
    assert "javascript:" not in cleaned.lower()

    # Safe formatting must be preserved
    assert "Join our innovative engineering team!" in cleaned
    assert "Python &amp; FastApi experience" in cleaned or "Python & FastApi experience" in cleaned
    assert "https://example.test/apply" in cleaned
    assert "<ul>" in cleaned
    assert "<li>" in cleaned


def test_sanitize_plain_text_strips_all_tags() -> None:
    title_with_xss = "Lead Architect <script>alert(1)</script> & <b onclick='hack()'>Backend</b>"
    cleaned = sanitize_plain_text(title_with_xss)

    assert cleaned == "Lead Architect & Backend"
    assert "<script>" not in cleaned
    assert "alert" not in cleaned
    assert "onclick" not in cleaned
    assert "<b>" not in cleaned


def test_handles_none_and_empty() -> None:
    assert sanitize_html(None) is None
    assert sanitize_plain_text(None) is None
    assert sanitize_html("") == ""
    assert sanitize_plain_text("   ") == ""
