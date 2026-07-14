from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from playwright.async_api import Browser, BrowserContext, Locator, Page, async_playwright


async def first_visible(page: Page, selectors: list[str]):
    for selector in selectors:
        locator = page.locator(selector).first()
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
async def browser_page() -> AsyncIterator[Page]:
    playwright = await async_playwright().start()
    browser: Browser | None = None
    context: BrowserContext | None = None
    try:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1440, "height": 1000})
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
