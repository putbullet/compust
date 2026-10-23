# Changelog

All notable changes to the **Compust** platform are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed
- **MySQL Foreign Key Schema Parity**: Fixed unsigned integer mismatch across `User.id`, `Company.id`, `Country.id`, `Job.id`, and `Resume.id` foreign keys in SQLAlchemy models, resolving MySQL `errno 150` on table creation and eliminating 500 Internal Server Errors on user sign-up/sign-in.
- **Database Startup Migrations**: Automated database migrations on whichever engine is active at startup (MySQL or SQLite), failing fast with actionable diagnostics rather than returning a bare 500 later.
- **HTTP Status Codes on Auth Endpoints**: Updated authentication responses to return standard semantic HTTP status codes with translated error messages: 409 Conflict for duplicate emails, 401 Unauthorized for invalid credentials, and 503 Service Unavailable when the database is unreachable.
- **Opportunities Stat Pills Hover Elimination**: Removed unrequested hover transforms, shadows, and cursor effects on Opportunities stat pills while maintaining exact visual fidelity.
- **Internships Stat Pills Structure**: Consolidated stat elements into a shared `StatPill` component (`hero` and `metric` variants), eliminating squeezed text, border overflow, and poor padding with responsive `flex-wrap` and gap spacing.

### Changed
- **Navbar AI Panel Performance**: Re-architected AI panel opening to load instantaneously (<150ms) from local cache; status probes run in the background with non-blocking progressive chips, 1.0s timeout for Ollama, and zero outbound network calls to cloud providers (Gemini/OpenAI) for status rendering.
- **Documentation Diagram Viewer**: Replaced static, shrunken Mermaid diagrams with a responsive, zoomable, and pannable `DiagramViewer` featuring inline `Ctrl+wheel` zoom, reset, fit-to-width, keyboard shortcuts, and portal-based modal expansion.

---

## [1.0.4] - 2026-10-23

### Added
- **Functional "Explain with AI" with Safe SVG Diagrams**:
  - Deep concept breakdown and real-world narrative case scenarios powered by the unified AI Gateway (`ai_gateway.py`), supporting Google Gemini 3.8 Flash and local Ollama, with smart deterministic fallback.
  - Safe, server-side validated and sanitized SVG architecture and concept flow diagrams (ElementTree and Bleach sanitized, enforcing `0 0 640 200` viewBox, stripping all `<script>`, `on*` event handlers, `<foreignObject>`, and external URI references).
  - Multi-stage visual generation progress list (`StageProgressList`) providing real-time feedback during AI reasoning and diagram generation.
  - SQLite/MySQL database explanation caching keyed by question, domain, and model, ensuring instant (<370ms) reloads.
  - Interactive "Regenerate" button with cache-bypassing parameter (`bypass_cache=true`).
- **Opportunities Stat-Card Pill Redesign**:
  - Redesigned 4 opportunity metrics cards into sleek horizontal pill containers matching modern dark/light mode aesthetic.
  - Purpose-specific SVG icons (Total Active Opportunities, Verified Portals, Countries Represented, Auto-Sync Status) with prominent high-contrast metrics and muted uppercase metadata labels.
  - Responsive flexbox wrapping ensuring optimal layout across 1440px desktop, 1200px laptop, 1024px, and 800px tablet displays.

### Changed
- **Extension Package Updates (v1.0.3)**:
  - Bumped Chrome and Firefox extension manifests to `1.0.3`.
  - Packaged official Mozilla Add-ons (AMO) source archive with build instructions.

### Fixed
- **Sync Now Button Spacing & Text Collision**:
  - Resolved visual overlap between the "Sync Now" action button and last sync timestamp text.
  - Enforced structured flex-row layout with `gap: 0.75rem`, `white-space: nowrap`, and responsive wrapping under narrow viewports.

---

## [1.0.3] - 2026-10-20

### Added
- **Compust Capture Extension v1.0.2**:
  - Enhanced job extraction heuristics for modern LinkedIn, Indeed, Glassdoor, and Welcome to the Jungle DOM layouts.
  - Added background token sync and instant match score badges.

### Changed
- **Gemini AI Quota & Rate-Limit Handling**:
  - Added exponential backoff and retry discipline for HTTP 429 quota exhaustion.
  - Optimized prompt token lengths to reduce API usage.

### Fixed
- **Resume Customization Contrast**: Resolved low-contrast text on dark backgrounds in the Suggest Resume Customization view.
- **Modal Stacking Context**: Fixed z-index layering issue where schedule settings modals appeared behind main content.

---

## [1.0.2] - 2026-10-18

### Added
- **Windows DPAPI Key Encryption**:
  - Added secure encryption at rest for Google Gemini API keys using Windows Data Protection API (`CryptProtectData`), eliminating plaintext credential storage.
- **Stepped Gemini Setup Wizard**:
  - Guided 4-stage configuration wizard (`gemini-3.8-flash` default) with live latency connectivity testing and privacy consent verification.
- **Guided Data Migration & Portable Backup**:
  - Auto-discovery of existing MySQL instances (`127.0.0.1:3306`) and development SQLite databases.
  - Conflict-free import and deduplication into `%LOCALAPPDATA%\Compust\data\compust.db`.
  - One-click portable `.zip` backup and restore preserving 100% data fidelity.
- **Hardened Offline Internships Dataset**:
  - Bundled `github_internships_seed.json` with 4,283 pre-indexed positions (4,021 active) for resilient offline operation.

### Changed
- **Bootstrap Technical Documentation Redesign**:
  - Clean 3-column layout replacing neon styling with professional Bootstrap-style technical documentation.
  - Added collapsible sidebar, sticky table of contents, and quick `/` keyboard search.
  - Monochrome dark-mode compatible Mermaid architecture and data model diagrams.

### Fixed
- **Relative API Paths**: Converted frontend client API calls to relative paths (`/api/v1`), eliminating port mismatches between development servers and installed ports.
- **Loopback CORS Middleware**: Hardened CORS policy for browser extensions and external origins.

---

## [1.0.1] - 2026-10-14

### Added
- **Compust Capture Browser Extension**:
  - Manifest V3 browser extension for LinkedIn, Indeed, Glassdoor, and Welcome to the Jungle.
  - Floating overlay with automatic job analysis, match scoring, and quick actions (Add, Applied, Save, Skip).
- **RenderCV Typst Resume Studio**:
  - Integrated Typst-based resume compiler with deterministic A4 live preview.
  - 6-pillar ATS audit engine evaluating structure, keywords, typography, and length.
- **Playwright Headless Browser Fallback**:
  - Headless Chromium rendering fallback for dynamic Single Page Application (SPA) career portals.
- **Job Title Intelligence**:
  - Context-aware DOM clustering against a local 73,380-title dictionary for fallback job detection.

### Fixed
- **Application Funnel Progression**: Fixed application pipeline progression logic in Kanban view.
- **Sankey Ribbon Collisions**: Adjusted canvas height and node positions to prevent visual collision between funnel ribbons.

---

## [1.0.0] - 2026-10-10

### Added
- **Initial Public Standalone Release**:
  - Inno Setup Windows installer (`Compust-Setup-v1.0.0.exe`) and zero-install portable zip edition.
  - Dual-mode database engine: automated TCP probe selects MySQL on port 3306 when reachable, with seamless fallback to SQLite.
  - 7-layer universal scraper pipeline with adapter auto-detection (Workable, Greenhouse, Lever, SmartRecruiters, Ashby).
  - Career opportunities directory with multi-country preferences, search, and remote-work filters.
  - 5-stage Kanban application tracker with notes, interview logging, and conversion analytics.
  - AI interview preparation center with role-specific questions and STAR method evaluation.
  - Contacts directory for recruiter and hiring manager relationship tracking.
  - In-app interactive guide and technical documentation center.
