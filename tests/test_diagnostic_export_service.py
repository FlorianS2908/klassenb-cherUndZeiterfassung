from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

from app.services import diagnostic_export_service

ROOT = Path(__file__).resolve().parents[1]


def _workspace() -> Path:
    path = ROOT / ".tools" / "test_env" / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def _raw_run(root: Path, run_id: str) -> Path:
    run_dir = root / "diagnostics" / "klassenbuch" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "module": "klassenbuch",
                "action": "load_open_klassenbuecher",
                "success": False,
                "problem_category": "login",
                "error_message": "Login failed for trainer@example.com with password super-secret",
                "probable_cause": "Benutzer trainer@example.com wurde abgelehnt.",
                "next_action": "Passwort im Setup pruefen.",
                "current_url": "https://klassenbuch.gfn.de/login?session=abc&token=def",
                "page_title": "Klassenbuch",
                "login_success": False,
                "overview_loaded": False,
                "tables_found": 0,
                "rows_found": 0,
                "entries_returned": 0,
                "summary_path": r"C:\Users\Florian.Schaffer\OneDrive - Amadeus Fire AG\Desktop\KlassenbuchTimebutler\diagnostics\klassenbuch\run\summary.json",
                "cookie": "session-cookie",
                "authorization": "Bearer abc",
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "steps.json").write_text(
        json.dumps(
            [
                {
                    "step": "login_failed",
                    "current_url": "https://klassenbuch.gfn.de/login?csrf=123",
                    "html_snapshot_path": r"C:\Users\Florian.Schaffer\Desktop\secret.html",
                    "password": "super-secret",
                }
            ]
        ),
        encoding="utf-8",
    )
    (run_dir / "network.log").write_text(
        '2026-07-14 {"event":"response","url":"https://klassenbuch.gfn.de/login?token=secret","status":401,"authorization":"Bearer abc"}\n'
        '2026-07-14 {"event":"requestfailed","url":"https://id.example.test/auth?session=secret","error_text":"boom"}\n',
        encoding="utf-8",
    )
    (run_dir / "snapshot.html").write_text(
        '<html><head><title>Klassenbuch trainer@example.com</title></head>'
        '<body><form><input name="password" value="super-secret"></form><table><tr><th>Datum</th></tr></table></body></html>',
        encoding="utf-8",
    )
    (run_dir / "playwright_trace.zip").write_text("raw trace", encoding="utf-8")
    return run_dir


def test_export_creates_sanitized_files_without_secrets(monkeypatch):
    workspace = _workspace()
    run_id = "2026-07-14_17-53-31"
    _raw_run(workspace, run_id)
    monkeypatch.setattr(diagnostic_export_service, "diagnostics_root", lambda module: workspace / "diagnostics" / module)
    monkeypatch.setattr(diagnostic_export_service, "resolve_project_path", lambda value: workspace / value)
    try:
        result = diagnostic_export_service.export_klassenbuch_diagnostic(run_id)
        export_dir = workspace / result["export_folder"]
        exported_text = "\n".join(path.read_text(encoding="utf-8") for path in export_dir.iterdir() if path.is_file())

        assert (export_dir / "report.md").exists()
        assert (export_dir / "summary_sanitized.json").exists()
        assert (export_dir / "steps_sanitized.json").exists()
        assert "super-secret" not in exported_text
        assert "trainer@example.com" not in exported_text
        assert "Florian.Schaffer" not in exported_text
        assert "C:\\Users" not in exported_text
        assert "session-cookie" not in exported_text
        assert "Bearer abc" not in exported_text
        assert "token=secret" not in exported_text
        assert "<EMAIL_REDACTED>" in exported_text
        assert "Problem-Kategorie" in (export_dir / "report.md").read_text(encoding="utf-8")
        assert "Naechste Aktion" in (export_dir / "report.md").read_text(encoding="utf-8")
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_raw_diagnostics_ignored_but_docs_diagnostics_not_ignored():
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert "diagnostics/" in lines
    assert "screenshots/" in lines
    assert "logs/" in lines
    assert ".env" in lines
    assert "*.env" in lines
    assert "secrets/" in lines
    assert "credentials/" in lines
    assert "api_key*.txt" in lines
    assert "*.key" in lines
    assert "*.secret" in lines
    assert "docs/diagnostics/" not in lines
