# Remaining Compust tasks

This document records work that remains after the initial FastAPI, database,
scrape-target, source-inspection, Orange parsing, and first job-persistence
milestones.

## Immediate scraper work

- [ ] Add a scraping-run model and migration.
  - Track target, start/finish timestamps, status, jobs found, added, updated,
    and parser/request errors.
  - Use the documented statuses: `pending`, `running`, `success`, `failed`,
    and `partial`.
- [ ] Remove the temporary Orange company-ID parser gate.
  - Replace it with source strategy selection based on target/company
    configuration rather than `company_id == 1`.
- [ ] Implement Orange pagination discovery.
  - Follow the live `rel="next"` URL pattern (`from`/`s`) only when present.
  - Stop on no next link, exhausted results, repeated job IDs, or a configured
    safety limit.
  - Add saved page-1/page-2 fixtures and duplicate-result tests.
- [ ] Improve URL normalization.
  - Canonicalize case, fragments, tracking parameters, and encoded paths while
    preserving the application URL.
- [ ] Add source-specific status/cooldown persistence.
  - Record 403, 429, timeout, connection, parser, and success outcomes.
  - Do not retry restricted sources aggressively.

## Job persistence and lifecycle

- [ ] Add repository/API tests against a MySQL test schema or isolated
  transaction strategy.
- [ ] Add safe indexes or migration constraints for job deduplication after
  measuring existing data:
  - company + external job ID;
  - company + canonical URL.
- [ ] Store scrape-target provenance on jobs.
  - The current `jobs` table has no `scrape_target_id`; design a
    non-destructive migration before adding it.
- [ ] Add cautious stale-job handling.
  - Never close a job after one incomplete scrape.
  - Require reliable successful source coverage before marking jobs stale or
    closed.
- [ ] Add job list/detail/search FastAPI endpoints with pagination and filters.
- [ ] Add normalized employment-type, remote-type, location, and skill
  vocabulary modules.

## Remaining real-source integrations

- [ ] Inspect and fixture-test Capgemini.
  - Determine pagination, country parameters, result payload, and job detail
    structure.
  - Implement only the source-specific strategy required by evidence.
- [ ] Inspect and fixture-test Inwi.
  - Determine server-rendered versus API-backed listings, pagination, and
    detail URLs.
- [ ] Compare all three sources and extract reusable discovery primitives.
- [ ] Add source configuration records or files without hardcoded company-name
  conditionals.

## API and operations

- [ ] Add explicit scraper-control endpoints for one target and one company.
- [ ] Add authentication before exposing private profile operations.
- [ ] Add request validation and consistent error response schemas.
- [ ] Add structured application logging without logging private profile data.
- [ ] Add configuration for request timeout, user agent, delay, and page limit.

## User and matching features

- [ ] Add secure password hashing and local user/profile APIs.
- [ ] Add education, skills, languages, experience, preferences, and country
  preference repositories.
- [ ] Preserve distinctions between professional experience, internships,
  projects, and transferable experience.
- [ ] Implement configurable, explainable rule-based matching.
- [ ] Add match explanations with positive and missing factors.

## Frontend

- [ ] Inspect and adapt the supplied UI snippets into a coherent React
  application.
- [ ] Use the preferred Tabler icon source after confirming the required icon
  package and license handling.
- [ ] Add country selection, job directory, filters, job detail, and profile
  views.
- [ ] Add responsive layouts, keyboard navigation, visible focus states, and
  reduced-motion behavior.
- [ ] Add frontend API client and loading/error/empty states.

## Internationalization and future intelligence

- [ ] Preserve original job text and add separate translation fields/modules.
- [ ] Add country-configured languages and normalized multilingual search terms.
- [ ] Keep all core scraping, parsing, persistence, and matching functional
  without AI.
- [ ] Consider AI-assisted classification or semantic matching only after
  reliable rule-based behavior and measurements exist.

## Quality and delivery

- [ ] Add migration version tracking before adding more schema migrations.
- [ ] Add CI tests using saved fixtures only; never require live websites.
- [ ] Add `DEVELOPMENT.md`, `DATABASE.md`, `CONFIGURATION.md`, `TESTING.md`,
  and `CHANGELOG.md`.
- [ ] Add a frontend build and test workflow once the React application exists.
- [ ] Measure requests, scrape duration, parser failures, duplicate rate,
  database writes, and discovered jobs before scaling beyond three sources.
