from __future__ import annotations

import pytest

from app import config
from app.config import Settings
from app.services import credentials_service, secret_store


class FakeKeyring:
    def __init__(self):
        self.values: dict[tuple[str, str], str] = {}

    def set_password(self, service: str, username: str, password: str) -> None:
        self.values[(service, username)] = password

    def get_password(self, service: str, username: str) -> str | None:
        return self.values.get((service, username))

    def delete_password(self, service: str, username: str) -> None:
        self.values.pop((service, username), None)


def test_secret_store_roundtrip_with_keyring(monkeypatch):
    fake = FakeKeyring()
    monkeypatch.setattr(secret_store, "_keyring", lambda: fake)

    secret_store.set_secret("klassenbuch.gfn.de", "trainer@example.com", "secret-one")

    assert secret_store.get_secret("klassenbuch.gfn.de", "trainer@example.com") == "secret-one"
    assert secret_store.has_secret("klassenbuch.gfn.de", "trainer@example.com") is True
    secret_store.delete_secret("klassenbuch.gfn.de", "trainer@example.com")
    assert secret_store.has_secret("klassenbuch.gfn.de", "trainer@example.com") is False


def test_credentials_service_reads_klassenbuch_password_from_keyring(monkeypatch):
    monkeypatch.setattr(config, "get_settings", lambda: Settings(klassenbuch_username="trainer@example.com", klassenbuch_password_source="keyring"))
    monkeypatch.setattr(credentials_service, "get_settings", config.get_settings)
    monkeypatch.setattr(credentials_service, "get_secret", lambda service, username: "secret-one")

    assert credentials_service.get_klassenbuch_credentials() == ("trainer@example.com", "secret-one")


def test_credentials_service_falls_back_to_env_password(monkeypatch):
    monkeypatch.setattr(
        credentials_service,
        "get_settings",
        lambda: Settings(klassenbuch_username="trainer@example.com", klassenbuch_password="env-secret", klassenbuch_password_source="keyring"),
    )
    monkeypatch.setattr(credentials_service, "get_secret", lambda service, username: None)

    assert credentials_service.get_klassenbuch_credentials() == ("trainer@example.com", "env-secret")


def test_credentials_service_raises_without_password(monkeypatch):
    monkeypatch.setattr(credentials_service, "get_settings", lambda: Settings(klassenbuch_username="trainer@example.com"))

    with pytest.raises(RuntimeError, match="Klassenbuch-Zugangsdaten fehlen"):
        credentials_service.get_klassenbuch_credentials()


def test_public_dict_never_returns_password(monkeypatch):
    monkeypatch.setattr(secret_store, "has_secret", lambda service, username: True)
    settings = Settings(klassenbuch_username="trainer@example.com", klassenbuch_password="env-secret", klassenbuch_password_source="env")

    public = settings.public_dict()

    assert public["credentials"]["klassenbuch_password_present"] is True
    assert public["credentials"]["klassenbuch_password_source"] == "env"
    assert "env-secret" not in str(public)
