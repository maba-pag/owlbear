"""Failing tests for task #758: Edge launcher + CDP connection manager implementation.

Covers the AC items from #758 not already addressed by the #755 RED-phase tests:
  AC#1:  serve/browser/pyproject.toml — name, playwright dep, hatchling build, packages
  AC#2:  launch_edge() function — subprocess launch + CDPConnectionManager return
  AC#3:  CDPConnectionManager as async context manager (__aenter__ / __aexit__)
  AC#5:  owlbear_browser __init__.py re-exports full public API
  AC#7:  Root pyproject.toml tool.ruff.src includes "serve/browser/src"
  AC#8:  Root pyproject.toml tool.coverage.run.source_pkgs includes "owlbear_browser"
  AC#9:  test_package_boundary.py ALLOWED_IMPORTS includes "owlbear_browser": set()
  AC#11: CDPConnectionManager __aexit__ terminates Edge subprocess on all exit paths

All tests intentionally fail on current HEAD — serve/browser/ does not exist yet.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CDP_MODULE = "owlbear_browser.cdp"
_LAUNCHER_MODULE = "owlbear_browser.launcher"
_DEFAULT_PORT = 9222
_USER_DATA_DIR = r"C:\tmp\edge-profile"

ROOT = Path(__file__).parent.parent
SERVE_BROWSER_DIR = ROOT / "serve" / "browser"
BROWSER_PYPROJECT = SERVE_BROWSER_DIR / "pyproject.toml"
ROOT_PYPROJECT = ROOT / "pyproject.toml"


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------


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


def _make_mock_process() -> MagicMock:
    """Return a mock subprocess.Popen-like object."""
    proc = MagicMock()
    proc.pid = 42000
    proc.returncode = None
    proc.terminate = MagicMock()
    proc.kill = MagicMock()
    proc.wait = MagicMock(return_value=0)
    return proc


def _patch_connect_over_cdp(browser: MagicMock) -> Any:  # noqa: ANN401
    return patch(f"{_CDP_MODULE}.playwright_connect_over_cdp", new=AsyncMock(return_value=browser))


def _patch_launch_deps(proc: MagicMock) -> Any:  # noqa: ANN401
    """Return a context manager that patches all launch_edge I/O dependencies."""
    from contextlib import ExitStack  # noqa: PLC0415

    stack = ExitStack()
    stack.enter_context(
        patch(f"{_LAUNCHER_MODULE}.find_edge_binary", return_value=Path(r"C:\edge\msedge.exe"))
    )
    stack.enter_context(
        patch(f"{_LAUNCHER_MODULE}.build_launch_args", return_value=["--remote-debugging-port=9222"])
    )
    stack.enter_context(patch(f"{_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc))
    return stack


# ---------------------------------------------------------------------------
# TestFromAC_PackagePyproject  (AC#1)
# ---------------------------------------------------------------------------


class TestFromAC_PackagePyproject:  # noqa: N801
    """serve/browser/pyproject.toml must exist with the correct structure."""

    def test_browser_pyproject_exists(self) -> None:
        """serve/browser/pyproject.toml must be present."""
        assert BROWSER_PYPROJECT.exists(), (
            "serve/browser/pyproject.toml does not exist — builder must create the package"
        )

    def test_browser_pyproject_name_is_owlbear_browser(self) -> None:
        """project.name must be 'owlbear-browser'."""
        data = tomllib.loads(BROWSER_PYPROJECT.read_text(encoding="utf-8"))
        assert data["project"]["name"] == "owlbear-browser"

    def test_browser_pyproject_depends_on_playwright(self) -> None:
        """'playwright' must appear in project.dependencies."""
        data = tomllib.loads(BROWSER_PYPROJECT.read_text(encoding="utf-8"))
        deps = data["project"].get("dependencies", [])
        assert any("playwright" in dep for dep in deps), (
            f"playwright not found in dependencies: {deps}"
        )

    def test_browser_pyproject_uses_hatchling_build(self) -> None:
        """hatchling must be the build-system backend."""
        data = tomllib.loads(BROWSER_PYPROJECT.read_text(encoding="utf-8"))
        backend = data["build-system"]["build-backend"]
        assert "hatchling" in backend, (
            f"Expected hatchling build backend, got: {backend}"
        )

    def test_browser_pyproject_packages_include_src_owlbear_browser(self) -> None:
        """tool.hatch.build.targets.wheel.packages must include 'src/owlbear_browser'."""
        data = tomllib.loads(BROWSER_PYPROJECT.read_text(encoding="utf-8"))
        packages = (
            data.get("tool", {})
            .get("hatch", {})
            .get("build", {})
            .get("targets", {})
            .get("wheel", {})
            .get("packages", [])
        )
        assert any("owlbear_browser" in p for p in packages), (
            f"'src/owlbear_browser' not in hatch wheel packages: {packages}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_LaunchEdge  (AC#2)
# ---------------------------------------------------------------------------


class TestFromAC_LaunchEdge:  # noqa: N801
    """launch_edge() — subprocess launch and CDPConnectionManager construction."""

    def test_launch_edge_is_callable(self) -> None:
        """launch_edge must be exported from owlbear_browser.launcher."""
        from owlbear_browser.launcher import launch_edge  # noqa: PLC0415

        assert callable(launch_edge)

    def test_launch_edge_calls_find_edge_binary(self) -> None:
        """launch_edge must call find_edge_binary to locate the Edge executable."""
        from owlbear_browser.launcher import launch_edge  # noqa: PLC0415

        proc = _make_mock_process()
        with (
            patch(f"{_LAUNCHER_MODULE}.find_edge_binary", return_value=Path(r"C:\edge\msedge.exe")) as mock_find,
            patch(f"{_LAUNCHER_MODULE}.build_launch_args", return_value=["--arg"]),
            patch(f"{_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc),
        ):
            launch_edge(port=_DEFAULT_PORT, user_data_dir=_USER_DATA_DIR)
        mock_find.assert_called_once()

    def test_launch_edge_calls_build_launch_args(self) -> None:
        """launch_edge must call build_launch_args to assemble CDP flags."""
        from owlbear_browser.launcher import launch_edge  # noqa: PLC0415

        proc = _make_mock_process()
        with (
            patch(f"{_LAUNCHER_MODULE}.find_edge_binary", return_value=Path(r"C:\edge\msedge.exe")),
            patch(f"{_LAUNCHER_MODULE}.build_launch_args", return_value=["--arg"]) as mock_build,
            patch(f"{_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc),
        ):
            launch_edge(port=_DEFAULT_PORT, user_data_dir=_USER_DATA_DIR)
        mock_build.assert_called_once()

    def test_launch_edge_starts_subprocess(self) -> None:
        """launch_edge must spawn an Edge subprocess via subprocess.Popen."""
        from owlbear_browser.launcher import launch_edge  # noqa: PLC0415

        proc = _make_mock_process()
        with (
            patch(f"{_LAUNCHER_MODULE}.find_edge_binary", return_value=Path(r"C:\edge\msedge.exe")),
            patch(f"{_LAUNCHER_MODULE}.build_launch_args", return_value=["--arg"]),
            patch(f"{_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc) as mock_popen,
        ):
            launch_edge(port=_DEFAULT_PORT, user_data_dir=_USER_DATA_DIR)
        mock_popen.assert_called_once()

    def test_launch_edge_popen_receives_edge_binary(self) -> None:
        """launch_edge must pass the Edge binary path as the first Popen argument."""
        from owlbear_browser.launcher import launch_edge  # noqa: PLC0415

        proc = _make_mock_process()
        edge_path = Path(r"C:\edge\msedge.exe")
        with (
            patch(f"{_LAUNCHER_MODULE}.find_edge_binary", return_value=edge_path),
            patch(f"{_LAUNCHER_MODULE}.build_launch_args", return_value=["--arg"]),
            patch(f"{_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc) as mock_popen,
        ):
            launch_edge(port=_DEFAULT_PORT, user_data_dir=_USER_DATA_DIR)
        call_args = mock_popen.call_args
        # First positional arg (or cmd= kwarg) must include the binary path
        cmd = call_args[0][0] if call_args[0] else call_args[1].get("args", call_args[1].get("cmd", []))
        assert any(str(edge_path) in str(part) for part in cmd), (
            f"Edge binary path {edge_path} not found in Popen command: {cmd}"
        )

    def test_launch_edge_returns_cdp_connection_manager(self) -> None:
        """launch_edge must return a CDPConnectionManager instance."""
        from owlbear_browser.cdp import CDPConnectionManager  # noqa: PLC0415
        from owlbear_browser.launcher import launch_edge  # noqa: PLC0415

        proc = _make_mock_process()
        with (
            patch(f"{_LAUNCHER_MODULE}.find_edge_binary", return_value=Path(r"C:\edge\msedge.exe")),
            patch(f"{_LAUNCHER_MODULE}.build_launch_args", return_value=["--arg"]),
            patch(f"{_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc),
        ):
            result = launch_edge(port=_DEFAULT_PORT, user_data_dir=_USER_DATA_DIR)
        assert isinstance(result, CDPConnectionManager)

    def test_launch_edge_propagates_edge_not_found_error(self) -> None:
        """EdgeNotFoundError must propagate to the caller unchanged."""
        from owlbear_browser.launcher import EdgeNotFoundError, launch_edge  # noqa: PLC0415

        with (
            patch(f"{_LAUNCHER_MODULE}.find_edge_binary", side_effect=EdgeNotFoundError("not found")),
            pytest.raises(EdgeNotFoundError),
        ):
            launch_edge(port=_DEFAULT_PORT, user_data_dir=_USER_DATA_DIR)

    def test_launch_edge_raises_cdp_connection_error_on_oserror(self) -> None:
        """CDPConnectionError raised when subprocess.Popen raises OSError (e.g. permission denied)."""
        from owlbear_browser.cdp import CDPConnectionError  # noqa: PLC0415
        from owlbear_browser.launcher import launch_edge  # noqa: PLC0415

        with (
            patch(f"{_LAUNCHER_MODULE}.find_edge_binary", return_value=Path(r"C:\edge\msedge.exe")),
            patch(f"{_LAUNCHER_MODULE}.build_launch_args", return_value=["--arg"]),
            patch(f"{_LAUNCHER_MODULE}.subprocess.Popen", side_effect=OSError("permission denied")),
            pytest.raises(CDPConnectionError),
        ):
            launch_edge(port=_DEFAULT_PORT, user_data_dir=_USER_DATA_DIR)


# ---------------------------------------------------------------------------
# TestFromAC_AsyncContextManager  (AC#3, AC#11)
# ---------------------------------------------------------------------------


class TestFromAC_AsyncContextManager:  # noqa: N801
    """CDPConnectionManager async context manager — __aenter__/__aexit__ and subprocess cleanup."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aenter_returns_manager_instance(self) -> None:
        """__aenter__ must return the CDPConnectionManager itself."""
        from owlbear_browser.cdp import CDPConnectionManager  # noqa: PLC0415

        browser = _make_mock_browser()
        with _patch_connect_over_cdp(browser):
            manager = CDPConnectionManager(port=_DEFAULT_PORT)
            result = await manager.__aenter__()
        assert result is manager

    @pytest.mark.asyncio(loop_scope="function")
    async def test_is_connected_inside_async_with_block(self) -> None:
        """is_connected must be True inside the async with block."""
        from owlbear_browser.cdp import CDPConnectionManager  # noqa: PLC0415

        browser = _make_mock_browser()
        with _patch_connect_over_cdp(browser):
            async with CDPConnectionManager(port=_DEFAULT_PORT) as manager:
                assert manager.is_connected

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aexit_closes_playwright_browser(self) -> None:
        """__aexit__ must close the Playwright browser connection."""
        from owlbear_browser.cdp import CDPConnectionManager  # noqa: PLC0415

        browser = _make_mock_browser()
        with _patch_connect_over_cdp(browser):
            async with CDPConnectionManager(port=_DEFAULT_PORT):
                pass
        browser.close.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aexit_terminates_edge_subprocess_on_normal_exit(self) -> None:
        """__aexit__ must terminate the Edge subprocess launched by launch_edge on normal exit."""
        from owlbear_browser.launcher import launch_edge  # noqa: PLC0415

        proc = _make_mock_process()
        browser = _make_mock_browser()
        with (
            patch(f"{_LAUNCHER_MODULE}.find_edge_binary", return_value=Path(r"C:\edge\msedge.exe")),
            patch(f"{_LAUNCHER_MODULE}.build_launch_args", return_value=["--arg"]),
            patch(f"{_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc),
            _patch_connect_over_cdp(browser),
        ):
            manager = launch_edge(port=_DEFAULT_PORT, user_data_dir=_USER_DATA_DIR)
            async with manager:
                pass
        assert proc.terminate.called or proc.kill.called, (
            "CDPConnectionManager.__aexit__ must terminate the Edge subprocess"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aexit_terminates_edge_subprocess_on_exception(self) -> None:
        """__aexit__ must terminate the Edge subprocess even when the body raises."""
        from owlbear_browser.launcher import launch_edge  # noqa: PLC0415

        proc = _make_mock_process()
        browser = _make_mock_browser()
        with (
            patch(f"{_LAUNCHER_MODULE}.find_edge_binary", return_value=Path(r"C:\edge\msedge.exe")),
            patch(f"{_LAUNCHER_MODULE}.build_launch_args", return_value=["--arg"]),
            patch(f"{_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc),
            _patch_connect_over_cdp(browser),
        ):
            manager = launch_edge(port=_DEFAULT_PORT, user_data_dir=_USER_DATA_DIR)
            err_msg = "simulated body failure"
            with pytest.raises(RuntimeError):
                async with manager:
                    raise RuntimeError(err_msg)
        assert proc.terminate.called or proc.kill.called, (
            "__aexit__ must terminate subprocess even when body raises"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_is_disconnected_after_aexit(self) -> None:
        """is_connected must be False after exiting the async with block."""
        from owlbear_browser.cdp import CDPConnectionManager  # noqa: PLC0415

        browser = _make_mock_browser()
        with _patch_connect_over_cdp(browser):
            manager = CDPConnectionManager(port=_DEFAULT_PORT)
            async with manager:
                pass
        assert not manager.is_connected

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aexit_does_not_raise_when_no_subprocess_attached(self) -> None:
        """__aexit__ must complete cleanly when no subprocess is attached (connect-only mode)."""
        from owlbear_browser.cdp import CDPConnectionManager  # noqa: PLC0415

        browser = _make_mock_browser()
        with _patch_connect_over_cdp(browser):
            # No process arg — pure connect mode (e.g. attach to already-running Edge)
            async with CDPConnectionManager(port=_DEFAULT_PORT):
                pass  # must not raise


# ---------------------------------------------------------------------------
# TestFromAC_PublicAPI  (AC#5)
# ---------------------------------------------------------------------------


class TestFromAC_PublicAPI:  # noqa: N801
    """owlbear_browser.__init__.py must re-export the complete public API."""

    def test_find_edge_binary_importable_from_top_level(self) -> None:
        """find_edge_binary must be importable directly from owlbear_browser."""
        from owlbear_browser import find_edge_binary  # noqa: PLC0415

        assert callable(find_edge_binary)

    def test_launch_edge_importable_from_top_level(self) -> None:
        """launch_edge must be importable directly from owlbear_browser."""
        from owlbear_browser import launch_edge  # noqa: PLC0415

        assert callable(launch_edge)

    def test_build_launch_args_importable_from_top_level(self) -> None:
        """build_launch_args must be importable directly from owlbear_browser."""
        from owlbear_browser import build_launch_args  # noqa: PLC0415

        assert callable(build_launch_args)

    def test_cdp_connection_manager_importable_from_top_level(self) -> None:
        """CDPConnectionManager must be importable directly from owlbear_browser."""
        from owlbear_browser import CDPConnectionManager  # noqa: PLC0415

        assert CDPConnectionManager is not None

    def test_edge_not_found_error_importable_from_top_level(self) -> None:
        """EdgeNotFoundError must be importable directly from owlbear_browser."""
        from owlbear_browser import EdgeNotFoundError  # noqa: PLC0415

        assert issubclass(EdgeNotFoundError, Exception)

    def test_cdp_connection_error_importable_from_top_level(self) -> None:
        """CDPConnectionError must be importable directly from owlbear_browser."""
        from owlbear_browser import CDPConnectionError  # noqa: PLC0415

        assert issubclass(CDPConnectionError, Exception)

    def test_authentication_required_importable_from_top_level(self) -> None:
        """AuthenticationRequired must be importable directly from owlbear_browser."""
        from owlbear_browser import AuthenticationRequired  # noqa: PLC0415

        assert issubclass(AuthenticationRequired, Exception)


# ---------------------------------------------------------------------------
# TestFromAC_WorkspaceConfig  (AC#7, AC#8, AC#9)
# ---------------------------------------------------------------------------


class TestFromAC_WorkspaceConfig:  # noqa: N801
    """Root pyproject.toml and test_package_boundary.py must include owlbear_browser entries."""

    def _root_pyproject(self) -> dict:
        return tomllib.loads(ROOT_PYPROJECT.read_text(encoding="utf-8"))

    def test_ruff_src_includes_serve_browser_src(self) -> None:
        """tool.ruff.src must include 'serve/browser/src' (ruff must type-check the package)."""
        data = self._root_pyproject()
        ruff_src = data["tool"]["ruff"]["src"]
        assert "serve/browser/src" in ruff_src, (
            f"'serve/browser/src' not in tool.ruff.src: {ruff_src}"
        )

    def test_coverage_source_pkgs_includes_owlbear_browser(self) -> None:
        """tool.coverage.run.source_pkgs must include 'owlbear_browser'."""
        data = self._root_pyproject()
        source_pkgs = data["tool"]["coverage"]["run"]["source_pkgs"]
        assert "owlbear_browser" in source_pkgs, (
            f"'owlbear_browser' not in coverage source_pkgs: {source_pkgs}"
        )

    def test_package_boundary_has_owlbear_browser_key(self) -> None:
        """ALLOWED_IMPORTS in test_package_boundary.py must contain an 'owlbear_browser' entry."""
        from tests.test_package_boundary import ALLOWED_IMPORTS  # noqa: PLC0415

        assert "owlbear_browser" in ALLOWED_IMPORTS, (
            "ALLOWED_IMPORTS missing 'owlbear_browser' key — builder must add the boundary entry"
        )

    def test_package_boundary_owlbear_browser_has_no_deps(self) -> None:
        """ALLOWED_IMPORTS['owlbear_browser'] must be set() — zero owlbear-namespace deps."""
        from tests.test_package_boundary import ALLOWED_IMPORTS  # noqa: PLC0415

        assert ALLOWED_IMPORTS.get("owlbear_browser") == set(), (
            "owlbear_browser must have an empty set() in ALLOWED_IMPORTS (foundation package)"
        )


# ---------------------------------------------------------------------------
# TestBuilderDiscovered — edge cases not covered by AC tests
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:
    """Builder-discovered edge cases (RED → GREEN verified)."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aexit_kills_subprocess_when_wait_times_out(self) -> None:
        """kill() is invoked when wait() raises TimeoutExpired (slow-exit Edge)."""
        import subprocess  # noqa: PLC0415

        from owlbear_browser.launcher import launch_edge  # noqa: PLC0415

        proc = _make_mock_process()
        proc.wait = MagicMock(side_effect=subprocess.TimeoutExpired(cmd="msedge", timeout=5))
        browser = _make_mock_browser()
        with (
            patch(f"{_LAUNCHER_MODULE}.find_edge_binary", return_value=Path(r"C:\edge\msedge.exe")),
            patch(f"{_LAUNCHER_MODULE}.build_launch_args", return_value=["--arg"]),
            patch(f"{_LAUNCHER_MODULE}.subprocess.Popen", return_value=proc),
            _patch_connect_over_cdp(browser),
        ):
            manager = launch_edge(port=_DEFAULT_PORT, user_data_dir=_USER_DATA_DIR)
            async with manager:
                pass
        assert proc.kill.called, "kill() must be called when wait() times out"
