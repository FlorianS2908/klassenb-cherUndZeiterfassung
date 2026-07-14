from __future__ import annotations


class SecretStoreUnavailable(RuntimeError):
    pass


def _keyring():
    try:
        import keyring  # type: ignore
    except Exception as exc:
        raise SecretStoreUnavailable("Windows Credential Manager ist nicht verfuegbar.") from exc
    return keyring


def set_secret(service: str, username: str, password: str) -> None:
    if not service.strip() or not username.strip():
        raise ValueError("Service und Benutzername sind erforderlich.")
    try:
        _keyring().set_password(service, username, password)
    except Exception as exc:
        raise SecretStoreUnavailable("Windows Credential Manager konnte das Passwort nicht speichern.") from exc


def get_secret(service: str, username: str) -> str | None:
    if not service.strip() or not username.strip():
        return None
    try:
        return _keyring().get_password(service, username)
    except Exception:
        return None


def delete_secret(service: str, username: str) -> None:
    if not service.strip() or not username.strip():
        return
    try:
        _keyring().delete_password(service, username)
    except Exception:
        return


def has_secret(service: str, username: str) -> bool:
    return bool(get_secret(service, username))
