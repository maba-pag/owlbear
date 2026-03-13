"""ScreenshotService — capture, save, and deliver screenshots."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear.channels.base import ChannelPlugin

__all__ = ["ScreenshotService"]


class ScreenshotService:
    """Stateless service for capturing, saving, and delivering screenshots.

    Provides four operations:

    * :meth:`save` — persist raw image bytes to disk.
    * :meth:`deliver` — send a saved file to a channel via :meth:`~owlbear.channels.base.ChannelPlugin.send_image`.
    * :meth:`capture_browser` — thin async wrapper around Playwright's
      ``page.screenshot()``.
    * :meth:`capture_terminal` — encode terminal text output as UTF-8 bytes.
    """

    # ------------------------------------------------------------------
    # save
    # ------------------------------------------------------------------

    def save(self, image_bytes: bytes, name: str, workspace: Path) -> Path:
        """Persist *image_bytes* as a PNG under *workspace*/.owlbear/screenshots/.

        The filename is ``{timestamp}_{name}.png`` where *timestamp* is
        :func:`time.time_ns` (nanosecond epoch) to avoid collisions.

        Creates the target directory if it does not already exist.

        Returns the :class:`~pathlib.Path` of the written file.
        """
        screenshots_dir = workspace / ".owlbear" / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{time.time_ns()}_{name}.png"
        dest = screenshots_dir / filename
        dest.write_bytes(image_bytes)
        return dest

    # ------------------------------------------------------------------
    # deliver
    # ------------------------------------------------------------------

    async def deliver(self, path: Path, channel: ChannelPlugin, caption: str) -> None:
        """Deliver *path* to *channel* via :meth:`~ChannelPlugin.send_image`."""
        await channel.send_image(path, caption=caption)

    # ------------------------------------------------------------------
    # capture helpers
    # ------------------------------------------------------------------

    async def capture_browser(self, page: object) -> bytes:
        """Capture a PNG screenshot from a Playwright *page*.

        Returns the raw PNG bytes.
        """
        result: bytes = await page.screenshot(type="png")  # type: ignore[attr-defined]
        return result

    def capture_terminal(self, text: str) -> bytes:
        """Encode *text* (terminal output) as UTF-8 bytes.

        This is intentionally simple — callers decide whether to write the
        result as a ``.txt`` file via :meth:`save` or handle it otherwise.
        """
        return text.encode()
