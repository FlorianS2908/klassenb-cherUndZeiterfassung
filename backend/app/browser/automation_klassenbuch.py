from __future__ import annotations

from app.browser.base import browser_page, click_first, fill_first, first_visible, optional_click, table_rows
from app.browser.selectors_klassenbuch import KLASSENBUCH_SELECTORS
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
    await page.goto(settings.klassenbuch_url, wait_until="domcontentloaded")
    await _safe_screenshot(page, "klassenbuch_login_loaded")
    await fill_first(page, KLASSENBUCH_SELECTORS["username"], settings.klassenbuch_username, "Benutzername")
    await fill_first(page, KLASSENBUCH_SELECTORS["password"], settings.klassenbuch_password, "Passwort")
    await click_first(page, KLASSENBUCH_SELECTORS["login_button"], "Anmelden")
    await page.wait_for_load_state("networkidle")
    await first_visible(page, KLASSENBUCH_SELECTORS["overview_markers"])
    await _safe_screenshot(page, "klassenbuch_login_success")


def _row_to_entry(text: str, index: int) -> dict[str, str]:
    parts = [part.strip() for part in text.splitlines() if part.strip()]
    joined = " | ".join(parts)
    return {
        "id": f"row-{index}",
        "row_index": str(index),
        "title": parts[0] if parts else joined[:80],
        "date": next((part for part in parts if "." in part or "-" in part), ""),
        "number": next((part for part in parts if part.isdigit()), ""),
        "room": "",
        "begin": "",
        "end": "",
        "einsatzzeit_von": "",
        "einsatzzeit_bis": "",
        "status": "Offen" if "offen" in joined.lower() else "",
        "raw": joined,
    }


async def load_open_klassenbuecher() -> list[dict[str, str]]:
    async with browser_page() as page:
        await _login(page)
        await first_visible(page, KLASSENBUCH_SELECTORS["overview_markers"])
        await _safe_screenshot(page, "klassenbuch_overview_loaded")
        entries: list[dict[str, str]] = []
        rows = await table_rows(page)
        for index, row in enumerate(rows):
            text = (await row.inner_text()).strip()
            if "offen" not in text.lower():
                continue
            entries.append(_row_to_entry(text, index))
        return entries


async def _select_entry(page, payload: dict) -> None:
    selected = payload.get("klassenbuch") or payload.get("selected_klassenbuch") or {}
    row_index = selected.get("row_index") or payload.get("row_index")
    rows = await table_rows(page)
    if row_index is not None and str(row_index).isdigit():
        row = rows[int(row_index)]
    else:
        needle = str(selected.get("raw") or selected.get("title") or payload.get("title") or "").lower()
        row = None
        for candidate in rows:
            if needle and needle in (await candidate.inner_text()).lower():
                row = candidate
                break
        if row is None:
            raise RuntimeError("Passendes offenes Klassenbuch konnte nicht eindeutig gefunden werden.")
    row_text = (await row.inner_text()).lower()
    if "offen" not in row_text:
        raise RuntimeError("Klassenbuch ist nicht im Status Offen.")
    for selector in KLASSENBUCH_SELECTORS["edit_button"]:
        candidate = row.locator(selector).first()
        try:
            if await candidate.is_visible() and await candidate.is_enabled():
                await candidate.click()
                break
        except Exception:
            continue
    else:
        raise RuntimeError("Bearbeiten-Button im offenen Klassenbuch-Eintrag nicht gefunden.")
    await page.wait_for_load_state("networkidle")
    await _safe_screenshot(page, "klassenbuch_entry_selected")


async def _fill_ue(page, payload: dict) -> None:
    await optional_click(page, KLASSENBUCH_SELECTORS["ue_tab"])
    await page.wait_for_load_state("networkidle")
    await _safe_screenshot(page, "klassenbuch_ue_opened")
    ue_items = payload.get("ue_items") or payload.get("unterrichtseinheiten") or []
    if len(ue_items) != 9:
        raise RuntimeError("Es muessen genau 9 UE fuer die Klassenbuch-Befuellung vorhanden sein.")
    fields = page.locator(", ".join(KLASSENBUCH_SELECTORS["content_fields"]))
    if await fields.count() < 9:
        raise RuntimeError("Nicht genug Lehrinhalt-Felder fuer 9 UE gefunden.")
    for index, item in enumerate(ue_items):
        content = item.get("content") or item.get("lehrinhalt") or ""
        await fields.nth(index).fill(str(content))
    await _safe_screenshot(page, "klassenbuch_ue_filled")


async def prepare_klassenbuch(payload: dict) -> ApiMessage:
    async with browser_page() as page:
        try:
            await _login(page)
            await _select_entry(page, payload)
            await _fill_ue(page, payload)
            await optional_click(page, KLASSENBUCH_SELECTORS["next_button"])
            await page.wait_for_load_state("networkidle")
            await _safe_screenshot(page, "klassenbuch_signature_opened")
            await _safe_screenshot(page, "klassenbuch_dry_run_preview")
            return ApiMessage(ok=True, message="Klassenbuch wurde im Dry-Run vorbereitet. Es wurde nicht signiert oder gespeichert.", data={"payload": payload})
        except Exception as exc:
            screenshot = await _safe_screenshot(page, "klassenbuch_error")
            return ApiMessage(ok=False, message=f"Klassenbuch-Dry-Run fehlgeschlagen: {exc}", data={"screenshot": screenshot})


async def submit_klassenbuch(payload: dict, review_confirmed: bool) -> ApiMessage:
    settings = get_settings()
    if not settings.auto_submit or not review_confirmed:
        return ApiMessage(ok=False, message="Finales Signieren gesperrt: AUTO_SUBMIT und Review-Bestaetigung erforderlich.")
    async with browser_page() as page:
        try:
            await _login(page)
            await _select_entry(page, payload)
            await _fill_ue(page, payload)
            await optional_click(page, KLASSENBUCH_SELECTORS["next_button"])
            await page.wait_for_load_state("networkidle")
            await fill_first(page, KLASSENBUCH_SELECTORS["signature"], settings.default_signature, "Signatur")
            await click_first(page, KLASSENBUCH_SELECTORS["sign_button"], "Signieren")
            await page.wait_for_load_state("networkidle")
            screenshot = await _safe_screenshot(page, "klassenbuch_submitted")
            return ApiMessage(ok=True, message="Klassenbuch wurde final signiert.", data={"screenshot": screenshot})
        except Exception as exc:
            screenshot = await _safe_screenshot(page, "klassenbuch_submit_error")
            return ApiMessage(ok=False, message=f"Klassenbuch-Submit fehlgeschlagen: {exc}", data={"screenshot": screenshot})
