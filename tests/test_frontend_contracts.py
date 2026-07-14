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


def test_guided_klassenbuch_workflow_contracts():
    app = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    layout = (ROOT / "frontend" / "src" / "components" / "Layout" / "Layout.tsx").read_text(encoding="utf-8")
    workflow = (ROOT / "frontend" / "src" / "state" / "workflowState.ts").read_text(encoding="utf-8")
    klassenbuch = (ROOT / "frontend" / "src" / "routes" / "KlassenbuchPage.tsx").read_text(encoding="utf-8")
    analysis = (ROOT / "frontend" / "src" / "routes" / "FileAnalysisPage.tsx").read_text(encoding="utf-8")
    review = (ROOT / "frontend" / "src" / "routes" / "ReviewPage.tsx").read_text(encoding="utf-8")

    assert "'/analysis': 'analysis'" in app
    assert "FileAnalysisPage" in app
    assert "workflow.selectedClassbook" in app
    assert "workflow.generatedEntries.length !== 9" in app
    assert "localStorage" in workflow
    assert "selectedClassbook" in workflow
    assert "generatedEntries" in workflow
    assert "resetWorkflow" in workflow
    assert "1 Uebersicht" in layout
    assert "2 Klassenbuecher" in layout
    assert "3 Datei & Analyse" in layout
    assert "4 Review" in layout
    assert "Workflow zuruecksetzen" in layout
    assert "Erweiterte Tools" in layout
    assert "selectedClassbook" in layout
    assert "Auswaehlen & weiter" in klassenbuch
    assert "setPage('analysis')" in klassenbuch
    assert "setWorkflow({" in klassenbuch
    assert "Kein Klassenbuch ausgewaehlt" in analysis
    assert "KI-Analyse starten" in analysis
    assert "Array.from({ length: 9 }" in analysis
    assert "Zur Review" in analysis
    assert "normalizeEntries" in analysis
    assert "Review noch nicht verfuegbar" in review
    assert "Ich habe die Eintraege geprueft" in review
    assert "Ins Klassenbuch eintragen" in review
    assert "prepareKlassenbuch" in review
