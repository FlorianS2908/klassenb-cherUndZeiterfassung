from __future__ import annotations

from datetime import date

from app.browser.base import browser_page, click_first, fill_first, optional_click, select_or_fill
from app.browser.selectors_timebutler import TIMEBUTLER_SELECTORS
from app.config import get_settings
from app.models.schemas import ApiMessage
from app.services.screenshot_service import save_page_screenshot
from app.services.status_service import status_service


def _run_id() -> str:
    return status_service.status.run_id


async def _safe_screenshot(page, step: str) -> str:
    try:
        return str(await save_page_screenshot(page, _run_id(), step))
    except Exception:
        return ""


async def _login(page) -> None:
    settings = get_settings()
    await page.goto(settings.timebutler_url, wait_until="domcontentloaded")
    await _safe_screenshot(page, "timebutler_login_loaded")
    await fill_first(page, TIMEBUTLER_SELECTORS["username"], settings.effective_timebutler_username, "Benutzername")
    await fill_first(page, TIMEBUTLER_SELECTORS["password"], settings.effective_timebutler_password, "Passwort")
    await click_first(page, TIMEBUTLER_SELECTORS["login_button"], "Anmelden")
    await page.wait_for_load_state("networkidle")
    await _safe_screenshot(page, "timebutler_login_success")


async def _open_time_form(page) -> None:
    await optional_click(page, TIMEBUTLER_SELECTORS["own_data"])
    await optional_click(page, TIMEBUTLER_SELECTORS["work_time"])
    await page.wait_for_load_state("networkidle")
    await _safe_screenshot(page, "timebutler_form_opened")


async def _duplicate_present(page, target: str) -> bool:
    content = (await page.locator("body").inner_text()).lower()
    return target.lower() in content and any(word in content for word in ["bereits", "vorhanden", "existiert"])


async def _fill_form(page, payload: dict) -> None:
    target = str(payload.get("target_date") or date.today().isoformat())
    await fill_first(page, TIMEBUTLER_SELECTORS["date"], target, "Datum")
    await select_or_fill(page, TIMEBUTLER_SELECTORS["project"], str(payload.get("project", "FbW")), "Projekt")
    await select_or_fill(page, TIMEBUTLER_SELECTORS["category"], str(payload.get("category", "Training/Coaching")), "Kategorie")
    await fill_first(page, TIMEBUTLER_SELECTORS["start"], str(payload.get("start", "")), "Start")
    await fill_first(page, TIMEBUTLER_SELECTORS["end"], str(payload.get("end", "")), "Ende")
    await fill_first(page, TIMEBUTLER_SELECTORS["pause"], str(payload.get("pause", "")), "Pause")
    try:
        await fill_first(page, TIMEBUTLER_SELECTORS["remark"], str(payload.get("remark", "")), "Bemerkung")
    except Exception:
        pass
    await _safe_screenshot(page, "timebutler_form_filled")


async def prepare_timebutler(payload: dict) -> ApiMessage:
    async with browser_page() as page:
        try:
            await _login(page)
            await _open_time_form(page)
            duplicate = await _duplicate_present(page, str(payload.get("target_date", "")))
            await _safe_screenshot(page, "timebutler_duplicate_checked")
            if duplicate:
                return ApiMessage(ok=False, message="Bestehender Timebutler-Eintrag erkannt. Dry-Run abgebrochen.")
            await _fill_form(page, payload)
            screenshot = await _safe_screenshot(page, "timebutler_dry_run_preview")
            return ApiMessage(ok=True, message="Timebutler wurde im Dry-Run vorbereitet. Es wurde nicht gespeichert.", data={"payload": payload, "screenshot": screenshot})
        except Exception as exc:
            screenshot = await _safe_screenshot(page, "timebutler_error")
            return ApiMessage(ok=False, message=f"Timebutler-Dry-Run fehlgeschlagen: {exc}", data={"screenshot": screenshot})


async def submit_timebutler(payload: dict, review_confirmed: bool) -> ApiMessage:
    settings = get_settings()
    if not settings.auto_submit or not review_confirmed:
        return ApiMessage(ok=False, message="Finales Speichern gesperrt: AUTO_SUBMIT und Review-Bestaetigung erforderlich.")
    async with browser_page() as page:
        try:
            await _login(page)
            await _open_time_form(page)
            duplicate = await _duplicate_present(page, str(payload.get("target_date", "")))
            await _safe_screenshot(page, "timebutler_duplicate_checked")
            if duplicate:
                return ApiMessage(ok=False, message="Bestehender Timebutler-Eintrag erkannt. Speichern abgebrochen.")
            await _fill_form(page, payload)
            await click_first(page, TIMEBUTLER_SELECTORS["save_button"], "Speichern")
            await page.wait_for_load_state("networkidle")
            screenshot = await _safe_screenshot(page, "timebutler_saved")
            return ApiMessage(ok=True, message="Timebutler-Zeiteintrag wurde gespeichert.", data={"screenshot": screenshot})
        except Exception as exc:
            screenshot = await _safe_screenshot(page, "timebutler_submit_error")
            return ApiMessage(ok=False, message=f"Timebutler-Submit fehlgeschlagen: {exc}", data={"screenshot": screenshot})
