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

## AI Behavioral & HR Mock Interview & STAR Assessment

The AI Behavioral & HR Mock Interview module enables realistic, spoken, turn-based behavioral interviews grounded in a comprehensive 60+ question bank (EN/FR/NL), paired with deterministic delivery metrics, grounded STAR qualitative assessment, an interactive minute-by-minute timeline chart, and targeted action plans.

### 1. Hard Architectural Separation: Deterministic Logic vs. LLM Reasoning
- **Deterministic Engine (`src/app/services/mock_interview_engine.py`)**:
  - Zero LLM calls for question planning, pacing, or metrics.
  - Duration budget: 5, 10, 15, or 20 minutes (`duration_minutes * 60`).
  - Deterministic competency selection across 16 core behavioral competencies (Introduction, Motivation, Teamwork, Conflict Handling, Leadership, Failure/Mistakes, Pressure/Time Management, Adaptability, Problem Solving, Communication, Feedback, Ethics, Career Goals, Why Hire You, Questions for Interviewer).
  - Target role is optional free text (blank role is a first-class path for general interviews; if provided, weights relevant competencies deterministically).
  - Respects spaced repetition history without repeats in a single session.
  - Natural human greeting and varied question acknowledgments.
  - Enforces strict follow-up bounds: max 1 follow-up probe per question, bounded state machine.
- **Deterministic Delivery Metrics (`src/app/services/interview_metrics.py`)**:
  - Computed purely in code from transcript and timestamps (never hallucinated by LLM):
    - Words Per Minute (WPM)
    - Multilingual filler word detection (EN/FR/NL)
    - Longest silence / pause detection
    - Time-to-first-word
    - "I" vs "We" ownership ratio
- **AI Reasoning Layer (`src/app/services/mock_interview_ai.py`)**:
  - **In-Interview Path**: Evaluates answer completeness to bound follow-up decisions. Never speaks evaluation feedback during live conversation.
  - **Post-Interview Grounded STAR Evaluation**: Structured Ollama calls evaluate Situation, Task, Action, and Result (Present / Partial / Missing), each backed by a verbatim quoted transcript span as evidence.
  - **Stronger Version Generator**: Constructs a stronger framing strictly from candidate-stated facts, using `[placeholders]` for missing details (never fabricating experience).
  - **Fallback Safety**: Fallback heuristic assessment when Ollama is unavailable, ensuring the user always receives a complete report.

### 2. Turn-Based Voice Transport & Local Processing
- **STT (Speech-to-Text)**: Local `faster-whisper` (`tiny` or `base` INT8 model on CPU) via `mock_interview_stt.py`.
- **Privacy Posture**: Microphone audio is processed in memory/temp buffer, transcribed, and discarded immediately. Zero audio files are retained on disk. Transcripts and reports are persisted only in the local database.
- **TTS (Text-to-Speech)**: Local Piper neural TTS on CPU (`mock_interview_tts.py`) and Edge-TTS with natural conversational voices, plus browser-native `SpeechSynthesis` fallback.
- **Visual Presentation**: Lightweight local 2D animated avatar with amplitude-driven mouth movement, natural blinking, and distinct speaking/listening/processing states, alongside a voice-only minimal orb mode.

### 3. Reporting & Timeline Visualization
- **Interactive Minute-by-Minute Timeline Chart**: Displays each interview question plotted across the elapsed interview minutes, height- and color-coded by quality band, with visual markers for long silences (>5s) and extended answers (>2.5m). Clicking any segment auto-scrolls to that question's STAR evidence card.
- **Behavioral Action Plan**: Suggests concrete next steps directly linked to matching sections of the Behavioral HR Prep Center.

### 4. Practice Disclaimer
All assessment screens and reports display a mandatory notice: *"AI-generated practice assessment. Evaluated using local AI against the behavioral interview rubric. This does not predict real-world hiring decisions."*


