"""ScreenshotOnErrorHook — auto-capture browser screenshot on error.

Registers on :attr:`~owlbear.core.hooks.HookEvent.ON_ERROR` and captures a
browser screenshot when the browser toolset has an active page.  Controlled
by the ``screenshot_mode`` config setting.

Usage::

    from owlbear.tools.screenshot_hook import ScreenshotOnErrorHook

    hook = ScreenshotOnErrorHook(
        screenshot_service=svc,
        browser_toolset=browser,
        workspace=workspace_root,
        screenshot_mode="on_error",
    )
    hook.register(hook_registry)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from owlbear.core.hooks import OnErrorData  # noqa: TC001

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear.core.hooks import HookRegistry
    from owlbear.tools.screenshot import ScreenshotService

__all__ = ["ScreenshotOnErrorHook"]

logger = logging.getLogger(__name__)


class ScreenshotOnErrorHook:
    """Hook that auto-captures a browser screenshot on tool/turn errors.

    Args:
        screenshot_service: Service for capturing and saving screenshots.
        browser_toolset: Browser toolset with ``.page`` property, or ``None``.
        workspace: Workspace root directory for saving screenshots.
        screenshot_mode: One of ``"auto"``, ``"manual"``, ``"on_error"``.
            Capture triggers on ``"auto"`` and ``"on_error"``; skipped on
            ``"manual"``.
    """

    def __init__(
        self,
        screenshot_service: ScreenshotService,
        browser_toolset: object | None,
        workspace: Path,
        screenshot_mode: str = "on_error",
    ) -> None:
        self._svc = screenshot_service
        self._browser = browser_toolset
        self._workspace = workspace
        self._mode = screenshot_mode

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, registry: HookRegistry) -> None:
        """Register this hook on :attr:`HookEvent.ON_ERROR`."""
        from owlbear.core.hooks import HookEvent  # noqa: PLC0415

        registry.register(HookEvent.ON_ERROR, self.handle)

    def unregister(self, registry: HookRegistry) -> None:
        """Remove this hook from :attr:`HookEvent.ON_ERROR`."""
        from owlbear.core.hooks import HookEvent  # noqa: PLC0415

        registry.unregister(HookEvent.ON_ERROR, self.handle)

    # ------------------------------------------------------------------
    # Handler
    # ------------------------------------------------------------------

    async def handle(self, data: OnErrorData) -> None:  # noqa: ARG002
        """Capture browser screenshot on error, if conditions are met."""
        if self._mode == "manual":
            return

        if self._browser is None:
            return

        try:
            page = self._browser.page  # type: ignore[union-attr]
        except (RuntimeError, AttributeError):
            logger.debug("Browser page unavailable — skipping error screenshot")
            return

        try:
            image_bytes = await self._svc.capture_browser(page)
            self._svc.save(image_bytes, "error", self._workspace)
            logger.info("Error screenshot saved to %s", self._workspace)
        except Exception:
            logger.exception("Failed to capture error screenshot")
