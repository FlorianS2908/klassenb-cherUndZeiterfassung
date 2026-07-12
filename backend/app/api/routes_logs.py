from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings, resolve_project_path

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
def logs():
    folder = resolve_project_path(get_settings().log_folder)
    folder.mkdir(parents=True, exist_ok=True)
    latest = sorted(folder.glob("*.log"), reverse=True)[:1]
    if not latest:
        return {"content": ""}
    return {"content": latest[0].read_text(encoding="utf-8", errors="ignore")[-12000:]}
