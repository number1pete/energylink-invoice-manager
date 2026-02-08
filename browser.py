"""Browser automation for EnergyLink scraper using Playwright."""

import time
from playwright.sync_api import sync_playwright, BrowserContext, Page

import config


class MFARequiredError(Exception):
    """Raised when MFA challenge is detected."""
    pass


class LoginError(Exception):
    """Raised when login fails for reasons other than MFA."""
    pass


def launch_browser() -> tuple:
    """Launch Playwright with persistent context (always headed). Returns (playwright, context, page)."""
    config.BROWSER_STATE_PATH.mkdir(parents=True, exist_ok=True)

    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        user_data_dir=str(config.BROWSER_STATE_PATH),
        headless=False,
        viewport={"width": 1280, "height": 900},
        accept_downloads=False,
    )
    context.set_default_timeout(config.NAV_TIMEOUT)
    page = context.pages[0] if context.pages else context.new_page()
    return pw, context, page


def close_browser(pw, context: BrowserContext) -> None:
    """Gracefully close browser and Playwright."""
    try:
        context.close()
    except Exception:
        pass
    try:
        pw.stop()
    except Exception:
        pass


def _is_dashboard(page: Page) -> bool:
    """Check if we're on the dashboard (logged in)."""
    return "/Core/BSP/Dashboard" in page.url


def _is_landing_page(page: Page) -> bool:
    """Check if we're on the EnergyLink landing/splash page (pre-login)."""
    url = page.url.lower()
    # Landing page is app.energylink.com/ without /Core/BSP/Dashboard
    return "app.energylink.com" in url and "/Core/BSP/" not in page.url


def _is_login_page(page: Page) -> bool:
    """Check if we're on the Auth0 login page."""
    url = page.url.lower()
    return "login.auth.enverus.com" in url or "authorize" in url


def _is_mfa_page(page: Page) -> bool:
    """Check if MFA challenge is present."""
    url = page.url.lower()
    if "mfa-sms-challenge" in url:
        return True
    try:
        page.wait_for_selector("text=Verify Your Identity", timeout=2000)
        return True
    except Exception:
        pass
    try:
        page.wait_for_selector("text=Enter the code", timeout=1000)
        return True
    except Exception:
        pass
    return False


def login(page: Page) -> None:
    """Navigate to EnergyLink and log in. Raises MFARequiredError if MFA appears."""
    page.goto(config.LOGIN_URL, wait_until="domcontentloaded", timeout=config.NAV_TIMEOUT)
    time.sleep(2)

    # Already logged in?
    if _is_dashboard(page):
        return

    # Landing page: need to click the "SIGN IN" link first
    if _is_landing_page(page) and not _is_login_page(page):
        sign_in_link = page.locator('a:has-text("SIGN IN")').first
        sign_in_link.click()
        # This triggers a postback that redirects to Auth0 or straight to dashboard
        time.sleep(5)

    # After clicking SIGN IN, we may end up at:
    # 1. Dashboard (auto-login via persistent session)
    # 2. Auth0 login page (need to fill credentials)
    # 3. MFA page (session remembered user, needs MFA)
    # 4. Auth0 /authorize/resume (session resuming, may redirect further)

    # Wait for things to settle — follow any auto-redirects
    for _ in range(10):
        if _is_dashboard(page):
            return
        if _is_mfa_page(page):
            _handle_mfa_wait(page)
            return
        if _is_login_page(page):
            # Check if login form is present or if it's a redirect page
            has_email = page.locator('input[name="email"], input[type="email"], input[name="username"]').count() > 0
            has_password = page.locator('input[name="password"], input[type="password"]').count() > 0
            if has_email or has_password:
                _do_login(page)
                return
        # Still redirecting, wait a bit
        time.sleep(2)

    raise LoginError(f"Login did not reach a known state. Current URL: {page.url}")


def _handle_mfa_wait(page: Page) -> None:
    """Handle MFA challenge. Wait for user to complete it in the browser window."""
    print("MFA detected — please complete MFA in the browser window...")
    print(f"Waiting up to {config.MFA_TIMEOUT // 1000 // 60} minutes for you to enter the code...")
    try:
        page.wait_for_url("**/Core/BSP/Dashboard**", timeout=config.MFA_TIMEOUT)
        print("MFA completed successfully! Device should now be trusted.")
    except Exception:
        if not _is_dashboard(page):
            raise MFARequiredError("MFA was not completed within 5 minutes")


def _do_login(page: Page) -> None:
    """Fill login form and submit."""
    # Fill email if the field is present
    email_input = page.locator('input[name="email"], input[type="email"], input[name="username"]').first
    email_input.wait_for(state="visible", timeout=config.LOAD_TIMEOUT)
    email_input.fill(config.USERNAME)

    # Some login flows have a "Continue" button before password
    continue_btn = page.locator('button:has-text("Continue"), button[type="submit"]').first
    continue_btn.click()
    time.sleep(3)

    # Check if we landed on dashboard, MFA, or password page
    if _is_dashboard(page):
        return
    if _is_mfa_page(page):
        _handle_mfa_wait(page)
        return

    # Fill password (may be on same or separate page)
    password_input = page.locator('input[name="password"], input[type="password"]').first
    password_input.wait_for(state="visible", timeout=config.LOAD_TIMEOUT)
    password_input.fill(config.PASSWORD)

    # Click sign in
    sign_in_btn = page.locator('button:has-text("Sign In"), button:has-text("Log In"), button[type="submit"]').first
    sign_in_btn.click()

    # Wait for navigation result
    time.sleep(5)

    if _is_dashboard(page):
        return
    if _is_mfa_page(page):
        _handle_mfa_wait(page)
        return

    # Wait for dashboard
    try:
        page.wait_for_url("**/Core/BSP/Dashboard**", timeout=config.NAV_TIMEOUT)
    except Exception:
        if _is_mfa_page(page):
            _handle_mfa_wait(page)
            return
        raise LoginError(f"Login did not reach dashboard. Current URL: {page.url}")


def navigate_to_invoices(page: Page) -> None:
    """Navigate to the Invoices / Checks tab."""
    page.goto(config.DASHBOARD_URL, wait_until="domcontentloaded", timeout=config.NAV_TIMEOUT)
    time.sleep(2)
    # Click the Invoices/Checks tab
    tab = page.get_by_role("tab", name="Invoices / Checks")
    tab.click()
    time.sleep(3)  # Wait for AG Grid to load


def navigate_to_invoice_summary(page: Page, invoice_id: int) -> None:
    """Navigate to an invoice summary page."""
    url = f"{config.ENERGYLINK_URL}/Invoice/InvoiceSummary.aspx?InvoiceId={invoice_id}&Context=Inbound"
    page.goto(url, wait_until="domcontentloaded", timeout=config.NAV_TIMEOUT)
    time.sleep(config.PAGE_DELAY)


def navigate_to_statement(page: Page, statement_id: int) -> None:
    """Navigate to a statement summary page."""
    url = f"{config.ENERGYLINK_URL}/Statement/StatementSummary.aspx?StatementId={statement_id}&Context=Inbound"
    page.goto(url, wait_until="domcontentloaded", timeout=config.NAV_TIMEOUT)
    time.sleep(config.PAGE_DELAY)
