from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator
import asyncio
import sys

from playwright.async_api import Browser, BrowserContext, Locator, Page, async_playwright

from app.config import get_settings


def _browser_start_context() -> str:
    policy = type(asyncio.get_event_loop_policy()).__name__
    platform = "Windows" if sys.platform.startswith("win") else sys.platform
    return (
        f"Plattform: {platform}. EventloopPolicy: {policy}. "
        "Wahrscheinlich wird Playwright unter einem nicht subprocess-faehigen Eventloop gestartet. "
        "Bitte Uvicorn ohne reload starten, sitecustomize.py laden lassen, WindowsProactorEventLoopPolicy vor dem Start setzen "
        "und python -m playwright install ausfuehren."
    )


def first_locator(scope, selector: str):
    return scope.locator(selector).nth(0)


async def first_visible(page: Page, selectors: list[str]):
    for selector in selectors:
        locator = first_locator(page, selector)
        try:
            if await locator.is_visible() and await locator.is_enabled():
                return locator
        except Exception:
            continue
    raise RuntimeError("Element konnte mit keinem Selector-Fallback sicher gefunden werden.")


async def click_first(page: Page, selectors: list[str], description: str = "Element") -> None:
    locator = await first_visible(page, selectors)
    await locator.click()


async def fill_first(page: Page, selectors: list[str], value: str, description: str = "Feld") -> None:
    locator = await first_visible(page, selectors)
    await locator.fill(value)


async def select_or_fill(page: Page, selectors: list[str], value: str, description: str = "Feld") -> None:
    locator = await first_visible(page, selectors)
    try:
        await locator.select_option(label=value)
        return
    except Exception:
        pass
    try:
        await locator.select_option(value=value)
        return
    except Exception:
        pass
    await locator.fill(value)


async def optional_click(page: Page, selectors: list[str]) -> bool:
    try:
        await click_first(page, selectors)
        return True
    except Exception:
        return False


@asynccontextmanager
async def browser_page(storage_state_path: Path | str | None = None) -> AsyncIterator[Page]:
    try:
        playwright = await async_playwright().start()
    except NotImplementedError as exc:
        raise RuntimeError(f"Playwright-Browserstart fehlgeschlagen: NotImplementedError. {_browser_start_context()}") from exc
    except Exception as exc:
        raise RuntimeError("Playwright konnte nicht gestartet werden. Bitte Playwright installieren und Windows-Eventloop pruefen.") from exc
    browser: Browser | None = None
    context: BrowserContext | None = None
    try:
        try:
            try:
                settings = get_settings()
                headless = settings.browser_headless
                slow_mo = settings.browser_slow_mo_ms
            except Exception:
                headless = True
                slow_mo = 0
            browser = await playwright.chromium.launch(headless=headless, slow_mo=slow_mo)
        except NotImplementedError as exc:
            raise RuntimeError(f"Playwright-Browserstart fehlgeschlagen: NotImplementedError. {_browser_start_context()}") from exc
        except Exception as exc:
            raise RuntimeError("Chromium konnte nicht gestartet werden. Bitte python -m playwright install ausfuehren.") from exc
        context_options: dict[str, object] = {"viewport": {"width": 1440, "height": 1000}}
        if storage_state_path:
            path = Path(storage_state_path)
            if path.exists():
                context_options["storage_state"] = str(path)
        context = await browser.new_context(**context_options)
        page = await context.new_page()
        page.set_default_timeout(15000)
        yield page
    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        await playwright.stop()


async def table_rows(page: Page) -> list[Locator]:
    for selector in ["table tbody tr", "table tr", '[role="row"]']:
        rows = page.locator(selector)
        count = await rows.count()
        if count:
            return [rows.nth(index) for index in range(count)]
    return []
