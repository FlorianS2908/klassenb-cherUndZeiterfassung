from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import ApiMessage
from app.services.analysis_history_service import delete_history, list_history, reopen_history, save_history

router = APIRouter(prefix="/api/analysis-history", tags=["analysis-history"])


@router.get("")
def get_history():
    return {"items": list_history()}


@router.post("/save")
def save(payload: dict):
    return ApiMessage(ok=True, message="Analyse-Lauf gespeichert.", data=save_history(payload))


@router.post("/reopen")
def reopen(payload: dict):
    try:
        return reopen_history(str(payload.get("id", "")))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{item_id}")
def delete(item_id: str):
    return ApiMessage(ok=delete_history(item_id), message="Analyse-Lauf geloescht.")
