# Database Schema and Migration Guide

## Overview

Compust uses MySQL 8.0+ in production/development and SQLAlchemy 2.0+ for Object Relational Mapping. SQLite in-memory databases are used for fast, isolated test suites.

## Migration System

From Phase 1 onward, all database migrations are versioned, reproducible, and tracked.
Both an idempotent SQL migration runner (`migrations/runner.py`) and **Alembic** (`alembic.ini` and `alembic/`) are configured and maintained in sync.

### Running Migrations

Using the migration runner:
```bash
python -m migrations.runner
```

Using Alembic:
```bash
alembic upgrade head
```

Checking current revision:
```bash
alembic current
```

Generating new migrations:
```bash
alembic revision --autogenerate -m "description_of_change"
```

### Migration History

1. **`001_create_scrape_targets.sql`**: Initial creation of `scrape_targets` table with FK to `companies(id)`.
2. **`002_create_scraping_runs.sql`**: Creation of `scraping_runs` table to record run status (`pending`, `running`, `success`, `failed`, `partial`), job counters, and error messages.
3. **`003_add_scrape_target_cooldown.sql`**: Added `cooldown_until DATETIME NULL` to `scrape_targets` for rate-limit and restriction backoff.
4. **`004_add_salary_compliance_user_fields.sql` (Alembic `d4cdab5fadff`)**:
   - `jobs`: `salary_min`, `salary_max`, `salary_currency`, `salary_period`
   - `user_preferences`: `salary_currency`
   - `scrape_targets`: `robots_txt_allowed`, `robots_txt_checked_at`
   - `users`: `email_verified`, `is_active`
5. **`005_add_scrape_target_provenance_and_indexes.sql` (Alembic `e5efb7c8a123`)**:
   - `jobs`: `scrape_target_id` (INT UNSIGNED, FK to `scrape_targets(id)`)
   - Indexes added:
     - `idx_jobs_company_external (company_id, external_job_id)`
     - `idx_jobs_company_url (company_id, job_url(255))`
     - `idx_jobs_target_seen (scrape_target_id, last_seen_at)`
     - `idx_jobs_active (active)`
6. **`006_create_user_profile_tables.sql` (Alembic `f6a1b2c3d4e5`)**:
   - `user_experience`: (id, user_id, title, company_name, experience_type, start_date, end_date, description)
   - `user_education`: (id, user_id, institution, degree, field_of_study, start_date, end_date, description)
   - `user_languages`: (id, user_id, language, proficiency)
7. **`007_create_user_applications.sql` (Alembic `a7b8c9d0e1f2`)**:
   - `user_applications`: (id, user_id, job_id, status, notes, applied_at, created_at, updated_at)
   - Unique constraint: `uq_user_job (user_id, job_id)`
   - Indexes: `idx_user_applications_user`, `idx_user_applications_status`
8. **`008_create_job_translations.sql` (Alembic `b8c9d0e1f2a3`)**:
   - `job_translations`: (id, job_id, language, title, description, source_language, created_at, updated_at)
   - Decoupled translation architecture preserving original employer text in `jobs` unmodified
   - Unique constraint: `uq_job_translation_lang (job_id, language)`
   - Indexes: `idx_job_translations_job`, `idx_job_translations_lang`

---

## Core Tables and Schemas

### `companies`
- `id` (INT UNSIGNED, PK)
- `name` (VARCHAR(255))
- `website_url` (VARCHAR(500))
- `careers_url` (VARCHAR(500), nullable)
- `active` (BOOLEAN)

### `countries`
- `id` (INT UNSIGNED, PK)
- `name` (VARCHAR(100))
- `code` (CHAR(2), unique ISO 3166-1 alpha-2)

### `company_countries`
- Secondary join table mapping `company_id` to `country_id`.

### `scrape_targets`
- `id` (INT UNSIGNED, PK)
- `company_id` (INT UNSIGNED, FK -> companies.id)
- `url` (VARCHAR(1000))
- `type` (VARCHAR(50))
- `active` (BOOLEAN)
- `last_scraped_at` (DATETIME, nullable)
- `status` (VARCHAR(50), nullable)
- `cooldown_until` (DATETIME, nullable)
- `robots_txt_allowed` (BOOLEAN, nullable)
- `robots_txt_checked_at` (DATETIME, nullable)

### `scraping_runs`
- `id` (INT UNSIGNED, PK)
- `company_id` (INT UNSIGNED, FK -> companies.id)
- `status` (VARCHAR(50): pending, running, success, failed, partial)
- `started_at` (DATETIME)
- `finished_at` (DATETIME, nullable)
- `jobs_found` (INT)
- `jobs_added` (INT)
- `jobs_updated` (INT)
- `error_message` (TEXT, nullable)

### `jobs`
- `id` (INT UNSIGNED, PK)
- `company_id` (INT UNSIGNED, FK -> companies.id)
- `country_id` (INT UNSIGNED, FK -> countries.id)
- `title` (VARCHAR(500))
- `location` (VARCHAR(255), nullable)
- `job_url` (VARCHAR(1000))
- `description` (TEXT, nullable, sanitized HTML)
- `employment_type` (VARCHAR(100), nullable)
- `remote_type` (VARCHAR(100), nullable)
- `department` (VARCHAR(255), nullable)
- `source` (VARCHAR(255), nullable)
- `external_job_id` (VARCHAR(255), nullable)
- `posted_at` (DATETIME, nullable)
- `discovered_at` (DATETIME)
- `last_seen_at` (DATETIME, nullable)
- `active` (BOOLEAN)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)
- `salary_min` (DECIMAL(12,2), nullable)
- `salary_max` (DECIMAL(12,2), nullable)
- `salary_currency` (CHAR(3), nullable, ISO 4217)
- `salary_period` (VARCHAR(20), nullable: 'annual', 'monthly', 'hourly')

### `job_skills`
- `id` (INT UNSIGNED, PK)
- `job_id` (INT UNSIGNED, FK -> jobs.id)
- `skill` (VARCHAR(150))

### `users`
- `id` (INT UNSIGNED, PK)
- `email` (VARCHAR(255), unique)
- `password_hash` (VARCHAR(255))
- `first_name` (VARCHAR(100), nullable)
- `last_name` (VARCHAR(100), nullable)
- `phone` (VARCHAR(50), nullable)
- `date_of_birth` (DATE, nullable)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)
- `email_verified` (BOOLEAN, default FALSE)
- `is_active` (BOOLEAN, default TRUE)

### `user_preferences`
- `id` (INT UNSIGNED, PK)
- `user_id` (INT UNSIGNED, FK -> users.id)
- `preferred_job_type` (VARCHAR(100), nullable)
- `preferred_work_mode` (VARCHAR(100), nullable)
- `preferred_location` (VARCHAR(255), nullable)
- `min_salary` (DECIMAL(12,2), nullable)
- `max_salary` (DECIMAL(12,2), nullable)
- `salary_currency` (CHAR(3), nullable, ISO 4217)

### `user_experience`
- `id` (INT UNSIGNED, PK)
- `user_id` (INT UNSIGNED, FK -> users.id, ON DELETE CASCADE)
- `title` (VARCHAR(255))
- `company_name` (VARCHAR(255))
- `experience_type` (VARCHAR(100), 'professional', 'internship', 'project', 'transferable')
- `start_date` (DATE, nullable)
- `end_date` (DATE, nullable)
- `description` (TEXT, nullable)

### `user_education`
- `id` (INT UNSIGNED, PK)
- `user_id` (INT UNSIGNED, FK -> users.id, ON DELETE CASCADE)
- `institution` (VARCHAR(255))
- `degree` (VARCHAR(255), nullable)
- `field_of_study` (VARCHAR(255), nullable)
- `start_date` (DATE, nullable)
- `end_date` (DATE, nullable)
- `description` (TEXT, nullable)

### `user_languages`
- `id` (INT UNSIGNED, PK)
- `user_id` (INT UNSIGNED, FK -> users.id, ON DELETE CASCADE)
- `language` (VARCHAR(100))
- `proficiency` (VARCHAR(50), 'native', 'fluent', 'intermediate', 'basic')

### `user_applications`
- `id` (INT UNSIGNED, PK)
- `user_id` (INT UNSIGNED, FK -> users.id, ON DELETE CASCADE)
- `job_id` (INT UNSIGNED, FK -> jobs.id, ON DELETE CASCADE)
- `status` (VARCHAR(50), 'saved', 'applied', 'interviewing', 'offer', 'rejected')
- `notes` (TEXT, nullable)
- `applied_at` (DATETIME, nullable)
- `created_at` (DATETIME)
- `updated_at` (DATETIME)
- `CONSTRAINT uq_user_job UNIQUE (user_id, job_id)`

### `job_translations`
- `id` (INT UNSIGNED, PK)
- `job_id` (INT UNSIGNED, FK -> jobs.id, ON DELETE CASCADE)
- `language` (VARCHAR(10), e.g., 'en', 'fr', 'ar')
- `title` (VARCHAR(500))
- `description` (TEXT, nullable)
- `source_language` (VARCHAR(10), default 'auto')
- `created_at` (DATETIME)
- `updated_at` (DATETIME)
- `CONSTRAINT uq_job_translation_lang UNIQUE (job_id, language)`
- `INDEX idx_job_translations_job (job_id)`
- `INDEX idx_job_translations_lang (language)`

