from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.signature_profile_service import delete_signature_profile, get_signature_profile_status, read_signature_profile, write_signature_profile

router = APIRouter(prefix="/api/signature", tags=["signature"])


@router.get("/status")
async def status():
    return {"ok": True, "data": get_signature_profile_status()}


@router.post("/save")
async def save(payload: dict):
    try:
        status_data = write_signature_profile(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "message": "Signatur wurde lokal gespeichert.", "data": status_data}


@router.post("/delete")
async def delete():
    delete_signature_profile()
    return {"ok": True, "message": "Lokale Signatur wurde geloescht.", "data": get_signature_profile_status()}


@router.get("/preview")
async def preview():
    profile = read_signature_profile()
    if not profile:
        return {"ok": False, "message": "Keine lokale Signatur gespeichert.", "data": {"preview_png_data_url": ""}}
    return {"ok": True, "message": "Lokale Signaturvorschau geladen.", "data": {"preview_png_data_url": profile.get("preview_png_data_url", "")}}
