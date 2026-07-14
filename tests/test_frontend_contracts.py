from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_klassenbuch_ui_exposes_diagnostics_and_browser_check():
    content = (ROOT / "frontend" / "src" / "routes" / "KlassenbuchPage.tsx").read_text(encoding="utf-8")
    assert "Letzte Diagnose oeffnen" in content
    assert "Browser-Check" in content
    assert "function isBrowserStartProblem" in content
    assert "function isPlaywrightPythonApiProblem" in content
    assert "playwright-browserstart" in content
    assert "notimplementederror" in content
    assert "Playwright-Python-API-Fehler" in content
    assert "Fehlerbericht fuers Repo exportieren" in content
    assert "exportLatestKlassenbuchDiagnostic" in content
    assert "diagnostics/ nicht committen" in content
    assert "Klassenbuecher werden geladen. Login laeuft im Hintergrund" in content
    assert "Login laeuft ..." in content
    assert "Klassenbuch-Zugangsdaten" in content
    assert "Zugangsdaten lokal speichern" in content
    assert "Letzter Login-Test" in content
    assert "getKlassenbuchCredentialStatus" in content


def test_setup_page_shows_secure_credential_storage_and_login_test():
    content = (ROOT / "frontend" / "src" / "routes" / "SetupPage.tsx").read_text(encoding="utf-8")

    assert "Windows Credential Manager" in content
    assert "Klassenbuch Passwort gespeichert" in content
    assert "Klassenbuch-Login testen" in content
    assert "Klassenbuch-Zugangsdaten lokal speichern" in content
    assert "Lokale Zugangsdaten loeschen" in content
    assert "testKlassenbuchLogin" in content


def test_app_routes_setup_not_found_and_error_boundary():
    app = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    not_found = (ROOT / "frontend" / "src" / "routes" / "NotFoundPage.tsx").read_text(encoding="utf-8")
    boundary = (ROOT / "frontend" / "src" / "components" / "ErrorBoundary" / "AppErrorBoundary.tsx").read_text(encoding="utf-8")

    assert "'/setup': 'setup'" in app
    assert "'/klassenbuch': 'klassenbuch'" in app
    assert "return routes[normalized] ?? 'not-found'" in app
    assert "AppErrorBoundary" in app
    assert "Seite nicht gefunden" in not_found
    assert "Zur Startseite" in not_found
    assert "Zum Setup" in not_found
    assert "unhandledrejection" in boundary
    assert "window.addEventListener('error'" in boundary
    assert "Zum Setup" in boundary
    assert "Login testen" in (ROOT / "frontend" / "src" / "routes" / "KlassenbuchPage.tsx").read_text(encoding="utf-8")
