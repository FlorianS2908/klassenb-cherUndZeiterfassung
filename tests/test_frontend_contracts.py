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


def test_setup_page_shows_secure_credential_storage_and_login_test():
    content = (ROOT / "frontend" / "src" / "routes" / "SetupPage.tsx").read_text(encoding="utf-8")

    assert "Windows Credential Manager" in content
    assert "Klassenbuch Passwort gespeichert" in content
    assert "Klassenbuch-Login testen" in content
    assert "testKlassenbuchLogin" in content
