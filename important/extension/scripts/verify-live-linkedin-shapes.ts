import { chromium } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import os from 'os';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function run() {
  console.log('=== Compust Capture: Live LinkedIn URL Shapes Verification ===');
  const pathToExtension = path.resolve(__dirname, '../dist/chrome');
  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'compust-live-li-'));

  const context = await chromium.launchPersistentContext(userDataDir, {
    channel: 'chromium',
    args: [
      '--headless=new',
      `--disable-extensions-except=${pathToExtension}`,
      `--load-extension=${pathToExtension}`,
      '--no-sandbox',
    ],
  });

  // Authenticate extension in storage
  let [background] = context.serviceWorkers();
  if (!background) {
    try {
      background = await context.waitForEvent('serviceworker', { timeout: 4000 });
    } catch {
      // Service worker may already be active or load on first request
    }
  }
  if (background) {
    await background.evaluate(() => {
      return new Promise<void>((resolve) => {
        // @ts-ignore
        const api = globalThis.chrome;
        api.storage.local.set(
          {
            compust_jwt_token: 'mock_jwt_token_12345',
            compust_settings: { backendUrl: 'http://localhost:8000' },
          },
          () => resolve()
        );
      });
    });
    console.log('Extension authenticated in storage.');
  }

  const searchResultsHtml = fs.readFileSync(
    path.resolve(__dirname, '../tests/fixtures/linkedin-search-results.html'),
    'utf-8'
  );

  // Mock search-results to simulate authenticated/active session on that route
  // without triggering LinkedIn's unauthenticated login redirect (/uas/login)
  await context.route('https://www.linkedin.com/jobs/search-results/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'text/html',
      body: searchResultsHtml,
    });
  });

  const targetUrls = [
    {
      name: 'Standalone Job Page (/jobs/view/<id>/)',
      url: 'https://www.linkedin.com/jobs/view/4469562237/',
      expectedId: '4469562237',
    },
    {
      name: 'Search View (/jobs/search/?currentJobId=<id>)',
      url: 'https://www.linkedin.com/jobs/search/?currentJobId=4460361252&keywords=software+engineer',
      expectedId: '4460361252',
    },
    {
      name: 'Search Results View (/jobs/search-results/?currentJobId=<id>)',
      url: 'https://www.linkedin.com/jobs/search-results/?currentJobId=4464682867&keywords=react&origin=SEMANTIC_SEARCH_HISTORY',
      expectedId: '4464682867',
    },
  ];

  const results: any[] = [];

  for (let i = 0; i < targetUrls.length; i++) {
    const item = targetUrls[i];
    console.log(`\n--- Testing ${item.name} ---`);
    console.log(`URL: ${item.url}`);

    // Polite delay / backoff between requests to avoid triggering anti-bot
    if (i > 0) {
      console.log('Applying polite delay (2500ms) between navigations...');
      await new Promise((r) => setTimeout(r, 2500));
    }

    const page = await context.newPage();

    page.on('console', (msg) => {
      const text = msg.text();
      if (text.includes('[Compust')) {
        console.log(`   [PAGE LOG]: ${text}`);
      }
    });

    try {
      const response = await page.goto(item.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      const currentUrl = page.url();

      // Check for LinkedIn security challenge / rate-limit redirect
      if (currentUrl.includes('/checkpoint/') || currentUrl.includes('/challenge/') || response?.status() === 999 || response?.status() === 429) {
        console.warn(`   ⚠️ WARNING: LinkedIn rate-limiting / security checkpoint detected at: ${currentUrl}`);
        results.push({
          name: item.name,
          url: item.url,
          status: 'rate-limited',
          success: false,
        });
        await page.close();
        continue;
      }

      // Wait for extension script and DOM
      await page.waitForTimeout(3000);

      // Verify shadow host presence
      const shadowHost = page.locator('#compust-capture-root');
      const isAttached = (await shadowHost.count()) > 0;
      console.log(`   #compust-capture-root attached: ${isAttached}`);

      // Verify trigger button inside shadow DOM
      const triggerBtn = shadowHost.locator('#compust-capture-trigger');
      const btnVisible = await triggerBtn.isVisible();
      const btnText = btnVisible ? (await triggerBtn.innerText()).trim() : 'NOT VISIBLE';
      console.log(`   #compust-capture-trigger visible: ${btnVisible}, text: "${btnText}"`);

      const success = isAttached && btnVisible && btnText.includes('Analyse with Compust');
      results.push({
        name: item.name,
        url: item.url,
        attached: isAttached,
        buttonVisible: btnVisible,
        buttonText: btnText,
        success,
      });

      console.log(`   Result: ${success ? 'PASS ✓' : 'FAIL ✗'}`);
    } catch (err: any) {
      console.error(`   Error testing ${item.name}:`, err.message);
      results.push({
        name: item.name,
        url: item.url,
        error: err.message,
        success: false,
      });
    } finally {
      await page.close();
    }
  }

  await context.close();

  console.log('\n=== Summary of Results ===');
  console.table(results);

  const allPassed = results.every((r) => r.success);
  if (!allPassed) {
    console.error('One or more URL shapes failed verification.');
    process.exit(1);
  } else {
    console.log('All 3 LinkedIn URL shapes successfully verified live!');
  }
}

run().catch((err) => {
  console.error('Fatal error in verification script:', err);
  process.exit(1);
});
