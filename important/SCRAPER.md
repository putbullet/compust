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

It upserts Orange candidates by company/external ID, falling back to the
company/job URL, and refreshes job skills without marking absent jobs closed.
