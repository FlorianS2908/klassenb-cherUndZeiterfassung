from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class StepState(str, Enum):
    waiting = "waiting"
    running = "running"
    success = "success"
    error = "error"
    manual_review = "manual_review"
    skipped = "skipped"


class StepStatus(BaseModel):
    name: str
    label: str
    state: StepState = StepState.waiting
    message: str = ""
    updated_at: datetime | None = None


class AppStatus(BaseModel):
    run_id: str
    target_date: date | None = None
    mode: Literal["dry-run", "productive"] = "dry-run"
    auto_submit: bool = False
    blocked: bool = False
    blocked_reason: str = ""
    progress: int = 0
    steps: list[StepStatus] = Field(default_factory=list)
    last_klassenbuch_run: str = "-"
    last_timebutler_run: str = "-"
    next_scheduled_run: str = "Mo-Fr 08:20 Europe/Berlin"


class RangeResult(BaseModel):
    selection: str
    selected: list[int]
    total_items: int
    is_full_range: bool
    count: int


class UploadedFileInfo(BaseModel):
    file_id: str
    filename: str
    file_type: str
    total_items: int
    unit_label: str
    size_bytes: int


class FilePreview(BaseModel):
    file_id: str
    range: RangeResult
    text_preview: str
    text_length: int


class UeItem(BaseModel):
    number: int = Field(ge=1, le=9)
    content: str
    formats: list[str] = Field(default_factory=lambda: ["Aufgaben-/Uebungsbesprechung", "betreute Einzelarbeit"])

    @field_validator("formats")
    @classmethod
    def max_two_formats(cls, value: list[str]) -> list[str]:
        if len(value) > 2:
            raise ValueError("Pro UE sind maximal zwei Lernformate erlaubt.")
        return value


class AnalysisResult(BaseModel):
    file_id: str
    topics: list[str]
    confidence_score: float = Field(ge=0, le=1)
    ue_items: list[UeItem]
    range: RangeResult
    text_length: int
    ai_used: bool = False
    ai_model: str = ""
    ai_warnings: list[str] = Field(default_factory=list)
    ai_truncated: bool = False


class TimebutlerPayload(BaseModel):
    target_date: date
    project: str
    category: str
    start: str
    end: str
    pause: str
    remark: str = Field(max_length=500)


class ReviewState(BaseModel):
    confirmed: bool = False
    confirmed_at: datetime | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class SubmitRequest(BaseModel):
    review_confirmed: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)


class ApiMessage(BaseModel):
    ok: bool
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
