/**
 * Context-Menu Flow Regression Suite
 *
 * Covers requirements specifically tied to the context-menu activation path:
 *  1. Zero-database-write status pill displayed after ephemeral analysis
 *  2. Fresh extraction each invocation — onCapture() is not cached between calls
 *  3. Auth-error handling shows inline login form, not a crash or blank panel
 *  4. Save-error renders inline in the panel, NOT via window.alert() (CSP-safe)
 *  5. Progress-stage loading UI (not bare spinner) is present during analysis
 *  6. Stale generation results are discarded
 *  7. Graceful no-job-content error message
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';
import { CompustOverlay } from '../../src/content/common/overlay';
import type { EphemeralAnalyzeResult, JobPayload } from '../../src/lib/types';

// ---- Shared test fixtures ------------------------------------------------

const MOCK_EPHEMERAL_RESULT: EphemeralAnalyzeResult = {
  title: 'Senior TypeScript Engineer',
  company: 'Acme Corp',
  location: 'Remote',
  url: 'https://jobs.acme.com/ts-engineer',
  has_active_resume: true,
  message: null,
  match_score: 78,
  positive_factors: ['TypeScript', 'React'],
  missing_factors: ['GraphQL'],
  demonstrated_skills: ['TypeScript', 'React', 'Node.js'],
  missing_skills: ['GraphQL'],
  resume_suggestions: [
    {
      id: 'sugg-1',
      section: 'skills',
      item_label: 'GraphQL',
      action: 'add',
      where: 'Skills section',
      suggested_text: 'GraphQL',
      reason: 'Required by job description.',
      grounded: false,
    },
  ],
  visa_analysis: null,
  content_hash: 'abc123hashvalue',
};

const MOCK_PAYLOAD: JobPayload = {
  title: 'Senior TypeScript Engineer',
  company: 'Acme Corp',
  location: 'Remote',
  description: 'We need TypeScript and React skills.',
  url: 'https://jobs.acme.com/ts-engineer',
  source: 'extension:generic',
};

// ---- beforeEach: fresh JSDOM per test ------------------------------------

function setupDom() {
  const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
    url: 'https://careers.generic-company.com/jobs/engineer-123',
  });
  (global as any).document = dom.window.document;
  (global as any).window = dom.window;
  (global as any).HTMLElement = dom.window.HTMLElement;
  (global as any).MutationObserver = dom.window.MutationObserver;
}

// ---- Test Suite ----------------------------------------------------------

describe('Context-Menu Flow — Regression Suite', () => {
  beforeEach(() => {
    setupDom();
  });

  // 1. ZERO-PERSIST: status pill shows "0 Database Writes" after ephemeral analysis
  it('showEphemeralResult renders "0 Database Writes" status pill — zero-persist indicator', () => {
    const overlay = new CompustOverlay({
      onCapture: async () => {},
      onRetry: () => {},
    });

    const root = document.getElementById('compust-capture-root');
    expect(root).not.toBeNull();
    const shadow = root!.shadowRoot!;

    const gen = overlay.getGeneration();
    overlay.showEphemeralResult(MOCK_EPHEMERAL_RESULT, MOCK_PAYLOAD, gen);

    const pill = shadow.querySelector('.compust-status-pill');
    expect(pill).not.toBeNull();
    expect(pill!.textContent).toContain('0 Database Writes');
    expect(pill!.textContent).toContain('Analysis Preview');
  });

  // 2. FRESH EXTRACTION: onCapture is called fresh each invocation
  it('each context-menu trigger calls onCapture fresh — no stale result reuse', async () => {
    let captureCallCount = 0;
    const overlay = new CompustOverlay({
      onCapture: async () => {
        captureCallCount++;
      },
      onRetry: () => {},
    });

    // Simulate context-menu click #1 — toggle opens (calls onCapture)
    overlay.toggle();
    expect(captureCallCount).toBe(1);

    // Close panel
    overlay.hidePanel();

    // Simulate context-menu click #2 — toggle re-opens (calls onCapture again)
    overlay.toggle();
    expect(captureCallCount).toBe(2);
  });

  // 3. AUTH ERROR: not-logged-in case shows inline login form, not a crash
  it('showError with NOT_LOGGED_IN renders inline login form inside shadow DOM', () => {
    const overlay = new CompustOverlay({
      onCapture: async () => {},
      onRetry: () => {},
    });

    const root = document.getElementById('compust-capture-root');
    const shadow = root!.shadowRoot!;

    const gen = overlay.getGeneration();
    overlay.showError('NOT_LOGGED_IN', true, false, gen);

    const panel = shadow.querySelector('.compust-panel');
    expect(panel).not.toBeNull();

    const loginForm = shadow.querySelector('#compust-inline-login-form');
    expect(loginForm).not.toBeNull();

    const emailInput = shadow.querySelector('#compust-inline-email');
    expect(emailInput).not.toBeNull();

    const authAlert = shadow.querySelector('.compust-alert-box');
    expect(authAlert).not.toBeNull();
    expect(authAlert!.textContent).toContain('Authentication Required');
  });

  // 4. SAVE ERROR: no window.alert() — error renders inline in actions area
  it('save failure renders inline error banner — NOT window.alert()', async () => {
    const alertSpy = vi.fn();
    (global as any).alert = alertSpy;

    const saveError = new Error('Network request failed during job save');

    const overlay = new CompustOverlay({
      onCapture: async () => {},
      onSaveAction: async () => {
        throw saveError;
      },
      onRetry: () => {},
    });

    const root = document.getElementById('compust-capture-root');
    const shadow = root!.shadowRoot!;

    const gen = overlay.getGeneration();
    overlay.showEphemeralResult(MOCK_EPHEMERAL_RESULT, MOCK_PAYLOAD, gen);

    const addBtn = shadow.querySelector('#compust-action-add') as HTMLButtonElement;
    expect(addBtn).not.toBeNull();
    addBtn.click();

    // Wait for async save to fail
    await new Promise((r) => setTimeout(r, 100));

    // CRITICAL: alert must NOT have been called
    expect(alertSpy).not.toHaveBeenCalled();

    // Error appears inline in the actions area
    const actions = shadow.querySelector('.compust-actions');
    expect(actions).not.toBeNull();
    const errBanner = actions!.querySelector('.compust-alert-box');
    expect(errBanner).not.toBeNull();
    expect(errBanner!.textContent).toContain('Save failed');
    expect(errBanner!.textContent).toContain('Network request failed during job save');
  });

  // 5. PROGRESS STAGES: loading state shows stage list
  it('showLoading renders stage-by-stage progress list — not a bare spinner', () => {
    const overlay = new CompustOverlay({
      onCapture: async () => {},
      onRetry: () => {},
    });

    const root = document.getElementById('compust-capture-root');
    const shadow = root!.shadowRoot!;

    const gen = overlay.getGeneration();
    overlay.showLoading(gen);

    const stageList = shadow.querySelector('.compust-stage-list');
    expect(stageList).not.toBeNull();

    const stageItems = shadow.querySelectorAll('.compust-stage-item');
    expect(stageItems.length).toBeGreaterThanOrEqual(4);

    const activeStage = shadow.querySelector('.compust-stage-active');
    expect(activeStage).not.toBeNull();
  });

  // 6. STALE GENERATION: prior context-menu result is discarded
  it('stale ephemeral result from prior context-menu activation is discarded after generation bump', () => {
    const overlay = new CompustOverlay({
      onCapture: async () => {},
      onRetry: () => {},
    });

    const root = document.getElementById('compust-capture-root');
    const shadow = root!.shadowRoot!;

    const gen0 = overlay.getGeneration();
    overlay.showLoading(gen0);

    overlay.bumpGeneration();
    expect(overlay.getGeneration()).toBe(1);

    overlay.showEphemeralResult(MOCK_EPHEMERAL_RESULT, MOCK_PAYLOAD, gen0);

    expect(shadow.querySelector('.compust-job-title')).toBeNull();
    expect(shadow.querySelector('.compust-status-pill')).toBeNull();
  });

  // 7. GRACEFUL NO-JOB-CONTENT error is readable
  it('showError on page with no job content renders a readable user-facing message', () => {
    const overlay = new CompustOverlay({
      onCapture: async () => {},
      onRetry: () => {},
    });

    const root = document.getElementById('compust-capture-root');
    const shadow = root!.shadowRoot!;

    const gen = overlay.getGeneration();
    overlay.showError(
      'Could not detect a job posting on this page. Please make sure you are viewing an active job listing.',
      false,
      false,
      gen
    );

    const alertBox = shadow.querySelector('.compust-alert-box');
    expect(alertBox).not.toBeNull();
    expect(alertBox!.textContent).toContain('job posting');
    expect(alertBox!.innerHTML).not.toContain('[object Object]');
  });
});
