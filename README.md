<p align="center">
  <img src="docs/logo-transparent.png" alt="Compust Logo" width="100" />
</p>

<h1 align="center">Compust</h1>

<p align="center">
  <em>Local-First Career Intelligence & Verified Vacancy Directory</em>
</p>

<p align="center">
  <a href="https://drive.google.com/file/d/1V1UkAwfKErwvKLdZK2VN0cH_suhf8MGZ/view?usp=sharing">
    <strong>🎥 Google Drive Video Demo</strong>
  </a>
</p>

<p align="center">
  <a href="https://drive.google.com/file/d/1V1UkAwfKErwvKLdZK2VN0cH_suhf8MGZ/view?usp=sharing">
    <img src="docs/screenshots/DEMO_COMPUST.png" alt="Compust Dashboard" width="100%" />
  </a>
</p>

<p align="center">
  <strong>A high-transparency employment intelligence platform combining automated multi-source career portal ingestion, deterministic resume parsing, vacancy match scoring, and interactive gap analysis.</strong>
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#key-features">Key Features</a> •
  <a href="#system-architecture">Architecture</a> •
  <a href="#quick-start-guide">Quick Start</a> •
  <a href="#testing--verification">Testing</a> •
  <a href="#api-examples">API Examples</a> •
  <a href="#future-roadmap">Future Roadmap</a>
</p>

---

## Overview

**Compust** is an end-to-end career intelligence and job discovery platform built for transparency, accuracy, and performance. Unlike traditional job aggregators that suffer from stale listings, broken links, or generic indexing, Compust connects directly to verified employer career portals (Workday, SmartRecruiters, Greenhouse, Ashby, Workable, Lever, Teamtailor, custom career sites) and processes listings through an ethical, rate-limited, and deduplicating ingestion pipeline.

> [!IMPORTANT]
> ### Please Read Before Using Compust
> - **What Compust IS:** A companion career discovery and intelligence tool that helps users ingest and centralize vacancies directly from verified employer portals, evaluate transparent match scores, manage resumes, and track recruitment pipelines.
> - **What Compust IS NOT:** Compust is **NOT** a full replacement for LinkedIn, Indeed, Glassdoor, professional recruiters, or company career boards. Compust does not contain every job on the internet.
> - **Why Some Jobs May Be Missing:** Whether an opening appears in Compust depends on whether its source portal can be accessed, detected, parsed, and normalized. **Not seeing a job in Compust does NOT mean the company does not have that opening available.** Always check company career portals directly.
> - **Project Limitations:** Some sites enforce Cloudflare WAF bot-protection (Compust respects robots.txt and does not bypass WAF/CAPTCHAs), client-rendered SPA shells (hydrated via our Playwright fallback), or multi-tier infinite-scroll pagination.
> - **In-App Interactive Guide:** For an interactive walkthrough, live architecture diagrams, and testing guides, open the **Guide & Docs** tab directly inside the Compust application or click the persistent **"Need Help? See Guide"** button.

In addition to job discovery, Compust provides a **Career Intelligence & Resume Match Engine**:
- Candidates upload their resumes in standard PDF format.
- Compust extracts text layers deterministically without lossy OCR and profiles key technical competencies.
- When inspecting any vacancy, candidates receive an instant **Requirements Match Analysis**, showing demonstrated skills, missing requirements, ATS compatibility advice, and targeted section enhancements.

---

## Key Features

### 1. Verified Career Opportunities Directory
- Real-time catalog of curated vacancies across Morocco and international tech hubs.
- Deep filtering by keyword, location, work mode (Remote, Hybrid, On-site), department, contract type, and salary.
- Multi-lingual user interface with instantaneous **English (EN) and French (FR)** locale toggles.

### 2. Resume Parsing & Candidate Profiling
- **Zero-OCR Deterministic Text Extraction**: Native PDF text extraction ensuring 100% fidelity without hallucination.
- Automated extraction of contact details, work experience history, education, skills, and languages.
- Ability to set an active primary resume or manage multiple profiles.

### 3. Gap Analysis & Career Recommendations
- **Demonstrated Skills vs. Missing Requirements**: Visual pill chips highlight what is already proven in your resume versus requirements you still need to highlight.
- **ATS Compatibility Advice**: Automated formatting checks to maximize ATS parsing efficiency.
- **Section Enhancements**: Practical advice for tailoring work experience bullets and summary statements.
- **Existing Document Downloads**: One-click export for tailored resumes in both PDF and Word DOCX formats.

<p align="center">
  <img src="docs/screenshots/job_detail_modal.jpg" alt="Job Detail and Gap Analysis" width="90%" />
</p>

> [!NOTE]
> **AI Resume Tailoring Status**: Automated vacancy-specific generative bullet tailoring and rewriting is currently in development and clearly marked as **"Coming Soon"**. The normal CV recommendations, gap analysis, and document downloads remain fully active.

### 4. Interactive Applications Kanban Tracker
- Built-in tracking board with fluid drag-and-drop workflow: `Applied` ➔ `Interviewing` ➔ `Offer` ➔ `Rejected`.
- Direct notes, date timestamps, and salary expectations per tracked application.

### 5. Ethical Career Scraper Hub
- **Robots.txt Enforced**: Automatic verification against site crawling rules before initiating scrape runs.
- **Deduplication Engine**: Unique hashing on company and external identifiers prevents duplicate listings.
- **Platform Adapters**: Dedicated parsers for corporate portals (Capgemini, Orange, Inwi, Deloitte, etc.) and generic universal heuristics for new sites.
- **Rate-Limiting & Cooldown**: Domain-aware back-off logic prevents target server overload.

---

## System Architecture

Compust is built with clean layer separation and modern standards:

```
[ Frontend (React 19 + TypeScript + Vite) ]
             |
             | HTTP / REST API (JWT Stateless Auth)
             v
[ FastAPI Application Layer (uvicorn) ]
     |              |               |
     v              v               v
[ Repositories ] [ Services ]  [ Scraper Engine ]
(Jobs, Auth,     (Parser, Match, (Universal, Robots,
 Applications)    Intelligence)   Normalizer)
     |              |               |
     +--------------+---------------+
                    |
           [ SQLAlchemy 2.0 ORM ]
                    |
         +----------+----------+
         |                     |
  [ MySQL 8.0 / XAMPP ]  [ In-Memory SQLite ]
   (Production & Dev)     (Automated Tests)
```

- **Backend**: Python 3.12+ (tested on Python 3.14) with FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, and Bleach sanitization.
- **Frontend**: React 19, TypeScript, Vite, Styled Components, and Lucide React.
- **Database**: MySQL 8.0+ (supported via XAMPP MySQL or standalone instances) with an isolated SQLite layer for lightning-fast pytest runs.

---

## Quick Start Guide

Follow these steps to run Compust locally on your machine.

### Prerequisites
- **Python**: 3.12+ (Python 3.14 supported)
- **Node.js**: 20.0+ and `npm` 10.0+
- **Database**: MySQL 8.0+ (e.g. through **XAMPP** or standalone MySQL Server)

---

### Step 1: Start the Database (XAMPP / MySQL)

1. Open the **XAMPP Control Panel**.
2. Click **Start** next to the **MySQL** module (default port `3306`).
3. Open phpMyAdmin (`http://localhost/phpmyadmin`) or run the MySQL command line, and create the database:
   ```sql
   CREATE DATABASE compust CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

---

### Step 2: Backend Setup & Virtual Environment

Open a terminal (PowerShell on Windows, or Bash on macOS/Linux) and navigate to the `important/` directory:

```powershell
# Navigate to backend directory
cd important

# 1. Create a Python virtual environment
python -m venv .venv

# 2. Activate the virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Windows (CMD):
.\.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate

# 3. Upgrade pip and install all required dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### Configure Environment Variables
Create or verify the `.env` file in the `important/` directory:

```env
COMPUST_DATABASE_URL=mysql+pymysql://root:@localhost:3306/compust
COMPUST_SECRET_KEY=your-secure-random-secret-key-at-least-32-chars
COMPUST_ENVIRONMENT=development
COMPUST_CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173
```

#### Run Database Migrations
Run the SQL migration runner to set up all tables:

```powershell
# Apply all schema migrations
python -m migrations.runner

# (Optional) Verify Alembic head state
alembic upgrade head
```

#### Start the FastAPI Server
Launch the backend server with auto-reloading enabled:

```powershell
uvicorn src.app.main:app --reload --port 8000
```

- **Backend API**: `http://localhost:8000`
- **Interactive Swagger Documentation**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

---

### Step 3: Frontend Setup (React + Vite)

Open a **second terminal window** and navigate to the frontend directory:

```powershell
# Navigate to frontend directory
cd important/frontend

# 1. Install Node dependencies
npm install

# 2. Start the local development server
npm run dev
```

The Vite dev server will launch at:
- **Application URL**: `http://localhost:5173/`

---

## Scraping & Source Management

Compust includes administrative tools to onboard, inspect, and scrape career portals safely:

```powershell
# In important/ directory with active .venv:

# 1. Onboard a new company career portal
python -m src.app.cli.onboard --name "Acme Corp" --careers-url "https://acme.com/careers" --country "MA"

# 2. Run diagnostics on a registered target
python -m src.app.scraper.diagnostics --target-id 1

# 3. Execute an ingestion run for pending scrape targets
python -m src.app.scraper.crawler --run-pending
```

---

## Testing & Verification

All backend tests run in isolated environments using in-memory SQLite instances so they execute without requiring external connections:

```powershell
# Run backend pytest suite (from important/ directory)
pytest -v

# Run dedicated AI tailoring disabled verification
pytest important/tests/test_ai_tailoring_disabled.py -v

# Run code style and linting checks
ruff check src tests
```

To validate the frontend:

```powershell
# From important/frontend/
npm run lint    # Oxlint check
npm run build   # TypeScript compiler + Vite production build
```

---

## API Examples

### 1. Health Check
```bash
curl http://localhost:8000/health
```
**Response:**
```json
{
  "status": "healthy",
  "environment": "development"
}
```

### 2. Search Vacancies
```bash
curl "http://localhost:8000/api/v1/jobs?search=Python&remote_type=Remote&limit=5"
```

### 3. Get Resume Recommendations for a Vacancy
```bash
curl -X POST "http://localhost:8000/api/v1/jobs/10/resume-suggestions" \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>"
```
**Response:**
```json
{
  "job_id": 10,
  "job_title": "Senior Cloud Security Engineer",
  "requirements_status": "PARTIAL",
  "already_demonstrated": ["Python", "Linux", "Docker", "AWS"],
  "missing_or_weak": ["Terraform", "Kubernetes"],
  "suggestions": [
    "Highlight experience deploying Kubernetes clusters in production.",
    "Add metrics showing cloud infrastructure cost or latency reductions."
  ],
  "ats_improvements": [
    "Ensure section headers use standard naming ('Professional Experience')."
  ]
}
```

---

## Future Roadmap

The following enhancements are planned for upcoming releases:

- [ ] **AI Resume Studio**: Generative vacancy-specific tailoring with fine-tuned LLM suggestions and side-by-side diff preview.
- [ ] **Automated Background Scheduler Daemon**: Autonomous background service to schedule recurring company scrapes based on cooldown intervals.
- [ ] **Instant Job Alerts**: Real-time vacancy notifications via WhatsApp and Email based on personalized skill preferences.
- [ ] **Live ATS Simulator**: Comprehensive visual breakdown of how third-party ATS parsers score your uploaded documents.
- [ ] **LinkedIn & GitHub One-Click Profile Import**: Seamless portfolio synchronization.

---

## Scraper & Parser Contributor Guide

Compust is designed to be extensible. If a company's career site is not currently parsed correctly, contributors can add or refine support:

1. **Test the Target URL**:
   Use the in-app **Data Supervision ➔ Scraper Test Diagnostic** tool or call `POST /api/v1/admin/scraper/test` to inspect HTTP status, rendering mode, detected platform, and diagnostic errors.
2. **Evaluate Strategy Fit**:
   - If the site uses a known ATS (Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Workday, Teamtailor), update or add a platform adapter in `important/src/app/scraper/platforms/`.
   - If the site is arbitrary HTML, it will flow through our 7-layer Universal Parser (JSON-LD, embedded state, semantic cards, and Job Title Intelligence).
   - If the site is a client-rendered SPA, Playwright headless rendering hydrates the DOM automatically.
3. **Add Deterministic Fixtures & Tests**:
   Save a representative HTML snapshot in `important/tests/fixtures/` and add test coverage in `important/tests/`.
4. **Run Full Verification**:
   Ensure all 204+ backend tests and frontend checks pass cleanly before submitting a Pull Request.

---

## Contributing & Community

Contributions are warmly welcome! Whether you are submitting a new career portal adapter, fixing a parser edge case, improving the match engine, or refining the UI:
1. Fork and clone the repository: `https://github.com/putbullet/compust`
2. Follow the detailed developer guidelines inside the in-app **Guide & Docs** center.
3. Keep changes modular, well-tested, and clean.
4. Note: Contribution is completely optional—you are free to use Compust simply as a user or build private custom solutions.

---

## License


Compust is distributed under the MIT License. See [LICENSE](LICENSE) for details.
