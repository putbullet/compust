# Remaining Compust tasks

This document records work that remains after the initial FastAPI, database,
scrape-target, source-inspection, Orange parsing, and first job-persistence
milestones.

## Immediate scraper work

- [x] Add a scraping-run model and migration.
  - Track target, start/finish timestamps, status, jobs found, added, updated,
    and parser/request errors.
  - Use the documented statuses: `pending`, `running`, `success`, `failed`,
    and `partial`.
- [x] Remove the temporary Orange company-ID parser gate.
  - Replace it with source strategy selection based on target/company
    configuration rather than `company_id == 1`.
- [x] Implement Orange pagination discovery.
  - Follow the live `rel="next"` URL pattern (`from`/`s`) only when present.
  - Stop on no next link, exhausted results, repeated job IDs, or a configured
    safety limit.
  - Add saved page-1/page-2 fixtures and duplicate-result tests.
- [x] Improve URL normalization.
  - Canonicalize case, fragments, tracking parameters, and encoded paths while
    preserving the application URL.
- [x] Add source-specific status/cooldown persistence.
  - Record 403, 429, timeout, connection, parser, and success outcomes.
  - Do not retry restricted sources aggressively.

## Job persistence and lifecycle

- [x] Add repository/API tests against a MySQL test schema or isolated
  transaction strategy.
- [x] Add safe indexes or migration constraints for job deduplication after
  measuring existing data:
  - company + external job ID;
  - company + canonical URL.
- [x] Store scrape-target provenance on jobs (`jobs.scrape_target_id` added in migration 005).
- [x] Add cautious stale-job handling (`evaluate_target_stale_jobs`).
  - Never close a job after one incomplete scrape.
  - Require reliable successful source coverage before marking jobs stale or
    closed.
- [x] Add job list/detail/search FastAPI endpoints with pagination and filters.
- [x] Add normalized employment-type, remote-type, location, and skill
  vocabulary modules.

## Remaining real-source integrations

- [x] Inspect and fixture-test Capgemini.
  - Determine pagination, country parameters, result payload, and job detail
    structure.
  - Implement only the source-specific strategy required by evidence.
- [x] Inspect and fixture-test Inwi.
  - Determine server-rendered versus API-backed listings, pagination, and
    detail URLs.
- [x] Compare all three sources and extract reusable discovery primitives.
- [x] Add source configuration records or files without hardcoded company-name
  conditionals (`config/sources.json` & `source_config.py`).

## API and operations

- [x] Add explicit scraper-control endpoints for one target and one company.
- [x] Add authentication before exposing private profile operations.
- [x] Add request validation and consistent error response schemas.
- [x] Add structured application logging without logging private profile data.
- [x] Add configuration for request timeout, user agent, delay, and page limit.

## User and matching features

- [x] Add education, skills, languages, experience, preferences, and country
  preference repositories.
- [x] Preserve distinctions between professional experience, internships,
  projects, and transferable experience.
- [x] Implement configurable, explainable rule-based matching.
- [x] Add match explanations with positive and missing factors.

## Frontend

- [x] Inspect and adapt the supplied UI snippets into a coherent React
  application.
- [x] Use the preferred Tabler / Lucide icon source after confirming the required icon
  package and license handling.
- [x] Add country selection, job directory, filters, job detail, and profile
  views.
- [x] Add responsive layouts, keyboard navigation, visible focus states, and
  reduced-motion behavior.
- [x] Add frontend API client and loading/error/empty states.
- [x] Add decoupled UI chrome internationalization (English & French).

## Internationalization and future intelligence

- [x] Preserve original job text and add separate translation fields/modules (`job_translations` table, decoupled translations service, and `JobDetailModal` language switcher).
- [x] Add country-configured languages and normalized multilingual search terms.
- [x] Keep all core scraping, parsing, persistence, and matching functional
  without AI (deterministic parsing, rule-based matching, and offline translation dictionaries).
- [x] Consider AI-assisted classification or semantic matching only after
  reliable rule-based behavior and measurements exist (pluggable `SemanticEnrichmentAdapter` with `RuleBasedSemanticFallback` and telemetry metrics).

## Quality and delivery

- [x] Add migration version tracking before adding more schema migrations (SQL runner + Alembic).
- [x] Add CI tests using saved fixtures only; never require live websites.
- [x] Add `DEVELOPMENT.md`, `CONFIGURATION.md`, `TESTING.md`, and `CHANGELOG.md`.
- [x] Add `DATABASE.md` documenting schema, tables, and migration history.
- [x] Add a frontend build and test workflow once the React application exists.
- [x] Measure requests, scrape duration, parser failures, duplicate rate,
  database writes, and discovered jobs before scaling beyond three sources (`GET /api/v1/admin/metrics`).

## Milestone v1.0.5 — Intelligence, Sync & Experience Enhancements

- [x] **Local AI & Gateway Stabilization**
  - [x] Restore local Ollama execution at `http://127.0.0.1:11434` and eliminate mutual recursion between `OllamaProvider.check_health` and `get_selected_model`.
  - [x] Provider isolation: isolate Gemini, OpenAI, and Ollama model lists and prevent cross-provider state leakage.
  - [x] Background non-blocking health probing with cache-first status returns.
- [x] **Interview Prep Visual Explanations**
  - [x] 2-tier "Explain with AI" generation: rapid concept breakdown + deep-dive with domain context packs and sanitized SVG diagrams.
  - [x] Pre-author curated high-yield explanations across AI Engineering, Security Engineering, and Data Engineering tracks.
- [x] **Resume Parsing & Profile Synchronization**
  - [x] Multi-lingual resume header detection: support Dutch (`werkervaring`, `opleiding`, `vaardigheden`, etc.) alongside English and French.
  - [x] Event-driven profile recomputation on all resume lifecycle events (upload, set default, parse, update, delete).
  - [x] Synchronize `is_default` and `is_active` atomically.
  - [x] Zero-stale prompt cache busting with `Cache-Control: no-store`.
- [x] **Deterministic "Copy as Prompt" Generator**
  - [x] Standardized Markdown prompt builder synthesizing vacancy details, de-duplicated unified profile, ATS requirements, and adjustment instructions.
  - [x] Interactive "Include contact info" toggle pill with persistent user preference storage.
  - [x] 100% offline-compatible requiring zero LLM quota or active provider.
- [x] **UI Polish & Responsive Layouts**
  - [x] Restructure Opportunities modal footer into a 2-tier layout: dedicated AI Tools bar + standard dialog action row.
  - [x] Standardize 38px uniform button heights and resolve multi-line text wrapping across all modal action buttons.
  - [x] Redesign Internship card footers: meta row (repo tag + date) and actions row (side-by-side prompt and apply buttons).
  - [x] Full dark/light contrast safety with explicit `[data-theme='light']` and system `@media (prefers-color-scheme: light)` support.


## Milestone v1.0.6 — Data Integrity, Self-Healing Schema & Database Doctor

- [x] **Self-Healing Schema Reconciler**
  - [x] Fix migration runner table creation race condition to prevent 1-column stub tables.
  - [x] Dynamic schema reconciliation (`reconcile_database_schema`) on startup/upgrade to sync missing columns, indexes, and tables.
  - [x] Automated pre-migration SQLite safety backups before executing any schema mutations or repairs.
- [x] **Pre-Login Database Doctor (`/doctor`)**
  - [x] Diagnostics view accessible before authentication showing dialect, health status, and missing columns count.
  - [x] One-click Auto-Repair and snapshot rollback (`restore_pre_migration_backup`).
  - [x] Instant SQLite switch for offline/remote database recovery.
  - [x] Dark design system restyle (`#080c14`, `#0f1623`, `#162032`) with `color-scheme: dark`.
  - [x] Automated WCAG AA contrast compliance across all 5 operational states (healthy, outdated, unreachable, repairing, failed) on desktop (1400px) and laptop (1024px) viewports with zero violations.
- [x] **Multi-Port MySQL Discovery & Resilient DB Engine**
  - [x] Auto-detect running MySQL/MariaDB instances across ports `3306-3309` and XAMPP `my.ini`.
  - [x] Windows DPAPI encryption for saved database passwords in `db_config.json`.
  - [x] Bundled `cryptography` runtime dependency for MySQL 8 authentication.
  - [x] Non-blocking schema fallback warning banner on login view.
- [x] **Import Wizard Overhaul with Dry-Run & Safe Undo**
  - [x] Dry-run simulation mode (`is_dry_run`) to preview import record counts without database writes.
  - [x] Auditable import history ledger (`import_batches` table).
  - [x] Safe Undo Import (`undo_import`) reverting imported records with pre-rollback safety backup.
  - [x] Always-accessible `DatabaseSection` embedded in Data Supervision view even when MySQL is stopped.
