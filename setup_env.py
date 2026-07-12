from __future__ import annotations

import getpass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
GITIGNORE_PATH = ROOT / ".gitignore"


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def ask_secret(prompt: str) -> str:
    return getpass.getpass(f"{prompt}: ").strip()


def ensure_gitignore() -> None:
    existing = GITIGNORE_PATH.read_text(encoding="utf-8") if GITIGNORE_PATH.exists() else ""
    required = [".env", "__pycache__/", ".venv/", "node_modules/", "dist/", "logs/", "screenshots/", "error_reports/", "uploads/", "analysis_history/", "*.pyc"]
    additions = [item for item in required if item not in existing.splitlines()]
    if additions:
        GITIGNORE_PATH.write_text((existing.rstrip() + "\n" + "\n".join(additions) + "\n").lstrip(), encoding="utf-8")


def main() -> int:
    if ENV_PATH.exists():
        overwrite = ask("Eine .env existiert bereits. Ueberschreiben? (j/N)", "N").lower()
        if overwrite not in {"j", "ja", "y", "yes"}:
            print("Setup abgebrochen. Bestehende .env bleibt unveraendert.")
            return 0

    klassenbuch_url = ask("Klassenbuch-URL", "https://klassenbuch.gfn.de/login")
    timebutler_url = ask("Timebutler-URL", "https://app.timebutler.com/do?ha=login&ac=2")
    username = ask("Klassenbuch-Benutzername")
    password = ask_secret("Klassenbuch-Passwort")
    separate = ask("Separate Timebutler-Zugangsdaten verwenden? (j/N)", "N").lower()
    tb_username = ""
    tb_password = ""
    if separate in {"j", "ja", "y", "yes"}:
        tb_username = ask("Timebutler-Benutzername")
        tb_password = ask_secret("Timebutler-Passwort")
    openai_key = ask_secret("OpenAI API-Key optional (leer lassen moeglich)")
    federal_state = ask("Bundesland", "BW")
    blocked_dates = ask("BLOCKED_DATES kommagetrennt YYYY-MM-DD", "")
    vacation_dates = ask("VACATION_DATES kommagetrennt YYYY-MM-DD", "")
    sick_dates = ask("SICK_DATES kommagetrennt YYYY-MM-DD", "")

    content = f"""KLASSENBUCH_URL={klassenbuch_url}
TIMEBUTLER_URL={timebutler_url}

KLASSENBUCH_USERNAME={username}
KLASSENBUCH_PASSWORD={password}

TIMEBUTLER_USERNAME={tb_username}
TIMEBUTLER_PASSWORD={tb_password}

OPENAI_API_KEY={openai_key}

AUTO_SUBMIT=false
DEFAULT_SIGNATURE=Schaffer

UPLOAD_FOLDER=./uploads
SCREENSHOT_FOLDER=./screenshots
LOG_FOLDER=./logs
ERROR_REPORT_FOLDER=./error_reports
ANALYSIS_HISTORY_FOLDER=./analysis_history

REFERENCE_SCREENSHOT_DIR=C:\\Users\\Florian.Schaffer\\OneDrive - Amadeus Fire AG\\Desktop\\Private\\Klassenbuecher

TIMEBUTLER_PROJECT=FbW
TIMEBUTLER_CATEGORY=Training/Coaching
TIMEBUTLER_START=08:30
TIMEBUTLER_END=16:30
TIMEBUTLER_PAUSE=45m
TIMEBUTLER_REMARK=Training/Coaching im Rahmen der FbW-Unterrichtsdurchfuehrung

FEDERAL_STATE={federal_state}
BLOCKED_DATES={blocked_dates}
VACATION_DATES={vacation_dates}
SICK_DATES={sick_dates}

DESKTOP_NOTIFICATIONS=true
AUTO_OPEN_BROWSER=true
AUTO_DRY_RUN_ON_START=false

GITHUB_REMOTE_URL=https://github.com/FlorianS2908/klassenb-cherUndZeiterfassung.git
GIT_DEFAULT_BRANCH=main
"""
    ENV_PATH.write_text(content, encoding="utf-8")
    ensure_gitignore()
    print("Konfiguration erfolgreich gespeichert. Zugangsdaten wurden nicht ausgegeben.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
