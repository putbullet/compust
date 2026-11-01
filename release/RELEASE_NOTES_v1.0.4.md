# Compust v1.0.4 — Official Release Notes

**Release Date:** October 2026  
**Tag:** `v1.0.4`  
**Commit:** `e8e9471`

---

## 📦 Downloads & Checksums

| Asset | Format | Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| **`Compust-Setup-v1.0.4.exe`** | Windows Inno Setup Installer | 223.59 MB (`234,454,172` bytes) | `6d5ee18d2fab5d103d0116acc0f7c76cbcd61fc37fe4f9e181c7a093b7c8972d` |
| **`Compust-Windows-Portable-v1.0.4.zip`** | Portable Zero-Install Archive | 84.43 MB (`88,529,523` bytes) | `97b8efc2ea09037215d5db0739925671953ee65a2a41d4d66e8b744c365001ff` |
| **`compust-capture-firefox-v1.0.3.zip`** | Firefox Extension Archive (AMO) | 89.38 KB (`91,523` bytes) | `e4ea7f87f21cb06dddad5446f2733a7e65d28c39d0fcdafcf5b3bd865efb8f66` |
| **`compust-capture-firefox-v1.0.3-source.zip`** | Firefox Extension Source Archive | 290.31 KB (`297,279` bytes) | `ac15e1a1432802ce434d9691336d3c5ea78826a669812e3f29288b6d48068dfe` |
| **`compust-capture-chrome-v1.0.3.zip`** | Chrome/Edge/Brave Extension Archive | 89.29 KB (`91,439` bytes) | `cc9b1bab0e4df95d10ea82000869ad9d54957eea9af6e8528e4ffb5ac4df9b80` |

---

## 🚀 Key Improvements & Highlights

### 1. Functional "Explain with AI" with Safe SVG Diagrams
- **Dual Engine Routing:** Explanations and concept breakdowns route through the unified `AIGateway` (`ai_gateway.py`), supporting Google Gemini 3.8 Flash, local Ollama, and deterministic smart offline fallback.
- **Server-Side Sanitized Vector Diagrams:** Clean `<svg viewBox="0 0 640 200">` architecture and data flow diagrams parsed via `xml.etree.ElementTree` and sanitized via `bleach` (strictly disallowing `<script>`, `on*` event handlers, `<foreignObject>`, and external URLs).
- **Multi-Stage Generation Progress:** Interactive `StageProgressList` animates through prompt analysis, architecture mapping, and SVG synthesis during generation.
- **Model-Keyed Database Caching:** Explanations cached per question and model in SQLite/MySQL for instant (<370ms) reloads.
- **Interactive Cache Bypass:** "Regenerate" action forces fresh model inference without touching stale cached rows.

### 2. Opportunities Stat-Card Pill Redesign
- **Modern Horizontal Pill Architecture:** Restructured the 4 opportunity metrics cards from vertical blocks into sleek horizontal pills matching reference dark/light mode aesthetics.
- **Purpose-Specific Icons:** High-contrast SVG icons for Total Active Opportunities, Verified Portals, Countries Represented, and Auto-Sync Status.
- **Responsive Flexbox Layout:** Fluid wrapping and alignment across 1440px desktop, 1200px laptop, 1024px, and 800px tablet displays.

### 3. Sync Now Button Spacing & Text Collision Resolution
- **Flexbox Spacing:** Added `gap: 0.75rem` and `white-space: nowrap` to prevent visual collision between the "Sync Now" button and the last synchronized timestamp text.
- **Responsive Viewport Stability:** Verified across 4 viewports (1440px, 1200px, 1024px, 800px) and varying timestamp lengths.

### 4. Extension Package Updates (v1.0.3)
- Bumped Chrome and Firefox manifest versions to `1.0.3`.
- Verified POSIX-compliant forward slashes across all archive entries.
- Packaged AMO source archive (`compust-capture-firefox-v1.0.3-source.zip`) with build instructions.

---

## 🧪 Verification & Automated Testing Matrix

- **Unit & Security Tests:** 36/36 passed (`test_interview_prep*.py` & `test_ai_explain_svg_security.py`).
- **Regression Test Suite:** 608 passed, 3 skipped, 0 failed across full backend suite.
- **Live Playwright E2E:** 2-pass verification of Explain with AI generation, cache hits, regeneration, and SVG rendering.
- **In-Place Upgrade Test:** Verified silent upgrade from `Compust-Setup-v1.0.4.exe` with 100% data preservation across 484 jobs, 58 applications, 41 companies, 18 contacts, and user AI settings.
