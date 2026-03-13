"""Tests for owlbear.tools.screenshot — ScreenshotService."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from owlbear.tools.screenshot import ScreenshotService

# Reusable fake path for deliver() tests (not actual filesystem access)
_FAKE_SHOT = Path("fake_workspace") / "shot.png"


# ---------------------------------------------------------------------------
# save()
# ---------------------------------------------------------------------------


class TestSave:
    """ScreenshotService.save persists image bytes to disk."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """save() should create a .png file in .owlbear/screenshots/."""
        svc = ScreenshotService()
        data = b"\x89PNG\r\n\x1a\nfake"
        result = svc.save(data, "test_shot", tmp_path)
        assert result.exists()
        assert result.read_bytes() == data

    def test_save_path_contains_timestamp_and_name(self, tmp_path: Path) -> None:
        """Filename should match {timestamp}_{name}.png pattern."""
        svc = ScreenshotService()
        result = svc.save(b"img", "my_capture", tmp_path)
        # Pattern: digits (timestamp) _ name .png
        assert re.match(r"\d+_my_capture\.png$", result.name)

    def test_save_creates_directory_if_missing(self, tmp_path: Path) -> None:
        """save() should create .owlbear/screenshots/ if it doesn't exist."""
        svc = ScreenshotService()
        workspace = tmp_path / "fresh_workspace"
        # Directory doesn't exist yet
        assert not workspace.exists()
        result = svc.save(b"data", "shot", workspace)
        assert result.exists()
        assert ".owlbear" in str(result)
        assert "screenshots" in str(result)

    def test_save_returns_path_under_screenshots_dir(self, tmp_path: Path) -> None:
        """Returned path should be under {workspace}/.owlbear/screenshots/."""
        svc = ScreenshotService()
        result = svc.save(b"data", "img", tmp_path)
        expected_dir = tmp_path / ".owlbear" / "screenshots"
        assert result.parent == expected_dir


# ---------------------------------------------------------------------------
# deliver()
# ---------------------------------------------------------------------------


class TestDeliver:
    """ScreenshotService.deliver dispatches to the appropriate channel method."""

    @pytest.mark.asyncio
    async def test_deliver_calls_send_image(self) -> None:
        """deliver() should delegate to channel.send_image()."""
        svc = ScreenshotService()
        channel = AsyncMock()
        channel.send_image = AsyncMock()

        await svc.deliver(_FAKE_SHOT, channel, "caption text")

        channel.send_image.assert_awaited_once_with(_FAKE_SHOT, caption="caption text")


# ---------------------------------------------------------------------------
# capture_browser()
# ---------------------------------------------------------------------------


class TestCaptureBrowser:
    """ScreenshotService.capture_browser wraps page.screenshot()."""

    @pytest.mark.asyncio
    async def test_capture_browser_calls_page_screenshot(self) -> None:
        """Should call page.screenshot() and return the bytes."""
        svc = ScreenshotService()
        page = AsyncMock()
        page.screenshot = AsyncMock(return_value=b"\x89PNGdata")

        result = await svc.capture_browser(page)

        page.screenshot.assert_awaited_once()
        assert result == b"\x89PNGdata"

    @pytest.mark.asyncio
    async def test_capture_browser_passes_full_page_false(self) -> None:
        """Default capture should be viewport-only (full_page=False)."""
        svc = ScreenshotService()
        page = AsyncMock()
        page.screenshot = AsyncMock(return_value=b"img")

        await svc.capture_browser(page)

        page.screenshot.assert_awaited_once_with(type="png")


# ---------------------------------------------------------------------------
# capture_terminal()
# ---------------------------------------------------------------------------


class TestCaptureTerminal:
    """ScreenshotService.capture_terminal encodes text as bytes."""

    def test_capture_terminal_returns_utf8_bytes(self) -> None:
        """Should encode terminal output text as UTF-8 bytes."""
        svc = ScreenshotService()
        result = svc.capture_terminal("hello\nworld")
        assert result == b"hello\nworld"

    def test_capture_terminal_handles_unicode(self) -> None:
        """Should handle unicode characters in terminal output."""
        svc = ScreenshotService()
        result = svc.capture_terminal("✓ passed • 5 tests")
        assert result == "✓ passed • 5 tests".encode()

    def test_capture_terminal_empty_string(self) -> None:
        """Should handle empty string."""
        svc = ScreenshotService()
        result = svc.capture_terminal("")
        assert result == b""
