# Compust

Compust is a local-first career intelligence and opportunity directory.

## Foundation status

The current milestone provides:

- FastAPI application setup;
- Uvicorn-compatible application import;
- environment-based MySQL configuration;
- SQLAlchemy session management;
- read-only country and company endpoints;
- company and country detail lookups with 404 handling;
- a database-backed health endpoint;
- focused pytest coverage.

The existing MySQL `compust` database remains the source of truth. This foundation
does not create tables, migrate schema, or modify existing records.

## Database migrations

Migrations are plain SQL files under `migrations/`. The scrape-target migration
is idempotent and only creates `scrape_targets` when it is missing:

```text
python -m migrations.runner
python -m migrations.seed_scrape_targets
```

The seed command derives targets from existing non-null `companies.careers_url`
values and will not insert duplicates.

## Run locally

1. Copy `.env.example` to `.env` and adjust credentials if needed.
2. Install dependencies:

   ```text
   pip install -r requirements.txt
   ```

3. Start the API:

   ```text
   uvicorn src.app.main:app --reload
   ```

Available endpoints:

- `GET /health`
- `GET /api/v1/countries`
- `GET /api/v1/countries/{code}`
- `GET /api/v1/companies`
- `GET /api/v1/companies/{company_id}`
- `GET /api/v1/scrape-targets`
- `GET /api/v1/scrape-targets/{target_id}`
- `POST /api/v1/scrape-targets/{target_id}/inspect`
- `POST /api/v1/scrape-targets/{target_id}/parse`
- `POST /api/v1/scrape-targets/{target_id}/sync`
- `GET /docs`
