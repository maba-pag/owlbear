"""Cockpit launch contracts for native workspace bootstrap."""

from __future__ import annotations

import contextlib
import importlib.util
from pathlib import Path
import sys
import types
from unittest.mock import patch

import pytest
from owlbear_kanban import NativeWorkspace

_REPO_ROOT = Path(__file__).parent.parent


def _init_consumer(target: Path) -> None:
    setup_path = _REPO_ROOT / "setup/init.py"
    spec = importlib.util.spec_from_file_location("owlbear_setup_init_launch", setup_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    assert isinstance(module, types.ModuleType)
    spec.loader.exec_module(module)
    module.init(target, _REPO_ROOT, interactive=False)


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


def test_setup_workspace_starts_native_cockpit_without_retired_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from owlbear_cockpit.main import app, run

    _init_consumer(tmp_path)
    root = tmp_path / ".owlbear/kanban"
    monkeypatch.setenv("OWLBEAR_WORK_ROOT", str(root))
    monkeypatch.setenv("MEMORY_DIR", str(tmp_path / ".owlbear/memory"))
    monkeypatch.setenv("COCKPIT_NO_OPEN", "1")
    started: list[bool] = []

    with patch("uvicorn.run", side_effect=lambda *_args, **_kwargs: started.append(True)):
        run()

    assert started == [True]
    assert isinstance(app.state.workspace, NativeWorkspace)
    assert app.state.workspace.work_root == root.resolve()
    forbidden_modules = {
        "openspec",
        "owlbear_kanban.decisions",
        "owlbear_kanban.engine",
        "owlbear_kanban.migrate",
        "owlbear_kanban.models",
        "owlbear_kanban.storage",
    }
    assert forbidden_modules.isdisjoint(sys.modules)
