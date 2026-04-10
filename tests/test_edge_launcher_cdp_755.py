"""Failing tests for Edge launcher + CDP connection manager (task #755).

Covers: Edge binary discovery (Windows path resolution), CDP launch args
security constraints (port, allow-origins, user-data-dir, Chrome 136),
connection lifecycle (connect, disconnect, reconnect, timeout), and
SSO login redirect detection (fail-fast AuthenticationRequired).

All tests fail on current HEAD because ``serve/browser/`` (``owlbear_browser``)
does not yet exist.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from owlbear_browser.launcher import (
    EdgeNotFoundError,
    build_launch_args,
    find_edge_binary,
)
from owlbear_browser.cdp import (
    AuthenticationRequired,
    CDPConnectionError,
    CDPConnectionManager,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LAUNCHER_MODULE = "owlbear_browser.launcher"
_CDP_MODULE = "owlbear_browser.cdp"

_EDGE_X86_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
_EDGE_PF_PATH = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
_DEFAULT_PORT = 9222
_IDP_URL = "https://login.microsoftonline.com/some/path"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_path_exists(path_str: str, *, found: bool) -> Any:  # noqa: ANN401
    """Patch pathlib.Path.exists for a specific path string."""
    original_exists = __import__("pathlib").Path.exists

    def _exists(self: Any) -> bool:  # noqa: ANN401
        if str(self) == path_str:
            return found
        return original_exists(self)

    return patch(f"{_LAUNCHER_MODULE}.Path.exists", side_effect=_exists)


def _patch_both_paths_missing() -> Any:  # noqa: ANN401
    return patch(f"{_LAUNCHER_MODULE}.Path.exists", return_value=False)


def _make_mock_browser() -> MagicMock:
    """Return a mock Playwright Browser object."""
    browser = MagicMock()
    context = MagicMock()
    page = MagicMock()
    page.url = "https://internal.company.com/page"
    page.query_selector = MagicMock(return_value=None)
    context.new_page = AsyncMock(return_value=page)
    context.pages = [page]
    browser.contexts = [context]
    browser.close = AsyncMock()
    return browser


def _patch_connect_over_cdp(browser: MagicMock) -> Any:  # noqa: ANN401
    return patch(f"{_CDP_MODULE}.playwright_connect_over_cdp", new=AsyncMock(return_value=browser))


# ---------------------------------------------------------------------------
# TestFromAC_EdgeDiscovery
# ---------------------------------------------------------------------------


class TestFromAC_EdgeDiscovery:  # noqa: N801
    """Edge binary discovery — Windows path resolution and env override."""

    def test_finds_edge_at_standard_x86_path(self) -> None:
        """Primary Windows install path is checked first and returned when found."""
        with patch(f"{_LAUNCHER_MODULE}.Path.exists", side_effect=lambda self=None: str(self) == _EDGE_X86_PATH):
            result = find_edge_binary()
        assert str(result) == _EDGE_X86_PATH

    def test_finds_edge_at_program_files_path_when_x86_missing(self) -> None:
        """Falls back to Program Files path when x86 path is absent."""
        def _exists(self: Any = None) -> bool:  # noqa: ANN401
            p = str(self)
            if p == _EDGE_X86_PATH:
                return False
            return p == _EDGE_PF_PATH

        with patch(f"{_LAUNCHER_MODULE}.Path.exists", side_effect=_exists):
            result = find_edge_binary()
        assert str(result) == _EDGE_PF_PATH

    def test_env_var_override_takes_priority(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """EDGE_PATH env var is respected and returned without checking default paths."""
        custom = r"D:\custom\msedge.exe"
        monkeypatch.setenv("EDGE_PATH", custom)
        with patch(f"{_LAUNCHER_MODULE}.Path.exists", return_value=True):
            result = find_edge_binary()
        assert str(result) == custom

    def test_raises_edge_not_found_error_when_no_binary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """EdgeNotFoundError raised when no binary found and EDGE_PATH is not set."""
        monkeypatch.delenv("EDGE_PATH", raising=False)
        with _patch_both_paths_missing(), pytest.raises(EdgeNotFoundError):
            find_edge_binary()

    def test_env_var_path_does_not_exist_raises_edge_not_found_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """EdgeNotFoundError raised when EDGE_PATH points to a non-existent file."""
        monkeypatch.setenv("EDGE_PATH", r"D:\nonexistent\msedge.exe")
        with patch(f"{_LAUNCHER_MODULE}.Path.exists", return_value=False), pytest.raises(EdgeNotFoundError):
            find_edge_binary()


# ---------------------------------------------------------------------------
# TestFromAC_CDPLaunchArgs
# ---------------------------------------------------------------------------


class TestFromAC_CDPLaunchArgs:  # noqa: N801
    """CDP launch args — security-critical requirements for Chrome 136 / Edge CDP."""

    def test_remote_debugging_port_arg_present(self) -> None:
        """--remote-debugging-port argument is always included."""
        args = build_launch_args(port=_DEFAULT_PORT, user_data_dir=r"C:\tmp\edge-profile")
        arg_str = " ".join(args)
        assert "--remote-debugging-port" in arg_str

    def test_remote_debugging_port_defaults_to_9222(self) -> None:
        """Default port is 9222."""
        args = build_launch_args(user_data_dir=r"C:\tmp\edge-profile")
        assert any(f"--remote-debugging-port={_DEFAULT_PORT}" in a for a in args)

    def test_remote_allow_origins_is_localhost_only(self) -> None:
        """--remote-allow-origins uses 127.0.0.1 only — no public or network hosts."""
        args = build_launch_args(port=_DEFAULT_PORT, user_data_dir=r"C:\tmp\edge-profile")
        origins_args = [a for a in args if "--remote-allow-origins" in a]
        assert len(origins_args) >= 1
        for arg in origins_args:
            assert "127.0.0.1" in arg

    def test_remote_allow_origins_never_wildcard(self) -> None:
        """Wildcard (*) must never appear in --remote-allow-origins (security: HR#4)."""
        args = build_launch_args(port=_DEFAULT_PORT, user_data_dir=r"C:\tmp\edge-profile")
        for arg in args:
            if "--remote-allow-origins" in arg:
                assert "*" not in arg, "--remote-allow-origins must never use wildcard"

    def test_user_data_dir_present(self) -> None:
        """--user-data-dir is mandatory (Chrome 136 requirement)."""
        args = build_launch_args(port=_DEFAULT_PORT, user_data_dir=r"C:\tmp\edge-profile")
        assert any("--user-data-dir" in a for a in args)

    def test_no_0_0_0_0_binding_in_args(self) -> None:
        """No arg binds to 0.0.0.0 — localhost only (security: HR#4)."""
        args = build_launch_args(port=_DEFAULT_PORT, user_data_dir=r"C:\tmp\edge-profile")
        for arg in args:
            assert "0.0.0.0" not in arg, f"Found 0.0.0.0 binding in arg: {arg}"  # noqa: S104


# ---------------------------------------------------------------------------
# TestFromAC_ConnectionLifecycle
# ---------------------------------------------------------------------------


class TestFromAC_ConnectionLifecycle:  # noqa: N801
    """CDP connection lifecycle — connect, disconnect, reconnect, timeout."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_connect_returns_connected_manager(self) -> None:
        """connect() returns an active CDPConnectionManager."""
        browser = _make_mock_browser()
        with _patch_connect_over_cdp(browser):
            manager = CDPConnectionManager(port=_DEFAULT_PORT)
            await manager.connect()
            assert manager.is_connected

    @pytest.mark.asyncio(loop_scope="function")
    async def test_connect_uses_localhost_endpoint(self) -> None:
        """connect() calls the CDP endpoint on 127.0.0.1, not 0.0.0.0 or hostname."""
        browser = _make_mock_browser()
        with _patch_connect_over_cdp(browser) as mock_connect:
            manager = CDPConnectionManager(port=_DEFAULT_PORT)
            await manager.connect()
            call_args = mock_connect.call_args
            endpoint = call_args[0][0] if call_args[0] else call_args[1].get("endpoint_url", "")
            assert "127.0.0.1" in endpoint

    @pytest.mark.asyncio(loop_scope="function")
    async def test_disconnect_closes_browser(self) -> None:
        """disconnect() closes the browser and marks manager as disconnected."""
        browser = _make_mock_browser()
        with _patch_connect_over_cdp(browser):
            manager = CDPConnectionManager(port=_DEFAULT_PORT)
            await manager.connect()
            await manager.disconnect()
        browser.close.assert_called_once()
        assert not manager.is_connected

    @pytest.mark.asyncio(loop_scope="function")
    async def test_reconnect_after_disconnect(self) -> None:
        """connect() succeeds after a previous disconnect."""
        browser = _make_mock_browser()
        with _patch_connect_over_cdp(browser):
            manager = CDPConnectionManager(port=_DEFAULT_PORT)
            await manager.connect()
            await manager.disconnect()
            await manager.connect()
            assert manager.is_connected

    @pytest.mark.asyncio(loop_scope="function")
    async def test_connect_timeout_raises_cdp_connection_error(self) -> None:
        """CDPConnectionError raised when connect_over_cdp times out."""
        with patch(
            f"{_CDP_MODULE}.playwright_connect_over_cdp",
            new=AsyncMock(side_effect=asyncio.TimeoutError),
        ):
            manager = CDPConnectionManager(port=_DEFAULT_PORT)
            with pytest.raises(CDPConnectionError):
                await manager.connect()


# ---------------------------------------------------------------------------
# TestFromAC_SSODetection
# ---------------------------------------------------------------------------


class TestFromAC_SSODetection:  # noqa: N801
    """SSO login redirect detection — fail-fast AuthenticationRequired on IdP redirect."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_idp_url_redirect_raises_authentication_required(self) -> None:
        """AuthenticationRequired raised when page URL matches an IdP domain."""
        browser = _make_mock_browser()
        page = browser.contexts[0].pages[0]
        page.url = _IDP_URL  # Redirected to Microsoft IdP

        with _patch_connect_over_cdp(browser):
            manager = CDPConnectionManager(port=_DEFAULT_PORT)
            await manager.connect()
            with pytest.raises(AuthenticationRequired):
                await manager.check_sso_redirect(page)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_login_form_raises_authentication_required(self) -> None:
        """AuthenticationRequired raised when a password input field is present."""
        browser = _make_mock_browser()
        page = browser.contexts[0].pages[0]
        page.url = "https://internal.company.com/page"
        # Simulate login form present
        page.query_selector = MagicMock(return_value=MagicMock())  # password field found

        with _patch_connect_over_cdp(browser):
            manager = CDPConnectionManager(port=_DEFAULT_PORT)
            await manager.connect()
            with pytest.raises(AuthenticationRequired):
                await manager.check_sso_redirect(page)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fail_fast_authentication_required_propagates(self) -> None:
        """AuthenticationRequired propagates to caller without suppression."""
        browser = _make_mock_browser()
        page = browser.contexts[0].pages[0]
        page.url = _IDP_URL

        with _patch_connect_over_cdp(browser):
            manager = CDPConnectionManager(port=_DEFAULT_PORT)
            await manager.connect()
            raised = False
            try:
                await manager.check_sso_redirect(page)
            except AuthenticationRequired:
                raised = True
            assert raised, "AuthenticationRequired must not be swallowed"

    def test_authentication_required_is_exception_subclass(self) -> None:
        """AuthenticationRequired is a proper exception type (subclass of Exception)."""
        assert issubclass(AuthenticationRequired, Exception)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_no_auth_required_on_normal_page(self) -> None:
        """No exception raised when page URL is normal and no login form is present."""
        browser = _make_mock_browser()
        page = browser.contexts[0].pages[0]
        page.url = "https://internal.company.com/normal-page"
        page.query_selector = MagicMock(return_value=None)  # no password field

        with _patch_connect_over_cdp(browser):
            manager = CDPConnectionManager(port=_DEFAULT_PORT)
            await manager.connect()
            # Should not raise
            await manager.check_sso_redirect(page)
