<!--
Before submitting, please review our contribution guidelines:
https://github.com/putbullet/compust/blob/master/CONTRIBUTING.md
-->

## Description

Please provide a concise summary of the changes made, the motivation behind them, and what bug or feature they address.

Fixes #(issue)

---

## Type of Change

Please mark the applicable option(s):
- [ ] **Bug fix** (non-breaking fix for an unexpected behavior or regression)
- [ ] **New feature** (non-breaking enhancement adding functionality)
- [ ] **Scraper / Extension adapter** (support for a new ATS portal or capture target)
- [ ] **Performance & Refactoring** (code structure, query optimization, zero API change)
- [ ] **Documentation & Localization** (updates to guides, README, or translations)

---

## Verification & Testing Checklist

Please confirm that the following verification steps were performed:

- [ ] **Backend Tests**: Added/updated automated tests and confirmed passing with `pytest -v` from `important/`.
- [ ] **Frontend Build**: Verified TypeScript typechecking and bundle build pass cleanly (`npm run build` from `important/frontend/`).
- [ ] **Extension Tests** *(if extension was touched)*: Verified `npm run test:unit` passes from `important/extension/`.
- [ ] **Code Quality & Linting**: Ran `ruff check src tests` (backend) and `npm run lint` (frontend).
- [ ] **Live Manual Verification**: Tested changes live in the running application (e.g., verified multi-stage state transitions, charts, or browser capture end-to-end).
- [ ] **Documentation**: Updated `README.md`, `CONTRIBUTING.md`, or in-app Guide if user-facing behavior changed.

---

## Screenshots / Evidence (Optional)

*If this PR modifies user interfaces, diagrams, or the recruitment pipeline funnel chart, please attach before/after screenshots or terminal evidence demonstrating live correctness.*
