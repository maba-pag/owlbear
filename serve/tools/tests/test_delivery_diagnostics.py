"""Focused contracts for the stdlib-only offline Delivery diagnostic."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

import pytest
from pydantic import BaseModel, ValidationError

import owlbear_tools.delivery_diagnostics as diagnostics
from owlbear_delivery import delivery_runtime, state_formats
from owlbear_delivery.change_workspace import ChangeContinuationAction, ChangeDirectOperation
from owlbear_delivery.delivery_admission import DeliveryAdmissionReceipt
from owlbear_delivery.delivery_runtime import (
    CompletedOutcomeRepairReceipt,
    DeliveryCommandResult,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryPendingStatePublication,
    DeliveryResultCandidate,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
)
from owlbear_delivery.merge_approval import MergeAttemptRecord
from owlbear_delivery.portfolio_application import DeliveryEngineActionResult
from owlbear_delivery.recovery import (
    RecoveryEvidence,
    RecoveryIntent,
    RecoveryInvocation,
    RecoveryReceipt,
    RetryAttempt,
    RetryAttemptOutcome,
    RetryLedgerSummary,
    RetryOwnerResult,
    RetryRepairBinding,
)
from owlbear_delivery.target_contract import DeliveryContract
from owlbear_delivery.worker_stall import DeliveryClaimIssuer, WindowHostIdentity
from owlbear_tools.delivery_diagnostics import (
    MAX_ENTRIES,
    MAX_RECORD_BYTES,
    inspect_delivery,
    main,
)

# Private inventory tables are the drift-guard subject for owner-model alignment.
_RECORD_VERSIONS = diagnostics._CHANGE_RECORD_VERSIONS  # noqa: SLF001
_HISTORICAL_KINDS = diagnostics._HISTORICAL_CHANGE_KINDS  # noqa: SLF001
_VERSIONLESS_FIELDS = diagnostics._VERSIONLESS_REQUIRED_FIELDS  # noqa: SLF001


def _root(tmp_path: Path) -> Path:
    delivery = tmp_path / ".owlbear/delivery"
    (delivery / "runtime/changes").mkdir(parents=True)
    (delivery / "runtime/coordination/changes").mkdir(parents=True)
    (delivery / "runtime/host.json").write_text(
        '{"schema_version":1,"execution_capacity":3,"claim_timeout_seconds":3600}\n', encoding="utf-8"
    )
    (delivery / "config.json").write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"safe/project"}\n',
        encoding="utf-8",
    )
    (delivery / "runtime/format.json").write_text('{"format":3}\n', encoding="utf-8")
    return tmp_path


def _add_change_authority(root: Path, change_id: str) -> Path:
    change = root / ".owlbear/delivery/runtime/changes" / change_id
    change.mkdir(parents=True, exist_ok=True)
    (change / "frontier.json").write_bytes(b'{"schema_version":19,"bindings":[]}\n')
    coordination = root / ".owlbear/delivery/runtime/coordination/changes" / f"{change_id}.json"
    coordination.write_text(
        json.dumps({"schema_version": 2, "change_id": change_id}) + "\n",
        encoding="utf-8",
    )
    snapshot = root / ".owlbear/delivery/state" / change_id
    snapshot.mkdir(parents=True)
    (snapshot / "snapshot.json").write_bytes(b'{"schema_version":3,"frontier":{}}\n')
    return change


def _complete_root(tmp_path: Path) -> Path:
    root = _root(tmp_path)
    _add_change_authority(root, "example")
    return root


def _write_claim_issuer(change: Path, window: WindowHostIdentity | None) -> DeliveryClaimIssuer:
    issuer = DeliveryClaimIssuer(
        change_id="example",
        outcome_id="OUT-001",
        attempt_id="builder-attempt-1",
        claim_id="claim-1",
        role="builder",
        window=window,
        issued_at="2026-10-02T00:00:00+00:00",
    )
    issuer_path = change / "claim-issuers" / f"{issuer.attempt_id}.json"
    issuer_path.parent.mkdir(parents=True)
    issuer_path.write_bytes(_canonical(issuer))
    return issuer


def _run_cli(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    script = Path(__file__).parents[1] / "src/owlbear_tools/delivery_diagnostics.py"
    isolated_runner = (
        "import importlib.abc,runpy,sys\n"
        "class Blocker(importlib.abc.MetaPathFinder):\n"
        " def find_spec(self,fullname,path=None,target=None):\n"
        "  blocked={'owlbear','owlbear_delivery','owlbear_delivery_mcp',\n"
        "   'owlbear_cockpit','fastapi','pydantic','uvicorn','mcp','fastmcp'}\n"
        "  if fullname.split('.')[0] in blocked:\n"
        "   raise ImportError('blocked unavailable package')\n"
        "sys.meta_path.insert(0,Blocker())\n"
        "target=sys.argv[1]\n"
        "sys.argv = [target, *sys.argv[2:]]\n"
        "runpy.run_path(target,run_name='__main__')\n"
    )
    return subprocess.run(  # noqa: S603 - executable and arguments are fixed by this test
        [sys.executable, "-I", "-B", "-c", isolated_runner, os.fspath(script), *arguments],
        cwd=root if root.is_dir() else root.parent,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


@pytest.mark.parametrize("failure", [FileNotFoundError, PermissionError])
@pytest.mark.parametrize("invocation", [("text", False), ("text", True), ("json", False), ("json", True)])
def test_unavailable_cwd_returns_redacted_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: type[OSError],
    invocation: tuple[str, bool],
) -> None:
    output_format, relative_root = invocation
    root = _root(tmp_path)
    arguments = ["inspect", "--format", output_format]
    if relative_root:
        arguments.extend(["--project-root", "relative-project"])

    def unavailable() -> Path:
        message = "private-cwd-detail"
        raise failure(message)

    with monkeypatch.context() as context:
        context.setattr(Path, "cwd", unavailable)
        exit_code = main(arguments)
        explicit = inspect_delivery(root)
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.err == ""
    assert "private-cwd-detail" not in captured.out
    assert "ROOT_UNAVAILABLE" in captured.out
    assert "PENDING_EFFECTS_UNKNOWN" in captured.out
    if output_format == "json":
        result = json.loads(captured.out)
        assert result["status"] == "unavailable"
        assert result["inspection_complete"] is False
        assert result["writes_performed"] is False
        assert result["bytes_inspected"] == 0
        assert result["records"] == []
    else:
        assert "status: unavailable" in captured.out
        assert "writes_performed: false" in captured.out
    assert explicit["status"] == "healthy-structure"


def test_valid_structure_is_bounded_and_healthy(tmp_path: Path) -> None:
    root = _root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    change.mkdir()
    (change / "frontier.json").write_text('{"schema_version":19,"bindings":[]}\n', encoding="utf-8")
    coordination = root / ".owlbear/delivery/runtime/coordination/changes/example.json"
    coordination.write_text('{"schema_version":2,"change_id":"example"}\n', encoding="utf-8")
    snapshot = root / ".owlbear/delivery/state/example"
    snapshot.mkdir(parents=True)
    (snapshot / "snapshot.json").write_text('{"schema_version":3,"frontier":{}}\n', encoding="utf-8")

    result = inspect_delivery(root)

    assert result["status"] == "healthy-structure"
    assert result["writes_performed"] is False
    assert all(
        result["versions"][key] == value
        for key, value in {"config": 2, "coordination": 2, "frontier": 19, "host": 1, "snapshot": 3}.items()
    )
    assert result["versions"]["python"]["major"] >= 3
    assert result["counts"]["frontier"] == 1
    assert result["maintenance_prompt"]
    assert result["truncated"] is False
    config = next(record for record in result["records"] if record["kind"] == "config")
    assert config["status"] == "supported"
    assert config["schema_version"] == 2


def test_malformed_retry_ledger_current_is_degraded_and_redacted(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    current = root / ".owlbear/delivery/runtime/changes/example/retry-ledger/current.json"
    current.parent.mkdir(parents=True)
    current.write_text('{"schema_version":1,"private":"LEDGER-SECRET"', encoding="utf-8")

    completed = _run_cli(root, "inspect", "--project-root", os.fspath(root), "--format", "json")

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["status"] == "degraded"
    assert "RETRY_LEDGER_MALFORMED" in result["diagnostic_codes"]
    assert any(
        record["locator"] == ".owlbear/delivery/runtime/changes/<redacted>/retry-ledger/current.json"
        for record in result["records"]
    )
    assert "LEDGER-SECRET" not in completed.stdout + completed.stderr
    assert result["writes_performed"] is False


def test_unsupported_retry_ledger_schema_is_reported_without_content(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    current = root / ".owlbear/delivery/runtime/changes/example/retry-ledger/current.json"
    current.parent.mkdir(parents=True)
    current.write_text('{"schema_version":99,"private":"VERSION-SECRET"}\n', encoding="utf-8")

    completed = _run_cli(root, "inspect", "--project-root", os.fspath(root), "--format", "json")

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["status"] == "unsupported"
    assert "RETRY_LEDGER_UNSUPPORTED" in result["diagnostic_codes"]
    retry_record = next(record for record in result["records"] if record["kind"] == "retry_ledger")
    assert retry_record["status"] == "newer"
    assert "VERSION-SECRET" not in completed.stdout + completed.stderr


def test_malformed_recovery_receipt_is_degraded_and_redacted(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    receipt = root / ".owlbear/delivery/runtime/changes/example/recovery-receipts/" / ("a" * 64) / "receipt.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text('{"schema_version":1,"private":"RECOVERY-SECRET"', encoding="utf-8")

    result = inspect_delivery(root)
    output = json.dumps(result)

    assert result["status"] == "degraded"
    assert "RECOVERY_RECEIPT_MALFORMED" in result["diagnostic_codes"]
    assert any(
        record["locator"] == ".owlbear/delivery/runtime/changes/<redacted>/recovery-receipts/<opaque>/receipt.json"
        for record in result["records"]
    )
    assert "RECOVERY-SECRET" not in output
    assert result["writes_performed"] is False


def test_change_scoped_records_are_recognized_and_read_only(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    digest = "a" * 64
    records = (
        change / "recovery-receipts" / digest / "intent.json",
        change / "recovery-receipts" / digest / "evidence.json",
        change / "recovery-receipts" / digest / "receipt.json",
        change / "retry-ledger/current.json",
        change / "retry-ledger/attempts/attempt-1.json",
        change / "retry-ledger/outcomes" / f"{digest}.json",
        change / "retry-ledger/repair-bindings" / f"{digest}.json",
        change / "retry-ledger/owner-results/attempt-1.json",
        change / "planning-pause-receipts/OUT-001" / f"{digest}.json",
        change / "planning-retry-receipts/OUT-001" / f"{digest}.json",
        change / "builder-invocation-receipts" / f"{digest}.json",
        change / "builder-plan-promotion-receipts" / f"{digest}.json",
        change / "builder-request-resolution-receipts" / f"{digest}.json",
        change / "builder-handoff-change-intent-receipts" / digest / "head.json",
        change / "builder-handoff-change-intent-receipts" / digest / f"{digest}.json",
    )
    for path in records:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"schema_version":1}\n', encoding="utf-8")

    def snapshot_tree() -> tuple[list[str], dict[str, bytes]]:
        members = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
        contents = {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}
        return members, contents

    before = snapshot_tree()
    result = inspect_delivery(root)
    after = snapshot_tree()

    assert result["status"] == "healthy-structure"
    assert result["inspection_complete"] is True
    assert result["writes_performed"] is False
    assert result["bytes_inspected"] <= 8 * 1024 * 1024
    assert len(result["records"]) >= len(records)
    assert before == after


def _canonical(model: BaseModel) -> bytes:
    return (json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()


def _promoted_result_candidate(change_id: str) -> DeliveryResultCandidate:
    commit = "1" * 40
    observed_at = datetime(2026, 8, 11, 12, tzinfo=UTC)
    task = DeliveryTaskDefinition(
        task_id="TASK-001",
        outcome_id="OUT-001",
        plan_scope_id="SCOPE-001",
        title="Diagnose runtime receipts",
        result="A normal promoted result receipt.",
        commitment_ids=("COM-001",),
        dependency_ids=(),
        required_outputs=("Result receipt",),
        maintained_surfaces=("delivery_diagnostics.py",),
        constraints=("Read only.",),
        exclusions=("No repair.",),
        acceptance_observations=("Receipt is recognized.",),
        proof_boundaries=("delivery-diagnose",),
    )
    result = DeliveryTaskResult(
        result_id="result-001",
        change_id=change_id,
        authority_digest="2" * 64,
        task_id=task.task_id,
        task_digest=task.digest,
        completed_commit=commit,
        observations=(
            DeliveryObservationReceipt.create(
                DeliveryObservation(
                    change_id=change_id,
                    task_or_finalization_id=task.task_id,
                    exact_commit=commit,
                    observation_kind="pytest",
                    procedure="diagnostic fixture",
                    result=DeliveryCommandResult(exit_status=0),
                    observer_or_runner_identity="pytest",
                    observed_at=observed_at,
                )
            ),
        ),
        review=DeliveryReviewReceipt.create(
            DeliveryReview(
                review_mode="task",
                exact_commit=commit,
                author_id="diagnostic fixture author",
                reviewer_id="diagnostic fixture reviewer",
                evidence=("The fixture result is exact.",),
                reviewed_at=observed_at,
            )
        ),
    )
    digest = hashlib.sha256(_canonical(result)).hexdigest()
    return DeliveryResultCandidate(candidate_id=f"result-{digest}", claim_id="claim-1", digest=digest, result=result)


def test_normal_result_promotion_receipts_are_healthy(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    candidate = _promoted_result_candidate("example")
    receipt = change / "result-receipts/OUT-001" / f"{candidate.digest}.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_bytes(_canonical(candidate))
    pending = DeliveryPendingStatePublication.pending("3" * 64, "4" * 64)
    (change / "state-publication.json").write_bytes(_canonical(pending))

    completed = _run_cli(root, "inspect", "--project-root", os.fspath(root), "--format", "json")

    assert completed.returncode == 0, completed.stdout
    result = json.loads(completed.stdout)
    assert result["status"] == "healthy-structure"
    assert result["inspection_complete"] is True
    assert result["pending_effects"] is False
    statuses = {record["kind"]: record["status"] for record in result["records"]}
    assert statuses["result_receipt"] == "supported"
    assert statuses["state_publication"] == "supported"


def _continuation_action(change_id: str, *, operation_id: str | None = None) -> ChangeContinuationAction:
    return ChangeContinuationAction(
        operation_id=operation_id or f"continue-{'5' * 64}",
        change_id=change_id,
        kind="reconcile-checkpoint",
        contract_digest="6" * 64,
        frontier_digest="7" * 64,
        exact_head="8" * 40,
        target_head="9" * 40,
        host_id="host-1",
        session_id="session-1",
        acquired_at="2026-08-11T12:00:00+00:00",
    )


def _write_every_change_family(change: Path) -> dict[str, int]:
    """Write one owner-shaped record per runtime family; return the expected kind counts."""
    digest = "a" * 64
    other = "b" * 64
    candidate = _promoted_result_candidate(change.name)
    action = _continuation_action(change.name)
    engine_result = DeliveryEngineActionResult(action=action, kind="stale", reason_code="readiness-changed")
    preservation = change / "recovery-receipts" / digest / "preservation"
    restoration = preservation / "restoration" / digest
    v1 = b'{"schema_version":1}\n'
    _write_claim_issuer(change, WindowHostIdentity(pid=4321, create_time=123.5, name="builder"))
    records: dict[Path, bytes] = {
        change / "contract.json": json.dumps({"schema_version": 2, "change_id": change.name}).encode() + b"\n",
        change / "admission.json": v1,
        change / "state-publication.json": _canonical(DeliveryPendingStatePublication.pending(digest, other)),
        change / "revisions" / digest / "contract.json": b'{"schema_version":2}\n',
        change / "revisions" / digest / "frontier.json": b'{"schema_version":17,"bindings":[]}\n',
        change / "revisions" / digest / "admission.json": v1,
        change / "result-receipts/OUT-001" / f"{candidate.digest}.json": _canonical(candidate),
        change / "action-receipts" / action.operation_id / "intent.json": _canonical(action),
        change / "action-receipts" / action.operation_id / "started.json": _canonical(action),
        change / "action-receipts" / action.operation_id / "result.json": (
            engine_result.model_dump_json() + "\n"
        ).encode(),
        change / "action-receipts" / f"direct-{digest}" / "started.json": v1,
        change / "action-receipts" / f"direct-{digest}" / "finished.json": v1,
        change / "invocations" / f"{digest}.json": v1,
        change / "recovery-receipts" / digest / "intent.json": v1,
        change / "recovery-receipts" / digest / "evidence.json": v1,
        change / "recovery-receipts" / digest / "receipt.json": v1,
        preservation / "manifest.json": b'{"schema_version":1,"objects":[]}\n',
        preservation / "objects" / f"{other}.raw": b"\x00opaque preserved bytes",
        restoration / "intent.json": v1,
        restoration / "result.json": v1,
        restoration / "failure.json": v1,
        restoration / "paths" / other / "intent.json": v1,
        restoration / "paths" / other / "result.json": v1,
        restoration / "paths" / other / "staging.json": v1,
        change / "retry-ledger/current.json": v1,
        change / "retry-ledger/attempts/builder-claim:attempt.1.json": v1,
        change / "retry-ledger/outcomes" / f"{digest}.json": v1,
        change / "retry-ledger/repair-bindings" / f"{digest}.json": v1,
        change / "retry-ledger/owner-results/builder-claim:attempt.1.json": v1,
        change / "planning-pause-receipts/OUT-001" / f"{digest}.json": v1,
        change / "planning-retry-receipts/OUT-001" / f"{digest}.json": v1,
        change / "builder-invocation-receipts" / f"{digest}.json": v1,
        change / "builder-plan-promotion-receipts" / f"{digest}.json": v1,
        change / "builder-request-resolution-receipts" / f"{digest}.json": v1,
        change / "builder-handoff-change-intent-receipts" / digest / "head.json": v1,
        change / "builder-handoff-change-intent-receipts" / digest / f"{other}.json": v1,
        change / "merge-attempts" / f"{digest}.json": v1,
    }
    for path, content in records.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return {
        "contract": 1,
        "admission": 1,
        "claim_issuer": 1,
        "merge_attempt": 1,
        "state_publication": 1,
        "revision_record": 3,
        "result_receipt": 1,
        "action_intent": 1,
        "action_started": 1,
        "action_result": 1,
        "direct_operation": 2,
        "recovery_invocation": 1,
        "recovery_intent": 1,
        "recovery_evidence": 1,
        "recovery_receipt": 1,
        "preservation_manifest": 1,
        "preservation_object": 1,
        "restoration_record": 6,
        "retry_ledger": 1,
        "retry_attempt": 1,
        "retry_outcome": 1,
        "retry_repair_binding": 1,
        "retry_owner_result": 1,
        "planning_pause_receipt": 1,
        "planning_retry_receipt": 1,
        "builder_invocation_receipt": 1,
        "builder_plan_promotion_receipt": 1,
        "builder_request_resolution_receipt": 1,
        "builder_handoff_change_intent_head": 1,
        "builder_handoff_change_intent_receipt": 1,
    }


def _add_action_receipt_volume(change: Path, count: int, *, payload_marker: str | None = None) -> None:
    for index in range(count):
        operation_id = f"continue-{index:064x}"
        action = _continuation_action(change.name, operation_id=operation_id)
        action_result = DeliveryEngineActionResult(action=action, kind="stale", reason_code="readiness-changed")
        receipt = change / "action-receipts" / operation_id
        receipt.mkdir(parents=True)
        (receipt / "intent.json").write_bytes(_canonical(action))
        (receipt / "started.json").write_bytes(_canonical(action))
        result_bytes = _canonical(action_result)
        if payload_marker is not None and index == 0:
            result_value = json.loads(result_bytes)
            result_value["private"] = payload_marker
            result_bytes = (json.dumps(result_value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        (receipt / "result.json").write_bytes(result_bytes)


def test_dense_selected_change_is_healthy_and_ignores_malformed_siblings(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    _write_every_change_family(change)
    _add_action_receipt_volume(change, 22)
    sibling = _add_change_authority(root, "sibling")
    (sibling / "frontier.json").write_text(
        '{"schema_version":99,"private":"SIBLING-SECRET"}\n',
        encoding="utf-8",
    )

    entry_count = len(list(change.rglob("*")))
    completed = _run_cli(
        root,
        "inspect",
        "--project-root",
        os.fspath(root),
        "--change-id",
        "example",
        "--format",
        "json",
    )

    assert 150 <= entry_count <= 200
    assert completed.returncode == 0, completed.stdout
    result = json.loads(completed.stdout)
    assert result["status"] == "healthy-structure"
    assert result["inspection_complete"] is True
    assert result["change_scope"] == "selected"
    assert result["truncated"] is False
    assert result["diagnostic_codes"] == []
    assert result["counts"]["frontier"] == 1
    assert sum(record["kind"] == "retry_ledger" for record in result["records"]) == 1
    assert "FRONTIER_UNSUPPORTED" not in result["diagnostic_codes"]
    assert "SIBLING-SECRET" not in completed.stdout
    assert "sibling" not in completed.stdout


def test_portfolio_truncation_keeps_current_records_ahead_of_receipts(tmp_path: Path) -> None:
    root = _root(tmp_path)
    for change_id in ("change-a", "change-b", "change-c"):
        change = _add_change_authority(root, change_id)
        _write_every_change_family(change)
        _add_action_receipt_volume(change, 30, payload_marker="PORTFOLIO-RECEIPT-SECRET")

    completed = _run_cli(root, "inspect", "--project-root", os.fspath(root), "--format", "json")

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["status"] == "degraded"
    assert result["inspection_complete"] is False
    assert result["truncated"] is True
    assert "ENTRY_LIMIT_EXCEEDED" in result["diagnostic_codes"]
    assert "PENDING_EFFECTS_UNKNOWN" in result["diagnostic_codes"]
    assert result["counts"]["frontier"] == 3
    assert sum(record["kind"] == "retry_ledger" for record in result["records"]) == 3
    assert "rerun" in result["maintenance_prompt"].lower()
    assert "--change-id <CHANGE_ID>" in result["maintenance_prompt"]
    assert "Do not manually edit" in result["maintenance_prompt"]
    assert "PORTFOLIO-RECEIPT-SECRET" not in completed.stdout

    text = _run_cli(root, "inspect", "--project-root", os.fspath(root), "--format", "text")
    assert text.returncode == 1
    assert "--change-id <CHANGE_ID>" in text.stdout
    assert "rerun" in text.stdout.lower()
    assert "PORTFOLIO-RECEIPT-SECRET" not in text.stdout


def test_many_change_current_records_obey_entry_budget(tmp_path: Path) -> None:
    root = _root(tmp_path)
    changes = root / ".owlbear/delivery/runtime/changes"
    for index in range(300):
        change = changes / f"change-{index:03}"
        (change / "retry-ledger").mkdir(parents=True)
        (change / "frontier.json").write_bytes(b'{"schema_version":19,"bindings":[]}\n')
        (change / "retry-ledger/current.json").write_bytes(b'{"schema_version":1}\n')

    completed = _run_cli(root, "inspect", "--project-root", os.fspath(root), "--format", "json")

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["truncated"] is True
    assert "ENTRY_LIMIT_EXCEEDED" in result["diagnostic_codes"]
    assert len(result["records"]) <= MAX_ENTRIES
    assert sum(record["kind"] in {"frontier", "retry_ledger"} for record in result["records"]) <= MAX_ENTRIES
    assert "rerun" in result["maintenance_prompt"].lower()
    assert "--change-id <CHANGE_ID>" in result["maintenance_prompt"]


def test_every_runtime_change_family_is_recognized_and_healthy(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    expected = _write_every_change_family(root / ".owlbear/delivery/runtime/changes/example")

    completed = _run_cli(root, "inspect", "--project-root", os.fspath(root), "--format", "json")

    assert completed.returncode == 0, completed.stdout
    result = json.loads(completed.stdout)
    assert result["status"] == "healthy-structure"
    assert result["inspection_complete"] is True
    assert result["pending_effects"] is False
    assert result["diagnostic_codes"] == []
    observed: dict[str, int] = {}
    for record in result["records"]:
        if record["kind"] in expected:
            assert record["status"] in {"supported", "observed-opaque"}, record
            observed[record["kind"]] = observed.get(record["kind"], 0) + 1
    assert observed == expected
    assert result["counts"]["change_records"] == sum(expected.values())
    assert set(expected) == {*_RECORD_VERSIONS, *_HISTORICAL_KINDS, "preservation_object"}
    assert b"opaque preserved bytes" not in completed.stdout.encode()


def test_null_window_claim_issuer_is_healthy(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    issuer = _write_claim_issuer(change, None)

    result = inspect_delivery(root)

    assert result["status"] == "healthy-structure"
    assert any(record["kind"] == "claim_issuer" and record["status"] == "supported" for record in result["records"])
    assert issuer.window is None


def test_claim_issuer_requires_window_key(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    issuer = _write_claim_issuer(change, None)
    issuer_path = change / "claim-issuers" / f"{issuer.attempt_id}.json"
    issuer_record = issuer.model_dump(mode="json")
    del issuer_record["window"]
    issuer_path.write_text(json.dumps(issuer_record) + "\n", encoding="utf-8")

    result = inspect_delivery(root)

    assert result["status"] == "degraded"
    assert "CLAIM_ISSUER_MALFORMED" in result["diagnostic_codes"]


@pytest.mark.parametrize(
    "window",
    [
        {"pid": True, "create_time": 12.5, "name": "WINDOW-NAME-SECRET"},
        {"pid": 1, "create_time": 12.5, "name": "WINDOW-NAME-SECRET"},
        {"pid": 987654321, "create_time": "12.5", "name": "WINDOW-NAME-SECRET"},
        {"pid": 987654321, "create_time": -1.0, "name": "WINDOW-NAME-SECRET"},
        {"pid": 987654321, "create_time": float("nan"), "name": "WINDOW-NAME-SECRET"},
        {"pid": 987654321, "create_time": float("inf"), "name": "WINDOW-NAME-SECRET"},
        {"pid": 987654321, "create_time": 12.5, "name": 987654321},
        {"pid": 987654321, "create_time": 12.5, "name": ""},
        {
            "pid": 987654321,
            "create_time": 12.5,
            "name": "WINDOW-NAME-SECRET",
            "extra": "EXTRA-SECRET",
        },
        {"pid": 987654321, "create_time": 12.5},
        [987654321, "WINDOW-NAME-SECRET"],
    ],
)
def test_malformed_claim_issuer_window_is_degraded_and_redacted(tmp_path: Path, window: object) -> None:
    root = _complete_root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    issuer = _write_claim_issuer(change, WindowHostIdentity(pid=4321, create_time=123.5, name="builder"))
    issuer_path = change / "claim-issuers" / f"{issuer.attempt_id}.json"
    issuer_record = issuer.model_dump(mode="json")
    issuer_record["window"] = window
    issuer_path.write_text(json.dumps(issuer_record) + "\n", encoding="utf-8")

    result = inspect_delivery(root)
    encoded = json.dumps(result)

    assert result["status"] == "degraded"
    assert "CLAIM_ISSUER_MALFORMED" in result["diagnostic_codes"]
    assert "987654321" not in encoded
    assert "WINDOW-NAME-SECRET" not in encoded
    assert "EXTRA-SECRET" not in encoded


@pytest.mark.parametrize(
    "create_time", [1.5, 0, 0.0, 10, 10**300, 10**400, -1, True, "1", float("inf"), float("nan")], ids=repr
)
def test_claim_issuer_window_create_time_matches_the_runtime_model(tmp_path: Path, create_time: object) -> None:
    root = _complete_root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    issuer = _write_claim_issuer(change, WindowHostIdentity(pid=4321, create_time=123.5, name="builder"))
    issuer_path = change / "claim-issuers" / f"{issuer.attempt_id}.json"
    issuer_record = issuer.model_dump(mode="json")
    issuer_record["window"]["create_time"] = create_time
    issuer_path.write_text(json.dumps(issuer_record) + "\n", encoding="utf-8")
    try:
        DeliveryClaimIssuer.model_validate_json(issuer_path.read_bytes())
    except ValidationError:
        runtime_accepts = False
    else:
        runtime_accepts = True
    try:
        WindowHostIdentity.model_validate(issuer_record["window"])
    except ValidationError:
        model_accepts = False
    else:
        model_accepts = True
    assert model_accepts is runtime_accepts

    result = inspect_delivery(root)

    assert ("CLAIM_ISSUER_MALFORMED" not in result["diagnostic_codes"]) is runtime_accepts


def test_retired_runtime_hosts_directory_is_not_traversed(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    baseline = inspect_delivery(root)
    hosts = root / ".owlbear/delivery/runtime/hosts"
    hosts.mkdir()
    (hosts / f"{'a' * 32}.lock").write_text("HOST-LOCK-SECRET", encoding="utf-8")

    result = inspect_delivery(root)
    encoded = json.dumps(result)

    assert result["status"] == baseline["status"]
    assert result["diagnostic_codes"] == baseline["diagnostic_codes"]
    assert "host_locks" not in result["counts"]
    assert "HOST-LOCK-SECRET" not in encoded


def test_malformed_result_receipt_is_degraded_with_kind_code(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    receipt = root / ".owlbear/delivery/runtime/changes/example/result-receipts/OUT-001" / f"{'c' * 64}.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text('{"candidate_id":"result-x","claim_id":"RESULT-SECRET"}\n', encoding="utf-8")

    completed = _run_cli(root, "inspect", "--project-root", os.fspath(root), "--format", "json")

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["status"] == "degraded"
    assert "RESULT_RECEIPT_MALFORMED" in result["diagnostic_codes"]
    assert "UNRECOGNIZED_CHANGE_ENTRY" not in result["diagnostic_codes"]
    assert result["pending_effects"] == "unknown"
    assert "RESULT-SECRET" not in completed.stdout


def test_versioned_result_receipt_is_unsupported_not_accepted(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    receipt = root / ".owlbear/delivery/runtime/changes/example/result-receipts/OUT-001" / f"{'c' * 64}.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(
        '{"schema_version":2,"candidate_id":"a","claim_id":"b","digest":"c","result":{}}\n', encoding="utf-8"
    )

    result = inspect_delivery(root)

    assert result["status"] == "unsupported"
    assert "RESULT_RECEIPT_UNSUPPORTED" in result["diagnostic_codes"]


def test_change_record_versions_match_owner_models() -> None:
    owners: dict[str, tuple[type[BaseModel], ...]] = {
        "contract": (DeliveryContract,),
        "admission": (DeliveryAdmissionReceipt,),
        "claim_issuer": (DeliveryClaimIssuer,),
        "merge_attempt": (MergeAttemptRecord,),
        "state_publication": (DeliveryPendingStatePublication,),
        "result_receipt": (DeliveryResultCandidate,),
        "action_intent": (ChangeContinuationAction,),
        "action_started": (ChangeContinuationAction,),
        "action_result": (DeliveryEngineActionResult,),
        "direct_operation": (ChangeDirectOperation,),
        "recovery_invocation": (RecoveryInvocation,),
        "recovery_intent": (RecoveryIntent,),
        "recovery_evidence": (RecoveryEvidence,),
        "recovery_receipt": (RecoveryReceipt, CompletedOutcomeRepairReceipt),
        "retry_ledger": (RetryLedgerSummary,),
        "retry_attempt": (RetryAttempt,),
        "retry_outcome": (RetryAttemptOutcome,),
        "retry_repair_binding": (RetryRepairBinding,),
        "retry_owner_result": (RetryOwnerResult,),
    }
    runtime_models = vars(delivery_runtime)
    owners |= {
        kind: (runtime_models[name],)
        for kind, name in {
            "planning_pause_receipt": "_DeliveryPlanningPauseReplay",
            "planning_retry_receipt": "_DeliveryPlanningRetrySettlementReceipt",
            "builder_invocation_receipt": "_DeliveryBuilderInvocationSettlementReceipt",
            "builder_plan_promotion_receipt": "_DeliveryBuilderPlanPromotionReceipt",
            "builder_request_resolution_receipt": "_DeliveryBuilderRequestResolutionReceipt",
            "builder_handoff_change_intent_head": "_DeliveryBuilderHandoffChangeIntentHead",
            "builder_handoff_change_intent_receipt": "_DeliveryBuilderHandoffChangeIntentReceipt",
        }.items()
    }
    # These two families are dict payloads written by change_workspace with a fixed schema_version of 1.
    unmodelled = {"preservation_manifest", "restoration_record"}
    assert set(owners) | unmodelled == set(_RECORD_VERSIONS)
    for kind, models in owners.items():
        expected = _RECORD_VERSIONS[kind]
        for model in models:
            field = model.model_fields.get("schema_version")
            if expected is None:
                assert field is None, kind
                required = _VERSIONLESS_FIELDS.get(kind, {})
                assert set(required) <= {name for name, info in model.model_fields.items() if info.is_required()}
            else:
                assert field is not None, kind
                assert get_args(field.annotation) == expected, kind


def test_interrupted_change_temporaries_are_pending_opaque_not_unknown(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    (change / f".tmp-{'d' * 24}-frontier.json").write_text('{"private":"TMP-SECRET"}', encoding="utf-8")
    stage_parent = change / "recovery-receipts" / ("a" * 64) / "preservation/restoration" / ("b" * 64) / "paths"
    stage_parent = stage_parent / ("c" * 64)
    stage_parent.mkdir(parents=True)
    (stage_parent / "intent.json").write_bytes(b'{"schema_version":1}\n')
    (stage_parent / f".tmp-{'e' * 24}").write_bytes(b"TMP-SECRET")
    (stage_parent / f"stage-{'f' * 32}").symlink_to("private-link-target")

    result = inspect_delivery(root)
    encoded = json.dumps(result)

    assert result["inspection_complete"] is True
    assert result["pending_effects"] is True
    assert result["diagnostic_codes"] == ["PENDING_TRANSACTIONS"]
    assert result["counts"]["pending_transactions"] == 3
    assert {record["kind"] for record in result["records"] if record["status"] == "pending-opaque"} == {
        "change_transient",
        "restoration_stage",
    }
    assert "TMP-SECRET" not in encoded
    assert "private-link-target" not in encoded


def test_symlinked_preservation_object_is_rejected(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    objects = root / ".owlbear/delivery/runtime/changes/example/recovery-receipts" / ("a" * 64) / "preservation/objects"
    objects.mkdir(parents=True)
    (objects / f"{'b' * 64}.raw").symlink_to(tmp_path / "outside")

    result = inspect_delivery(root)

    assert "SYMLINK_REJECTED" in result["diagnostic_codes"]
    assert result["inspection_complete"] is False
    assert result["pending_effects"] == "unknown"


def test_unknown_change_entry_makes_inspection_incomplete(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    extra = root / ".owlbear/delivery/runtime/changes/example/unrecognized-secret.json"
    extra.write_text('{"private":"UNRECOGNIZED-SECRET"}\n', encoding="utf-8")

    completed = _run_cli(root, "inspect", "--project-root", os.fspath(root), "--format", "json")

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["status"] == "degraded"
    assert result["inspection_complete"] is False
    assert "UNRECOGNIZED_CHANGE_ENTRY" in result["diagnostic_codes"]
    assert result["pending_effects"] == "unknown"
    assert "unrecognized-secret" not in completed.stdout
    assert "UNRECOGNIZED-SECRET" not in completed.stdout
    assert result["writes_performed"] is False


@pytest.mark.parametrize("missing", ["coordination", "changes", "row"])
def test_valid_runtime_frontier_without_coordination_is_unknown_and_read_only(
    tmp_path: Path,
    missing: str,
) -> None:
    root = _root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    change.mkdir()
    (change / "frontier.json").write_bytes(b'{"schema_version":19,"bindings":[]}\n')
    coordination = root / ".owlbear/delivery/runtime/coordination/changes/example.json"
    if missing == "coordination":
        shutil.rmtree(coordination.parent.parent)
    elif missing == "changes":
        shutil.rmtree(coordination.parent)
    else:
        coordination.write_bytes(b'{"schema_version":2,"change_id":"example"}\n')
        coordination.unlink()

    def snapshot() -> tuple[tuple[str, bytes | None], ...]:
        return tuple(
            sorted(
                (
                    path.relative_to(root).as_posix(),
                    path.read_bytes() if path.is_file() else None,
                )
                for path in root.rglob("*")
            )
        )

    before = snapshot()
    results = (inspect_delivery(root), inspect_delivery(root, change_id="example"))
    for result in results:
        assert result["status"] == "degraded"
        assert result["inspection_complete"] is False
        assert {"COORDINATION_MISSING", "PENDING_EFFECTS_UNKNOWN"} <= set(result["diagnostic_codes"])
        assert result["pending_effects"] == "unknown"
        assert result["truncated"] is False
        assert result["writes_performed"] is False
        assert result["counts"]["frontier"] == 1
        assert result["counts"]["coordination"] == 0
        assert "CHANGE_NOT_FOUND" not in result["diagnostic_codes"]

    completed = _run_cli(root, "inspect", "--project-root", os.fspath(root), "--format", "json")
    assert completed.returncode == 1
    cli_result = json.loads(completed.stdout)
    assert cli_result["status"] == "degraded"
    assert cli_result["inspection_complete"] is False
    assert {"COORDINATION_MISSING", "PENDING_EFFECTS_UNKNOWN"} <= set(cli_result["diagnostic_codes"])
    assert cli_result["pending_effects"] == "unknown"
    assert cli_result["truncated"] is False
    assert cli_result["writes_performed"] is False
    assert "example" not in completed.stdout + completed.stderr
    assert snapshot() == before


def test_empty_runtime_without_coordination_is_not_missing_a_change(tmp_path: Path) -> None:
    root = _root(tmp_path)
    shutil.rmtree(root / ".owlbear/delivery/runtime/coordination")

    result = inspect_delivery(root)

    assert result["status"] == "healthy-structure"
    assert result["inspection_complete"] is True
    assert "COORDINATION_MISSING" not in result["diagnostic_codes"]
    assert result["pending_effects"] is False
    assert result["truncated"] is False
    assert result["writes_performed"] is False


def test_coordination_identity_mismatch_is_unknown_not_missing_and_read_only(tmp_path: Path) -> None:
    root = _root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    change.mkdir()
    (change / "frontier.json").write_bytes(b'{"schema_version":19,"bindings":[]}\n')
    coordination = root / ".owlbear/delivery/runtime/coordination/changes/example.json"
    coordination.write_bytes(b'{"schema_version":2,"change_id":"other"}\n')
    before = tuple(
        sorted(
            (path.relative_to(root).as_posix(), path.read_bytes() if path.is_file() else None)
            for path in root.rglob("*")
        )
    )

    result = inspect_delivery(root)

    after = tuple(
        sorted(
            (path.relative_to(root).as_posix(), path.read_bytes() if path.is_file() else None)
            for path in root.rglob("*")
        )
    )
    assert result["status"] == "degraded"
    assert result["inspection_complete"] is False
    assert {"COORDINATION_MALFORMED", "PENDING_EFFECTS_UNKNOWN"} <= set(result["diagnostic_codes"])
    assert "COORDINATION_MISSING" not in result["diagnostic_codes"]
    assert result["pending_effects"] == "unknown"
    assert result["writes_performed"] is False
    assert after == before


def test_listed_coordination_disappearing_at_stat_is_unknown_and_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    change.mkdir()
    (change / "frontier.json").write_bytes(b'{"schema_version":19,"bindings":[]}\n')
    coordination = root / ".owlbear/delivery/runtime/coordination/changes/example.json"
    coordination.write_bytes(b'{"schema_version":2,"change_id":"example"}\n')
    before = tuple(
        sorted(
            (path.relative_to(root).as_posix(), path.read_bytes() if path.is_file() else None)
            for path in root.rglob("*")
        )
    )
    real_stat = os.stat

    def disappear_listed_row(path, *args, **kwargs):
        if path == "example.json" and kwargs.get("dir_fd") is not None:
            raise FileNotFoundError(errno.ENOENT, "disappeared", os.fspath(path))
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(diagnostics.os, "stat", disappear_listed_row)

    result = inspect_delivery(root)

    after = tuple(
        sorted(
            (path.relative_to(root).as_posix(), path.read_bytes() if path.is_file() else None)
            for path in root.rglob("*")
        )
    )
    assert result["status"] == "degraded"
    assert result["inspection_complete"] is False
    assert "COORDINATION_MISSING" in result["diagnostic_codes"]
    assert "PENDING_EFFECTS_UNKNOWN" in result["diagnostic_codes"]
    assert result["pending_effects"] == "unknown"
    assert result["counts"]["coordination"] == 0
    assert not any(record["kind"] == "coordination" and record["status"] == "missing" for record in result["records"])
    assert result["writes_performed"] is False
    assert after == before


@pytest.mark.parametrize("symlink", ["coordination", "changes"])
def test_symlinked_coordination_is_unknown_not_missing(tmp_path: Path, symlink: str) -> None:
    root = _root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    change.mkdir()
    (change / "frontier.json").write_bytes(b'{"schema_version":19,"bindings":[]}\n')
    coordination = root / ".owlbear/delivery/runtime/coordination/changes/example.json"
    target = root / "target"
    target.mkdir()
    link = coordination.parent.parent if symlink == "coordination" else coordination.parent
    shutil.rmtree(link)
    link.symlink_to(target, target_is_directory=True)

    result = inspect_delivery(root)

    assert result["status"] == "degraded"
    assert result["inspection_complete"] is False
    assert "SYMLINK_REJECTED" in result["diagnostic_codes"]
    assert "COORDINATION_MISSING" not in result["diagnostic_codes"]
    assert result["pending_effects"] == "unknown"
    assert result["truncated"] is True
    assert result["writes_performed"] is False


@pytest.mark.parametrize(
    ("relative", "content", "code"),
    [
        (".owlbear/delivery/config.json", "{", "CONFIG_MALFORMED"),
        (".owlbear/delivery/config.json", '{"schema_version":99}', "CONFIG_UNSUPPORTED"),
        (".owlbear/delivery/runtime/changes/example/frontier.json", '{"schema_version":18}', "FRONTIER_MALFORMED"),
        (
            ".owlbear/delivery/runtime/changes/example/frontier.json",
            '{"schema_version":99,"bindings":[]}',
            "FRONTIER_UNSUPPORTED",
        ),
    ],
)
def test_malformed_and_unsupported_records_are_bounded(tmp_path: Path, relative: str, content: str, code: str) -> None:
    root = _root(tmp_path)
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    result = inspect_delivery(root)

    assert result["status"] in {"degraded", "unsupported"}
    assert code in result["diagnostic_codes"]
    assert "safe/project" not in json.dumps(result)


@pytest.mark.parametrize(
    ("relative", "content", "status", "code"),
    [
        (
            ".owlbear/delivery/runtime/changes/example/frontier.json",
            '{"schema_version":17,"bindings":[]}',
            "migration-required",
            "FRONTIER_MIGRATION_REQUIRED",
        ),
        (
            ".owlbear/delivery/state/example/snapshot.json",
            '{"schema_version":1,"frontier":{}}',
            "readable-legacy",
            None,
        ),
        (
            ".owlbear/delivery/state/example/snapshot.json",
            '{"schema_version":2,"frontier":{}}',
            "readable-legacy",
            None,
        ),
        (
            ".owlbear/delivery/runtime/changes/example/frontier.json",
            '{"schema_version":18,"bindings":[]}',
            "readable-legacy",
            None,
        ),
        (
            ".owlbear/delivery/runtime/changes/example/frontier.json",
            '{"schema_version":20,"bindings":[]}',
            "newer",
            "FRONTIER_UNSUPPORTED",
        ),
        (
            ".owlbear/delivery/runtime/changes/example/frontier.json",
            '{"schema_version":16,"bindings":[]}',
            "unsupported",
            "FRONTIER_UNSUPPORTED",
        ),
        (
            ".owlbear/delivery/runtime/coordination/changes/example.json",
            '{"schema_version":3,"change_id":"example"}',
            "newer",
            "COORDINATION_UNSUPPORTED",
        ),
        (
            ".owlbear/delivery/runtime/coordination/changes/example.json",
            '{"schema_version":1,"change_id":"example"}',
            "migration-required",
            "COORDINATION_MIGRATION_REQUIRED",
        ),
        (
            ".owlbear/delivery/runtime/changes/example/claim-issuers/attempt-1.json",
            '{"schema_version":2,"window":null}',
            "newer",
            "CLAIM_ISSUER_UNSUPPORTED",
        ),
    ],
)
def test_inspector_classifies_readable_legacy_and_newer_versions_like_the_registry(
    tmp_path: Path, relative: str, content: str, status: str, code: str | None
) -> None:
    root = _complete_root(tmp_path)
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    kind = state_formats.classify_kind(relative.removeprefix(".owlbear/delivery/"))
    assert kind is not None

    result = inspect_delivery(root)
    payload = json.loads(content)
    registry_status = state_formats.classify_version(kind, payload["schema_version"], present=True)

    statuses = [record["status"] for record in result["records"] if record["kind"] == kind.kind_id]
    assert status in statuses
    assert registry_status == {"unsupported": "unknown-version"}.get(status, status)
    if code is None:
        assert not any(item.endswith("_UNSUPPORTED") for item in result["diagnostic_codes"])
    else:
        assert code in result["diagnostic_codes"]
        assert result["status"] == ("degraded" if status == "migration-required" else "unsupported")


# Inspector record kinds mirror registry record kinds; action receipts share one registry row.
_INSPECTOR_KIND_TO_REGISTRY = {
    "action_intent": "action_receipt",
    "action_started": "action_receipt",
    "action_result": "action_receipt",
    "recovery_intent": "recovery_record",
    "recovery_evidence": "recovery_record",
    "recovery_receipt": "recovery_record",
}


def test_inspector_version_tables_mirror_the_delivery_format_registry() -> None:
    registry = {kind.kind_id: kind for kind in state_formats.RECORD_KINDS}
    current = _inspector_version_tables()
    mismatches = []
    for inspector_kind, versions in current.items():
        kind = registry[_INSPECTOR_KIND_TO_REGISTRY.get(inspector_kind, inspector_kind)]
        if isinstance(versions, int):
            legacy = diagnostics.READABLE_LEGACY_VERSIONS.get(inspector_kind, ())
            observed = (*legacy, versions)
        else:
            observed = versions or ()
        if tuple(observed) != kind.read_versions:
            mismatches.append((inspector_kind, observed, kind.read_versions))

    assert mismatches == []
    assert set(diagnostics.READABLE_LEGACY_VERSIONS) <= set(diagnostics.SUPPORTED_VERSIONS)
    assert {
        kind_id: tuple(version for version, _rewrite in registry[kind_id].rewrites)
        for kind_id in registry
        if registry[kind_id].rewrites
    } == diagnostics.MIGRATION_REQUIRED_VERSIONS
    assert diagnostics.SUPPORTED_FORMAT == state_formats.SUPPORTED_FORMAT
    assert diagnostics.MIGRATION_JOURNAL_STATES == state_formats.JOURNAL_STATES
    assert tuple(diagnostics.MIGRATION_JOURNAL_KINDS) == state_formats.JOURNAL_READ_VERSIONS
    assert {
        version: state_formats.journal_kind(
            {"schema_version": version, "kind": kind} if version > 1 else {"schema_version": version}
        )
        for version, kind in diagnostics.MIGRATION_JOURNAL_KINDS.items()
    } == diagnostics.MIGRATION_JOURNAL_KINDS


def _inspector_version_tables() -> dict[str, object]:
    return {
        **diagnostics.SUPPORTED_VERSIONS,
        **_RECORD_VERSIONS,
        **diagnostics._RUNTIME_RECORD_VERSIONS,  # noqa: SLF001
    }


def _uninspected_registry_kinds(inspector_kinds: set[str], declared: dict[str, str]) -> list[str]:
    """Return registry kinds neither version-inspected nor declared uninspectable with a reason."""
    inspected = {_INSPECTOR_KIND_TO_REGISTRY.get(kind, kind) for kind in inspector_kinds}
    return sorted(
        kind.kind_id
        for kind in state_formats.RECORD_KINDS
        if kind.kind_id not in inspected and not declared.get(kind.kind_id, "").strip()
    )


def test_every_registered_record_kind_is_version_inspected_or_declared_uninspectable() -> None:
    inspector_kinds = set(_inspector_version_tables())
    declared = diagnostics.VERSION_UNINSPECTED_KINDS
    registry_kinds = {kind.kind_id for kind in state_formats.RECORD_KINDS}

    assert _uninspected_registry_kinds(inspector_kinds, declared) == []
    assert set(declared) <= registry_kinds
    assert not set(declared) & {_INSPECTOR_KIND_TO_REGISTRY.get(kind, kind) for kind in inspector_kinds}


def test_coverage_guard_reports_an_omitted_family() -> None:
    inspector_kinds = set(_inspector_version_tables()) - {"finalizer_settlement", "completion_display"}
    declared = {**diagnostics.VERSION_UNINSPECTED_KINDS, "completion_display": " "}

    assert _uninspected_registry_kinds(inspector_kinds, declared) == ["completion_display", "finalizer_settlement"]


_JOURNAL_ID = "a" * 64


def _write_journal(
    root: Path, state: str, *, schema_version: int = 1, kind: str | None = None, truncated: bool = False
) -> None:
    journal = root / ".owlbear/delivery/runtime/migrations" / _JOURNAL_ID / "journal.json"
    journal.parent.mkdir(parents=True)
    payload: dict[str, object] = {"schema_version": schema_version, "migration_id": _JOURNAL_ID, "state": state}
    if not truncated:
        payload |= {"source_format": 1, "target_format": 1, "backup_manifest_sha256": "b" * 64, "batches": []}
        if schema_version == 2:
            payload |= {"confirmed": None, "retained": [], "steps": []}
    if kind is not None:
        payload["kind"] = kind
    journal.write_bytes((json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode())


_JOURNAL_CASES = {
    "journal-applied": ("applied", 1, None),
    "journal-verified": ("verified", 1, None),
    "journal-newer": ("applied", 3, None),
    "journal-repair-applied": ("applied", 2, "repair"),
    "journal-repair-verified": ("verified", 2, "repair"),
    "journal-v2-without-kind": ("verified", 2, None),
    "journal-v1-with-kind": ("verified", 1, "migration"),
    "journal-truncated-verified": ("verified", 1, None),
    "journal-truncated-repair-verified": ("verified", 2, "repair"),
}


@pytest.mark.parametrize(
    ("case", "codes", "gate_codes"),
    [
        ("fresh", [], []),
        ("format-0-with-records", ["FORMAT_MIGRATION_REQUIRED"], ["state-migration-required"]),
        ("format-previous-with-records", ["FORMAT_MIGRATION_REQUIRED"], ["state-migration-required"]),
        ("format-4", ["FORMAT_UNSUPPORTED"], ["state-newer-than-controller"]),
        ("journal-applied", ["MIGRATION_INCOMPLETE"], ["state-migration-incomplete"]),
        ("journal-verified", [], []),
        ("journal-newer", ["MIGRATION_JOURNAL_UNSUPPORTED"], ["state-newer-than-controller"]),
        ("journal-repair-applied", ["MIGRATION_INCOMPLETE"], ["state-migration-incomplete"]),
        ("journal-repair-verified", [], []),
        ("journal-v2-without-kind", ["MIGRATION_JOURNAL_MALFORMED"], ["state-migration-incomplete"]),
        ("journal-v1-with-kind", ["MIGRATION_JOURNAL_MALFORMED"], ["state-migration-incomplete"]),
        ("journal-truncated-verified", ["MIGRATION_JOURNAL_MALFORMED"], ["state-migration-incomplete"]),
        ("journal-truncated-repair-verified", ["MIGRATION_JOURNAL_MALFORMED"], ["state-migration-incomplete"]),
        ("namespace-file", ["MIGRATION_JOURNAL_MALFORMED"], ["state-migration-incomplete"]),
    ],
)
def test_inspector_mirrors_the_gate_format_and_journal_classification(
    tmp_path: Path, case: str, codes: list[str], gate_codes: list[str]
) -> None:
    root = _root(tmp_path) if case == "fresh" else _complete_root(tmp_path)
    runtime = root / ".owlbear/delivery/runtime"
    if case in {"fresh", "format-0-with-records"}:
        (runtime / "format.json").unlink()
    elif case == "format-previous-with-records":
        (runtime / "format.json").write_bytes(state_formats.format_marker_bytes(state_formats.SUPPORTED_FORMAT - 1))
    elif case == "format-4":
        (runtime / "format.json").write_text('{"format":4}\n', encoding="utf-8")
    elif case == "namespace-file":
        (runtime / "migrations").write_text("not a directory\n", encoding="utf-8")
    elif case.startswith("journal-"):
        state, schema_version, kind = _JOURNAL_CASES[case]
        _write_journal(root, state, schema_version=schema_version, kind=kind, truncated="truncated" in case)

    result = inspect_delivery(root)
    gate = [refusal.code for refusal in state_formats.scan_capability(root).refusals]

    assert [code for code in result["diagnostic_codes"] if code.startswith(("FORMAT_", "MIGRATION_"))] == codes
    assert gate == gate_codes
    assert result["format"]["supported"] == state_formats.SUPPORTED_FORMAT
    assert result["writes_performed"] is False


_GOLDEN = Path(__file__).parents[2] / "delivery/tests/fixtures/state_formats/golden"
_GOLDEN_RUNTIME_FAMILIES = (
    "runtime/finalization-reports",
    "runtime/proof-attempts",
    "runtime/finalizer-settlements",
    "runtime/completions",
    "runtime/publications",
    "runtime/claims",
    "packages",
)


def _copy_golden_runtime_families(root: Path) -> dict[str, str]:
    """Copy golden non-Change families into an inspector root and return locator -> registry kind."""
    delivery = root / ".owlbear/delivery"
    kinds: dict[str, str] = {}
    for family in _GOLDEN_RUNTIME_FAMILIES:
        source = _GOLDEN / family
        if not source.exists():
            continue
        shutil.copytree(source, delivery / family, dirs_exist_ok=True)
        for path in source.rglob("*"):
            if path.is_file():
                locator = path.relative_to(_GOLDEN).as_posix()
                kind = state_formats.classify_kind(locator)
                assert kind is not None, locator
                kinds[locator] = kind.kind_id
    return kinds


def test_golden_runtime_and_package_families_are_version_inspected(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    golden = _copy_golden_runtime_families(root)

    result = inspect_delivery(root)

    expected = set(golden.values())
    observed = {(record["kind"], record["status"]) for record in result["records"] if record["kind"] in expected}
    assert observed == {(kind, "supported") for kind in expected}
    assert expected >= {"finalizer_settlement", "completion_evidence", "package_manifest", "package_authority"}
    assert result["status"] == "healthy-structure", result["diagnostic_codes"]
    assert result["counts"]["runtime_records"] == len(golden)


@pytest.mark.parametrize(
    ("kind_id", "version", "status", "code"),
    [
        ("finalizer_settlement", 2, "newer", "FINALIZER_SETTLEMENT_UNSUPPORTED"),
        ("completion_evidence", 2, "newer", "COMPLETION_EVIDENCE_UNSUPPORTED"),
        ("completion_display", 0, "unsupported", "COMPLETION_DISPLAY_UNSUPPORTED"),
        ("pull_request_summary_receipt", 2, "newer", "PULL_REQUEST_SUMMARY_RECEIPT_UNSUPPORTED"),
        ("package_manifest", 2, "newer", "PACKAGE_MANIFEST_UNSUPPORTED"),
        ("proof_attempt", 1, "unsupported", "PROOF_ATTEMPT_UNSUPPORTED"),
    ],
)
def test_inspector_reports_unsupported_runtime_family_versions(
    tmp_path: Path, kind_id: str, version: int, status: str, code: str
) -> None:
    root = _complete_root(tmp_path)
    golden = _copy_golden_runtime_families(root)
    locator = next(locator for locator, kind in sorted(golden.items()) if kind == kind_id)
    path = root / ".owlbear/delivery" / locator
    payload = json.loads(path.read_bytes())
    payload["schema_version"] = version
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = inspect_delivery(root)

    statuses = [record["status"] for record in result["records"] if record["kind"] == kind_id]
    assert status in statuses
    assert code in result["diagnostic_codes"]
    assert result["status"] == "unsupported"
    registry_kind = next(kind for kind in state_formats.RECORD_KINDS if kind.kind_id == kind_id)
    registry_status = state_formats.classify_version(registry_kind, version, present=True)
    assert registry_status == {"unsupported": "unknown-version"}.get(status, status)


def test_selected_change_inspects_only_attributable_runtime_records(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    golden = _copy_golden_runtime_families(root)
    settlement = next(locator for locator, kind in golden.items() if kind == "finalizer_settlement")
    moved = root / ".owlbear/delivery" / settlement.replace("/change-a/", "/example/")
    moved.parent.mkdir(parents=True)
    payload = json.loads((root / ".owlbear/delivery" / settlement).read_bytes())
    moved.write_text(json.dumps({**payload, "schema_version": 2}), encoding="utf-8")

    result = inspect_delivery(root, "example")

    kinds = [record["kind"] for record in result["records"]]
    assert kinds.count("finalizer_settlement") == 1
    assert "FINALIZER_SETTLEMENT_UNSUPPORTED" in result["diagnostic_codes"]
    assert "branch_publication" not in kinds
    assert "completion_evidence" not in kinds


def test_missing_root_and_invalid_change_id_have_exit_two(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = inspect_delivery(tmp_path / "missing")
    assert result["status"] == "unavailable"
    assert {"ROOT_UNAVAILABLE", "PENDING_EFFECTS_UNKNOWN"} <= set(result["diagnostic_codes"])
    assert result["pending_effects"] == "unknown"
    monkeypatch.setattr("sys.argv", ["delivery-diagnose", "inspect", "--change-id", "../secret"])
    with pytest.raises(SystemExit, match="2"):
        main()


def test_project_marker_with_missing_delivery_state_is_degraded(tmp_path: Path) -> None:
    (tmp_path / ".owlbear").mkdir()

    result = inspect_delivery(tmp_path)

    assert result["status"] == "degraded"
    assert result["diagnostic_codes"] == ["DELIVERY_STATE_MISSING"]


def test_valid_project_with_missing_delivery_records_is_not_unavailable(tmp_path: Path) -> None:
    (tmp_path / ".owlbear/delivery").mkdir(parents=True)

    result = inspect_delivery(tmp_path)

    assert result["status"] == "degraded"
    assert "ROOT_UNAVAILABLE" not in result["diagnostic_codes"]
    assert "CONFIG_MISSING" in result["diagnostic_codes"]
    assert "RUNTIME_UNREADABLE" in result["diagnostic_codes"]


def test_missing_delivery_tree_is_distinct_from_unsafe_delivery_tree(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    (missing / ".owlbear").mkdir(parents=True)

    missing_result = inspect_delivery(missing)

    assert missing_result["diagnostic_codes"] == ["DELIVERY_STATE_MISSING"]
    assert missing_result["pending_effects"] is False

    unsafe = tmp_path / "unsafe"
    (unsafe / ".owlbear").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (unsafe / ".owlbear/delivery").symlink_to(outside, target_is_directory=True)

    unsafe_result = inspect_delivery(unsafe)

    assert "SYMLINK_REJECTED" in unsafe_result["diagnostic_codes"]
    assert unsafe_result["pending_effects"] == "unknown"
    assert unsafe_result["inspection_complete"] is False


def test_invalid_cli_input_uses_bounded_error_without_echo(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit, match="2"):
        main(["inspect", "--not-a-real-option", "private-input"])
    output = capsys.readouterr().out
    assert output == "ERR_INVALID_INVOCATION\n"
    assert "private-input" not in output


def test_standalone_cli_valid_text_and_json_are_isolated_and_bounded(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    before_membership = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    before_bytes = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    readonly_files = [
        root / ".owlbear/delivery/config.json",
        root / ".owlbear/delivery/runtime/host.json",
        root / ".owlbear/delivery/runtime/changes/example/frontier.json",
        root / ".owlbear/delivery/runtime/coordination/changes/example.json",
        root / ".owlbear/delivery/state/example/snapshot.json",
    ]
    readonly_dirs = [root / ".owlbear/delivery/state/example"]
    for path in readonly_files:
        path.chmod(0o444)
    for path in readonly_dirs:
        path.chmod(0o555)

    try:
        text = _run_cli(root, "inspect", "--project-root", os.fspath(root))
        payload = _run_cli(
            root,
            "inspect",
            "--project-root",
            os.fspath(root),
            "--format",
            "json",
        )
    finally:
        for path in readonly_files:
            path.chmod(0o644)
        for path in readonly_dirs:
            path.chmod(0o755)

    after_membership = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    after_bytes = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    assert text.returncode == 0
    assert text.stdout.startswith("status: healthy-structure\n")
    assert "writes_performed: false" in text.stdout
    assert payload.returncode == 0
    result = json.loads(payload.stdout)
    assert result["status"] == "healthy-structure"
    assert result["writes_performed"] is False
    assert "blocked unavailable package" not in payload.stderr
    assert after_membership == before_membership
    assert after_bytes == before_bytes


@pytest.mark.parametrize(
    ("relative", "content", "expected_status"),
    [
        (".owlbear/delivery/config.json", b"{", "degraded"),
        (".owlbear/delivery/config.json", b'{"schema_version":99}', "unsupported"),
    ],
)
def test_standalone_cli_degraded_and_unsupported_exit_one(
    tmp_path: Path, relative: str, content: bytes, expected_status: str
) -> None:
    root = _root(tmp_path)
    path = root / relative
    path.write_bytes(content)

    completed = _run_cli(root, "inspect", "--project-root", os.fspath(root), "--format", "json")

    assert completed.returncode == 1
    assert json.loads(completed.stdout)["status"] == expected_status


def test_standalone_cli_missing_root_and_error_redaction(tmp_path: Path) -> None:
    missing = tmp_path / "missing-root"
    unavailable = _run_cli(missing, "inspect", "--project-root", os.fspath(missing), "--format", "json")
    assert unavailable.returncode == 2
    assert json.loads(unavailable.stdout)["status"] == "unavailable"

    marked = tmp_path / "marked-project"
    (marked / ".owlbear").mkdir(parents=True)
    missing_state = _run_cli(marked, "inspect", "--project-root", os.fspath(marked), "--format", "json")
    assert missing_state.returncode == 1
    assert json.loads(missing_state.stdout)["status"] == "degraded"

    invalid = _run_cli(
        tmp_path,
        "inspect",
        "--project-root",
        os.fspath(tmp_path),
        "--change-id",
        "../private-secret-identifier",
    )
    assert invalid.returncode == 2
    assert invalid.stdout == "ERR_INVALID_INVOCATION\n"
    assert "private-secret-identifier" not in invalid.stdout


def test_nested_cwd_discovers_nearest_fixed_project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    nested = root / "work" / "nested"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    result = inspect_delivery()

    assert result["status"] == "healthy-structure"
    assert result["change_scope"] == "all"


def test_pending_yaml_is_opaque_and_private_payload_is_not_echoed(tmp_path: Path) -> None:
    root = _root(tmp_path)
    transaction = root / ".owlbear/delivery/runtime/transactions"
    transaction.mkdir()
    (transaction / "private-secret.yaml").write_text("password: TOP-SECRET\n", encoding="utf-8")

    result = inspect_delivery(root)
    encoded = json.dumps(result)

    assert result["pending_effects"] is True
    assert result["counts"]["pending_transactions"] == 1
    assert "TOP-SECRET" not in encoded
    assert "private-secret" not in encoded


def test_known_nested_transaction_families_are_inspected(tmp_path: Path) -> None:
    root = _root(tmp_path)
    nested = root / ".owlbear/delivery/runtime/finalization-reports/report-1/transactions"
    nested.mkdir(parents=True)
    (nested / "pending.yaml").write_text("secret: hidden\n", encoding="utf-8")
    package = root / ".owlbear/delivery/packages/example/transactions"
    package.mkdir(parents=True)
    (package / "package.yaml").write_text("secret: hidden\n", encoding="utf-8")
    legacy = root / ".owlbear/delivery/runtime/changes/example/transactions"
    legacy.mkdir(parents=True)
    (legacy / "legacy.yaml").write_text("secret: hidden\n", encoding="utf-8")
    reports_tx = root / ".owlbear/delivery/runtime/finalization-reports/report-1/transactions"
    (reports_tx / "report.yaml").write_text("secret: hidden\n", encoding="utf-8")

    result = inspect_delivery(root)

    assert result["counts"]["pending_transactions"] == 4
    assert result["pending_effects"] is True
    assert "hidden" not in json.dumps(result)
    locators = {record["locator"] for record in result["records"] if record["kind"].startswith("transaction")}
    assert ".owlbear/delivery/runtime/changes/<redacted>/transactions/<opaque>.yaml" in locators
    assert ".owlbear/delivery/packages/<redacted>/transactions/<opaque>.yaml" in locators
    assert ".owlbear/delivery/runtime/finalization-reports/<redacted>/transactions/<opaque>.yaml" in locators


def test_package_root_transactions_are_inspected_with_root_locator(tmp_path: Path) -> None:
    root = _root(tmp_path)
    transactions = root / ".owlbear/delivery/packages/transactions"
    transactions.mkdir(parents=True)
    (transactions / "active.yaml").write_text("secret: hidden\n", encoding="utf-8")

    result = inspect_delivery(root)

    assert result["counts"]["pending_transactions"] == 1
    assert result["pending_effects"] is True
    assert ".owlbear/delivery/packages/transactions/<opaque>.yaml" in {
        record["locator"] for record in result["records"]
    }
    assert "hidden" not in json.dumps(result)


def test_regular_package_storage_lock_does_not_degrade_inspection(tmp_path: Path) -> None:
    root = _root(tmp_path)
    packages = root / ".owlbear/delivery/packages"
    packages.mkdir()
    (packages / ".storage.lock").write_bytes(b"")

    result = inspect_delivery(root)

    assert result["status"] == "healthy-structure"
    assert result["inspection_complete"] is True
    assert result["pending_effects"] is False


@pytest.mark.parametrize("entry_type", ["symlink", "fifo"])
def test_non_regular_package_storage_lock_keeps_pending_effects_contained(
    tmp_path: Path,
    entry_type: str,
) -> None:
    root = _root(tmp_path)
    packages = root / ".owlbear/delivery/packages"
    packages.mkdir()
    lock = packages / ".storage.lock"
    if entry_type == "symlink":
        target = tmp_path / "outside"
        target.write_bytes(b"not inspected")
        lock.symlink_to(target)
        diagnostic = "SYMLINK_REJECTED"
    else:
        os.mkfifo(lock)
        diagnostic = "SPECIAL_FILE_REJECTED"

    result = inspect_delivery(root)

    assert result["status"] == "degraded"
    assert result["inspection_complete"] is False
    assert result["pending_effects"] == "unknown"
    assert diagnostic in result["diagnostic_codes"]


def test_optional_host_local_and_selected_package_scope_are_bounded(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    runtime = root / ".owlbear/delivery/runtime"
    (runtime / "host.local.json").write_bytes(b'{"schema_version":99}\n')
    other = root / ".owlbear/delivery/packages/other"
    other.mkdir(parents=True)
    selected = root / ".owlbear/delivery/packages/example"
    selected.mkdir(parents=True)

    result = inspect_delivery(root, change_id="example")

    assert "HOST_LOCAL_UNSUPPORTED" in result["diagnostic_codes"]
    assert result["counts"]["packages"] == 1


def test_host_local_optional_null_overrides_are_structurally_valid(tmp_path: Path) -> None:
    root = _root(tmp_path)
    (root / ".owlbear/delivery/runtime/host.local.json").write_bytes(
        b'{"execution_capacity":null,"claim_timeout_seconds":null}\n'
    )
    result = inspect_delivery(root)
    host_local = next(record for record in result["records"] if record["kind"] == "host_local")

    assert "HOST_LOCAL_MALFORMED" not in result["diagnostic_codes"]
    assert host_local["status"] == "supported"


def test_missing_frontier_is_incomplete_without_unknown_pending_effects(tmp_path: Path) -> None:
    root = _root(tmp_path)
    (root / ".owlbear/delivery/runtime/changes/example").mkdir()

    result = inspect_delivery(root)

    assert "FRONTIER_MISSING" in result["diagnostic_codes"]
    assert result["inspection_complete"] is False
    assert result["pending_effects"] is False


@pytest.mark.parametrize(
    ("runtime_changes", "expected_code", "expected_pending_effects"),
    [
        ("missing-record", "CHANGE_NOT_FOUND", "verified-absent"),
        ("unreadable", "SYMLINK_REJECTED", "unknown"),
        ("unrelated-records", "CHANGE_NOT_FOUND", "verified-absent"),
    ],
)
def test_selected_change_presence_requires_runtime_record(
    tmp_path: Path,
    runtime_changes: str,
    expected_code: str,
    expected_pending_effects: str,
) -> None:
    root = _complete_root(tmp_path)
    changes = root / ".owlbear/delivery/runtime/changes"
    if runtime_changes == "missing-record":
        shutil.rmtree(changes / "example")
    elif runtime_changes == "unreadable":
        shutil.rmtree(changes)
        outside = tmp_path / "outside"
        outside.mkdir()
        changes.symlink_to(outside, target_is_directory=True)
    else:
        shutil.rmtree(changes / "example")
        for index in range(MAX_ENTRIES + 1):
            (changes / f"other-{index}").mkdir()
    before_membership = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    before_bytes = {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }

    completed = _run_cli(
        root,
        "inspect",
        "--project-root",
        str(root),
        "--change-id",
        "example",
        "--format",
        "json",
    )
    result = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert result["status"] == "degraded"
    assert result["inspection_complete"] is False
    assert expected_code in result["diagnostic_codes"]
    assert result["pending_effects"] == (False if expected_pending_effects == "verified-absent" else "unknown")
    if expected_pending_effects == "unknown":
        assert "CHANGE_NOT_FOUND" not in result["diagnostic_codes"]
    assert result["writes_performed"] is False
    assert before_membership == sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    assert before_bytes == {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }


def test_failed_present_pending_families_make_pending_effects_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path)
    family = root / ".owlbear/delivery/runtime/finalization-reports"
    family.mkdir()
    packages = root / ".owlbear/delivery/packages"
    packages.mkdir()
    real_open_directory = diagnostics._open_directory  # noqa: SLF001

    def deny_pending_family(
        parent_fd: int,
        name: str,
        inspection: object,
        code_prefix: str,
        *,
        required: bool = False,
    ) -> object:
        if name in {"finalization-reports", "packages"}:
            return None
        return real_open_directory(parent_fd, name, inspection, code_prefix, required=required)

    monkeypatch.setattr(diagnostics, "_open_directory", deny_pending_family)

    result = inspect_delivery(root)

    assert result["pending_effects"] == "unknown"
    assert "PENDING_EFFECTS_UNKNOWN" in result["diagnostic_codes"]


def test_unavailable_runtime_makes_pending_effects_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    real_open_directory = diagnostics._open_directory  # noqa: SLF001

    def deny_runtime(
        parent_fd: int,
        name: str,
        inspection: object,
        code_prefix: str,
        *,
        required: bool = False,
    ) -> object:
        if name == "runtime":
            return None
        return real_open_directory(parent_fd, name, inspection, code_prefix, required=required)

    monkeypatch.setattr(diagnostics, "_open_directory", deny_runtime)

    result = inspect_delivery(root)

    assert result["pending_effects"] == "unknown"
    assert "PENDING_EFFECTS_UNKNOWN" in result["diagnostic_codes"]


def test_replaced_scanner_ancestor_makes_pending_effects_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path)
    child = root / "child"
    child.mkdir()
    parent_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    child_fd = os.open("child", os.O_RDONLY | os.O_DIRECTORY, dir_fd=parent_fd)
    opened = os.fstat(child_fd)
    real_stat = diagnostics.os.stat

    def replaced(path: object, *args: object, **kwargs: object) -> os.stat_result:
        current = real_stat(path, *args, **kwargs)
        if path == "child" and kwargs.get("dir_fd") == parent_fd:
            values = list(current)
            values[1] += 1
            return os.stat_result(values)
        return current

    monkeypatch.setattr(diagnostics.os, "stat", replaced)
    inspection = diagnostics._Inspection(root, None)  # noqa: SLF001
    try:
        diagnostics._close_directory(parent_fd, "child", child_fd, opened, inspection)  # noqa: SLF001
    finally:
        os.close(parent_fd)

    assert inspection.transaction_scan_unknown is True


def test_symlink_fifo_and_read_only_membership(tmp_path: Path) -> None:
    root = _root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    change.mkdir()
    (root / ".owlbear/delivery/runtime/changes/unsafe name").mkdir()
    packages = root / ".owlbear/delivery/packages"
    packages.mkdir()
    (packages / "unsafe").symlink_to(root)
    (change / "frontier.json").symlink_to(root / "secret.json")
    os.mkfifo(root / ".owlbear/delivery/runtime/coordination/changes/example.json")
    before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

    result = inspect_delivery(root)
    after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

    assert before == after
    assert "SYMLINK_REJECTED" in result["diagnostic_codes"]
    assert "SPECIAL_FILE_REJECTED" in result["diagnostic_codes"]
    assert result["pending_effects"] == "unknown"
    assert result["writes_performed"] is False


def test_entry_and_size_limits_are_reported_without_reading_unbounded_data(tmp_path: Path) -> None:
    root = _root(tmp_path)
    changes = root / ".owlbear/delivery/runtime/changes"
    for index in range(MAX_ENTRIES + 1):
        (changes / f"change-{index}").mkdir()
    huge = root / ".owlbear/delivery/config.json"
    huge.write_bytes(b"{" + b"x" * MAX_RECORD_BYTES)

    result = inspect_delivery(root)

    assert "ENTRY_LIMIT_EXCEEDED" in result["diagnostic_codes"]
    assert "OVERSIZED_RECORD" in result["diagnostic_codes"]
    assert result["inspection_complete"] is False
    assert result["counts"]["frontier"] <= MAX_ENTRIES
    assert result["counts"]["config"] == 0
    assert result["counts"]["pending_transactions"] == 0


def test_entry_limit_is_global_across_fixed_directories(tmp_path: Path) -> None:
    root = _root(tmp_path)
    changes = root / ".owlbear/delivery/runtime/changes"
    coordination = root / ".owlbear/delivery/runtime/coordination/changes"
    for index in range(MAX_ENTRIES // 2 + 2):
        (changes / f"change-{index}").mkdir()
        (coordination / f"change-{index}.json").write_text("{}", encoding="utf-8")

    result = inspect_delivery(root)

    assert "ENTRY_LIMIT_EXCEEDED" in result["diagnostic_codes"]
    assert result["inspection_complete"] is False


def test_total_byte_limit_is_independent_of_record_and_entry_limits(tmp_path: Path) -> None:
    root = _root(tmp_path)
    changes = root / ".owlbear/delivery/runtime/changes"
    record = b"{" + b"x" * (MAX_RECORD_BYTES - 2) + b"}"
    for index in range(9):
        change = changes / f"change-{index}"
        change.mkdir()
        (change / "frontier.json").write_bytes(record)

    result = inspect_delivery(root)

    assert "TOTAL_LIMIT_EXCEEDED" in result["diagnostic_codes"]
    assert "ENTRY_LIMIT_EXCEEDED" not in result["diagnostic_codes"]
    assert result["inspection_complete"] is False


def test_total_byte_budget_stays_bounded_when_file_grows_during_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path)
    baseline = int(inspect_delivery(root)["bytes_inspected"])
    monkeypatch.setattr(diagnostics, "MAX_TOTAL_BYTES", baseline + 16)
    frontier = root / ".owlbear/delivery/runtime/changes/example/frontier.json"
    frontier.parent.mkdir()
    frontier.write_bytes(b"{}")
    real_open = diagnostics.os.open
    real_read = diagnostics.os.read
    frontier_fd: int | None = None
    grown = False

    def capture_frontier_fd(path: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        nonlocal frontier_fd
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        if path == "frontier.json" and dir_fd is not None:
            frontier_fd = descriptor
        return descriptor

    def grow_after_read(fd: int, size: int) -> bytes:
        nonlocal grown
        data = real_read(fd, size)
        if fd == frontier_fd and data and not grown:
            frontier.write_bytes(b'{"schema_version":19,"bindings":[]}\n')
            grown = True
        return data

    monkeypatch.setattr(diagnostics.os, "open", capture_frontier_fd)
    monkeypatch.setattr(diagnostics.os, "read", grow_after_read)

    result = inspect_delivery(root)

    assert grown is True
    assert {"CHANGED_DURING_READ", "REPLACED_DURING_READ"} & set(result["diagnostic_codes"])
    assert result["bytes_inspected"] <= diagnostics.MAX_TOTAL_BYTES
    assert result["inspection_complete"] is False


def test_unreadable_record_is_reported_without_treating_it_as_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path)
    real_stat = diagnostics.os.stat

    def deny_config(path: object, *args: object, **kwargs: object) -> os.stat_result:
        if path == "config.json" and kwargs.get("dir_fd") is not None:
            raise PermissionError from None
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(diagnostics.os, "stat", deny_config)

    result = inspect_delivery(root)

    assert "CONFIG_UNREADABLE" in result["diagnostic_codes"]
    assert "CONFIG_MISSING" not in result["diagnostic_codes"]


def test_helper_substitution_probe_is_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    real_state = diagnostics._same_file_state  # noqa: SLF001 - deterministic race probe
    calls = 0

    def substitute_once(left: os.stat_result, right: os.stat_result) -> bool:
        nonlocal calls
        calls += 1
        return False if calls == 1 else real_state(left, right)

    monkeypatch.setattr(diagnostics, "_same_file_state", substitute_once)

    result = inspect_delivery(root)

    assert "REPLACED_DURING_READ" in result["diagnostic_codes"]


def test_real_file_substitution_during_open_is_detected_without_blocking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path)
    config = root / ".owlbear/delivery/config.json"
    replacement = (
        b'{"schema_version":2,"remote":"replacement","target_branch":"dev","github_repository":"safe/project"}\n'
    )
    original = config.read_bytes()
    real_open = diagnostics.os.open
    swapped = False

    def swap_before_open(path: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        nonlocal swapped
        if path == "config.json" and dir_fd is not None and not swapped:
            config.replace(config.with_name("config.original"))
            config.write_bytes(replacement)
            swapped = True
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(diagnostics.os, "open", swap_before_open)
    result = inspect_delivery(root)

    assert swapped is True
    assert "REPLACED_DURING_READ" in result["diagnostic_codes"]
    assert (root / ".owlbear/delivery/config.original").read_bytes() == original


def test_log_path_substitution_after_read_is_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    logs = root / ".owlbear/delivery/runtime/logs"
    logs.mkdir()
    log = logs / "entry.log"
    original = b"original log\n"
    log.write_bytes(original)
    real_open = diagnostics.os.open
    real_read = diagnostics.os.read
    log_fd: int | None = None
    swapped = False

    def capture_log_fd(path: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        nonlocal log_fd
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        if path == "entry.log" and dir_fd is not None:
            log_fd = descriptor
        return descriptor

    def swap_log_path(fd: int, size: int) -> bytes:
        nonlocal swapped
        if fd == log_fd and not swapped:
            log.replace(log.with_name("entry.original"))
            log.write_bytes(b"replacement log\n")
            swapped = True
        return real_read(fd, size)

    monkeypatch.setattr(diagnostics.os, "open", capture_log_fd)
    monkeypatch.setattr(diagnostics.os, "read", swap_log_path)
    result = inspect_delivery(root)

    assert swapped is True
    assert "REPLACED_DURING_READ" in result["diagnostic_codes"]
    assert (logs / "entry.original").read_bytes() == original


def test_opaque_transaction_replacement_is_detected_without_yaml_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path)
    transactions = root / ".owlbear/delivery/runtime/transactions"
    transactions.mkdir()
    pending = transactions / "pending.yaml"
    pending.write_text("secret: opaque\n", encoding="utf-8")
    real_stat = diagnostics.os.stat
    stat_calls = 0

    def swap_on_poststat(path: object, *args: object, **kwargs: object) -> os.stat_result:
        nonlocal stat_calls
        if path == "pending.yaml" and kwargs.get("dir_fd") is not None:
            stat_calls += 1
            if stat_calls == 2:
                pending.replace(transactions / "pending.original")
                pending.write_text("secret: replacement\n", encoding="utf-8")
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(diagnostics.os, "stat", swap_on_poststat)
    result = inspect_delivery(root)

    assert stat_calls >= 2
    assert "REPLACED_DURING_READ" in result["diagnostic_codes"]
    assert result["pending_effects"] == "unknown"
    assert "replacement" not in json.dumps(result)


def test_root_ancestor_replacement_is_revalidated_before_return(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _complete_root(tmp_path)
    real_scan_runtime = diagnostics._scan_runtime  # noqa: SLF001

    def replace_after_scan(delivery_fd: int, inspection: object, *, selected: str | None) -> None:
        real_scan_runtime(delivery_fd, inspection, selected=selected)
        root.rename(root.with_name("replaced-root"))
        root.mkdir()

    monkeypatch.setattr(diagnostics, "_scan_runtime", replace_after_scan)
    result = inspect_delivery(root)

    assert "REPLACED_DURING_INSPECTION" in result["diagnostic_codes"]
    assert result["inspection_complete"] is False
    assert result["pending_effects"] == "unknown"
    assert result["status"] == "degraded"


@pytest.mark.parametrize("part", [".owlbear", ".owlbear/delivery", ".owlbear/delivery/runtime"])
def test_cli_unsafe_ancestry_is_unknown_without_reading_target(tmp_path: Path, part: str) -> None:
    root = _complete_root(tmp_path / "project")
    rejected = root / part
    retained = tmp_path / "retained"
    rejected.rename(retained)
    rejected.symlink_to(retained, target_is_directory=True)
    before = {path: path.read_bytes() for path in retained.rglob("*") if path.is_file()}

    completed = _run_cli(root, "inspect", "--project-root", str(root), "--format", "json")
    result = json.loads(completed.stdout)

    assert completed.returncode == (2 if part == ".owlbear" else 1)
    assert result["inspection_complete"] is False
    assert result["pending_effects"] == "unknown"
    assert "PENDING_EFFECTS_UNKNOWN" in result["diagnostic_codes"]
    assert before == {path: path.read_bytes() for path in retained.rglob("*") if path.is_file()}


@pytest.mark.parametrize("kind", ["symlink", "fifo", "unsafe-name"])
def test_cli_rejected_records_are_incomplete(tmp_path: Path, kind: str) -> None:
    root = _complete_root(tmp_path)
    frontier = root / ".owlbear/delivery/runtime/changes/example/frontier.json"
    if kind == "unsafe-name":
        record = root / ".owlbear/delivery/runtime/coordination/changes/unsafe name.json"
        record.write_bytes(b"private-placeholder")
    else:
        frontier.unlink()
        if kind == "fifo":
            os.mkfifo(frontier)
        else:
            target = tmp_path / "not-inspected"
            target.write_bytes(b"private-placeholder")
            frontier.symlink_to(target)
    before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

    completed = _run_cli(root, "inspect", "--project-root", str(root), "--format", "json")
    result = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert result["status"] == "degraded"
    assert result["inspection_complete"] is False
    assert "private-placeholder" not in completed.stdout
    assert before == sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))


@pytest.mark.parametrize(
    ("content", "status"),
    [
        ('{"execution_capacity":3}', "healthy-structure"),
        ('{"schema_version":99,"execution_capacity":3}', "unsupported"),
        ('{"execution_capacity":true}', "degraded"),
        ('{"execution_capacity":0}', "degraded"),
        ('{"execution_capacity":"3"}', "degraded"),
        ('{"unexpected":3}', "degraded"),
    ],
)
def test_cli_local_override_structural_compatibility(tmp_path: Path, content: str, status: str) -> None:
    root = _complete_root(tmp_path)
    override = root / ".owlbear/delivery/runtime/host.local.json"
    override.write_text(content, encoding="utf-8")

    completed = _run_cli(root, "inspect", "--project-root", str(root), "--format", "json")
    result = json.loads(completed.stdout)

    assert completed.returncode == (0 if status == "healthy-structure" else 1)
    assert result["status"] == status
    assert override.read_text(encoding="utf-8") == content
    if status == "healthy-structure":
        record = next(record for record in result["records"] if record["kind"] == "host_local")
        assert record["schema_version"] == 1


def test_initial_fstat_failure_is_bounded_and_closes_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _complete_root(tmp_path)
    real_open = diagnostics.os.open
    real_fstat = diagnostics.os.fstat
    real_close = diagnostics.os.close
    failed_fd = None
    closed = False
    failed = False

    def capture_open(path: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        nonlocal failed_fd
        fd = real_open(path, flags, mode, dir_fd=dir_fd)
        if path == "config.json":
            failed_fd = fd
        return fd

    def fail_first_record_stat(fd: int) -> os.stat_result:
        nonlocal failed
        if fd == failed_fd and not failed:
            failed = True
            message = "private failure text"
            raise OSError(message)
        return real_fstat(fd)

    def capture_close(fd: int) -> None:
        nonlocal closed
        if fd == failed_fd and failed:
            closed = True
        real_close(fd)

    monkeypatch.setattr(diagnostics.os, "open", capture_open)
    monkeypatch.setattr(diagnostics.os, "fstat", fail_first_record_stat)
    monkeypatch.setattr(diagnostics.os, "close", capture_close)
    result_code = main(["inspect", "--project-root", str(root), "--format", "json"])
    output = capsys.readouterr().out
    result = json.loads(output)

    assert failed
    assert closed
    assert result_code == 1
    assert "CONFIG_UNREADABLE" in result["diagnostic_codes"]
    assert result["inspection_complete"] is False
    assert "private failure text" not in output
    expected_bytes = sum(
        path.stat().st_size for path in (root / ".owlbear/delivery").rglob("*.json") if path.name != "config.json"
    )
    assert result["bytes_inspected"] == expected_bytes


@pytest.mark.parametrize("part", ["root", ".owlbear", ".owlbear/delivery"])
def test_cli_replaced_ancestry_reports_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], part: str
) -> None:
    root = _complete_root(tmp_path / "project")
    original = root if part == "root" else root / part
    retained = tmp_path / "original-tree"
    before = {path.relative_to(original): path.read_bytes() for path in original.rglob("*") if path.is_file()}
    real_scan = diagnostics._scan_runtime  # noqa: SLF001

    def replace_after_scan(fd: int, inspection: diagnostics._Inspection, *, selected: str | None) -> None:
        real_scan(fd, inspection, selected=selected)
        original.rename(retained)
        original.mkdir()

    monkeypatch.setattr(diagnostics, "_scan_runtime", replace_after_scan)
    exit_code = main(["inspect", "--project-root", str(root), "--format", "json"])
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert result["status"] == "degraded"
    assert result["inspection_complete"] is False
    assert result["pending_effects"] == "unknown"
    assert before == {path.relative_to(retained): path.read_bytes() for path in retained.rglob("*") if path.is_file()}


def test_installed_console_creates_no_bytecode_or_project_writes(tmp_path: Path) -> None:
    """Exercise the built wheel's actual launcher, not an import-target imitation."""
    uv = shutil.which("uv")
    assert uv is not None, "the maintained uv build/install tool is required"
    tools = Path(__file__).parents[1]
    wheels = tmp_path / "wheels"
    subprocess.run(  # noqa: S603 - maintained offline build with fixed arguments
        # The running interpreter avoids requiring the repository's pinned .python-version offline.
        [uv, "build", "--offline", "--wheel", "--python", sys.executable, "--out-dir", str(wheels), str(tools)],
        check=True,
        capture_output=True,
        timeout=30,
    )
    root = _complete_root(tmp_path / "project")
    environment = root / ".venv"
    subprocess.run(  # noqa: S603 - disposable virtual environment only
        [uv, "venv", "--offline", "--python", sys.executable, str(environment)],
        check=True,
        capture_output=True,
        timeout=30,
    )
    python = environment / "bin/python"
    wheel = next(wheels.glob("*.whl"))
    subprocess.run(  # noqa: S603 - install only the locally built wheel, without dependencies
        [uv, "pip", "install", "--offline", "--no-deps", "--python", str(python), str(wheel)],
        check=True,
        capture_output=True,
        timeout=30,
    )
    assert not list(root.rglob("__pycache__"))
    before = {
        path.relative_to(root): path.read_bytes() if path.is_file() and not path.is_symlink() else None
        for path in root.rglob("*")
    }
    env = dict(os.environ)
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    env.pop("PYTHONPYCACHEPREFIX", None)
    launcher = environment / "bin/delivery-diagnose"
    completed = subprocess.run(  # noqa: S603 - actual installed command under inspected root
        [str(launcher), "inspect", "--project-root", str(root), "--format", "json"],
        env=env,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["status"] == "healthy-structure"
    assert not list(root.rglob("__pycache__"))
    assert not list(root.rglob("*.pyc"))
    assert before == {
        path.relative_to(root): path.read_bytes() if path.is_file() and not path.is_symlink() else None
        for path in root.rglob("*")
    }
