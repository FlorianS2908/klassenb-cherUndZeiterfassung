from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.config import get_settings, resolve_project_path


def screenshot_name(run_id: str, step: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_step = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in step)
    return f"{run_id}_{stamp}_{safe_step}.png"


def list_screenshots() -> list[dict[str, str]]:
    folder = resolve_project_path(get_settings().screenshot_folder)
    folder.mkdir(parents=True, exist_ok=True)
    return [{"name": path.name, "path": str(path)} for path in sorted(folder.glob("*.png"), reverse=True)]


async def save_page_screenshot(page, run_id: str, step: str) -> Path:
    folder = resolve_project_path(get_settings().screenshot_folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / screenshot_name(run_id, step)
    await page.screenshot(path=str(path), full_page=True)
    return path
