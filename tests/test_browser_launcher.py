"""Tests for Edge launcher — find, launch, probe, and kill Edge CDP.

Covers: find_edge() path discovery, launch_edge_cdp() subprocess management,
is_cdp_available() HTTP probing, and kill_edge() process termination.
All OS / subprocess / network calls are mocked for isolation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

MODULE = "owlbear.tools.browser.launcher"

# ---------------------------------------------------------------------------
# TestFindEdge
# ---------------------------------------------------------------------------


class TestFindEdge:
    """find_edge() discovers the Edge executable on disk."""

    def test_returns_path_when_x86_exists(self) -> None:
        """Program Files (x86) location is found first."""
        from owlbear.tools.browser.launcher import find_edge

        with patch(f"{MODULE}.Path") as mock_path_cls:
            # Only the x86 candidate returns True
            x86_instance = MagicMock()
            x86_instance.exists.return_value = True
            x86_instance.__str__ = lambda _: (
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
            )

            regular_instance = MagicMock()
            regular_instance.exists.return_value = False

            # Path() is called twice: first x86, then regular
            mock_path_cls.side_effect = [x86_instance, regular_instance]

            result = find_edge()

        assert result is not None
        assert "msedge.exe" in result

    def test_returns_path_when_program_files_exists(self) -> None:
        """Falls back to Program Files when x86 is absent."""
        from owlbear.tools.browser.launcher import find_edge

        with patch(f"{MODULE}.Path") as mock_path_cls:
            x86_instance = MagicMock()
            x86_instance.exists.return_value = False

            regular_instance = MagicMock()
            regular_instance.exists.return_value = True
            regular_instance.__str__ = lambda _: (
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
            )

            mock_path_cls.side_effect = [x86_instance, regular_instance]

            result = find_edge()

        assert result is not None
        assert "msedge.exe" in result

    def test_returns_none_when_neither_path_exists(self) -> None:
        """Returns None when Edge is not installed."""
        from owlbear.tools.browser.launcher import find_edge

        with patch(f"{MODULE}.Path") as mock_path_cls:
            absent = MagicMock()
            absent.exists.return_value = False
            mock_path_cls.return_value = absent

            result = find_edge()

        assert result is None

    def test_respects_explicit_executable_parameter(self) -> None:
        """Returns override path as-is without filesystem checks."""
        from owlbear.tools.browser.launcher import find_edge

        custom = r"D:\custom\edge.exe"
        result = find_edge(executable=custom)

        assert result == custom


# ---------------------------------------------------------------------------
# TestLaunchEdgeCdp
# ---------------------------------------------------------------------------


class TestLaunchEdgeCdp:
    """launch_edge_cdp() spawns Edge with CDP flags."""

    def test_calls_popen_with_debugging_port(self) -> None:
        """Popen receives --remote-debugging-port={port}."""
        from owlbear.tools.browser.launcher import launch_edge_cdp

        mock_proc = MagicMock()
        mock_proc.pid = 12345

        with (
            patch(f"{MODULE}.subprocess.Popen", return_value=mock_proc) as mock_popen,
            patch(f"{MODULE}.find_edge", return_value=r"C:\edge\msedge.exe"),
        ):
            launch_edge_cdp(port=9333)

        args_flat = " ".join(str(a) for a in mock_popen.call_args[0][0])
        assert "--remote-debugging-port=9333" in args_flat

    def test_includes_no_first_run_flag(self) -> None:
        """Popen args include --no-first-run."""
        from owlbear.tools.browser.launcher import launch_edge_cdp

        mock_proc = MagicMock()
        mock_proc.pid = 12345

        with (
            patch(f"{MODULE}.subprocess.Popen", return_value=mock_proc) as mock_popen,
            patch(f"{MODULE}.find_edge", return_value=r"C:\edge\msedge.exe"),
        ):
            launch_edge_cdp()

        args_flat = " ".join(str(a) for a in mock_popen.call_args[0][0])
        assert "--no-first-run" in args_flat

    def test_returns_subprocess_pid(self) -> None:
        """Returns the PID of the spawned process."""
        from owlbear.tools.browser.launcher import launch_edge_cdp

        mock_proc = MagicMock()
        mock_proc.pid = 42

        with (
            patch(f"{MODULE}.subprocess.Popen", return_value=mock_proc),
            patch(f"{MODULE}.find_edge", return_value=r"C:\edge\msedge.exe"),
        ):
            pid = launch_edge_cdp()

        assert pid == 42
        assert isinstance(pid, int)

    def test_raises_file_not_found_when_no_executable(self) -> None:
        """Raises FileNotFoundError if find_edge() returns None."""
        from owlbear.tools.browser.launcher import launch_edge_cdp

        with (
            patch(f"{MODULE}.find_edge", return_value=None),
            pytest.raises(FileNotFoundError),
        ):
            launch_edge_cdp()


# ---------------------------------------------------------------------------
# TestIsCdpAvailable
# ---------------------------------------------------------------------------


class TestIsCdpAvailable:
    """is_cdp_available() probes the CDP /json/version endpoint."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_true_on_200(self) -> None:
        """Returns True when the endpoint responds with 200."""
        from owlbear.tools.browser.launcher import is_cdp_available

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=mock_client):
            result = await is_cdp_available(port=9222)

        assert result is True

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_false_on_connection_error(self) -> None:
        """Returns False when a ConnectionError occurs."""
        import httpx

        from owlbear.tools.browser.launcher import is_cdp_available

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=mock_client):
            result = await is_cdp_available(port=9222)

        assert result is False

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_false_on_timeout(self) -> None:
        """Returns False when the request times out."""
        import httpx

        from owlbear.tools.browser.launcher import is_cdp_available

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=mock_client):
            result = await is_cdp_available(port=9222)

        assert result is False


# ---------------------------------------------------------------------------
# TestKillEdge
# ---------------------------------------------------------------------------


class TestKillEdge:
    """kill_edge() terminates a process by PID."""

    def test_terminates_process_with_given_pid(self) -> None:
        """Calls os.kill (or subprocess) with the expected PID."""
        from owlbear.tools.browser.launcher import kill_edge

        with patch(f"{MODULE}.os.kill") as mock_kill:
            kill_edge(pid=12345)

        mock_kill.assert_called_once()
        # First arg to os.kill should be the PID
        assert mock_kill.call_args[0][0] == 12345

    def test_handles_already_dead_process(self) -> None:
        """Does not raise when the process is already gone."""
        from owlbear.tools.browser.launcher import kill_edge

        with patch(f"{MODULE}.os.kill", side_effect=ProcessLookupError):
            # Should not raise
            kill_edge(pid=99999)

    def test_handles_permission_error_gracefully(self) -> None:
        """Does not raise on PermissionError (process owned by another user)."""
        from owlbear.tools.browser.launcher import kill_edge

        with patch(f"{MODULE}.os.kill", side_effect=PermissionError):
            # Should not raise
            kill_edge(pid=99999)
