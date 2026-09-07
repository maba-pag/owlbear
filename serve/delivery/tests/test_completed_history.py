from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery.acceptance import (
    CompletionDisplayMetadata,
    CompletionEvidence,
    CompletionPullRequestIdentity,
    CompletionReceipt,
    CompletionReceiptStore,
)
from owlbear_delivery.change_workspace import ChangeCoordination, ChangeTargetSyncConflictState
from owlbear_delivery.completed_history import (
    CompletedHistoryCatalog,
    CompletedHistoryDiagnosticCode,
    CompletedHistoryError,
    CompletedHistoryReceiptSetAdvancedError,
    ReceiptCompletedChangeRecord,
)
from owlbear_delivery.delivery_runtime import (
    DeliveryChangeAbandonment,
    DeliveryChangeStage,
    DeliveryFrontier,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    OutcomeAuthorityBinding,
)
from owlbear_delivery.target_contract import (
    DeliveryCommitment,
    DeliveryCommitmentClass,
    DeliveryContract,
    DeliveryOutcome,
    DeliveryPlanScope,
)


def _canonical(value: object) -> bytes:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return f"{json.dumps(value, sort_keys=True, separators=(',', ':'))}\n".encode()


def _contract(change_id: str, title: str, intent: bytes, design: bytes) -> DeliveryContract:
    return DeliveryContract(
        change_id=change_id,
        title=title,
        commitments=(
            DeliveryCommitment(
                commitment_id="COM-001",
                commitment_class=DeliveryCommitmentClass.AGREED_PATH,
                provenance="accepted design",
                statement="Keep completed history bounded.",
            ),
        ),
        outcomes=(
            DeliveryOutcome(
                outcome_id="OUT-001",
                title=f"Ship {title}",
                promise="Return a verified semantic record.",
                acceptance=("Completed history is queryable.",),
                commitment_ids=("COM-001",),
                dependency_ids=(),
            ),
        ),
        plan_scopes=(DeliveryPlanScope(scope_id="SCOPE-001", outcome_id="OUT-001"),),
        source_bindings=(
            {"source_name": "intent.md", "sha256": hashlib.sha256(intent).hexdigest()},
            {"source_name": "design.md", "sha256": hashlib.sha256(design).hexdigest()},
        ),
    )


def _task_result(
    result_id: str,
    change_id: str,
    authority_digest: str,
    task: DeliveryTaskDefinition,
    completed_commit: str,
) -> DeliveryTaskResult:
    observed_at = datetime(2026, 8, 11, 12, tzinfo=UTC)
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=change_id,
            task_or_finalization_id=task.task_id,
            exact_commit=completed_commit,
            observation_kind="pytest",
            command_or_procedure="completed-history fixture validation",
            exit_status_or_artifact_locator="exit:0",
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            exact_commit=completed_commit,
            author_id="Completed history test author",
            reviewer_id="Completed history test reviewer",
            evidence=("The exact fixture commit satisfies task authority.",),
            reviewed_at=observed_at,
        )
    )
    return DeliveryTaskResult(
        result_id=result_id,
        change_id=change_id,
        authority_digest=authority_digest,
        task_id=task.task_id,
        task_digest=task.digest,
        completed_commit=completed_commit,
        observations=(observation,),
        review=review,
    )


def _task() -> DeliveryTaskDefinition:
    return DeliveryTaskDefinition(
        task_id="TASK-001",
        outcome_id="OUT-001",
        plan_scope_id="SCOPE-001",
        title="Build bounded history",
        result="A Git-backed semantic catalog.",
        commitment_ids=("COM-001",),
        dependency_ids=(),
        required_outputs=("Completed record",),
        maintained_surfaces=("completed_history.py",),
        constraints=("Do not expose bodies.",),
        exclusions=("No active package query.",),
        acceptance_observations=("History is bounded.",),
        proof_boundaries=("CompletedHistoryCatalog",),
    )


def _receipt_digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _receipt_commit(value: str) -> str:
    return _receipt_digest(value)[:40]


def _publish_receipt(
    runtime_root: Path,
    change_id: str,
    title: str,
    *,
    pull_request_number: int,
) -> CompletionReceipt:
    merged_at = datetime(2026, 8, 11, 12, tzinfo=UTC)
    receipt = CompletionReceipt.create(
        CompletionEvidence(
            change_id=change_id,
            finalization_receipt_id=_receipt_digest(f"finalization:{change_id}"),
            finalized_change_head=_receipt_commit(f"finalized:{change_id}"),
            repository_identity="example/project",
            pull_request_identity=CompletionPullRequestIdentity(
                number=pull_request_number,
                node_id=f"PR_node_{pull_request_number}",
            ),
            accepted_target_ref="main",
            accepted_merge_commit=_receipt_commit(f"accepted:{change_id}"),
            merged_at=merged_at,
            acceptance_observation_id=_receipt_digest(f"acceptance:{change_id}"),
            check_observation_ids=(_receipt_digest(f"checks:{change_id}"),),
            review_receipt_ids=(_receipt_digest(f"review:{change_id}"),),
            completed_at=datetime(2026, 8, 11, 13, tzinfo=UTC),
        )
    )
    display = CompletionDisplayMetadata.create(
        change_id=change_id,
        completion_id=receipt.completion_id,
        title=title,
        outcome_titles=(f"Ship {title}",),
        outcome_promises=(f"Deliver the purpose of {title}.",),
    )
    store = CompletionReceiptStore(runtime_root)
    for participant in (store.participant(receipt), store.display_participant(display)):
        destination = participant.destination()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(participant.content)
    return receipt


def test_catalog_reports_missing_queries(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    catalog = CompletedHistoryCatalog(runtime_root)
    _publish_receipt(runtime_root, "change-a", "Alpha", pull_request_number=7)
    _publish_receipt(runtime_root, "change-b", "Beta", pull_request_number=8)
    cursor = catalog.list(limit=1).next_cursor
    _publish_receipt(runtime_root, "change-c", "Gamma", pull_request_number=9)

    with pytest.raises(CompletedHistoryError) as missing:
        catalog.show("missing-change")
    with pytest.raises(CompletedHistoryError) as exact_missing:
        catalog.show("change-a", "0" * 64)
    with pytest.raises(CompletedHistoryError) as stale:
        catalog.list(cursor=cursor, limit=1)

    assert missing.value.diagnostic.code == CompletedHistoryDiagnosticCode.MISSING
    assert exact_missing.value.diagnostic.code == CompletedHistoryDiagnosticCode.MISSING
    assert stale.value.diagnostic.code == CompletedHistoryDiagnosticCode.RECEIPT_SET_ADVANCED


def test_catalog_pages_searches_and_shows_receipt_history(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    _publish_receipt(runtime_root, "change-a", "Alpha", pull_request_number=7)
    second = _publish_receipt(runtime_root, "change-b", "Beta", pull_request_number=8)
    catalog = CompletedHistoryCatalog(runtime_root)

    page = catalog.list()
    search = catalog.search("beta")
    shown = catalog.show("change-b", second.completion_id)

    assert tuple((record.change_id, record.record_kind) for record in page.records) == (
        ("change-a", "completion-receipt"),
        ("change-b", "completion-receipt"),
    )
    assert page.total_count == 2
    assert search.records[0].completion_id == second.completion_id
    assert isinstance(shown, ReceiptCompletedChangeRecord)
    assert shown.finalized_change_head == second.finalized_change_head
    assert shown.accepted_merge_commit == second.accepted_merge_commit
    assert shown.finalized_change_head != shown.accepted_merge_commit


def test_catalog_reports_receipt_growth_separately_from_target_staleness(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    catalog = CompletedHistoryCatalog(runtime_root)
    _publish_receipt(runtime_root, "change-a", "Alpha accepted", pull_request_number=7)
    _publish_receipt(runtime_root, "change-b", "Beta accepted", pull_request_number=8)
    cursor = catalog.list(limit=1).next_cursor
    assert cursor is not None
    _publish_receipt(runtime_root, "change-c", "Gamma accepted", pull_request_number=9)

    with pytest.raises(CompletedHistoryReceiptSetAdvancedError) as advanced:
        catalog.list(cursor=cursor, limit=1)

    assert advanced.value.diagnostic.code == CompletedHistoryDiagnosticCode.RECEIPT_SET_ADVANCED


def test_catalog_fails_closed_for_malformed_receipt_display_metadata(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    _publish_receipt(runtime_root, "change-c", "Gamma accepted", pull_request_number=8)
    (runtime_root / "completions/change-c/display.json").write_bytes(b"not-json\n")

    with pytest.raises(CompletedHistoryError) as malformed:
        CompletedHistoryCatalog(runtime_root).list()

    assert malformed.value.diagnostic.code == CompletedHistoryDiagnosticCode.MALFORMED


def test_catalog_ignores_stray_runtime_entries_but_rejects_recognized_corruption(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    changes_root = runtime_root / "changes"
    changes_root.mkdir(parents=True)
    (changes_root / "README.txt").write_text("unrelated runtime note\n", encoding="utf-8")
    (changes_root / "not_a_change").mkdir()
    (changes_root / "not_a_change" / "frontier.json").write_text("not a Change\n", encoding="utf-8")
    (changes_root / "stray-link").symlink_to(changes_root / "README.txt")

    abandoned_id = "abandoned-change"
    abandoned_root = changes_root / abandoned_id
    abandoned_root.mkdir()
    contract = _contract(abandoned_id, "Abandoned delivery", b"intent", b"design")
    abandonment = DeliveryChangeAbandonment.create(
        change_id=abandoned_id,
        prior_stage=DeliveryChangeStage.BUILDING,
        abandoned_at=datetime(2026, 8, 11, 14, tzinfo=UTC),
        reason="User stopped the Change.",
    )
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.IMPLEMENTATION,
            ),
        ),
        change_abandonment=abandonment,
    )
    (abandoned_root / "contract.json").write_bytes(_canonical(contract))
    (abandoned_root / "frontier.json").write_bytes(_canonical(frontier))

    catalog = CompletedHistoryCatalog(runtime_root)
    page = catalog.list()

    assert tuple(record.change_id for record in page.records) == (abandoned_id,)
    assert page.records[0].record_kind == "abandoned-change"

    corrupt_root = changes_root / "recognized-corruption"
    corrupt_root.mkdir()
    (corrupt_root / "frontier.json").write_text("not-json\n", encoding="utf-8")

    with pytest.raises(CompletedHistoryError) as malformed:
        catalog.list()

    assert malformed.value.diagnostic.code == CompletedHistoryDiagnosticCode.MALFORMED
    assert malformed.value.diagnostic.change_id == "recognized-corruption"


def test_catalog_preserves_abandoned_target_sync_conflict_identity(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    change_id = "abandoned-change"
    changes_root = runtime_root / "changes" / change_id
    changes_root.mkdir(parents=True)
    contract = _contract(change_id, "Abandoned delivery", b"intent", b"design")
    abandonment = DeliveryChangeAbandonment.create(
        change_id=change_id,
        prior_stage=DeliveryChangeStage.BUILDING,
        abandoned_at=datetime(2026, 8, 11, 14, tzinfo=UTC),
        reason="User stopped the Change.",
    )
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.IMPLEMENTATION,
            ),
        ),
        change_abandonment=abandonment,
    )
    (changes_root / "contract.json").write_bytes(_canonical(contract))
    (changes_root / "frontier.json").write_bytes(_canonical(frontier))

    conflict = ChangeTargetSyncConflictState.create(
        operation_id="sync-abandoned",
        change_id=change_id,
        target_head="c" * 40,
        change_head_before="b" * 40,
        conflict_paths=("product.txt",),
    )
    coordination_root = runtime_root / "coordination" / "changes"
    coordination_root.mkdir(parents=True)
    coordination = ChangeCoordination(
        change_id=change_id,
        branch=f"owlbear/change/{change_id}",
        worktree_path=runtime_root / "worktrees" / change_id,
        integration_target="main",
        target_head="c" * 40,
        last_reviewed_commit="b" * 40,
        target_sync_conflict=conflict,
    )
    (coordination_root / f"{change_id}.json").write_bytes(coordination.model_dump_json().encode())

    record = CompletedHistoryCatalog(runtime_root).list().records[0]

    assert record.record_kind == "abandoned-change"
    assert record.target_sync_conflict is True
    assert record.target_sync_conflict_target_head == "c" * 40
    assert record.target_sync_conflict_operation_id == "sync-abandoned"
