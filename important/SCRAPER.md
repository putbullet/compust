# Scraper foundation

The first scraper layer is intentionally limited to source acquisition and
inspection. It does not discover or persist jobs.

`fetch_source` follows normal redirects, uses a bounded timeout, identifies
non-success responses, and raises an explicit `SourceFetchError` for failures.
`inspect_source` parses the acquired HTML to report links, forms, pagination
hints, JSON-LD blocks, and basic API references.

The OrangeMaroc target can be inspected through:

```text
POST /api/v1/scrape-targets/1/inspect
```

The response is metadata only; raw HTML is not exposed through the API.
Automated tests use the saved fixture at
`tests/fixtures/orange_search_results.html` rather than depending on the live
website.

Orange structured job candidates can be parsed through:

```text
POST /api/v1/scrape-targets/1/parse
```

This endpoint returns normalized candidates and parser errors only. It does not
write to the `jobs` table.

The first persistence endpoint is:

```text
POST /api/v1/scrape-targets/1/sync
```

It upserts candidates by company/external ID, falling back to the canonical company/job URL, and refreshes job skills without marking absent jobs closed.

---

## Legal & Scraping Compliance (Addendum Section B)

### Automated `robots.txt` Enforcement

Before scraping or inspecting any target, Compust automatically fetches and parses the domain's `robots.txt`:
1. The target URL's path is checked against `Disallow` rules for the `CompustBot/1.0` and wildcard `*` user agents.
2. The check result is recorded on `scrape_targets.robots_txt_allowed` (BOOLEAN) and `scrape_targets.robots_txt_checked_at` (DATETIME).
3. If a target's path is disallowed:
   - Scraping is strictly prevented.
   - The target status is flagged as `SOURCE_DISALLOWED`.
   - API endpoints (`/inspect`, `/parse`, `/sync`) return an HTTP 403 Forbidden error.
4. If `robots.txt` returns 404 (Not Found), standard web convention applies and the target is permitted.

### Manual Terms of Service Review Findings

A manual review of the target career portals was conducted for explicit anti-scraping clauses:

1. **Orange Maroc (`orange.jobs`)**:
   - *Target path*: Public careers search and listing portal.
   - *Robots.txt*: Permits public listing pages; crawls restricted only on admin/internal paths.
   - *TOS Review*: No explicit contractual restriction found prohibiting automated indexation of public employment vacancies.
   - *Operating parameters*: Multi-page rel="next" traversal capped at 20 pages max per run, with bounded timeouts and cooldown on rate limits.

2. **Capgemini (`careers.capgemini.com` / `cg-jobstream-api.azurewebsites.net`)**:
   - *Target path*: Public career vacancy search and public jobstream API endpoint.
   - *Robots.txt*: Public vacancy endpoints are accessible; standard web indexers permitted.
   - *TOS Review*: No explicit prohibition on reading public career listings found. Standard API payload format utilized without evasive behavior.
   - *Operating parameters*: Polite paging, pagination bounded by total vacancy count, non-disruptive query size.

3. **Inwi (`recrutement.inwi.ma`)**:
   - *Target path*: Public recruitment directory and turbo-stream pagination endpoint.
   - *Robots.txt*: Public vacancy listings permitted.
   - *TOS Review*: No explicit anti-scraping restriction found for public job postings.
   - *Operating parameters*: Bounded incremental pagination following `show_more` links.

### Content Sanitization (Addendum Section C)

All scraped HTML and free-text fields (such as `description`, `title`, `department`, `location`) are sanitized upon ingestion using `bleach` and `BeautifulSoup` before reaching the database:
- Executable scripts (`<script>`), styles (`<style>`), frames (`<iframe>`), objects, and event handlers (`onload`, `onerror`, `onclick`, etc.) are completely decomposed and stripped.
- Safe formatting tags (`<p>`, `<ul>`, `<li>`, `<strong>`, `<em>`, `<a>` with http/https) are preserved for structured frontend presentation.
- Tested and verified against malicious XSS script injection test fixtures.

---

## Company Onboarding & Heuristic Classification (Addendum Section G)

When onboarding new employers beyond the initial sources, Compust uses an automated classifier to analyze candidate career URLs:

1. **Classification Pipeline**:
   - `classify_portal(url)` inspects domain names, HTML tags, headers, and DOM scripts.
   - Identifies candidate ATS vendors (Workday, SmartRecruiters, Greenhouse, Taleo, TurboStream/Hotwire, direct JSON API, or standard HTML).
   - Detects pagination mechanisms: `rel_next`, query parameters (`page=`, `from=`), offsets (`offset=`), or incremental stream buttons (`show_more`).
   - Automatically checks `robots.txt` before target registration.

2. **Onboarding Execution**:
   - **CLI**:
     ```bash
     python -m src.app.cli.onboard --name "Atlas Tech" --website "https://atlas.ma" --careers "https://atlas.ma/careers" --country "MA"
     ```
   - **Admin API**:
     `POST /api/v1/admin/onboard` with JSON payload `{ "name": "...", "website_url": "...", "careers_url": "...", "country_code": "MA" }`.

