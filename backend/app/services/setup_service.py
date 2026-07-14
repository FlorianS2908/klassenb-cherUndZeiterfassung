from __future__ import annotations

from pathlib import Path

from dotenv import dotenv_values

from app.config import ENV_PATH, Settings, get_settings
from app.models.schemas import OpenAiKeyFileCheck, SetupCheckResult, SetupDefaults, SetupPayload


def _existing_env() -> dict[str, str]:
    if not ENV_PATH.exists():
        return {}
    values = dotenv_values(ENV_PATH)
    return {key: str(value or "") for key, value in values.items()}


def _bool(value: bool) -> str:
    return "true" if value else "false"


def _quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _payload_to_env(payload: SetupPayload, existing: dict[str, str]) -> dict[str, str]:
    use_separate = payload.use_separate_timebutler_credentials
    klassenbuch_password = payload.klassenbuch_password or existing.get("KLASSENBUCH_PASSWORD", "")
    timebutler_password = payload.timebutler_password or existing.get("TIMEBUTLER_PASSWORD", "")
    openai_api_key = payload.openai_api_key or existing.get("OPENAI_API_KEY", "")
    timebutler_username = payload.timebutler_username if use_separate else ""
    if not use_separate:
        timebutler_password = ""

    return {
        "KLASSENBUCH_URL": payload.klassenbuch_url,
        "TIMEBUTLER_URL": payload.timebutler_url,
        "KLASSENBUCH_USERNAME": payload.klassenbuch_username,
        "KLASSENBUCH_PASSWORD": klassenbuch_password,
        "TIMEBUTLER_USERNAME": timebutler_username,
        "TIMEBUTLER_PASSWORD": timebutler_password,
        "OPENAI_API_KEY_FILE": payload.openai_api_key_file,
        "OPENAI_API_KEY": openai_api_key,
        "OPENAI_MODEL": payload.openai_model,
        "OPENAI_MAX_INPUT_CHARS": str(payload.openai_max_input_chars),
        "OPENAI_TIMEOUT_SECONDS": str(payload.openai_timeout_seconds),
        "OPENAI_RETRY_COUNT": str(payload.openai_retry_count),
        "OPENAI_TEMPERATURE": str(payload.openai_temperature),
        "AUTO_SUBMIT": _bool(payload.auto_submit),
        "DEFAULT_SIGNATURE": payload.default_signature,
        "UPLOAD_FOLDER": payload.upload_folder,
        "SCREENSHOT_FOLDER": payload.screenshot_folder,
        "LOG_FOLDER": payload.log_folder,
        "ERROR_REPORT_FOLDER": payload.error_report_folder,
        "ANALYSIS_HISTORY_FOLDER": payload.analysis_history_folder,
        "REFERENCE_SCREENSHOT_DIR": payload.reference_screenshot_dir,
        "TIMEBUTLER_PROJECT": payload.timebutler_project,
        "TIMEBUTLER_CATEGORY": payload.timebutler_category,
        "TIMEBUTLER_START": payload.timebutler_start,
        "TIMEBUTLER_END": payload.timebutler_end,
        "TIMEBUTLER_PAUSE": payload.timebutler_pause,
        "TIMEBUTLER_REMARK": payload.timebutler_remark,
        "FEDERAL_STATE": payload.federal_state,
        "BLOCKED_DATES": payload.blocked_dates,
        "VACATION_DATES": payload.vacation_dates,
        "SICK_DATES": payload.sick_dates,
        "DESKTOP_NOTIFICATIONS": _bool(payload.desktop_notifications),
        "AUTO_OPEN_BROWSER": _bool(payload.auto_open_browser),
        "AUTO_DRY_RUN_ON_START": _bool(payload.auto_dry_run_on_start),
        "GITHUB_REMOTE_URL": payload.github_remote_url,
        "GIT_DEFAULT_BRANCH": payload.git_default_branch,
    }


def _missing_from_env(values: dict[str, str]) -> list[str]:
    missing = [
        key
        for key in ["KLASSENBUCH_URL", "TIMEBUTLER_URL", "KLASSENBUCH_USERNAME", "KLASSENBUCH_PASSWORD"]
        if not values.get(key, "").strip()
    ]
    if values.get("TIMEBUTLER_USERNAME", "").strip() and not values.get("TIMEBUTLER_PASSWORD", "").strip():
        missing.append("TIMEBUTLER_PASSWORD")
    if values.get("TIMEBUTLER_PASSWORD", "").strip() and not values.get("TIMEBUTLER_USERNAME", "").strip():
        missing.append("TIMEBUTLER_USERNAME")
    return missing


def default_setup_values() -> SetupDefaults:
    settings = get_settings()
    return SetupDefaults(
        klassenbuch_url=settings.klassenbuch_url,
        timebutler_url=settings.timebutler_url,
        klassenbuch_username=settings.klassenbuch_username,
        timebutler_username=settings.timebutler_username,
        use_separate_timebutler_credentials=bool(settings.timebutler_username or settings.timebutler_password),
        openai_api_key_file=settings.openai_api_key_file,
        openai_model=settings.openai_model,
        openai_max_input_chars=settings.openai_max_input_chars,
        openai_timeout_seconds=settings.openai_timeout_seconds,
        openai_retry_count=settings.openai_retry_count,
        openai_temperature=settings.openai_temperature,
        auto_submit=settings.auto_submit and not settings.dry_run_forced,
        default_signature=settings.default_signature,
        upload_folder=settings.upload_folder,
        screenshot_folder=settings.screenshot_folder,
        log_folder=settings.log_folder,
        error_report_folder=settings.error_report_folder,
        analysis_history_folder=settings.analysis_history_folder,
        reference_screenshot_dir=settings.reference_screenshot_dir,
        timebutler_project=settings.timebutler_project,
        timebutler_category=settings.timebutler_category,
        timebutler_start=settings.timebutler_start,
        timebutler_end=settings.timebutler_end,
        timebutler_pause=settings.timebutler_pause,
        timebutler_remark=settings.timebutler_remark,
        federal_state=settings.federal_state,
        blocked_dates=settings.blocked_dates,
        vacation_dates=settings.vacation_dates,
        sick_dates=settings.sick_dates,
        desktop_notifications=settings.desktop_notifications,
        auto_open_browser=settings.auto_open_browser,
        auto_dry_run_on_start=settings.auto_dry_run_on_start,
        github_remote_url=settings.github_remote_url,
        git_default_branch=settings.git_default_branch,
    )


def check_setup() -> SetupCheckResult:
    env_values = _existing_env()
    missing = _missing_from_env(env_values) if ENV_PATH.exists() else ["ENV_FILE"]
    messages = []
    if not ENV_PATH.exists():
        messages.append("Keine .env gefunden. Bitte Setup in der Weboberflaeche abschliessen.")
    elif missing:
        messages.append("Pflichtwerte fehlen: " + ", ".join(missing))
    else:
        messages.append("Setup vollstaendig.")
    return SetupCheckResult(
        env_exists=ENV_PATH.exists(),
        setup_required=bool(missing),
        missing=missing,
        messages=messages,
        config_public=get_settings().public_dict(),
    )


def validate_openai_key_file(path: str) -> OpenAiKeyFileCheck:
    if not path.strip():
        return OpenAiKeyFileCheck(exists=False, readable=False, has_content=False, message="Kein Pfad angegeben.")
    key_path = Path(path)
    if not key_path.exists():
        return OpenAiKeyFileCheck(exists=False, readable=False, has_content=False, message="Datei wurde nicht gefunden.")
    try:
        content = key_path.read_text(encoding="utf-8").strip()
    except OSError:
        return OpenAiKeyFileCheck(exists=True, readable=False, has_content=False, message="Datei ist nicht lesbar.")
    return OpenAiKeyFileCheck(
        exists=True,
        readable=True,
        has_content=bool(content),
        message="API-Key-Datei ist lesbar." if content else "Datei ist leer.",
    )


def validate_setup_payload(payload: SetupPayload, env_values: dict[str, str]) -> None:
    values = _payload_to_env(payload, env_values)
    missing = _missing_from_env(values)
    if missing:
        raise ValueError("Pflichtwerte fehlen: " + ", ".join(missing))


def save_setup(payload: SetupPayload) -> dict[str, object]:
    existing = _existing_env()
    validate_setup_payload(payload, existing)
    values = _payload_to_env(payload, existing)
    lines = [
        "# Lokale Konfiguration. Diese Datei enthaelt Zugangsdaten und wird nicht committet.",
        "# Erstellt durch die Weboberflaeche unter /setup.",
        "",
    ]
    for key, value in values.items():
        lines.append(f"{key}={_quote(value)}")
    tmp_path = ENV_PATH.with_suffix(".env.tmp")
    tmp_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp_path.replace(ENV_PATH)
    get_settings.cache_clear()
    return {
        "env_exists": True,
        "setup_required": False,
        "config_public": get_settings().public_dict(),
    }
