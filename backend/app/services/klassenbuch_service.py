from __future__ import annotations


def open_klassenbuecher_stub() -> list[dict[str, str]]:
    return [
        {"id": "dry-run-1", "title": "Offenes Klassenbuch", "date": "Zieltag", "status": "Offen"},
    ]


def ensure_open_status(entry: dict[str, str]) -> bool:
    return entry.get("status", "").lower() == "offen"
