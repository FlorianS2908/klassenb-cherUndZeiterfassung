from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_klassenbuch


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
