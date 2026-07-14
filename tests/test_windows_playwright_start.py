from pathlib import Path

from app.browser.playwright_health import _details
from app.config import Settings

ROOT = Path(__file__).resolve().parents[1]


def test_sitecustomize_exists_for_early_windows_eventloop_policy():
    assert (ROOT / "backend" / "sitecustomize.py").exists()


def test_main_uses_uvicorn_without_reload():
    content = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    assert "reload=False" in content
    assert "reload=True" not in content


def test_start_batch_uses_uvicorn_without_reload():
    content = (ROOT / "KlassenbuchTool_starten.bat").read_text(encoding="utf-8")
    assert "-m uvicorn app.main:app --host 127.0.0.1 --port 8000" in content
    assert "--reload" not in content


def test_browser_health_details_include_eventloop_information():
    details = _details()
    assert "platform" in details
    assert "python_version" in details
    assert "event_loop_policy" in details
    assert "is_windows_proactor_policy" in details


def test_browser_headless_default_is_true():
    settings = Settings()
    assert settings.browser_headless is True
