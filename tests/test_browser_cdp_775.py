"""Tests for task #782: owlbear_browser package scaffold and CDP launcher.

Covers:
  AC1 - import owlbear_browser succeeds; EdgeCDPLauncher accessible from package
  AC2 - CDP launcher class (EdgeCDPLauncher) exists with async launch(), connect(), close()
  AC3 - Edge binary path resolution (Windows) via EdgeCDPLauncher

AC4 (constraint): all tests use mocked subprocess/CDP — no real browser launched.

All tests must be in the RED (failing) phase until the builder confirms the green pass.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EDGE_LAUNCHER_MODULE = "owlbear_browser.edge_launcher"
_CDP_MODULE = "owlbear_browser.cdp"

_FAKE_BINARY = r"C:\edge\msedge.exe"
_DEFAULT_PORT = 9222
_CUSTOM_PORT = 1234


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_mock_process() -> MagicMock:
    """Return a mock subprocess.Popen-like object."""
    proc = MagicMock()
    proc.pid = 42000
    proc.returncode = None
    proc.terminate = MagicMock()
    proc.kill = MagicMock()
    proc.wait = MagicMock(return_value=0)
    return proc


def _make_mock_manager() -> MagicMock:
    """Return a mock CDPConnectionManager instance with async connect/disconnect."""
    mgr = MagicMock()
    mgr.connect = AsyncMock()
    mgr.disconnect = AsyncMock()
    return mgr



# ---------------------------------------------------------------------------
# TestFromAC_PackageImport  (AC1)
# ---------------------------------------------------------------------------


class TestFromAC_PackageImport:  # noqa: N801
    """AC1: import owlbear_browser succeeds; EdgeCDPLauncher is accessible from the package."""

    def test_import_owlbear_browser_succeeds(self) -> None:
        """Top-level owlbear_browser package is importable without error."""
        import owlbear_browser  # noqa: F401

    def test_edge_cdp_launcher_importable_from_package(self) -> None:
        """EdgeCDPLauncher is importable via `from owlbear_browser import EdgeCDPLauncher`."""
        from owlbear_browser import EdgeCDPLauncher  # noqa: F401

    def test_edge_cdp_launcher_in_package_all(self) -> None:
        """'EdgeCDPLauncher' appears in owlbear_browser.__all__."""
        import owlbear_browser

        assert "EdgeCDPLauncher" in owlbear_browser.__all__


# ---------------------------------------------------------------------------
# TestFromAC_EdgeCDPLauncherInterface  (AC2)
# ---------------------------------------------------------------------------


class TestFromAC_EdgeCDPLauncherInterface:  # noqa: N801
    """AC2: EdgeCDPLauncher class with async launch(), connect(), close() methods."""

    def test_launcher_class_importable_from_edge_launcher_module(self) -> None:
        """EdgeCDPLauncher is importable from owlbear_browser.edge_launcher."""
        from owlbear_browser.edge_launcher import EdgeCDPLauncher  # noqa: F401

    def test_launch_is_coroutine_function(self) -> None:
        """EdgeCDPLauncher.launch is an async coroutine function."""
        from owlbear_browser.edge_launcher import EdgeCDPLauncher

        assert asyncio.iscoroutinefunction(EdgeCDPLauncher.launch)

    def test_connect_is_coroutine_function(self) -> None:
        """EdgeCDPLauncher.connect is an async coroutine function."""
        from owlbear_browser.edge_launcher import EdgeCDPLauncher

        assert asyncio.iscoroutinefunction(EdgeCDPLauncher.connect)

    def test_close_is_coroutine_function(self) -> None:
        """EdgeCDPLauncher.close is an async coroutine function."""
        from owlbear_browser.edge_launcher import EdgeCDPLauncher

        assert asyncio.iscoroutinefunction(EdgeCDPLauncher.close)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_launch_calls_subprocess_popen(self) -> None:
        """launch() spawns an Edge subprocess via subprocess.Popen."""
        from owlbear_browser.edge_launcher import EdgeCDPLauncher

        proc = _make_mock_process()
        mgr_instance = _make_mock_manager()
        mgr_class = MagicMock(return_value=mgr_instance)

        with (
            patch(f"{_EDGE_LAUNCHER_MODULE}.Path.exists", return_value=True),
            patch(
                f"{_EDGE_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc
            ) as mock_popen,
            patch(f"{_EDGE_LAUNCHER_MODULE}.build_launch_args", return_value=[]),
            patch(f"{_CDP_MODULE}.CDPConnectionManager", mgr_class),
        ):
            launcher = EdgeCDPLauncher(binary_path=_FAKE_BINARY)
            await launcher.launch()

        mock_popen.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_connect_after_launch_delegates_to_manager_connect(self) -> None:
        """connect() after launch() calls CDPConnectionManager.connect() exactly once."""
        from owlbear_browser.edge_launcher import EdgeCDPLauncher

        proc = _make_mock_process()
        mgr_instance = _make_mock_manager()
        mgr_class = MagicMock(return_value=mgr_instance)

        with (
            patch(f"{_EDGE_LAUNCHER_MODULE}.Path.exists", return_value=True),
            patch(f"{_EDGE_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc),
            patch(f"{_EDGE_LAUNCHER_MODULE}.build_launch_args", return_value=[]),
            patch(f"{_CDP_MODULE}.CDPConnectionManager", mgr_class),
        ):
            launcher = EdgeCDPLauncher(binary_path=_FAKE_BINARY)
            await launcher.launch()
            await launcher.connect()

        mgr_instance.connect.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_close_after_launch_calls_disconnect_and_terminate(self) -> None:
        """close() calls manager.disconnect() and process.terminate() after a launch."""
        from owlbear_browser.edge_launcher import EdgeCDPLauncher

        proc = _make_mock_process()
        mgr_instance = _make_mock_manager()
        mgr_class = MagicMock(return_value=mgr_instance)

        with (
            patch(f"{_EDGE_LAUNCHER_MODULE}.Path.exists", return_value=True),
            patch(f"{_EDGE_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc),
            patch(f"{_EDGE_LAUNCHER_MODULE}.build_launch_args", return_value=[]),
            patch(f"{_CDP_MODULE}.CDPConnectionManager", mgr_class),
        ):
            launcher = EdgeCDPLauncher(binary_path=_FAKE_BINARY)
            await launcher.launch()
            await launcher.close()

        mgr_instance.disconnect.assert_called_once()
        proc.terminate.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_close_before_launch_is_silent_noop(self) -> None:
        """close() called before launch() does not raise any exception."""
        from owlbear_browser.edge_launcher import EdgeCDPLauncher

        launcher = EdgeCDPLauncher()
        await launcher.close()  # must not raise

    @pytest.mark.asyncio(loop_scope="function")
    async def test_connect_before_launch_is_silent_noop(self) -> None:
        """connect() called before launch() does not raise any exception."""
        from owlbear_browser.edge_launcher import EdgeCDPLauncher

        launcher = EdgeCDPLauncher()
        await launcher.connect()  # must not raise

    @pytest.mark.asyncio(loop_scope="function")
    async def test_close_kills_process_when_terminate_times_out(self) -> None:
        """close() must kill the process with SIGKILL when wait(timeout=5) times out.

        Defensive cleanup contract: a process that ignores SIGTERM within 5 seconds
        should be force-killed to prevent orphaned browser processes.
        """
        from owlbear_browser.edge_launcher import EdgeCDPLauncher

        proc = _make_mock_process()
        proc.wait.side_effect = subprocess.TimeoutExpired(cmd=_FAKE_BINARY, timeout=5)
        mgr_instance = _make_mock_manager()
        mgr_class = MagicMock(return_value=mgr_instance)

        with (
            patch(f"{_EDGE_LAUNCHER_MODULE}.Path.exists", return_value=True),
            patch(f"{_EDGE_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc),
            patch(f"{_EDGE_LAUNCHER_MODULE}.build_launch_args", return_value=[]),
            patch(f"{_CDP_MODULE}.CDPConnectionManager", mgr_class),
        ):
            launcher = EdgeCDPLauncher(binary_path=_FAKE_BINARY)
            await launcher.launch()
            await launcher.close()

        # FAILS: current close() suppresses TimeoutExpired without calling kill()
        proc.kill.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_close_is_idempotent(self) -> None:
        """Calling close() twice is safe — second call is a silent no-op."""
        from owlbear_browser.edge_launcher import EdgeCDPLauncher

        proc = _make_mock_process()
        mgr_instance = _make_mock_manager()
        mgr_class = MagicMock(return_value=mgr_instance)

        with (
            patch(f"{_EDGE_LAUNCHER_MODULE}.Path.exists", return_value=True),
            patch(f"{_EDGE_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc),
            patch(f"{_EDGE_LAUNCHER_MODULE}.build_launch_args", return_value=[]),
            patch(f"{_CDP_MODULE}.CDPConnectionManager", mgr_class),
        ):
            launcher = EdgeCDPLauncher(binary_path=_FAKE_BINARY)
            await launcher.launch()
            await launcher.close()
            await launcher.close()  # second call — must not raise


# ---------------------------------------------------------------------------
# TestFromAC_EdgeBinaryResolution  (AC3)
# ---------------------------------------------------------------------------


class TestFromAC_EdgeBinaryResolution:  # noqa: N801
    """AC3: Edge binary path resolution (Windows) through EdgeCDPLauncher."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_explicit_binary_path_passed_to_popen(self) -> None:
        """launch() uses the explicit binary_path as the first arg to subprocess.Popen."""
        from owlbear_browser.edge_launcher import EdgeCDPLauncher

        proc = _make_mock_process()
        mgr_instance = _make_mock_manager()
        mgr_class = MagicMock(return_value=mgr_instance)

        with (
            patch(f"{_EDGE_LAUNCHER_MODULE}.Path.exists", return_value=True),
            patch(
                f"{_EDGE_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc
            ) as mock_popen,
            patch(f"{_EDGE_LAUNCHER_MODULE}.build_launch_args", return_value=[]),
            patch(f"{_CDP_MODULE}.CDPConnectionManager", mgr_class),
        ):
            launcher = EdgeCDPLauncher(binary_path=_FAKE_BINARY)
            await launcher.launch()

        popen_cmd = mock_popen.call_args[0][0]
        assert popen_cmd[0] == str(Path(_FAKE_BINARY))

    @pytest.mark.asyncio(loop_scope="function")
    async def test_nonexistent_explicit_path_raises_file_not_found(self) -> None:
        """launch() raises FileNotFoundError when binary_path points to a missing file."""
        from owlbear_browser.edge_launcher import EdgeCDPLauncher

        with patch(f"{_EDGE_LAUNCHER_MODULE}.Path.exists", return_value=False):
            launcher = EdgeCDPLauncher(binary_path=_FAKE_BINARY)
            with pytest.raises(FileNotFoundError):
                await launcher.launch()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_none_binary_path_delegates_to_find_edge_binary(self) -> None:
        """launch() calls find_edge_binary() when binary_path=None."""
        from owlbear_browser.edge_launcher import EdgeCDPLauncher

        proc = _make_mock_process()
        resolved = Path(_FAKE_BINARY)
        mgr_instance = _make_mock_manager()
        mgr_class = MagicMock(return_value=mgr_instance)

        with (
            patch(
                f"{_EDGE_LAUNCHER_MODULE}.find_edge_binary", return_value=resolved
            ) as mock_find,
            patch(f"{_EDGE_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc),
            patch(f"{_EDGE_LAUNCHER_MODULE}.build_launch_args", return_value=[]),
            patch(f"{_CDP_MODULE}.CDPConnectionManager", mgr_class),
        ):
            launcher = EdgeCDPLauncher(binary_path=None)
            await launcher.launch()

        mock_find.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_none_binary_path_propagates_edge_not_found_error(self) -> None:
        """EdgeNotFoundError from find_edge_binary() propagates through launch()."""
        from owlbear_browser import EdgeNotFoundError
        from owlbear_browser.edge_launcher import EdgeCDPLauncher

        with patch(
            f"{_EDGE_LAUNCHER_MODULE}.find_edge_binary",
            side_effect=EdgeNotFoundError("Edge not found"),
        ):
            launcher = EdgeCDPLauncher(binary_path=None)
            with pytest.raises(EdgeNotFoundError):
                await launcher.launch()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_user_data_dir_forwarded_to_build_launch_args(self) -> None:
        """launch() passes user_data_dir to build_launch_args."""
        from owlbear_browser.edge_launcher import EdgeCDPLauncher

        proc = _make_mock_process()
        user_dir = r"C:\tmp\edge-profile"
        mgr_instance = _make_mock_manager()
        mgr_class = MagicMock(return_value=mgr_instance)

        with (
            patch(f"{_EDGE_LAUNCHER_MODULE}.Path.exists", return_value=True),
            patch(f"{_EDGE_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc),
            patch(
                f"{_EDGE_LAUNCHER_MODULE}.build_launch_args", return_value=[]
            ) as mock_args,
            patch(f"{_CDP_MODULE}.CDPConnectionManager", mgr_class),
        ):
            launcher = EdgeCDPLauncher(binary_path=_FAKE_BINARY, user_data_dir=user_dir)
            await launcher.launch()

        mock_args.assert_called_once_with(port=_DEFAULT_PORT, user_data_dir=user_dir)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_custom_port_passed_to_build_launch_args(self) -> None:
        """launch() passes the configured port to build_launch_args."""
        from owlbear_browser.edge_launcher import EdgeCDPLauncher

        proc = _make_mock_process()
        mgr_instance = _make_mock_manager()
        mgr_class = MagicMock(return_value=mgr_instance)

        with (
            patch(f"{_EDGE_LAUNCHER_MODULE}.Path.exists", return_value=True),
            patch(f"{_EDGE_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc),
            patch(
                f"{_EDGE_LAUNCHER_MODULE}.build_launch_args", return_value=[]
            ) as mock_args,
            patch(f"{_CDP_MODULE}.CDPConnectionManager", mgr_class),
        ):
            launcher = EdgeCDPLauncher(binary_path=_FAKE_BINARY, port=_CUSTOM_PORT)
            await launcher.launch()

        mock_args.assert_called_once_with(port=_CUSTOM_PORT, user_data_dir="")
