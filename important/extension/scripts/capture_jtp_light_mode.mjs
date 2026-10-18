import { chromium } from '@playwright/test';
import path from 'path';

const artifactsDir = 'C:/Users/soula/.gemini/antigravity-ide/brain/1342d9bc-4f05-4bdb-ad08-12eabc86d541';

async function main() {
  const browser = await chromium.launch({ headless: true });
  
  // Create context with light color scheme
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    colorScheme: 'light',
  });

  const page = await context.newPage();
  
  // Set localStorage auth token if needed
  await page.goto('http://127.0.0.1:5173/?tab=profile', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);

  // If redirected or not logged in, check if login modal or button is present
  const signInBtn = page.locator('button:has-text("Sign In")').first();
  if (await signInBtn.isVisible()) {
    await signInBtn.click();
    await page.waitForTimeout(500);
    // Fill credentials
    const emailInput = page.locator('input[type="email"]').first();
    const passInput = page.locator('input[type="password"]').first();
    if (await emailInput.isVisible()) {
      await emailInput.fill('test@compust.internal');
      await passInput.fill('Password123!');
      const submitBtn = page.locator('button[type="submit"]:has-text("Sign In"), .auth-submit-btn').first();
      await submitBtn.click();
      await page.waitForTimeout(1500);
    }
  }

  // Navigate back to profile tab
  await page.goto('http://127.0.0.1:5173/?tab=profile', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);

  // Click "Resume Builder Studio" subtab
  const resumeStudioBtn = page.locator('button:has-text("Resume Builder Studio")').first();
  if (await resumeStudioBtn.isVisible()) {
    await resumeStudioBtn.click();
    console.log('Clicked Resume Builder Studio tab');
    await page.waitForTimeout(1000);
  }

  // Look for existing resume or create one
  const resumeCards = page.locator('.resume-card, .resume-card-compact, .resume-item');
  if (await resumeCards.count() > 0) {
    await resumeCards.first().click();
    await page.waitForTimeout(1000);
  } else {
    const createBtn = page.locator('button:has-text("Create Resume"), button:has-text("New Resume"), .btn-create-resume').first();
    if (await createBtn.isVisible()) {
      await createBtn.click();
      console.log('Clicked Create Resume');
      await page.waitForTimeout(1500);
    }
  }

  // Scroll to #resume-job-target-section
  const jobTargetSection = page.locator('#resume-job-target-section, .jtp-panel');
  if (await jobTargetSection.count() > 0) {
    await jobTargetSection.first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);

    // Fill role and description
    const roleInput = page.locator('#jtp-role');
    await roleInput.waitFor({ state: 'visible', timeout: 5000 });
    await roleInput.fill('Senior Python Engineer');

    const descInput = page.locator('#jtp-desc');
    await descInput.waitFor({ state: 'visible', timeout: 5000 });
    await descInput.fill('We are seeking a Senior Python Engineer with 5+ years experience in FastAPI, PostgreSQL, Docker, and modern React SPAs. Kubernetes and cloud deployment knowledge is a plus. Experience in microservices and distributed caching.');

    const analyzeBtn = page.locator('#jtp-analyze-btn');
    await analyzeBtn.waitFor({ state: 'visible', timeout: 5000 });
    await page.waitForTimeout(500);
    await analyzeBtn.click();
    console.log('Clicked #jtp-analyze-btn, waiting for analysis...');

    // Wait for analysis results to render
    const resultsPanel = page.locator('.jtp-results').first();
    await resultsPanel.waitFor({ state: 'visible', timeout: 25000 });
    console.log('Analysis results visible!');
    await page.waitForTimeout(1000);

    // Click Recommendations tab
    const recTab = page.locator('.jtp-tab:has-text("Recommendations")').first();
    if (await recTab.isVisible()) {
      await recTab.click();
      await page.waitForTimeout(800);
    }

    // Save light mode recommendations screenshot
    const recPath = path.join(artifactsDir, 'jtp_recommendations_light_mode.png');
    await page.screenshot({ path: recPath, fullPage: false });
    console.log(`Saved Light Mode Recommendations screenshot to: ${recPath}`);

    // Click Cold Email tab
    const coldEmailTab = page.locator('.jtp-tab:has-text("Cold Email")').first();
    if (await coldEmailTab.isVisible()) {
      await coldEmailTab.click();
      await page.waitForTimeout(800);
      const emailPath = path.join(artifactsDir, 'jtp_cold_email_light_mode.png');
      await page.screenshot({ path: emailPath, fullPage: false });
      console.log(`Saved Light Mode Cold Email screenshot to: ${emailPath}`);
    }
  } else {
    console.log('JobTargetPanel not found, taking current page screenshot for debug.');
    await page.screenshot({ path: path.join(artifactsDir, 'jtp_debug_page.png') });
  }

  await context.close();
  await browser.close();
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
