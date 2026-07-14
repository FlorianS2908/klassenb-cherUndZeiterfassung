from __future__ import annotations

from datetime import date, datetime
from enum import Enum
import re
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
    browser_mode: str = "unsichtbar/headless"
    browser_headless: bool = True
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
    signature_confirmed: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)


class SetupDefaults(BaseModel):
    klassenbuch_url: str
    timebutler_url: str
    klassenbuch_username: str = ""
    timebutler_username: str = ""
    use_separate_timebutler_credentials: bool = False
    openai_api_key_file: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_max_input_chars: int = 30000
    openai_timeout_seconds: int = 60
    openai_retry_count: int = 2
    openai_temperature: float = 0.2
    auto_submit: bool = False
    default_signature: str = "Schaffer"
    upload_folder: str = "./uploads"
    screenshot_folder: str = "./screenshots"
    log_folder: str = "./logs"
    error_report_folder: str = "./error_reports"
    analysis_history_folder: str = "./analysis_history"
    reference_screenshot_dir: str = ""
    timebutler_project: str = "FbW"
    timebutler_category: str = "Training/Coaching"
    timebutler_start: str = "08:30"
    timebutler_end: str = "16:30"
    timebutler_pause: str = "45m"
    timebutler_remark: str = "Training/Coaching im Rahmen der FbW-Unterrichtsdurchfuehrung"
    federal_state: str = "BW"
    blocked_dates: str = ""
    vacation_dates: str = ""
    sick_dates: str = ""
    desktop_notifications: bool = True
    auto_open_browser: bool = True
    auto_dry_run_on_start: bool = False
    browser_headless: bool = True
    browser_slow_mo_ms: int = 0
    browser_keep_open_on_error: bool = False
    github_remote_url: str = ""
    git_default_branch: str = "main"


class SetupPayload(SetupDefaults):
    klassenbuch_password: str = ""
    timebutler_password: str = ""
    openai_api_key: str = ""

    @field_validator(
        "klassenbuch_url",
        "timebutler_url",
        "klassenbuch_username",
        "openai_model",
        "default_signature",
        "timebutler_project",
        "timebutler_category",
        "timebutler_start",
        "timebutler_end",
        "timebutler_pause",
        "timebutler_remark",
        "federal_state",
        "git_default_branch",
    )
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator(
        "timebutler_username",
        "openai_api_key_file",
        "openai_api_key",
        "reference_screenshot_dir",
        "blocked_dates",
        "vacation_dates",
        "sick_dates",
        "github_remote_url",
    )
    @classmethod
    def strip_optional_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("timebutler_start", "timebutler_end")
    @classmethod
    def validate_time(cls, value: str) -> str:
        if not re.fullmatch(r"\d{2}:\d{2}", value):
            raise ValueError("Zeit muss im Format hh:mm angegeben werden.")
        hours, minutes = value.split(":")
        if int(hours) > 23 or int(minutes) > 59:
            raise ValueError("Zeit muss im Format hh:mm angegeben werden.")
        return value


class SetupCheckResult(BaseModel):
    env_exists: bool
    setup_required: bool
    missing: list[str] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)
    config_public: dict[str, Any] = Field(default_factory=dict)


class OpenAiKeyFileCheck(BaseModel):
    exists: bool
    readable: bool
    non_empty: bool
    message: str


class ApiMessage(BaseModel):
    ok: bool
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
