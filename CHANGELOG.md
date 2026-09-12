# Changelog

All notable changes to the **Compust** platform are documented in this file.

---

## [Unreleased] - 2026-09-11

### Added
- **Phase 13: Decoupled Job Translation Architecture & Semantic Enrichment Adapter**:
  - Migration 008 (`008_create_job_translations.sql` & Alembic `b8c9d0e1f2a3`): decoupled `job_translations` table with `uq_job_translation_lang` unique constraint and cascade deletion.
  - Source text invariance: original employer postings in `jobs.title` and `jobs.description` are preserved unmodified.
  - Zero-AI, offline deterministic translation provider (`DeterministicTranslationProvider` in `src/app/services/translation.py`) translating French/English titles and description sections.
  - Translation endpoints: `GET /api/v1/jobs/{job_id}/translations` and `POST /api/v1/jobs/{job_id}/translations`.
  - Pluggable `SemanticEnrichmentAdapter` protocol with `RuleBasedSemanticFallback` layered on top of the deterministic rule-based matcher with fault-tolerant error recovery.
  - Frontend vacancy language toggle bar (`JobDetailModal.tsx`) with dynamic translation and ground truth reassurance badge.

- **Phase 12: Declarative Sources, Country Preferences, Application Pipeline & Scraper Analytics**:
  - Migration 007 (`007_create_user_applications.sql` & Alembic `a7b8c9d0e1f2`): `user_applications` table with `uq_user_job` constraint.
  - Candidate country preferences: `PUT /api/v1/profile/countries` and interactive multi-country selector.
  - Multilingual query expander (`src/app/scraper/search.py`) mapping English and French technical job terms and workplace vocabulary.
  - Application Pipeline Kanban view (`ApplicationsView.tsx`) with 5 lifecycle stages, notes, and direct vacancy modals.
  - Declarative source registry (`config/sources.json` & `source_config.py`).
  - Scraper telemetry and analytics: `GET /api/v1/admin/metrics` and top metrics summary bar in `ScraperDashboard.tsx`.

- **Phase 11: Candidate Multi-Dimensional Profile**:
  - Migration 006 (`006_create_user_profile_tables.sql` & Alembic `f6a1b2c3d4e5`): `user_experience`, `user_education`, `user_languages`.
  - Profile CRUD endpoints for career history, degrees, and language proficiencies.
  - Role-type matching distinction (professional, internship, project, transferable).
  - Profile management UI cards with experience-type badges in `ProfileView.tsx`.

- **Phase 10: Persistence Provenance, Stale Lifecycle & Vocabulary Normalization**:
  - Migration 005 (`005_add_scrape_target_provenance_and_indexes.sql` & Alembic `e5efb7c8a123`): Added `jobs.scrape_target_id` and composite indexes (`company_id + external_job_id`, `company_id + job_url`, `scrape_target_id + last_seen_at`, `active`).
  - Cautious stale-job lifecycle service (`evaluate_target_stale_jobs`).
  - Standardized vocabulary normalizers (`src/app/scraper/vocabulary.py`) for employment types, remote modes, locations, and technical skills.
  - Comprehensive documentation suite: `DEVELOPMENT.md`, `CONFIGURATION.md`, and `TESTING.md`.

- **Master Build Prompt Addendum v1**:
  - Session continuity protocol and `PROGRESS.md` audit.
  - Automated `robots.txt` compliance checking and `SOURCE_DISALLOWED` enforcement.
  - Ingestion HTML sanitization using `bleach` and `BeautifulSoup` to prevent stored XSS attacks.
  - Data model gaps closed: salary columns, `scrape_targets.robots_txt_*`, and user lifecycle fields.
  - Company onboarding pipeline with heuristic portal classification and CLI tool.
  - Tooling & CI: `.python-version`, Node engines, GitHub Actions workflow, and pre-commit configuration.
  - Observability: enhanced `/health` with database query latency, and structured JSON logging.
  - UI Chrome internationalization: decoupled English and French switcher in React frontend.

- **Phase 9: Frontend React Web Application**:
  - Modern glassmorphic web application built with React 19, TypeScript, and Vite.
  - Floating dock navbar, search bar with quick-filters, opportunity cards, detail modal, auth modal, profile preferences view, and Scraper Hub monitor dashboard.

- **Phase 8: Authentication, Profile & Matching Engine APIs**:
  - Stateless JWT issuance, bcrypt password hashing, and user registration/login.
  - Deterministic rule-based matching engine calculating match percentages and explanation breakdowns.

- **Phases 0-4: Foundation, Cooldowns, Source Parsers, Persistence & APIs**:
  - FastAPI application with MySQL connection pool.
  - Three verified career portals integrated: Orange Maroc, Capgemini Morocco, and Inwi.
  - URL canonicalization, tracking parameter stripping, and idempotent candidate upsert.
  - Job directory search and filter endpoints with pagination.
