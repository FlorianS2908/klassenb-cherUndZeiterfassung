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
