# Compust — Configuration Reference

All settings in Compust are managed via environment variables and loaded through Pydantic's `BaseSettings` (`src/app/config.py`). A local `.env` file can be placed in `important/` (see `.env.example`).

---

## 1. Environment Variables

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `COMPUST_APP_NAME` | `"Compust API"` | Application name surfaced in OpenAPI metadata. |
| `COMPUST_DEBUG` | `False` | Toggle debug mode in FastAPI. |
| `COMPUST_DATABASE_URL` | `mysql+pymysql://root:@127.0.0.1:3306/compust` | SQLAlchemy connection string to MySQL database. |
| `COMPUST_DB_POOL_PRE_PING` | `True` | Tests MySQL connection liveness before checkout from pool. |
| `COMPUST_JWT_SECRET` | `compust-secret-key-for-development...` | Secret key for signing and verifying stateless HS256 JWT tokens. |
| `COMPUST_JWT_EXPIRE_MINUTES` | `1440` (24 hours) | Expiry duration for issued access tokens. |
| `COMPUST_CORS_ALLOWED_ORIGINS` | `["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"]` | Allowed origins for browser CORS headers. In production, set to your production domain(s). |

---

## 2. Scraper Configuration

- **User Agent**: `CompustBot/1.0 (+https://compust.ma; contact@compust.ma)`
- **Request Timeout**: 20.0 seconds per HTTP call.
- **Safety Pagination Limit**: Max 20 pages per scrape run (`max_pages`).
- **Robots.txt Cache**: Cached for 24 hours per target domain before re-checking.
- **Rate Limit Cooldown**:
  - HTTP 429 (Rate Limited): Exponential backoff (minimum 4 hours).
  - HTTP 403 (Restricted): 24-hour backoff.
  - Robots Disallowed: Permanently flagged `SOURCE_DISALLOWED` until manual review or robots.txt change.

---

## 3. Stale Job Policy

- **Max Missed Runs**: A job is only transitioned to inactive (`active = False`) if absent for **3 consecutive verified successful crawl runs** (`is_full_success=True`).
- Incomplete, partial, or failed scrapes never trigger job closure.
