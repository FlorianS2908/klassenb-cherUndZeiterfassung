from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.config import get_settings, resolve_project_path


def history_folder() -> Path:
    folder = resolve_project_path(get_settings().analysis_history_folder)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def list_history() -> list[dict]:
    items: list[dict] = []
    for path in sorted(history_folder().glob("*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data.setdefault("id", path.stem)
            items.append(data)
        except json.JSONDecodeError:
            continue
    return items


def save_history(payload: dict) -> dict:
    item_id = payload.get("id") or uuid4().hex
    data = {
        **payload,
        "id": item_id,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    (history_folder() / f"{item_id}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return data


def reopen_history(item_id: str) -> dict:
    path = history_folder() / f"{item_id}.json"
    if not path.exists():
        raise FileNotFoundError("Analyse-Lauf wurde nicht gefunden.")
    return json.loads(path.read_text(encoding="utf-8"))


def delete_history(item_id: str) -> bool:
    path = history_folder() / f"{item_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False
