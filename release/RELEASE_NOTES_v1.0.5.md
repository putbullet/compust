# Compust v1.0.5 — Official Release Notes

**Release Date:** November 2026  
**Tag:** `v1.0.5`  

---

## 📦 Downloads & Checksums

| Asset | Format | Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| **`Compust-Setup-v1.0.5.exe`** | Windows Inno Setup Installer | 225.26 MB (`236,199,207` bytes) | `7e006438d0206fa13eb7c15ef542c0ea3883743a8f966f5b277ee1292809e8cf` |
| **`Compust-Windows-Portable-v1.0.5.zip`** | Portable Zero-Install Archive | 84.82 MB (`88,938,757` bytes) | `2372846007b8794de3421bae8bc352ba541fb65d3b1473bcc61cde1a642d685c` |

---

## 🚀 Key Improvements & Highlights

### 1. Deterministic "Copy as Prompt" Resume Tailoring
- **Zero-Quota Tailoring Prompt Generator:** Generate comprehensive, structured Markdown prompts directly from any job or internship posting (in Opportunities detail modal, Internships card view, and Internships table view).
- **External LLM Integration:** Ready to paste into ChatGPT, Claude, Gemini, or DeepSeek to build resumes perfectly targeted to the specific role and company.
- **Privacy & Contact Info Control:** User-controllable toggle pill to include or omit sensitive personal contact details (email, phone, address, LinkedIn URL) with instant feedback.
- **Offline & Instant:** Deterministic templating requiring zero LLM API calls, zero quota consumption, and working 100% offline.

### 2. Multi-Language Resume Extraction & Dynamic Profile Synchronization
- **Dutch, French & International Resume Parsing:** Added robust multilingual extraction patterns supporting Dutch headers (`Werkervaring`, `Ervaring`, `Loopbaan`, `Opleiding`, etc.) alongside English and French.
- **Event-Driven Profile ↔ Resume Sync:** Switching or uploading an active resume now immediately publishes cache invalidation and triggers profile re-synchronization (`sync_profile_from_resume`), ensuring downstream consumers (like prompt builders and tailoring assistants) always receive fresh data without manual page refreshes.
- **Resume Studio Re-Activation:** Switching between uploaded resumes and Resume Studio custom resumes dynamically synchronizes the canonical candidate profile.

### 3. Comprehensive Button Styling, Alignment & Spacing Overhaul
- **Opportunities Detail Modal:**
  - Modern two-tier structured footer:
    - **Tier 1 (Utility Controls):** "Copy as prompt" with sleek inline "Include contact info" toggle pill, alongside "Suggest Customization".
    - **Tier 2 (Action Buttons):** Standardized 40px action row featuring "Close", "Mark as Applied", and "Apply on Portal" with high-contrast active states.
- **Internships Card & Table Views:**
  - Replaced cramped inline layouts with responsive action containers (`.curated-card-actions-wrapper` and `.table-col-action`).
  - Standardized compact 34px button heights for "Apply" and "Copy prompt".
  - Sleek 28px/38px toggle pills with smooth slide animations and full dark/light theme high-contrast support.

### 4. Local AI & Provider Gateway Hardening
- **Local Ollama Auto-Detection:** Resolved Ollama local connectivity discrepancies; streamlined model fetching and health checks.
- **Provider Gateway Resilience:** Model lists for Gemini and OpenAI providers hardened against transient network failures with automated fallback to cached or built-in model lists.
- **Visual Question Explanations:** Enhanced technical interview question bank with rich visual architecture diagrams and verified explanation tracks.

---

## 🧪 Verification & Automated Testing Matrix

- **Ollama AI Gateway Regression Suite:** 9/9 passed (`test_ollama_regression.py`).
- **Profile & Resume Sync Verification Suite:** 8/8 passed (`test_profile_resume_sync.py`).
- **Live Browser Playwright E2E:** Verified across desktop (1440px), laptop (1200px), tablet (800px), dark theme, and light theme.
- **Production Bundle & Packaging:** Clean Vite production build (`dist/`) and Inno Setup 6 compilation without errors or warnings.
