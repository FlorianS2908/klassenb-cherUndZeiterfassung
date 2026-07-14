from __future__ import annotations

from app.browser.automation_klassenbuch import load_open_klassenbuecher


def ensure_open_status(entry: dict[str, str]) -> bool:
    return entry.get("status", "").lower() == "offen"
