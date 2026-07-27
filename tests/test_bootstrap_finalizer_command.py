"""Public command coverage for bootstrap carrier finalization."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from owlbear_kanban import (
    BootstrapFinalizationReadiness,
    BootstrapFinalizationRequest,
    LegacyActiveItem,
    LegacyDisposition,
    inventory_legacy_source,
)

_REPO_ROOT = Path(__file__).parent.parent
_COMMAND_PATH = _REPO_ROOT / "setup" / "finalize.py"
_SPEC = importlib.util.spec_from_file_location("owlbear_bootstrap_finalize", _COMMAND_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
_COMMAND = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_COMMAND)
_DIGEST = "a" * 64


def _request(workspace: Path) -> BootstrapFinalizationRequest:
    source = workspace / ".owlbear/kanban"
    (source / "tasks").mkdir(parents=True)
    (source / "tasks/1-active.md").write_text("active\n", encoding="utf-8")
    carrier = workspace / ".vscode/legacy-mcp.json"
    carrier.parent.mkdir()
    carrier.write_text("{}\n", encoding="utf-8")
    active_items = (LegacyActiveItem(item_id="task:1", relative_path="tasks/1-active.md"),)
    dispositions = {"task:1": LegacyDisposition.REINTRODUCE_NATIVE}
    source_digest = inventory_legacy_source(source, active_items, dispositions).source_digest
    return BootstrapFinalizationRequest(
        source_path=".owlbear/kanban",
        sibling_carrier_path=".vscode/legacy-mcp.json",
        snapshot_path=".owlbear/legacy/kanban-final",
        receipt_path=".owlbear/legacy/bootstrap-finalization.json",
        active_items=active_items,
        dispositions=dispositions,
        expected_source_digest=source_digest,
        expected_delivery_digest=_DIGEST,
        actual_delivery_digest=_DIGEST,
        expected_code_revision=_DIGEST,
        actual_code_revision=_DIGEST,
        approval="FINALIZE_BOOTSTRAP_CARRIER",
        readiness=BootstrapFinalizationReadiness(terminal=True),
    )


def _write_request(workspace: Path, request: BootstrapFinalizationRequest) -> Path:
    path = workspace / "finalization-request.json"
    path.write_text(request.model_dump_json(indent=2), encoding="utf-8")
    return path


def test_public_command_returns_exact_tracked_paths(tmp_path: Path, capsys) -> None:
    request_path = _write_request(tmp_path, _request(tmp_path))

    exit_code = _COMMAND.main(["--workspace", str(tmp_path), "--request", str(request_path)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["result"]["tracked_paths"] == [
        ".owlbear/kanban",
        ".vscode/legacy-mcp.json",
        ".owlbear/legacy/kanban-final",
        ".owlbear/legacy/bootstrap-finalization.json",
    ]


def test_public_command_returns_typed_currentness_failure(tmp_path: Path, capsys) -> None:
    stale = _request(tmp_path).model_copy(update={"actual_code_revision": "b" * 64})
    request_path = _write_request(tmp_path, stale)

    exit_code = _COMMAND.main(["--workspace", str(tmp_path), "--request", str(request_path)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload == {
        "ok": False,
        "error": {
            "code": "ERR_BOOTSTRAP_FINALIZATION_CODE_STALE",
            "detail": "code does not match the expected revision",
        },
    }
    assert (tmp_path / ".owlbear/kanban").exists()
    assert not (tmp_path / ".owlbear/legacy").exists()


def test_public_command_rejects_missing_approval_as_typed_request_failure(tmp_path: Path, capsys) -> None:
    request = _request(tmp_path).model_dump(mode="json")
    request.pop("approval")
    request_path = tmp_path / "finalization-request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")

    exit_code = _COMMAND.main(["--workspace", str(tmp_path), "--request", str(request_path)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "ERR_BOOTSTRAP_FINALIZATION_REQUEST_INVALID"
    assert (tmp_path / ".owlbear/kanban").exists()
