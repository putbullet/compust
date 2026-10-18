import { chromium, firefox } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import os from 'os';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const artifactsDir = 'C:/Users/soula/.gemini/antigravity-ide/brain/1342d9bc-4f05-4bdb-ad08-12eabc86d541';
const extensionDir = path.resolve(__dirname, '..');
const chromeExtPath = path.resolve(extensionDir, 'dist/chrome');

const linkedinFixture = fs.readFileSync(
  path.resolve(extensionDir, 'tests/fixtures/linkedin-job.html'),
  'utf-8'
);

const ephemeralResponse = {
  title: 'Senior Full Stack Engineer',
  company: 'Cloud Innovations Ltd',
  location: 'Paris, France',
  url: 'https://www.linkedin.com/jobs/view/9876543210/',
  has_active_resume: true,
  message: null,
  match_score: 88,
  positive_factors: ['TypeScript experience', 'FastAPI & Python architecture', 'React 18 SPA'],
  missing_factors: ['Kubernetes production cluster admin'],
  demonstrated_skills: ['Python FastAPI', 'TypeScript', 'Docker', 'PostgreSQL', 'React'],
  missing_skills: ['Kubernetes', 'GraphQL'],
  resume_suggestions: [
    {
      section: 'skills',
      action: 'add',
      original_phrase: '',
      suggested_phrase: 'Kubernetes',
      reason: 'Key differentiator mentioned in requirements.',
    },
  ],
  visa_analysis: {
    mentioned: true,
    snippet: 'Visa sponsorship available for eligible EU and international candidates.',
  },
  content_hash: 'content_hash_v102_demo',
};

async function authenticateExtension(context) {
  let [background] = context.serviceWorkers();
  if (!background) {
    background = await context.waitForEvent('serviceworker');
  }
  await background.evaluate(() => {
    return new Promise((resolve) => {
      const api = globalThis.chrome;
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

async function captureChromeVisual() {
  console.log('--- Capturing Chrome Extension Overlay Visual ---');
  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'compust-chrome-vis-'));
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    viewport: { width: 1440, height: 900 },
    args: [
      `--disable-extensions-except=${chromeExtPath}`,
      `--load-extension=${chromeExtPath}`,
      '--no-sandbox',
    ],
  });

  await context.route('https://www.linkedin.com/jobs/view/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'text/html',
      body: linkedinFixture,
    });
  });

  await context.route('**/health', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', database: 'sqlite' }),
    });
  });

  await context.route('**/api/v1/jobs/analyze-ephemeral', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(ephemeralResponse),
    });
  });

  await authenticateExtension(context);

  const page = await context.newPage();
  await page.goto('https://www.linkedin.com/jobs/view/9876543210/');
  await page.waitForTimeout(1000);

  const shadowHost = page.locator('#compust-capture-root');
  await shadowHost.waitFor({ state: 'attached', timeout: 10000 });

  const triggerBtn = shadowHost.locator('#compust-capture-trigger');
  await triggerBtn.waitFor({ state: 'visible', timeout: 5000 });
  await triggerBtn.click();

  const panel = shadowHost.locator('.compust-panel');
  await panel.waitFor({ state: 'visible', timeout: 5000 });
  await page.waitForTimeout(1000);

  const screenshotPath = path.join(artifactsDir, 'extension_overlay_chrome_v102.png');
  await page.screenshot({ path: screenshotPath, fullPage: false });
  console.log(`Saved Chrome screenshot to: ${screenshotPath}`);

  await context.close();
}

async function captureFirefoxVisual() {
  console.log('--- Capturing Firefox Injected Overlay Visual ---');
  const browser = await firefox.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });

  await context.route('https://www.linkedin.com/jobs/view/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'text/html',
      body: linkedinFixture,
    });
  });

  await context.route('**/health', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', database: 'sqlite' }),
    });
  });

  await context.route('**/api/v1/jobs/analyze-ephemeral', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(ephemeralResponse),
    });
  });

  const page = await context.newPage();
  await page.goto('https://www.linkedin.com/jobs/view/9876543210/');
  await page.waitForTimeout(500);

  const ffContentJs = fs.readFileSync(
    path.resolve(extensionDir, 'dist/firefox/src/content/linkedin.js'),
    'utf-8'
  );

  await page.evaluate((ephem) => {
    window.chrome = {
      storage: {
        local: {
          get: (keys, cb) => cb ? cb({ compust_jwt_token: 'mock_jwt', compust_settings: {} }) : Promise.resolve({ compust_jwt_token: 'mock_jwt', compust_settings: {} }),
          set: (obj, cb) => cb ? cb() : Promise.resolve(),
        },
      },
      runtime: {
        sendMessage: (msg, cb) => {
          const response = { ok: true, data: ephem };
          if (typeof cb === 'function') {
            setTimeout(() => cb(response), 50);
          }
          return Promise.resolve(response);
        },
        getURL: (path) => path,
      },
    };
    window.browser = window.chrome;
  }, ephemeralResponse);

  await page.addScriptTag({ content: ffContentJs });
  await page.waitForTimeout(1000);

  const shadowHost = page.locator('#compust-capture-root');
  await shadowHost.waitFor({ state: 'attached', timeout: 10000 });

  const triggerBtn = shadowHost.locator('#compust-capture-trigger');
  await triggerBtn.waitFor({ state: 'visible', timeout: 5000 });
  await triggerBtn.click();

  const panel = shadowHost.locator('.compust-panel');
  await panel.waitFor({ state: 'visible', timeout: 5000 });
  await page.waitForTimeout(1000);

  const screenshotPath = path.join(artifactsDir, 'extension_overlay_firefox_v102.png');
  await page.screenshot({ path: screenshotPath, fullPage: false });
  console.log(`Saved Firefox screenshot to: ${screenshotPath}`);

  await browser.close();
}

async function main() {
  await captureChromeVisual();
  await captureFirefoxVisual();
  console.log('All extension visuals captured successfully!');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
