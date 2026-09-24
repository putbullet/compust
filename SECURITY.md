# Security Policy

The Compust team takes the security and privacy of our software and user data seriously. This document outlines our supported versions, scope of security considerations, and the procedure for reporting vulnerabilities responsibly.

---

## Supported Versions

Security updates and critical patches are actively applied to the default branch (`master`) and the latest stable release:

| Version / Branch | Supported          | Notes                                     |
| ---------------- | ------------------ | ----------------------------------------- |
| `master`         | :white_check_mark: | Actively supported development branch     |
| `>= 1.0.0`       | :white_check_mark: | Standalone Windows / Portable releases    |
| `< 1.0.0`        | :x:                | Older pre-release and legacy prototypes   |

---

## Security Scope & Threat Model

Compust is a **local-first career intelligence platform**. Understanding the security architecture and boundaries is essential when assessing vulnerabilities:

### 1. Local-First Data Privacy (PII & Resumes)
- **Candidate Data**: Compust processes highly sensitive Personally Identifiable Information (PII), including uploaded resume PDFs, extracted personal contacts, employment records, compensation notes, and interview prep history.
- **Zero Cloud Storage**: All candidate data is persisted locally in the candidate's local MySQL or SQLite database (`compust_local.db`). The backend does not transmit resumes or PII to external cloud servers.
- **Vulnerabilities in Scope**: Insecure local permissions, SQL injection, arbitrary file writes during PDF generation/RenderCV Typst compilation, or unauthorized token extraction.

### 2. Browser Extension Boundary (`Compust Capture`)
- **Execution Context**: The extension runs content scripts across authenticated user browser sessions on supported third-party sites (LinkedIn, Indeed, Glassdoor, Welcome to the Jungle) and arbitrary company career portals.
- **Auth & Tokens**: The extension stores JWT access tokens in `browser.storage.local` to authenticate requests with the local FastAPI backend.
- **CORS & Allowed Origins**: The backend enforces explicit CORS origins (`COMPUST_EXTENSION_ORIGINS`) to prevent arbitrary web pages from querying the local Compust API.
- **Shadow DOM Isolation**: Extractor overlays use isolated Shadow DOM trees to prevent host-page JavaScript from inspecting or hijacking extension state.
- **Vulnerabilities in Scope**: Cross-Site Scripting (XSS) within extension overlays, token leakage to host pages, unauthorized cross-origin requests, or permission escalation.

### 3. Local LLM & AI Ingestion (Ollama)
- **Inference Boundary**: Resume evaluation and ATS recommendations connect strictly to the local Ollama instance (`http://127.0.0.1:11434`).
- **Prompt Injection & Data Leakage**: Prompt inputs must remain local and must not exfiltrate data via unverified outbound calls.

### 4. Career Scraper & Third-Party HTTP Requests
- **Scraper Bounds**: Talks to public employer career portals. Strictly respects `robots.txt`, implements rate limits, and honors WAF boundaries without attempting CAPTCHA bypasses.
- **Vulnerabilities in Scope**: Server-Side Request Forgery (SSRF) via malicious career URLs or remote code execution via untrusted document parsing.

---

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues, discussions, or pull requests.**

To report a vulnerability responsibly:

### Primary Method: GitHub Private Vulnerability Reporting
If enabled on the repository, submit your report confidentially via GitHub Security Advisories:
👉 **[Report a vulnerability](https://github.com/putbullet/compust/security/advisories/new)**

### Alternative Method: Direct Security Contact
If you cannot use GitHub's private vulnerability advisory tool, you may reach out directly to the project maintainers:

<!-- TODO: add security contact email or dedicated private reporting address here -->
**Contact**: `[Security contact to be configured by maintainer - see repository owner @putbullet]`

### What to Include in Your Report
To help us investigate and reproduce the issue quickly, please provide:
1. A clear description of the vulnerability and its potential impact.
2. The affected component (Backend API, Browser Extension, Resume Parser, Scraper, Launcher).
3. Step-by-step instructions or a minimal Proof of Concept (PoC) to reproduce the vulnerability.
4. Any potential mitigations or remediations you have identified.

---

## Coordinated Disclosure Process

Maintainers are committed to handling security vulnerabilities responsibly:

1. **Acknowledgment**: Maintainers will review incoming reports and acknowledge receipt.
   <!-- TODO: Maintainer to confirm response SLA (e.g. within 48 to 72 hours) -->
2. **Investigation & Assessment**: We will assess the severity, verify the proof of concept, and keep you informed of progress.
3. **Patch & Testing**: A fix will be developed and verified across supported environments.
4. **Public Release & Advisory**: A patched release and coordinated security advisory will be published, providing appropriate credit to the reporter (unless you request anonymity).

<!-- TODO: Maintainer to confirm coordinated disclosure timeline (e.g. 90-day standard disclosure window) -->

Thank you for helping keep Compust and its community safe and secure!
