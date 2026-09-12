# Compust — Testing Guide

Testing is a core discipline in Compust. We mandate 100% network-isolated automated testing to guarantee reproducible, fast, and deterministic test runs.

---

## 1. Running Tests

```bash
# From important/ directory
cd important

# Run entire test suite
pytest -v

# Run a specific module
pytest tests/test_stale_lifecycle.py -v
pytest tests/test_matching.py -v
pytest tests/test_vocabulary.py -v
```

---

## 2. Test Architecture

### A. Zero Live Network Dependency
- **Rule**: Tests must **never** make live HTTP requests to external career portals during automated runs.
- **Mechanism**: `httpx.MockTransport` or saved disk fixtures in `tests/fixtures/` (`orange_search_results.html`, `capgemini_jobs.json`, `inwi_page1.html`, `inwi_stream_page2.html`).

### B. Database Isolation
- Production runs on MySQL 8.0+.
- Unit and integration tests run against ephemeral in-memory SQLite instances using `StaticPool` (`sqlite://`), ensuring complete state isolation between test cases.
- Database dependencies are swapped using FastAPI's `app.dependency_overrides[get_db] = fake_db`.

---

## 3. Test Suites Overview

| Suite | Purpose |
| :--- | :--- |
| `tests/test_app.py` | Validates OpenAPI docs, health check latency, and read endpoints. |
| `tests/test_auth.py` | Registration, duplicate email rejection, JWT login, profile queries, and preference updates. |
| `tests/test_matching.py` | Rule-based match scoring (0-100%), positive factor explanations, and missing factor identification. |
| `tests/test_jobs.py` & `test_jobs_api.py` | Idempotent candidate upsert, skills syncing, and list/filter/pagination endpoints. |
| `tests/test_scraper.py` | Inspection, structure extraction, error categorization (403, 404, 429, 500). |
| `tests/test_orange_parser.py` | Multi-page Orange `rel="next"` parsing and structured candidate extraction. |
| `tests/test_capgemini.py` | REST API payload parsing, pagination boundary detection, and location normalization. |
| `tests/test_inwi.py` | TurboStream partial DOM parsing and `show_more` pagination link extraction. |
| `tests/test_robots.py` | Standard `robots.txt` rules evaluation and `SOURCE_DISALLOWED` enforcement. |
| `tests/test_sanitizer.py` | Stored XSS defense: strips `<script>`, event handlers (`onload`), `<iframe>`, and preserves safe tags. |
| `tests/test_stale_lifecycle.py` | Cautious job deprecation and target provenance verification across verified successful crawl runs. |
| `tests/test_vocabulary.py` | Normalization of employment types, remote modes, locations, and skills. |
| `tests/test_onboarding.py` | Heuristic portal classifier for Workday, SmartRecruiters, TurboStream, and HTML. |
| `tests/test_logging.py` | Structured JSON log output and `ScrapingRunScope` context tagging. |
| `tests/test_migrations.py` | Migration runner validation and version sequence tracking. |
