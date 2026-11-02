# Compust v1.0.6 — Official Release Notes

**Release Date:** November 2026  
**Tag:** `v1.0.6`  

---

## 📦 Downloads & Checksums

| Asset | Format | Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| **`Compust-Setup-v1.0.6.exe`** | Windows Inno Setup Installer | 225.26 MB (`236,205,728` bytes) | `a90924c93de93275f9e335b729624da1b1ed1fc0ab8cb5243745442aaa4fd4b5` |
| **`Compust-Windows-Portable-v1.0.6.zip`** | Portable Zero-Install Archive | 84.84 MB (`88,962,389` bytes) | `fd675cfdd0e5b32306fe0a6435c4bfc021f495595c3cb2e4920b849bfb07b18a` |

---

## 🚨 Critical Hotfix: Data Integrity & Schema Reconciliation

This release resolves the critical startup and data detection regression where newly installed or upgraded Compust desktop builds showed `0 active vacancies`, `0 users`, and failed to sign in with generic `503 Service Unavailable` or `OperationalError: no such column: users.email`.

### 1. Root Cause Resolution
- **Self-Healing Schema Reconciler:** Resolved a race condition where table fallback stubs were previously generated with only `(id INTEGER PRIMARY KEY)` when migrations ran ahead of metadata initialization. Schema reconciler now dynamically introspects existing tables and alters/adds missing columns, indexes, and full definitions safely on every startup without data loss.
- **Pre-Migration Safety Backups:** Automated, timestamped SQLite snapshot backups are generated prior to running any schema change, repair, or migration.

### 2. Pre-Login Database Doctor View (`/doctor`)
- **Self-Service Diagnostics:** Users experiencing schema mismatches, corrupt local databases, or connection errors can now access `/doctor` directly before logging in.
- **Automated Health Audit:** Displays live engine dialect, schema sync status, missing columns/tables count, and per-table row counts.
- **One-Click Repair & Rollback:**
  - **Auto-Repair:** Executes live schema reconciliation without losing existing user entries.
  - **Restore Pre-Migration Backup:** One-click rollback to the most recent automatic snapshot.
  - **Switch to SQLite:** Emergency fallback to a clean local SQLite instance if a remote MySQL server is unreachable.

### 3. Multi-Port MySQL Discovery & Resilient DB Engine
- **Multi-Port Port Probing:** Automatically detects running MySQL and MariaDB servers across standard and custom development ports (`3306`, `3307`, `3308`, `3309`) and XAMPP `my.ini` configs.
- **Cryptographic Security (Windows DPAPI):** Database passwords saved in `db_config.json` are encrypted using Windows Data Protection API (DPAPI) via Python `cryptography`, preventing plaintext credential storage on disk.
- **Runtime Dependency Bundling:** Bundled `cryptography` and `cffi` inside the private Python runtime to support MySQL 8 `caching_sha2_password` authentication out of the box.
- **Graceful Fallback:** If the configured MySQL instance is offline, the backend seamlessly falls back to the local SQLite database while displaying a non-blocking UI alert banner with a direct link to the Database Doctor.

### 4. Overhauled Data Supervision Import Wizard & Ledger
- **Dry-Run Simulation Mode:** Allows users to preview import statistics (jobs, companies, applications, contacts) before writing any records to SQLite.
- **Auditable Import Ledger:** Tracks every import batch in a dedicated `import_batches` table with timestamps, source engine, item counts, and status.
- **Safe Undo Import:** Reverts imported records by batch ID while preserving existing native records and pre-creating a rollback backup.
- **Always-Accessible Database Configuration:** Embedded `DatabaseSection` in the Data Supervision view ensures database switching, port scanning, and connection testing are available even when local MySQL services are stopped.

---

## 🧪 Verification & Automated Testing Matrix

- **DB Upgrade Matrix Suite:** 4/4 passed (`test_db_upgrade_matrix.py`):
  - Corrupt 1-column table schema self-healing verification.
  - Windows DPAPI credential encryption round-trip.
  - Dry-run simulation and safe import undo workflow.
  - Migration sequence completeness (001 through 020).
- **Installed Build Verification:** Verified against live installed background daemon on port 8000:
  - Deep health endpoint `/health/deep` confirmed `database: ok`, `migrations: synced`, `schema_synced: true`.
  - Database Doctor `/doctor` UI confirmed healthy state and 0 missing columns.
  - Opportunities UI confirmed active vacancies loaded correctly.
- **Playwright E2E Screenshots:** Captured and verified in light and dark modes:
  - `installed_opportunities_populated.png`
  - `installed_doctor_view.png`
  - `installed_supervision_import_wizard.png`
