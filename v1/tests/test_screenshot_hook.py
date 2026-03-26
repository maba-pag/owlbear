"""Tests for owlbear.tools.screenshot_hook — ScreenshotOnErrorHook."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.tools.screenshot_hook import ScreenshotOnErrorHook

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def screenshot_svc() -> MagicMock:
    """Mock ScreenshotService."""
    svc = MagicMock()
    svc.save.return_value = Path("/fake/.owlbear/screenshots/err_shot.png")
    svc.capture_browser = AsyncMock(return_value=b"\x89PNGerror")
    return svc


@pytest.fixture
def browser_toolset() -> MagicMock:
    """Mock BrowserToolset with an active page."""
    bt = MagicMock()
    bt.page = AsyncMock()  # has a .page property
    return bt


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def hook(
    screenshot_svc: MagicMock,
    browser_toolset: MagicMock,
    workspace: Path,
) -> ScreenshotOnErrorHook:
    return ScreenshotOnErrorHook(
        screenshot_service=screenshot_svc,
        browser_toolset=browser_toolset,
        workspace=workspace,
        screenshot_mode="on_error",
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    """ScreenshotOnErrorHook registers on ON_ERROR."""

    def test_register_adds_handler(self, hook: ScreenshotOnErrorHook) -> None:
        """register() adds the hook handler to the ON_ERROR event."""
        registry = HookRegistry()
        hook.register(registry)
        handlers = registry.handlers.get(HookEvent.ON_ERROR, [])
        assert len(handlers) == 1

    def test_unregister_removes_handler(self, hook: ScreenshotOnErrorHook) -> None:
        """unregister() removes the hook handler from ON_ERROR."""
        registry = HookRegistry()
        hook.register(registry)
        hook.unregister(registry)
        handlers = registry.handlers.get(HookEvent.ON_ERROR, [])
        assert len(handlers) == 0


# ---------------------------------------------------------------------------
# ON_ERROR behaviour
# ---------------------------------------------------------------------------


class TestOnError:
    """Hook captures screenshot on error when browser is available."""

    @pytest.mark.asyncio
    async def test_captures_browser_screenshot(
        self,
        hook: ScreenshotOnErrorHook,
        screenshot_svc: MagicMock,
        browser_toolset: MagicMock,
    ) -> None:
        """Should call capture_browser with the browser page."""
        await hook.handle({"error": "something broke"})
        screenshot_svc.capture_browser.assert_awaited_once_with(browser_toolset.page)

    @pytest.mark.asyncio
    async def test_saves_error_screenshot(
        self,
        hook: ScreenshotOnErrorHook,
        screenshot_svc: MagicMock,
        workspace: Path,
    ) -> None:
        """Should save the captured bytes with 'error' name."""
        await hook.handle({"error": "fail"})
        screenshot_svc.save.assert_called_once()
        args = screenshot_svc.save.call_args[0]
        assert args[0] == b"\x89PNGerror"
        assert args[1] == "error"
        assert args[2] == workspace

    @pytest.mark.asyncio
    async def test_noop_when_browser_none(
        self,
        screenshot_svc: MagicMock,
        workspace: Path,
    ) -> None:
        """Should do nothing when browser_toolset is None."""
        hook = ScreenshotOnErrorHook(
            screenshot_service=screenshot_svc,
            browser_toolset=None,
            workspace=workspace,
            screenshot_mode="on_error",
        )
        await hook.handle({"error": "no browser"})
        screenshot_svc.capture_browser.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_noop_when_page_raises(
        self,
        screenshot_svc: MagicMock,
        workspace: Path,
    ) -> None:
        """Should swallow exception when accessing page raises RuntimeError."""
        bt = MagicMock()
        type(bt).page = property(lambda _self: (_ for _ in ()).throw(RuntimeError("not set up")))
        hook = ScreenshotOnErrorHook(
            screenshot_service=screenshot_svc,
            browser_toolset=bt,
            workspace=workspace,
            screenshot_mode="on_error",
        )
        # Should not raise
        await hook.handle({"error": "bad page"})
        screenshot_svc.capture_browser.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_noop_when_mode_manual(
        self,
        screenshot_svc: MagicMock,
        browser_toolset: MagicMock,
        workspace: Path,
    ) -> None:
        """Should skip capture when screenshot_mode is 'manual'."""
        hook = ScreenshotOnErrorHook(
            screenshot_service=screenshot_svc,
            browser_toolset=browser_toolset,
            workspace=workspace,
            screenshot_mode="manual",
        )
        await hook.handle({"error": "manual mode"})
        screenshot_svc.capture_browser.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_captures_when_mode_auto(
        self,
        screenshot_svc: MagicMock,
        browser_toolset: MagicMock,
        workspace: Path,
    ) -> None:
        """Should capture when screenshot_mode is 'auto'."""
        hook = ScreenshotOnErrorHook(
            screenshot_service=screenshot_svc,
            browser_toolset=browser_toolset,
            workspace=workspace,
            screenshot_mode="auto",
        )
        await hook.handle({"error": "auto mode"})
        screenshot_svc.capture_browser.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_captures_when_mode_on_error(
        self,
        hook: ScreenshotOnErrorHook,
        screenshot_svc: MagicMock,
    ) -> None:
        """Should capture when screenshot_mode is 'on_error' (default)."""
        await hook.handle({"error": "on_error mode"})
        screenshot_svc.capture_browser.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_swallows_capture_exception(
        self,
        screenshot_svc: MagicMock,
        browser_toolset: MagicMock,
        workspace: Path,
    ) -> None:
        """Exceptions during capture should be logged, not raised."""
        screenshot_svc.capture_browser = AsyncMock(side_effect=RuntimeError("boom"))
        hook = ScreenshotOnErrorHook(
            screenshot_service=screenshot_svc,
            browser_toolset=browser_toolset,
            workspace=workspace,
            screenshot_mode="on_error",
        )
        # Should not raise
        await hook.handle({"error": "capture fails"})


# ---------------------------------------------------------------------------
# Integration with HookRegistry.emit
# ---------------------------------------------------------------------------


class TestEmitIntegration:
    """Hook works when dispatched via HookRegistry.emit."""

    @pytest.mark.asyncio
    async def test_emit_triggers_capture(
        self,
        hook: ScreenshotOnErrorHook,
        screenshot_svc: MagicMock,
    ) -> None:
        """Emitting ON_ERROR via registry should trigger screenshot capture."""
        registry = HookRegistry()
        hook.register(registry)
        await registry.emit(HookEvent.ON_ERROR, {"error": "emit test"})
        screenshot_svc.capture_browser.assert_awaited_once()
