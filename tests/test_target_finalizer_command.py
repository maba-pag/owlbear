"""Public command coverage for target runtime cutover."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from owlbear_delivery import (
    LegacyDisposition,
    TargetAdapterRef,
    TargetAuthority,
    TargetCutoverClassification,
    TargetCutoverReadiness,
    TargetCutoverRequest,
    TargetCutoverSource,
    TargetCutoverSubjectKind,
    authorize_target_mutation,
    inventory_legacy_source,
    target_authority_digest,
)

_REPO_ROOT = Path(__file__).parent.parent
_COMMAND_PATH = _REPO_ROOT / "setup" / "finalize.py"
_SPEC = importlib.util.spec_from_file_location("owlbear_target_finalize", _COMMAND_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
_COMMAND = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_COMMAND)
_REVISION = "a" * 64


def _request(workspace: Path) -> TargetCutoverRequest:
    source = workspace / ".owlbear/kanban"
    source.mkdir(parents=True)
    (source / "current.json").write_text('{"state":"current"}\n', encoding="utf-8")
    adapter = workspace / ".owlbear/adapters/delivery"
    adapter.parent.mkdir(parents=True)
    adapter.write_text("target\n", encoding="utf-8")
    authority = TargetAuthority(change_id="consumer-cutover", title="Consumer cutover")
    return TargetCutoverRequest(
        sources=(
            TargetCutoverSource(
                source_path=".owlbear/kanban",
                snapshot_name="runtime",
                expected_source_digest=inventory_legacy_source(source, (), {}).source_digest,
            ),
        ),
        snapshot_path=".owlbear/legacy/target-cutover",
        target_path=".owlbear/target",
        receipt_path=".owlbear/target-cutover.json",
        adapter_refs=(TargetAdapterRef(relative_path=".owlbear/adapters/delivery", target="target"),),
        authorities=(authority,),
        classifications=(
            TargetCutoverClassification(
                change_id=authority.change_id,
                subject_kind=TargetCutoverSubjectKind.CHANGE,
                subject_id=authority.change_id,
                disposition=LegacyDisposition.REINTRODUCE_NATIVE,
            ),
        ),
        expected_authority_digest=target_authority_digest((authority,)),
        actual_code_revision=_REVISION,
        expected_code_revision=_REVISION,
        readiness=TargetCutoverReadiness(),
        approval="ACTIVATE_TARGET_RUNTIME",
    )


def _write_request(workspace: Path, request: TargetCutoverRequest) -> Path:
    path = workspace / ".owlbear/target-cutover-request.json"
    path.write_text(request.model_dump_json(indent=2), encoding="utf-8")
    return path


def test_public_command_publishes_target_receipt_and_authority(tmp_path: Path, capsys) -> None:
    request = _request(tmp_path)
    request_path = _write_request(tmp_path, request)

    exit_code = _COMMAND.main(["--workspace", str(tmp_path), "--request", str(request_path)])

    payload = json.loads(capsys.readouterr().out)
    mutation_authority = authorize_target_mutation(tmp_path, request)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["result"]["replayed"] is False
    assert payload["result"]["receipt"] == mutation_authority.receipt.model_dump(mode="json")
    assert [item.change_id for item in mutation_authority.authorities] == ["consumer-cutover"]
    assert not (tmp_path / ".owlbear/kanban").exists()


def test_public_command_replays_the_published_cutover(tmp_path: Path, capsys) -> None:
    request_path = _write_request(tmp_path, _request(tmp_path))

    assert _COMMAND.main(["--workspace", str(tmp_path), "--request", str(request_path)]) == 0
    capsys.readouterr()
    replay_exit = _COMMAND.main(["--workspace", str(tmp_path), "--request", str(request_path)])
    replay = json.loads(capsys.readouterr().out)

    assert replay_exit == 0
    assert replay["result"]["replayed"] is True


def test_public_command_returns_typed_currentness_failure(tmp_path: Path, capsys) -> None:
    stale = _request(tmp_path).model_copy(update={"actual_code_revision": "b" * 64})
    request_path = _write_request(tmp_path, stale)

    exit_code = _COMMAND.main(["--workspace", str(tmp_path), "--request", str(request_path)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["error"]["code"] == "ERR_TARGET_CUTOVER_CODE_STALE"
    assert (tmp_path / ".owlbear/kanban").exists()
    assert not (tmp_path / ".owlbear/target-cutover.json").exists()


def test_public_command_rejects_missing_approval_as_typed_request_failure(tmp_path: Path, capsys) -> None:
    request = _request(tmp_path).model_dump(mode="json")
    request.pop("approval")
    request_path = tmp_path / ".owlbear/target-cutover-request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")

    exit_code = _COMMAND.main(["--workspace", str(tmp_path), "--request", str(request_path)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["error"]["code"] == "ERR_TARGET_CUTOVER_REQUEST_INVALID"
    assert (tmp_path / ".owlbear/kanban").exists()


def test_public_command_rejects_missing_classification_without_publication(tmp_path: Path, capsys) -> None:
    request = _request(tmp_path).model_copy(update={"classifications": ()})
    request_path = _write_request(tmp_path, request)

    exit_code = _COMMAND.main(["--workspace", str(tmp_path), "--request", str(request_path)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["error"]["code"] == "ERR_TARGET_CUTOVER_UNCLASSIFIED"
    assert (tmp_path / ".owlbear/kanban/current.json").is_file()
    assert not (tmp_path / ".owlbear/target-cutover.json").exists()
