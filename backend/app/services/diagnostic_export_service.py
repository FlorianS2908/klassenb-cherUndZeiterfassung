from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.config import resolve_project_path
from app.services.diagnostics_service import diagnostic_run_id, diagnostics_root, read_steps, read_summary

SECRET_KEY_RE = re.compile(r"(password|passwd|pwd|secret|token|api[_-]?key|authorization|cookie|set-cookie|session|csrf|bearer)", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
LOCAL_PATH_RE = re.compile(r"C:\\Users\\([^\\\s]+)\\OneDrive - Amadeus Fire AG\\Desktop\\KlassenbuchTimebutler", re.IGNORECASE)
WINDOWS_USER_RE = re.compile(r"Florian\.Schaffer", re.IGNORECASE)

STRUCTURE_KEYS = {
    "page_type",
    "title",
    "page_title",
    "form_count",
    "input_count",
    "table_count",
    "tables_found",
    "row_count",
    "rows_found",
    "tbody_row_count",
    "headers_found",
    "tabs_found",
    "tab_names_found",
    "edit_links_found",
    "found_edit_links",
    "entries_returned",
}


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value).strip("_") or "diagnostic"


def _strip_url_query(value: str) -> str:
    if not value.lower().startswith(("http://", "https://")):
        return value
    parsed = urlsplit(value)
    query = "error" if parsed.query == "error" else ""
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, ""))


def sanitize_text(value: str) -> str:
    sanitized = EMAIL_RE.sub("<EMAIL_REDACTED>", value)
    sanitized = re.sub(
        r"\b(password|passwort|passwd|pwd|secret|token|api[_-]?key|authorization|cookie|set-cookie|session|csrf|bearer)\b\s*[:=]?\s+[^\s,;]+",
        r"\1 <REDACTED>",
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = LOCAL_PATH_RE.sub(r"<LOCAL_PROJECT_PATH>", sanitized)
    sanitized = WINDOWS_USER_RE.sub("<WINDOWS_USER>", sanitized)
    sanitized = re.sub(r"C:\\Users\\[^\s\"']+", r"<LOCAL_PROJECT_PATH>", sanitized)
    if sanitized.lower().startswith(("http://", "https://")):
        sanitized = _strip_url_query(sanitized)
    return sanitized


def sanitize_value(value: Any, key: str = "") -> Any:
    if SECRET_KEY_RE.search(key):
        if isinstance(value, bool):
            return value
        return "<REDACTED>"
    if isinstance(value, dict):
        return {sanitize_text(str(child_key)): sanitize_value(child_value, str(child_key)) for child_key, child_value in value.items() if not SECRET_KEY_RE.search(str(child_key))}
    if isinstance(value, list):
        return [sanitize_value(item, key) for item in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return value


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _network_metadata(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "network.log"
    domains: set[str] = set()
    statuses: list[int] = []
    request_failed = 0
    if not path.exists():
        return {"domains": [], "statuses": [], "request_failed": 0}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = re.search(r"(\{.*\})", line)
        if not match:
            continue
        try:
            event = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        url = str(event.get("url", ""))
        if url:
            parsed = urlsplit(url)
            if parsed.netloc:
                domains.add(parsed.netloc)
        if isinstance(event.get("status"), int):
            statuses.append(event["status"])
        if event.get("event") == "requestfailed":
            request_failed += 1
    return {"domains": sorted(domains), "statuses": sorted(set(statuses)), "request_failed": request_failed}


def _html_analysis(run_dir: Path) -> dict[str, Any] | None:
    html_files = sorted(run_dir.glob("*.html"))
    if not html_files:
        return None
    latest_html = html_files[-1].read_text(encoding="utf-8", errors="ignore")
    headers = re.findall(r"<th[^>]*>(.*?)</th>", latest_html, flags=re.IGNORECASE | re.DOTALL)
    tabs = re.findall(r'role=["\']tab["\'][^>]*>(.*?)<', latest_html, flags=re.IGNORECASE | re.DOTALL)
    title_match = re.search(r"<title[^>]*>(.*?)</title>", latest_html, flags=re.IGNORECASE | re.DOTALL)
    analysis = {
        "page_type": "html_snapshot",
        "title": sanitize_text(re.sub(r"\s+", " ", title_match.group(1)).strip()) if title_match else "",
        "form_count": len(re.findall(r"<form\b", latest_html, flags=re.IGNORECASE)),
        "input_count": len(re.findall(r"<input\b", latest_html, flags=re.IGNORECASE)),
        "table_count": len(re.findall(r"<table\b", latest_html, flags=re.IGNORECASE)),
        "row_count": len(re.findall(r"<tr\b", latest_html, flags=re.IGNORECASE)),
        "headers_found": [sanitize_text(re.sub(r"<[^>]+>", "", header).strip()) for header in headers[:30]],
        "tabs_found": [sanitize_text(re.sub(r"<[^>]+>", "", tab).strip()) for tab in tabs[:20] if tab.strip()],
        "edit_links_found": len(re.findall(r"forwardToWizardWithPreselection|/classbooks/wizard|Bearbeiten", latest_html, flags=re.IGNORECASE)),
    }
    return analysis


def _pick_structure(data: dict[str, Any]) -> dict[str, Any]:
    return {key: sanitize_value(value, key) for key, value in data.items() if key in STRUCTURE_KEYS}


def _evaluation(summary: dict[str, Any]) -> str:
    category = str(summary.get("problem_category", ""))
    if category == "login":
        return "Die Webseite wurde erreicht, aber der Login wurde abgelehnt. Zugangsdaten im Setup pruefen."
    if category == "browser_start":
        return "Der Browser konnte nicht gestartet werden. Playwright/Chromium pruefen."
    if summary.get("overview_loaded") is False and summary.get("login_success") is True:
        return "Login erfolgreich, aber Uebersicht wurde nicht erreicht."
    if int(summary.get("tables_found") or summary.get("table_count") or 0) == 0 and summary.get("overview_loaded") is True:
        return "Uebersicht erreicht, aber Tabelle nicht gefunden."
    if int(summary.get("rows_found") or summary.get("row_count") or 0) > 0 and int(summary.get("entries_returned") or 0) == 0:
        return "Tabelle vorhanden, aber Parser erzeugt keine Eintraege."
    return "Keine eindeutige automatische Bewertung verfuegbar."


def _yes_no(value: Any) -> str:
    return "ja" if bool(value) else "nein"


def _report(summary: dict[str, Any], metadata: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Klassenbuch Diagnosebericht",
            "",
            "## Ergebnis",
            f"- Erfolg: {_yes_no(summary.get('success'))}",
            f"- Problem-Kategorie: {summary.get('problem_category', '-')}",
            f"- Fehlermeldung: {summary.get('error_message', '-')}",
            f"- Wahrscheinliche Ursache: {summary.get('probable_cause', '-')}",
            f"- Naechste Aktion: {summary.get('next_action', '-')}",
            "",
            "## Laufdaten",
            f"- Run-ID: {summary.get('run_id', '-')}",
            f"- Start: {summary.get('started_at', '-')}",
            f"- Ende: {summary.get('finished_at', '-')}",
            f"- Modul: {summary.get('module', '-')}",
            f"- Aktion: {summary.get('action', '-')}",
            "",
            "## Status",
            f"- Browser gestartet: {_yes_no(summary.get('playwright_started', True))}",
            f"- Webseite erreicht: {_yes_no(summary.get('website_reached', False))}",
            f"- Login erfolgreich: {_yes_no(summary.get('login_success'))}",
            f"- Overview geladen: {_yes_no(summary.get('overview_loaded'))}",
            f"- Tabellen gefunden: {summary.get('tables_found', summary.get('table_count', 0))}",
            f"- Zeilen gefunden: {summary.get('rows_found', summary.get('row_count', 0))}",
            f"- Eintraege zurueckgegeben: {summary.get('entries_returned', 0)}",
            "",
            "## Diagnosepfad lokal",
            "- Lokaler Rohdatenpfad: <LOCAL_ONLY>",
            "",
            "## Technische Details",
            f"- current_url: {summary.get('current_url', '-')}",
            f"- page_title: {summary.get('page_title', '-')}",
            f"- headers_found: {summary.get('headers_found', [])}",
            f"- tabs: {summary.get('tabs', {})}",
            f"- table_count: {summary.get('table_count', summary.get('tables_found', 0))}",
            f"- row_count: {summary.get('row_count', summary.get('rows_found', 0))}",
            f"- entries_returned: {summary.get('entries_returned', 0)}",
            f"- trace vorhanden: {_yes_no(metadata.get('trace_present'))}",
            "",
            "## Bewertung",
            _evaluation(summary),
            "",
        ]
    )


def export_klassenbuch_diagnostic(run_id: str | None = None) -> dict[str, Any]:
    selected_run_id = run_id or diagnostic_run_id()
    if run_id is None:
        runs = sorted((path for path in diagnostics_root("klassenbuch").glob("*") if path.is_dir()), key=lambda path: path.name, reverse=True)
        if not runs:
            raise FileNotFoundError("Noch keine Diagnose vorhanden.")
        selected_run_id = runs[0].name
    safe_run_id = _safe_name(selected_run_id)
    run_dir = diagnostics_root("klassenbuch") / safe_run_id
    if not run_dir.exists():
        raise FileNotFoundError("Diagnose-Lauf nicht gefunden.")

    summary = sanitize_value(read_summary("klassenbuch", safe_run_id) or _read_json(run_dir / "summary.json") or {}, "summary")
    steps = sanitize_value(read_steps("klassenbuch", safe_run_id) or _read_json(run_dir / "steps.json") or [], "steps")
    if not isinstance(summary, dict):
        summary = {}
    if not isinstance(steps, list):
        steps = []

    summary["run_id"] = safe_run_id
    metadata = {
        "run_id": safe_run_id,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "source": "diagnostics/klassenbuch/<RUN_ID>",
        "raw_data_exported": False,
        "trace_present": (run_dir / "playwright_trace.zip").exists(),
        "network": sanitize_value(_network_metadata(run_dir), "network"),
        "local_raw_path": "<LOCAL_ONLY>",
    }
    html_analysis = sanitize_value(_html_analysis(run_dir), "html_analysis")
    if isinstance(html_analysis, dict):
        metadata["html_analysis_file"] = "html_analysis_sanitized.json"
        summary.update({key: summary.get(key, value) for key, value in _pick_structure(html_analysis).items()})

    export_dir = resolve_project_path(f"docs/diagnostics/klassenbuch/{safe_run_id}")
    export_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "summary_sanitized.json": summary,
        "steps_sanitized.json": steps,
        "metadata.json": metadata,
    }
    for name, content in files.items():
        (export_dir / name).write_text(json.dumps(content, indent=2, ensure_ascii=True), encoding="utf-8")
    if isinstance(html_analysis, dict):
        (export_dir / "html_analysis_sanitized.json").write_text(json.dumps(html_analysis, indent=2, ensure_ascii=True), encoding="utf-8")
    (export_dir / "report.md").write_text(_report(summary, metadata), encoding="utf-8")
    file_names = ["summary_sanitized.json", "steps_sanitized.json", "report.md", "metadata.json"]
    if isinstance(html_analysis, dict):
        file_names.append("html_analysis_sanitized.json")
    return {
        "ok": True,
        "message": "Sanitisierter Diagnosebericht wurde erzeugt.",
        "run_id": safe_run_id,
        "export_folder": f"docs/diagnostics/klassenbuch/{safe_run_id}",
        "files": file_names,
    }
