from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def settings():
    return get_settings().public_dict()
