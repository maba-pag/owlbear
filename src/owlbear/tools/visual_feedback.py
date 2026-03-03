"""VisualFeedbackToolset — agent-callable screenshot and share tools.

Provides two tools for agents to capture and deliver visual output:

* ``share_screenshot`` — captures browser screenshot, saves, delivers to channel.
* ``share_terminal_output`` — saves terminal text output, delivers to channel.

Usage::

    from owlbear.tools.screenshot import ScreenshotService
    from owlbear.tools.visual_feedback import VisualFeedbackToolset

    toolset = VisualFeedbackToolset(
        screenshot_service=ScreenshotService(),
        channel=cli_channel,
        page_getter=lambda: browser_toolset.page,
        workspace=workspace_root,
    )
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic_ai.toolsets import FunctionToolset

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear.channels.base import ChannelPlugin
    from owlbear.tools.screenshot import ScreenshotService

__all__ = ["VisualFeedbackToolset"]

logger = logging.getLogger(__name__)


class VisualFeedbackToolset(FunctionToolset):
    """FunctionToolset providing screenshot capture and delivery tools.

    Args:
        screenshot_service: Service for capturing, saving, and delivering.
        channel: Channel adapter for delivering output to the user.
        page_getter: Callable returning the active Playwright page.
        workspace: Workspace root directory for saving files.
    """

    def __init__(
        self,
        screenshot_service: ScreenshotService,
        channel: ChannelPlugin,
        page_getter: Callable[[], object],
        workspace: Path,
    ) -> None:
        super().__init__()
        self._svc = screenshot_service
        self._channel = channel
        self._page_getter = page_getter
        self._workspace = workspace
        self._register_tools()

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register visual feedback tools on this toolset."""
        self.add_function(
            self.share_screenshot,
            name="share_screenshot",
            description=(
                "Capture a browser screenshot, save it, and deliver to the user. "
                "Returns the saved file path."
            ),
        )
        self.add_function(
            self.share_terminal_output,
            name="share_terminal_output",
            description=(
                "Save terminal text output as a file and deliver to the user. "
                "Returns the saved file path."
            ),
        )

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    async def share_screenshot(self, caption: str) -> str:
        """Capture browser screenshot, save, deliver, return path."""
        page = self._page_getter()
        image_bytes = await self._svc.capture_browser(page)
        path = self._svc.save(image_bytes, "screenshot", self._workspace)
        await self._svc.deliver(path, self._channel, caption)
        return str(path)

    async def share_terminal_output(self, output: str, caption: str) -> str:
        """Save terminal text output, deliver, return path."""
        text_bytes = self._svc.capture_terminal(output)
        path = self._svc.save(text_bytes, "terminal", self._workspace)
        await self._svc.deliver(path, self._channel, caption)
        return str(path)
