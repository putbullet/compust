import pytest
import time
from playwright.sync_api import sync_playwright

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

  const defaultCanvasBg = theme === 'light' ? [255, 255, 255, 1.0] : [9, 13, 22, 1.0];
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
    # Set theme attribute on root
    page.evaluate(
        f"""() => {{
        document.documentElement.setAttribute('data-theme', '{theme}');
        document.body.className = '{theme}';
        localStorage.setItem('compust_theme', '{theme}');
    }}"""
    )
    page.wait_for_timeout(300)
    violations = page.evaluate(CONTRAST_EVAL_JS, theme)
    return violations


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_wcag_contrast_across_views(theme):
    """Walks the rendered DOM of every major view in dark and light mode, asserting WCAG AA contrast."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # Views to test
        views = [
            ("Opportunities", f"{BASE_URL}/?tab=directory"),
            ("Internships", f"{BASE_URL}/?tab=internships"),
            ("Applications", f"{BASE_URL}/?tab=tracker"),
            ("Resume Studio", f"{BASE_URL}/?tab=profile"),
            ("Interview Prep", f"{BASE_URL}/?tab=interview_prep"),
        ]

        all_violations = []

        for name, url in views:
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(600)

            # If opportunities, also test with Job Detail Modal open
            if name == "Opportunities":
                job_card = page.locator(".job-card, .jobs-grid > div").first
                if job_card.count() > 0:
                    job_card.click()
                    page.wait_for_timeout(600)
                    modal_violations = evaluate_contrast_on_page(page, theme)
                    for v in modal_violations:
                        v["view"] = "Opportunities (JobDetailModal)"
                        v["theme"] = theme
                        all_violations.append(v)
                    # Close modal
                    close_btn = page.locator("button.modal-close-btn, button[aria-label='Close modal']").first
                    if close_btn.count() > 0:
                        close_btn.click()
                        page.wait_for_timeout(400)

            v_list = evaluate_contrast_on_page(page, theme)
            for v in v_list:
                v["view"] = name
                v["theme"] = theme
                all_violations.append(v)

        browser.close()

        if all_violations:
            summary = "\n".join(
                [
                    f"[{v['theme']}][{v['view']}] <{v['tag']} class='{v['className']}'> \"{v['text']}\" "
                    f"Ratio: {v['ratio']}:1 (Req: {v['requiredRatio']}:1) FG: {v['fg']} BG: {v['bg']}"
                    for v in all_violations[:20]
                ]
            )
            pytest.fail(f"Found {len(all_violations)} WCAG AA contrast violations:\n{summary}")
