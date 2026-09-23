import { describe, it, expect } from 'vitest';
import { JSDOM } from 'jsdom';
import fs from 'fs';
import path from 'path';
import { IndeedExtractor } from '../../src/content/indeed';

describe('IndeedExtractor', () => {
  const extractor = new IndeedExtractor();
  const fixturePath = path.resolve(__dirname, '../fixtures/indeed-job.html');
  const missingFixturePath = path.resolve(__dirname, '../fixtures/indeed-missing.html');

  it('correctly identifies Indeed job URLs', () => {
    expect(extractor.canHandle('https://www.indeed.com/viewjob?jk=1a2b3c')).toBe(true);
    expect(extractor.canHandle('https://www.indeed.com/jobs?q=engineer')).toBe(true);
    expect(extractor.canHandle('https://www.indeed.com/companies')).toBe(false);
  });

  it('extracts all posting fields from realistic Indeed fixture', () => {
    const html = fs.readFileSync(fixturePath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.indeed.com/viewjob?jk=1a2b3c4d5e6f' });
    const payload = extractor.extract(dom.window.document);

    expect(payload).not.toBeNull();
    expect(payload?.title).toBe('Python Backend Engineer (FastAPI & SQLAlchemy)');
    expect(payload?.company).toBe('Apex Software Systems');
    expect(payload?.location).toBe('Paris, Île-de-France, France');
    expect(payload?.employment_type).toBe('Full-time');
    expect(payload?.description).toContain('local-first microservices using Python, FastAPI');
    expect(payload?.source).toBe('extension:indeed');
    expect(payload?.url).toBe('https://www.indeed.com/viewjob?jk=1a2b3c4d5e6f');
  });

  it('gracefully degrades on missing DOM elements without throwing', () => {
    const html = fs.readFileSync(missingFixturePath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.indeed.com/viewjob?jk=missing' });
    const payload = extractor.extract(dom.window.document);

    expect(payload).not.toBeNull();
    expect(payload?.title).toBeNull();
    expect(payload?.company).toBeNull();
    expect(payload?.location).toBeNull();
    expect(payload?.description).toBeNull();
  });

  it('extracts complete job from Indeed GraphQL response fixture', () => {
    const apiFixturePath = path.resolve(__dirname, '../fixtures/indeed-api-job.json');
    const apiJson = JSON.parse(fs.readFileSync(apiFixturePath, 'utf-8'));
    const payload = extractor.extractFromApiResponse(apiJson, 'https://www.indeed.com/viewjob?jk=5e409e577046830a');

    expect(payload).not.toBeNull();
    expect(payload?.title).toBe('Principal Systems Architect');
    expect(payload?.company).toBe('CloudScale Technologies');
    expect(payload?.location).toBe('Austin, TX');
    expect(payload?.description).toContain('enterprise distributed platforms');
    expect(payload?.employment_type).toBe('Full-time');
    expect(payload?.remote_type).toBe('Remote');
    expect(payload?.source).toBe('extension:indeed');
  });

  it('extractAsync attempts GraphQL API and gracefully falls back to DOM if API fails', async () => {
    const html = fs.readFileSync(fixturePath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.indeed.com/viewjob?jk=1a2b3c4d5e6f' });

    // Mock fetch rejection
    const origFetch = globalThis.fetch;
    try {
      globalThis.fetch = () => Promise.reject(new Error('Simulated network failure'));
      const fallbackPayload = await extractor.extractAsync(dom.window.document);
      expect(fallbackPayload).not.toBeNull();
      expect(fallbackPayload?.title).toBe('Python Backend Engineer (FastAPI & SQLAlchemy)');
      expect(fallbackPayload?.company).toBe('Apex Software Systems');
      expect(fallbackPayload?.description).toContain('local-first microservices using Python, FastAPI');
    } finally {
      globalThis.fetch = origFetch;
    }
  });

  it('correctly extracts Job B when user switches cards on a search results page with stale initial JSON-LD', async () => {
    const multiJobHtml = `
      <!DOCTYPE html>
      <html>
        <head>
          <!-- Stale JSON-LD from initial server render for Job A -->
          <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "JobPosting",
              "title": "Stale Job A Title",
              "hiringOrganization": { "@type": "Organization", "name": "Company A" },
              "jobLocation": { "@type": "Place", "address": { "@type": "PostalAddress", "addressLocality": "London" } },
              "description": "Stale Job A Description"
            }
          </script>
        </head>
        <body>
          <!-- Search results list -->
          <div id="mosaic-provider-jobcards">
            <div class="job_seen_beacon" data-jk="job_a_111">
              <h2 class="jobTitle">Stale Job A Title</h2>
            </div>
            <div class="job_seen_beacon" data-jk="job_b_222" aria-selected="true">
              <h2 class="jobTitle">Active Job B Title</h2>
            </div>
          </div>

          <!-- Active detail pane rendered for Job B -->
          <div id="jobsearch-ViewjobPaneWrapper" data-jk="job_b_222">
            <div class="jobsearch-JobInfoHeader-title-container">
              <h1 class="jobsearch-JobInfoHeader-title">Active Job B Title</h1>
            </div>
            <div data-company-name="true">Active Company B</div>
            <div data-testid="inlineHeader-companyLocation">Berlin, Germany</div>
            <div id="jobDescriptionText">
              <p>This is the active job description for Job B that must be extracted.</p>
            </div>
          </div>
        </body>
      </html>
    `;

    const dom = new JSDOM(multiJobHtml, { url: 'https://www.indeed.com/jobs?q=engineer' });
    const payload = extractor.extract(dom.window.document);

    expect(payload).not.toBeNull();
    expect(payload?.title).toBe('Active Job B Title');
    expect(payload?.company).toBe('Active Company B');
    expect(payload?.location).toBe('Berlin, Germany');
    expect(payload?.description).toContain('This is the active job description for Job B');
    expect(payload?.url).toBe('https://www.indeed.com/viewjob?jk=job_b_222');
  });
});

