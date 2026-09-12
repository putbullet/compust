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
