import { test, expect, chromium, BrowserContext } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import os from 'os';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function authenticateExtension(context: BrowserContext) {
  let [background] = context.serviceWorkers();
  if (!background) {
    background = await context.waitForEvent('serviceworker');
  }
  await background.evaluate(() => {
    return new Promise<void>((resolve) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const api = (globalThis as any).chrome;
      api.storage.local.set(
        {
          compust_jwt_token: 'mock_jwt_token_12345',
          compust_settings: { backendUrl: 'http://localhost:8000' },
        },
        () => {
          api.storage.local.get('compust_jwt_token', () => resolve());
        }
      );
    });
  });
}

test.describe('Compust Capture Extension E2E Tests', () => {
  let context: BrowserContext;
  const pathToExtension = path.resolve(__dirname, '../../dist/chrome');
  const linkedinFixture = fs.readFileSync(
    path.resolve(__dirname, '../fixtures/linkedin-job.html'),
    'utf-8'
  );
  const linkedinSearchResultsFixture = fs.readFileSync(
    path.resolve(__dirname, '../fixtures/linkedin-search-results.html'),
    'utf-8'
  );
  const linkedinSplitPaneFixture = fs.readFileSync(
    path.resolve(__dirname, '../fixtures/linkedin-splitpane-job.html'),
    'utf-8'
  );
  const indeedFixture = fs.readFileSync(
    path.resolve(__dirname, '../fixtures/indeed-job.html'),
    'utf-8'
  );
  const glassdoorFixture = fs.readFileSync(
    path.resolve(__dirname, '../fixtures/glassdoor-job.html'),
    'utf-8'
  );
  const glassdoorLiveFixture = fs.readFileSync(
    path.resolve(__dirname, '../fixtures/glassdoor-live-job.html'),
    'utf-8'
  );
  const wttjFixture = fs.readFileSync(
    path.resolve(__dirname, '../fixtures/welcometothejungle-job.html'),
    'utf-8'
  );

  test.beforeEach(async () => {
    // Create isolated user data dir for persistent context
    const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'compust-pw-ext-'));

    context = await chromium.launchPersistentContext(userDataDir, {
      headless: true,
      args: [
        `--disable-extensions-except=${pathToExtension}`,
        `--load-extension=${pathToExtension}`,
        '--no-sandbox',
      ],
    });

    // Mock LinkedIn, Indeed, Glassdoor, and WTTJ pages to return fixture HTML
    await context.route('https://www.linkedin.com/jobs/view/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: linkedinFixture,
      });
    });

    await context.route('https://www.linkedin.com/jobs/search-results/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: linkedinSearchResultsFixture,
      });
    });

    await context.route('https://www.linkedin.com/jobs/search**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: linkedinSplitPaneFixture,
      });
    });

    await context.route('https://www.indeed.com/viewjob**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: indeedFixture,
      });
    });

    await context.route('https://www.glassdoor.com/job-listing/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: glassdoorFixture,
      });
    });
    await context.route('https://www.glassdoor.com/Job/software-developer-jobs**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: glassdoorLiveFixture,
      });
    });
    await context.route('https://www.glassdoor.com/Job/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: glassdoorFixture,
      });
    });

    await context.route('https://www.welcometothejungle.com/en/companies', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: '<html><body><h1>Company Directory</h1><div class="directory-list"></div></body></html>',
      });
    });

    await context.route('https://www.welcometothejungle.com/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: wttjFixture,
      });
    });

    // Mock Compust backend responses
    await context.route('**/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', database: 'sqlite' }),
      });
    });

    await context.route('**/api/v1/jobs/quick-add-and-analyze', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job: {
            id: 42,
            title: 'Senior Frontend Engineer',
            company: 'Cloud Innovations Ltd',
            source: 'extension:linkedin',
            status: 'draft',
          },
          is_duplicate: false,
          has_active_resume: true,
          score_breakdown: {
            overall_score: 85,
          },
          match_analysis: {
            already_demonstrated: ['Python FastAPI', 'TypeScript', 'Docker'],
            missing_or_weak: ['GraphQL'],
            suggestions: ['Highlight Python async projects in resume.'],
          },
        }),
      });
    });

    // Mock the ephemeral analyze endpoint used by all four supported site content scripts
    // (LinkedIn, Indeed, Glassdoor, Welcome to the Jungle) via ANALYZE_EPHEMERAL_JOB message.
    await context.route('**/api/v1/jobs/analyze-ephemeral', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          title: 'Senior Frontend Engineer',
          company: 'Cloud Innovations Ltd',
          location: 'Paris, France',
          url: 'https://www.linkedin.com/jobs/view/9876543210/',
          has_active_resume: true,
          message: null,
          match_score: 85,
          positive_factors: ['TypeScript experience', 'React development'],
          missing_factors: ['GraphQL knowledge'],
          demonstrated_skills: ['Python FastAPI', 'TypeScript', 'Docker'],
          missing_skills: ['GraphQL'],
          resume_suggestions: [
            {
              section: 'skills',
              action: 'add',
              original_phrase: '',
              suggested_phrase: 'GraphQL',
              reason: 'Required skill missing from resume.',
            },
          ],
          visa_analysis: {
            mentioned: true,
            snippet: 'Visa sponsorship available for eligible candidates.',
          },
          content_hash: 'abc123',
        }),
      });
    });
  });

  test.afterEach(async () => {
    await context.close();
  });

  test('injects floating button into Shadow DOM and captures LinkedIn posting with match analysis', async () => {
    await authenticateExtension(context);

    const page = await context.newPage();
    await page.goto('https://www.linkedin.com/jobs/view/9876543210/');

    const shadowHost = page.locator('#compust-capture-root');
    await expect(shadowHost).toBeAttached({ timeout: 10000 });

    const triggerBtn = shadowHost.locator('#compust-capture-trigger');
    await expect(triggerBtn).toBeVisible({ timeout: 5000 });
    await expect(triggerBtn).toContainText('Analyse with Compust');
    await triggerBtn.click();

    const panel = shadowHost.locator('.compust-panel');
    await expect(panel).toBeVisible({ timeout: 5000 });
    await expect(panel.locator('.compust-status-pill')).toContainText('Analysis Preview • 0 Database Writes');
    await expect(panel.locator('#compust-action-save')).toBeVisible();
    await expect(panel.locator('#compust-action-applied')).toBeVisible();
    await expect(panel.locator('#compust-action-dismiss')).toBeVisible();
    await expect(panel.locator('.compust-score-num')).toContainText('85%');
    await expect(panel.locator('.compust-chip').first()).toContainText('Python FastAPI');
  });

  test('injects floating button on LinkedIn split-pane search-results view and captures selected job (Issue 2)', async () => {
    await authenticateExtension(context);

    const page = await context.newPage();
    await page.goto('https://www.linkedin.com/jobs/search-results/?currentJobId=9876543210&keywords=software+engineer');

    const shadowHost = page.locator('#compust-capture-root');
    await expect(shadowHost).toBeAttached({ timeout: 10000 });

    const triggerBtn = shadowHost.locator('#compust-capture-trigger');
    await expect(triggerBtn).toBeVisible({ timeout: 5000 });
    await triggerBtn.click();

    const panel = shadowHost.locator('.compust-panel');
    await expect(panel).toBeVisible({ timeout: 5000 });
    await expect(panel.locator('.compust-score-num')).toContainText('85%');
  });

  test('injects floating button on LinkedIn /jobs/search/ view with currentJobId', async () => {
    await authenticateExtension(context);

    const page = await context.newPage();
    await page.goto('https://www.linkedin.com/jobs/search/?currentJobId=1029384756&keywords=software+engineer');

    const shadowHost = page.locator('#compust-capture-root');
    await expect(shadowHost).toBeAttached({ timeout: 10000 });

    const triggerBtn = shadowHost.locator('#compust-capture-trigger');
    await expect(triggerBtn).toBeVisible({ timeout: 5000 });
    await triggerBtn.click();

    const panel = shadowHost.locator('.compust-panel');
    await expect(panel).toBeVisible({ timeout: 5000 });
    await expect(panel.locator('.compust-score-num')).toContainText('85%');
  });

  test('displays actionable offline message when Compust backend is unreachable', async () => {
    await authenticateExtension(context);

    // Override health to fail
    await context.route('**/health', async (route) => {
      await route.abort('connectionrefused');
    });
    await context.route('**/api/v1/jobs/quick-add-and-analyze', async (route) => {
      await route.abort('connectionrefused');
    });

    const page = await context.newPage();
    await page.goto('https://www.linkedin.com/jobs/view/9876543210/');

    const shadowHost = page.locator('#compust-capture-root');
    const triggerBtn = shadowHost.locator('#compust-capture-trigger');
    await triggerBtn.click();

    const panel = shadowHost.locator('.compust-panel');
    await expect(panel).toBeVisible({ timeout: 5000 });
    await expect(panel.locator('.compust-alert-box')).toContainText("Compust isn't running");

    const retryBtn = panel.locator('#compust-retry-btn');
    await expect(retryBtn).toBeVisible();
  });

  test('captures Glassdoor posting with match analysis', async () => {
    await authenticateExtension(context);

    const page = await context.newPage();
    await page.goto('https://www.glassdoor.com/job-listing/full-stack-cloud-developer-JV_IC1234.htm');

    const shadowHost = page.locator('#compust-capture-root');
    await expect(shadowHost).toBeAttached({ timeout: 10000 });

    const triggerBtn = shadowHost.locator('#compust-capture-trigger');
    await expect(triggerBtn).toBeVisible({ timeout: 5000 });
    await triggerBtn.click();

    const panel = shadowHost.locator('.compust-panel');
    await expect(panel).toBeVisible({ timeout: 5000 });
    await expect(panel.locator('.compust-score-num')).toContainText('85%');
  });

  test('captures Glassdoor live search split-pane posting with full description (Issue 1)', async () => {
    await authenticateExtension(context);

    const page = await context.newPage();
    await page.goto('https://www.glassdoor.com/Job/software-developer-jobs-SRCH_KO0,18.htm');

    const shadowHost = page.locator('#compust-capture-root');
    await expect(shadowHost).toBeAttached({ timeout: 10000 });

    const triggerBtn = shadowHost.locator('#compust-capture-trigger');
    await expect(triggerBtn).toBeVisible({ timeout: 5000 });
    await triggerBtn.click();

    const panel = shadowHost.locator('.compust-panel');
    await expect(panel).toBeVisible({ timeout: 5000 });
    await expect(panel.locator('.compust-score-num')).toContainText('85%');
  });

  test('captures Indeed posting with match analysis (regression check)', async () => {
    await authenticateExtension(context);

    const page = await context.newPage();
    await page.goto('https://www.indeed.com/viewjob?jk=1234567890abcdef');

    const shadowHost = page.locator('#compust-capture-root');
    await expect(shadowHost).toBeAttached({ timeout: 10000 });

    const triggerBtn = shadowHost.locator('#compust-capture-trigger');
    await expect(triggerBtn).toBeVisible({ timeout: 5000 });
    await triggerBtn.click();

    const panel = shadowHost.locator('.compust-panel');
    await expect(panel).toBeVisible({ timeout: 5000 });
    await expect(panel.locator('.compust-score-num')).toContainText('85%');
  });

  test('captures Welcome to the Jungle French posting with match analysis & Deep Analysis', async () => {
    await authenticateExtension(context);

    const page = await context.newPage();
    await page.goto('https://www.welcometothejungle.com/fr/companies/tech-innovations-paris/jobs/ingenieur-cloud-devops_paris');

    const shadowHost = page.locator('#compust-capture-root');
    await expect(shadowHost).toBeAttached({ timeout: 10000 });

    const triggerBtn = shadowHost.locator('#compust-capture-trigger');
    await expect(triggerBtn).toBeVisible({ timeout: 5000 });
    await triggerBtn.click();

    const panel = shadowHost.locator('.compust-panel');
    await expect(panel).toBeVisible({ timeout: 5000 });
    await expect(panel.locator('.compust-score-num')).toContainText('85%');
    await expect(panel).toContainText('Deep Analysis: Visa & Work Authorization');
  });

  test('does not inject capture button on Welcome to the Jungle company directory page (Issue 3)', async () => {
    const page = await context.newPage();
    await page.goto('https://www.welcometothejungle.com/en/companies');
    await page.waitForTimeout(1000);

    const shadowHost = page.locator('#compust-capture-root');
    await expect(shadowHost).toHaveCount(0);
  });
});
