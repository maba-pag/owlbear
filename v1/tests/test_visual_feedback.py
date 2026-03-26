"""Tests for owlbear.tools.visual_feedback — VisualFeedbackToolset."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear.tools.visual_feedback import VisualFeedbackToolset

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def screenshot_svc() -> MagicMock:
    """Mock ScreenshotService with sync save and async capture/deliver."""
    svc = MagicMock()
    svc.save.return_value = Path("/fake/.owlbear/screenshots/12345_shot.png")
    svc.capture_browser = AsyncMock(return_value=b"\x89PNGdata")
    svc.capture_terminal.return_value = b"terminal output bytes"
    svc.deliver = AsyncMock()
    return svc


@pytest.fixture
def channel() -> AsyncMock:
    """Mock ChannelPlugin."""
    ch = AsyncMock()
    ch.name = "test"
    return ch


@pytest.fixture
def page() -> AsyncMock:
    """Mock Playwright page."""
    return AsyncMock()


@pytest.fixture
def page_getter(page: AsyncMock) -> MagicMock:
    """Callable that returns the mock page."""
    return MagicMock(return_value=page)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def toolset(
    screenshot_svc: MagicMock,
    channel: AsyncMock,
    page_getter: MagicMock,
    workspace: Path,
) -> VisualFeedbackToolset:
    return VisualFeedbackToolset(
        screenshot_service=screenshot_svc,
        channel=channel,
        page_getter=page_getter,
        workspace=workspace,
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    """VisualFeedbackToolset wires up correctly."""

    def test_is_function_toolset(self, toolset: VisualFeedbackToolset) -> None:
        """Should be a FunctionToolset subclass."""
        from pydantic_ai.toolsets import FunctionToolset

        assert isinstance(toolset, FunctionToolset)

    def test_registers_two_tools(self, toolset: VisualFeedbackToolset) -> None:
        """Should register share_screenshot and share_terminal_output tools."""
        names = set(toolset.tools)
        assert "share_screenshot" in names
        assert "share_terminal_output" in names


# ---------------------------------------------------------------------------
# share_screenshot
# ---------------------------------------------------------------------------


class TestShareScreenshot:
    """share_screenshot captures, saves, delivers, returns path."""

    @pytest.mark.asyncio
    async def test_captures_browser_page(
        self,
        toolset: VisualFeedbackToolset,
        screenshot_svc: MagicMock,
        page: AsyncMock,
    ) -> None:
        """Should call capture_browser with the page from page_getter."""
        await toolset.share_screenshot(caption="test cap")
        screenshot_svc.capture_browser.assert_awaited_once_with(page)

    @pytest.mark.asyncio
    async def test_saves_captured_bytes(
        self,
        toolset: VisualFeedbackToolset,
        screenshot_svc: MagicMock,
        workspace: Path,
    ) -> None:
        """Should save the captured bytes via ScreenshotService.save."""
        await toolset.share_screenshot(caption="save test")
        screenshot_svc.save.assert_called_once()
        args = screenshot_svc.save.call_args
        assert args[0][0] == b"\x89PNGdata"  # image_bytes
        assert args[0][2] == workspace  # workspace

    @pytest.mark.asyncio
    async def test_delivers_to_channel(
        self,
        toolset: VisualFeedbackToolset,
        screenshot_svc: MagicMock,
    ) -> None:
        """Should deliver the saved path to the channel."""
        await toolset.share_screenshot(caption="deliver cap")
        screenshot_svc.deliver.assert_awaited_once()
        call_args = screenshot_svc.deliver.call_args[0]
        assert call_args[0] == Path("/fake/.owlbear/screenshots/12345_shot.png")
        assert call_args[2] == "deliver cap"

    @pytest.mark.asyncio
    async def test_returns_path_string(
        self,
        toolset: VisualFeedbackToolset,
    ) -> None:
        """Should return the string representation of the saved path."""
        result = await toolset.share_screenshot(caption="ret test")
        assert result == str(Path("/fake/.owlbear/screenshots/12345_shot.png"))

    @pytest.mark.asyncio
    async def test_save_name_is_screenshot(
        self,
        toolset: VisualFeedbackToolset,
        screenshot_svc: MagicMock,
    ) -> None:
        """save() name arg should be 'screenshot'."""
        await toolset.share_screenshot(caption="name test")
        name_arg = screenshot_svc.save.call_args[0][1]
        assert name_arg == "screenshot"


# ---------------------------------------------------------------------------
# share_terminal_output
# ---------------------------------------------------------------------------


class TestShareTerminalOutput:
    """share_terminal_output saves text, delivers, returns path."""

    @pytest.mark.asyncio
    async def test_captures_terminal_text(
        self,
        toolset: VisualFeedbackToolset,
        screenshot_svc: MagicMock,
    ) -> None:
        """Should call capture_terminal with the output text."""
        await toolset.share_terminal_output(output="hello world", caption="term cap")
        screenshot_svc.capture_terminal.assert_called_once_with("hello world")

    @pytest.mark.asyncio
    async def test_saves_terminal_bytes(
        self,
        toolset: VisualFeedbackToolset,
        screenshot_svc: MagicMock,
        workspace: Path,
    ) -> None:
        """Should save the encoded bytes via ScreenshotService.save."""
        await toolset.share_terminal_output(output="data", caption="save")
        screenshot_svc.save.assert_called_once()
        args = screenshot_svc.save.call_args
        assert args[0][0] == b"terminal output bytes"
        assert args[0][2] == workspace

    @pytest.mark.asyncio
    async def test_delivers_to_channel(
        self,
        toolset: VisualFeedbackToolset,
        screenshot_svc: MagicMock,
    ) -> None:
        """Should deliver the saved path to the channel."""
        await toolset.share_terminal_output(output="x", caption="term deliver")
        screenshot_svc.deliver.assert_awaited_once()
        call_args = screenshot_svc.deliver.call_args[0]
        assert call_args[2] == "term deliver"

    @pytest.mark.asyncio
    async def test_returns_path_string(
        self,
        toolset: VisualFeedbackToolset,
    ) -> None:
        """Should return the string representation of the saved path."""
        result = await toolset.share_terminal_output(output="y", caption="c")
        assert result == str(Path("/fake/.owlbear/screenshots/12345_shot.png"))

    @pytest.mark.asyncio
    async def test_save_name_is_terminal(
        self,
        toolset: VisualFeedbackToolset,
        screenshot_svc: MagicMock,
    ) -> None:
        """save() name arg should be 'terminal'."""
        await toolset.share_terminal_output(output="z", caption="n")
        name_arg = screenshot_svc.save.call_args[0][1]
        assert name_arg == "terminal"
