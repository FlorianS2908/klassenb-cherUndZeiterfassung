from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import get_settings, resolve_project_path
from app.services.screenshot_service import list_screenshots

SECRET_RE = re.compile(r"(password|api_key|token|cookie|session)", re.IGNORECASE)


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: ("<redacted>" if SECRET_RE.search(key) else sanitize(val)) for key, val in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"(sk-[A-Za-z0-9_-]+)", "<redacted>", value)
    return value


def create_error_report(run_id: str, status: dict[str, Any]) -> Path:
    settings = get_settings()
    report_dir = resolve_project_path(settings.error_report_folder)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{run_id}_error_report_{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    log_dir = resolve_project_path(settings.log_folder)
    with zipfile.ZipFile(report_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("status.json", json.dumps(sanitize(status), ensure_ascii=False, indent=2, default=str))
        zf.writestr("settings.json", json.dumps(sanitize(settings.public_dict()), ensure_ascii=False, indent=2))
        for log in log_dir.glob("*.log"):
            zf.write(log, f"logs/{log.name}")
        for screenshot in list_screenshots():
            path = Path(screenshot["path"])
            if path.exists():
                zf.write(path, f"screenshots/{path.name}")
    return report_path
