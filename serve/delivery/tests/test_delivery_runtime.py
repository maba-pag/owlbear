from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from owlbear_delivery import (
    DELIVERY_TRANSITION_ADAPTER,
    ActivateDeliveryClaim,
    AdministrativeDeliveryMove,
    AdvanceDelivery,
    BlockDelivery,
    ChangeExternalHeadAdoptionReceipt,
    ChangeExternalHeadPromotionReceipt,
    ChangeTargetSyncReceipt,
    ChangeWorkspaceManager,
    ChangeWriter,
    CompletionDisplayMetadata,
    CompletionEvidence,
    CompletionPullRequestIdentity,
    CompletionReceipt,
    DeliveryAcceptanceWaitingError,
    DeliveryActiveClaim,
    DeliveryChangeAbandonment,
    DeliveryChangeCompletion,
    DeliveryChangeDeferral,
    DeliveryChangeDisposition,
    DeliveryChangeDispositionKind,
    DeliveryChangePublicationHistory,
    DeliveryChangePublicationIdentity,
    DeliveryChangeStage,
    DeliveryCheckpointTrigger,
    DeliveryCheckpointTriggerKind,
    DeliveryContract,
    DeliveryFinalizationInvalidationReceipt,
    DeliveryFinalizationReceipt,
    DeliveryFrontier,
    DeliveryIntegrationAttention,
    DeliveryIntegrationAttentionCode,
    DeliveryIntegrationAttentionDisposition,
    DeliveryMergedPullRequestLatch,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryOutcome,
    DeliveryOutputKind,
    DeliveryOutputReference,
    DeliveryPendingCheckpoint,
    DeliveryPlanScope,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryRequestResolution,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryRuntimeReferenceError,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryWorkerRole,
    FinalizeDeliveryChange,
    OutcomeAuthorityBinding,
    PortfolioCoordinator,
    PublicationPullRequest,
    PublicationPullRequestObservationReceipt,
    PublishDeliveryOutput,
    PublishDeliveryPlan,
    PublishDeliveryResult,
    RetryDelivery,
    ReturnDelivery,
    integration_attention_disposition,
    repair_missing_request_provenance,
)
from owlbear_delivery.delivery_runtime import (
    DeliveryBlock,
    DeliveryBuilderHandoffContext,
    DeliveryBuilderInvocationSettlement,
    DeliveryPlanningRetrySettlement,
    DeliveryRecoveryAttention,
    _DeliveryBuilderHandoffChangeIntentHead,
    _DeliveryBuilderHandoffChangeIntentReceipt,
    _DeliveryBuilderInvocationSettlementReceipt,
    _DeliveryBuilderRequestResolutionReceipt,
    _model_content,
    _read_builder_handoff_change_intent_receipts,
    _read_builder_request_resolution_receipt,
    invalidate_checkpoint_publication,
    parse_delivery_frontier,
)
from owlbear_delivery.draft_pull_request import PullRequestReadyReceipt
from owlbear_delivery.recovery import (
    DeliveryWorkerExclusionRequiredError,
    RetryEpisodeKey,
    RetryFailureClass,
    RetryLedger,
    RetryOwnerResult,
)
from owlbear_delivery.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionParticipant,
)


def test_parse_delivery_frontier_canonicalizes_schema_17_retry_defaults() -> None:
    frontier = DeliveryFrontier(bindings=(OutcomeAuthorityBinding(outcome_id="OUT-001", plan_scope_id="SCOPE-001"),))
    payload = frontier.model_dump(mode="json")
    payload["schema_version"] = 17
    payload["bindings"][0].pop("retry_count")
    payload["bindings"][0].pop("retry_fingerprint")
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()

    migrated, canonical = parse_delivery_frontier(raw)

    assert migrated.schema_version == 18
    assert migrated.bindings[0].retry_count == 0
    assert migrated.bindings[0].retry_fingerprint is None
    assert (
        canonical
        == (json.dumps(migrated.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    )


def test_parse_delivery_frontier_keeps_bytes_written_before_optional_binding_fields() -> None:
    frontier = DeliveryFrontier(bindings=(OutcomeAuthorityBinding(outcome_id="OUT-001", plan_scope_id="SCOPE-001"),))
    payload = frontier.model_dump(mode="json")
    payload["bindings"][0].pop("builder_handoff_context", None)
    payload["bindings"][0].pop("retry_diagnostic", None)
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()

    parsed, canonical = parse_delivery_frontier(raw)

    assert canonical == raw
    assert parsed.bindings[0].builder_handoff_context is None
    assert parsed.bindings[0].retry_diagnostic is None


def test_recovery_attention_omits_absent_diagnostic_transition() -> None:
    attention = DeliveryRecoveryAttention(
        attempt_id="attempt-1",
        claim_id="claim-1",
        reason="dirty worktree",
        worktree_path=".owlbear/delivery/worktrees/example",
        branch_head="a" * 40,
        last_reviewed_commit="b" * 40,
        custody_retained=True,
        retry_condition="inspect the worktree",
    )

    payload = attention.model_dump(mode="json")

    assert "diagnostic_transition" not in payload
    assert DeliveryRecoveryAttention.model_validate(payload) == attention


def test_repair_missing_request_provenance_rejects_wrong_or_multiple_defects() -> None:
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                requests=(
                    DeliveryRequest(
                        request_id="REQ-001",
                        kind=DeliveryRequestKind.ACTION,
                        outcome_id="OUT-001",
                        summary="Complete the pilot.",
                        resolution=DeliveryRequestResolution(
                            response_text="Use approved targets.",
                            provenance="user-confirmed",
                        ),
                    ),
                ),
            ),
        ),
    )
    payload = frontier.model_dump(mode="json")
    payload["schema_version"] = 17
    payload["bindings"][0]["requests"][0]["resolution"].pop("provenance")
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()

    with pytest.raises(DeliveryRuntimeReferenceError, match="unsupported request-provenance defect"):
        repair_missing_request_provenance(raw, "WRONG-REQUEST")

    duplicate = json.loads(raw)
    second = json.loads(json.dumps(duplicate["bindings"][0]["requests"][0]))
    second["request_id"] = "REQ-002"
    duplicate["bindings"][0]["requests"].append(second)
    duplicate_raw = (json.dumps(duplicate, sort_keys=True, separators=(",", ":")) + "\n").encode()
    with pytest.raises(DeliveryRuntimeReferenceError, match="unsupported request-provenance defect"):
        repair_missing_request_provenance(duplicate_raw, "REQ-001")


def test_exact_commit_evidence_receipts_validate_identity_and_independence() -> None:
    observed_at = datetime(2026, 8, 11, 12, tzinfo=UTC)
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id="delivery-runtime",
            task_or_finalization_id="TASK-001",
            exact_commit="1" * 40,
            observation_kind="pytest",
            command_or_procedure="uv run pytest focused.py",
            exit_status_or_artifact_locator="exit:0",
            observer_or_runner_identity="GitHub Copilot",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            exact_commit="1" * 40,
            author_id="GitHub Copilot",
            reviewer_id="build-reviewer",
            evidence=("Exact diff satisfies the Task authority.",),
            reviewed_at=observed_at,
        )
    )
    result_values = {
        "result_id": "RESULT-001",
        "change_id": "delivery-runtime",
        "authority_digest": "a" * 64,
        "task_id": "TASK-001",
        "task_digest": "b" * 64,
        "completed_commit": "1" * 40,
        "observations": (observation,),
        "review": review,
    }

    assert observation.exact_commit == review.exact_commit
    assert DeliveryTaskResult(**result_values).completed_commit == observation.exact_commit
    with pytest.raises(ValidationError, match="identity is invalid"):
        DeliveryObservationReceipt.model_validate(observation.model_copy(update={"exact_commit": "2" * 40}))
    with pytest.raises(ValidationError, match="independent"):
        DeliveryReviewReceipt.model_validate(review.model_copy(update={"reviewer_id": review.author_id}))
    with pytest.raises(ValidationError, match="observation evidence does not match"):
        DeliveryTaskResult(**(result_values | {"completed_commit": "2" * 40}))
    with pytest.raises(ValidationError, match="review evidence does not match"):
        DeliveryTaskResult(
            **(
                result_values
                | {
                    "review": DeliveryReviewReceipt.create(
                        DeliveryReview(
                            exact_commit="2" * 40,
                            author_id="GitHub Copilot",
                            reviewer_id="build-reviewer",
                            evidence=("Exact diff satisfies the Task authority.",),
                            reviewed_at=observed_at,
                        )
                    )
                }
            )
        )


def test_integration_attention_codes_have_one_operational_disposition() -> None:
    expected = {
        DeliveryIntegrationAttentionCode.MERGE_CONFLICT: DeliveryIntegrationAttentionDisposition.REPAIR_REQUIRED,
        DeliveryIntegrationAttentionCode.TARGET_CAS_LOST: DeliveryIntegrationAttentionDisposition.RETRYABLE,
    }

    assert {code: integration_attention_disposition(code) for code in DeliveryIntegrationAttentionCode} == {
        code: expected.get(code, DeliveryIntegrationAttentionDisposition.OPERATOR_REQUIRED)
        for code in DeliveryIntegrationAttentionCode
    }


def _contract() -> DeliveryContract:
    outcomes = (
        DeliveryOutcome(
            outcome_id="OUT-001",
            title="Foundation",
            promise="Deliver the foundation.",
            acceptance=("Foundation is observable.",),
            commitment_ids=(),
            dependency_ids=(),
        ),
        DeliveryOutcome(
            outcome_id="OUT-002",
            title="Dependent",
            promise="Deliver the dependent result.",
            acceptance=("Dependent result is observable.",),
            commitment_ids=(),
            dependency_ids=("OUT-001",),
        ),
        DeliveryOutcome(
            outcome_id="OUT-003",
            title="Independent",
            promise="Deliver the independent result.",
            acceptance=("Independent result is observable.",),
            commitment_ids=(),
            dependency_ids=(),
        ),
    )
    return DeliveryContract(
        change_id="delivery-runtime",
        title="Delivery runtime",
        commitments=(),
        outcomes=outcomes,
        plan_scopes=tuple(
            DeliveryPlanScope(scope_id=f"SCOPE-{index:03}", outcome_id=outcome.outcome_id)
            for index, outcome in enumerate(outcomes, start=1)
        ),
        source_bindings=(
            {"source_name": "intent.md", "sha256": "a" * 64},
            {"source_name": "design.md", "sha256": "b" * 64},
        ),
    )


def _canonical(model: DeliveryFrontier) -> bytes:
    return (json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()


def _frontier_changed_fields(before: DeliveryFrontier, after: DeliveryFrontier) -> set[str]:
    return {
        field_name
        for field_name in DeliveryFrontier.model_fields
        if getattr(before, field_name) != getattr(after, field_name)
    }


def _runtime(
    tmp_path: Path,
    *,
    stages: tuple[DeliveryStage, DeliveryStage, DeliveryStage] = (
        DeliveryStage.PLANNING,
        DeliveryStage.PLANNING,
        DeliveryStage.PLANNING,
    ),
) -> DeliveryRuntime:
    contract = _contract()
    authority_digest = hashlib.sha256(
        (json.dumps(contract.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    bindings = []
    for index, stage in enumerate(stages, start=1):
        task = _task(f"TASK-{index:03}", outcome_id=f"OUT-{index:03}")
        results = (
            (
                _task_result(
                    f"RESULT-{index:03}",
                    "delivery-runtime",
                    authority_digest,
                    task,
                    f"{index}" * 40,
                ),
            )
            if stage == DeliveryStage.COMPLETED
            else ()
        )
        bindings.append(
            OutcomeAuthorityBinding(
                outcome_id=f"OUT-{index:03}",
                plan_scope_id=f"SCOPE-{index:03}",
                stage=stage,
                tasks=(task,) if stage not in {DeliveryStage.DESIGN, DeliveryStage.PLANNING} else (),
                results=results,
            )
        )
    frontier = DeliveryFrontier(bindings=tuple(bindings))
    path = tmp_path / "changes/delivery-runtime/frontier.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(_canonical(frontier))
    return DeliveryRuntime(tmp_path, contract)


def _persist_frontier(tmp_path: Path, runtime: DeliveryRuntime, **updates: object) -> None:
    path = tmp_path / "changes/delivery-runtime/frontier.json"
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)
    path.write_bytes(_canonical(frontier.model_copy(update=updates)))


def _output(claim_id: str, stage: DeliveryStage) -> DeliveryOutputReference:
    return DeliveryOutputReference(
        output_id=f"output-{stage.value}",
        claim_id=claim_id,
        stage=stage,
        kind=DeliveryOutputKind(stage.value),
        digest="c" * 64,
    )


def _activate(
    runtime: DeliveryRuntime,
    outcome_id: str,
    claim_id: str,
    *,
    task_id: str | None = None,
    attempt_id: str | None = None,
):
    stage = runtime.show_binding(outcome_id).stage
    role = {
        DeliveryStage.PLANNING: DeliveryWorkerRole.PLANNER,
        DeliveryStage.IMPLEMENTATION: DeliveryWorkerRole.BUILDER,
    }[stage]
    return runtime.activate_claim(
        ActivateDeliveryClaim(
            outcome_id=outcome_id,
            claim=DeliveryActiveClaim(
                attempt_id=attempt_id or f"attempt-{claim_id}",
                claim_id=claim_id,
                owner_id=f"owner-{claim_id}",
                process_id=f"process-{claim_id}",
                started_at="2026-08-04T00:00:00Z",
                worker_role=role,
                task_id=task_id,
            ),
        )
    )


def _claim_with_output(runtime: DeliveryRuntime, outcome_id: str, claim_id: str) -> DeliveryOutputReference:
    binding = runtime.show_binding(outcome_id)
    task_id = runtime.claimable_task_ids(outcome_id)[0] if binding.stage == DeliveryStage.IMPLEMENTATION else None
    claimed = _activate(runtime, outcome_id, claim_id, task_id=task_id)
    output = _output(claim_id, claimed.stage)
    runtime.publish_output(PublishDeliveryOutput(outcome_id=outcome_id, claim_id=claim_id, output=output))
    return output


def test_integration_repair_claim_is_change_scoped_and_exact(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    attention = DeliveryIntegrationAttention(
        attention_id="a" * 64,
        code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
        change_id="delivery-runtime",
        change_head="1" * 40,
        target_head="2" * 40,
        integration_target="main",
        diagnostics=("merge conflict",),
        retry_condition="Admit an independently reviewed repair.",
    )
    _persist_frontier(tmp_path, runtime, integration_attention=attention)
    claim = DeliveryActiveClaim(
        attempt_id="repair-attempt",
        claim_id="repair-claim",
        owner_id="repair-owner",
        process_id="repair-process",
        started_at="2026-08-04T00:00:00Z",
        worker_role=DeliveryWorkerRole.INTEGRATION_REPAIRER,
    )

    _persist_frontier(
        tmp_path,
        runtime,
        integration_attention=attention,
        integration_repair_claim=claim,
    )
    assert runtime.require_integration_repair_claim("repair-attempt", "repair-claim") == claim
    with pytest.raises(DeliveryRuntimeConflictError, match="execution identity"):
        runtime.require_integration_repair_claim("other-attempt", "repair-claim")
    before = runtime.frontier_bytes()
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        runtime.remove_integration_repair_claim("repair-attempt", "repair-claim")
    assert runtime.frontier_bytes() == before
    assert runtime.integration_repair_claim() == claim


def _task(
    task_id: str,
    *,
    outcome_id: str = "OUT-001",
    dependency_ids: tuple[str, ...] = (),
) -> DeliveryTaskDefinition:
    plan_scope_id = outcome_id.replace("OUT", "SCOPE")
    return DeliveryTaskDefinition(
        task_id=task_id,
        outcome_id=outcome_id,
        plan_scope_id=plan_scope_id,
        title=f"Produce {task_id}",
        result="One bounded implementation result.",
        commitment_ids=(),
        dependency_ids=dependency_ids,
        required_outputs=("Reviewed source commit",),
        maintained_surfaces=("serve/delivery/src/owlbear_delivery/delivery_runtime.py",),
        constraints=("Keep schema-v2 state isolated.",),
        exclusions=("Do not edit bootstrap runtime.",),
        acceptance_observations=("The public runtime exposes the completed result binding.",),
        proof_boundaries=("Focused DeliveryRuntime behavior test",),
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
            command_or_procedure="focused Delivery runtime test",
            exit_status_or_artifact_locator="exit:0",
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            exact_commit=completed_commit,
            author_id="Delivery test author",
            reviewer_id="Delivery test reviewer",
            evidence=("The exact test commit satisfies task authority.",),
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


def _finalization_request(exact_head: str) -> FinalizeDeliveryChange:
    operation_id = "finalize-delivery-runtime"
    observed_at = datetime(2026, 8, 11, 13, tzinfo=UTC)
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id="delivery-runtime",
            task_or_finalization_id=operation_id,
            exact_commit=exact_head,
            observation_kind="pytest",
            command_or_procedure="full Delivery finalization validation",
            exit_status_or_artifact_locator="exit:0",
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            exact_commit=exact_head,
            author_id="Delivery finalization author",
            reviewer_id="Delivery finalization reviewer",
            evidence=("The exact Change head satisfies finalization authority.",),
            reviewed_at=observed_at,
        )
    )
    return FinalizeDeliveryChange(
        operation_id=operation_id,
        exact_head=exact_head,
        observations=(observation,),
        review=review,
    )


def _ready_receipt(finalization_id: str, exact_head: str) -> PullRequestReadyReceipt:
    observed_at = datetime(2026, 8, 11, 15, tzinfo=UTC)
    values = {
        "schema_version": 1,
        "operation_id": "ready-delivery-runtime",
        "change_id": "delivery-runtime",
        "finalization_id": finalization_id,
        "repository": "example/project",
        "number": 7,
        "node_id": "PR_node_7",
        "head_sha": exact_head,
        "draft": False,
        "observed_at": observed_at,
        "provider_evidence_digest": "a" * 64,
    }
    candidate = PullRequestReadyReceipt.model_construct(receipt_id="0" * 64, **values)
    payload = json.dumps(
        candidate.model_dump(mode="json", exclude={"receipt_id"}),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    receipt_id = hashlib.sha256(payload).hexdigest()
    return PullRequestReadyReceipt(receipt_id=receipt_id, **values)


def _pull_request_observation(  # noqa: PLR0913
    *,
    merged: bool = True,
    state: str | None = None,
    merge_commit_sha: str = "5" * 40,
    observed_at: datetime = datetime(2026, 8, 11, 16, tzinfo=UTC),
    merged_at: datetime = datetime(2026, 8, 11, 15, tzinfo=UTC),
    merged_by_login: str | None = None,
) -> PublicationPullRequestObservationReceipt:
    snapshot = PublicationPullRequest(
        repository="example/project",
        number=7,
        node_id="PR_node_7",
        head_branch="owlbear/change/delivery-runtime",
        head_sha="3" * 40,
        base_branch="main",
        title="Delivery runtime",
        body="Generated summary",
        draft=False,
        state=state or ("closed" if merged else "open"),
        merged=merged,
        merge_commit_sha=merge_commit_sha,
        merged_at=merged_at if merged else None,
        merged_by_login=merged_by_login,
    )
    provider_evidence_digest = hashlib.sha256(
        json.dumps(snapshot.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    values = {
        "schema_version": 1,
        "change_id": "delivery-runtime",
        "observed_at": observed_at,
        "snapshot": snapshot,
        "provider_evidence_digest": provider_evidence_digest,
    }
    candidate = PublicationPullRequestObservationReceipt.model_construct(observation_id="0" * 64, **values)
    observation_id = hashlib.sha256(
        json.dumps(
            candidate._identity_payload(),  # noqa: SLF001
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return PublicationPullRequestObservationReceipt(observation_id=observation_id, **values)


def _publication_identity(
    head_sha: str = "3" * 40,
    *,
    number: int = 7,
    node_id: str = "PR_node_7",
) -> DeliveryChangePublicationIdentity:
    return DeliveryChangePublicationIdentity(
        change_id="delivery-runtime",
        repository="example/project",
        number=number,
        node_id=node_id,
        head_sha=head_sha,
    )


def _completion_receipt(runtime: DeliveryRuntime) -> CompletionReceipt:
    finalization = runtime.finalization()
    latch = runtime.merged_pull_request_latch()
    assert finalization is not None
    assert latch is not None
    return CompletionReceipt.create(
        CompletionEvidence(
            change_id="delivery-runtime",
            finalization_receipt_id=finalization.finalization_id,
            finalized_change_head=finalization.exact_head,
            repository_identity=latch.repository,
            pull_request_identity=CompletionPullRequestIdentity(
                number=latch.number,
                node_id=latch.node_id,
            ),
            accepted_target_ref=latch.base_branch,
            accepted_merge_commit=latch.accepted_merge_commit,
            merged_at=latch.merged_at,
            acceptance_observation_id=latch.acceptance_observation_id,
            check_observation_ids=("8" * 64,),
            review_receipt_ids=(finalization.review.review_id,),
            completed_at=datetime(2026, 8, 11, 18, tzinfo=UTC),
        )
    )


def _awaiting_merge_runtime(tmp_path: Path) -> DeliveryRuntime:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    exact_head = "3" * 40
    finalization = runtime.finalize_change(
        _finalization_request(exact_head),
        datetime(2026, 8, 11, 14, tzinfo=UTC),
    )
    runtime.mark_awaiting_merge(_ready_receipt(finalization.finalization_id, exact_head))
    runtime.latch_merged_pull_request(_pull_request_observation())
    return runtime


def test_finalization_binds_exact_head_and_invalidates_on_head_drift(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    exact_head = "3" * 40
    request = _finalization_request(exact_head)

    receipt = runtime.finalize_change(request, datetime(2026, 8, 11, 14, tzinfo=UTC))

    assert isinstance(receipt, DeliveryFinalizationReceipt)
    assert runtime.finalize_change(request, datetime(2026, 8, 11, 15, tzinfo=UTC)) == receipt
    assert runtime.change_stage() == DeliveryChangeStage.FINALIZED
    publication = runtime.checkpoint_publication_state()
    assert publication.pending_checkpoint is not None
    assert publication.pending_checkpoint.head == exact_head
    assert DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FINALIZATION) in (
        publication.pending_checkpoint.triggers
    )

    ready = runtime.mark_awaiting_merge(_ready_receipt(receipt.finalization_id, exact_head))

    assert runtime.ready_receipt() == ready
    assert runtime.change_stage() == DeliveryChangeStage.AWAITING_MERGE

    invalidation = runtime.reconcile_finalization_head("4" * 40, datetime(2026, 8, 11, 16, tzinfo=UTC))

    assert isinstance(invalidation, DeliveryFinalizationInvalidationReceipt)
    assert invalidation.finalization_id == receipt.finalization_id
    assert runtime.finalization() is None
    assert runtime.ready_receipt() is None
    assert runtime.finalization_invalidation() == invalidation
    assert runtime.change_stage() == DeliveryChangeStage.BUILDING
    assert runtime.checkpoint_publication_state().pending_checkpoint is None


def test_review_repair_invalidates_current_finalization_and_replays(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    finalization = runtime.finalize_change(
        _finalization_request("3" * 40),
        datetime(2026, 8, 11, 14, tzinfo=UTC),
    )
    runtime.mark_awaiting_merge(_ready_receipt(finalization.finalization_id, "3" * 40))

    invalidation = runtime.prepare_review_repair(
        finalization.finalization_id,
        datetime(2026, 8, 11, 16, tzinfo=UTC),
    )

    assert invalidation.reason == "review-repair"
    assert invalidation.expected_head == invalidation.observed_head == "3" * 40
    assert runtime.finalization() is None
    assert runtime.ready_receipt() is None
    assert runtime.finalization_invalidation() == invalidation
    assert runtime.checkpoint_publication_state().pending_checkpoint is None
    assert runtime.prepare_review_repair(finalization.finalization_id, datetime(2026, 8, 11, 17, tzinfo=UTC)) == (
        invalidation
    )


def test_review_repair_rejects_finalizing_the_unchanged_head(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    finalization = runtime.finalize_change(
        _finalization_request("3" * 40),
        datetime(2026, 8, 11, 14, tzinfo=UTC),
    )
    runtime.prepare_review_repair(finalization.finalization_id, datetime(2026, 8, 11, 16, tzinfo=UTC))

    with pytest.raises(DeliveryRuntimeConflictError, match="new Change commit"):
        runtime.finalize_change(
            _finalization_request("3" * 40),
            datetime(2026, 8, 11, 17, tzinfo=UTC),
        )


def test_target_sync_persists_receipt_invalidates_finalization_and_queues_republication(
    tmp_path: Path,
) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    finalization = runtime.finalize_change(
        _finalization_request("3" * 40),
        datetime(2026, 8, 11, 14, tzinfo=UTC),
    )
    receipt = ChangeTargetSyncReceipt.create(
        operation_id="sync-delivery-runtime",
        change_id="delivery-runtime",
        integration_target="main",
        expected_target="4" * 40,
        target_head="4" * 40,
        change_head_before="3" * 40,
        merged_head="5" * 40,
        merge_commit=True,
    )

    recorded = runtime.record_target_sync(receipt, datetime(2026, 8, 11, 16, tzinfo=UTC))

    assert recorded == receipt
    assert runtime.finalization() is None
    assert runtime.finalization_invalidation() is not None
    assert runtime.finalization_invalidation().finalization_id == finalization.finalization_id
    assert runtime.change_stage() == DeliveryChangeStage.BUILDING
    publication = runtime.checkpoint_publication_state()
    assert publication.pending_checkpoint is not None
    assert publication.pending_checkpoint.head == "5" * 40
    assert publication.pending_checkpoint.triggers == (
        DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.EXPLICIT),
    )
    assert DeliveryRuntime(tmp_path, _contract()).frontier_bytes() == runtime.frontier_bytes()
    assert runtime.record_target_sync(receipt, datetime(2026, 8, 11, 17, tzinfo=UTC)) == receipt


def test_external_head_adoption_persists_receipt_invalidates_finalization_and_queues_republication(
    tmp_path: Path,
) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    finalization = runtime.finalize_change(
        _finalization_request("3" * 40),
        datetime(2026, 8, 11, 14, tzinfo=UTC),
    )
    receipt = ChangeExternalHeadAdoptionReceipt.create(
        operation_id="adopt-delivery-runtime",
        change_id="delivery-runtime",
        branch="owlbear/change/delivery-runtime",
        expected_head="3" * 40,
        adopted_head="5" * 40,
    )

    recorded = runtime.record_external_head_adoption(receipt, datetime(2026, 8, 11, 16, tzinfo=UTC))

    assert recorded == receipt
    assert runtime.external_head_adoption_receipt() == receipt
    assert runtime.finalization() is None
    invalidation = runtime.finalization_invalidation()
    assert invalidation is not None
    assert invalidation.finalization_id == finalization.finalization_id
    assert runtime.change_stage() == DeliveryChangeStage.BUILDING
    publication = runtime.checkpoint_publication_state()
    assert publication.pending_checkpoint is not None
    assert publication.pending_checkpoint.head == "5" * 40
    assert publication.pending_checkpoint.triggers == (
        DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.EXPLICIT),
    )
    assert DeliveryRuntime(tmp_path, _contract()).frontier_bytes() == runtime.frontier_bytes()
    assert runtime.record_external_head_adoption(receipt, datetime(2026, 8, 11, 17, tzinfo=UTC)) == receipt


def test_external_head_promotion_persists_exact_admission_and_replays_by_operation(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    adoption = ChangeExternalHeadAdoptionReceipt.create(
        operation_id="adopt-delivery-runtime",
        change_id="delivery-runtime",
        branch="owlbear/change/delivery-runtime",
        expected_head="1" * 40,
        adopted_head="5" * 40,
    )
    runtime.record_external_head_adoption(adoption, datetime(2026, 8, 11, 16, tzinfo=UTC))
    promotion = ChangeExternalHeadPromotionReceipt.create(
        operation_id="promote-delivery-runtime",
        change_id="delivery-runtime",
        branch="owlbear/change/delivery-runtime",
        adoption_receipt_id=adoption.receipt_id,
        promoted_head=adoption.adopted_head,
        provenance="explicit",
    )

    recorded = runtime.record_external_head_promotion(promotion, datetime(2026, 8, 11, 17, tzinfo=UTC))

    assert recorded == promotion
    assert runtime.external_head_promotion_receipt() == promotion
    assert DeliveryRuntime(tmp_path, _contract()).external_head_promotion_receipt() == promotion
    assert runtime.record_external_head_promotion(promotion, datetime(2026, 8, 11, 18, tzinfo=UTC)) == promotion


def test_external_head_promotion_rejects_stale_or_mismatched_adoption_evidence(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    adoption = ChangeExternalHeadAdoptionReceipt.create(
        operation_id="adopt-delivery-runtime",
        change_id="delivery-runtime",
        branch="owlbear/change/delivery-runtime",
        expected_head="1" * 40,
        adopted_head="5" * 40,
    )
    runtime.record_external_head_adoption(adoption, datetime(2026, 8, 11, 16, tzinfo=UTC))
    promotion = ChangeExternalHeadPromotionReceipt.create(
        operation_id="promote-delivery-runtime",
        change_id="delivery-runtime",
        branch="owlbear/change/delivery-runtime",
        adoption_receipt_id=adoption.receipt_id,
        promoted_head=adoption.adopted_head,
        provenance="explicit",
    )
    replacement_adoption = ChangeExternalHeadAdoptionReceipt.create(
        operation_id="adopt-replacement",
        change_id=adoption.change_id,
        branch=adoption.branch,
        expected_head=adoption.expected_head,
        adopted_head=adoption.adopted_head,
    )
    _persist_frontier(tmp_path, runtime, external_head_adoption_receipt=replacement_adoption)

    with pytest.raises(DeliveryRuntimeConflictError, match="current adoption evidence"):
        runtime.record_external_head_promotion(promotion, datetime(2026, 8, 11, 17, tzinfo=UTC))


def test_target_sync_conflict_captures_attention_and_invalidates_finalization(
    tmp_path: Path,
) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    finalization = runtime.finalize_change(
        _finalization_request("3" * 40),
        datetime(2026, 8, 11, 14, tzinfo=UTC),
    )

    disposition = runtime.capture_target_sync_conflict(
        "sync-conflict",
        "4" * 40,
        datetime(2026, 8, 11, 16, tzinfo=UTC),
        ("target synchronization merge conflict", "conflict-path:product.txt"),
    )

    assert disposition.kind == DeliveryChangeDispositionKind.PUBLICATION_ATTENTION
    assert runtime.change_stage() == DeliveryChangeStage.PUBLICATION_ATTENTION
    assert runtime.finalization() is None
    assert runtime.ready_receipt() is None
    invalidation = runtime.finalization_invalidation()
    assert invalidation is not None
    assert invalidation.finalization_id == finalization.finalization_id
    assert invalidation.reason == "target-sync-conflict"
    assert runtime.checkpoint_publication_state().pending_checkpoint is None


def test_target_sync_conflict_replaces_stale_receipt_and_normalizes_legacy_frontier(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    receipt = ChangeTargetSyncReceipt.create(
        operation_id="sync-previous",
        change_id="delivery-runtime",
        integration_target="main",
        expected_target="4" * 40,
        target_head="4" * 40,
        change_head_before="1" * 40,
        merged_head="5" * 40,
        merge_commit=True,
    )
    runtime.record_target_sync(receipt, datetime(2026, 8, 11, 15, tzinfo=UTC))

    runtime.capture_target_sync_conflict(
        "sync-current",
        "6" * 40,
        datetime(2026, 8, 11, 16, tzinfo=UTC),
        ("target synchronization merge conflict",),
    )

    assert runtime.target_sync_receipt() is None
    frontier_path = tmp_path / "changes/delivery-runtime/frontier.json"
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)
    frontier_path.write_bytes(_canonical(frontier.model_copy(update={"target_sync_receipt": receipt})))

    reloaded = DeliveryRuntime(tmp_path, _contract())
    assert reloaded.target_sync_receipt() is None
    assert reloaded.change_disposition() is not None


def test_change_attention_is_first_write_wins_and_blocks_claims(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    recorded_at = datetime(2026, 8, 11, 16, tzinfo=UTC)

    disposition = runtime.capture_publication_attention(recorded_at, ("provider unavailable",))

    assert disposition.kind == DeliveryChangeDispositionKind.PUBLICATION_ATTENTION
    assert runtime.change_disposition() == disposition
    assert runtime.capture_change_disposition(disposition) == disposition
    with pytest.raises(DeliveryRuntimeConflictError, match="different attention"):
        runtime.capture_change_disposition(
            DeliveryChangeDisposition.create(
                kind=DeliveryChangeDispositionKind.PUBLICATION_ATTENTION,
                change_id="delivery-runtime",
                entered_from=DeliveryChangeStage.BUILDING,
                recorded_at=recorded_at,
                diagnostics=("different evidence",),
            )
        )
    assert (
        runtime.capture_change_disposition(
            DeliveryChangeDisposition.create(
                kind=disposition.kind,
                change_id=disposition.change_id,
                entered_from=disposition.entered_from,
                recorded_at=recorded_at.replace(hour=17),
                diagnostics=disposition.diagnostics,
            )
        )
        == disposition
    )
    with pytest.raises(DeliveryRuntimeConflictError, match="requires attention"):
        _activate(runtime, "OUT-001", "claim-001")


def test_change_attention_resolution_is_exact_idempotent_and_preserves_ready_invalidation(tmp_path: Path) -> None:
    runtime = _awaiting_merge_runtime(tmp_path)
    disposition = runtime.capture_publication_attention(
        datetime(2026, 8, 11, 16, tzinfo=UTC),
        ("provider unavailable",),
        clear_ready=True,
    )

    with pytest.raises(DeliveryRuntimeConflictError, match="identity is stale"):
        runtime.resolve_change_disposition("0" * 64, datetime(2026, 8, 11, 17, tzinfo=UTC))

    resolution = runtime.resolve_change_disposition(
        disposition.disposition_id,
        datetime(2026, 8, 11, 17, tzinfo=UTC),
    )

    assert runtime.change_disposition() is None
    assert runtime.change_disposition_resolution() == resolution
    assert runtime.ready_receipt() is None
    assert (
        runtime.resolve_change_disposition(disposition.disposition_id, datetime(2026, 8, 11, 18, tzinfo=UTC))
        == resolution
    )


def test_publication_history_refreshes_one_pr_and_appends_successors(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    predecessor = _publication_identity()
    refreshed = _publication_identity("4" * 40)
    successor = _publication_identity("5" * 40, number=8, node_id="PR_node_8")

    first = runtime.record_publication_identity(predecessor)
    current = runtime.record_publication_identity(refreshed)
    runtime.capture_publication_attention(
        datetime(2026, 8, 11, 16, tzinfo=UTC),
        ("published history requires correction",),
        publication_identity=refreshed,
    )
    history = runtime.record_publication_successor(refreshed, successor)

    assert first.publications == (predecessor,)
    assert current.publications == (refreshed,)
    assert history.publications == (refreshed, successor)
    assert runtime.publication_history() == history
    assert (
        DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False).change_disposition_publication
        == successor
    )


def test_publication_history_rejects_stale_or_duplicate_successors(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    predecessor = _publication_identity()
    successor = _publication_identity("5" * 40, number=8, node_id="PR_node_8")
    runtime.record_publication_identity(predecessor)
    runtime.capture_publication_attention(
        datetime(2026, 8, 11, 16, tzinfo=UTC),
        ("published history requires correction",),
        publication_identity=predecessor,
    )

    with pytest.raises(DeliveryRuntimeConflictError, match="does not match current attention"):
        runtime.record_publication_successor(_publication_identity("4" * 40), successor)

    runtime.record_publication_successor(predecessor, successor)
    with pytest.raises(DeliveryRuntimeConflictError, match="does not match current attention"):
        runtime.record_publication_successor(
            predecessor, _publication_identity("6" * 40, number=9, node_id="PR_node_9")
        )


def test_publication_history_rejects_duplicate_provider_pr_generations() -> None:
    predecessor = _publication_identity()
    with pytest.raises(ValidationError, match="identities must be unique"):
        DeliveryChangePublicationHistory(
            change_id="delivery-runtime",
            publications=(predecessor, predecessor.model_copy(update={"head_sha": "4" * 40})),
        )


def test_publication_history_rejects_same_pr_as_a_new_successor(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    predecessor = _publication_identity()
    runtime.record_publication_identity(predecessor)
    runtime.capture_publication_attention(
        datetime(2026, 8, 11, 16, tzinfo=UTC),
        ("published history requires correction",),
        publication_identity=predecessor,
    )

    with pytest.raises(DeliveryRuntimeConflictError, match="identities must be unique"):
        runtime.record_publication_successor(predecessor, predecessor.model_copy(update={"head_sha": "4" * 40}))

    history = runtime.publication_history()
    assert history is not None
    assert history.publications == (predecessor,)


def test_ready_replay_backfills_history_for_migrated_frontier(tmp_path: Path) -> None:
    runtime = _awaiting_merge_runtime(tmp_path)
    ready = runtime.ready_receipt()
    assert ready is not None
    _persist_frontier(tmp_path, runtime, change_publication_history=None)

    assert runtime.publication_history() is None
    assert runtime.mark_awaiting_merge(ready) == ready
    history = runtime.publication_history()
    assert history is not None
    assert history.current.head_sha == ready.head_sha


def test_change_attention_recapture_clears_prior_resolution(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    recorded_at = datetime(2026, 8, 11, 16, tzinfo=UTC)
    disposition = runtime.capture_publication_attention(recorded_at, ("provider unavailable",))

    runtime.resolve_change_disposition(disposition.disposition_id, datetime(2026, 8, 11, 17, tzinfo=UTC))

    assert runtime.capture_publication_attention(recorded_at, ("provider unavailable",)) == disposition
    assert runtime.change_disposition_resolution() is None


def test_change_attention_capture_rejects_active_claims(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)
    claim = DeliveryActiveClaim(
        attempt_id="attempt-capture",
        claim_id="claim-capture",
        owner_id="owner-capture",
        process_id="process-capture",
        started_at="2026-08-11T16:00:00Z",
        worker_role=DeliveryWorkerRole.PLANNER,
    )
    claimed_binding = frontier.bindings[0].model_copy(update={"active_claim": claim})
    invalid_frontier = frontier.model_copy(update={"bindings": (claimed_binding, *frontier.bindings[1:])})

    with (
        patch.object(runtime, "_read", return_value=(invalid_frontier, runtime.frontier_bytes())),
        pytest.raises(DeliveryRuntimeConflictError, match="cannot overlap an active mutation claim"),
    ):
        runtime.capture_publication_attention(
            datetime(2026, 8, 11, 16, tzinfo=UTC),
            ("provider unavailable",),
        )


def test_change_attention_resolution_rejects_active_claims(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    disposition = runtime.capture_publication_attention(
        datetime(2026, 8, 11, 16, tzinfo=UTC),
        ("provider unavailable",),
    )
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)
    claim = DeliveryActiveClaim(
        attempt_id="attempt-resolution",
        claim_id="claim-resolution",
        owner_id="owner-resolution",
        process_id="process-resolution",
        started_at="2026-08-11T16:00:00Z",
        worker_role=DeliveryWorkerRole.PLANNER,
    )
    claimed_binding = frontier.bindings[0].model_copy(update={"active_claim": claim})
    invalid_frontier = frontier.model_copy(update={"bindings": (claimed_binding, *frontier.bindings[1:])})

    with (
        patch.object(runtime, "_read", return_value=(invalid_frontier, runtime.frontier_bytes())),
        pytest.raises(DeliveryRuntimeConflictError, match="cannot overlap an active mutation claim"),
    ):
        runtime.resolve_change_disposition(disposition.disposition_id, datetime(2026, 8, 11, 17, tzinfo=UTC))


def test_change_deferral_retains_frontier_and_suppresses_claimability(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)

    deferral = runtime.defer_change("pause for user review", datetime(2026, 8, 11, 17, tzinfo=UTC))

    assert isinstance(deferral, DeliveryChangeDeferral)
    assert deferral.prior_stage == DeliveryChangeStage.BUILDING
    assert runtime.change_deferral() == deferral
    assert runtime.change_stage() == DeliveryChangeStage.DEFERRED
    assert "OUT-001" not in runtime.claimable_outcome_ids()
    with pytest.raises(DeliveryRuntimeConflictError, match="requires resumption"):
        _activate(runtime, "OUT-001", "claim-deferred")

    assert runtime.resume_change() == deferral
    assert runtime.change_deferral() is None
    assert runtime.change_stage() == DeliveryChangeStage.BUILDING
    assert runtime.claimable_outcome_ids() == ("OUT-001", "OUT-003")
    assert not (tmp_path / "changes/delivery-runtime/builder-handoff-change-intent-receipts").exists()


def test_attention_can_be_deferred_and_resumes_to_the_same_attention_state(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    attention = runtime.capture_publication_attention(
        datetime(2026, 8, 11, 17, tzinfo=UTC),
        ("provider unavailable",),
    )

    deferral = runtime.defer_change("wait for provider recovery", datetime(2026, 8, 11, 18, tzinfo=UTC))

    assert deferral.prior_stage == DeliveryChangeStage.PUBLICATION_ATTENTION
    assert runtime.change_stage() == DeliveryChangeStage.DEFERRED
    runtime.resume_change()
    assert runtime.change_stage() == DeliveryChangeStage.PUBLICATION_ATTENTION
    assert runtime.change_disposition() == attention


def test_attention_can_be_abandoned_and_clears_active_attention(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.capture_publication_attention(
        datetime(2026, 8, 11, 17, tzinfo=UTC),
        ("provider unavailable",),
    )

    abandonment = runtime.abandon_change("user stopped the Change", datetime(2026, 8, 11, 18, tzinfo=UTC))

    assert abandonment.prior_stage == DeliveryChangeStage.PUBLICATION_ATTENTION
    assert runtime.change_disposition() is None
    assert runtime.change_abandonment() == abandonment
    assert runtime.change_stage() == DeliveryChangeStage.ABANDONED


def test_abandonment_clears_live_publication_and_integration_authority(tmp_path: Path) -> None:
    runtime = _awaiting_merge_runtime(tmp_path)
    attention = DeliveryIntegrationAttention(
        attention_id="a" * 64,
        code=DeliveryIntegrationAttentionCode.REPAIR_AUTHORITY,
        change_id="delivery-runtime",
        change_head="1" * 40,
        target_head="2" * 40,
        integration_target="main",
        diagnostics=("The repair exceeded admitted authority.",),
        retry_condition="Abandon the Change.",
    )
    _persist_frontier(tmp_path, runtime, integration_attention=attention)

    runtime.abandon_change("user stopped the Change", datetime(2026, 8, 11, 18, tzinfo=UTC))

    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)
    assert frontier.integration_attention is None
    assert frontier.integration_repair_claim is None
    assert frontier.pending_checkpoint is None
    assert frontier.ready is None
    assert frontier.merged_pull_request_latch is None


def test_change_deferral_rejects_active_claims(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _activate(runtime, "OUT-001", "claim-deferral")

    with pytest.raises(DeliveryRuntimeConflictError, match="cannot overlap an active mutation claim"):
        runtime.defer_change("pause", datetime(2026, 8, 11, 17, tzinfo=UTC))


def test_frontier_rejects_deferred_change_with_completion_authority(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.defer_change("pause for user review", datetime(2026, 8, 11, 17, tzinfo=UTC))
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)
    payload = frontier.model_dump(mode="python")
    payload["change_completion"] = DeliveryChangeCompletion(
        completion_id="a" * 64,
        completed_at=datetime(2026, 8, 11, 18, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="deferred Change cannot retain terminal completion authority"):
        DeliveryFrontier.model_validate(payload)


def test_change_abandonment_is_terminal_and_idempotent(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)

    abandonment = runtime.abandon_change("user stopped the Change", datetime(2026, 8, 11, 17, tzinfo=UTC))

    assert isinstance(abandonment, DeliveryChangeAbandonment)
    assert abandonment.prior_stage == DeliveryChangeStage.BUILDING
    assert runtime.change_abandonment() == abandonment
    assert runtime.change_stage() == DeliveryChangeStage.ABANDONED
    assert runtime.claimable_outcome_ids() == ()
    assert runtime.abandon_change("different replay text", datetime(2026, 8, 11, 18, tzinfo=UTC)) == abandonment
    with pytest.raises(DeliveryRuntimeConflictError, match="terminal"):
        runtime.resume_change()


def test_deferred_change_can_be_abandoned_with_deferred_prior_stage(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.defer_change("wait for user review", datetime(2026, 8, 11, 17, tzinfo=UTC))

    abandonment = runtime.abandon_change("user stopped the Change", datetime(2026, 8, 11, 18, tzinfo=UTC))

    assert abandonment.prior_stage == DeliveryChangeStage.DEFERRED
    assert runtime.change_deferral() is None
    assert runtime.change_stage() == DeliveryChangeStage.ABANDONED


def test_frontier_rejects_abandoned_change_with_lifecycle_attention(tmp_path: Path) -> None:
    attention_runtime = _runtime(tmp_path / "attention")
    attention_runtime.capture_publication_attention(
        datetime(2026, 8, 11, 17, tzinfo=UTC),
        ("provider unavailable",),
    )
    abandonment = DeliveryChangeAbandonment.create(
        change_id="delivery-runtime",
        prior_stage=DeliveryChangeStage.PUBLICATION_ATTENTION,
        abandoned_at=datetime(2026, 8, 11, 18, tzinfo=UTC),
        reason="user stopped the Change",
    )
    attention_payload = DeliveryFrontier.model_validate_json(
        attention_runtime.frontier_bytes(), strict=False
    ).model_dump(mode="python")
    attention_payload["change_abandonment"] = abandonment.model_dump(mode="python")

    with pytest.raises(ValueError, match="abandoned Change cannot retain active or terminal authority"):
        DeliveryFrontier.model_validate(attention_payload)


def test_pull_request_draft_regression_persists_publication_attention(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    exact_head = "3" * 40
    finalization = runtime.finalize_change(
        _finalization_request(exact_head),
        datetime(2026, 8, 11, 14, tzinfo=UTC),
    )
    ready = runtime.mark_awaiting_merge(_ready_receipt(finalization.finalization_id, exact_head))

    runtime.reconcile_pull_request_draft_state(
        provider_draft=True,
        observed_at=datetime(2026, 8, 11, 15, tzinfo=UTC),
        observation_id="d" * 64,
    )

    disposition = runtime.change_disposition()
    assert disposition is not None
    assert disposition.kind == DeliveryChangeDispositionKind.PUBLICATION_ATTENTION
    assert disposition.entered_from == DeliveryChangeStage.AWAITING_MERGE
    assert runtime.ready_receipt() is None
    assert ready.finalization_id == finalization.finalization_id


def test_open_unmerged_pull_request_is_retry_safe_waiting(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    exact_head = "3" * 40
    finalization = runtime.finalize_change(
        _finalization_request(exact_head),
        datetime(2026, 8, 11, 14, tzinfo=UTC),
    )
    runtime.mark_awaiting_merge(_ready_receipt(finalization.finalization_id, exact_head))

    with pytest.raises(DeliveryAcceptanceWaitingError, match="still open and unmerged"):
        runtime.latch_merged_pull_request(_pull_request_observation(merged=False))

    assert runtime.change_disposition() is None
    assert runtime.ready_receipt() is not None


def test_closed_unmerged_pull_request_persists_acceptance_attention(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    exact_head = "3" * 40
    finalization = runtime.finalize_change(
        _finalization_request(exact_head),
        datetime(2026, 8, 11, 14, tzinfo=UTC),
    )
    runtime.mark_awaiting_merge(_ready_receipt(finalization.finalization_id, exact_head))

    with pytest.raises(DeliveryRuntimeConflictError, match="does not report a merged"):
        runtime.latch_merged_pull_request(_pull_request_observation(merged=False, state="closed"))

    disposition = runtime.change_disposition()
    assert disposition is not None
    assert disposition.kind == DeliveryChangeDispositionKind.ACCEPTANCE_ATTENTION
    assert runtime.ready_receipt() is None
    publication = DeliveryFrontier.model_validate_json(
        runtime.frontier_bytes(), strict=False
    ).change_disposition_publication
    assert publication is not None
    assert (publication.repository, publication.number, publication.head_sha) == (
        "example/project",
        7,
        exact_head,
    )
    assert runtime.finalization() == finalization


def test_merged_pull_request_latch_is_monotonic_and_rejects_regression(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    exact_head = "3" * 40
    finalization = runtime.finalize_change(
        _finalization_request(exact_head),
        datetime(2026, 8, 11, 14, tzinfo=UTC),
    )
    runtime.mark_awaiting_merge(_ready_receipt(finalization.finalization_id, exact_head))

    first = runtime.latch_merged_pull_request(_pull_request_observation())
    replayed = runtime.latch_merged_pull_request(
        _pull_request_observation(
            observed_at=datetime(2026, 8, 11, 17, tzinfo=UTC),
            merged_by_login="octocat",
        )
    )

    assert isinstance(first, DeliveryMergedPullRequestLatch)
    assert replayed == first
    assert runtime.merged_pull_request_latch() == first

    with pytest.raises(DeliveryRuntimeConflictError):
        runtime.latch_merged_pull_request(_pull_request_observation(merge_commit_sha="6" * 40))
    with pytest.raises(DeliveryRuntimeConflictError):
        runtime.latch_merged_pull_request(_pull_request_observation(merged=False))

    assert runtime.merged_pull_request_latch() == first


def test_merged_pull_request_regression_captures_attention_and_retains_latch(tmp_path: Path) -> None:
    runtime = _awaiting_merge_runtime(tmp_path)
    original = runtime.merged_pull_request_latch()
    assert original is not None

    with pytest.raises(DeliveryRuntimeConflictError, match="regressed from the immutable merged latch"):
        runtime.latch_merged_pull_request(_pull_request_observation(merged=False))

    disposition = runtime.change_disposition()
    assert disposition is not None
    assert disposition.kind == DeliveryChangeDispositionKind.ACCEPTANCE_ATTENTION
    assert runtime.merged_pull_request_latch() == original
    assert runtime.ready_receipt() is None


def test_merged_pull_request_evidence_conflict_captures_attention(tmp_path: Path) -> None:
    runtime = _awaiting_merge_runtime(tmp_path)
    original = runtime.merged_pull_request_latch()
    assert original is not None

    with pytest.raises(DeliveryRuntimeConflictError, match="conflicts with the immutable latch"):
        runtime.latch_merged_pull_request(_pull_request_observation(merge_commit_sha="6" * 40))

    disposition = runtime.change_disposition()
    assert disposition is not None
    assert disposition.kind == DeliveryChangeDispositionKind.ACCEPTANCE_ATTENTION
    assert runtime.merged_pull_request_latch() == original
    assert runtime.ready_receipt() is None


def test_unfinalized_completed_change_uses_building_stage(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )

    assert runtime.change_stage() == DeliveryChangeStage.BUILDING
    assert DeliveryChangeStage.BUILDING.value == "building"


def test_completion_receipt_and_terminal_frontier_publish_atomically(tmp_path: Path) -> None:
    runtime = _awaiting_merge_runtime(tmp_path)
    receipt = _completion_receipt(runtime)

    completed = runtime.complete_change(receipt)

    assert completed == receipt
    assert runtime.completion_receipt() == receipt
    assert runtime.change_stage() == DeliveryChangeStage.COMPLETED
    assert runtime.complete_change(receipt) == receipt
    completion_path = tmp_path / "completions/delivery-runtime" / f"{receipt.completion_id}.json"
    assert CompletionReceipt.model_validate_json(completion_path.read_bytes()) == receipt
    display_path = tmp_path / "completions/delivery-runtime/display.json"
    display = CompletionDisplayMetadata.model_validate_json(display_path.read_bytes())
    assert display.completion_id == receipt.completion_id
    assert display.title == runtime.contract.title
    assert display.outcome_titles == tuple(outcome.title for outcome in runtime.contract.outcomes)
    assert display.outcome_promises == tuple(outcome.promise for outcome in runtime.contract.outcomes)
    with pytest.raises(DeliveryRuntimeConflictError, match="terminal"):
        runtime.reconcile_finalization_head("4" * 40, datetime(2026, 8, 11, 19, tzinfo=UTC))


def test_terminal_completion_rejects_missing_display_metadata(tmp_path: Path) -> None:
    runtime = _awaiting_merge_runtime(tmp_path)
    runtime.complete_change(_completion_receipt(runtime))
    (tmp_path / "completions/delivery-runtime/display.json").unlink()

    with pytest.raises(DeliveryRuntimeConflictError, match="completion record"):
        runtime.completion_receipt()


def test_completion_transaction_recovers_after_receipt_publication(tmp_path: Path) -> None:
    runtime = _awaiting_merge_runtime(tmp_path)
    receipt = _completion_receipt(runtime)
    original_commit = RuntimeTransaction.commit

    def fail_after_receipt(transaction: RuntimeTransaction) -> None:
        def failure(point: str) -> None:
            if point == "after-first-publication":
                message = "simulated completion crash"
                raise RuntimeError(message)

        original_commit(transaction, failure=failure)

    with (
        patch.object(RuntimeTransaction, "commit", fail_after_receipt),
        pytest.raises(RuntimeError, match="simulated completion crash"),
    ):
        runtime.complete_change(receipt)

    recovered = DeliveryRuntime(tmp_path, _contract())

    assert recovered.completion_receipt() == receipt
    assert recovered.change_stage() == DeliveryChangeStage.COMPLETED
    assert not tuple((tmp_path / "transactions").glob("*.yaml"))


def test_plan_publication_is_idempotent_and_promotes_dependency_order(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _activate(runtime, "OUT-001", "claim-001")
    request = PublishDeliveryPlan(
        outcome_id="OUT-001",
        claim_id="claim-001",
        tasks=(_task("TASK-001"), _task("TASK-002", dependency_ids=("TASK-001",))),
    )

    candidate = runtime.publish_plan(request)
    replayed = runtime.publish_plan(request)

    assert replayed == candidate
    assert runtime.show_binding("OUT-001").stage == DeliveryStage.PLANNING
    assert runtime.show_binding("OUT-001").tasks == ()

    promoted = runtime.transition(
        AdvanceDelivery(action="advance", outcome_id="OUT-001", claim_id="claim-001", output=candidate.output)
    )

    assert promoted.tasks == request.tasks
    assert promoted.candidate is None
    assert promoted.stage == DeliveryStage.IMPLEMENTATION
    assert runtime.claimable_task_ids("OUT-001") == ("TASK-001",)


def test_plan_publication_rejects_unresolved_or_cyclic_graph_without_mutation(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _activate(runtime, "OUT-001", "claim-001")
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryRuntimeReferenceError, match="dependency"):
        runtime.publish_plan(
            PublishDeliveryPlan(
                outcome_id="OUT-001",
                claim_id="claim-001",
                tasks=(_task("TASK-001", dependency_ids=("TASK-404",)),),
            )
        )
    assert runtime.frontier_bytes() == before

    with pytest.raises(DeliveryRuntimeConflictError, match="acyclic"):
        runtime.publish_plan(
            PublishDeliveryPlan(
                outcome_id="OUT-001",
                claim_id="claim-001",
                tasks=(
                    _task("TASK-001", dependency_ids=("TASK-002",)),
                    _task("TASK-002", dependency_ids=("TASK-001",)),
                ),
            )
        )
    assert runtime.frontier_bytes() == before


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603
        ("git", "-C", str(repository), *arguments),  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_worktree_snapshot(worktree: Path) -> tuple[tuple[tuple[str, bytes], ...], tuple[tuple[str, bytes], ...], str]:
    git_dir = Path(_git(worktree, "rev-parse", "--absolute-git-dir")).resolve()
    common_dir = Path(_git(worktree, "rev-parse", "--git-common-dir"))
    if not common_dir.is_absolute():
        common_dir = (worktree / common_dir).resolve()
    git_files = tuple(
        (str(path), path.read_bytes())
        for path in sorted(
            {path for root in {git_dir, common_dir} for path in root.rglob("*") if path.is_file()}, key=str
        )
    )
    worktree_files = tuple(
        (path.relative_to(worktree).as_posix(), path.read_bytes())
        for path in sorted(worktree.rglob("*"))
        if path.is_file()
    )
    status = _git(worktree, "--no-optional-locks", "status", "--porcelain=v2", "--untracked-files=all")
    return git_files, worktree_files, status


def _dirty_builder_worktree(worktree: Path) -> None:
    (worktree / "product.txt").write_text("unstaged builder work\n", encoding="utf-8")
    (worktree / "staged.txt").write_text("staged builder work\n", encoding="utf-8")
    _git(worktree, "add", "staged.txt")
    (worktree / "untracked.txt").write_text("untracked builder work\n", encoding="utf-8")


def _workspace(tmp_path: Path):
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Delivery Runtime Test")
    _git(repository, "config", "user.email", "delivery-runtime@example.invalid")
    (repository / "product.txt").write_text("base\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "baseline")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    state_root = tmp_path / "state"
    coordinator = PortfolioCoordinator(state_root)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "main")
    coordination = manager.ensure("delivery-runtime")
    return state_root, coordinator, manager, coordination


def _publish_task_result(
    runtime: DeliveryRuntime,
    coordinator: PortfolioCoordinator,
    coordination,
    *,
    job_id: int,
    outcome_id: str = "OUT-001",
):
    task_id = runtime.claimable_task_ids(outcome_id)[0]
    attempt_id = f"attempt-{job_id:03}"
    claim_id = f"claim-{job_id:03}"
    coordinator.acquire(
        "delivery-runtime",
        ChangeWriter(
            attempt_id=attempt_id,
            claim_id=claim_id,
            actor_id=f"builder-{job_id:03}",
            process_id=f"process-{job_id:03}",
            claimed_at=f"2026-08-04T00:0{job_id}:00Z",
            job_id=job_id,
            kind="build",
        ),
    )
    _activate(runtime, outcome_id, claim_id, task_id=task_id)
    (coordination.worktree_path / "product.txt").write_text(f"{task_id}\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "product.txt")
    _git(coordination.worktree_path, "commit", "-m", f"complete {task_id}")
    completed_commit = _git(coordination.worktree_path, "rev-parse", "HEAD")
    task = next(item for item in runtime.show_binding(outcome_id).tasks if item.task_id == task_id)
    result = _task_result(
        f"RESULT-{job_id:03}",
        "delivery-runtime",
        runtime.authority_digest,
        task,
        completed_commit,
    )
    candidate = runtime.publish_result(PublishDeliveryResult(outcome_id=outcome_id, claim_id=claim_id, result=result))
    return result, candidate, completed_commit, claim_id


def _plan_single_task(runtime: DeliveryRuntime, outcome_id: str, task: DeliveryTaskDefinition) -> None:
    claim_id = f"plan-{outcome_id}"
    _activate(runtime, outcome_id, claim_id)
    plan = runtime.publish_plan(
        PublishDeliveryPlan(
            outcome_id=outcome_id,
            claim_id=claim_id,
            tasks=(task,),
        )
    )
    runtime.transition(AdvanceDelivery(action="advance", outcome_id=outcome_id, claim_id=claim_id, output=plan.output))


def test_first_task_checkpoint_is_change_wide_and_one_task_outcomes_coalesce(tmp_path: Path) -> None:
    state_root, coordinator, manager, coordination = _workspace(tmp_path)
    frontier = DeliveryFrontier(
        bindings=tuple(
            OutcomeAuthorityBinding(
                outcome_id=f"OUT-{index:03}",
                plan_scope_id=f"SCOPE-{index:03}",
            )
            for index in range(1, 4)
        ),
        published_head=coordination.last_reviewed_commit,
    )
    frontier_path = state_root / "changes/delivery-runtime/frontier.json"
    frontier_path.parent.mkdir(parents=True)
    frontier_path.write_bytes(_canonical(frontier))
    runtime = DeliveryRuntime(state_root, _contract(), workspace_manager=manager)

    for index in (1, 3):
        outcome_id = f"OUT-{index:03}"
        task_id = f"TASK-{index:03}"
        _plan_single_task(runtime, outcome_id, _task(task_id, outcome_id=outcome_id))
        _result, candidate, _commit, claim_id = _publish_task_result(
            runtime,
            coordinator,
            coordination,
            job_id=index,
            outcome_id=outcome_id,
        )
        runtime.transition(
            AdvanceDelivery(action="advance", outcome_id=outcome_id, claim_id=claim_id, output=candidate.output)
        )

    pending = runtime.checkpoint_publication_state().pending_checkpoint
    assert pending is not None
    assert tuple((trigger.kind, trigger.outcome_id) for trigger in pending.triggers) == (
        (DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK, None),
        (DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME, "OUT-001"),
        (DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME, "OUT-003"),
    )

    preview = runtime.preview_administrative_move("OUT-001", DeliveryStage.PLANNING)
    runtime.administrative_move(
        AdministrativeDeliveryMove(
            move_id="move-checkpoint-reanchor",
            outcome_id="OUT-001",
            target=DeliveryStage.PLANNING,
            reason="Replace invalidated foundation authority.",
            expected_version=preview.snapshot_version,
        )
    )
    unanchored = runtime.checkpoint_publication_state().pending_checkpoint
    assert unanchored is not None
    assert unanchored.head is None
    assert tuple((trigger.kind, trigger.outcome_id) for trigger in unanchored.triggers) == (
        (DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK, None),
        (DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME, "OUT-003"),
    )

    _plan_single_task(runtime, "OUT-001", _task("TASK-004", outcome_id="OUT-001"))
    _result, candidate, reviewed_head, claim_id = _publish_task_result(
        runtime,
        coordinator,
        coordination,
        job_id=4,
    )
    runtime.transition(
        AdvanceDelivery(action="advance", outcome_id="OUT-001", claim_id=claim_id, output=candidate.output)
    )
    reanchored = runtime.checkpoint_publication_state().pending_checkpoint
    assert reanchored is not None
    assert reanchored.head == reviewed_head
    assert tuple((trigger.kind, trigger.outcome_id) for trigger in reanchored.triggers) == (
        (DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK, None),
        (DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME, "OUT-003"),
        (DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME, "OUT-001"),
    )


def test_pending_checkpoint_rejects_duplicate_first_task_trigger() -> None:
    with pytest.raises(ValueError, match="unique per scope"):
        DeliveryPendingCheckpoint(
            head="1" * 40,
            triggers=(
                DeliveryCheckpointTrigger(
                    kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
                ),
                DeliveryCheckpointTrigger(
                    kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
                ),
            ),
        )


def test_empty_checkpoint_invalidation_preserves_valid_anchor() -> None:
    pending = DeliveryPendingCheckpoint(
        head="1" * 40,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
    )

    assert invalidate_checkpoint_publication(pending, set()) is pending


def test_checkpoint_failure_metadata_survives_reload_and_reanchors_by_head(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    initial = DeliveryPendingCheckpoint(
        head="1" * 40,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.EXPLICIT),),
    )
    _persist_frontier(tmp_path, runtime, pending_checkpoint=initial)

    state = runtime.checkpoint_publication_state()
    assert state.pending_checkpoint is not None
    failed = runtime.record_checkpoint_failure(
        state.pending_checkpoint,
        datetime(2026, 8, 11, 16, tzinfo=UTC),
        "ERR_PROVIDER_UNAVAILABLE",
        "The provider is unavailable.",
    )

    pending = failed.pending_checkpoint
    assert pending is not None
    assert pending.attempt_count == 1
    assert pending.last_attempted_at == datetime(2026, 8, 11, 16, tzinfo=UTC)
    assert pending.last_error_code == "ERR_PROVIDER_UNAVAILABLE"
    assert pending.last_error_detail == "The provider is unavailable."
    assert DeliveryRuntime(tmp_path, _contract()).checkpoint_publication_state() == failed

    same_head = pending.model_copy(
        update={
            "triggers": (*pending.triggers, DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FINALIZATION))
        }
    )
    _persist_frontier(tmp_path, runtime, pending_checkpoint=same_head)
    assert runtime.checkpoint_publication_state().pending_checkpoint == same_head

    reanchored = DeliveryPendingCheckpoint(
        head="2" * 40,
        triggers=same_head.triggers,
    )
    _persist_frontier(tmp_path, runtime, pending_checkpoint=reanchored)
    assert runtime.checkpoint_publication_state().pending_checkpoint == reanchored


def test_build_advance_binds_exact_commit_evidence_and_releases_writer(tmp_path: Path) -> None:
    state_root, coordinator, manager, coordination = _workspace(tmp_path)
    frontier = DeliveryFrontier(
        bindings=tuple(
            OutcomeAuthorityBinding(
                outcome_id=f"OUT-{index:03}",
                plan_scope_id=f"SCOPE-{index:03}",
            )
            for index in range(1, 4)
        )
    )
    frontier_path = state_root / "changes/delivery-runtime/frontier.json"
    frontier_path.parent.mkdir(parents=True)
    frontier_path.write_bytes(_canonical(frontier))
    runtime = DeliveryRuntime(state_root, _contract(), workspace_manager=manager)
    _activate(runtime, "OUT-001", "plan-claim")
    plan = runtime.publish_plan(
        PublishDeliveryPlan(
            outcome_id="OUT-001",
            claim_id="plan-claim",
            tasks=(
                _task("TASK-001"),
                _task("TASK-002", dependency_ids=("TASK-001",)),
                _task("TASK-003", dependency_ids=("TASK-002",)),
            ),
        )
    )
    runtime.transition(
        AdvanceDelivery(action="advance", outcome_id="OUT-001", claim_id="plan-claim", output=plan.output)
    )
    result, candidate, completed_commit, first_claim = _publish_task_result(
        runtime,
        coordinator,
        coordination,
        job_id=1,
    )

    advance = AdvanceDelivery(action="advance", outcome_id="OUT-001", claim_id=first_claim, output=candidate.output)
    with (
        patch.object(runtime, "_replace", side_effect=RuntimeError("injected after workspace completion")),
        pytest.raises(RuntimeError, match="injected"),
    ):
        runtime.transition(advance)
    assert coordinator.show("delivery-runtime").last_reviewed_commit == completed_commit
    assert coordinator.show("delivery-runtime").writer is None

    advanced = runtime.transition(advance)

    assert advanced.results == (result,)
    assert advanced.stage == DeliveryStage.IMPLEMENTATION
    assert runtime.claimable_task_ids("OUT-001") == ("TASK-002",)
    assert coordinator.show("delivery-runtime").last_reviewed_commit == completed_commit
    assert coordinator.show("delivery-runtime").writer is None
    assert json.loads(runtime.frontier_bytes())["bindings"][0]["results"] == [result.model_dump(mode="json")]
    first_checkpoint = runtime.checkpoint_publication_state()
    assert first_checkpoint.published_head is None
    assert first_checkpoint.pending_checkpoint is not None
    assert first_checkpoint.pending_checkpoint.head == completed_commit
    assert tuple(trigger.kind for trigger in first_checkpoint.pending_checkpoint.triggers) == (
        DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
    )
    runtime.record_checkpoint_branch_publication(first_checkpoint, completed_commit)
    runtime.acknowledge_checkpoint_publication(first_checkpoint.pending_checkpoint, completed_commit)

    second_result, second_candidate, second_commit, second_claim = _publish_task_result(
        runtime,
        coordinator,
        coordination,
        job_id=2,
    )

    second_advance = runtime.transition(
        AdvanceDelivery(
            action="advance",
            outcome_id="OUT-001",
            claim_id=second_claim,
            output=second_candidate.output,
        )
    )

    assert second_advance.stage == DeliveryStage.IMPLEMENTATION
    middle_checkpoint = runtime.checkpoint_publication_state()
    assert middle_checkpoint.pending_checkpoint is not None
    assert middle_checkpoint.pending_checkpoint.head == second_commit
    assert tuple(trigger.kind for trigger in middle_checkpoint.pending_checkpoint.triggers) == (
        DeliveryCheckpointTriggerKind.VERIFIED_TASK,
    )
    third_result, third_candidate, _third_commit, third_claim = _publish_task_result(
        runtime,
        coordinator,
        coordination,
        job_id=3,
    )

    completed = runtime.transition(
        AdvanceDelivery(
            action="advance",
            outcome_id="OUT-001",
            claim_id=third_claim,
            output=third_candidate.output,
        )
    )

    assert completed.stage == DeliveryStage.COMPLETED
    assert completed.results == (result, second_result, third_result)
    completed_checkpoint = runtime.checkpoint_publication_state()
    assert completed_checkpoint.pending_checkpoint is not None
    assert completed_checkpoint.pending_checkpoint.head == third_result.completed_commit
    assert tuple(trigger.kind for trigger in completed_checkpoint.pending_checkpoint.triggers) == (
        DeliveryCheckpointTriggerKind.VERIFIED_TASK,
        DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
    )
    serialized = runtime.frontier_bytes().decode()
    for promoted_result in completed.results:
        assert promoted_result.observations[0].observation_id in serialized
        assert promoted_result.review.review_id in serialized


def _active_second_task(tmp_path: Path):
    state_root, coordinator, manager, coordination = _workspace(tmp_path)
    initial = _git(coordination.worktree_path, "rev-parse", "HEAD")
    contract = _contract()
    authority_digest = hashlib.sha256(
        (json.dumps(contract.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    tasks = (_task("TASK-001"), _task("TASK-002", dependency_ids=("TASK-001",)))
    first_result = _task_result(
        "RESULT-001",
        "delivery-runtime",
        authority_digest,
        tasks[0],
        initial,
    )
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.IMPLEMENTATION,
                tasks=tasks,
                results=(first_result,),
            ),
            OutcomeAuthorityBinding(outcome_id="OUT-002", plan_scope_id="SCOPE-002"),
            OutcomeAuthorityBinding(outcome_id="OUT-003", plan_scope_id="SCOPE-003"),
        )
    )
    frontier_path = state_root / "changes/delivery-runtime/frontier.json"
    frontier_path.parent.mkdir(parents=True)
    frontier_path.write_bytes(_canonical(frontier))
    runtime = DeliveryRuntime(state_root, contract, workspace_manager=manager)
    coordinator.acquire(
        "delivery-runtime",
        ChangeWriter(
            attempt_id="attempt-002",
            claim_id="claim-002",
            actor_id="builder-002",
            process_id="process-002",
            claimed_at="2026-08-04T00:00:00Z",
            job_id=2,
            kind="build",
        ),
    )
    _activate(runtime, "OUT-001", "claim-002", task_id="TASK-002", attempt_id="attempt-002")
    (coordination.worktree_path / "product.txt").write_text("unreviewed task two\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "product.txt")
    _git(coordination.worktree_path, "commit", "-m", "unreviewed task two")
    attempt_commit = _git(coordination.worktree_path, "rev-parse", "HEAD")
    return runtime, coordinator, coordination, initial, attempt_commit, first_result, tasks


@pytest.mark.parametrize("instruction", ["planning", "design", "block"])
def test_implementation_nonadvance_requires_verified_worker_exclusion(
    tmp_path: Path,
    instruction: str,
) -> None:
    runtime, coordinator, coordination, _, attempt_commit, _, _ = _active_second_task(tmp_path)
    requests = {
        "planning": ReturnDelivery(
            action="return",
            outcome_id="OUT-001",
            claim_id="claim-002",
            target=DeliveryStage.PLANNING,
            reason="The remaining task authority is incomplete.",
            locators=("TASK-002",),
            preserved_commit=attempt_commit,
            attempt_id="attempt-002",
        ),
        "design": ReturnDelivery(
            action="return",
            outcome_id="OUT-001",
            claim_id="claim-002",
            target=DeliveryStage.DESIGN,
            reason="The admitted outcome meaning is insufficient.",
            locators=("OUT-001",),
            preserved_commit=attempt_commit,
            attempt_id="attempt-002",
        ),
        "block": BlockDelivery(
            action="block",
            outcome_id="OUT-001",
            claim_id="claim-002",
            block_id="block-002",
            reason="External evidence is unavailable.",
            unblock_condition="The evidence is supplied.",
            expected_evidence=("External result",),
            locators=("TASK-002",),
            request=DeliveryRequest(
                request_id="request-002",
                kind=DeliveryRequestKind.ACTION,
                outcome_id="OUT-001",
                summary="Supply the external result.",
            ),
            resume_commit=attempt_commit,
        ),
    }

    before_frontier = runtime.frontier_bytes()
    before_coordination = coordinator.show("delivery-runtime")
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        runtime.transition(requests[instruction])

    before = DeliveryFrontier.model_validate_json(before_frontier)
    after = DeliveryFrontier.model_validate_json(runtime.frontier_bytes())
    assert after.bindings[0].recovery_attention.diagnostic_transition == requests[instruction]
    assert (
        after.model_copy(
            update={
                "bindings": tuple(binding.model_copy(update={"recovery_attention": None}) for binding in after.bindings)
            }
        )
        == before
    )
    assert coordinator.show("delivery-runtime") == before_coordination
    assert runtime.show_binding("OUT-001").active_claim_id == "claim-002"
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == attempt_commit
    legacy_attention = after.model_dump(mode="json")
    legacy_attention["bindings"][0]["recovery_attention"].pop("diagnostic_transition")
    parsed, _canonical_bytes = parse_delivery_frontier(json.dumps(legacy_attention).encode())
    assert parsed.schema_version == 18
    assert parsed.bindings[0].recovery_attention.diagnostic_transition is None
    assert parsed.bindings[0].active_claim == after.bindings[0].active_claim


def test_dirty_implementation_retry_rejects_without_mutating_claim_or_worktree(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, attempt_commit, _first_result, _tasks = _active_second_task(tmp_path)
    dirty_file = coordination.worktree_path / "dirty-retry.txt"
    dirty_file.write_text("preserve this work\n", encoding="utf-8")
    before = dirty_file.read_bytes()

    with pytest.raises(RuntimeError, match="clean change worktree"):
        runtime.transition(
            RetryDelivery(
                action="retry",
                outcome_id="OUT-001",
                claim_id="claim-002",
                abandoned_commit=attempt_commit,
                attempt_id="attempt-002",
            )
        )

    assert dirty_file.read_bytes() == before
    assert runtime.show_binding("OUT-001").active_claim_id == "claim-002"
    assert coordinator.show("delivery-runtime").writer is not None


def test_repeated_retry_exclusion_required_preserves_claim_and_budget(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path, stages=(DeliveryStage.PLANNING, DeliveryStage.PLANNING, DeliveryStage.PLANNING))
    _activate(runtime, "OUT-001", "retry-claim")
    before = DeliveryFrontier.model_validate_json(runtime.frontier_bytes())
    request = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="retry-claim",
        failure_code="planner-failed",
    )
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        runtime.transition(request)
    after = DeliveryFrontier.model_validate_json(runtime.frontier_bytes())
    active_claim = before.bindings[0].active_claim
    assert active_claim is not None
    after_payload = after.model_dump(mode="json")
    before_payload = before.model_dump(mode="json")
    assert after_payload["bindings"][0]["retry_diagnostic"] == {
        "code": "ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED",
        "attempt_id": active_claim.attempt_id,
        "transition": request.model_dump(mode="json"),
    }
    after_payload["bindings"][0]["retry_diagnostic"] = before_payload["bindings"][0]["retry_diagnostic"]
    assert after_payload == before_payload
    reloaded = DeliveryRuntime(tmp_path, runtime.contract)
    assert reloaded.show_binding("OUT-001").model_dump(mode="json")["retry_diagnostic"] == {
        "code": "ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED",
        "attempt_id": active_claim.attempt_id,
        "transition": request.model_dump(mode="json"),
    }
    persisted = runtime.frontier_bytes()
    for _attempt in range(3):
        with pytest.raises(DeliveryWorkerExclusionRequiredError):
            runtime.transition(request)
        assert runtime.frontier_bytes() == persisted
    assert "OUT-001" not in runtime.claimable_outcome_ids()


def test_clean_implementation_retry_exclusion_required(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, attempt_commit, _first_result, _tasks = _active_second_task(tmp_path)
    before = DeliveryFrontier.model_validate_json(runtime.frontier_bytes())
    custody = coordinator.show("delivery-runtime")
    before_head = _git(coordination.worktree_path, "rev-parse", "HEAD")
    before_index_tree = _git(coordination.worktree_path, "write-tree")
    before_refs = _git(coordination.worktree_path, "for-each-ref", "--format=%(refname) %(objectname)")
    before_status = _git(coordination.worktree_path, "status", "--porcelain")
    request = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        abandoned_commit=attempt_commit,
        attempt_id="attempt-002",
    )
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        runtime.transition(request)
    after = DeliveryFrontier.model_validate_json(runtime.frontier_bytes())
    active_claim = before.bindings[0].active_claim
    assert active_claim is not None
    assert after.bindings[0].model_dump(mode="json")["retry_diagnostic"] == {
        "code": "ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED",
        "attempt_id": active_claim.attempt_id,
        "transition": request.model_dump(mode="json"),
    }
    after_payload = after.model_dump(mode="json")
    before_payload = before.model_dump(mode="json")
    after_payload["bindings"][0]["retry_diagnostic"] = before_payload["bindings"][0]["retry_diagnostic"]
    assert after_payload == before_payload
    assert coordinator.show("delivery-runtime") == custody
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == before_head == attempt_commit
    assert _git(coordination.worktree_path, "write-tree") == before_index_tree
    assert _git(coordination.worktree_path, "for-each-ref", "--format=%(refname) %(objectname)") == before_refs
    assert _git(coordination.worktree_path, "status", "--porcelain") == before_status
    reloaded = DeliveryRuntime(tmp_path / "state", runtime.contract)
    assert reloaded.show_binding("OUT-001").model_dump(mode="json")["retry_diagnostic"] == {
        "code": "ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED",
        "attempt_id": active_claim.attempt_id,
        "transition": request.model_dump(mode="json"),
    }


def test_foreign_retry_claim_or_attempt_does_not_persist_diagnostic(tmp_path: Path) -> None:
    planning = _runtime(tmp_path, stages=(DeliveryStage.PLANNING, DeliveryStage.PLANNING, DeliveryStage.PLANNING))
    _activate(planning, "OUT-001", "retry-claim")
    planning_before = planning.frontier_bytes()
    with pytest.raises(DeliveryRuntimeConflictError):
        planning.transition(
            RetryDelivery(
                action="retry",
                outcome_id="OUT-001",
                claim_id="foreign-claim",
                failure_code="planner-failed",
            )
        )
    assert planning.frontier_bytes() == planning_before
    assert planning.show_binding("OUT-001").model_dump(mode="json")["retry_diagnostic"] is None

    builder, _coordinator, coordination, _initial, attempt_commit, _result, _tasks = _active_second_task(tmp_path)
    builder_before = builder.frontier_bytes()
    with pytest.raises(DeliveryRuntimeConflictError):
        builder.transition(
            RetryDelivery(
                action="retry",
                outcome_id="OUT-001",
                claim_id="claim-002",
                abandoned_commit=attempt_commit,
                attempt_id="foreign-attempt",
            )
        )
    assert builder.frontier_bytes() == builder_before
    assert builder.show_binding("OUT-001").model_dump(mode="json")["retry_diagnostic"] is None
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == attempt_commit


def _reserve_planning_settlement(runtime, attempt_id):
    ledger = runtime.retry_ledger()
    key = RetryEpisodeKey(
        change_id="delivery-runtime",
        action_kind="planning-retry",
        exact_head="planning-authority",
        outcome_id="OUT-001",
    )
    reservation = ledger.reserve(
        key,
        failure_class=RetryFailureClass.MECHANICAL,
        now=datetime(2026, 8, 4, tzinfo=UTC),
        attempt_id=attempt_id,
        original=True,
    )
    assert reservation.allowed
    return ledger, key


def test_planning_retry_settlement_clears_claim_and_replays_exact_receipt(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    claimed = _activate(runtime, "OUT-001", "planner-claim", attempt_id="planner-attempt")
    ledger, key = _reserve_planning_settlement(runtime, "planner-attempt")
    request = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="planner-claim",
        failure_code="planner-failed",
    )
    envelope = DeliveryPlanningRetrySettlement(
        change_id="delivery-runtime",
        outcome_id="OUT-001",
        claim_id="planner-claim",
        attempt_id="planner-attempt",
        disposition="normal-return",
        request=request,
    )

    observed_at = datetime(2026, 8, 4, tzinfo=UTC)
    result = runtime.settle_planning_retry(envelope, retry_observed_at=observed_at)
    owner_result_path = tmp_path / "changes/delivery-runtime/retry-ledger/owner-results/planner-attempt.json"
    owner_result = RetryOwnerResult.model_validate_json(owner_result_path.read_bytes())
    assert owner_result.accepted is False
    assert owner_result.failure_code == "planner-failed"
    assert datetime.fromisoformat(owner_result.observed_at) == observed_at
    ledger.reconcile_owner_results()
    assert ledger.episode(key).last_status == "failed"

    assert claimed.active_claim is not None
    assert result.stage == DeliveryStage.PLANNING
    assert result.active_claim is None
    assert result.output is None
    assert result.candidate is None
    assert result.retry_count == claimed.retry_count
    assert result.retry_fingerprint == claimed.retry_fingerprint
    settled_frontier = runtime.frontier_bytes()
    assert runtime.settle_planning_retry(envelope) == result
    assert runtime.frontier_bytes() == settled_frontier

    conflicting = envelope.model_copy(update={"request": request.model_copy(update={"failure_code": "other-failure"})})
    with pytest.raises(DeliveryRuntimeConflictError, match="immutable attempt receipt"):
        runtime.settle_planning_retry(conflicting)
    assert runtime.frontier_bytes() == settled_frontier
    _activate(runtime, "OUT-001", "new-planner-claim", attempt_id="new-planner-attempt")
    reacquired = runtime.frontier_bytes()
    accounted = ledger.read()
    assert runtime.settle_planning_retry(envelope) == result
    assert runtime.frontier_bytes() == reacquired
    assert ledger.read() == accounted
    with pytest.raises(DeliveryRuntimeConflictError):
        runtime.publish_plan(
            PublishDeliveryPlan(outcome_id="OUT-001", claim_id="planner-claim", tasks=(_task("TASK-001"),))
        )
    assert runtime.frontier_bytes() == reacquired


@pytest.mark.parametrize(
    "identity_update",
    [
        {"change_id": "another-change"},
        {"outcome_id": "OUT-002"},
        {"claim_id": "foreign-claim"},
        {"attempt_id": "stale-attempt"},
    ],
)
def test_planning_retry_settlement_rejects_foreign_or_stale_identity(
    tmp_path: Path,
    identity_update: dict[str, str],
) -> None:
    runtime = _runtime(tmp_path)
    _activate(runtime, "OUT-001", "planner-claim", attempt_id="planner-attempt")
    envelope = DeliveryPlanningRetrySettlement(
        change_id="delivery-runtime",
        outcome_id="OUT-001",
        claim_id="planner-claim",
        attempt_id="planner-attempt",
        disposition="normal-return",
        request=RetryDelivery(
            action="retry",
            outcome_id="OUT-001",
            claim_id="planner-claim",
            failure_code="planner-failed",
        ),
    )
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryRuntimeConflictError):
        runtime.settle_planning_retry(envelope.model_copy(update=identity_update))

    assert runtime.frontier_bytes() == before
    assert runtime.show_binding("OUT-001").active_claim is not None


def test_planning_retry_settlement_rejects_builder_claim(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.IMPLEMENTATION, DeliveryStage.PLANNING, DeliveryStage.PLANNING),
    )
    claimed = _activate(runtime, "OUT-001", "builder-claim", task_id="TASK-001", attempt_id="builder-attempt")
    envelope = DeliveryPlanningRetrySettlement(
        change_id="delivery-runtime",
        outcome_id="OUT-001",
        claim_id="builder-claim",
        attempt_id="builder-attempt",
        disposition="normal-return",
        request=RetryDelivery(
            action="retry",
            outcome_id="OUT-001",
            claim_id="builder-claim",
            failure_code="builder-failed",
        ),
    )
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryRuntimeConflictError, match="active Planner claim"):
        runtime.settle_planning_retry(envelope)

    assert claimed.active_claim is not None
    assert runtime.frontier_bytes() == before
    assert runtime.show_binding("OUT-001").active_claim == claimed.active_claim


def test_planning_retry_settlement_requires_completed_typed_disposition() -> None:
    values = {
        "change_id": "delivery-runtime",
        "outcome_id": "OUT-001",
        "claim_id": "planner-claim",
        "attempt_id": "planner-attempt",
    }
    request = RetryDelivery(action="retry", outcome_id="OUT-001", claim_id="planner-claim")

    with pytest.raises(ValidationError):
        DeliveryPlanningRetrySettlement(**values, disposition="running")
    with pytest.raises(ValidationError):
        DeliveryPlanningRetrySettlement(**values, disposition="normal-return")
    with pytest.raises(ValidationError, match="worker-timeout is reserved"):
        DeliveryPlanningRetrySettlement(
            **values,
            disposition="normal-return",
            request=RetryDelivery(
                action="retry",
                outcome_id="OUT-001",
                claim_id="planner-claim",
                failure_code="worker-timeout",
            ),
        )
    with pytest.raises(ValidationError):
        DeliveryPlanningRetrySettlement(
            **values,
            disposition="completed-timeout",
            request=request,
        )


def test_completed_planning_timeout_records_only_typed_worker_timeout(tmp_path: Path) -> None:
    attempt_id = "planning-timeout-attempt"
    runtime = _runtime(tmp_path)
    _activate(runtime, "OUT-001", "planner-claim", attempt_id=attempt_id)
    ledger, key = _reserve_planning_settlement(runtime, attempt_id)
    owner_result_path = tmp_path / "changes/delivery-runtime/retry-ledger/owner-results" / f"{attempt_id}.json"
    raw_retry = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="planner-claim",
        failure_code="worker-timeout",
    )
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        runtime.transition(raw_retry)
    assert not owner_result_path.exists()
    assert ledger.episode(key).last_status == "reserved"

    result = runtime.settle_planning_retry(
        DeliveryPlanningRetrySettlement(
            change_id="delivery-runtime",
            outcome_id="OUT-001",
            claim_id="planner-claim",
            attempt_id=attempt_id,
            disposition="completed-timeout",
        )
    )

    owner_result = RetryOwnerResult.model_validate_json(owner_result_path.read_bytes())
    assert result.active_claim is None
    assert owner_result.accepted is False
    assert owner_result.failure_code == "worker-timeout"
    ledger.reconcile_owner_results()
    episode = ledger.episode(key)
    assert episode is not None
    assert episode.total_attempts == 1
    assert episode.last_status == "failed"


def _builder_settlement_envelope(
    runtime: DeliveryRuntime,
    coordination,
    request: RetryDelivery | BlockDelivery | ReturnDelivery | None,
    disposition: str = "normal-return",
) -> DeliveryBuilderInvocationSettlement:
    claim = runtime.show_binding("OUT-001").active_claim
    assert claim is not None
    assert claim.task_id is not None
    return DeliveryBuilderInvocationSettlement(
        change_id="delivery-runtime",
        outcome_id="OUT-001",
        claim_id=claim.claim_id,
        attempt_id=claim.attempt_id,
        task_id=claim.task_id,
        expected_last_reviewed_commit=coordination.last_reviewed_commit,
        disposition=disposition,
        request=request,
    )


def _reserve_builder_settlement(
    runtime: DeliveryRuntime,
    attempt_id: str,
    expected_last_reviewed_commit: str,
    *,
    total_attempts: int = 1,
):
    ledger = runtime.retry_ledger()
    key = RetryEpisodeKey.worker(
        "delivery-runtime",
        "builder-claim",
        expected_last_reviewed_commit,
        contract_digest=runtime.authority_digest,
        outcome_id="OUT-001",
        task_lineage="TASK-002",
        procedure_class="builder",
        original_candidate="OUT-001",
    )
    started_at = datetime(2026, 8, 4, tzinfo=UTC)
    for index in range(1, total_attempts):
        reservation = ledger.reserve(
            key,
            failure_class=RetryFailureClass.MECHANICAL,
            now=started_at + timedelta(seconds=10 * index),
            attempt_id=f"prior-builder-attempt-{index}",
            original=index == 1,
        )
        assert reservation.allowed
        ledger.record_failure(
            reservation,
            failure_code="prior-builder-failure",
            now=started_at + timedelta(seconds=10 * index + 1),
        )
    reservation = ledger.reserve(
        key,
        failure_class=RetryFailureClass.MECHANICAL,
        now=started_at + timedelta(seconds=10 * (total_attempts + 1)),
        attempt_id=attempt_id,
        original=total_attempts == 1,
    )
    assert reservation.allowed
    return ledger, key


def test_builder_retry_settlement_preserves_git_bytes_and_same_task_handoff(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, first_result, tasks = _active_second_task(tmp_path)
    _dirty_builder_worktree(coordination.worktree_path)
    before_git = _git_worktree_snapshot(coordination.worktree_path)
    ledger, key = _reserve_builder_settlement(
        runtime,
        "attempt-002",
        coordination.last_reviewed_commit,
    )
    request = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        abandoned_commit=branch_head,
        attempt_id="attempt-002",
        failure_code="builder-failed",
    )
    envelope = _builder_settlement_envelope(runtime, coordination, request)
    tasks = (*tasks, _task("TASK-003"))
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes())
    expanded_binding = frontier.bindings[0].model_copy(update={"tasks": tasks})
    frontier_path = coordinator.runtime_root / "changes/delivery-runtime/frontier.json"
    frontier_path.write_bytes(
        _canonical(frontier.model_copy(update={"bindings": (expanded_binding, *frontier.bindings[1:])}))
    )
    observed_at = datetime(2026, 8, 4, 12, tzinfo=UTC)

    result = runtime.settle_builder_invocation(envelope, retry_observed_at=observed_at)

    assert _git_worktree_snapshot(coordination.worktree_path) == before_git
    assert result.stage == DeliveryStage.IMPLEMENTATION
    assert result.active_claim is None
    assert result.tasks == tasks
    assert result.results == (first_result,)
    assert result.block is None
    handoff_context = result.builder_handoff_context
    assert handoff_context is not None
    assert (
        handoff_context.outcome_id,
        handoff_context.original_task_id,
        handoff_context.attempt_id,
        handoff_context.last_reviewed_commit,
        handoff_context.route,
    ) == ("OUT-001", "TASK-002", "attempt-002", coordination.last_reviewed_commit, "same-task")
    assert runtime.claimable_task_ids("OUT-001") == ("TASK-002",)
    before_unrelated_activation = runtime.frontier_bytes()
    with pytest.raises(DeliveryRuntimeConflictError, match="implementation task is not claimable"):
        _activate(runtime, "OUT-001", "claim-unrelated-task", task_id="TASK-003", attempt_id="attempt-unrelated-task")
    assert runtime.frontier_bytes() == before_unrelated_activation
    workspace = coordinator.show("delivery-runtime")
    assert workspace.writer is not None
    assert workspace.writer.kind == "handoff"
    assert workspace.builder_handoff is not None
    assert workspace.builder_handoff.settlement_id == handoff_context.settlement_id
    assert workspace.builder_handoff.original_task_id == "TASK-002"
    assert workspace.builder_handoff.last_reviewed_commit == handoff_context.last_reviewed_commit
    assert workspace.builder_handoff.branch_head == handoff_context.branch_head
    assert workspace.builder_handoff.metadata_fingerprint == handoff_context.metadata_fingerprint
    owner_result_path = (
        coordinator.runtime_root / "changes/delivery-runtime/retry-ledger/owner-results/attempt-002.json"
    )
    owner_result_bytes = owner_result_path.read_bytes()
    owner_result = RetryOwnerResult.model_validate_json(owner_result_bytes)
    assert owner_result.accepted is False
    assert owner_result.paused is False
    assert owner_result.failure_code == "builder-failed"
    assert datetime.fromisoformat(owner_result.observed_at) == observed_at
    ledger.reconcile_owner_results()
    episode = ledger.episode(key)
    assert episode is not None
    assert episode.total_attempts == 1
    assert episode.reset_count == 0


@pytest.mark.parametrize("target", [DeliveryStage.PLANNING, DeliveryStage.DESIGN])
def test_builder_handoff_refuses_administrative_orphaning(tmp_path: Path, target: DeliveryStage) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    _dirty_builder_worktree(coordination.worktree_path)
    _reserve_builder_settlement(runtime, "attempt-002", coordination.last_reviewed_commit)
    request = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        attempt_id="attempt-002",
        abandoned_commit=branch_head,
    )
    runtime.settle_builder_invocation(_builder_settlement_envelope(runtime, coordination, request))
    frontier = runtime.frontier_bytes()
    custody = coordinator.coordination_bytes("delivery-runtime")
    git_state = _git_worktree_snapshot(coordination.worktree_path)
    with pytest.raises(DeliveryRuntimeConflictError, match="cannot orphan"):
        runtime.preview_administrative_move("OUT-001", target)
    with pytest.raises(DeliveryRuntimeConflictError, match="cannot orphan"):
        runtime.administrative_move(
            AdministrativeDeliveryMove(
                move_id="orphan-handoff",
                outcome_id="OUT-001",
                target=target,
                reason="synthetic operator move",
                expected_version=hashlib.sha256(frontier).hexdigest(),
            )
        )
    assert runtime.frontier_bytes() == frontier
    assert coordinator.coordination_bytes("delivery-runtime") == custody
    assert _git_worktree_snapshot(coordination.worktree_path) == git_state


def test_builder_settlement_reuses_registered_commit_alias_without_budget_renewal(tmp_path: Path) -> None:
    runtime, coordinator, coordination, initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    ledger, current_key = _reserve_builder_settlement(runtime, "alias-original-attempt", initial)
    original = ledger.episode(current_key)
    assert original is not None
    ledger.record_failure("alias-original-attempt", failure_code="original-failure", now="2026-08-04T00:00:31Z")
    next_key = current_key.model_copy(update={"exact_head": coordination.last_reviewed_commit})
    reserved = ledger.reserve(
        next_key,
        failure_class=RetryFailureClass.MECHANICAL,
        now="2026-08-04T00:00:40Z",
        attempt_id="attempt-002",
    )
    assert reserved.allowed
    assert reserved.episode_id == original.episode_id
    request = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        attempt_id="attempt-002",
        abandoned_commit=branch_head,
    )
    result = runtime.settle_builder_invocation(_builder_settlement_envelope(runtime, coordination, request))
    assert result.active_claim is None
    ledger.reconcile_owner_results()
    episode = ledger.episode_for_attempt("attempt-002")
    assert episode is not None
    assert episode.episode_id == original.episode_id
    assert episode.total_attempts == 2
    assert episode.reset_count == 0
    assert coordinator.show("delivery-runtime").builder_handoff is not None


def test_builder_settlement_skips_portable_publication_while_other_claim_is_active(tmp_path: Path) -> None:
    runtime, _coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    _activate(runtime, "OUT-003", "other-planner", attempt_id="other-planning-attempt")
    _reserve_builder_settlement(runtime, "attempt-002", coordination.last_reviewed_commit)
    request = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        attempt_id="attempt-002",
        abandoned_commit=branch_head,
    )
    result = runtime.settle_builder_invocation(_builder_settlement_envelope(runtime, coordination, request))
    assert result.active_claim is None
    assert runtime.show_binding("OUT-003").active_claim_id == "other-planner"
    assert runtime.pending_state_publication() is None


def test_builder_handoff_direct_activation_without_consumption_is_refused(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    _reserve_builder_settlement(runtime, "attempt-002", coordination.last_reviewed_commit)
    request = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        attempt_id="attempt-002",
        abandoned_commit=branch_head,
    )
    runtime.settle_builder_invocation(_builder_settlement_envelope(runtime, coordination, request))
    frontier = runtime.frontier_bytes()
    custody = coordinator.coordination_bytes("delivery-runtime")
    workspace = _git_worktree_snapshot(coordination.worktree_path)
    state_root = coordinator.runtime_root / "changes/delivery-runtime"
    state = {path.relative_to(state_root): path.read_bytes() for path in state_root.rglob("*") if path.is_file()}
    with pytest.raises(DeliveryRuntimeConflictError, match="jointly prepared"):
        _activate(runtime, "OUT-001", "unjoined-claim", task_id="TASK-002", attempt_id="unjoined-attempt")
    assert runtime.frontier_bytes() == frontier
    assert coordinator.coordination_bytes("delivery-runtime") == custody
    assert _git_worktree_snapshot(coordination.worktree_path) == workspace
    assert {
        path.relative_to(state_root): path.read_bytes() for path in state_root.rglob("*") if path.is_file()
    } == state

    owner_result_path = (
        coordinator.runtime_root / "changes/delivery-runtime/retry-ledger/owner-results/attempt-002.json"
    )
    owner_result = owner_result_path.read_bytes()
    bogus_participant = ReplacementTransactionParticipant(
        root=coordinator.runtime_root,
        relative_path=owner_result_path.relative_to(coordinator.runtime_root),
        expected_content=owner_result,
        replacement_content=owner_result,
    )
    activation = ActivateDeliveryClaim(
        outcome_id="OUT-001",
        claim=DeliveryActiveClaim(
            attempt_id="unjoined-attempt",
            claim_id="unjoined-claim",
            owner_id="owner-unjoined-claim",
            process_id="process-unjoined-claim",
            started_at="2026-08-04T00:00:00Z",
            worker_role=DeliveryWorkerRole.BUILDER,
            task_id="TASK-002",
        ),
    )
    with (
        coordinator.publication_lock("delivery-runtime") as lock,
        pytest.raises(
            DeliveryRuntimeConflictError,
            match="participant does not match",
        ),
    ):
        runtime.activate_claim(
            activation,
            builder_handoff_participant=bogus_participant,
            builder_handoff_lock=lock,
        )
    assert runtime.frontier_bytes() == frontier
    assert coordinator.coordination_bytes("delivery-runtime") == custody
    assert _git_worktree_snapshot(coordination.worktree_path) == workspace
    assert {
        path.relative_to(state_root): path.read_bytes() for path in state_root.rglob("*") if path.is_file()
    } == state


def test_builder_settlement_replay_conflict_and_late_publish_refusal(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, tasks = _active_second_task(tmp_path)
    _reserve_builder_settlement(runtime, "attempt-002", coordination.last_reviewed_commit)
    request = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        abandoned_commit=branch_head,
        attempt_id="attempt-002",
        failure_code="builder-failed",
    )
    envelope = _builder_settlement_envelope(runtime, coordination, request)
    result = runtime.settle_builder_invocation(envelope)
    owner_result_path = (
        coordinator.runtime_root / "changes/delivery-runtime/retry-ledger/owner-results/attempt-002.json"
    )
    owner_result_bytes = owner_result_path.read_bytes()
    settled_frontier = runtime.frontier_bytes()
    settled_workspace = coordinator.show("delivery-runtime")

    assert runtime.settle_builder_invocation(envelope) == result
    assert runtime.frontier_bytes() == settled_frontier
    assert coordinator.show("delivery-runtime") == settled_workspace
    assert owner_result_path.read_bytes() == owner_result_bytes

    conflicting = envelope.model_copy(
        update={"request": request.model_copy(update={"failure_code": "different-failure"})}
    )
    with pytest.raises(DeliveryRuntimeConflictError, match="immutable attempt receipt"):
        runtime.settle_builder_invocation(conflicting)
    assert runtime.frontier_bytes() == settled_frontier
    assert coordinator.show("delivery-runtime") == settled_workspace
    assert owner_result_path.read_bytes() == owner_result_bytes

    late_result = _task_result(
        "RESULT-002-LATE",
        "delivery-runtime",
        runtime.authority_digest,
        tasks[1],
        branch_head,
    )
    with pytest.raises(DeliveryRuntimeConflictError):
        runtime.publish_result(PublishDeliveryResult(outcome_id="OUT-001", claim_id="claim-002", result=late_result))
    assert runtime.frontier_bytes() == settled_frontier


def test_builder_settlement_rejects_candidate_conflicting_with_accepted_result(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, tasks = _active_second_task(tmp_path)
    candidate_result = _task_result(
        "RESULT-002-CANDIDATE",
        "delivery-runtime",
        runtime.authority_digest,
        tasks[1],
        branch_head,
    )
    runtime.publish_result(PublishDeliveryResult(outcome_id="OUT-001", claim_id="claim-002", result=candidate_result))
    accepted_result = _task_result(
        "RESULT-002-ACCEPTED",
        "delivery-runtime",
        runtime.authority_digest,
        tasks[1],
        coordination.last_reviewed_commit,
    )
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes())
    binding = frontier.bindings[0].model_copy(update={"results": (*frontier.bindings[0].results, accepted_result)})
    frontier_path = coordinator.runtime_root / "changes/delivery-runtime/frontier.json"
    frontier_path.write_bytes(_canonical(frontier.model_copy(update={"bindings": (binding, *frontier.bindings[1:])})))
    request = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        abandoned_commit=branch_head,
        attempt_id="attempt-002",
    )
    envelope = _builder_settlement_envelope(runtime, coordination, request)
    before_frontier = runtime.frontier_bytes()
    before_workspace = coordinator.show("delivery-runtime")
    before_git = _git_worktree_snapshot(coordination.worktree_path)

    with pytest.raises(DeliveryRuntimeConflictError, match="conflicts with its accepted result"):
        runtime.settle_builder_invocation(envelope)

    assert runtime.frontier_bytes() == before_frontier
    assert coordinator.show("delivery-runtime") == before_workspace
    assert _git_worktree_snapshot(coordination.worktree_path) == before_git


def test_builder_completed_timeout_records_only_typed_worker_timeout(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    before_git = _git_worktree_snapshot(coordination.worktree_path)
    ledger, key = _reserve_builder_settlement(
        runtime,
        "attempt-002",
        coordination.last_reviewed_commit,
    )
    envelope = _builder_settlement_envelope(runtime, coordination, None, "completed-timeout")

    result = runtime.settle_builder_invocation(
        envelope,
        retry_observed_at=datetime(2026, 8, 4, 12, tzinfo=UTC),
    )

    assert _git_worktree_snapshot(coordination.worktree_path) == before_git
    assert result.stage == DeliveryStage.IMPLEMENTATION
    owner_result = RetryOwnerResult.model_validate_json(
        (coordinator.runtime_root / "changes/delivery-runtime/retry-ledger/owner-results/attempt-002.json").read_bytes()
    )
    assert owner_result.failure_code == "worker-timeout"
    assert owner_result.accepted is False
    assert owner_result.paused is False
    ledger.reconcile_owner_results()
    episode = ledger.episode(key)
    assert episode is not None
    assert episode.total_attempts == 1
    assert episode.reset_count == 0
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == branch_head


def test_ended_without_result_settlements_require_no_request_and_reserve_failure_code() -> None:
    planner_values = {
        "change_id": "delivery-runtime",
        "outcome_id": "OUT-001",
        "claim_id": "planner-claim",
        "attempt_id": "planner-attempt",
    }
    builder_values = {
        "change_id": "delivery-runtime",
        "outcome_id": "OUT-001",
        "claim_id": "builder-claim",
        "attempt_id": "builder-attempt",
        "task_id": "TASK-002",
        "expected_last_reviewed_commit": "a" * 40,
    }
    planner_retry = RetryDelivery(action="retry", outcome_id="OUT-001", claim_id="planner-claim")
    builder_retry = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="builder-claim",
        attempt_id="builder-attempt",
        abandoned_commit="b" * 40,
    )

    assert DeliveryPlanningRetrySettlement(**planner_values, disposition="ended-without-result").request is None
    assert DeliveryBuilderInvocationSettlement(**builder_values, disposition="ended-without-result").request is None
    with pytest.raises(ValidationError, match="cannot carry an inner request"):
        DeliveryPlanningRetrySettlement(**planner_values, disposition="ended-without-result", request=planner_retry)
    with pytest.raises(ValidationError, match="cannot carry an inner request"):
        DeliveryBuilderInvocationSettlement(**builder_values, disposition="ended-without-result", request=builder_retry)
    with pytest.raises(ValidationError, match="worker-ended-without-result is reserved"):
        DeliveryPlanningRetrySettlement(
            **planner_values,
            disposition="normal-return",
            request=planner_retry.model_copy(update={"failure_code": "worker-ended-without-result"}),
        )
    with pytest.raises(ValidationError, match="worker-ended-without-result is reserved"):
        DeliveryBuilderInvocationSettlement(
            **builder_values,
            disposition="normal-return",
            request=builder_retry.model_copy(update={"failure_code": "worker-ended-without-result"}),
        )


def test_planning_ended_without_result_records_reserved_failure_and_replays_exact_receipt(tmp_path: Path) -> None:
    attempt_id = "planning-ended-attempt"
    runtime = _runtime(tmp_path)
    _activate(runtime, "OUT-001", "planner-claim", attempt_id=attempt_id)
    ledger, key = _reserve_planning_settlement(runtime, attempt_id)
    owner_result_path = tmp_path / "changes/delivery-runtime/retry-ledger/owner-results" / f"{attempt_id}.json"
    envelope = DeliveryPlanningRetrySettlement(
        change_id="delivery-runtime",
        outcome_id="OUT-001",
        claim_id="planner-claim",
        attempt_id=attempt_id,
        disposition="ended-without-result",
    )

    result = runtime.settle_planning_retry(envelope)

    owner_result_bytes = owner_result_path.read_bytes()
    owner_result = RetryOwnerResult.model_validate_json(owner_result_bytes)
    assert result.stage == DeliveryStage.PLANNING
    assert result.active_claim is None
    assert owner_result.accepted is False
    assert owner_result.failure_code == "worker-ended-without-result"
    settled_frontier = runtime.frontier_bytes()
    assert runtime.settle_planning_retry(envelope) == result
    assert runtime.frontier_bytes() == settled_frontier
    assert owner_result_path.read_bytes() == owner_result_bytes
    with pytest.raises(DeliveryRuntimeConflictError, match="immutable attempt receipt"):
        runtime.settle_planning_retry(envelope.model_copy(update={"disposition": "completed-timeout"}))
    with pytest.raises(DeliveryRuntimeConflictError):
        runtime.publish_plan(
            PublishDeliveryPlan(outcome_id="OUT-001", claim_id="planner-claim", tasks=(_task("TASK-001"),))
        )
    assert runtime.frontier_bytes() == settled_frontier
    assert owner_result_path.read_bytes() == owner_result_bytes
    ledger.reconcile_owner_results()
    episode = ledger.episode(key)
    assert episode is not None
    assert episode.total_attempts == 1
    assert episode.last_status == "failed"


def test_builder_ended_without_result_preserves_work_for_same_task_and_refuses_late_result(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, first_result, tasks = _active_second_task(tmp_path)
    _dirty_builder_worktree(coordination.worktree_path)
    before_git = _git_worktree_snapshot(coordination.worktree_path)
    ledger, key = _reserve_builder_settlement(runtime, "attempt-002", coordination.last_reviewed_commit)
    envelope = _builder_settlement_envelope(runtime, coordination, None, "ended-without-result")

    result = runtime.settle_builder_invocation(envelope, retry_observed_at=datetime(2026, 8, 4, 12, tzinfo=UTC))

    assert _git_worktree_snapshot(coordination.worktree_path) == before_git
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == branch_head
    assert result.stage == DeliveryStage.IMPLEMENTATION
    assert result.active_claim is None
    assert result.results == (first_result,)
    assert result.block is None
    handoff_context = result.builder_handoff_context
    assert handoff_context is not None
    assert (handoff_context.original_task_id, handoff_context.attempt_id, handoff_context.route) == (
        "TASK-002",
        "attempt-002",
        "same-task",
    )
    assert runtime.claimable_task_ids("OUT-001") == ("TASK-002",)
    workspace = coordinator.show("delivery-runtime")
    assert workspace.writer is not None
    assert workspace.writer.kind == "handoff"
    assert workspace.builder_handoff is not None
    assert workspace.builder_handoff.branch_head == handoff_context.branch_head
    owner_result_path = (
        coordinator.runtime_root / "changes/delivery-runtime/retry-ledger/owner-results/attempt-002.json"
    )
    owner_result_bytes = owner_result_path.read_bytes()
    owner_result = RetryOwnerResult.model_validate_json(owner_result_bytes)
    assert owner_result.failure_code == "worker-ended-without-result"
    assert owner_result.accepted is False
    assert owner_result.paused is False

    settled_frontier = runtime.frontier_bytes()
    assert runtime.settle_builder_invocation(envelope) == result
    assert runtime.frontier_bytes() == settled_frontier
    assert coordinator.show("delivery-runtime") == workspace
    with pytest.raises(DeliveryRuntimeConflictError, match="immutable attempt receipt"):
        runtime.settle_builder_invocation(envelope.model_copy(update={"disposition": "completed-timeout"}))
    late_result = _task_result("RESULT-002-LATE", "delivery-runtime", runtime.authority_digest, tasks[1], branch_head)
    with pytest.raises(DeliveryRuntimeConflictError):
        runtime.publish_result(PublishDeliveryResult(outcome_id="OUT-001", claim_id="claim-002", result=late_result))
    assert runtime.frontier_bytes() == settled_frontier
    assert coordinator.show("delivery-runtime") == workspace
    assert owner_result_path.read_bytes() == owner_result_bytes
    assert _git_worktree_snapshot(coordination.worktree_path) == before_git
    ledger.reconcile_owner_results()
    episode = ledger.episode(key)
    assert episode is not None
    assert episode.total_attempts == 1
    assert episode.reset_count == 0


def test_builder_request_block_pauses_without_charging_or_discarding_work(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, tasks = _active_second_task(tmp_path)
    candidate_result = _task_result(
        "pause-candidate", "delivery-runtime", runtime.authority_digest, tasks[1], branch_head
    )
    runtime.publish_result(PublishDeliveryResult(outcome_id="OUT-001", claim_id="claim-002", result=candidate_result))
    _dirty_builder_worktree(coordination.worktree_path)
    before_git = _git_worktree_snapshot(coordination.worktree_path)
    ledger, key = _reserve_builder_settlement(
        runtime,
        "attempt-002",
        coordination.last_reviewed_commit,
    )
    delivery_request = DeliveryRequest(
        request_id="builder-request-002",
        kind=DeliveryRequestKind.ACTION,
        outcome_id="OUT-001",
        summary="Provide the external evidence needed to continue.",
    )
    request = BlockDelivery(
        action="block",
        outcome_id="OUT-001",
        claim_id="claim-002",
        block_id="builder-block-002",
        reason="External evidence is unavailable.",
        unblock_condition="The requested evidence is supplied.",
        expected_evidence=("External evidence",),
        locators=("TASK-002",),
        request=delivery_request,
        resume_commit=branch_head,
    )
    envelope = _builder_settlement_envelope(runtime, coordination, request)

    result = runtime.settle_builder_invocation(envelope)

    assert _git_worktree_snapshot(coordination.worktree_path) == before_git
    assert result.active_claim is None
    assert result.output is None
    assert result.candidate is None
    assert result.result_candidate is None
    assert result.requests[-1] == delivery_request
    assert result.block is not None
    assert result.block.request_id == delivery_request.request_id
    assert not result.block.resolved
    assert result.builder_handoff_context is not None
    assert result.builder_handoff_context.original_task_id == "TASK-002"
    assert "OUT-001" not in runtime.claimable_outcome_ids()
    owner_result = RetryOwnerResult.model_validate_json(
        (coordinator.runtime_root / "changes/delivery-runtime/retry-ledger/owner-results/attempt-002.json").read_bytes()
    )
    assert owner_result.accepted is False
    assert owner_result.accepted_progress is False
    assert owner_result.paused is True
    ledger.reconcile_owner_results()
    episode = ledger.episode(key)
    assert episode is not None
    assert episode.total_attempts == 0
    assert episode.last_status == "paused"
    assert episode.reset_count == 0
    assert coordinator.show("delivery-runtime").builder_handoff is not None


def _assert_builder_request_resolution_receipt(
    receipt: _DeliveryBuilderRequestResolutionReceipt,
    resolved: DeliveryRequest,
    binding: OutcomeAuthorityBinding,
    context: DeliveryBuilderHandoffContext,
    receipt_path: Path,
) -> None:
    assert set(receipt.model_dump(mode="json")) == {
        "schema_version",
        "change_id",
        "outcome_id",
        "request_id",
        "settlement_id",
        "builder_handoff_context",
        "resolved_request",
        "updated_block",
    }
    assert receipt.change_id == "delivery-runtime"
    assert receipt.outcome_id == "OUT-001"
    assert receipt.request_id == resolved.request_id
    assert receipt.settlement_id == context.settlement_id
    assert receipt.builder_handoff_context == context
    assert receipt.resolved_request == resolved
    assert receipt.updated_block == binding.block
    assert receipt.updated_block.resolved
    assert receipt_path.name == f"{context.settlement_id}.json"

    invalid_request_identity = receipt.model_dump() | {"request_id": "different-builder-request"}
    with pytest.raises(ValidationError, match="Builder request resolution receipt"):
        _DeliveryBuilderRequestResolutionReceipt.model_validate(invalid_request_identity)
    invalid_settlement_identity = receipt.model_dump() | {"settlement_id": "f" * 64}
    with pytest.raises(ValidationError, match="Builder request resolution receipt"):
        _DeliveryBuilderRequestResolutionReceipt.model_validate(invalid_settlement_identity)
    unresolved_decision = receipt.model_dump()
    unresolved_decision["resolved_request"]["resolution"]["selected_option_id"] = None
    with pytest.raises(ValidationError, match="Builder request resolution receipt"):
        _DeliveryBuilderRequestResolutionReceipt.model_validate(unresolved_decision)
    forged_choice = receipt.model_dump()
    forged_choice["resolved_request"]["resolution"]["selected_option_id"] = "forged"
    with pytest.raises(ValidationError, match="Builder request resolution receipt"):
        _DeliveryBuilderRequestResolutionReceipt.model_validate(forged_choice)


def _stage_followup_builder_request_settlement(
    runtime: DeliveryRuntime,
    coordinator: PortfolioCoordinator,
    request: DeliveryRequest,
    original_block: BlockDelivery,
    previous_context: DeliveryBuilderHandoffContext,
) -> DeliveryBuilderHandoffContext:
    attempt_id = "attempt-003"
    claim_id = "claim-003"
    block_request = original_block.model_copy(
        update={"block_id": "builder-request-resolution-block-003", "claim_id": claim_id}
    )
    envelope = DeliveryBuilderInvocationSettlement(
        change_id="delivery-runtime",
        outcome_id=request.outcome_id,
        claim_id=claim_id,
        attempt_id=attempt_id,
        task_id=previous_context.original_task_id,
        expected_last_reviewed_commit=previous_context.last_reviewed_commit,
        disposition="normal-return",
        request=block_request,
    )
    context = DeliveryBuilderHandoffContext(
        settlement_id=hashlib.sha256(_model_content(envelope)).hexdigest(),
        original_task_id=previous_context.original_task_id,
        outcome_id=previous_context.outcome_id,
        attempt_id=attempt_id,
        last_reviewed_commit=previous_context.last_reviewed_commit,
        branch_head=previous_context.branch_head,
        metadata_fingerprint=previous_context.metadata_fingerprint,
        route="same-task",
    )
    block = DeliveryBlock(
        block_id=block_request.block_id,
        reason=block_request.reason,
        unblock_condition=block_request.unblock_condition,
        expected_evidence=block_request.expected_evidence,
        locators=block_request.locators,
        request_id=request.request_id,
        resume_commit=block_request.resume_commit,
    )
    binding = runtime.show_binding(request.outcome_id)
    followup_binding = OutcomeAuthorityBinding.model_validate(
        binding.model_dump(mode="python")
        | {
            "active_claim": None,
            "block": block,
            "builder_handoff_context": context,
            "requests": (request,),
        }
    )
    settlement_receipt = _DeliveryBuilderInvocationSettlementReceipt(
        settlement_id=context.settlement_id,
        envelope=envelope,
        handoff_context=context,
        result=followup_binding,
    )
    previous = runtime.frontier_bytes()
    frontier = DeliveryFrontier.model_validate_json(previous)
    followup_frontier = frontier.model_copy(
        update={
            "bindings": tuple(
                followup_binding if item.outcome_id == request.outcome_id else item for item in frontier.bindings
            )
        }
    )
    runtime._replace(
        previous,
        followup_frontier,
        additional_participants=(
            TransactionParticipant(
                coordinator.runtime_root,
                Path("changes")
                / "delivery-runtime"
                / "builder-invocation-receipts"
                / f"{hashlib.sha256(attempt_id.encode('utf-8')).hexdigest()}.json",
                _model_content(settlement_receipt),
            ),
        ),
    )
    return context


def _assert_resolution_reader_rejects_invalid_decisions(
    coordinator: PortfolioCoordinator,
    receipt_path: Path,
    receipt_content: bytes,
    receipt: _DeliveryBuilderRequestResolutionReceipt,
) -> None:
    context = receipt.builder_handoff_context
    try:
        for selected_option_id in (None, "forged"):
            invalid_receipt = receipt.model_dump(mode="json")
            invalid_receipt["resolved_request"]["resolution"]["selected_option_id"] = selected_option_id
            invalid_content = (json.dumps(invalid_receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
            receipt_path.write_bytes(invalid_content)
            with pytest.raises(DeliveryRuntimeReferenceError, match="Builder request resolution receipt is invalid"):
                _read_builder_request_resolution_receipt(
                    coordinator.runtime_root,
                    receipt.change_id,
                    receipt.request_id,
                    context,
                )
    finally:
        receipt_path.write_bytes(receipt_content)


def _assert_reused_request_has_independent_settlement_receipts(
    runtime: DeliveryRuntime,
    coordinator: PortfolioCoordinator,
    block_request: BlockDelivery,
    receipt: _DeliveryBuilderRequestResolutionReceipt,
    receipt_path: Path,
) -> None:
    request = block_request.request
    assert request is not None
    context = receipt.builder_handoff_context
    answer = receipt.resolved_request.resolution
    assert answer is not None
    resolved = receipt.resolved_request
    receipt_content = receipt_path.read_bytes()
    pending_publication = runtime.pending_state_publication()
    second_context = _stage_followup_builder_request_settlement(runtime, coordinator, request, block_request, context)
    second_receipt_path = receipt_path.parent / f"{second_context.settlement_id}.json"
    before_second_resolution = runtime.frontier_bytes()
    assert second_context.settlement_id != context.settlement_id
    assert second_receipt_path != receipt_path
    assert runtime.resolve_request(request.request_id, answer) == resolved
    after_second_resolution = runtime.frontier_bytes()
    assert after_second_resolution != before_second_resolution
    assert runtime.pending_state_publication() == pending_publication
    assert receipt_path.read_bytes() == receipt_content
    second_receipt = _read_builder_request_resolution_receipt(
        coordinator.runtime_root,
        "delivery-runtime",
        request.request_id,
        second_context,
    )
    _assert_builder_request_resolution_receipt(
        second_receipt,
        resolved,
        runtime.show_binding(context.outcome_id),
        second_context,
        second_receipt_path,
    )
    second_receipt_content = second_receipt_path.read_bytes()
    with pytest.raises(DeliveryRuntimeConflictError, match="already resolved"):
        runtime.resolve_request(request.request_id, DeliveryRequestResolution(selected_option_id="remote"))
    assert runtime.frontier_bytes() == after_second_resolution
    assert runtime.pending_state_publication() == pending_publication
    assert receipt_path.read_bytes() == receipt_content
    assert second_receipt_path.read_bytes() == second_receipt_content


def test_builder_request_resolution_persists_exact_local_receipt_without_side_effects(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    _dirty_builder_worktree(coordination.worktree_path)
    before_index = _git(coordination.worktree_path, "write-tree")
    before_git = _git_worktree_snapshot(coordination.worktree_path)
    ledger, key = _reserve_builder_settlement(runtime, "attempt-002", coordination.last_reviewed_commit)
    request = DeliveryRequest(
        request_id="builder-request-resolution-002",
        kind=DeliveryRequestKind.DECISION,
        outcome_id="OUT-001",
        summary="Choose the evidence source for the retained Builder task.",
        options=(
            DeliveryRequestOption(option_id="local", label="Use local evidence"),
            DeliveryRequestOption(option_id="remote", label="Wait for remote evidence"),
        ),
    )
    block_request = BlockDelivery(
        action="block",
        outcome_id="OUT-001",
        claim_id="claim-002",
        block_id="builder-request-resolution-block",
        reason="A bounded evidence-source decision is required.",
        unblock_condition="The user selects an evidence source.",
        expected_evidence=("Selected evidence source",),
        locators=("TASK-002",),
        request=request,
        resume_commit=branch_head,
    )
    settled = runtime.settle_builder_invocation(_builder_settlement_envelope(runtime, coordination, block_request))
    context = settled.builder_handoff_context
    assert context is not None
    assert settled.block is not None
    assert not settled.block.resolved
    ledger.reconcile_owner_results()
    paused_episode = ledger.episode(key)
    assert paused_episode is not None

    answer = DeliveryRequestResolution(
        selected_option_id="local",
        response_text="Use the verified local evidence.",
        provenance="user-confirmed",
    )
    unknown_request_id = "unknown-builder-request"
    receipt_directory = coordinator.runtime_root / "changes/delivery-runtime/builder-request-resolution-receipts"
    unknown_receipts_before = tuple(receipt_directory.glob("*.json"))
    before_unknown = runtime.frontier_bytes()
    with pytest.raises(DeliveryRuntimeReferenceError, match="absent or ambiguous"):
        runtime.resolve_request(unknown_request_id, answer)
    assert runtime.frontier_bytes() == before_unknown
    assert tuple(receipt_directory.glob("*.json")) == unknown_receipts_before

    receipt_path = (
        coordinator.runtime_root
        / "changes/delivery-runtime/builder-request-resolution-receipts"
        / f"{context.settlement_id}.json"
    )
    before_frontier = runtime.frontier_bytes()
    before_custody = coordinator.coordination_bytes("delivery-runtime")
    before_publication = runtime.pending_state_publication()

    resolved = runtime.resolve_request(request.request_id, answer)

    receipt_content = receipt_path.read_bytes()
    receipt = _DeliveryBuilderRequestResolutionReceipt.model_validate_json(receipt_content, strict=True)
    _assert_resolution_reader_rejects_invalid_decisions(
        coordinator,
        receipt_path,
        receipt_content,
        receipt,
    )
    binding = runtime.show_binding("OUT-001")
    _assert_builder_request_resolution_receipt(receipt, resolved, binding, context, receipt_path)
    assert (
        _read_builder_request_resolution_receipt(
            coordinator.runtime_root,
            "delivery-runtime",
            request.request_id,
            context,
        )
        == receipt
    )

    after_resolution = runtime.frontier_bytes()
    assert after_resolution != before_frontier
    assert runtime.pending_state_publication() == before_publication
    assert _git_worktree_snapshot(coordination.worktree_path) == before_git
    assert _git(coordination.worktree_path, "write-tree") == before_index
    assert coordinator.coordination_bytes("delivery-runtime") == before_custody
    assert coordinator.show("delivery-runtime").builder_handoff is not None
    assert ledger.episode(key) == paused_episode

    assert runtime.resolve_request(request.request_id, answer) == resolved
    assert runtime.frontier_bytes() == after_resolution
    assert runtime.pending_state_publication() == before_publication
    assert receipt_path.read_bytes() == receipt_content
    _assert_reused_request_has_independent_settlement_receipts(
        runtime,
        coordinator,
        block_request,
        receipt,
        receipt_path,
    )


def test_builder_handoff_blocks_administrative_move_without_mutation(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    _reserve_builder_settlement(runtime, "attempt-002", coordination.last_reviewed_commit)
    delivery_request = DeliveryRequest(
        request_id="builder-request-002",
        kind=DeliveryRequestKind.ACTION,
        outcome_id="OUT-001",
        summary="Provide the external evidence needed to continue.",
    )
    request = BlockDelivery(
        action="block",
        outcome_id="OUT-001",
        claim_id="claim-002",
        block_id="builder-block-002",
        reason="External evidence is unavailable.",
        unblock_condition="The requested evidence is supplied.",
        expected_evidence=("External evidence",),
        locators=("TASK-002",),
        request=delivery_request,
        resume_commit=branch_head,
    )
    runtime.settle_builder_invocation(_builder_settlement_envelope(runtime, coordination, request))
    before_frontier = runtime.frontier_bytes()
    before_coordination = coordinator.show("delivery-runtime")
    before_git = _git_worktree_snapshot(coordination.worktree_path)

    with pytest.raises(DeliveryRuntimeConflictError, match="Builder handoff"):
        runtime.preview_administrative_move("OUT-001", DeliveryStage.PLANNING)

    assert runtime.frontier_bytes() == before_frontier
    assert coordinator.show("delivery-runtime") == before_coordination
    assert _git_worktree_snapshot(coordination.worktree_path) == before_git

    with pytest.raises(DeliveryRuntimeConflictError, match="Builder handoff"):
        runtime.administrative_move(
            AdministrativeDeliveryMove(
                move_id="move-handoff",
                outcome_id="OUT-001",
                target=DeliveryStage.PLANNING,
                reason="The outcome authority needs revision.",
                expected_version=hashlib.sha256(before_frontier).hexdigest(),
            )
        )

    assert runtime.show_binding("OUT-001").builder_handoff_context is not None
    assert runtime.frontier_bytes() == before_frontier
    assert coordinator.show("delivery-runtime") == before_coordination
    assert _git_worktree_snapshot(coordination.worktree_path) == before_git


def _builder_handoff_external_state(
    runtime: DeliveryRuntime,
    coordinator: PortfolioCoordinator,
    worktree: Path,
    ledger: RetryLedger,
    key: RetryEpisodeKey,
) -> tuple[object, ...]:
    ledger_root = coordinator.runtime_root / "changes/delivery-runtime/retry-ledger"
    return (
        coordinator.coordination_bytes("delivery-runtime"),
        _git_worktree_snapshot(worktree),
        ledger.episode(key),
        tuple(
            (path.relative_to(ledger_root).as_posix(), path.read_bytes())
            for path in sorted(ledger_root.rglob("*"))
            if path.is_file()
        ),
        runtime.pending_state_publication(),
    )


def test_builder_handoff_defer_resume_receipts_are_exact_and_replayable(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    _dirty_builder_worktree(coordination.worktree_path)
    ledger, key = _reserve_builder_settlement(runtime, "attempt-002", coordination.last_reviewed_commit)
    retry = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        attempt_id="attempt-002",
        abandoned_commit=branch_head,
        failure_code="builder-failed",
    )
    settled = runtime.settle_builder_invocation(_builder_settlement_envelope(runtime, coordination, retry))
    context = settled.builder_handoff_context
    assert context is not None
    ledger.reconcile_owner_results()
    external_state = _builder_handoff_external_state(
        runtime,
        coordinator,
        coordination.worktree_path,
        ledger,
        key,
    )

    before_defer = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)
    deferral = runtime.defer_change("pause for user review", datetime(2026, 8, 11, 17, tzinfo=UTC))
    deferred_frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)
    defer_receipt = _read_builder_handoff_change_intent_receipts(
        coordinator.runtime_root,
        "delivery-runtime",
        context,
    )[0]
    assert defer_receipt.action == "defer"
    assert defer_receipt.deferral == deferral
    assert defer_receipt.before_frontier == before_defer
    assert defer_receipt.after_frontier == deferred_frontier
    assert defer_receipt.before_frontier_digest == hashlib.sha256(_model_content(before_defer)).hexdigest()
    assert defer_receipt.after_frontier_digest == hashlib.sha256(_model_content(deferred_frontier)).hexdigest()
    assert _frontier_changed_fields(before_defer, deferred_frontier) == {"change_deferral"}
    assert before_defer.bindings == deferred_frontier.bindings
    assert _builder_handoff_external_state(runtime, coordinator, coordination.worktree_path, ledger, key) == (
        external_state
    )

    before_replay = runtime.frontier_bytes()
    assert runtime.defer_change("different replay text", datetime(2026, 8, 11, 18, tzinfo=UTC)) == deferral
    assert runtime.frontier_bytes() == before_replay
    assert len(_read_builder_handoff_change_intent_receipts(coordinator.runtime_root, "delivery-runtime", context)) == 1

    assert runtime.resume_change() == deferral
    resumed_frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)
    receipts = _read_builder_handoff_change_intent_receipts(coordinator.runtime_root, "delivery-runtime", context)
    assert len(receipts) == 2
    resume_receipt = receipts[-1]
    assert resume_receipt.action == "resume"
    assert resume_receipt.deferral == deferral
    assert resume_receipt.before_frontier.change_deferral == deferral
    assert resume_receipt.after_frontier == resumed_frontier
    assert resume_receipt.after_frontier.change_deferral is None
    assert _frontier_changed_fields(resume_receipt.before_frontier, resumed_frontier) == {"change_deferral"}
    assert _builder_handoff_external_state(runtime, coordinator, coordination.worktree_path, ledger, key) == (
        external_state
    )

    before_duplicate_resume = runtime.frontier_bytes()
    with pytest.raises(DeliveryRuntimeConflictError, match="not deferred"):
        runtime.resume_change()
    assert runtime.frontier_bytes() == before_duplicate_resume


def test_builder_handoff_abandonment_receipt_removes_exact_deferral(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    _dirty_builder_worktree(coordination.worktree_path)
    ledger, key = _reserve_builder_settlement(runtime, "attempt-002", coordination.last_reviewed_commit)
    retry = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        attempt_id="attempt-002",
        abandoned_commit=branch_head,
        failure_code="builder-failed",
    )
    settled = runtime.settle_builder_invocation(_builder_settlement_envelope(runtime, coordination, retry))
    context = settled.builder_handoff_context
    assert context is not None
    ledger.reconcile_owner_results()
    external_state = _builder_handoff_external_state(runtime, coordinator, coordination.worktree_path, ledger, key)

    deferral = runtime.defer_change("pause before abandoning", datetime(2026, 8, 11, 17, tzinfo=UTC))
    before_abandon = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)
    abandonment = runtime.abandon_change("user stopped the Change", datetime(2026, 8, 11, 18, tzinfo=UTC))
    after_abandon = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)
    receipts = _read_builder_handoff_change_intent_receipts(
        coordinator.runtime_root,
        "delivery-runtime",
        context,
    )
    abandon_receipt = receipts[-1]
    assert len(receipts) == 2
    assert abandon_receipt.action == "abandon"
    assert abandon_receipt.deferral == deferral
    assert abandon_receipt.abandonment == abandonment
    assert abandonment.prior_stage == DeliveryChangeStage.DEFERRED
    assert after_abandon.change_deferral is None
    assert _frontier_changed_fields(before_abandon, after_abandon) == {"change_deferral", "change_abandonment"}
    assert _builder_handoff_external_state(runtime, coordinator, coordination.worktree_path, ledger, key) == (
        external_state
    )

    before_replay = runtime.frontier_bytes()
    assert runtime.abandon_change("ignored replay text", datetime(2026, 8, 11, 19, tzinfo=UTC)) == abandonment
    assert runtime.frontier_bytes() == before_replay
    assert (
        len(
            _read_builder_handoff_change_intent_receipts(
                coordinator.runtime_root,
                "delivery-runtime",
                context,
            )
        )
        == 2
    )


def test_builder_handoff_change_intent_cap_only_allows_terminal_abandon(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    _dirty_builder_worktree(coordination.worktree_path)
    ledger, key = _reserve_builder_settlement(runtime, "attempt-002", coordination.last_reviewed_commit)
    retry = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        attempt_id="attempt-002",
        abandoned_commit=branch_head,
        failure_code="builder-failed",
    )
    settled = runtime.settle_builder_invocation(_builder_settlement_envelope(runtime, coordination, retry))
    context = settled.builder_handoff_context
    assert context is not None
    ledger.reconcile_owner_results()
    external_state = _builder_handoff_external_state(runtime, coordinator, coordination.worktree_path, ledger, key)

    for index in range(16):
        deferred_at = datetime(2026, 8, 11, 17, tzinfo=UTC) + timedelta(minutes=index)
        runtime.defer_change(f"bounded pause {index}", deferred_at)
        runtime.resume_change()

    receipts = _read_builder_handoff_change_intent_receipts(coordinator.runtime_root, "delivery-runtime", context)
    assert len(receipts) == 32
    before_refused_defer = runtime.frontier_bytes()
    with pytest.raises(DeliveryRuntimeConflictError, match="receipt chain is exhausted"):
        runtime.defer_change("one too many nonterminal entries", datetime(2026, 8, 12, 17, tzinfo=UTC))
    assert runtime.frontier_bytes() == before_refused_defer
    assert (
        len(_read_builder_handoff_change_intent_receipts(coordinator.runtime_root, "delivery-runtime", context)) == 32
    )

    before_abandon = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)
    abandonment = runtime.abandon_change(
        "terminal abandonment at the receipt cap",
        datetime(2026, 8, 12, 18, tzinfo=UTC),
    )
    after_abandon = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)
    receipts = _read_builder_handoff_change_intent_receipts(coordinator.runtime_root, "delivery-runtime", context)
    assert len(receipts) == 33
    assert receipts[-1].sequence == 33
    assert receipts[-1].action == "abandon"
    assert receipts[-1].before_frontier == before_abandon
    assert receipts[-1].after_frontier == after_abandon
    assert after_abandon.change_abandonment == abandonment
    assert _builder_handoff_external_state(runtime, coordinator, coordination.worktree_path, ledger, key) == (
        external_state
    )

    first_deferral = next(receipt.deferral for receipt in receipts if receipt.action == "defer")
    assert first_deferral is not None
    base_frontier = receipts[-2].after_frontier
    nonterminal_after = base_frontier.model_copy(update={"change_deferral": first_deferral})
    nonterminal = _DeliveryBuilderHandoffChangeIntentReceipt.create(
        action="defer",
        change_id="delivery-runtime",
        outcome_id=context.outcome_id,
        context=context,
        sequence=33,
        previous_receipt_id=receipts[-2].receipt_id,
        before_frontier=base_frontier,
        after_frontier=nonterminal_after,
        deferral=first_deferral,
        abandonment=None,
    )
    head_path = (
        coordinator.runtime_root
        / "changes/delivery-runtime/builder-handoff-change-intent-receipts"
        / context.settlement_id
        / "head.json"
    )
    nonterminal_path = head_path.parent / f"{nonterminal.receipt_id}.json"
    nonterminal_path.write_bytes(_model_content(nonterminal))
    nonterminal_head = _DeliveryBuilderHandoffChangeIntentHead(
        change_id="delivery-runtime",
        outcome_id=context.outcome_id,
        settlement_id=context.settlement_id,
        builder_handoff_context=context,
        latest_receipt_id=nonterminal.receipt_id,
        sequence=33,
    )
    head_path.write_bytes(_model_content(nonterminal_head))
    with pytest.raises(DeliveryRuntimeReferenceError, match="receipt chain exceeds its supported limit"):
        _read_builder_handoff_change_intent_receipts(coordinator.runtime_root, "delivery-runtime", context)

    oversized_head = json.loads(head_path.read_bytes())
    oversized_head["sequence"] = 34
    head_path.write_bytes((json.dumps(oversized_head, sort_keys=True, separators=(",", ":")) + "\n").encode())
    with pytest.raises(DeliveryRuntimeReferenceError, match="head is invalid"):
        _read_builder_handoff_change_intent_receipts(coordinator.runtime_root, "delivery-runtime", context)


def test_builder_handoff_change_intent_rejects_bad_record_and_unknown_head(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    _dirty_builder_worktree(coordination.worktree_path)
    ledger, key = _reserve_builder_settlement(runtime, "attempt-002", coordination.last_reviewed_commit)
    retry = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        attempt_id="attempt-002",
        abandoned_commit=branch_head,
        failure_code="builder-failed",
    )
    settled = runtime.settle_builder_invocation(_builder_settlement_envelope(runtime, coordination, retry))
    context = settled.builder_handoff_context
    assert context is not None
    ledger.reconcile_owner_results()
    external_state = _builder_handoff_external_state(runtime, coordinator, coordination.worktree_path, ledger, key)
    runtime.defer_change("pause for user review", datetime(2026, 8, 11, 17, tzinfo=UTC))
    receipt = _read_builder_handoff_change_intent_receipts(
        coordinator.runtime_root,
        "delivery-runtime",
        context,
    )[0]

    invalid_receipt = receipt.model_dump(mode="json")
    invalid_receipt["after_frontier"]["bindings"][0]["tasks"][0]["title"] = "Unrecorded task mutation"
    invalid_after = DeliveryFrontier.model_validate_json(json.dumps(invalid_receipt["after_frontier"]), strict=True)
    invalid_receipt["after_frontier_digest"] = hashlib.sha256(_model_content(invalid_after)).hexdigest()
    with pytest.raises(ValidationError, match="unsupported frontier fields"):
        _DeliveryBuilderHandoffChangeIntentReceipt.model_validate_json(json.dumps(invalid_receipt), strict=True)

    head_path = (
        coordinator.runtime_root
        / "changes/delivery-runtime/builder-handoff-change-intent-receipts"
        / context.settlement_id
        / "head.json"
    )
    original_head = head_path.read_bytes()
    invalid_head = json.loads(original_head)
    invalid_head["latest_receipt_id"] = "f" * 64
    corrupt_head = (json.dumps(invalid_head, sort_keys=True, separators=(",", ":")) + "\n").encode()
    head_path.write_bytes(corrupt_head)
    before_refused_resume = runtime.frontier_bytes()
    try:
        with pytest.raises(DeliveryRuntimeReferenceError, match="Builder handoff change-intent receipt"):
            runtime.resume_change()
        assert runtime.frontier_bytes() == before_refused_resume
        assert head_path.read_bytes() == corrupt_head
    finally:
        head_path.write_bytes(original_head)
    assert _builder_handoff_external_state(runtime, coordinator, coordination.worktree_path, ledger, key) == (
        external_state
    )


def test_builder_handoff_rejects_other_binding_answer_and_unblock_without_mutation(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    _dirty_builder_worktree(coordination.worktree_path)
    ledger, key = _reserve_builder_settlement(runtime, "attempt-002", coordination.last_reviewed_commit)
    retry = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        attempt_id="attempt-002",
        abandoned_commit=branch_head,
        failure_code="builder-failed",
    )
    settled = runtime.settle_builder_invocation(_builder_settlement_envelope(runtime, coordination, retry))
    assert settled.builder_handoff_context is not None
    ledger.reconcile_owner_results()

    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)
    request = DeliveryRequest(
        request_id="other-outcome-request",
        kind=DeliveryRequestKind.ACTION,
        outcome_id="OUT-003",
        summary="Provide evidence for the unrelated outcome.",
    )
    requested_block = DeliveryBlock(
        block_id="other-outcome-request-block",
        reason="The unrelated outcome needs user evidence.",
        unblock_condition="The evidence is supplied.",
        expected_evidence=("User evidence",),
        locators=("OUT-003",),
        request_id=request.request_id,
    )
    requestless_block = DeliveryBlock(
        block_id="other-outcome-requestless-block",
        reason="The unrelated outcome needs verification.",
        unblock_condition="Verification is recorded.",
        expected_evidence=("Verification locator",),
        locators=("OUT-002",),
    )
    bindings = tuple(
        binding.model_copy(update={"requests": (request,), "block": requested_block})
        if binding.outcome_id == "OUT-003"
        else binding.model_copy(update={"block": requestless_block})
        if binding.outcome_id == "OUT-002"
        else binding
        for binding in frontier.bindings
    )
    path = coordinator.runtime_root / "changes/delivery-runtime/frontier.json"
    path.write_bytes(_canonical(frontier.model_copy(update={"bindings": bindings})))

    ledger_root = coordinator.runtime_root / "changes/delivery-runtime/retry-ledger"
    ledger_files = {
        item.relative_to(ledger_root).as_posix(): item.read_bytes()
        for item in sorted(ledger_root.rglob("*"))
        if item.is_file()
    }
    ledger_episode = ledger.episode(key)
    coordination_state = coordinator.coordination_bytes("delivery-runtime")
    git_state = _git_worktree_snapshot(coordination.worktree_path)
    before_frontier = runtime.frontier_bytes()
    publication_state = runtime.pending_state_publication()

    with pytest.raises(DeliveryRuntimeConflictError, match="outside the exact retained Builder handoff"):
        runtime.resolve_request(
            request.request_id,
            DeliveryRequestResolution(response_text="Use user workflow.", provenance="user-confirmed"),
        )
    assert runtime.frontier_bytes() == before_frontier

    with pytest.raises(DeliveryRuntimeConflictError, match="requestless unblock cannot mutate"):
        runtime.unblock(
            "OUT-002",
            requestless_block.block_id,
            "Retry budget is exhausted; wait for the user workflow handler.",
            ("retry-ledger",),
        )
    assert runtime.frontier_bytes() == before_frontier
    assert coordinator.coordination_bytes("delivery-runtime") == coordination_state
    assert _git_worktree_snapshot(coordination.worktree_path) == git_state
    assert ledger.episode(key) == ledger_episode
    assert {
        item.relative_to(ledger_root).as_posix(): item.read_bytes()
        for item in sorted(ledger_root.rglob("*"))
        if item.is_file()
    } == ledger_files
    assert runtime.pending_state_publication() == publication_state


def test_builder_return_to_planning_preserves_history_and_retains_partial_handoff(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, first_result, tasks = _active_second_task(tmp_path)
    before_git = _git_worktree_snapshot(coordination.worktree_path)
    ledger, key = _reserve_builder_settlement(
        runtime,
        "attempt-002",
        coordination.last_reviewed_commit,
    )
    request = ReturnDelivery(
        action="return",
        outcome_id="OUT-001",
        claim_id="claim-002",
        target=DeliveryStage.PLANNING,
        reason="The remaining implementation task needs clearer boundaries.",
        locators=("TASK-002",),
        preserved_commit=branch_head,
        attempt_id="attempt-002",
    )
    envelope = _builder_settlement_envelope(runtime, coordination, request)

    result = runtime.settle_builder_invocation(envelope)

    assert _git_worktree_snapshot(coordination.worktree_path) == before_git
    assert result.stage == DeliveryStage.PLANNING
    assert result.tasks == tasks
    assert result.results == (first_result,)
    assert result.return_context is not None
    assert result.return_context.completed_boundary == coordination.last_reviewed_commit
    assert result.builder_handoff_context is not None
    assert result.builder_handoff_context.route == "same-outcome-planner"
    assert result.block is None
    assert "OUT-001" in runtime.claimable_outcome_ids()
    assert coordinator.show("delivery-runtime").builder_handoff is not None
    ledger.reconcile_owner_results()
    episode = ledger.episode(key)
    assert episode is not None
    assert episode.total_attempts == 1
    assert episode.reset_count == 0


def _settle_builder_return_to_planning(tmp_path: Path, *, total_attempts: int = 1):
    runtime, coordinator, coordination, _initial, branch_head, _first_result, tasks = _active_second_task(tmp_path)
    ledger, _key = _reserve_builder_settlement(
        runtime,
        "attempt-002",
        coordination.last_reviewed_commit,
        total_attempts=total_attempts,
    )
    request = ReturnDelivery(
        action="return",
        outcome_id="OUT-001",
        claim_id="claim-002",
        target=DeliveryStage.PLANNING,
        reason="The remaining implementation task needs clearer boundaries.",
        locators=("TASK-002",),
        preserved_commit=branch_head,
        attempt_id="attempt-002",
    )
    returned = runtime.settle_builder_invocation(_builder_settlement_envelope(runtime, coordination, request))
    ledger.reconcile_owner_results()
    assert returned.builder_handoff_context is not None
    assert returned.builder_handoff_context.route == "same-outcome-planner"
    return runtime, coordinator, coordination, returned, tasks


def _activate_returned_planner(
    runtime: DeliveryRuntime,
    coordinator: PortfolioCoordinator,
    claim_id: str,
) -> OutcomeAuthorityBinding:
    activation = ActivateDeliveryClaim(
        outcome_id="OUT-001",
        claim=DeliveryActiveClaim(
            attempt_id=f"attempt-{claim_id}",
            claim_id=claim_id,
            owner_id=f"owner-{claim_id}",
            process_id=f"process-{claim_id}",
            started_at="2026-08-04T00:00:00Z",
            worker_role=DeliveryWorkerRole.PLANNER,
        ),
    )
    with coordinator.publication_lock("delivery-runtime") as lock:
        return runtime.activate_claim(activation, builder_handoff_lock=lock)


def _planner_return_block(claim_id: str, request: DeliveryRequest | None) -> BlockDelivery:
    return BlockDelivery(
        action="block",
        outcome_id="OUT-001",
        claim_id=claim_id,
        block_id=f"planner-return-block-{claim_id}",
        reason="The returned task boundary needs a user decision.",
        unblock_condition="The user records the boundary decision.",
        expected_evidence=("Boundary decision",),
        locators=("TASK-002",),
        request=request,
    )


def test_planner_pause_after_builder_return_is_answerable_and_reacquirable(tmp_path: Path) -> None:
    runtime, coordinator, coordination, returned, tasks = _settle_builder_return_to_planning(tmp_path)
    _activate_returned_planner(runtime, coordinator, "planner-claim-003")
    request = DeliveryRequest(
        request_id="planner-return-request-003",
        kind=DeliveryRequestKind.DECISION,
        outcome_id="OUT-001",
        summary="Choose the boundary for the returned task.",
        options=(
            DeliveryRequestOption(option_id="narrow", label="Narrow the task"),
            DeliveryRequestOption(option_id="split", label="Split the task"),
        ),
    )
    block = _planner_return_block("planner-claim-003", request)
    blocked = runtime.transition(block)
    assert blocked.block is not None
    assert blocked.block.request_id == request.request_id
    assert blocked.builder_handoff_context == returned.builder_handoff_context
    assert "OUT-001" not in runtime.claimable_outcome_ids()
    before_git = _git_worktree_snapshot(coordination.worktree_path)
    before_custody = coordinator.coordination_bytes("delivery-runtime")

    answer = DeliveryRequestResolution(selected_option_id="narrow", provenance="user-confirmed")
    resolved = runtime.resolve_request(request.request_id, answer)

    assert resolved.resolution == answer
    binding = runtime.show_binding("OUT-001")
    assert binding.block is not None
    assert binding.block.resolved
    assert binding.return_context == returned.return_context
    assert binding.builder_handoff_context == returned.builder_handoff_context
    assert runtime.claimable_outcome_ids() == ("OUT-001",)
    assert runtime.pending_state_publication() is None
    assert coordinator.coordination_bytes("delivery-runtime") == before_custody
    assert _git_worktree_snapshot(coordination.worktree_path) == before_git

    resolved_frontier = runtime.frontier_bytes()
    reopened = DeliveryRuntime(
        coordinator.runtime_root,
        runtime.contract,
        workspace_manager=ChangeWorkspaceManager(tmp_path / "repository", tmp_path / "worktrees", coordinator, "main"),
    )
    assert reopened.frontier_bytes() == resolved_frontier
    assert reopened.resolve_request(request.request_id, answer) == resolved
    assert reopened.transition(block) == blocked
    assert reopened.frontier_bytes() == resolved_frontier
    assert reopened.claimable_outcome_ids() == ("OUT-001",)

    _activate_returned_planner(reopened, coordinator, "planner-claim-004")
    candidate = reopened.publish_plan(
        PublishDeliveryPlan(outcome_id="OUT-001", claim_id="planner-claim-004", tasks=tasks)
    )
    advanced = reopened.transition(
        AdvanceDelivery(
            action="advance",
            outcome_id="OUT-001",
            claim_id="planner-claim-004",
            output=candidate.output,
        )
    )
    assert advanced.stage == DeliveryStage.IMPLEMENTATION
    assert advanced.builder_handoff_context is not None
    assert advanced.builder_handoff_context.route == "same-task"
    assert reopened.claimable_task_ids("OUT-001") == ("TASK-002",)


def test_requestless_planner_block_after_builder_return_is_operator_clearable(tmp_path: Path) -> None:
    runtime, coordinator, _coordination, returned, _tasks = _settle_builder_return_to_planning(tmp_path)
    _activate_returned_planner(runtime, coordinator, "planner-claim-003")
    block = _planner_return_block("planner-claim-003", None)
    runtime.transition(block)
    assert "OUT-001" not in runtime.claimable_outcome_ids()

    with pytest.raises(ValueError, match="operator note and locators"):
        runtime.unblock("OUT-001", block.block_id, "", ())
    cleared = runtime.unblock("OUT-001", block.block_id, "Boundary verified by operator.", ("TASK-002",))

    assert cleared.block is not None
    assert cleared.block.resolved
    assert cleared.return_context == returned.return_context
    assert cleared.builder_handoff_context == returned.builder_handoff_context
    assert runtime.claimable_outcome_ids() == ("OUT-001",)
    after = runtime.frontier_bytes()
    assert runtime.unblock("OUT-001", block.block_id, "Boundary verified by operator.", ("TASK-002",)) == cleared
    assert runtime.frontier_bytes() == after


def test_planner_return_handoff_refuses_foreign_or_unrecorded_answers_without_mutation(tmp_path: Path) -> None:
    runtime, coordinator, _coordination, _returned, _tasks = _settle_builder_return_to_planning(tmp_path)
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)
    other_request = DeliveryRequest(
        request_id="other-outcome-request",
        kind=DeliveryRequestKind.ACTION,
        outcome_id="OUT-003",
        summary="Provide evidence for the unrelated outcome.",
    )
    forged_request = other_request.model_copy(
        update={"request_id": "unrecorded-planner-request", "outcome_id": "OUT-001"}
    )
    other_block = DeliveryBlock(
        block_id="other-outcome-request-block",
        reason="The unrelated outcome needs user evidence.",
        unblock_condition="The evidence is supplied.",
        expected_evidence=("User evidence",),
        locators=("OUT-003",),
        request_id=other_request.request_id,
    )
    forged_block = other_block.model_copy(
        update={"block_id": "unrecorded-planner-block", "request_id": forged_request.request_id}
    )
    requestless_block = other_block.model_copy(update={"block_id": "other-requestless-block", "request_id": None})
    bindings = tuple(
        binding.model_copy(update={"requests": (forged_request,), "block": forged_block})
        if binding.outcome_id == "OUT-001"
        else binding.model_copy(update={"requests": (other_request,), "block": other_block})
        if binding.outcome_id == "OUT-003"
        else binding.model_copy(update={"block": requestless_block})
        for binding in frontier.bindings
    )
    path = coordinator.runtime_root / "changes/delivery-runtime/frontier.json"
    path.write_bytes(_canonical(frontier.model_copy(update={"bindings": bindings})))
    before = runtime.frontier_bytes()
    answer = DeliveryRequestResolution(response_text="Use user workflow.", provenance="user-confirmed")

    with pytest.raises(DeliveryRuntimeConflictError, match="outside the exact retained Builder handoff"):
        runtime.resolve_request(other_request.request_id, answer)
    with pytest.raises(DeliveryRuntimeConflictError, match="Builder handoff"):
        runtime.resolve_request(forged_request.request_id, answer)
    with pytest.raises(DeliveryRuntimeConflictError, match="requestless unblock cannot mutate"):
        runtime.unblock("OUT-002", requestless_block.block_id, "Operator verified.", ("OUT-002",))
    assert runtime.frontier_bytes() == before


def test_planner_return_exhaustion_block_stays_refused_for_unblock(tmp_path: Path) -> None:
    runtime, _coordinator, _coordination, returned, _tasks = _settle_builder_return_to_planning(
        tmp_path,
        total_attempts=3,
    )
    assert returned.block is not None
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryRuntimeConflictError, match="requestless unblock cannot mutate"):
        runtime.unblock("OUT-001", returned.block.block_id, "Operator verified.", ("TASK-002",))

    assert runtime.frontier_bytes() == before


@pytest.mark.parametrize("settlement_kind", ["retry", "planning-return"])
def test_third_builder_failure_persists_requestless_exhaustion_block(
    tmp_path: Path,
    settlement_kind: str,
) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    ledger, key = _reserve_builder_settlement(
        runtime,
        "attempt-002",
        coordination.last_reviewed_commit,
        total_attempts=3,
    )
    request = (
        RetryDelivery(
            action="retry",
            outcome_id="OUT-001",
            claim_id="claim-002",
            abandoned_commit=branch_head,
            attempt_id="attempt-002",
            failure_code="builder-failed",
        )
        if settlement_kind == "retry"
        else ReturnDelivery(
            action="return",
            outcome_id="OUT-001",
            claim_id="claim-002",
            target=DeliveryStage.PLANNING,
            reason="The remaining task authority needs revision.",
            locators=("TASK-002",),
            preserved_commit=branch_head,
            attempt_id="attempt-002",
        )
    )
    envelope = _builder_settlement_envelope(runtime, coordination, request)

    result = runtime.settle_builder_invocation(envelope)

    assert result.stage == (DeliveryStage.IMPLEMENTATION if settlement_kind == "retry" else DeliveryStage.PLANNING)
    assert result.block is not None
    assert result.block.block_id.startswith(
        "builder-attempt-limit-" if settlement_kind == "retry" else "builder-planning-route-"
    )
    assert "three-attempt limit" in result.block.reason
    assert result.block.request_id is None
    assert not result.block.resolved
    assert result.builder_handoff_context is not None
    assert result.builder_handoff_context.original_task_id == "TASK-002"
    assert "OUT-001" not in runtime.claimable_outcome_ids()
    ledger.reconcile_owner_results()
    episode = ledger.episode(key)
    assert episode is not None
    assert episode.total_attempts == 3
    assert episode.last_status == "failed"
    assert episode.reset_count == 0
    assert coordinator.show("delivery-runtime").builder_handoff is not None


@pytest.mark.parametrize(
    "identity_update",
    [
        {"change_id": "another-change"},
        {"outcome_id": "OUT-002"},
        {"claim_id": "foreign-claim"},
        {"attempt_id": "foreign-attempt"},
        {"task_id": "TASK-001"},
        {"expected_last_reviewed_commit": "f" * 40},
    ],
)
def test_builder_settlement_refuses_foreign_identity_without_mutation(
    tmp_path: Path,
    identity_update: dict[str, str],
) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    request = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        abandoned_commit=branch_head,
        attempt_id="attempt-002",
        failure_code="builder-failed",
    )
    envelope = _builder_settlement_envelope(runtime, coordination, request)
    envelope = envelope.model_copy(update=identity_update)
    before_frontier = runtime.frontier_bytes()
    before_workspace = coordinator.show("delivery-runtime")
    before_git = _git_worktree_snapshot(coordination.worktree_path)

    with pytest.raises((DeliveryRuntimeConflictError, RuntimeError, ValueError)):
        runtime.settle_builder_invocation(envelope)

    assert runtime.frontier_bytes() == before_frontier
    assert coordinator.show("delivery-runtime") == before_workspace
    assert _git_worktree_snapshot(coordination.worktree_path) == before_git


def test_builder_settlement_refuses_unrelated_registered_head_without_mutation(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    tree = _git(coordination.worktree_path, "rev-parse", "HEAD^{tree}")
    unrelated_head = _git(coordination.worktree_path, "commit-tree", tree, "-m", "unrelated root")
    branch_ref = _git(coordination.worktree_path, "symbolic-ref", "HEAD")
    _git(coordination.worktree_path, "update-ref", branch_ref, unrelated_head)
    request = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        abandoned_commit=branch_head,
        attempt_id="attempt-002",
    )
    envelope = _builder_settlement_envelope(runtime, coordination, request)
    before_frontier = runtime.frontier_bytes()
    before_workspace = coordinator.show("delivery-runtime")
    before_git = _git_worktree_snapshot(coordination.worktree_path)

    with pytest.raises((DeliveryRuntimeConflictError, RuntimeError, ValueError)):
        runtime.settle_builder_invocation(envelope)

    assert runtime.frontier_bytes() == before_frontier
    assert coordinator.show("delivery-runtime") == before_workspace
    assert _git_worktree_snapshot(coordination.worktree_path) == before_git


def test_builder_settlement_refuses_attempt_without_retry_reservation(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    request = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        abandoned_commit=branch_head,
        attempt_id="attempt-002",
    )
    envelope = _builder_settlement_envelope(runtime, coordination, request)
    before_frontier = runtime.frontier_bytes()
    before_workspace = coordinator.show("delivery-runtime")
    before_git = _git_worktree_snapshot(coordination.worktree_path)

    with pytest.raises(DeliveryRuntimeConflictError, match="exact reserved retry episode"):
        runtime.settle_builder_invocation(envelope)

    assert runtime.frontier_bytes() == before_frontier
    assert coordinator.show("delivery-runtime") == before_workspace
    assert _git_worktree_snapshot(coordination.worktree_path) == before_git


@pytest.mark.parametrize(
    "invalid_shape",
    ["unknown-request", "unknown-return", "elapsed-timeout", "timeout-inner-request"],
)
def test_builder_settlement_rejects_unknown_request_or_return_and_elapsed_timeout_without_mutation(
    tmp_path: Path,
    invalid_shape: str,
) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    request = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        abandoned_commit=branch_head,
        attempt_id="attempt-002",
    )
    envelope = _builder_settlement_envelope(runtime, coordination, request)
    invalid_values = envelope.model_dump(mode="json")
    if invalid_shape == "unknown-request":
        invalid_values["request"] = AdvanceDelivery(
            action="advance",
            outcome_id="OUT-001",
            claim_id="claim-002",
            output=_output("claim-002", DeliveryStage.IMPLEMENTATION),
        ).model_dump(mode="json")
    elif invalid_shape == "unknown-return":
        invalid_values["request"] = {
            "action": "return",
            "outcome_id": "OUT-001",
            "claim_id": "claim-002",
            "target": "unsupported-stage",
            "reason": "The admitted meaning needs revision.",
            "locators": ["OUT-001"],
            "preserved_commit": branch_head,
            "attempt_id": "attempt-002",
        }
    elif invalid_shape == "elapsed-timeout":
        invalid_values["elapsed_timeout"] = True
    else:
        invalid_values["disposition"] = "completed-timeout"
    before_frontier = runtime.frontier_bytes()
    before_workspace = coordinator.show("delivery-runtime")
    before_git = _git_worktree_snapshot(coordination.worktree_path)
    before_ledger = runtime.retry_ledger().read()

    with pytest.raises(ValidationError):
        DeliveryBuilderInvocationSettlement.model_validate(invalid_values)

    assert runtime.frontier_bytes() == before_frontier
    assert coordinator.show("delivery-runtime") == before_workspace
    assert _git_worktree_snapshot(coordination.worktree_path) == before_git
    assert runtime.retry_ledger().read() == before_ledger


@pytest.mark.parametrize(
    ("foreign_field", "foreign_value"),
    [
        ("change_id", "foreign-change"),
        ("outcome_id", "OUT-099"),
        ("claim_id", "foreign-claim"),
        ("task_id", "TASK-FOREIGN"),
        ("attempt_id", "foreign-attempt"),
    ],
)
def test_builder_design_settlement_rejects_foreign_identity_without_mutation(
    tmp_path: Path,
    foreign_field: str,
    foreign_value: str,
) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    request = ReturnDelivery(
        action="return",
        outcome_id="OUT-001",
        claim_id="claim-002",
        target=DeliveryStage.DESIGN,
        reason="The admitted meaning needs revision.",
        locators=("design.md",),
        preserved_commit=branch_head,
        attempt_id="attempt-002",
    )
    envelope = _builder_settlement_envelope(runtime, coordination, request)
    before_frontier = runtime.frontier_bytes()
    before_workspace = coordinator.show("delivery-runtime")
    before_git = _git_worktree_snapshot(coordination.worktree_path)
    before_ledger = runtime.retry_ledger().read()

    with pytest.raises(DeliveryRuntimeConflictError):
        runtime.settle_builder_invocation(envelope.model_copy(update={foreign_field: foreign_value}))

    assert runtime.frontier_bytes() == before_frontier
    assert coordinator.show("delivery-runtime") == before_workspace
    assert _git_worktree_snapshot(coordination.worktree_path) == before_git
    assert runtime.retry_ledger().read() == before_ledger


def test_builder_return_to_design_settles_as_passive_design_handoff(tmp_path: Path) -> None:
    runtime, coordinator, coordination, _initial, branch_head, first_result, tasks = _active_second_task(tmp_path)
    before_git = _git_worktree_snapshot(coordination.worktree_path)
    ledger, key = _reserve_builder_settlement(
        runtime,
        "attempt-002",
        coordination.last_reviewed_commit,
    )
    request = ReturnDelivery(
        action="return",
        outcome_id="OUT-001",
        claim_id="claim-002",
        target=DeliveryStage.DESIGN,
        reason="The admitted meaning needs revision.",
        locators=("OUT-001",),
        preserved_commit=branch_head,
        attempt_id="attempt-002",
    )
    envelope = _builder_settlement_envelope(runtime, coordination, request)

    result = runtime.settle_builder_invocation(envelope)

    assert _git_worktree_snapshot(coordination.worktree_path) == before_git
    assert result.stage == DeliveryStage.DESIGN
    assert result.active_claim is None
    assert result.tasks == tasks
    assert result.results == (first_result,)
    assert result.return_context is not None
    assert result.return_context.target == DeliveryStage.DESIGN
    assert result.return_context.reason == request.reason
    assert result.return_context.locators == request.locators
    assert result.return_context.preserved_commit == branch_head
    assert result.return_context.completed_boundary == coordination.last_reviewed_commit
    handoff = result.builder_handoff_context
    assert handoff is not None
    assert handoff.route == "same-outcome-design"
    assert handoff.original_task_id == "TASK-002"
    assert handoff.original_task_commitment_ids == tasks[1].commitment_ids
    assert handoff.original_task_maintained_surfaces == tasks[1].maintained_surfaces
    workspace = coordinator.show("delivery-runtime")
    assert workspace.writer is not None
    assert workspace.writer.kind == "handoff"
    assert workspace.builder_handoff is not None
    assert workspace.builder_handoff.original_task_id == "TASK-002"
    assert workspace.builder_handoff.settlement_id == handoff.settlement_id
    ledger.reconcile_owner_results()
    episode = ledger.episode(key)
    assert episode is not None
    assert episode.total_attempts == 1
    assert episode.reset_count == 0
    owner_result_path = (
        coordinator.runtime_root / "changes/delivery-runtime/retry-ledger/owner-results/attempt-002.json"
    )
    owner_result = RetryOwnerResult.model_validate_json(owner_result_path.read_bytes())
    assert owner_result.accepted is False
    assert owner_result.paused is False
    assert owner_result.failure_code == "worker-returned"


@pytest.mark.parametrize("crash_stage", ["after-first-publication", "before-handoff-publication"])
def test_interrupted_builder_settlement_recovers_all_atomic_participants(tmp_path: Path, crash_stage: str) -> None:
    runtime, coordinator, coordination, _initial, branch_head, _first_result, _tasks = _active_second_task(tmp_path)
    before_git = _git_worktree_snapshot(coordination.worktree_path)
    _reserve_builder_settlement(runtime, "attempt-002", coordination.last_reviewed_commit)
    request = RetryDelivery(
        action="retry",
        outcome_id="OUT-001",
        claim_id="claim-002",
        abandoned_commit=branch_head,
        attempt_id="attempt-002",
        failure_code="builder-failed",
    )
    envelope = _builder_settlement_envelope(runtime, coordination, request)
    original_commit = RuntimeTransaction.commit
    import owlbear_delivery.runtime_transaction as transaction_module  # noqa: PLC0415

    original_replace = transaction_module._publish_replacement  # noqa: SLF001

    def fail_before_handoff(destination, participant):
        if (
            crash_stage == "before-handoff-publication"
            and destination.parent.name == "changes"
            and destination.parent.parent.name == "coordination"
        ):
            message = "simulated Builder settlement crash"
            raise RuntimeError(message)
        return original_replace(destination, participant)

    def fail_after_frontier(transaction: RuntimeTransaction) -> None:
        def failure(point: str) -> None:
            if crash_stage == "after-first-publication" and point == "after-first-publication":
                message = "simulated Builder settlement crash"
                raise RuntimeError(message)

        original_commit(transaction, failure=failure)

    with (
        patch.object(RuntimeTransaction, "commit", fail_after_frontier),
        patch.object(transaction_module, "_publish_replacement", fail_before_handoff),
        pytest.raises(RuntimeError, match="simulated Builder settlement crash"),
    ):
        runtime.settle_builder_invocation(envelope)

    custody_path = coordinator.runtime_root / "coordination/changes/delivery-runtime.json"
    assert json.loads(custody_path.read_bytes())["writer"]["kind"] == "build"
    result = runtime.settle_builder_invocation(envelope)

    assert json.loads(custody_path.read_bytes())["writer"]["kind"] == "handoff"
    assert not tuple((coordinator.runtime_root / "transactions").glob("*.yaml"))
    assert result.active_claim is None
    assert result.builder_handoff_context is not None
    assert coordinator.show("delivery-runtime").builder_handoff is not None
    assert (coordinator.runtime_root / "changes/delivery-runtime/retry-ledger/owner-results/attempt-002.json").is_file()
    assert _git_worktree_snapshot(coordination.worktree_path) == before_git
    assert not tuple((coordinator.runtime_root / "transactions").glob("*.yaml"))


@pytest.mark.parametrize(
    ("stage", "transition", "expected_stage"),
    [
        (DeliveryStage.PLANNING, "block", DeliveryStage.PLANNING),
    ],
)
def test_worker_transition_routes_canonical_stage_and_rejects_stale_or_review_input(
    tmp_path: Path,
    stage: DeliveryStage,
    transition: str,
    expected_stage: DeliveryStage,
) -> None:
    runtime = _runtime(tmp_path, stages=(stage, DeliveryStage.PLANNING, DeliveryStage.PLANNING))
    output = _claim_with_output(runtime, "OUT-001", "claim-001")

    request = {
        "advance": AdvanceDelivery(action="advance", outcome_id="OUT-001", claim_id="claim-001", output=output),
        "retry": RetryDelivery(action="retry", outcome_id="OUT-001", claim_id="claim-001"),
        "return": ReturnDelivery(
            action="return",
            outcome_id="OUT-001",
            claim_id="claim-001",
            target=DeliveryStage.PLANNING,
            reason="The task authority needs revision.",
            locators=("TASK-001",),
        ),
        "block": BlockDelivery(
            action="block",
            outcome_id="OUT-001",
            claim_id="claim-001",
            block_id="block-001",
            reason="External evidence is unavailable.",
            unblock_condition="The evidence is supplied.",
            expected_evidence=("External result",),
            locators=("RESULT-001",),
        ),
    }[transition]
    result = runtime.transition(request)

    assert result.stage == expected_stage
    before = runtime.frontier_bytes()
    assert runtime.transition(request) == result
    assert runtime.frontier_bytes() == before
    with pytest.raises(ValidationError):
        DELIVERY_TRANSITION_ADAPTER.validate_python(
            {
                "action": "advance",
                "outcome_id": "OUT-001",
                "claim_id": "claim-002",
                "output": _output("claim-002", expected_stage).model_dump(mode="json"),
                "reviewer_id": "reviewer-001",
                "disposition": "acceptable",
            }
        )
    assert runtime.frontier_bytes() == before


def test_portable_transition_retains_publication_intent_across_runtime_restart(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _activate(runtime, "OUT-001", "claim-001")
    runtime.transition(
        BlockDelivery(
            action="block",
            outcome_id="OUT-001",
            claim_id="claim-001",
            block_id="block-publication",
            reason="Remote publication is unavailable.",
            unblock_condition="Remote publication succeeds.",
            expected_evidence=("Published state",),
            locators=("test_delivery_runtime.py",),
        )
    )

    pending = runtime.pending_state_publication()
    restarted = DeliveryRuntime(tmp_path, runtime.contract)

    assert pending is not None
    assert pending.status == "pending"
    assert restarted.pending_state_publication() == pending
    restarted.acknowledge_pending_publication(pending.frontier_digest)
    assert restarted.pending_state_publication() is None


def test_request_resolution_and_requestless_unblock_preserve_stage_and_answer(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="user-confirmed provenance"):
        DeliveryRequestResolution(response_text="Unattributed action evidence.")

    runtime = _runtime(tmp_path)
    _activate(runtime, "OUT-001", "claim-001")
    request = DeliveryRequest(
        request_id="request-001",
        kind=DeliveryRequestKind.DECISION,
        outcome_id="OUT-001",
        summary="Choose the bounded source.",
        options=(
            DeliveryRequestOption(option_id="local", label="Use local source"),
            DeliveryRequestOption(option_id="remote", label="Use remote source"),
        ),
    )
    runtime.transition(
        BlockDelivery(
            action="block",
            outcome_id="OUT-001",
            claim_id="claim-001",
            block_id="block-001",
            reason="A bounded decision is required.",
            unblock_condition="The source is selected.",
            expected_evidence=("Selected source",),
            locators=("COM-001",),
            request=request,
        )
    )

    with pytest.raises(DeliveryRuntimeReferenceError, match="selected option"):
        runtime.resolve_request(
            "request-001",
            DeliveryRequestResolution(response_text="Use the checked-in copy.", provenance="user-confirmed"),
        )

    resolved = runtime.resolve_request(
        "request-001",
        DeliveryRequestResolution(
            selected_option_id="local",
            response_text="Use the checked-in copy.",
            provenance="user-confirmed",
        ),
    )

    assert resolved.resolution is not None
    assert resolved.resolution.selected_option_id == "local"
    assert resolved.resolution.response_text == "Use the checked-in copy."
    assert runtime.show_binding("OUT-001").stage == DeliveryStage.PLANNING
    assert runtime.claimable_outcome_ids() == ("OUT-001", "OUT-003")

    _activate(runtime, "OUT-003", "claim-003")
    runtime.transition(
        BlockDelivery(
            action="block",
            outcome_id="OUT-003",
            claim_id="claim-003",
            block_id="block-003",
            reason="Manual verification is pending.",
            unblock_condition="Verification is recorded.",
            expected_evidence=("Verification locator",),
            locators=("RESULT-003",),
        )
    )
    runtime.unblock("OUT-003", "block-003", "Verification completed.", ("RESULT-003",))
    assert runtime.show_binding("OUT-003").stage == DeliveryStage.PLANNING
    assert "OUT-003" in runtime.claimable_outcome_ids()


def test_implementation_block_requires_bounded_user_request(tmp_path: Path) -> None:
    runtime, coordinator, _coordination, _initial, attempt_commit, _first_result, _tasks = _active_second_task(tmp_path)
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryRuntimeConflictError, match="bounded user request"):
        runtime.transition(
            BlockDelivery(
                action="block",
                outcome_id="OUT-001",
                claim_id="claim-002",
                block_id="build-context-tool-unavailable",
                reason="Required live Build context is unavailable.",
                unblock_condition="The Build context tool is available.",
                expected_evidence=("Successful Build context lookup",),
                locators=("TASK-002",),
                resume_commit=attempt_commit,
            )
        )

    assert runtime.frontier_bytes() == before
    assert coordinator.show("delivery-runtime").writer is not None


def test_implementation_block_cannot_bypass_exclusion_with_stale_resume_commit(tmp_path: Path) -> None:
    runtime, coordinator, coordination, initial, attempt_commit, _, _ = _active_second_task(tmp_path)
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        runtime.transition(
            BlockDelivery(
                action="block",
                outcome_id="OUT-001",
                claim_id="claim-002",
                block_id="block-stale-resume",
                reason="External evidence is unavailable.",
                unblock_condition="The evidence is supplied.",
                expected_evidence=("External result",),
                locators=("TASK-002",),
                request=DeliveryRequest(
                    request_id="request-stale-resume",
                    kind=DeliveryRequestKind.ACTION,
                    outcome_id="OUT-001",
                    summary="Supply the external result.",
                ),
                resume_commit=initial,
            )
        )

    assert runtime.frontier_bytes() == before
    assert coordinator.show("delivery-runtime").writer is not None
    assert runtime.show_binding("OUT-001").active_claim_id == "claim-002"
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == attempt_commit


def test_administrative_backward_move_invalidates_completed_dependents_only(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    path = tmp_path / "changes/delivery-runtime/frontier.json"
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)
    pending = DeliveryPendingCheckpoint(
        head="3" * 40,
        triggers=(
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
            ),
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-001",
            ),
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-003",
            ),
        ),
    )
    path.write_bytes(_canonical(frontier.model_copy(update={"pending_checkpoint": pending})))
    runtime = DeliveryRuntime(tmp_path, _contract())
    before = runtime.frontier_bytes()
    preview = runtime.preview_administrative_move("OUT-001", DeliveryStage.PLANNING)

    assert preview.invalidated_outcome_ids == ("OUT-001", "OUT-002")
    assert preview.snapshot_version == hashlib.sha256(before).hexdigest()
    assert runtime.frontier_bytes() == before

    result = runtime.administrative_move(
        AdministrativeDeliveryMove(
            move_id="move-001",
            outcome_id="OUT-001",
            target=DeliveryStage.PLANNING,
            reason="The foundation result was invalidated by operator evidence.",
            expected_version=preview.snapshot_version,
        )
    )

    assert result.invalidated_outcome_ids == ("OUT-001", "OUT-002")
    assert runtime.show_binding("OUT-001").stage == DeliveryStage.PLANNING
    assert runtime.show_binding("OUT-002").stage == DeliveryStage.PLANNING
    assert runtime.show_binding("OUT-003").stage == DeliveryStage.COMPLETED
    assert runtime.show_binding("OUT-003").result_ids == ("RESULT-003",)
    retained = runtime.checkpoint_publication_state().pending_checkpoint
    assert retained is not None
    assert retained.head is None
    assert retained.triggers == (pending.triggers[0], pending.triggers[2])
    assert runtime.change_stage() == DeliveryChangeStage.BUILDING


def test_administrative_move_retires_integration_attention(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    attention = DeliveryIntegrationAttention(
        attention_id="a" * 64,
        code=DeliveryIntegrationAttentionCode.REPAIR_AUTHORITY,
        change_id="delivery-runtime",
        change_head="1" * 40,
        target_head="2" * 40,
        integration_target="main",
        diagnostics=("The repair exceeded admitted authority.",),
        retry_condition="Move the change to an earlier stage.",
    )
    _persist_frontier(tmp_path, runtime, integration_attention=attention)

    runtime.administrative_move(
        AdministrativeDeliveryMove(
            move_id="move-001",
            outcome_id="OUT-001",
            target=DeliveryStage.PLANNING,
            reason="Revise the admitted authority.",
            expected_version=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
        )
    )

    assert runtime.integration_attention() is None
    assert runtime.change_stage() == DeliveryChangeStage.BUILDING


def test_administrative_move_rejects_active_integration_repair(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    attention = DeliveryIntegrationAttention(
        attention_id="a" * 64,
        code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
        change_id="delivery-runtime",
        change_head="1" * 40,
        target_head="2" * 40,
        integration_target="main",
        diagnostics=("merge conflict",),
        retry_condition="Admit an independently reviewed repair.",
    )
    _persist_frontier(tmp_path, runtime, integration_attention=attention)
    _persist_frontier(
        tmp_path,
        runtime,
        integration_attention=attention,
        integration_repair_claim=DeliveryActiveClaim(
            attempt_id="repair-attempt",
            claim_id="repair-claim",
            owner_id="repair-owner",
            process_id="repair-process",
            started_at="2026-08-04T00:00:00Z",
            worker_role=DeliveryWorkerRole.INTEGRATION_REPAIRER,
        ),
    )
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryRuntimeConflictError, match="active Integration repair claim"):
        runtime.administrative_move(
            AdministrativeDeliveryMove(
                move_id="move-001",
                outcome_id="OUT-001",
                target=DeliveryStage.PLANNING,
                reason="Revise the admitted authority.",
                expected_version=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            )
        )

    assert runtime.frontier_bytes() == before


def test_administrative_move_rejects_active_dependent_claim(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.IMPLEMENTATION, DeliveryStage.COMPLETED),
    )
    _activate(runtime, "OUT-002", "claim-002", task_id="TASK-002")
    active_dependent = runtime.show_binding("OUT-002")

    with pytest.raises(DeliveryRuntimeConflictError, match="active mutation claim"):
        runtime.administrative_move(
            AdministrativeDeliveryMove(
                move_id="move-001",
                outcome_id="OUT-001",
                target=DeliveryStage.PLANNING,
                reason="The foundation result was invalidated by operator evidence.",
                expected_version=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            )
        )

    assert runtime.show_binding("OUT-002") == active_dependent


def test_administrative_move_rejects_a_stale_preview(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    preview = runtime.preview_administrative_move("OUT-001", DeliveryStage.PLANNING)
    attention = DeliveryIntegrationAttention(
        attention_id="a" * 64,
        code=DeliveryIntegrationAttentionCode.REPAIR_AUTHORITY,
        change_id="delivery-runtime",
        change_head="1" * 40,
        target_head="2" * 40,
        integration_target="main",
        diagnostics=("Authority changed.",),
        retry_condition="Move backward.",
    )
    _persist_frontier(tmp_path, runtime, integration_attention=attention)

    with pytest.raises(DeliveryRuntimeConflictError, match="preview is stale"):
        runtime.administrative_move(
            AdministrativeDeliveryMove(
                move_id="move-stale",
                outcome_id="OUT-001",
                target=DeliveryStage.PLANNING,
                reason="Use stale evidence.",
                expected_version=preview.snapshot_version,
            )
        )


_FRESH_EXPORT_COMPLETENESS_SCRIPT = """
import inspect
import json

from pydantic import BaseModel
from pydantic_core import to_jsonable_python

import owlbear_delivery
from owlbear_delivery import OutcomeAuthorityBinding

incomplete = sorted(
    name
    for name in owlbear_delivery.__all__
    if inspect.isclass(model := getattr(owlbear_delivery, name))
    and issubclass(model, BaseModel)
    and not model.__pydantic_complete__
)
binding = OutcomeAuthorityBinding.model_construct(outcome_id="OUT-001", plan_scope_id="SCOPE-001")
print(json.dumps({"incomplete": incomplete, "binding": to_jsonable_python(binding)}))
"""


def test_fresh_process_exports_only_complete_models() -> None:
    result = subprocess.run(  # noqa: S603
        (sys.executable, "-c", _FRESH_EXPORT_COMPLETENESS_SCRIPT),
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout.strip().splitlines()[-1])
    assert observed["incomplete"] == []
    assert observed["binding"]["outcome_id"] == "OUT-001"
