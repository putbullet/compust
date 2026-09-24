# Compust Capture — Browser Extension

A Manifest V3 browser extension for **Chrome, Edge, Brave, and Firefox** that integrates with your local **Compust** career intelligence platform (`http://localhost:8000`).

While browsing job postings on **LinkedIn**, **Indeed**, or **Glassdoor**, Compust Capture injects a subtle floating button into an isolated Shadow DOM container. With one click, it extracts clean job details, creates/deduplicates the posting in your local Compust database, generates an instant **Requirements Match Analysis** against your active resume, and enables one-click tracking to your Kanban board at `Applied` or `Interested` status.

<p align="center">
  <a href="https://drive.google.com/file/d/1KRz11E0OOpLJNTWerkFmbSLtkoqL0dua/view?usp=sharing">
    <img src="../../docs/media/extension-demo-thumbnail.png" alt="Click to see how the extension works!" width="100%" />
  </a>
  <br />
  <em>↗ Opens an external demo video hosted on Google Drive.</em>
</p>

---

## Key Architecture & Security Decisions

1. **Manifest V3 Cross-Browser Support**:
   - Compiles two separate targets from a single source tree:
     - `dist/chrome`: Uses Service Worker background (`src/background/index.js`) and Chrome MV3 schema.
     - `dist/firefox`: Uses Background Script (`src/background/index.js`) and Gecko settings (`compust-capture@compust.ma`, min version `109.0`).
2. **Narrow Host Permissions (No `<all_urls>`)**:
   - `host_permissions` are strictly restricted to job-posting URL patterns:
     - LinkedIn: `*://*.linkedin.com/jobs/view/*`, `*://*.linkedin.com/jobs/collections/*`, `*://*.linkedin.com/jobs/search/*`
     - Indeed: `*://*.indeed.com/viewjob*`, `*://*.indeed.com/jobs?*`, `*://*.indeed.com/job/*`
     - Glassdoor: `*://*.glassdoor.com/Job/*`, `*://*.glassdoor.com/job-listing/*`
     - Local backend: `http://localhost/*`, `http://127.0.0.1/*`
3. **Strict JWT Context Isolation**:
   - The user's authentication token is stored exclusively in `browser.storage.local` and accessed only by the background service worker.
   - Content scripts execute in the page DOM context and **never** import auth modules, never touch `storage.local` for credentials, and never have the JWT in scope. All API calls are brokered via `chrome.runtime.sendMessage`.
4. **Shadow DOM Style Isolation**:
   - Floating buttons and analysis overlays are mounted under a closed/open Shadow Root (`#compust-capture-root`), ensuring zero style leakage between host job boards and the extension UI.
5. **Deduplication Single Source of Truth**:
   - Uses the same 3-tier backend deduplication hash and Bleach HTML sanitization as Compust's scrapers (`persist_candidate` in `app.repositories.jobs`).
6. **In-Memory Rate Limiting**:
   - The backend rate limiter (`UserRateLimiter`, 30 requests/min per user) operates in-memory on the FastAPI process. Note that this rate limiter resets on backend restart and is not meant to persist across processes.

---

## Building the Extension

### Prerequisites
- Node.js 18+ (tested on Node v22+)
- npm 9+

### Commands

```bash
cd important/extension

# Install dependencies
npm install

# Build both Chrome and Firefox distributions
npm run build

# Or build individual targets
npm run build:chrome    # Outputs to dist/chrome
npm run build:firefox   # Outputs to dist/firefox
```

The build script compiles popup and options pages as HTML bundles, and bundles the background script and site content scripts as self-contained IIFEs (`dist/<target>/src/content/*.js`) to ensure seamless execution in content script environments without external ES module imports.

---

## Installation & Loading

### Chrome / Edge / Brave (Chromium)

1. Open `chrome://extensions/` (or `edge://extensions/` / `brave://extensions/`).
2. Enable **Developer mode** (toggle in the top-right corner).
3. Click **Load unpacked**.
4. Select the directory: `<path-to-repo>/important/extension/dist/chrome`.
5. Find the extension ID assigned by the browser (e.g. `chrome-extension://abcdefghijklmnop...`).
6. Add the origin to your Compust backend `.env`:
   ```bash
   COMPUST_EXTENSION_ORIGINS=["chrome-extension://abcdefghijklmnop..."]
   ```
7. Pin the **Compust Capture** icon to your toolbar.

### Firefox

1. Open Firefox and navigate to `about:debugging#/runtime/this-firefox`.
2. Click **Load Temporary Add-on...**.
3. Select `dist/firefox/manifest.json`.
4. Add the extension's UUID/origin to your backend `.env` if required (e.g. `moz-extension://<uuid>`).

> **Note regarding Safari**: Safari requires Xcode wrapping and App Store notarization and is intentionally out of scope.

---

## Usage Guide

1. **Start the Compust Backend**:
   ```bash
   cd important
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
   ```
2. **Log In via Toolbar Popup**:
   - Click the Compust Capture icon in your browser toolbar.
   - Enter your Compust account credentials (`candidate@compust.ma`).
   - The popup displays connection status, active resume name, and direct links to your Kanban board and Resume Studio.
3. **Analyse & Track a Job**:
   - Navigate to any job posting on LinkedIn, Indeed, Glassdoor, or Welcome to the Jungle.
   - Click the floating **Analyse with Compust** button in the bottom-right corner.
   - The extension runs your active resume against the job description and shows live progress stages.
   - The job is automatically saved to the central **Jobs Directory** for future reference, but **NOT** added to your personal Applications Kanban board yet.
   - The floating card expands to show:
     - **Requirements Match Score** (e.g. 85%)
     - **Demonstrated Skills** (green badges)
     - **Missing / Weak Skills** (amber badges)
     - **Resume Tailoring Suggestions**
     - **Deep Analysis** for Visa & Work Authorization
   - **Explicit Tracking Choice**: Choose whether to track the job by clicking **★ Interested** or **✓ Applied** to add it to your Kanban board, or click **Keep Untracked** / dismiss if you only wanted the analysis.

---

## Important Notice: Live Verification & Rate Limiting

When performing live verification on LinkedIn:
- Automated requests should be spaced out with deliberate delays/backoff.
- Frequent, rapid requests from the same IP/account may trigger LinkedIn's bot detection, security checkpoints, or HTTP 429/999 status codes.
- Tests should preferably use mock responses or cached HTML fixtures (`tests/fixtures/`) during routine CI/CD, reserving live navigation for occasional smoke tests with a logged-in user profile.

---

## Testing

### Unit Tests (Vitest)
Validates site-specific DOM extractors, JSON-LD parsing, fallback degradation, and JWT isolation:
```bash
npm run test:unit
```

### End-to-End Tests (Playwright Chromium)
Runs automated end-to-end capture on mocked LinkedIn pages, verifies Shadow DOM mounting, match score rendering, Kanban tracking, and offline error handling:
```bash
npm run test:e2e
```

### Backend Integration Tests (Pytest)
Validates backend quick-add endpoints, Bleach XSS stripping, rate limiting, and CORS validation:
```bash
cd important
.\.venv\Scripts\python.exe -m pytest tests/test_extension_quick_add.py -v
```

---

## Packaging for Distribution

Zipped archives are automatically generated during `npm run build`:
- `dist/compust-capture-chrome.zip` (for Chrome, Edge, Brave)
- `dist/compust-capture-firefox.zip` (for Firefox)

These are served directly by the backend download endpoint (`/api/v1/extension/download/{browser}`) and can be uploaded directly to the Chrome Web Store or Mozilla Add-ons (AMO).
