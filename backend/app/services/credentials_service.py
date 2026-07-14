from __future__ import annotations

from app.config import get_settings
from app.services.secret_store import get_secret

KLASSENBUCH_SERVICE = "klassenbuch.gfn.de"
TIMEBUTLER_SERVICE = "timebutler"


def get_klassenbuch_credentials() -> tuple[str, str]:
    settings = get_settings()
    username = settings.klassenbuch_username.strip()
    password = ""
    if settings.klassenbuch_password_source == "keyring":
        password = get_secret(KLASSENBUCH_SERVICE, username) or ""
    password = password or settings.klassenbuch_password
    if not username or not password:
        raise RuntimeError("Klassenbuch-Zugangsdaten fehlen. Bitte Setup oeffnen und Zugangsdaten speichern.")
    return username, password
