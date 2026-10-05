import pytest
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"

@pytest.mark.parametrize("browser_type", ["chromium", "firefox"])
def test_opportunities_detail_modal(browser_type):
    """Verify Opportunities loads and job detail modal opens cleanly without alert/crash."""
    with sync_playwright() as p:
        browser = getattr(p, browser_type)
        instance = browser.launch(headless=True)
        page = instance.new_page(viewport={"width": 1400, "height": 900})

        dialog_messages = []
        page.on("dialog", lambda dialog: dialog_messages.append(dialog.message))

        page.goto(f"{BASE_URL}/?tab=directory", wait_until="networkidle")
        page.wait_for_timeout(1500)

        # Check for error banners or alerts
        assert len(dialog_messages) == 0, f"Unexpected alert dialog: {dialog_messages}"

        # Click first job card / title
        job_card = page.locator(".jobs-grid > div, .job-title").first
        assert job_card.count() > 0, "No opportunity job card found"
        job_card.click()
        page.wait_for_timeout(1000)

        # Verify no dialog popped up on click
        assert len(dialog_messages) == 0, f"Dialog popped on opening job detail: {dialog_messages}"

        # Verify modal container opened
        modal = page.locator(".modal-container, .modal-backdrop")
        assert modal.count() > 0, "Job detail modal did not open"

        # Verify close button works
        close_btn = page.locator("button.close-btn, button[aria-label='Close modal']").first
        if close_btn.count() > 0:
            close_btn.click()
            page.wait_for_timeout(500)

        instance.close()

@pytest.mark.parametrize("browser_type", ["chromium", "firefox"])
def test_internships_page_curated(browser_type):
    """Verify Internships page loads curated listings from bundled seed instantly."""
    with sync_playwright() as p:
        browser = getattr(p, browser_type)
        instance = browser.launch(headless=True)
        page = instance.new_page(viewport={"width": 1400, "height": 900})

        page.goto(f"{BASE_URL}/?tab=internships", wait_until="networkidle")
        page.wait_for_timeout(1500)

        # Check total tracked metric
        tracked_stat = page.locator("text=TOTAL TRACKED")
        assert tracked_stat.count() > 0, "Internships metrics not displayed"

        # Check listings cards are visible
        cards = page.locator(".curated-card, .internship-card, .job-card")
        card_count = cards.count()
        assert card_count > 0, "Internship listing cards did not load"

        instance.close()

@pytest.mark.parametrize("browser_type", ["chromium", "firefox"])
def test_data_management_view(browser_type):
    """Verify Data Management & Portability tab shows populated counts and export option."""
    with sync_playwright() as p:
        browser = getattr(p, browser_type)
        instance = browser.launch(headless=True)
        page = instance.new_page(viewport={"width": 1400, "height": 900})

        page.goto(f"{BASE_URL}/?tab=supervision", wait_until="networkidle")
        page.wait_for_timeout(1500)

        # Click Import & Backup tab
        import_tab = page.locator("button:has-text('Import & Backup')")
        assert import_tab.count() > 0, "Import & Backup subnav button missing"
        import_tab.click()
        page.wait_for_timeout(1000)

        # Verify active SQLite standalone database info is displayed
        assert page.locator("text=Active Local Database (SQLite Standalone)").count() > 0
        assert page.locator("text=Data Populated").count() > 0

        # Verify populated statistics (451 jobs, 57 applications)
        assert page.locator("text=451").count() > 0, "Expected 451 jobs count not shown"
        assert page.locator("text=57").count() > 0, "Expected 57 applications count not shown"

        # Verify export backup button exists
        export_btn = page.locator("button:has-text('Export Backup Archive')")
        assert export_btn.count() > 0, "Export backup button not found"

        instance.close()

@pytest.mark.parametrize("browser_type", ["chromium", "firefox"])
def test_guide_docs_redesign(browser_type):
    """Verify Guide & Docs clean technical layout, collapsible sidebar, TOC, and keyboard / search."""
    with sync_playwright() as p:
        browser = getattr(p, browser_type)
        instance = browser.launch(headless=True)
        page = instance.new_page(viewport={"width": 1400, "height": 900})

        page.goto(f"{BASE_URL}/?tab=guide", wait_until="networkidle")
        page.wait_for_timeout(1500)

        # Verify header title and version badge
        assert page.locator(".guide-docs-title:has-text('Documentation')").count() > 0
        assert page.locator(".version-pill:has-text('v1.0.2')").count() > 0

        # Verify keyboard '/' focuses search
        page.keyboard.press("/")
        page.wait_for_timeout(300)
        is_focused = page.evaluate("document.activeElement.classList.contains('guide-search-input')")
        assert is_focused, "Keyboard '/' did not focus the guide search input"

        # Verify sidebar collapsible toggle
        toggle_btn = page.locator(".guide-sidebar-toggle-btn")
        assert toggle_btn.count() > 0, "Sidebar toggle button not found"
        toggle_btn.click()
        page.wait_for_timeout(300)
        assert page.locator(".guide-layout.sidebar-collapsed").count() > 0, "Sidebar did not collapse"
        toggle_btn.click()
        page.wait_for_timeout(300)
        assert page.locator(".guide-layout.sidebar-collapsed").count() == 0, "Sidebar did not expand"

        # Verify right 'On this page' TOC
        on_this_page = page.locator(".guide-on-this-page")
        assert on_this_page.count() > 0, "Right On this page TOC missing"
        toc_links = on_this_page.locator(".on-this-page-link")
        assert toc_links.count() > 0, "On this page TOC has no links"

        instance.close()

@pytest.mark.parametrize("browser_type", ["chromium", "firefox"])
def test_gemini_provider_wizard(browser_type):
    """Verify Gemini stepped provider setup flow and default model selection."""
    with sync_playwright() as p:
        browser = getattr(p, browser_type)
        instance = browser.launch(headless=True)
        page = instance.new_page(viewport={"width": 1400, "height": 900})

        page.goto(f"{BASE_URL}/?tab=directory", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Open AI Settings
        ai_btn = page.locator("button[title*='AI Settings'], .status-pill, button:has-text('AI')").first
        ai_btn.click()
        page.wait_for_timeout(800)

        # Click Google Gemini Provider Card
        cards = page.locator("div[role='button']")
        count = cards.count()
        for i in range(count):
            text = cards.nth(i).inner_text()
            if "Google Gemini" in text:
                cards.nth(i).click()
                break

        page.wait_for_timeout(800)

        # Verify Step 1: Explicit Consent
        assert page.locator("text=Step 1: Explicit Consent").count() > 0
        accept_btn = page.locator("button:has-text('I Understand & Accept')")
        assert accept_btn.count() > 0, "Consent accept button not found"

        # Click to advance to Step 2
        accept_btn.click()
        page.wait_for_timeout(800)

        # Verify Step 2: Key & Model
        assert page.locator("text=Step 2: API Key & Model Configuration").count() > 0
        assert page.locator("text=Encrypted locally with Windows DPAPI").count() > 0

        # Check default model in select is gemini-3.8-flash
        model_select = page.locator("select").last
        selected_val = model_select.input_value()
        assert selected_val == "gemini-3.8-flash", f"Default model was {selected_val}, expected gemini-3.8-flash"

        instance.close()
