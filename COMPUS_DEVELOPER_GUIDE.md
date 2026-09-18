# Compust — Comprehensive Developer & Architecture Guide
**File**: `COMPUS_DEVELOPER_GUIDE.md`  
**Target Audience**: Software Engineers, System Architects, Content Ingestion Engineers, and Autonomous LLM Coding Agents working directly on the Compust codebase.

---

## 1. Project Overview & Philosophy

**Compust** is an end-to-end, local-first career intelligence and vacancy aggregation platform. It combines automated multi-source career portal ingestion, deterministic resume parsing, vacancy match scoring, interactive gap analysis, and a structured technical & behavioral interview preparation center.

### Core Architectural Principles
1. **Local-First & Privacy Preserving**: User resumes, application pipelines, and AI interactions run entirely locally or on user-controlled infrastructure. No candidate resumes or PII are transmitted to third-party cloud APIs.
2. **Zero-OCR Deterministic Parsing**: PDF parsing extracts text layers natively with 100% fidelity without hallucination or lossy OCR.
3. **Resilient Dual-Mode Database**: Supports production MySQL 8.0+ (via XAMPP or native service) and features automated, transparent fallback to local SQLite (`important/data/compust_local.db`) when MySQL is unreachable.
4. **Non-Technical Windows Distribution**: Packaged as a single-click portable executable archive (`Compust.bat`) requiring zero installation of Python, Node.js, npm, MySQL, XAMPP, or Git.
5. **Anti-Hallucination AI Architecture**: AI-generated suggestions, gap analyses, and interview explanations strictly ground themselves in verified knowledge or candidate data. If Ollama/local LLMs are offline, the system falls back seamlessly to deterministic heuristic rule engines.

---

## 2. Repository Layout & Directory Structure

```
compust/
├── Compust.bat                    # Non-technical single-click launcher for Windows
├── setup_shortcut.bat             # Utility to create desktop shortcut with custom icon
├── COMPUS_DEVELOPER_GUIDE.md      # This authoritative architectural specification
├── README.md                      # Public project documentation & feature overview
├── CHANGELOG.md                   # Chronological version changes and release notes
├── DEVELOPMENT.md                 # Developer onboarding and local setup guide
├── TESTING.md                     # Test execution instructions and test strategy
├── CONFIGURATION.md               # Environment variables and config reference
├── PROGRESS.md                    # Project tracking and feature checklists
├── docs/                          # Architecture diagrams, screenshots, and visual assets
├── logs/                          # Runtime logs for launcher and backend
├── release/                       # Distribution zip archives and build artifacts
│   └── Compust-Windows-Portable-v1.0.0.zip
├── launcher/                      # Python-based multi-process launcher system
│   ├── launcher_core.py           # Process manager, port checker, and dev/prod router
│   ├── run_app.py                 # CLI entry point for launcher
│   └── check_deps.py              # System dependency inspector
└── important/                     # Core application codebase
    ├── alembic/                   # Database schema migrations
    ├── data/                      # Local SQLite database, scraped snapshots, raw data
    ├── scripts/                   # Management, ingestion, and build automation scripts
    │   ├── build_windows_release.py   # Windows portable zip builder
    │   ├── ingest_interview_content.py # Markdown interview ingestion pipeline
    │   └── init_db.py             # Database schema initialization script
    ├── src/
    │   └── app/
    │       ├── main.py            # FastAPI entry point, lifecycle events, CORS, static SPA mount
    │       ├── config.py          # Pydantic Settings management (.env loader)
    │       ├── database.py        # SQLAlchemy engine, session factory, and SQLite fallback
    │       ├── api/               # REST API endpoints (v1 routes)
    │       │   ├── auth.py        # User authentication & JWT issuance
    │       │   ├── jobs.py        # Vacancy querying, filtering, and detail endpoints
    │       │   ├── applications.py# Application tracking Kanban endpoints
    │       │   ├── resume.py      # Resume upload, parsing, and management
    │       │   ├── interview_prep.py # Technical & behavioral interview preparation API
    │       │   ├── admin.py       # Scraper supervisor, system diagnostics, and logs
    │       │   └── vocabulary.py  # Taxonomy, skills, and industry dictionary
    │       ├── cli/               # CLI commands for developer operations
    │       │   └── onboard.py     # Command-line career portal onboarding tool
    │       ├── models/            # SQLAlchemy ORM database models
    │       │   ├── user.py        # User accounts and credentials
    │       │   ├── job.py         # Vacancies, companies, locations, and salary data
    │       │   ├── application.py# Job application pipeline status records
    │       │   ├── resume.py      # Resumes, parsed sections, skills, work experiences
    │       │   ├── interview_prep.py # Interview questions, tracks, and multilingual content
    │       │   └── scraper.py     # Scrape targets, runs, and error audit logs
    │       ├── repositories/      # Database abstraction layer (Data Access Objects)
    │       │   ├── jobs.py
    │       │   ├── applications.py
    │       │   ├── resumes.py
    │       │   └── interview_prep.py
    │       ├── services/          # Core business logic layer
    │       │   ├── resume_parser.py       # PDF extraction and structure profiling
    │       │   ├── resume_matcher.py      # Keyword gap analysis and match scoring
    │       │   ├── resume_ai_tailoring.py # Local Ollama tailoring and cold outreach drafts
    │       │   ├── interview_prep.py      # Interview prep logic & narrative AI explanations
    │       │   └── scraper_supervisor.py  # Scrape job scheduling and orchestrator
    │       └── scraper/           # Web scraping engine
    │           ├── crawler.py     # Multi-worker async crawler with robots.txt enforcement
    │           ├── diagnostics.py # Single-target crawler diagnostic CLI
    │           ├── normalizer.py  # Job posting normalization, deduplication, hashing
    │           ├── universal.py   # 7-layer heuristic HTML/SPA extractor
    │           └── platforms/     # Dedicated ATS adapters (Workday, SmartRecruiters, etc.)
    ├── frontend/                  # React Single Page Application (SPA)
    │   ├── package.json           # Node dependencies and scripts
    │   ├── vite.config.ts         # Vite bundler configuration
    │   ├── tsconfig.json          # TypeScript strict configuration
    │   ├── index.html             # Single page entry HTML
    │   ├── dist/                  # Compiled production static bundle (served by FastAPI)
    │   └── src/
    │       ├── App.tsx            # Main application component, tabs, hero section
    │       ├── main.tsx           # React DOM root render
    │       ├── index.css          # Global design system, typography, resets, theme tokens
    │       ├── components/        # Reusable UI component library
    │       │   ├── SearchBar.tsx          # Real-time search bar with scope-isolated icons
    │       │   ├── FilterBar.tsx          # Multi-facet filtering (Remote, Contract, Salary)
    │       │   ├── JobCard.tsx            # Vacancy preview card
    │       │   ├── JobDetailModal.tsx     # Full vacancy detail and instant gap analysis
    │       │   ├── ApplicationsKanban.tsx # Drag-and-drop recruitment pipeline board
    │       │   ├── ResumeBuilder/         # WYSIWYG Resume Studio and Job Targeting Assistant
    │       │   │   ├── ResumeStudioView.tsx
    │       │   │   ├── ResumeEditor.tsx
    │       │   │   ├── ResumePreview.tsx
    │       │   │   └── JobTargetingAssistant.tsx
    │       │   ├── InterviewPrep/         # Dedicated Interview Preparation Center
    │       │   │   ├── InterviewPrepView.tsx
    │       │   │   ├── InterviewPrepView.css
    │       │   │   ├── QuestionDetailModal.tsx
    │       │   │   └── AIExplanationDrawer.tsx
    │       │   └── GuideDocs/             # Interactive in-app documentation and diagrams
    │       ├── context/           # React Context providers (Auth, Language, Theme)
    │       └── services/          # Frontend HTTP client and API service bindings
    └── tests/                     # Automated pytest verification suite
        ├── test_database_resilience.py  # SQLite fallback and automatic schema initialization tests
        ├── test_interview_prep.py       # Interview prep endpoints & narrative AI tests
        ├── test_interview_prep_ingestion.py # Repository Markdown ingestion tests
        ├── test_resume_matcher.py       # Deterministic keyword scoring tests
        └── ...
```

---

## 3. Database Layer & High-Resilience Connection Strategy

### Dual-Mode Database Architecture
Compust is engineered to operate without requiring technical users to install or start MySQL/XAMPP.

```
+-------------------------------------------------------------+
|                      SQLAlchemy Engine                      |
+-------------------------------------------------------------+
                               |
              [ Pre-Flight TCP Socket Check (port 3306) ]
                               |
            +------------------+------------------+
            | MySQL Reachable                     | MySQL Unreachable / Refused
            v                                     v
+-----------------------+             +-------------------------------+
|  MySQL 8.0 Engine     |             |  Local SQLite Engine          |
|  (compust_db)         |             |  (important/data/compust.db)  |
|  Production Server    |             |  Zero Configuration Fallback  |
+-----------------------+             +-------------------------------+
```

### Connection Resilience (`important/src/app/database.py`)
1. **Pre-flight Socket Probe**: Before opening SQLAlchemy connection pools, a raw socket probe checks if `localhost:3306` (or configured `DB_HOST:DB_PORT`) is actively accepting connections with a 1.0-second timeout.
2. **Transparent Fallback**:
   - If MySQL connects: SQLAlchemy configures MySQL connection pooling (`pool_size=10, max_overflow=20, pool_pre_ping=True`).
   - If MySQL fails/refuses: The engine dynamically switches to SQLite:
     ```python
     sqlite_path = DATA_DIR / "compust_local.db"
     DATABASE_URL = f"sqlite:///{sqlite_path.as_posix()}?check_same_thread=False"
     ```
3. **Automatic Schema Initialization**:
   - `init_database_schema()` is automatically invoked during FastAPI startup (`@asynccontextmanager` in `main.py`).
   - If running on SQLite or an uninitialized MySQL database, `Base.metadata.create_all(bind=engine)` creates all 11 core tables cleanly without blocking user interaction.
4. **Testing Isolation**:
   - Backend unit tests always execute against an in-memory SQLite database (`sqlite:///:memory:`) configured in `tests/conftest.py`. No test ever modifies development or production databases.

---

## 4. Web Application & API Specification

### FastAPI Application Layer (`important/src/app/main.py`)
- **Port**: `8000` (Default)
- **CORS**: Configured to allow `http://localhost:5173` (Vite dev server) and local network origins.
- **Production SPA Serving**: When running in standalone/production mode, FastAPI serves the compiled React application from `important/frontend/dist` via `StaticFiles(directory=dist_dir, html=True)`. A catch-all route ensures React client-side routing works for all deep links.

### Key API Endpoints

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/health` | Server health, database type (mysql/sqlite), and status | No |
| `POST` | `/api/v1/auth/login` | JWT authentication and session token generation | No |
| `POST` | `/api/v1/auth/register` | Create local candidate account | No |
| `GET` | `/api/v1/jobs` | Query vacancies with filtering (title, location, remote, salary) | No |
| `GET` | `/api/v1/jobs/{id}` | Retrieve complete job description and requirements | No |
| `POST` | `/api/v1/jobs/{id}/resume-suggestions` | Compute instant gap analysis against candidate resume | Yes |
| `GET` | `/api/v1/applications` | Retrieve all applications for Kanban tracking | Yes |
| `PUT` | `/api/v1/applications/{id}/status` | Update Kanban column (Applied, Interviewing, Offer, Rejected) | Yes |
| `POST` | `/api/v1/resumes/upload` | Upload and deterministically parse native PDF resume | Yes |
| `GET` | `/api/v1/resumes/active` | Get currently active primary resume and parsed sections | Yes |
| `POST` | `/api/v1/resumes/tailor` | Generate job-targeted resume bullets and cold outreach | Yes |
| `GET` | `/api/v1/interview-prep/tracks` | List all technical and behavioral interview preparation tracks | No |
| `GET` | `/api/v1/interview-prep/questions` | Query curated questions with filters (track, difficulty, language) | No |
| `POST` | `/api/v1/interview-prep/explain` | Generate structured AI narrative explanation with actor scenarios | No |
| `POST` | `/api/v1/admin/scraper/test` | Run immediate single-target crawler diagnostic | Admin |

---

## 5. Interview Prep Module & "Explain with AI" Narrative Engine

### Track Taxonomy & Repository Content
The Interview Prep module provides curated technical and behavioral curriculum ingested from verified high-quality open-source sources:
- **Behavioral Preparation**: STAR method frameworks across 4 languages (English, French, German, Spanish).
- **Data Engineering**: Sourced from Oliver Benner's `data-engineering-interview-questions` (ETL/ELT, distributed streaming, Spark, Kafka, SQL data warehousing).
- **Cybersecurity & Network Defense**: Ingested and structured based on standard industry domains (Phishing, Social Engineering, Ransomware, Botnets, Network Firewalls, Cryptography, Identity/OAuth).
- **AI & Machine Learning Engineering**: Transformers, Attention mechanisms, RAG, AI Agent tool calling, Deep Learning loss functions, Gradient Descent.
- **Frontend & Web Engineering**: Ingested from Nick Scialli's `interview-guide` (DOM internals, Event Loop, Closures, Web Security, Performance).

### Narrative Case Scenario Generator (`important/src/app/services/interview_prep.py`)
When a user clicks **"Explain with AI"**, the system does NOT return generic theoretical definitions. Instead, it generates a structured, multi-section narrative:
1. **Simplified Core Concept**: Plain-English, analogy-driven definition free of unnecessary jargon.
2. **Real-World Narrative Case Scenario**: An explicit, realistic multi-step case study with named actors:
   - *Example*: Alice (customer support agent at a logistics firm) and Bob (an external threat actor crafting a spear-phishing attack via spoofed domain credentials).
   - Shows the exact attack chain or architecture pipeline step-by-step.
   - Shows how standard defenses or best practices detect and neutralize the risk.
3. **Key Technical Insights & Trade-offs**: Specific engineering nuances and evaluation trade-offs.
4. **How to Frame This in an Interview**: Actionable, concise talking points candidate can directly verbalize.

### Fallback Guarantee
If the local Ollama instance is not running or takes longer than 4 seconds to respond, `_build_smart_explanation_fields` deterministically generates the structured narrative case scenario from internal knowledge fixtures.

---

## 6. Resume Studio & Job Targeting Assistant

### WYSIWYG Resume Studio
Located within the candidate Profile view, the Resume Studio provides a live two-column split-view:
- **Left Column**: Live editable resume sections (Summary, Experience, Education, Skills, Projects, Certifications).
- **Right Column**: Real-time PDF-accurate visual preview.

### Job Targeting Assistant
Integrated directly above or alongside the preview, the Job Targeting Assistant allows candidates to select any active vacancy from the database:
- **Deterministic Gap Analysis**: Compares candidate's active resume skills against vacancy requirements.
- **Visual Pill Status**:
  - Green chips (`already_demonstrated`): Proven skills already present in the resume.
  - Amber chips (`missing_or_weak`): Key vacancy requirements missing from the resume.
- **ATS Formatting Advice**: Actionable structural recommendations (standard section headings, bullet length, metrics).
- **Cold Outreach Drafts**: Generates tailored Cold Emails, LinkedIn connection notes, and Cover Letters with editable variable brackets (e.g. `[Hiring Manager Name]`).

---

## 7. Scraper Engine Architecture

### Ethical Crawling Rules
1. **Robots.txt Enforcement**: Every target URL's `robots.txt` is queried and parsed before crawling. Disallowed paths are dropped.
2. **Rate Limiting**: Domain-specific cooldown timers prevent aggressive repeated requests.
3. **No CAPTCHA Bypassing**: Compust respects bot defenses and does not attempt black-hat evasion.

### Universal 7-Layer Ingestion Pipeline
When crawling career sites that do not match dedicated platform adapters (Greenhouse, Workday, SmartRecruiters, Lever, Ashby):
1. **Layer 1: Schema.org / JSON-LD Extraction**: Extracts structured `JobPosting` metadata embedded in the HTML.
2. **Layer 2: Embedded Next.js / Nuxt / Redux State**: Inspects `__NEXT_DATA__` or inline JSON payloads.
3. **Layer 3: Microdata & OpenGraph**: Scrapes structured meta tags (`og:title`, `og:description`).
4. **Layer 4: Semantic Job Card Detection**: Scans DOM nodes using heuristic selectors (`.job-item`, `.career-listing`).
5. **Layer 5: Title Intelligence Filter**: Filters noisy non-job content using natural language classification.
6. **Layer 6: Content Normalization**: Cleans, sanitizes, and normalizes locations, currencies, and job types.
7. **Layer 7: Deduplication Hashing**: Computes SHA-256 hashes of `company_name + normalized_job_title + location` to prevent duplicate listings.

---

## 8. Windows Portable Release & Launcher System

### Launcher Architecture (`launcher/launcher_core.py`)
The Python launcher supports dual-mode operation:
- **Development Mode**: When Node.js and npm are present and `frontend/dist` is not compiled, the launcher spawns FastAPI on port `8000` and Vite on port `5173`.
- **Standalone Production Mode**: When Node.js is absent, the launcher starts FastAPI on port `8000` (which serves the compiled `frontend/dist` SPA directly) and opens `http://localhost:8000` in the user's default browser.

### Building the Release (`important/scripts/build_windows_release.py`)
To build the distribution archive:
```powershell
cd important
.\.venv\Scripts\python.exe scripts\build_windows_release.py
```
This script:
1. Compiles the React frontend using `npm run build` into `important/frontend/dist`.
2. Assembles a clean portable directory tree in `release/Compust-Windows-Portable-v1.0.0`.
3. Copies application source code, assets, and launcher scripts while strictly excluding `.git`, `.venv`, `node_modules`, cached SQLite files (`compust_local.db`), and sensitive local configs.
4. Generates a compressed `.zip` distribution archive with an accompanying SHA-256 integrity hash.

---

## 9. LLM Coding Safety Rules & Developer Constraints

Future AI assistants and developers modifying Compust MUST adhere to these strict rules:

1. **Preserve Database Resilience**: Never make changes that assume MySQL is always running. Any new tables or columns must be defined in SQLAlchemy ORM models (`src/app/models/`) and tested against SQLite.
2. **Protect User Privacy**: Never log, transmit, or expose user resume data, personal details, or auth tokens to external third parties.
3. **Scoped CSS Rule**: Never define un-scoped, global CSS class names (such as `.search-icon`, `.title`, `.card`) that could collide across different views. Always scope styles under parent container class selectors.
4. **Deterministic Testing**: Always verify that backend tests use the in-memory SQLite fixtures. Do not introduce dependencies on external services in the automated test suite.
5. **Console Encoding on Windows**: In Python scripts targeting Windows, avoid unescaped Unicode characters (such as `✓` or `✗`) without explicit UTF-8 stdout configuration, as Windows consoles default to `cp1252` and will raise `UnicodeEncodeError`.
6. **Verify Before Pushing**: Always run `pytest tests/` and `npm run build` before committing and pushing code.

---

*Guide maintained by the Compust Engineering Team. Updated September 2026.*
