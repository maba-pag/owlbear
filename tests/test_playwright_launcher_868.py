"""Failing tests for Playwright launcher + SSO extension discovery (task #868).

Covers: SSO extension discovery (filesystem path resolution, env-override,
version-subfolder enumeration), Playwright args security constraints (CDP-dead,
no 0.0.0.0), and PlaywrightLauncher lifecycle (launch, close, context manager,
page property).

All tests fail on current HEAD because
``owlbear_browser.playwright_launcher`` does not yet exist.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from owlbear_browser.playwright_launcher import (
    PlaywrightLauncher,
    SSOExtensionNotFoundError,
    build_playwright_args,
    find_sso_extension,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MODULE = "owlbear_browser.playwright_launcher"
_SSO_EXT_ID = "ppnbnpeolgkicgegkbkbjmhlideopiji"
_FAKE_EXT_PATH = Path(r"C:\fake\Local\Google\Chrome\User Data\Default\Extensions") / _SSO_EXT_ID
_FAKE_PROFILE_DIR = r"C:\fake\owlbear\profile"

# Relative path from LOCALAPPDATA to the SSO extension root directory.
_EXT_REL = Path("Google") / "Chrome" / "User Data" / "Default" / "Extensions" / _SSO_EXT_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_playwright() -> MagicMock:
    """Return a mock playwright object with chromium and context stubs."""
    pw = MagicMock()
    context = MagicMock()
    page = MagicMock()
    context.pages = [page]
    context.close = AsyncMock()
    pw.chromium.launch_persistent_context = AsyncMock(return_value=context)
    pw.stop = MagicMock()
    return pw


def _patch_async_playwright(pw: MagicMock) -> Any:  # noqa: ANN401
    """Patch async_playwright() to return ``pw`` inside a context manager."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=pw)
    cm.__aexit__ = AsyncMock(return_value=None)
    return patch(f"{_MODULE}.async_playwright", return_value=cm)


# ---------------------------------------------------------------------------
# TestFromAC_SSOExtensionDiscovery  (AC2)
# ---------------------------------------------------------------------------


class TestFromAC_SSOExtensionDiscovery:  # noqa: N801
    """SSO extension path discovery — filesystem resolution and env-override."""

    def test_returns_versioned_path_when_extension_dir_has_version_subfolder(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns a versioned subfolder path when the extension dir contains a version dir."""
        ext_root = tmp_path / _EXT_REL
        version_dir = ext_root / "1.2.3_0"
        version_dir.mkdir(parents=True)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        monkeypatch.delenv("SSO_EXTENSION_PATH", raising=False)

        result = find_sso_extension()

        assert result == version_dir

    def test_raises_when_extension_dir_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """SSOExtensionNotFoundError raised when the extension root directory does not exist."""
        # LOCALAPPDATA points to tmp_path but no extension dir is created
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        monkeypatch.delenv("SSO_EXTENSION_PATH", raising=False)

        with pytest.raises(SSOExtensionNotFoundError):
            find_sso_extension()

    def test_raises_when_extension_dir_has_no_version_subfolders(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SSOExtensionNotFoundError raised when the extension root exists but is empty."""
        ext_root = tmp_path / _EXT_REL
        ext_root.mkdir(parents=True)  # exists but no version subdirs
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        monkeypatch.delenv("SSO_EXTENSION_PATH", raising=False)

        with pytest.raises(SSOExtensionNotFoundError):
            find_sso_extension()

    def test_env_var_override_returns_given_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """SSO_EXTENSION_PATH env var is respected and returned without filesystem discovery."""
        override = tmp_path / "custom_sso_ext"
        override.mkdir()
        monkeypatch.setenv("SSO_EXTENSION_PATH", str(override))

        result = find_sso_extension()

        assert result == override

    def test_env_var_override_raises_when_path_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """SSOExtensionNotFoundError raised when SSO_EXTENSION_PATH points to a non-existent path."""
        missing = tmp_path / "nonexistent_ext"
        # Do NOT create the directory
        monkeypatch.setenv("SSO_EXTENSION_PATH", str(missing))

        with pytest.raises(SSOExtensionNotFoundError):
            find_sso_extension()

    def test_multiple_version_subfolders_returns_a_valid_version_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns one of the versioned subdirectory paths when multiple versions are present."""
        ext_root = tmp_path / _EXT_REL
        for ver in ("1.0.0_0", "1.1.0_0", "1.2.0_0"):
            (ext_root / ver).mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        monkeypatch.delenv("SSO_EXTENSION_PATH", raising=False)

        result = find_sso_extension()

        assert result.parent == ext_root
        assert result.is_dir()


# ---------------------------------------------------------------------------
# TestFromAC_PlaywrightArgs  (AC3)
# ---------------------------------------------------------------------------


class TestFromAC_PlaywrightArgs:  # noqa: N801
    """Playwright launch args — extension loading and security constraints."""

    def test_includes_disable_extensions_except_flag(self) -> None:
        """--disable-extensions-except={path} is present in the args list."""
        ext_path = Path(r"C:\ext\sso")
        args = build_playwright_args(ext_path)
        assert any(f"--disable-extensions-except={ext_path}" in a for a in args)

    def test_includes_load_extension_flag(self) -> None:
        """--load-extension={path} is present in the args list."""
        ext_path = Path(r"C:\ext\sso")
        args = build_playwright_args(ext_path)
        assert any(f"--load-extension={ext_path}" in a for a in args)

    def test_never_includes_remote_debugging_port(self) -> None:
        """--remote-debugging-port must not appear — CDP approach is dead."""
        ext_path = Path(r"C:\ext\sso")
        args = build_playwright_args(ext_path)
        for arg in args:
            assert "--remote-debugging-port" not in arg, f"CDP arg must not appear in Playwright args: {arg}"

    def test_never_includes_0_0_0_0(self) -> None:
        """No arg binds to 0.0.0.0 — security constraint (open network binding)."""
        ext_path = Path(r"C:\ext\sso")
        args = build_playwright_args(ext_path)
        for arg in args:
            assert "0.0.0.0" not in arg, f"Found 0.0.0.0 binding in arg: {arg}"  # noqa: S104


# ---------------------------------------------------------------------------
# TestFromAC_PlaywrightLauncherLifecycle  (AC4)
# ---------------------------------------------------------------------------


class TestFromAC_PlaywrightLauncherLifecycle:  # noqa: N801
    """PlaywrightLauncher lifecycle — launch, close, context manager, page."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_launch_calls_launch_persistent_context(self) -> None:
        """launch() calls playwright.chromium.launch_persistent_context()."""
        pw = _make_mock_playwright()
        ext_path = Path(r"C:\ext\sso")
        launcher = PlaywrightLauncher(sso_ext_path=ext_path, user_data_dir=_FAKE_PROFILE_DIR)

        with _patch_async_playwright(pw):
            await launcher.launch()

        pw.chromium.launch_persistent_context.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_launch_passes_user_data_dir_to_context(self) -> None:
        """launch() passes user_data_dir as the first positional or keyword arg."""
        pw = _make_mock_playwright()
        ext_path = Path(r"C:\ext\sso")
        launcher = PlaywrightLauncher(sso_ext_path=ext_path, user_data_dir=_FAKE_PROFILE_DIR)

        with _patch_async_playwright(pw):
            await launcher.launch()

        call_kwargs = pw.chromium.launch_persistent_context.call_args
        # user_data_dir may be positional or keyword
        positional = call_kwargs[0] or ()
        keyword = call_kwargs[1] or {}
        all_args = list(positional) + list(keyword.values())
        assert any(_FAKE_PROFILE_DIR in str(a) for a in all_args), (
            f"user_data_dir={_FAKE_PROFILE_DIR!r} not found in launch call: {call_kwargs}"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_close_calls_context_close(self) -> None:
        """close() calls context.close() on the persistent context."""
        pw = _make_mock_playwright()
        ext_path = Path(r"C:\ext\sso")
        launcher = PlaywrightLauncher(sso_ext_path=ext_path, user_data_dir=_FAKE_PROFILE_DIR)

        with _patch_async_playwright(pw):
            await launcher.launch()
            await launcher.close()

        pw.chromium.launch_persistent_context.return_value.close.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_close_calls_playwright_stop(self) -> None:
        """close() calls playwright.stop() to release the Playwright instance."""
        pw = _make_mock_playwright()
        ext_path = Path(r"C:\ext\sso")
        launcher = PlaywrightLauncher(sso_ext_path=ext_path, user_data_dir=_FAKE_PROFILE_DIR)

        with _patch_async_playwright(pw):
            await launcher.launch()
            await launcher.close()

        pw.stop.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_context_manager_delegates_to_launch_and_close(self) -> None:
        """async with PlaywrightLauncher(...) calls launch on enter and close on exit."""
        pw = _make_mock_playwright()
        ext_path = Path(r"C:\ext\sso")
        launcher = PlaywrightLauncher(sso_ext_path=ext_path, user_data_dir=_FAKE_PROFILE_DIR)

        with _patch_async_playwright(pw):
            async with launcher:
                # launch must have been called at this point
                pw.chromium.launch_persistent_context.assert_called_once()

        # close must have been called on exit
        pw.chromium.launch_persistent_context.return_value.close.assert_called_once()
        pw.stop.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_page_property_returns_first_context_page(self) -> None:
        """page property returns the first page from the persistent context."""
        pw = _make_mock_playwright()
        ext_path = Path(r"C:\ext\sso")
        launcher = PlaywrightLauncher(sso_ext_path=ext_path, user_data_dir=_FAKE_PROFILE_DIR)
        expected_page = pw.chromium.launch_persistent_context.return_value.pages[0]

        with _patch_async_playwright(pw):
            await launcher.launch()
            result = launcher.page

        assert result is expected_page
