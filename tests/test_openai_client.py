from pathlib import Path

from app.config import get_settings
from app.services.openai_client import load_api_key, normalize_ue_items, public_status, trim_text


def test_openai_key_loaded_from_file(monkeypatch):
    key_file = Path(__file__).resolve().parents[1] / "openai_key_test.secret"
    key_file.write_text("sk-test-value", encoding="utf-8")
    settings = get_settings()
    monkeypatch.setattr(settings, "openai_api_key_file", str(key_file))
    monkeypatch.setattr(settings, "openai_api_key", "")
    key, status = load_api_key()
    assert public_status()["key_present"] is True
    key_file.unlink()
    assert key == "sk-test-value"
    assert status.source == "file"


def test_missing_key_file_disables_ai(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "openai_api_key_file", "C:/does/not/exist/api_key_klassenbuch.txt")
    monkeypatch.setattr(settings, "openai_api_key", "")
    key, status = load_api_key()
    assert key == ""
    assert not status.active


def test_empty_key_file_disables_ai(monkeypatch):
    key_file = Path(__file__).resolve().parents[1] / "openai_empty_key_test.secret"
    key_file.write_text("", encoding="utf-8")
    settings = get_settings()
    monkeypatch.setattr(settings, "openai_api_key_file", str(key_file))
    key, status = load_api_key()
    key_file.unlink()
    assert key == ""
    assert status.source == "empty_file"


def test_env_key_fallback(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "openai_api_key_file", "")
    monkeypatch.setattr(settings, "openai_api_key", "sk-env-value")
    key, status = load_api_key()
    assert key == "sk-env-value"
    assert status.source == "env"


def test_trim_text_uses_limit(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "openai_max_input_chars", 1200)
    trimmed, truncated = trim_text("x" * 1300)
    assert len(trimmed) == 1200
    assert truncated


def test_missing_required_format_is_added():
    items = normalize_ue_items([
        {"ue": index, "lehrinhalt": "Sachlicher Lehrinhalt zur Unterrichtsdokumentation mit ausreichend Laenge.", "lernformate": ["Gruppenarbeit"]}
        for index in range(1, 10)
    ])
    assert all("Aufgaben-/Uebungsbesprechung" in item.formats for item in items)
