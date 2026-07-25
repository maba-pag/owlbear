"""Failing tests for cockpit launch command — run() in main.py (#937).

RED phase — all tests must fail until run() is implemented in GREEN phase.

AC coverage:
  - AC #1: pyproject.toml script entry / run() callable exists in main.py
  - AC #2: uvicorn on 127.0.0.1:{port}, default 8420, configurable via COCKPIT_PORT
  - AC #2 (revised): invalid port (non-integer, 0, 65536) → sys.exit with error
  - AC #3: static file handler mounted inside run(), NOT at module import
  - AC #4: catch-all route for SPA client-side routing serves index.html
  - AC #5: browser auto-opens; suppressed via COCKPIT_NO_OPEN=1; failure non-fatal
  - AC #7: sys.exit with error message if dist/ directory is missing
  - AC #8: KanbanEngine from CWD/.owlbear/kanban/ or KANBAN_DIR env var; set on
           app.state.engine before uvicorn starts; sys.exit if kanban dir missing
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_KANBAN_CONFIG = """\
next_id: 1
"""


def _make_kanban_dir(base: Path) -> Path:
    """Create a minimal kanban board directory. Returns kanban_dir path."""
    kanban_dir = base / ".owlbear" / "kanban"
    kanban_dir.mkdir(parents=True)
    (kanban_dir / "config.yml").write_text(_KANBAN_CONFIG, encoding="utf-8")
    (kanban_dir / "tasks").mkdir()
    (kanban_dir / "archive").mkdir()
    return kanban_dir


@pytest.fixture(autouse=True)
def _reset_app_after_run() -> object:
    """Restore app routes and state between tests that call run().

    run() adds static mounts and a catch-all route to the shared FastAPI app.
    Without cleanup, these persist across tests and pollute later assertions.
    """
    import owlbear_cockpit.main as _m  # noqa: PLC0415

    saved_routes = list(_m.app.routes)
    yield
    _m.app.routes[:] = saved_routes
    with contextlib.suppress(AttributeError, KeyError):
        del _m.app.state.engine


# ---------------------------------------------------------------------------
# TestFromAC_CockpitLaunch
# ---------------------------------------------------------------------------


class TestFromAC_CockpitLaunch:
    """AC-derived tests for the cockpit launch command (#937).

    All tests FAIL in RED phase because run() does not yet exist in main.py.
    Expected failure mode: ImportError on `from owlbear_cockpit.main import run`.
    """

    # ---- AC #1 — run() is callable in main.py --------------------------------

    def test_run_is_callable_in_main(self) -> None:
        """run() must be importable and callable from owlbear_cockpit.main."""
        from owlbear_cockpit.main import run  # noqa: PLC0415

        assert callable(run)

    def test_pyproject_has_cockpit_script_entry(self, project_root: Path) -> None:
        """pyproject.toml has a [project.scripts] cockpit entry pointing to run()."""
        content = (project_root / "serve" / "cockpit" / "pyproject.toml").read_text()
        assert "[project.scripts]" in content
        assert "owlbear_cockpit.main:run" in content

    # ---- AC #2 — default port 8420, host 127.0.0.1 --------------------------

    def test_run_invokes_uvicorn_with_default_port(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """uvicorn is called with port=8420 when COCKPIT_PORT is not set."""
        kanban_dir = _make_kanban_dir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(kanban_dir))
        monkeypatch.delenv("COCKPIT_PORT", raising=False)
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        with patch("uvicorn.run") as mock_uvicorn_run:
            from owlbear_cockpit.main import run  # noqa: PLC0415

            run()

        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs.get("port") == 8420

    def test_run_binds_to_localhost(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """uvicorn is called with host='127.0.0.1' (never 0.0.0.0)."""
        kanban_dir = _make_kanban_dir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(kanban_dir))
        monkeypatch.delenv("COCKPIT_PORT", raising=False)
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        with patch("uvicorn.run") as mock_uvicorn_run:
            from owlbear_cockpit.main import run  # noqa: PLC0415

            run()

        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs.get("host") == "127.0.0.1"

    def test_run_uses_cockpit_port_env_var(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """COCKPIT_PORT=9999 causes uvicorn to bind on port 9999."""
        kanban_dir = _make_kanban_dir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(kanban_dir))
        monkeypatch.setenv("COCKPIT_PORT", "9999")
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        with patch("uvicorn.run") as mock_uvicorn_run:
            from owlbear_cockpit.main import run  # noqa: PLC0415

            run()

        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs.get("port") == 9999

    # ---- AC #2 (revised) — port validation -----------------------------------

    def test_run_exits_on_non_integer_port(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """COCKPIT_PORT='notaport' causes sys.exit with a non-zero exit code."""
        monkeypatch.setenv("COCKPIT_PORT", "notaport")
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        from owlbear_cockpit.main import run  # noqa: PLC0415

        with pytest.raises(SystemExit) as exc_info:
            run()

        assert exc_info.value.code != 0

    def test_run_exits_on_port_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Port 0 is below the valid range (1-65535) and causes sys.exit."""
        monkeypatch.setenv("COCKPIT_PORT", "0")
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        from owlbear_cockpit.main import run  # noqa: PLC0415

        with pytest.raises(SystemExit) as exc_info:
            run()

        assert exc_info.value.code != 0

    def test_run_exits_on_port_above_max(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Port 65536 is above the valid range (1-65535) and causes sys.exit."""
        monkeypatch.setenv("COCKPIT_PORT", "65536")
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        from owlbear_cockpit.main import run  # noqa: PLC0415

        with pytest.raises(SystemExit) as exc_info:
            run()

        assert exc_info.value.code != 0

    def test_run_accepts_port_boundary_low(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Port 1 is the lower boundary of 1-65535 and must be accepted."""
        kanban_dir = _make_kanban_dir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(kanban_dir))
        monkeypatch.setenv("COCKPIT_PORT", "1")
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        with patch("uvicorn.run") as mock_uvicorn_run:
            from owlbear_cockpit.main import run  # noqa: PLC0415

            run()

        mock_uvicorn_run.assert_called_once()
        assert mock_uvicorn_run.call_args[1].get("port") == 1

    def test_run_accepts_port_boundary_high(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Port 65535 is the upper boundary of 1-65535 and must be accepted."""
        kanban_dir = _make_kanban_dir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(kanban_dir))
        monkeypatch.setenv("COCKPIT_PORT", "65535")
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        with patch("uvicorn.run") as mock_uvicorn_run:
            from owlbear_cockpit.main import run  # noqa: PLC0415

            run()

        mock_uvicorn_run.assert_called_once()
        assert mock_uvicorn_run.call_args[1].get("port") == 65535

    # ---- AC #3 — static files mounted in run(), NOT at module import ----------

    def test_static_files_not_mounted_at_module_import(self) -> None:
        """Importing main.py must NOT add static file routes to the app.

        Static files are only added inside run() to preserve TestClient isolation.
        run() must exist for this architectural invariant to be testable.
        """
        from owlbear_cockpit.main import run  # noqa: PLC0415 - fails in RED
        from starlette.staticfiles import StaticFiles  # noqa: PLC0415

        import owlbear_cockpit.main as _m  # noqa: PLC0415

        assert callable(run)  # run() must exist
        static_routes = [r for r in _m.app.routes if hasattr(r, "app") and isinstance(r.app, StaticFiles)]
        assert static_routes == [], (
            "Static files must not be mounted at import time — only inside run() to preserve TestClient isolation."
        )

    def test_static_files_mounted_after_run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """After run() executes, at least one StaticFiles mount is on the app."""
        kanban_dir = _make_kanban_dir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(kanban_dir))
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        with patch("uvicorn.run"):
            from owlbear_cockpit.main import app, run  # noqa: PLC0415

            run()

        from starlette.staticfiles import StaticFiles  # noqa: PLC0415

        static_routes = [r for r in app.routes if hasattr(r, "app") and isinstance(r.app, StaticFiles)]
        assert len(static_routes) >= 1

    # ---- AC #4 — catch-all route serves index.html for SPA paths --------------

    def test_catchall_route_serves_index_html_for_spa_paths(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-API paths return a 200 response with index.html content."""
        from fastapi.testclient import TestClient  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_kanban_dir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(kanban_dir))
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        with patch("uvicorn.run"):
            from owlbear_cockpit.deps import get_engine  # noqa: PLC0415
            from owlbear_cockpit.main import app, run  # noqa: PLC0415

            run()

        engine = KanbanEngine(kanban_dir)
        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with TestClient(app, raise_server_exceptions=True) as client:
                resp = client.get("/some/spa/route")
            assert resp.status_code == 200
            assert resp.headers.get("content-type", "").startswith("text/html")
            assert "<html" in resp.text.lower()
        finally:
            app.dependency_overrides.clear()

    # ---- AC #5 — browser auto-opens on startup --------------------------------

    def test_browser_opens_on_startup(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """webbrowser.open is called with http://127.0.0.1:{port}/ on startup."""
        kanban_dir = _make_kanban_dir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(kanban_dir))
        monkeypatch.delenv("COCKPIT_PORT", raising=False)
        monkeypatch.delenv("COCKPIT_NO_OPEN", raising=False)

        # Simulate Timer firing immediately so we can verify the callback.
        class _ImmediateTimer:
            def __init__(self, _delay: float, fn: object, *_args: object, **_kwargs: object) -> None:
                self._fn = fn

            def start(self) -> None:
                self._fn()  # type: ignore[operator]

            def cancel(self) -> None:
                pass

        with (
            patch("uvicorn.run"),
            patch("threading.Timer", _ImmediateTimer),
            patch("webbrowser.open") as mock_open,
        ):
            from owlbear_cockpit.main import run  # noqa: PLC0415

            run()

        mock_open.assert_called_once()
        url = mock_open.call_args[0][0]
        assert "127.0.0.1" in url
        assert "8420" in url

    def test_cockpit_no_open_suppresses_browser(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """COCKPIT_NO_OPEN=1 prevents webbrowser.open from being called."""
        kanban_dir = _make_kanban_dir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(kanban_dir))
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        with (
            patch("uvicorn.run"),
            patch("webbrowser.open") as mock_open,
        ):
            from owlbear_cockpit.main import run  # noqa: PLC0415

            run()

        mock_open.assert_not_called()

    def test_browser_failure_does_not_crash_server(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """webbrowser.open raising an exception must not prevent uvicorn from starting."""
        kanban_dir = _make_kanban_dir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(kanban_dir))
        monkeypatch.delenv("COCKPIT_NO_OPEN", raising=False)

        class _ImmediateTimer:
            def __init__(self, _delay: float, fn: object, *_args: object, **_kwargs: object) -> None:
                self._fn = fn

            def start(self) -> None:
                self._fn()  # type: ignore[operator]

            def cancel(self) -> None:
                pass

        with (
            patch("uvicorn.run") as mock_uvicorn_run,
            patch("threading.Timer", _ImmediateTimer),
            patch("webbrowser.open", side_effect=OSError("browser not available")),
        ):
            from owlbear_cockpit.main import run  # noqa: PLC0415

            # Must not raise even when webbrowser.open fails
            run()

        mock_uvicorn_run.assert_called_once()

    # ---- AC #7 — error if dist/ directory is missing --------------------------

    def test_run_exits_with_error_if_dist_missing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """run() calls sys.exit(1) with an error message when dist/ is not found.

        Uses a selective Path.is_dir mock so only the dist path returns False
        (kanban dir is provided via KANBAN_DIR and really exists).
        """
        kanban_dir = _make_kanban_dir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(kanban_dir))
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        original_is_dir = Path.is_dir

        def _dist_missing(self: Path) -> bool:  # noqa: N805
            if self.name == "dist":
                return False
            return original_is_dir(self)

        monkeypatch.setattr(Path, "is_dir", _dist_missing)

        from owlbear_cockpit.main import run  # noqa: PLC0415

        with pytest.raises(SystemExit) as exc_info:
            run()

        assert exc_info.value.code != 0
        captured = capsys.readouterr()
        assert "dist" in (captured.out + captured.err).lower()

    # ---- AC #8 — KanbanEngine init, app.state.engine, kanban dir missing -----

    def test_engine_initialized_from_kanban_dir_env_var(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """KANBAN_DIR env var is used as the kanban directory for KanbanEngine."""
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_kanban_dir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(kanban_dir))
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        with patch("uvicorn.run"):
            from owlbear_cockpit.main import app, run  # noqa: PLC0415

            run()

        assert isinstance(app.state.engine, KanbanEngine)

    def test_engine_initialized_from_cwd_owlbear_kanban(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without KANBAN_DIR, run() resolves .owlbear/kanban/ from CWD."""
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        _make_kanban_dir(tmp_path)  # creates tmp_path/.owlbear/kanban/
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("KANBAN_DIR", raising=False)
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        with patch("uvicorn.run"):
            from owlbear_cockpit.main import app, run  # noqa: PLC0415

            run()

        assert isinstance(app.state.engine, KanbanEngine)

    def test_engine_set_on_app_state_before_uvicorn_starts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """app.state.engine is a KanbanEngine when uvicorn.run is invoked."""
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_kanban_dir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(kanban_dir))
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        engine_present_at_start: list[bool] = []

        def _check_state(*_args: object, **_kwargs: object) -> None:
            from owlbear_cockpit.main import app as _app  # noqa: PLC0415

            engine_present_at_start.append(isinstance(getattr(_app.state, "engine", None), KanbanEngine))

        with patch("uvicorn.run", side_effect=_check_state):
            from owlbear_cockpit.main import run  # noqa: PLC0415

            run()

        assert engine_present_at_start == [True], "app.state.engine must be a KanbanEngine before uvicorn.run is called"

    def test_run_exits_with_error_if_kanban_dir_missing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """run() calls sys.exit with error message when kanban dir is not found.

        CWD is a fresh temp dir without .owlbear/kanban/ and KANBAN_DIR is unset.
        """
        monkeypatch.chdir(tmp_path)  # no .owlbear/kanban/ here
        monkeypatch.delenv("KANBAN_DIR", raising=False)
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        from owlbear_cockpit.main import run  # noqa: PLC0415

        with pytest.raises(SystemExit) as exc_info:
            run()

        assert exc_info.value.code != 0
        captured = capsys.readouterr()
        assert "kanban" in (captured.out + captured.err).lower()
