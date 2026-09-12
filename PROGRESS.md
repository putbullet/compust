PROGRESS.md
---
Last updated: 2026-09-11
Current phase: Phase 13 Completed (Decoupled Job Translation Architecture & Semantic Enrichment Adapter)
Completed phases:
  - Phase 0: Foundation & audit (FastAPI app, MySQL connection, read-only country & company endpoints, health check)
  - Phase 1: Scraping runs & cooldowns (scraping_runs table, run lifecycle, target status, exponential/fixed cooldown persistence)
  - Phase 2: Source parsers & discovery (Orange Maroc multi-page rel="next", Capgemini API translation & JSON parser, Inwi HTML/turbo-stream parser, source registry)
  - Phase 3: URL normalization & job persistence (canonicalization, query tracking stripping, idempotent candidate upsert by external_id or job_url, job skills synchronization)
  - Phase 4: Job directory API endpoints (GET /api/v1/jobs with filters & pagination, GET /api/v1/jobs/{id} with skills)
  - Addendum v1 (Continuity, Compliance, Security & Data Models):
      * Section A: PROGRESS.md session start & continuity protocol implemented at repo root.
      * Section B: robots.txt automated compliance check, SOURCE_DISALLOWED flag & blocking, Terms of Service reviews documented in SCRAPER.md.
      * Section C: HTML sanitization on ingestion via bleach & BeautifulSoup, stripping script injections/event handlers, verified with XSS test fixtures.
      * Section D: Data model gaps closed: jobs.salary_* columns, user_preferences.salary_currency, scrape_targets.robots_txt_*, users.email_verified & users.is_active.
      * Section E: Authentication design documented in ARCHITECTURE.md (stateless JWT, token rotation, Argon2id/bcrypt, lockout prevention, login rate limits).
      * Section F: Alembic migration framework initialized (alembic.ini, env.py, revision d4cdab5fadff) and kept in sync with versioned SQL runner (migration 004 applied to live MySQL).
      * Section G: Company & source onboarding pipeline: CLI tool (`python -m src.app.cli.onboard`), admin endpoint (`POST /api/v1/admin/onboard`), and heuristic portal classifier detecting ATS vendor signatures (Workday, SmartRecruiters, Greenhouse, Taleo, TurboStream, JSON API, standard HTML) and pagination patterns with upfront robots.txt compliance.
      * Section H: Tooling and CI: pinned Python (`.python-version` 3.14.2), Node (`engines >=20.0.0`), GitHub Actions workflow (`.github/workflows/ci.yml`), pre-commit hooks (`.pre-commit-config.yaml`), and environment-driven CORS configuration (`COMPUST_CORS_ALLOWED_ORIGINS`).
      * Section I: Observability: enhanced `/health` endpoint with MySQL query latency measurement (`latency_ms`), and structured JSON logging (`src/app/logging.py`) with contextvars tagging all scraper logs by `scraping_runs.id`, `company_id`, and `target_id`.
      * Section J: UI chrome internationalization: separate `LanguageContext` and `useTranslation` in React frontend supporting instant English (`EN`) and French (`FR`) toggle across navbar, search filters, hero, empty states, and modals, strictly decoupled from job vacancy content translation.
  - Phase 8: Authentication, Profile & Matching Engine APIs:
      * Implemented bcrypt password hashing and JWT issuance/verification (`security.py`).
      * Created auth endpoints: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`.
      * Created profile endpoints: `GET /api/v1/profile`, `PUT /api/v1/profile/preferences`, `PUT /api/v1/profile/skills`.
      * Implemented rule-based matching engine (`matching/matcher.py`): computes score (0-100%) and positive/missing factor breakdowns based on title, skills, work mode, and target salary.
      * Extended `GET /api/v1/jobs` and `GET /api/v1/jobs/{id}` with personalized match scores when authenticated.
      * Added CORS middleware for Vite frontend development (`localhost:5173`) and configurable production origins.
  - Phase 9: Frontend React Web Application:
      * Initialized Vite + React 19 + TypeScript frontend with styled-components, Lucide icons, and modern glassmorphic design system.
      * Integrated UI widgets from `important/items/`:
          - Floating dock navbar with smooth tooltips, language toggle, and auth pill (`small_navbar.md`).
          - Glassmorphism search input with instant debounced filtering, country and remote quick-pills (`search_bar.md`).
          - Modern opportunity cards with salary badges, match percentages, and save bookmarks.
          - Opportunity detail modal with XSS-safe sanitized description rendering and match factor breakdowns.
          - Authentication modal supporting Login & Registration (`login_form.md`).
          - Profile and matching preferences view with interactive skill tagger (`profile_card.md`).
          - Scraper Hub monitor dashboard with live target statuses, cooldown timers, robots.txt compliance flags, and sync triggers.
      * Verified production build: `npm run build` succeeds cleanly with 0 TypeScript or bundle errors.
  - Phase 10: Persistence Provenance, Stale Lifecycle & Vocabulary Normalization:
      * Migration 005 applied to MySQL: Added `jobs.scrape_target_id` FK and composite indexes (`company_id + external_job_id`, `company_id + job_url`, `scrape_target_id + last_seen_at`, `active`).
      * Cautious stale-job lifecycle service (`src/app/services/stale_lifecycle.py`): strictly guards against false job closure on partial or failing crawls, requiring multiple verified consecutive successful scrapes before deactivating absent postings.
      * Standardized vocabulary normalizer (`src/app/scraper/vocabulary.py`) for employment types (CDI/CDD/Stage -> canonical tokens), remote types (Remote/Hybride/Sur site -> canonical tokens), locations, and technical skills across parsers.
  - Phase 11: Candidate Multi-Dimensional Profile (Experience, Education, Languages):
      * Applied Migration 006 (`migrations/006_create_user_profile_tables.sql` & Alembic `f6a1b2c3d4e5`): created `user_experience`, `user_education`, and `user_languages` tables with cascade deletion.
      * Mapped ORM models in `src/app/models.py`: declared `UserExperience`, `UserEducation`, and `UserLanguage` models with eager selectin relationships on `User`.
      * Created Pydantic request/response models (`src/app/schemas_profile.py`): experience type literals (`professional`, `internship`, `project`, `transferable`), education history, and language proficiencies (`native`, `fluent`, `intermediate`, `basic`).
      * Created Profile Repository (`src/app/repositories/profile.py`): CRUD handlers for adding and deleting experiences, educations, and languages.
      * Added REST Endpoints to FastAPI (`src/app/main.py`):
          - `POST /api/v1/profile/experiences` & `DELETE /api/v1/profile/experiences/{id}`
          - `POST /api/v1/profile/educations` & `DELETE /api/v1/profile/educations/{id}`
          - `POST /api/v1/profile/languages` & `DELETE /api/v1/profile/languages/{id}`
      * Enhanced Matching Engine (`src/app/matching/matcher.py`): multi-dimensional match calculation differentiating career tenure (seniority requirement validation from verified professional roles, internship/project portfolio alignment for junior roles, and language requirements against posting specifications).
      * Expanded React Frontend (`ProfileView.tsx` and `client.ts`): interactive management cards for career experience (with experience-type badges), academic background, and language proficiencies with upsert/delete controls.
  - Phase 12: Declarative Sources, Country Preferences, Application Tracking & Scraper Analytics:
      * Applied Migration 007 (`migrations/007_create_user_applications.sql` & Alembic `a7b8c9d0e1f2`): created `user_applications` with cascade deletion and unique constraint `uq_user_job`.
      * Candidate Country Preferences: added `user_country_preferences` sync endpoint `PUT /api/v1/profile/countries` and interactive multi-country selector in React frontend.
      * Multilingual Search Query Expansion (`src/app/scraper/search.py`): deterministic lexical query expansion between French and English technical roles and workplace terms (e.g. *développeur* ↔ *developer*, *stage* ↔ *internship*, *télétravail* ↔ *remote*).
      * Application Pipeline & Tracking (`src/app/repositories/applications.py` & `src/app/schemas_applications.py`):
          - Endpoints: `GET /api/v1/applications`, `POST /api/v1/applications/{job_id}`, `PATCH /api/v1/applications/{id}`, `DELETE /api/v1/applications/{id}`.
          - Frontend: dedicated **Applications Pipeline** Kanban view (`ApplicationsView.tsx`) tracking Saved, Applied, Interviewing, Offer, and Rejected stages with notes and direct vacancy modals.
          - Opportunity feed bookmark button persists directly to database when authenticated.
      * Declarative Source Configurations (`config/sources.json` & `src/app/scraper/source_config.py`): refactored `registry.py` to match strategies declaratively by domains and target types, removing all hardcoded company-name conditionals.
      * Scraper Telemetry & Failure Analytics (`src/app/repositories/metrics.py` & `src/app/schemas_metrics.py`):
          - Added `GET /api/v1/admin/metrics` returning run count, status breakdown, success rate, duplicate ingestion rate, average duration, target statuses, and recent errors.
          - Integrated top telemetry metrics summary bar into `ScraperDashboard.tsx`.
      * Verification: 61 pytest tests passing cleanly; `npm run build` succeeds with 0 TypeScript/bundling errors.
  - Phase 13: Decoupled Job Translation Architecture & Semantic Enrichment Adapter:
      * Applied Migration 008 (`migrations/008_create_job_translations.sql` & Alembic `b8c9d0e1f2a3`): created `job_translations` table with cascade deletion, unique constraint `uq_job_translation_lang (job_id, language)`, and indexes on `job_id` and `language`.
      * Employer Text Ground Truth Preservation: `jobs.title` and `jobs.description` strictly preserved unmodified. All localized and machine translations stored in decoupled `job_translations` records.
      * Decoupled Translation Architecture (`src/app/services/translation.py`):
          - Zero-dependency, offline deterministic translation provider (`DeterministicTranslationProvider`) translating technical role titles and description sections (e.g. French <-> English) without external AI API dependencies.
          - Service methods: `get_translations`, `get_translation`, `create_or_update_translation`, `auto_translate_job`.
          - Endpoints: `GET /api/v1/jobs/{id}/translations` and `POST /api/v1/jobs/{id}/translations`.
      * Semantic Enrichment Adapter Protocol (`src/app/matching/semantic_adapter.py`):
          - Pluggable `SemanticEnrichmentAdapter` interface cleanly layered on top of the deterministic rule-based matching engine.
          - `RuleBasedSemanticFallback`: 100% offline keyword/token Jaccard affinity engine operating with 0 external API keys or network dependencies.
          - Fail-safe fault tolerance: any external AI/embedding adapter failure gracefully defaults to the verified deterministic rule-based score.
      * Frontend Vacancy Translation Toggle (`JobDetailModal.tsx` & `client.ts`):
          - Language toggle pill bar (`Original (Employer)`, `English`, `Français`) in the vacancy modal.
          - Ground truth assurance badge ("Employer source text preserved unmodified").
          - Dynamic on-demand translation fetching and caching.
      * Verification: 65/65 pytest tests passing cleanly; `npm run build` succeeds in 490ms with 0 TypeScript or bundling errors.
  - Phases 16–21: Local Company Management, Country Mapping, Ollama AI, Assistant & Resume Intelligence:
      * Phase 16: Company & Country Association & Scrape Targets Management:
          - Database migration 009 applied to live MySQL (`resumes` table with parsed JSON sections).
          - Company CRUD & status management (`src/app/repositories/companies.py`): create, update, reversible deactivation (`is_active` toggle), and hard delete with confirmation guard (`confirm=true`).
          - Scrape target CRUD & manual execution (`src/app/repositories/scrape_targets.py`): associate with companies and country codes, toggle target status, trigger immediate scraping runs (`POST /api/v1/scrape-targets/{id}/run`).
          - Frontend: dedicated Company Management view (`CompanyManagementView.tsx`), country badges, targets list, live run scraper trigger, and deactivation modal safeguards.
      * Phase 17: Ollama Local AI Integration:
          - Local AI service (`src/app/services/ai_service.py`): dynamically queries local Ollama instance (`/api/tags`), inspects installed models, parameter size, and quantization without hardcoding model tags.
          - Fail-safe resilience: COMPUST operates 100% deterministically when Ollama is offline or not installed.
          - Providers endpoint: `GET /api/v1/ai/providers` listing local Ollama and optional cloud providers.
          - Settings endpoint: `POST /api/v1/ai/settings` allowing runtime model selection.
      * Phases 18, 22, 23: Local AI Information Assistant & Deterministic Tool Set:
          - Tool execution layer (`src/app/services/ai_tools.py`): strictly parameterized, deterministic query tools (count active jobs, latest opportunities, target company jobs, match analysis). Zero arbitrary SQL and zero database credentials passed to the LLM.
          - System prompt tuned for compact local models (`qwen3.5:0.8b`) with structured context grounding and conversational fallback.
          - Frontend: floating bottom-right AI Assistant chat widget (`AIAssistantWidget.tsx`) with provider status indicator, quick action prompts, and chat history.
      * Phase 19: Resume Upload & Heuristic Structuring:
          - Resume extraction engine (`src/app/services/resume_parser.py`): extracts text via `pypdf`, strictly rejects scanned/image-only PDFs (`ScannedPdfError`) with clear instructions. No OCR dependencies.
          - Heuristic section parsing: categorizes text into summary, experience, education, skills, projects, certifications, and languages.
          - Multi-resume lifecycle (`src/app/repositories/resume.py`): active resume designation, retrieval, and deletion.
          - Frontend: Resume Intelligence card in `ProfileView.tsx` with upload dropzone and structured skill badges.
      * Phase 20: Advisory Resume Customization Assistant:
          - Customization service (`src/app/services/resume_customization.py`): deterministic gap analysis comparing resume against job requirements (`already_demonstrated` vs `missing_or_weak`).
          - Ethical advisory tone: strictly avoids fabricating skills or experiences; highlights authentic strengths and phrasing recommendations.
          - Vacancy modal integration (`JobDetailModal.tsx`): "Suggest Resume Customization" button and interactive recommendations drawer.
      * Phase 21: Application Pipeline Quick Action:
          - "Mark as Applied" directly accessible from the job detail modal, seamlessly linking vacancy view with the `user_applications` pipeline.
      * Verification: 77/77 pytest tests passing cleanly; `npm run build` succeeds in 641ms with 0 TypeScript or bundling errors.
In-progress work: Complete Master Build Prompt, Addendum directives, and Extension Phases 16–21 fully implemented and verified.
Known broken/incomplete pieces: None.
Last verified against real DB/code: 2026-09-11 (Verified against local MySQL 'compust' database with migrations 001-009 applied, live Ollama runtime on 127.0.0.1:11434 with qwen3.5:0.8b, live FastAPI server, live Vite dev server, 77 passing pytest tests, and clean Vite production build).
Next recommended step: Production containerization / deployment, continuous scheduled scraping, and automated employer ingestion.
