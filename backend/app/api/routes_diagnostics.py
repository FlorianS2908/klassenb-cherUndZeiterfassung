from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.services.diagnostic_export_service import export_klassenbuch_diagnostic
from app.services.diagnostics_service import latest_summary, list_diagnostic_runs, read_steps, read_summary, resolve_diagnostic_file

router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])


@router.get("/klassenbuch/runs")
async def klassenbuch_runs():
    return {"items": list_diagnostic_runs("klassenbuch")}


@router.get("/klassenbuch/latest")
async def klassenbuch_latest():
    return latest_summary("klassenbuch")


@router.get("/klassenbuch/latest/export-sanitized")
async def export_latest_klassenbuch_sanitized():
    try:
        return export_klassenbuch_diagnostic()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Noch keine Diagnose vorhanden. Bitte zuerst Klassenbuecher laden.") from exc


@router.post("/klassenbuch/{run_id}/export-sanitized")
async def export_klassenbuch_sanitized(run_id: str):
    try:
        return export_klassenbuch_diagnostic(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Diagnose-Lauf nicht gefunden.") from exc


@router.get("/klassenbuch/{run_id}")
async def klassenbuch_run(run_id: str):
    summary = read_summary("klassenbuch", run_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Diagnose-Lauf nicht gefunden.")
    return {"summary": summary, "steps": read_steps("klassenbuch", run_id)}


@router.get("/klassenbuch/{run_id}/file")
async def klassenbuch_file(run_id: str, name: str = Query(..., min_length=1)):
    try:
        path = resolve_diagnostic_file("klassenbuch", run_id, name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Diagnose-Datei nicht gefunden.") from exc
    return FileResponse(path)
