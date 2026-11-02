import json
import pytest
from playwright.sync_api import sync_playwright
from src.app.diagnostics_view import render_missing_frontend_page, render_friendly_error_page

BASE_URL = "http://127.0.0.1:8000"

CONTRAST_EVAL_JS = """
(theme) => {
  function parseColor(str) {
    if (!str) return null;
    str = str.trim();
    if (str === 'transparent' || str === 'rgba(0, 0, 0, 0)') {
      return [0, 0, 0, 0];
    }
    const rgbaMatch = str.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([\\d.]+))?\\)/);
    if (rgbaMatch) {
      return [
        parseInt(rgbaMatch[1], 10),
        parseInt(rgbaMatch[2], 10),
        parseInt(rgbaMatch[3], 10),
        rgbaMatch[4] !== undefined ? parseFloat(rgbaMatch[4]) : 1.0
      ];
    }
    return null;
  }

  function composite(fg, bg) {
    const a = fg[3] + bg[3] * (1 - fg[3]);
    if (a === 0) return [0, 0, 0, 0];
    const r = Math.round((fg[0] * fg[3] + bg[0] * bg[3] * (1 - fg[3])) / a);
    const g = Math.round((fg[1] * fg[3] + bg[1] * bg[3] * (1 - fg[3])) / a);
    const b = Math.round((fg[2] * fg[3] + bg[2] * bg[3] * (1 - fg[3])) / a);
    return [r, g, b, a];
  }

  function getLuminance(r, g, b) {
    const [rs, gs, bs] = [r, g, b].map(c => {
      const v = c / 255;
      return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
  }

  function getContrastRatio(c1, c2) {
    const l1 = getLuminance(c1[0], c1[1], c1[2]);
    const l2 = getLuminance(c2[0], c2[1], c2[2]);
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
  }

  function getEffectiveBg(el, rootBg) {
    let current = el;
    const bgLayers = [];
    while (current && current !== document.documentElement) {
      const style = window.getComputedStyle(current);
      const parsed = parseColor(style.backgroundColor);
      if (parsed && parsed[3] > 0) {
        bgLayers.unshift(parsed);
      }
      current = current.parentElement;
    }
    let effective = rootBg;
    for (const layer of bgLayers) {
      effective = composite(layer, effective);
    }
    return effective;
  }

  const defaultCanvasBg = [9, 13, 22, 1.0];
  const violations = [];

  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  let node = walker.nextNode();

  while (node) {
    const el = node;
    node = walker.nextNode();

    // Check direct text content
    let hasDirectText = false;
    for (let i = 0; i < el.childNodes.length; i++) {
      const child = el.childNodes[i];
      if (child.nodeType === Node.TEXT_NODE && child.textContent.trim().length > 0) {
        hasDirectText = true;
        break;
      }
    }

    if (!hasDirectText) continue;

    const style = window.getComputedStyle(el);
    if (
      style.display === 'none' ||
      style.visibility === 'hidden' ||
      parseFloat(style.opacity) < 0.1 ||
      el.offsetWidth === 0 ||
      el.offsetHeight === 0
    ) {
      continue;
    }

    // Exclude disabled elements and decorative aria-hidden elements
    if (el.matches(':disabled, [disabled], [aria-disabled="true"], [aria-hidden="true"]')) continue;

    const fg = parseColor(style.color);
    if (!fg || fg[3] === 0) continue;

    const bg = getEffectiveBg(el, defaultCanvasBg);
    const effectiveFg = composite(fg, bg);

    const ratio = getContrastRatio(effectiveFg, bg);

    const fontSizePx = parseFloat(style.fontSize);
    const fontWeight = style.fontWeight;
    const isBold = fontWeight === 'bold' || parseInt(fontWeight, 10) >= 700;
    const isLarge = fontSizePx >= 24 || (fontSizePx >= 18.5 && isBold);
    const requiredRatio = isLarge ? 3.0 : 4.5;

    // Allow tiny tolerance (0.05) for subpixel antialiasing/rounding
    if (ratio < (requiredRatio - 0.05)) {
      violations.push({
        tag: el.tagName.toLowerCase(),
        className: el.className,
        text: el.textContent.trim().slice(0, 50),
        fg: `rgb(${effectiveFg[0]}, ${effectiveFg[1]}, ${effectiveFg[2]})`,
        bg: `rgb(${bg[0]}, ${bg[1]}, ${bg[2]})`,
        ratio: Math.round(ratio * 100) / 100,
        requiredRatio,
        fontSize: style.fontSize,
        fontWeight: style.fontWeight
      });
    }
  }

  return violations;
}
"""


def evaluate_contrast_on_page(page, theme="dark"):
    page.evaluate(
        """() => {
        document.documentElement.setAttribute('data-theme', 'dark');
        document.body.className = 'dark';
        localStorage.setItem('compust_theme', 'dark');
    }"""
    )
    page.wait_for_timeout(300)
    violations = page.evaluate(CONTRAST_EVAL_JS, "dark")
    return violations


def test_wcag_contrast_across_views():
    """Walks the rendered DOM of every major view in the single dark theme, asserting WCAG AA contrast."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(color_scheme="dark", viewport={"width": 1400, "height": 900})

        views = [
            ("Opportunities", f"{BASE_URL}/?tab=directory"),
            ("Internships", f"{BASE_URL}/?tab=internships"),
            ("Applications", f"{BASE_URL}/?tab=tracker"),
            ("Resume Studio", f"{BASE_URL}/?tab=profile"),
            ("Interview Prep", f"{BASE_URL}/?tab=interview_prep"),
            ("Database Doctor", f"{BASE_URL}/?tab=doctor"),
        ]

        all_violations = []

        for name, url in views:
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(600)

            v_list = evaluate_contrast_on_page(page, "dark")
            for v in v_list:
                v["view"] = name
                all_violations.append(v)

        browser.close()

        if all_violations:
            summary = "\n".join(
                [
                    f"[{v['view']}] <{v['tag']} class='{v['className']}'> \"{v['text']}\" "
                    f"Ratio: {v['ratio']}:1 (Req: {v['requiredRatio']}:1) FG: {v['fg']} BG: {v['bg']}"
                    for v in all_violations[:20]
                ]
            )
            pytest.fail(f"Found {len(all_violations)} WCAG AA contrast violations:\n{summary}")


def test_wcag_contrast_database_doctor_states():
    """Verifies WCAG AA contrast across all Database Doctor states (healthy, schema outdated, unreachable, repair failed)."""
    healthy_status = {
        "is_healthy": True,
        "active_engine": "sqlite",
        "active_location": "compust.db",
        "is_sqlite": True,
        "is_fallback_active": False,
        "schema_synced": True,
        "missing_tables": [],
        "missing_columns": {},
        "table_counts": {"users": 2, "jobs": 84, "companies": 42},
        "backup_count": 1,
        "latest_backups": [{"filename": "backup.db", "timestamp": "2026-11-02", "size_kb": 100}],
        "size_mb": 0.2,
        "db_version": "1.0.6",
    }

    outdated_status = {
        **healthy_status,
        "is_healthy": False,
        "schema_synced": False,
        "missing_tables": ["audit_logs"],
        "missing_columns": {"users": ["email"]},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        all_violations = []

        # 1. Healthy state
        page = browser.new_page(color_scheme="dark", viewport={"width": 1400, "height": 900})
        page.route("**/api/v1/doctor/status", lambda route: route.fulfill(
            status=200, content_type="application/json", body=json.dumps(healthy_status)
        ))
        page.goto(f"{BASE_URL}/?tab=doctor", wait_until="networkidle")
        page.wait_for_timeout(400)
        for v in evaluate_contrast_on_page(page, "dark"):
            v["state"] = "Doctor (Healthy)"
            all_violations.append(v)
        page.close()

        # 2. Schema outdated state (Broken Database simulation)
        page = browser.new_page(color_scheme="dark", viewport={"width": 1400, "height": 900})
        page.route("**/api/v1/doctor/status", lambda route: route.fulfill(
            status=200, content_type="application/json", body=json.dumps(outdated_status)
        ))
        page.goto(f"{BASE_URL}/?tab=doctor", wait_until="networkidle")
        page.wait_for_timeout(400)
        for v in evaluate_contrast_on_page(page, "dark"):
            v["state"] = "Doctor (Schema Outdated)"
            all_violations.append(v)
        page.close()

        # 3. Unreachable database error state
        page = browser.new_page(color_scheme="dark", viewport={"width": 1400, "height": 900})
        page.route("**/api/v1/doctor/status", lambda route: route.abort("failed"))
        page.goto(f"{BASE_URL}/?tab=doctor", wait_until="networkidle")
        page.wait_for_timeout(400)
        for v in evaluate_contrast_on_page(page, "dark"):
            v["state"] = "Doctor (Unreachable)"
            all_violations.append(v)
        page.close()

        # 4. Repair failed state
        page = browser.new_page(color_scheme="dark", viewport={"width": 1400, "height": 900})
        page.route("**/api/v1/doctor/status", lambda route: route.fulfill(
            status=200, content_type="application/json", body=json.dumps(outdated_status)
        ))
        page.route("**/api/v1/doctor/repair", lambda route: route.fulfill(
            status=500, content_type="application/json", body=json.dumps({"detail": "Schema lock timeout"})
        ))
        page.goto(f"{BASE_URL}/?tab=doctor", wait_until="networkidle")
        page.wait_for_timeout(300)
        page.locator(".repair-primary-btn").click()
        page.wait_for_timeout(500)
        for v in evaluate_contrast_on_page(page, "dark"):
            v["state"] = "Doctor (Repair Failed)"
            all_violations.append(v)
        page.close()

        browser.close()

        if all_violations:
            summary = "\n".join(
                [
                    f"[{v['state']}] <{v['tag']} class='{v['className']}'> \"{v['text']}\" "
                    f"Ratio: {v['ratio']}:1 (Req: {v['requiredRatio']}:1) FG: {v['fg']} BG: {v['bg']}"
                    for v in all_violations[:20]
                ]
            )
            pytest.fail(f"Found {len(all_violations)} WCAG AA contrast violations in Doctor states:\n{summary}")


def test_wcag_contrast_standalone_diagnostic_pages():
    """Verifies WCAG AA contrast on standalone backend diagnostic and server error pages."""
    p1_html = render_missing_frontend_page(port=8000, mode="installed", logs_path="logs/backend.log", db_status="ok", version="1.0.6")
    p2_html = render_friendly_error_page(request_id="req_test_12345", path="/api/v1/test", logs_path="logs/backend.log", error_summary="An unexpected server error occurred.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        all_violations = []

        # Missing frontend page
        page = browser.new_page(color_scheme="dark", viewport={"width": 1400, "height": 900})
        page.set_content(p1_html)
        page.wait_for_timeout(300)
        for v in page.evaluate(CONTRAST_EVAL_JS, "dark"):
            v["page"] = "Missing Frontend Diagnostic Page"
            all_violations.append(v)
        page.close()

        # Friendly error page
        page = browser.new_page(color_scheme="dark", viewport={"width": 1400, "height": 900})
        page.set_content(p2_html)
        page.wait_for_timeout(300)
        for v in page.evaluate(CONTRAST_EVAL_JS, "dark"):
            v["page"] = "Friendly Error Page"
            all_violations.append(v)
        page.close()

        browser.close()

        if all_violations:
            summary = "\n".join(
                [
                    f"[{v['page']}] <{v['tag']} class='{v['className']}'> \"{v['text']}\" "
                    f"Ratio: {v['ratio']}:1 (Req: {v['requiredRatio']}:1) FG: {v['fg']} BG: {v['bg']}"
                    for v in all_violations[:20]
                ]
            )
            pytest.fail(f"Found {len(all_violations)} WCAG AA contrast violations in standalone pages:\n{summary}")
