from __future__ import annotations

import asyncio
import sys

from playwright.async_api import async_playwright


def _details() -> dict:
    policy = asyncio.get_event_loop_policy()
    try:
        loop = asyncio.get_running_loop()
        loop_name = type(loop).__name__
    except RuntimeError:
        loop_name = ""
    return {
        "platform": sys.platform,
        "python_version": sys.version,
        "event_loop_policy": type(policy).__name__,
        "event_loop": loop_name,
        "is_windows_proactor_policy": type(policy).__name__ == "WindowsProactorEventLoopPolicy",
        "playwright_importable": True,
    }


def _failure(step: str, exc: Exception) -> dict:
    return {
        "ok": False,
        "step": step,
        "message": str(exc).strip() or f"unbekannter Fehler ({type(exc).__name__})",
        "exception_type": type(exc).__name__,
        "details": _details(),
    }


async def check_playwright_health() -> dict:
    playwright = None
    browser = None
    context = None
    try:
        try:
            playwright = await async_playwright().start()
        except Exception as exc:
            return _failure("playwright_start", exc)
        try:
            browser = await playwright.chromium.launch(headless=True)
        except Exception as exc:
            return _failure("chromium_launch", exc)
        try:
            context = await browser.new_context()
            page = await context.new_page()
        except Exception as exc:
            return _failure("new_page", exc)
        try:
            await page.goto("about:blank", wait_until="domcontentloaded")
        except Exception as exc:
            return _failure("goto_blank", exc)
        return {"ok": True, "step": "close", "message": "Playwright/Chromium ist startbar.", "exception_type": "", "details": _details()}
    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()
