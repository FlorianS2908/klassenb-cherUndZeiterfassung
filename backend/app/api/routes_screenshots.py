from __future__ import annotations

from fastapi import APIRouter

from app.services.screenshot_service import list_screenshots

router = APIRouter(prefix="/api/screenshots", tags=["screenshots"])


@router.get("")
def screenshots():
    return {"items": list_screenshots()}
