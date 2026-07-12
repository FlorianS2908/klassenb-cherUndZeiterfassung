from __future__ import annotations


def notify(title: str, message: str, enabled: bool = True) -> None:
    if not enabled:
        return
    try:
        from plyer import notification

        notification.notify(title=title, message=message, app_name="Klassenbuch-Tool", timeout=8)
    except Exception:
        return
