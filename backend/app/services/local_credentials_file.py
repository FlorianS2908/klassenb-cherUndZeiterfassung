from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import resolve_project_path

KLASSENBUCH_CREDENTIALS_FILE = "runtime/secrets/klassenbuch.credentials.json"


def _credentials_file_path() -> Path:
    return resolve_project_path(KLASSENBUCH_CREDENTIALS_FILE)


def read_klassenbuch_credentials_file() -> dict[str, str] | None:
    path = _credentials_file_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    source = str(data.get("source", "local_file") or "local_file")
    if not username or not password:
        return None
    return {"username": username, "password": password, "source": source}


def write_klassenbuch_credentials_file(username: str, password: str) -> dict[str, Any]:
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
    path.write_text(
        json.dumps(
            {
                "username": username,
                "password": password,
                "source": "local_file",
                "created_at": existing_created_at or now,
                "updated_at": now,
            },
            indent=2,
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    return get_klassenbuch_credentials_file_status()


def delete_klassenbuch_credentials_file() -> None:
    try:
        _credentials_file_path().unlink(missing_ok=True)
    except OSError:
        return


def get_klassenbuch_credentials_file_status() -> dict[str, Any]:
    path = _credentials_file_path()
    credentials = read_klassenbuch_credentials_file()
    return {
        "exists": path.exists(),
        "username_present": bool(credentials and credentials.get("username")),
        "password_present": bool(credentials and credentials.get("password")),
        "source": "local_file" if credentials else "missing",
        "path": KLASSENBUCH_CREDENTIALS_FILE,
    }
