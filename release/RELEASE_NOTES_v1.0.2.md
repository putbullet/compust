# Compust v1.0.2 — Official Release Notes

**Release Date:** October 2026  
**Tag:** `v1.0.2`  
**Commit:** `a9df1e0`

---

## 📦 Downloads & Checksums

| Asset | Format | Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| **`Compust-Setup-v1.0.2.exe`** | Windows Inno Setup Installer | 222.56 MB (`233,368,937` bytes) | `716f12ca2028bc888fdf83235caf145f526c926b9c5b712d7237580c1bf0d70b` |
| **`Compust-Windows-Portable-v1.0.2.zip`** | Portable Zero-Install Archive | 82.12 MB (`86,112,176` bytes) | `84e40eb2182e245d5b3f40c25b5a6af913bcb253acb02e2f809df503b2fe0efe` |

---

## 🚀 Key Improvements & Highlights

### 1. Dual AI Engine & Windows DPAPI Key Encryption
- **Google Gemini Stepped Setup Wizard:** Guided 4-stage configuration wizard (`gemini-3.8-flash` default) with live latency connectivity testing.
- **DPAPI Encryption:** API keys are encrypted at rest using the Windows Data Protection API (`CryptProtectData`), eliminating plaintext secret exposure.
- **Dynamic Hot-Switching:** Instantly switch between local Ollama and Google Gemini across all AI features without restarting the backend or web browser.

### 2. Guided Data Migration & Portable Backup/Restore
- **Auto-Discovery:** Automatically scans for legacy MySQL instances (`127.0.0.1:3306`) and development SQLite databases.
- **Conflict-Free Import:** Safely imports and deduplicates jobs, user applications, companies, contacts, and resumes into `%LOCALAPPDATA%\Compust\data\compust.db`.
- **Portable Backups:** One-click `.zip` export and restore preserving 100% data fidelity.

### 3. Hardened Internships Caching & Offline Fallback
- **Bundled Offline Dataset:** Shipped with `github_internships_seed.json` featuring **4,283** pre-indexed positions (**4,021** active).
- **Sub-100ms Responses:** Resilient multi-tiered cache guarantees instant loading even when external GitHub API rate limits or network dropouts occur.

### 4. Bootstrap Technical Documentation Redesign
- **Clean 3-Column Layout:** Replaced flashy neon styling with Bootstrap-style technical documentation layout.
- **Navigation & Search:** Added collapsible sidebar, sticky table of contents, and quick `/` keyboard search.
- **Monochrome Diagrams:** Dark-mode compatible Mermaid architecture and data model diagrams.

### 5. Network Error Elimination & Stability
- Converted frontend client API calls to relative paths (`/api/v1`), resolving port mismatches between development servers and installed ports.
- Hardened loopback CORS middleware for browser extensions and external origins.
- Re-routed Ollama requests through the unified `AIGateway`.

---

## 🧪 Verification & Automated Testing Matrix

- **Source Hygiene:** 100% passed (0 hardcoded backend ports, 0 "gmail" references, 0 hardcoded secrets).
- **Playwright E2E Suite:** 10/10 passed across Chromium and Firefox testing all core views and wizards.
- **In-Place Upgrade Test:** Verified silent upgrade from installer over existing data with 100% row preservation across all tables (451 jobs, 57 applications, 40 companies, 17 contacts, 1 resume).
