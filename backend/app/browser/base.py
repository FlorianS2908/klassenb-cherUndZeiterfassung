from __future__ import annotations

from playwright.async_api import Page


async def first_visible(page: Page, selectors: list[str]):
    for selector in selectors:
        locator = page.locator(selector).first()
        try:
            if await locator.is_visible() and await locator.is_enabled():
                return locator
        except Exception:
            continue
    raise RuntimeError("Element konnte mit keinem Selector-Fallback sicher gefunden werden.")
