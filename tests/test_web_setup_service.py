from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import config
from app.api.routes_setup import router
from app.models.schemas import SetupPayload
from app.services import setup_service

ROOT = Path(__file__).resolve().parents[1]


def _env_path():
    folder = ROOT / ".tools" / "test_env" / uuid4().hex
    folder.mkdir(parents=True, exist_ok=True)
    return folder / ".env"


def _payload(**overrides):
    data = {
        "klassenbuch_url": "https://klassenbuch.example/login",
        "timebutler_url": "https://timebutler.example/login",
        "klassenbuch_username": "trainer@example.com",
        "klassenbuch_password": "secret-one",
        "timebutler_username": "",
        "timebutler_password": "",
        "use_separate_timebutler_credentials": False,
        "openai_api_key_file": "",
        "openai_api_key": "secret-two",
        "openai_model": "gpt-4o-mini",
        "openai_max_input_chars": 30000,
        "openai_timeout_seconds": 60,
        "openai_retry_count": 2,
        "openai_temperature": 0.2,
        "auto_submit": False,
        "default_signature": "Schaffer",
        "upload_folder": "./uploads",
        "screenshot_folder": "./screenshots",
        "log_folder": "./logs",
        "error_report_folder": "./error_reports",
        "analysis_history_folder": "./analysis_history",
        "reference_screenshot_dir": "",
        "timebutler_project": "FbW",
        "timebutler_category": "Training/Coaching",
        "timebutler_start": "08:30",
        "timebutler_end": "16:30",
        "timebutler_pause": "45m",
        "timebutler_remark": "Training/Coaching",
        "federal_state": "BW",
        "blocked_dates": "",
        "vacation_dates": "",
        "sick_dates": "",
        "desktop_notifications": True,
        "auto_open_browser": True,
        "auto_dry_run_on_start": False,
        "github_remote_url": "",
        "git_default_branch": "main",
    }
    data.update(overrides)
    return SetupPayload(**data)


def test_check_setup_without_env_points_to_web_ui(monkeypatch):
    env_path = _env_path()
    monkeypatch.setattr(config, "ENV_PATH", env_path)
    monkeypatch.setattr(setup_service, "ENV_PATH", env_path)
    config.get_settings.cache_clear()

    result = setup_service.check_setup()

    assert result.setup_required is True
    assert result.missing == ["ENV_FILE"]
    assert "Weboberflaeche" in result.messages[0]


def test_check_setup_detects_missing_required_values(monkeypatch):
    env_path = _env_path()
    env_path.write_text(
        'KLASSENBUCH_URL="https://klassenbuch.example"\n'
        'TIMEBUTLER_URL="https://timebutler.example"\n'
        'KLASSENBUCH_USERNAME=""\n'
        'KLASSENBUCH_PASSWORD=""\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "ENV_PATH", env_path)
    monkeypatch.setattr(setup_service, "ENV_PATH", env_path)
    config.get_settings.cache_clear()

    result = setup_service.check_setup()

    assert result.setup_required is True
    assert "KLASSENBUCH_USERNAME" in result.missing
    assert "KLASSENBUCH_PASSWORD" in result.missing


def test_save_setup_writes_env_without_returning_secrets(monkeypatch):
    env_path = _env_path()
    monkeypatch.setattr(config, "ENV_PATH", env_path)
    monkeypatch.setattr(setup_service, "ENV_PATH", env_path)
    config.get_settings.cache_clear()

    result = setup_service.save_setup(_payload())
    content = env_path.read_text(encoding="utf-8")

    assert "KLASSENBUCH_PASSWORD" in content
    assert "secret-one" in content
    assert "secret-one" not in str(result)
    assert "secret-two" not in str(result)
    assert (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines().count(".env") >= 1


def test_save_setup_preserves_existing_password_when_form_is_empty(monkeypatch):
    env_path = _env_path()
    env_path.write_text(
        'KLASSENBUCH_URL="https://old.example"\n'
        'TIMEBUTLER_URL="https://old-time.example"\n'
        'KLASSENBUCH_USERNAME="old@example.com"\n'
        'KLASSENBUCH_PASSWORD="kept-secret"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "ENV_PATH", env_path)
    monkeypatch.setattr(setup_service, "ENV_PATH", env_path)
    config.get_settings.cache_clear()

    setup_service.save_setup(_payload(klassenbuch_password=""))

    assert 'KLASSENBUCH_PASSWORD="kept-secret"' in env_path.read_text(encoding="utf-8")


def test_openai_key_file_check_returns_only_status():
    key_path = _env_path().with_name("api.key")
    key_path.write_text("sk-secret-value", encoding="utf-8")

    result = setup_service.validate_openai_key_file(str(key_path))

    assert result.exists is True
    assert result.readable is True
    assert result.non_empty is True
    assert "sk-secret-value" not in result.model_dump_json()


def test_setup_run_does_not_start_console_process():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.post("/api/setup/run")

    assert response.status_code == 200
    assert response.json()["data"]["setup_url"] == "/setup"
    assert "Weboberflaeche" in response.json()["message"]


def test_openai_key_file_endpoint_wraps_status_without_secret():
    key_path = _env_path().with_name("api-endpoint.key")
    key_path.write_text("sk-endpoint-secret", encoding="utf-8")
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.post("/api/setup/validate-openai-key-file", json={"openai_api_key_file": str(key_path)})
    body = response.json()

    assert response.status_code == 200
    assert body["ok"] is True
    assert body["data"]["exists"] is True
    assert body["data"]["readable"] is True
    assert body["data"]["non_empty"] is True
    assert "sk-endpoint-secret" not in str(body)
