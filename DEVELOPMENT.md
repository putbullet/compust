# Compust — Developer Guide

Welcome to the **Compust** development repository. Compust is a high-transparency employment intelligence platform focused on verified career portals across Morocco and international markets.

---

## 1. Prerequisites & Environment

- **Python**: 3.12+ (pinned to `3.14.2` in `.python-version`)
- **Node.js**: 20.0+ (pinned in `frontend/package.json`)
- **Database**: MySQL 8.0+ running locally on port 3306 with schema `compust`

---

## 2. Backend Setup

From the `important/` directory:

```bash
# Create virtual environment (if not present)
python -m venv .venv

# Activate environment
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Database Migrations

```bash
# Run migration runner to apply pending SQL migrations
python -m migrations.runner

# Or using Alembic
alembic upgrade head
```

### Starting the FastAPI Server

```bash
uvicorn src.app.main:app --reload --port 8000
```
- API Base: `http://localhost:8000`
- Interactive Swagger Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

---

## 3. Frontend Setup

From the `important/frontend/` directory:

```bash
# Install packages
npm install

# Start Vite dev server
npm run dev
```
- Frontend Dev URL: `http://localhost:5173`
- Production Build Check: `npm run build`

---

## 4. Running the Tests

Backend tests run completely isolated from external networks using saved fixtures and in-memory SQLite instances:

```bash
# From important/ directory
pytest -v
```

---

## 5. Code Quality & Pre-Commit

We enforce formatting and linting via Ruff:

```bash
# Check code style
ruff check src tests

# Format code
ruff format src tests

# Install pre-commit hooks
pre-commit install
```

---

## 6. Onboarding New Career Sources

To register a new company and automatically classify its career portal:

```bash
# Run CLI tool
python -m src.app.cli.onboard --name "Company Name" --website "https://company.ma" --careers "https://company.ma/careers" --country "MA"
```
Or use the admin API: `POST /api/v1/admin/onboard`.
