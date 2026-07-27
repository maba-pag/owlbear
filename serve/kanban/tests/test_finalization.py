"""Behavioral coverage for bootstrap carrier finalization."""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import (
    BootstrapFinalizationAbsenceError,
    BootstrapFinalizationCurrentnessError,
    BootstrapFinalizationPathError,
    BootstrapFinalizationPreconditionError,
    BootstrapFinalizationPublicationError,
    BootstrapFinalizationReadiness,
    BootstrapFinalizationReceipt,
    BootstrapFinalizationReceiptError,
    BootstrapFinalizationRequest,
    LegacyActiveItem,
    LegacyDisposition,
    LegacySnapshotDestinationError,
    LegacySnapshotSourceChangedError,
    LegacySnapshotVerificationError,
    finalize_bootstrap_carrier,
    inventory_legacy_source,
    verify_legacy_snapshot,
)

_DIGEST = "a" * 64


def _legacy_workspace(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / ".owlbear/kanban"
    (source / "tasks").mkdir(parents=True)
    (source / "tasks/1-active.md").write_text("active\n", encoding="utf-8")
    carrier = tmp_path / ".vscode/legacy-mcp.json"
    carrier.parent.mkdir()
    carrier.write_text("{}\n", encoding="utf-8")
    return source, carrier


def _active_items() -> tuple[LegacyActiveItem, ...]:
    return (LegacyActiveItem(item_id="task:1", relative_path="tasks/1-active.md"),)


def _dispositions() -> dict[str, LegacyDisposition]:
    return {"task:1": LegacyDisposition.REINTRODUCE_NATIVE}


def _request(source: Path, *, readiness: BootstrapFinalizationReadiness | None = None) -> BootstrapFinalizationRequest:
    source_digest = inventory_legacy_source(source, _active_items(), _dispositions()).source_digest
    return BootstrapFinalizationRequest(
        source_path=".owlbear/kanban",
        sibling_carrier_path=".vscode/legacy-mcp.json",
        snapshot_path=".owlbear/legacy/kanban-final",
        receipt_path=".owlbear/legacy/bootstrap-finalization.json",
        active_items=_active_items(),
        dispositions=_dispositions(),
        expected_source_digest=source_digest,
        expected_delivery_digest=_DIGEST,
        actual_delivery_digest=_DIGEST,
        expected_code_revision=_DIGEST,
        actual_code_revision=_DIGEST,
        approval="FINALIZE_BOOTSTRAP_CARRIER",
        readiness=readiness or BootstrapFinalizationReadiness(terminal=True),
    )


def test_finalizer_rejects_active_claim_before_mutation(tmp_path: Path) -> None:
    source, carrier = _legacy_workspace(tmp_path)
    request = _request(
        source,
        readiness=BootstrapFinalizationReadiness(terminal=True, active_claim_ids=("claim-1",)),
    )

    with pytest.raises(BootstrapFinalizationPreconditionError, match="active claims") as raised:
        finalize_bootstrap_carrier(tmp_path, request)

    assert raised.value.code == "ERR_BOOTSTRAP_FINALIZATION_ACTIVE_CLAIMS"
    assert source.is_dir()
    assert carrier.is_file()
    assert not (tmp_path / ".owlbear/legacy").exists()


def test_finalizer_publishes_receipt_removes_carriers_and_replays(tmp_path: Path) -> None:
    source, carrier = _legacy_workspace(tmp_path)
    request = _request(source)

    result = finalize_bootstrap_carrier(tmp_path, request)
    replay = finalize_bootstrap_carrier(tmp_path, request)

    assert result.replayed is False
    assert replay.replayed is True
    assert replay.receipt == result.receipt
    assert result.tracked_paths == (
        ".owlbear/kanban",
        ".vscode/legacy-mcp.json",
        ".owlbear/legacy/kanban-final",
        ".owlbear/legacy/bootstrap-finalization.json",
    )
    assert not source.exists()
    assert not carrier.exists()
    snapshot = verify_legacy_snapshot(tmp_path / request.snapshot_path)
    assert snapshot.manifest.source_digest == request.expected_source_digest
    receipt = BootstrapFinalizationReceipt.model_validate_json((tmp_path / request.receipt_path).read_bytes())
    assert receipt == result.receipt
    assert not (tmp_path / ".owlbear/legacy/.bootstrap-finalization.json.pending").exists()


@pytest.mark.parametrize(
    ("readiness", "code"),
    [
        (BootstrapFinalizationReadiness(terminal=False), "ERR_BOOTSTRAP_FINALIZATION_NONTERMINAL"),
        (
            BootstrapFinalizationReadiness(terminal=True, proof_verified=False),
            "ERR_BOOTSTRAP_FINALIZATION_PROOF_STALE",
        ),
        (
            BootstrapFinalizationReadiness(terminal=True, active_writer_ids=("writer-1",)),
            "ERR_BOOTSTRAP_FINALIZATION_ACTIVE_WRITERS",
        ),
        (
            BootstrapFinalizationReadiness(terminal=True, pending_request_ids=("request-1",)),
            "ERR_BOOTSTRAP_FINALIZATION_PENDING_REQUESTS",
        ),
        (
            BootstrapFinalizationReadiness(terminal=True, unclassified_record_ids=("record-1",)),
            "ERR_BOOTSTRAP_FINALIZATION_UNCLASSIFIED",
        ),
    ],
)
def test_finalizer_rejects_unready_state_without_mutation(
    tmp_path: Path,
    readiness: BootstrapFinalizationReadiness,
    code: str,
) -> None:
    source, carrier = _legacy_workspace(tmp_path)

    with pytest.raises(BootstrapFinalizationPreconditionError) as raised:
        finalize_bootstrap_carrier(tmp_path, _request(source, readiness=readiness))

    assert raised.value.code == code
    assert source.exists()
    assert carrier.exists()
    assert not (tmp_path / ".owlbear/legacy").exists()


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("actual_delivery_digest", "ERR_BOOTSTRAP_FINALIZATION_AUTHORITY_STALE"),
        ("actual_code_revision", "ERR_BOOTSTRAP_FINALIZATION_CODE_STALE"),
        ("expected_source_digest", "ERR_BOOTSTRAP_FINALIZATION_SOURCE_CHANGED"),
    ],
)
def test_finalizer_rejects_stale_identity_without_publication(tmp_path: Path, field: str, code: str) -> None:
    source, carrier = _legacy_workspace(tmp_path)
    request = _request(source).model_copy(update={field: "b" * 64})

    with pytest.raises(BootstrapFinalizationCurrentnessError) as raised:
        finalize_bootstrap_carrier(tmp_path, request)

    assert raised.value.code == code
    assert source.exists()
    assert carrier.exists()
    assert not (tmp_path / ".owlbear/legacy").exists()


def test_finalizer_rejects_overlapping_and_symlinked_paths(tmp_path: Path) -> None:
    source, _carrier = _legacy_workspace(tmp_path)
    overlapping = _request(source).model_copy(update={"snapshot_path": ".owlbear/kanban/archive"})

    with pytest.raises(BootstrapFinalizationPathError):
        finalize_bootstrap_carrier(tmp_path, overlapping)

    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / ".owlbear/link").symlink_to(outside, target_is_directory=True)
    linked = _request(source).model_copy(update={"snapshot_path": ".owlbear/link/snapshot"})
    with pytest.raises(BootstrapFinalizationPathError):
        finalize_bootstrap_carrier(tmp_path, linked)


def test_finalizer_rejects_unowned_existing_destination(tmp_path: Path) -> None:
    source, carrier = _legacy_workspace(tmp_path)
    request = _request(source)
    destination = tmp_path / request.snapshot_path
    destination.mkdir(parents=True)
    (destination / "owner.txt").write_text("keep\n", encoding="utf-8")

    with pytest.raises(LegacySnapshotDestinationError):
        finalize_bootstrap_carrier(tmp_path, request)

    assert source.exists()
    assert carrier.exists()
    assert (destination / "owner.txt").read_text(encoding="utf-8") == "keep\n"


@pytest.mark.parametrize("interruption_stage", ["after-snapshot", "after-source-removal"])
def test_finalizer_replays_after_publication_interruption(tmp_path: Path, interruption_stage: str) -> None:
    source, carrier = _legacy_workspace(tmp_path)
    request = _request(source)

    def interrupt(stage: str, _path: Path) -> None:
        if stage == interruption_stage:
            message = "interrupted"
            raise RuntimeError(message)

    with pytest.raises(BootstrapFinalizationPublicationError):
        finalize_bootstrap_carrier(tmp_path, request, failure=interrupt)

    assert not (tmp_path / request.receipt_path).exists()
    assert (tmp_path / request.snapshot_path).exists()
    replay = finalize_bootstrap_carrier(tmp_path, request)
    assert replay.replayed is False
    assert not source.exists()
    assert not carrier.exists()


def test_finalizer_absence_failure_has_no_receipt_and_replays_after_correction(tmp_path: Path) -> None:
    source, _carrier = _legacy_workspace(tmp_path)
    request = _request(source)

    def replace_source(stage: str, _path: Path) -> None:
        if stage == "before-absence-verification":
            source.mkdir()

    with pytest.raises(BootstrapFinalizationAbsenceError):
        finalize_bootstrap_carrier(tmp_path, request, failure=replace_source)

    assert not (tmp_path / request.receipt_path).exists()
    source.rmdir()
    result = finalize_bootstrap_carrier(tmp_path, request)
    assert result.receipt.source_digest == request.expected_source_digest


def test_finalizer_receipt_publication_interruption_replays_same_identity(tmp_path: Path) -> None:
    source, _carrier = _legacy_workspace(tmp_path)
    request = _request(source)

    def interrupt(stage: str, _path: Path) -> None:
        if stage == "before-receipt-publication":
            message = "interrupted"
            raise RuntimeError(message)

    with pytest.raises(BootstrapFinalizationPublicationError):
        finalize_bootstrap_carrier(tmp_path, request, failure=interrupt)

    assert not (tmp_path / request.receipt_path).exists()
    first = finalize_bootstrap_carrier(tmp_path, request)
    second = finalize_bootstrap_carrier(tmp_path, request)
    assert second.receipt.receipt_id == first.receipt.receipt_id
    assert second.snapshot_manifest_sha256 == first.snapshot_manifest_sha256


def test_finalizer_rolls_back_receipt_when_interrupted_after_link(tmp_path: Path) -> None:
    source, _carrier = _legacy_workspace(tmp_path)
    request = _request(source)

    def interrupt(stage: str, _path: Path) -> None:
        if stage == "after-receipt-link":
            message = "interrupted"
            raise RuntimeError(message)

    with pytest.raises(BootstrapFinalizationPublicationError):
        finalize_bootstrap_carrier(tmp_path, request, failure=interrupt)

    assert not (tmp_path / request.receipt_path).exists()
    result = finalize_bootstrap_carrier(tmp_path, request)
    assert result.receipt.receipt_id


def test_finalizer_rolls_back_corrupt_snapshot_while_source_is_recoverable(tmp_path: Path) -> None:
    source, carrier = _legacy_workspace(tmp_path)
    request = _request(source)

    def corrupt(stage: str, path: Path) -> None:
        if stage == "after-snapshot":
            (path / "content/tasks/1-active.md").write_text("corrupt\n", encoding="utf-8")

    with pytest.raises(LegacySnapshotVerificationError):
        finalize_bootstrap_carrier(tmp_path, request, failure=corrupt)

    assert source.exists()
    assert carrier.exists()
    assert not (tmp_path / request.snapshot_path).exists()
    assert not (tmp_path / ".owlbear/legacy/.bootstrap-finalization.json.pending").exists()


def test_finalizer_rejects_source_mutation_during_snapshot_and_replays_after_correction(tmp_path: Path) -> None:
    source, carrier = _legacy_workspace(tmp_path)
    request = _request(source)

    def mutate(stage: str, _path: Path) -> None:
        if stage == "before-publication":
            (source / "tasks/1-active.md").write_text("changed\n", encoding="utf-8")

    with pytest.raises(LegacySnapshotSourceChangedError):
        finalize_bootstrap_carrier(tmp_path, request, failure=mutate)

    assert not (tmp_path / request.snapshot_path).exists()
    assert not (tmp_path / request.receipt_path).exists()
    assert carrier.exists()
    (source / "tasks/1-active.md").write_text("active\n", encoding="utf-8")
    result = finalize_bootstrap_carrier(tmp_path, request)
    assert result.receipt.source_digest == request.expected_source_digest


def test_finalizer_rejects_tampered_completed_receipt(tmp_path: Path) -> None:
    source, _carrier = _legacy_workspace(tmp_path)
    request = _request(source)
    finalize_bootstrap_carrier(tmp_path, request)
    receipt_path = tmp_path / request.receipt_path
    receipt_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(BootstrapFinalizationReceiptError):
        finalize_bootstrap_carrier(tmp_path, request)
