from __future__ import annotations

from fastapi import APIRouter

from app.services.review_service import review_service

router = APIRouter(prefix="/api/review", tags=["review"])


@router.post("/confirm")
def confirm(data: dict):
    return review_service.confirm(data)
