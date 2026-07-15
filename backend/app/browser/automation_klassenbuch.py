from __future__ import annotations

import logging
import math
import re
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

from app.browser.base import browser_page, click_first, fill_first, first_locator, first_visible, optional_click, table_rows
from app.browser.selectors_klassenbuch import KLASSENBUCH_SELECTORS
from app.config import get_settings, resolve_project_path
from app.models.schemas import StepState
from app.models.schemas import ApiMessage
from app.services.credentials_service import get_klassenbuch_credentials
from app.services.diagnostics_service import append_console_message, append_network_event, categorize_problem, create_diagnostic_run, explain_exception, save_step_snapshot, write_steps, write_summary
from app.services.screenshot_service import save_page_screenshot, screenshot_name
from app.services.signature_profile_service import read_signature_profile
from app.services.status_service import status_service


OVERVIEW_TABS = [
    ("offene", "offene Themendokumentationen"),
    ("ueberfaellige", "\u00dcberf\u00e4llige Themendokumentationen"),
    ("freigegebene", "Freigegebene Themendokumentationen"),
    ("korrektur", "Korrektur notwendig"),
]


class KlassenbuchLoadError(RuntimeError):
    def __init__(self, message: str, diagnostics: dict | None = None):
        super().__init__(message)
        self.diagnostics = diagnostics or {}


class KlassenbuchDiagnosticsRun:
    def __init__(self, run_id: str, action: str):
        self.run_id = run_id
        self.action = action
        self.run_dir = create_diagnostic_run("klassenbuch", run_id)
        self.started_at = datetime.now().isoformat(timespec="seconds")
        self.steps: list[dict[str, Any]] = []
        self.trace_file = ""
        self.trace_error = ""
        self.login_success = False
        self.overview_loaded = False
        self.tabs: dict[str, dict[str, Any]] = {}

    @property
    def relative_folder(self) -> str:
        return str(Path("diagnostics") / "klassenbuch" / self.run_id)


def _run_id() -> str:
    return status_service.status.run_id


def _diagnostic_run_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _public_url(value: str) -> str:
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


async def _diag_step(page, diag: KlassenbuchDiagnosticsRun | None, step: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    if diag is None:
        return {}
    entry = await save_step_snapshot(page, diag.run_dir, step, extra)
    diag.steps.append(entry)
    write_steps(diag.run_dir, diag.steps)
    return entry


def _attach_diagnostic_listeners(page, diag: KlassenbuchDiagnosticsRun) -> None:
    page.on("console", lambda message: append_console_message(diag.run_dir, f"{message.type}: {message.text[:1000]}"))
    page.on("pageerror", lambda error: append_console_message(diag.run_dir, f"pageerror: {str(error)[:1000]}"))
    page.on(
        "requestfailed",
        lambda request: append_network_event(
            diag.run_dir,
            {
                "event": "requestfailed",
                "method": request.method,
                "url": _public_url(request.url),
                "resource_type": request.resource_type,
                "error_text": request.failure or "",
            },
        ),
    )
    page.on(
        "response",
        lambda response: append_network_event(
            diag.run_dir,
            {
                "event": "response",
                "method": response.request.method,
                "url": _public_url(response.url),
                "resource_type": response.request.resource_type,
                "status": response.status,
            },
        ),
    )


async def _start_trace(page, diag: KlassenbuchDiagnosticsRun) -> None:
    try:
        await page.context.tracing.start(screenshots=True, snapshots=True, sources=False)
    except Exception as exc:
        diag.trace_error = _exception_message(exc, "Trace konnte nicht gestartet werden")


async def _stop_trace(page, diag: KlassenbuchDiagnosticsRun) -> None:
    if diag.trace_error:
        return
    try:
        trace_path = diag.run_dir / "playwright_trace.zip"
        await page.context.tracing.stop(path=str(trace_path))
        diag.trace_file = str(trace_path)
    except Exception as exc:
        diag.trace_error = _exception_message(exc, "Trace konnte nicht gespeichert werden")


async def _write_diagnostic_summary(
    page,
    diag: KlassenbuchDiagnosticsRun,
    *,
    success: bool,
    error_message: str = "",
    exception_type: str = "",
    entries_returned: int = 0,
    diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    diagnostics = diagnostics or {}
    counters = diagnostics.copy()
    if page is not None:
        try:
            counters.update(await _overview_diagnostics(page, diagnostics.get("screenshot_path", ""), diagnostics.get("html_snapshot_path", "")))
        except Exception:
            pass
    screenshots = [step.get("screenshot_path", "") for step in diag.steps if step.get("screenshot_path")]
    html_snapshots = [step.get("html_snapshot_path", "") for step in diag.steps if step.get("html_snapshot_path")]
    probable_cause = diagnostics.get("probable_cause", "")
    next_action = diagnostics.get("next_action", "")
    if exception_type:
        class _NamedException(Exception):
            pass

        _NamedException.__name__ = exception_type
        diagnostic_exception = _NamedException(error_message)
        fallback_cause, fallback_action = explain_exception(diagnostic_exception)
        probable_cause = probable_cause or fallback_cause
        next_action = next_action or fallback_action
        problem_context = categorize_problem(diagnostics.get("step", ""), diagnostic_exception)
    else:
        problem_context = {}
    summary = {
        "run_id": diag.run_id,
        "module": "klassenbuch",
        "action": diag.action,
        "started_at": diag.started_at,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "success": success,
        "error_message": error_message,
        "exception_type": exception_type,
        "current_url": counters.get("current_url", ""),
        "page_title": counters.get("page_title", ""),
        "setup_complete": True,
        "login_success": diag.login_success,
        "overview_loaded": diag.overview_loaded,
        "tabs": diag.tabs,
        "tables_found": counters.get("table_count", 0),
        "rows_found": counters.get("row_count", 0),
        "tbody_rows_found": counters.get("tbody_row_count", 0),
        "headers_found": counters.get("headers_found", []),
        "edit_links_found": counters.get("found_edit_links", 0),
        "entries_returned": entries_returned,
        "screenshots": screenshots,
        "html_snapshots": html_snapshots,
        "trace_file": diag.trace_file,
        "trace_error": diag.trace_error,
        "probable_cause": probable_cause,
        "next_action": next_action,
        **problem_context,
        "diagnostics_folder": diag.relative_folder,
        "summary_path": str(diag.run_dir / "summary.json"),
        "steps_path": str(diag.run_dir / "steps.json"),
        "console_log": str(diag.run_dir / "console.log"),
        "network_log": str(diag.run_dir / "network.log"),
        "notes": [],
    }
    write_steps(diag.run_dir, diag.steps)
    write_summary(diag.run_dir, summary)
    return summary


async def _safe_screenshot(page, step: str) -> str:
    try:
        return str(await save_page_screenshot(page, _run_id(), step))
    except Exception:
        return ""


async def save_html_snapshot(page, name: str) -> str:
    try:
        settings = get_settings()
        folder = resolve_project_path(get_settings().screenshot_folder)
        folder.mkdir(parents=True, exist_ok=True)
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)
        path = folder / f"{_run_id()}_{safe_name}.html"
        html = await page.content()
        secrets = [settings.klassenbuch_password, settings.timebutler_password]
        try:
            _, klassenbuch_password = get_klassenbuch_credentials()
            secrets.append(klassenbuch_password)
        except Exception:
            pass
        for secret in secrets:
            if secret:
                html = html.replace(secret, "***")
        html = re.sub(r'(<input[^>]+type=["\']?password["\']?[^>]*value=)["\'][^"\']*["\']', r'\1"***"', html, flags=re.IGNORECASE)
        path.write_text(html, encoding="utf-8")
        return str(path)
    except Exception:
        return ""


async def _safe_html_snapshot(page, step: str) -> str:
    return await save_html_snapshot(page, step)


def _exception_message(exc: Exception, fallback: str) -> str:
    text = str(exc).strip()
    if text:
        return text
    return f"{fallback} ({type(exc).__name__})"


async def _failure_diagnostics(page, step: str, exc: Exception | None = None) -> dict:
    screenshot_path = await _safe_screenshot(page, f"klassenbuch_{step}_error")
    html_snapshot_path = await _safe_html_snapshot(page, f"klassenbuch_{step}_error")
    diagnostics = await _overview_diagnostics(page, screenshot_path, html_snapshot_path)
    diagnostics["step"] = step
    if exc is not None:
        diagnostics["exception_type"] = type(exc).__name__
    return diagnostics


async def _raise_load_error(page, step: str, message: str, exc: Exception | None = None) -> None:
    detail = message if exc is None else f"{message}: {_exception_message(exc, 'unbekannter Fehler')}"
    raise KlassenbuchLoadError(detail, await _failure_diagnostics(page, step, exc))


def _set_signature_step(state: StepState, message: str) -> None:
    status_service.set_step("signature", state, message)


def _set_klassenbuch_step(state: StepState, message: str) -> None:
    status_service.set_step("klassenbuch", state, message)


async def _is_any_visible(page, selectors: list[str]) -> bool:
    for selector in selectors:
        try:
            locator = first_locator(page, selector)
            if await locator.is_visible():
                return True
        except Exception:
            continue
    return False


async def _locator_or_none(page, selectors: list[str]):
    for selector in selectors:
        try:
            locator = first_locator(page, selector)
            if await locator.is_visible() and await locator.is_enabled():
                return locator
        except Exception:
            continue
    return None


async def _first_visible_in(scope, selectors: list[str]):
    for selector in selectors:
        try:
            locator = first_locator(scope, selector)
            if await locator.is_visible():
                return locator
        except Exception:
            continue
    return None


def _storage_state_path() -> Path:
    return resolve_project_path("runtime/klassenbuch_storage_state.json")


async def _save_storage_state(page) -> None:
    try:
        path = _storage_state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        await page.context.storage_state(path=str(path))
    except Exception:
        logging.exception("Klassenbuch storage_state konnte nicht gespeichert werden.")


async def _login_error_text(page) -> str:
    selectors = [
        ".alert-danger",
        ".alert-error",
        ".error",
        ".invalid-feedback",
        '[role="alert"]',
        'text="Login fehlgeschlagen"',
        'text="Anmeldung fehlgeschlagen"',
        'text="ungültig"',
        'text="ungueltig"',
    ]
    messages: list[str] = []
    for selector in selectors:
        try:
            locators = page.locator(selector)
            for index in range(min(await locators.count(), 5)):
                locator = locators.nth(index)
                if await locator.is_visible():
                    text = (await locator.inner_text()).strip()
                    if text:
                        messages.append(text)
        except Exception:
            continue
    return " | ".join(dict.fromkeys(messages))


async def _wait_for_login_result(page) -> bool:
    try:
        await page.wait_for_function(
            """() => {
                const text = document.body?.innerText || "";
                return !location.href.toLowerCase().includes('/login')
                    || location.href.toLowerCase().includes('/overview')
                    || text.includes('Übersicht')
                    || text.includes('Uebersicht')
                    || text.includes('Themendokumentationen');
            }""",
            timeout=10000,
        )
    except Exception:
        pass
    if "/login" not in page.url.lower():
        return True
    return await _is_any_visible(page, KLASSENBUCH_SELECTORS["overview_url_marker"])


async def _login(page, diag: KlassenbuchDiagnosticsRun | None = None, credentials: tuple[str, str] | None = None) -> None:
    settings = get_settings()
    username, password = credentials or get_klassenbuch_credentials()
    try:
        if _storage_state_path().exists():
            await page.goto(_overview_url(), wait_until="domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            if "/login" not in page.url.lower() and await _is_any_visible(page, KLASSENBUCH_SELECTORS["overview_url_marker"]):
                await _safe_screenshot(page, "klassenbuch_session_reused")
                await _diag_step(page, diag, "session_reused")
                if diag:
                    diag.login_success = True
                    diag.overview_loaded = True
                return
            await _diag_step(page, diag, "session_expired")
        await page.goto(settings.klassenbuch_url, wait_until="domcontentloaded")
        await _safe_screenshot(page, "klassenbuch_login_loaded")
        await _diag_step(page, diag, "login_loaded")
        if "/login" not in page.url.lower():
            await _safe_screenshot(page, "klassenbuch_login_success")
            await _diag_step(page, diag, "login_success")
            await _save_storage_state(page)
            if diag:
                diag.login_success = True
            return
        await fill_first(page, KLASSENBUCH_SELECTORS["username"], username, "Benutzername")
        await fill_first(page, KLASSENBUCH_SELECTORS["password"], password, "Passwort")
        await click_first(page, KLASSENBUCH_SELECTORS["login_button"], "Anmelden")
        await _diag_step(page, diag, "login_submitted")
        try:
            login_ok = await _wait_for_login_result(page)
        except Exception:
            login_ok = False
        if not login_ok:
            login_message = await _login_error_text(page)
            detail = "Login ins Klassenbuch fehlgeschlagen"
            if login_message:
                detail = f"{detail}: {login_message}"
            await _diag_step(page, diag, "login_failed", {"login_error": login_message})
            await _raise_load_error(page, "login_failed", detail)
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        await _safe_screenshot(page, "klassenbuch_login_success")
        await _diag_step(page, diag, "login_success")
        await _save_storage_state(page)
        if diag:
            diag.login_success = True
    except KlassenbuchLoadError:
        raise
    except Exception as exc:
        await _raise_load_error(page, "login_failed", "Login ins Klassenbuch fehlgeschlagen", exc)


async def test_klassenbuch_login(credentials: tuple[str, str] | None = None) -> dict:
    diag = KlassenbuchDiagnosticsRun(_diagnostic_run_id(), "test_klassenbuch_login")
    async with browser_page(storage_state_path=_storage_state_path()) as page:
        _attach_diagnostic_listeners(page, diag)
        await _start_trace(page, diag)
        try:
            await _login(page, diag, credentials)
            await _stop_trace(page, diag)
            summary = await _write_diagnostic_summary(page, diag, success=True, entries_returned=0)
            return {"ok": True, "diagnostics": summary}
        except KlassenbuchLoadError as exc:
            await _stop_trace(page, diag)
            summary = await _write_diagnostic_summary(page, diag, success=False, error_message=str(exc), exception_type=exc.diagnostics.get("exception_type", type(exc).__name__), diagnostics=exc.diagnostics)
            exc.diagnostics.update(summary)
            raise


def _overview_url() -> str:
    settings = get_settings()
    parsed = urlsplit(settings.klassenbuch_url or "https://klassenbuch.gfn.de/login")
    if not parsed.scheme or not parsed.netloc:
        return "https://klassenbuch.gfn.de/overview"
    return urlunsplit((parsed.scheme, parsed.netloc, "/overview", "", ""))


async def _open_overview(page, diag: KlassenbuchDiagnosticsRun | None = None) -> None:
    await _diag_step(page, diag, "overview_open_started")
    await page.goto(_overview_url(), wait_until="domcontentloaded")
    try:
        await page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass
    if "/login" in page.url.lower():
        await _raise_load_error(page, "overview_loaded", "Login ins Klassenbuch fehlgeschlagen")
    if not await _is_any_visible(page, KLASSENBUCH_SELECTORS["overview_url_marker"]):
        await _raise_load_error(page, "overview_loaded", "Timeout beim Warten auf Uebersichtstabelle")
    await _safe_screenshot(page, "klassenbuch_overview_loaded")
    await _diag_step(page, diag, "overview_loaded")
    if diag:
        diag.overview_loaded = True


def _normalize_table_key(value: str) -> str:
    normalized = value.strip().lower()
    replacements = {
        "\u00e4": "ae",
        "\u00f6": "oe",
        "\u00fc": "ue",
        "\u00df": "ss",
        "\u00c4": "ae",
        "\u00d6": "oe",
        "\u00dc": "ue",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[^a-z0-9 ]+", "", normalized).strip()
    aliases = {
        "raum": "raum",
        "nummer": "nummer",
        "nr": "nummer",
        "titel": "titel",
        "beginn": "beginn",
        "begin": "beginn",
        "ende": "ende",
        "einsatzzeit von": "einsatzzeit_von",
        "einsatzzeitvon": "einsatzzeit_von",
        "von": "einsatzzeit_von",
        "einsatzzeit bis": "einsatzzeit_bis",
        "einsatzzeitbis": "einsatzzeit_bis",
        "bis": "einsatzzeit_bis",
        "status": "status",
        "datum": "datum",
        "bearbeiten": "bearbeiten",
        "aktion": "bearbeiten",
        "aktionen": "bearbeiten",
    }
    return aliases.get(normalized, normalized.replace(" ", "_"))


async def _visible_table(page):
    tables = page.locator("table")
    for index in range(await tables.count()):
        table = tables.nth(index)
        try:
            if await table.is_visible() and await table.locator("tr").count():
                return table
        except Exception:
            continue
    return None


async def read_table_headers(page) -> dict[str, int]:
    table = await _visible_table(page)
    if table is None:
        return {}
    header_cells = table.locator("thead th")
    if not await header_cells.count():
        header_cells = first_locator(table, "tr").locator("th")
    if not await header_cells.count():
        header_cells = first_locator(table, "tr").locator("td")
    headers: dict[str, int] = {}
    for index in range(await header_cells.count()):
        text = (await header_cells.nth(index).inner_text()).strip()
        key = _normalize_table_key(text)
        if key:
            headers[key] = index
    return headers


def _cell_value(cells: list[str], headers: dict[str, int], key: str) -> str:
    index = headers.get(key)
    if index is None or index >= len(cells):
        return ""
    return cells[index].strip()


def _tab_key(tab_name: str) -> str:
    normalized = _normalize_table_key(tab_name)
    if "ueberfaellige" in normalized:
        return "ueberfaellige"
    if "freigegebene" in normalized:
        return "freigegebene"
    if "korrektur" in normalized:
        return "korrektur"
    return "offene"


def _extract_edit_action_index(onclick: str) -> str:
    match = re.search(r"forwardToWizardWithPreselection\((\d+)\)", onclick or "")
    return match.group(1) if match else ""


async def _row_edit_action(row) -> tuple[bool, str, str, str]:
    for selector in KLASSENBUCH_SELECTORS["edit_button"]:
        try:
            locator = first_locator(row, selector)
            if await locator.count() and await locator.is_visible():
                href = ""
                onclick = ""
                try:
                    href = await locator.get_attribute("href") or ""
                except Exception:
                    href = ""
                try:
                    onclick = await locator.get_attribute("onclick") or ""
                except Exception:
                    onclick = ""
                if not href:
                    try:
                        parent_link = first_locator(locator, "xpath=ancestor-or-self::a[1]")
                        href = await parent_link.get_attribute("href") or ""
                        onclick = onclick or await parent_link.get_attribute("onclick") or ""
                    except Exception:
                        href = ""
                if href and href != "#":
                    href = urljoin(get_settings().klassenbuch_url, href)
                else:
                    href = ""
                return True, href, onclick, _extract_edit_action_index(onclick)
        except Exception:
            continue
    return False, "", "", ""


async def read_table_by_headers(page, tab_name: str, diag: KlassenbuchDiagnosticsRun | None = None) -> list[dict]:
    table = await _visible_table(page)
    if table is None:
        await _diag_step(page, diag, f"tab_{_tab_key(tab_name)}_table_read", {"headers_found": [], "entries_count": 0})
        return []
    headers = await read_table_headers(page)
    rows = table.locator("tbody tr")
    if not await rows.count():
        rows = table.locator("tr")
    entries: list[dict] = []
    for index in range(await rows.count()):
        row = rows.nth(index)
        if await row.locator("th").count():
            continue
        cells_locator = row.locator("td")
        cell_count = await cells_locator.count()
        if not cell_count:
            continue
        cells = [(await cells_locator.nth(cell_index).inner_text()).strip() for cell_index in range(cell_count)]
        raw = " | ".join(cell for cell in cells if cell)
        if not raw:
            continue
        editable, edit_href, edit_onclick, edit_action_index = await _row_edit_action(row)
        row_index = ""
        try:
            row_index = await row.get_attribute("data-index") or ""
        except Exception:
            row_index = ""
        row_index = row_index or str(index)
        if headers:
            entry = {
                "tab": tab_name,
                "raum": _cell_value(cells, headers, "raum") or "unbekannt",
                "nummer": _cell_value(cells, headers, "nummer"),
                "titel": _cell_value(cells, headers, "titel"),
                "beginn": _cell_value(cells, headers, "beginn"),
                "ende": _cell_value(cells, headers, "ende"),
                "einsatzzeit_von": _cell_value(cells, headers, "einsatzzeit_von"),
                "einsatzzeit_bis": _cell_value(cells, headers, "einsatzzeit_bis"),
                "status": _cell_value(cells, headers, "status"),
                "datum": _cell_value(cells, headers, "datum"),
                "editable": editable,
                "edit_href": edit_href,
                "edit_onclick": edit_onclick,
                "edit_action_index": edit_action_index,
                "row_index": row_index,
                "raw": raw,
            }
        else:
            entry = _row_to_entry(raw, index)
            entry["tab"] = tab_name
            entry["editable"] = editable
            entry["edit_href"] = edit_href
            entry["edit_onclick"] = edit_onclick
            entry["edit_action_index"] = edit_action_index
            entry["row_index"] = row_index
        entry["id"] = f"{_tab_key(tab_name)}-{row_index}"
        entry["title"] = entry.get("titel") or entry.get("title") or raw[:80]
        entry["number"] = entry.get("nummer") or entry.get("number") or ""
        entry["date"] = entry.get("datum") or entry.get("beginn") or entry.get("date") or ""
        entries.append(entry)
    await _diag_step(page, diag, f"tab_{_tab_key(tab_name)}_table_read", {"headers_found": list(headers.keys()), "entries_count": len(entries)})
    return entries


async def read_overview_table(page, tab_name: str, diag: KlassenbuchDiagnosticsRun | None = None) -> list[dict]:
    return await read_table_by_headers(page, tab_name, diag)


async def read_current_tab_table(page, tab_name: str) -> list[dict]:
    return await read_overview_table(page, tab_name)


async def _click_overview_tab(page, key: str, tab_name: str, diag: KlassenbuchDiagnosticsRun | None = None) -> None:
    await _diag_step(page, diag, f"tab_{key}_started")
    selectors = KLASSENBUCH_SELECTORS["overview_tabs"][key]
    tab = await _locator_or_none(page, selectors)
    if tab is None:
        raise RuntimeError(f"Tab nicht gefunden: {tab_name}")
    await tab.click()
    try:
        await page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass
    await page.wait_for_timeout(700)
    await _safe_screenshot(page, f"klassenbuch_tab_{key}_loaded")
    await _diag_step(page, diag, f"tab_{key}_loaded")


async def read_all_overview_tabs(page, diag: KlassenbuchDiagnosticsRun | None = None) -> tuple[list[dict], dict[str, list[dict]], list[dict[str, str]]]:
    entries: list[dict] = []
    groups: dict[str, list[dict]] = {tab_name: [] for _, tab_name in OVERVIEW_TABS}
    tab_errors: list[dict[str, str]] = []
    for key, tab_name in OVERVIEW_TABS:
        try:
            await _click_overview_tab(page, key, tab_name, diag)
            tab_entries = await read_table_by_headers(page, tab_name, diag)
            groups[tab_name] = tab_entries
            entries.extend(tab_entries)
            if diag:
                diag.tabs[tab_name] = {"found": True, "row_count": len(tab_entries), "entries_count": len(tab_entries), "error": ""}
        except Exception as exc:
            screenshot_path = await _safe_screenshot(page, f"klassenbuch_tab_{key}_error")
            html_snapshot_path = await _safe_html_snapshot(page, f"klassenbuch_tab_{key}_error")
            await _diag_step(page, diag, f"tab_{key}_error", {"error": _exception_message(exc, "Tab konnte nicht gelesen werden")})
            if diag:
                diag.tabs[tab_name] = {"found": False, "row_count": 0, "entries_count": 0, "error": _exception_message(exc, "Tab konnte nicht gelesen werden")}
            tab_errors.append(
                {
                    "tab": tab_name,
                    "step": f"tab_{key}",
                    "message": _exception_message(exc, "Tab konnte nicht gelesen werden"),
                    "exception_type": type(exc).__name__,
                    "screenshot_path": screenshot_path,
                    "html_snapshot_path": html_snapshot_path,
                }
            )
    return entries, groups, tab_errors


async def _overview_diagnostics(page, screenshot_path: str = "", html_snapshot_path: str = "") -> dict:
    table_count = 0
    row_count = 0
    tab_names: list[str] = []
    try:
        table_count = await page.locator("table").count()
        row_count = await page.locator("table tr").count()
        tab_candidates = page.locator('[role="tab"], button, a')
        for index in range(min(await tab_candidates.count(), 80)):
            text = (await tab_candidates.nth(index).inner_text()).strip()
            if "Themendokumentationen" in text or "Korrektur" in text:
                tab_names.append(text)
    except Exception:
        pass
    return {
        "current_url": page.url,
        "page_title": await page.title(),
        "tabs_found": tab_names,
        "tab_names_found": tab_names,
        "table_count": table_count,
        "row_count": row_count,
        "screenshot_path": screenshot_path,
        "html_snapshot_path": html_snapshot_path,
    }


def _row_to_entry(text: str, index: int) -> dict[str, str]:
    parts = [part.strip() for part in text.splitlines() if part.strip()]
    joined = " | ".join(parts)
    number = next((part for part in parts if re.fullmatch(r"[A-Z0-9]{4,}", part, flags=re.IGNORECASE)), "")
    return {
        "id": f"row-{index}",
        "row_index": str(index),
        "title": parts[0] if parts else joined[:80],
        "date": next((part for part in parts if "." in part or "-" in part), ""),
        "number": number,
        "room": "",
        "begin": "",
        "end": "",
        "einsatzzeit_von": "",
        "einsatzzeit_bis": "",
        "status": "Offen" if "offen" in joined.lower() else "",
        "raw": joined,
    }


async def load_open_klassenbuecher() -> list[dict[str, str]]:
    result = await load_klassenbuecher_overview()
    return result["items"]


async def load_klassenbuecher_overview() -> dict:
    diag = KlassenbuchDiagnosticsRun(_diagnostic_run_id(), "load_open_klassenbuecher")
    page = None
    try:
        async with browser_page(storage_state_path=_storage_state_path()) as page:
            _attach_diagnostic_listeners(page, diag)
            await _start_trace(page, diag)
            try:
                await _login(page, diag)
                await _open_overview(page, diag)
                entries, groups, tab_errors = await read_all_overview_tabs(page, diag)
                diagnostics = await _overview_diagnostics(page)
                diagnostics["tab_errors"] = tab_errors
                diagnostics["run_id"] = diag.run_id
                diagnostics["diagnostics_folder"] = diag.relative_folder
                if not entries:
                    screenshot_path = await _safe_screenshot(page, "klassenbuch_overview_no_rows")
                    html_snapshot_path = await _safe_html_snapshot(page, "klassenbuch_overview_no_rows")
                    await _diag_step(page, diag, "overview_no_rows", {"message": "Keine Eintraege gefunden."})
                    diagnostics = await _overview_diagnostics(page, screenshot_path, html_snapshot_path)
                    diagnostics["step"] = "overview_no_rows"
                    diagnostics["tab_errors"] = tab_errors
                    diagnostics["message"] = "Keine Eintraege gefunden. Diagnose gespeichert."
                await _stop_trace(page, diag)
                summary = await _write_diagnostic_summary(page, diag, success=True, entries_returned=len(entries), diagnostics=diagnostics)
                diagnostics.update(
                    {
                        "run_id": diag.run_id,
                        "diagnostics_folder": diag.relative_folder,
                        "summary_path": summary.get("summary_path", ""),
                        "trace_path": summary.get("trace_file", ""),
                        "console_log": summary.get("console_log", ""),
                        "network_log": summary.get("network_log", ""),
                    }
                )
                return {"ok": True, "items": entries, "groups": groups, "diagnostics": diagnostics, "count": len(entries)}
            except KlassenbuchLoadError as exc:
                await _diag_step(page, diag, "error", {"error": str(exc), "exception_type": type(exc).__name__})
                await _stop_trace(page, diag)
                summary = await _write_diagnostic_summary(page, diag, success=False, error_message=str(exc), exception_type=exc.diagnostics.get("exception_type", type(exc).__name__), diagnostics=exc.diagnostics)
                exc.diagnostics.update(
                    {
                        "run_id": diag.run_id,
                        "diagnostics_folder": diag.relative_folder,
                        "summary_path": summary.get("summary_path", ""),
                        "trace_path": summary.get("trace_file", ""),
                        "console_log": summary.get("console_log", ""),
                        "network_log": summary.get("network_log", ""),
                    }
                )
                raise
            except Exception as exc:
                diagnostics = await _failure_diagnostics(page, "overview_read", exc)
                await _diag_step(page, diag, "error", {"error": _exception_message(exc, "Klassenbuecher konnten nicht geladen werden"), "exception_type": type(exc).__name__})
                await _stop_trace(page, diag)
                summary = await _write_diagnostic_summary(page, diag, success=False, error_message=_exception_message(exc, "Klassenbuecher konnten nicht geladen werden"), exception_type=type(exc).__name__, diagnostics=diagnostics)
                diagnostics.update(
                    {
                        "run_id": diag.run_id,
                        "diagnostics_folder": diag.relative_folder,
                        "summary_path": summary.get("summary_path", ""),
                        "trace_path": summary.get("trace_file", ""),
                        "console_log": summary.get("console_log", ""),
                        "network_log": summary.get("network_log", ""),
                    }
                )
                raise KlassenbuchLoadError(f"Klassenbuecher konnten nicht geladen werden: {_exception_message(exc, 'unbekannter Fehler')}", diagnostics) from exc
    except KlassenbuchLoadError:
        raise
    except Exception as exc:
        diagnostics = {
            "run_id": diag.run_id,
            "diagnostics_folder": diag.relative_folder,
            "step": "browser_start",
            "current_url": "",
            "page_title": "",
            "screenshot_path": "",
            "html_snapshot_path": "",
            "exception_type": type(exc).__name__,
        }
        summary = await _write_diagnostic_summary(None, diag, success=False, error_message=_exception_message(exc, "Klassenbuecher konnten nicht geladen werden"), exception_type=type(exc).__name__, diagnostics=diagnostics)
        diagnostics.update(
            {
                "summary_path": summary.get("summary_path", ""),
                "trace_path": summary.get("trace_file", ""),
                "console_log": summary.get("console_log", ""),
                "network_log": summary.get("network_log", ""),
                "probable_cause": summary.get("probable_cause", "Playwright/Chromium konnte nicht gestartet werden. Der Fehler trat vor dem Oeffnen der Klassenbuch-Webseite auf."),
                "next_action": summary.get("next_action", "Browser-Check ausfuehren und Playwright-Installation pruefen."),
            }
        )
        raise KlassenbuchLoadError(f"Klassenbuecher konnten nicht geladen werden: {_exception_message(exc, 'unbekannter Fehler')}", diagnostics) from exc


async def _select_entry(page, payload: dict, diag: KlassenbuchDiagnosticsRun | None = None) -> None:
    selected = payload.get("klassenbuch") or payload.get("selected_klassenbuch") or {}
    await _diag_step(page, diag, "wizard_open_started")
    edit_href = selected.get("edit_href")
    if edit_href:
        await page.goto(urljoin(page.url, str(edit_href)), wait_until="domcontentloaded")
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        await _safe_screenshot(page, "klassenbuch_entry_selected")
        await _ensure_wizard_loaded(page, diag)
        return
    if selected.get("row_index") is not None:
        await _open_selected_entry_from_overview(page, selected, diag)
        return
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
        candidate = first_locator(row, selector)
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
    await _ensure_wizard_loaded(page, diag)


async def _open_selected_entry_from_overview(page, selected: dict, diag: KlassenbuchDiagnosticsRun | None = None) -> None:
    await _open_overview(page, diag)
    tab_name = str(selected.get("tab") or "offene Themendokumentationen")
    key = _tab_key(tab_name)
    await _click_overview_tab(page, key, tab_name, diag)
    row_index = str(selected.get("row_index"))
    row = first_locator(page, f'tr[data-index="{row_index}"]')
    if not await row.count():
        diagnostics = await _failure_diagnostics(page, "wizard_open")
        raise KlassenbuchLoadError(f'Klassenbuch-Zeile mit data-index="{row_index}" wurde nicht gefunden.', diagnostics)
    for selector in KLASSENBUCH_SELECTORS["edit_button"]:
        try:
            button = first_locator(row, selector)
            if await button.count() and await button.is_visible() and await button.is_enabled():
                await button.click()
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass
                await _safe_screenshot(page, "klassenbuch_entry_selected")
                await _ensure_wizard_loaded(page, diag)
                return
        except Exception:
            continue
    action_index = selected.get("edit_action_index")
    if action_index is not None and str(action_index).isdigit():
        try:
            await page.evaluate("index => classbookApp.overview.forwardToWizardWithPreselection(Number(index))", str(action_index))
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            await _safe_screenshot(page, "klassenbuch_entry_selected")
            await _ensure_wizard_loaded(page, diag)
            return
        except Exception:
            pass
    diagnostics = await _failure_diagnostics(page, "wizard_open")
    raise KlassenbuchLoadError("Klassenbuch-Bearbeitungsseite konnte nicht geoeffnet werden.", diagnostics)


async def _ensure_wizard_loaded(page, diag: KlassenbuchDiagnosticsRun | None = None) -> None:
    if "/classbooks/wizard/new" in page.url.lower() or await _is_any_visible(page, KLASSENBUCH_SELECTORS["wizard_markers"]):
        await _diag_step(page, diag, "wizard_loaded")
        return
    diagnostics = await _failure_diagnostics(page, "wizard_open")
    raise KlassenbuchLoadError("Klassenbuch-Bearbeitungsseite konnte nicht geoeffnet werden.", diagnostics)


async def _ue_textarea_locators(page) -> list:
    selector_groups = [
        'textarea[name^="classBookEntry-"]',
        'textarea[id^="classBookEntry-"]',
        "textarea.ueEntry",
        'textarea:near(:text("Themendokumentation bearbeiten"))',
        "textarea",
    ]
    for selector in selector_groups:
        locators = page.locator(selector)
        visible = []
        for index in range(await locators.count()):
            locator = locators.nth(index)
            try:
                if await locator.is_visible() and await locator.is_enabled():
                    visible.append(locator)
            except Exception:
                continue
        if len(visible) >= 9:
            indexed: list[tuple[int, object]] = []
            for fallback_index, locator in enumerate(visible):
                field_name = ""
                try:
                    field_name = (await locator.get_attribute("name")) or (await locator.get_attribute("id")) or ""
                except Exception:
                    field_name = ""
                match = re.search(r"classBookEntry-(\d+)", field_name)
                indexed.append((int(match.group(1)) if match else fallback_index, locator))
            return [locator for _, locator in sorted(indexed, key=lambda item: item[0])[:9]]
    return []


async def fill_ue_textareas(page, ue_items: list[dict], diag: KlassenbuchDiagnosticsRun | None = None) -> None:
    if len(ue_items) != 9:
        raise RuntimeError("Es muessen genau 9 UE fuer die Klassenbuch-Befuellung vorhanden sein.")
    fields = await _ue_textarea_locators(page)
    await _diag_step(page, diag, "ue_textareas_found", {"found_textareas": len(fields)})
    if len(fields) < 9:
        diagnostics = await _failure_diagnostics(page, "ue_textareas")
        raise KlassenbuchLoadError("Nicht genug classBookEntry-Textareas fuer 9 UE gefunden.", diagnostics)
    for index, item in enumerate(ue_items):
        content = str(item.get("content") or item.get("lehrinhalt") or "").strip()
        if len(content) < 40:
            diagnostics = await _failure_diagnostics(page, "ue_validation")
            raise KlassenbuchLoadError(f"UE {index + 1} ist zu kurz ({len(content)} Zeichen, mindestens 40).", diagnostics)
        if len(content) > 220:
            diagnostics = await _failure_diagnostics(page, "ue_validation")
            raise KlassenbuchLoadError(f"UE {index + 1} ist zu lang ({len(content)} Zeichen, maximal 220).", diagnostics)
        await fields[index].fill(content)
        actual = (await fields[index].input_value()).strip()
        if actual != content:
            diagnostics = await _failure_diagnostics(page, "ue_fill")
            raise KlassenbuchLoadError(f"UE {index + 1} konnte nicht korrekt in classBookEntry-{index} eingetragen werden.", diagnostics)
    await _diag_step(page, diag, "ue_filled")


async def _fill_ue(page, payload: dict, diag: KlassenbuchDiagnosticsRun | None = None) -> None:
    await optional_click(page, KLASSENBUCH_SELECTORS["ue_tab"])
    try:
        await page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass
    await _safe_screenshot(page, "klassenbuch_ue_opened")
    ue_items = payload.get("ue_items") or payload.get("unterrichtseinheiten") or []
    await fill_ue_textareas(page, ue_items, diag)
    await select_teaching_formats_for_all_rows(page, len(ue_items), diag)
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


async def _teaching_format_control_for_row(page, row_index: int):
    textarea = first_locator(page, f'textarea[name="classBookEntry-{row_index}"]')
    if not await textarea.count():
        textarea = first_locator(page, f"#classBookEntry-{row_index}")
    try:
        if await textarea.count() and await textarea.is_visible():
            row = first_locator(textarea, "xpath=ancestor::tr[1]")
            if await row.count():
                for selector in ['div[id^="classBookEntry2-"]', '[data-target="#id-modal-lessons"]', '[data-toggle="modal"]', ".ueEntryButtonGroup button", ".input-group-addon.ueEntryButtonGroup button", "button", '[role="button"]']:
                    controls = row.locator(selector)
                    for control_index in range(await controls.count()):
                        control = controls.nth(control_index)
                        if await control.is_visible() and await control.is_enabled():
                            return control
            container = first_locator(textarea, "xpath=ancestor::*[contains(@class, 'input-group')][1]")
            if await container.count():
                control = first_locator(container, 'div[id^="classBookEntry2-"], [data-target="#id-modal-lessons"], [data-toggle="modal"], .ueEntryButtonGroup button, button')
                if await control.count() and await control.is_visible() and await control.is_enabled():
                    return control
    except Exception:
        pass
    controls = await _visible_locators(page, KLASSENBUCH_SELECTORS["teaching_format_fields"])
    if len(controls) > row_index:
        return controls[row_index]
    return None


async def open_teaching_format_for_ue(page, index: int, diag: KlassenbuchDiagnosticsRun | None = None):
    return await open_teaching_format_modal(page, index, diag)


async def open_teaching_format_modal(page, row_index: int, diag: KlassenbuchDiagnosticsRun | None = None):
    control = await _teaching_format_control_for_row(page, row_index)
    if control is None:
        await _safe_screenshot(page, "lernformat_modal_error")
        _set_klassenbuch_step(StepState.error, f"Lernformat-Feld fuer UE {row_index + 1} nicht gefunden.")
        raise RuntimeError(f"Lernformat-Feld fuer UE {row_index + 1} nicht gefunden.")
    await control.click()
    modal = await _locator_or_none(page, KLASSENBUCH_SELECTORS["teaching_format_modal"][:4])
    if modal is None and await _is_any_visible(page, KLASSENBUCH_SELECTORS["teaching_format_modal"]):
        modal = page.locator("body")
    if modal is None:
        await _safe_screenshot(page, "lernformat_modal_error")
        _set_klassenbuch_step(StepState.error, f"Lernformat-Modal fuer UE {row_index + 1} wurde nicht geoeffnet.")
        raise RuntimeError(f"Lernformat-Modal fuer UE {row_index + 1} wurde nicht geoeffnet.")
    await _safe_screenshot(page, "lernformat_modal_open")
    await _diag_step(page, diag, "teaching_format_modal_open", {"ue_index": row_index})
    return modal


async def _checkbox_for_label(scope, label_variants: Sequence[str]):
    for label in label_variants:
        try:
            checkbox = scope.get_by_label(re.compile(re.escape(label), re.IGNORECASE)).nth(0)
            if await checkbox.is_visible() and await checkbox.is_enabled():
                return checkbox
        except Exception:
            pass
        try:
            label_locator = scope.locator("label").filter(has_text=re.compile(re.escape(label), re.IGNORECASE)).nth(0)
            if await label_locator.is_visible():
                nested = first_locator(label_locator, 'input[type="checkbox"]')
                if await nested.count() and await nested.is_enabled():
                    return nested
                return label_locator
        except Exception:
            pass
        try:
            checkbox = first_locator(scope, f'input[type="checkbox"]:near(:text("{label}"))')
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


async def set_teaching_formats(page, modal, diag: KlassenbuchDiagnosticsRun | None = None) -> None:
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
    await _diag_step(page, diag, "teaching_format_selected")
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


async def select_teaching_formats_for_all_rows(page, row_count: int = 9, diag: KlassenbuchDiagnosticsRun | None = None) -> None:
    _set_klassenbuch_step(StepState.running, "Lernformate werden gesetzt.")
    for index in range(row_count):
        modal = await open_teaching_format_for_ue(page, index, diag)
        await set_teaching_formats(page, modal, diag)
    _set_klassenbuch_step(StepState.running, "Lernformate wurden fuer alle UE gesetzt.")


async def _save_ue(page) -> None:
    status_service.set_step("klassenbuch", StepState.running, "Unterrichtseinheiten werden gespeichert.")
    await click_first(page, KLASSENBUCH_SELECTORS["save_button"], "Speichern")
    await page.wait_for_load_state("networkidle")
    await _safe_screenshot(page, "klassenbuch_saved_success")
    status_service.set_step("klassenbuch", StepState.success, "Alle 9 UE wurden gespeichert.")


async def _open_signature_step(page) -> None:
    _set_signature_step(StepState.running, "Signaturseite gesucht.")
    next_button = await _locator_or_none(page, KLASSENBUCH_SELECTORS["next_button"])
    if next_button is None:
        await _safe_screenshot(page, "signature_page_not_reached")
        _set_signature_step(StepState.error, "Weiter-Button zur Signatur wurde nicht gefunden.")
        raise RuntimeError("Weiter-Button zur Signatur wurde nicht gefunden.")
    await next_button.click()
    await page.wait_for_load_state("networkidle")
    signature_reached = False
    for _ in range(10):
        if await _is_any_visible(page, KLASSENBUCH_SELECTORS["signature_page_markers"]) or await _locator_or_none(page, KLASSENBUCH_SELECTORS["signature_canvas"]) is not None:
            signature_reached = True
            break
        await page.wait_for_timeout(300)
    if not signature_reached:
        await _safe_screenshot(page, "signature_page_not_reached")
        _set_signature_step(StepState.error, "Signaturseite wurde nach Weiter nicht erreicht.")
        raise RuntimeError("Signaturseite wurde nach Weiter nicht erreicht.")
    await _safe_screenshot(page, "klassenbuch_signature_page_loaded")
    await _safe_screenshot(page, "signatur_page_loaded")


async def _guard_manual_signature_challenge(page) -> None:
    if await _is_any_visible(page, KLASSENBUCH_SELECTORS["manual_signature_markers"]):
        await _safe_screenshot(page, "klassenbuch_signature_error")
        _set_signature_step(StepState.manual_review, "Manuelle Signatur erforderlich.")
        raise RuntimeError("Manuelle Signatur erforderlich: 2FA, TAN, Zertifikat oder externer Signaturdienst erkannt.")


async def _recognize_signature_page(page) -> None:
    await _guard_manual_signature_challenge(page)
    signature_canvas = await _locator_or_none(page, KLASSENBUCH_SELECTORS["signature_canvas"])
    canvas_visible = False
    if signature_canvas is not None:
        try:
            canvas_visible = await signature_canvas.is_visible()
        except Exception:
            canvas_visible = False
    url_matches = "/classbooks/wizard/new" in page.url.lower()
    marker_found = await _is_any_visible(page, KLASSENBUCH_SELECTORS["signature_page_markers"])
    text_found = False
    for text in ["Signatur", "Signierung", "Bitte hier unterschreiben"]:
        try:
            if await page.locator(f"text={text}").first.count() and await page.locator(f"text={text}").first.is_visible():
                text_found = True
                break
        except Exception:
            continue
    signature_field = await _locator_or_none(page, KLASSENBUCH_SELECTORS["signature"])
    sign_button = await _locator_or_none(page, KLASSENBUCH_SELECTORS["sign_button"])
    recognized = url_matches or marker_found or text_found or canvas_visible
    if not recognized or (not canvas_visible and signature_field is None and sign_button is None):
        await _safe_screenshot(page, "klassenbuch_signature_error")
        _set_signature_step(StepState.manual_review, "Signaturseite nicht eindeutig erkannt.")
        raise RuntimeError("Signaturseite nicht eindeutig erkannt.")
    if canvas_visible:
        await _safe_screenshot(page, "signatur_canvas_detected")
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


async def _canvas_has_ink(canvas) -> bool:
    try:
        return bool(await canvas.evaluate(
            """node => {
                const ctx = node.getContext && node.getContext("2d");
                if (!ctx || !node.width || !node.height) return false;
                const data = ctx.getImageData(0, 0, node.width, node.height).data;
                let ink = 0;
                for (let i = 0; i < data.length; i += 4) {
                    const r = data[i], g = data[i + 1], b = data[i + 2], a = data[i + 3];
                    if (a > 0 && r < 240 && g < 240 && b < 240) ink += 1;
                    if (ink > 100) return true;
                }
                return false;
            }"""
        ))
    except Exception:
        return False


async def _canvas_debug_info(canvas) -> dict[str, Any]:
    info: dict[str, Any] = {"canvas_has_ink": await _canvas_has_ink(canvas)}
    try:
        info["bounding_box"] = await canvas.bounding_box()
    except Exception:
        info["bounding_box"] = None
    try:
        info.update(await canvas.evaluate(
            """node => {
                const rect = node.getBoundingClientRect();
                const style = window.getComputedStyle(node);
                return {
                    canvas_width: node.width,
                    canvas_height: node.height,
                    css_width: style.width || `${rect.width}px`,
                    css_height: style.height || `${rect.height}px`
                };
            }"""
        ))
    except Exception:
        pass
    return info


async def _notify_signature_pad_changed(page, canvas) -> None:
    try:
        await canvas.evaluate(
            """node => {
                const rect = node.getBoundingClientRect();
                const x = rect.left + rect.width * 0.55;
                const y = rect.top + rect.height * 0.55;
                for (const type of ["pointerdown", "pointermove", "pointerup", "mouseup"]) {
                    try {
                        node.dispatchEvent(new PointerEvent(type, { bubbles: true, clientX: x, clientY: y, pointerId: 1, pointerType: "mouse" }));
                    } catch (_) {
                        node.dispatchEvent(new MouseEvent(type.replace("pointer", "mouse"), { bubbles: true, clientX: x, clientY: y }));
                    }
                }
                node.dispatchEvent(new Event("input", { bubbles: true }));
                node.dispatchEvent(new Event("change", { bubbles: true }));
                const dataUrl = node.toDataURL ? node.toDataURL("image/png") : "";
                if (dataUrl) {
                    const container = node.closest("#signature-pad, .m-signature-pad, form, body") || document;
                    const inputs = Array.from(container.querySelectorAll("input[type='hidden'], input:not([type]), textarea"));
                    for (const input of inputs) {
                        const marker = `${input.name || ""} ${input.id || ""} ${input.className || ""}`.toLowerCase();
                        if (marker.includes("signature") || marker.includes("sign") || marker.includes("unterschrift")) {
                            input.value = dataUrl;
                            input.dispatchEvent(new Event("input", { bubbles: true }));
                            input.dispatchEvent(new Event("change", { bubbles: true }));
                        }
                    }
                }
            }"""
        )
    except Exception:
        pass
    try:
        await page.evaluate(
            """() => {
                if (window.jQuery) {
                    try { window.jQuery("#signature-pad canvas").trigger("change"); } catch (_) {}
                }
            }"""
        )
    except Exception:
        pass


async def _draw_signature_with_mouse(page, canvas) -> bool:
    if canvas is None:
        await _safe_screenshot(page, "signatur_error")
        _set_signature_step(StepState.error, "Signatur-Zeichenflaeche nicht gefunden.")
        raise RuntimeError("Signatur-Zeichenflaeche nicht gefunden.")
    box = await canvas.bounding_box()
    if not box or box["width"] < 80 or box["height"] < 30:
        await _safe_screenshot(page, "signatur_error")
        _set_signature_step(StepState.error, "Signatur-Zeichenflaeche hat keine plausible Groesse.")
        raise RuntimeError("Signatur-Zeichenflaeche hat keine plausible Groesse.")
    _set_signature_step(StepState.running, "Signatur wird per Mausbewegung gezeichnet.")
    await _safe_screenshot(page, "signatur_draw_started")
    margin_x = box["width"] * 0.10
    top_y = box["height"] * 0.35
    draw_width = box["width"] * 0.80
    draw_height = box["height"] * 0.35
    points = _interpolate_points(_signature_points())
    start_x = box["x"] + margin_x + points[0][0] * draw_width
    start_y = box["y"] + top_y + points[0][1] * draw_height
    await page.mouse.move(start_x, start_y)
    await page.mouse.down()
    for point_x, point_y in points[1:]:
        await page.mouse.move(box["x"] + margin_x + point_x * draw_width, box["y"] + top_y + point_y * draw_height, steps=2)
    await page.mouse.up()
    await _notify_signature_pad_changed(page, canvas)
    await _safe_screenshot(page, "signatur_mouse_drawn")
    return await _canvas_has_ink(canvas)


async def _draw_signature_direct_canvas(canvas) -> bool:
    try:
        await canvas.evaluate(
            """node => {
                const ctx = node.getContext && node.getContext("2d");
                if (!ctx) return;
                const w = node.width || node.getBoundingClientRect().width;
                const h = node.height || node.getBoundingClientRect().height;
                const x = p => w * (0.10 + p[0] * 0.80);
                const y = p => h * (0.35 + p[1] * 0.35);
                const points = [
                    [0.08,0.55],[0.16,0.40],[0.25,0.52],[0.14,0.68],[0.31,0.64],
                    [0.36,0.46],[0.38,0.64],[0.48,0.67],[0.55,0.50],[0.50,0.67],
                    [0.62,0.48],[0.70,0.32],[0.68,0.63],[0.79,0.45],[0.82,0.36],
                    [0.81,0.66],[0.90,0.52],[0.84,0.59],[0.95,0.59]
                ];
                ctx.save();
                ctx.strokeStyle = "#111";
                ctx.lineWidth = 3;
                ctx.lineCap = "round";
                ctx.lineJoin = "round";
                ctx.beginPath();
                ctx.moveTo(x(points[0]), y(points[0]));
                for (const point of points.slice(1)) ctx.lineTo(x(point), y(point));
                ctx.stroke();
                ctx.restore();
                node.dispatchEvent(new Event("input", { bubbles: true }));
                node.dispatchEvent(new Event("change", { bubbles: true }));
                node.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
                try { node.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, pointerId: 1, pointerType: "mouse" })); } catch (_) {}
            }"""
        )
    except Exception:
        return False
    return await _canvas_has_ink(canvas)


async def _load_saved_signature_profile() -> dict:
    profile = read_signature_profile()
    if not profile:
        return {}
    return profile


def _signature_profile_diagnostics(profile: dict) -> dict[str, Any]:
    strokes = profile.get("strokes") if isinstance(profile.get("strokes"), list) else []
    return {
        "stroke_count": len(strokes),
        "point_count": sum(len(stroke) for stroke in strokes if isinstance(stroke, list)),
        "has_preview": bool(profile.get("preview_png_data_url")),
        "source": profile.get("source", "local_signature_pad"),
    }


def _signature_strokes(profile: dict) -> list[list[dict[str, Any]]]:
    strokes = profile.get("strokes")
    if not isinstance(strokes, list):
        return []
    normalized: list[list[dict[str, Any]]] = []
    for stroke in strokes:
        if not isinstance(stroke, list):
            continue
        points = []
        for point in stroke:
            if not isinstance(point, dict):
                continue
            try:
                points.append({"x": max(0.0, min(1.0, float(point.get("x", 0)))), "y": max(0.0, min(1.0, float(point.get("y", 0))))})
            except Exception:
                continue
        if points:
            normalized.append(points)
    return normalized


async def _draw_saved_signature_with_mouse(page, canvas, profile: dict) -> bool:
    box = await canvas.bounding_box()
    if not box or box["width"] < 80 or box["height"] < 30:
        raise RuntimeError("Signatur-Zeichenflaeche hat keine plausible Groesse.")
    strokes = _signature_strokes(profile)
    if not strokes:
        return False
    await _safe_screenshot(page, "signature_mouse_draw_started")
    for stroke in strokes:
        first = stroke[0]
        start_x = box["x"] + first["x"] * box["width"]
        start_y = box["y"] + first["y"] * box["height"]
        await page.mouse.move(start_x, start_y)
        await page.mouse.down()
        for point in stroke[1:]:
            x = box["x"] + point["x"] * box["width"]
            y = box["y"] + point["y"] * box["height"]
            x = max(box["x"], min(box["x"] + box["width"], x))
            y = max(box["y"], min(box["y"] + box["height"], y))
            await page.mouse.move(x, y, steps=2)
        await page.mouse.up()
    await _notify_signature_pad_changed(page, canvas)
    await _safe_screenshot(page, "signature_mouse_draw_done")
    return await _canvas_has_ink(canvas)


async def _draw_saved_signature_direct_canvas(page, canvas, profile: dict) -> bool:
    strokes = _signature_strokes(profile)
    if not strokes:
        return False
    try:
        await canvas.evaluate(
            """(node, strokes) => {
                const ctx = node.getContext && node.getContext("2d");
                if (!ctx) return;
                const w = node.width || node.getBoundingClientRect().width;
                const h = node.height || node.getBoundingClientRect().height;
                ctx.save();
                ctx.strokeStyle = "#111";
                ctx.lineWidth = Math.max(2, Math.round(Math.min(w, h) / 90));
                ctx.lineCap = "round";
                ctx.lineJoin = "round";
                for (const stroke of strokes) {
                    if (!stroke.length) continue;
                    ctx.beginPath();
                    ctx.moveTo(Math.max(0, Math.min(1, stroke[0].x)) * w, Math.max(0, Math.min(1, stroke[0].y)) * h);
                    for (const point of stroke.slice(1)) {
                        ctx.lineTo(Math.max(0, Math.min(1, point.x)) * w, Math.max(0, Math.min(1, point.y)) * h);
                    }
                    ctx.stroke();
                }
                ctx.restore();
                node.dispatchEvent(new Event("input", { bubbles: true }));
                node.dispatchEvent(new Event("change", { bubbles: true }));
                node.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
                try { node.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, pointerId: 1, pointerType: "mouse" })); } catch (_) {}
            }""",
            strokes,
        )
    except Exception:
        return False
    await _notify_signature_pad_changed(page, canvas)
    return await _canvas_has_ink(canvas)


async def draw_signature_schaffer(page, canvas_locator=None) -> None:
    canvas = canvas_locator or await _locator_or_none(page, KLASSENBUCH_SELECTORS["signature_canvas"])
    if canvas is None:
        await _safe_screenshot(page, "signatur_error")
        _set_signature_step(StepState.error, "Signatur-Zeichenflaeche nicht gefunden.")
        raise RuntimeError("Signatur-Zeichenflaeche nicht gefunden.")
    await _safe_screenshot(page, "signatur_canvas_detected")
    mouse_has_ink = await _draw_signature_with_mouse(page, canvas)
    if not mouse_has_ink:
        _set_signature_step(StepState.running, "Mauszeichnung ohne Canvas-Ink, Fallback wird genutzt.")
        await _safe_screenshot(page, "signatur_direct_canvas_fallback")
        direct_has_ink = await _draw_signature_direct_canvas(canvas)
        await _notify_signature_pad_changed(page, canvas)
        if not direct_has_ink:
            await _safe_screenshot(page, "signatur_error")
            _set_signature_step(StepState.error, "Signatur-Canvas wurde nicht beschrieben.")
            raise RuntimeError("Signatur-Canvas wurde nicht beschrieben.")
    await _safe_screenshot(page, "signatur_canvas_has_ink")
    _set_signature_step(StepState.success, "Signatur Schaffer wurde eingezeichnet.")


async def _fill_signature(page, allow_overwrite: bool, draw_canvas: bool = True, diag: KlassenbuchDiagnosticsRun | None = None) -> dict[str, Any]:
    if draw_canvas:
        canvas = await _locator_or_none(page, KLASSENBUCH_SELECTORS["signature_canvas"])
        if canvas is not None:
            _set_signature_step(StepState.running, "Signatur-Zeichenflaeche gefunden.")
            await _diag_step(page, diag, "signature_canvas_detected", await _canvas_debug_info(canvas))
            profile = await _load_saved_signature_profile()
            if profile:
                profile_diag = _signature_profile_diagnostics(profile)
                await _diag_step(page, diag, "signature_profile_loaded", profile_diag)
                _set_signature_step(StepState.running, "Lokale Signatur wird gezeichnet.")
                mouse_has_ink = await _draw_saved_signature_with_mouse(page, canvas, profile)
                await _diag_step(page, diag, "signature_mouse_draw_done", {**profile_diag, "canvas_has_ink": mouse_has_ink})
                if not mouse_has_ink:
                    await _safe_screenshot(page, "signature_direct_canvas_fallback")
                    direct_has_ink = await _draw_saved_signature_direct_canvas(page, canvas, profile)
                    await _diag_step(page, diag, "signature_direct_canvas_fallback", {**profile_diag, "canvas_has_ink": direct_has_ink})
                    if not direct_has_ink:
                        raise RuntimeError("Lokale Signatur konnte nicht in das Canvas gezeichnet werden.")
            else:
                await _diag_step(page, diag, "signature_profile_missing", {"stroke_count": 0, "point_count": 0})
                await draw_signature_schaffer(page, canvas)
            debug_info = await _canvas_debug_info(canvas)
            await _diag_step(page, diag, "signature_canvas_has_ink", debug_info)
            return debug_info
    settings = get_settings()
    locator = await _locator_or_none(page, KLASSENBUCH_SELECTORS["signature"])
    if locator is None:
        await _safe_screenshot(page, "klassenbuch_signature_error")
        await _diag_step(page, diag, "signatur_error", {"error": "Signaturfeld nicht gefunden.", "canvas_detected": False})
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
        await _diag_step(page, diag, "signatur_error", {"error": "Signaturfeld ist bereits befuellt."})
        _set_signature_step(StepState.manual_review, "Signaturfeld ist bereits befuellt.")
        raise RuntimeError("Signaturfeld ist bereits befuellt. Im Dry-Run wird nicht ueberschrieben.")
    _set_signature_step(StepState.running, "Signaturfeld gefunden.")
    await locator.fill(settings.default_signature)
    await _safe_screenshot(page, "klassenbuch_signature_filled")
    await _diag_step(page, diag, "signatur_canvas_has_ink", {"canvas_has_ink": False, "text_signature_filled": True})
    _set_signature_step(StepState.success, "Signatur eingetragen.")
    return {"canvas_has_ink": False, "text_signature_filled": True}


async def _confirm_signature_checkbox(page) -> None:
    checkbox = await _locator_or_none(page, KLASSENBUCH_SELECTORS["signature_confirm_checkbox"])
    if checkbox is not None:
        try:
            if not await checkbox.is_checked():
                await checkbox.check()
        except Exception:
            await checkbox.click()


async def _finalize_signature(page, diag: KlassenbuchDiagnosticsRun | None = None) -> str:
    await _guard_manual_signature_challenge(page)
    _set_signature_step(StepState.running, "Finale Signatur gestartet.")
    await _confirm_signature_checkbox(page)
    await click_first(page, KLASSENBUCH_SELECTORS["sign_button"], "Signieren")
    await page.wait_for_load_state("networkidle")
    if not await _is_any_visible(page, KLASSENBUCH_SELECTORS["signature_success"]):
        await _safe_screenshot(page, "klassenbuch_signature_error")
        await _diag_step(page, diag, "signatur_error", {"error": "Keine eindeutige Erfolgsmeldung nach dem Signieren erkannt."})
        _set_signature_step(StepState.error, "Signatur fehlgeschlagen.")
        raise RuntimeError("Keine eindeutige Erfolgsmeldung nach dem Signieren erkannt.")
    await _safe_screenshot(page, "signatur_submit_success")
    screenshot = await _safe_screenshot(page, "klassenbuch_signed_success")
    await _diag_step(page, diag, "signatur_submit_success", {"screenshot_path": screenshot})
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


def _validate_fill_signature_payload(payload: dict, review_confirmed: bool) -> str | None:
    if not review_confirmed:
        return "Klassenbuch-Befuellung gesperrt: Review-Bestaetigung erforderlich."
    selected = payload.get("klassenbuch") or payload.get("selected_klassenbuch") or payload.get("classbook")
    if not isinstance(selected, dict) or not selected:
        return "Klassenbuch-Befuellung gesperrt: Kein Klassenbuch ausgewaehlt."
    ue_items = payload.get("ue_items") or payload.get("unterrichtseinheiten") or []
    if len(ue_items) != 9:
        return "Klassenbuch-Befuellung gesperrt: Es muessen genau 9 UE vorhanden sein."
    for index, item in enumerate(ue_items, start=1):
        if not isinstance(item, dict):
            return f"Klassenbuch-Befuellung gesperrt: UE {index} ist ungueltig."
        if not str(item.get("content") or item.get("lehrinhalt") or "").strip():
            return f"Klassenbuch-Befuellung gesperrt: UE {index} hat keinen Inhalt."
        formats = item.get("formats") or []
        if not isinstance(formats, list) or not formats:
            return f"Klassenbuch-Befuellung gesperrt: Lernformate fuer UE {index} fehlen."
        if len(formats) > 2:
            return f"Klassenbuch-Befuellung gesperrt: UE {index} hat mehr als zwei Lernformate."
    return None


async def prepare_klassenbuch(payload: dict) -> ApiMessage:
    async with browser_page(storage_state_path=_storage_state_path()) as page:
        diag = KlassenbuchDiagnosticsRun(_diagnostic_run_id(), "prepare_klassenbuch")
        _attach_diagnostic_listeners(page, diag)
        await _start_trace(page, diag)
        try:
            await _login(page, diag)
            await _select_entry(page, payload, diag)
            await _fill_ue(page, payload, diag)
            screenshot = await _safe_screenshot(page, "klassenbuch_ue_dry_run")
            await _stop_trace(page, diag)
            summary = await _write_diagnostic_summary(page, diag, success=True, entries_returned=0, diagnostics={"screenshot_path": screenshot})
            status_service.set_step("klassenbuch", StepState.skipped, "Dry-Run: UE wurden eingetragen, aber nicht gespeichert.")
            _set_signature_step(StepState.skipped, "Dry-Run: Signatur wurde nicht gestartet.")
            return ApiMessage(ok=True, message="Dry-Run: UE wurden eingetragen, aber nicht gespeichert.", data={"payload": payload, "screenshot": screenshot, "diagnostics": summary})
        except Exception as exc:
            screenshot = await _safe_screenshot(page, "klassenbuch_signature_error")
            await _diag_step(page, diag, "error", {"error": _exception_message(exc, "Klassenbuch-Dry-Run fehlgeschlagen"), "exception_type": type(exc).__name__})
            await _stop_trace(page, diag)
            summary = await _write_diagnostic_summary(page, diag, success=False, error_message=_exception_message(exc, "Klassenbuch-Dry-Run fehlgeschlagen"), exception_type=type(exc).__name__, diagnostics={"screenshot_path": screenshot})
            return ApiMessage(ok=False, message=f"Klassenbuch-Dry-Run fehlgeschlagen: {_exception_message(exc, 'unbekannter Fehler')}", data={"screenshot": screenshot, "diagnostics": summary})


async def fill_classbook_and_open_signature(payload: dict, review_confirmed: bool) -> ApiMessage:
    blocked_reason = _validate_fill_signature_payload(payload, review_confirmed)
    if blocked_reason:
        return ApiMessage(ok=False, message=blocked_reason)
    async with browser_page(storage_state_path=_storage_state_path()) as page:
        diag = KlassenbuchDiagnosticsRun(_diagnostic_run_id(), "fill_classbook_and_open_signature")
        _attach_diagnostic_listeners(page, diag)
        await _start_trace(page, diag)
        try:
            await _diag_step(page, diag, "fill_signature_workflow_started")
            await _login(page, diag)
            await _select_entry(page, payload, diag)
            await _diag_step(page, diag, "selected_classbook_opened")
            await _fill_ue(page, payload, diag)
            await _diag_step(page, diag, "teaching_formats_finished")
            await _save_ue(page)
            await _diag_step(page, diag, "ue_saved")
            await _open_signature_step(page)
            await _diag_step(page, diag, "next_to_signature_clicked")
            await _recognize_signature_page(page)
            screenshot = await _safe_screenshot(page, "klassenbuch_signature_ready")
            await _diag_step(page, diag, "signature_page_ready", {"screenshot_path": screenshot, "signature_page_ready": True})
            await _stop_trace(page, diag)
            summary = await _write_diagnostic_summary(page, diag, success=True, diagnostics={"screenshot_path": screenshot})
            _set_signature_step(StepState.manual_review, "Klassenbuch wurde befuellt und steht auf Signierung.")
            return ApiMessage(
                ok=True,
                message="Klassenbuch wurde befuellt und die Signaturseite wurde geoeffnet.",
                data={"screenshot": screenshot, "diagnostics": summary, "signature_page_ready": True},
            )
        except Exception as exc:
            screenshot = await _safe_screenshot(page, "signature_page_not_reached")
            html_snapshot = await _safe_html_snapshot(page, "signature_page_not_reached")
            await _diag_step(page, diag, "signature_page_not_reached", {"error": _exception_message(exc, "Klassenbuch-Befuellung fehlgeschlagen"), "exception_type": type(exc).__name__})
            await _stop_trace(page, diag)
            summary = await _write_diagnostic_summary(
                page,
                diag,
                success=False,
                error_message=_exception_message(exc, "Klassenbuch-Befuellung fehlgeschlagen"),
                exception_type=type(exc).__name__,
                diagnostics={"screenshot_path": screenshot, "html_snapshot_path": html_snapshot, "step": "signature_page_not_reached"},
            )
            _set_signature_step(StepState.error, "Klassenbuch-Befuellung oder Signaturseitenwechsel fehlgeschlagen.")
            return ApiMessage(
                ok=False,
                message=f"Klassenbuch-Befuellung fehlgeschlagen: {_exception_message(exc, 'unbekannter Fehler')}",
                data={"screenshot": screenshot, "diagnostics": summary, "signature_page_ready": False},
            )


async def prepare_signature_klassenbuch(payload: dict, review_confirmed: bool) -> ApiMessage:
    if not review_confirmed:
        return ApiMessage(ok=False, message="Signatur-Vorbereitung gesperrt: Review-Bestaetigung erforderlich.")
    ue_items = payload.get("ue_items") or payload.get("unterrichtseinheiten") or []
    if len(ue_items) != 9:
        return ApiMessage(ok=False, message="Signatur-Vorbereitung gesperrt: Es muessen genau 9 UE vorhanden sein.")
    async with browser_page(storage_state_path=_storage_state_path()) as page:
        diag = KlassenbuchDiagnosticsRun(_diagnostic_run_id(), "prepare_signature_klassenbuch")
        _attach_diagnostic_listeners(page, diag)
        await _start_trace(page, diag)
        try:
            await _login(page, diag)
            await _select_entry(page, payload, diag)
            await _fill_ue(page, payload, diag)
            await _save_ue(page)
            await _open_signature_step(page)
            await _diag_step(page, diag, "signatur_page_loaded")
            await _recognize_signature_page(page)
            canvas_info = await _fill_signature(page, allow_overwrite=True, diag=diag)
            screenshot = await _safe_screenshot(page, "signatur_ready_for_submit")
            await _diag_step(page, diag, "signatur_ready_for_submit", {"screenshot_path": screenshot, **canvas_info})
            await _stop_trace(page, diag)
            summary = await _write_diagnostic_summary(
                page,
                diag,
                success=True,
                diagnostics={"screenshot_path": screenshot, **canvas_info},
            )
            _set_signature_step(StepState.manual_review, "Signatur wurde vorbereitet. Bitte Review pruefen.")
            return ApiMessage(
                ok=True,
                message="Signatur wurde vorbereitet. Bitte Review pruefen.",
                data={"screenshot": screenshot, "diagnostics": summary, "canvas_has_ink": bool(canvas_info.get("canvas_has_ink"))},
            )
        except Exception as exc:
            screenshot = await _safe_screenshot(page, "signatur_error")
            html_snapshot = await _safe_html_snapshot(page, "signatur_error")
            canvas = await _locator_or_none(page, KLASSENBUCH_SELECTORS["signature_canvas"])
            canvas_info = await _canvas_debug_info(canvas) if canvas is not None else {"canvas_detected": False, "canvas_has_ink": False}
            await _diag_step(page, diag, "signatur_error", {"error": _exception_message(exc, "Signatur-Vorbereitung fehlgeschlagen"), "exception_type": type(exc).__name__, **canvas_info})
            await _stop_trace(page, diag)
            summary = await _write_diagnostic_summary(
                page,
                diag,
                success=False,
                error_message=_exception_message(exc, "Signatur-Vorbereitung fehlgeschlagen"),
                exception_type=type(exc).__name__,
                diagnostics={"screenshot_path": screenshot, "html_snapshot_path": html_snapshot, **canvas_info},
            )
            _set_signature_step(StepState.error, "Signatur-Vorbereitung fehlgeschlagen.")
            return ApiMessage(
                ok=False,
                message=f"Signatur-Vorbereitung fehlgeschlagen: {_exception_message(exc, 'unbekannter Fehler')}",
                data={"screenshot": screenshot, "diagnostics": summary, "canvas_has_ink": bool(canvas_info.get("canvas_has_ink"))},
            )


async def submit_klassenbuch(payload: dict, review_confirmed: bool, signature_confirmed: bool = False) -> ApiMessage:
    blocked_reason = _validate_signature_submit_allowed(payload, review_confirmed, signature_confirmed)
    if blocked_reason:
        return ApiMessage(ok=False, message=blocked_reason)
    async with browser_page(storage_state_path=_storage_state_path()) as page:
        diag = KlassenbuchDiagnosticsRun(_diagnostic_run_id(), "submit_klassenbuch")
        _attach_diagnostic_listeners(page, diag)
        await _start_trace(page, diag)
        try:
            await _login(page, diag)
            await _select_entry(page, payload, diag)
            await _fill_ue(page, payload, diag)
            await _save_ue(page)
            await _open_signature_step(page)
            await _diag_step(page, diag, "signatur_page_loaded")
            await _recognize_signature_page(page)
            canvas_info = await _fill_signature(page, allow_overwrite=True, diag=diag)
            await _diag_step(page, diag, "signatur_ready_for_submit", canvas_info)
            screenshot = await _finalize_signature(page, diag)
            await _stop_trace(page, diag)
            summary = await _write_diagnostic_summary(page, diag, success=True, diagnostics={"screenshot_path": screenshot, **canvas_info})
            return ApiMessage(ok=True, message="Klassenbuch wurde final signiert.", data={"screenshot": screenshot, "diagnostics": summary, "canvas_has_ink": bool(canvas_info.get("canvas_has_ink"))})
        except Exception as exc:
            screenshot = await _safe_screenshot(page, "klassenbuch_signature_error")
            html_snapshot = await _safe_html_snapshot(page, "klassenbuch_signature_error")
            canvas = await _locator_or_none(page, KLASSENBUCH_SELECTORS["signature_canvas"])
            canvas_info = await _canvas_debug_info(canvas) if canvas is not None else {"canvas_detected": False, "canvas_has_ink": False}
            await _diag_step(page, diag, "signatur_error", {"error": _exception_message(exc, "Klassenbuch-Submit fehlgeschlagen"), "exception_type": type(exc).__name__, **canvas_info})
            await _stop_trace(page, diag)
            summary = await _write_diagnostic_summary(
                page,
                diag,
                success=False,
                error_message=_exception_message(exc, "Klassenbuch-Submit fehlgeschlagen"),
                exception_type=type(exc).__name__,
                diagnostics={"screenshot_path": screenshot, "html_snapshot_path": html_snapshot, **canvas_info},
            )
            _set_signature_step(StepState.error, "Signatur fehlgeschlagen.")
            return ApiMessage(ok=False, message=f"Klassenbuch-Submit fehlgeschlagen: {_exception_message(exc, 'unbekannter Fehler')}", data={"screenshot": screenshot, "diagnostics": summary, "canvas_has_ink": bool(canvas_info.get("canvas_has_ink"))})
