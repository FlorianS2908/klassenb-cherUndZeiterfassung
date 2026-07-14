from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import get_settings, resolve_project_path
from app.services.secret_store import get_secret

KLASSENBUCH_SERVICE = "klassenbuch.gfn.de"
TIMEBUTLER_SERVICE = "timebutler"
KLASSENBUCH_CREDENTIALS_FILE = "runtime/secrets/klassenbuch.credentials.json"


def _credentials_file_path() -> Path:
    return resolve_project_path(KLASSENBUCH_CREDENTIALS_FILE)


def _read_local_credentials() -> tuple[str, str] | None:
    path = _credentials_file_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    if username and password:
        return username, password
    return None


def write_klassenbuch_local_credentials(username: str, password: str) -> dict[str, Any]:
    username = username.strip()
    if not username or not password:
        raise ValueError("Benutzername und Passwort sind erforderlich.")
    path = _credentials_file_path()
    existing_created_at = ""
    if path.exists():
        try:
            existing_created_at = str(json.loads(path.read_text(encoding="utf-8")).get("created_at", ""))
        except (OSError, json.JSONDecodeError):
            existing_created_at = ""
    now = datetime.now().isoformat(timespec="seconds")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "username": username,
        "password": password,
        "source": "local_file",
        "created_at": existing_created_at or now,
        "updated_at": now,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return get_klassenbuch_credential_status()


def get_klassenbuch_credential_status() -> dict[str, Any]:
    settings = get_settings()
    path = _credentials_file_path()
    local = _read_local_credentials()
    if local:
        username, password = local
        return {
            "username_present": bool(username),
            "password_present": bool(password),
            "source": "local_file",
            "credentials_file_exists": True,
            "credentials_file_path": KLASSENBUCH_CREDENTIALS_FILE,
        }
    keyring_password = ""
    if settings.klassenbuch_username.strip() and settings.klassenbuch_password_source == "keyring":
        keyring_password = get_secret(KLASSENBUCH_SERVICE, settings.klassenbuch_username.strip()) or ""
    if settings.klassenbuch_username.strip() and keyring_password:
        source = "keyring"
    elif settings.klassenbuch_username.strip() and settings.klassenbuch_password:
        source = "env"
    else:
        source = "missing"
    return {
        "username_present": bool(settings.klassenbuch_username.strip()),
        "password_present": bool(keyring_password or settings.klassenbuch_password),
        "source": source,
        "credentials_file_exists": path.exists(),
        "credentials_file_path": KLASSENBUCH_CREDENTIALS_FILE,
    }


def get_klassenbuch_credentials() -> tuple[str, str]:
    settings = get_settings()
    local = _read_local_credentials()
    if local:
        return local
    username = settings.klassenbuch_username.strip()
    password = ""
    if settings.klassenbuch_password_source == "keyring":
        password = get_secret(KLASSENBUCH_SERVICE, username) or ""
    password = password or settings.klassenbuch_password
    if not username or not password:
        raise RuntimeError("Klassenbuch-Zugangsdaten fehlen. Bitte Setup oeffnen oder lokale Credential-Datei anlegen.")
    return username, password
