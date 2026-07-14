from __future__ import annotations

import logging
import math
import re
from collections.abc import Sequence

from app.browser.base import browser_page, click_first, fill_first, first_visible, optional_click, table_rows
from app.browser.selectors_klassenbuch import KLASSENBUCH_SELECTORS
from app.config import get_settings
from app.models.schemas import StepState
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


def _set_signature_step(state: StepState, message: str) -> None:
    status_service.set_step("signature", state, message)


def _set_klassenbuch_step(state: StepState, message: str) -> None:
    status_service.set_step("klassenbuch", state, message)


async def _is_any_visible(page, selectors: list[str]) -> bool:
    for selector in selectors:
        try:
            locator = page.locator(selector).first()
            if await locator.is_visible():
                return True
        except Exception:
            continue
    return False


async def _locator_or_none(page, selectors: list[str]):
    for selector in selectors:
        try:
            locator = page.locator(selector).first()
            if await locator.is_visible() and await locator.is_enabled():
                return locator
        except Exception:
            continue
    return None


async def _first_visible_in(scope, selectors: list[str]):
    for selector in selectors:
        try:
            locator = scope.locator(selector).first()
            if await locator.is_visible():
                return locator
        except Exception:
            continue
    return None


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
    await select_teaching_formats_for_all_rows(page, len(ue_items))
    await _safe_screenshot(page, "klassenbuch_ue_filled")


async def _visible_locators(page, selectors: Sequence[str]) -> list:
    for selector in selectors:
        locators = page.locator(selector)
        count = await locators.count()
        visible = []
        for index in range(count):
            locator = locators.nth(index)
            try:
                if await locator.is_visible() and await locator.is_enabled():
                    visible.append(locator)
            except Exception:
                continue
        if visible:
            return visible
    return []


async def open_teaching_format_modal(page, row_index: int):
    controls = await _visible_locators(page, KLASSENBUCH_SELECTORS["teaching_format_fields"])
    if len(controls) <= row_index:
        await _safe_screenshot(page, "lernformat_modal_error")
        _set_klassenbuch_step(StepState.error, f"Lernformat-Feld fuer UE {row_index + 1} nicht gefunden.")
        raise RuntimeError(f"Lernformat-Feld fuer UE {row_index + 1} nicht gefunden.")
    await controls[row_index].click()
    modal = await _locator_or_none(page, KLASSENBUCH_SELECTORS["teaching_format_modal"][:4])
    if modal is None and await _is_any_visible(page, KLASSENBUCH_SELECTORS["teaching_format_modal"]):
        modal = page.locator("body")
    if modal is None:
        await _safe_screenshot(page, "lernformat_modal_error")
        _set_klassenbuch_step(StepState.error, f"Lernformat-Modal fuer UE {row_index + 1} wurde nicht geoeffnet.")
        raise RuntimeError(f"Lernformat-Modal fuer UE {row_index + 1} wurde nicht geoeffnet.")
    await _safe_screenshot(page, "lernformat_modal_open")
    return modal


async def _checkbox_for_label(scope, label_variants: Sequence[str]):
    for label in label_variants:
        try:
            checkbox = scope.get_by_label(re.compile(re.escape(label), re.IGNORECASE)).first()
            if await checkbox.is_visible() and await checkbox.is_enabled():
                return checkbox
        except Exception:
            pass
        try:
            label_locator = scope.locator("label").filter(has_text=re.compile(re.escape(label), re.IGNORECASE)).first()
            if await label_locator.is_visible():
                nested = label_locator.locator('input[type="checkbox"]').first()
                if await nested.count() and await nested.is_enabled():
                    return nested
                return label_locator
        except Exception:
            pass
        try:
            checkbox = scope.locator(f'input[type="checkbox"]:near(:text("{label}"))').first()
            if await checkbox.is_visible() and await checkbox.is_enabled():
                return checkbox
        except Exception:
            pass
    return None


async def _ensure_checkbox_checked(scope, label_variants: Sequence[str]) -> None:
    checkbox = await _checkbox_for_label(scope, label_variants)
    if checkbox is None:
        raise RuntimeError(f"Lernformat-Option nicht gefunden: {label_variants[0]}")
    try:
        if await checkbox.is_checked():
            return
        await checkbox.check()
        return
    except Exception:
        pass
    await checkbox.click()


async def set_teaching_formats(page, modal) -> None:
    await _ensure_checkbox_checked(modal, ["betreute Einzelarbeit", "Betreute Einzelarbeit"])
    await _ensure_checkbox_checked(
        modal,
        [
            "Aufgaben-/Uebungsbesprechung",
            "Aufgaben-/\u00dcbungsbesprechung",
            "Aufgabenbesprechung",
            "\u00dcbungsbesprechung",
        ],
    )
    await _safe_screenshot(page, "lernformat_modal_selected")
    apply_button = await _first_visible_in(modal, KLASSENBUCH_SELECTORS["teaching_format_apply"])
    if apply_button is None:
        apply_button = await _locator_or_none(page, KLASSENBUCH_SELECTORS["teaching_format_apply"])
    if apply_button is None:
        await _safe_screenshot(page, "lernformat_modal_error")
        _set_klassenbuch_step(StepState.error, "Uebernehmen-Button im Lernformat-Modal nicht gefunden.")
        raise RuntimeError("Uebernehmen-Button im Lernformat-Modal nicht gefunden.")
    await apply_button.click()
    tag_name = ""
    try:
        tag_name = await modal.evaluate("element => element.tagName.toLowerCase()")
    except Exception:
        tag_name = ""
    try:
        if tag_name == "body":
            await page.wait_for_timeout(400)
            if await apply_button.is_visible():
                raise RuntimeError("Uebernehmen-Button ist nach Klick weiter sichtbar.")
        else:
            await modal.wait_for(state="hidden", timeout=5000)
    except Exception as exc:
        await _safe_screenshot(page, "lernformat_modal_error")
        _set_klassenbuch_step(StepState.error, "Lernformat-Modal wurde nach Uebernehmen nicht geschlossen.")
        raise RuntimeError("Lernformat-Modal wurde nach Uebernehmen nicht geschlossen.") from exc
    await _safe_screenshot(page, "lernformat_modal_confirmed")


async def select_teaching_formats_for_row(page, row_index: int) -> None:
    modal = await open_teaching_format_modal(page, row_index)
    await set_teaching_formats(page, modal)


async def select_teaching_formats_for_all_rows(page, row_count: int = 9) -> None:
    _set_klassenbuch_step(StepState.running, "Lernformate werden gesetzt.")
    for index in range(row_count):
        await select_teaching_formats_for_row(page, index)
    _set_klassenbuch_step(StepState.running, "Lernformate wurden fuer alle UE gesetzt.")


async def _save_ue(page) -> None:
    status_service.set_step("klassenbuch", StepState.running, "Unterrichtseinheiten werden gespeichert.")
    await click_first(page, KLASSENBUCH_SELECTORS["save_button"], "Speichern")
    await page.wait_for_load_state("networkidle")
    status_service.set_step("klassenbuch", StepState.success, "Alle 9 UE wurden gespeichert.")


async def _open_signature_step(page) -> None:
    _set_signature_step(StepState.running, "Signaturseite gesucht.")
    await optional_click(page, KLASSENBUCH_SELECTORS["next_button"])
    await page.wait_for_load_state("networkidle")
    await _safe_screenshot(page, "klassenbuch_signature_page_loaded")
    await _safe_screenshot(page, "signatur_page_loaded")


async def _guard_manual_signature_challenge(page) -> None:
    if await _is_any_visible(page, KLASSENBUCH_SELECTORS["manual_signature_markers"]):
        await _safe_screenshot(page, "klassenbuch_signature_error")
        _set_signature_step(StepState.manual_review, "Manuelle Signatur erforderlich.")
        raise RuntimeError("Manuelle Signatur erforderlich: 2FA, TAN, Zertifikat oder externer Signaturdienst erkannt.")


async def _recognize_signature_page(page) -> None:
    await _guard_manual_signature_challenge(page)
    marker_found = await _is_any_visible(page, KLASSENBUCH_SELECTORS["signature_page_markers"])
    signature_canvas = await _locator_or_none(page, KLASSENBUCH_SELECTORS["signature_canvas"])
    signature_field = await _locator_or_none(page, KLASSENBUCH_SELECTORS["signature"])
    sign_button = await _locator_or_none(page, KLASSENBUCH_SELECTORS["sign_button"])
    if not marker_found or (signature_canvas is None and signature_field is None and sign_button is None):
        await _safe_screenshot(page, "klassenbuch_signature_error")
        _set_signature_step(StepState.manual_review, "Signaturseite nicht eindeutig erkannt.")
        raise RuntimeError("Signaturseite nicht eindeutig erkannt.")
    _set_signature_step(StepState.success, "Signaturseite erkannt.")


def _signature_points() -> list[tuple[float, float]]:
    return [
        (0.08, 0.55), (0.11, 0.38), (0.20, 0.34), (0.25, 0.43), (0.20, 0.52), (0.12, 0.56), (0.08, 0.65),
        (0.14, 0.72), (0.25, 0.69), (0.31, 0.58), (0.29, 0.48), (0.21, 0.48), (0.18, 0.56), (0.22, 0.66),
        (0.31, 0.66), (0.36, 0.53), (0.35, 0.44), (0.34, 0.64), (0.41, 0.62), (0.45, 0.51), (0.44, 0.61),
        (0.48, 0.67), (0.54, 0.61), (0.55, 0.50), (0.51, 0.48), (0.48, 0.57), (0.50, 0.67), (0.58, 0.63),
        (0.62, 0.48), (0.66, 0.37), (0.70, 0.32), (0.69, 0.47), (0.63, 0.48), (0.62, 0.59), (0.68, 0.63),
        (0.75, 0.57), (0.79, 0.45), (0.82, 0.36), (0.84, 0.34), (0.82, 0.49), (0.76, 0.50), (0.75, 0.60),
        (0.81, 0.66), (0.88, 0.61), (0.90, 0.52), (0.86, 0.50), (0.84, 0.59), (0.89, 0.65), (0.95, 0.59),
    ]


def _interpolate_points(points: Sequence[tuple[float, float]], max_step: float = 0.018) -> list[tuple[float, float]]:
    interpolated: list[tuple[float, float]] = []
    for start, end in zip(points, points[1:]):
        if not interpolated:
            interpolated.append(start)
        distance = math.dist(start, end)
        steps = max(1, math.ceil(distance / max_step))
        for step in range(1, steps + 1):
            ratio = step / steps
            interpolated.append((start[0] + (end[0] - start[0]) * ratio, start[1] + (end[1] - start[1]) * ratio))
    return interpolated


async def draw_signature_schaffer(page, canvas_locator=None) -> None:
    canvas = canvas_locator or await _locator_or_none(page, KLASSENBUCH_SELECTORS["signature_canvas"])
    if canvas is None:
        await _safe_screenshot(page, "signatur_error")
        _set_signature_step(StepState.error, "Signatur-Zeichenflaeche nicht gefunden.")
        raise RuntimeError("Signatur-Zeichenflaeche nicht gefunden.")
    box = await canvas.bounding_box()
    if not box or box["width"] < 80 or box["height"] < 30:
        await _safe_screenshot(page, "signatur_error")
        _set_signature_step(StepState.error, "Signatur-Zeichenflaeche hat keine plausible Groesse.")
        raise RuntimeError("Signatur-Zeichenflaeche hat keine plausible Groesse.")
    await _safe_screenshot(page, "signatur_canvas_detected")
    margin_x = box["width"] * 0.08
    margin_y = box["height"] * 0.18
    draw_width = box["width"] - margin_x * 2
    draw_height = box["height"] - margin_y * 2
    points = _interpolate_points(_signature_points())
    start_x = box["x"] + margin_x + points[0][0] * draw_width
    start_y = box["y"] + margin_y + points[0][1] * draw_height
    await page.mouse.move(start_x, start_y)
    await page.mouse.down()
    for point_x, point_y in points[1:]:
        await page.mouse.move(box["x"] + margin_x + point_x * draw_width, box["y"] + margin_y + point_y * draw_height, steps=2)
    await page.mouse.up()
    await _safe_screenshot(page, "signatur_schaffer_drawn")
    _set_signature_step(StepState.success, "Signatur Schaffer wurde eingezeichnet.")


async def _fill_signature(page, allow_overwrite: bool, draw_canvas: bool = True) -> None:
    if draw_canvas:
        canvas = await _locator_or_none(page, KLASSENBUCH_SELECTORS["signature_canvas"])
        if canvas is not None:
            _set_signature_step(StepState.running, "Signatur-Zeichenflaeche gefunden.")
            await draw_signature_schaffer(page, canvas)
            return
    settings = get_settings()
    locator = await _locator_or_none(page, KLASSENBUCH_SELECTORS["signature"])
    if locator is None:
        await _safe_screenshot(page, "klassenbuch_signature_error")
        _set_signature_step(StepState.error, "Signaturfeld nicht gefunden.")
        raise RuntimeError("Signaturfeld nicht gefunden.")
    current = ""
    try:
        current = (await locator.input_value()).strip()
    except Exception:
        try:
            current = (await locator.inner_text()).strip()
        except Exception:
            current = ""
    if current and not allow_overwrite:
        await _safe_screenshot(page, "klassenbuch_signature_error")
        _set_signature_step(StepState.manual_review, "Signaturfeld ist bereits befuellt.")
        raise RuntimeError("Signaturfeld ist bereits befuellt. Im Dry-Run wird nicht ueberschrieben.")
    _set_signature_step(StepState.running, "Signaturfeld gefunden.")
    await locator.fill(settings.default_signature)
    await _safe_screenshot(page, "klassenbuch_signature_filled")
    _set_signature_step(StepState.success, "Signatur eingetragen.")


async def _confirm_signature_checkbox(page) -> None:
    checkbox = await _locator_or_none(page, KLASSENBUCH_SELECTORS["signature_confirm_checkbox"])
    if checkbox is not None:
        try:
            if not await checkbox.is_checked():
                await checkbox.check()
        except Exception:
            await checkbox.click()


async def _finalize_signature(page) -> str:
    await _guard_manual_signature_challenge(page)
    _set_signature_step(StepState.running, "Finale Signatur gestartet.")
    await _confirm_signature_checkbox(page)
    await click_first(page, KLASSENBUCH_SELECTORS["sign_button"], "Signieren")
    await page.wait_for_load_state("networkidle")
    if not await _is_any_visible(page, KLASSENBUCH_SELECTORS["signature_success"]):
        await _safe_screenshot(page, "klassenbuch_signature_error")
        _set_signature_step(StepState.error, "Signatur fehlgeschlagen.")
        raise RuntimeError("Keine eindeutige Erfolgsmeldung nach dem Signieren erkannt.")
    await _safe_screenshot(page, "signatur_submit_success")
    screenshot = await _safe_screenshot(page, "klassenbuch_signed_success")
    _set_signature_step(StepState.success, "Klassenbuch signiert.")
    logging.info("Klassenbuch wurde final signiert.")
    return screenshot


def _validate_signature_submit_allowed(payload: dict, review_confirmed: bool, signature_confirmed: bool) -> str | None:
    settings = get_settings()
    if not settings.auto_submit:
        return "Finales Signieren gesperrt: AUTO_SUBMIT=true ist erforderlich."
    if not review_confirmed:
        return "Finales Signieren gesperrt: Review-Bestaetigung erforderlich."
    if not signature_confirmed:
        return "Finales Signieren gesperrt: Signatur-Bestaetigung erforderlich."
    if status_service.status.blocked:
        return "Finales Signieren gesperrt: Zieltag ist gesperrt."
    ue_items = payload.get("ue_items") or payload.get("unterrichtseinheiten") or []
    if len(ue_items) != 9:
        return "Finales Signieren gesperrt: Es muessen genau 9 UE vorhanden sein."
    selected = payload.get("klassenbuch") or payload.get("selected_klassenbuch") or {}
    if selected and str(selected.get("status", "")).lower() != "offen":
        return "Finales Signieren gesperrt: Klassenbuch ist nicht im Status Offen."
    return None


async def prepare_klassenbuch(payload: dict) -> ApiMessage:
    async with browser_page() as page:
        try:
            await _login(page)
            await _select_entry(page, payload)
            await _fill_ue(page, payload)
            await _open_signature_step(page)
            await _recognize_signature_page(page)
            try:
                await _fill_signature(page, allow_overwrite=False)
            except RuntimeError as exc:
                if "bereits befuellt" not in str(exc):
                    raise
            screenshot = await _safe_screenshot(page, "klassenbuch_signature_dry_run")
            _set_signature_step(StepState.skipped, "Dry-Run: Signatur vorbereitet, aber nicht abgeschlossen.")
            return ApiMessage(ok=True, message="Dry-Run: Signatur vorbereitet, aber nicht abgeschlossen.", data={"payload": payload, "screenshot": screenshot})
        except Exception as exc:
            screenshot = await _safe_screenshot(page, "klassenbuch_signature_error")
            return ApiMessage(ok=False, message=f"Klassenbuch-Dry-Run fehlgeschlagen: {exc}", data={"screenshot": screenshot})


async def submit_klassenbuch(payload: dict, review_confirmed: bool, signature_confirmed: bool = False) -> ApiMessage:
    blocked_reason = _validate_signature_submit_allowed(payload, review_confirmed, signature_confirmed)
    if blocked_reason:
        return ApiMessage(ok=False, message=blocked_reason)
    async with browser_page() as page:
        try:
            await _login(page)
            await _select_entry(page, payload)
            await _fill_ue(page, payload)
            await _save_ue(page)
            await _open_signature_step(page)
            await _recognize_signature_page(page)
            await _fill_signature(page, allow_overwrite=True)
            screenshot = await _finalize_signature(page)
            return ApiMessage(ok=True, message="Klassenbuch wurde final signiert.", data={"screenshot": screenshot})
        except Exception as exc:
            screenshot = await _safe_screenshot(page, "klassenbuch_signature_error")
            _set_signature_step(StepState.error, "Signatur fehlgeschlagen.")
            return ApiMessage(ok=False, message=f"Klassenbuch-Submit fehlgeschlagen: {exc}", data={"screenshot": screenshot})
