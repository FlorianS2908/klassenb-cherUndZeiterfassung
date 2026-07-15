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
    assert "Klassenbuecher werden geladen ... Login/Session wird geprueft ... Offene Klassenbuecher werden gelesen" in content
    assert "Vollstaendige Diagnose laden" in content
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
    klassenbuch_page = (ROOT / "frontend" / "src" / "routes" / "KlassenbuchPage.tsx").read_text(encoding="utf-8")
    service = (ROOT / "frontend" / "src" / "services" / "klassenbuchService.ts").read_text(encoding="utf-8")
    assert "Klassenbuecher werden geladen ... Login/Session wird geprueft ... Offene Klassenbuecher werden gelesen" in klassenbuch_page
    assert "Vollstaendige Diagnose laden" in klassenbuch_page
    assert "getOpenKlassenbuecherDiagnostic" in klassenbuch_page
    assert "/api/klassenbuch/open-diagnostic" in service


def test_guided_klassenbuch_workflow_contracts():
    app = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    layout = (ROOT / "frontend" / "src" / "components" / "Layout" / "Layout.tsx").read_text(encoding="utf-8")
    workflow = (ROOT / "frontend" / "src" / "state" / "workflowState.ts").read_text(encoding="utf-8")
    klassenbuch = (ROOT / "frontend" / "src" / "routes" / "KlassenbuchPage.tsx").read_text(encoding="utf-8")
    analysis = (ROOT / "frontend" / "src" / "routes" / "FileAnalysisPage.tsx").read_text(encoding="utf-8")
    review = (ROOT / "frontend" / "src" / "routes" / "ReviewPage.tsx").read_text(encoding="utf-8")
    signature = (ROOT / "frontend" / "src" / "routes" / "SignatureSettingsPage.tsx").read_text(encoding="utf-8")
    signature_service = (ROOT / "frontend" / "src" / "services" / "signatureService.ts").read_text(encoding="utf-8")

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
    assert "Zuerst ein Klassenbuch unter Schritt 2 auswaehlen" in layout
    assert "Zuerst Datei hochladen und KI-Analyse abschliessen" in layout
    assert "disabled={disabled}" in layout
    assert "workflow.generatedEntries.length !== 9" in layout
    assert "done" in layout
    assert "Bearbeiten / Auswaehlen & weiter" in klassenbuch
    assert "Nicht bearbeitbar" in klassenbuch
    assert "disabled={!editable}" in klassenbuch
    assert "if (!book.editable) return" in klassenbuch
    assert "setPage('analysis', { selectedClassbook: true })" in klassenbuch
    assert "setWorkflow({" in klassenbuch
    assert "analysisResult: null" in klassenbuch
    assert "reviewConfirmed: false" in klassenbuch
    assert "signatureReady: false" in klassenbuch
    assert "Kein Klassenbuch ausgewaehlt" in analysis
    assert "Bitte waehlen Sie zuerst unter Klassenbuecher ein bearbeitbares Klassenbuch aus." in analysis
    assert "Ausgewaehltes Klassenbuch" in analysis
    assert "<span>Titel</span>" in analysis
    assert "<span>Nummer</span>" in analysis
    assert "<span>Datum</span>" in analysis
    assert "<span>Raum</span>" in analysis
    assert "<span>Status</span>" in analysis
    assert "<span>Tab/Gruppe</span>" in analysis
    assert "Anderes Klassenbuch auswaehlen" in analysis
    assert "Auswahl zuruecksetzen" in analysis
    assert "Bitte laden Sie zuerst eine Datei hoch." in analysis
    assert "disabled={!selection.trim()}" in analysis
    assert "disabled={!canAnalyze}" in analysis
    assert "const canAnalyze = Boolean(workflow.selectedClassbook && file && selection.trim())" in analysis
    assert "Bitte geben Sie die Folien-/Seitenrange ein" in analysis
    assert "KI-Analyse starten" in analysis
    assert "Array.from({ length: 9 }" in analysis
    assert "Zur Review" in analysis
    assert "const canGoReview = items.length === 9 && items.every((item) => item.content.trim())" in analysis
    assert "disabled={!canGoReview}" in analysis
    assert "normalizeEntries" in analysis
    assert "Review noch nicht verfuegbar" in review
    assert "Ich habe die 9 Unterrichtseinheiten geprueft" in review
    assert "Klassenbuch befuellen und zur Signatur" in review
    assert "fillClassbookAndOpenSignature" in review
    assert "number: item.number ?? index + 1" in review
    assert "content: item.content" in review
    assert "formats: item.formats?.length" in review
    assert "Klassenbuch wurde befuellt und die Signaturseite wurde geoeffnet" in review
    assert "Ich bestaetige, dass diese Signatur final verwendet werden darf" in review
    assert "Signatur vorbereiten" in review
    assert "Final signieren" in review
    assert "prepareKlassenbuchSignature" in review
    assert "submitKlassenbuch" in review
    assert "!autoSubmit" in review
    assert "signaturePrepared" in review
    assert "Signatur wurde in das Klassenbuch-Canvas eingetragen" in review
    assert "fillClassbook" in review
    assert "Signatur verwalten" in signature
    assert "onPointerDown" in signature
    assert "Signatur lokal speichern" in signature
    assert "Gespeicherte Signatur testen" in signature
    assert "preview_png_data_url" in signature_service
    assert "/api/signature/save" in signature_service


def test_app_hard_guards_direct_workflow_urls():
    app = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")

    assert "page === 'analysis' && !workflow.selectedClassbook" in app
    assert "setPageState('klassenbuch')" in app
    assert "window.history.replaceState(null, '', '/klassenbuch')" in app
    assert "Bitte zuerst ein Klassenbuch auswaehlen." in app
    assert "page === 'review' && (!workflow.analysisDone || workflow.generatedEntries.length !== 9)" in app
    assert "setPageState('analysis')" in app
    assert "setPage('analysis', { selectedClassbook: true })" not in app
