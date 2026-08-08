"""Cockpit launch contracts for receipt-authorized target startup."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
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


def test_run_registers_instance_while_uvicorn_owns_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from owlbear_cockpit import main

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    registry = tmp_path / "registry"
    monkeypatch.chdir(workspace_root)
    monkeypatch.setattr(main, "_DIST_DIR", _dist(tmp_path))
    monkeypatch.setenv("OWLBEAR_COCKPIT_REGISTRY", str(registry))
    monkeypatch.setenv("COCKPIT_NO_OPEN", "1")
    observed: list[bool] = []

    def check_record(*_args: object, **_kwargs: object) -> None:
        observed.append((registry / f"{main.os.getpid()}.json").is_file())

    with (
        patch("owlbear_cockpit.main.load_target_context", return_value=object()),
        patch("uvicorn.run", side_effect=check_record),
    ):
        main.run(port_override=8431)

    assert observed == [True]
    assert not (registry / f"{main.os.getpid()}.json").exists()


def test_running_instances_removes_stale_records(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from owlbear_cockpit import main
    from owlbear_cockpit.models import CockpitInstance

    registry = tmp_path / "registry"
    registry.mkdir()
    running = CockpitInstance(pid=101, port=8420, workspace="/running", started_at=datetime.now(UTC))
    stale = CockpitInstance(pid=102, port=8421, workspace="/stale", started_at=datetime.now(UTC))
    (registry / "101.json").write_text(running.model_dump_json(), encoding="utf-8")
    (registry / "102.json").write_text(stale.model_dump_json(), encoding="utf-8")
    monkeypatch.setenv("OWLBEAR_COCKPIT_REGISTRY", str(registry))

    with patch("owlbear_cockpit.main._probe_instance", side_effect=lambda item: item.pid == 101):
        instances = main._running_instances()  # noqa: SLF001

    assert instances == [running]
    assert (registry / "101.json").exists()
    assert not (registry / "102.json").exists()
