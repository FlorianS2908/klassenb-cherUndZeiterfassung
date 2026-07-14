import pytest
import shutil
from pathlib import Path
from uuid import uuid4

from app.services import diagnostics_service


def _workspace_tmp() -> Path:
    path = Path(".test_tmp_unit") / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_diagnostic_run_writes_summary_and_steps(monkeypatch):
    tmp_path = _workspace_tmp()
    monkeypatch.setattr(diagnostics_service, "resolve_project_path", lambda value: tmp_path / value)
    run_dir = diagnostics_service.create_diagnostic_run("klassenbuch", "run-1")

    try:
        diagnostics_service.write_summary(run_dir, {"run_id": "run-1", "success": True, "entries_returned": 2})
        diagnostics_service.write_steps(run_dir, [{"step": "overview_loaded"}])

        assert diagnostics_service.read_summary("klassenbuch", "run-1")["entries_returned"] == 2
        assert diagnostics_service.read_steps("klassenbuch", "run-1")[0]["step"] == "overview_loaded"
        assert diagnostics_service.list_diagnostic_runs("klassenbuch")[0]["run_id"] == "run-1"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_diagnostic_file_resolution_blocks_traversal(monkeypatch):
    tmp_path = _workspace_tmp()
    monkeypatch.setattr(diagnostics_service, "resolve_project_path", lambda value: tmp_path / value)
    run_dir = diagnostics_service.create_diagnostic_run("klassenbuch", "run-1")
    try:
        (run_dir / "console.log").write_text("ok", encoding="utf-8")

        assert diagnostics_service.resolve_diagnostic_file("klassenbuch", "run-1", "console.log").name == "console.log"
        with pytest.raises(FileNotFoundError):
            diagnostics_service.resolve_diagnostic_file("klassenbuch", "run-1", "../secret.txt")
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
