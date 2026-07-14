from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.local_credentials_file import (
    KLASSENBUCH_CREDENTIALS_FILE,
    get_klassenbuch_credentials_file_status,
    read_klassenbuch_credentials_file,
    write_klassenbuch_credentials_file,
)
from app.services.secret_store import get_secret

KLASSENBUCH_SERVICE = "klassenbuch.gfn.de"
TIMEBUTLER_SERVICE = "timebutler"


def write_klassenbuch_local_credentials(username: str, password: str) -> dict[str, Any]:
    write_klassenbuch_credentials_file(username, password)
    return get_klassenbuch_credential_status()


def get_klassenbuch_credential_status() -> dict[str, Any]:
    settings = get_settings()
    file_status = get_klassenbuch_credentials_file_status()
    local = read_klassenbuch_credentials_file()
    if local:
        return {
            "username_present": True,
            "password_present": True,
            "source": "local_file",
            "local_file_exists": True,
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
        "local_file_exists": file_status["exists"],
        "credentials_file_exists": file_status["exists"],
        "credentials_file_path": KLASSENBUCH_CREDENTIALS_FILE,
    }


def get_klassenbuch_credentials() -> tuple[str, str]:
    settings = get_settings()
    local = read_klassenbuch_credentials_file()
    if local:
        return local["username"], local["password"]
    username = settings.klassenbuch_username.strip()
    password = ""
    if settings.klassenbuch_password_source == "keyring":
        password = get_secret(KLASSENBUCH_SERVICE, username) or ""
    password = password or settings.klassenbuch_password
    if not username or not password:
        raise RuntimeError("Klassenbuch-Zugangsdaten fehlen. Bitte Setup oeffnen und Zugangsdaten lokal speichern.")
    return username, password
