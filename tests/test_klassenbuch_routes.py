from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_klassenbuch
from app.services import credentials_service, local_credentials_file
from pathlib import Path
from uuid import uuid4
import shutil

ROOT = Path(__file__).resolve().parents[1]


def test_browser_health_endpoint_returns_diagnostics_on_failure(monkeypatch):
    async def fake_health():
        return {"ok": False, "step": "playwright_start", "message": "boom", "exception_type": "RuntimeError", "details": {}}

    monkeypatch.setattr(routes_klassenbuch, "check_playwright_health", fake_health)
    monkeypatch.setattr(
        routes_klassenbuch,
        "write_route_error_diagnostic",
        lambda module, action, step, exc, extra=None: {
            "run_id": "run-1",
            "diagnostics_folder": "diagnostics/klassenbuch/run-1",
            "step": step,
            "error_message": str(exc),
            "exception_type": type(exc).__name__,
        },
    )
    app = FastAPI()
    app.include_router(routes_klassenbuch.router)
    client = TestClient(app)

    response = client.get("/api/klassenbuch/browser-health")
    body = response.json()

    assert response.status_code == 200
    assert body["ok"] is False
    assert body["diagnostics"]["diagnostics_folder"] == "diagnostics/klassenbuch/run-1"


def test_open_books_route_error_returns_diagnostics_folder(monkeypatch):
    async def fake_load():
        raise NotImplementedError()

    monkeypatch.setattr(routes_klassenbuch, "load_klassenbuecher_overview", fake_load)
    monkeypatch.setattr(
        routes_klassenbuch,
        "write_route_error_diagnostic",
        lambda module, action, step, exc, extra=None: {
            "run_id": "run-2",
            "diagnostics_folder": "diagnostics/klassenbuch/run-2",
            "step": step,
            "error_message": "Klassenbuecher konnten nicht geladen werden: unbekannter Fehler (NotImplementedError)",
            "exception_type": type(exc).__name__,
            "probable_cause": "Playwright/Chromium konnte nicht gestartet werden.",
            "next_action": "Browser-Check ausfuehren.",
        },
    )
    app = FastAPI()
    app.include_router(routes_klassenbuch.router)
    client = TestClient(app)

    response = client.get("/api/klassenbuch/open")
    body = response.json()

    assert response.status_code == 500
    assert body["detail"]["diagnostics"]["diagnostics_folder"] == "diagnostics/klassenbuch/run-2"
    assert body["detail"]["diagnostics"]["probable_cause"]


def test_klassenbuch_credentials_endpoints_do_not_return_password(monkeypatch):
    workspace = ROOT / ".tools" / "test_env" / uuid4().hex
    monkeypatch.setattr(local_credentials_file, "resolve_project_path", lambda value: workspace / value)
    monkeypatch.setattr(credentials_service, "get_klassenbuch_credentials_file_status", local_credentials_file.get_klassenbuch_credentials_file_status)
    monkeypatch.setattr(credentials_service, "read_klassenbuch_credentials_file", local_credentials_file.read_klassenbuch_credentials_file)
    app = FastAPI()
    app.include_router(routes_klassenbuch.router)
    client = TestClient(app)

    try:
        save_response = client.post("/api/klassenbuch/credentials/save", json={"username": "trainer@example.com", "password": "local-secret"})
        status_response = client.get("/api/klassenbuch/credentials/status")
        delete_response = client.post("/api/klassenbuch/credentials/delete")

        assert save_response.status_code == 200
        assert status_response.status_code == 200
        assert save_response.json()["data"]["source"] == "local_file"
        assert status_response.json()["data"]["password_present"] is True
        assert "local-secret" not in str(save_response.json())
        assert "local-secret" not in str(status_response.json())
        assert delete_response.status_code == 200
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_klassenbuch_login_test_endpoint_uses_payload_without_hard_error(monkeypatch):
    async def fake_login(username=None, password=None, url=None):
        assert username == "trainer@example.com"
        assert password == "local-secret"
        return {"ok": False, "message": "Login fehlgeschlagen.", "problem_category": "login", "credential_source_used": "payload"}

    monkeypatch.setattr(routes_klassenbuch, "test_klassenbuch_login_only", fake_login)
    app = FastAPI()
    app.include_router(routes_klassenbuch.router)
    client = TestClient(app)

    response = client.post("/api/klassenbuch/login-test", json={"username": "trainer@example.com", "password": "local-secret"})
    body = response.json()

    assert response.status_code == 200
    assert body["ok"] is False
    assert body["data"]["credential_source_used"] == "payload"
    assert "local-secret" not in str(body)
