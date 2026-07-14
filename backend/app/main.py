from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime

if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_analysis_history, routes_diagnostics, routes_error_report, routes_files, routes_klassenbuch, routes_logs, routes_review, routes_screenshots, routes_settings, routes_setup, routes_status, routes_timebutler
from app.config import ensure_runtime_ready, get_settings, resolve_project_path
from app.scheduler import create_scheduler


def configure_logging() -> None:
    settings = get_settings()
    log_dir = resolve_project_path(settings.log_folder)
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def create_app() -> FastAPI:
    ok, messages = ensure_runtime_ready(run_setup_if_missing=False)
    configure_logging()
    for message in messages:
        logging.warning(message)
    app = FastAPI(title="Klassenbuch Timebutler Tool", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in [
        routes_status.router,
        routes_setup.router,
        routes_files.router,
        routes_analysis_history.router,
        routes_klassenbuch.router,
        routes_timebutler.router,
        routes_review.router,
        routes_screenshots.router,
        routes_settings.router,
        routes_logs.router,
        routes_error_report.router,
        routes_diagnostics.router,
    ]:
        app.include_router(router)

    @app.get("/")
    def root():
        return {"ok": ok, "messages": messages}

    scheduler = create_scheduler()

    @app.on_event("startup")
    def start_scheduler():
        if not scheduler.running:
            scheduler.start()

    @app.on_event("shutdown")
    def stop_scheduler():
        if scheduler.running:
            scheduler.shutdown(wait=False)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
