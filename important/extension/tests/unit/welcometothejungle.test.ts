import { describe, it, expect } from 'vitest';
import { JSDOM } from 'jsdom';
import fs from 'fs';
import path from 'path';
import { WelcomeToTheJungleExtractor } from '../../src/content/welcomeToTheJungle';
import { validateJobPayload } from '../../src/content/common/jobExtractor';

describe('WelcomeToTheJungleExtractor', () => {
  const extractor = new WelcomeToTheJungleExtractor();
  const fixturePath = path.resolve(__dirname, '../fixtures/welcometothejungle-job.html');
  const liveFixturePath = path.resolve(__dirname, '../fixtures/wttj-live-job.html');

  it('correctly matches real job-posting URLs and rejects company directory listing pages (Issue 3)', () => {
    // Valid job postings under /companies/<company>/jobs/<slug>
    expect(extractor.canHandle('https://www.welcometothejungle.com/fr/companies/tech-paris/jobs/lead-dev')).toBe(true);
    expect(extractor.canHandle('https://www.welcometothejungle.com/en/companies/tech-paris/jobs/lead-dev')).toBe(true);
    expect(extractor.canHandle('https://www.welcometothejungle.com/en/companies/wttj/jobs/group-treasury-accounting-manager_paris')).toBe(true);

    // Company directory / search pages must NOT match
    expect(extractor.canHandle('https://www.welcometothejungle.com/en/companies')).toBe(false);
    expect(extractor.canHandle('https://www.welcometothejungle.com/companies')).toBe(false);
    expect(extractor.canHandle('https://www.welcometothejungle.com/en/jobs')).toBe(false);
    expect(extractor.canHandle('https://www.welcometothejungle.com/fr/media')).toBe(false);

    // With document provided for real job posting
    const html = fs.readFileSync(fixturePath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.welcometothejungle.com/fr/companies/tech-innovations-paris/jobs/ingenieur-cloud-devops_paris' });
    expect(extractor.canHandle('https://www.welcometothejungle.com/fr/companies/tech-innovations-paris/jobs/ingenieur-cloud-devops_paris', dom.window.document)).toBe(true);

    const emptyDom = new JSDOM('<html><body><div>Empty media list</div></body></html>', { url: 'https://www.welcometothejungle.com/fr/companies/test/jobs/empty' });
    expect(extractor.canHandle('https://www.welcometothejungle.com/fr/companies/test/jobs/empty', emptyDom.window.document)).toBe(false);
  });

  it('extracts French posting with proper accent and encoding preservation', () => {
    const html = fs.readFileSync(fixturePath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.welcometothejungle.com/fr/companies/tech-innovations-paris/jobs/ingenieur-cloud-devops_paris' });
    const payload = extractor.extract(dom.window.document);

    expect(payload).not.toBeNull();
    expect(payload?.title).toBe('Ingénieur Cloud & DevOps H/F');
    expect(payload?.company).toBe('Tech Innovations Paris');
    expect(payload?.location).toBe('Paris');
    expect(payload?.description).toContain('Tech Innovations Paris recherche un(e) Ingénieur(e) Cloud & DevOps');
    expect(payload?.description).toContain('AWS et Kubernetes');
    expect(payload?.remote_type).toBe('Remote');
    expect(payload?.source).toBe('extension:welcometothejungle');

    const validation = validateJobPayload(payload);
    expect(validation.isValid).toBe(true);
  });

  it('extracts real live Welcome to the Jungle posting via JSON-LD / DOM fallback (Issue 3 Live Verification)', () => {
    const html = fs.readFileSync(liveFixturePath, 'utf-8');
    const dom = new JSDOM(html, { url: 'https://www.welcometothejungle.com/en/companies/wttj/jobs/group-treasury-accounting-manager_paris' });
    const payload = extractor.extract(dom.window.document);

    expect(payload).not.toBeNull();
    expect(payload?.title).toBe('Responsable Trésorerie & Comptabilité Groupe');
    expect(payload?.company).toBe('Welcome to the Jungle');
    expect(payload?.location).toBe('Paris');
    expect(payload?.description).not.toBeNull();
    expect(payload?.description).toContain('Group Treasury');
    expect(payload?.description).toContain('Accounting Manager');
    expect(payload?.source).toBe('extension:welcometothejungle');

    const validation = validateJobPayload(payload);
    expect(validation.isValid).toBe(true);
  });
});
