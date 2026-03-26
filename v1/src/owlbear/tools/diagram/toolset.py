"""DiagramToolset — agent-callable diagram generation tool.

Provides a ``generate_diagram`` tool that renders diagram source code
via :class:`~owlbear.tools.diagram.service.DiagramService` (Kroki API),
saves the output via :class:`~owlbear.tools.screenshot.ScreenshotService`,
and delivers it to the user's channel.

Usage::

    from owlbear.tools.diagram.service import DiagramService
    from owlbear.tools.screenshot import ScreenshotService
    from owlbear.tools.diagram.toolset import DiagramToolset

    toolset = DiagramToolset(
        diagram_service=DiagramService(),
        screenshot_service=ScreenshotService(),
        channel=cli_channel,
        workspace=workspace_root,
    )
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic_ai.toolsets import FunctionToolset

from owlbear.tools.diagram.service import DiagramError

if TYPE_CHECKING:
    from pathlib import Path
    from typing import ClassVar

    from owlbear.channels.base import ChannelPlugin
    from owlbear.tools.diagram.service import DiagramService
    from owlbear.tools.screenshot import ScreenshotService

__all__ = ["DiagramToolset"]

logger = logging.getLogger(__name__)


class DiagramToolset(FunctionToolset):
    """FunctionToolset providing diagram generation and delivery.

    Args:
        diagram_service: Service for rendering diagrams via Kroki.
        screenshot_service: Service for saving and delivering output files.
        channel: Channel adapter for delivering output to the user.
        workspace: Workspace root directory for saving files.
    """

    tool_alias: ClassVar[str] = "diagram"

    def __init__(
        self,
        diagram_service: DiagramService,
        screenshot_service: ScreenshotService,
        channel: ChannelPlugin,
        workspace: Path,
    ) -> None:
        super().__init__()
        self._svc = diagram_service
        self._screenshot = screenshot_service
        self._channel = channel
        self._workspace = workspace
        self._register_tools()

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register diagram tools on this toolset."""
        self.add_function(
            self.generate_diagram,
            name="generate_diagram",
            description=(
                "Render a diagram from source code (mermaid, plantuml, graphviz, "
                "d2, c4plantuml), save the output, and deliver to the user. "
                "Returns the saved file path or an error message."
            ),
        )

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    async def generate_diagram(
        self,
        diagram_type: str,
        source: str,
        output_format: str = "svg",
    ) -> str:
        """Render diagram, save, deliver, return path."""
        try:
            image_bytes = await self._svc.generate(
                diagram_type=diagram_type,
                source=source,
                output_format=output_format,
            )
        except DiagramError as exc:
            logger.warning("Diagram generation failed: %s", exc)
            return f"Diagram generation failed (HTTP {exc.status_code}): {exc.body}"
        except ValueError as exc:
            logger.warning("Invalid diagram input: %s", exc)
            return f"Invalid input: {exc}"

        path = self._screenshot.save(image_bytes, "diagram", self._workspace)
        caption = f"{diagram_type} diagram"
        await self._screenshot.deliver(path, self._channel, caption)
        return str(path)
