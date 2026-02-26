"""Browser action tools — navigate, click, type, select, read text, screenshot.

Provides Playwright-based browser actions:

* :func:`browser_navigate` — navigate to a URL with safety checks
* :func:`browser_click` — click an element by selector
* :func:`browser_type` — fill text into an input by selector
* :func:`browser_select` — select a dropdown option by selector
* :func:`browser_read_text` — extract text from the page or a specific element
* :func:`browser_screenshot` — capture a screenshot as base64 PNG
"""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING

from owlbear.tools.browser.safety import URLSafetyGuard

if TYPE_CHECKING:
    from playwright.async_api import Page

    from owlbear.tools.browser.config import BrowserConfig

logger = logging.getLogger(__name__)


async def browser_navigate(url: str, *, page: Page, config: BrowserConfig) -> str:
    """Navigate *page* to *url* after safety validation.

    Validates the URL against ``config.blocked_urls`` and
    ``config.allowed_urls`` via :class:`URLSafetyGuard` **before**
    issuing the navigation request.

    Args:
        url: The target URL to navigate to.
        page: An active Playwright page instance.
        config: Browser configuration with URL safety lists and timeout.

    Returns:
        A human-readable confirmation string:
        ``"Navigated to {title} ({url})"``.

    Raises:
        BlockedURLError: If the URL is denied by the safety guard.
        TimeoutError: If navigation exceeds ``config.timeout_ms``.
    """
    guard = URLSafetyGuard(config)
    guard.check_url(url)

    await page.goto(url, timeout=config.timeout_ms)

    title = await page.title()
    return f"Navigated to {title} ({page.url})"


async def browser_click(selector: str, *, page: Page) -> str:
    """Click the element matching *selector*.

    Waits for the selector to appear in the DOM, then clicks it.

    Args:
        selector: A CSS or Playwright selector string.
        page: An active Playwright page instance.

    Returns:
        A confirmation string: ``"Clicked {selector}"``.

    Raises:
        TimeoutError: If the selector is not found within the default timeout.
    """
    await page.wait_for_selector(selector)
    await page.click(selector)
    return f"Clicked {selector}"


async def browser_type(selector: str, text: str, *, page: Page) -> str:
    """Fill *text* into the input matching *selector*.

    Uses ``page.fill`` (not ``page.type``) so the field is cleared before
    the new value is set — this is more reliable for most form inputs.

    Args:
        selector: A CSS or Playwright selector string for the input element.
        text: The text to fill into the input.
        page: An active Playwright page instance.

    Returns:
        A confirmation string: ``"Typed '{text}' into {selector}"``.

    Raises:
        TimeoutError: If the selector is not found within the default timeout.
    """
    await page.wait_for_selector(selector)
    await page.fill(selector, text)
    return f"Typed '{text}' into {selector}"


async def browser_select(selector: str, value: str, *, page: Page) -> str:
    """Select the option with *value* in the ``<select>`` matching *selector*.

    Args:
        selector: A CSS or Playwright selector for the ``<select>`` element.
        value: The option value to select.
        page: An active Playwright page instance.

    Returns:
        A confirmation string: ``"Selected '{value}' in {selector}"``.

    Raises:
        TimeoutError: If the selector is not found within the default timeout.
    """
    await page.wait_for_selector(selector)
    await page.select_option(selector, value)
    return f"Selected '{value}' in {selector}"


async def browser_read_text(
    *,
    page: Page,
    selector: str | None = None,
    max_length: int = 5000,
) -> str:
    """Extract text content from the page or a specific element.

    If *selector* is ``None``, reads the full page text via
    ``page.inner_text("body")``.  Otherwise waits for the selector
    to appear, then reads its ``inner_text``.

    The result is stripped of leading/trailing whitespace.  If the
    stripped text exceeds *max_length* characters it is truncated and
    the suffix ``"... [truncated]"`` is appended.

    Args:
        page: An active Playwright page instance.
        selector: Optional CSS or Playwright selector.  ``None`` means
            read the entire page body.
        max_length: Maximum character count before truncation.

    Returns:
        The extracted (and possibly truncated) text.

    Raises:
        TimeoutError: If the selector is not found within the default timeout.
    """
    if selector is not None:
        await page.wait_for_selector(selector)

    target = selector if selector is not None else "body"
    text = await page.inner_text(target)
    text = text.strip()

    if len(text) > max_length:
        text = text[:max_length] + "... [truncated]"

    return text


async def browser_screenshot(
    *,
    page: Page,
    selector: str | None = None,
    full_page: bool = True,
) -> str:
    """Capture a screenshot and return it as a base64-encoded PNG string.

    If *selector* is ``None``, captures the viewport (or the full
    scrollable page when *full_page* is ``True``).  If *selector* is
    given, waits for the element then captures an element-level
    screenshot; *full_page* is ignored in this case.

    Args:
        page: An active Playwright page instance.
        selector: Optional CSS or Playwright selector for element
            screenshot.  ``None`` means capture the page.
        full_page: Whether to capture the full scrollable page.
            Only used when *selector* is ``None``.

    Returns:
        A base64-encoded PNG string.

    Raises:
        TimeoutError: If the selector is not found within the default timeout.
    """
    if selector is not None:
        locator = await page.wait_for_selector(selector)
        screenshot_bytes = await locator.screenshot()
    else:
        screenshot_bytes = await page.screenshot(full_page=full_page)

    return base64.b64encode(screenshot_bytes).decode("ascii")
