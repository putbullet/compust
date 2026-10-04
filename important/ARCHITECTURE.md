# Compust Architecture

The backend follows an incremental, clean flow:

```text
FastAPI route
  -> Dependency injection (DB session, auth, rate limiting)
  -> Scraper / Repository / Service layer
  -> SQLAlchemy ORM models
  -> MySQL 8.0+ compust database
```

---

## Authentication Design (Addendum Section E / Phase 9)

Before implementing user accounts and private profile operations, the following architectural decisions govern authentication:

### 1. Session Mechanism: Stateless JWT
- **Chosen Mechanism**: Stateless JSON Web Tokens (JWT).
- **Transport**: Stored in an `HttpOnly`, `SameSite=Lax`, `Secure` cookie for browser-based clients to prevent JavaScript access (mitigating XSS theft). API clients may alternatively supply the token via the `Authorization: Bearer <token>` header.
- Only one session model is built; server-side session cookies are not duplicated.

### 2. Token Lifecycles & Rotation
- **Access Token**: Short-lived (15 minutes). Contains standard claims: `sub` (user ID), `email`, `exp`, `iat`.
- **Refresh Token**: Longer-lived (7 days). Stored hashed (SHA-256) in a `user_refresh_tokens` table when auth is implemented, supporting:
  - Single-use refresh rotation (each refresh issues a new pair and invalidates the prior refresh token);
  - Immediate global revocation (e.g. "log out of all devices");
  - Automatic expiry without server state explosion.

### 3. Password Hashing Algorithm
- **Algorithm**: `Argon2id` via `argon2-cffi` (OWASP recommended password hashing algorithm) or `bcrypt` (work factor 12).
- Plaintext passwords and hand-rolled hashing schemes are strictly prohibited.
- Passwords must meet minimum length requirements (>= 8 characters) before hashing.

### 4. Account Lifecycle & Failure Degradation
- **Account Fields**: `users.email_verified` (BOOLEAN, default FALSE) and `users.is_active` (BOOLEAN, default TRUE).
- **Graceful Degradation**:
  - Unverified users may log in and browse public/saved jobs, but profile export or sensitive notifications require verified email.
  - Password reset links use a cryptographically secure token with a 1-hour expiration.
  - Non-revealing error responses: Login and password-reset endpoints return generic status messages ("Invalid credentials" or "If an account exists, a reset link was sent") to prevent user enumeration.
  - Users must never be locked out silently: accounts flagged inactive or under cooldown receive explicit guidance on recovery.

### 5. Dedicated Rate Limiting
- **Targeted Endpoints**: `/api/v1/auth/login`, `/api/v1/auth/register`, and `/api/v1/auth/forgot-password`.
- **Thresholds**:
  - Login: 5 attempts per 5-minute window per IP + account identifier.
  - Registration: 3 creations per hour per IP.
- Operates independently from general API rate limiting to thwart credential-stuffing and brute-force attacks.

---

## Scraper & Ingestion Security

- **Robots.txt Compliance**: Domains are verified against robots.txt before any scraping or inspection. Disallowed targets are assigned status `SOURCE_DISALLOWED` and blocked from crawling.
- **HTML Sanitization**: All incoming free-text and job descriptions pass through `bleach` and `BeautifulSoup` to strip executable scripts, frames, and event handlers before hitting MySQL.
- **Deduplication**: Jobs are idempotently upserted based on `(company_id, external_job_id)` with fallback to `(company_id, canonical_url)`.

---

## Company & Source Onboarding (Addendum Section G)

- **Onboarding Interface**: Available via CLI (`python -m src.app.cli.onboard`) and admin API (`POST /api/v1/admin/onboard`).
- **Heuristic Portal Classifier**: Automatically analyzes candidate career URLs and inspects DOM structure:
  - Detects ATS vendor signatures (Workday, SmartRecruiters, Greenhouse, Taleo, TurboStream/Hotwire, direct JSON API, or standard server-rendered HTML).
  - Infers pagination patterns (`rel_next`, `page_param`, `offset_limit`, `show_more_button`, `single_page`).
  - Enforces upfront `robots.txt` compliance verification before registering targets into the scraping schedule.

---

## Tooling, Environment & CI (Addendum Section H)

- **Version Pinning**: Python runtime pinned via `.python-version` (`3.14.2`); Node environment pinned in `frontend/package.json` (`node >=20.0.0`).
- **Continuous Integration**: GitHub Actions workflow (`.github/workflows/ci.yml`) runs Pytest backend test suite with Ruff linting, and validates frontend TypeScript compilation and production bundle build on every push and PR.
- **Git Hooks**: Pre-commit hooks (`.pre-commit-config.yaml`) enforce formatting, trailing whitespace cleanup, and Ruff checks across all commits.
- **CORS Policies**: Environment-driven CORS origin configuration (`COMPUST_CORS_ALLOWED_ORIGINS`) prevents open wildcards in production while allowing local Vite development.

---

## Observability & Structured Logging (Addendum Section I)

- **System Health**: `/health` endpoint validates live MySQL database connectivity and measures query round-trip latency in milliseconds (`latency_ms`).
- **Structured JSON Logging**: Standard library logging formatted into JSON (`src/app/logging.py`) with fields `timestamp`, `level`, `logger`, `message`, and `event`.
- **Trace Context**: Scraper executions use Python `contextvars` (`ScrapingRunScope`) to automatically tag all nested operations with `scraping_run_id`, `company_id`, and `target_id`.

---

## Internationalization: UI Chrome vs. Content (Addendum Section J)

- **UI Chrome Layer**: Handled in React frontend via `LanguageContext` and `useTranslation` (`frontend/src/i18n.ts`). Provides seamless switching between English (`en`) and French (`fr`) for all UI labels, navigation tooltips, search inputs, modal titles, and empty states.
- **Job Content Layer**: Job vacancies preserve original scraped employer text. Future machine translation modules operate independently on `job.description` without coupling to or mutating the frontend UI chrome dictionary.

---

## AI Mock Technical Interview & Skills Assessment

The AI Mock Interview module enables realistic, spoken, turn-based technical interviews grounded in Compust's existing question bank, paired with post-interview evaluation and targeted study plans.

### 1. Hard Architectural Separation: Deterministic Logic vs. LLM Reasoning
- **Deterministic Engine (`src/app/services/mock_interview_engine.py`)**:
  - Zero LLM calls, zero I/O, zero database queries.
  - Computes time budget in seconds (`duration_minutes * 60`).
  - Proportional subdomain allocation with floor=1 guarantee (small categories are not starved; large categories receive proportional representation).
  - Shuffles questions without replacement; respects spaced-repetition history.
  - Dynamically trims question queue based on actual elapsed time.
  - Enforces strict follow-up bounds: max 1 follow-up per primary question, max 3 follow-ups per session total, no follow-ups if time remaining is below budget threshold.
- **AI Reasoning Layer (`src/app/services/mock_interview_ai.py`)**:
  - **In-Interview Path**: Exactly one lightweight, low-token Ollama classification per primary answer (`classify_follow_up`) to determine if a follow-up is warranted. Never blocks conversation; fallback to standard question on timeout/failure. Usable on modest local hardware (~0.8B models).
  - **Post-Interview Path**: Background batch evaluation (`evaluate_answer`) across 5 dimensions (correctness, completeness, relevance, technical depth, clarity), identifying missing concepts and strengths. Evaluates semantic correctness against rubrics, never penalizing different phrasing or syntactic variance.
  - **Skill Matrix & Recommendations**: Deterministic rollup of scores by category (no hallucinated overall ratings).

### 2. Turn-Based Voice Transport & Local Processing
- **STT (Speech-to-Text)**: Local `faster-whisper` (`tiny` INT8 model by default on CPU). Audio recorded via browser `MediaRecorder` API and transmitted as a single chunk per turn.
- **Privacy Posture**: Raw audio is written to a temporary memory file, transcribed, and deleted immediately. No raw audio is ever persisted in database or files. Disclosed transparently to the user on the pre-interview permission screen.
- **TTS (Text-to-Speech)**: Client-side browser-native `SpeechSynthesis` API. Zero server overhead, zero privacy exposure, instant playback.
- **Swappability**: STT (`mock_interview_stt.py`), TTS, and the transport layer are decoupled behind standard interfaces. Upgrading to streaming audio (e.g. Pipecat) or local Piper TTS requires modifying only the transport adapter without changing the interview engine or assessment logic.

### 3. Persistence & Relational Schema (`src/app/models_mock_interview.py`)
- `MockInterviewSession`: Tracks state machine, duration, configuration, and JSON serialized `interview_plan`.
- `MockInterviewTurn`: Records turn index, question reference (points to existing static JSON question bank by string ID — no duplicated content), transcript text, STT confidence, and follow-up flags.
- `MockAnswerEvaluation`: Detailed 5-dimension rubric scores, missing concepts, incorrect claims, and better answer guidance.
- `MockInterviewAssessment`: Aggregated score, category skill matrix, weak areas, and targeted recommendations.
- `MockQuestionRubric`: Caches extracted key concepts and evaluation criteria per question to avoid regeneration.

### 4. Practice Disclaimer
All assessment screens and scoring outputs display a mandatory notice: *"This is an AI-generated practice assessment only. It does not predict real interview outcomes or hiring decisions."*


