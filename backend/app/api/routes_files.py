from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, UploadFile

from app.config import get_settings, resolve_project_path
from app.models.schemas import AnalysisResult, ApiMessage, FilePreview, UploadedFileInfo
from app.services.file_parser import SUPPORTED_EXTENSIONS, count_items, detect_file_type, extract_text
from app.services.range_service import parse_range_selection
from app.services.ue_planner import plan_nine_ue

router = APIRouter(prefix="/api/files", tags=["files"])


def upload_path(file_id: str, filename: str) -> Path:
    suffix = Path(filename).suffix.lower()
    return resolve_project_path(get_settings().upload_folder) / f"{file_id}{suffix}"


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return ApiMessage(ok=False, message="Dateityp wird nicht unterstuetzt.")
    file_id = uuid4().hex
    target = upload_path(file_id, file.filename or f"upload{suffix}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(await file.read())
    file_type, unit = detect_file_type(target)
    info = UploadedFileInfo(file_id=file_id, filename=file.filename or target.name, file_type=file_type, total_items=count_items(target), unit_label=unit, size_bytes=target.stat().st_size)
    return ApiMessage(ok=True, message="Datei hochgeladen.", data=info.model_dump())


@router.post("/metadata")
def metadata(file_id: str = Form(...), filename: str = Form(...)):
    path = upload_path(file_id, filename)
    file_type, unit = detect_file_type(path)
    return UploadedFileInfo(file_id=file_id, filename=filename, file_type=file_type, total_items=count_items(path), unit_label=unit, size_bytes=path.stat().st_size)


@router.post("/preview-range")
def preview_range(file_id: str = Form(...), filename: str = Form(...), selection: str = Form("")):
    path = upload_path(file_id, filename)
    total = count_items(path)
    parsed = parse_range_selection(selection, total)
    text = extract_text(path, parsed.selected)
    return FilePreview(file_id=file_id, range=parsed, text_preview=text[:4000], text_length=len(text))


@router.post("/analyze")
def analyze(file_id: str = Form(...), filename: str = Form(...), selection: str = Form("")):
    path = upload_path(file_id, filename)
    parsed = parse_range_selection(selection, count_items(path))
    text = extract_text(path, parsed.selected)
    topics, confidence, items = plan_nine_ue(text)
    return AnalysisResult(file_id=file_id, topics=topics, confidence_score=confidence, ue_items=items, range=parsed, text_length=len(text))
