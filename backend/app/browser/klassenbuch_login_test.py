from __future__ import annotations

from app.browser.base import browser_page, click_first, fill_first
from app.browser.selectors_klassenbuch import KLASSENBUCH_SELECTORS
from app.config import get_settings
from app.services.credentials_service import get_klassenbuch_credential_status, get_klassenbuch_credentials


async def _page_has_login_error(page) -> bool:
    error_texts = [
        "Benutzname oder Passwort nicht korrekt",
        "Benutzername oder Passwort nicht korrekt",
        "Login fehlgeschlagen",
        "Anmeldung fehlgeschlagen",
        "Passwort nicht korrekt",
    ]
    for text in error_texts:
        try:
            if await page.get_by_text(text, exact=False).count():
                return True
        except Exception:
            continue
    return False


async def test_klassenbuch_login_only(username: str | None = None, password: str | None = None, url: str | None = None) -> dict:
    credential_source = "payload" if username and password else get_klassenbuch_credential_status().get("source", "missing")
    if not username or not password:
        username, password = get_klassenbuch_credentials()
    login_url = url or get_settings().klassenbuch_url
    async with browser_page() as page:
        await page.goto(login_url, wait_until="domcontentloaded")
        await fill_first(page, KLASSENBUCH_SELECTORS["username"], username, "Benutzername")
        await fill_first(page, KLASSENBUCH_SELECTORS["password"], password, "Passwort")
        await click_first(page, KLASSENBUCH_SELECTORS["login_button"], "Anmelden")
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        current_url = page.url.lower()
        login_error = "/login?error" in current_url or await _page_has_login_error(page)
        if login_error:
            return {
                "ok": False,
                "message": "Login fehlgeschlagen.",
                "problem_category": "login",
                "credential_source_used": credential_source,
            }
        if "/login" not in current_url:
            return {
                "ok": True,
                "message": "Login erfolgreich.",
                "problem_category": "",
                "credential_source_used": credential_source,
            }
        return {
            "ok": False,
            "message": "Login konnte nicht eindeutig bestaetigt werden.",
            "problem_category": "login",
            "credential_source_used": credential_source,
        }
