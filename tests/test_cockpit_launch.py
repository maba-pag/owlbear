"""Cockpit launch contracts for native workspace bootstrap."""

from __future__ import annotations

import contextlib
from pathlib import Path
from unittest.mock import patch

import pytest
from owlbear_kanban import NativeWorkspace


@pytest.fixture(autouse=True)
def reset_app() -> object:
    from owlbear_cockpit import main

    routes = list(main.app.routes)
    yield
    main.app.routes[:] = routes
    with contextlib.suppress(AttributeError, KeyError):
        del main.app.state.workspace


def _work_root(tmp_path: Path) -> Path:
    root = tmp_path / ".owlbear" / "kanban"
    root.mkdir(parents=True)
    return root


def test_run_binds_native_workspace_before_uvicorn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from owlbear_cockpit.main import app, run

    root = _work_root(tmp_path)
    monkeypatch.setenv("OWLBEAR_WORK_ROOT", str(root))
    monkeypatch.setenv("COCKPIT_NO_OPEN", "1")
    present: list[bool] = []

    def check_state(*_args: object, **_kwargs: object) -> None:
        present.append(isinstance(getattr(app.state, "workspace", None), NativeWorkspace))

    with patch("uvicorn.run", side_effect=check_state):
        run()

    assert present == [True]
    assert app.state.workspace.work_root == root.resolve()


def test_run_rejects_missing_native_work_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from owlbear_cockpit.main import run

    monkeypatch.setenv("OWLBEAR_WORK_ROOT", str(tmp_path / "missing"))
    monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

    with pytest.raises(SystemExit):
        run()
