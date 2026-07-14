from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"


class Settings(BaseModel):
    klassenbuch_url: str = "https://klassenbuch.gfn.de/login"
    timebutler_url: str = "https://app.timebutler.com/do?ha=login&ac=2"
    klassenbuch_username: str = ""
    klassenbuch_password: str = ""
    klassenbuch_password_source: str = "env"
    timebutler_username: str = ""
    timebutler_password: str = ""
    timebutler_password_source: str = "env"
    openai_api_key_file: str = r"C:\Users\Florian.Schaffer\OneDrive - Amadeus Fire AG\Desktop\KlassenbuchTimebutler\api_key_klassenbuch.txt"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_max_input_chars: int = 30000
    openai_timeout_seconds: int = 60
    openai_retry_count: int = 2
    openai_temperature: float = 0.2
    auto_submit: bool = False
    default_signature: str = "Schaffer"
    upload_folder: str = "./uploads"
    screenshot_folder: str = "./screenshots"
    log_folder: str = "./logs"
    error_report_folder: str = "./error_reports"
    analysis_history_folder: str = "./analysis_history"
    reference_screenshot_dir: str = r"C:\Users\Florian.Schaffer\OneDrive - Amadeus Fire AG\Desktop\Private\Klassenbuecher"
    timebutler_project: str = "FbW"
    timebutler_category: str = "Training/Coaching"
    timebutler_start: str = "08:30"
    timebutler_end: str = "16:30"
    timebutler_pause: str = "45m"
    timebutler_remark: str = "Training/Coaching im Rahmen der FbW-Unterrichtsdurchfuehrung"
    federal_state: str = "BW"
    blocked_dates: str = ""
    vacation_dates: str = ""
    sick_dates: str = ""
    desktop_notifications: bool = True
    auto_open_browser: bool = True
    auto_dry_run_on_start: bool = False
    browser_headless: bool = True
    browser_slow_mo_ms: int = 0
    browser_keep_open_on_error: bool = False
    github_remote_url: str = "https://github.com/FlorianS2908/klassenb-cherUndZeiterfassung.git"
    git_default_branch: str = "main"
    dry_run_forced: bool = Field(default_factory=lambda: os.getenv("FORCE_DRY_RUN", "").lower() == "true")

    @property
    def effective_timebutler_username(self) -> str:
        return self.timebutler_username or self.klassenbuch_username

    @property
    def effective_timebutler_password(self) -> str:
        return self.timebutler_password or self.klassenbuch_password

    def public_dict(self) -> dict[str, object]:
        klassenbuch_secret_present = False
        timebutler_secret_present = False
        try:
            from app.services.secret_store import has_secret

            klassenbuch_secret_present = has_secret("klassenbuch.gfn.de", self.klassenbuch_username)
            timebutler_secret_present = has_secret("timebutler", self.effective_timebutler_username)
        except Exception:
            klassenbuch_secret_present = False
            timebutler_secret_present = False
        klassenbuch_password_present = bool(self.klassenbuch_password or klassenbuch_secret_present)
        timebutler_password_present = bool(self.effective_timebutler_password or timebutler_secret_present)
        return {
            "klassenbuch_url": self.klassenbuch_url,
            "timebutler_url": self.timebutler_url,
            "auto_submit": self.auto_submit and not self.dry_run_forced,
            "default_signature": self.default_signature,
            "folders": {
                "uploads": self.upload_folder,
                "screenshots": self.screenshot_folder,
                "logs": self.log_folder,
                "error_reports": self.error_report_folder,
                "analysis_history": self.analysis_history_folder,
                "reference_screenshots": self.reference_screenshot_dir,
            },
            "timebutler": {
                "project": self.timebutler_project,
                "category": self.timebutler_category,
                "start": self.timebutler_start,
                "end": self.timebutler_end,
                "pause": self.timebutler_pause,
                "remark": self.timebutler_remark,
            },
            "federal_state": self.federal_state,
            "desktop_notifications": self.desktop_notifications,
            "auto_open_browser": self.auto_open_browser,
            "auto_dry_run_on_start": self.auto_dry_run_on_start,
            "browser": {
                "headless": self.browser_headless,
                "mode": "unsichtbar/headless" if self.browser_headless else "sichtbar/debug",
                "slow_mo_ms": self.browser_slow_mo_ms,
                "keep_open_on_error": self.browser_keep_open_on_error,
            },
            "credentials": {
                "klassenbuch_username_present": bool(self.klassenbuch_username),
                "klassenbuch_password_present": klassenbuch_password_present,
                "klassenbuch_password_source": self.klassenbuch_password_source if klassenbuch_password_present else "missing",
                "timebutler_username_present": bool(self.effective_timebutler_username),
                "timebutler_password_present": timebutler_password_present,
                "timebutler_password_source": self.timebutler_password_source if timebutler_password_present else "missing",
            },
            "dry_run_forced": self.dry_run_forced,
            "github": {
                "remote_url": self.github_remote_url,
                "default_branch": self.git_default_branch,
            },
            "openai": {
                "model": self.openai_model or "gpt-4o-mini",
                "max_input_chars": self.openai_max_input_chars,
                "timeout_seconds": self.openai_timeout_seconds,
                "retry_count": self.openai_retry_count,
                "temperature": self.openai_temperature,
            },
        }


@lru_cache
def get_settings() -> Settings:
    load_dotenv(ENV_PATH, override=True)
    def env(name: str, default: str = "") -> str:
        return os.getenv(name, default)

    def env_bool(name: str, default: bool = False) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        return raw.lower() in {"1", "true", "yes", "ja", "y", "j"}

    def env_int(name: str, default: int) -> int:
        try:
            return int(env(name, str(default)))
        except ValueError:
            return default

    def env_float(name: str, default: float) -> float:
        try:
            return float(env(name, str(default)))
        except ValueError:
            return default

    return Settings(
        klassenbuch_url=env("KLASSENBUCH_URL", "https://klassenbuch.gfn.de/login"),
        timebutler_url=env("TIMEBUTLER_URL", "https://app.timebutler.com/do?ha=login&ac=2"),
        klassenbuch_username=env("KLASSENBUCH_USERNAME"),
        klassenbuch_password=env("KLASSENBUCH_PASSWORD"),
        klassenbuch_password_source=env("KLASSENBUCH_PASSWORD_SOURCE", "env") or "env",
        timebutler_username=env("TIMEBUTLER_USERNAME"),
        timebutler_password=env("TIMEBUTLER_PASSWORD"),
        timebutler_password_source=env("TIMEBUTLER_PASSWORD_SOURCE", "env") or "env",
        openai_api_key_file=env("OPENAI_API_KEY_FILE", r"C:\Users\Florian.Schaffer\OneDrive - Amadeus Fire AG\Desktop\KlassenbuchTimebutler\api_key_klassenbuch.txt"),
        openai_api_key=env("OPENAI_API_KEY"),
        openai_model=env("OPENAI_MODEL", "gpt-4o-mini") or "gpt-4o-mini",
        openai_max_input_chars=env_int("OPENAI_MAX_INPUT_CHARS", 30000),
        openai_timeout_seconds=env_int("OPENAI_TIMEOUT_SECONDS", 60),
        openai_retry_count=env_int("OPENAI_RETRY_COUNT", 2),
        openai_temperature=env_float("OPENAI_TEMPERATURE", 0.2),
        auto_submit=env_bool("AUTO_SUBMIT", False),
        default_signature=env("DEFAULT_SIGNATURE", "Schaffer"),
        upload_folder=env("UPLOAD_FOLDER", "./uploads"),
        screenshot_folder=env("SCREENSHOT_FOLDER", "./screenshots"),
        log_folder=env("LOG_FOLDER", "./logs"),
        error_report_folder=env("ERROR_REPORT_FOLDER", "./error_reports"),
        analysis_history_folder=env("ANALYSIS_HISTORY_FOLDER", "./analysis_history"),
        reference_screenshot_dir=env("REFERENCE_SCREENSHOT_DIR", r"C:\Users\Florian.Schaffer\OneDrive - Amadeus Fire AG\Desktop\Private\Klassenbuecher"),
        timebutler_project=env("TIMEBUTLER_PROJECT", "FbW"),
        timebutler_category=env("TIMEBUTLER_CATEGORY", "Training/Coaching"),
        timebutler_start=env("TIMEBUTLER_START", "08:30"),
        timebutler_end=env("TIMEBUTLER_END", "16:30"),
        timebutler_pause=env("TIMEBUTLER_PAUSE", "45m"),
        timebutler_remark=env("TIMEBUTLER_REMARK", "Training/Coaching im Rahmen der FbW-Unterrichtsdurchfuehrung"),
        federal_state=env("FEDERAL_STATE", "BW"),
        blocked_dates=env("BLOCKED_DATES"),
        vacation_dates=env("VACATION_DATES"),
        sick_dates=env("SICK_DATES"),
        desktop_notifications=env_bool("DESKTOP_NOTIFICATIONS", True),
        auto_open_browser=env_bool("AUTO_OPEN_BROWSER", True),
        auto_dry_run_on_start=env_bool("AUTO_DRY_RUN_ON_START", False),
        browser_headless=env_bool("BROWSER_HEADLESS", True),
        browser_slow_mo_ms=env_int("BROWSER_SLOW_MO_MS", 0),
        browser_keep_open_on_error=env_bool("BROWSER_KEEP_OPEN_ON_ERROR", False),
        github_remote_url=env("GITHUB_REMOTE_URL", "https://github.com/FlorianS2908/klassenb-cherUndZeiterfassung.git"),
        git_default_branch=env("GIT_DEFAULT_BRANCH", "main"),
    )


def resolve_project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT_DIR / path


def ensure_runtime_ready(run_setup_if_missing: bool = False) -> tuple[bool, list[str]]:
    messages: list[str] = []
    if not ENV_PATH.exists():
        messages.append("Keine .env gefunden. Bitte Setup in der Weboberflaeche abschliessen.")
    settings = get_settings()
    missing = []
    for key, value in {
        "KLASSENBUCH_URL": settings.klassenbuch_url,
        "TIMEBUTLER_URL": settings.timebutler_url,
        "KLASSENBUCH_USERNAME": settings.klassenbuch_username,
    }.items():
        if not value:
            missing.append(key)
    has_klassenbuch_password = bool(settings.klassenbuch_password)
    if not has_klassenbuch_password and settings.klassenbuch_password_source == "keyring":
        try:
            from app.services.secret_store import has_secret

            has_klassenbuch_password = has_secret("klassenbuch.gfn.de", settings.klassenbuch_username)
        except Exception:
            has_klassenbuch_password = False
    if not has_klassenbuch_password:
        missing.append("KLASSENBUCH_PASSWORD")
    if missing:
        messages.append("Pflichtwerte fehlen: " + ", ".join(missing))
    for folder in [settings.upload_folder, settings.screenshot_folder, settings.log_folder, settings.error_report_folder, settings.analysis_history_folder]:
        resolve_project_path(folder).mkdir(parents=True, exist_ok=True)
    return not missing and ENV_PATH.exists(), messages
