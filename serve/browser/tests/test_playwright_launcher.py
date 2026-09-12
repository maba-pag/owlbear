"""Focused launcher mechanics for managed Edge and preserved Chromium."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_browser import (
    BrowserMode,
    ManagedEdgeUnavailableError,
    ManagedProfileInUseError,
    PlaywrightLauncher,
)
from owlbear_browser import playwright_launcher as launcher_module


class _FakeContext:
    def __init__(self) -> None:
        self.pages: list[object] = []
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class _FakeBrowserType:
    def __init__(self, context: _FakeContext, error: Exception | None = None) -> None:
        self.context = context
        self.error = error
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def launch_persistent_context(self, user_data_dir: str, **kwargs: object) -> _FakeContext:
        self.calls.append((user_data_dir, kwargs))
        if self.error is not None:
            raise self.error
        return self.context


class _FakePlaywright:
    def __init__(self, browser_type: _FakeBrowserType) -> None:
        self.chromium = browser_type
        self.stopped = False

    async def stop(self) -> None:
        self.stopped = True


class _FakePlaywrightManager:
    def __init__(self, playwright: _FakePlaywright) -> None:
        self.playwright = playwright

    async def __aenter__(self) -> _FakePlaywright:
        return self.playwright

    async def __aexit__(self, *_: object) -> None:
        return None


@pytest.mark.asyncio
async def test_managed_edge_uses_owned_profile_and_stable_edge() -> None:
    context = _FakeContext()
    browser_type = _FakeBrowserType(context)
    playwright = _FakePlaywright(browser_type)
    profile = Path("edge-profile")
    launcher = PlaywrightLauncher(
        user_data_dir=str(profile),
        mode=BrowserMode.MANAGED_EDGE,
        headless=True,
    )

    with (
        patch.object(launcher_module, "async_playwright", return_value=_FakePlaywrightManager(playwright)),
        patch.object(launcher_module, "find_sso_extension", side_effect=AssertionError("extension lookup")),
    ):
        await launcher.launch()

    assert browser_type.calls == [
        (
            str(profile),
            {"headless": False, "channel": "msedge", "chromium_sandbox": True},
        )
    ]
    assert launcher.capabilities.mode is BrowserMode.MANAGED_EDGE
    assert launcher.capabilities.owned_persistent_profile is True
    assert launcher.capabilities.visible_manual_auth is True

    await launcher.close()
    assert context.closed is True
    assert playwright.stopped is True
    assert launcher.capabilities.owned_persistent_profile is False
    assert launcher.capabilities.visible_manual_auth is False


@pytest.mark.asyncio
async def test_chromium_retains_extension_arguments_when_configured() -> None:
    context = _FakeContext()
    browser_type = _FakeBrowserType(context)
    playwright = _FakePlaywright(browser_type)
    extension = Path("sso-extension")
    launcher = PlaywrightLauncher(sso_ext_path=extension, mode=BrowserMode.CHROMIUM, headless=True)

    with patch.object(launcher_module, "async_playwright", return_value=_FakePlaywrightManager(playwright)):
        await launcher.launch()

    assert browser_type.calls == [
        (
            launcher._user_data_dir,  # noqa: SLF001
            {
                "headless": True,
                "args": [
                    f"--disable-extensions-except={extension}",
                    f"--load-extension={extension}",
                ],
            },
        )
    ]
    assert launcher.capabilities.mode is BrowserMode.CHROMIUM
    assert launcher.capabilities.owned_persistent_profile is True
    assert launcher.capabilities.visible_manual_auth is False
    await launcher.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            Exception("Chromium distribution 'msedge' is not found at /Applications/Microsoft Edge.app"),
            ManagedEdgeUnavailableError,
        ),
        (
            Exception(
                "Failed to create a ProcessSingleton for your profile directory. "
                "This usually means that the profile is already in use by another instance of Chromium."
            ),
            ManagedProfileInUseError,
        ),
        (
            Exception(
                "Opening in existing browser session. "
                "This usually means that the profile is already in use by another instance of Chromium."
            ),
            ManagedProfileInUseError,
        ),
    ],
)
async def test_managed_edge_failures_are_typed_without_chromium_fallback(
    error: Exception, expected: type[Exception]
) -> None:
    context = _FakeContext()
    browser_type = _FakeBrowserType(context, error=error)
    playwright = _FakePlaywright(browser_type)
    launcher = PlaywrightLauncher(mode=BrowserMode.MANAGED_EDGE)

    with (
        patch.object(launcher_module, "async_playwright", return_value=_FakePlaywrightManager(playwright)),
        pytest.raises(expected),
    ):
        await launcher.launch()

    assert len(browser_type.calls) == 1
    assert playwright.stopped is True
    assert launcher.capabilities.owned_persistent_profile is False
