import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def run_diagnostics(browser_name: str, host: str, port: int = 8000):
    url = f"http://{host}:{port}"
    print(f"\n========================================================")
    print(f"RUNNING E2E REPRO: {browser_name.upper()} on {url}")
    print(f"========================================================")
    
    async with async_playwright() as p:
        browser_type = getattr(p, browser_name)
        browser = await browser_type.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        console_errors = []
        network_failures = []
        alerts = []

        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None)
        page.on("pageerror", lambda err: console_errors.append(f"[UNCAUGHT] {err}"))
        
        async def handle_dialog(dialog):
            print(f"[{browser_name.upper()} DIALOG ALERT]: {dialog.message}")
            alerts.append(dialog.message)
            await dialog.dismiss()
        page.on("dialog", handle_dialog)

        async def on_request_failed(request):
            network_failures.append({
                "url": request.url,
                "method": request.method,
                "failure": str(request.failure),
            })
            print(f"[{browser_name.upper()} NETWORK FAILED]: {request.method} {request.url} -> {request.failure}")
        page.on("requestfailed", on_request_failed)

        async def on_response(response):
            if response.status >= 400:
                print(f"[{browser_name.upper()} HTTP {response.status}]: {response.request.method} {response.url}")
        page.on("response", on_response)

        print(f"1. Navigating to {url}...")
        await page.goto(url, wait_until="networkidle", timeout=15000)

        # -----------------------------------------------------------------
        # Bug 1: Opportunities -> Click Job Details
        # -----------------------------------------------------------------
        print("\n2. Testing Opportunities Job Detail Click...")
        job_titles = page.locator(".job-title")
        job_count = await job_titles.count()
        print(f"   Found {job_count} jobs.")
        if job_count > 0:
            print("   Clicking first job title...")
            await job_titles.first.click()
            await page.wait_for_timeout(2000)
            if alerts:
                print(f"   BUG REPRODUCED - Alert triggered: {alerts[-1]}")
            else:
                print("   No alert triggered on job click.")
        else:
            print("   No job titles found to click.")

        # -----------------------------------------------------------------
        # Bug 2: Internships Page
        # -----------------------------------------------------------------
        print("\n3. Testing Internships Page Navigation...")
        internships_nav = page.locator("div.nav-item, [role='tab']").filter(has_text="Internships").first
        if await internships_nav.count() > 0:
            print("   Clicking Internships tab...")
            await internships_nav.click()
            await page.wait_for_timeout(3000)
            
            # Check for error banner or text
            error_banners = page.locator(".curated-error-banner, .error-banner, .alert-danger")
            if await error_banners.count() > 0:
                err_text = await error_banners.first.text_content()
                print(f"   BUG REPRODUCED - Internships UI Error Banner: {err_text}")
            else:
                body_text = await page.text_content("body")
                if "network error" in body_text.lower() or "failed to fetch" in body_text.lower():
                    print("   BUG REPRODUCED - Found 'network error' in page content!")
                else:
                    print("   Internships loaded without visible error banner.")
        else:
            print("   Internships tab not found in navbar!")

        # -----------------------------------------------------------------
        # Bug 3: Gemini Provider Consent Button
        # -----------------------------------------------------------------
        print("\n4. Testing Gemini Consent Button...")
        ai_trigger = page.locator(".ai-assistant-trigger, [title*='AI'], button:has-text('AI')").first
        # Also check settings button in AI widget if open or open directly
        await page.evaluate("""() => {
            // Trigger AISettingsModal if trigger exists
            const btn = document.querySelector('.ai-assistant-trigger') || document.querySelector('[aria-label=\"AI Settings\"]');
            if (btn) btn.click();
        }""")
        await page.wait_for_timeout(1000)

        # Look for AI settings modal trigger inside assistant
        settings_gear = page.locator(".settings-toggle-btn, button[title='Settings'], button[aria-label='Settings']").first
        if await settings_gear.count() > 0:
            await settings_gear.click()
            await page.wait_for_timeout(1000)

        gemini_radio = page.locator("label, div, button").filter(has_text="Google Gemini").first
        if await gemini_radio.count() > 0:
            print("   Selecting Google Gemini provider...")
            await gemini_radio.click()
            await page.wait_for_timeout(1000)

            consent_btn = page.locator("button:has-text('I understand and enable')").first
            if await consent_btn.count() > 0:
                print("   Clicking 'I understand and enable' consent button...")
                await consent_btn.click()
                await page.wait_for_timeout(2000)
                if await consent_btn.is_visible():
                    print("   BUG REPRODUCED - Consent button STILL VISIBLE after click (hung / did nothing)!")
                else:
                    print("   Consent modal closed successfully.")
            else:
                print("   Consent button not visible (consent might already be granted).")
        else:
            print("   Could not find Google Gemini provider option.")

        print("\nSummary for", browser_name.upper(), "on", host)
        print(f"Network Failures count: {len(network_failures)}")
        print(f"Alerts count: {len(alerts)}")
        print(f"Console Errors/Warnings count: {len(console_errors)}")
        for err in console_errors[:5]:
            print("  ", err)

        await browser.close()

async def main():
    # Test Firefox with 127.0.0.1
    await run_diagnostics("firefox", "127.0.0.1")
    # Test Firefox with localhost
    await run_diagnostics("firefox", "localhost")
    # Test Chromium with 127.0.0.1
    await run_diagnostics("chromium", "127.0.0.1")
    # Test Chromium with localhost
    await run_diagnostics("chromium", "localhost")

if __name__ == "__main__":
    asyncio.run(main())
