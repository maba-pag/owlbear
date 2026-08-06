"""Cockpit launch contracts for receipt-authorized target startup."""

from __future__ import annotations

import contextlib
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def reset_app() -> object:
    from owlbear_cockpit import main

    routes = list(main.app.routes)
    yield
    main.app.routes[:] = routes
    for attribute in ("workspace_root", "target_context", "memory_engine"):
        with contextlib.suppress(AttributeError, KeyError):
            delattr(main.app.state, attribute)


def _dist(tmp_path: Path) -> Path:
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<html></html>\n", encoding="utf-8")
    (root / "theme-bootstrap.js").write_text("export {};\n", encoding="utf-8")
    return root


def test_run_binds_target_context_before_uvicorn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from owlbear_cockpit import main

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    request_path = workspace_root / ".owlbear/target-cutover-request.json"
    context = object()
    monkeypatch.chdir(workspace_root)
    monkeypatch.setattr(main, "_DIST_DIR", _dist(tmp_path))
    monkeypatch.setenv("OWLBEAR_WORKSPACE_ROOT", str(tmp_path / "ignored-workspace"))
    monkeypatch.setenv("OWLBEAR_TARGET_CUTOVER_REQUEST", str(tmp_path / "ignored-request.json"))
    monkeypatch.setenv("COCKPIT_DIST_DIR", str(tmp_path / "ignored-dist"))
    monkeypatch.setenv("COCKPIT_NO_OPEN", "1")
    present: list[bool] = []

    def check_state(*_args: object, **_kwargs: object) -> None:
        present.append(main.app.state.target_context is context)

    with (
        patch("owlbear_cockpit.main.load_target_context", return_value=context) as load,
        patch("uvicorn.run", side_effect=check_state),
    ):
        main.run()

    assert present == [True]
    assert main.app.state.workspace_root == workspace_root.resolve()
    load.assert_called_once_with(workspace_root.resolve(), request_path.resolve())


def test_run_rejects_missing_target_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from owlbear_cockpit.main import run

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

    with (
        patch(
            "owlbear_cockpit.main.load_target_context",
            side_effect=RuntimeError("Cockpit startup requires a valid target cutover request and receipt"),
        ),
        pytest.raises(SystemExit),
    ):
        run()
