import { describe, it, expect, beforeEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';
import { CompustOverlay } from '../../src/content/common/overlay';
import { linkedInExtractor } from '../../src/content/linkedin';
import { indeedExtractor } from '../../src/content/indeed';
import { glassdoorExtractor } from '../../src/content/glassdoor';
import { welcomeToTheJungleExtractor } from '../../src/content/welcomeToTheJungle';
import { JobPayload, EphemeralAnalyzeResult } from '../../src/lib/types';

describe('Phase 1: SPA Generation Counter & Navigation Stability', () => {
  let dom: JSDOM;

  beforeEach(() => {
    dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
      url: 'https://www.linkedin.com/jobs/search?currentJobId=1001',
    });
    (global as any).document = dom.window.document;
    (global as any).window = dom.window;
    (global as any).HTMLElement = dom.window.HTMLElement;
    (global as any).MutationObserver = dom.window.MutationObserver;
  });

  it('increments generation counter correctly on each bumpGeneration call', () => {
    const overlay = new CompustOverlay({
      onCapture: async () => {},
      onRetry: () => {},
    });

    expect(overlay.getGeneration()).toBe(0);
    expect(overlay.bumpGeneration()).toBe(1);
    expect(overlay.getGeneration()).toBe(1);
    expect(overlay.isCurrentGeneration(1)).toBe(true);
    expect(overlay.isCurrentGeneration(0)).toBe(false);

    expect(overlay.bumpGeneration()).toBe(2);
    expect(overlay.getGeneration()).toBe(2);
    expect(overlay.isCurrentGeneration(2)).toBe(true);
    expect(overlay.isCurrentGeneration(1)).toBe(false);
  });

  it('discards stale showEphemeralResult when generation has advanced', () => {
    const overlay = new CompustOverlay({
      onCapture: async () => {},
      onRetry: () => {},
    });

    const root = document.getElementById('compust-capture-root');
    expect(root).toBeTruthy();
    const shadow = root!.shadowRoot!;

    // Capture at generation 0
    const gen0 = overlay.getGeneration();
    overlay.showLoading(gen0);

    // User navigates away before result returns -> bumpGeneration
    overlay.bumpGeneration();
    expect(overlay.getGeneration()).toBe(1);

    // Stale result arrives for generation 0
    const staleResult: EphemeralAnalyzeResult = {
      title: 'Stale Old Job',
      company: 'Old Corp',
      has_active_resume: true,
      match_score: 85,
    };
    const stalePayload: JobPayload = {
      title: 'Stale Old Job',
      company: 'Old Corp',
      url: 'https://example.com/stale',
      source: 'test',
    };

    overlay.showEphemeralResult(staleResult, stalePayload, gen0);

    // The shadow DOM should NOT show 'Stale Old Job' because gen0 was discarded!
    const titleEl = shadow.querySelector('.compust-job-title');
    expect(titleEl).toBeNull();

    // Now current result arrives for generation 1
    const freshResult: EphemeralAnalyzeResult = {
      title: 'Fresh Job B',
      company: 'New Corp',
      has_active_resume: true,
      match_score: 95,
    };
    const freshPayload: JobPayload = {
      title: 'Fresh Job B',
      company: 'New Corp',
      url: 'https://example.com/fresh',
      source: 'test',
    };

    overlay.showEphemeralResult(freshResult, freshPayload, 1);
    const freshTitleEl = shadow.querySelector('.compust-job-title');
    expect(freshTitleEl).toBeTruthy();
    expect(freshTitleEl!.textContent).toContain('Fresh Job B');
  });

  it('discards stale showError when generation has changed', () => {
    const overlay = new CompustOverlay({
      onCapture: async () => {},
      onRetry: () => {},
    });

    const root = document.getElementById('compust-capture-root');
    const shadow = root!.shadowRoot!;

    const gen0 = overlay.getGeneration();
    overlay.showLoading(gen0);

    // User navigates to next job
    overlay.bumpGeneration();

    // Stale error arrives for gen0
    overlay.showError('Stale Error Message', false, false, gen0);

    // Stale error should NOT be displayed
    const alertBox = shadow.querySelector('.compust-alert-box');
    expect(alertBox).toBeNull();
  });

  describe('Rapid Navigation A -> B -> Click reads DOM at the moment of click', () => {
    it('LinkedIn: extracts fresh Job B details after rapid switch from Job A', () => {
      // Step 1: Render Job A in DOM
      document.body.innerHTML = `
        <div class="jobs-search__job-details">
          <h1 class="topcard__title">Senior Frontend Engineer (Job A)</h1>
          <a class="topcard__org-name-link">Company Alpha</a>
          <span class="topcard__flavor--bullet">Paris, France</span>
          <div class="show-more-less-html__markup">Job A description with React and TypeScript.</div>
        </div>
      `;

      const payloadA = linkedInExtractor.extract(document);
      expect(payloadA?.title).toBe('Senior Frontend Engineer (Job A)');
      expect(payloadA?.company).toBe('Company Alpha');

      // Step 2: Rapid navigation to Job B (DOM changes immediately in SPA)
      document.body.innerHTML = `
        <div class="jobs-search__job-details">
          <h1 class="topcard__title">Staff Backend Engineer (Job B)</h1>
          <a class="topcard__org-name-link">Company Beta</a>
          <span class="topcard__flavor--bullet">Berlin, Germany</span>
          <div class="show-more-less-html__markup">Job B description with Python and Go.</div>
        </div>
      `;

      // Step 3: Click occurs NOW -> extraction MUST yield Job B
      const payloadB = linkedInExtractor.extract(document);
      expect(payloadB?.title).toBe('Staff Backend Engineer (Job B)');
      expect(payloadB?.company).toBe('Company Beta');
      expect(payloadB?.location).toBe('Berlin, Germany');
      expect(payloadB?.description).toContain('Job B description');
    });

    it('Indeed: extracts fresh Job B details after rapid switch from Job A', () => {
      // Job A in Indeed ViewjobPaneWrapper
      document.body.innerHTML = `
        <div id="jobsearch-ViewjobPaneWrapper">
          <h1 data-testid="jobsearch-JobInfoHeader-title">Data Analyst (Job A)</h1>
          <div data-testid="inlineHeader-companyName">Alpha Analytics</div>
          <div data-testid="inlineHeader-companyLocation">Remote</div>
          <div id="jobDescriptionText">Job A SQL and Tableau description.</div>
        </div>
      `;

      const payloadA = indeedExtractor.extract(document);
      expect(payloadA?.title).toBe('Data Analyst (Job A)');
      expect(payloadA?.company).toBe('Alpha Analytics');

      // Rapid switch to Job B
      document.body.innerHTML = `
        <div id="jobsearch-ViewjobPaneWrapper">
          <h1 data-testid="jobsearch-JobInfoHeader-title">ML Engineer (Job B)</h1>
          <div data-testid="inlineHeader-companyName">Beta AI Lab</div>
          <div data-testid="inlineHeader-companyLocation">New York, NY</div>
          <div id="jobDescriptionText">Job B PyTorch and LLM description.</div>
        </div>
      `;

      // Click happens
      const payloadB = indeedExtractor.extract(document);
      expect(payloadB?.title).toBe('ML Engineer (Job B)');
      expect(payloadB?.company).toBe('Beta AI Lab');
      expect(payloadB?.location).toBe('New York, NY');
      expect(payloadB?.description).toContain('Job B PyTorch');
    });

    it('Glassdoor: extracts fresh Job B details after rapid switch from Job A', () => {
      // Job A
      document.body.innerHTML = `
        <div class="TwoColumnLayout_jobDetailsContainer">
          <h1 data-test="job-title">Product Manager (Job A)</h1>
          <div data-test="employer-name">Alpha Products</div>
          <div id="JobDescriptionContainer">Job A product roadmapping description.</div>
        </div>
      `;

      const payloadA = glassdoorExtractor.extract(document);
      expect(payloadA?.title).toBe('Product Manager (Job A)');
      expect(payloadA?.company).toBe('Alpha Products');

      // Rapid switch to Job B
      document.body.innerHTML = `
        <div class="TwoColumnLayout_jobDetailsContainer">
          <h1 data-test="job-title">Engineering Manager (Job B)</h1>
          <div data-test="employer-name">Beta Cloud</div>
          <div id="JobDescriptionContainer">Job B engineering leadership description.</div>
        </div>
      `;

      // Click happens
      const payloadB = glassdoorExtractor.extract(document);
      expect(payloadB?.title).toBe('Engineering Manager (Job B)');
      expect(payloadB?.company).toBe('Beta Cloud');
      expect(payloadB?.description).toContain('Job B engineering leadership');
    });

    it('Welcome to the Jungle: extracts fresh Job B details after rapid switch from Job A', () => {
      // Job A
      document.body.innerHTML = `
        <main>
          <h1 data-testid="job-title">DevOps Engineer (Job A)</h1>
          <div data-testid="job-company-name">Alpha Cloud S.A.</div>
          <div data-testid="job-location">Paris</div>
          <div data-testid="job-section-description">Job A Kubernetes and Terraform description.</div>
        </main>
      `;

      const payloadA = welcomeToTheJungleExtractor.extract(document);
      expect(payloadA?.title).toBe('DevOps Engineer (Job A)');
      expect(payloadA?.company).toBe('Alpha Cloud S.A.');

      // Rapid switch to Job B
      document.body.innerHTML = `
        <main>
          <h1 data-testid="job-title">Security Architect (Job B)</h1>
          <div data-testid="job-company-name">Beta Sec Ltd</div>
          <div data-testid="job-location">London</div>
          <div data-testid="job-section-description">Job B Cyber security and SOC description.</div>
        </main>
      `;

      // Click happens
      const payloadB = welcomeToTheJungleExtractor.extract(document);
      expect(payloadB?.title).toBe('Security Architect (Job B)');
      expect(payloadB?.company).toBe('Beta Sec Ltd');
      expect(payloadB?.location).toBe('London');
      expect(payloadB?.description).toContain('Job B Cyber security');
    });
  });
});
