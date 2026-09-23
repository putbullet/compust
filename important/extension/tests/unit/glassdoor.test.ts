import { describe, it, expect } from 'vitest';
import { JSDOM } from 'jsdom';
import fs from 'fs';
import path from 'path';
import { GlassdoorExtractor, expandDescriptionIfCollapsed } from '../../src/content/glassdoor';
import { validateJobPayload } from '../../src/content/common/jobExtractor';

describe('GlassdoorExtractor', () => {
  const extractor = new GlassdoorExtractor();
  const fixturePath = path.resolve(__dirname, '../fixtures/glassdoor-job.html');
  const liveFixturePath = path.resolve(__dirname, '../fixtures/glassdoor-live-job.html');
  const jsonLdPath = path.resolve(__dirname, '../fixtures/glassdoor-jsonld-job.html');
  const missingFixturePath = path.resolve(__dirname, '../fixtures/glassdoor-missing.html');

  it('correctly identifies Glassdoor job URLs and checks DOM presence via canHandle', () => {
    expect(extractor.canHandle('https://www.glassdoor.com/Job/san-francisco-engineer-jobs-SRCH_IL.0,13.htm')).toBe(true);
    expect(extractor.canHandle('https://www.glassdoor.com/job-listing/senior-developer-JV_IC12345.htm')).toBe(true);
    expect(extractor.canHandle('https://www.glassdoor.com/Salaries/index.htm')).toBe(false);

    const validHtml = fs.readFileSync(fixturePath, 'utf-8');
    const validDom = new JSDOM(validHtml, { url: 'https://www.glassdoor.com/job-listing/full-stack-cloud-developer-JV_IC1234.htm' });
    expect(extractor.canHandle('https://www.glassdoor.com/job-listing/full-stack-cloud-developer-JV_IC1234.htm', validDom.window.document)).toBe(true);

    const emptyDom = new JSDOM('<html><body><div class="empty"></div></body></html>', { url: 'https://www.glassdoor.com/Job/empty.htm' });
    expect(extractor.canHandle('https://www.glassdoor.com/Job/empty.htm', emptyDom.window.document)).toBe(false);
  });

  it('extracts all posting fields from realistic Glassdoor DOM fixture', () => {
    const html = fs.readFileSync(fixturePath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.glassdoor.com/job-listing/full-stack-cloud-developer-JV_IC1234.htm' });
    const payload = extractor.extract(dom.window.document);

    expect(payload).not.toBeNull();
    expect(payload?.title).toBe('Full Stack Cloud Developer');
    expect(payload?.company).toBe('Global Cloud Dynamics');
    expect(payload?.location).toBe('Remote');
    expect(payload?.employment_type).toBe('Permanent, Full-time');
    expect(payload?.description).toContain('React, TypeScript, Python, FastAPI, Docker');
    expect(payload?.source).toBe('extension:glassdoor');
    expect(payload?.url).toBe('https://www.glassdoor.com/job-listing/full-stack-cloud-developer-JV_IC1234.htm');
  });

  it('extracts full description, title, and company from real live Glassdoor split-pane fixture (Issue 1 Regression)', () => {
    const html = fs.readFileSync(liveFixturePath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.glassdoor.com/Job/software-developer-jobs-SRCH_KO0,18.htm' });
    const payload = extractor.extract(dom.window.document);

    expect(payload).not.toBeNull();
    expect(payload?.title).toBe('Software Engineer II (REMOTE)');
    expect(payload?.company).toBe('The Home Depot');
    expect(payload?.location).toBe('Austin, TX');
    // Description must be non-empty, reasonably complete, and not truncated
    expect(payload?.description).not.toBeNull();
    expect(payload?.description!.length).toBeGreaterThan(1000);
    expect(payload?.description).toContain('Software Engineer II');
    expect(payload?.description).toContain('Position Purpose');

    const validation = validateJobPayload(payload);
    expect(validation.isValid).toBe(true);
    expect(validation.missingError).toBeUndefined();
  });

  it('expandDescriptionIfCollapsed triggers button click when present', () => {
    const dom = new JSDOM(`
      <html><body>
        <div class="JobDetails_jobDescription">Snippet</div>
        <button class="ShowMoreCTA_showMore">Show more</button>
      </body></html>
    `);
    let clicked = false;
    const btn = dom.window.document.querySelector('button')!;
    btn.onclick = () => { clicked = true; };

    const result = expandDescriptionIfCollapsed(dom.window.document);
    expect(result).toBe(true);
    expect(clicked).toBe(true);
  });

  it('extracts top-level array JSON-LD and cleans trailing employer ratings / star badges', () => {
    const html = fs.readFileSync(jsonLdPath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.glassdoor.com/job-listing/senior-platform-engineer-JV_IC777.htm' });
    const payload = extractor.extract(dom.window.document);

    expect(payload).not.toBeNull();
    expect(payload?.title).toBe('Senior Platform Engineer');
    // Notice rating badge "4.5 ★" is cleaned from employer name:
    expect(payload?.company).toBe('Nexus Systems');
    expect(payload?.location).toBe('Amsterdam');
    expect(payload?.remote_type).toBe('Remote');
    expect(payload?.description).toContain('scale internal developer tooling and Kubernetes clusters');
    expect(payload?.source).toBe('extension:glassdoor');

    const validation = validateJobPayload(payload);
    expect(validation.isValid).toBe(true);
  });

  it('gracefully degrades on missing DOM elements without throwing', () => {
    const html = fs.readFileSync(missingFixturePath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.glassdoor.com/Job/missing.htm' });
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

  it('extracts complete job from JobSpy-adapted Glassdoor GraphQL response fixture', () => {
    const apiFixturePath = path.resolve(__dirname, '../fixtures/glassdoor-api-job.json');
    const apiJson = JSON.parse(fs.readFileSync(apiFixturePath, 'utf-8'));
    const payload = extractor.extractFromApiResponse(apiJson, 'https://www.glassdoor.com/job-listing/j?jl=1009876543');

    expect(payload).not.toBeNull();
    expect(payload?.title).toBe('Staff Cloud Software Engineer');
    expect(payload?.company).toBe('Datadog');
    expect(payload?.location).toBe('Boston, MA');
    expect(payload?.description).toContain('resilient distributed systems using Go, Python, and Kubernetes');
    expect(payload?.source).toBe('extension:glassdoor');
  });

  it('extractAsync attempts GraphQL API and gracefully falls back to DOM if API fails', async () => {
    const html = fs.readFileSync(fixturePath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.glassdoor.com/job-listing/full-stack-cloud-developer-JV_IC1234.htm' });

    // Mock fetch rejection
    const origFetch = globalThis.fetch;
    try {
      globalThis.fetch = () => Promise.reject(new Error('Simulated GraphQL timeout'));
      const fallbackPayload = await extractor.extractAsync(dom.window.document);
      expect(fallbackPayload).not.toBeNull();
      expect(fallbackPayload?.title).toBe('Full Stack Cloud Developer');
      expect(fallbackPayload?.company).toBe('Global Cloud Dynamics');
      expect(fallbackPayload?.description).toContain('React, TypeScript, Python, FastAPI, Docker');
    } finally {
      globalThis.fetch = origFetch;
    }
  });
});

