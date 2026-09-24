---
name: Bug Report
about: Create a report to help us improve Compust
title: '[BUG] '
labels: ['bug']
assignees: ''
---

### Affected Component

Please select all components involved in this issue:
- [ ] **Web Application** (React UI, Job Cards, Applications Funnel / Pipeline Chart)
- [ ] **FastAPI Backend** (API Endpoints, SQLAlchemy Repositories, Migrations)
- [ ] **Compust Capture Browser Extension** (Overlay, Detection, Content Scripts)
- [ ] **Career Portal Scraper & Parser** (Company Adapter, Universal Parser, Ingestion)
- [ ] **Resume Builder & ATS Engine** (PDF Parsing, WYSIWYG Editor, RenderCV / Typst)
- [ ] **Desktop Launcher** (One-Click Windows Launcher, Service Lifecycle)

---

### Environment Details

- **Operating System**: (e.g., Windows 11, Windows 10, macOS 14, Ubuntu 22.04)
- **Database Engine**:
  - [ ] MySQL 8.0+
  - [ ] Embedded SQLite fallback (`compust_local.db`)
- **Python Version**: (e.g., 3.12, 3.14)
- **Node.js Version**: (e.g., 20.x, 22.x)
- **Ollama / Local LLM**: (e.g., Installed with `qwen3.5:0.8b` / Not installed)

---

### If Browser Extension Related

- **Browser & Version**: (e.g., Google Chrome 122, Microsoft Edge 122, Brave 1.63, Firefox 123)
- **Target Job Board / Site**:
  - [ ] LinkedIn
  - [ ] Indeed
  - [ ] Glassdoor
  - [ ] Welcome to the Jungle
  - [ ] Other Career Portal (please specify URL):
- **Capture Method**:
  - [ ] In-page Floating Capture Button
  - [ ] Universal Context Menu ("Capture Job with Compust")
  - [ ] Keyboard Shortcut

---

### Bug Description

A clear and concise description of what the bug is.

---

### Steps to Reproduce

1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

---

### Expected Behavior

A clear and concise description of what you expected to happen.

---

### Actual Behavior & Screenshots

What actually happened instead. If applicable, add screenshots or GIF recordings to help explain your problem.

---

### Logs & Terminal Output

Paste any relevant terminal output or log entries from `logs/backend.log`, `logs/launcher.log`, or browser developer console:

```text
# Paste error logs here
```

---

### Additional Context

Add any other context about the problem here (e.g. number of applications tracked, specific resume language, filters applied).
