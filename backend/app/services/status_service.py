from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from app.models.schemas import AppStatus, StepState, StepStatus


class StatusService:
    def __init__(self) -> None:
        self.status = AppStatus(run_id=self.new_run_id(), steps=self.default_steps())

    def new_run_id(self) -> str:
        return f"RUN-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6]}"

    def default_steps(self) -> list[StepStatus]:
        labels = [
            ("setup", "Setup pruefen"),
            ("target_date", "Zieltag berechnen"),
            ("upload", "Datei hochladen"),
            ("analysis", "Material analysieren"),
            ("klassenbuch", "Klassenbuch vorbereiten"),
            ("timebutler", "Zeiterfassung vorbereiten"),
            ("review", "Finale Review"),
            ("signature", "Klassenbuch signieren"),
        ]
        return [StepStatus(name=name, label=label) for name, label in labels]

    def reset(self, target_date: date | None, mode: str, auto_submit: bool, blocked: bool, blocked_reason: str) -> AppStatus:
        self.status = AppStatus(
            run_id=self.new_run_id(),
            target_date=target_date,
            mode="dry-run" if mode == "dry-run" else "productive",
            auto_submit=auto_submit,
            blocked=blocked,
            blocked_reason=blocked_reason,
            steps=self.default_steps(),
        )
        return self.status

    def set_step(self, name: str, state: StepState, message: str = "") -> AppStatus:
        for step in self.status.steps:
            if step.name == name:
                step.state = state
                step.message = message
                step.updated_at = datetime.now()
        done = sum(1 for step in self.status.steps if step.state in {StepState.success, StepState.skipped})
        self.status.progress = round(done / len(self.status.steps) * 100)
        return self.status


status_service = StatusService()
