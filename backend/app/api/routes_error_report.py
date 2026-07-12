from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import ApiMessage
from app.services.error_report_service import create_error_report
from app.services.status_service import status_service

router = APIRouter(prefix="/api/error-report", tags=["error-report"])


@router.post("")
def error_report():
    path = create_error_report(status_service.status.run_id, status_service.status.model_dump(mode="json"))
    return ApiMessage(ok=True, message="Fehlerbericht erstellt.", data={"path": str(path)})
