"""BrowserToolset — FunctionToolset wrapping all 7 browser action tools.

Registers browser_navigate, browser_click, browser_type, browser_select,
browser_read_text, browser_screenshot, and browser_snapshot as tools on a
:class:`~pydantic_ai.toolsets.FunctionToolset`.  Owns a
:class:`BrowserManager` instance and injects ``page`` / ``config`` into
each tool wrapper.

Usage::

    from owlbear.tools.browser.toolset import BrowserToolset

    toolset = BrowserToolset()
    await toolset.setup()
    # ... use with an Agent ...
    await toolset.teardown()
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic_ai.toolsets import FunctionToolset

from owlbear.tools.browser.actions import (
    browser_click,
    browser_navigate,
    browser_read_text,
    browser_screenshot,
    browser_select,
    browser_type,
)
from owlbear.tools.browser.config import BrowserConfig
from owlbear.tools.browser.content_guard import ContentInjectionGuard
from owlbear.tools.browser.manager import BrowserManager

if TYPE_CHECKING:
    from typing import ClassVar

    from playwright.async_api import Page

__all__ = ["BrowserToolset"]

logger = logging.getLogger(__name__)

# JS snippet that watches <title> for mutations and re-applies the OwlBear
# prefix.  The prefix is passed as a safe argument via Playwright's
# parameterized page.evaluate() — never interpolated into the JS string.
_TITLE_OBSERVER_JS = """
(prefix) => {
    const titleEl = document.querySelector('title');
    if (!titleEl) return;
    const obs = new MutationObserver(() => {
        if (!document.title.startsWith(prefix)) {
            document.title = prefix + ' ' + document.title;
        }
    });
    obs.observe(titleEl, { childList: true });
}
""".strip()


class BrowserToolset(FunctionToolset):
    """FunctionToolset subclass that registers all 7 browser action tools.

    Owns a :class:`BrowserManager` and injects ``page`` and ``config``
    into each tool wrapper.  The caller manages browser lifecycle via
    :meth:`setup` / :meth:`teardown`.

    Args:
        config: Browser configuration.  Defaults to :class:`BrowserConfig`
            with all default values when ``None``.
    """

    tool_alias: ClassVar[str] = "browser"

    def __init__(self, config: BrowserConfig | None = None) -> None:
        super().__init__()
        self._config: BrowserConfig = config or BrowserConfig()
        self._manager: BrowserManager | None = None
        self._content_guard = ContentInjectionGuard(mode=self._config.content_scan_mode)
        self._register_tools()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def config(self) -> BrowserConfig:
        """The browser configuration for this toolset."""
        return self._config

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def setup(self, *, task_label: str | None = None) -> None:
        """Launch browser — creates BrowserManager and enters context.

        In CDP mode, prefixes the page title with ``[OwlBear]`` (or
        ``[OwlBear {task_label}]`` when *task_label* is given) and installs
        a ``MutationObserver`` that re-applies the prefix whenever the
        title changes.

        Args:
            task_label: Optional label embedded in the title prefix
                (e.g. ``"Task 65"`` → ``[OwlBear Task 65]``).
        """
        self._manager = BrowserManager(self._config)
        await self._manager.__aenter__()

        if self._config.cdp_endpoint:
            prefix = f"[OwlBear {task_label}]" if task_label else "[OwlBear]"
            await self.page.evaluate(
                "(prefix) => { document.title = prefix + ' ' + document.title }",
                prefix,
            )
            await self.page.evaluate(_TITLE_OBSERVER_JS, prefix)
            logger.warning("CDP mode: attached to user browser — full session access")

    async def teardown(self) -> None:
        """Close browser — exits BrowserManager context."""
        if self._manager is not None:
            await self._manager.__aexit__(None, None, None)
            self._manager = None

    @property
    def page(self) -> Page:
        """The active Playwright page from the managed browser.

        Raises:
            RuntimeError: If :meth:`setup` has not been called.
        """
        if self._manager is None:
            msg = "BrowserToolset not set up. Call setup() first."
            raise RuntimeError(msg)
        return self._manager.page

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register all 7 browser action tools on this toolset."""
        self.add_function(
            self._navigate,
            name="browser_navigate",
            description="Navigate to a URL with safety checks.",
        )
        self.add_function(
            self._click,
            name="browser_click",
            description="Click an element by CSS selector.",
        )
        self.add_function(
            self._type,
            name="browser_type",
            description="Fill text into an input by CSS selector.",
        )
        self.add_function(
            self._select,
            name="browser_select",
            description="Select a dropdown option by CSS selector and value.",
        )
        self.add_function(
            self._read_text,
            name="browser_read_text",
            description="Extract text from the page or a specific element.",
        )
        self.add_function(
            self._screenshot,
            name="browser_screenshot",
            description="Capture a screenshot as base64 PNG.",
        )
        self.add_function(
            self._snapshot,
            name="browser_snapshot",
            description=(
                "Get accessibility tree snapshot of the current page. "
                "Token cost by filter: text (~800 tokens) — page text only; "
                "interactive (~3600) — clickable elements; "
                "full (~10500) — complete tree. Default: interactive."
            ),
        )

    # ------------------------------------------------------------------
    # Tool wrappers (inject page/config from self)
    # ------------------------------------------------------------------

    async def _navigate(self, url: str) -> str:
        """Navigate to a URL."""
        return await browser_navigate(url, page=self.page, config=self._config)

    async def _click(self, selector: str) -> str:
        """Click an element by selector."""
        return await browser_click(selector, page=self.page)

    async def _type(self, selector: str, text: str) -> str:
        """Fill text into an input by selector."""
        return await browser_type(selector, text, page=self.page)

    async def _select(self, selector: str, value: str) -> str:
        """Select a dropdown option by selector and value."""
        return await browser_select(selector, value, page=self.page)

    async def _read_text(
        self,
        *,
        selector: str | None = None,
        max_length: int = 5000,
    ) -> str:
        """Extract text from the page or a specific element."""
        text = await browser_read_text(
            page=self.page,
            selector=selector,
            max_length=max_length,
        )
        result = self._content_guard.scan(text)
        if result.blocked:
            return f"BLOCKED: {result.reason}"
        return text

    async def _screenshot(
        self,
        *,
        selector: str | None = None,
        full_page: bool = True,
    ) -> str:
        """Capture a screenshot as base64 PNG."""
        return await browser_screenshot(
            page=self.page,
            selector=selector,
            full_page=full_page,
        )

    async def _snapshot(
        self,
        *,
        filter: str = "interactive",  # noqa: A002
    ) -> str:
        """Get accessibility tree snapshot, formatted as text."""
        if self._manager is None:
            msg = "BrowserToolset not set up. Call setup() first."
            raise RuntimeError(msg)
        nodes = await self._manager.snapshot(filter=filter)
        return "\n".join(f"[{node.id}] {node.role}: {node.name}" for node in nodes)
