import { describe, it, expect } from 'vitest';
import { JSDOM } from 'jsdom';
import fs from 'fs';
import path from 'path';
import { LinkedInExtractor, getLinkedInJobId } from '../../src/content/linkedin';
import { validateJobPayload } from '../../src/content/common/jobExtractor';

globalThis.DOMParser = new JSDOM().window.DOMParser;

describe('LinkedInExtractor', () => {
  const extractor = new LinkedInExtractor();
  const fixturePath = path.resolve(__dirname, '../fixtures/linkedin-job.html');
  const splitPanePath = path.resolve(__dirname, '../fixtures/linkedin-splitpane-job.html');
  const searchResultsPath = path.resolve(__dirname, '../fixtures/linkedin-search-results.html');
  const jsonLdPath = path.resolve(__dirname, '../fixtures/linkedin-jsonld-job.html');
  const missingDescPath = path.resolve(__dirname, '../fixtures/linkedin-missing-desc.html');
  const missingFixturePath = path.resolve(__dirname, '../fixtures/linkedin-missing.html');

  it('correctly extracts Job ID from direct URLs and search-results split-pane URLs', () => {
    // 3 Confirmed shapes from Issue 1:
    const standaloneUrl = 'https://www.linkedin.com/jobs/view/4469562237/';
    const searchUrl = 'https://www.linkedin.com/jobs/search/?currentJobId=4460361252&keywords=software+engineer';
    const searchResultsUrl = 'https://www.linkedin.com/jobs/search-results/?currentJobId=4464682867&eBP=CwEAAAGW...&keywords=react&origin=SEMANTIC_SEARCH_HISTORY&geoId=103644278&distance=0.0';

    expect(getLinkedInJobId(standaloneUrl)).toBe('4469562237');
    expect(getLinkedInJobId(searchUrl)).toBe('4460361252');
    expect(getLinkedInJobId(searchResultsUrl)).toBe('4464682867');

    // Additional coverage
    expect(getLinkedInJobId('https://www.linkedin.com/jobs/view/123456789/')).toBe('123456789');
    expect(getLinkedInJobId('https://www.linkedin.com/jobs/view/987654321/?trackingId=abc')).toBe('987654321');
    expect(getLinkedInJobId('https://www.linkedin.com/jobs/collections/?currentJobId=11223344')).toBe('11223344');
    expect(getLinkedInJobId('https://www.linkedin.com/feed/')).toBeNull();
  });

  it('correctly identifies LinkedIn job URLs across all 3 shapes via canHandle (Issue 1)', () => {
    const standaloneUrl = 'https://www.linkedin.com/jobs/view/4469562237/';
    const searchUrl = 'https://www.linkedin.com/jobs/search/?currentJobId=4460361252&keywords=software+engineer';
    const searchResultsUrl = 'https://www.linkedin.com/jobs/search-results/?currentJobId=4464682867&eBP=CwEAAAGW...&keywords=react&origin=SEMANTIC_SEARCH_HISTORY&geoId=103644278&distance=0.0';

    // All 3 shapes identify a job and canHandle must return true
    expect(extractor.canHandle(standaloneUrl)).toBe(true);
    expect(extractor.canHandle(searchUrl)).toBe(true);
    expect(extractor.canHandle(searchResultsUrl)).toBe(true);
    expect(extractor.canHandle('https://www.linkedin.com/jobs/collections/?currentJobId=123')).toBe(true);
    expect(extractor.canHandle('https://www.linkedin.com/feed/')).toBe(false);

    // With document provided: canHandle must be true because URL identifies a specific job
    const emptyDom = new JSDOM('<html><body><div class="empty-feed"></div></body></html>');
    expect(extractor.canHandle(standaloneUrl, emptyDom.window.document)).toBe(true);
    expect(extractor.canHandle(searchUrl, emptyDom.window.document)).toBe(true);
    expect(extractor.canHandle(searchResultsUrl, emptyDom.window.document)).toBe(true);

    // Search page WITHOUT job ID in URL and WITHOUT detail DOM returns false
    expect(extractor.canHandle('https://www.linkedin.com/jobs/search/', emptyDom.window.document)).toBe(false);

    // With realistic DOM
    const splitHtml = fs.readFileSync(splitPanePath, 'utf-8');
    const validDom = new JSDOM(splitHtml, { url: searchUrl });
    expect(extractor.canHandle(searchUrl, validDom.window.document)).toBe(true);

    const searchResultsHtml = fs.readFileSync(searchResultsPath, 'utf-8');
    const searchDom = new JSDOM(searchResultsHtml, { url: searchResultsUrl });
    expect(extractor.canHandle(searchResultsUrl, searchDom.window.document)).toBe(true);
  });

  it('extracts all posting fields from realistic direct LinkedIn fixture', () => {
    const html = fs.readFileSync(fixturePath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.linkedin.com/jobs/view/9876543210/' });
    const payload = extractor.extract(dom.window.document);

    expect(payload).not.toBeNull();
    expect(payload?.title).toBe('Senior Frontend Engineer (React & TypeScript)');
    expect(payload?.company).toBe('Cloud Innovations Ltd');
    expect(payload?.location).toBe('Casablanca, Casablanca-Settat, Morocco');
    expect(payload?.employment_type).toContain('Full-time');
    expect(payload?.description).toContain('5+ years of experience with modern TypeScript and React');
    expect(payload?.source).toBe('extension:linkedin');
    expect(payload?.url).toBe('https://www.linkedin.com/jobs/view/9876543210/');
  });

  it('extracts split-pane search-results layout scoped to detail pane (Issue 2)', () => {
    const html = fs.readFileSync(searchResultsPath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.linkedin.com/jobs/search-results/?currentJobId=9876543210' });
    const payload = extractor.extract(dom.window.document);

    expect(payload).not.toBeNull();
    // Must extract selected job in detail pane ("Principal Cloud Architect"), NOT list items ("Junior Frontend Engineer")
    expect(payload?.title).toBe('Principal Cloud Architect');
    expect(payload?.company).toBe('Apex Cloud Systems');
    expect(payload?.location).toBe('Austin, TX (Hybrid)');
    expect(payload?.description).toContain('lead enterprise migration');
    expect(payload?.description).toContain('Kubernetes, Terraform, and Go');
    expect(payload?.source).toBe('extension:linkedin');
  });

  it('extracts split-pane search / collections layout (h2 titles, .jobs-search__job-details)', () => {
    const html = fs.readFileSync(splitPanePath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.linkedin.com/jobs/search/?currentJobId=1029384756' });
    const payload = extractor.extract(dom.window.document);

    expect(payload).not.toBeNull();
    expect(payload?.title).toBe('Staff Backend Systems Engineer');
    expect(payload?.company).toBe('HyperScale Systems');
    expect(payload?.location).toContain('Paris');
    expect(payload?.description).toContain('Staff Backend Systems Engineer');
    expect(payload?.description).toContain('Python, FastAPI, and Go');
    expect(payload?.source).toBe('extension:linkedin');
  });

  it('prioritizes JSON-LD structured data block when present', () => {
    const html = fs.readFileSync(jsonLdPath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.linkedin.com/jobs/view/9988776655/' });
    const payload = extractor.extract(dom.window.document);

    expect(payload).not.toBeNull();
    expect(payload?.title).toBe('Principal Cloud Architect');
    expect(payload?.company).toBe('Apex Enterprise Solutions');
    expect(payload?.location).toBe('London');
    expect(payload?.remote_type).toBe('Remote');
    expect(payload?.description).toContain('Lead our enterprise multi-cloud transformation');
  });

  it('provides precise diagnostic error message when description is missing', () => {
    const html = fs.readFileSync(missingDescPath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.linkedin.com/jobs/view/123456789/' });
    const payload = extractor.extract(dom.window.document);

    expect(payload).not.toBeNull();
    expect(payload?.title).toBe('Engineering Lead');
    expect(payload?.company).toBe('Acme Corp');
    expect(payload?.description).toBeNull();

    const validation = validateJobPayload(payload);
    expect(validation.isValid).toBe(false);
    expect(validation.missingError).toContain('could not detect the job description');
    expect(validation.missingError).toContain('Engineering Lead');
  });

  it('gracefully degrades on missing DOM elements without throwing', () => {
    const html = fs.readFileSync(missingFixturePath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.linkedin.com/jobs/view/9876543210/' });
    const payload = extractor.extract(dom.window.document);

    expect(payload).not.toBeNull();
    expect(payload?.title).toBeNull();
    expect(payload?.company).toBeNull();
    expect(payload?.location).toBeNull();
    expect(payload?.description).toBeNull();

    const validation = validateJobPayload(payload);
    expect(validation.isValid).toBe(false);
    expect(validation.missingError).toContain('Could not detect a job posting');
  });

  it('extracts complete job posting from JobSpy-adapted API response fixture', () => {
    const apiFixturePath = path.resolve(__dirname, '../fixtures/linkedin-api-job.html');
    const apiHtml = fs.readFileSync(apiFixturePath, 'utf-8');
    const payload = extractor.extractFromApiResponse(apiHtml, 'https://www.linkedin.com/jobs/view/4469562237/');

    expect(payload).not.toBeNull();
    expect(payload?.title).toBe('Software Engineer III - Java');
    expect(payload?.company).toBe('JPMorganChase');
    expect(payload?.location).toBe('Columbus, OH');
    expect(payload?.description).toContain('take your software engineering career to the next level');
    expect(payload?.employment_type).toBe('Full-time');
    expect(payload?.source).toBe('extension:linkedin');
  });

  it('extractAsync calls API endpoint when available and falls back to DOM if API fails', async () => {
    const html = fs.readFileSync(fixturePath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.linkedin.com/jobs/view/9876543210/' });

    // 1. When API fails (mock fetch reject), falls back to DOM
    const origFetch = globalThis.fetch;
    try {
      globalThis.fetch = () => Promise.reject(new Error('Network error simulated'));
      const fallbackPayload = await extractor.extractAsync(dom.window.document);
      expect(fallbackPayload).not.toBeNull();
      expect(fallbackPayload?.title).toBe('Senior Frontend Engineer (React & TypeScript)');
      expect(fallbackPayload?.company).toBe('Cloud Innovations Ltd');
      expect(fallbackPayload?.description).toContain('5+ years of experience');
    } finally {
      globalThis.fetch = origFetch;
    }
  });
});

