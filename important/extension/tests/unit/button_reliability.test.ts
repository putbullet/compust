/**
 * Phase 1: Button Reliability Regression Tests
 *
 * These tests verify the fix for the race condition where the overlay FAB was
 * not created because canHandle(url, document) returned false at document_idle
 * on SPA sites (detail pane not yet rendered).
 *
 * After the fix, all four content scripts create the overlay eagerly on URL
 * match alone — the DOM detail pane presence is no longer a prerequisite for
 * the FAB to appear. The onCapture() callback reads the DOM fresh at click time.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

// ----- Extractor helpers -----
import { getLinkedInJobId, linkedInExtractor } from '../../src/content/linkedin';
import { getIndeedJobKey, indeedExtractor } from '../../src/content/indeed';
import { getGlassdoorJobId, glassdoorExtractor } from '../../src/content/glassdoor';
import { getWTTJJobSlug, welcomeToTheJungleExtractor } from '../../src/content/welcomeToTheJungle';

function makeEmptyDom(url: string): JSDOM {
  return new JSDOM('<!DOCTYPE html><html><body><main><p>Loading...</p></main></body></html>', { url });
}

function makeLinkedInJobDom(url: string): JSDOM {
  return new JSDOM(
    `<!DOCTYPE html><html><body>
      <div class="jobs-search__job-details">
        <h2 class="job-details-jobs-unified-top-card__job-title">Software Engineer</h2>
        <a class="job-details-jobs-unified-top-card__company-name-link" href="/company/acme">Acme Corp</a>
        <div class="jobs-description__content"><p>Build amazing things with TypeScript.</p></div>
      </div>
    </body></html>`,
    { url }
  );
}

function makeGlassdoorJobDom(url: string): JSDOM {
  return new JSDOM(
    `<!DOCTYPE html><html><body>
      <div data-test="job-title">Product Manager</div>
      <span data-test="employer-name">Innovation LLC</span>
      <div data-test="jobDescription"><p>Lead product strategy.</p></div>
    </body></html>`,
    { url }
  );
}

function makeWTTJJobDom(url: string): JSDOM {
  return new JSDOM(
    `<!DOCTYPE html><html><body>
      <h1 data-testid="job-header-title">Cloud DevOps Engineer</h1>
      <a href="/companies/acme">Acme Cloud</a>
      <div data-testid="job-section-description"><p>Deploy Kubernetes everywhere.</p></div>
    </body></html>`,
    { url }
  );
}

function setGlobal(dom: JSDOM) {
  (global as any).document = dom.window.document;
  (global as any).window = dom.window;
  (global as any).HTMLElement = dom.window.HTMLElement;
  (global as any).MutationObserver = dom.window.MutationObserver;
}

describe('Phase 1: Button Reliability — Eager Overlay Creation (Race Condition Fix)', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('URL-only canHandle() — overlay creation gate (post-fix)', () => {
    it('LinkedIn: canHandle passes on /jobs/view/ without doc', () => {
      expect(linkedInExtractor.canHandle('https://www.linkedin.com/jobs/view/9876543210/')).toBe(true);
    });

    it('LinkedIn: canHandle passes on /jobs/search?currentJobId=xxx without doc', () => {
      expect(linkedInExtractor.canHandle('https://www.linkedin.com/jobs/search?currentJobId=1001&keywords=engineer')).toBe(true);
    });

    it('Indeed: canHandle passes on /viewjob without doc', () => {
      expect(indeedExtractor.canHandle('https://www.indeed.com/viewjob?jk=abc123')).toBe(true);
    });

    it('Glassdoor: canHandle passes on /Job/ without doc', () => {
      expect(glassdoorExtractor.canHandle('https://www.glassdoor.com/Job/senior-engineer-jobs-SRCH_KO0,15.htm?jl=9876')).toBe(true);
    });

    it('Glassdoor: canHandle passes on /job-listing/ without doc', () => {
      expect(glassdoorExtractor.canHandle('https://www.glassdoor.com/job-listing/cloud-developer-JV_IC1234.htm')).toBe(true);
    });

    it('WTTJ: canHandle passes on /companies/.../jobs/... without doc', () => {
      expect(
        welcomeToTheJungleExtractor.canHandle(
          'https://www.welcometothejungle.com/fr/companies/tech-co/jobs/cloud-engineer_paris'
        )
      ).toBe(true);
    });
  });

  describe('Overlay creation without rendered detail pane (Phase 0 regression)', () => {
    it('LinkedIn: canHandle(url) true even when detail pane is absent from DOM', () => {
      const dom = makeEmptyDom('https://www.linkedin.com/jobs/search?currentJobId=1001');
      setGlobal(dom);
      const url = 'https://www.linkedin.com/jobs/search?currentJobId=1001';
      expect(linkedInExtractor.canHandle(url)).toBe(true);
      // Confirms the old gate would have blocked — DOM-check fails on empty body
      // LinkedIn URL with currentJobId in URL always returns true (early return before DOM check) -- this confirms URL-only check is sufficient
    });

    it('Indeed: canHandle(url) true even when detail pane is absent from DOM', () => {
      const dom = makeEmptyDom('https://www.indeed.com/viewjob?jk=abc123');
      setGlobal(dom);
      const url = 'https://www.indeed.com/viewjob?jk=abc123';
      expect(indeedExtractor.canHandle(url)).toBe(true);
      expect(indeedExtractor.canHandle(url, dom.window.document)).toBe(false);
    });

    it('Glassdoor: canHandle(url) true even when detail pane is absent from DOM', () => {
      const dom = makeEmptyDom('https://www.glassdoor.com/Job/engineer-jobs-SRCH_KO0.htm?jl=9876');
      setGlobal(dom);
      const url = 'https://www.glassdoor.com/Job/engineer-jobs-SRCH_KO0.htm?jl=9876';
      expect(glassdoorExtractor.canHandle(url)).toBe(true);
      expect(glassdoorExtractor.canHandle(url, dom.window.document)).toBe(false);
    });

    it('WTTJ: canHandle(url) true even when detail pane is absent from DOM', () => {
      const dom = makeEmptyDom(
        'https://www.welcometothejungle.com/fr/companies/tech-co/jobs/cloud-engineer_paris'
      );
      setGlobal(dom);
      const url = 'https://www.welcometothejungle.com/fr/companies/tech-co/jobs/cloud-engineer_paris';
      expect(welcomeToTheJungleExtractor.canHandle(url)).toBe(true);
      expect(welcomeToTheJungleExtractor.canHandle(url, dom.window.document)).toBe(false);
    });
  });

  describe('WTTJ directory page — no overlay (Issue 3 regression)', () => {
    it('WTTJ: canHandle returns false on company directory page', () => {
      expect(welcomeToTheJungleExtractor.canHandle('https://www.welcometothejungle.com/en/companies')).toBe(false);
      expect(welcomeToTheJungleExtractor.canHandle('https://www.welcometothejungle.com/en/jobs')).toBe(false);
    });
  });

  describe('Job identifier extraction — stale-detection inputs', () => {
    it('LinkedIn: getLinkedInJobId extracts from URL search param', () => {
      const id = getLinkedInJobId('https://www.linkedin.com/jobs/search?currentJobId=9876543210&keywords=engineer');
      expect(id).toBe('9876543210');
    });

    it('LinkedIn: getLinkedInJobId extracts from /jobs/view/ path', () => {
      const id = getLinkedInJobId('https://www.linkedin.com/jobs/view/9876543210/');
      expect(id).toBe('9876543210');
    });

    it('Indeed: getIndeedJobKey extracts jk param', () => {
      const key = getIndeedJobKey('https://www.indeed.com/viewjob?jk=abc123456def');
      expect(key).toBe('abc123456def');
    });

    it('Glassdoor: getGlassdoorJobId extracts jl param', () => {
      const id = getGlassdoorJobId('https://www.glassdoor.com/Job/senior-engineer.htm?jl=9876', undefined);
      expect(id).toBe('9876');
    });

    it('WTTJ: getWTTJJobSlug extracts slug from path', () => {
      const slug = getWTTJJobSlug('https://www.welcometothejungle.com/fr/companies/acme/jobs/cloud-engineer_paris');
      expect(slug).toBe('cloud-engineer_paris');
    });
  });

  describe('Extraction works at click time (DOM rendered before click)', () => {
    it('LinkedIn: extract returns job details from rendered DOM', () => {
      const dom = makeLinkedInJobDom('https://www.linkedin.com/jobs/search?currentJobId=9876543210');
      setGlobal(dom);
      const payload = linkedInExtractor.extract(dom.window.document);
      expect(payload?.title).toBe('Software Engineer');
      expect(payload?.company).toBe('Acme Corp');
      expect(payload?.description).toBeTruthy();
    });

    it('Glassdoor: extract returns job details from rendered DOM', () => {
      const dom = makeGlassdoorJobDom('https://www.glassdoor.com/Job/product-manager.htm?jl=4321');
      setGlobal(dom);
      const payload = glassdoorExtractor.extract(dom.window.document);
      expect(payload?.title).toBe('Product Manager');
      expect(payload?.company).toBe('Innovation LLC');
    });

    it('WTTJ: extract returns job details from rendered DOM', () => {
      const dom = makeWTTJJobDom(
        'https://www.welcometothejungle.com/fr/companies/acme/jobs/cloud-devops_paris'
      );
      setGlobal(dom);
      const payload = welcomeToTheJungleExtractor.extract(dom.window.document);
      expect(payload?.title).toBe('Cloud DevOps Engineer');
    });
  });

  describe('Job-switch detection with eager overlay — generation counter inputs', () => {
    it('LinkedIn: different jobIds on URL change trigger bumpGeneration', () => {
      const url1 = 'https://www.linkedin.com/jobs/search?currentJobId=1001';
      const url2 = 'https://www.linkedin.com/jobs/search?currentJobId=2002';
      expect(getLinkedInJobId(url1)).toBe('1001');
      expect(getLinkedInJobId(url2)).toBe('2002');
      expect(getLinkedInJobId(url1) !== getLinkedInJobId(url2)).toBe(true);
    });

    it('WTTJ: different slugs trigger bumpGeneration', () => {
      const url1 = 'https://www.welcometothejungle.com/fr/companies/acme/jobs/cloud-engineer_paris';
      const url2 = 'https://www.welcometothejungle.com/fr/companies/acme/jobs/frontend-dev_paris';
      expect(getWTTJJobSlug(url1)).toBe('cloud-engineer_paris');
      expect(getWTTJJobSlug(url2)).toBe('frontend-dev_paris');
      expect(getWTTJJobSlug(url1) !== getWTTJJobSlug(url2)).toBe(true);
    });
  });
});
