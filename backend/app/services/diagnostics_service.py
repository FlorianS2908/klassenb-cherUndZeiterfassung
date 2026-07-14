from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import resolve_project_path


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value).strip("_") or "snapshot"


def diagnostics_root(module: str) -> Path:
    return resolve_project_path(f"diagnostics/{_safe_name(module)}")


def create_diagnostic_run(module: str, run_id: str) -> Path:
    run_dir = diagnostics_root(module) / _safe_name(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    for name in ["console.log", "network.log"]:
        path = run_dir / name
        if not path.exists():
            path.write_text("", encoding="utf-8")
    return run_dir


def diagnostic_run_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def explain_exception(exc: Exception) -> tuple[str, str]:
    if type(exc).__name__ == "NotImplementedError" or "NotImplementedError" in str(exc):
        return (
            "Playwright/Chromium konnte nicht gestartet werden. Der Fehler trat vor dem Oeffnen der Klassenbuch-Webseite auf.",
            "Playwright-Installation und Windows-Eventloop pruefen. python -m playwright install ausfuehren. Zusaetzlich ProactorEventLoopPolicy auf Windows setzen.",
        )
    return ("Fehler trat vor oder waehrend der Webautomation auf.", "Diagnoseordner pruefen und Browser-Check ausfuehren.")


def exception_message(exc: Exception, prefix: str = "") -> str:
    text = str(exc).strip() or f"unbekannter Fehler ({type(exc).__name__})"
    return f"{prefix}: {text}" if prefix else text


def write_route_error_diagnostic(module: str, action: str, step: str, exc: Exception, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    run_id = diagnostic_run_id()
    run_dir = create_diagnostic_run(module, run_id)
    probable_cause, next_action = explain_exception(exc)
    message = exception_message(exc, "Klassenbuecher konnten nicht geladen werden")
    now = datetime.now().isoformat(timespec="seconds")
    relative_folder = str(Path("diagnostics") / _safe_name(module) / run_id)
    summary = {
        "run_id": run_id,
        "module": module,
        "action": action,
        "started_at": now,
        "finished_at": now,
        "success": False,
        "step": step,
        "error_message": message,
        "exception_type": type(exc).__name__,
        "current_url": "",
        "page_title": "",
        "login_success": False,
        "overview_loaded": False,
        "tables_found": 0,
        "rows_found": 0,
        "entries_returned": 0,
        "diagnostics_folder": relative_folder,
        "summary_path": str(run_dir / "summary.json"),
        "steps_path": str(run_dir / "steps.json"),
        "console_log": str(run_dir / "console.log"),
        "network_log": str(run_dir / "network.log"),
        "trace_file": "",
        "trace_path": "",
        "probable_cause": probable_cause,
        "next_action": next_action,
        "notes": [],
    }
    if extra:
        summary.update(extra)
    steps = [
        {
            "step": step,
            "success": False,
            "exception_type": type(exc).__name__,
            "message": message,
            "timestamp": now,
        }
    ]
    write_steps(run_dir, steps)
    write_summary(run_dir, summary)
    return summary


def _mask_sensitive_html(html: str) -> str:
    masked = re.sub(r'(<input[^>]+type=["\']?password["\']?[^>]*value=)["\'][^"\']*["\']', r'\1"***"', html, flags=re.IGNORECASE)
    masked = re.sub(r'(<input[^>]+name=["\']?password["\']?[^>]*value=)["\'][^"\']*["\']', r'\1"***"', masked, flags=re.IGNORECASE)
    return masked


def _json_default(value: Any) -> str:
    return str(value)


async def save_step_snapshot(page, run_dir: Path, step_name: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    safe_step = _safe_name(step_name)
    screenshot_path = run_dir / f"{stamp}_{safe_step}.png"
    html_path = run_dir / f"{stamp}_{safe_step}.html"
    try:
        await page.screenshot(path=str(screenshot_path), full_page=True)
    except Exception:
        screenshot_path = Path("")
    try:
        html_path.write_text(_mask_sensitive_html(await page.content()), encoding="utf-8")
    except Exception:
        html_path = Path("")
    counters = await collect_page_counters(page)
    entry = {
        "step": step_name,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "current_url": getattr(page, "url", ""),
        "page_title": await _safe_title(page),
        "screenshot_path": str(screenshot_path) if str(screenshot_path) else "",
        "html_snapshot_path": str(html_path) if str(html_path) else "",
        **counters,
    }
    if extra:
        entry.update(extra)
    return entry


async def _safe_title(page) -> str:
    try:
        return await page.title()
    except Exception:
        return ""


async def collect_page_counters(page) -> dict[str, Any]:
    selectors = {
        "table_count": "table",
        "row_count": "tr",
        "tbody_row_count": "tbody tr",
        "tab_count": '[role="tab"], .nav-tabs a, .nav-tabs button',
        "visible_buttons": "button",
        "visible_links": "a",
        "found_edit_links": 'a[onclick*="forwardToWizardWithPreselection"], tr[data-index] td:last-child a, a[href*="/classbooks/wizard"]',
        "found_textareas": 'textarea[name^="classBookEntry-"], textarea[id^="classBookEntry-"], textarea.ueEntry',
    }
    counters: dict[str, Any] = {}
    for key, selector in selectors.items():
        try:
            locators = page.locator(selector)
            count = 0
            for index in range(await locators.count()):
                try:
                    if await locators.nth(index).is_visible():
                        count += 1
                except Exception:
                    continue
            counters[key] = count
        except Exception:
            counters[key] = 0
    try:
        headers = page.locator("table th")
        counters["headers_found"] = [(await headers.nth(index).inner_text()).strip() for index in range(min(await headers.count(), 30))]
    except Exception:
        counters["headers_found"] = []
    return counters


def append_console_message(run_dir: Path, message: str) -> None:
    _append_log(run_dir / "console.log", message)


def append_network_event(run_dir: Path, event: dict[str, Any]) -> None:
    _append_log(run_dir / "network.log", json.dumps(event, ensure_ascii=True, default=_json_default))


def _append_log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{datetime.now().isoformat(timespec='seconds')} {message}\n")


def write_summary(run_dir: Path, summary: dict[str, Any]) -> Path:
    path = run_dir / "summary.json"
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=True, default=_json_default), encoding="utf-8")
    return path


def write_steps(run_dir: Path, steps: list[dict[str, Any]]) -> Path:
    path = run_dir / "steps.json"
    path.write_text(json.dumps(steps, indent=2, ensure_ascii=True, default=_json_default), encoding="utf-8")
    return path


def list_diagnostic_runs(module: str) -> list[dict[str, Any]]:
    root = diagnostics_root(module)
    if not root.exists():
        return []
    runs = []
    for run_dir in sorted((path for path in root.iterdir() if path.is_dir()), key=lambda path: path.name, reverse=True):
        summary = read_summary(module, run_dir.name)
        runs.append(
            {
                "run_id": run_dir.name,
                "created_at": summary.get("started_at") or run_dir.name,
                "success": summary.get("success", False),
                "error_message": summary.get("error_message", ""),
                "entries_returned": summary.get("entries_returned", 0),
            }
        )
    return runs


def latest_summary(module: str) -> dict[str, Any]:
    runs = list_diagnostic_runs(module)
    if not runs:
        return {}
    return read_summary(module, runs[0]["run_id"])


def read_summary(module: str, run_id: str) -> dict[str, Any]:
    path = diagnostics_root(module) / _safe_name(run_id) / "summary.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_steps(module: str, run_id: str) -> list[dict[str, Any]]:
    path = diagnostics_root(module) / _safe_name(run_id) / "steps.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_diagnostic_file(module: str, run_id: str, name: str) -> Path:
    run_dir = (diagnostics_root(module) / _safe_name(run_id)).resolve()
    path = (run_dir / name).resolve()
    try:
        path.relative_to(run_dir)
    except ValueError as exc:
        raise FileNotFoundError(name) from exc
    if not path.is_file():
        raise FileNotFoundError(name)
    return path
