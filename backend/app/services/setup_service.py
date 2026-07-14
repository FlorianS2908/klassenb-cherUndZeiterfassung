from __future__ import annotations

from pathlib import Path

from dotenv import dotenv_values

from app.config import ENV_PATH, ROOT_DIR, get_settings, resolve_project_path
from app.models.schemas import OpenAiKeyFileCheck, SetupCheckResult, SetupDefaults, SetupPayload
from app.services.credentials_service import KLASSENBUCH_SERVICE, TIMEBUTLER_SERVICE, get_klassenbuch_credential_status
from app.services.secret_store import SecretStoreUnavailable, has_secret, set_secret

GITIGNORE_REQUIRED_LINES = [
    ".env",
    "*.env",
    "api_key_klassenbuch.txt",
    "api_key*.txt",
    "*.key",
    "*.secret",
    "*.credentials.json",
    "*.secret.json",
    "runtime/*",
    "runtime/secrets/*",
    "!runtime/secrets/klassenbuch.credentials.example.json",
    "secrets/",
    "credentials/",
    "uploads/",
    "screenshots/",
    "logs/",
    "diagnostics/",
    "error_reports/",
    "analysis_history/",
    "node_modules/",
    ".venv/",
    "dist/",
    "__pycache__/",
]


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
        "KLASSENBUCH_PASSWORD_SOURCE": existing.get("KLASSENBUCH_PASSWORD_SOURCE", "env"),
        "TIMEBUTLER_USERNAME": timebutler_username,
        "TIMEBUTLER_PASSWORD": timebutler_password,
        "TIMEBUTLER_PASSWORD_SOURCE": existing.get("TIMEBUTLER_PASSWORD_SOURCE", "env"),
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
        "BROWSER_HEADLESS": _bool(payload.browser_headless),
        "BROWSER_SLOW_MO_MS": str(payload.browser_slow_mo_ms),
        "BROWSER_KEEP_OPEN_ON_ERROR": _bool(payload.browser_keep_open_on_error),
        "GITHUB_REMOTE_URL": payload.github_remote_url,
        "GIT_DEFAULT_BRANCH": payload.git_default_branch,
    }


def _missing_from_env(values: dict[str, str]) -> list[str]:
    missing = [key for key in ["KLASSENBUCH_URL", "TIMEBUTLER_URL", "KLASSENBUCH_USERNAME"] if not values.get(key, "").strip()]
    if not _has_password(values, "KLASSENBUCH", KLASSENBUCH_SERVICE):
        missing.append("KLASSENBUCH_PASSWORD")
    if values.get("TIMEBUTLER_USERNAME", "").strip() and not values.get("TIMEBUTLER_PASSWORD", "").strip():
        missing.append("TIMEBUTLER_PASSWORD")
    if values.get("TIMEBUTLER_PASSWORD", "").strip() and not values.get("TIMEBUTLER_USERNAME", "").strip():
        missing.append("TIMEBUTLER_USERNAME")
    return missing


def _has_password(values: dict[str, str], prefix: str, service: str) -> bool:
    if prefix == "KLASSENBUCH":
        try:
            if get_klassenbuch_credential_status()["source"] == "local_file":
                return True
        except Exception:
            pass
    username = values.get(f"{prefix}_USERNAME", "").strip()
    if values.get(f"{prefix}_PASSWORD", "").strip():
        return True
    if values.get(f"{prefix}_PASSWORD_SOURCE", "env") == "keyring" and username:
        return has_secret(service, username)
    return False


def _store_password(
    *,
    values: dict[str, str],
    prefix: str,
    service: str,
    username: str,
    submitted_password: str,
    existing_password: str,
    warnings: list[str],
) -> None:
    if submitted_password:
        if not username.strip():
            values[f"{prefix}_PASSWORD"] = submitted_password
            values[f"{prefix}_PASSWORD_SOURCE"] = "env"
            return
        try:
            set_secret(service, username, submitted_password)
            values[f"{prefix}_PASSWORD"] = ""
            values[f"{prefix}_PASSWORD_SOURCE"] = "keyring"
            return
        except SecretStoreUnavailable:
            values[f"{prefix}_PASSWORD"] = submitted_password
            values[f"{prefix}_PASSWORD_SOURCE"] = "env"
            warnings.append("Windows Credential Manager nicht verfuegbar. Passwort wird lokal in .env gespeichert.")
            return
    if username.strip() and has_secret(service, username):
        values[f"{prefix}_PASSWORD"] = ""
        values[f"{prefix}_PASSWORD_SOURCE"] = "keyring"
        return
    values[f"{prefix}_PASSWORD"] = existing_password
    values[f"{prefix}_PASSWORD_SOURCE"] = "env" if existing_password else values.get(f"{prefix}_PASSWORD_SOURCE", "env")


def _ensure_gitignore() -> None:
    gitignore = ROOT_DIR / ".gitignore"
    existing = set()
    if gitignore.exists():
        existing = set(gitignore.read_text(encoding="utf-8").splitlines())
    missing = [line for line in GITIGNORE_REQUIRED_LINES if line not in existing]
    if missing:
        with gitignore.open("a", encoding="utf-8") as handle:
            if existing:
                handle.write("\n")
            handle.write("\n".join(missing) + "\n")


def _ensure_runtime_folders(values: dict[str, str]) -> None:
    for key in ["UPLOAD_FOLDER", "SCREENSHOT_FOLDER", "LOG_FOLDER", "ERROR_REPORT_FOLDER", "ANALYSIS_HISTORY_FOLDER"]:
        folder = values.get(key, "").strip()
        if folder:
            resolve_project_path(folder).mkdir(parents=True, exist_ok=True)


def default_setup_values() -> SetupDefaults:
    settings = get_settings()
    return SetupDefaults(
        klassenbuch_url=settings.klassenbuch_url,
        timebutler_url=settings.timebutler_url,
        klassenbuch_username=settings.klassenbuch_username,
        klassenbuch_password_present=bool(settings.klassenbuch_password) or has_secret(KLASSENBUCH_SERVICE, settings.klassenbuch_username),
        klassenbuch_password_source=settings.klassenbuch_password_source if (settings.klassenbuch_password or has_secret(KLASSENBUCH_SERVICE, settings.klassenbuch_username)) else "missing",
        timebutler_username=settings.timebutler_username,
        timebutler_password_present=bool(settings.timebutler_password) or has_secret(TIMEBUTLER_SERVICE, settings.effective_timebutler_username),
        timebutler_password_source=settings.timebutler_password_source if (settings.timebutler_password or has_secret(TIMEBUTLER_SERVICE, settings.effective_timebutler_username)) else "missing",
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
        browser_headless=settings.browser_headless,
        browser_slow_mo_ms=settings.browser_slow_mo_ms,
        browser_keep_open_on_error=settings.browser_keep_open_on_error,
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
    config_public = get_settings().public_dict()
    credential_status = get_klassenbuch_credential_status()
    config_public["credentials"] = {
        **dict(config_public.get("credentials", {})),
        "klassenbuch_username_present": credential_status["username_present"],
        "klassenbuch_password_present": credential_status["password_present"],
        "klassenbuch_password_source": credential_status["source"],
        "klassenbuch_credentials_file_exists": credential_status["credentials_file_exists"],
        "klassenbuch_credentials_file_path": credential_status["credentials_file_path"],
    }
    return SetupCheckResult(
        env_exists=ENV_PATH.exists(),
        setup_required=bool(missing),
        missing=missing,
        messages=messages,
        config_public=config_public,
    )


def validate_openai_key_file(path: str) -> OpenAiKeyFileCheck:
    if not path.strip():
        return OpenAiKeyFileCheck(exists=False, readable=False, non_empty=False, message="Kein Pfad angegeben.")
    key_path = Path(path)
    if not key_path.exists():
        return OpenAiKeyFileCheck(exists=False, readable=False, non_empty=False, message="Datei wurde nicht gefunden.")
    try:
        content = key_path.read_text(encoding="utf-8").strip()
    except OSError:
        return OpenAiKeyFileCheck(exists=True, readable=False, non_empty=False, message="Datei ist nicht lesbar.")
    return OpenAiKeyFileCheck(
        exists=True,
        readable=True,
        non_empty=bool(content),
        message="API-Key-Datei ist lesbar." if content else "Datei ist leer.",
    )


def validate_setup_payload(payload: SetupPayload, env_values: dict[str, str]) -> None:
    values = _payload_to_env(payload, env_values)
    missing = _missing_from_env(values)
    if missing:
        raise ValueError("Pflichtwerte fehlen: " + ", ".join(missing))


def save_setup(payload: SetupPayload) -> dict[str, object]:
    existing = _existing_env()
    values = _payload_to_env(payload, existing)
    warnings: list[str] = []
    _store_password(
        values=values,
        prefix="KLASSENBUCH",
        service=KLASSENBUCH_SERVICE,
        username=payload.klassenbuch_username,
        submitted_password=payload.klassenbuch_password,
        existing_password=existing.get("KLASSENBUCH_PASSWORD", ""),
        warnings=warnings,
    )
    if payload.use_separate_timebutler_credentials:
        _store_password(
            values=values,
            prefix="TIMEBUTLER",
            service=TIMEBUTLER_SERVICE,
            username=payload.timebutler_username,
            submitted_password=payload.timebutler_password,
            existing_password=existing.get("TIMEBUTLER_PASSWORD", ""),
            warnings=warnings,
        )
    else:
        values["TIMEBUTLER_PASSWORD"] = ""
        values["TIMEBUTLER_PASSWORD_SOURCE"] = "env"
    missing = _missing_from_env(values)
    if missing:
        if "KLASSENBUCH_PASSWORD" in missing:
            raise ValueError("Kein gespeichertes Klassenbuch-Passwort gefunden.")
        raise ValueError("Pflichtwerte fehlen: " + ", ".join(missing))
    _ensure_gitignore()
    _ensure_runtime_folders(values)
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
        "warnings": warnings,
    }
