"""Offline controller inspection must remain usable without Delivery imports."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "setup/delivery_controller.py"
SPEC = importlib.util.spec_from_file_location("delivery_controller", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
controller = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(controller)


def test_offline_inspection_preserves_state_and_detects_custody(tmp_path: Path) -> None:
    frontier = tmp_path / ".owlbear/delivery/runtime/changes/sample/frontier.json"
    frontier.parent.mkdir(parents=True)
    original = json.dumps({"schema_version": 18, "bindings": [{"active_claim": None}]}).encode()
    frontier.write_bytes(original)

    result = controller.inspect_workspace(tmp_path)

    assert result["ready_for_switch"]
    assert frontier.read_bytes() == original
    frontier.write_text(json.dumps({"bindings": [{"active_claim": {"claim_id": "busy"}}]}))
    assert not controller.inspect_workspace(tmp_path)["ready_for_switch"]


@pytest.mark.parametrize("content", [b"not-json", b"[]", b'{"bindings":null}'])
def test_offline_inspection_fails_closed_without_rewriting(tmp_path: Path, content: bytes) -> None:
    frontier = tmp_path / ".owlbear/delivery/runtime/changes/sample/frontier.json"
    frontier.parent.mkdir(parents=True)
    frontier.write_bytes(content)

    result = controller.inspect_workspace(tmp_path)

    assert not result["ready_for_switch"]
    assert frontier.read_bytes() == content


def test_offline_inspection_rejects_symlinked_runtime(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    runtime = tmp_path / ".owlbear/delivery/runtime"
    runtime.parent.mkdir(parents=True)
    runtime.symlink_to(outside, target_is_directory=True)

    assert not controller.inspect_workspace(tmp_path)["ready_for_switch"]
    assert not list(outside.iterdir())


def test_current_gate_ignores_archived_claims_but_not_transactions(tmp_path: Path) -> None:
    archive = tmp_path / ".owlbear/delivery/runtime/changes/sample/revisions/old/frontier.json"
    archive.parent.mkdir(parents=True)
    archive.write_text(json.dumps({"schema_version": 17, "bindings": [{"active_claim": {"id": "old"}}]}))
    assert controller.inspect_workspace(tmp_path)["ready_for_switch"]
    transaction = tmp_path / ".owlbear/delivery/runtime/transactions/.transactions/pending.yaml"
    transaction.parent.mkdir(parents=True)
    transaction.write_text("participants: []\n")
    assert not controller.inspect_workspace(tmp_path)["ready_for_switch"]


@pytest.mark.parametrize(("head", "changes"), [("b" * 40, ""), ("a" * 40, " M source.py")])
def test_release_check_rejects_wrong_head_and_dirty_source(tmp_path: Path, head: str, changes: str) -> None:
    with patch.object(controller, "_git", side_effect=[head, changes]), pytest.raises(ValueError, match="release"):
        controller.verify_release(tmp_path / "release", "a" * 40, tmp_path / "workspace")


def test_release_check_accepts_only_clean_detached_revision(tmp_path: Path) -> None:
    with patch.object(controller, "_git", side_effect=["a" * 40, "", ""]):
        controller.verify_release(tmp_path / "release", "a" * 40, tmp_path / "workspace")
    with (
        patch.object(controller, "_git", side_effect=["a" * 40, "", "dev"]),
        pytest.raises(ValueError, match="detached"),
    ):
        controller.verify_release(tmp_path / "release", "a" * 40, tmp_path / "workspace")


def test_acknowledged_publication_does_not_block_switch(tmp_path: Path) -> None:
    marker = tmp_path / ".owlbear/delivery/runtime/changes/sample/state-publication.json"
    marker.parent.mkdir(parents=True)
    marker.write_text('{"status":"acknowledged"}')
    assert controller.inspect_workspace(tmp_path)["ready_for_switch"]
    marker.write_text('{"status":"pending"}')
    assert not controller.inspect_workspace(tmp_path)["ready_for_switch"]


def test_schema_check_rejects_new_frontier_without_rewriting(tmp_path: Path) -> None:
    root = tmp_path / ".owlbear/delivery/runtime/changes/sample"
    root.mkdir(parents=True)
    frontier = root / "frontier.json"
    content = b'{"schema_version":999,"bindings":[]}'
    frontier.write_bytes(content)

    errors = controller.validate_state(tmp_path)

    assert any(error["path"].endswith("frontier.json") for error in errors)
    assert frontier.read_bytes() == content


def test_controller_lock_excludes_second_server(tmp_path: Path) -> None:
    with controller.controller_lock(tmp_path), pytest.raises(BlockingIOError), controller.controller_lock(tmp_path):
        pytest.fail("second controller entered")


def test_running_consumers_prevent_activation(tmp_path: Path) -> None:
    with (
        controller.controller_lock(tmp_path, shared=True),
        controller.controller_lock(tmp_path, shared=True),
        pytest.raises(BlockingIOError),
        controller.controller_lock(tmp_path),
    ):
        pytest.fail("activation overlapped a running controller")


def test_active_custody_prevents_configuration_switch(tmp_path: Path) -> None:
    config = tmp_path / ".vscode/mcp.json"
    config.parent.mkdir()
    original = b'{"servers":{"owlbear-delivery":{"command":"old"}}}'
    config.write_bytes(original)
    (tmp_path / ".owlbear/delivery/runtime/changes").mkdir(parents=True)
    blocked = {"ready_for_switch": False, "blockers": [{"reason": "active outcome claim"}]}

    with (
        patch.object(controller, "legacy_consumers", return_value=[]),
        patch.object(controller, "check_controller", return_value=blocked),
    ):
        result = controller.activate_controller(tmp_path, "a" * 40)

    assert not result["ready_for_switch"]
    assert config.read_bytes() == original
    assert not (tmp_path / ".owlbear/controllers/backups").exists()


def test_legacy_consumer_prevents_activation(tmp_path: Path) -> None:
    (tmp_path / ".owlbear/delivery/runtime/changes").mkdir(parents=True)
    with patch.object(controller, "legacy_consumers", return_value=["123"]), pytest.raises(ValueError, match="legacy"):
        controller.activate_controller(tmp_path, "a" * 40)


@pytest.mark.parametrize("changed", [False, True])
def test_activation_preserves_inputs_and_fences_changed_state(tmp_path: Path, *, changed: bool) -> None:
    workspace = tmp_path / "workspace"
    config = workspace / ".vscode/mcp.json"
    config.parent.mkdir(parents=True)
    original = {"servers": {"owlbear-delivery": {"command": "old"}, "other": {"command": "keep"}}}
    original_bytes = json.dumps(original).encode()
    config.write_bytes(original_bytes)
    delivery = workspace / ".owlbear/delivery"
    (delivery / "runtime/changes").mkdir(parents=True)
    (delivery / "packages").mkdir()
    (delivery / "config.json").write_text("{}")
    release = tmp_path / "release"
    (release / ".venv/bin").mkdir(parents=True)
    (release / ".venv/bin/python").touch()
    fingerprint = "changed" if changed else "before"
    with (
        patch.object(controller, "__file__", str(release / "setup/delivery_controller.py")),
        patch.object(controller, "legacy_consumers", return_value=[]),
        patch.object(controller, "check_controller", return_value={"ready_for_switch": True}),
        patch.object(controller, "state_fingerprint", side_effect=["before", fingerprint]),
    ):
        if changed:
            with pytest.raises(ValueError, match="changed during activation"):
                controller.activate_controller(workspace, "a" * 40)
            assert config.read_bytes() == original_bytes
        else:
            result = controller.activate_controller(workspace, "a" * 40)
            assert result["activated_configuration"]
            assert json.loads(config.read_bytes())["servers"]["other"] == original["servers"]["other"]
            assert (Path(result["backup"]) / "mcp.json").read_bytes() == original_bytes
            assert (Path(result["backup"]) / "runtime/changes").is_dir()
