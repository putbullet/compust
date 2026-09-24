# Contributing to Compust

Thank you for your interest in contributing to **Compust**! Compust is an open-source, local-first employment intelligence platform combining automated career portal ingestion, deterministic resume parsing, vacancy match scoring, and omnipresent browser job capture.

Contributions of all kinds are warmly welcomed: whether you are adding support for a new career portal ATS, fixing a parser edge case, improving the match engine, enhancing the browser extension, or refining documentation and localization.

---

## Code of Conduct & Security

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it to understand our community standards and enforcement guidelines.

If you discover a security vulnerability, please do **not** open a public issue. Review our [Security Policy](SECURITY.md) for instructions on confidential reporting.

---

## Getting Started & Development Setup

Compust is structured as a full-stack monorepo:
- **`important/src/`**: FastAPI backend, SQLAlchemy database models, career portal scraper, and resume parser.
- **`important/frontend/`**: React 19 + TypeScript + Vite web dashboard and WYSIWYG Resume Studio.
- **`important/extension/`**: Compust Capture browser extension (Manifest V3 for Chrome/Edge/Brave and Firefox).
- **`launcher/`**: Python-based one-click desktop launcher engine.

### Prerequisites

- **Python**: 3.12+ (tested up to 3.14, see `.python-version`)
- **Node.js**: 20.0+ and `npm` 10.0+
- **Database**: MySQL 8.0+ running locally on port 3306 (Compust will also run automatically against an embedded SQLite database if MySQL is not detected).
- **Optional**: [Ollama](https://ollama.com/) running locally with model `qwen3.5:0.8b` (or your preferred local LLM) for offline ATS checking and interview prep features.

### Step-by-Step Setup

For complete local setup instructions, follow the [Quick Start Guide in the README](README.md#quick-start-guide) or consult [DEVELOPMENT.md](DEVELOPMENT.md) and [COMPUS_DEVELOPER_GUIDE.md](COMPUS_DEVELOPER_GUIDE.md).

```bash
# 1. Backend setup (from important/)
cd important
python -m venv .venv
source .venv/bin/activate       # On Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m migrations.runner     # Apply database migrations
uvicorn src.app.main:app --reload --port 8000

# 2. Frontend setup (from important/frontend/)
cd important/frontend
npm install
npm run dev                    # Starts Vite server on http://localhost:5173

# 3. Extension build (from important/extension/)
cd important/extension
npm install
npm run build                  # Builds dist/chrome and dist/firefox
```

---

## Key Contribution Areas & Extension Points

### 1. Adding or Updating Career Scraper Platform Adapters

Compust connects directly to verified employer career portals. If an employer's portal is not indexed or parsed correctly:
1. **Inspect with Diagnostics**: Use the in-app **Data Supervision ➔ Scraper Test Diagnostic** tool or `POST /api/v1/admin/scraper/test` to inspect HTTP status, rendering mode, and detected platform.
2. **Implement Platform Adapter**: Add or update an adapter under `important/src/app/scraper/platforms/` (existing adapters include Greenhouse, Lever, Workday, SmartRecruiters, Ashby, Workable, Teamtailor).
3. **Add Test Fixtures**: Save a sanitized HTML sample in `important/tests/fixtures/` and add automated test coverage in `important/tests/`.
4. **Follow Responsible Scraping Principles**: Respect `robots.txt`, honor rate limits, and never attempt to bypass Cloudflare WAF or CAPTCHAs.

For detailed guidelines, see the [Scraper & Parser Contributor Guide in README.md](README.md#scraper--parser-contributor-guide).

### 2. Browser Extension Site Extractors (`Compust Capture`)

The browser extension ingests vacancies via native adapters (LinkedIn, Indeed, Glassdoor, Welcome to the Jungle) and a universal semantic context-menu extractor:
- Native content scripts reside in `important/extension/src/content/`.
- Adapters operate within isolated Shadow DOM containers and implement an **analyze-first, ephemeral workflow**: external positions are only persisted when the user explicitly clicks `Add`, `Applied`, or `Save`.
- Unit tests use Vitest with JSDOM fixtures under `important/extension/tests/unit/`.

### 3. Resume Parsing & ATS Enhancement

- Resume extraction operates deterministically without lossy OCR (`important/src/app/services/resume_parser.py`).
- Supports multilingual headers and competencies across English, French, and German.
- Document exports are typeset via RenderCV and Typst.

---

## Code Quality & Linting Standards

Please run automated formatters and linters prior to committing changes:

### Python Backend
```bash
# From important/
ruff check src tests           # Lint check
ruff format --check src tests   # Code formatting check
```

### Frontend & Web App
```bash
# From important/frontend/
npm run lint                   # Lints using oxlint
npm run build                  # Typechecks with tsc -b and tests production bundling
```

### Pre-Commit Hooks
Pre-commit hooks are configured in `.pre-commit-config.yaml`. You can install them with:
```bash
pre-commit install
```

---

## Running the Test Suites

All Pull Requests must pass automated test suites before being merged:

```bash
# 1. Run Backend Pytest Suite (from important/)
pytest -v

# 2. Run Extension Unit & E2E Tests (from important/extension/)
npm run test:unit              # Runs Vitest unit tests
npm run test:e2e               # Runs Playwright E2E tests (if browser environment configured)

# 3. Verify Frontend Build (from important/frontend/)
npm run build
```

### Live Verification Requirement

In addition to automated tests, Compust maintainers emphasize **live manual verification** for any user-facing changes:
- Verify that the running application (`http://localhost:5173`) reflects state transitions accurately.
- For UI charts (such as the Sankey Pipeline funnel), confirm that multi-stage transitions (forward, backward, and lateral) update immediately and without stale rendering artifacts.
- When opening a PR, include a note or screenshot documenting your live verification steps.

---

## Git Commit Conventions

Compust follows the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` A new user-facing feature or capability (e.g. `feat(scraper): add Greenhouse API pagination`)
- `fix:` A bug fix (e.g. `fix(funnel): determine stage placement strictly from current status`)
- `docs:` Documentation updates (e.g. `docs: add community standards and contribution guide`)
- `test:` Adding or updating tests (e.g. `test(pipeline): add backward transition regression tests`)
- `refactor:` Code improvements without behavioral changes
- `chore:` Build scripts, dependencies, or tool configurations

Keep commit messages concise and descriptive.

---

## Submitting a Pull Request

1. **Fork the Repository**: Create your branch from `master` (e.g. `git checkout -b fix/funnel-stage-counts`).
2. **Make Focused Changes**: Keep PRs focused on a single issue or feature.
3. **Verify Locally**: Run test suites, formatters, and verify the changes live in the running application.
4. **Open Pull Request**: Fill out the [Pull Request Template](.github/PULL_REQUEST_TEMPLATE.md) completely, referencing any related issue numbers.
5. **Code Review**: A maintainer will review your contribution. Be prepared to address feedback or add clarifying tests.

Thank you for helping make Compust a better tool for the global tech community!
