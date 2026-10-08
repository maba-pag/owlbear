# ruff: noqa: SLF001

from __future__ import annotations

import hashlib
import itertools
import json
import os
import shutil
import stat
import subprocess
import sys
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from threading import Barrier, Event, Lock
from typing import Literal
from unittest.mock import Mock, patch, sentinel

import pytest
from pydantic import ValidationError
from serve.delivery.tests.evidence_support import finalization_proof
from serve.delivery.tests.test_delivery_state import _commit_corrupt_snapshot, _Crash
from serve.delivery.tests.test_draft_pull_request import _Provider

from owlbear_delivery import (
    ActivateDeliveryClaim,
    AdministrativeDeliveryMove,
    AdvanceDelivery,
    BlockDelivery,
    CapacityLedger,
    ChangeBranchPublicationReceipt,
    ChangeBranchPublisher,
    ChangeBranchSupersessionReceipt,
    ChangeExternalHeadAdoptionReceipt,
    ChangeFinalizationAttempt,
    ChangeTargetSyncAbortReceipt,
    ChangeTargetSyncConflictError,
    ChangeTargetSyncConflictState,
    ChangeTargetSyncReceipt,
    ChangeWorkspaceManager,
    ChangeWorktreeAttentionCode,
    ChangeWorktreeAttentionError,
    ChangeWriter,
    CompletedHistoryCatalog,
    CompletionDisplayMetadata,
    CompletionEvidence,
    CompletionPullRequestIdentity,
    CompletionReceipt,
    CompletionReceiptStore,
    CoordinationConflictError,
    CreateOrReconcileDraftPullRequest,
    DeliveryAcceptanceAttentionReason,
    DeliveryAcceptanceReconciliationOutcome,
    DeliveryAcceptanceReconciliationStatus,
    DeliveryAcceptanceRef,
    DeliveryAcceptanceWaitingError,
    DeliveryAcquisitionFailure,
    DeliveryActionSelectionConflictError,
    DeliveryActiveClaim,
    DeliveryAdmissionConflictError,
    DeliveryAdmissionReceipt,
    DeliveryAdmissionRequest,
    DeliveryAnswer,
    DeliveryAnswerKind,
    DeliveryApplicationLoadError,
    DeliveryAuthorityRegistry,
    DeliveryChangeDispositionBusyError,
    DeliveryChangeDispositionResolution,
    DeliveryChangeIntent,
    DeliveryChangeIntentKind,
    DeliveryChangePublicationIdentity,
    DeliveryChangeStage,
    DeliveryChangeWorktreeCleanup,
    DeliveryChangeWorktreeRecovery,
    DeliveryCheckpointPublicationState,
    DeliveryCheckpointTrigger,
    DeliveryCheckpointTriggerKind,
    DeliveryCommandResult,
    DeliveryCommitment,
    DeliveryCommitmentClass,
    DeliveryContract,
    DeliveryDesignPut,
    DeliveryEngineActionResult,
    DeliveryFinalizationInvalidationReceipt,
    DeliveryFinalizationReceipt,
    DeliveryFrontier,
    DeliveryHealthDiagnostic,
    DeliveryHealthReason,
    DeliveryHealthResolution,
    DeliveryHealthStatus,
    DeliveryHostConfig,
    DeliveryIntegrationAttention,
    DeliveryIntegrationAttentionCode,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryOutcome,
    DeliveryPendingCheckpoint,
    DeliveryPendingStatePublication,
    DeliveryPlanScope,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryRequestResolution,
    DeliveryResultSubmission,
    DeliveryRetainedWorktreeCleanupBlockReason,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryRolePolicy,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryStage,
    DeliveryStartupConfig,
    DeliveryStatePublicationError,
    DeliveryStatePublisher,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryWorkerRole,
    DesignPackageConflictError,
    DesignPackageManifest,
    DesignPackageStore,
    DraftPullRequestPublicationHistory,
    DraftPullRequestPublicationReceipt,
    DraftPullRequestPublisher,
    DraftPullRequestSupersessionReceipt,
    ExecuteDeliveryChangeAction,
    FinalizationReport,
    FinalizeDeliveryChange,
    FinalizerSettlement,
    FinalizerSettlementReceipt,
    GeneratedPullRequestSummaryReceipt,
    MarkChangePullRequestReady,
    ObserveChangePublicationChecks,
    ObserveChangePublicationPullRequest,
    OutcomeAuthorityBinding,
    PortfolioApplication,
    PortfolioApplicationConfig,
    PortfolioApplicationDependencies,
    PortfolioApplicationError,
    PortfolioApplicationHooks,
    PortfolioCoordinator,
    PrepareCompletedOutcomeRepair,
    PublicationBaselineUnavailableError,
    PublicationCheck,
    PublicationCheckBlockingState,
    PublicationCheckKind,
    PublicationCheckSnapshot,
    PublicationLease,
    PublicationPullRequestObservationReceipt,
    PublishChangeBranch,
    PublishDeliveryPlan,
    PublishDeliveryResult,
    PullRequestReadyReceipt,
    ReadChangePublicationCheckObservations,
    ReadChangePublicationHistory,
    RetryDelivery,
    ReturnDelivery,
    WorkspaceRecoverySnapshot,
    acceptance_criteria,
    classify_publication_check,
    load_delivery_application,
    remote_git,
)
from owlbear_delivery.change_workspace import (
    ChangeContinuationAction,
    FinalizerAcquisition,
    PreservationFenceError,
    PreservationPathProvenance,
    PreservationProvenanceEvidence,
)
from owlbear_delivery.delivery_admission import DeliveryRevisionError
from owlbear_delivery.delivery_contract_discovery import (
    DeliveryDiscoveryErrorCode,
    contract_fingerprint,
    discover_persisted_changes,
)
from owlbear_delivery.delivery_runtime import (
    DeliveryBuilderInvocationSettlement,
    DeliveryLegacyObservationReceipt,
    DeliveryPlanningRetrySettlement,
    DeliveryRuntimeReferenceError,
    parse_delivery_frontier,
)
from owlbear_delivery.delivery_state import DeliveryStateSnapshotDiagnostic, DeliveryStateSnapshotInventory
from owlbear_delivery.finalization_reports import (
    FinalizationFailureCode,
    FinalizationReportError,
    FinalizationReportStore,
    MaintainedProofProcedure,
    ProofAttemptBasis,
    ProofAttemptObservation,
    ProofAttemptStore,
    ReportFinalizationFailure,
)
from owlbear_delivery.portfolio_application import (
    DeliveryActionBusyError,
    DeliveryActionSelection,
    DeliveryCapacityWaitingError,
    DeliveryContinuationRequest,
    DeliveryContinuationResult,
    DeliveryRuntimeReconciliationError,
    _required_check_diagnostics,
)
from owlbear_delivery.publication_provider import (
    PublicationProviderError,
    PublicationProviderFailureCode,
    PublicationPullRequest,
    PublicationRepository,
)
from owlbear_delivery.recovery import (
    DeliveryWorkerExclusionRequiredError,
    RetryEpisodeKey,
    RetryFailureClass,
    RetryLedger,
    RetryLedgerConflictError,
    digest,
)
from owlbear_delivery.runtime_models import _receipt_digest
from owlbear_delivery.runtime_transaction import ReplacementTransactionParticipant, RuntimeTransaction
from owlbear_delivery.state_formats import classify_kind, format_marker_bytes
from owlbear_delivery.storage_io import locked_roots
from owlbear_delivery_github import GitHubCliPublicationProvider

_USER_CHECKOUT_STATES = (
    "clean",
    "modified",
    "staged",
    "untracked",
    "conflicted",
    "detached",
    "mid-merge",
    "mid-rebase",
)


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603
        ("git", "-C", str(repository), *arguments),  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_ref_exists(repository: Path, reference: str) -> bool:
    return (
        subprocess.run(  # noqa: S603
            ("git", "-C", str(repository), "rev-parse", "--verify", reference),  # noqa: S607
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def _commit_reviewed_head(application, coordination, filename: str, content: str, message: str) -> str:
    (coordination.worktree_path / filename).write_text(content, encoding="utf-8")
    _git(coordination.worktree_path, "add", filename)
    _git(coordination.worktree_path, "commit", "-m", message)
    head = _git(coordination.worktree_path, "rev-parse", "HEAD")
    application._workspace_manager.record_reviewed("change-a", head)
    return head


def _commit_local_descendant(coordination, filename: str = "local-repair.txt") -> str:
    (coordination.worktree_path / filename).write_text("local repair\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", filename)
    _git(coordination.worktree_path, "commit", "-m", "local repair")
    return _git(coordination.worktree_path, "rev-parse", "HEAD")


def _canonical(model) -> bytes:
    return (json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()


def _recover_claim(
    application: PortfolioApplication,
    change_id: str,
    outcome_id: str,
    attempt_id: str,
    claim_id: str,
) -> object:
    return application.recover_claim(
        change_id,
        outcome_id,
        attempt_id,
        claim_id,
        confirmed_lost=True,
    )


def _assert_recovery_excluded(application: PortfolioApplication, package) -> None:
    runtime = application._runtime(package.change_id)
    frontier = runtime.frontier_bytes()
    coordination = application._coordinator.show(package.change_id)
    files = _file_bytes(package.worktree_path)
    index = Path(_git(package.worktree_path, "rev-parse", "--path-format=absolute", "--git-path", "index"))
    index_bytes = index.read_bytes()
    refs = _git(package.worktree_path, "show-ref")
    for confirmed in (False, True):
        with pytest.raises(DeliveryWorkerExclusionRequiredError):
            application.recover_claim(
                package.change_id,
                package.outcome_id,
                package.claim.attempt_id,
                package.claim.claim_id,
                confirmed_lost=confirmed,
            )
    assert runtime.frontier_bytes() == frontier
    assert application._coordinator.show(package.change_id) == coordination
    assert _file_bytes(package.worktree_path) == files
    assert index.read_bytes() == index_bytes
    assert _git(package.worktree_path, "show-ref") == refs


def _approved_package_id(application: PortfolioApplication, change_id: str) -> str:
    package = application._package_store.read_verified(change_id)
    authored_manifest = DesignPackageManifest.from_content(
        change_id,
        package.intent_bytes,
        package.design_bytes,
    )
    return hashlib.sha256(authored_manifest.canonical_bytes()).hexdigest()


def _receipt_id(payload: dict[str, object]) -> str:
    content = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode()).hexdigest()


def _branch_receipt(head: str, expected: str | None = None) -> ChangeBranchPublicationReceipt:
    return ChangeBranchPublicationReceipt(
        receipt_id="1" * 64,
        operation_id="branch-operation",
        change_id="change-a",
        remote="origin",
        branch="owlbear/change/change-a",
        target_branch="main",
        expected_remote_head=expected,
        published_head=head,
    )


def _requested_branch_receipt(request: PublishChangeBranch) -> ChangeBranchPublicationReceipt:
    assert request.expected_published_head is not None
    return _branch_receipt(request.expected_published_head, request.expected_remote_head)


def _draft_receipt(
    head: str,
    *,
    number: int = 7,
    operation_id: str = "pull-request-operation",
    head_branch: str = "owlbear/change/change-a",
) -> DraftPullRequestPublicationReceipt:
    payload = {
        "schema_version": 1,
        "operation_id": operation_id,
        "change_id": "change-a",
        "repository": "example/project",
        "number": number,
        "node_id": f"PR_{number}",
        "head_branch": head_branch,
        "head_sha": head,
        "base_branch": "main",
        "provider_evidence_digest": "2" * 64,
    }
    return DraftPullRequestPublicationReceipt(receipt_id=_receipt_id(payload), **payload)


def _draft_history(
    publications: tuple[DraftPullRequestPublicationReceipt, ...],
    predecessor_receipt_ids: tuple[str | None, ...],
) -> DraftPullRequestPublicationHistory:
    payload = {
        "schema_version": 1,
        "change_id": "change-a",
        "publications": tuple(publication.model_dump(mode="json") for publication in publications),
        "predecessor_receipt_ids": predecessor_receipt_ids,
        "current_receipt_id": publications[-1].receipt_id,
    }
    return DraftPullRequestPublicationHistory(
        history_id=_receipt_id(payload),
        publications=publications,
        predecessor_receipt_ids=predecessor_receipt_ids,
        current_receipt_id=publications[-1].receipt_id,
        change_id="change-a",
    )


def _summary_receipt(head: str, *, number: int = 7) -> GeneratedPullRequestSummaryReceipt:
    payload = {
        "schema_version": 1,
        "operation_id": "summary-operation",
        "change_id": "change-a",
        "repository": "example/project",
        "number": number,
        "head_sha": head,
        "body_digest": "3" * 64,
        "provider_evidence_digest": "4" * 64,
    }
    return GeneratedPullRequestSummaryReceipt(receipt_id=_receipt_id(payload), **payload)


def _publication_observation(
    change_id: str,
    head: str,
    *,
    mergeable: bool | None,
    merge_state_status: str | None,
) -> PublicationPullRequestObservationReceipt:
    snapshot = PublicationPullRequest(
        repository="example/project",
        number=7,
        node_id="PR_7",
        head_branch=f"owlbear/change/{change_id}",
        head_sha=head,
        base_branch="main",
        title=f"Delivery {change_id}",
        body="Generated summary",
        draft=True,
        state="open",
        merged=False,
        mergeable=mergeable,
        merge_state_status=merge_state_status,
    )
    observed_at = datetime(2026, 8, 11, 16, tzinfo=UTC)
    evidence_digest = hashlib.sha256(
        json.dumps(
            {
                **snapshot.model_dump(mode="json"),
                "mergeable": mergeable,
                "merge_state_status": merge_state_status,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    payload = {
        "schema_version": 1,
        "change_id": change_id,
        "observed_at": observed_at,
        "snapshot": snapshot,
        "provider_evidence_digest": evidence_digest,
        "mergeable": mergeable,
        "merge_state_status": merge_state_status,
    }
    candidate = PublicationPullRequestObservationReceipt.model_construct(observation_id="0" * 64, **payload)
    observation_id = hashlib.sha256(
        json.dumps(
            candidate._identity_payload(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return PublicationPullRequestObservationReceipt(observation_id=observation_id, **payload)


class _ObservedLock:
    def __init__(self) -> None:
        self._lock = Lock()
        self.observe_attempts = Event()
        self.attempted = Event()
        self.acquired = Event()

    def __enter__(self) -> None:
        if self.observe_attempts.is_set():
            self.attempted.set()
        self._lock.acquire()
        if self.observe_attempts.is_set():
            self.acquired.set()

    def __exit__(self, *_args: object) -> None:
        self._lock.release()


def _contract(
    change_id: str,
    intent: bytes,
    design: bytes,
    *,
    include_downstream: bool = False,
    include_independent: bool = False,
) -> DeliveryContract:
    outcomes = [
        DeliveryOutcome(
            outcome_id="OUT-001",
            title="Acquire work",
            promise="Return one bounded launch package.",
            acceptance=("AC-001: The launch is observable.",),
            commitment_ids=("COM-001",),
            dependency_ids=(),
        )
    ]
    plan_scopes = [DeliveryPlanScope(scope_id="SCOPE-001", outcome_id="OUT-001")]
    if include_downstream or include_independent:
        outcomes.append(
            DeliveryOutcome(
                outcome_id="OUT-002",
                title="Report work",
                promise="Retain one downstream report.",
                acceptance=("AC-002: The report is retained.",),
                commitment_ids=("COM-001",),
                dependency_ids=("OUT-001",) if include_downstream else (),
            )
        )
        plan_scopes.append(DeliveryPlanScope(scope_id="SCOPE-002", outcome_id="OUT-002"))
    return DeliveryContract(
        change_id=change_id,
        title=f"Delivery {change_id}",
        commitments=(
            DeliveryCommitment(
                commitment_id="COM-001",
                commitment_class=DeliveryCommitmentClass.AGREED_PATH,
                provenance="accepted design",
                statement="Keep acquisition deterministic.",
            ),
        ),
        outcomes=tuple(outcomes),
        plan_scopes=tuple(plan_scopes),
        source_bindings=(
            {"source_name": "intent.md", "sha256": hashlib.sha256(intent).hexdigest()},
            {"source_name": "design.md", "sha256": hashlib.sha256(design).hexdigest()},
        ),
    )


def _admission_receipt(
    contract: DeliveryContract,
    frontier: DeliveryFrontier,
    checkpoint_commit: str,
) -> DeliveryAdmissionReceipt:
    source_bindings = [item.model_dump(mode="json") for item in contract.source_bindings]
    payload = {
        "schema_version": 1,
        "change_id": contract.change_id,
        "contract_digest": contract_fingerprint(contract),
        "source_bindings_digest": hashlib.sha256(
            json.dumps(source_bindings, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "integration_target": "main",
        "checkpoint_commit": checkpoint_commit,
        "frontier_ids": tuple(binding.plan_scope_id for binding in frontier.bindings),
    }
    return DeliveryAdmissionReceipt(receipt_id=_receipt_id(payload), **payload)


def _task() -> DeliveryTaskDefinition:
    return DeliveryTaskDefinition(
        task_id="TASK-001",
        outcome_id="OUT-001",
        plan_scope_id="SCOPE-001",
        title="Implement acquisition",
        result="One transport-free acquisition service.",
        commitment_ids=("COM-001",),
        dependency_ids=(),
        required_outputs=("Bounded launch package",),
        maintained_surfaces=("serve/delivery/src/owlbear_delivery/portfolio_application.py",),
        constraints=("Separate execution and writer capacity.",),
        exclusions=("Do not expose portfolio inventory.",),
        acceptance_observations=("The public acquisition result names the active claim.",),
        proof_boundaries=("PortfolioApplication.acquire_frontier_work",),
    )


def _downstream_task() -> DeliveryTaskDefinition:
    return DeliveryTaskDefinition(
        task_id="TASK-002",
        outcome_id="OUT-002",
        plan_scope_id="SCOPE-002",
        title="Report acquisition",
        result="One retained downstream report.",
        commitment_ids=("COM-001",),
        dependency_ids=("TASK-001",),
        required_outputs=("Retained downstream report",),
        maintained_surfaces=("serve/delivery/src/owlbear_delivery/delivery_runtime.py",),
        constraints=("Retain prior result evidence.",),
        exclusions=("Do not rewrite prior results.",),
        acceptance_observations=("The downstream report remains historical evidence.",),
        proof_boundaries=("PortfolioApplication completed-outcome repair",),
    )


def _task_result(  # noqa: PLR0913 - revision fixtures name the criteria a result covers.
    result_id: str,
    change_id: str,
    authority_digest: str,
    task: DeliveryTaskDefinition,
    completed_commit: str,
    *,
    covers: tuple[DeliveryAcceptanceRef, ...] = (),
) -> DeliveryTaskResult:
    observed_at = datetime(2026, 8, 11, 12, tzinfo=UTC)
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=change_id,
            task_or_finalization_id=task.task_id,
            exact_commit=completed_commit,
            observation_kind="pytest",
            procedure="PortfolioApplication fixture validation",
            result=DeliveryCommandResult(exit_status=0),
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
            covers=covers,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            review_mode="task",
            exact_commit=completed_commit,
            author_id="Portfolio test author",
            reviewer_id="Portfolio test reviewer",
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


_FINALIZATION_RUNTIMES: dict[str, DeliveryRuntime] = {}
"""Latest fixture runtime per Change; its state supplies the engine-derived finalization basis."""


def _legacy_task_result(result: DeliveryTaskResult) -> DeliveryTaskResult:
    """Return the same result as a D03 record: schema-1 observation and review receipts."""
    observed_at = result.review.reviewed_at
    observation_values = {
        "schema_version": 1,
        "change_id": result.change_id,
        "task_or_finalization_id": result.task_id,
        "step_id": None,
        "exact_commit": result.completed_commit,
        "observation_kind": "pytest",
        "command_or_procedure": "PortfolioApplication fixture validation",
        "exit_status_or_artifact_locator": "exit:0",
        "observer_or_runner_identity": "pytest",
        "observed_at": observed_at,
    }
    observation = DeliveryLegacyObservationReceipt.model_construct(observation_id="0" * 64, **observation_values)
    review_values = {
        "schema_version": 1,
        "exact_commit": result.completed_commit,
        "author_id": result.review.author_id,
        "reviewer_id": result.review.reviewer_id,
        "disposition": "pass",
        "evidence": result.review.evidence,
        "reviewed_at": observed_at,
    }
    review = DeliveryReviewReceipt.model_construct(review_id="0" * 64, **review_values)
    return result.model_copy(
        update={
            "observations": (
                DeliveryLegacyObservationReceipt(
                    observation_id=_receipt_digest(observation, "observation_id"), **observation_values
                ),
            ),
            "review": DeliveryReviewReceipt(review_id=_receipt_digest(review, "review_id"), **review_values),
        }
    )


def _finalization_request(
    change_id: str,
    exact_head: str,
    operation_id: str | None = None,
    *,
    runtime: DeliveryRuntime | None = None,
) -> FinalizeDeliveryChange:
    runtime = runtime or _FINALIZATION_RUNTIMES[change_id]
    return finalization_proof(
        runtime.finalization_semantics(exact_head),
        change_id=change_id,
        exact_head=exact_head,
        operation_id=operation_id or f"finalize-{change_id}",
        observed_at=datetime(2026, 8, 11, 13, tzinfo=UTC),
        procedure="Portfolio finalization exact-head check",
        author_id="Portfolio finalization author",
        reviewer_id="Portfolio finalization reviewer",
        evidence="The exact Change head satisfies finalization authority.",
    )


def _runtime(  # noqa: PLR0913
    state_root: Path,
    contract: DeliveryContract,
    manager: ChangeWorkspaceManager,
    stage: DeliveryStage,
    completed_commit: str,
    *,
    legacy: bool = False,
) -> DeliveryRuntime:
    task = _task()
    authority_digest = hashlib.sha256(_canonical(contract)).hexdigest()
    has_task = stage in {DeliveryStage.IMPLEMENTATION, DeliveryStage.COMPLETED}
    has_result = stage == DeliveryStage.COMPLETED
    shape = _legacy_task_result if legacy else (lambda item: item)
    result = shape(
        _task_result(
            "RESULT-001",
            contract.change_id,
            authority_digest,
            task,
            completed_commit,
        )
    )
    bindings = [
        OutcomeAuthorityBinding(
            outcome_id="OUT-001",
            plan_scope_id="SCOPE-001",
            stage=stage,
            tasks=(task,) if has_task else (),
            results=(result,) if has_result else (),
        )
    ]
    if len(contract.outcomes) > 1:
        downstream_task = _downstream_task()
        if not contract.outcomes[1].dependency_ids:
            downstream_task = downstream_task.model_copy(update={"dependency_ids": ()})
        downstream_result = shape(
            _task_result(
                "RESULT-002",
                contract.change_id,
                authority_digest,
                downstream_task,
                completed_commit,
            )
        )
        bindings.append(
            OutcomeAuthorityBinding(
                outcome_id="OUT-002",
                plan_scope_id="SCOPE-002",
                stage=DeliveryStage.COMPLETED if has_result else DeliveryStage.IMPLEMENTATION,
                tasks=(downstream_task,) if has_task else (),
                results=(downstream_result,) if has_result else (),
            )
        )
    frontier = DeliveryFrontier(bindings=tuple(bindings), schema_version=18 if legacy else 19)
    path = state_root / "changes" / contract.change_id / "frontier.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical(frontier))
    runtime = DeliveryRuntime(state_root, contract, workspace_manager=manager)
    _FINALIZATION_RUNTIMES[contract.change_id] = runtime
    return runtime


def _set_checkpoint(
    runtime: DeliveryRuntime,
    state_root: Path,
    pending: DeliveryPendingCheckpoint,
    *,
    published_head: str | None = None,
) -> Path:
    path = state_root / f"changes/{runtime.contract.change_id}/frontier.json"
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    path.write_bytes(
        _canonical(frontier.model_copy(update={"published_head": published_head, "pending_checkpoint": pending}))
    )
    return path


def _policies() -> tuple[DeliveryRolePolicy, ...]:
    return (
        DeliveryRolePolicy(
            worker_role=DeliveryWorkerRole.PLANNER,
            worker_agent="planner",
            reviewer_agent="planner-challenger",
        ),
        DeliveryRolePolicy(
            worker_role=DeliveryWorkerRole.BUILDER,
            worker_agent="builder",
            reviewer_agent="build-reviewer",
        ),
    )


def _startup_config() -> DeliveryStartupConfig:
    return DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
    )


def _mark_current_format(runtime_root: Path) -> None:
    """Record the supported format for runtime records seeded directly through their owners."""
    runtime_root.mkdir(parents=True, exist_ok=True)
    (runtime_root / "format.json").write_bytes(format_marker_bytes())


def _repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir(parents=True)
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Loader Test")
    _git(repository, "config", "user.email", "loader@example.invalid")
    (repository / "product.txt").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "baseline")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(repository, "remote", "add", "origin", "https://github.com/example/project.git")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repository


class _TestPreservationProvenanceProvider:
    def classify(self, **kwargs):
        intent = kwargs["intent"]
        worktree = kwargs["worktree_path"]

        def before_state(path: str) -> tuple[str, str | None, int | None]:
            candidate = worktree / PurePosixPath(path)
            try:
                metadata = candidate.lstat()
            except FileNotFoundError:
                return "absent", None, None
            if stat.S_ISLNK(metadata.st_mode):
                content = os.fsencode(candidate.readlink())
                return "symlink", hashlib.sha256(content).hexdigest(), 0o777
            content = candidate.read_bytes()
            return "regular", hashlib.sha256(content).hexdigest(), stat.S_IMODE(metadata.st_mode)

        def path_provenance(path: str) -> PreservationPathProvenance:
            kind, before_digest, before_mode = before_state(path)
            return PreservationPathProvenance(
                path=path,
                disposition="disposable",
                producer_id="test-owner",
                before_kind=kind,
                before_digest=before_digest,
                before_mode=before_mode,
            )

        return PreservationProvenanceEvidence(
            evidence_id="test-owner-evidence",
            change_id=kwargs["change_id"],
            recovery_id=kwargs["recovery_id"],
            worktree_path=worktree,
            workspace_fingerprint=intent.workspace_fingerprint,
            exact_head=kwargs["exact_head"],
            index_digest=kwargs["index_digest"],
            task_id=intent.admitted_task_id,
            task_digest=intent.admitted_task_digest,
            paths=tuple(path_provenance(path) for path in kwargs["paths"]),
        )

    def verify(self, **kwargs):
        return kwargs["evidence"]


def _advance_remote_target(tmp_path: Path, remote: Path, *, product: str | None = None) -> str:
    target_repository = tmp_path / "target-repository"
    _git(tmp_path, "clone", str(remote), str(target_repository))
    _git(target_repository, "config", "user.name", "Target User")
    _git(target_repository, "config", "user.email", "target@example.invalid")
    target_file = target_repository / ("product.txt" if product is not None else "target.txt")
    target_file.write_text(product if product is not None else "target\n", encoding="utf-8")
    _git(target_repository, "add", target_file.name)
    _git(target_repository, "commit", "-m", "advance target")
    _git(target_repository, "push", "origin", "HEAD:refs/heads/main")
    return _git(target_repository, "rev-parse", "HEAD")


def _publish_external_change_head(
    tmp_path: Path,
    repository: Path,
    branch: str,
    base_head: str,
) -> str:
    remote = tmp_path / "external-change-remote.git"
    _git(tmp_path, "init", "--bare", "-b", branch, str(remote))
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", f"{base_head}:refs/heads/{branch}")
    external = tmp_path / "external-change-repository"
    _git(tmp_path, "clone", str(remote), str(external))
    _git(external, "checkout", "-b", "external", base_head)
    _git(external, "config", "user.name", "External User")
    _git(external, "config", "user.email", "external@example.invalid")
    (external / "external.txt").write_text("external\n", encoding="utf-8")
    _git(external, "add", "external.txt")
    _git(external, "commit", "-m", "external Change update")
    adopted = _git(external, "rev-parse", "HEAD")
    _git(external, "push", "origin", f"{adopted}:refs/heads/{branch}")
    return adopted


def _change_intent(
    application, change_id: str, kind: DeliveryChangeIntentKind, reason: str | None = None, digest: str | None = None
):
    """Apply one Pause or Resume through the single public intent path, bound to the current frontier."""
    if digest is None:
        digest = hashlib.sha256(application._runtimes[change_id].frontier_bytes()).hexdigest()
    return application.set_change_intent(
        DeliveryChangeIntent(change_id=change_id, kind=kind, expected_frontier_digest=digest, reason=reason)
    ).receipt


def _portfolio(  # noqa: PLR0913 - shared fixture preserves existing controls and independent-outcome setup.
    tmp_path: Path,
    stages: dict[str, DeliveryStage],
    *,
    execution_capacity: int = 3,
    clock: Callable[[], str] = lambda: "2026-08-04T00:00:00Z",
    include_downstream: bool = False,
    include_independent: bool = False,
):
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Portfolio Test")
    _git(repository, "config", "user.email", "portfolio@example.invalid")
    (repository / "product.txt").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "baseline")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    state_root = tmp_path / "state"
    package_root = tmp_path / "packages"
    coordinator = PortfolioCoordinator(state_root)
    manager = ChangeWorkspaceManager(
        repository,
        tmp_path / "worktrees",
        coordinator,
        "main",
        preservation_provenance_provider=_TestPreservationProvenanceProvider(),
    )
    store = DesignPackageStore(package_root, repository)
    authority_registry = DeliveryAuthorityRegistry(state_root, store, integration_target="main")
    runtimes = {}
    for change_id, stage in stages.items():
        intent = f"intent prose sentinel {change_id}\n".encode()
        design = f"design prose sentinel {change_id}\n".encode()
        contract = _contract(
            change_id,
            intent,
            design,
            include_downstream=include_downstream,
            include_independent=include_independent,
        )
        package = store.create(change_id, intent, design)
        store.publish_contract(change_id, package.package_id, _canonical(contract), lambda *_content: None)
        coordination = manager.ensure(change_id)
        runtime = _runtime(state_root, contract, manager, stage, coordination.last_reviewed_commit)
        runtimes[change_id] = runtime
        frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
        (state_root / "changes" / change_id / "contract.json").write_bytes(_canonical(contract))
        (state_root / "changes" / change_id / "admission.json").write_bytes(
            _canonical(_admission_receipt(contract, frontier, coordination.last_reviewed_commit))
        )
    identities = (f"identity-{index:03}" for index in itertools.count(1))

    application = PortfolioApplication(
        dict(reversed(tuple(runtimes.items()))),
        PortfolioApplicationDependencies(
            target_root=state_root,
            package_store=store,
            authority_registry=authority_registry,
            coordinator=coordinator,
            workspace_manager=manager,
            completed_history_catalog=CompletedHistoryCatalog(state_root),
        ),
        PortfolioApplicationConfig(
            package_root=package_root,
            execution_capacity=execution_capacity,
            role_policies=_policies(),
        ),
        PortfolioApplicationHooks(
            identity_factory=lambda: next(identities),
            clock=clock,
        ),
    )
    return application, runtimes, coordinator, state_root


def _seed_loader_composed_completed_change(
    tmp_path: Path,
    change_stages: tuple[tuple[str, DeliveryStage], ...] = (("change-a", DeliveryStage.COMPLETED),),
    *,
    marked: bool = True,
) -> tuple[Path, Path]:
    """Seed loader-visible state through its owners; ``marked=False`` leaves it in the D03 format 0."""
    repository = _repository(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    package_root = repository / ".owlbear/delivery/packages"
    worktree_root = repository / ".owlbear/delivery/worktrees"
    if marked:
        _mark_current_format(runtime_root)
    coordinator = PortfolioCoordinator(runtime_root)
    manager = ChangeWorkspaceManager(repository, worktree_root, coordinator, "main", "origin")
    store = DesignPackageStore(package_root, repository, transaction_root=runtime_root)
    for change_id, stage in change_stages:
        intent = f"loader-composed intent {change_id}\n".encode()
        design = f"loader-composed design {change_id}\n".encode()
        contract = _contract(change_id, intent, design)
        package = store.create(change_id, intent, design)
        store.publish_contract(change_id, package.package_id, _canonical(contract), lambda *_content: None)
        coordination = manager.ensure(change_id)
        runtime = _runtime(
            runtime_root,
            contract,
            manager,
            stage,
            coordination.last_reviewed_commit,
            legacy=not marked,
        )
        frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
        change_root = runtime_root / "changes" / change_id
        (change_root / "contract.json").write_bytes(_canonical(contract))
        (change_root / "admission.json").write_bytes(
            _canonical(_admission_receipt(contract, frontier, coordination.last_reviewed_commit))
        )
    return repository, runtime_root


def _reopen_portfolio(
    tmp_path: Path,
    state_root: Path,
    runtimes: dict[str, DeliveryRuntime],
    *,
    clock: Callable[[], str] | None = None,
    execution_capacity: int = 3,
) -> tuple[PortfolioApplication, PortfolioCoordinator, ChangeWorkspaceManager]:
    repository = tmp_path / "repository"
    package_root = tmp_path / "packages"
    coordinator = PortfolioCoordinator(state_root)
    manager = ChangeWorkspaceManager(
        repository,
        tmp_path / "worktrees",
        coordinator,
        "main",
        preservation_provenance_provider=_TestPreservationProvenanceProvider(),
    )
    store = DesignPackageStore(package_root, repository)
    authority_registry = DeliveryAuthorityRegistry(state_root, store, integration_target="main")
    hooks = (
        None if clock is None else PortfolioApplicationHooks(identity_factory=lambda: str(uuid.uuid4()), clock=clock)
    )
    reopened_runtimes = {
        change_id: DeliveryRuntime(state_root, runtime.contract, workspace_manager=manager)
        for change_id, runtime in runtimes.items()
    }
    application = PortfolioApplication(
        reopened_runtimes,
        PortfolioApplicationDependencies(
            target_root=state_root,
            package_store=store,
            authority_registry=authority_registry,
            coordinator=coordinator,
            workspace_manager=manager,
            completed_history_catalog=CompletedHistoryCatalog(state_root),
        ),
        PortfolioApplicationConfig(
            package_root=package_root,
            execution_capacity=execution_capacity,
            role_policies=_policies(),
        ),
        hooks,
    )
    return application, coordinator, manager


def test_show_work_item_explains_mcp_publication_identity(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )

    with pytest.raises(
        PortfolioApplicationError,
        match=r"invalid for MCP publication lookup.*change-a.*work_item_id",
    ):
        application.show_work_item("change-a", "publication")


def _shared_acquisition_command() -> str:
    return r"""
import json
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from owlbear_delivery import (
    ChangeWorkspaceManager,
    CompletedHistoryCatalog,
    DeliveryAuthorityRegistry,
    DeliveryRolePolicy,
    DeliveryRuntime,
    DeliveryWorkerRole,
    DesignPackageStore,
    PortfolioApplication,
    PortfolioApplicationConfig,
    PortfolioApplicationDependencies,
    PortfolioCoordinator,
)
from owlbear_delivery.delivery_contract_discovery import discover_persisted_changes

state_root, repository, package_root, worktree_root, barrier_root = map(Path, sys.argv[1:6])
worker_id = sys.argv[6]
coordinator = PortfolioCoordinator(state_root)
workspace_manager = ChangeWorkspaceManager(repository, worktree_root, coordinator, "main")
package_store = DesignPackageStore(package_root, repository)
authority_registry = DeliveryAuthorityRegistry(state_root, package_store, integration_target="main")
observations = discover_persisted_changes(state_root)
runtimes = {
    observation.change_id: DeliveryRuntime(state_root, observation.contract, workspace_manager=workspace_manager)
    for observation in observations
    if observation.contract is not None
}
policies = (
    DeliveryRolePolicy(
        worker_role=DeliveryWorkerRole.PLANNER,
        worker_agent="planner",
        reviewer_agent="planner-challenger",
    ),
    DeliveryRolePolicy(
        worker_role=DeliveryWorkerRole.BUILDER,
        worker_agent="builder",
        reviewer_agent="build-reviewer",
    ),
)
application = PortfolioApplication(
    runtimes,
    PortfolioApplicationDependencies(
        target_root=state_root,
        package_store=package_store,
        authority_registry=authority_registry,
        coordinator=coordinator,
        workspace_manager=workspace_manager,
        completed_history_catalog=CompletedHistoryCatalog(state_root),
    ),
    PortfolioApplicationConfig(package_root=package_root, execution_capacity=3, role_policies=policies),
)
(barrier_root / f"ready-{worker_id}").write_text("ready", encoding="ascii")
while not (barrier_root / "go").exists():
    time.sleep(0.01)
original_lock = coordinator.acquisition_lock
original_reconcile = application._reconcile_runtimes
lock_marker = barrier_root / f"lock-{worker_id}"
outside_marker = barrier_root / f"outside-{worker_id}"

@contextmanager
def observed_lock():
    with original_lock():
        lock_marker.write_text("locked", encoding="ascii")
        try:
            yield
        finally:
            active = [
                claim
                for observation in discover_persisted_changes(state_root)
                if observation.frontier is not None
                for binding in observation.frontier.bindings
                for claim in (binding.active_claim,)
                if claim is not None
            ]
            (barrier_root / f"inside-{worker_id}.json").write_text(
                json.dumps({"count": len(active), "roles": sorted(claim.worker_role.value for claim in active)}),
                encoding="utf-8",
            )
            lock_marker.unlink(missing_ok=True)

def reconcile():
    location = "inside" if lock_marker.exists() else "outside"
    (barrier_root / f"reconcile-{worker_id}-{location}").write_text("reconciled", encoding="ascii")
    return original_reconcile()

coordinator.acquisition_lock = observed_lock
application._reconcile_runtimes = reconcile
result = application.acquire_frontier_work()
(barrier_root / f"result-{worker_id}.json").write_text(
    json.dumps({"launches": len(result.launch_packages)}),
    encoding="utf-8",
)
"""


def _wait_for_files(paths: tuple[Path, ...], timeout: float = 10) -> None:
    deadline = time.monotonic() + timeout
    while not all(path.exists() for path in paths):
        if time.monotonic() >= deadline:
            message = f"timed out waiting for {paths}"
            raise TimeoutError(message)
        time.sleep(0.01)


def test_continuation_acquires_only_selected_change_and_never_redispatches(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING}
    )
    sibling = runtimes["change-b"].frontier_bytes()
    view = application.get_change("change-a")
    request = DeliveryContinuationRequest(
        change_id="change-a",
        expected_basis=view.readiness.basis,
        capabilities=("planner", "builder", "finalizer"),
        host_id="test-host",
        session_id="test-session",
    )

    acquired = application.acquire_change_action(request)
    repeated = application.acquire_change_action(request)

    assert acquired.kind == "acquired"
    assert acquired.launch.change_id == "change-a"
    assert acquired.launch.claim.owner_id == request.host_id
    assert acquired.launch.claim.process_id == request.session_id
    active = application.get_change("change-a").unresolved_outcomes[0].active_claim
    assert active.owner_id == request.host_id
    assert active.process_id == request.session_id
    assert active.continuation
    assert active.claim_id == acquired.launch.claim.claim_id
    assert view.readiness.basis.source_head == acquired.launch.source_head
    assert view.readiness.basis.candidate_head is None
    assert repeated.kind == "busy"
    assert repeated.launch is None
    assert runtimes["change-b"].frontier_bytes() == sibling
    assert coordinator.show("change-b").writer is None


def _continuation_request(application, change_id="change-a", **updates):
    return DeliveryContinuationRequest(
        change_id=change_id,
        expected_basis=application.get_change(change_id).readiness.basis,
        capabilities=("planner", "builder", "finalizer", "engine"),
        host_id="test-host",
        session_id="test-session",
    ).model_copy(update=updates)


def test_runtime_rejects_mismatched_coordination_recovery_root(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    before = runtimes["change-a"].frontier_bytes()
    with pytest.raises(DeliveryRuntimeConflictError, match="share one transaction root"):
        DeliveryRuntime(
            state_root / "other", runtimes["change-a"].contract, workspace_manager=application._workspace_manager
        )
    assert runtimes["change-a"].frontier_bytes() == before
    assert not (state_root / "other").exists()


def test_completed_outcome_of_open_change_reports_outcome_complete(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})

    readiness = application.show_work_item_view("change-a", "outcome:OUT-001").card.readiness
    publication = application.show_work_item_view("change-a", "publication").card.readiness

    assert readiness is not None
    assert (readiness.status, readiness.reason_code) == ("complete", "outcome-complete")
    assert publication is not None
    assert publication.reason_code != "change-terminal"


def test_engine_action_custody_survives_restart_and_fences_runtime(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    basis = application.get_change("change-a").readiness.basis
    action = ChangeContinuationAction(
        operation_id="continue-" + "a" * 64,
        change_id="change-a",
        kind="reconcile-checkpoint",
        contract_digest=basis.contract_digest,
        frontier_digest=basis.frontier_digest,
        exact_head=basis.candidate_head,
        target_head=application._workspace_manager.observed_target_head(),
        host_id="host",
        session_id="session",
        acquired_at="2026-09-13T00:00:00Z",
    )
    coordinator.acquire_continuation_action(action)
    reopened, other_coordinator, _manager = _reopen_portfolio(tmp_path, state_root, runtimes)
    assert other_coordinator.show("change-a").continuation_action == action
    with pytest.raises(CoordinationConflictError, match="continuation action custody"):
        reopened._runtimes["change-a"].queue_explicit_checkpoint(action.exact_head)
    with coordinator.continuation_execution(action):
        runtimes["change-a"].queue_explicit_checkpoint(action.exact_head)
        coordinator.finish_continuation_action(action, b"{}\n", "2026-09-13T00:00:01Z", release=True)
    assert other_coordinator.show("change-a").continuation_action.finished_at is not None
    assert coordinator.continuation_record_path("change-a", action.operation_id, result=True).read_bytes() == b"{}\n"


@pytest.mark.parametrize("damage", [None, "missing", "malformed"])
def test_public_mutation_distinguishes_engine_custody_from_coordination_damage(
    tmp_path: Path, damage: str | None
) -> None:
    application, runtime, _provider, _state, _head, state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False
    )
    action = _engine_action(application)
    before = runtime.frontier_bytes()
    path = state_root / "coordination/changes/change-a.json"
    if damage == "missing":
        path.unlink()
    elif damage == "malformed":
        path.write_bytes(b"{")
    intent = DeliveryChangeIntent(
        change_id="change-a",
        kind=DeliveryChangeIntentKind.DEFER,
        expected_frontier_digest=hashlib.sha256(before).hexdigest(),
        reason="pause",
    )
    if damage is None:
        # N09-A2: Pause under engine custody records a draining request instead of being refused.
        result = application.set_change_intent(intent)
        assert result.receipt == application._coordinator.pause_request("change-a")
    else:
        with pytest.raises(DeliveryRuntimeReconciliationError):
            application.set_change_intent(intent)
    assert runtime.frontier_bytes() == before
    if damage is None:
        assert application._coordinator.show("change-a").continuation_action == action
    elif damage == "missing":
        assert not path.exists()
    else:
        assert path.read_bytes() == b"{"


def _engine_action(application: PortfolioApplication, change_id: str = "change-a") -> ChangeContinuationAction:
    acquired = application.acquire_change_action(_continuation_request(application, change_id))
    if acquired.kind == "reconciled":
        acquired = application.acquire_change_action(_continuation_request(application, change_id))
    assert acquired.kind == "acquired", acquired
    assert acquired.engine_action is not None, acquired
    return acquired.engine_action


def _execute_engine(application: PortfolioApplication, action: ChangeContinuationAction) -> DeliveryEngineActionResult:
    return application.execute_change_action(
        ExecuteDeliveryChangeAction(change_id=action.change_id, operation_id=action.operation_id)
    )


def _attach_local_target(application: PortfolioApplication, tmp_path: Path) -> Path:
    repository = application._workspace_manager.repository
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    operation = "set-url" if "origin" in _git(repository, "remote").splitlines() else "add"
    _git(repository, "remote", operation, "origin", str(remote))
    _git(repository, "push", "origin", "HEAD:refs/heads/main")
    return remote


def _workspace_mutation_snapshot(worktree: Path) -> tuple[dict[str, bytes], bytes, tuple[str, ...], str]:
    index_path = Path(_git(worktree, "rev-parse", "--path-format=absolute", "--git-path", "index"))
    refs = tuple(
        line
        for line in _git(worktree, "show-ref").splitlines()
        if not line.endswith("refs/remotes/origin/owlbear/delivery-state")
    )
    return (
        _file_bytes(worktree),
        index_path.read_bytes(),
        refs,
        _git(worktree, "status", "--porcelain=v1", "--untracked-files=all"),
    )


def _workspace_content_snapshot(worktree: Path) -> tuple[dict[str, bytes], bytes, tuple[str, ...]]:
    index_path = Path(_git(worktree, "rev-parse", "--path-format=absolute", "--git-path", "index"))
    refs = tuple(
        line
        for line in _git(worktree, "show-ref").splitlines()
        if not line.endswith("refs/remotes/origin/owlbear/delivery-state")
    )
    return _file_bytes(worktree), index_path.read_bytes(), refs


def _loader_activation_state_snapshot(application: PortfolioApplication) -> dict[str, object]:
    coordinator = application._coordinator
    changes = {}
    for change_id, runtime in application._runtimes.items():
        coordination = coordinator.show(change_id)
        changes[change_id] = {
            "frontier": runtime.frontier_bytes(),
            "retry_ledger": runtime.retry_ledger().read(),
            "coordination": (coordinator.runtime_root / "coordination" / "changes" / f"{change_id}.json").read_bytes(),
            "workspace": _workspace_mutation_snapshot(coordination.worktree_path),
        }
    return {
        "changes": changes,
        "repository_refs": _git(
            application._workspace_manager.repository,
            "for-each-ref",
            "--format=%(refname) %(objectname)",
        ),
    }


def _loader_engine_state_snapshot(  # noqa: PLR0913
    application: PortfolioApplication,
    *,
    runtime_root: Path,
    remote_refs: str,
    provider: _Provider,
    change_id: str,
    operation_id: str,
) -> dict[str, object]:
    """Capture durable owner effects and replay evidence around loader boundaries."""

    def json_tree(root: Path) -> tuple[tuple[str, bytes], ...]:
        if not root.exists():
            return ()
        return tuple(
            (path.relative_to(root).as_posix(), path.read_bytes())
            for path in sorted(root.rglob("*.json"))
            if path.is_file()
        )

    coordinator = application._coordinator
    runtime = application._runtimes[change_id]
    worktree = coordinator.show(change_id).worktree_path
    workspace = _workspace_mutation_snapshot(worktree)
    operation_path = coordinator.continuation_record_path(change_id, operation_id)
    operation_journal = {
        "intent": operation_path.read_bytes() if operation_path.is_file() else None,
        "started": (
            operation_path.with_name("started.json").read_bytes()
            if operation_path.with_name("started.json").is_file()
            else None
        ),
        "result": (
            operation_path.with_name("result.json").read_bytes()
            if operation_path.with_name("result.json").is_file()
            else None
        ),
    }
    siblings = {}
    for sibling_id, sibling_runtime in application._runtimes.items():
        if sibling_id == change_id:
            continue
        sibling_coordination = coordinator.show(sibling_id)
        sibling_workspace = _workspace_mutation_snapshot(sibling_coordination.worktree_path)
        siblings[sibling_id] = {
            "frontier": sibling_runtime.frontier_bytes(),
            "retry_ledger": sibling_runtime.retry_ledger().read(),
            "retry_journal": json_tree(runtime_root / "changes" / sibling_id / "retry-ledger"),
            "coordination": (coordinator.runtime_root / "coordination" / "changes" / f"{sibling_id}.json").read_bytes(),
            "continuation_action": sibling_coordination.continuation_action,
            "workspace": sibling_workspace,
            "raw_index": sibling_workspace[1],
            "checkpoint_publication": sibling_runtime.checkpoint_publication_state(),
            "publication_history": sibling_runtime.publication_history(),
        }
    return {
        "frontier": runtime.frontier_bytes(),
        "retry_ledger": runtime.retry_ledger().read(),
        "retry_journal": json_tree(runtime_root / "changes" / change_id / "retry-ledger"),
        "coordination": (coordinator.runtime_root / "coordination" / "changes" / f"{change_id}.json").read_bytes(),
        "continuation_action": coordinator.show(change_id).continuation_action,
        "workspace": workspace,
        "raw_index": workspace[1],
        "remote_refs": remote_refs,
        "provider_mutations": (
            provider.create_calls,
            provider.update_calls,
            provider.draft_state_calls,
        ),
        "provider_reads": {
            "read_pull_request": (
                provider.read_pull_request.call_count,
                tuple(provider.read_pull_request.call_args_list),
            ),
            "observe_checks": (
                provider.observe_checks.call_count,
                tuple(provider.observe_checks.call_args_list),
            ),
        },
        "continuation_operation_journal": operation_journal,
        "checkpoint_publication": runtime.checkpoint_publication_state(),
        "publication_history": runtime.publication_history(),
        "branch_publication_journal": json_tree(runtime_root / "publications" / "change-branches" / "operations"),
        "publication_journal": json_tree(runtime_root / "publications"),
        "completion_journal": json_tree(runtime_root / "completions"),
        "siblings": siblings,
    }


def _assert_checkpoint_branch_operation(
    before: dict[str, object],
    after: dict[str, object],
    *,
    change_id: str,
    published_head: str,
    expected_remote_head: str | None,
) -> None:
    """Require the exact action-bound branch operation, whether new or replayed."""
    operation_payload = json.dumps(("branch", change_id, published_head), separators=(",", ":"))
    operation_id = f"checkpoint-branch-{hashlib.sha256(operation_payload.encode()).hexdigest()}"
    operation_path = f"{hashlib.sha256(operation_id.encode()).hexdigest()}.json"
    before_journal = dict(before["branch_publication_journal"])
    after_journal = dict(after["branch_publication_journal"])
    assert operation_path in after_journal
    if operation_path in before_journal:
        assert before_journal[operation_path] == after_journal[operation_path]
    else:
        assert after_journal[operation_path]
    operation = json.loads(after_journal[operation_path])
    assert operation["operation_id"] == operation_id
    assert operation["change_id"] == change_id
    assert operation["branch"] == f"owlbear/change/{change_id}"
    assert operation["expected_remote_head"] == expected_remote_head
    assert operation["published_head"] == published_head


def _assert_loader_observation_only(before: dict[str, object], after: dict[str, object]) -> None:
    """Allow boundary startup to record only its read-only provider observations."""
    before_reads = before["provider_reads"]
    after_reads = after["provider_reads"]
    before_pull_reads = before_reads["read_pull_request"]
    after_pull_reads = after_reads["read_pull_request"]
    assert after_pull_reads[0] >= before_pull_reads[0]
    assert after_pull_reads[1][: before_pull_reads[0]] == before_pull_reads[1]
    added_calls = after_pull_reads[1][before_pull_reads[0] :]
    assert all(call.args in {("example/project", 7), ("example/project", 8)} for call in added_calls)
    assert after_reads["observe_checks"] == before_reads["observe_checks"]
    assert after["provider_mutations"] == before["provider_mutations"]

    before_publications = dict(before["publication_journal"])
    after_publications = dict(after["publication_journal"])
    assert set(before_publications) <= set(after_publications)
    changed_publications = {
        path
        for path in before_publications.keys() & after_publications.keys()
        if before_publications[path] != after_publications[path]
    }
    added_publications = after_publications.keys() - before_publications.keys()
    assert all(
        path.startswith("pull-requests/pull-request-observations/")
        for path in changed_publications | added_publications
    )
    expected = dict(before)
    expected["provider_reads"] = after_reads
    expected["publication_journal"] = after["publication_journal"]
    assert after == expected


def _assert_loader_retry_recording(
    before: dict[str, object],
    after: dict[str, object],
    *,
    action_id: str,
    accepted_progress: bool,
) -> None:
    """Check the retry ledger replay performed while composing the fresh loader."""
    before_ledger = before["retry_ledger"]
    after_ledger = after["retry_ledger"]
    before_journal = dict(before["retry_journal"])
    after_journal = dict(after["retry_journal"])
    if not accepted_progress:
        assert after_ledger == before_ledger
        assert after_journal == before_journal
        return

    before_episodes = {episode.episode_id: episode for episode in before_ledger.episodes}
    after_episodes = {episode.episode_id: episode for episode in after_ledger.episodes}
    episode_id = next(episode.episode_id for episode in before_ledger.episodes if action_id in episode.attempt_ids)
    previous = before_episodes[episode_id]
    recorded = after_episodes[episode_id]
    assert recorded.attempt_ids == previous.attempt_ids
    assert recorded.outcome_ids[:-1] == previous.outcome_ids
    assert len(recorded.outcome_ids) == len(previous.outcome_ids) + 1
    assert recorded.accepted_attempt_ids == (*previous.accepted_attempt_ids, action_id)
    assert recorded.total_attempts == 0
    assert recorded.repair_attempts == 0
    assert recorded.observation_attempts == 0
    assert recorded.explicit_observations == 0
    assert recorded.last_status is None
    assert recorded.last_failure_at is None
    assert recorded.next_eligible_at is None
    assert recorded.stop_code is None
    assert recorded.reset_count == previous.reset_count + 1
    assert recorded.legacy_failures == previous.legacy_failures
    assert {key: value for key, value in before_episodes.items() if key != episode_id} == {
        key: value for key, value in after_episodes.items() if key != episode_id
    }
    assert after_ledger.version == before_ledger.version + 1

    added = after_journal.keys() - before_journal.keys()
    changed = {
        path for path in before_journal.keys() & after_journal.keys() if before_journal[path] != after_journal[path]
    }
    assert len(added) == 1
    outcome_path = next(iter(added))
    outcome_id = recorded.outcome_ids[-1]
    assert outcome_path == f"outcomes/{outcome_id}.json"
    assert changed == {"current.json"}
    outcome = json.loads(after_journal[outcome_path])
    assert outcome["attempt_id"] == action_id
    assert outcome["episode_id"] == episode_id
    assert outcome["status"] == "succeeded"


def _attach_engine_publication(application: PortfolioApplication, tmp_path: Path) -> tuple[_Provider, Path]:
    repository = application._workspace_manager.repository
    remote = _attach_local_target(application, tmp_path)
    provider = _Provider(lose_create_response=True, lose_update_response=True, lose_draft_state_response=True)
    application._change_branch_publisher = ChangeBranchPublisher(
        repository,
        application._coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "branch-operations",
    )
    application._draft_pull_request_publisher = DraftPullRequestPublisher(
        provider,
        repository="example/project",
        target_branch="main",
        state_root=tmp_path / "pull-requests",
    )
    application._delivery_state_publisher = DeliveryStatePublisher(
        repository,
        remote="origin",
        state_branch="owlbear/delivery-state",
    )
    return provider, remote


def test_continuation_publishes_syncs_finalizes_and_observes_acceptance(tmp_path: Path) -> None:  # noqa: PLR0915 - one journey.
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    runtime = runtimes["change-a"]
    head = coordinator.show("change-a").last_reviewed_commit
    _set_checkpoint(
        runtime,
        state_root,
        DeliveryPendingCheckpoint(
            head=head,
            triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
        ),
    )
    provider, remote = _attach_engine_publication(application, tmp_path)
    checkpoint_action = _engine_action(application)
    assert checkpoint_action.kind == "reconcile-checkpoint"
    checkpoint = _execute_engine(application, checkpoint_action)
    assert checkpoint.kind == "completed", checkpoint
    assert checkpoint.checkpoint.reconciled
    assert _execute_engine(application, checkpoint_action) == checkpoint
    for field in ("attempted_head", "published_head"):
        malformed = checkpoint.model_dump(mode="json")
        target = malformed["checkpoint"] if field == "attempted_head" else malformed["checkpoint"]["state"]
        target[field] = "f" * 40
        with pytest.raises(ValidationError, match="checkpoint result differs"):
            DeliveryEngineActionResult.model_validate_json(json.dumps(malformed))
    assert provider.create_calls == 1
    sync_action = _engine_action(application)
    assert sync_action.kind == "sync-target"
    synchronized = _execute_engine(application, sync_action)
    assert synchronized.kind == "completed", synchronized
    assert synchronized.target_sync.operation_id == sync_action.operation_id
    assert _execute_engine(application, sync_action) == synchronized
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.kind == "acquired", acquired
    finalizer = acquired.finalization
    assert finalizer is not None
    proof = _finalization_request("change-a", finalizer.attempt.exact_head, finalizer.attempt.writer.attempt_id)
    application.finalize_change("change-a", proof)
    published = _execute_engine(application, _engine_action(application))
    assert published.kind == "completed", published
    ready_action = _engine_action(application)
    assert ready_action.kind == "mark-ready"
    ready = _execute_engine(application, ready_action)
    assert ready.kind == "completed", ready
    assert provider.draft_state_calls == 1
    waiting = application.acquire_change_action(_continuation_request(application))
    if waiting.kind == "reconciled":
        waiting = application.acquire_change_action(_continuation_request(application))
    assert (waiting.kind, waiting.reason_code, waiting.engine_action) == ("human", "merge-blocked", None), waiting
    assert runtime.completion_receipt() is None
    assert _git(remote, "rev-parse", "refs/heads/main") == head
    provider.pull_requests[0] = provider.pull_requests[0].model_copy(
        update={
            "state": "closed",
            "merged": True,
            "merge_commit_sha": finalizer.attempt.exact_head,
            "merged_at": datetime(2026, 8, 3, tzinfo=UTC),
        }
    )
    application._clock = lambda: "2026-08-04T00:00:01Z"
    application._publication_observation_cache.clear()
    acceptance_action = _engine_action(application)
    accepted = _execute_engine(application, acceptance_action)
    assert accepted.kind == "completed", accepted
    assert accepted.acceptance == runtime.completion_receipt()
    reopened, _coordinator, _manager = _reopen_portfolio(tmp_path, state_root, runtimes)
    assert _execute_engine(reopened, acceptance_action) == accepted
    assert reopened.acquire_change_action(_continuation_request(reopened)).kind == "terminal"


def test_engine_mark_ready_replays_lost_response_and_acceptance_waits_without_merge(tmp_path: Path) -> None:
    application, runtime, provider, state, head, state_root = _awaiting_acceptance_fixture(tmp_path, mark_ready=False)
    action = _engine_action(application)
    assert action.kind == "mark-ready"
    original = provider.set_pull_request_draft_state.side_effect

    def lose_response(request):
        original(request)
        raise PublicationProviderError(
            PublicationProviderFailureCode.RESPONSE_UNKNOWN, action.operation_id, "lost response", retry_safe=False
        )

    provider.set_pull_request_draft_state.side_effect = lose_response
    result = _execute_engine(application, action)
    assert result.kind == "completed", result
    assert result.ready.head_sha == head
    assert result.ready.operation_id == action.operation_id
    reopened, coordinator, _manager = _reopen_portfolio(tmp_path, state_root, {"change-a": runtime})
    assert _execute_engine(reopened, action) == result
    assert provider.set_pull_request_draft_state.call_count == 1
    assert coordinator.show("change-a").continuation_action.finished_at is not None
    opened = state["pull_request"]
    state["pull_request"] = opened.model_copy(
        update={
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "f" * 40,
            "merged_at": datetime(2026, 8, 3, tzinfo=UTC),
        }
    )
    application._publication_observation_cache.clear()
    request = _continuation_request(application)
    acquired = application.acquire_change_action(request)
    if acquired.kind == "reconciled":
        request = _continuation_request(application)
        acquired = application.acquire_change_action(request)
    waiting_action = acquired.engine_action
    assert waiting_action.kind == "observe-acceptance"
    state["pull_request"] = opened
    waiting = _execute_engine(application, waiting_action)
    assert waiting.kind == "waiting", waiting
    assert waiting.reason_code == "merge-approval-required"
    replayed = application.acquire_change_action(request)
    assert (replayed.kind, replayed.reason_code, replayed.engine_result) == ("human", "merge-blocked", waiting)
    assert not state["pull_request"].merged
    assert runtime.completion_receipt() is None
    assert _execute_engine(application, waiting_action) == waiting


@pytest.mark.parametrize("drift", ["head", "target", "dirty", "untracked"])
def test_engine_action_rechecks_head_target_and_workspace_before_provider(tmp_path: Path, drift: str) -> None:
    application, runtime, provider, _state, _head, _state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False
    )
    action = _engine_action(application)
    coordination = application._coordinator.show("change-a")
    if drift == "head":
        _commit_local_descendant(coordination)
    elif drift == "target":
        moved = _commit_local_descendant(coordination)
        _git(coordination.worktree_path, "update-ref", "refs/remotes/origin/main", moved)
        _git(coordination.worktree_path, "reset", "--hard", action.exact_head)
    else:
        dirty = coordination.worktree_path / ("product.txt" if drift == "dirty" else "untracked.txt")
        dirty.write_text("foreign changes\n")
    result = _execute_engine(application, action)
    assert result.kind == "stale", result
    assert result.reason_code == "readiness-changed"
    assert provider.set_pull_request_draft_state.call_count == 0
    assert runtime.ready_receipt() is None
    assert application._coordinator.show("change-a").continuation_action.finished_at is not None
    marker = application._coordinator.continuation_record_path("change-a", action.operation_id).with_name(
        "started.json"
    )
    assert not marker.exists()
    assert _execute_engine(application, action) == result
    if drift in {"dirty", "untracked"}:
        assert dirty.read_text() == "foreign changes\n"


def test_engine_preflight_interruption_replays_same_operation_after_restart(tmp_path: Path) -> None:
    application, runtime, provider, _state, _head, state_root = _awaiting_acceptance_fixture(tmp_path, mark_ready=False)
    action = _engine_action(application)
    intent = application._coordinator.continuation_record_path("change-a", action.operation_id)
    before = intent.read_bytes()
    with (
        patch.object(application._workspace_manager, "capture_finalization_workspace", side_effect=KeyboardInterrupt),
        pytest.raises(KeyboardInterrupt),
    ):
        _execute_engine(application, action)
    assert not intent.with_name("started.json").exists()
    assert not intent.with_name("result.json").exists()
    assert provider.set_pull_request_draft_state.call_count == 0
    reopened, coordinator, _manager = _reopen_portfolio(tmp_path, state_root, {"change-a": runtime})
    reopened._draft_pull_request_publisher = application._draft_pull_request_publisher
    assert coordinator.show("change-a").continuation_action == action
    result = _execute_engine(reopened, action)
    assert result.kind == "completed", result
    assert result.action == action
    assert intent.read_bytes() == before
    assert tuple(intent.parent.parent.iterdir()) == (intent.parent,)
    assert coordinator.show("change-a").continuation_action.finished_at is not None
    assert _execute_engine(reopened, action) == result
    assert provider.set_pull_request_draft_state.call_count == 1


@pytest.mark.parametrize("drift", ["frontier", "head", "target", "dirty"])
def test_engine_entry_marker_prevents_stale_release_after_interruption(tmp_path: Path, drift: str) -> None:
    application, runtime, provider, _state, _head, state_root = _awaiting_acceptance_fixture(tmp_path, mark_ready=False)
    action = _engine_action(application)
    coordinator = application._coordinator
    with coordinator.continuation_execution(action):
        assert coordinator.start_continuation_action(action)
    coordination = coordinator.show("change-a")
    if drift == "frontier":
        (state_root / "changes/change-a/frontier.json").write_bytes(runtime.frontier_bytes() + b"\n")
    elif drift == "head":
        _commit_local_descendant(coordination)
    elif drift == "target":
        moved = _commit_local_descendant(coordination)
        _git(coordination.worktree_path, "update-ref", "refs/remotes/origin/main", moved)
        _git(coordination.worktree_path, "reset", "--hard", action.exact_head)
    else:
        (coordination.worktree_path / "product.txt").write_text("foreign changes\n")
    reopened, coordinator, _manager = _reopen_portfolio(tmp_path, state_root, {"change-a": runtime})
    with patch.object(reopened, "_invoke_engine_owner") as owner:
        result = _execute_engine(reopened, action)
        assert _execute_engine(reopened, action) == result
    assert result.kind == "blocked"
    assert result.reason_code == "engine-action-interrupted"
    assert coordinator.show("change-a").continuation_action == action
    owner.assert_not_called()
    assert provider.set_pull_request_draft_state.call_count == 0


@pytest.mark.parametrize("damage", ["mismatched", "unreadable"])
def test_engine_damaged_entry_marker_retains_custody_without_effect(tmp_path: Path, damage: str) -> None:
    application, _runtime, provider, _state, _head, _state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False
    )
    action = _engine_action(application)
    coordinator = application._coordinator
    marker = coordinator.continuation_record_path("change-a", action.operation_id).with_name("started.json")
    if damage == "mismatched":
        marker.write_bytes(b"{")
    else:
        marker.mkdir()
    _commit_local_descendant(coordinator.show("change-a"))
    result = _execute_engine(application, action)
    assert result.kind == "blocked"
    assert coordinator.show("change-a").continuation_action == action
    assert _execute_engine(application, action) == result
    assert marker.read_bytes() == b"{" if damage == "mismatched" else marker.is_dir()
    assert provider.set_pull_request_draft_state.call_count == 0


@pytest.mark.parametrize("custody", ["claim", "integration-repair", "publication", "workspace-guard"])
def test_engine_conflicting_custody_prevents_stale_release(tmp_path: Path, custody: str) -> None:
    application, runtime, provider, _state, _head, state_root = _awaiting_acceptance_fixture(tmp_path, mark_ready=False)
    action = _engine_action(application)
    coordinator = application._coordinator
    coordination = coordinator.show("change-a")
    _commit_local_descendant(coordination)
    if custody in {"claim", "integration-repair"}:
        frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
        role = DeliveryWorkerRole.BUILDER if custody == "claim" else DeliveryWorkerRole.INTEGRATION_REPAIRER
        claim = application._new_claim(role, None)
        if custody == "claim":
            binding = frontier.bindings[0].model_copy(update={"active_claim": claim})
            frontier = frontier.model_copy(update={"bindings": (binding, *frontier.bindings[1:])})
        else:
            frontier = frontier.model_copy(update={"integration_repair_claim": claim})
        path = state_root / "changes/change-a/frontier.json"
        path.write_bytes(_canonical(frontier))
    else:
        update = (
            {
                "publication_lease": PublicationLease(
                    operation_id="foreign", owner_id="foreign", expires_at="2026-09-13T00:05:00Z"
                )
            }
            if custody == "publication"
            else {"last_reviewed_commit": "f" * 40}
        )
        path = state_root / "coordination/changes/change-a.json"
        path.write_bytes(_canonical(coordination.model_copy(update=update)))
    before = path.read_bytes()
    result = _execute_engine(application, action)
    assert result.kind == "blocked", result
    assert coordinator.show("change-a").continuation_action == action
    assert path.read_bytes() == before
    assert not coordinator.continuation_record_path("change-a", action.operation_id).with_name("started.json").exists()
    assert _execute_engine(application, action) == result
    assert provider.set_pull_request_draft_state.call_count == 0


def test_engine_contradictory_writer_is_preserved_without_release(tmp_path: Path) -> None:
    application, _runtime, provider, _state, _head, state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False
    )
    action = _engine_action(application)
    coordination = application._coordinator.show("change-a")
    _commit_local_descendant(coordination)
    writer = ChangeWriter(
        attempt_id="foreign",
        claim_id="foreign",
        actor_id="foreign",
        process_id="foreign",
        claimed_at="2026-09-13T00:00:00Z",
        job_id=1,
        kind="build",
    )
    path = state_root / "coordination/changes/change-a.json"
    before = _canonical(coordination.model_copy(update={"writer": writer}))
    path.write_bytes(before)
    with pytest.raises(CoordinationConflictError):
        _execute_engine(application, action)
    assert path.read_bytes() == before
    assert not application._coordinator.continuation_record_path("change-a", action.operation_id, result=True).exists()
    assert provider.set_pull_request_draft_state.call_count == 0


@pytest.mark.parametrize("head_field", ["candidate_head", "target_head"])
def test_engine_acquisition_without_required_head_returns_typed_stop(tmp_path: Path, head_field: str) -> None:
    application, _runtime, provider, _state, _head, _state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False
    )
    capture = application._capture_action_basis

    def missing_head(*args):
        basis, reason, guidance = capture(*args)
        return basis.model_copy(update={head_field: None}), reason, guidance

    with patch.object(application, "_capture_action_basis", side_effect=missing_head):
        result = application.acquire_change_action(_continuation_request(application))
        if result.kind == "reconciled":
            result = application.acquire_change_action(_continuation_request(application))
    assert result.kind == "waiting", result
    assert result.reason_code == "engine-owner-unavailable"
    assert result.engine_action is None
    assert application._coordinator.show("change-a").continuation_action is None
    assert provider.set_pull_request_draft_state.call_count == 0


@pytest.mark.parametrize("interrupted", [False, True])
def test_engine_unknown_result_after_effect_never_reenters_owner(tmp_path: Path, *, interrupted: bool) -> None:
    application, runtime, provider, _state, _head, state_root = _awaiting_acceptance_fixture(tmp_path, mark_ready=False)
    action = _engine_action(application)
    invoke = application._invoke_engine_owner

    def lose_result(retained):
        invoke(retained)
        raise KeyboardInterrupt if interrupted else RuntimeError("lost owner result")

    with patch.object(application, "_invoke_engine_owner", side_effect=lose_result):
        if interrupted:
            with pytest.raises(KeyboardInterrupt):
                _execute_engine(application, action)
        else:
            assert _execute_engine(application, action).kind == "blocked"
    assert runtime.ready_receipt() is not None
    reopened, coordinator, _manager = _reopen_portfolio(tmp_path, state_root, {"change-a": runtime})
    with patch.object(reopened, "_invoke_engine_owner") as owner:
        result = _execute_engine(reopened, action)
        assert result.kind == "blocked"
        assert _execute_engine(reopened, action) == result
    owner.assert_not_called()
    assert coordinator.show("change-a").continuation_action == action
    assert provider.set_pull_request_draft_state.call_count == 1


def test_engine_action_lost_dispatch_preserves_identity_and_strict_public_result(tmp_path: Path) -> None:
    application, runtime, _provider, _state, _head, state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False
    )
    request = _continuation_request(application)
    acquired = application.acquire_change_action(request)
    if acquired.kind == "reconciled":
        request = _continuation_request(application)
        acquired = application.acquire_change_action(request)
    action = acquired.engine_action
    assert action is not None
    reopened, _coordinator, _manager = _reopen_portfolio(tmp_path, state_root, {"change-a": runtime})
    replayed = reopened.acquire_change_action(request.model_copy(update={"session_id": "other-session"}))
    assert replayed.engine_action == action
    assert replayed.engine_action.session_id == "test-session"
    result = _execute_engine(application, action)
    assert DeliveryEngineActionResult.model_validate_json(result.model_dump_json()) == result
    for update in ({"reason_code": "ERR_FAKE"}, {"kind": "blocked"}, {"ready": None}, {"extra": True}):
        with pytest.raises(ValidationError):
            DeliveryEngineActionResult.model_validate_json(json.dumps(result.model_dump(mode="json") | update))
    replayed = reopened.acquire_change_action(request)
    assert replayed.kind == "reconciled"
    assert replayed.engine_result == result
    for update in ({"kind": "terminal"}, {"reason_code": "ready"}):
        with pytest.raises(ValidationError, match="exact engine disposition"):
            DeliveryContinuationResult.model_validate_json(json.dumps(replayed.model_dump(mode="json") | update))
    intent = application._coordinator.continuation_record_path(action.change_id, action.operation_id)
    intent.unlink()
    with pytest.raises(DeliveryRuntimeReconciliationError, match="original continuation intent"):
        _execute_engine(reopened, action)


@pytest.mark.parametrize("damage", ["missing-intent", "corrupt-intent", "missing-result", "corrupt-result"])
def test_engine_finished_action_requires_original_journal_before_advancing(tmp_path: Path, damage: str) -> None:
    application, runtime, provider, _state, _head, state_root = _awaiting_acceptance_fixture(tmp_path, mark_ready=False)
    action = _engine_action(application)
    assert _execute_engine(application, action).kind == "completed"
    path = application._coordinator.continuation_record_path(
        action.change_id, action.operation_id, result=damage.endswith("result")
    )
    if damage.startswith("missing"):
        path.unlink()
    else:
        path.write_bytes(b"{")
    reopened, coordinator, _manager = _reopen_portfolio(tmp_path, state_root, {"change-a": runtime})
    request = _continuation_request(reopened)
    result = reopened.acquire_change_action(request)
    assert result.kind == "unavailable"
    assert result.reason_code == "engine-action-blocked"
    assert result.failure.attempt_id == action.operation_id
    assert result.failure.code == DeliveryRuntimeReconciliationError.code
    assert "original intent/result journal cannot be verified" in result.failure.retry_condition
    assert "do not reconstruct or retry effects" in result.failure.retry_condition
    assert coordinator.show("change-a").continuation_action.operation_id == action.operation_id
    assert not coordinator.continuation_record_path("change-a", reopened._continuation_operation_id(request)).exists()
    assert provider.set_pull_request_draft_state.call_count == 1


@pytest.mark.parametrize("interrupted", [False, True])
def test_engine_failure_retains_exact_action_without_retry_or_release(tmp_path: Path, *, interrupted: bool) -> None:
    application, runtime, provider, _state, _head, state_root = _awaiting_acceptance_fixture(tmp_path, mark_ready=False)
    request = _continuation_request(application)
    acquired = application.acquire_change_action(request)
    if acquired.kind == "reconciled":
        request = _continuation_request(application)
        acquired = application.acquire_change_action(request)
    assert acquired.kind == "acquired"
    assert acquired.engine_action is not None
    action = acquired.engine_action
    if interrupted:
        with application._coordinator.continuation_execution(action):
            application._coordinator.start_continuation_action(action)
    else:
        provider.observe_checks.side_effect = PublicationProviderError(
            PublicationProviderFailureCode.UNAVAILABLE, "observe_checks", "provider unavailable", retry_safe=False
        )
    result = _execute_engine(application, action)
    assert result.kind == "blocked"
    assert result.reason_code == ("engine-action-interrupted" if interrupted else "engine-action-failed")
    assert result.failure.attempt_id == action.operation_id
    if interrupted:
        assert "authoritative result for this operation is unavailable" in result.failure.retry_condition
    else:
        assert "Automatic retry is unavailable for this recorded failure" in result.failure.retry_condition
    assert "release custody" in result.failure.retry_condition
    assert "start a replacement" in result.failure.retry_condition
    reopened, coordinator, _manager = _reopen_portfolio(tmp_path, state_root, {"change-a": runtime})
    assert _execute_engine(reopened, action) == result
    stopped = reopened.acquire_change_action(request)
    assert stopped.kind == "unavailable"
    assert stopped.engine_result == result
    assert stopped.failure == result.failure
    assert coordinator.show("change-a").continuation_action == action
    with pytest.raises(CoordinationConflictError, match="continuation action custody"):
        runtime.queue_explicit_checkpoint("f" * 40)
    assert provider.set_pull_request_draft_state.call_count == 0


@pytest.mark.parametrize(
    ("provider_method", "operation"),
    [("read_pull_request", "read_pull_request"), ("observe_checks", "observe_checks")],
)
def test_mark_ready_read_failure_retries_after_backoff_with_new_operation(
    tmp_path: Path, provider_method: str, operation: str
) -> None:
    now = {"value": "2026-08-04T00:00:00Z"}

    def clock() -> str:
        return now["value"]

    application, runtime, provider, state, _head, _state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False, clock=clock
    )
    action = _engine_action(application)
    getattr(provider, provider_method).side_effect = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE,
        operation,
        "provider unavailable",
        retry_safe=True,
    )

    failed = _execute_engine(application, action)

    assert failed.kind == "blocked"
    assert failed.failure.pre_effect_retryable
    assert application._coordinator.show("change-a").continuation_action.finished_at is not None
    assert application._execution_occupancy() == 0
    if provider_method == "read_pull_request":
        provider.read_pull_request.side_effect = lambda _repository, _number: state["pull_request"]
    else:
        provider.observe_checks.side_effect = None
    publisher = application._draft_pull_request_publisher
    application, _coordinator, _manager = _reopen_portfolio(
        tmp_path,
        _state_root,
        {"change-a": runtime},
        clock=clock,
    )
    application._draft_pull_request_publisher = publisher
    runtime = application._runtimes["change-a"]
    before_backoff = application.acquire_change_action(_continuation_request(application))
    assert before_backoff.kind == "waiting"
    assert before_backoff.reason_code == "retry-backoff"

    now["value"] = "2026-08-04T00:00:02Z"
    retry = application.acquire_change_action(_continuation_request(application))

    assert retry.kind == "acquired"
    assert retry.engine_action is not None
    assert retry.engine_action.operation_id != action.operation_id
    key = RetryEpisodeKey.engine(
        "change-a",
        "mark-ready",
        action.exact_head,
        action.target_head,
        action.finalization_id,
    )
    episode = runtime.retry_ledger(clock=clock).episode(key)
    assert episode is not None
    assert episode.total_attempts == 2
    completed = _execute_engine(application, retry.engine_action)
    assert completed.kind == "completed"
    assert provider.set_pull_request_draft_state.call_count == 1
    episode = runtime.retry_ledger(clock=clock).episode(key)
    assert episode is not None
    assert episode.total_attempts == 0
    assert retry.engine_action.operation_id in episode.accepted_attempt_ids
    next_action = application.acquire_change_action(_continuation_request(application))
    if next_action.kind == "reconciled":
        next_action = application.acquire_change_action(_continuation_request(application))
    assert (next_action.kind, next_action.reason_code, next_action.engine_action) == ("human", "merge-blocked", None)


def test_mark_ready_retry_exhaustion_is_non_actionable_with_diagnostic(tmp_path: Path) -> None:
    now = {"value": "2026-08-04T00:00:00Z"}
    application, _runtime, provider, _state, _head, _state_root = _awaiting_acceptance_fixture(
        tmp_path,
        mark_ready=False,
        clock=lambda: now["value"],
    )
    provider.observe_checks.side_effect = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE,
        "observe_checks",
        "provider unavailable",
        retry_safe=True,
    )

    for retry_time in (None, "2026-08-04T00:00:05Z", "2026-08-04T00:00:20Z"):
        if retry_time is not None:
            now["value"] = retry_time
        action = _engine_action(application)
        failed = _execute_engine(application, action)
        assert failed.kind == "blocked"
        assert failed.failure.pre_effect_retryable

    exhausted = application.acquire_change_action(_continuation_request(application))
    assert exhausted.kind == "unsupported"
    assert exhausted.reason_code == "retry-exhausted"
    assert exhausted.readiness.next_actor.value == "agent"
    assert exhausted.readiness.prompt is not None
    assert exhausted.readiness.prompt.startswith("/inspect-change change-a")
    assert exhausted.readiness.executable is False
    assert exhausted.readiness.operation is None
    assert exhausted.readiness.attempts == 3


@pytest.mark.parametrize(
    "journal_state",
    ["pending", "started", "invalid-intent", "mismatched-intent", "invalid-result", "mismatched-result"],
)
def test_readiness_distinguishes_retained_engine_journal_states_without_writes(  # noqa: PLR0915
    tmp_path: Path, journal_state: str
) -> None:
    repository, _runtime_root, remote, provider, application, _head_a, _head_b = _loader_composed_engine_fixture(
        tmp_path
    )
    action = _engine_action(application, "change-a")
    coordinator = application._coordinator
    intent_path = coordinator.continuation_record_path("change-a", action.operation_id)
    result_path = intent_path.with_name("result.json")
    if journal_state == "started":
        with coordinator.continuation_execution(action):
            assert coordinator.start_continuation_action(action)
    elif journal_state == "invalid-intent":
        intent_path.write_bytes(b"{")
    elif journal_state == "mismatched-intent":
        intent = ChangeContinuationAction.model_validate_json(intent_path.read_bytes())
        intent_path.write_bytes(_canonical(intent.model_copy(update={"session_id": "foreign-session"})))
    elif journal_state == "invalid-result":
        result_path.mkdir()
    elif journal_state == "mismatched-result":
        foreign_action = action.model_copy(update={"session_id": "foreign-session"})
        foreign_result = application._engine_action_failure(
            foreign_action,
            "engine-action-failed",
            "provider unavailable",
        )
        result_path.write_bytes(_canonical(foreign_result))

    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    reloaded = load_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    reloaded_runtime = reloaded._runtimes["change-a"]
    reloaded_coordinator = reloaded._coordinator
    reloaded_intent_path = reloaded_coordinator.continuation_record_path("change-a", action.operation_id)
    reloaded_started_path = reloaded_intent_path.with_name("started.json")
    reloaded_result_path = reloaded_intent_path.with_name("result.json")
    reloaded_worktree = reloaded_coordinator.show("change-a").worktree_path
    before = {
        "intent": reloaded_intent_path.read_bytes(),
        "started": reloaded_started_path.read_bytes() if reloaded_started_path.exists() else None,
        "result": reloaded_result_path.read_bytes() if reloaded_result_path.is_file() else None,
        "coordination": (reloaded_coordinator.runtime_root / "coordination/changes/change-a.json").read_bytes(),
        "frontier": reloaded_runtime.frontier_bytes(),
        "ledger": reloaded_runtime.retry_ledger().read(),
        "workspace": _workspace_mutation_snapshot(reloaded_worktree),
        "remote": _git(remote, "rev-parse", "refs/heads/owlbear/delivery-state"),
        "provider_calls": provider.draft_state_calls,
    }
    view = reloaded.get_change("change-a")
    repeated = reloaded.get_change("change-a")
    listed_items = reloaded.list_work_items()
    listed = next(item for item in listed_items if item.change_id == "change-a" and item.work_item_id == "change-a")
    shown = reloaded.show_work_item("change-a", "change-a")
    assert listed.next_action == view.detail.card.next_step
    assert shown.projection.next_action == view.detail.card.next_step
    assert "merge" not in listed.next_action.casefold()
    assert "mark" not in listed.next_action.casefold()
    assert reloaded.list_work_items() == listed_items
    assert reloaded.show_work_item("change-a", "change-a") == shown

    expected_reason = {
        "pending": "engine-action-pending",
        "started": "engine-action-interrupted",
        "invalid-intent": "engine-action-blocked",
        "mismatched-intent": "engine-action-blocked",
        "invalid-result": "engine-action-blocked",
        "mismatched-result": "engine-action-blocked",
    }[journal_state]
    assert view.readiness.reason_code == expected_reason
    assert repeated.readiness == view.readiness
    assert view.readiness.status == ("running" if journal_state == "pending" else "blocked")
    assert not view.readiness.executable
    assert view.readiness.action is None
    if journal_state == "pending":
        assert view.readiness.prompt == (
            "/continue-change change-a Resume the exact engine-selected operation after rereading readiness; "
            "do not replace it or infer closure."
        )
        assert "Delivery engine owner" in view.detail.card.next_step
        assert "unstarted exact operation" in view.detail.card.next_step
    elif journal_state == "started":
        assert view.readiness.prompt == (
            "/continue-change change-a only after the Delivery engine owner verifies host/worker closure and settles "
            "all descendant writers and jobs; preserve custody and journals, and do not retry or infer termination."
        )
        assert "Delivery engine owner" in view.detail.card.next_step
        assert "all descendant writers and jobs" in view.detail.card.next_step
    else:
        assert view.readiness.prompt == (
            "/repair-delivery Diagnose Change change-a read-only; preserve existing custody and journals. "
            "This does not repair authority or prove host/worker closure. Do not stop a worker, retry, release "
            "custody, or dispatch a replacement. The responsible owner must establish any missing authority "
            "through a supported path before Delivery can resume; this diagnostic does not supply that authority."
        )
        assert "journals cannot be verified" in view.detail.card.next_step
        assert "do not reconstruct or retry" in view.detail.card.next_step
    assert provider.draft_state_calls == before["provider_calls"]
    assert reloaded_intent_path.read_bytes() == before["intent"]
    assert (reloaded_started_path.read_bytes() if reloaded_started_path.exists() else None) == before["started"]
    assert (reloaded_result_path.read_bytes() if reloaded_result_path.is_file() else None) == before["result"]
    assert reloaded_result_path.is_dir() is (journal_state == "invalid-result")
    assert (reloaded_coordinator.runtime_root / "coordination/changes/change-a.json").read_bytes() == before[
        "coordination"
    ]
    assert reloaded_runtime.frontier_bytes() == before["frontier"]
    assert reloaded_runtime.retry_ledger().read() == before["ledger"]
    assert _workspace_mutation_snapshot(reloaded_worktree) == before["workspace"]
    assert _git(remote, "rev-parse", "refs/heads/owlbear/delivery-state") == before["remote"]
    assert provider.draft_state_calls == before["provider_calls"]


def test_readiness_projects_recorded_engine_failure_as_contained(tmp_path: Path) -> None:
    application, runtime, provider, _state, _head, state_root = _awaiting_acceptance_fixture(tmp_path, mark_ready=False)
    action = _engine_action(application)
    provider.observe_checks.side_effect = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE,
        "observe_checks",
        "provider unavailable",
        retry_safe=False,
    )
    result = _execute_engine(application, action)
    assert result.reason_code == "engine-action-failed"
    before = {
        "result": application._coordinator.continuation_record_path(
            "change-a", action.operation_id, result=True
        ).read_bytes(),
        "coordination": (state_root / "coordination/changes/change-a.json").read_bytes(),
        "frontier": runtime.frontier_bytes(),
        "ledger": runtime.retry_ledger().read(),
    }

    view = application.get_change("change-a")

    assert view.readiness.status == "blocked"
    assert view.readiness.reason_code == "engine-action-failed"
    assert not view.readiness.executable
    assert view.readiness.action is None
    assert "publication owner" in view.detail.card.next_step
    assert "provider/readback failure" in view.detail.card.next_step
    assert "provider unavailable" not in view.detail.card.next_step
    assert view.detail.card.needs_headline == view.detail.card.next_step
    assert "merge" not in view.detail.card.needs_headline.casefold()
    assert "mark-ready" not in view.detail.card.needs_headline.casefold()
    compatibility = next(item for item in application.list_work_items() if item.change_id == "change-a")
    assert compatibility.next_action == view.detail.card.next_step
    assert "merge" not in compatibility.next_action.casefold()
    assert "mark-ready" not in compatibility.next_action.casefold()
    assert application.get_change("change-a").readiness == view.readiness
    assert (
        application._coordinator.continuation_record_path("change-a", action.operation_id, result=True).read_bytes()
        == before["result"]
    )
    assert (state_root / "coordination/changes/change-a.json").read_bytes() == before["coordination"]
    assert runtime.frontier_bytes() == before["frontier"]
    assert runtime.retry_ledger().read() == before["ledger"]


def test_readiness_contains_unexecuted_acceptance_observation(tmp_path: Path) -> None:
    application, runtime, _provider, state, _head, _state_root = _awaiting_acceptance_fixture(tmp_path, mark_ready=True)
    state["pull_request"] = state["pull_request"].model_copy(
        update={
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "f" * 40,
            "merged_at": datetime(2026, 8, 3, tzinfo=UTC),
        }
    )
    application._publication_observation_cache.clear()
    action = _engine_action(application)

    assert action.kind == "observe-acceptance"
    assert runtime.ready_receipt() is not None
    assert runtime.change_stage() == DeliveryChangeStage.AWAITING_MERGE

    view = application.get_change("change-a")
    assert not view.readiness.executable
    assert "merge" not in view.detail.card.needs_headline.casefold()
    assert "mark-ready" not in view.detail.card.needs_headline.casefold()
    assert "merge" not in view.detail.card.next_step.casefold()
    assert "mark-ready" not in view.detail.card.next_step.casefold()

    compatibility = next(item for item in application.list_work_items() if item.change_id == "change-a")
    assert "merge" not in compatibility.next_action.casefold()
    assert "mark-ready" not in compatibility.next_action.casefold()
    assert "merge" not in application.show_work_item("change-a", "change-a").projection.next_action.casefold()
    assert "mark-ready" not in application.show_work_item("change-a", "change-a").projection.next_action.casefold()


@pytest.mark.parametrize("started_state", ["matching", "mismatched", "invalid"])
def test_readiness_validates_started_journal_with_recorded_result(tmp_path: Path, started_state: str) -> None:
    application, _runtime, provider, _state, _head, _state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False
    )
    action = _engine_action(application)
    provider.observe_checks.side_effect = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE,
        "observe_checks",
        "provider unavailable",
        retry_safe=False,
    )
    result = _execute_engine(application, action)
    assert result.reason_code == "engine-action-failed"
    started_path = application._coordinator.continuation_record_path("change-a", action.operation_id).with_name(
        "started.json"
    )
    if started_state == "matching":
        started_path.write_bytes(_canonical(action))
    elif started_state == "mismatched":
        started_path.write_bytes(_canonical(action.model_copy(update={"session_id": "foreign-session"})))
    else:
        started_path.write_bytes(b"{")

    view = application.get_change("change-a")

    assert view.readiness.reason_code == (
        "engine-action-failed" if started_state == "matching" else "engine-action-blocked"
    )
    assert view.readiness.status == "blocked"
    assert not view.readiness.executable
    assert view.readiness.action is None


@pytest.mark.parametrize("restart", [False, True])
def test_engine_result_transaction_recovers_without_repeating_provider(tmp_path: Path, *, restart: bool) -> None:
    application, runtime, provider, _state, _head, state_root = _awaiting_acceptance_fixture(tmp_path, mark_ready=False)
    action = _engine_action(application)
    original_commit = RuntimeTransaction.commit

    def interrupted(transaction):
        def fail(stage):
            if stage == "after-first-publication":
                message = "injected engine result interruption"
                raise RuntimeError(message)

        original_commit(
            transaction,
            failure=fail if transaction._transaction_id == f"portfolio-result-{action.operation_id}" else None,
        )

    with patch.object(RuntimeTransaction, "commit", interrupted), pytest.raises(RuntimeError, match="injected"):
        _execute_engine(application, action)
    reopened, coordinator = application, application._coordinator
    if restart:
        reopened, coordinator, _manager = _reopen_portfolio(tmp_path, state_root, {"change-a": runtime})
        assert RetryLedger(state_root, "change-a").read().episodes[0].reset_count == 1
    result = _execute_engine(reopened, action)
    assert result.kind == "completed"
    assert result.ready == runtime.ready_receipt()
    assert provider.set_pull_request_draft_state.call_count == 1
    assert coordinator.show("change-a").continuation_action.finished_at is not None
    ledger = RetryLedger(state_root, "change-a")
    episode = ledger.episode(
        RetryEpisodeKey.engine("change-a", action.kind, action.exact_head, action.target_head, action.finalization_id)
    )
    assert episode.total_attempts == 0
    assert episode.reset_count == 1
    assert episode.attempt_ids == (action.operation_id,)
    assert _execute_engine(reopened, action) == result
    assert ledger.read().episodes == (episode,)


def test_acceptance_retry_budget_never_infers_explicit_observation(tmp_path: Path) -> None:
    application, _runtime, provider, _state, _head, state_root = _awaiting_acceptance_fixture(tmp_path)
    now = datetime(2026, 8, 4, tzinfo=UTC)

    def clock():
        return now.isoformat()

    application._clock = clock
    for index, seconds in enumerate((0, 1, 3)):
        now = datetime(2026, 8, 4, tzinfo=UTC) + timedelta(seconds=seconds)
        assert application.reconcile_awaiting_acceptance(("change-a",))[0].status.value == "waiting"
        episode = RetryLedger(state_root, "change-a").read().episodes[0]
        assert episode.total_attempts == index + 1
        assert episode.explicit_observations == 0
        assert application.get_change("change-a").readiness.executable is False
        assert application.get_change("change-a").readiness.prompt is None
    calls = provider.read_pull_request.call_count
    now += timedelta(days=1)
    stopped = application.acquire_change_action(_continuation_request(application, session_id="another-session"))
    if stopped.kind == "reconciled":
        stopped = application.acquire_change_action(_continuation_request(application, session_id="another-session"))
    assert stopped.engine_action is None
    assert stopped.reason_code == "merge-blocked"
    assert provider.read_pull_request.call_count == calls
    with pytest.raises(ValidationError):
        DeliveryContinuationRequest.model_validate(
            _continuation_request(application).model_dump() | {"explicit_acceptance_observation": True}
        )


@pytest.mark.parametrize("mixed", [False, True])
def test_background_and_explicit_acceptance_share_durable_budget(tmp_path: Path, *, mixed: bool) -> None:
    application, runtime, provider, _state, _head, state_root = _awaiting_acceptance_fixture(tmp_path)
    start = datetime(2026, 8, 4, tzinfo=UTC)
    now = start

    def clock():
        return now.isoformat()

    application._clock = clock
    for index, seconds in enumerate((0, 1, 3)):
        now = start + timedelta(seconds=seconds)
        calls = provider.read_pull_request.call_count
        if mixed and index != 1:
            with pytest.raises(DeliveryAcceptanceWaitingError):
                application.observe_acceptance("change-a")
        else:
            assert application.reconcile_awaiting_acceptance(("change-a",))[0].status.value == "waiting"
        assert provider.read_pull_request.call_count == calls + 1
        snapshot = RetryLedger(state_root, "change-a").read()
        assert len(snapshot.episodes) == 1
        application.get_change("change-a")
        application.reconcile_awaiting_acceptance(("change-a",))
        assert provider.read_pull_request.call_count == calls + 1
        assert RetryLedger(state_root, "change-a").read() == snapshot
    reopened, _, _ = _reopen_portfolio(tmp_path, state_root, {"change-a": runtime})
    reopened._draft_pull_request_publisher = application._draft_pull_request_publisher
    now = start + timedelta(days=1)
    reopened._clock = clock
    request = _continuation_request(reopened)
    calls = provider.read_pull_request.call_count
    assert reopened.acquire_change_action(request).engine_action is None
    assert reopened.reconcile_awaiting_acceptance(("change-a",))[0].status.value == "waiting"
    assert provider.read_pull_request.call_count == calls
    for explicit in (1, 2):
        with pytest.raises(DeliveryAcceptanceWaitingError):
            reopened.observe_acceptance("change-a")
        assert provider.read_pull_request.call_count == calls + explicit
        episode = RetryLedger(state_root, "change-a").read().episodes[0]
        assert (episode.total_attempts, episode.explicit_observations, episode.reset_count) == (3, explicit, 0)
        assert reopened.reconcile_awaiting_acceptance(("change-a",))[0].status.value == "waiting"
        assert provider.read_pull_request.call_count == calls + explicit


def acceptance_budget_case(tmp_path: Path, *, exhausted: bool):
    """Build durable backoff/exhaustion and a fresh application for consumer tests."""
    application, runtime, provider, _state, _head, state_root = _awaiting_acceptance_fixture(tmp_path)
    now = datetime(2026, 8, 4, tzinfo=UTC)

    def clock():
        return now.isoformat()

    application._clock = clock
    for delay in (0, 1, 2) if exhausted else (0,):
        now += timedelta(seconds=delay)
        calls = provider.read_pull_request.call_count
        assert application.reconcile_awaiting_acceptance(("change-a",))[0].status.value == "waiting"
        assert provider.read_pull_request.call_count == calls + 1
    if exhausted:
        now += timedelta(days=1)

    def restart():
        reopened, _, _ = _reopen_portfolio(tmp_path, state_root, {"change-a": runtime}, clock=clock)
        reopened._draft_pull_request_publisher = application._draft_pull_request_publisher
        return reopened

    return application, provider, RetryLedger(state_root, "change-a"), restart


def test_acceptance_completion_reconciles_accounting_without_observing_again(tmp_path: Path) -> None:
    application, runtime, provider, state, _head, state_root = _awaiting_acceptance_fixture(tmp_path)
    ledger = RetryLedger(state_root, "change-a")
    other_key = RetryEpisodeKey.engine(
        "change-a", "observe-acceptance", _head, "d" * 40, runtime.finalization().finalization_id
    )
    ledger.reserve(other_key, failure_class="acceptance", now=application._clock(), attempt_id="other-target")
    state["pull_request"] = state["pull_request"].model_copy(
        update={
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "f" * 40,
            "merged_at": datetime(2026, 8, 3, 14, tzinfo=UTC),
            "merged_by_login": "octocat",
        }
    )
    with (
        patch.object(RetryLedger, "record_accepted_progress", side_effect=OSError("injected accounting failure")),
        pytest.raises(OSError, match="injected accounting"),
    ):
        application.observe_acceptance("change-a")
    calls = provider.read_pull_request.call_count
    assert runtime.completion_receipt() is not None
    _reopen_portfolio(tmp_path, state_root, {"change-a": runtime})
    episode = next(item for item in ledger.read().episodes if item.key != other_key)
    assert episode.reset_count == 1
    assert episode.total_attempts == 0
    assert ledger.episode(other_key).reset_count == 0
    assert ledger.episode(other_key).total_attempts == 1
    assert ledger.episode(other_key).last_status == "reserved"
    assert provider.read_pull_request.call_count == calls


def test_readiness_uses_budgeted_acceptance_evidence_without_observing_again(tmp_path: Path) -> None:
    application, _runtime, provider, state, _head, state_root = _awaiting_acceptance_fixture(tmp_path)
    state["pull_request"] = state["pull_request"].model_copy(update={"mergeable": False, "merge_state_status": "dirty"})
    application.reconcile_awaiting_acceptance(("change-a",))
    calls = provider.read_pull_request.call_count
    ledger = RetryLedger(state_root, "change-a")
    before = ledger.read()
    detail = application.show_work_item_view("change-a", "publication")
    assert detail.publication.mergeable is False
    assert detail.publication.merge_state_status == "dirty"
    application.get_change("change-a")
    assert provider.read_pull_request.call_count == calls
    assert ledger.read() == before


@pytest.mark.parametrize("count", [1, 2, 3])
@pytest.mark.parametrize("clear_legacy_block", [False, True])
def test_worker_legacy_budget_is_imported_before_dispatch(
    tmp_path: Path, count: int, *, clear_legacy_block: bool
) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    runtime = runtimes["change-a"]
    frontier = json.loads(runtime.frontier_bytes())
    frontier["bindings"][0].update(retry_count=count, retry_fingerprint="a" * 64)
    if clear_legacy_block:
        frontier["bindings"][0]["block"] = {
            "block_id": "legacy-retry-budget",
            "reason": "Legacy failure",
            "unblock_condition": "Prerequisite restored",
            "expected_evidence": ["restored"],
            "locators": ["check"],
        }
    runtime._frontier_path.write_text(json.dumps(frontier))
    if clear_legacy_block:
        application.clear_block("change-a", "OUT-001", "legacy-retry-budget", "Restored", ("check",))
        assert runtime.show_binding("OUT-001").retry_count == count
        assert RetryLedger(state_root, "change-a").read().episodes[0].legacy_failures == count
    first = application.acquire_change_action(_continuation_request(application))
    if first.kind == "reconciled":
        first = application.acquire_change_action(_continuation_request(application))
    assert first.launch is None
    assert first.reason_code == ("retry-backoff" if count < 3 else "retry-exhausted")
    assert first.readiness.attempts == count
    assert first.failure is None
    if count == 3:
        assert first.readiness.next_actor.value == "agent"
        assert first.readiness.prompt is not None
        assert first.readiness.prompt.startswith("/inspect-change change-a")
        assert first.readiness.executable is False
        assert first.readiness.operation is None
    episode = RetryLedger(state_root, "change-a").read().episodes[0]
    assert episode.total_attempts == count
    assert episode.legacy_failures == count
    reopened, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes, clock=lambda: "2030-01-01T00:00:00Z")
    acquired = reopened.acquire_change_action(_continuation_request(reopened))
    assert (acquired.launch is not None) is (count < 3)
    assert RetryLedger(state_root, "change-a").read().episodes[0].total_attempts == min(count + 1, 3)


@pytest.mark.parametrize("crash_stage", ["before-publication", "after-first-publication", "before-manifest-cleanup"])
def test_planner_accepted_retry_reconciles_without_caller_replay(tmp_path: Path, crash_stage: str) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    launch = application.acquire_change_action(_continuation_request(application)).launch
    candidate = application.publish_delivery_plan(
        "change-a", PublishDeliveryPlan(outcome_id=launch.outcome_id, claim_id=launch.claim.claim_id, tasks=(_task(),))
    )
    original = RuntimeTransaction.commit

    def interrupted(transaction):
        def fail(stage):
            if stage == crash_stage:
                message = "injected owner interruption"
                raise OSError(message)

        original(transaction, failure=fail)

    with patch.object(RuntimeTransaction, "commit", interrupted), pytest.raises(OSError, match="injected"):
        application.transition_delivery(
            "change-a",
            AdvanceDelivery(
                action="advance", outcome_id=launch.outcome_id, claim_id=launch.claim.claim_id, output=candidate.output
            ),
        )
    _reopen_portfolio(tmp_path, state_root, runtimes)
    episode = RetryLedger(state_root, "change-a").read().episodes[0]
    assert episode.total_attempts == 0
    assert episode.reset_count == 1
    assert episode.accepted_attempt_ids == (launch.claim.attempt_id,)


def test_legacy_active_claim_is_imported_before_accepted_advance_clears_counters(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    runtime = runtimes["change-a"]
    launch = application.acquire_change_action(_continuation_request(application)).launch
    shutil.rmtree(state_root / "changes/change-a/retry-ledger")
    frontier = json.loads(runtime.frontier_bytes())
    frontier["bindings"][0].update(retry_count=2, retry_fingerprint="a" * 64)
    runtime._frontier_path.write_text(json.dumps(frontier))
    candidate = application.publish_delivery_plan(
        "change-a", PublishDeliveryPlan(outcome_id=launch.outcome_id, claim_id=launch.claim.claim_id, tasks=(_task(),))
    )
    with patch.object(RetryLedger, "record_accepted_progress", side_effect=OSError("interrupted accounting")):
        application.transition_delivery(
            "change-a",
            AdvanceDelivery(
                action="advance", outcome_id=launch.outcome_id, claim_id=launch.claim.claim_id, output=candidate.output
            ),
        )
    ledger = RetryLedger(state_root, "change-a")
    imported = ledger.read().episodes[0]
    assert imported.legacy_failures == 2
    assert imported.total_attempts == 3
    assert imported.attempt_ids == (launch.claim.attempt_id,)
    assert runtime.show_binding("OUT-001").retry_count == 0
    _reopen_portfolio(tmp_path, state_root, runtimes)
    accepted = ledger.read().episodes[0]
    assert (accepted.legacy_failures, accepted.total_attempts, accepted.reset_count) == (2, 0, 1)


@pytest.mark.parametrize("batch", [False, True])
def test_worker_budget_survives_resolved_blocks_and_leaves_sibling_runnable(tmp_path: Path, *, batch: bool) -> None:
    now = datetime(2026, 8, 4, tzinfo=UTC)

    def clock():
        return now.isoformat()

    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING},
        clock=clock,
        execution_capacity=1,
    )
    for index, seconds in enumerate((0, 1, 3)):
        now = datetime(2026, 8, 4, tzinfo=UTC) + timedelta(seconds=seconds)
        acquired = application.acquire_change_action(_continuation_request(application))
        if acquired.kind == "reconciled":
            acquired = application.acquire_change_action(_continuation_request(application))
        assert acquired.launch is not None, acquired
        application.transition_delivery(
            "change-a",
            BlockDelivery(
                action="block",
                outcome_id="OUT-001",
                claim_id=acquired.launch.claim.claim_id,
                block_id=f"block-{index}",
                reason=f"Changed failure prose {index}",
                unblock_condition="Procedure available",
                expected_evidence=("procedure",),
                locators=("TASK-001",),
            ),
        )
        application.clear_block("change-a", "OUT-001", f"block-{index}", "Prerequisite available", ("procedure",))
        ledger = RetryLedger(state_root, "change-a")
        assert len(ledger.read().episodes) == 1
        assert ledger.read().episodes[0].total_attempts == index + 1
        assert not application.get_change("change-a").readiness.executable
    reopened, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes, clock=clock, execution_capacity=1)
    assert reopened.get_change("change-a").readiness.reason_code == "retry-exhausted"
    assert reopened.get_change("change-a").readiness.next_actor.value == "agent"
    assert reopened.get_change("change-a").readiness.prompt is not None
    assert reopened.get_change("change-a").readiness.prompt.startswith("/inspect-change change-a")
    assert reopened.acquire_change_action(_continuation_request(reopened)).launch is None
    if batch:
        acquired = reopened.acquire_frontier_work()
        assert len(acquired.launch_packages) == 1
        assert acquired.launch_packages[0].change_id == "change-b"
    else:
        sibling = reopened.acquire_change_action(_continuation_request(reopened, "change-b"))
        assert sibling.launch is not None
        assert sibling.launch.change_id == "change-b"


def test_batch_corrupt_retry_ledger_does_not_block_independent_change(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING},
        execution_capacity=2,
    )
    summary_path = RetryLedger(state_root, "change-a").summary_path
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_bytes(b"{")
    frontier_before = runtimes["change-a"].frontier_bytes()
    coordination_before = coordinator.show("change-a")

    acquired = application.acquire_frontier_work()

    assert [package.change_id for package in acquired.launch_packages] == ["change-b"]
    failures = [failure for failure in acquired.failures if failure.change_id == "change-a"]
    assert len(failures) == 1
    assert failures[0].code == "ERR_DELIVERY_RUNTIME_RECONCILIATION"
    assert failures[0].claim_id is None
    assert "{" not in failures[0].detail
    assert not any(failure.change_id == "portfolio" for failure in acquired.failures)
    assert runtimes["change-a"].frontier_bytes() == frontier_before
    assert runtimes["change-a"].active_claims() == ()
    assert coordinator.show("change-a") == coordination_before
    assert summary_path.read_bytes() == b"{"
    assert runtimes["change-b"].active_claims()[0][1] == acquired.launch_packages[0].claim


def test_batch_retry_reservation_conflict_does_not_block_independent_change(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING},
        execution_capacity=2,
    )
    reserve = application._reserve_worker_attempt
    frontier_before = runtimes["change-a"].frontier_bytes()
    coordination_before = coordinator.show("change-a")

    def conflict_change_a(candidate, *args):
        if candidate.change_id == "change-a":
            message = "concurrent retry writer"
            raise RetryLedgerConflictError(message)
        return reserve(candidate, *args)

    with patch.object(application, "_reserve_worker_attempt", side_effect=conflict_change_a):
        acquired = application.acquire_frontier_work()

    assert [package.change_id for package in acquired.launch_packages] == ["change-b"]
    failures = [failure for failure in acquired.failures if failure.change_id == "change-a"]
    assert len(failures) == 1
    assert failures[0].code == "ERR_DELIVERY_RETRY_LEDGER_CONFLICT"
    assert "concurrent retry writer" not in failures[0].detail
    assert runtimes["change-a"].frontier_bytes() == frontier_before
    assert runtimes["change-a"].active_claims() == ()
    assert coordinator.show("change-a") == coordination_before


def test_batch_worker_backoff_reports_backoff_not_exhaustion(tmp_path: Path) -> None:
    current_time = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, clock=lambda: current_time[0]
    )
    with (
        patch.object(runtimes["change-a"], "activate_claim", side_effect=OSError("interrupted owner publication")),
        pytest.raises(OSError, match="interrupted owner"),
    ):
        application.acquire_change_action(_continuation_request(application))
    ledger = RetryLedger(state_root, "change-a")
    before = ledger.read().episodes[0]
    assert before.last_status == "failed"
    assert before.next_eligible_at == "2026-08-04T00:00:01Z"

    acquired = application.acquire_frontier_work()

    assert acquired.launch_packages == ()
    failures = [failure for failure in acquired.failures if failure.change_id == "change-a"]
    assert len(failures) == 1
    assert failures[0].code == "ERR_DELIVERY_RETRY_BACKOFF"
    assert "exhaust" not in failures[0].detail.lower()
    assert ledger.read().episodes[0].total_attempts == before.total_attempts
    assert runtimes["change-a"].active_claims() == ()
    assert coordinator.show("change-a").writer is None


def _acquire_planning_claim(application: PortfolioApplication) -> DeliveryActiveClaim:
    acquired = application.acquire_change_action(_continuation_request(application))
    if acquired.kind == "reconciled":
        acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.launch is not None, acquired
    return acquired.launch.claim


def _planning_decision_block(claim_id: str, index: int) -> BlockDelivery:
    return BlockDelivery(
        action="block",
        outcome_id="OUT-001",
        claim_id=claim_id,
        block_id=f"decision-block-{index}",
        reason="Planning needs a user decision",
        unblock_condition="User selects an option",
        expected_evidence=("user answer",),
        locators=("SCOPE-001",),
        request=DeliveryRequest(
            request_id=f"decision-{index}",
            kind=DeliveryRequestKind.DECISION,
            outcome_id="OUT-001",
            summary="Choose the planning direction",
            options=(DeliveryRequestOption(option_id="proceed", label="Proceed"),),
        ),
    )


def _fail_planning_attempt(application: PortfolioApplication, index: int) -> None:
    claim = _acquire_planning_claim(application)
    application.transition_delivery(
        "change-a",
        BlockDelivery(
            action="block",
            outcome_id="OUT-001",
            claim_id=claim.claim_id,
            block_id=f"failure-{index}",
            reason="Planning procedure failed",
            unblock_condition="Procedure available",
            expected_evidence=("procedure",),
            locators=("SCOPE-001",),
        ),
    )
    application.clear_block("change-a", "OUT-001", f"failure-{index}", "Procedure available", ("procedure",))
    reconciled = application.acquire_change_action(_continuation_request(application))
    assert reconciled.kind == "reconciled"
    assert reconciled.launch is None


@pytest.mark.parametrize("prior_failures", [0, 1, 2])
def test_planning_decisions_suspend_retry_budget_across_restart(tmp_path: Path, prior_failures: int) -> None:
    now = datetime(2026, 8, 4, tzinfo=UTC)

    def clock() -> str:
        return now.isoformat()

    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, clock=clock
    )
    ledger = RetryLedger(state_root, "change-a")
    for index in range(prior_failures):
        _fail_planning_attempt(application, index)
        waiting = application.acquire_change_action(_continuation_request(application))
        assert waiting.launch is None
        assert waiting.reason_code == "retry-backoff"
        now += timedelta(seconds=index + 1)
    prior = ledger.read().episodes[0] if prior_failures else None
    history = {
        path: path.read_bytes()
        for directory in ("attempts", "outcomes", "owner-results")
        for path in (ledger.summary_path.parent / directory).glob("*.json")
    }
    episode_id = prior.episode_id if prior else None
    for index in range(3):
        claim = _acquire_planning_claim(application)
        application.transition_delivery("change-a", _planning_decision_block(claim.claim_id, index))
        application, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes, clock=clock)
        now += timedelta(seconds=10)
        assert application.acquire_change_action(_continuation_request(application)).launch is None
        assert application.acquire_change_action(_continuation_request(application)).launch is None
        assert application.acquire_frontier_work().launch_packages == ()
        application.answer(
            DeliveryAnswer(
                change_id="change-a",
                kind=DeliveryAnswerKind.REQUEST,
                expected_frontier_digest=hashlib.sha256(runtimes["change-a"].frontier_bytes()).hexdigest(),
                request_id=f"decision-{index}",
                resolution=DeliveryRequestResolution(selected_option_id="proceed", provenance="user-confirmed"),
            ),
        )
        episode = ledger.read().episodes[0]
        episode_id = episode_id or episode.episode_id
        assert episode.episode_id == episode_id
        assert (episode.total_attempts, episode.repair_attempts, episode.reset_count) == (
            prior_failures,
            max(0, prior_failures - 1),
            0,
        )
        assert episode.accepted_attempt_ids == ()
        assert len(episode.attempt_ids) == prior_failures + index + 1
        assert len(ledger.read().episodes) == 1
        assert episode.last_failure_at == (prior.last_failure_at if prior else None)
        assert episode.next_eligible_at == (prior.next_eligible_at if prior else None)
        assert all(path.read_bytes() == content for path, content in history.items())
    for index in range(prior_failures, 3):
        _fail_planning_attempt(application, index)
        stopped = application.acquire_change_action(_continuation_request(application))
        assert stopped.launch is None
        assert stopped.reason_code == ("retry-exhausted" if index == 2 else "retry-backoff")
        assert stopped.readiness.attempts == index + 1
        now += timedelta(seconds=2)
    application, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes, clock=clock)
    assert application.get_change("change-a").readiness.reason_code == "retry-exhausted"
    assert application.get_change("change-a").readiness.next_actor.value == "agent"
    assert application.get_change("change-a").readiness.prompt is not None
    assert application.get_change("change-a").readiness.prompt.startswith("/inspect-change change-a")


@pytest.mark.parametrize(
    ("disposition", "failure_code"),
    [
        ("normal-return", "worker-retry"),
        ("completed-timeout", "worker-timeout"),
        ("ended-without-result", "worker-ended-without-result"),
    ],
)
def test_settled_planner_retries_exhaust_after_three_exact_attempts(
    tmp_path: Path,
    disposition: str,
    failure_code: str,
) -> None:
    now = datetime(2026, 8, 4, tzinfo=UTC)

    def clock() -> str:
        return now.isoformat()

    application, _runtimes, _coordinator, state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, clock=clock
    )
    for index, elapsed in enumerate((0, 1, 3)):
        now = datetime(2026, 8, 4, tzinfo=UTC) + timedelta(seconds=elapsed)
        acquired = application.acquire_actions()
        assert len(acquired.launch_packages) == 1
        claim = acquired.launch_packages[0].claim
        request = (
            RetryDelivery(
                action="retry",
                outcome_id="OUT-001",
                claim_id=claim.claim_id,
                failure_code=failure_code,
            )
            if disposition == "normal-return"
            else None
        )
        settlement = DeliveryPlanningRetrySettlement(
            change_id="change-a",
            outcome_id="OUT-001",
            claim_id=claim.claim_id,
            attempt_id=claim.attempt_id,
            disposition=disposition,
            request=request,
        )

        settled = application.settle_worker_invocation(
            settlement,
            host_id="ignored-host",
            session_id="ignored-session",
        )

        assert settled.active_claim is None
        episode = RetryLedger(state_root, "change-a").read().episodes[0]
        assert episode.total_attempts == index + 1
        assert episode.reset_count == 0
        assert episode.attempt_ids[-1] == claim.attempt_id
        owner_result_path = state_root / "changes/change-a/retry-ledger/owner-results" / f"{claim.attempt_id}.json"
        assert json.loads(owner_result_path.read_text(encoding="utf-8"))["failure_code"] == failure_code
        if index < 2:
            assert application.get_change("change-a").readiness.reason_code == "retry-backoff"
    readiness = application.get_change("change-a").readiness
    assert readiness.reason_code == "retry-exhausted"
    assert readiness.next_actor.value == "agent"
    assert readiness.prompt is not None
    assert readiness.prompt.startswith("/inspect-change change-a")
    view = application.show_work_item_view("change-a", "outcome:OUT-001")
    assert view.card.next_actor.value == "agent"
    assert view.card.action.kind.value == "none"
    assert "Planner" in view.card.next_step
    assert application.acquire_actions().launch_packages == ()
    assert RetryLedger(state_root, "change-a").read().episodes[0].total_attempts == 3


def test_planner_settlement_replay_does_not_publish_unrelated_pending_state(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    claim = _acquire_planning_claim(application)
    settlement = DeliveryPlanningRetrySettlement(
        change_id="change-a",
        outcome_id="OUT-001",
        claim_id=claim.claim_id,
        attempt_id=claim.attempt_id,
        disposition="normal-return",
        request=RetryDelivery(action="retry", outcome_id="OUT-001", claim_id=claim.claim_id),
    )
    publisher = Mock()
    application._delivery_state_publisher = publisher
    settled = application.settle_worker_invocation(settlement, host_id=claim.owner_id, session_id=claim.process_id)
    publisher.publish.assert_called_once()
    publisher.reset_mock()
    runtime = runtimes["change-a"]
    runtime.queue_explicit_checkpoint(application._workspace_manager.show("change-a").last_reviewed_commit)
    frontier = runtime.frontier_bytes()
    accounting = runtime.retry_ledger().read()
    pending = runtime.pending_state_publication()
    assert pending is not None
    assert application.settle_worker_invocation(settlement) == settled
    assert runtime.frontier_bytes() == frontier
    assert runtime.retry_ledger().read() == accounting
    assert runtime.pending_state_publication() == pending
    publisher.publish.assert_not_called()


def test_planner_settlement_replays_its_own_failed_publication(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
        clock=lambda: "2026-08-04T05:06:07Z",
    )
    claim = _acquire_planning_claim(application)
    settlement = DeliveryPlanningRetrySettlement(
        change_id="change-a",
        outcome_id="OUT-001",
        claim_id=claim.claim_id,
        attempt_id=claim.attempt_id,
        disposition="normal-return",
        request=RetryDelivery(action="retry", outcome_id="OUT-001", claim_id=claim.claim_id),
    )
    runtime = runtimes["change-a"]
    frontier_before_wrong_owner = runtime.frontier_bytes()
    ledger_before_wrong_owner = runtime.retry_ledger().read()
    publisher = Mock()
    publisher.publish.side_effect = [OSError("synthetic publication unavailable"), None]
    application._delivery_state_publisher = publisher
    for host_id, session_id in (
        ("foreign-host", claim.process_id),
        (claim.owner_id, "foreign-session"),
    ):
        with pytest.raises(PortfolioApplicationError, match="host and session binding"):
            application.settle_worker_invocation(settlement, host_id=host_id, session_id=session_id)
        assert runtime.frontier_bytes() == frontier_before_wrong_owner
        assert runtime.retry_ledger().read() == ledger_before_wrong_owner
        publisher.publish.assert_not_called()
    with pytest.raises(OSError, match="synthetic publication unavailable"):
        application.settle_worker_invocation(settlement, host_id=claim.owner_id, session_id=claim.process_id)
    frontier = runtime.frontier_bytes()
    accounting = runtime.retry_ledger().read()
    pending = runtime.pending_state_publication()
    assert pending is not None
    assert pending.transition_request_digest == hashlib.sha256(_canonical(settlement)).hexdigest()
    publisher.read_snapshot_inventory.return_value = Mock(
        remote_head="a" * 40,
        snapshots=(Mock(change_id="change-a", frontier=DeliveryFrontier.model_validate_json(frontier, strict=True)),),
    )
    result = application.settle_worker_invocation(settlement, host_id=claim.owner_id, session_id=claim.process_id)
    assert result.active_claim is None
    owner_result_path = (
        runtime._target_root / "changes/change-a/retry-ledger/owner-results" / f"{claim.attempt_id}.json"
    )
    assert json.loads(owner_result_path.read_bytes())["observed_at"] == application._clock()
    assert runtime.frontier_bytes() == frontier
    assert runtime.retry_ledger().read() == accounting
    assert runtime.pending_state_publication() is None
    assert publisher.publish.call_count == 2


def _builder_retry_handoff_setup(
    tmp_path: Path,
    now: list[str],
    *,
    include_independent: bool = False,
    add_workspace_changes: bool = True,
    publish_initial_state: bool = False,
):
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION, "change-b": DeliveryStage.PLANNING},
        execution_capacity=1,
        clock=lambda: now[0],
        include_independent=include_independent,
    )
    if publish_initial_state:
        repository = application._workspace_manager.repository
        _attach_local_target(application, tmp_path)
        application._delivery_state_publisher = DeliveryStatePublisher(
            repository,
            remote="origin",
            state_branch="owlbear/delivery-state",
        )
        assert (
            application._publish_delivery_state(
                "change-a",
                runtimes["change-a"],
                "builder-handoff-baseline",
            )
            is not None
        )
    first_result = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert first_result.launch is not None
    first = first_result.launch
    assert first.task_id == "TASK-001"
    blocked_sibling = application.acquire_change_action(_continuation_request(application, "change-b"))
    assert blocked_sibling.kind == "waiting"
    assert blocked_sibling.reason_code == "execution-capacity"

    if add_workspace_changes:
        committed_file = first.worktree_path / "committed.txt"
        committed_file.write_text("committed Builder work\n", encoding="utf-8")
        _git(first.worktree_path, "add", committed_file.name)
        _git(first.worktree_path, "commit", "-m", "preserve Builder commit")
        branch_head = _git(first.worktree_path, "rev-parse", "HEAD")
        product = first.worktree_path / "product.txt"
        product.write_text("staged Builder work\n", encoding="utf-8")
        _git(first.worktree_path, "add", product.name)
        product.write_text("unstaged Builder work\n", encoding="utf-8")
        untracked_file = first.worktree_path / "untracked.txt"
        untracked_file.write_text("untracked Builder work\n", encoding="utf-8")
    else:
        branch_head = _git(first.worktree_path, "rev-parse", "HEAD")
    before_workspace = _workspace_content_snapshot(first.worktree_path)
    retry = RetryDelivery(
        action="retry",
        outcome_id=first.outcome_id,
        claim_id=first.claim.claim_id,
        attempt_id=first.claim.attempt_id,
        abandoned_commit=branch_head,
        failure_code="builder-failed",
    )
    settlement = DeliveryBuilderInvocationSettlement(
        change_id=first.change_id,
        outcome_id=first.outcome_id,
        claim_id=first.claim.claim_id,
        attempt_id=first.claim.attempt_id,
        task_id=first.task_id,
        expected_last_reviewed_commit=first.last_reviewed_commit,
        disposition="normal-return",
        request=retry,
    )
    return application, runtimes["change-a"], coordinator, state_root, first, branch_head, before_workspace, settlement


def _settle_builder_handoff_attempt(
    application: PortfolioApplication,
    claim: DeliveryActiveClaim,
    settlement: DeliveryBuilderInvocationSettlement,
) -> OutcomeAuthorityBinding:
    return application.settle_worker_invocation(
        settlement,
        host_id=claim.owner_id,
        session_id=claim.process_id,
    )


def _seed_two_task_builder(application, runtimes, coordinator, state_root):
    completed_task = _task()
    original_task = completed_task.model_copy(
        update={
            "task_id": "TASK-002",
            "title": "Implement the retained task",
            "result": "One bounded implementation after Planning repair.",
            "dependency_ids": ("TASK-001",),
        }
    )
    for change_id, runtime in runtimes.items():
        frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
        completed_result = _task_result(
            "RESULT-001",
            change_id,
            runtime.authority_digest,
            completed_task,
            coordinator.show(change_id).last_reviewed_commit,
        )
        bindings = []
        for binding in frontier.bindings:
            if change_id == "change-a" and binding.outcome_id == "OUT-001":
                update = {
                    "stage": DeliveryStage.IMPLEMENTATION,
                    "tasks": (completed_task, original_task),
                    "results": (completed_result,),
                }
            else:
                update = {"stage": DeliveryStage.PLANNING, "tasks": (), "results": ()}
            bindings.append(
                binding.model_copy(
                    update={
                        **update,
                        "active_claim": None,
                        "output": None,
                        "candidate": None,
                        "result_candidate": None,
                        "return_context": None,
                        "builder_handoff_context": None,
                        "block": None,
                        "recovery_attention": None,
                        "retry_diagnostic": None,
                    }
                )
            )
        seeded = DeliveryFrontier.model_validate_json(
            _canonical(frontier.model_copy(update={"bindings": tuple(bindings)})),
            strict=True,
        )
        path = state_root / "changes" / change_id / "frontier.json"
        path.write_bytes(_canonical(seeded))
        runtime.bindings()
    first_result = runtimes["change-a"].show_binding("OUT-001").results[0]
    builder_result = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert builder_result.launch is not None, builder_result
    builder = builder_result.launch
    assert builder.task_id == original_task.task_id
    return completed_task, original_task, first_result, builder


def _return_builder(application, builder, *, target: DeliveryStage = DeliveryStage.PLANNING, unmerged: bool = False):
    committed = builder.worktree_path / "preserved-builder-commit.txt"
    committed.write_text("committed Builder bytes\n", encoding="utf-8")
    _git(builder.worktree_path, "add", committed.name)
    _git(builder.worktree_path, "commit", "-m", "preserve Builder commit")
    branch_head = _git(builder.worktree_path, "rev-parse", "HEAD")
    staged = builder.worktree_path / "staged.txt"
    staged.write_text("staged Builder bytes\n", encoding="utf-8")
    _git(builder.worktree_path, "add", staged.name)
    product = builder.worktree_path / "product.txt"
    product.write_text("unstaged Builder bytes\n", encoding="utf-8")
    untracked = builder.worktree_path / "untracked.txt"
    untracked.write_text("untracked Builder bytes\n", encoding="utf-8")
    if unmerged:
        blob = _git(builder.worktree_path, "hash-object", "-w", untracked.name)
        subprocess.run(  # noqa: S603
            ("git", "-C", str(builder.worktree_path), "update-index", "--index-info"),  # noqa: S607
            input="".join(f"100644 {blob} {stage}\tconflicted.txt\n" for stage in (1, 2, 3)),
            check=True,
            text=True,
        )
        (builder.worktree_path / "conflicted.txt").write_text("conflicted Builder bytes\n", encoding="utf-8")
    before_workspace = _workspace_content_snapshot(builder.worktree_path)
    reason = (
        "The admitted Design lacks the premise for the retained task."
        if target is DeliveryStage.DESIGN
        else "The retained task needs a clearer implementation boundary."
    )
    locators = ("design.md",) if target is DeliveryStage.DESIGN else (builder.task_id,)
    request = ReturnDelivery(
        action="return",
        outcome_id=builder.outcome_id,
        claim_id=builder.claim.claim_id,
        target=target,
        reason=reason,
        locators=locators,
        preserved_commit=branch_head,
        attempt_id=builder.claim.attempt_id,
    )
    settlement = DeliveryBuilderInvocationSettlement(
        change_id=builder.change_id,
        outcome_id=builder.outcome_id,
        claim_id=builder.claim.claim_id,
        attempt_id=builder.claim.attempt_id,
        task_id=builder.task_id,
        expected_last_reviewed_commit=builder.last_reviewed_commit,
        disposition="normal-return",
        request=request,
    )
    settled = application.settle_worker_invocation(
        settlement,
        host_id=builder.claim.owner_id,
        session_id=builder.claim.process_id,
    )
    return settled, branch_head, before_workspace, reason


def _assert_returned_planner_handoff(
    application,
    builder,
    settled: OutcomeAuthorityBinding,
    before_workspace,
) -> None:
    runtime = application._runtimes["change-a"]
    coordinator = application._coordinator
    handoff = coordinator.show("change-a").builder_handoff
    completed_task, original_task = settled.tasks
    assert settled.stage == DeliveryStage.PLANNING
    assert settled.results == (runtime.show_binding("OUT-001").results[0],)
    assert settled.return_context is not None
    assert settled.return_context.reason == "The retained task needs a clearer implementation boundary."
    assert settled.return_context.preserved_commit == handoff.branch_head
    assert settled.return_context.completed_boundary == builder.last_reviewed_commit
    assert settled.builder_handoff_context is not None
    assert settled.builder_handoff_context.route == "same-outcome-planner"
    assert settled.builder_handoff_context.original_task_commitment_ids == original_task.commitment_ids
    assert settled.builder_handoff_context.original_task_maintained_surfaces == original_task.maintained_surfaces
    assert handoff is not None
    assert handoff.original_task_id == original_task.task_id
    assert handoff.branch_head == settled.builder_handoff_context.branch_head
    assert _workspace_content_snapshot(builder.worktree_path) == before_workspace
    assert runtime.claimable_outcome_ids() == ("OUT-001",)

    before_frontier = runtime.frontier_bytes()
    before_coordination = coordinator.show("change-a")
    before_ledger = runtime.retry_ledger().read()
    with pytest.raises(DeliveryActionSelectionConflictError, match="selected action"):
        application.acquire_actions(
            DeliveryActionSelection(
                change_id="change-a",
                outcome_id="OUT-002",
                expected_stage=DeliveryStage.PLANNING,
                expected_frontier_digest=hashlib.sha256(before_frontier).hexdigest(),
                expected_source_head=handoff.branch_head,
            )
        )
    assert runtime.frontier_bytes() == before_frontier
    assert coordinator.show("change-a") == before_coordination
    assert runtime.retry_ledger().read() == before_ledger
    assert _workspace_content_snapshot(builder.worktree_path) == before_workspace
    assert completed_task.task_id == settled.results[0].task_id


def _assert_returned_handoff_metadata_fences(application, builder, before_workspace) -> None:
    runtime = application._runtimes["change-a"]
    coordinator = application._coordinator
    before_frontier = runtime.frontier_bytes()
    before_coordination = coordinator.show("change-a")
    before_ledger = runtime.retry_ledger().read()
    builder_episode = runtime.retry_ledger().episode_for_attempt(builder.claim.attempt_id)
    assert builder_episode is not None
    assert builder_episode.key.exact_head == builder.last_reviewed_commit
    assert builder_episode.total_attempts == 1
    assert builder_episode.reset_count == 0
    retained_metadata = application._workspace_manager._capture_builder_handoff_metadata(before_coordination)
    stale_metadata = replace(retained_metadata, status_digest="0" * 64)
    with patch.object(
        application._workspace_manager,
        "_capture_builder_handoff_metadata",
        return_value=stale_metadata,
    ):
        result = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert result.kind == "unavailable"
    assert result.reason_code == "source-unavailable"
    assert result.launch is None
    assert runtime.frontier_bytes() == before_frontier
    assert runtime.retry_ledger().read() == before_ledger
    assert coordinator.show("change-a") == before_coordination
    assert _workspace_content_snapshot(builder.worktree_path) == before_workspace
    assert runtime.active_claims() == ()

    with (
        patch.object(
            application._workspace_manager,
            "_capture_builder_handoff_metadata",
            side_effect=(retained_metadata, stale_metadata),
        ),
        pytest.raises(PreservationFenceError, match="metadata changed before source preparation"),
    ):
        application.acquire_change_action(_continuation_request(application, "change-a"))
    assert runtime.active_claims() == ()
    assert coordinator.show("change-a") == before_coordination
    ledger_after = runtime.retry_ledger()
    assert ledger_after.episode_for_attempt(builder.claim.attempt_id) == builder_episode
    assert ledger_after.pending_attempts() == ()
    assert _workspace_content_snapshot(builder.worktree_path) == before_workspace


def _acquire_returned_planner(application, builder, before_workspace):
    runtime = application._runtimes["change-a"]
    coordinator = application._coordinator
    binding = runtime.show_binding("OUT-001")
    handoff = coordinator.show("change-a").builder_handoff
    result = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert result.launch is not None, (result.reason_code, result.failure)
    planner = result.launch
    assert planner.claim.worker_role is DeliveryWorkerRole.PLANNER
    assert planner.task_id is None
    assert planner.writer is None
    assert planner.source_head == handoff.branch_head
    assert planner.worktree_path == builder.worktree_path
    context = application.show_plan_context(
        "change-a", planner.outcome_id, planner.claim.attempt_id, planner.claim.claim_id
    )
    assert context.return_context is not None
    assert context.return_context.reason == binding.return_context.reason
    assert context.return_context.preserved_commit == handoff.branch_head
    assert context.launch.builder_handoff_context == binding.builder_handoff_context
    assert context.launch.writer is None
    assert _workspace_content_snapshot(builder.worktree_path) == before_workspace
    assert coordinator.show("change-a").builder_handoff == handoff
    assert coordinator.show("change-a").writer == handoff.original_writer.model_copy(update={"kind": "handoff"})
    sibling = application.acquire_change_action(_continuation_request(application, "change-b"))
    assert sibling.kind == "waiting"
    assert sibling.reason_code == "execution-capacity"
    assert application._runtimes["change-b"].active_claims() == ()
    assert coordinator.show("change-b").writer is None
    return planner


def _assert_return_plan_rejected(application, planner, tasks, message: str, claim_id: str | None = None) -> None:
    runtime = application._runtimes["change-a"]
    coordination = application._coordinator.show("change-a")
    before_frontier = runtime.frontier_bytes()
    before_ledger = runtime.retry_ledger().read()
    before_workspace = _workspace_content_snapshot(coordination.worktree_path)
    with pytest.raises(DeliveryRuntimeConflictError, match=message):
        application.publish_delivery_plan(
            "change-a",
            PublishDeliveryPlan(
                outcome_id="OUT-001",
                claim_id=claim_id or planner.claim.claim_id,
                tasks=tasks,
            ),
        )
    assert runtime.frontier_bytes() == before_frontier
    assert application._coordinator.show("change-a") == coordination
    assert runtime.retry_ledger().read() == before_ledger
    assert _workspace_content_snapshot(coordination.worktree_path) == before_workspace


def _assert_return_plan_rejections(application, planner) -> tuple[DeliveryTaskDefinition, ...]:
    binding = application._runtimes["change-a"].show_binding("OUT-001")
    completed_task, original_task = binding.tasks
    planned_original = original_task.model_copy(
        update={"title": "Clarify the retained task", "result": "One clarified bounded implementation."}
    )
    followup = _task().model_copy(
        update={
            "task_id": "TASK-003",
            "title": "Implement the follow-up",
            "dependency_ids": ("TASK-002",),
        }
    )
    planned_tasks = (completed_task, planned_original, followup)
    invalid_plans = (
        (planned_tasks, "claim", "wrong-planner-claim"),
        ((original_task.model_copy(update={"dependency_ids": ()}),), "completed task definitions", None),
        (
            (completed_task.model_copy(update={"title": "Rewrite completed task"}), original_task),
            "completed task definitions",
            None,
        ),
        ((completed_task,), "original task", None),
        (
            (completed_task, original_task.model_copy(update={"maintained_surfaces": ("share/WIRING.md",)})),
            "original task",
            None,
        ),
        (
            (completed_task, original_task.model_copy(update={"commitment_ids": ("COM-002",)})),
            "original task",
            None,
        ),
    )
    for tasks, message, claim_id in invalid_plans:
        _assert_return_plan_rejected(application, planner, tasks, message, claim_id)
    return planned_tasks


def _advance_returned_plan(application, planner, builder, planned_tasks):
    runtime = application._runtimes["change-a"]
    binding = runtime.show_binding("OUT-001")
    completed_task = binding.tasks[0]
    first_result = binding.results[0]
    handoff = binding.builder_handoff_context
    before_workspace = _workspace_content_snapshot(builder.worktree_path)
    candidate = application.publish_delivery_plan(
        "change-a",
        PublishDeliveryPlan(outcome_id="OUT-001", claim_id=planner.claim.claim_id, tasks=planned_tasks),
    )
    advanced = application.transition_delivery(
        "change-a",
        AdvanceDelivery(
            action="advance",
            outcome_id="OUT-001",
            claim_id=planner.claim.claim_id,
            output=candidate.output,
        ),
    )
    assert advanced.stage == DeliveryStage.IMPLEMENTATION
    assert advanced.tasks[0].model_dump_json().encode("utf-8") == completed_task.model_dump_json().encode("utf-8")
    assert tuple(result.model_dump_json().encode("utf-8") for result in advanced.results) == (
        first_result.model_dump_json().encode("utf-8"),
    )
    assert advanced.builder_handoff_context is not None
    assert advanced.builder_handoff_context.route == "same-task"
    assert advanced.builder_handoff_context.settlement_id == handoff.settlement_id
    assert advanced.builder_handoff_context.metadata_fingerprint == handoff.metadata_fingerprint
    assert runtime.claimable_task_ids("OUT-001") == ("TASK-002",)
    assert _workspace_content_snapshot(builder.worktree_path) == before_workspace
    return advanced


def _assert_returned_builder_reacquisition(application, builder, advanced, now, before_workspace) -> None:
    runtime = application._runtimes["change-a"]
    episode_before = runtime.retry_ledger().episode_for_attempt(builder.claim.attempt_id)
    assert episode_before is not None
    assert episode_before.total_attempts == 1
    assert episode_before.reset_count == 0
    now[0] = "2026-08-04T01:00:00Z"
    result = application.acquire_actions(
        DeliveryActionSelection(
            change_id="change-a",
            outcome_id="OUT-001",
            expected_stage=DeliveryStage.IMPLEMENTATION,
            expected_task_id="TASK-002",
            expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            expected_source_head=advanced.builder_handoff_context.branch_head,
        )
    )
    assert len(result.launch_packages) == 1, (
        tuple((failure.code, failure.detail, failure.retry_condition) for failure in result.failures),
        runtime.retry_ledger().episode_for_attempt(builder.claim.attempt_id),
    )
    resumed = result.launch_packages[0]
    assert resumed.claim.worker_role is DeliveryWorkerRole.BUILDER
    assert resumed.task_id == "TASK-002"
    assert resumed.source_head == advanced.builder_handoff_context.branch_head
    assert resumed.builder_handoff_context == advanced.builder_handoff_context
    assert resumed.writer is not None
    assert application._coordinator.show("change-a").builder_handoff is None
    assert application._coordinator.show("change-a").writer == resumed.writer
    assert _workspace_content_snapshot(builder.worktree_path) == before_workspace
    episode_after = runtime.retry_ledger().episode_for_attempt(builder.claim.attempt_id)
    assert episode_after is not None
    assert episode_after.total_attempts == 2
    assert episode_after.reset_count == 0
    assert builder.claim.attempt_id in episode_after.attempt_ids
    assert resumed.claim.attempt_id in episode_after.attempt_ids


def test_builder_return_routes_through_planner_then_same_task_retry(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING},
        execution_capacity=1,
        clock=lambda: now[0],
        include_independent=True,
    )
    _completed_task, _original_task, _first_result, builder = _seed_two_task_builder(
        application, runtimes, coordinator, state_root
    )
    settled, _branch_head, before_workspace, _reason = _return_builder(application, builder)
    _assert_returned_planner_handoff(application, builder, settled, before_workspace)
    _assert_returned_handoff_metadata_fences(application, builder, before_workspace)
    planner = _acquire_returned_planner(application, builder, before_workspace)
    planned_tasks = _assert_return_plan_rejections(application, planner)
    advanced = _advance_returned_plan(application, planner, builder, planned_tasks)
    _assert_returned_builder_reacquisition(application, builder, advanced, now, before_workspace)


def test_builder_return_to_design_routes_to_human_and_releases_capacity(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING},
        execution_capacity=1,
        include_independent=True,
    )
    _completed_task, _original_task, _first_result, builder = _seed_two_task_builder(
        application, runtimes, coordinator, state_root
    )

    settled, _branch_head, before_workspace, reason = _return_builder(
        application,
        builder,
        target=DeliveryStage.DESIGN,
    )

    assert settled.stage == DeliveryStage.DESIGN
    assert settled.active_claim is None
    assert settled.return_context is not None
    assert settled.return_context.reason == reason
    assert settled.return_context.locators == ("design.md",)
    assert _workspace_content_snapshot(builder.worktree_path) == before_workspace
    runtime = runtimes["change-a"]
    assert runtime.claimable_outcome_ids() == ()
    assert runtime.claimable_task_ids("OUT-001") == ()
    assert runtime.active_claims() == ()

    view = application.get_change("change-a")
    readiness = view.readiness
    assert readiness.reason_code == "design-attention"
    assert readiness.next_actor.value == "you"
    assert readiness.status == "blocked"
    assert not readiness.executable
    assert view.detail.return_context == settled.return_context
    assert view.detail.card.action.kind.value == "resume-design"
    assert view.detail.card.action.command == "/design change-a"
    assert readiness.prompt is not None
    assert readiness.prompt.startswith("/inspect-change change-a")
    assert reason in readiness.prompt
    assert "design.md" in readiness.prompt
    assert "Outcome: OUT-001" in readiness.prompt
    assert "Delivery stage: design" in readiness.prompt
    assert f"Preserved commit: {settled.return_context.preserved_commit}" in readiness.prompt
    assert f"Completed boundary: {settled.return_context.completed_boundary}" in readiness.prompt
    assert "does not approve or admit" in readiness.prompt
    assert "managed worktree" in readiness.prompt
    assert "Pause the Change, then revise its package with /design change-a" in readiness.prompt

    continuation = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert continuation.kind == "human"
    assert continuation.reason_code == "design-attention"
    assert continuation.readiness.prompt == readiness.prompt
    assert continuation.launch is None
    assert continuation.engine_action is None
    assert runtime.active_claims() == ()
    assert _workspace_content_snapshot(builder.worktree_path) == before_workspace
    handoff = coordinator.show("change-a").builder_handoff
    assert handoff is not None
    assert coordinator.show("change-a").writer == handoff.original_writer.model_copy(update={"kind": "handoff"})

    independent = application.acquire_change_action(_continuation_request(application, "change-b"))
    assert independent.kind == "acquired"
    assert independent.launch is not None
    assert independent.launch.claim.worker_role is DeliveryWorkerRole.PLANNER


def _builder_decision_handoff_setup(tmp_path: Path, now: list[str]):
    application, runtime, coordinator, state_root, first, branch_head, before_workspace, settlement = (
        _builder_retry_handoff_setup(tmp_path, now, include_independent=True)
    )
    request = DeliveryRequest(
        request_id="builder-pause-decision",
        kind=DeliveryRequestKind.DECISION,
        outcome_id=first.outcome_id,
        summary="Choose whether this Builder task may resume.",
        options=(DeliveryRequestOption(option_id="resume", label="Resume"),),
    )
    block = BlockDelivery(
        action="block",
        outcome_id=first.outcome_id,
        claim_id=first.claim.claim_id,
        block_id="builder-pause",
        reason="The Builder needs a user decision.",
        unblock_condition="The user decision is recorded.",
        expected_evidence=("A confirmed decision.",),
        locators=(first.task_id,),
        resume_commit=branch_head,
        request=request,
    )
    paused = _settle_builder_handoff_attempt(application, first.claim, settlement.model_copy(update={"request": block}))
    return application, runtime, coordinator, state_root, first, before_workspace, request, paused


def test_builder_retry_handoff_reacquires_same_task_without_changing_workspace(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, coordinator, state_root, first, _branch_head, before_workspace, settlement = (
        _builder_retry_handoff_setup(tmp_path, now)
    )
    settled = application.settle_worker_invocation(
        settlement,
        host_id=first.claim.owner_id,
        session_id=first.claim.process_id,
    )

    assert settled.active_claim is None
    assert settled.builder_handoff_context is not None
    owner_result_path = state_root / "changes/change-a/retry-ledger/owner-results" / f"{first.claim.attempt_id}.json"
    assert json.loads(owner_result_path.read_bytes())["observed_at"] == now[0]
    handoff = coordinator.show("change-a").builder_handoff
    assert handoff is not None
    assert coordinator.show("change-a").writer is not None
    assert coordinator.show("change-a").writer.kind == "handoff"
    assert runtime.show_binding("OUT-001").recovery_attention is None
    assert _workspace_content_snapshot(first.worktree_path) == before_workspace

    sibling_result = application.acquire_change_action(_continuation_request(application, "change-b"))
    assert sibling_result.launch is not None
    sibling = sibling_result.launch
    sibling_retry = RetryDelivery(
        action="retry",
        outcome_id=sibling.outcome_id,
        claim_id=sibling.claim.claim_id,
    )
    application.settle_worker_invocation(
        DeliveryPlanningRetrySettlement(
            change_id=sibling.change_id,
            outcome_id=sibling.outcome_id,
            claim_id=sibling.claim.claim_id,
            attempt_id=sibling.claim.attempt_id,
            disposition="normal-return",
            request=sibling_retry,
        ),
        host_id=sibling.claim.owner_id,
        session_id=sibling.claim.process_id,
    )
    now[0] = "2026-08-04T01:00:00Z"

    resumed_result = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert resumed_result.launch is not None, (
        resumed_result.failure.detail if resumed_result.failure is not None else resumed_result
    )
    resumed = resumed_result.launch
    assert resumed.claim.task_id == first.task_id
    assert resumed.claim.attempt_id != first.claim.attempt_id
    assert resumed.builder_handoff_context == settled.builder_handoff_context
    assert coordinator.show("change-a").builder_handoff is None
    assert coordinator.show("change-a").writer == resumed.writer
    assert _workspace_content_snapshot(first.worktree_path) == before_workspace
    coordination = coordinator.show("change-a")
    foreign_writers = (
        resumed.writer.model_copy(update={"claim_id": "foreign-builder-claim"}),
        resumed.writer.model_copy(update={"claimed_at": "2026-08-04T02:00:00Z"}),
    )
    for foreign_writer in foreign_writers:
        with (
            patch.object(
                application._workspace_manager,
                "show",
                return_value=coordination.model_copy(update={"writer": foreign_writer}),
            ),
            pytest.raises(PortfolioApplicationError, match="active Builder handoff context does not match"),
        ):
            application.show_build_context(
                resumed.change_id,
                resumed.outcome_id,
                resumed.claim.attempt_id,
                resumed.claim.claim_id,
            )
    (resumed.worktree_path / "product.txt").write_text("active Builder edit\n", encoding="utf-8")
    build_context = application.show_build_context(
        resumed.change_id,
        resumed.outcome_id,
        resumed.claim.attempt_id,
        resumed.claim.claim_id,
    )
    assert build_context.launch.builder_handoff_context == settled.builder_handoff_context

    ledger = runtime.retry_ledger().read()
    assert len(ledger.episodes) == 1
    episode = ledger.episodes[0]
    assert episode.total_attempts == 2
    assert episode.reset_count == 0
    assert episode.key.exact_head == first.last_reviewed_commit
    assert first.claim.attempt_id in episode.attempt_ids
    assert resumed.claim.attempt_id in episode.attempt_ids


def test_builder_retry_handoff_keeps_dirty_workspace_out_of_remote_state(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, _coordinator, _state_root, first, _branch_head, before_workspace, settlement = (
        _builder_retry_handoff_setup(tmp_path, now, publish_initial_state=True)
    )
    publisher = application._delivery_state_publisher
    assert isinstance(publisher, DeliveryStatePublisher)
    initial_inventory = publisher.read_snapshot_inventory()
    initial_snapshot = publisher.read_snapshot("change-a")
    assert initial_inventory.remote_head is not None
    assert initial_snapshot is not None

    settled = application.settle_worker_invocation(
        settlement,
        host_id=first.claim.owner_id,
        session_id=first.claim.process_id,
    )

    assert settled.active_claim is None
    assert settled.builder_handoff_context is not None
    assert runtime.pending_state_publication() is None
    assert application._publish_delivery_state("change-a", runtime, "builder-handoff-retry") is None
    assert runtime.pending_state_publication() is None
    assert publisher.read_snapshot_inventory().remote_head == initial_inventory.remote_head
    assert publisher.read_snapshot("change-a") == initial_snapshot
    assert _workspace_content_snapshot(first.worktree_path) == before_workspace

    now[0] = "2026-08-04T01:00:00Z"
    resumed_result = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert resumed_result.launch is not None, resumed_result
    resumed = resumed_result.launch

    assert resumed.claim.task_id == first.task_id
    assert resumed.claim.attempt_id != first.claim.attempt_id
    assert _workspace_content_snapshot(resumed.worktree_path) == before_workspace
    assert runtime.pending_state_publication() is None
    assert publisher.read_snapshot_inventory().remote_head == initial_inventory.remote_head
    assert publisher.read_snapshot("change-a") == initial_snapshot


def test_paused_builder_handoff_releases_capacity_and_refuses_late_result(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    (
        application,
        runtime,
        coordinator,
        state_root,
        first,
        before_workspace,
        request,
        paused,
    ) = _builder_decision_handoff_setup(tmp_path, now)

    assert paused.active_claim is None
    assert paused.requests == (request,)
    assert paused.block is not None
    assert not paused.block.resolved
    handoff = coordinator.show("change-a").builder_handoff
    assert handoff is not None
    assert runtime.active_claims() == ()
    assert _workspace_content_snapshot(first.worktree_path) == before_workspace

    late_result = _task_result(
        "RESULT-LATE-PAUSED-BUILDER",
        "change-a",
        runtime.authority_digest,
        runtime.show_binding(first.outcome_id).tasks[0],
        _git(first.worktree_path, "rev-parse", "HEAD"),
    )
    with pytest.raises(DeliveryRuntimeConflictError):
        runtime.publish_result(
            PublishDeliveryResult(outcome_id=first.outcome_id, claim_id=first.claim.claim_id, result=late_result)
        )

    reopened, reopened_coordinator, _manager = _reopen_portfolio(
        tmp_path,
        state_root,
        application._runtimes,
        clock=lambda: now[0],
        execution_capacity=1,
    )
    while_unanswered = reopened.acquire_frontier_work()
    assert while_unanswered.failures == ()
    assert tuple(package.change_id for package in while_unanswered.launch_packages) == ("change-b",)
    assert while_unanswered.launch_packages[0].claim.worker_role is DeliveryWorkerRole.PLANNER
    assert reopened._runtimes["change-a"].active_claims() == ()
    assert reopened_coordinator.show("change-a").builder_handoff == handoff
    assert _workspace_content_snapshot(first.worktree_path) == before_workspace


def test_builder_decision_answer_survives_restart_and_reacquires_same_task(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    (
        application,
        _runtime,
        coordinator,
        state_root,
        first,
        before_workspace,
        request,
        paused,
    ) = _builder_decision_handoff_setup(tmp_path, now)
    handoff = coordinator.show("change-a").builder_handoff
    assert handoff is not None
    reopened, reopened_coordinator, _manager = _reopen_portfolio(
        tmp_path,
        state_root,
        application._runtimes,
        clock=lambda: now[0],
        execution_capacity=1,
    )
    answer_view = reopened.get_change("change-a")
    answer = DeliveryAnswer(
        change_id="change-a",
        request_id=request.request_id,
        resolution=DeliveryRequestResolution(selected_option_id="resume"),
        expected_frontier_digest=answer_view.frontier_digest,
    )
    answered = reopened.answer(answer)
    assert answered.request.resolution == answer.resolution
    assert reopened_coordinator.show("change-a").builder_handoff == handoff
    assert _workspace_content_snapshot(first.worktree_path) == before_workspace

    restarted, restarted_coordinator, _manager = _reopen_portfolio(
        tmp_path,
        state_root,
        application._runtimes,
        clock=lambda: now[0],
        execution_capacity=1,
    )
    assert restarted._runtimes["change-a"].show_binding(first.outcome_id).requests[0].resolution == answer.resolution
    resumed_result = restarted.acquire_change_action(_continuation_request(restarted, "change-a"))
    assert resumed_result.kind == "acquired"
    assert resumed_result.launch is not None, resumed_result
    resumed = resumed_result.launch
    assert resumed.claim.task_id == first.task_id
    assert resumed.builder_handoff_context == paused.builder_handoff_context
    assert resumed.claim.attempt_id != first.claim.attempt_id
    assert resumed.claim.claim_id != first.claim.claim_id
    assert restarted_coordinator.show("change-a").builder_handoff is None
    assert _workspace_content_snapshot(first.worktree_path) == before_workspace

    ledger = restarted._runtimes["change-a"].retry_ledger().read()
    assert len(ledger.episodes) == 1
    episode = ledger.episodes[0]
    assert episode.total_attempts == 1
    assert episode.last_failure_at is None
    assert episode.legacy_failures == 0
    assert set(episode.attempt_ids) == {first.claim.attempt_id, resumed.claim.attempt_id}


def test_builder_retry_handoff_refuses_foreign_task_and_workspace_drift(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, coordinator, _state_root, first, branch_head, before_workspace, settlement = (
        _builder_retry_handoff_setup(tmp_path, now)
    )
    frontier_before_wrong_owner = runtime.frontier_bytes()
    ledger_before_wrong_owner = runtime.retry_ledger().read()
    for host_id, session_id in (
        ("foreign-host", first.claim.process_id),
        (first.claim.owner_id, "foreign-session"),
    ):
        with pytest.raises(PortfolioApplicationError, match="host and session binding"):
            application.settle_worker_invocation(settlement, host_id=host_id, session_id=session_id)
        assert runtime.frontier_bytes() == frontier_before_wrong_owner
        assert runtime.retry_ledger().read() == ledger_before_wrong_owner
        assert _workspace_content_snapshot(first.worktree_path) == before_workspace

    settled = application.settle_worker_invocation(
        settlement,
        host_id=first.claim.owner_id,
        session_id=first.claim.process_id,
    )

    assert settled.active_claim is None
    assert settled.builder_handoff_context is not None
    handoff = coordinator.show("change-a").builder_handoff
    assert handoff is not None
    assert runtime.show_binding("OUT-001").recovery_attention is None
    assert _workspace_content_snapshot(first.worktree_path) == before_workspace

    frontier_before_refusals = runtime.frontier_bytes()
    foreign_claim = DeliveryActiveClaim(
        attempt_id="foreign-attempt",
        claim_id="foreign-claim",
        owner_id="foreign-host",
        process_id="foreign-session",
        started_at=now[0],
        worker_role=DeliveryWorkerRole.BUILDER,
        task_id="TASK-FOREIGN",
    )
    with pytest.raises(DeliveryRuntimeConflictError, match="implementation task is not claimable"):
        runtime.activate_claim(ActivateDeliveryClaim(outcome_id="OUT-001", claim=foreign_claim))
    late_result = _task_result(
        "RESULT-LATE-BUILDER",
        "change-a",
        runtime.authority_digest,
        runtime.show_binding("OUT-001").tasks[0],
        branch_head,
    )
    with pytest.raises(DeliveryRuntimeConflictError):
        runtime.publish_result(
            PublishDeliveryResult(outcome_id="OUT-001", claim_id=first.claim.claim_id, result=late_result)
        )
    assert runtime.frontier_bytes() == frontier_before_refusals
    assert coordinator.show("change-a").builder_handoff == handoff

    now[0] = "2026-08-04T01:00:00Z"
    drift_file = first.worktree_path / "post-handoff-drift.txt"
    drift_file.write_text("workspace changed after handoff\n", encoding="utf-8")
    drift_snapshot = _workspace_content_snapshot(first.worktree_path)
    drift_result = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert drift_result.kind == "unavailable", drift_result
    assert drift_result.launch is None
    assert runtime.active_claims() == ()
    assert coordinator.show("change-a").builder_handoff == handoff
    assert _workspace_content_snapshot(first.worktree_path) == drift_snapshot
    drift_file.unlink()
    assert _workspace_content_snapshot(first.worktree_path) == before_workspace


def test_batch_handoff_selects_exact_task_over_higher_ranked_independent_outcome(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, coordinator, _state_root, first, _branch_head, _workspace, settlement = (
        _builder_retry_handoff_setup(
            tmp_path,
            now,
            include_independent=True,
            add_workspace_changes=False,
        )
    )
    settled = _settle_builder_handoff_attempt(application, first.claim, settlement)
    assert settled.builder_handoff_context is not None
    now[0] = "2026-08-04T01:00:00Z"

    def rank_candidate(candidate_runtime: DeliveryRuntime, outcome_id: str) -> int:
        if candidate_runtime.contract.change_id == "change-a":
            return {"OUT-002": -1, "OUT-001": 0}[outcome_id]
        return 1

    assert rank_candidate(runtime, "OUT-002") < rank_candidate(runtime, "OUT-001")
    with patch.object(application, "_dependency_depth", side_effect=rank_candidate):
        result = application.acquire_frontier_work()

    assert result.failures == ()
    assert tuple(package.change_id for package in result.launch_packages) == ("change-a",)
    resumed = result.launch_packages[0]
    assert resumed.outcome_id == first.outcome_id
    assert resumed.claim.task_id == first.task_id
    assert resumed.builder_handoff_context == settled.builder_handoff_context
    assert runtime.active_claims() == ((first.outcome_id, resumed.claim),)
    assert runtime.show_binding("OUT-002").active_claim is None
    assert coordinator.show("change-a").builder_handoff is None


@pytest.mark.parametrize("handoff_state", ["paused", "exhausted"])
def test_nonclaimable_builder_handoff_leaves_capacity_for_independent_change(
    tmp_path: Path,
    handoff_state: str,
) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, coordinator, _state_root, first, _branch_head, _workspace, settlement = (
        _builder_retry_handoff_setup(
            tmp_path,
            now,
            include_independent=True,
            add_workspace_changes=False,
        )
    )
    if handoff_state == "paused":
        request = BlockDelivery(
            action="block",
            outcome_id=first.outcome_id,
            claim_id=first.claim.claim_id,
            block_id="builder-pause",
            reason="The Builder needs a user decision.",
            unblock_condition="The user decision is recorded.",
            expected_evidence=("A confirmed decision.",),
            locators=(first.task_id,),
            resume_commit=first.source_head,
            request=DeliveryRequest(
                request_id="builder-pause-decision",
                kind=DeliveryRequestKind.DECISION,
                outcome_id=first.outcome_id,
                summary="Choose whether this Builder task may resume.",
                options=(DeliveryRequestOption(option_id="resume", label="Resume"),),
            ),
        )
        settlement = settlement.model_copy(update={"request": request})
    _settle_builder_handoff_attempt(application, first.claim, settlement)
    if handoff_state == "exhausted":
        for hour in (1, 2):
            now[0] = f"2026-08-04T{hour:02}:00:00Z"
            resumed_result = application.acquire_change_action(_continuation_request(application))
            assert resumed_result.launch is not None
            resumed = resumed_result.launch
            retry = RetryDelivery(
                action="retry",
                outcome_id=resumed.outcome_id,
                claim_id=resumed.claim.claim_id,
                attempt_id=resumed.claim.attempt_id,
                abandoned_commit=resumed.source_head,
                failure_code="builder-failed",
            )
            retry_settlement = DeliveryBuilderInvocationSettlement(
                change_id=resumed.change_id,
                outcome_id=resumed.outcome_id,
                claim_id=resumed.claim.claim_id,
                attempt_id=resumed.claim.attempt_id,
                task_id=resumed.task_id,
                expected_last_reviewed_commit=resumed.last_reviewed_commit,
                disposition="normal-return",
                request=retry,
            )
            _settle_builder_handoff_attempt(application, resumed.claim, retry_settlement)
        assert runtime.show_binding(first.outcome_id).block is not None

    assert runtime.claimable_outcome_ids() == ("OUT-002",)

    def rank_sibling_first(candidate_runtime: DeliveryRuntime, outcome_id: str) -> int:
        return -1 if candidate_runtime.contract.change_id == "change-a" and outcome_id == "OUT-002" else 0

    with patch.object(application, "_dependency_depth", side_effect=rank_sibling_first):
        result = application.acquire_frontier_work()

    assert result.failures == ()
    assert tuple(package.change_id for package in result.launch_packages) == ("change-b",)
    assert coordinator.show("change-a").builder_handoff is not None
    assert coordinator.show("change-a").writer is not None
    assert coordinator.show("change-a").writer.kind == "handoff"
    assert runtime.show_binding("OUT-002").active_claim is None
    assert application._execution_occupancy() == 1


@pytest.mark.parametrize("add_workspace_changes", [False, True], ids=["clean", "preserved-work"])
def test_builder_handoff_readiness_uses_original_task_retry_episode(
    tmp_path: Path, *, add_workspace_changes: bool
) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, coordinator, state_root, first, _head, _workspace, settlement = _builder_retry_handoff_setup(
        tmp_path, now, add_workspace_changes=add_workspace_changes
    )
    _settle_builder_handoff_attempt(application, first.claim, settlement)
    episode = runtime.retry_ledger().episode_for_attempt(first.claim.attempt_id)
    assert episode is not None
    assert episode.total_attempts == 1
    assert episode.next_eligible_at is not None

    frontier_path = state_root / "changes" / "change-a" / "frontier.json"
    frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
    bindings = []
    for binding in frontier.bindings:
        if binding.outcome_id != first.outcome_id:
            bindings.append(binding)
            continue
        parallel = binding.tasks[0].model_copy(
            update={"task_id": "TASK-000", "title": "Implement a parallel task", "dependency_ids": ()}
        )
        bindings.append(binding.model_copy(update={"tasks": (parallel, *binding.tasks)}))
    frontier_path.write_bytes(_canonical(frontier.model_copy(update={"bindings": tuple(bindings)})))
    assert runtime.claimable_task_ids(first.outcome_id) == (first.task_id,)
    handoff = coordinator.show("change-a").builder_handoff

    readiness = application.get_change("change-a").readiness

    assert readiness.reason_code == "retry-backoff", readiness
    assert readiness.status == "waiting"
    assert readiness.attempts == 1
    assert readiness.next_eligible_at == episode.next_eligible_at
    assert not readiness.executable
    assert runtime.active_claims() == ()
    assert coordinator.show("change-a").builder_handoff == handoff
    assert runtime.retry_ledger().episode_for_attempt(first.claim.attempt_id) == episode


def test_exhausted_builder_retry_projects_read_only_diagnostic_without_clear_action(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, _coordinator, _state_root, first, _head, _workspace, settlement = (
        _builder_retry_handoff_setup(tmp_path, now, add_workspace_changes=False)
    )
    _settle_builder_handoff_attempt(application, first.claim, settlement)
    attempt_ids = [first.claim.attempt_id]

    for hour in (1, 2):
        now[0] = f"2026-08-04T{hour:02}:00:00Z"
        acquired = application.acquire_change_action(_continuation_request(application, "change-a"))
        assert acquired.launch is not None, acquired
        resumed = acquired.launch
        attempt_ids.append(resumed.claim.attempt_id)
        retry_settlement = DeliveryBuilderInvocationSettlement(
            change_id=resumed.change_id,
            outcome_id=resumed.outcome_id,
            claim_id=resumed.claim.claim_id,
            attempt_id=resumed.claim.attempt_id,
            task_id=resumed.task_id,
            expected_last_reviewed_commit=resumed.last_reviewed_commit,
            disposition="normal-return",
            request=RetryDelivery(
                action="retry",
                outcome_id=resumed.outcome_id,
                claim_id=resumed.claim.claim_id,
                attempt_id=resumed.claim.attempt_id,
                abandoned_commit=resumed.source_head,
                failure_code="builder-failed",
            ),
        )
        _settle_builder_handoff_attempt(application, resumed.claim, retry_settlement)

    binding = runtime.show_binding("OUT-001")
    assert binding.block is not None
    assert binding.block.request_id is None
    assert binding.requests == ()
    assert "three-attempt limit" in binding.block.reason
    episode = runtime.retry_ledger().read().episodes[0]
    assert episode.total_attempts == 3
    assert episode.attempt_ids == tuple(attempt_ids)
    assert episode.stop_code.value == "retry-exhausted"
    assert episode.reset_count == 0

    view = application.show_work_item_view("change-a", "outcome:OUT-001")
    assert view.readiness is not None
    assert view.card.needs.value == "none"
    assert view.card.next_actor.value == "agent"
    assert view.card.action.kind.value == "none"
    assert view.card.action.command is None
    assert view.readiness.reason_code == "retry-exhausted"
    assert view.readiness.attempts == 3
    assert view.readiness.executable is False
    assert view.readiness.operation is None
    assert view.readiness.prompt is not None
    assert view.readiness.prompt.startswith("/inspect-change change-a")
    assert "read-only" in view.readiness.prompt
    assert "do not clear the block, retry, dispatch, or reset the budget" in view.readiness.prompt
    assert "Builder" in view.card.next_step
    assert "approved current authority" in view.card.next_step


def _builder_retry_history(items) -> list[tuple[int, str, str, str | None]]:
    return [(item.ordinal, item.kind, item.status, item.failure_code) for item in items]


def _exhaust_builder_retry_with_distinct_codes(tmp_path: Path):
    """Fail one Builder task three times with distinct codes across a restart; return the reopened application."""
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, _coordinator, state_root, first, _head, _workspace, settlement = _builder_retry_handoff_setup(
        tmp_path, now, add_workspace_changes=False
    )
    _settle_builder_handoff_attempt(application, first.claim, settlement)
    contexts = []

    now[0] = "2026-08-04T01:00:00Z"
    acquired = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert acquired.launch is not None, acquired
    second = acquired.launch
    assert second.task_id == first.task_id
    contexts.append(
        application.show_build_context(
            second.change_id, second.outcome_id, second.claim.attempt_id, second.claim.claim_id
        )
    )
    _settle_builder_handoff_attempt(
        application,
        second.claim,
        DeliveryBuilderInvocationSettlement(
            change_id=second.change_id,
            outcome_id=second.outcome_id,
            claim_id=second.claim.claim_id,
            attempt_id=second.claim.attempt_id,
            task_id=second.task_id,
            expected_last_reviewed_commit=second.last_reviewed_commit,
            disposition="completed-timeout",
        ),
    )

    now[0] = "2026-08-04T02:00:00Z"
    reopened, _reopened_coordinator, _manager = _reopen_portfolio(
        tmp_path, state_root, application._runtimes, clock=lambda: now[0]
    )
    acquired = reopened.acquire_change_action(_continuation_request(reopened, "change-a"))
    assert acquired.launch is not None, acquired
    third = acquired.launch
    assert third.task_id == first.task_id
    contexts.append(
        reopened.show_build_context(third.change_id, third.outcome_id, third.claim.attempt_id, third.claim.claim_id)
    )
    _settle_builder_handoff_attempt(
        reopened,
        third.claim,
        DeliveryBuilderInvocationSettlement(
            change_id=third.change_id,
            outcome_id=third.outcome_id,
            claim_id=third.claim.claim_id,
            attempt_id=third.claim.attempt_id,
            task_id=third.task_id,
            expected_last_reviewed_commit=third.last_reviewed_commit,
            disposition="normal-return",
            request=RetryDelivery(
                action="retry",
                outcome_id=third.outcome_id,
                claim_id=third.claim.claim_id,
                attempt_id=third.claim.attempt_id,
                abandoned_commit=third.source_head,
                failure_code="builder-review-failed",
            ),
        ),
    )
    return reopened, runtime, contexts


def test_builder_retry_history_reaches_fresh_builder_and_exhaustion_diagnosis(tmp_path: Path) -> None:
    application, runtime, contexts = _exhaust_builder_retry_with_distinct_codes(tmp_path)

    second_context, third_context = contexts
    assert _builder_retry_history(second_context.prior_attempts) == [(1, "original", "failed", "builder-failed")]
    assert _builder_retry_history(third_context.prior_attempts) == [
        (1, "original", "failed", "builder-failed"),
        (2, "repair", "failed", "worker-timeout"),
    ]
    assert [item.observed_at for item in third_context.prior_attempts] == [
        "2026-08-04T00:00:00Z",
        "2026-08-04T01:00:00Z",
    ]
    episode = runtime.retry_ledger().read().episodes[0]
    assert episode.stop_code is not None
    assert episode.stop_code.value == "retry-exhausted"
    expected = [
        (1, "original", "failed", "builder-failed"),
        (2, "repair", "failed", "worker-timeout"),
        (3, "repair", "failed", "builder-review-failed"),
    ]

    view = application.show_work_item_view("change-a", "outcome:OUT-001")
    assert view.readiness is not None
    assert view.readiness.reason_code == "retry-exhausted"
    assert view.readiness.next_actor.value == "agent"
    assert view.readiness.attempts == 3
    assert _builder_retry_history(view.readiness.retry_history) == expected
    change = application.get_change("change-a")
    assert change.kind == "available"
    exhausted = next(item for item in change.unresolved_outcomes if item.outcome_id == "OUT-001")
    assert exhausted.card.readiness is not None
    assert _builder_retry_history(exhausted.card.readiness.retry_history) == expected


def _requestless_builder_settlement(launch, disposition: str) -> DeliveryBuilderInvocationSettlement:
    return DeliveryBuilderInvocationSettlement(
        change_id=launch.change_id,
        outcome_id=launch.outcome_id,
        claim_id=launch.claim.claim_id,
        attempt_id=launch.claim.attempt_id,
        task_id=launch.task_id,
        expected_last_reviewed_commit=launch.last_reviewed_commit,
        disposition=disposition,
    )


def test_builder_ended_without_result_reacquires_same_task_with_preserved_work_and_history(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, coordinator, state_root, first, branch_head, before_workspace, _settlement = (
        _builder_retry_handoff_setup(tmp_path, now)
    )
    settlement = _requestless_builder_settlement(first, "ended-without-result")
    frontier_before = runtime.frontier_bytes()
    ledger_before = runtime.retry_ledger().read()
    for host_id, session_id in (
        ("foreign-host", first.claim.process_id),
        (first.claim.owner_id, "foreign-session"),
    ):
        with pytest.raises(PortfolioApplicationError, match="host and session binding"):
            application.settle_worker_invocation(settlement, host_id=host_id, session_id=session_id)
        assert runtime.frontier_bytes() == frontier_before
        assert runtime.retry_ledger().read() == ledger_before

    settled = _settle_builder_handoff_attempt(application, first.claim, settlement)

    assert settled.active_claim is None
    assert settled.block is None
    assert settled.builder_handoff_context is not None
    assert settled.builder_handoff_context.route == "same-task"
    assert settled.builder_handoff_context.branch_head == branch_head
    assert _workspace_content_snapshot(first.worktree_path) == before_workspace
    assert coordinator.show("change-a").builder_handoff is not None
    owner_result_path = state_root / "changes/change-a/retry-ledger/owner-results" / f"{first.claim.attempt_id}.json"
    assert json.loads(owner_result_path.read_bytes())["failure_code"] == "worker-ended-without-result"
    assert _settle_builder_handoff_attempt(application, first.claim, settlement) == settled
    waiting = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert waiting.launch is None
    assert waiting.reason_code == "retry-backoff"
    late_result = _task_result(
        "RESULT-LATE-ENDED-BUILDER",
        "change-a",
        runtime.authority_digest,
        runtime.show_binding(first.outcome_id).tasks[0],
        branch_head,
    )
    with pytest.raises(DeliveryRuntimeConflictError):
        runtime.publish_result(
            PublishDeliveryResult(outcome_id=first.outcome_id, claim_id=first.claim.claim_id, result=late_result)
        )

    now[0] = "2026-08-04T01:00:00Z"
    resumed_result = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert resumed_result.launch is not None, resumed_result
    resumed = resumed_result.launch
    assert resumed.claim.task_id == first.task_id
    assert resumed.claim.attempt_id != first.claim.attempt_id
    assert resumed.builder_handoff_context == settled.builder_handoff_context
    assert _workspace_content_snapshot(resumed.worktree_path) == before_workspace
    build_context = application.show_build_context(
        resumed.change_id, resumed.outcome_id, resumed.claim.attempt_id, resumed.claim.claim_id
    )
    assert build_context.launch.builder_handoff_context == settled.builder_handoff_context
    assert _builder_retry_history(build_context.prior_attempts) == [
        (1, "original", "failed", "worker-ended-without-result")
    ]
    episode = runtime.retry_ledger().read().episodes[0]
    assert episode.total_attempts == 2
    assert episode.reset_count == 0
    assert episode.attempt_ids == (first.claim.attempt_id, resumed.claim.attempt_id)


@pytest.mark.parametrize(
    ("dispositions", "expected_codes"),
    [
        (
            ("ended-without-result", "ended-without-result", "ended-without-result"),
            ("worker-ended-without-result",) * 3,
        ),
        (
            ("completed-timeout", "ended-without-result", "normal-return"),
            ("worker-timeout", "worker-ended-without-result", "builder-failed"),
        ),
    ],
    ids=["three-crashes", "mixed"],
)
def test_ended_without_result_builder_attempts_share_one_exhausting_budget(
    tmp_path: Path,
    dispositions: tuple[str, ...],
    expected_codes: tuple[str, ...],
) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, _coordinator, _state_root, launch, _head, before_workspace, _settlement = (
        _builder_retry_handoff_setup(tmp_path, now)
    )
    attempt_ids = []
    for hour, disposition in enumerate(dispositions):
        if hour:
            now[0] = f"2026-08-04T{hour:02}:00:00Z"
            acquired = application.acquire_change_action(_continuation_request(application, "change-a"))
            assert acquired.launch is not None, acquired
            launch = acquired.launch
        attempt_ids.append(launch.claim.attempt_id)
        if disposition == "normal-return":
            settlement = DeliveryBuilderInvocationSettlement(
                change_id=launch.change_id,
                outcome_id=launch.outcome_id,
                claim_id=launch.claim.claim_id,
                attempt_id=launch.claim.attempt_id,
                task_id=launch.task_id,
                expected_last_reviewed_commit=launch.last_reviewed_commit,
                disposition="normal-return",
                request=RetryDelivery(
                    action="retry",
                    outcome_id=launch.outcome_id,
                    claim_id=launch.claim.claim_id,
                    attempt_id=launch.claim.attempt_id,
                    abandoned_commit=_git(launch.worktree_path, "rev-parse", "HEAD"),
                    failure_code="builder-failed",
                ),
            )
        else:
            settlement = _requestless_builder_settlement(launch, disposition)
        _settle_builder_handoff_attempt(application, launch.claim, settlement)
        assert _workspace_content_snapshot(launch.worktree_path) == before_workspace

    binding = runtime.show_binding("OUT-001")
    assert binding.block is not None
    assert "three-attempt limit" in binding.block.reason
    ledger = runtime.retry_ledger().read()
    assert len(ledger.episodes) == 1
    episode = ledger.episodes[0]
    assert episode.total_attempts == 3
    assert episode.reset_count == 0
    assert episode.attempt_ids == tuple(attempt_ids)
    assert episode.stop_code is not None
    assert episode.stop_code.value == "retry-exhausted"
    now[0] = "2026-08-04T05:00:00Z"
    stopped = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert stopped.launch is None
    view = application.show_work_item_view("change-a", "outcome:OUT-001")
    assert view.readiness is not None
    assert view.readiness.reason_code == "retry-exhausted"
    assert view.readiness.executable is False
    assert _builder_retry_history(view.readiness.retry_history) == [
        (index + 1, "original" if index == 0 else "repair", "failed", code) for index, code in enumerate(expected_codes)
    ]


def test_exhausted_builder_return_to_planning_projects_read_only_diagnostic(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, coordinator, _state_root, first, _head, _workspace, retry_settlement = (
        _builder_retry_handoff_setup(tmp_path, now, add_workspace_changes=False)
    )
    builders = [first]
    _settle_builder_handoff_attempt(application, first.claim, retry_settlement)

    for hour in (1, 2):
        now[0] = f"2026-08-04T{hour:02}:00:00Z"
        acquired = application.acquire_change_action(_continuation_request(application, "change-a"))
        assert acquired.launch is not None, acquired
        builder = acquired.launch
        builders.append(builder)
        if hour == 1:
            retry_settlement = DeliveryBuilderInvocationSettlement(
                change_id=builder.change_id,
                outcome_id=builder.outcome_id,
                claim_id=builder.claim.claim_id,
                attempt_id=builder.claim.attempt_id,
                task_id=builder.task_id,
                expected_last_reviewed_commit=builder.last_reviewed_commit,
                disposition="normal-return",
                request=RetryDelivery(
                    action="retry",
                    outcome_id=builder.outcome_id,
                    claim_id=builder.claim.claim_id,
                    attempt_id=builder.claim.attempt_id,
                    abandoned_commit=builder.source_head,
                    failure_code="builder-failed",
                ),
            )
            _settle_builder_handoff_attempt(application, builder.claim, retry_settlement)
        else:
            settled, preserved_commit, _before_workspace, _reason = _return_builder(application, builder)
            assert settled.stage is DeliveryStage.PLANNING
            assert settled.builder_handoff_context is not None
            assert settled.builder_handoff_context.attempt_id == builder.claim.attempt_id
            assert settled.builder_handoff_context.branch_head == preserved_commit

    binding = runtime.show_binding("OUT-001")
    assert binding.block is not None
    assert binding.block.block_id.startswith("builder-planning-route-")
    assert binding.block.request_id is None
    assert binding.requests == ()
    assert binding.builder_handoff_context is not None
    episode = runtime.retry_ledger().episode_for_attempt(builders[-1].claim.attempt_id)
    assert episode is not None
    assert episode.total_attempts == 3
    assert episode.attempt_ids == tuple(builder.claim.attempt_id for builder in builders)
    assert episode.key.exact_head == builders[-1].last_reviewed_commit
    assert episode.reset_count == 0

    before_frontier = runtime.frontier_bytes()
    before_coordination = coordinator.show("change-a")
    before_ledger = runtime.retry_ledger().read()
    view = application.show_work_item_view("change-a", "outcome:OUT-001")
    assert view.readiness is not None
    assert view.readiness.reason_code == "retry-exhausted"
    assert view.readiness.attempts == 3
    assert view.readiness.operation is None
    assert not view.readiness.executable
    assert view.readiness.prompt is not None
    assert view.readiness.prompt.startswith("/inspect-change change-a")
    assert "read-only" in view.readiness.prompt
    assert view.card.next_actor.value == "agent"
    assert view.card.action.kind.value == "none"
    assert view.card.action.command is None
    assert runtime.frontier_bytes() == before_frontier
    assert coordinator.show("change-a") == before_coordination
    assert runtime.retry_ledger().read() == before_ledger


@pytest.mark.parametrize("writer_state", ["unchanged", "replaced"])
def test_handoff_pre_activation_cas_failure_refunds_only_unchanged_writer_reservation(
    tmp_path: Path,
    writer_state: Literal["unchanged", "replaced"],
) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, coordinator, state_root, first, _branch_head, _workspace, settlement = (
        _builder_retry_handoff_setup(
            tmp_path,
            now,
        )
    )
    _settle_builder_handoff_attempt(application, first.claim, settlement)
    ledger = runtime.retry_ledger()
    before_episode = ledger.read().episodes[0]
    before_pending = ledger.pending_attempts()
    before_frontier = runtime.frontier_bytes()
    before_coordination = coordinator.show("change-a")
    assert before_coordination.builder_handoff is not None
    assert before_coordination.writer == before_coordination.builder_handoff.original_writer.model_copy(
        update={"kind": "handoff"}
    )
    assert runtime.show_binding(first.outcome_id).builder_handoff_context is not None
    coordination_path = state_root / "coordination/changes/change-a.json"
    before_coordination_bytes = coordination_path.read_bytes()
    before_workspace = _workspace_content_snapshot(before_coordination.worktree_path)
    before_non_ledger_files = {
        path: content
        for path, content in _file_bytes(state_root).items()
        if not path.startswith("changes/change-a/retry-ledger/")
    }
    assert runtime.claimable_outcome_ids() == ("OUT-001",)

    def rank_handoff_first(candidate_runtime: DeliveryRuntime, outcome_id: str) -> int:
        return -1 if candidate_runtime.contract.change_id == "change-a" and outcome_id == "OUT-001" else 0

    with patch.object(application, "_dependency_depth", side_effect=rank_handoff_first):
        candidate = next(
            candidate
            for candidate in application._candidates("change-a")
            if candidate.binding.outcome_id == first.outcome_id
        )
    source = application._prepare_source(candidate, allow_dirty=True)
    assert not isinstance(source, DeliveryAcquisitionFailure), source.detail
    assert source.coordination.builder_handoff == before_coordination.builder_handoff

    now[0] = "2026-08-04T01:00:00Z"
    if writer_state == "replaced":
        replacement_writer = ChangeWriter(
            attempt_id="replacement-attempt",
            claim_id="replacement-claim",
            actor_id="replacement-host",
            process_id="replacement-session",
            claimed_at=now[0],
            job_id=1,
            kind="build",
        )
        with (
            patch.object(
                coordinator,
                "show",
                return_value=before_coordination.model_copy(update={"writer": replacement_writer}),
            ),
            patch.object(
                application,
                "_activate_candidate_claim",
                side_effect=OSError("injected interrupted claim activation"),
            ),
            pytest.raises(OSError, match="interrupted claim activation"),
        ):
            application._activate_candidate(candidate, source)
    else:
        with (
            patch.object(
                application._workspace_manager,
                "prepare_builder_handoff_acquisition",
                side_effect=OSError("injected handoff metadata compare-and-swap failure"),
            ),
            pytest.raises(OSError, match="metadata compare-and-swap failure"),
        ):
            application._activate_candidate(candidate, source)

    after_episode = ledger.read().episodes[0]
    assert runtime.frontier_bytes() == before_frontier
    assert coordinator.show("change-a") == before_coordination
    assert coordination_path.read_bytes() == before_coordination_bytes
    assert _workspace_content_snapshot(before_coordination.worktree_path) == before_workspace
    assert {
        path: content
        for path, content in _file_bytes(state_root).items()
        if not path.startswith("changes/change-a/retry-ledger/")
    } == before_non_ledger_files
    if writer_state == "replaced":
        assert after_episode.total_attempts == before_episode.total_attempts + 1
        assert after_episode.repair_attempts == before_episode.repair_attempts + 1
        assert len(ledger.pending_attempts()) == len(before_pending) + 1
    else:
        assert after_episode.total_attempts == before_episode.total_attempts
        assert after_episode.repair_attempts == before_episode.repair_attempts
        assert ledger.pending_attempts() == before_pending
    assert runtime.active_claims() == ()
    assert coordinator.show("change-a").writer.kind == "handoff"


def test_builder_settlement_replay_does_not_publish_unrelated_pending_state(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    runtime = runtimes["change-a"]
    builder = application.acquire_frontier_work().launch_packages[0]
    publisher = Mock()
    application._delivery_state_publisher = publisher
    settlement = DeliveryBuilderInvocationSettlement(
        change_id="change-a",
        outcome_id=builder.outcome_id,
        claim_id=builder.claim.claim_id,
        attempt_id=builder.claim.attempt_id,
        task_id=builder.task_id,
        expected_last_reviewed_commit=builder.last_reviewed_commit,
        disposition="normal-return",
        request=RetryDelivery(
            action="retry",
            outcome_id=builder.outcome_id,
            claim_id=builder.claim.claim_id,
            attempt_id=builder.claim.attempt_id,
            abandoned_commit=_git(builder.worktree_path, "rev-parse", "HEAD"),
        ),
    )

    result = application.settle_worker_invocation(
        settlement,
        host_id=builder.claim.owner_id,
        session_id=builder.claim.process_id,
    )
    assert result.active_claim is None
    publisher.publish.assert_not_called()
    publisher.reset_mock()
    runtime.queue_explicit_checkpoint(builder.last_reviewed_commit)
    frontier = runtime.frontier_bytes()
    accounting = runtime.retry_ledger().read()
    pending = runtime.pending_state_publication()
    assert pending is None
    assert runtime.checkpoint_publication_state().pending_checkpoint is not None

    assert (
        application.settle_worker_invocation(
            settlement,
            host_id=builder.claim.owner_id,
            session_id=builder.claim.process_id,
        )
        == result
    )
    assert runtime.frontier_bytes() == frontier
    assert runtime.retry_ledger().read() == accounting
    assert runtime.pending_state_publication() == pending
    publisher.publish.assert_not_called()


def _acknowledge_and_replay_planning_pause(
    tmp_path: Path,
    state_root: Path,
    runtimes: dict[str, DeliveryRuntime],
    application: PortfolioApplication,
    request: BlockDelivery,
) -> PortfolioApplication:
    publisher = Mock()
    application._delivery_state_publisher = publisher
    binding = application.transition_delivery("change-a", request)
    publisher.publish.assert_called_once()
    assert application._runtime("change-a").pending_state_publication() is None
    assert binding.block is not None
    assert binding.block.request_id == "decision-0"
    assert binding.requests[-1].resolution is None
    application, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes)
    runtime = application._runtime("change-a")
    before_replay = runtime.frontier_bytes()
    assert application.transition_delivery("change-a", request) == binding
    assert runtime.frontier_bytes() == before_replay
    return application


@pytest.mark.parametrize(
    ("owner", "crash_stage"),
    [
        (owner, stage)
        for owner in ("delivery-runtime", "retry-ledger")
        for stage in ("before-publication", "after-first-publication", "before-manifest-cleanup")
    ]
    + [("retry-ledger", "before-staging")],
)
def test_planning_pause_owner_result_replays_once(tmp_path: Path, owner: str, crash_stage: str) -> None:
    now = datetime(2026, 8, 4, tzinfo=UTC)

    def clock() -> str:
        return now.isoformat()

    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, clock=clock
    )
    _fail_planning_attempt(application, 0)
    ledger = RetryLedger(state_root, "change-a")
    prior = ledger.read().episodes[0]
    now += timedelta(seconds=1)
    claim = _acquire_planning_claim(application)
    request = _planning_decision_block(claim.claim_id, 0)
    original = RuntimeTransaction.commit
    interruptions = []

    def interrupted(transaction):
        def fail(stage):
            if stage == crash_stage:
                interruptions.append(stage)
                message = "injected pause interruption"
                raise OSError(message)

        if transaction._transaction_id.startswith(f"{owner}-") and not interruptions:
            fail("before-staging")
            original(transaction, failure=fail)
        else:
            original(transaction)

    expected = pytest.raises(OSError, match="injected pause") if owner == "delivery-runtime" else nullcontext()
    with patch.object(RuntimeTransaction, "commit", interrupted), expected:
        application.transition_delivery("change-a", request)
    assert interruptions == [crash_stage]
    application, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes, clock=clock)
    settled = ledger.read()
    episode = settled.episodes[0]
    assert episode.episode_id == prior.episode_id
    assert (episode.total_attempts, episode.repair_attempts, episode.reset_count) == (1, 0, 0)
    assert episode.accepted_attempt_ids == ()
    assert episode.last_failure_at == prior.last_failure_at
    assert episode.next_eligible_at == prior.next_eligible_at
    application = _acknowledge_and_replay_planning_pause(tmp_path, state_root, runtimes, application, request)
    assert ledger.read() == settled
    assert application.acquire_change_action(_continuation_request(application)).launch is None
    answer = DeliveryAnswer(
        change_id="change-a",
        kind=DeliveryAnswerKind.REQUEST,
        expected_frontier_digest=hashlib.sha256(runtimes["change-a"].frontier_bytes()).hexdigest(),
        request_id="decision-0",
        resolution=DeliveryRequestResolution(selected_option_id="proceed", provenance="user-confirmed"),
    )
    application.answer(answer)
    application.answer(answer)
    assert ledger.read() == settled
    resumed = _acquire_planning_claim(application)
    application, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes, clock=clock)
    assert ledger.read().episodes[0].total_attempts == 2
    assert tuple(attempt.attempt_id for attempt in ledger.pending_attempts()) == (resumed.attempt_id,)


def _assert_historical_planning_pause(application, request, paused, publisher):
    runtime = application._runtime("change-a")
    ledger = runtime.retry_ledger()
    frontier = runtime.frontier_bytes()
    accounting = ledger.read()
    publisher.reset_mock()
    assert application.transition_delivery("change-a", request) == paused
    assert runtime.frontier_bytes() == frontier
    assert ledger.read() == accounting
    publisher.publish.assert_not_called()


def test_planning_pause_replays_exactly_after_acknowledged_publication_and_resume(tmp_path: Path) -> None:
    now = datetime(2026, 8, 4, tzinfo=UTC)

    def clock() -> str:
        return now.isoformat()

    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, clock=clock
    )
    _fail_planning_attempt(application, 0)
    ledger = RetryLedger(state_root, "change-a")
    prior = ledger.read().episodes[0]
    now += timedelta(seconds=1)
    claim = _acquire_planning_claim(application)
    request = _planning_decision_block(claim.claim_id, 0)
    publisher = Mock()
    application._delivery_state_publisher = publisher

    paused = application.transition_delivery("change-a", request)
    publisher.publish.assert_called_once()
    assert runtimes["change-a"].pending_state_publication() is None
    assert paused.block is not None
    assert paused.block.request_id == "decision-0"
    assert paused.requests[-1].resolution is None
    settled = ledger.read()
    assert settled.episodes[0].total_attempts == prior.total_attempts
    assert settled.episodes[0].accepted_attempt_ids == prior.accepted_attempt_ids

    application, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes)
    publisher.reset_mock()
    application._delivery_state_publisher = publisher
    runtime = application._runtime("change-a")
    before_replay = runtime.frontier_bytes()
    assert application.transition_delivery("change-a", request) == paused
    assert runtime.frontier_bytes() == before_replay
    publisher.publish.assert_not_called()
    with pytest.raises(DeliveryRuntimeConflictError):
        application.transition_delivery("change-a", request.model_copy(update={"reason": "Changed reason"}))
    with pytest.raises(DeliveryRuntimeConflictError):
        application.transition_delivery("change-a", request.model_copy(update={"claim_id": "foreign-claim"}))
    assert runtime.frontier_bytes() == before_replay
    assert application.acquire_change_action(_continuation_request(application)).launch is None

    answer = DeliveryAnswer(
        change_id="change-a",
        kind=DeliveryAnswerKind.REQUEST,
        expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
        request_id="decision-0",
        resolution=DeliveryRequestResolution(selected_option_id="proceed", provenance="user-confirmed"),
    )
    application.answer(answer)
    application.answer(answer)
    _assert_historical_planning_pause(application, request, paused, publisher)

    resumed = _acquire_planning_claim(application)
    _assert_historical_planning_pause(application, request, paused, publisher)
    after_reacquire = runtime.frontier_bytes()
    current = DeliveryFrontier.model_validate_json(after_reacquire, strict=True).bindings[0]
    assert current.active_claim == resumed
    assert current.requests[-1].resolution == answer.resolution


@pytest.mark.parametrize("writer_recorded", [False, True])
def test_batch_failed_activation_retains_execution_capacity(tmp_path: Path, *, writer_recorded: bool) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION, "change-b": DeliveryStage.IMPLEMENTATION},
        execution_capacity=1,
    )
    acquire = coordinator.acquire

    def fail(change_id, writer, **kwargs):
        if writer_recorded:
            acquire(change_id, writer, **kwargs)
        message = "writer activation interrupted"
        raise OSError(message)

    with patch.object(coordinator, "acquire", fail):
        result = application.acquire_frontier_work()
    assert result.launch_packages == ()
    assert len(result.failures) == 1
    assert runtimes["change-a"].active_claims()
    assert runtimes["change-b"].active_claims() == ()
    assert application._execution_occupancy() == 1


@pytest.mark.parametrize("failure", ["recount", "activation"])
def test_batch_failure_returns_already_acquired_launches(tmp_path: Path, failure: str) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.IMPLEMENTATION,
            "change-b": DeliveryStage.IMPLEMENTATION,
            "change-c": DeliveryStage.IMPLEMENTATION,
        },
    )
    acquire = coordinator.acquire
    registered = coordinator.list_registered
    unavailable = False

    def fail_second_writer(change_id, writer, **kwargs):
        nonlocal unavailable
        if change_id == "change-b":
            unavailable = True
            message = "writer storage unavailable"
            raise OSError(message)
        return acquire(change_id, writer, **kwargs)

    def list_registered():
        if unavailable:
            message = "coordination storage unavailable"
            raise OSError(message)
        return registered()

    if failure == "recount":
        with (
            patch.object(coordinator, "acquire", fail_second_writer),
            patch.object(coordinator, "list_registered", list_registered),
        ):
            result = application.acquire_frontier_work()
    else:
        with patch.object(runtimes["change-b"], "activate_claim", side_effect=OSError("activation unavailable")):
            result = application.acquire_frontier_work()
    assert len(result.launch_packages) == 1
    launch = result.launch_packages[0]
    assert launch.change_id == "change-a"
    assert runtimes["change-a"].show_binding("OUT-001").active_claim == launch.claim
    assert coordinator.show("change-a").writer.claim_id == launch.claim.claim_id
    assert bool(runtimes["change-b"].active_claims()) is (failure == "recount")
    assert runtimes["change-c"].active_claims() == ()
    assert result.failures[-1].change_id == "portfolio"
    assert "Preserve all existing claims" in result.failures[-1].retry_condition


def test_interrupted_engine_reservation_waits_for_no_launch_backoff(tmp_path: Path) -> None:
    now = {"value": "2026-08-04T00:00:00Z"}

    def clock() -> str:
        return now["value"]

    application, runtime, provider, _state, _head, state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False, clock=clock
    )
    assert application.acquire_change_action(_continuation_request(application)).kind == "reconciled"
    with (
        patch.object(
            application._coordinator, "acquire_continuation_action", side_effect=OSError("interrupted intent")
        ),
        pytest.raises(OSError, match="interrupted intent"),
    ):
        application.acquire_change_action(_continuation_request(application))
    before = RetryLedger(state_root, "change-a").read()
    assert before.episodes[0].total_attempts == 1
    assert before.episodes[0].last_status == "failed"
    assert before.episodes[0].next_eligible_at == "2026-08-04T00:00:01Z"
    reopened, _, _ = _reopen_portfolio(tmp_path, state_root, {"change-a": runtime}, clock=clock)
    reopened._draft_pull_request_publisher = application._draft_pull_request_publisher
    before_backoff = reopened.acquire_change_action(_continuation_request(reopened, session_id="fresh-session"))
    assert before_backoff.kind == "waiting"
    assert before_backoff.reason_code == "retry-backoff"
    now["value"] = "2026-08-04T00:00:01Z"
    retried = reopened.acquire_change_action(_continuation_request(reopened, session_id="fresh-session"))
    assert retried.kind == "acquired"
    assert retried.engine_action is not None
    after = RetryLedger(state_root, "change-a").read()
    assert after.episodes[0].total_attempts == 2
    assert retried.engine_action.operation_id in after.episodes[0].attempt_ids
    assert provider.set_pull_request_draft_state.call_count == 0


def test_worker_preflight_read_failure_does_not_reserve_an_attempt(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    candidate = application._candidates()[0]
    source = application._prepare_source(candidate)
    assert not isinstance(source, DeliveryAcquisitionFailure)
    with (
        patch.object(candidate.runtime, "frontier_bytes", side_effect=OSError("preflight read failed")),
        pytest.raises(OSError, match="preflight read failed"),
    ):
        application._activate_candidate(candidate, source)
    assert RetryLedger(state_root, "change-a").read().episodes == ()
    assert runtimes["change-a"].active_claims() == ()
    assert coordinator.show("change-a").writer is None
    reopened, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes)
    acquired = reopened.acquire_change_action(_continuation_request(reopened))
    assert acquired.launch is not None


@pytest.mark.parametrize("stage", [DeliveryStage.PLANNING, DeliveryStage.COMPLETED])
def test_worker_and_finalizer_no_launch_retries_wait_for_backoff(tmp_path: Path, stage) -> None:
    current_time = ["2026-08-04T00:00:00Z"]

    def clock() -> str:
        return current_time[0]

    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": stage}, clock=clock)
    if stage is DeliveryStage.PLANNING:
        with (
            patch.object(
                runtimes["change-a"],
                "activate_claim",
                side_effect=OSError("interrupted owner publication"),
            ) as injected,
            pytest.raises(OSError, match="interrupted owner"),
        ):
            application.acquire_change_action(_continuation_request(application))
    else:
        with patch.object(
            coordinator,
            "_acquire",
            side_effect=CoordinationConflictError("interrupted owner publication"),
        ) as injected:
            result = application.acquire_change_action(_continuation_request(application))
        assert result.kind == "unavailable"
        assert result.reason_code == "workspace-preflight-failed"
        assert result.launch is None
        assert result.finalization is None
    injected.assert_called_once()
    ledger = RetryLedger(state_root, "change-a")
    before = ledger.read()
    assert before.episodes[0].total_attempts == 1
    assert before.episodes[0].last_status == "failed"
    assert before.episodes[0].next_eligible_at == "2026-08-04T00:00:01Z"
    too_soon = ledger.reserve(
        before.episodes[0].key,
        failure_class=before.episodes[0].failure_class,
        now=current_time[0],
        attempt_id="too-soon",
    )
    assert not too_soon.allowed
    assert too_soon.reason_code == "retry-backoff"
    current_time[0] = before.episodes[0].next_eligible_at
    reopened, reopened_coordinator, _manager = _reopen_portfolio(tmp_path, state_root, runtimes, clock=clock)
    retried = reopened.acquire_change_action(_continuation_request(reopened, session_id="new-session"))
    after = ledger.read()
    assert after.episodes[0].total_attempts == 2
    assert len(after.episodes[0].attempt_ids) == 2
    if stage is DeliveryStage.PLANNING:
        assert retried.launch is not None
        assert retried.launch.claim.attempt_id in after.episodes[0].attempt_ids
        assert reopened_coordinator.show("change-a").writer is None
        active_claims = runtimes["change-a"].active_claims()
        assert len(active_claims) == 1
        assert active_claims[0][1] == retried.launch.claim
    else:
        assert retried.finalization is not None
        assert retried.finalization.attempt.writer.attempt_id in after.episodes[0].attempt_ids
        assert reopened_coordinator.show("change-a").writer == retried.finalization.attempt.writer
        assert runtimes["change-a"].active_claims() == ()


@pytest.mark.parametrize("stage", [DeliveryStage.PLANNING, DeliveryStage.COMPLETED])
def test_committed_worker_or_finalizer_publication_error_keeps_reservation_pending(tmp_path: Path, stage) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": stage})
    owner = runtimes["change-a"] if stage is DeliveryStage.PLANNING else coordinator
    operation = "activate_claim" if stage is DeliveryStage.PLANNING else "_acquire"
    publish = getattr(owner, operation)
    message = "owner publication response lost"

    def publish_then_raise(*args, **kwargs):
        publish(*args, **kwargs)
        raise OSError(message)

    with (
        patch.object(owner, operation, side_effect=publish_then_raise) as injected,
        pytest.raises(OSError, match="owner publication response lost"),
    ):
        application.acquire_change_action(_continuation_request(application))
    injected.assert_called_once()

    ledger = RetryLedger(state_root, "change-a")
    pending_ids = {attempt.attempt_id for attempt in ledger.pending_attempts()}
    assert len(pending_ids) == 1
    if stage is DeliveryStage.PLANNING:
        active_claims = runtimes["change-a"].active_claims()
        assert len(active_claims) == 1
        assert active_claims[0][1].attempt_id in pending_ids
        assert coordinator.show("change-a").writer is None
    else:
        writer = coordinator.show("change-a").writer
        assert writer is not None
        assert writer.attempt_id in pending_ids
        assert runtimes["change-a"].active_claims() == ()


def test_recovered_finalizer_acquisition_keeps_reservation_pending(tmp_path: Path) -> None:
    application, _runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    original_commit = RuntimeTransaction.commit
    message = "injected finalizer acquisition interruption"

    def interrupted(transaction):
        def fail(stage: str) -> None:
            if stage == "before-publication" and transaction._transaction_id.startswith("portfolio-acquire-change-a-"):
                raise RuntimeError(message)

        original_commit(transaction, failure=fail)

    with (
        patch.object(RuntimeTransaction, "commit", interrupted),
        pytest.raises(RuntimeError, match=message),
    ):
        application.acquire_change_action(_continuation_request(application))

    pending = RetryLedger(state_root, "change-a").pending_attempts()
    writer = coordinator.show("change-a").writer
    assert writer is not None
    assert tuple(item.attempt_id for item in pending) == (writer.attempt_id,)


def test_committed_engine_action_publication_error_keeps_reservation_pending(tmp_path: Path) -> None:
    application, runtime, _provider, _state, _head, _state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False
    )
    assert application.acquire_change_action(_continuation_request(application)).kind == "reconciled"
    publish = application._coordinator.acquire_continuation_action
    message = "engine owner publication response lost"

    def publish_then_raise(action: ChangeContinuationAction) -> None:
        publish(action)
        raise OSError(message)

    with (
        patch.object(application._coordinator, "acquire_continuation_action", side_effect=publish_then_raise),
        pytest.raises(OSError, match="engine owner publication response lost"),
    ):
        application.acquire_change_action(_continuation_request(application))

    action = application._coordinator.show("change-a").continuation_action
    assert action is not None
    assert action.finished_at is None
    assert {attempt.attempt_id for attempt in runtime.retry_ledger().pending_attempts()} == {action.operation_id}


def test_existing_finalization_receipt_reconciles_accounting_without_marker(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    attempt = application.acquire_change_action(_continuation_request(application)).finalization.attempt
    with patch.object(RetryLedger, "record_accepted_progress", side_effect=OSError("interrupted accounting")):
        application.finalize_change(
            "change-a", _finalization_request("change-a", attempt.exact_head, attempt.writer.attempt_id)
        )
    # A previous B version wrote finalization receipts without this companion.
    (state_root / "changes/change-a/retry-ledger/owner-results" / f"{attempt.writer.attempt_id}.json").unlink()
    _reopen_portfolio(tmp_path, state_root, runtimes)
    episode = RetryLedger(state_root, "change-a").read().episodes[0]
    assert episode.reset_count == 1
    assert episode.accepted_attempt_ids == (attempt.writer.attempt_id,)


@pytest.mark.parametrize("original_claim", [False, True])
def test_existing_builder_receipt_requires_original_claim_for_accounting(
    tmp_path: Path, *, original_claim: bool
) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    runtime = runtimes["change-a"]
    launch = application.acquire_change_action(_continuation_request(application)).launch
    _git(launch.worktree_path, "commit", "--allow-empty", "-m", "complete task")
    submission = DeliveryResultSubmission(
        change_id="change-a",
        outcome_id=launch.outcome_id,
        claim_id=launch.claim.claim_id,
        result=_task_result(
            "existing-builder-result",
            "change-a",
            runtime.authority_digest,
            runtime.show_binding(launch.outcome_id).tasks[0],
            _git(launch.worktree_path, "rev-parse", "HEAD"),
        ),
    )
    with patch.object(RetryLedger, "record_accepted_progress", side_effect=OSError("interrupted accounting")):
        application.submit_result(submission)
    (state_root / "changes/change-a/retry-ledger/owner-results" / f"{launch.claim.attempt_id}.json").unlink()
    if not original_claim:
        (receipt_path,) = (state_root / "changes/change-a/result-receipts/OUT-001").glob("*.json")
        receipt = json.loads(receipt_path.read_bytes())
        receipt["claim_id"] = "another-claim"
        receipt_path.write_text(json.dumps(receipt))
    _reopen_portfolio(tmp_path, state_root, runtimes)
    episode = RetryLedger(state_root, "change-a").read().episodes[0]
    assert episode.reset_count == (1 if original_claim else 0)
    assert episode.total_attempts == (0 if original_claim else 1)


def test_block_accounting_failure_still_publishes_and_replays_without_refund(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    launch = application.acquire_change_action(_continuation_request(application)).launch
    request = BlockDelivery(
        action="block",
        outcome_id="OUT-001",
        claim_id=launch.claim.claim_id,
        block_id="blocked-check",
        reason="Check failed",
        unblock_condition="Check prerequisite available",
        expected_evidence=("check",),
        locators=("check",),
    )
    with (
        patch.object(RetryLedger, "record_failure", side_effect=OSError("injected accounting failure")),
        patch.object(application, "_publish_delivery_state", wraps=application._publish_delivery_state) as publish,
    ):
        blocked = application.transition_delivery("change-a", request)
    publish.assert_called_once()
    assert blocked.active_claim is None
    assert runtimes["change-a"].show_binding("OUT-001") == blocked
    ledger = RetryLedger(state_root, "change-a")
    reserved = ledger.read().episodes[0]
    assert reserved.total_attempts == 1
    assert reserved.last_status == "reserved"
    assert reserved.outcome_ids == ()
    reopened, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes)
    accounted = ledger.read().episodes[0]
    assert accounted.total_attempts == 1
    assert accounted.reset_count == 0
    assert accounted.last_status == "failed"
    assert len(accounted.outcome_ids) == 1
    assert reopened.transition_delivery("change-a", request) == blocked
    assert ledger.read().episodes[0] == accounted


def builder_transition_case(tmp_path: Path, action: str):
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    launch = application.acquire_frontier_work().launch_packages[0]
    head = _git(launch.worktree_path, "rev-parse", "HEAD")
    common = {
        "outcome_id": "OUT-001",
        "claim_id": launch.claim.claim_id,
        "reason": "Cannot proceed.",
        "locators": ("TASK-001",),
    }
    transition = (
        BlockDelivery(
            action="block",
            block_id="blocked",
            unblock_condition="Prerequisite repaired.",
            expected_evidence=("Proof",),
            resume_commit=head,
            request=DeliveryRequest(
                request_id="diagnostic-only",
                kind=DeliveryRequestKind.ACTION,
                outcome_id="OUT-001",
                summary="Repair prerequisite.",
            ),
            **common,
        )
        if action == "block"
        else ReturnDelivery(
            action="return",
            target=DeliveryStage.PLANNING,
            preserved_commit=head,
            attempt_id=launch.claim.attempt_id,
            **common,
        )
    )
    return application, runtimes, coordinator, state_root, launch, transition


def _assert_contained_builder_views(
    application: PortfolioApplication, transition: BlockDelivery | ReturnDelivery, claim: DeliveryActiveClaim
) -> None:
    change = application.get_change("change-a")
    detail = application.show_work_item_view("change-a", f"outcome:{transition.outcome_id}")
    operator = application.show_operator_context("change-a", transition.outcome_id)
    for readiness in (change.readiness, detail.readiness):
        assert readiness.status == "blocked"
        assert readiness.reason_code == "builder-transition-contained"
        assert not readiness.executable
        assert readiness.operation is None
        assert readiness.action is None
        assert "read-only" in readiness.prompt
        assert "host worker-exclusion evidence is missing" in readiness.prompt
        assert "does not establish" in readiness.prompt
    for attention in (
        detail.recovery_attention,
        operator.recovery_attention,
        change.unresolved_outcomes[0].recovery_attention,
    ):
        assert attention.diagnostic_transition == transition
        assert attention.custody_retained
        assert attention.claim_id == claim.claim_id
        assert attention.attempt_id == claim.attempt_id
    assert operator.active_claim.owner_id == claim.owner_id
    assert operator.block is None
    assert operator.requests == ()
    assert operator.return_context is None
    assert detail.block is None
    assert detail.requests == ()
    assert detail.return_context is None
    assert detail.card.action.kind == "none"
    assert detail.card.needs == "none"
    assert detail.card.activity.state == "idle"
    assert claim.owner_id in detail.card.next_step
    assert transition.reason in detail.card.next_step
    assert "Host worker-exclusion evidence is missing" in detail.card.next_step
    assert application.show_work_item("change-a", transition.outcome_id).projection.next_action == detail.card.next_step


@pytest.mark.parametrize("kind", ["block", "return", "retry"])
def test_refused_builder_transition_does_not_refresh_stat_dirty_index(tmp_path: Path, kind: str) -> None:
    application, runtimes, coordinator, state_root, launch, transition = builder_transition_case(tmp_path, kind)
    if kind == "retry":
        transition = RetryDelivery(
            action="retry",
            outcome_id=launch.outcome_id,
            claim_id=launch.claim.claim_id,
            abandoned_commit=launch.last_reviewed_commit,
            attempt_id=launch.claim.attempt_id,
        )
    before_frontier = runtimes["change-a"].frontier_bytes()
    product = launch.worktree_path / "product.txt"
    before_product = product.read_bytes()
    metadata = product.stat()
    os.utime(product, ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 10_000_000_000))
    index = Path(_git(launch.worktree_path, "rev-parse", "--path-format=absolute", "--git-path", "index"))
    before_index = index.read_bytes()
    before_index_mtime = index.stat().st_mtime_ns
    before_coordination = coordinator.show("change-a")
    retry_ledger = RetryLedger(state_root, "change-a")
    before_retry_ledger = retry_ledger.read()
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application.transition_delivery("change-a", transition)
    assert index.read_bytes() == before_index
    assert index.stat().st_mtime_ns == before_index_mtime
    assert product.read_bytes() == before_product
    assert coordinator.show("change-a") == before_coordination
    assert retry_ledger.read() == before_retry_ledger
    assert runtimes["change-a"].show_binding("OUT-001").active_claim == launch.claim
    if kind == "retry":
        before_payload = json.loads(before_frontier)
        after_payload = json.loads(runtimes["change-a"].frontier_bytes())
        assert after_payload["bindings"][0]["retry_diagnostic"] == {
            "code": "ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED",
            "attempt_id": launch.claim.attempt_id,
            "transition": transition.model_dump(mode="json"),
        }
        assert "retry_diagnostic" not in before_payload["bindings"][0]
        after_payload["bindings"][0].pop("retry_diagnostic")
        assert after_payload == before_payload


def test_change_selection_prioritizes_contained_builder_over_other_outcomes(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root, _launch, transition = builder_transition_case(tmp_path, "block")
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application.transition_delivery("change-a", transition)
    snapshot = application._delivery_snapshot(runtimes["change-a"])
    card = application.show_work_item_view("change-a", "outcome:OUT-001").card
    other = card.model_copy(
        update={
            "item_key": "outcome:OUT-002",
            "work_item_id": "OUT-002",
            "readiness": card.readiness.model_copy(update={"status": "complete", "reason_code": "change-terminal"}),
        }
    )
    assert application._selected_change_card(snapshot, (other, card)) == card


def test_builder_return_without_exclusion_keeps_custody_and_retry_reservation(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    planner = application.acquire_change_action(_continuation_request(application)).launch
    candidate = application.publish_delivery_plan(
        "change-a",
        PublishDeliveryPlan(outcome_id=planner.outcome_id, claim_id=planner.claim.claim_id, tasks=(_task(),)),
    )
    application.transition_delivery(
        "change-a",
        AdvanceDelivery(
            action="advance",
            outcome_id=planner.outcome_id,
            claim_id=planner.claim.claim_id,
            output=candidate.output,
        ),
    )
    builder_result = application.acquire_change_action(_continuation_request(application))
    if builder_result.kind == "reconciled":
        builder_result = application.acquire_change_action(_continuation_request(application))
    builder = builder_result.launch
    preserved_commit = _git(builder.worktree_path, "rev-parse", "HEAD")
    request = ReturnDelivery(
        action="return",
        outcome_id=builder.outcome_id,
        claim_id=builder.claim.claim_id,
        target=DeliveryStage.PLANNING,
        reason="The Builder needs a revised plan.",
        locators=("TASK-001",),
        preserved_commit=preserved_commit,
        attempt_id=builder.claim.attempt_id,
    )

    ledger = RetryLedger(state_root, "change-a")
    before_frontier = runtimes["change-a"].frontier_bytes()
    before_coordination = coordinator.show("change-a")
    before_ledger = ledger.read()
    reserved = next(item for item in before_ledger.episodes if item.key.procedure_class == "builder")
    assert reserved.total_attempts == 1
    assert reserved.last_status == "reserved"
    assert reserved.outcome_ids == ()

    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application.transition_delivery("change-a", request)

    before = DeliveryFrontier.model_validate_json(before_frontier)
    after = DeliveryFrontier.model_validate_json(runtimes["change-a"].frontier_bytes())
    assert after.bindings[0].recovery_attention.diagnostic_transition == request
    assert (
        after.model_copy(
            update={
                "bindings": tuple(binding.model_copy(update={"recovery_attention": None}) for binding in after.bindings)
            }
        )
        == before
    )
    assert coordinator.show("change-a") == before_coordination
    assert ledger.read() == before_ledger
    owner_result = state_root / "changes/change-a/retry-ledger/owner-results" / f"{builder.claim.attempt_id}.json"
    assert not owner_result.exists()


@pytest.mark.parametrize("dirty", [False, True])
def test_builder_return_stays_contained_after_reload_and_elapsed_backoff(tmp_path: Path, *, dirty: bool) -> None:
    now = datetime(2026, 8, 4, tzinfo=UTC)

    def clock() -> str:
        return now.isoformat()

    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
        clock=clock,
    )
    planner = application.acquire_change_action(_continuation_request(application)).launch
    candidate = application.publish_delivery_plan(
        "change-a",
        PublishDeliveryPlan(outcome_id=planner.outcome_id, claim_id=planner.claim.claim_id, tasks=(_task(),)),
    )
    application.transition_delivery(
        "change-a",
        AdvanceDelivery(
            action="advance",
            outcome_id=planner.outcome_id,
            claim_id=planner.claim.claim_id,
            output=candidate.output,
        ),
    )
    builder_result = application.acquire_change_action(_continuation_request(application))
    if builder_result.kind == "reconciled":
        builder_result = application.acquire_change_action(_continuation_request(application))
    builder = builder_result.launch
    assert builder is not None
    request = ReturnDelivery(
        action="return",
        outcome_id=builder.outcome_id,
        claim_id=builder.claim.claim_id,
        target=DeliveryStage.PLANNING,
        reason="The Builder needs a revised plan.",
        locators=("TASK-001",),
        preserved_commit=_git(builder.worktree_path, "rev-parse", "HEAD"),
        attempt_id=builder.claim.attempt_id,
    )
    if dirty:
        product = builder.worktree_path / "product.txt"
        product.write_text("staged Builder work\n", encoding="utf-8")
        _git(builder.worktree_path, "add", product.name)
        product.write_text("unstaged Builder work\n", encoding="utf-8")
    before_workspace = _workspace_mutation_snapshot(builder.worktree_path)
    before_coordination = coordinator.show("change-a")
    ledger = RetryLedger(state_root, "change-a")
    before_ledger = ledger.read()
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application.transition_delivery("change-a", request)

    attention = runtimes["change-a"].show_binding("OUT-001").recovery_attention
    assert attention is not None
    assert attention.reason == request.reason

    retained_frontier = runtimes["change-a"].frontier_bytes()
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application.transition_delivery("change-a", request)
    assert runtimes["change-a"].frontier_bytes() == retained_frontier
    now += timedelta(days=1)
    reopened, reopened_coordinator, _manager = _reopen_portfolio(tmp_path, state_root, runtimes, clock=clock)
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        reopened.transition_delivery("change-a", request)
    _assert_contained_builder_views(reopened, request, builder.claim)
    result = reopened.acquire_change_action(_continuation_request(reopened, session_id="fresh-session"))

    assert result.launch is None
    assert result.readiness.status == "blocked"
    assert result.readiness.reason_code == "builder-transition-contained"
    assert not result.readiness.executable
    assert result.readiness.action is None
    assert result.readiness.prompt is not None
    assert "read-only" in result.readiness.prompt
    assert reopened._runtimes["change-a"].show_binding("OUT-001").active_claim.claim_id == builder.claim.claim_id
    assert reopened_coordinator.show("change-a").writer.claim_id == builder.claim.claim_id
    assert reopened_coordinator.show("change-a") == before_coordination
    assert reopened._runtimes["change-a"].frontier_bytes() == retained_frontier
    assert _workspace_mutation_snapshot(builder.worktree_path) == before_workspace
    assert ledger.read() == before_ledger


@pytest.mark.parametrize("restart_during_execution", [False, True])
def test_engine_executor_excludes_second_host_without_holding_portfolio_lock(
    tmp_path: Path, *, restart_during_execution: bool
) -> None:
    application, runtime, provider, _state, _head, state_root = _awaiting_acceptance_fixture(tmp_path, mark_ready=False)
    action = _engine_action(application)
    if not restart_during_execution:
        reopened, _coordinator, _manager = _reopen_portfolio(tmp_path, state_root, {"change-a": runtime})
    entered, release = Event(), Event()
    original = provider.set_pull_request_draft_state.side_effect

    def blocked(request):
        entered.set()
        assert release.wait(timeout=5)
        return original(request)

    provider.set_pull_request_draft_state.side_effect = blocked
    with ThreadPoolExecutor(max_workers=1) as executor:
        running = executor.submit(_execute_engine, application, action)
        try:
            assert entered.wait(timeout=5)
            if restart_during_execution:
                reopened, _coordinator, _manager = _reopen_portfolio(tmp_path, state_root, {"change-a": runtime})
            with (
                locked_roots((state_root / "claims/acquisition-lock",), blocking=False),
                pytest.raises(DeliveryActionBusyError),
            ):
                _execute_engine(reopened, action)
            with pytest.raises(CoordinationConflictError, match="continuation action custody"):
                runtime.queue_explicit_checkpoint("f" * 40)
        finally:
            release.set()
        assert running.result(timeout=5).kind == "completed"
    assert provider.set_pull_request_draft_state.call_count == 1


@pytest.mark.parametrize("conflict", [False, True])
def test_engine_target_fetch_drift_is_stale_then_syncs_exact_target(tmp_path: Path, *, conflict: bool) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    runtime = runtimes["change-a"]
    head = coordinator.show("change-a").last_reviewed_commit
    if conflict:
        head = _commit_reviewed_head(
            application, coordinator.show("change-a"), "product.txt", "Change implementation\n", "Change edit"
        )
    _set_checkpoint(
        runtime,
        state_root,
        DeliveryPendingCheckpoint(
            head=head,
            triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
        ),
    )
    _provider, remote = _attach_engine_publication(application, tmp_path)
    assert _execute_engine(application, _engine_action(application)).kind == "completed"
    action = _engine_action(application)
    target = _advance_remote_target(tmp_path, remote, product="Competing target edit\n" if conflict else None)
    stale = _execute_engine(application, action)
    assert stale.kind == "stale", stale
    repository = application._workspace_manager.repository
    assert _git(repository, "rev-parse", "refs/remotes/origin/main") == action.target_head
    started_path = coordinator.continuation_record_path("change-a", action.operation_id).with_name("started.json")
    assert started_path.is_file()
    pending_attempt_ids = {attempt.attempt_id for attempt in RetryLedger(state_root, "change-a").pending_attempts()}
    assert action.operation_id in pending_attempt_ids
    assert coordinator.show("change-a").last_reviewed_commit == action.exact_head
    fresh = _engine_action(application)
    assert fresh.operation_id != action.operation_id
    assert fresh.target_head == target
    synchronized = _execute_engine(application, fresh)
    if conflict:
        assert synchronized.kind == "blocked", synchronized
        assert synchronized.failure.code == "ERR_TARGET_SYNC_CONFLICT"
        coordination = coordinator.show("change-a")
        assert coordination.continuation_action == fresh
        assert coordination.target_sync_conflict.operation_id == fresh.operation_id
        assert _git(coordination.worktree_path, "rev-parse", "MERGE_HEAD") == target
        assert _execute_engine(application, fresh) == synchronized
        assert application.acquire_change_action(_continuation_request(application)).kind == "unavailable"
        return
    assert synchronized.kind == "completed", synchronized
    assert synchronized.target_sync.target_head == target
    assert synchronized.target_sync.merged_head != action.exact_head
    assert _execute_engine(application, fresh) == synchronized


@pytest.mark.parametrize("exit_kind", ["resolve", "abort"])
def test_engine_target_sync_conflict_exit_releases_retained_engine_custody(tmp_path: Path, exit_kind: str) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    runtime = runtimes["change-a"]
    head = _commit_reviewed_head(
        application, coordinator.show("change-a"), "product.txt", "Change implementation\n", "Change edit"
    )
    _set_checkpoint(
        runtime,
        state_root,
        DeliveryPendingCheckpoint(
            head=head,
            triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
        ),
    )
    _provider, remote = _attach_engine_publication(application, tmp_path)
    assert _execute_engine(application, _engine_action(application)).kind == "completed"
    stale = _engine_action(application)
    target = _advance_remote_target(tmp_path, remote, product="Competing target edit\n")
    assert _execute_engine(application, stale).kind == "stale"
    action = _engine_action(application)
    assert action.target_head == target
    blocked = _execute_engine(application, action)
    assert blocked.kind == "blocked", blocked
    assert blocked.failure.code == "ERR_TARGET_SYNC_CONFLICT"
    readiness = application.get_change("change-a").readiness
    assert readiness.reason_code == "engine-action-failed"
    assert readiness.prompt.startswith("/resolve-target-conflict change-a ")
    disposition_id = runtime.change_disposition().disposition_id
    worktree = Path(coordinator.show("change-a").worktree_path)
    intent = coordinator.continuation_record_path("change-a", action.operation_id)
    result = coordinator.continuation_record_path("change-a", action.operation_id, result=True)
    journals = (intent.read_bytes(), result.read_bytes())

    if exit_kind == "resolve":
        (worktree / "product.txt").write_text("Change implementation\nCompeting target edit\n")
        _git(worktree, "add", "product.txt")
        receipt = application.resolve_target_sync_conflict("change-a", disposition_id, target, action.operation_id)
        assert receipt.target_head == target
        assert _git(worktree, "rev-parse", "HEAD") == receipt.merged_head
    else:
        application.abort_target_sync_conflict("change-a", disposition_id, target, action.operation_id)
        assert _git(worktree, "rev-parse", "HEAD") == action.exact_head

    assert coordinator.show("change-a").continuation_action is None
    assert (intent.read_bytes(), result.read_bytes()) == journals
    assert runtime.change_disposition() is None
    assert application.get_change("change-a").readiness.reason_code != "engine-action-failed"
    assert _execute_engine(application, action) == blocked
    following = application.acquire_change_action(_continuation_request(application))
    assert following.kind != "unavailable", following
    assert following.engine_action is None or following.engine_action.operation_id != action.operation_id


def test_engine_exact_sync_after_remote_rewind_selects_the_rewound_target(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    _set_checkpoint(
        runtimes["change-a"],
        state_root,
        DeliveryPendingCheckpoint(
            head=coordinator.show("change-a").last_reviewed_commit,
            triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
        ),
    )
    _provider, remote = _attach_engine_publication(application, tmp_path)
    assert _execute_engine(application, _engine_action(application)).kind == "completed"
    repository = application._workspace_manager.repository
    initial = _git(remote, "rev-parse", "refs/heads/main")
    (tmp_path / "abandoned").mkdir()
    (tmp_path / "replacement").mkdir()
    abandoned = _advance_remote_target(tmp_path / "abandoned", remote, product="Abandoned target edit\n")
    _git(repository, "fetch", "origin", "+refs/heads/main:refs/remotes/origin/main")
    _git(remote, "update-ref", "refs/heads/main", initial)
    replacement = _advance_remote_target(tmp_path / "replacement", remote)
    action = _engine_action(application)
    assert action.kind == "sync-target"
    assert action.target_head == abandoned

    assert _execute_engine(application, action).kind == "stale"
    assert _git(repository, "rev-parse", "refs/remotes/origin/main") == abandoned
    fresh = _engine_action(application)
    assert fresh.target_head == replacement
    synchronized = _execute_engine(application, fresh)

    assert synchronized.kind == "completed", synchronized
    assert synchronized.target_sync.target_head == replacement
    assert _git(repository, "rev-parse", "refs/remotes/origin/main") == replacement
    assert application.get_change("change-a").readiness.basis.target_head == replacement
    following = application.acquire_change_action(_continuation_request(application))
    assert following.kind != "stale", following
    assert following.engine_action is None or following.engine_action.target_head == replacement


def test_continuation_finalizer_survives_restart_and_completes_exactly_once(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.COMPLETED, "change-b": DeliveryStage.PLANNING}
    )
    request = _continuation_request(application)
    acquired = application.acquire_change_action(request)
    assert acquired.kind == "acquired"
    assert acquired.launch is None
    attempt = acquired.finalization.attempt
    assert coordinator.show("change-a").writer == attempt.writer
    assert application.get_change("change-a").readiness.status == "running"
    assert application.get_change("change-a").finalization_attempt == attempt
    reopened, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes)
    assert reopened.acquire_change_action(request).kind == "busy"
    with pytest.raises(CoordinationConflictError, match="atomic finalization"):
        coordinator.release("change-a", attempt.writer.claim_id)
    with pytest.raises(DeliveryActionSelectionConflictError, match="attempt"):
        reopened.finalize_change("change-a", _finalization_request("change-a", attempt.exact_head))

    proof = _finalization_request("change-a", attempt.exact_head, attempt.writer.attempt_id)
    receipt = reopened.finalize_change("change-a", proof)
    assert reopened.finalize_change("change-a", proof) == receipt
    assert coordinator.show("change-a").writer is None
    assert coordinator.show("change-a").finalization_attempt.finished_at is not None
    assert runtimes["change-a"].finalization() == receipt
    assert runtimes["change-b"].active_claims() == ()


def test_continuation_reenters_finalization_with_new_exact_attempt_after_invalidation(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    first = application.acquire_change_action(_continuation_request(application)).finalization.attempt
    application.finalize_change(
        "change-a", _finalization_request("change-a", first.exact_head, first.writer.attempt_id)
    )
    repaired_head = _commit_reviewed_head(
        application, coordinator.show("change-a"), "review-fix.txt", "review fix\n", "repair review"
    )
    runtimes["change-a"].reconcile_finalization_head(repaired_head, datetime.now(UTC))
    acquired = application.acquire_change_action(_continuation_request(application))
    if acquired.kind == "reconciled":
        acquired = application.acquire_change_action(_continuation_request(application))
    second = acquired.finalization.attempt
    assert second.writer.attempt_id != first.writer.attempt_id
    assert second.exact_head == repaired_head
    with pytest.raises(DeliveryActionSelectionConflictError):
        application.finalize_change(
            "change-a", _finalization_request("change-a", repaired_head, first.writer.attempt_id)
        )
    assert coordinator.show("change-a").writer == second.writer
    receipt = application.finalize_change(
        "change-a", _finalization_request("change-a", repaired_head, second.writer.attempt_id)
    )
    assert runtimes["change-a"].finalization() == receipt
    assert coordinator.show("change-a").finalization_attempt.writer == second.writer
    assert coordinator.show("change-a").writer is None


def test_continuation_finalizer_counts_capacity_and_never_expires_custody(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.COMPLETED, "change-b": DeliveryStage.PLANNING}, execution_capacity=1
    )
    acquired = application.acquire_change_action(_continuation_request(application))
    sibling = runtimes["change-b"].frontier_bytes()
    waiting = application.acquire_change_action(_continuation_request(application, "change-b"))
    assert waiting.kind == "waiting"
    assert waiting.reason_code == "execution-capacity"
    reopened, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes, clock=lambda: "2030-01-01T00:00:00Z")
    repeated = reopened.acquire_change_action(_continuation_request(reopened))
    assert repeated.kind == "busy"
    assert coordinator.show("change-a").writer == acquired.finalization.attempt.writer
    assert runtimes["change-b"].frontier_bytes() == sibling


def test_continuation_finalizer_fences_frontier_at_custody_acquisition(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    request = _continuation_request(application)
    original_acquire = coordinator._acquire
    drift = []

    def changed(change_id, writer, **kwargs):
        before = runtimes[change_id].frontier_bytes()
        runtimes[change_id].queue_explicit_checkpoint(request.expected_basis.candidate_head)
        drift.append(runtimes[change_id].frontier_bytes() != before)
        return original_acquire(change_id, writer, **kwargs)

    with patch.object(coordinator, "_acquire", changed):
        rejected = application.acquire_change_action(request)
    assert drift == [True]
    assert rejected.kind == "stale"
    assert rejected.reason_code == "readiness-changed"
    assert rejected.finalization is None
    assert coordinator.show("change-a").writer is None
    assert coordinator.show("change-a").finalization_attempt is None


def test_continuation_acquisition_fences_a_prepared_runtime_mutation(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    request = _continuation_request(application)
    runtime = runtimes["change-a"]
    before = runtime.frontier_bytes()
    original_replace = runtime._replace_content
    acquired = []

    def acquire_before_commit(*args, **kwargs):
        acquired.append(application.acquire_change_action(request))
        original_replace(*args, **kwargs)

    with patch.object(runtime, "_replace_content", acquire_before_commit), pytest.raises(RuntimeError):
        runtime.queue_explicit_checkpoint(request.expected_basis.candidate_head)
    assert len(acquired) == 1
    assert acquired[0].kind == "acquired"
    assert runtime.frontier_bytes() == before
    assert coordinator.show("change-a").writer == acquired[0].finalization.attempt.writer


def test_continuation_finalizer_rejects_target_drift_without_releasing_custody(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    acquired = application.acquire_change_action(_continuation_request(application))
    attempt = acquired.finalization.attempt
    repository = application._workspace_manager.repository
    _git(repository, "commit", "--allow-empty", "-m", "target advances")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")

    with pytest.raises(CoordinationConflictError, match="target head changed"):
        application.finalize_change(
            "change-a", _finalization_request("change-a", attempt.exact_head, attempt.writer.attempt_id)
        )
    assert runtimes["change-a"].finalization() is None
    assert coordinator.show("change-a").writer == attempt.writer


def _owns_finalization_frontier_publication(transaction: RuntimeTransaction) -> bool:
    return any(
        isinstance(participant, ReplacementTransactionParticipant)
        and participant.relative_path.name == "frontier.json"
        and json.loads(participant.replacement_content).get("finalization") is not None
        for participant in transaction._participants
    )


@pytest.mark.parametrize("crash_stage", ["before-publication", "after-first-publication", "before-manifest-cleanup"])
def test_continuation_finalization_replays_atomic_custody_release_after_interruption(
    tmp_path: Path, crash_stage: str
) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    acquired = application.acquire_change_action(_continuation_request(application))
    attempt = acquired.finalization.attempt
    proof = _finalization_request("change-a", attempt.exact_head, attempt.writer.attempt_id)
    original_commit = RuntimeTransaction.commit
    injected = []

    def interrupted(transaction):
        def fail(stage):
            if stage == crash_stage:
                injected.append(stage)
                message = "injected custody completion interruption"
                raise RuntimeError(message)

        original_commit(transaction, failure=fail if _owns_finalization_frontier_publication(transaction) else None)

    with patch.object(RuntimeTransaction, "commit", interrupted), pytest.raises(RuntimeError, match="injected"):
        application.finalize_change("change-a", proof)
    assert injected == [crash_stage]
    if crash_stage != "before-manifest-cleanup":
        assert coordinator.show("change-a").writer == attempt.writer
    reopened, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes)
    assert RetryLedger(state_root, "change-a").read().episodes[0].reset_count == 1
    receipt = reopened.finalize_change("change-a", proof)
    assert receipt.operation_id == attempt.writer.attempt_id
    assert coordinator.show("change-a").writer is None
    assert coordinator.show("change-a").finalization_attempt.finished_at is not None


@pytest.mark.parametrize("stage", [DeliveryStage.PLANNING, DeliveryStage.COMPLETED])
@pytest.mark.parametrize("other_change", ["change-a", "change-b"])
def test_continuation_concurrent_sessions_grant_one_owner(tmp_path: Path, stage, other_change) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path, {"change-a": stage, "change-b": stage}, execution_capacity=1
    )
    reopened, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes)
    reopened._execution_capacity = 1
    requests = (_continuation_request(application), _continuation_request(reopened, other_change))
    barrier = Barrier(2)

    def acquire(instance, request, session):
        barrier.wait(timeout=5)
        return instance.acquire_change_action(request.model_copy(update={"session_id": session}))

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(acquire, instance, requests[index], f"session-{index}")
            for index, instance in enumerate((application, reopened))
        ]
        results = [future.result(timeout=10) for future in futures]
    assert sorted(result.kind for result in results) == [
        "acquired",
        "busy" if other_change == "change-a" else "waiting",
    ]


def test_continuation_failure_retains_custody_and_blocks_success_and_mutations(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    acquired = application.acquire_change_action(_continuation_request(application))
    attempt = acquired.finalization.attempt
    with pytest.raises(FinalizationReportError, match="diagnostic-conflict"):
        application.report_finalization_failure(_failure_request(application))
    failure = _failure_request(application, attempt_key=attempt.writer.attempt_id)
    report = application.report_finalization_failure(failure)
    assert application.report_finalization_failure(failure) == report
    FinalizationReportStore(state_root, "change-a").retire(attempt.exact_head, attempt.contract_digest)
    assert FinalizationReportStore(state_root, "change-a").read().current_report_id is None
    with pytest.raises(DeliveryActionBusyError):
        application.finalize_change(
            "change-a", _finalization_request("change-a", attempt.exact_head, attempt.writer.attempt_id)
        )
    # N09-A2: Pause under retained finalizer custody records a draining request instead of being refused.
    paused = application.set_change_intent(
        DeliveryChangeIntent(
            change_id="change-a",
            kind=DeliveryChangeIntentKind.DEFER,
            expected_frontier_digest=attempt.frontier_digest,
            reason="pause",
        )
    )
    assert paused.receipt == coordinator.pause_request("change-a")
    assert runtimes["change-a"].change_deferral() is None
    application.set_change_intent(
        DeliveryChangeIntent(
            change_id="change-a",
            kind=DeliveryChangeIntentKind.RESUME,
            expected_frontier_digest=attempt.frontier_digest,
        )
    )
    assert coordinator.pause_request("change-a") is None
    reopened, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes)
    view = reopened.get_change("change-a")
    assert view.readiness.status == "blocked"
    assert view.readiness.reason_code == "finalization-failed"
    assert not view.readiness.executable
    assert view.finalization_attempt == attempt
    assert view.readiness.last_attempt.report == report
    stopped = reopened.acquire_change_action(_continuation_request(reopened))
    assert stopped.kind == "unavailable"
    assert stopped.reason_code == "finalization-failed"
    assert coordinator.show("change-a").writer == attempt.writer
    assert runtimes["change-a"].finalization() is None


@pytest.mark.parametrize("writer_recorded", [False, True])
def test_continuation_preserves_failed_activation_identity(tmp_path: Path, *, writer_recorded: bool) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    acquire = coordinator.acquire

    def fail(change_id, writer, **kwargs):
        if writer_recorded:
            acquire(change_id, writer, **kwargs)
        message = "injected writer persistence failure"
        raise OSError(message)

    with patch.object(coordinator, "acquire", fail):
        stopped = application.acquire_change_action(_continuation_request(application))
    claim = runtimes["change-a"].show_binding("OUT-001").active_claim
    assert stopped.kind == "unavailable"
    assert stopped.reason_code == "claim-activation-failed"
    assert stopped.failure.claim_id == claim.claim_id
    assert stopped.failure.attempt_id == claim.attempt_id
    assert "injected writer persistence failure" in stopped.failure.detail
    assert "host/worker evidence is missing" in stopped.failure.retry_condition
    assert not stopped.readiness.executable
    with pytest.raises(ValueError, match="reason_code"):
        DeliveryContinuationResult.model_validate(stopped.model_dump() | {"reason_code": stopped.failure.code})
    assert stopped.launch is None
    assert (coordinator.show("change-a").writer is not None) == writer_recorded
    with pytest.raises(DeliveryWorkerExclusionRequiredError, match="supported worker exclusion"):
        application.recover_claim("change-a", "OUT-001", claim.attempt_id, claim.claim_id, confirmed_lost=True)
    assert runtimes["change-a"].show_binding("OUT-001").active_claim == claim
    ledger = RetryLedger(_state_root, "change-a")
    episode = ledger.read().episodes[0]
    assert episode.total_attempts == 1
    assert episode.attempt_ids == (claim.attempt_id,)
    assert episode.last_status == "failed"
    reopened, _, _ = _reopen_portfolio(tmp_path, _state_root, runtimes)
    assert reopened.acquire_change_action(_continuation_request(reopened)).launch is None
    assert ledger.read().episodes == (episode,)


def test_continuation_stale_and_unavailable_capability_do_not_acquire(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    request = _continuation_request(application)
    unavailable = application.acquire_change_action(request.model_copy(update={"capabilities": ()}))
    assert unavailable.kind == "waiting"
    assert unavailable.reason_code == "host-capability-unavailable"
    stale = application.acquire_change_action(
        request.model_copy(
            update={"expected_basis": request.expected_basis.model_copy(update={"frontier_digest": "0" * 64})}
        )
    )
    assert stale.kind == "stale"
    assert runtimes["change-a"].active_claims() == ()
    assert coordinator.show("change-a").writer is None


@pytest.mark.parametrize("kind", ["human", "terminal", "unavailable"])
def test_continuation_nonworker_dispositions_preserve_state(tmp_path: Path, kind: str) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.DESIGN})
    if kind == "terminal":
        runtimes["change-a"].abandon_change("stop this Change", datetime.now(UTC))
    request = _continuation_request(application)
    frontier = state_root / "changes/change-a/frontier.json"
    if kind == "unavailable":
        frontier.write_bytes(b"{")
    before = frontier.read_bytes()
    result = application.acquire_change_action(request)
    assert result.kind == kind
    assert result.launch is None
    assert result.finalization is None
    assert frontier.read_bytes() == before
    assert coordinator.show("change-a").writer is None


@pytest.mark.parametrize("stage", [DeliveryStage.PLANNING, DeliveryStage.IMPLEMENTATION])
def test_continuation_workers_cannot_be_recovered_by_timeout_or_caller_assertion(tmp_path: Path, stage) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": stage})
    launch = application.acquire_change_action(_continuation_request(application)).launch
    reopened, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes, clock=lambda: "2030-01-01T00:00:00Z")
    before = runtimes["change-a"].frontier_bytes()
    assert reopened.acquire_actions().launch_packages == ()
    with pytest.raises(DeliveryWorkerExclusionRequiredError, match="supported worker exclusion"):
        reopened.recover_claim(
            "change-a", launch.outcome_id, launch.claim.attempt_id, launch.claim.claim_id, confirmed_lost=True
        )
    assert runtimes["change-a"].frontier_bytes() == before
    assert coordinator.show("change-a").writer == launch.writer


@pytest.mark.parametrize("stage", [DeliveryStage.PLANNING, DeliveryStage.IMPLEMENTATION])
@pytest.mark.parametrize("orphan_child", [False, True])
def test_legacy_process_exclusion_required_after_lease(
    tmp_path: Path, stage: DeliveryStage, *, orphan_child: bool
) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": stage})
    launch = application.acquire_frontier_work().launch_packages[0]
    product = launch.worktree_path / "product.txt"
    worker_code = (
        "import pathlib,sys\n"
        "product=pathlib.Path(sys.argv[1])\n"
        "product.write_text('worker started\\n')\n"
        "print('writing',flush=True)\n"
        "sys.stdin.readline()\n"
        "product.write_text('late worker write\\n')\n"
    )
    command = (sys.executable, "-c", worker_code, str(product))
    if orphan_child:
        parent_code = "import subprocess,sys\nsubprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]])\n"
        command = (sys.executable, "-c", parent_code, worker_code, str(product))
    with subprocess.Popen(  # noqa: S603 - controlled worker in a disposable repository.
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    ) as worker:
        try:
            assert worker.stdout.readline().strip() == "writing"
            if orphan_child:
                assert worker.wait(timeout=10) == 0
            reopened, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes, clock=lambda: "2030-01-01T00:00:00Z")
            before = runtimes["change-a"].frontier_bytes()
            custody = coordinator.show("change-a")
            assert reopened.acquire_actions().launch_packages == ()
            with pytest.raises(DeliveryWorkerExclusionRequiredError):
                reopened.recover_claim(
                    "change-a", launch.outcome_id, launch.claim.attempt_id, launch.claim.claim_id, confirmed_lost=True
                )
            assert (worker.poll() is not None) == orphan_child
            assert runtimes["change-a"].frontier_bytes() == before
            assert coordinator.show("change-a") == custody
        finally:
            worker.communicate("\n", timeout=10)
    assert product.read_text() == "late worker write\n"
    assert runtimes["change-a"].active_claims() == ((launch.outcome_id, launch.claim),)


def test_continuation_live_worker_remains_excluded_after_lease(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    launch = application.acquire_change_action(_continuation_request(application)).launch
    writing = Event()
    finish = Event()

    def worker():
        product = launch.worktree_path / "product.txt"
        product.write_text("worker is still active\n", encoding="utf-8")
        writing.set()
        assert finish.wait(timeout=10)
        product.write_text("worker finished its preserved write\n", encoding="utf-8")

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(worker)
        try:
            assert writing.wait(timeout=5)
            reopened, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes, clock=lambda: "2030-01-01T00:00:00Z")
            assert reopened.acquire_change_action(_continuation_request(reopened)).kind == "busy"
            assert reopened.acquire_actions().launch_packages == ()
            with pytest.raises(DeliveryWorkerExclusionRequiredError):
                reopened.recover_claim(
                    "change-a", launch.outcome_id, launch.claim.attempt_id, launch.claim.claim_id, confirmed_lost=True
                )
            assert coordinator.show("change-a").writer == launch.writer
        finally:
            finish.set()
        future.result(timeout=5)
    assert (launch.worktree_path / "product.txt").read_text(encoding="utf-8") == "worker finished its preserved write\n"


def test_continuation_plans_builds_and_finalizes_via_existing_result_routes(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    planner = application.acquire_change_action(_continuation_request(application)).launch
    candidate = application.publish_delivery_plan(
        "change-a",
        PublishDeliveryPlan(outcome_id=planner.outcome_id, claim_id=planner.claim.claim_id, tasks=(_task(),)),
    )
    assert RetryLedger(_state_root, "change-a").read().episodes[0].total_attempts == 1
    assert RetryLedger(_state_root, "change-a").read().episodes[0].reset_count == 0
    application.transition_delivery(
        "change-a",
        AdvanceDelivery(
            action="advance", outcome_id=planner.outcome_id, claim_id=planner.claim.claim_id, output=candidate.output
        ),
    )
    assert RetryLedger(_state_root, "change-a").read().episodes[0].total_attempts == 0
    assert RetryLedger(_state_root, "change-a").read().episodes[0].reset_count == 1
    assert application.acquire_change_action(_continuation_request(application)).kind == "reconciled"
    builder = application.acquire_change_action(_continuation_request(application)).launch
    _git(builder.worktree_path, "commit", "--allow-empty", "-m", "complete task")
    runtime = runtimes["change-a"]
    submission = DeliveryResultSubmission(
        change_id="change-a",
        outcome_id=builder.outcome_id,
        claim_id=builder.claim.claim_id,
        result=_task_result(
            "result-continuation",
            "change-a",
            runtime.authority_digest,
            runtime.show_binding(builder.outcome_id).tasks[0],
            _git(builder.worktree_path, "rev-parse", "HEAD"),
        ),
    )
    receipt = application.submit_result(submission)
    assert application.submit_result(submission) == receipt
    assert application.acquire_change_action(_continuation_request(application)).kind == "reconciled"
    finalizer = application.acquire_change_action(_continuation_request(application)).finalization
    finalization = application.finalize_change(
        "change-a", _finalization_request("change-a", finalizer.attempt.exact_head, finalizer.attempt.writer.attempt_id)
    )
    assert finalization.exact_head == submission.result.completed_commit
    assert application.acquire_change_action(_continuation_request(application)).kind == "reconciled"
    unsupported = application.acquire_change_action(_continuation_request(application))
    assert unsupported.kind == "waiting"
    assert unsupported.reason_code == "engine-owner-unavailable"
    assert unsupported.readiness.operation.value == "reconcile-checkpoint"


def test_selected_acquisition_leaves_sibling_claims_unchanged(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING},
    )
    before_sibling = runtimes["change-a"].frontier_bytes()
    selection = DeliveryActionSelection(
        change_id="change-b",
        outcome_id="OUT-001",
        expected_stage=DeliveryStage.PLANNING,
        expected_frontier_digest=hashlib.sha256(runtimes["change-b"].frontier_bytes()).hexdigest(),
        expected_source_head=coordinator.show("change-b").last_reviewed_commit,
    )

    result = application.acquire_actions(selection)

    assert len(result.launch_packages) == 1
    assert result.launch_packages[0].change_id == "change-b"
    assert result.launch_packages[0].task_id is None
    assert runtimes["change-a"].frontier_bytes() == before_sibling
    assert coordinator.show("change-a").writer is None
    assert result.recoveries == result.failures == result.integration_attention == ()


@pytest.mark.parametrize("changed_field", ["expected_frontier_digest", "expected_source_head", "outcome_id"])
def test_selected_acquisition_rejects_stale_selection_without_claims(tmp_path: Path, changed_field: str) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING},
    )
    before = {change_id: runtime.frontier_bytes() for change_id, runtime in runtimes.items()}
    selection = DeliveryActionSelection(
        change_id="change-b",
        outcome_id="OUT-001",
        expected_stage=DeliveryStage.PLANNING,
        expected_frontier_digest=hashlib.sha256(before["change-b"]).hexdigest(),
        expected_source_head=coordinator.show("change-b").last_reviewed_commit,
    )
    rejected = {
        "expected_frontier_digest": "0" * 64,
        "expected_source_head": "0" * 40,
        "outcome_id": "OUT-999",
    }

    with pytest.raises(DeliveryActionSelectionConflictError, match="selected action"):
        application.acquire_actions(selection.model_copy(update={changed_field: rejected[changed_field]}))

    assert {change_id: runtime.frontier_bytes() for change_id, runtime in runtimes.items()} == before
    assert coordinator.show("change-b").writer is None


def test_selected_acquisition_rejects_wrong_task_then_acquires_expected_task(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION, "change-b": DeliveryStage.PLANNING},
    )
    runtime = runtimes["change-a"]
    before = runtime.frontier_bytes()
    expected_task = runtime.claimable_task_ids("OUT-001")[0]
    selection = DeliveryActionSelection(
        change_id="change-a",
        outcome_id="OUT-001",
        expected_stage=DeliveryStage.IMPLEMENTATION,
        expected_task_id="wrong-task",
        expected_frontier_digest=hashlib.sha256(before).hexdigest(),
        expected_source_head=coordinator.show("change-a").last_reviewed_commit,
    )

    with pytest.raises(DeliveryActionSelectionConflictError, match="next eligible"):
        application.acquire_actions(selection)
    assert runtime.frontier_bytes() == before
    result = application.acquire_actions(selection.model_copy(update={"expected_task_id": expected_task}))

    assert len(result.launch_packages) == 1
    assert result.launch_packages[0].task_id == expected_task
    assert result.launch_packages[0].writer is not None
    assert runtimes["change-b"].active_claims() == ()


def test_selected_acquisition_honors_capacity_and_returns_source_failure(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING},
        execution_capacity=1,
    )

    def selection_for(change_id: str) -> DeliveryActionSelection:
        return DeliveryActionSelection(
            change_id=change_id,
            outcome_id="OUT-001",
            expected_stage=DeliveryStage.PLANNING,
            expected_frontier_digest=hashlib.sha256(runtimes[change_id].frontier_bytes()).hexdigest(),
            expected_source_head=coordinator.show(change_id).last_reviewed_commit,
        )

    dirty = coordinator.show("change-a").worktree_path / "product.txt"
    original = dirty.read_bytes()
    dirty.write_text("unreviewed source\n", encoding="utf-8")
    result = application.acquire_actions(selection_for("change-a"))
    assert result.launch_packages == ()
    assert len(result.failures) == 1
    assert result.failures[0].change_id == "change-a"
    assert runtimes["change-a"].active_claims() == ()
    dirty.write_bytes(original)
    application.acquire_actions(selection_for("change-a"))

    with pytest.raises(DeliveryCapacityWaitingError, match="execution capacity"):
        application.acquire_actions(selection_for("change-b"))
    assert runtimes["change-b"].active_claims() == ()


def test_selected_acquisition_fences_frontier_at_claim_activation(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    runtime = runtimes["change-a"]
    selection = DeliveryActionSelection(
        change_id="change-a",
        outcome_id="OUT-001",
        expected_stage=DeliveryStage.PLANNING,
        expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
        expected_source_head=coordinator.show("change-a").last_reviewed_commit,
    )
    original_activate = runtime.activate_claim

    def change_before_activation(request: ActivateDeliveryClaim) -> OutcomeAuthorityBinding:
        runtime.queue_explicit_checkpoint(selection.expected_source_head)
        return original_activate(request)

    with (
        patch.object(runtime, "activate_claim", side_effect=change_before_activation),
        pytest.raises(DeliveryRuntimeConflictError, match="before claim activation"),
    ):
        application.acquire_actions(selection)

    assert runtime.active_claims() == ()
    assert coordinator.show("change-a").writer is None


@pytest.mark.parametrize("selected", [True, False])
def test_acquisition_retains_recovery_identity_after_writer_failure(tmp_path: Path, *, selected: bool) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    runtime = runtimes["change-a"]
    selection = DeliveryActionSelection(
        change_id="change-a",
        outcome_id="OUT-001",
        expected_stage=DeliveryStage.IMPLEMENTATION,
        expected_task_id=runtime.claimable_task_ids("OUT-001")[0],
        expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
        expected_source_head=coordinator.show("change-a").last_reviewed_commit,
    )

    with patch.object(coordinator, "acquire", side_effect=OSError("injected writer persistence failure")):
        result = application.acquire_actions(selection if selected else None)

    assert result.launch_packages == ()
    assert len(result.failures) == 1
    failure = result.failures[0]
    active_claim = runtime.show_binding("OUT-001").active_claim
    assert active_claim is not None
    assert failure.claim_id == active_claim.claim_id
    assert failure.attempt_id == active_claim.attempt_id
    assert failure.change_id == "change-a"
    assert coordinator.show("change-a").writer is None


def test_selected_acquisition_holds_checkpoint_lock_through_activation(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    selection = DeliveryActionSelection(
        change_id="change-a",
        outcome_id="OUT-001",
        expected_stage=DeliveryStage.PLANNING,
        expected_frontier_digest=hashlib.sha256(runtimes["change-a"].frontier_bytes()).hexdigest(),
        expected_source_head=coordinator.show("change-a").last_reviewed_commit,
    )
    original_activate = runtimes["change-a"].activate_claim

    def verify_lock(request: ActivateDeliveryClaim) -> OutcomeAuthorityBinding:
        with (
            pytest.raises(BlockingIOError),
            locked_roots((state_root / "publications/checkpoints/locks/change-a",), blocking=False),
        ):
            pytest.fail("selected activation released its checkpoint lock")
        return original_activate(request)

    with patch.object(runtimes["change-a"], "activate_claim", side_effect=verify_lock):
        result = application.acquire_actions(selection)

    assert len(result.launch_packages) == 1


def test_selected_acquisition_busy_checkpoint_releases_portfolio_lock(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    before = runtimes["change-a"].frontier_bytes()
    selection = DeliveryActionSelection(
        change_id="change-a",
        outcome_id="OUT-001",
        expected_stage=DeliveryStage.PLANNING,
        expected_frontier_digest=hashlib.sha256(before).hexdigest(),
        expected_source_head=coordinator.show("change-a").last_reviewed_commit,
    )

    with (
        locked_roots((state_root / "publications/checkpoints/locks/change-a",)),
        pytest.raises(DeliveryActionBusyError),
    ):
        application.acquire_actions(selection)

    with locked_roots((state_root / "claims/acquisition-lock",), blocking=False):
        assert runtimes["change-a"].frontier_bytes() == before


def test_selected_acquisition_repeated_call_reports_active_without_second_launch(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    selection = DeliveryActionSelection(
        change_id="change-a",
        outcome_id="OUT-001",
        expected_stage=DeliveryStage.PLANNING,
        expected_frontier_digest=hashlib.sha256(runtimes["change-a"].frontier_bytes()).hexdigest(),
        expected_source_head=coordinator.show("change-a").last_reviewed_commit,
    )
    first = application.acquire_actions(selection)
    claimed = runtimes["change-a"].frontier_bytes()

    repeated = application.acquire_actions(selection)

    assert len(first.launch_packages) == 1
    assert repeated.launch_packages == ()
    assert repeated.failures[0].code == "ERR_DELIVERY_ACTION_ALREADY_ACTIVE"
    assert repeated.failures[0].claim_id is None
    assert "do not redispatch or release its claim" in repeated.failures[0].retry_condition.casefold()
    assert runtimes["change-a"].frontier_bytes() == claimed


def test_selected_acquisition_replays_only_its_pending_publication(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING}
    )
    previous = {
        change_id: DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
        for change_id, runtime in runtimes.items()
    }
    publisher = Mock()
    publisher.publish.return_value = object()
    publisher.read_snapshot_inventory.return_value = Mock(
        remote_head="remote-head",
        snapshots=tuple(Mock(change_id=change_id, frontier=frontier) for change_id, frontier in previous.items()),
    )
    application._delivery_state_publisher = publisher
    for runtime in runtimes.values():
        content = runtime.frontier_bytes()
        frontier = DeliveryFrontier.model_validate_json(content, strict=True)
        runtime._replace_content(content, _canonical(frontier.model_copy(update={"published_head": "a" * 40})))
    sibling_content = runtimes["change-b"].frontier_bytes()
    sibling_pending = runtimes["change-b"].pending_state_publication()
    selection = DeliveryActionSelection(
        change_id="change-a",
        outcome_id="OUT-001",
        expected_stage=DeliveryStage.PLANNING,
        expected_frontier_digest=hashlib.sha256(runtimes["change-a"].frontier_bytes()).hexdigest(),
        expected_source_head=coordinator.show("change-a").last_reviewed_commit,
    )

    result = application.acquire_actions(selection)

    assert len(result.launch_packages) == 1
    assert result.failures == ()
    assert publisher.publish.call_count == 1
    assert runtimes["change-a"].pending_state_publication() is None
    assert runtimes["change-b"].frontier_bytes() == sibling_content
    assert runtimes["change-b"].pending_state_publication() == sibling_pending


def test_shared_acquisition_serializes_reconciliation_and_bounds_claims(tmp_path: Path) -> None:
    _application, _runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.PLANNING,
            "change-b": DeliveryStage.IMPLEMENTATION,
            "change-c": DeliveryStage.IMPLEMENTATION,
        },
        execution_capacity=3,
    )
    repository = tmp_path / "repository"
    package_root = tmp_path / "packages"
    worktree_root = tmp_path / "worktrees"
    barrier_root = tmp_path / "acquisition-barrier"
    barrier_root.mkdir()
    source_root = Path(__file__).resolve().parents[1] / "src"
    python_path = os.pathsep.join(filter(None, (str(source_root), os.environ.get("PYTHONPATH"))))
    processes = [
        subprocess.Popen(  # noqa: S603
            (
                sys.executable,
                "-c",
                _shared_acquisition_command(),
                str(state_root),
                str(repository),
                str(package_root),
                str(worktree_root),
                str(barrier_root),
                worker_id,
            ),
            cwd=repository,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "PYTHONPATH": python_path},
        )
        for worker_id in ("one", "two")
    ]
    outputs: list[tuple[str, str]] = []
    try:
        _wait_for_files(tuple(barrier_root / f"ready-{worker_id}" for worker_id in ("one", "two")))
        (barrier_root / "go").write_text("go", encoding="ascii")
        outputs = [process.communicate(timeout=30) for process in processes]
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
            if process.returncode is None:
                process.communicate()

    for process, (_stdout, stderr) in zip(processes, outputs, strict=False):
        assert process.returncode == 0, stderr
    assert all((barrier_root / f"reconcile-{worker_id}-inside").is_file() for worker_id in ("one", "two"))
    assert not list(barrier_root.glob("reconcile-*-outside"))
    inside = [
        json.loads((barrier_root / f"inside-{worker_id}.json").read_text(encoding="utf-8"))
        for worker_id in ("one", "two")
    ]
    assert all(item["count"] <= 3 for item in inside)
    launches = [
        json.loads((barrier_root / f"result-{worker_id}.json").read_text(encoding="utf-8"))["launches"]
        for worker_id in ("one", "two")
    ]
    assert sorted(launches) == [0, 3]
    active_claims = [
        binding.active_claim
        for observation in discover_persisted_changes(state_root)
        if observation.frontier is not None
        for binding in observation.frontier.bindings
        if binding.active_claim is not None
    ]
    assert len(active_claims) == 3
    assert {claim.worker_role for claim in active_claims} == {
        DeliveryWorkerRole.PLANNER,
        DeliveryWorkerRole.BUILDER,
    }


def test_acquisition_returns_preclaim_attention_and_refreshes_snapshot_cache(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.PLANNING,
            "change-b": DeliveryStage.COMPLETED,
        },
        execution_capacity=1,
    )
    completed = coordinator.show("change-b")
    original_activate = application._activate_candidate
    reconciliation = Mock(wraps=application._reconcile_runtimes)

    def activate(candidate, source, **kwargs):
        launch = original_activate(candidate, source, **kwargs)
        _publish_merge_conflict_attention(
            runtimes,
            state_root,
            "change-b",
            completed.last_reviewed_commit,
            completed.target_head,
        )
        return launch

    with (
        patch.object(application, "_activate_candidate", side_effect=activate),
        patch.object(application, "_reconcile_runtimes", new=reconciliation),
    ):
        acquired = application.acquire_frontier_work()

    assert tuple(package.change_id for package in acquired.launch_packages) == ("change-a",)
    assert acquired.integration_attention == ()
    assert reconciliation.call_count == 1
    assert application._runtime_snapshots["change-b"].frontier.integration_attention is not None


def test_acquisition_charges_noncomposable_change_from_persisted_claims(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.PLANNING,
        },
        execution_capacity=1,
    )
    _admit_discovery_change(application, "blocked-change")
    blocked_runtime = runtimes.get("blocked-change", application._runtimes["blocked-change"])
    claim = application._new_claim(DeliveryWorkerRole.PLANNER, None)
    blocked_runtime.activate_claim(ActivateDeliveryClaim(outcome_id="OUT-001", claim=claim))
    (state_root / "changes/blocked-change/contract.json").unlink()

    acquired = application.acquire_frontier_work()

    assert acquired.launch_packages == ()
    assert runtimes["change-a"].active_claims() == ()
    observation = next(item for item in application._discovered_changes.values() if item.change_id == "blocked-change")
    assert observation.frontier is not None
    assert sum(binding.active_claim is not None for binding in observation.frontier.bindings) == 1
    assert application._runtime_reconciliation_errors["blocked-change"]
    assert acquired.health_hint == "Call delivery_health for current Delivery diagnostics."


def test_acquisition_uses_maximum_observed_occupancy_once_per_change(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.PLANNING,
            "change-b": DeliveryStage.PLANNING,
        },
        execution_capacity=3,
    )
    claims = tuple(
        DeliveryActiveClaim(
            attempt_id=f"attempt-{index}",
            claim_id=f"claim-{index}",
            owner_id=f"owner-{index}",
            process_id=f"process-{index}",
            started_at="2026-08-04T00:00:00Z",
            worker_role=DeliveryWorkerRole.PLANNER,
        )
        for index in range(3)
    )
    invalid_frontier = DeliveryFrontier(
        bindings=tuple(
            OutcomeAuthorityBinding(
                outcome_id=f"OUT-{index + 1:03}",
                plan_scope_id=f"SCOPE-{index + 1:03}",
                active_claim=claim,
            )
            for index, claim in enumerate(claims)
        )
    )
    (state_root / "changes/change-a/frontier.json").write_bytes(_canonical(invalid_frontier))

    with patch.object(
        runtimes["change-a"],
        "active_claims",
        return_value=(("OUT-001", claims[0]), ("OUT-002", claims[1])),
    ):
        acquired = application.acquire_frontier_work()

    assert acquired.launch_packages == ()
    assert application._execution_occupancy() == 3


def test_finalization_uses_managed_head_and_invalidates_observed_drift(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    exact_head = coordination.last_reviewed_commit
    request = _finalization_request("change-a", exact_head)

    receipt = application.finalize_change("change-a", request)

    assert isinstance(receipt, DeliveryFinalizationReceipt)
    assert application.finalize_change("change-a", request) == receipt
    assert runtimes["change-a"].change_stage() == DeliveryChangeStage.FINALIZED
    assert application.list_integration_attention() == ()
    publication = application.show_change_checkpoint_publication("change-a")
    assert publication.pending_checkpoint is not None
    assert publication.pending_checkpoint.head == exact_head

    (coordination.worktree_path / "external.txt").write_text("external head drift\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "external.txt")
    _git(coordination.worktree_path, "commit", "-m", "simulate external head drift")
    observed_head = _git(coordination.worktree_path, "rev-parse", "HEAD")

    invalidation = application.reconcile_finalization_head("change-a")

    assert isinstance(invalidation, DeliveryFinalizationInvalidationReceipt)
    assert invalidation.expected_head == exact_head
    assert invalidation.observed_head == observed_head
    assert runtimes["change-a"].change_stage() == DeliveryChangeStage.BUILDING
    assert application.list_integration_attention() == ()


def test_finalization_admits_clean_local_descendant_and_advances_reviewed_boundary(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    initial = coordination.last_reviewed_commit
    exact_head = _commit_local_descendant(coordination)

    context = application.show_finalization_context("change-a")

    assert context.ready_for_finalization is True
    assert context.change_head == exact_head
    assert context.reviewed_change_head == initial
    request = _finalization_request("change-a", exact_head)
    finalization = application.finalize_change("change-a", request)

    assert finalization.exact_head == exact_head
    assert coordinator.show("change-a").last_reviewed_commit == exact_head
    assert runtimes["change-a"].finalization() == finalization
    pending = runtimes["change-a"].checkpoint_publication_state().pending_checkpoint
    assert pending is not None
    assert pending.head == exact_head
    assert application.finalize_change("change-a", request) == finalization


def test_local_descendant_does_not_grant_builder_authority(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    coordination = coordinator.show("change-a")
    initial = coordination.last_reviewed_commit
    _commit_local_descendant(coordination)

    acquired = application.acquire_frontier_work()

    assert acquired.launch_packages == ()
    assert len(acquired.failures) == 1
    assert "reviewed" in acquired.failures[0].detail
    assert coordinator.show("change-a").last_reviewed_commit == initial


def test_finalization_admits_local_descendant_after_promoted_external_ancestor(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    initial = coordination.last_reviewed_commit
    adopted = _publish_external_change_head(
        tmp_path,
        application._workspace_manager.repository,
        coordination.branch,
        initial,
    )
    application.adopt_external_head("change-a", initial, adopted, "adopt-before-local-finalization")
    application.promote_external_head("change-a", adopted, "promote-before-local-finalization")
    exact_head = _commit_local_descendant(coordination, "local-after-adoption.txt")

    finalization = application.finalize_change("change-a", _finalization_request("change-a", exact_head))

    assert finalization.exact_head == exact_head
    assert coordinator.show("change-a").last_reviewed_commit == exact_head
    promotion = coordinator.show("change-a").external_head_promotion_receipt
    assert promotion is not None
    assert promotion.promoted_head == adopted
    assert runtimes["change-a"].finalization() == finalization


def test_finalization_replays_atomic_local_boundary_after_interruption(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    initial = coordination.last_reviewed_commit
    exact_head = _commit_local_descendant(coordination, "local-replay.txt")
    request = _finalization_request("change-a", exact_head)
    original_commit = RuntimeTransaction.commit
    injected = []

    def interrupt_after_frontier(transaction: RuntimeTransaction) -> None:
        def interrupt(stage: str) -> None:
            if stage == "after-first-publication":
                injected.append(stage)
                message = "simulated finalization interruption"
                raise RuntimeError(message)

        original_commit(
            transaction, failure=interrupt if _owns_finalization_frontier_publication(transaction) else None
        )

    with (
        patch.object(RuntimeTransaction, "commit", interrupt_after_frontier),
        pytest.raises(RuntimeError, match="simulated finalization interruption"),
    ):
        application.finalize_change("change-a", request)

    assert injected == ["after-first-publication"]
    assert coordinator.show("change-a").last_reviewed_commit == initial
    assert tuple((state_root / "transactions").glob("*.yaml"))

    replayed = application.finalize_change("change-a", request)

    assert replayed == runtimes["change-a"].finalization()
    assert coordinator.show("change-a").last_reviewed_commit == exact_head
    assert not tuple((state_root / "transactions").glob("*.yaml"))


@pytest.mark.parametrize("user_state", _USER_CHECKOUT_STATES)
def test_finalization_preserves_user_checkout_states(
    tmp_path: Path,
    user_state: str,
    user_checkout_snapshot,
    prepare_user_checkout_state,
    seed_user_checkout_metadata,
) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    repository = application._workspace_manager.repository
    seed_user_checkout_metadata(repository)
    prepare_user_checkout_state(repository, user_state)
    before = user_checkout_snapshot(repository, ("refs/heads/owlbear/change/change-a",))
    exact_head = coordinator.show("change-a").last_reviewed_commit
    request = _finalization_request("change-a", exact_head)

    receipt = application.finalize_change("change-a", request)
    replayed = application.finalize_change("change-a", request)

    assert replayed == receipt
    assert receipt.exact_head == exact_head
    before.assert_unchanged(repository)


def test_application_binds_target_sync_receipt_and_invalidates_finalization(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    finalization = application.finalize_change("change-a", _finalization_request("change-a", exact_head))
    receipt = ChangeTargetSyncReceipt.create(
        operation_id="sync-change-a",
        change_id="change-a",
        integration_target="main",
        expected_target="2" * 40,
        target_head="2" * 40,
        change_head_before=exact_head,
        merged_head="3" * 40,
        merge_commit=True,
    )

    with patch.object(application._workspace_manager, "sync_with_target", return_value=receipt) as sync:
        assert application.sync_change_with_target("change-a", "2" * 40, "sync-change-a") == receipt

    request = sync.call_args.args[0]
    assert request.change_id == "change-a"
    assert request.expected_target == "2" * 40
    assert request.operation_id == "sync-change-a"
    assert runtimes["change-a"].target_sync_receipt() == receipt
    assert runtimes["change-a"].finalization() is None
    assert runtimes["change-a"].finalization_invalidation().finalization_id == finalization.finalization_id


def test_clean_target_sync_publishes_branch_before_state_snapshot(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    application.finalize_change("change-a", _finalization_request("change-a", exact_head))
    receipt = ChangeTargetSyncReceipt.create(
        operation_id="sync-clean-ordered",
        change_id="change-a",
        integration_target="main",
        expected_target="2" * 40,
        target_head="2" * 40,
        change_head_before=exact_head,
        merged_head="3" * 40,
        merge_commit=True,
    )
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    state_publisher = Mock()

    def publish_state(**_kwargs: object) -> None:
        assert branch_publisher.publish.call_count == 1

    state_publisher.publish.side_effect = publish_state
    application._change_branch_publisher = branch_publisher
    application._delivery_state_publisher = state_publisher

    with patch.object(application._workspace_manager, "sync_with_target", return_value=receipt):
        synchronized = application.sync_change_with_target(
            "change-a",
            "2" * 40,
            "sync-clean-ordered",
        )

    assert synchronized == receipt
    assert runtimes["change-a"].checkpoint_publication_state().published_head == receipt.merged_head
    assert runtimes["change-a"].target_sync_receipt() == receipt


def test_application_binds_external_head_adoption_without_advancing_reviewed_authority(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    expected_head = coordination.last_reviewed_commit
    finalization = application.finalize_change("change-a", _finalization_request("change-a", expected_head))
    receipt = ChangeExternalHeadAdoptionReceipt.create(
        operation_id="adopt-change-a",
        change_id="change-a",
        branch=coordination.branch,
        expected_head=expected_head,
        adopted_head="5" * 40,
    )

    with patch.object(application._workspace_manager, "adopt_external_head", return_value=receipt) as adopt:
        assert application.adopt_external_head("change-a", expected_head, "5" * 40, "adopt-change-a") == receipt

    request = adopt.call_args.args[0]
    assert request.change_id == "change-a"
    assert request.expected_head == expected_head
    assert request.adopted_head == "5" * 40
    assert request.operation_id == "adopt-change-a"
    assert coordinator.show("change-a").last_reviewed_commit == expected_head
    assert runtimes["change-a"].external_head_adoption_receipt() == receipt
    assert runtimes["change-a"].finalization() is None
    invalidation = runtimes["change-a"].finalization_invalidation()
    assert invalidation is not None
    assert invalidation.finalization_id == finalization.finalization_id
    publication = runtimes["change-a"].checkpoint_publication_state()
    assert publication.pending_checkpoint is not None
    assert publication.pending_checkpoint.head == "5" * 40


def test_application_binds_observed_external_head_without_granting_review_authority(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    expected_head = coordination.last_reviewed_commit
    repository = tmp_path / "repository"
    adopted = _publish_external_change_head(tmp_path, repository, coordination.branch, expected_head)
    _git(
        repository,
        "fetch",
        "origin",
        f"refs/heads/{coordination.branch}:refs/remotes/origin/{coordination.branch}",
    )
    _git(coordination.worktree_path, "merge", "--ff-only", adopted)

    receipt = application.adopt_external_head("change-a", expected_head, adopted, "observe-change-a")

    assert receipt.provenance == "observed"
    assert runtimes["change-a"].external_head_adoption_receipt() == receipt
    assert coordinator.show("change-a").last_reviewed_commit == expected_head
    assert runtimes["change-a"].checkpoint_publication_state().pending_checkpoint is not None


def test_application_requires_adopted_head_promotion_before_build_acquisition(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    initial = coordinator.show("change-a").last_reviewed_commit
    branch = coordinator.show("change-a").branch
    adopted = _publish_external_change_head(tmp_path, application._workspace_manager.repository, branch, initial)

    application.adopt_external_head("change-a", initial, adopted, "adopt-for-acquisition")
    blocked = application.acquire_frontier_work()

    assert blocked.launch_packages == ()
    assert len(blocked.failures) == 1
    assert "explicit promotion" in blocked.failures[0].detail
    assert coordinator.show("change-a").last_reviewed_commit == initial

    promoted = application.promote_external_head("change-a", adopted, "promote-for-acquisition")
    assert promoted.promoted_head == adopted
    acquired = application.acquire_frontier_work()

    assert acquired.failures == ()
    assert len(acquired.launch_packages) == 1
    launch = acquired.launch_packages[0]
    assert launch.source_head == adopted
    assert launch.last_reviewed_commit == adopted
    assert runtimes["change-a"].external_head_adoption_receipt().adopted_head == adopted


def test_finalization_replay_promotes_an_adopted_head_after_runtime_commit(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    initial = coordinator.show("change-a").last_reviewed_commit
    branch = coordinator.show("change-a").branch
    adopted = _publish_external_change_head(tmp_path, application._workspace_manager.repository, branch, initial)
    application.adopt_external_head("change-a", initial, adopted, "adopt-for-finalization")
    request = _finalization_request("change-a", adopted)

    with (
        patch.object(
            application,
            "_promote_finalized_external_head",
            side_effect=RuntimeError("simulated promotion crash"),
        ),
        pytest.raises(RuntimeError, match="simulated promotion crash"),
    ):
        application.finalize_change("change-a", request)

    assert runtimes["change-a"].finalization() is not None
    assert coordinator.show("change-a").last_reviewed_commit == initial
    replayed = application.reconcile_finalization_head("change-a")

    assert replayed == runtimes["change-a"].finalization()
    assert coordinator.show("change-a").last_reviewed_commit == adopted


def test_finalization_replay_repairs_runtime_promotion_after_workspace_commit(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    initial = coordinator.show("change-a").last_reviewed_commit
    branch = coordinator.show("change-a").branch
    adopted = _publish_external_change_head(tmp_path, application._workspace_manager.repository, branch, initial)
    application.adopt_external_head("change-a", initial, adopted, "adopt-for-finalization-repair")
    request = _finalization_request("change-a", adopted)

    with (
        patch.object(
            runtimes["change-a"],
            "record_external_head_promotion",
            side_effect=RuntimeError("simulated runtime promotion crash"),
        ),
        pytest.raises(PortfolioApplicationError, match="finalization could not promote"),
    ):
        application.finalize_change("change-a", request)

    workspace_promotion = coordinator.show("change-a").external_head_promotion_receipt
    assert workspace_promotion is not None
    assert runtimes["change-a"].external_head_promotion_receipt() is None

    application.reconcile_finalization_head("change-a")

    assert runtimes["change-a"].external_head_promotion_receipt() == workspace_promotion


def test_finalization_replay_skips_reconciled_promotion_after_worktree_loss(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    initial = coordinator.show("change-a").last_reviewed_commit
    branch = coordinator.show("change-a").branch
    adopted = _publish_external_change_head(tmp_path, application._workspace_manager.repository, branch, initial)
    application.adopt_external_head("change-a", initial, adopted, "adopt-for-idempotent-replay")
    request = _finalization_request("change-a", adopted)
    finalization = application.finalize_change("change-a", request)

    shutil.rmtree(coordinator.show("change-a").worktree_path)

    with patch.object(
        application._workspace_manager,
        "promote_external_head",
        side_effect=AssertionError("reconciled finalization must not re-enter workspace promotion"),
    ):
        assert application.finalize_change("change-a", request) == finalization

    assert runtimes["change-a"].external_head_promotion_receipt() is not None


def test_finalization_after_builder_child_does_not_repromote_adopted_ancestor(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    initial = coordinator.show("change-a").last_reviewed_commit
    branch = coordinator.show("change-a").branch
    adopted = _publish_external_change_head(tmp_path, application._workspace_manager.repository, branch, initial)
    application.adopt_external_head("change-a", initial, adopted, "adopt-for-builder")
    application.promote_external_head("change-a", adopted, "promote-for-builder")

    launch = application.acquire_frontier_work().launch_packages[0]
    task = runtimes["change-a"].show_binding("OUT-001").tasks[0]
    builder_file = launch.worktree_path / "builder.txt"
    builder_file.write_text("builder child\n", encoding="utf-8")
    _git(launch.worktree_path, "add", builder_file.name)
    _git(launch.worktree_path, "commit", "-m", "builder child")
    child = _git(launch.worktree_path, "rev-parse", "HEAD")
    result = application.publish_delivery_result(
        "change-a",
        PublishDeliveryResult(
            outcome_id="OUT-001",
            claim_id=launch.claim.claim_id,
            result=_task_result(
                "RESULT-BUILDER-CHILD",
                "change-a",
                runtimes["change-a"].authority_digest,
                task,
                child,
            ),
        ),
    )
    application.transition_delivery(
        "change-a",
        AdvanceDelivery(
            action="advance",
            outcome_id="OUT-001",
            claim_id=launch.claim.claim_id,
            output=result.output,
        ),
    )

    assert coordinator.show("change-a").last_reviewed_commit == child
    with patch.object(
        application._workspace_manager,
        "promote_external_head",
        side_effect=AssertionError("finalization must not re-promote a reviewed Builder child"),
    ):
        finalization = application.finalize_change("change-a", _finalization_request("change-a", child))

    assert finalization.exact_head == child


def test_application_promotes_only_reconciled_adoption_evidence(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    initial = coordinator.show("change-a").last_reviewed_commit
    branch = coordinator.show("change-a").branch
    adopted = _publish_external_change_head(tmp_path, application._workspace_manager.repository, branch, initial)
    application.adopt_external_head("change-a", initial, adopted, "adopt-for-promotion")

    promoted = application.promote_external_head("change-a", adopted, "promote-for-promotion")
    replayed = application.promote_external_head("change-a", adopted, "promote-for-promotion")

    assert promoted == replayed
    assert promoted.change_id == "change-a"
    assert promoted.promoted_head == adopted
    assert coordinator.show("change-a").last_reviewed_commit == adopted
    assert runtimes["change-a"].external_head_adoption_receipt().adopted_head == adopted


def test_application_acquires_after_real_target_sync_at_the_merged_head(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    repository = application._workspace_manager.repository
    remote = tmp_path / "remote.git"
    subprocess.run(("git", "init", "--bare", "-b", "main", str(remote)), check=True, capture_output=True)  # noqa: S603, S607
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "refs/heads/main:refs/heads/main")
    target_head = _advance_remote_target(tmp_path, remote)

    receipt = application.sync_change_with_target("change-a", target_head, "sync-change-a")
    acquired = application.acquire_frontier_work()

    assert acquired.failures == ()
    assert len(acquired.launch_packages) == 1
    assert acquired.launch_packages[0].source_head == receipt.merged_head
    assert application._workspace_manager.reviewed_source_head("change-a") == receipt.merged_head


def test_target_sync_demotes_ready_pull_request_before_moving_managed_branch(tmp_path: Path) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    repository = application._workspace_manager.repository
    remote = tmp_path / "target-remote.git"
    subprocess.run(("git", "init", "--bare", "-b", "main", str(remote)), check=True, capture_output=True)  # noqa: S603, S607
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "refs/heads/main:refs/heads/main")
    target_head = _advance_remote_target(tmp_path, remote)
    coordination = application._workspace_manager.show("change-a")
    draft_transition_heads: list[tuple[str, str, bool]] = []
    original_transition = provider.set_pull_request_draft_state.side_effect

    def observe_transition(request):
        draft_transition_heads.append(
            (
                _git(repository, "rev-parse", coordination.branch),
                request.expected_head_sha,
                request.draft,
            )
        )
        return original_transition(request)

    provider.set_pull_request_draft_state.side_effect = observe_transition

    receipt = application.sync_change_with_target("change-a", target_head, "sync-before-branch-move")

    assert draft_transition_heads == [(exact_head, exact_head, True)]
    assert _git(repository, "rev-parse", coordination.branch) == receipt.merged_head
    assert state["pull_request"].draft is True
    assert runtime.ready_receipt() is None


def test_external_head_adoption_demotes_ready_pull_request_before_moving_managed_branch(tmp_path: Path) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    repository = application._workspace_manager.repository
    coordination = application._workspace_manager.show("change-a")
    adopted_head = _publish_external_change_head(tmp_path, repository, coordination.branch, exact_head)
    draft_transition_heads: list[tuple[str, str, bool]] = []
    original_transition = provider.set_pull_request_draft_state.side_effect

    def observe_transition(request):
        draft_transition_heads.append(
            (
                _git(repository, "rev-parse", coordination.branch),
                request.expected_head_sha,
                request.draft,
            )
        )
        return original_transition(request)

    provider.set_pull_request_draft_state.side_effect = observe_transition

    receipt = application.adopt_external_head(
        "change-a",
        exact_head,
        adopted_head,
        "adopt-before-branch-move",
    )

    assert draft_transition_heads == [(exact_head, exact_head, True)]
    assert _git(repository, "rev-parse", coordination.branch) == adopted_head
    assert state["pull_request"].draft is True
    assert runtime.ready_receipt() is None
    assert receipt.adopted_head == adopted_head


def test_external_head_adoption_retains_attention_after_demotion_then_movement_failure(tmp_path: Path) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    repository = application._workspace_manager.repository
    coordination = application._workspace_manager.show("change-a")
    adopted_head = _publish_external_change_head(tmp_path, repository, coordination.branch, exact_head)
    provider.set_pull_request_draft_state.reset_mock()
    original_run_git = application._workspace_manager._run_git

    def fail_merge(*arguments: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if arguments and arguments[0] == "merge":
            return subprocess.CompletedProcess(arguments, 1, b"", b"fast-forward failed")
        return original_run_git(*arguments, **kwargs)

    with (
        patch.object(application._workspace_manager, "_run_git", side_effect=fail_merge),
        pytest.raises(PortfolioApplicationError, match="external Change head could not be adopted"),
    ):
        application.adopt_external_head("change-a", exact_head, adopted_head, "adopt-after-demotion")

    attention = runtime.change_disposition()
    assert attention is not None
    assert attention.kind.value == "publication-attention"
    assert attention.diagnostics[:2] == (
        "external-head-adoption-movement-failed",
        "external-head-adoption-operation:adopt-after-demotion",
    )
    assert runtime.ready_receipt() is None
    assert state["pull_request"].draft is True


def test_target_sync_conflict_survives_attention_publication_failure(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    application.finalize_change("change-a", _finalization_request("change-a", exact_head))
    publisher = Mock()
    publisher.publish.side_effect = DeliveryStatePublicationError(
        "Delivery state is unavailable",
        retry_safe=True,
    )
    application._delivery_state_publisher = publisher

    conflict = ChangeTargetSyncConflictError(
        "change-a",
        "sync-publication-failure",
        "2" * 40,
        ("product.txt",),
    )
    with (
        patch.object(application._workspace_manager, "sync_with_target", side_effect=conflict),
        pytest.raises(ChangeTargetSyncConflictError, match=r"product\.txt"),
    ):
        application.sync_change_with_target("change-a", "2" * 40, "sync-publication-failure")

    assert runtimes["change-a"].change_disposition() is not None
    publisher.publish.assert_called_once()


def test_external_head_adoption_error_survives_attention_publication_failure(tmp_path: Path) -> None:
    application, runtime, provider, _state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    repository = application._workspace_manager.repository
    coordination = application._workspace_manager.show("change-a")
    adopted_head = _publish_external_change_head(tmp_path, repository, coordination.branch, exact_head)
    provider.set_pull_request_draft_state.reset_mock()
    state_publisher = Mock()
    state_publisher.publish.side_effect = DeliveryStatePublicationError(
        "Delivery state is unavailable",
        retry_safe=True,
    )
    application._delivery_state_publisher = state_publisher
    original_run_git = application._workspace_manager._run_git

    def fail_merge(*arguments: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if arguments and arguments[0] == "merge":
            return subprocess.CompletedProcess(arguments, 1, b"", b"fast-forward failed")
        return original_run_git(*arguments, **kwargs)

    with (
        patch.object(application._workspace_manager, "_run_git", side_effect=fail_merge),
        pytest.raises(PortfolioApplicationError, match="external Change head could not be adopted"),
    ):
        application.adopt_external_head("change-a", exact_head, adopted_head, "adopt-publication-failure")

    assert runtime.change_disposition() is not None
    state_publisher.publish.assert_called_once()


def test_provider_demotion_failure_prevents_target_sync_branch_movement(tmp_path: Path) -> None:
    application, runtime, provider, _state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    repository = application._workspace_manager.repository
    remote = tmp_path / "target-failure-remote.git"
    subprocess.run(("git", "init", "--bare", "-b", "main", str(remote)), check=True, capture_output=True)  # noqa: S603, S607
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "refs/heads/main:refs/heads/main")
    target_head = _advance_remote_target(tmp_path, remote)
    branch = application._workspace_manager.show("change-a").branch
    provider.set_pull_request_draft_state.side_effect = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE,
        "return_to_draft",
        "provider unavailable",
        retry_safe=True,
    )

    with pytest.raises(PortfolioApplicationError, match="target synchronization could not be completed"):
        application.sync_change_with_target("change-a", target_head, "sync-provider-failure")

    assert _git(repository, "rev-parse", branch) == exact_head
    assert runtime.ready_receipt() is not None


def test_hung_target_fetch_is_bounded_and_releases_checkpoint_target_sync_and_publication_locks(
    tmp_path: Path,
    ext_remote,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application, runtime, _provider, _state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    repository = application._workspace_manager.repository
    remote = tmp_path / "hung-target-remote.git"
    subprocess.run(("git", "init", "--bare", "-b", "main", str(remote)), check=True, capture_output=True)  # noqa: S603, S607
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "refs/heads/main:refs/heads/main")
    target_head = _advance_remote_target(tmp_path, remote)
    transport = ext_remote(remote)
    transport.use(repository)
    transport.modes("upload-pack", "hang")
    monkeypatch.setattr(remote_git, "READ_TIMEOUT_SECONDS", 1.0)
    branch = application._workspace_manager.show("change-a").branch

    started = time.monotonic()
    with pytest.raises(PortfolioApplicationError, match="target synchronization could not be completed") as raised:
        application.sync_change_with_target("change-a", target_head, "sync-hung-fetch")

    assert time.monotonic() - started < 10
    assert isinstance(raised.value.__cause__, remote_git.RemoteGitTimeout)
    transport.assert_exited("upload-pack")
    assert _git(repository, "rev-parse", branch) == exact_head
    assert runtime.ready_receipt() is not None
    lock_roots = (
        application._checkpoint_lock_root("change-a"),
        application._workspace_manager.runtime_root / "coordination" / "target-sync-lock",
    )
    with (
        locked_roots(lock_roots, blocking=False),
        application._workspace_manager._coordinator.publication_lock("change-a", blocking=False),
    ):
        pass


def test_application_captures_target_sync_conflict_as_publication_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    finalization = application.finalize_change("change-a", _finalization_request("change-a", exact_head))

    with (
        patch.object(
            application._workspace_manager,
            "sync_with_target",
            side_effect=ChangeTargetSyncConflictError(
                "change-a",
                "sync-change-a",
                "2" * 40,
                ("product.txt",),
            ),
        ),
        pytest.raises(ChangeTargetSyncConflictError) as raised,
    ):
        application.sync_change_with_target("change-a", "2" * 40, "sync-change-a")

    assert raised.value.code == "ERR_TARGET_SYNC_CONFLICT"
    assert raised.value.conflict_paths == ("product.txt",)
    attention = runtimes["change-a"].change_disposition()
    assert attention is not None
    assert attention.kind.value == "publication-attention"
    assert attention.diagnostics == (
        "target-sync-operation:sync-change-a",
        "target synchronization merge conflict",
        "conflict-path:product.txt",
    )
    assert runtimes["change-a"].finalization() is None
    assert runtimes["change-a"].finalization_invalidation().finalization_id == finalization.finalization_id
    assert runtimes["change-a"].finalization_invalidation().reason == "target-sync-conflict"


@pytest.mark.parametrize("lifecycle", [DeliveryChangeStage.DEFERRED, DeliveryChangeStage.ABANDONED])
def test_target_sync_rejects_terminal_or_deferred_change_before_workspace_mutation(
    tmp_path: Path,
    lifecycle: DeliveryChangeStage,
) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    if lifecycle is DeliveryChangeStage.DEFERRED:
        _change_intent(application, "change-a", DeliveryChangeIntentKind.DEFER, "Wait before target synchronization")
    else:
        application.abandon_change("change-a", "Stop before target synchronization")
    before = coordinator.show("change-a")

    with (
        patch.object(application._workspace_manager, "sync_with_target") as workspace_sync,
        pytest.raises(PortfolioApplicationError, match="requires a mutable Change"),
    ):
        application.sync_change_with_target("change-a", "2" * 40, "sync-lifecycle")

    assert not workspace_sync.called
    assert coordinator.show("change-a") == before
    assert runtimes["change-a"].change_stage() is lifecycle


def test_application_aborts_target_sync_conflict_and_resolves_exact_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    disposition = runtimes["change-a"].capture_target_sync_conflict(
        "sync-abort",
        "2" * 40,
        datetime.now(UTC),
        ("target synchronization merge conflict",),
    )
    receipt = ChangeTargetSyncAbortReceipt.create(
        operation_id="sync-abort",
        change_id="change-a",
        target_head="2" * 40,
        restored_head=exact_head,
    )

    with patch.object(application._workspace_manager, "abort_target_sync_conflict", return_value=receipt):
        assert (
            application.abort_target_sync_conflict(
                "change-a",
                disposition.disposition_id,
                "2" * 40,
                "sync-abort",
            )
            == receipt
        )

    assert runtimes["change-a"].change_disposition() is None
    assert runtimes["change-a"].change_disposition_resolution().disposition_id == disposition.disposition_id


def test_resolving_change_attention_fails_fast_when_checkpoint_is_busy(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    disposition = runtimes["change-a"].capture_publication_attention(
        datetime(2026, 8, 11, 16, tzinfo=UTC),
        ("provider unavailable",),
    )

    with (
        patch("owlbear_delivery.application_lifecycle._ATTENTION_RESOLUTION_LOCK_TIMEOUT_SECONDS", 0.0),
        locked_roots((state_root / "publications/checkpoints/locks/change-a",)),
        pytest.raises(DeliveryChangeDispositionBusyError, match="already in progress"),
    ):
        application.resolve_change_disposition("change-a", disposition.disposition_id)

    assert runtimes["change-a"].change_disposition() == disposition


def test_resolving_change_attention_retries_short_checkpoint_contention(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    disposition = runtimes["change-a"].capture_publication_attention(
        datetime(2026, 8, 11, 16, tzinfo=UTC),
        ("provider unavailable",),
    )
    lock = locked_roots((state_root / "publications/checkpoints/locks/change-a",))
    lock.__enter__()
    released = False

    def release_lock(_delay: float) -> None:
        nonlocal released
        lock.__exit__(None, None, None)
        released = True

    try:
        with patch("owlbear_delivery.portfolio_application.time.sleep", side_effect=release_lock) as sleep:
            resolution = application.resolve_change_disposition("change-a", disposition.disposition_id)
        sleep.assert_called_once()
    finally:
        if not released:
            lock.__exit__(None, None, None)

    assert resolution.disposition_id == disposition.disposition_id
    assert runtimes["change-a"].change_disposition() is None


def test_resolving_change_attention_publishes_and_replays_delivery_state(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    disposition = runtimes["change-a"].capture_publication_attention(
        datetime(2026, 8, 11, 16, tzinfo=UTC),
        ("provider unavailable",),
    )
    publisher = Mock()
    application._delivery_state_publisher = publisher
    resolution = DeliveryChangeDispositionResolution.create(
        change_id="change-a",
        disposition_id=disposition.disposition_id,
        resolved_at=datetime(2026, 8, 11, 17, tzinfo=UTC),
    )

    with patch(
        "owlbear_delivery.application_lifecycle._timestamp",
        return_value=resolution.resolved_at,
    ):
        first = application.resolve_change_disposition("change-a", disposition.disposition_id)
        second = application.resolve_change_disposition("change-a", disposition.disposition_id)

    assert first == second == resolution
    assert publisher.publish.call_count == 2
    assert publisher.publish.call_args_list[0].kwargs["operation_id"] == (
        f"attention-resolution-{resolution.resolution_id}"
    )
    assert publisher.publish.call_args_list[1].kwargs["operation_id"] == (
        f"attention-resolution-{resolution.resolution_id}"
    )


def test_application_records_semantic_target_resolution_with_exact_runtime_receipt(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    finalization = application.finalize_change("change-a", _finalization_request("change-a", exact_head))
    disposition = runtimes["change-a"].capture_target_sync_conflict(
        "sync-resolve",
        "2" * 40,
        datetime.now(UTC),
        ("target synchronization merge conflict",),
    )
    receipt = ChangeTargetSyncReceipt.create(
        operation_id="sync-resolve",
        change_id="change-a",
        integration_target="main",
        expected_target="2" * 40,
        target_head="2" * 40,
        change_head_before=exact_head,
        merged_head="3" * 40,
        merge_commit=True,
    )

    with patch.object(application._workspace_manager, "resolve_target_sync_conflict", return_value=receipt):
        assert (
            application.resolve_target_sync_conflict(
                "change-a",
                disposition.disposition_id,
                "2" * 40,
                "sync-resolve",
            )
            == receipt
        )

    assert runtimes["change-a"].change_disposition() is None
    assert runtimes["change-a"].target_sync_receipt() == receipt
    assert runtimes["change-a"].finalization() is None
    assert runtimes["change-a"].finalization_invalidation().finalization_id == finalization.finalization_id


def test_target_sync_resolution_publishes_branch_before_state_snapshot(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    application.finalize_change("change-a", _finalization_request("change-a", exact_head))
    disposition = runtimes["change-a"].capture_target_sync_conflict(
        "sync-ordered",
        "2" * 40,
        datetime.now(UTC),
        ("target synchronization merge conflict",),
    )
    receipt = ChangeTargetSyncReceipt.create(
        operation_id="sync-ordered",
        change_id="change-a",
        integration_target="main",
        expected_target="2" * 40,
        target_head="2" * 40,
        change_head_before=exact_head,
        merged_head="3" * 40,
        merge_commit=True,
        review_required=True,
    )
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    state_publisher = Mock()

    def publish_state(**_kwargs: object) -> None:
        assert branch_publisher.publish.call_count == 1

    state_publisher.publish.side_effect = publish_state
    application._change_branch_publisher = branch_publisher
    application._delivery_state_publisher = state_publisher

    with patch.object(application._workspace_manager, "resolve_target_sync_conflict", return_value=receipt):
        resolved = application.resolve_target_sync_conflict(
            "change-a",
            disposition.disposition_id,
            "2" * 40,
            "sync-ordered",
        )

    assert resolved == receipt
    branch_request = branch_publisher.publish.call_args.args[0]
    assert branch_request.expected_published_head == receipt.merged_head
    assert branch_request.expected_remote_head is None
    assert runtimes["change-a"].checkpoint_publication_state().published_head == receipt.merged_head
    assert runtimes["change-a"].checkpoint_publication_state().pending_checkpoint is None
    assert runtimes["change-a"].target_sync_receipt() == receipt


def test_target_sync_resolution_replays_branch_after_state_publication_failure(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    disposition = runtimes["change-a"].capture_target_sync_conflict(
        "sync-retry",
        "2" * 40,
        datetime.now(UTC),
        ("target synchronization merge conflict",),
    )
    receipt = ChangeTargetSyncReceipt.create(
        operation_id="sync-retry",
        change_id="change-a",
        integration_target="main",
        expected_target="2" * 40,
        target_head="2" * 40,
        change_head_before=exact_head,
        merged_head="3" * 40,
        merge_commit=True,
        review_required=True,
    )
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    state_publisher = Mock()
    state_publisher.publish.side_effect = [
        DeliveryStatePublicationError("state unavailable", retry_safe=True),
        None,
    ]
    application._change_branch_publisher = branch_publisher
    application._delivery_state_publisher = state_publisher

    with patch.object(application._workspace_manager, "resolve_target_sync_conflict", return_value=receipt):
        with pytest.raises(DeliveryStatePublicationError, match="state unavailable"):
            application.resolve_target_sync_conflict(
                "change-a",
                disposition.disposition_id,
                "2" * 40,
                "sync-retry",
            )

        assert runtimes["change-a"].checkpoint_publication_state().published_head == receipt.merged_head

        replayed = application.resolve_target_sync_conflict(
            "change-a",
            disposition.disposition_id,
            "2" * 40,
            "sync-retry",
        )

    assert replayed == receipt
    assert branch_publisher.publish.call_count == 1
    assert state_publisher.publish.call_count == 2


def test_target_sync_publication_repair_reconciles_quarantined_state_and_preserves_review_gate(
    tmp_path: Path,
) -> None:
    application, runtime_map, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    runtime = runtime_map["change-a"]
    initial_head = coordinator.show("change-a").last_reviewed_commit
    merged_head = _commit_local_descendant(coordinator.show("change-a"), "target-sync-repair.txt")
    application._workspace_manager.record_reviewed("change-a", merged_head)
    receipt = ChangeTargetSyncReceipt.create(
        operation_id="sync-repair",
        change_id="change-a",
        integration_target="main",
        expected_target="2" * 40,
        target_head="2" * 40,
        change_head_before=initial_head,
        merged_head=merged_head,
        merge_commit=True,
        review_required=True,
    )
    runtime.record_target_sync(receipt, datetime.now(UTC))
    _set_checkpoint(
        runtime,
        state_root,
        DeliveryPendingCheckpoint(
            head=merged_head,
            triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.EXPLICIT),),
        ),
        published_head=initial_head,
    )
    application._startup_health_diagnostics = (
        DeliveryHealthDiagnostic(
            source="remote-state",
            code="remote-state-reconciliation-required",
            detail="remote Change branch differs from Delivery-state snapshot: change-a",
            change_id="change-a",
            reason=DeliveryHealthReason.REMOTE_CHANGE_HEAD_MISMATCH,
        ),
    )
    application._reconcile_runtimes()
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    state_publisher = Mock()

    def publish_state(**_kwargs: object) -> None:
        assert branch_publisher.publish.call_count == 1
        assert runtime.checkpoint_publication_state().published_head == merged_head

    state_publisher.publish.side_effect = publish_state
    application._change_branch_publisher = branch_publisher
    application._delivery_state_publisher = state_publisher
    application._draft_pull_request_publisher = Mock()

    repaired = application.repair_target_sync_publication(
        "change-a",
        initial_head,
        merged_head,
        "sync-repair",
        "repair-sync-repair",
        confirmed_repair=True,
    )

    assert repaired.repaired_head == merged_head
    assert repaired.review_required is True
    assert application.delivery_health().diagnostics == ()
    assert runtime.finalization() is None
    blocked = application.reconcile_change_checkpoint("change-a")
    assert blocked.reconciled is True
    assert runtime.target_sync_receipt().review_required is True


def test_resolved_target_merge_requires_fresh_finalization_before_checkpoint_publication(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    repository = application._workspace_manager.repository
    remote = tmp_path / "resolved-merge-remote.git"
    subprocess.run(("git", "init", "--bare", "-b", "main", str(remote)), check=True, capture_output=True)  # noqa: S603, S607
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "refs/heads/main:refs/heads/main")
    target_head = _advance_remote_target(tmp_path, remote, product="target\n")
    coordination = coordinator.show("change-a")
    (coordination.worktree_path / "product.txt").write_text("change\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "product.txt")
    _git(coordination.worktree_path, "commit", "-m", "change branch edit")
    reviewed_head = _git(coordination.worktree_path, "rev-parse", "HEAD")
    application._workspace_manager.record_reviewed("change-a", reviewed_head)

    with pytest.raises(ChangeTargetSyncConflictError):
        application.sync_change_with_target("change-a", target_head, "sync-resolved-merge")

    disposition = runtimes["change-a"].change_disposition()
    assert disposition is not None
    (coordination.worktree_path / "product.txt").write_text("resolved\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "product.txt")
    receipt = application.resolve_target_sync_conflict(
        "change-a",
        disposition.disposition_id,
        target_head,
        "sync-resolved-merge",
    )
    application._change_branch_publisher = Mock()
    application._draft_pull_request_publisher = Mock()

    result = application.reconcile_change_checkpoint("change-a")

    assert receipt.review_required is True
    assert receipt.schema_version == 2
    assert runtimes["change-a"].finalization() is None
    assert result.reconciled is False
    assert result.state.pending_checkpoint is not None
    assert result.state.pending_checkpoint.head == receipt.merged_head
    application._change_branch_publisher.publish.assert_not_called()
    application._draft_pull_request_publisher.publish.assert_not_called()


@pytest.mark.parametrize("operation", ["abort_target_sync_conflict", "resolve_target_sync_conflict"])
def test_target_sync_conflict_exit_rejects_deferred_change_before_workspace_mutation(
    tmp_path: Path,
    operation: str,
) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    runtime = runtimes["change-a"]
    disposition = runtime.capture_target_sync_conflict(
        "sync-deferred",
        "2" * 40,
        datetime.now(UTC),
        ("target synchronization merge conflict",),
    )
    _change_intent(application, "change-a", DeliveryChangeIntentKind.DEFER, "Wait before resolving the preserved merge")

    with (
        patch.object(application._workspace_manager, operation) as workspace_exit,
        pytest.raises(PortfolioApplicationError, match="requires a mutable Change"),
    ):
        getattr(application, operation)(
            "change-a",
            disposition.disposition_id,
            "2" * 40,
            "sync-deferred",
        )

    assert not workspace_exit.called
    assert runtime.change_stage() is DeliveryChangeStage.DEFERRED


@pytest.mark.parametrize("operation", ["abort_target_sync_conflict", "resolve_target_sync_conflict"])
def test_target_sync_conflict_exit_rejects_abandoned_change_before_workspace_mutation(
    tmp_path: Path,
    operation: str,
) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    runtime = runtimes["change-a"]
    disposition = runtime.capture_target_sync_conflict(
        "sync-abandoned",
        "2" * 40,
        datetime.now(UTC),
        ("target synchronization merge conflict",),
    )
    application.abandon_change("change-a", "Stop the unresolved Change")

    with (
        patch.object(application._workspace_manager, operation) as workspace_exit,
        pytest.raises(DeliveryRuntimeConflictError, match="target synchronization"),
    ):
        getattr(application, operation)(
            "change-a",
            disposition.disposition_id,
            "2" * 40,
            "sync-abandoned",
        )

    assert not workspace_exit.called
    assert runtime.change_stage() is DeliveryChangeStage.ABANDONED


def test_abandoning_preserved_target_sync_conflict_surfaces_cleanup_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    repository = application._workspace_manager.repository
    remote = tmp_path / "remote.git"
    subprocess.run(("git", "init", "--bare", "-b", "main", str(remote)), check=True, capture_output=True)  # noqa: S603, S607
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "refs/heads/main:refs/heads/main")
    target_head = _advance_remote_target(tmp_path, remote, product="target\n")
    coordination = coordinator.show("change-a")
    (coordination.worktree_path / "product.txt").write_text("change\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "product.txt")
    _git(coordination.worktree_path, "commit", "-m", "change branch edit")
    application._workspace_manager.record_reviewed(
        "change-a",
        _git(coordination.worktree_path, "rev-parse", "HEAD"),
    )

    with pytest.raises(ChangeTargetSyncConflictError):
        application.sync_change_with_target("change-a", target_head, "sync-abandoned-cleanup")

    application.abandon_change("change-a", "Stop the unresolved Change")

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        application.cleanup_abandoned_change_worktree("change-a")

    assert ChangeWorktreeAttentionCode.WORKTREE_DIRTY in raised.value.attention
    assert runtimes["change-a"].change_stage() is DeliveryChangeStage.ABANDONED
    assert coordination.worktree_path.exists()


@pytest.mark.parametrize("remove_worktree", [False, True])
def test_abandoned_target_sync_conflict_can_be_discarded_and_cleaned(
    tmp_path: Path,
    remove_worktree: bool,  # noqa: FBT001 - pytest parametrization supplies this boolean positionally.
) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    repository = application._workspace_manager.repository
    remote = tmp_path / "discard-merge-remote.git"
    subprocess.run(("git", "init", "--bare", "-b", "main", str(remote)), check=True, capture_output=True)  # noqa: S603, S607
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "refs/heads/main:refs/heads/main")
    target_head = _advance_remote_target(tmp_path, remote, product="target\n")
    coordination = coordinator.show("change-a")
    (coordination.worktree_path / "product.txt").write_text("change\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "product.txt")
    _git(coordination.worktree_path, "commit", "-m", "change branch edit")
    application._workspace_manager.record_reviewed(
        "change-a",
        _git(coordination.worktree_path, "rev-parse", "HEAD"),
    )

    with pytest.raises(ChangeTargetSyncConflictError):
        application.sync_change_with_target("change-a", target_head, "sync-discard-cleanup")
    application.abandon_change("change-a", "Stop the unresolved Change")
    if remove_worktree:
        _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))

    with pytest.raises(PortfolioApplicationError, match="conflict evidence is stale"):
        application.cleanup_abandoned_change_worktree_after_target_sync_discard(
            "change-a",
            confirmed_discard=True,
            expected_target_head=target_head,
            expected_operation_id="stale-operation",
        )

    receipt = application.cleanup_abandoned_change_worktree_after_target_sync_discard(
        "change-a",
        confirmed_discard=True,
        expected_target_head=target_head,
        expected_operation_id="sync-discard-cleanup",
    )

    assert receipt.change_id == "change-a"
    assert not coordination.worktree_path.exists()
    assert _git_ref_exists(repository, coordination.branch)
    assert runtimes["change-a"].change_stage() is DeliveryChangeStage.ABANDONED
    assert coordinator.show("change-a").target_sync_conflict is None
    assert coordinator.show("change-a").target_sync_abort_receipt is not None
    assert application.list_retained_change_worktrees() == ()


@pytest.mark.parametrize("dirty", [False, True])
def test_captured_readiness_agrees_across_public_reads(tmp_path: Path, *, dirty: bool) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    coordination = coordinator.show("change-a")
    if dirty:
        (coordination.worktree_path / "product.txt").unlink()
    before = runtimes["change-a"].frontier_bytes()
    context = application.show_finalization_context("change-a")
    group = application.list_changes().groups[0]
    card = next(item for item in group.items if item.item_key == "publication")
    detail = application.show_work_item_view("change-a", "publication")
    with patch.object(
        application._workspace_manager,
        "observed_change_head",
        wraps=application._workspace_manager.observed_change_head,
    ) as observe:
        change = application.get_change("change-a")
    assert observe.call_count == 1
    assert card.readiness == detail.readiness == change.readiness == context.readiness
    assert context.readiness.executable is not dirty
    assert context.readiness.reason_code == ("workspace-dirty" if dirty else "ready")
    if dirty:
        assert context.readiness.prompt is not None
        assert context.readiness.prompt.startswith("/repair-delivery Diagnose Change change-a read-only")
    else:
        assert context.readiness.prompt == (
            "/continue-change change-a reread get_change and pass its readiness basis unchanged "
            "to acquire_change_action; declare only capabilities this session can dispatch and "
            "execute only the acquired operation. Yield on busy, "
            "waiting, and human; do not dispatch siblings or infer progress."
        )
    assert context.readiness.checks_state == "not-run"
    assert runtimes["change-a"].frontier_bytes() == before
    if not dirty:
        (coordination.worktree_path / "product.txt").write_text("changed after read\n")
    with pytest.raises(PortfolioApplicationError):
        application.finalize_change("change-a", _finalization_request("change-a", coordination.last_reviewed_commit))
    assert runtimes["change-a"].finalization() is None


@pytest.mark.parametrize(
    ("reason", "executable", "prompt_prefix"),
    [
        ("ready", True, "/continue-change"),
        ("request-action", True, "/continue-change"),
        ("ready", False, None),
        ("engine-action-pending", False, "/continue-change"),
        ("engine-action-interrupted", False, "/continue-change"),
        ("engine-action-failed", False, "/repair-delivery"),
        ("engine-action-incomplete", False, "/repair-delivery"),
        ("engine-action-blocked", False, "/repair-delivery"),
        ("coordination-unavailable", False, "/repair-delivery"),
        ("active-custody", False, "/repair-delivery"),
        ("claim-activation-failed", False, "/repair-delivery"),
        ("claim-custody-unreconciled", False, "/repair-delivery"),
        ("dependency-wait", False, None),
        ("publication-wait", False, None),
        ("change-terminal", False, None),
        ("retry-backoff", False, None),
        ("retry-exhausted", False, "/inspect-change"),
        ("acceptance-wait", False, None),
        ("workspace-dirty", False, "/repair-delivery"),
        ("workspace-preflight-failed", False, "/repair-delivery"),
        ("workspace-inspection-failed", False, "/repair-delivery"),
        ("retry-containment", False, "/repair-delivery"),
        ("retry-ledger-unavailable", False, "/repair-delivery"),
    ],
)
def test_engine_action_prompt_is_applicable_to_final_readiness_state(
    *,
    reason: str,
    executable: bool,
    prompt_prefix: str | None,
) -> None:
    prompt = PortfolioApplication._engine_action_prompt("change-a", reason, executable=executable)
    if prompt_prefix is None:
        assert prompt is None
    else:
        assert prompt is not None
        assert prompt.startswith(prompt_prefix)


def test_continuation_activation_failure_fallback_clears_runnable_prompt(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    readiness = application.get_change("change-a").readiness
    assert readiness.executable
    assert readiness.prompt is not None
    assert readiness.prompt.startswith("/continue-change")
    candidate = application._candidates("change-a")[0]
    failure = DeliveryAcquisitionFailure(
        change_id="change-a",
        outcome_id=candidate.binding.outcome_id,
        code="ERR_DELIVERY_CLAIM_ACTIVATION_FAILED",
        detail="injected activation failure",
        retry_condition="closure is unverified",
    )
    with patch.object(application, "_delivery_snapshot", side_effect=OSError("snapshot unavailable")):
        result = application._continuation_launch_failure(candidate, readiness, failure)
    assert result.kind == "unavailable"
    assert result.reason_code == "claim-activation-failed"
    assert result.readiness.executable is False
    assert result.readiness.prompt.startswith("/repair-delivery")
    assert "read-only" in result.readiness.prompt


@pytest.mark.parametrize("failure", [PermissionError("private detail"), subprocess.TimeoutExpired("git", 10)])
def test_required_workspace_inspection_is_bounded_and_isolated(tmp_path: Path, failure: Exception) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.COMPLETED, "change-b": DeliveryStage.DESIGN}
    )
    manager = application._workspace_manager
    with patch.object(manager, "capture_finalization_workspace", side_effect=failure) as capture:
        view = application.list_changes()
    assert capture.call_count == 1
    card = next(item for item in view.groups[0].items if item.item_key == "publication")
    assert card.readiness.status == "unavailable"
    assert card.readiness.reason_code == "workspace-inspection-failed"
    assert card.readiness.basis.workspace_fingerprint is None
    assert not card.readiness.executable
    assert view.groups[1].change_id == "change-b"


def _failure_request(application: PortfolioApplication, **updates):
    readiness = application.show_finalization_context("change-a").readiness
    return ReportFinalizationFailure(
        **{
            "change_id": "change-a",
            "expected_contract_digest": readiness.basis.contract_digest,
            "expected_frontier_digest": readiness.basis.frontier_digest,
            "expected_change_head": readiness.basis.candidate_head,
            "expected_reviewed_head": readiness.basis.reviewed_head,
            "expected_diagnostic_sequence": readiness.basis.diagnostic_sequence,
            "attempt_key": "attempt-1",
            "category": "maintained-check",
            "code": FinalizationFailureCode.MAINTAINED_CHECK_FAILED,
            "checks_state": "failed",
            **updates,
        }
    )


def _finalizer_settlement(
    application: PortfolioApplication,
    attempt: ChangeFinalizationAttempt,
    report: FinalizationReport,
    **updates: object,
) -> FinalizerSettlement:
    coordination = application._workspace_manager.show(report.request.change_id)
    return FinalizerSettlement(
        change_id=report.request.change_id,
        attempt_id=attempt.writer.attempt_id,
        claim_id=attempt.writer.claim_id,
        expected_head=attempt.exact_head,
        expected_reviewed_base=coordination.last_reviewed_commit,
        report_id=report.report_id,
        disposition="normal-return",
        outcome="review-failed" if report.request.category == "independent-review" else "proof-failed",
        host_id=attempt.writer.actor_id,
        session_id=attempt.writer.process_id,
    ).model_copy(update=updates)


@pytest.mark.parametrize(
    ("category", "code", "expected_outcome"),
    [
        ("maintained-check", FinalizationFailureCode.MAINTAINED_CHECK_FAILED, "proof-failed"),
        ("independent-review", FinalizationFailureCode.INDEPENDENT_REVIEW_FAILED, "review-failed"),
    ],
)
def test_normal_finalizer_failure_settlement_releases_slot_without_granting_proof(
    tmp_path: Path,
    category: str,
    code: FinalizationFailureCode,
    expected_outcome: str,
) -> None:
    now = "2026-08-04T00:00:00Z"
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED, "change-b": DeliveryStage.PLANNING},
        clock=lambda: now,
        execution_capacity=1,
    )
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.kind == "acquired"
    assert acquired.finalization is not None
    attempt = acquired.finalization.attempt
    report = application.report_finalization_failure(
        _failure_request(application, attempt_key=attempt.writer.attempt_id, category=category, code=code)
    )
    assert isinstance(report, FinalizationReport)
    settlement = _finalizer_settlement(application, attempt, report)
    assert settlement.outcome == expected_outcome
    before_ledger = RetryLedger(state_root, "change-a").read()
    worktree = coordinator.show("change-a").worktree_path
    index_path = Path(_git(worktree, "rev-parse", "--git-path", "index"))
    if not index_path.is_absolute():
        index_path = worktree / index_path
    workspace_bytes = tuple(
        (path.relative_to(worktree).as_posix(), path.read_bytes())
        for path in sorted(worktree.rglob("*"))
        if path.is_file() and path.name != ".git"
    )
    protected_bytes = (
        runtimes["change-a"].frontier_bytes(),
        index_path.read_bytes(),
        _git(application._workspace_manager.repository, "show-ref"),
        workspace_bytes,
    )

    waiting = application.acquire_change_action(_continuation_request(application, "change-b"))
    assert waiting.kind == "waiting"
    assert waiting.reason_code == "execution-capacity"

    receipt = application.settle_finalizer_invocation(settlement)
    assert isinstance(receipt, FinalizerSettlementReceipt)
    assert receipt.finished_at.isoformat().replace("+00:00", "Z") == now
    attention = coordinator.show("change-a").finalization_attention
    assert attention is not None
    assert coordinator.show("change-a").writer is not None
    assert coordinator.show("change-a").writer.kind == "finalization-attention"
    assert coordinator.show("change-a").finalization_attempt.finished_at == receipt.finished_at.isoformat().replace(
        "+00:00", "Z"
    )
    assert attention.receipt_id == receipt.receipt_id
    assert runtimes["change-a"].finalization() is None
    assert (
        runtimes["change-a"].frontier_bytes(),
        index_path.read_bytes(),
        _git(application._workspace_manager.repository, "show-ref"),
        tuple(
            (path.relative_to(worktree).as_posix(), path.read_bytes())
            for path in sorted(worktree.rglob("*"))
            if path.is_file() and path.name != ".git"
        ),
    ) == protected_bytes
    RetryLedger(state_root, "change-a").reconcile_owner_results()
    assert RetryLedger(state_root, "change-a").read() == before_ledger
    owner_result = state_root / "changes/change-a/retry-ledger/owner-results" / f"{attempt.writer.attempt_id}.json"
    assert owner_result.is_file()
    assert json.loads(owner_result.read_text())["accepted"] is False
    assert FinalizationReportStore(state_root, "change-a").read().current_report_id == report.report_id

    failed_view = application.get_change("change-a")
    assert failed_view.readiness.status != "passed"
    assert failed_view.readiness.checks_state == "failed"
    assert failed_view.readiness.last_attempt is not None
    assert failed_view.readiness.last_attempt.report == report
    assert failed_view.readiness.last_attempt.applicability == "current"
    assert failed_view.finalization_attempt.finished_at is not None
    assert application.settle_finalizer_invocation(settlement) == receipt

    next_claim = application.acquire_change_action(_continuation_request(application, "change-b"))
    if next_claim.kind == "reconciled":
        next_claim = application.acquire_change_action(_continuation_request(application, "change-b"))
    assert next_claim.kind == "acquired"


def test_finalization_attention_replays_only_its_report_and_rejects_new_diagnostics(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None
    attempt = acquired.finalization.attempt
    request = _failure_request(application, attempt_key=attempt.writer.attempt_id)
    report = application.report_finalization_failure(request)
    assert isinstance(report, FinalizationReport)
    settlement = _finalizer_settlement(application, attempt, report)
    receipt = application.settle_finalizer_invocation(settlement)
    assert isinstance(receipt, FinalizerSettlementReceipt)
    with pytest.raises(DeliveryActionSelectionConflictError):
        application.settle_finalizer_invocation(settlement.model_copy(update={"claim_id": "conflicting-claim"}))

    report_store = FinalizationReportStore(state_root, "change-a")
    ledger = RetryLedger(state_root, "change-a")
    coordination_path = state_root / "coordination/changes/change-a.json"
    report_state = (
        report_store.read(),
        ledger.read(),
        coordination_path.read_bytes(),
        runtimes["change-a"].frontier_bytes(),
    )
    assert application.report_finalization_failure(request) == report
    assert (
        report_store.read(),
        ledger.read(),
        coordination_path.read_bytes(),
        runtimes["change-a"].frontier_bytes(),
    ) == report_state
    conflicting_request = request.model_copy(
        update={"attempt_key": "post-attention-attempt", "expected_diagnostic_sequence": report.sequence}
    )
    with pytest.raises(FinalizationReportError, match="diagnostic-conflict"):
        application.report_finalization_failure(conflicting_request)
    assert (
        report_store.read(),
        ledger.read(),
        coordination_path.read_bytes(),
        runtimes["change-a"].frontier_bytes(),
    ) == report_state


def test_finalizer_attention_allows_only_passive_change_intents(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None
    attempt = acquired.finalization.attempt
    report = application.report_finalization_failure(
        _failure_request(application, attempt_key=attempt.writer.attempt_id)
    )
    assert isinstance(report, FinalizationReport)
    receipt = application.settle_finalizer_invocation(_finalizer_settlement(application, attempt, report))
    assert isinstance(receipt, FinalizerSettlementReceipt)
    attention = coordinator.show("change-a").finalization_attention
    assert attention is not None

    with pytest.raises(CoordinationConflictError, match="mutation cannot overlap active or retained Finalizer custody"):
        application._workspace_manager.prepare_runtime_custody_guard("change-a")

    deferred = application.set_change_intent(
        DeliveryChangeIntent(
            change_id="change-a",
            kind=DeliveryChangeIntentKind.DEFER,
            expected_frontier_digest=hashlib.sha256(runtimes["change-a"].frontier_bytes()).hexdigest(),
            reason="Wait for a user decision.",
        )
    )
    assert deferred.kind is DeliveryChangeIntentKind.DEFER
    assert coordinator.show("change-a").finalization_attention == attention
    assert coordinator.show("change-a").writer.kind == "finalization-attention"

    resumed = application.set_change_intent(
        DeliveryChangeIntent(
            change_id="change-a",
            kind=DeliveryChangeIntentKind.RESUME,
            expected_frontier_digest=deferred.frontier_digest,
        )
    )
    assert resumed.kind is DeliveryChangeIntentKind.RESUME
    assert coordinator.show("change-a").finalization_attention == attention
    assert coordinator.show("change-a").writer.kind == "finalization-attention"

    abandoned = application.set_change_intent(
        DeliveryChangeIntent(
            change_id="change-a",
            kind=DeliveryChangeIntentKind.ABANDON,
            expected_frontier_digest=resumed.frontier_digest,
            reason="Stop this Change.",
        )
    )
    assert abandoned.kind is DeliveryChangeIntentKind.ABANDON
    assert coordinator.show("change-a").finalization_attention == attention
    assert coordinator.show("change-a").writer.kind == "finalization-attention"
    assert (
        state_root / application._finalizer_settlement_receipt_path("change-a", attempt.writer.attempt_id)
    ).is_file()
    assert FinalizationReportStore(state_root, "change-a").read().reports[0] == report


@pytest.mark.parametrize(
    ("damage", "expected_reason"),
    [
        ("dirty-worktree", "workspace-dirty"),
        ("changed-head", "workspace-preflight-failed"),
        ("missing-receipt", "finalization-failed"),
        ("corrupt-receipt", "workspace-inspection-failed"),
        ("missing-report", "report-store-unavailable"),
        ("corrupt-report", "report-store-unavailable"),
        ("retired-report", "finalization-failed"),
    ],
)
def test_finalizer_attention_retry_requires_current_receipt_and_clean_workspace(
    tmp_path: Path, damage: str, expected_reason: str
) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        clock=lambda: now[0],
    )
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None
    attempt = acquired.finalization.attempt
    report = application.report_finalization_failure(
        _failure_request(application, attempt_key=attempt.writer.attempt_id)
    )
    assert isinstance(report, FinalizationReport)
    application.settle_finalizer_invocation(_finalizer_settlement(application, attempt, report))
    attention = coordinator.show("change-a").finalization_attention
    assert attention is not None
    receipt_path = state_root / application._finalizer_settlement_receipt_path("change-a", attempt.writer.attempt_id)
    report_path = state_root / "finalization-reports/change-a/reports" / f"{report.report_id}.json"
    worktree = coordinator.show("change-a").worktree_path

    if damage == "dirty-worktree":
        (worktree / "product.txt").write_text("preserve this local change\n", encoding="utf-8")
    elif damage == "changed-head":
        _commit_local_descendant(coordinator.show("change-a"))
    elif damage == "missing-receipt":
        receipt_path.unlink()
    elif damage == "corrupt-receipt":
        receipt_path.write_bytes(b"{")
    elif damage == "missing-report":
        report_path.unlink()
    elif damage == "corrupt-report":
        report_path.write_bytes(b"{")
    else:
        FinalizationReportStore(state_root, "change-a").retire(attempt.exact_head, attempt.contract_digest)

    now[0] = "2026-08-04T00:00:01Z"
    coordination_before = (state_root / "coordination/changes/change-a.json").read_bytes()
    frontier_before = runtimes["change-a"].frontier_bytes()
    ledger_before = RetryLedger(state_root, "change-a").read()
    receipt_before = receipt_path.read_bytes() if receipt_path.exists() else None
    report_before = report_path.read_bytes() if report_path.exists() else None
    head_before = _git(worktree, "rev-parse", "HEAD")
    dirty_status_before = _git(worktree, "status", "--porcelain=v1", "-z", "--untracked-files=all")

    result = application.acquire_change_action(_continuation_request(application))
    assert result.kind != "acquired", result
    assert result.reason_code == expected_reason
    assert coordinator.show("change-a").finalization_attention == attention
    assert coordinator.show("change-a").writer == attempt.writer.model_copy(update={"kind": "finalization-attention"})
    assert coordinator.show("change-a").finalization_attempt == attempt.model_copy(
        update={"finished_at": attention.finished_at}
    )
    assert (state_root / "coordination/changes/change-a.json").read_bytes() == coordination_before
    assert runtimes["change-a"].frontier_bytes() == frontier_before
    assert RetryLedger(state_root, "change-a").read() == ledger_before
    assert (receipt_path.read_bytes() if receipt_path.exists() else None) == receipt_before
    assert (report_path.read_bytes() if report_path.exists() else None) == report_before
    assert _git(worktree, "rev-parse", "HEAD") == head_before
    assert _git(worktree, "status", "--porcelain=v1", "-z", "--untracked-files=all") == dirty_status_before


def test_settled_dirty_finalizer_attention_stays_blocked_after_workspace_cleanup(tmp_path: Path) -> None:  # noqa: PLR0915 - retains dirty settlement evidence through cleanup.
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        clock=lambda: now[0],
    )
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None
    attempt = acquired.finalization.attempt
    worktree = coordinator.show("change-a").worktree_path
    private_path = worktree / "private-material.txt"
    private_path.write_text("private payload that must remain undisclosed\n", encoding="utf-8")
    failure_basis = application.show_finalization_context("change-a").readiness.basis
    assert failure_basis.workspace_fingerprint is not None
    report = application.report_finalization_failure(
        _failure_request(
            application,
            attempt_key=attempt.writer.attempt_id,
            category="custody-preflight",
            code=FinalizationFailureCode.WORKSPACE_DIRTY,
            checks_state="not-run",
            expected_workspace_fingerprint=failure_basis.workspace_fingerprint,
            paths=(private_path.name,),
        )
    )
    assert isinstance(report, FinalizationReport)
    receipt = application.settle_finalizer_invocation(_finalizer_settlement(application, attempt, report))
    assert isinstance(receipt, FinalizerSettlementReceipt)
    attention = coordinator.show("change-a").finalization_attention
    assert attention is not None
    assert report.request.paths == (private_path.name,)
    assert attention.workspace_paths == receipt.workspace.paths == (private_path.name,)

    now[0] = "2026-08-04T00:00:02Z"
    private_path.write_text("changed private payload\n", encoding="utf-8")
    changed = application.get_change("change-a").readiness
    assert changed.reason_code == "workspace-dirty"
    assert changed.status == "blocked"
    assert not changed.executable
    assert changed.prompt is None

    private_path.unlink()
    cleaned_change = application.get_change("change-a")
    cleaned = cleaned_change.readiness
    assert cleaned.reason_code == "workspace-dirty"
    assert cleaned.status == "blocked"
    assert cleaned.next_actor.value == "agent"
    assert cleaned.checks_state != "passed"
    assert cleaned.last_attempt is not None
    assert cleaned.last_attempt.report == report
    assert not cleaned.executable
    assert cleaned.action is None
    assert cleaned.prompt is None
    assert cleaned.basis.workspace_fingerprint != attention.workspace_fingerprint

    publication = next(
        item for group in application.list_changes().groups for item in group.items if item.item_key == "publication"
    )
    assert publication.next_actor.value == "agent"
    assert publication.action.kind.value == "none"
    assert "/inspect-change change-a" in publication.next_step
    assert "read-only" in publication.next_step
    assert "pause or abandon" in publication.next_step.lower()
    assert "supported repair" in publication.next_step
    assert "private-material.txt" not in publication.next_step
    assert "private payload" not in publication.next_step
    assert "host/worker closure" not in publication.next_step

    index_path = Path(_git(worktree, "rev-parse", "--git-path", "index"))
    if not index_path.is_absolute():
        index_path = worktree / index_path
    protected_state = (
        _file_bytes(state_root),
        runtimes["change-a"].frontier_bytes(),
        index_path.read_bytes(),
        _git(worktree, "rev-parse", "HEAD"),
        _git(worktree, "status", "--porcelain=v1", "-z", "--untracked-files=all"),
        _workspace_content_snapshot(worktree),
    )
    with (
        patch.object(application, "_register_recovery_invocation") as register_invocation,
        patch.object(application, "finalize_change") as finalize_change,
        patch.object(application, "sync_change_with_target") as sync_with_target,
    ):
        blocked = application.acquire_change_action(_continuation_request(application))
    assert blocked.kind != "acquired"
    assert blocked.reason_code == "workspace-dirty"
    register_invocation.assert_not_called()
    finalize_change.assert_not_called()
    sync_with_target.assert_not_called()
    assert (
        _file_bytes(state_root),
        runtimes["change-a"].frontier_bytes(),
        index_path.read_bytes(),
        _git(worktree, "rev-parse", "HEAD"),
        _git(worktree, "status", "--porcelain=v1", "-z", "--untracked-files=all"),
        _workspace_content_snapshot(worktree),
    ) == protected_state


def _inject_settled_attention_drift(
    application: PortfolioApplication,
    state_root: Path,
    worktree: Path,
    receipt_path: Path,
    damage: str,
) -> None:
    if damage == "dirty":
        (worktree / "foreign-private.txt").write_text("private\n", encoding="utf-8")
        return
    if damage == "branch":
        _git(worktree, "commit", "--allow-empty", "-m", "advance Change branch")
        return
    if damage == "index":
        product_file = worktree / "product.txt"
        product_file.write_text("staged-only\n", encoding="utf-8")
        _git(worktree, "add", "product.txt")
        product_file.write_text("baseline\n", encoding="utf-8")
        return
    if damage == "receipt":
        receipt_path.write_bytes(b"{")
        return
    if damage == "receipt-before-registration":
        receipt_path.write_bytes(b"{")
        return
    if damage == "missing-receipt":
        receipt_path.unlink()
        return

    coordination = application._workspace_manager.show("change-a")
    attempt = coordination.finalization_attempt
    attention = coordination.finalization_attention
    assert attempt is not None
    assert attention is not None
    if damage == "contract":
        replacement = coordination.model_copy(
            update={"finalization_attempt": attempt.model_copy(update={"contract_digest": "f" * 64})}
        )
    elif damage == "frontier":
        replacement = coordination.model_copy(
            update={"finalization_attempt": attempt.model_copy(update={"frontier_digest": "f" * 64})}
        )
    elif damage == "report":
        replacement = coordination.model_copy(
            update={"finalization_attention": attention.model_copy(update={"report_id": "f" * 64})}
        )
    else:
        raise AssertionError
    (state_root / "coordination/changes/change-a.json").write_bytes(_canonical(replacement))


@pytest.mark.parametrize(
    ("publisher_configured", "damage"),
    [
        pytest.param(False, None, id="no-publisher"),
        pytest.param(True, None, id="publisher-configured"),
        pytest.param(True, "dirty", id="dirty-private-material"),
        pytest.param(True, "contract", id="stale-contract"),
        pytest.param(True, "frontier", id="stale-frontier"),
        pytest.param(True, "branch", id="stale-branch"),
        pytest.param(True, "index", id="stale-index"),
        pytest.param(True, "report", id="stale-report-identity"),
        pytest.param(True, "receipt", id="stale-settlement-receipt"),
        pytest.param(True, "missing-receipt", id="missing-settlement-receipt"),
        pytest.param(True, "receipt-before-registration", id="receipt-changed-before-registration"),
        pytest.param(True, "receipt-after-reservation", id="receipt-changed-before-effect"),
    ],
)
def test_settled_finalizer_attention_continues_target_drift_through_engine_owner(  # noqa: C901, PLR0915 - lifecycle proof.
    tmp_path: Path, *, publisher_configured: bool, damage: str | None
) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED, "change-b": DeliveryStage.COMPLETED},
        execution_capacity=1,
        clock=lambda: now[0],
    )
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None
    attempt = acquired.finalization.attempt
    report = application.report_finalization_failure(
        _failure_request(application, attempt_key=attempt.writer.attempt_id)
    )
    assert isinstance(report, FinalizationReport)
    receipt = application.settle_finalizer_invocation(_finalizer_settlement(application, attempt, report))
    assert isinstance(receipt, FinalizerSettlementReceipt)
    attention = coordinator.show("change-a").finalization_attention
    assert attention is not None
    finalizer_budget = RetryLedger(state_root, "change-a").episode_for_attempt(attempt.writer.attempt_id)
    assert finalizer_budget is not None

    provider, remote = _attach_engine_publication(application, tmp_path)
    if not publisher_configured:
        application._change_branch_publisher = None
        application._draft_pull_request_publisher = None

    now[0] = "2026-08-04T00:00:01Z"
    repository = application._workspace_manager.repository
    target = _advance_remote_target(tmp_path, remote)
    _git(repository, "fetch", "origin", "main:refs/remotes/origin/main")
    assert application._workspace_manager.observed_target_head() == target
    assert target != attempt.target_head

    coordination_path = state_root / "coordination/changes/change-a.json"
    worktree = coordinator.show("change-a").worktree_path
    index_path = Path(_git(worktree, "rev-parse", "--git-path", "index"))
    if not index_path.is_absolute():
        index_path = worktree / index_path
    receipt_path = state_root / application._finalizer_settlement_receipt_path("change-a", attempt.writer.attempt_id)
    if damage is not None and damage not in {"receipt-after-reservation", "receipt-before-registration"}:
        _inject_settled_attention_drift(application, state_root, worktree, receipt_path, damage)
    report_store = FinalizationReportStore(state_root, "change-a")
    report_before = report_store.read()
    receipt_before = receipt_path.read_bytes() if receipt_path.exists() else None

    def protected_state():
        return (
            coordination_path.read_bytes(),
            runtimes["change-a"].frontier_bytes(),
            RetryLedger(state_root, "change-a").read(),
            report_store.read(),
            receipt_path.read_bytes() if receipt_path.exists() else None,
            _git(worktree, "rev-parse", "HEAD"),
            _git(worktree, "status", "--porcelain=v1", "-z", "--untracked-files=all"),
            index_path.read_bytes(),
            _git(repository, "show-ref"),
        )

    state_before = protected_state()
    if not publisher_configured or damage not in {
        None,
        "receipt-after-reservation",
        "receipt-before-registration",
    }:
        with (
            patch.object(application, "_register_recovery_invocation") as register_invocation,
            patch.object(application, "_identity_factory", wraps=application._identity_factory) as identity_factory,
            patch.object(application, "sync_change_with_target") as sync_with_target,
        ):
            for _ in range(2):
                readiness = application.get_change("change-a").readiness
                assert readiness.status in {"blocked", "unavailable"}
                assert readiness.reason_code != "ready"
                assert readiness.operation is None or readiness.operation.value != "sync-target"
                assert not readiness.executable
                assert readiness.action is None
                if not publisher_configured:
                    assert readiness.reason_code == "settled-attention-target-drift"
                    assert readiness.prompt is not None
                    assert readiness.prompt.startswith("/inspect-change change-a ")
                    assert "Read-only" in readiness.prompt
                    assert "Do not synchronize the target" in readiness.prompt

                blocked = application.acquire_change_action(_continuation_request(application))
                assert blocked.kind != "acquired"
                assert blocked.reason_code != "ready"
                if not publisher_configured:
                    assert blocked.reason_code == "settled-attention-target-drift"
                assert blocked.readiness is not None
                assert blocked.readiness.status in {"blocked", "unavailable"}
                assert not blocked.readiness.executable
                assert blocked.readiness.action is None
                assert protected_state() == state_before

        register_invocation.assert_not_called()
        identity_factory.assert_not_called()
        sync_with_target.assert_not_called()
        assert provider.create_calls == 0
        assert provider.draft_state_calls == 0
        if not publisher_configured:
            assert coordinator.show("change-a").finalization_attention == attention
            assert coordinator.show("change-a").finalization_attempt == attempt.model_copy(
                update={"finished_at": attention.finished_at}
            )
            assert runtimes["change-a"].finalization() is None
        return

    readiness = application.get_change("change-a").readiness
    assert readiness.status == "ready", readiness
    assert readiness.operation.value == "sync-target"
    assert readiness.executable
    assert readiness.action is not None
    assert readiness.action.kind.value == "sync-target"

    sync_request = _continuation_request(application)
    if damage == "receipt-before-registration":
        original_preflight = application._engine_action_preflight
        observed_after_corruption = []

        def corrupt_before_preflight(action, runtime):
            receipt_path.write_bytes(b"{")
            observed_after_corruption.append(protected_state())
            return original_preflight(action, runtime)

        with (
            patch.object(application, "_engine_action_preflight", side_effect=corrupt_before_preflight),
            patch.object(application, "_register_recovery_invocation") as register_invocation,
            patch.object(application, "sync_change_with_target") as sync_with_target,
        ):
            stale = application.acquire_change_action(sync_request)
        assert stale.kind == "stale", stale
        assert stale.engine_result is not None
        assert stale.engine_result.reason_code == "readiness-changed"
        register_invocation.assert_not_called()
        sync_with_target.assert_not_called()
        assert observed_after_corruption == [(*state_before[:4], b"{", *state_before[5:])]
        assert protected_state() == observed_after_corruption[0]
        assert provider.create_calls == 0
        assert provider.draft_state_calls == 0
        return

    with patch.object(
        application, "_register_recovery_invocation", wraps=application._register_recovery_invocation
    ) as register_invocation:
        sync_owner = application.acquire_change_action(sync_request)
        assert sync_owner.kind == "acquired", sync_owner
        assert sync_owner.engine_action is not None
        action = sync_owner.engine_action
        assert action.kind == "sync-target"
        assert action.exact_head == attempt.exact_head
        assert action.target_head == target

        same_owner = application.acquire_change_action(sync_request)
        assert same_owner.kind == "acquired", same_owner
        assert same_owner.engine_action == action
        assert register_invocation.call_count == 1

    reserved = coordinator.show("change-a")
    assert reserved.continuation_action == action
    assert reserved.finalization_attention == attention
    assert reserved.writer == attempt.writer.model_copy(update={"kind": "finalization-attention"})
    assert reserved.finalization_attempt == attempt.model_copy(update={"finished_at": attention.finished_at})
    unrelated = application.acquire_change_action(_continuation_request(application, "change-b"))
    assert unrelated.kind == "waiting"
    assert unrelated.reason_code == "execution-capacity"

    if damage == "receipt-after-reservation":
        receipt_path.write_bytes(b"{")
        workspace_before = (
            _git(worktree, "rev-parse", "HEAD"),
            _git(worktree, "status", "--porcelain=v1", "-z", "--untracked-files=all"),
            index_path.read_bytes(),
            _git(repository, "show-ref"),
        )
        frontier_before = runtimes["change-a"].frontier_bytes()
        start_path = coordinator.continuation_record_path("change-a", action.operation_id).with_name("started.json")
        sync_call = Mock(wraps=application.sync_change_with_target)
        with patch.object(application, "sync_change_with_target", sync_call):
            stale = _execute_engine(application, action)
        assert stale.kind == "stale", stale
        sync_call.assert_not_called()
        assert not start_path.exists()
        assert (
            _git(worktree, "rev-parse", "HEAD"),
            _git(worktree, "status", "--porcelain=v1", "-z", "--untracked-files=all"),
            index_path.read_bytes(),
            _git(repository, "show-ref"),
        ) == workspace_before
        assert runtimes["change-a"].frontier_bytes() == frontier_before
        assert receipt_path.read_bytes() == b"{"
        assert provider.create_calls == 0
        assert provider.draft_state_calls == 0
        return

    sync_call = Mock(wraps=application.sync_change_with_target)
    original_finish = coordinator.finish_continuation_action

    def lose_result_response(*args, **kwargs):
        original_finish(*args, **kwargs)
        raise RuntimeError

    with (
        patch.object(application, "sync_change_with_target", sync_call),
        patch.object(coordinator, "finish_continuation_action", side_effect=lose_result_response),
        pytest.raises(RuntimeError),
    ):
        _execute_engine(application, action)
    sync_call.assert_called_once_with("change-a", target, action.operation_id)

    reopened, reopened_coordinator, _manager = _reopen_portfolio(tmp_path, state_root, runtimes, execution_capacity=1)
    with patch.object(reopened, "sync_change_with_target") as repeated_sync:
        synchronized = _execute_engine(reopened, action)
        repeated_sync.assert_not_called()
    assert synchronized.kind == "completed", synchronized
    assert synchronized.target_sync.target_head == target
    assert synchronized.target_sync.merged_head != attempt.exact_head
    assert synchronized.target_sync.review_required

    settled = reopened_coordinator.show("change-a")
    assert settled.finalization_attention is None
    assert settled.writer is None
    assert settled.finalization_attempt == attempt.model_copy(update={"finished_at": attention.finished_at})
    assert FinalizationReportStore(state_root, "change-a").read() == report_before
    assert receipt_path.read_bytes() == receipt_before
    assert RetryLedger(state_root, "change-a").episode_for_attempt(attempt.writer.attempt_id) == finalizer_budget

    fresh_readiness = reopened.get_change("change-a").readiness
    assert fresh_readiness.status == "ready", fresh_readiness
    assert fresh_readiness.operation.value == "finalize"
    assert fresh_readiness.executable
    fresh = reopened.acquire_change_action(_continuation_request(reopened))
    assert fresh.kind == "acquired", fresh
    assert fresh.finalization is not None
    fresh_attempt = fresh.finalization.attempt
    assert fresh_attempt.writer.attempt_id != attempt.writer.attempt_id
    assert fresh_attempt.exact_head == synchronized.target_sync.merged_head
    assert fresh_attempt.target_head == target
    finalized = reopened.finalize_change(
        "change-a", _finalization_request("change-a", fresh_attempt.exact_head, fresh_attempt.writer.attempt_id)
    )
    assert reopened._runtime("change-a").finalization() == finalized

    newly_available = reopened.acquire_change_action(_continuation_request(reopened, "change-b"))
    assert newly_available.kind == "acquired", newly_available
    assert newly_available.finalization is not None


def _settle_failed_finalizer_attempt(application: PortfolioApplication) -> ChangeFinalizationAttempt:
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.kind == "acquired"
    assert acquired.finalization is not None
    attempt = acquired.finalization.attempt
    report = application.report_finalization_failure(
        _failure_request(application, attempt_key=attempt.writer.attempt_id)
    )
    assert isinstance(report, FinalizationReport)
    receipt = application.settle_finalizer_invocation(_finalizer_settlement(application, attempt, report))
    assert isinstance(receipt, FinalizerSettlementReceipt)
    return attempt


def test_successful_finalizer_syncs_after_target_conflict_abort(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.COMPLETED}, clock=lambda: now[0]
    )
    coordination = coordinator.show("change-a")
    worktree = coordination.worktree_path
    (worktree / "product.txt").write_text("change\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")
    _git(worktree, "commit", "-m", "Change product")
    exact_head = _git(worktree, "rev-parse", "HEAD")
    coordinator.update(coordination.model_copy(update={"last_reviewed_commit": exact_head}))

    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None
    attempt = acquired.finalization.attempt
    assert attempt.exact_head == exact_head
    application.finalize_change(
        "change-a", _finalization_request("change-a", attempt.exact_head, attempt.writer.attempt_id)
    )
    _provider, remote = _attach_engine_publication(application, tmp_path)
    runtime = runtimes["change-a"]
    conflicted_target = _advance_remote_target(tmp_path, remote, product="target\n")
    repository = application._workspace_manager.repository
    _git(repository, "fetch", "origin", "main:refs/remotes/origin/main")
    assert application._workspace_manager.observed_target_head() == conflicted_target
    with pytest.raises(ChangeTargetSyncConflictError) as raised:
        application.sync_change_with_target("change-a", conflicted_target, "sync-conflict")
    assert raised.value.conflict_paths == ("product.txt",)
    disposition = runtime.change_disposition()
    assert disposition is not None
    abort_receipt = application.abort_target_sync_conflict(
        "change-a",
        disposition.disposition_id,
        conflicted_target,
        "sync-conflict",
    )
    assert abort_receipt.restored_head == attempt.exact_head
    assert coordinator.show("change-a").target_sync_conflict is None

    retry_root = tmp_path / "retry-target"
    retry_root.mkdir()
    target = _advance_remote_target(retry_root, remote, product="baseline\n")
    _git(repository, "fetch", "--no-prune", "origin", "main:refs/remotes/origin/main")
    assert application._workspace_manager.observed_target_head() == target
    now[0] = "2026-08-04T00:00:01Z"

    readiness = application.get_change("change-a").readiness
    assert readiness.status == "ready", readiness
    assert readiness.operation is not None
    assert readiness.operation.value == "sync-target"
    owner = application.acquire_change_action(_continuation_request(application))
    assert owner.kind == "acquired", owner
    assert owner.engine_action is not None
    synchronized = _execute_engine(application, owner.engine_action)

    assert synchronized.kind == "completed", synchronized
    assert synchronized.target_sync is not None
    assert synchronized.target_sync.target_head == target
    assert coordinator.show("change-a").writer is None
    assert coordinator.show("change-a").finalization_attention is None


def test_corrupt_settlement_receipt_after_sync_reservation_retains_attention(  # noqa: PLR0915 - stale custody proof.
    tmp_path: Path,
) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.COMPLETED}, clock=lambda: now[0]
    )
    attempt = _settle_failed_finalizer_attempt(application)
    attention = coordinator.show("change-a").finalization_attention
    assert attention is not None
    attention_writer = attempt.writer.model_copy(update={"kind": "finalization-attention"})
    retry_ledger = RetryLedger(state_root, "change-a")
    budget_before = retry_ledger.episode_for_attempt(attempt.writer.attempt_id)
    assert budget_before is not None
    report_store = FinalizationReportStore(state_root, "change-a")
    reports_before = report_store.read()

    _provider, remote = _attach_engine_publication(application, tmp_path)
    target = _advance_remote_target(tmp_path, remote)
    repository = application._workspace_manager.repository
    _git(repository, "fetch", "--no-prune", "origin", "main:refs/remotes/origin/main")
    assert application._workspace_manager.observed_target_head() == target
    now[0] = "2026-08-04T00:00:01Z"
    readiness = application.get_change("change-a").readiness
    assert readiness.status == "ready", readiness
    assert readiness.operation is not None
    assert readiness.operation.value == "sync-target"

    owner = application.acquire_change_action(_continuation_request(application))
    assert owner.kind == "acquired", owner
    assert owner.engine_action is not None
    action = owner.engine_action
    reserved = coordinator.show("change-a")
    assert reserved.continuation_action == action
    assert reserved.writer == attention_writer
    assert reserved.finalization_attention == attention

    receipt_path = state_root / application._finalizer_settlement_receipt_path("change-a", attempt.writer.attempt_id)
    receipt_path.write_bytes(b"{")
    worktree = reserved.worktree_path
    workspace_before = _workspace_mutation_snapshot(worktree)
    frontier_before = runtimes["change-a"].frontier_bytes()
    start_path = coordinator.continuation_record_path("change-a", action.operation_id).with_name("started.json")
    stale = _execute_engine(application, action)

    assert stale.kind == "stale", stale
    assert stale.reason_code == "readiness-changed"
    assert not start_path.exists()
    assert _workspace_mutation_snapshot(worktree) == workspace_before
    assert runtimes["change-a"].frontier_bytes() == frontier_before
    assert report_store.read() == reports_before
    assert receipt_path.read_bytes() == b"{"
    assert retry_ledger.episode_for_attempt(attempt.writer.attempt_id) == budget_before

    after = coordinator.show("change-a")
    assert after.continuation_action is not None
    assert after.continuation_action.operation_id == action.operation_id
    assert after.continuation_action.finished_at is not None
    assert after.writer == attention_writer
    assert after.finalization_attention == attention
    assert after.finalization_attempt == attempt.model_copy(update={"finished_at": attention.finished_at})

    blocked_readiness = application.get_change("change-a").readiness
    assert blocked_readiness.status in {"blocked", "unavailable"}
    assert not blocked_readiness.executable
    assert blocked_readiness.action is None
    assert blocked_readiness.operation is None or blocked_readiness.operation.value != "sync-target"
    blocked = application.acquire_change_action(_continuation_request(application))
    assert blocked.kind != "acquired", blocked
    assert blocked.reason_code != "ready"
    after_retry = coordinator.show("change-a")
    assert after_retry.writer == attention_writer
    assert after_retry.finalization_attention == attention
    assert retry_ledger.episode_for_attempt(attempt.writer.attempt_id) == budget_before


@pytest.mark.parametrize("failed_attempts", [1, 2, 3], ids=["one-failure", "two-failures", "exhausted"])
def test_finalizer_retry_budget_survives_settled_target_sync(  # noqa: PLR0915 - lifecycle proof.
    tmp_path: Path, *, failed_attempts: int
) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        clock=lambda: now[0],
    )
    attempts = []
    for index in range(failed_attempts):
        now[0] = f"2026-08-04T00:00:{index * 10:02d}Z"
        attempts.append(_settle_failed_finalizer_attempt(application))

    retry_ledger = RetryLedger(state_root, "change-a")
    episode = retry_ledger.episode_for_attempt(attempts[-1].writer.attempt_id)
    assert episode is not None
    assert episode.total_attempts == failed_attempts
    for attempt in attempts:
        linked = retry_ledger.episode_for_attempt(attempt.writer.attempt_id)
        assert linked is not None
        assert linked.episode_id == episode.episode_id

    _provider, remote = _attach_engine_publication(application, tmp_path)
    target = _advance_remote_target(tmp_path, remote)
    repository = application._workspace_manager.repository
    _git(repository, "fetch", "origin", "main:refs/remotes/origin/main")
    now[0] = "2026-08-04T00:01:00Z"
    worktree = coordinator.show("change-a").worktree_path
    head_before_sync = _git(worktree, "rev-parse", "HEAD")
    assert target != attempts[-1].target_head

    readiness = application.get_change("change-a").readiness
    if failed_attempts == RetryLedger.transient_attempts:
        assert readiness.status == "blocked"
        assert readiness.reason_code == "retry-exhausted"
        assert readiness.attempts == failed_attempts
        assert readiness.operation is None
        assert not readiness.executable

        blocked = application.acquire_change_action(_continuation_request(application))
        assert blocked.kind != "acquired"
        assert blocked.reason_code == "retry-exhausted"
        assert runtimes["change-a"].target_sync_receipt() is None
        assert _git(worktree, "rev-parse", "HEAD") == head_before_sync
        assert coordinator.show("change-a").finalization_attention is not None
        return

    assert readiness.status == "ready", readiness
    assert readiness.operation is not None
    assert readiness.operation.value == "sync-target"
    sync_owner = application.acquire_change_action(_continuation_request(application))
    assert sync_owner.kind == "acquired", sync_owner
    assert sync_owner.engine_action is not None
    synchronized = _execute_engine(application, sync_owner.engine_action)
    assert synchronized.kind == "completed", synchronized
    assert synchronized.target_sync is not None
    assert synchronized.target_sync.target_head == target
    assert synchronized.target_sync.review_required

    fresh_readiness = application.get_change("change-a").readiness
    assert fresh_readiness.status == "ready", fresh_readiness
    assert fresh_readiness.operation is not None
    assert fresh_readiness.operation.value == "finalize"
    assert fresh_readiness.attempts == failed_attempts
    fresh = application.acquire_change_action(_continuation_request(application))
    assert fresh.kind == "acquired", fresh
    assert fresh.finalization is not None
    fresh_attempt = fresh.finalization.attempt
    assert fresh_attempt.exact_head == synchronized.target_sync.merged_head
    assert fresh_attempt.target_head == target
    continued_episode = retry_ledger.episode_for_attempt(fresh_attempt.writer.attempt_id)
    assert continued_episode is not None
    assert continued_episode.episode_id == episode.episode_id
    assert continued_episode.total_attempts == failed_attempts + 1

    finalized = application.finalize_change(
        "change-a",
        _finalization_request("change-a", fresh_attempt.exact_head, fresh_attempt.writer.attempt_id),
    )
    assert finalized.exact_head == fresh_attempt.exact_head


def test_refunded_settled_finalizer_retry_syncs_target_under_original_budget(
    tmp_path: Path,
) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        clock=lambda: now[0],
    )
    attempt = _settle_failed_finalizer_attempt(application)
    retry_ledger = RetryLedger(state_root, "change-a")
    episode = retry_ledger.episode_for_attempt(attempt.writer.attempt_id)
    assert episode is not None
    assert episode.total_attempts == 1

    now[0] = "2026-08-04T00:00:10Z"
    with patch.object(
        coordinator,
        "_acquire",
        side_effect=CoordinationConflictError("interrupted owner publication"),
    ) as injected:
        refused = application.acquire_change_action(_continuation_request(application))
    injected.assert_called_once()
    assert refused.kind != "acquired", refused
    refunded = retry_ledger.episode_for_attempt(attempt.writer.attempt_id)
    assert refunded is not None
    assert refunded.episode_id == episode.episode_id
    assert refunded.last_status == "paused"
    assert refunded.total_attempts == 1
    assert retry_ledger.pending_attempts() == ()

    _provider, remote = _attach_engine_publication(application, tmp_path)
    target = _advance_remote_target(tmp_path, remote)
    repository = application._workspace_manager.repository
    _git(repository, "fetch", "origin", "main:refs/remotes/origin/main")
    now[0] = "2026-08-04T00:01:00Z"

    readiness = application.get_change("change-a").readiness
    assert readiness.status == "ready", readiness
    assert readiness.operation is not None
    assert readiness.operation.value == "sync-target"
    sync_owner = application.acquire_change_action(_continuation_request(application))
    assert sync_owner.kind == "acquired", sync_owner
    assert sync_owner.engine_action is not None
    synchronized = _execute_engine(application, sync_owner.engine_action)
    assert synchronized.kind == "completed", synchronized
    assert synchronized.target_sync is not None
    assert synchronized.target_sync.target_head == target

    fresh_readiness = application.get_change("change-a").readiness
    assert fresh_readiness.status == "ready", fresh_readiness
    assert fresh_readiness.operation is not None
    assert fresh_readiness.operation.value == "finalize"
    assert fresh_readiness.attempts == 1
    fresh = application.acquire_change_action(_continuation_request(application))
    assert fresh.kind == "acquired", fresh
    assert fresh.finalization is not None
    fresh_attempt = fresh.finalization.attempt
    continued = retry_ledger.episode_for_attempt(fresh_attempt.writer.attempt_id)
    assert continued is not None
    assert continued.episode_id == episode.episode_id
    assert continued.total_attempts == 2
    assert runtimes["change-a"].active_claims() == ()


@pytest.mark.parametrize("mismatched_field", ["contract_digest", "frontier_digest", "target_head"])
def test_manager_rejects_stale_finalizer_attention_before_registration(  # noqa: PLR0915 - custody proof.
    tmp_path: Path, *, mismatched_field: str
) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None
    first_attempt = acquired.finalization.attempt
    report = application.report_finalization_failure(
        _failure_request(application, attempt_key=first_attempt.writer.attempt_id)
    )
    assert isinstance(report, FinalizationReport)
    application.settle_finalizer_invocation(_finalizer_settlement(application, first_attempt, report))

    attention_coordination = coordinator.show("change-a")
    attention = attention_coordination.finalization_attention
    retained_attempt = attention_coordination.finalization_attempt
    assert attention is not None
    assert retained_attempt is not None
    manager = application._workspace_manager
    repository = manager.repository
    if mismatched_field == "target_head":
        _git(repository, "commit", "--allow-empty", "-m", "advance target")
        _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")

    writer = retained_attempt.writer.model_copy(
        update={
            "attempt_id": f"late-{mismatched_field}-attempt",
            "claim_id": f"late-{mismatched_field}-claim",
            "actor_id": "late-host",
            "process_id": "late-session",
            "claimed_at": "2026-08-04T00:00:01Z",
        }
    )
    attempt_updates = {"writer": writer, "finished_at": None}
    attempt_updates[mismatched_field] = (
        manager.observed_target_head()
        if mismatched_field == "target_head"
        else hashlib.sha256(f"stale-{mismatched_field}".encode()).hexdigest()
    )
    retry_attempt = retained_attempt.model_copy(update=attempt_updates)
    promoted_commits = tuple(
        result.completed_commit for binding in runtimes["change-a"].bindings() for result in binding.results
    )
    workspace = manager.capture_finalization_workspace("change-a", promoted_commits)
    assert workspace[4] == "active-custody"
    register_invocation = Mock()
    finalizer = FinalizerAcquisition(
        attempt=retry_attempt,
        expected_attention=attention,
        expected_workspace_fingerprint=workspace[2],
        promoted_commits=promoted_commits,
        before_acquire=register_invocation,
    )

    coordination_path = state_root / "coordination/changes/change-a.json"
    receipt_path = state_root / application._finalizer_settlement_receipt_path(
        "change-a", first_attempt.writer.attempt_id
    )
    report_store = FinalizationReportStore(state_root, "change-a")
    worktree = attention_coordination.worktree_path
    index_path = Path(_git(worktree, "rev-parse", "--git-path", "index"))
    if not index_path.is_absolute():
        index_path = worktree / index_path
    refs_before = _git(repository, "show-ref")
    workspace_before = (
        _git(worktree, "rev-parse", "HEAD"),
        _git(worktree, "status", "--porcelain=v1", "-z", "--untracked-files=all"),
        index_path.read_bytes(),
    )
    coordination_before = coordination_path.read_bytes()
    frontier_before = runtimes["change-a"].frontier_bytes()
    ledger_before = RetryLedger(state_root, "change-a").read()
    report_before = report_store.read()
    receipt_before = receipt_path.read_bytes()

    with pytest.raises(CoordinationConflictError, match="finalizer retry does not match its retained attention"):
        manager.acquire("change-a", writer, finalizer=finalizer)

    register_invocation.assert_not_called()
    assert coordination_path.read_bytes() == coordination_before
    assert runtimes["change-a"].frontier_bytes() == frontier_before
    assert RetryLedger(state_root, "change-a").read() == ledger_before
    assert report_store.read() == report_before
    assert receipt_path.read_bytes() == receipt_before
    assert _git(repository, "show-ref") == refs_before
    assert (
        _git(worktree, "rev-parse", "HEAD"),
        _git(worktree, "status", "--porcelain=v1", "-z", "--untracked-files=all"),
        index_path.read_bytes(),
    ) == workspace_before
    assert coordinator.show("change-a").finalization_attempt == retained_attempt


def test_unsettled_finalizer_failure_keeps_active_writer_after_backoff(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        clock=lambda: now[0],
    )
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None
    attempt = acquired.finalization.attempt
    report = application.report_finalization_failure(
        _failure_request(application, attempt_key=attempt.writer.attempt_id)
    )
    assert isinstance(report, FinalizationReport)
    coordination_before = (state_root / "coordination/changes/change-a.json").read_bytes()
    frontier_before = runtimes["change-a"].frontier_bytes()
    ledger_before = RetryLedger(state_root, "change-a").read()
    assert not application._finalizer_settlement_receipt_path("change-a", attempt.writer.attempt_id).exists()

    now[0] = "2026-08-04T00:00:01Z"
    result = application.acquire_change_action(_continuation_request(application))
    assert result.kind == "unavailable"
    assert result.reason_code == "finalization-failed"
    assert coordinator.show("change-a").writer == attempt.writer
    assert coordinator.show("change-a").finalization_attempt == attempt
    assert coordinator.show("change-a").finalization_attention is None
    assert (state_root / "coordination/changes/change-a.json").read_bytes() == coordination_before
    assert runtimes["change-a"].frontier_bytes() == frontier_before
    assert RetryLedger(state_root, "change-a").read() == ledger_before


def test_finalizer_acquisition_recaptures_workspace_before_attention_cas(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        clock=lambda: now[0],
    )
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None
    attempt = acquired.finalization.attempt
    report = application.report_finalization_failure(
        _failure_request(application, attempt_key=attempt.writer.attempt_id)
    )
    assert isinstance(report, FinalizationReport)
    receipt = application.settle_finalizer_invocation(_finalizer_settlement(application, attempt, report))
    assert isinstance(receipt, FinalizerSettlementReceipt)
    attention = coordinator.show("change-a").finalization_attention
    assert attention is not None
    receipt_path = state_root / application._finalizer_settlement_receipt_path("change-a", attempt.writer.attempt_id)
    receipt_bytes = receipt_path.read_bytes()
    reports_before = FinalizationReportStore(state_root, "change-a").read()
    coordination_before = (state_root / "coordination/changes/change-a.json").read_bytes()
    frontier_before = runtimes["change-a"].frontier_bytes()
    refs_before = _git(application._workspace_manager.repository, "show-ref")
    worktree = coordinator.show("change-a").worktree_path
    dirty_path = worktree / "product.txt"
    now[0] = "2026-08-04T00:00:01Z"
    request = _continuation_request(application)
    manager = application._workspace_manager
    original_acquire = manager.acquire

    def dirty_before_acquire(*args, **kwargs):
        dirty_path.write_text("preserve this new local work\n", encoding="utf-8")
        return original_acquire(*args, **kwargs)

    with (
        patch.object(application, "_register_recovery_invocation") as register_invocation,
        patch.object(manager, "acquire", side_effect=dirty_before_acquire),
    ):
        blocked = application.acquire_change_action(request)

    register_invocation.assert_not_called()
    assert blocked.kind == "unavailable"
    assert blocked.reason_code == "workspace-dirty"
    assert dirty_path.read_text(encoding="utf-8") == "preserve this new local work\n"
    assert coordinator.show("change-a").finalization_attention == attention
    assert coordinator.show("change-a").writer == attempt.writer.model_copy(update={"kind": "finalization-attention"})
    assert coordinator.show("change-a").finalization_attempt.finished_at == attention.finished_at
    assert (state_root / "coordination/changes/change-a.json").read_bytes() == coordination_before
    assert runtimes["change-a"].frontier_bytes() == frontier_before
    assert _git(application._workspace_manager.repository, "show-ref") == refs_before
    assert receipt_path.read_bytes() == receipt_bytes
    assert FinalizationReportStore(state_root, "change-a").read() == reports_before
    assert RetryLedger(state_root, "change-a").read().episodes[0].total_attempts == 1


def test_settled_finalizer_retries_stop_at_three_attempts_without_recovery(tmp_path: Path) -> None:  # noqa: PLR0915 - full retry-budget proof.
    now = ["2026-08-04T00:00:00Z"]
    application, _runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        clock=lambda: now[0],
    )
    attempt_ids: list[str] = []
    expected_key = None

    for index, eligible_at in enumerate(("00:00:00Z", "00:00:01Z", "00:00:03Z")):
        now[0] = f"2026-08-04T{eligible_at}"
        acquired = application.acquire_change_action(_continuation_request(application))
        assert acquired.kind == "acquired", acquired
        assert acquired.finalization is not None
        attempt = acquired.finalization.attempt
        attempt_ids.append(attempt.writer.attempt_id)
        episode_key = RetryLedger(state_root, "change-a").read().episodes[0].key
        expected_key = episode_key if expected_key is None else expected_key
        assert episode_key == expected_key

        report = application.report_finalization_failure(
            _failure_request(application, attempt_key=attempt.writer.attempt_id)
        )
        assert isinstance(report, FinalizationReport)
        reports = FinalizationReportStore(state_root, "change-a").read()
        assert reports.current_report_id == report.report_id
        assert len(reports.reports) == index + 1
        settlement = _finalizer_settlement(application, attempt, report)
        assert isinstance(application.settle_finalizer_invocation(settlement), FinalizerSettlementReceipt)
        episode = RetryLedger(state_root, "change-a").read().episodes[0]
        assert episode.key == expected_key
        assert episode.total_attempts == index + 1
        assert episode.reset_count == 0

        if index == 1:
            now[0] = "2026-08-04T00:00:02Z"
            before_backoff = application.acquire_change_action(_continuation_request(application))
            assert before_backoff.kind == "waiting"
            assert before_backoff.reason_code == "retry-backoff"
            assert RetryLedger(state_root, "change-a").read().episodes[0].total_attempts == 2

    episode = RetryLedger(state_root, "change-a").read().episodes[0]
    assert len(set(attempt_ids)) == 3
    assert set(attempt_ids) <= set(episode.attempt_ids)
    assert {alias.value for alias in episode.aliases if alias.alias_kind == "operation"} >= set(attempt_ids)
    assert episode.total_attempts == 3
    assert episode.reset_count == 0
    assert len(FinalizationReportStore(state_root, "change-a").read().reports) == 3
    assert all(
        (state_root / application._finalizer_settlement_receipt_path("change-a", attempt_id)).is_file()
        for attempt_id in attempt_ids
    )

    blocked = application.acquire_change_action(_continuation_request(application))
    assert blocked.kind == "unsupported"
    assert blocked.reason_code == "retry-exhausted"
    assert blocked.readiness is not None
    assert blocked.readiness.attempts == 3
    assert not blocked.readiness.executable
    assert blocked.readiness.action is None
    assert blocked.readiness.next_actor.value == "agent"
    assert blocked.readiness.prompt is not None
    assert blocked.readiness.prompt.startswith("/inspect-change change-a Diagnose")
    assert "read-only" in blocked.readiness.prompt
    assert "do not clear the block, retry, dispatch, or reset the budget" in blocked.readiness.prompt
    assert RetryLedger(state_root, "change-a").read().episodes[0].total_attempts == 3
    assert coordinator.show("change-a").finalization_attention is not None
    assert coordinator.show("change-a").finalization_attempt.finished_at is not None


@pytest.mark.parametrize(
    ("category", "code"),
    [
        ("maintained-check", FinalizationFailureCode.MAINTAINED_CHECK_FAILED),
        ("independent-review", FinalizationFailureCode.INDEPENDENT_REVIEW_FAILED),
    ],
)
def test_settled_finalizer_failure_retries_after_persisted_backoff(  # noqa: PLR0915 - full settled-retry lifecycle proof.
    tmp_path: Path, category: str, code: FinalizationFailureCode
) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        clock=lambda: now[0],
    )
    first = application.acquire_change_action(_continuation_request(application))
    assert first.finalization is not None
    first_attempt = first.finalization.attempt
    report = application.report_finalization_failure(
        _failure_request(
            application,
            attempt_key=first_attempt.writer.attempt_id,
            category=category,
            code=code,
        )
    )
    assert isinstance(report, FinalizationReport)
    settlement = _finalizer_settlement(application, first_attempt, report)
    receipt = application.settle_finalizer_invocation(settlement)
    assert isinstance(receipt, FinalizerSettlementReceipt)
    with pytest.raises(DeliveryActionBusyError, match="failed finalization attempt cannot submit success"):
        application.finalize_change(
            "change-a", _finalization_request("change-a", first_attempt.exact_head, first_attempt.writer.attempt_id)
        )

    ledger = RetryLedger(state_root, "change-a")
    settled_ledger = ledger.read()
    receipt_path = state_root / application._finalizer_settlement_receipt_path(
        "change-a", first_attempt.writer.attempt_id
    )
    receipt_bytes = receipt_path.read_bytes()
    report_store = FinalizationReportStore(state_root, "change-a")
    reports = report_store.read()
    assert application.settle_finalizer_invocation(settlement) == receipt

    application, coordinator, _manager = _reopen_portfolio(
        tmp_path,
        state_root,
        runtimes,
        clock=lambda: now[0],
    )
    coordination_path = state_root / "coordination/changes/change-a.json"
    frontier_path = state_root / "changes/change-a/frontier.json"
    worktree = coordinator.show("change-a").worktree_path
    index_path = Path(_git(worktree, "rev-parse", "--git-path", "index"))
    if not index_path.is_absolute():
        index_path = worktree / index_path
    workspace_state = (
        _git(worktree, "rev-parse", "HEAD"),
        _git(worktree, "status", "--porcelain=v1", "-z", "--untracked-files=all"),
        index_path.read_bytes(),
        _git(application._workspace_manager.repository, "show-ref"),
        tuple(
            (path.relative_to(worktree).as_posix(), path.read_bytes())
            for path in sorted(worktree.rglob("*"))
            if path.is_file() and path.name != ".git"
        ),
    )

    before_backoff = application.acquire_change_action(_continuation_request(application))
    assert before_backoff.kind == "waiting"
    assert before_backoff.reason_code == "retry-backoff"
    assert ledger.read() == settled_ledger

    now[0] = "2026-08-04T00:00:01Z"
    retry_request = _continuation_request(application, host_id="retry-host", session_id="retry-session")
    retry = application.acquire_change_action(retry_request)
    assert retry.kind == "acquired", retry
    assert retry.finalization is not None
    second_attempt = retry.finalization.attempt
    assert second_attempt.writer.attempt_id != first_attempt.writer.attempt_id
    assert second_attempt.writer.claim_id != first_attempt.writer.claim_id
    assert second_attempt.exact_head == first_attempt.exact_head
    assert coordinator.show("change-a").writer == second_attempt.writer
    assert coordinator.show("change-a").finalization_attempt == second_attempt
    assert coordinator.show("change-a").finalization_attention is None
    assert receipt_path.read_bytes() == receipt_bytes
    assert report_store.read() == reports
    duplicate_before = (
        (state_root / "coordination/changes/change-a.json").read_bytes(),
        runtimes["change-a"].frontier_bytes(),
        ledger.read(),
    )
    duplicate = application.acquire_change_action(retry_request)
    assert duplicate.kind == "busy"
    assert (
        (state_root / "coordination/changes/change-a.json").read_bytes(),
        runtimes["change-a"].frontier_bytes(),
        ledger.read(),
    ) == duplicate_before
    with pytest.raises(DeliveryActionBusyError, match="failed finalization attempt cannot submit success"):
        application.finalize_change(
            "change-a", _finalization_request("change-a", first_attempt.exact_head, first_attempt.writer.attempt_id)
        )
    assert (
        (state_root / "coordination/changes/change-a.json").read_bytes(),
        runtimes["change-a"].frontier_bytes(),
        ledger.read(),
    ) == duplicate_before
    assert (
        _git(worktree, "rev-parse", "HEAD"),
        _git(worktree, "status", "--porcelain=v1", "-z", "--untracked-files=all"),
        index_path.read_bytes(),
        _git(application._workspace_manager.repository, "show-ref"),
        tuple(
            (path.relative_to(worktree).as_posix(), path.read_bytes())
            for path in sorted(worktree.rglob("*"))
            if path.is_file() and path.name != ".git"
        ),
    ) == workspace_state
    episodes = ledger.read().episodes
    assert len(episodes) == 1
    assert episodes[0].key == settled_ledger.episodes[0].key
    assert episodes[0].total_attempts == 2
    assert {first_attempt.writer.attempt_id, second_attempt.writer.attempt_id} <= set(episodes[0].attempt_ids)
    assert {alias.value for alias in episodes[0].aliases if alias.alias_kind == "operation"} >= {
        first_attempt.writer.attempt_id,
        second_attempt.writer.attempt_id,
    }

    retained_before_replay = (
        coordination_path.read_bytes(),
        frontier_path.read_bytes(),
        ledger.read(),
        report_store.read(),
        receipt_path.read_bytes(),
    )
    assert application.settle_finalizer_invocation(settlement) == receipt
    assert (
        coordination_path.read_bytes(),
        frontier_path.read_bytes(),
        ledger.read(),
        report_store.read(),
        receipt_path.read_bytes(),
    ) == retained_before_replay

    finalization = application.finalize_change(
        "change-a", _finalization_request("change-a", second_attempt.exact_head, second_attempt.writer.attempt_id)
    )
    assert finalization.operation_id == second_attempt.writer.attempt_id
    assert coordinator.show("change-a").writer is None
    assert receipt_path.read_bytes() == receipt_bytes
    assert any(item.report_id == report.report_id for item in report_store.read().reports)


def test_finalizer_settlement_rejects_mismatched_authority_without_effects(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED, "change-b": DeliveryStage.PLANNING},
        execution_capacity=1,
    )
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None
    attempt = acquired.finalization.attempt
    report = application.report_finalization_failure(
        _failure_request(application, attempt_key=attempt.writer.attempt_id)
    )
    assert isinstance(report, FinalizationReport)
    valid = _finalizer_settlement(application, attempt, report)
    other_report_id = "0" * 64 if report.report_id != "0" * 64 else "f" * 64
    other_head = "0" * 40 if attempt.exact_head != "0" * 40 else "1" * 40
    other_reviewed_base = "0" * 40 if valid.expected_reviewed_base != "0" * 40 else "1" * 40
    invalid = (
        valid.model_copy(update={"report_id": other_report_id}),
        valid.model_copy(update={"session_id": "other-session"}),
        valid.model_copy(update={"host_id": "other-host"}),
        valid.model_copy(update={"claim_id": "other-claim"}),
        valid.model_copy(update={"expected_head": other_head}),
        valid.model_copy(update={"expected_reviewed_base": other_reviewed_base}),
        valid.model_copy(update={"outcome": "review-failed"}),
        valid.model_copy(update={"disposition": "cancelled"}),
        valid.model_copy(update={"change_id": "change-b"}),
    )
    worktrees = tuple(
        (
            change_id,
            tuple(
                (path.relative_to(coordinator.show(change_id).worktree_path).as_posix(), path.read_bytes())
                for path in sorted(coordinator.show(change_id).worktree_path.rglob("*"))
                if path.is_file() and path.name != ".git"
            ),
        )
        for change_id in ("change-a", "change-b")
    )
    before = (
        tuple(
            (change_id, (state_root / f"coordination/changes/{change_id}.json").read_bytes())
            for change_id in ("change-a", "change-b")
        ),
        tuple(
            (change_id, runtimes[change_id].frontier_bytes(), RetryLedger(state_root, change_id).read())
            for change_id in ("change-a", "change-b")
        ),
        _git(application._workspace_manager.repository, "show-ref"),
        worktrees,
        FinalizationReportStore(state_root, "change-a").read(),
    )
    for candidate in invalid:
        with pytest.raises(DeliveryActionSelectionConflictError):
            application.settle_finalizer_invocation(candidate)
        after_worktrees = tuple(
            (
                change_id,
                tuple(
                    (path.relative_to(coordinator.show(change_id).worktree_path).as_posix(), path.read_bytes())
                    for path in sorted(coordinator.show(change_id).worktree_path.rglob("*"))
                    if path.is_file() and path.name != ".git"
                ),
            )
            for change_id in ("change-a", "change-b")
        )
        after = (
            tuple(
                (change_id, (state_root / f"coordination/changes/{change_id}.json").read_bytes())
                for change_id in ("change-a", "change-b")
            ),
            tuple(
                (change_id, runtimes[change_id].frontier_bytes(), RetryLedger(state_root, change_id).read())
                for change_id in ("change-a", "change-b")
            ),
            _git(application._workspace_manager.repository, "show-ref"),
            after_worktrees,
            FinalizationReportStore(state_root, "change-a").read(),
        )
        assert after == before
    assert not application._finalizer_settlement_receipt_path("change-a", attempt.writer.attempt_id).exists()
    waiting = application.acquire_change_action(_continuation_request(application, "change-b"))
    assert waiting.kind == "waiting"
    assert waiting.reason_code == "execution-capacity"


def test_finalizer_settlement_uses_report_time_when_initial_failure_charge_fails(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, _runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        clock=lambda: now[0],
    )
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None
    attempt = acquired.finalization.attempt
    request = _failure_request(application, attempt_key=attempt.writer.attempt_id)
    with patch.object(RetryLedger, "record_failure", side_effect=OSError("injected accounting failure")):
        report = application.report_finalization_failure(request)
    assert isinstance(report, FinalizationReport)

    now[0] = "2026-08-04T00:01:00Z"
    settlement = _finalizer_settlement(application, attempt, report)
    assert isinstance(application.settle_finalizer_invocation(settlement), FinalizerSettlementReceipt)
    observed_at = report.observed_at.isoformat().replace("+00:00", "Z")
    owner_result_path = state_root / "changes/change-a/retry-ledger/owner-results" / f"{attempt.writer.attempt_id}.json"
    assert json.loads(owner_result_path.read_text())["observed_at"] == observed_at

    ledger = RetryLedger(state_root, "change-a")
    ledger.reconcile_owner_results()
    episode = ledger.episode_for_attempt(attempt.writer.attempt_id)
    assert episode is not None
    assert episode.last_failure_at == observed_at
    assert episode.next_eligible_at == (report.observed_at + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    assert episode.total_attempts == 1
    assert episode.reset_count == 0
    assert len(episode.outcome_ids) == 1


def test_corrupt_finalizer_settlement_receipt_keeps_capacity_occupied(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED, "change-b": DeliveryStage.PLANNING},
        execution_capacity=1,
    )
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None
    attempt = acquired.finalization.attempt
    report = application.report_finalization_failure(
        _failure_request(application, attempt_key=attempt.writer.attempt_id)
    )
    assert isinstance(report, FinalizationReport)
    settlement = _finalizer_settlement(application, attempt, report)
    receipt_path = state_root / application._finalizer_settlement_receipt_path("change-a", attempt.writer.attempt_id)
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_bytes(b"{")
    coordination_path = state_root / "coordination/changes/change-a.json"
    before = (
        coordination_path.read_bytes(),
        runtimes["change-a"].frontier_bytes(),
        RetryLedger(state_root, "change-a").read(),
    )

    with pytest.raises(ValidationError):
        application.settle_finalizer_invocation(settlement)

    assert (
        coordination_path.read_bytes(),
        runtimes["change-a"].frontier_bytes(),
        RetryLedger(state_root, "change-a").read(),
    ) == before
    assert coordinator.show("change-a").writer == attempt.writer
    waiting = application.acquire_change_action(_continuation_request(application, "change-b"))
    assert waiting.kind == "waiting"
    assert waiting.reason_code == "execution-capacity"


def test_finalizer_settlement_rejects_retired_report_without_releasing_custody(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None
    attempt = acquired.finalization.attempt
    report = application.report_finalization_failure(
        _failure_request(application, attempt_key=attempt.writer.attempt_id)
    )
    assert isinstance(report, FinalizationReport)
    FinalizationReportStore(state_root, "change-a").retire(attempt.exact_head, attempt.contract_digest)
    settlement = _finalizer_settlement(application, attempt, report)
    before = (
        (state_root / "coordination/changes/change-a.json").read_bytes(),
        runtimes["change-a"].frontier_bytes(),
        RetryLedger(state_root, "change-a").read(),
        _git(application._workspace_manager.repository, "show-ref"),
    )
    with pytest.raises(DeliveryActionSelectionConflictError):
        application.settle_finalizer_invocation(settlement)
    assert (
        (state_root / "coordination/changes/change-a.json").read_bytes(),
        runtimes["change-a"].frontier_bytes(),
        RetryLedger(state_root, "change-a").read(),
        _git(application._workspace_manager.repository, "show-ref"),
    ) == before
    assert coordinator.show("change-a").writer == attempt.writer
    assert coordinator.show("change-a").finalization_attempt.finished_at is None


def test_finalizer_settlement_replays_after_interrupted_atomic_publication(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        clock=lambda: "2026-08-04T00:00:00Z",
    )
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None
    attempt = acquired.finalization.attempt
    report = application.report_finalization_failure(
        _failure_request(application, attempt_key=attempt.writer.attempt_id)
    )
    assert isinstance(report, FinalizationReport)
    settlement = _finalizer_settlement(application, attempt, report)
    original_commit = RuntimeTransaction.commit
    injected = []

    def interrupted(transaction: RuntimeTransaction) -> None:
        def fail(stage: str) -> None:
            if stage == "after-first-publication":
                injected.append(stage)
                message = "injected Finalizer settlement interruption"
                raise RuntimeError(message)

        owned = transaction._transaction_id.startswith("finalizer-settlement-")
        original_commit(transaction, failure=fail if owned else None)

    with (
        patch.object(RuntimeTransaction, "commit", interrupted),
        pytest.raises(RuntimeError, match="injected Finalizer settlement interruption"),
    ):
        application.settle_finalizer_invocation(settlement)
    assert injected == ["after-first-publication"]
    assert coordinator.show("change-a").writer == attempt.writer
    assert runtimes["change-a"].finalization() is None

    receipt = application.settle_finalizer_invocation(settlement)
    assert isinstance(receipt, FinalizerSettlementReceipt)
    assert coordinator.show("change-a").finalization_attention.receipt_id == receipt.receipt_id
    assert (state_root / "changes/change-a/retry-ledger/owner-results" / f"{attempt.writer.attempt_id}.json").is_file()
    assert application.settle_finalizer_invocation(settlement) == receipt


def test_finalizer_settlement_is_noop_after_exact_successful_finalization(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None
    attempt = acquired.finalization.attempt
    reviewed_base = coordinator.show("change-a").last_reviewed_commit
    finalization = application.finalize_change(
        "change-a",
        _finalization_request("change-a", attempt.exact_head, attempt.writer.attempt_id),
    )
    before = (
        (state_root / "coordination/changes/change-a.json").read_bytes(),
        runtimes["change-a"].frontier_bytes(),
        _git(application._workspace_manager.repository, "show-ref"),
    )
    settlement = FinalizerSettlement(
        change_id="change-a",
        attempt_id=attempt.writer.attempt_id,
        claim_id=attempt.writer.claim_id,
        expected_head=attempt.exact_head,
        expected_reviewed_base=reviewed_base,
        report_id="0" * 64,
        disposition="normal-return",
        outcome="proof-failed",
        host_id=attempt.writer.actor_id,
        session_id=attempt.writer.process_id,
    )

    assert application.settle_finalizer_invocation(settlement) == finalization
    assert (
        (state_root / "coordination/changes/change-a.json").read_bytes(),
        runtimes["change-a"].frontier_bytes(),
        _git(application._workspace_manager.repository, "show-ref"),
    ) == before
    assert coordinator.show("change-a").writer is None
    assert coordinator.show("change-a").finalization_attention is None
    assert not application._finalizer_settlement_receipt_path("change-a", attempt.writer.attempt_id).exists()


def test_application_retains_failure_without_lifecycle_effect_and_prioritizes_success(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    request = _failure_request(application)
    before = runtimes["change-a"].frontier_bytes()
    custody = coordinator.show("change-a")
    report = application.report_finalization_failure(request)
    assert runtimes["change-a"].frontier_bytes() == before
    assert coordinator.show("change-a") == custody
    view = application.get_change("change-a")
    assert view.readiness.last_attempt.report == report
    assert view.readiness.last_attempt.applicability == "current"
    assert view.readiness.checks_state == "failed"
    assert view.readiness.action.label == "Retry verification"
    assert view.readiness.executable
    application.finalize_change("change-a", _finalization_request("change-a", custody.last_reviewed_commit))
    successful = application.show_finalization_context("change-a")
    assert successful.readiness.checks_state == "passed"
    assert successful.readiness.last_attempt.applicability == "historical"
    assert (state_root / "finalization-reports/change-a/reports" / f"{report.report_id}.json").is_file()
    assert application.report_finalization_failure(request) == report


def test_application_restart_marks_changed_candidate_report_historical_and_replays(tmp_path: Path) -> None:
    application, _runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    request = _failure_request(application)
    report = application.report_finalization_failure(request)
    restarted = PortfolioApplication(
        {},
        PortfolioApplicationDependencies(
            target_root=state_root,
            package_store=application._package_store,
            authority_registry=application._authority_registry,
            coordinator=coordinator,
            workspace_manager=application._workspace_manager,
        ),
        PortfolioApplicationConfig(
            package_root=application._package_root, execution_capacity=3, role_policies=_policies()
        ),
    )
    assert restarted.get_change("change-a").readiness.last_attempt.report == report
    _commit_local_descendant(coordinator.show("change-a"))
    decision = restarted.get_change("change-a").readiness
    assert decision.last_attempt.applicability == "historical"
    assert decision.executable
    assert restarted.report_finalization_failure(request) == report
    with pytest.raises(FinalizationReportError, match="diagnostic-conflict"):
        restarted.report_finalization_failure(
            request.model_copy(update={"attempt_key": "new-key", "expected_diagnostic_sequence": 1})
        )


def test_success_survives_report_retirement_failure_and_replay_reconciles(tmp_path: Path) -> None:
    application, _runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    report = application.report_finalization_failure(_failure_request(application))
    pointer = state_root / "finalization-reports/change-a/current.json"
    before = pointer.read_bytes()
    request = _finalization_request("change-a", coordinator.show("change-a").last_reviewed_commit)
    with patch(
        "owlbear_delivery.application_lifecycle.FinalizationReportStore.retire",
        side_effect=FinalizationReportError("report-store-unavailable"),
    ):
        receipt = application.finalize_change("change-a", request)
    assert application.get_change("change-a").readiness.checks_state == "passed"
    assert pointer.read_bytes() == before
    assert application.finalize_change("change-a", request) == receipt
    assert json.loads(pointer.read_bytes())["report_id"] is None
    assert (pointer.parent / "reports" / f"{report.report_id}.json").is_file()


def test_custody_reporting_rejects_stale_fingerprint_and_unobserved_paths(tmp_path: Path) -> None:
    application, _runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    path = coordinator.show("change-a").worktree_path / "product.txt"
    path.write_text("dirty\n")
    basis = application.show_finalization_context("change-a").readiness.basis
    request = _failure_request(
        application,
        category="custody-preflight",
        code=FinalizationFailureCode.WORKSPACE_DIRTY,
        checks_state="not-run",
        expected_workspace_fingerprint=basis.workspace_fingerprint,
        paths=("absent.txt",),
    )
    with pytest.raises(FinalizationReportError, match="diagnostic-conflict"):
        application.report_finalization_failure(request)
    path.write_text("different dirt\n")
    with pytest.raises(FinalizationReportError, match="diagnostic-conflict"):
        application.report_finalization_failure(request.model_copy(update={"paths": ("product.txt",)}))
    assert not (state_root / "finalization-reports/change-a/current.json").exists()
    assert path.read_text() == "different dirt\n"


@pytest.mark.parametrize("damage", ["missing", "malformed", "frontier", "unknown"])
def test_coordination_damage_isolates_reads_and_preserves_unknown_capacity(tmp_path: Path, damage: str) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING}, execution_capacity=1
    )
    request = _continuation_request(application, "change-b")
    before = {change: runtime.frontier_bytes() for change, runtime in runtimes.items()}
    root = state_root / "coordination/changes"
    if damage == "missing":
        (root / "change-a.json").unlink()
    elif damage == "malformed":
        (root / "change-a.json").write_bytes(b"{")
    elif damage == "frontier":
        (state_root / "changes/change-a/frontier.json").write_bytes(b"{")
    elif damage == "unknown":
        (root / "unknown.json").write_bytes(b"{")
    assert application.get_change("change-b").kind == "available"
    assert len(application.list_changes().groups) == (1 if damage == "frontier" else 2)
    if damage in {"missing", "malformed"}:
        damaged = application.get_change("change-a")
        assert damaged.kind == "unavailable"
        assert damaged.readiness.reason_code == "coordination-unavailable"
        assert damaged.coordination_status == ("missing" if damage == "missing" else "unreadable")
        with pytest.raises(DeliveryRuntimeReconciliationError):
            application.set_change_intent(
                DeliveryChangeIntent(
                    change_id="change-a",
                    kind=DeliveryChangeIntentKind.DEFER,
                    expected_frontier_digest=hashlib.sha256(before["change-a"]).hexdigest(),
                    reason="pause",
                )
            )
    stopped = application.acquire_change_action(request)
    assert stopped.kind == "unavailable"
    assert stopped.reason_code == "execution-occupancy-unavailable"
    assert stopped.readiness.reason_code == "execution-occupancy-unavailable"
    assert stopped.failure.code == DeliveryRuntimeReconciliationError.code
    assert not stopped.readiness.executable
    batch = application.acquire_frontier_work()
    assert not batch.launch_packages
    assert batch.failures[0].code == DeliveryRuntimeReconciliationError.code
    if damage == "frontier":
        assert (state_root / "changes/change-a/frontier.json").read_bytes() == b"{"
    else:
        assert runtimes["change-a"].frontier_bytes() == before["change-a"]
    assert runtimes["change-b"].frontier_bytes() == before["change-b"]


@pytest.mark.parametrize("active", [False, True])
def test_orphan_coordination_charges_only_retained_writers(tmp_path: Path, *, active: bool) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, execution_capacity=1
    )
    orphan = coordinator.show("change-a").model_copy(update={"change_id": "orphan-change"})
    coordinator.register(orphan)
    if active:
        coordinator.acquire(
            "orphan-change",
            ChangeWriter(
                attempt_id="unknown-attempt",
                claim_id="unknown-claim",
                actor_id="unknown-owner",
                process_id="unknown-process",
                claimed_at="2026-08-02T00:01:00Z",
                job_id=1,
                kind="build",
            ),
        )
    custody = coordinator.show("orphan-change")
    before = runtimes["change-a"].frontier_bytes()
    result = application.acquire_change_action(_continuation_request(application))
    assert result.kind == ("waiting" if active else "acquired")
    if active:
        assert result.reason_code == "execution-capacity"
        assert runtimes["change-a"].frontier_bytes() == before
    assert coordinator.show("orphan-change") == custody


def test_known_corrupt_change_remains_visible_without_relaxing_parser(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.COMPLETED, "change-b": DeliveryStage.DESIGN}
    )
    path = state_root / "changes/change-a/frontier.json"
    path.write_bytes(b"{invalid canonical bytes")
    view = application.get_change("change-a")
    assert view.kind == "unavailable"
    assert view.readiness.basis.frontier_digest is None
    assert view.readiness.action is None
    assert view.readiness.progress is not None
    assert (view.readiness.progress.situation, view.readiness.progress.waiting_on) == ("needs-attention", "you")
    assert application.show_work_item_view("change-a", "publication") == view
    listing = application.list_changes()
    assert listing.unavailable_changes == (view,)
    assert listing.groups[0].change_id == "change-b"
    with pytest.raises(json.JSONDecodeError):
        parse_delivery_frontier(path.read_bytes())
    with pytest.raises(PortfolioApplicationError):
        application.get_change("unknown-change")
    assert path.read_bytes() == b"{invalid canonical bytes"


@pytest.mark.parametrize(
    ("stage", "operation"),
    [
        (DeliveryStage.PLANNING, "start-orchestration"),
        (DeliveryStage.IMPLEMENTATION, "start-orchestration"),
    ],
)
def test_nonfinalization_ready_actions_skip_workspace_inspection(tmp_path: Path, stage, operation) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(tmp_path, {"change-a": stage})
    with patch.object(
        application._workspace_manager,
        "observed_change_head",
        side_effect=AssertionError("irrelevant workspace inspection"),
    ):
        decision = application.get_change("change-a").readiness
    assert decision.status == "ready"
    assert decision.operation.value == operation
    assert decision.executable
    assert decision.basis.workspace_fingerprint is None


def test_design_attention_is_human_not_executable_by_continuation(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.DESIGN})

    view = application.get_change("change-a")
    readiness = view.readiness
    assert readiness.status == "blocked"
    assert readiness.operation is None
    assert not readiness.executable
    assert readiness.action is None
    assert readiness.next_actor.value == "you"
    assert readiness.reason_code == "design-attention"
    assert readiness.prompt is not None
    assert readiness.prompt.startswith("/design change-a")
    assert "does not approve or admit" in readiness.prompt
    assert view.detail.card.action.kind.value == "resume-design"
    assert view.detail.card.action.command == "/design change-a"

    result = application.acquire_change_action(_continuation_request(application, "change-a"))

    assert result.kind == "human"
    assert result.reason_code == "design-attention"
    assert result.readiness.prompt == readiness.prompt
    assert result.launch is None
    assert result.engine_action is None
    assert runtimes["change-a"].active_claims() == ()
    assert runtimes["change-a"].claimable_outcome_ids() == ()


def test_active_lifecycle_guard_survives_readiness_capture(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    acquired = application.acquire_frontier_work()
    assert len(acquired.launch_packages) == 1
    active = application.get_change("change-a").readiness
    assert active.status == "running"
    assert not active.executable
    assert active.reason_code == "active-custody"


def test_finalization_context_uses_managed_change_head(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    change_head = coordinator.show("change-a").last_reviewed_commit

    context = application.show_finalization_context("change-a")

    assert context.change_head == change_head
    assert context.reviewed_change_head == change_head
    assert context.publication_phase.value == "ready-for-finalization"


def test_finalization_context_reports_existing_exact_finalization_head(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    request = _finalization_request("change-a", exact_head)
    receipt = application.finalize_change("change-a", request)

    context = application.show_finalization_context("change-a")

    assert context.finalization_id == receipt.finalization_id
    assert context.finalized_head == exact_head
    assert context.change_head == exact_head


def test_finalization_rejects_change_head_drift_before_persistence(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = application._workspace_manager.show("change-a")
    exact_head = coordination.last_reviewed_commit
    request = _finalization_request("change-a", exact_head)
    (coordination.worktree_path / "unreviewed.txt").write_text("unreviewed\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "unreviewed.txt")
    _git(coordination.worktree_path, "commit", "-m", "unreviewed Change head")

    with pytest.raises(PortfolioApplicationError, match="finalization"):
        application.finalize_change("change-a", request)

    assert runtimes["change-a"].finalization() is None


def test_finalization_rejects_exact_head_mismatch(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = runtimes["change-a"].bindings()[0].results[0].completed_commit
    request = _finalization_request("change-a", exact_head).model_copy(
        update={"exact_head": "f" * 40},
    )

    with pytest.raises(PortfolioApplicationError, match="current Change head"):
        application.finalize_change("change-a", request)

    assert runtimes["change-a"].finalization() is None


def _fail_once_then_set_draft_state(pull_requests: list[PublicationPullRequest]):
    failures_remaining = 1

    def transition(request):
        nonlocal failures_remaining
        if failures_remaining:
            failures_remaining -= 1
            raise PublicationProviderError(
                PublicationProviderFailureCode.UNAVAILABLE,
                "set_pull_request_draft_state",
                "provider unavailable",
                retry_safe=True,
            )
        pull_requests[0] = pull_requests[0].model_copy(update={"draft": request.draft})
        return pull_requests[0]

    return transition


def test_finalization_invalidates_provider_pull_request_head_drift(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    receipt = application.finalize_change("change-a", _finalization_request("change-a", exact_head))
    provider = Mock()
    provider.read_repository.return_value = PublicationRepository(
        repository="example/project",
        default_branch="main",
    )
    provider.find_pull_request.return_value = None
    pull_requests: list[PublicationPullRequest] = []

    def create_pull_request(request):
        pull_request = PublicationPullRequest(
            repository=request.repository,
            number=7,
            node_id="PR_node_7",
            head_branch=request.head_branch,
            head_sha=request.head_sha,
            base_branch=request.base_branch,
            title=request.title,
            body=request.body,
            draft=True,
            state="open",
            merged=False,
        )
        pull_requests.append(pull_request)
        return pull_request

    provider.create_draft_pull_request.side_effect = create_pull_request
    publisher = DraftPullRequestPublisher(
        provider,
        repository="example/project",
        target_branch="main",
        state_root=tmp_path / "pull-requests",
    )
    publisher.publish(
        CreateOrReconcileDraftPullRequest(
            change_id="change-a",
            operation_id="create-change-a",
            published_head=exact_head,
            title="Change A",
            generated_summary="Finalized Change A.",
        )
    )
    provider.read_pull_request.side_effect = lambda _repository, _number: pull_requests[0]
    provider.observe_checks.return_value = PublicationCheckSnapshot(
        repository="example/project",
        number=7,
        head_sha=exact_head,
        checks=(),
    )

    def set_draft_state(request):
        pull_requests[0] = pull_requests[0].model_copy(update={"draft": request.draft})
        return pull_requests[0]

    provider.set_pull_request_draft_state.side_effect = set_draft_state
    application._draft_pull_request_publisher = publisher
    checkpoint = runtimes["change-a"].checkpoint_publication_state()
    assert checkpoint.pending_checkpoint is not None
    ready_request = MarkChangePullRequestReady(
        change_id="change-a",
        operation_id="ready-change-a",
        finalization_id=receipt.finalization_id,
        exact_head=exact_head,
    )

    with pytest.raises(PortfolioApplicationError, match="reconciled final checkpoint"):
        application.mark_change_ready("change-a", ready_request)

    assert provider.set_pull_request_draft_state.call_count == 0
    runtimes["change-a"].record_checkpoint_branch_publication(checkpoint, exact_head)
    runtimes["change-a"].acknowledge_checkpoint_publication(checkpoint.pending_checkpoint, exact_head)

    ready = application.mark_current_change_ready("change-a")

    assert (
        ready.finalization_id,
        runtimes["change-a"].change_stage(),
        application.list_integration_attention(),
    ) == (receipt.finalization_id, DeliveryChangeStage.AWAITING_MERGE, ())
    assert pull_requests[0].draft is False
    provider.observe_checks.assert_called_once()
    pull_requests[0] = pull_requests[0].model_copy(update={"head_sha": "f" * 40})
    provider.set_pull_request_draft_state.side_effect = _fail_once_then_set_draft_state(pull_requests)

    with pytest.raises(PublicationProviderError) as exc_info:
        application.reconcile_finalization_head("change-a")

    assert exc_info.value.code is PublicationProviderFailureCode.UNAVAILABLE
    assert runtimes["change-a"].finalization() == receipt
    assert runtimes["change-a"].ready_receipt() == ready
    assert runtimes["change-a"].change_stage() == DeliveryChangeStage.AWAITING_MERGE
    assert pull_requests[0].draft is False

    invalidation = application.reconcile_finalization_head("change-a")

    assert isinstance(invalidation, DeliveryFinalizationInvalidationReceipt)
    assert invalidation.finalization_id == receipt.finalization_id
    assert invalidation.expected_head == exact_head
    assert invalidation.observed_head == "f" * 40
    assert application._workspace_manager.observed_change_head("change-a") == exact_head
    assert runtimes["change-a"].change_stage() == DeliveryChangeStage.BUILDING
    assert pull_requests[0].draft is True
    assert provider.set_pull_request_draft_state.call_count == 3


def _awaiting_acceptance_fixture(  # noqa: PLR0913 - shared fixture keeps each independent control.
    tmp_path: Path,
    *,
    checks: tuple[PublicationCheck, ...] | Callable[[str], tuple[PublicationCheck, ...]] = (),
    mark_ready: bool = True,
    record_publication_identity: bool = True,
    clock: Callable[[], str] = lambda: "2026-08-04T00:00:00Z",
    sync_target: bool = False,
):
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        clock=clock,
    )
    runtime = runtimes["change-a"]
    exact_head = coordinator.show("change-a").last_reviewed_commit
    if sync_target:
        _attach_local_target(application, tmp_path)
        application.sync_change_with_current_target("change-a", "sync-before-finalization")
        exact_head = _commit_local_descendant(coordinator.show("change-a"), "merge-offer.txt")
    application.finalize_change(
        "change-a",
        _finalization_request("change-a", exact_head),
    )
    state = {
        "pull_request": PublicationPullRequest(
            repository="example/project",
            number=7,
            node_id="PR_node_7",
            head_branch="owlbear/change/change-a",
            head_sha=exact_head,
            base_branch="main",
            title="Change A",
            body=(
                "<!-- owlbear-change:change-a -->\n\n"
                "<!-- owlbear-generated:start -->\n"
                "Finalized Change A.\n"
                "<!-- owlbear-generated:end -->\n"
            ),
            draft=True,
            state="open",
            merged=False,
        )
    }
    provider = Mock()
    provider.read_repository.return_value = PublicationRepository(
        repository="example/project",
        default_branch="main",
    )
    provider.find_pull_request.return_value = None
    provider.create_draft_pull_request.side_effect = lambda _request: state["pull_request"]
    provider.read_pull_request.side_effect = lambda _repository, _number: state["pull_request"]
    observed_checks = checks(exact_head) if callable(checks) else checks
    provider.observe_checks.return_value = PublicationCheckSnapshot(
        repository="example/project",
        number=7,
        head_sha=exact_head,
        checks=observed_checks,
    )

    def set_draft_state(request):
        state["pull_request"] = state["pull_request"].model_copy(update={"draft": request.draft})
        return state["pull_request"]

    provider.set_pull_request_draft_state.side_effect = set_draft_state
    publisher = DraftPullRequestPublisher(
        provider,
        repository="example/project",
        target_branch="main",
        state_root=tmp_path / "pull-requests",
    )
    publisher.publish(
        CreateOrReconcileDraftPullRequest(
            change_id="change-a",
            operation_id="create-change-a",
            published_head=exact_head,
            title="Change A",
            generated_summary="Finalized Change A.",
        )
    )
    application._draft_pull_request_publisher = publisher
    checkpoint = runtime.checkpoint_publication_state()
    assert checkpoint.pending_checkpoint is not None
    runtime.record_checkpoint_branch_publication(checkpoint, exact_head)
    runtime.acknowledge_checkpoint_publication(checkpoint.pending_checkpoint, exact_head)
    if record_publication_identity:
        runtime.record_publication_identity(
            DeliveryChangePublicationIdentity(
                change_id="change-a",
                repository="example/project",
                number=7,
                node_id="PR_node_7",
                head_sha=exact_head,
            )
        )
    if not mark_ready:
        return application, runtime, provider, state, exact_head, _state_root
    ready = application.mark_current_change_ready("change-a")
    assert ready.head_sha == exact_head
    return application, runtime, provider, state, exact_head, _state_root


@pytest.mark.parametrize(
    ("kind", "status", "conclusion"),
    [
        (PublicationCheckKind.CHECK_RUN, "completed", "failure"),
        (PublicationCheckKind.STATUS_CONTEXT, "error", "error"),
        (PublicationCheckKind.CHECK_RUN, "completed", None),
        (PublicationCheckKind.CHECK_RUN, "completed", "provider-added-failure"),
    ],
)
def test_mark_change_ready_captures_required_check_failure(
    tmp_path: Path,
    kind: PublicationCheckKind,
    status: str,
    conclusion: str | None,
) -> None:
    application, runtime, provider, _state, exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path,
        checks=lambda head: (
            PublicationCheck(
                check_id="check-failure",
                kind=kind,
                name="unit tests",
                head_sha=head,
                status=status,
                conclusion=conclusion,
                required=True,
            ),
        ),
        mark_ready=False,
    )

    ready = application.mark_current_change_ready("change-a")

    disposition = runtime.change_disposition()
    assert disposition is not None
    observations = application._draft_pull_request_publisher.read_check_observations(
        ReadChangePublicationCheckObservations(
            change_id="change-a",
            repository="example/project",
            number=7,
            exact_commit=exact_head,
        )
    )
    assert len(observations) == 1
    observation_id = observations[0].observation_id
    assert disposition.diagnostics[:4] == (
        "required-publication-check-failure",
        f"exact-head:{exact_head}",
        f"check-observation:{observation_id}",
        "failing-required-checks:1",
    )
    assert runtime.change_disposition_publication() == runtime.publication_history().current
    assert ready.head_sha == exact_head
    assert runtime.ready_receipt() == ready
    assert provider.set_pull_request_draft_state.call_count == 1
    assert tuple(observation.observation_id for observation in observations) == (observation_id,)


@pytest.mark.parametrize(
    ("kind", "status", "conclusion", "required"),
    [
        (PublicationCheckKind.CHECK_RUN, "queued", None, True),
        (PublicationCheckKind.CHECK_RUN, "completed", "neutral", True),
        (PublicationCheckKind.CHECK_RUN, "completed", "skipped", True),
        (PublicationCheckKind.CHECK_RUN, "completed", "failure", False),
    ],
)
def test_mark_change_ready_does_not_gate_on_pending_or_nonblocking_checks(
    tmp_path: Path,
    kind: PublicationCheckKind,
    status: str,
    conclusion: str | None,
    required: bool,  # noqa: FBT001 - pytest parametrization supplies this boolean positionally.
) -> None:
    application, runtime, provider, _state, exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path,
        checks=lambda head: (
            PublicationCheck(
                check_id="check-nonblocking",
                kind=kind,
                name="optional check",
                head_sha=head,
                status=status,
                conclusion=conclusion,
                required=required,
            ),
        ),
        mark_ready=False,
    )

    ready = application.mark_current_change_ready("change-a")

    assert ready.head_sha == exact_head
    assert runtime.change_disposition() is None
    assert runtime.change_stage() == DeliveryChangeStage.AWAITING_MERGE
    assert provider.set_pull_request_draft_state.call_count == 1


def test_mark_change_ready_aborts_before_draft_mutation_when_check_observation_fails(
    tmp_path: Path,
) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path,
        mark_ready=False,
    )
    provider.observe_checks.side_effect = PublicationProviderError(
        PublicationProviderFailureCode.INVALID_RESPONSE,
        "observe_checks",
        "GitHub returned an invalid check duration",
        retry_safe=True,
    )

    with pytest.raises(PublicationProviderError, match="invalid check duration"):
        application.mark_current_change_ready("change-a")

    assert runtime.finalization() is not None
    assert runtime.finalization().exact_head == exact_head
    assert runtime.ready_receipt() is None
    assert state["pull_request"].draft is True
    provider.set_pull_request_draft_state.assert_not_called()


@pytest.mark.parametrize(
    ("status", "conclusion", "required", "expected"),
    [
        ("completed", "failure", True, PublicationCheckBlockingState.BLOCKING),
        ("queued", None, True, PublicationCheckBlockingState.REQUIRED_PENDING),
        ("completed", None, True, PublicationCheckBlockingState.BLOCKING),
        ("completed", "neutral", True, PublicationCheckBlockingState.NOT_BLOCKING),
        ("completed", "failure", False, PublicationCheckBlockingState.NOT_BLOCKING),
    ],
)
def test_classify_publication_check_preserves_ready_semantics(
    status: str,
    conclusion: str | None,
    required: Literal[True, False],
    expected: PublicationCheckBlockingState,
) -> None:
    check = PublicationCheck(
        check_id="check-classification",
        kind=PublicationCheckKind.CHECK_RUN,
        name="classification",
        head_sha="a" * 40,
        status=status,
        conclusion=conclusion,
        required=required,
    )

    assert classify_publication_check(check) is expected


def test_required_check_attention_records_after_ready_without_preexisting_publication_identity(tmp_path: Path) -> None:
    application, runtime, provider, _state, _exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path,
        checks=lambda head: (
            PublicationCheck(
                check_id="check-failure",
                kind=PublicationCheckKind.CHECK_RUN,
                name="unit tests",
                head_sha=head,
                status="completed",
                conclusion="failure",
                required=True,
            ),
        ),
        mark_ready=False,
        record_publication_identity=False,
    )

    ready = application.mark_current_change_ready("change-a")

    assert runtime.change_disposition() is not None
    assert runtime.ready_receipt() == ready
    assert provider.set_pull_request_draft_state.call_count == 1


def test_mark_change_ready_publishes_ready_authority_to_delivery_state(tmp_path: Path) -> None:
    application, runtime, _provider, _state, _exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path,
        mark_ready=False,
    )
    state_publisher = Mock()
    application._delivery_state_publisher = state_publisher

    ready = application.mark_current_change_ready("change-a")

    state_publisher.publish.assert_called_once()
    publication = state_publisher.publish.call_args.kwargs
    assert publication["change_id"] == "change-a"
    assert publication["operation_id"] == f"ready-{ready.receipt_id}"
    assert publication["runtime"] is runtime
    assert publication["runtime"].ready_receipt() == ready


def test_reconcile_acceptance_publishes_new_attention_authority(tmp_path: Path) -> None:
    application, runtime, _provider, state, _exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    state_publisher = Mock()
    application._delivery_state_publisher = state_publisher
    state["pull_request"] = state["pull_request"].model_copy(update={"state": "closed"})

    outcomes = application.reconcile_awaiting_acceptance(("change-a",))

    assert outcomes[0].status.value == "attention"
    disposition = runtime.change_disposition()
    assert disposition is not None
    state_publisher.publish.assert_called_once()
    publication = state_publisher.publish.call_args.kwargs
    assert publication["change_id"] == "change-a"
    assert publication["operation_id"] == f"acceptance-attention-{disposition.disposition_id}"
    assert publication["runtime"] is runtime


def test_latch_regression_preserves_domain_error_when_attention_publication_fails(tmp_path: Path) -> None:
    application, runtime, _provider, state, _exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    merged = state["pull_request"].model_copy(
        update={
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "f" * 40,
            "merged_at": datetime(2026, 8, 3, 23, tzinfo=UTC),
            "merged_by_login": "octocat",
        }
    )
    state["pull_request"] = merged
    observation = application._draft_pull_request_publisher.observe_pull_request(
        ObserveChangePublicationPullRequest(change_id="change-a")
    )
    assert observation is not None
    runtime.latch_merged_pull_request(observation)

    state_publisher = Mock()
    state_publisher.publish.side_effect = DeliveryStatePublicationError(
        "Delivery state is unavailable",
        retry_safe=True,
    )
    application._delivery_state_publisher = state_publisher
    state["pull_request"] = merged.model_copy(update={"state": "open", "merged": False, "merged_at": None})

    with pytest.raises(PortfolioApplicationError, match="regressed from the established merged observation"):
        application.observe_acceptance("change-a")

    disposition = runtime.change_disposition()
    assert disposition is not None
    assert disposition.acceptance_reason is DeliveryAcceptanceAttentionReason.LATCH_REGRESSION
    state_publisher.publish.assert_called_once()
    assert state_publisher.publish.call_args.kwargs["operation_id"].startswith("acceptance-attention-")


def test_required_check_attention_retries_with_stable_diagnostics_after_resolution(tmp_path: Path) -> None:
    application, runtime, _provider, _state, _exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path,
        checks=lambda head: (
            PublicationCheck(
                check_id="check-failure",
                kind=PublicationCheckKind.CHECK_RUN,
                name="unit\ntests",
                head_sha=head,
                status="completed",
                conclusion="failure",
                required=True,
            ),
        ),
        mark_ready=False,
    )

    ready = application.mark_current_change_ready("change-a")
    first = runtime.change_disposition()
    assert first is not None
    assert runtime.ready_receipt() == ready

    application.resolve_change_disposition("change-a", first.disposition_id)

    replayed = application.mark_current_change_ready("change-a")

    assert replayed == ready
    assert runtime.change_disposition() is None
    assert _provider.observe_checks.call_count == 1


def test_mark_change_ready_replays_existing_ready_without_reobserving_checks(tmp_path: Path) -> None:
    application, runtime, provider, _state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    first = runtime.ready_receipt()
    assert first is not None
    observed_calls = provider.observe_checks.call_count
    draft_state_calls = provider.set_pull_request_draft_state.call_count
    provider.observe_checks.return_value = PublicationCheckSnapshot(
        repository="example/project",
        number=7,
        head_sha=exact_head,
        checks=(
            PublicationCheck(
                check_id="check-failure",
                kind=PublicationCheckKind.CHECK_RUN,
                name="unit tests",
                head_sha=exact_head,
                status="completed",
                conclusion="failure",
                required=True,
            ),
        ),
    )

    replayed = application.mark_current_change_ready("change-a")

    assert replayed == first
    assert provider.observe_checks.call_count == observed_calls
    assert provider.set_pull_request_draft_state.call_count == draft_state_calls
    assert runtime.change_stage() == DeliveryChangeStage.AWAITING_MERGE
    assert runtime.change_disposition() is None

    with pytest.raises(DeliveryRuntimeConflictError, match="already awaiting merge"):
        application.mark_change_ready(
            "change-a",
            MarkChangePullRequestReady(
                change_id="change-a",
                operation_id="different-ready-operation",
                finalization_id=first.finalization_id,
                exact_head=exact_head,
            ),
        )

    assert provider.observe_checks.call_count == observed_calls
    assert provider.set_pull_request_draft_state.call_count == draft_state_calls
    assert runtime.ready_receipt() == first
    assert runtime.change_disposition() is None


def test_required_check_diagnostics_are_sorted_and_sanitized() -> None:
    head = "a" * 40
    checks = (
        PublicationCheck(
            check_id="check-zeta",
            kind=PublicationCheckKind.CHECK_RUN,
            name="zeta\ncheck",
            head_sha=head,
            status="completed",
            conclusion="failure",
            required=True,
        ),
        PublicationCheck(
            check_id="check-alpha",
            kind=PublicationCheckKind.STATUS_CONTEXT,
            name="alpha",
            head_sha=head,
            status="error",
            conclusion="error",
            required=True,
        ),
    )
    snapshot = PublicationCheckSnapshot(
        repository="example/project",
        number=7,
        head_sha=head,
        checks=checks,
    )

    diagnostics = _required_check_diagnostics(snapshot, "b" * 64, checks)

    assert diagnostics == (
        "required-publication-check-failure",
        f"exact-head:{head}",
        f"check-observation:{'b' * 64}",
        "failing-required-checks:2",
        "required-check:check-alpha:name=alpha:status=error:conclusion=error",
        "required-check:check-zeta:name=zeta check:status=completed:conclusion=failure",
    )


def test_required_check_diagnostics_cap_reports_truncation() -> None:
    head = "a" * 40
    checks = tuple(
        PublicationCheck(
            check_id=f"check-{index:02d}",
            kind=PublicationCheckKind.CHECK_RUN,
            name=f"check {index:02d}",
            head_sha=head,
            status="completed",
            conclusion="failure",
            required=True,
        )
        for index in range(9)
    )
    snapshot = PublicationCheckSnapshot(
        repository="example/project",
        number=7,
        head_sha=head,
        checks=checks,
    )

    diagnostics = _required_check_diagnostics(snapshot, "b" * 64, checks)

    assert len(diagnostics) == 4 + 8 + 1
    assert diagnostics[-1] == "required-checks-truncated:1"


def test_observe_change_publication_checks_remains_read_only_for_required_failure(tmp_path: Path) -> None:
    application, runtime, provider, _state, _exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path,
        checks=lambda head: (
            PublicationCheck(
                check_id="check-failure",
                kind=PublicationCheckKind.CHECK_RUN,
                name="unit tests",
                head_sha=head,
                status="completed",
                conclusion="failure",
                required=True,
            ),
        ),
        mark_ready=False,
    )

    observation = application.observe_change_publication_checks("change-a")

    assert observation.snapshot.checks[0].conclusion == "failure"
    assert runtime.change_disposition() is None
    assert provider.set_pull_request_draft_state.call_count == 0


def test_reconcile_awaiting_acceptance_isolated_provider_matrix(tmp_path: Path) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    now = datetime(2026, 8, 4, tzinfo=UTC)

    def clock():
        return now.isoformat()

    application._clock = clock
    waiting = application.reconcile_awaiting_acceptance(("change-a",))
    assert waiting[0].status.value == "waiting"
    assert runtime.change_disposition() is None

    provider.read_pull_request.side_effect = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE,
        "read_pull_request",
        "GitHub is unavailable",
        retry_safe=True,
    )
    now += timedelta(seconds=1)
    unavailable = application.reconcile_awaiting_acceptance(("change-a",))
    assert unavailable[0].status.value == "provider-unavailable"
    assert unavailable[0].code == "unavailable"
    provider.read_pull_request.side_effect = lambda _repository, _number: state["pull_request"]

    state["pull_request"] = state["pull_request"].model_copy(
        update={
            "head_sha": exact_head,
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "f" * 40,
            "merged_at": datetime(2026, 8, 3, 14, tzinfo=UTC),
            "merged_by_login": "octocat",
        }
    )
    now += timedelta(seconds=2)
    calls = provider.read_pull_request.call_count
    completed = application.reconcile_awaiting_acceptance(("change-a",))
    assert provider.read_pull_request.call_count == calls + 1
    assert completed[0].status.value == "completed"
    assert completed[0].completion_id is not None
    assert runtime.completion_receipt() is not None


def test_prepare_review_repair_returns_ready_pull_request_to_draft(tmp_path: Path) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    provider.set_pull_request_draft_state.reset_mock()

    invalidation = application.prepare_review_repair("change-a")

    assert invalidation.reason == "review-repair"
    assert invalidation.expected_head == invalidation.observed_head == exact_head
    assert runtime.finalization() is None
    assert runtime.ready_receipt() is None
    assert state["pull_request"].draft is True
    provider.set_pull_request_draft_state.assert_called_once()
    assert provider.set_pull_request_draft_state.call_args.args[0].draft is True
    assert application.prepare_review_repair("change-a") == invalidation
    assert provider.set_pull_request_draft_state.call_count == 1


def test_prepare_review_repair_accepts_pull_request_already_in_draft(tmp_path: Path) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path,
        mark_ready=False,
    )

    invalidation = application.prepare_review_repair("change-a")

    assert invalidation.expected_head == invalidation.observed_head == exact_head
    assert runtime.finalization() is None
    assert state["pull_request"].draft is True
    assert provider.set_pull_request_draft_state.call_count == 0


def test_prepare_review_repair_rejects_merged_pull_request(tmp_path: Path) -> None:
    application, runtime, provider, state, _exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    state["pull_request"] = state["pull_request"].model_copy(
        update={
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "f" * 40,
            "merged_at": datetime(2026, 8, 3, 23, tzinfo=UTC),
            "merged_by_login": "octocat",
        }
    )
    provider.set_pull_request_draft_state.reset_mock()

    with pytest.raises(PortfolioApplicationError, match="open pull request at the finalized head"):
        application.prepare_review_repair("change-a")

    assert runtime.finalization() is not None
    assert runtime.ready_receipt() is not None
    assert provider.set_pull_request_draft_state.call_count == 0


def test_prepare_review_repair_rejects_provider_head_mismatch(tmp_path: Path) -> None:
    application, runtime, _provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    state["pull_request"] = state["pull_request"].model_copy(update={"head_sha": "f" * 40})

    with pytest.raises(PortfolioApplicationError, match="open pull request at the finalized head"):
        application.prepare_review_repair("change-a")

    assert runtime.finalization() is not None
    assert runtime.finalization().exact_head == exact_head
    assert runtime.ready_receipt() is not None


def test_prepare_review_repair_preserves_authority_when_draft_transition_fails(tmp_path: Path) -> None:
    application, runtime, provider, _state, _exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    provider.set_pull_request_draft_state.reset_mock()
    provider.set_pull_request_draft_state.side_effect = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE,
        "return_to_draft",
        "GitHub is unavailable",
        retry_safe=True,
    )

    with pytest.raises(PublicationProviderError, match="GitHub is unavailable"):
        application.prepare_review_repair("change-a")

    assert runtime.finalization() is not None
    assert runtime.ready_receipt() is not None


def test_prepare_review_repair_does_not_mutate_provider_with_existing_attention(tmp_path: Path) -> None:
    application, runtime, provider, state, _exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    runtime.capture_publication_attention(
        datetime(2026, 8, 11, 16, tzinfo=UTC),
        ("provider check failed",),
    )
    provider.set_pull_request_draft_state.reset_mock()
    provider.observe_pull_request.reset_mock()

    with pytest.raises(PortfolioApplicationError, match="current Change attention resolution"):
        application.prepare_review_repair("change-a")

    assert state["pull_request"].draft is False
    provider.observe_pull_request.assert_not_called()
    provider.set_pull_request_draft_state.assert_not_called()
    assert runtime.finalization() is not None
    assert runtime.ready_receipt() is not None


@pytest.mark.parametrize(
    "operation",
    ["sync", "adopt", "promote"],
)
def test_review_repair_fences_external_head_mutations_before_workspace_side_effects(
    tmp_path: Path,
    operation: str,
) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    application.prepare_review_repair("change-a")
    provider.set_pull_request_draft_state.reset_mock()
    provider.update_pull_request.reset_mock()
    workspace_method = {
        "sync": "sync_with_target",
        "adopt": "adopt_external_head",
        "promote": "promote_external_head",
    }[operation]
    operation_call = {
        "sync": lambda: application.sync_change_with_target("change-a", "2" * 40, "sync-during-review-repair"),
        "adopt": lambda: application.adopt_external_head(
            "change-a",
            exact_head,
            "5" * 40,
            "adopt-during-review-repair",
        ),
        "promote": lambda: application.promote_external_head(
            "change-a",
            exact_head,
            "promote-during-review-repair",
        ),
    }[operation]

    with (
        patch.object(application._workspace_manager, workspace_method) as workspace_operation,
        pytest.raises(
            PortfolioApplicationError,
            match="review repair",
        ),
    ):
        operation_call()

    workspace_operation.assert_not_called()
    provider.set_pull_request_draft_state.assert_not_called()
    provider.update_pull_request.assert_not_called()
    assert state["pull_request"].head_sha == exact_head
    assert runtime.finalization_invalidation() is not None
    assert runtime.finalization_invalidation().reason == "review-repair"


def test_review_repair_commit_can_be_refinalized_published_and_marked_ready(tmp_path: Path) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path, sync_target=True
    )
    invalidation = application.prepare_review_repair("change-a")
    stopped = application.acquire_change_action(_continuation_request(application))
    assert stopped.kind == "reconciled"
    stopped = application.acquire_change_action(_continuation_request(application))
    assert stopped.kind == "unsupported"
    assert stopped.reason_code == "repair-required"
    coordination = application._workspace_manager.show("change-a")
    repaired_head = _commit_reviewed_head(
        application,
        coordination,
        "review-fix.txt",
        "review fix\n",
        "address review feedback",
    )
    provider.observe_checks.return_value = PublicationCheckSnapshot(
        repository="example/project",
        number=7,
        head_sha=repaired_head,
        checks=(),
    )

    def update_summary(request):
        state["pull_request"] = state["pull_request"].model_copy(update={"body": request.body})
        return state["pull_request"]

    provider.update_pull_request.side_effect = update_summary
    branch_publisher = Mock()

    def publish_branch(request: PublishChangeBranch) -> ChangeBranchPublicationReceipt:
        state["pull_request"] = state["pull_request"].model_copy(update={"head_sha": repaired_head})
        return _requested_branch_receipt(request)

    branch_publisher.publish.side_effect = publish_branch
    application._change_branch_publisher = branch_publisher

    assert state["pull_request"].head_sha == exact_head
    finalization = application.finalize_change(
        "change-a",
        _finalization_request("change-a", repaired_head),
    )

    assert invalidation.expected_head == exact_head
    assert finalization.finalization_id != invalidation.finalization_id
    assert runtime.finalization_invalidation() is None
    assert state["pull_request"].head_sha == exact_head
    result = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled is True
    assert result.state.pending_checkpoint is None
    assert result.state.published_head == repaired_head
    assert runtime.finalization() == finalization
    assert state["pull_request"].head_sha == repaired_head
    assert state["pull_request"].draft is True
    branch_publisher.publish.assert_called_once()

    ready = application.mark_current_change_ready("change-a")

    assert ready.head_sha == repaired_head
    assert state["pull_request"].draft is False
    assert runtime.change_stage() == DeliveryChangeStage.AWAITING_MERGE


def test_reconcile_awaiting_acceptance_repairs_open_head_drift(tmp_path: Path) -> None:
    application, runtime, provider, state, _exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    provider.set_pull_request_draft_state.reset_mock()

    state["pull_request"] = state["pull_request"].model_copy(update={"head_sha": "f" * 40})
    moved = application.reconcile_awaiting_acceptance(("change-a",))

    assert moved[0].status.value == "head-moved"
    assert moved[0].code == "ERR_DELIVERY_ACCEPTANCE_HEAD_MOVED"
    assert runtime.change_stage() == DeliveryChangeStage.ACCEPTANCE_ATTENTION
    assert runtime.finalization() is None
    assert runtime.finalization_invalidation() is not None
    assert runtime.ready_receipt() is None
    disposition = runtime.change_disposition()
    assert disposition is not None
    assert disposition.acceptance_reason is DeliveryAcceptanceAttentionReason.HEAD_MOVED
    assert state["pull_request"].draft is True
    provider.set_pull_request_draft_state.assert_called_once()


def test_reconcile_awaiting_acceptance_skips_a_busy_change_without_provider_io(tmp_path: Path) -> None:
    application, _runtime, provider, _state, _exact_head, state_root = _awaiting_acceptance_fixture(tmp_path)
    lock_root = state_root / "publications/checkpoints/locks/change-a"
    provider_calls = provider.read_pull_request.call_count

    with locked_roots((lock_root,)):
        outcomes = application.reconcile_awaiting_acceptance(("change-a",))

    assert outcomes[0].status.value == "skipped"
    assert outcomes[0].code == "ERR_DELIVERY_RECONCILIATION_BUSY"
    assert provider.read_pull_request.call_count == provider_calls


def test_reconcile_awaiting_acceptance_ignores_ineligible_changes(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )

    assert application.reconcile_awaiting_acceptance() == ()


def _stub_acceptance_reconciliation(
    application: PortfolioApplication,
    statuses: dict[str, DeliveryAcceptanceReconciliationStatus] | None = None,
) -> list[str]:
    calls: list[str] = []
    selected_statuses = statuses or {}

    def reconcile(change_id: str) -> DeliveryAcceptanceReconciliationOutcome:
        calls.append(change_id)
        return DeliveryAcceptanceReconciliationOutcome(
            change_id=change_id,
            status=selected_statuses.get(change_id, DeliveryAcceptanceReconciliationStatus.WAITING),
        )

    application._reconcile_awaiting_acceptance_change = reconcile
    return calls


def test_reconcile_awaiting_acceptance_rotates_beyond_batch_limit(tmp_path: Path) -> None:
    change_ids = tuple(f"change-{index:02d}" for index in range(9))
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        dict.fromkeys(change_ids, DeliveryStage.COMPLETED),
    )
    application._is_acceptance_reconciliation_eligible = lambda _runtime: True
    calls = _stub_acceptance_reconciliation(application)

    first = application.reconcile_awaiting_acceptance(change_ids)
    assert tuple(calls) == change_ids[:8]
    assert first[-1].change_id == "change-08"
    assert first[-1].status is DeliveryAcceptanceReconciliationStatus.SKIPPED

    calls.clear()
    second = application.reconcile_awaiting_acceptance(change_ids)
    assert tuple(calls) == ("change-08", *change_ids[:7])
    assert second[0].change_id == "change-08"
    assert second[0].status is DeliveryAcceptanceReconciliationStatus.WAITING


def test_reconcile_awaiting_acceptance_partial_request_does_not_regress_cursor(tmp_path: Path) -> None:
    change_ids = tuple(f"change-{index:02d}" for index in range(9))
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        dict.fromkeys(change_ids, DeliveryStage.COMPLETED),
    )
    application._is_acceptance_reconciliation_eligible = lambda _runtime: True
    calls = _stub_acceptance_reconciliation(application)

    application.reconcile_awaiting_acceptance(change_ids)
    calls.clear()
    application.reconcile_awaiting_acceptance(change_ids[:8])
    assert tuple(calls) == change_ids[:8]

    calls.clear()
    application.reconcile_awaiting_acceptance(("change-08",))
    calls.clear()
    application.reconcile_awaiting_acceptance(change_ids)
    assert calls[0] == "change-08"

    calls.clear()
    application.reconcile_awaiting_acceptance(change_ids)
    assert calls[0] == "change-07"

    calls.clear()
    application.reconcile_awaiting_acceptance(("change-00",))
    calls.clear()
    application.reconcile_awaiting_acceptance(change_ids)
    assert calls[0] == "change-06"


def test_reconcile_awaiting_acceptance_full_request_with_extra_ids_advances_cursor(tmp_path: Path) -> None:
    change_ids = tuple(f"change-{index:02d}" for index in range(9))
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        dict.fromkeys(change_ids, DeliveryStage.COMPLETED),
    )
    application._is_acceptance_reconciliation_eligible = lambda _runtime: True
    calls = _stub_acceptance_reconciliation(application)

    application.reconcile_awaiting_acceptance((*change_ids, "change-99"))
    assert tuple(calls) == change_ids[:8]

    calls.clear()
    application.reconcile_awaiting_acceptance(change_ids)
    assert calls[0] == "change-08"


def test_reconcile_awaiting_acceptance_advances_after_failure_and_busy_change(tmp_path: Path) -> None:
    change_ids = tuple(f"change-{index:02d}" for index in range(9))
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        dict.fromkeys(change_ids, DeliveryStage.COMPLETED),
    )
    application._is_acceptance_reconciliation_eligible = lambda _runtime: True
    calls = _stub_acceptance_reconciliation(
        application,
        {
            "change-00": DeliveryAcceptanceReconciliationStatus.PROVIDER_UNAVAILABLE,
            "change-01": DeliveryAcceptanceReconciliationStatus.SKIPPED,
        },
    )

    first = application.reconcile_awaiting_acceptance(change_ids)
    assert tuple(calls) == change_ids[:8]
    assert first[0].status is DeliveryAcceptanceReconciliationStatus.PROVIDER_UNAVAILABLE
    assert first[1].status is DeliveryAcceptanceReconciliationStatus.SKIPPED

    calls.clear()
    application.reconcile_awaiting_acceptance(change_ids)
    assert calls[0] == "change-08"


def test_reconcile_awaiting_acceptance_cursor_survives_restart(tmp_path: Path) -> None:
    change_ids = tuple(f"change-{index:02d}" for index in range(9))
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        dict.fromkeys(change_ids, DeliveryStage.COMPLETED),
    )
    application._is_acceptance_reconciliation_eligible = lambda _runtime: True
    first_calls = _stub_acceptance_reconciliation(application)
    application.reconcile_awaiting_acceptance(change_ids)
    assert tuple(first_calls) == change_ids[:8]
    cursor_path = state_root / "claims/acceptance-reconciliation/cursor.json"
    assert json.loads(cursor_path.read_text(encoding="utf-8"))["next_change_id"] == "change-08"

    reopened, _coordinator, _manager = _reopen_portfolio(tmp_path, state_root, runtimes)
    reopened._is_acceptance_reconciliation_eligible = lambda _runtime: True
    second_calls = _stub_acceptance_reconciliation(reopened)
    reopened.reconcile_awaiting_acceptance(change_ids)

    assert second_calls[0] == "change-08"


@pytest.mark.parametrize("user_state", _USER_CHECKOUT_STATES)
def test_observe_acceptance_preserves_user_checkout_states(
    tmp_path: Path,
    user_state: str,
    user_checkout_snapshot,
    prepare_user_checkout_state,
    seed_user_checkout_metadata,
) -> None:
    application, runtime, _provider, state, _exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    repository = application._workspace_manager.repository
    seed_user_checkout_metadata(repository)
    prepare_user_checkout_state(repository, user_state)
    before = user_checkout_snapshot(repository, ("refs/heads/owlbear/change/change-a",))
    state["pull_request"] = state["pull_request"].model_copy(
        update={
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "f" * 40,
            "merged_at": datetime(2026, 8, 3, 23, tzinfo=UTC),
            "merged_by_login": "octocat",
        }
    )

    receipt = application.observe_acceptance("change-a")
    replayed = application.observe_acceptance("change-a")

    assert isinstance(receipt, CompletionReceipt)
    assert replayed == receipt
    assert receipt.accepted_merge_commit == "f" * 40
    assert runtime.change_stage() == DeliveryChangeStage.COMPLETED
    before.assert_unchanged(repository)


def test_github_provider_acceptance_rejects_incomplete_evidence_and_replays_completion(tmp_path: Path) -> None:
    application, runtime, provider, _state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    now = datetime(2026, 8, 4, tzinfo=UTC)

    def clock():
        return now.isoformat()

    application._clock = clock
    provider_calls_before_acceptance = provider.read_pull_request.call_count
    merge_oid = "e" * 40
    merged_at = "2026-08-03T23:00:00Z"
    rest_response = {
        "number": 7,
        "node_id": "PR_node_7",
        "head": {"ref": "owlbear/change/change-a", "sha": exact_head},
        "base": {"ref": "main", "sha": "b" * 40},
        "title": "Change A",
        "body": (
            "<!-- owlbear-change:change-a -->\n\n"
            "<!-- owlbear-generated:start -->\n"
            "Finalized Change A.\n"
            "<!-- owlbear-generated:end -->\n"
        ),
        "draft": False,
        "state": "closed",
        "merged": True,
        "merge_commit_sha": None,
        "merged_at": merged_at,
        "merged_by": {"login": "octocat"},
    }
    graphql_response = {
        "data": {
            "repository": {
                "nameWithOwner": "example/project",
                "pullRequest": {
                    "number": 7,
                    "headRefOid": exact_head,
                    "baseRefName": "main",
                    "merged": True,
                    "mergedAt": merged_at,
                    "mergeCommit": {"oid": merge_oid},
                },
            },
        },
    }
    incomplete_graphql_response = {
        "data": {
            "repository": {
                "nameWithOwner": "example/project",
                "pullRequest": {
                    "number": 7,
                    "headRefOid": exact_head,
                    "baseRefName": "main",
                    "merged": True,
                    "mergedAt": merged_at,
                    "mergeCommit": None,
                },
            },
        },
    }

    def completed(payload: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            args=(),
            returncode=0,
            stdout=json.dumps(payload).encode(),
            stderr=b"",
        )

    runner = Mock(
        side_effect=(
            completed(rest_response),
            completed(incomplete_graphql_response),
            completed(rest_response),
            completed(graphql_response),
        )
    )
    github_provider = GitHubCliPublicationProvider(runner=runner)
    provider.read_pull_request.side_effect = github_provider.read_pull_request

    with pytest.raises(PublicationProviderError) as exc_info:
        application.observe_acceptance("change-a")

    assert exc_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert exc_info.value.retry_safe is True
    assert runtime.completion_receipt() is None
    assert runtime.change_stage() == DeliveryChangeStage.AWAITING_MERGE
    assert provider.read_pull_request.call_count == provider_calls_before_acceptance + 1
    assert runner.call_count == 2

    with pytest.raises(DeliveryAcceptanceWaitingError, match="retry-backoff"):
        application.observe_acceptance("change-a")
    assert runner.call_count == 2
    now += timedelta(seconds=1)
    receipt = application.observe_acceptance("change-a")

    assert isinstance(receipt, CompletionReceipt)
    assert receipt.accepted_merge_commit == merge_oid
    assert receipt.finalized_change_head == exact_head
    assert receipt.accepted_merge_commit != receipt.finalized_change_head
    assert runtime.completion_receipt() == receipt
    assert runtime.change_stage() == DeliveryChangeStage.COMPLETED
    provider_calls_after_completion = provider.read_pull_request.call_count
    runner_calls_after_completion = runner.call_count

    replayed = application.observe_acceptance("change-a")

    assert replayed == receipt
    assert provider.read_pull_request.call_count == provider_calls_after_completion
    assert runner.call_count == runner_calls_after_completion


def test_observe_acceptance_completes_once_and_replays_without_provider_io(  # noqa: PLR0915 - scenario covers full replay lifecycle.
    tmp_path: Path,
    user_checkout_snapshot,
) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    repository = tmp_path / "repository"
    runtime = runtimes["change-a"]
    exact_head = coordinator.show("change-a").last_reviewed_commit
    finalization = application.finalize_change(
        "change-a",
        _finalization_request("change-a", exact_head),
    )
    pull_request = PublicationPullRequest(
        repository="example/project",
        number=7,
        node_id="PR_node_7",
        head_branch="owlbear/change/change-a",
        head_sha=exact_head,
        base_branch="main",
        title="Change A",
        body=(
            "<!-- owlbear-change:change-a -->\n\n"
            "<!-- owlbear-generated:start -->\n"
            "Finalized Change A.\n"
            "<!-- owlbear-generated:end -->\n"
        ),
        draft=True,
        state="open",
        merged=False,
    )
    provider = Mock()
    provider.read_repository.return_value = PublicationRepository(
        repository="example/project",
        default_branch="main",
    )
    provider.find_pull_request.return_value = None
    provider.create_draft_pull_request.side_effect = lambda _request: pull_request
    provider.read_pull_request.side_effect = lambda _repository, _number: pull_request
    provider.observe_checks.return_value = PublicationCheckSnapshot(
        repository="example/project",
        number=7,
        head_sha=exact_head,
        checks=(),
    )

    def set_draft_state(request):
        nonlocal pull_request
        pull_request = pull_request.model_copy(update={"draft": request.draft})
        return pull_request

    provider.set_pull_request_draft_state.side_effect = set_draft_state
    publisher = DraftPullRequestPublisher(
        provider,
        repository="example/project",
        target_branch="main",
        state_root=tmp_path / "pull-requests",
    )
    publisher.publish(
        CreateOrReconcileDraftPullRequest(
            change_id="change-a",
            operation_id="create-change-a",
            published_head=exact_head,
            title="Change A",
            generated_summary="Finalized Change A.",
        )
    )
    application._draft_pull_request_publisher = publisher
    checkpoint = runtime.checkpoint_publication_state()
    assert checkpoint.pending_checkpoint is not None
    runtime.record_checkpoint_branch_publication(checkpoint, exact_head)
    runtime.acknowledge_checkpoint_publication(checkpoint.pending_checkpoint, exact_head)
    application.mark_change_ready(
        "change-a",
        MarkChangePullRequestReady(
            change_id="change-a",
            operation_id="ready-change-a",
            finalization_id=finalization.finalization_id,
            exact_head=exact_head,
        ),
    )
    user_checkout_before = user_checkout_snapshot(repository)
    now = datetime(2026, 8, 4, tzinfo=UTC)

    def clock():
        return now.isoformat()

    application._clock = clock
    with pytest.raises(DeliveryAcceptanceWaitingError, match="still open and unmerged"):
        application.observe_acceptance("change-a")
    assert runtime.change_disposition() is None
    pull_request = pull_request.model_copy(update={"state": "closed"})
    now += timedelta(seconds=1)
    with pytest.raises(PortfolioApplicationError, match="does not satisfy acceptance authority"):
        application.observe_acceptance("change-a")
    disposition = runtime.change_disposition()
    assert disposition is not None
    assert disposition.kind.value == "acceptance-attention"
    assert disposition.acceptance_reason is DeliveryAcceptanceAttentionReason.CLOSED_UNMERGED
    assert runtime.ready_receipt() is None
    with pytest.raises(PortfolioApplicationError, match="requires attention resolution"):
        application.observe_acceptance("change-a")
    assert application.resolve_change_disposition("change-a", disposition.disposition_id).disposition_id == (
        disposition.disposition_id
    )

    pull_request = pull_request.model_copy(update={"state": "open", "draft": True})
    assert application.reconcile_finalization_head("change-a") == finalization
    application.mark_current_change_ready("change-a")
    pull_request = pull_request.model_copy(
        update={
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "f" * 40,
            "merged_at": datetime(2026, 8, 3, 23, tzinfo=UTC),
            "merged_by_login": "octocat",
        }
    )

    merged_observation = publisher.observe_pull_request(ObserveChangePublicationPullRequest(change_id="change-a"))
    assert merged_observation is not None
    original_latch = runtime.latch_merged_pull_request(merged_observation)
    pull_request = pull_request.model_copy(update={"state": "open", "merged": False, "merged_at": None})
    now += timedelta(seconds=2)
    with pytest.raises(PortfolioApplicationError, match="regressed from the established merged observation"):
        application.observe_acceptance("change-a")
    disposition = runtime.change_disposition()
    assert disposition is not None
    assert disposition.kind.value == "acceptance-attention"
    assert disposition.acceptance_reason is DeliveryAcceptanceAttentionReason.LATCH_REGRESSION
    assert runtime.merged_pull_request_latch() == original_latch
    assert runtime.ready_receipt() is None

    application.resolve_change_disposition("change-a", disposition.disposition_id)
    pull_request = pull_request.model_copy(update={"draft": True})
    assert application.reconcile_finalization_head("change-a") == finalization
    application.mark_change_ready(
        "change-a",
        MarkChangePullRequestReady(
            change_id="change-a",
            operation_id="ready-after-acceptance-regression",
            finalization_id=finalization.finalization_id,
            exact_head=exact_head,
        ),
    )
    pull_request = pull_request.model_copy(
        update={
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "f" * 40,
            "merged_at": datetime(2026, 8, 3, 23, tzinfo=UTC),
            "merged_by_login": "octocat",
        }
    )

    receipt = application.observe_acceptance("change-a")
    provider_calls = provider.read_pull_request.call_count
    replayed = application.observe_acceptance("change-a")
    reconciled = application.reconcile_finalization_head("change-a")

    assert isinstance(receipt, CompletionReceipt)
    assert replayed == receipt
    assert reconciled == finalization
    assert provider.read_pull_request.call_count == provider_calls
    assert runtime.change_stage() == DeliveryChangeStage.COMPLETED
    assert application.list_work_items() == ()
    assert application.list_integration_attention() == ()
    assert receipt.accepted_merge_commit == "f" * 40
    assert receipt.check_observation_ids
    assert receipt.review_receipt_ids == (finalization.review.review_id,)
    assert application.list_retained_change_worktrees() == ()
    assert application.cleanup_change_worktree("change-a", receipt.completion_id).change_id == "change-a"
    assert application.show_work_item_view("change-a", "publication").publication.worktree_cleanup is None
    assert application.get_change("change-a").detail.publication.worktree_recovery is None
    user_checkout_before.assert_unchanged(repository)


def test_change_lifecycle_dispositions_delegate_through_application_lock(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    runtime = runtimes["change-a"]
    state_publisher = Mock()
    application._delivery_state_publisher = state_publisher

    deferral = _change_intent(application, "change-a", DeliveryChangeIntentKind.DEFER, "Wait for user review")
    assert runtime.change_deferral() == deferral
    assert runtime.change_stage() == DeliveryChangeStage.DEFERRED

    assert _change_intent(application, "change-a", DeliveryChangeIntentKind.RESUME) == deferral
    assert runtime.change_stage() == DeliveryChangeStage.BUILDING

    abandonment = application.abandon_change("change-a", "User stopped the Change")
    assert abandonment.prior_stage == DeliveryChangeStage.BUILDING
    assert runtime.change_stage() == DeliveryChangeStage.ABANDONED
    assert state_publisher.publish.call_count == 3
    retained = application.list_retained_change_worktrees()
    assert retained[0].cleanup_eligible is True
    assert retained[0].cleanup_blocked_reason is None


@pytest.mark.parametrize("user_state", _USER_CHECKOUT_STATES)
def test_abandoned_change_worktree_cleanup_preserves_branch_and_replays_receipt(
    tmp_path: Path,
    user_state: str,
    user_checkout_snapshot,
    prepare_user_checkout_state,
    seed_user_checkout_metadata,
) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    repository = application._workspace_manager.repository
    seed_user_checkout_metadata(repository)
    prepare_user_checkout_state(repository, user_state)
    coordination = application._workspace_manager.show("change-a")
    before = user_checkout_snapshot(repository, ("refs/heads/owlbear/change/change-a",))
    application.abandon_change("change-a", "User stopped the Change")

    receipt = application.cleanup_abandoned_change_worktree("change-a")

    assert isinstance(receipt, DeliveryChangeWorktreeCleanup)
    assert receipt.change_id == "change-a"
    assert not coordination.worktree_path.exists()
    assert _git_ref_exists(application._workspace_manager.repository, coordination.branch)
    assert runtimes["change-a"].change_stage() == DeliveryChangeStage.ABANDONED
    assert application.cleanup_abandoned_change_worktree("change-a") == receipt
    assert application.list_retained_change_worktrees() == ()
    assert application.show_work_item_view("change-a", "publication").publication.worktree_cleanup is None
    assert application.get_change("change-a").detail.publication.worktree_recovery is None
    before.assert_unchanged(repository)


def test_change_worktree_recovery_recreates_missing_worktree_and_replays_receipt(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = application._workspace_manager.show("change-a")
    shutil.rmtree(coordination.worktree_path)

    detail = application.show_work_item_view("change-a", "publication")
    change = application.get_change("change-a")
    assert detail.publication.worktree_recovery == change.detail.publication.worktree_recovery
    assert detail.publication.worktree_recovery.eligible is True
    assert detail.publication.worktree_recovery.recovery_reviewed_head == coordination.last_reviewed_commit

    receipt = application.recover_change_worktree(
        "change-a",
        coordination.last_reviewed_commit,
        confirmed_recovery=True,
    )

    assert isinstance(receipt, DeliveryChangeWorktreeRecovery)
    assert receipt.change_id == "change-a"
    assert receipt.branch_head == coordination.last_reviewed_commit
    assert receipt.recovery_reviewed_head == coordination.last_reviewed_commit
    assert receipt.worktree_path.is_dir()
    assert (
        application.recover_change_worktree(
            "change-a",
            coordination.last_reviewed_commit,
            confirmed_recovery=True,
        )
        == receipt
    )


def test_change_worktree_recovery_rejects_active_writer(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    coordination = coordinator.show("change-a")
    writer = ChangeWriter(
        attempt_id="attempt-change-a",
        claim_id="claim-change-a",
        actor_id="builder",
        process_id="process-change-a",
        claimed_at="2026-08-04T00:00:00Z",
        job_id=1,
        kind="build",
    )
    coordinator.acquire("change-a", writer)
    shutil.rmtree(coordination.worktree_path)

    with pytest.raises(CoordinationConflictError, match="recovery cannot overlap an active writer"):
        application.recover_change_worktree(
            "change-a",
            coordination.last_reviewed_commit,
            confirmed_recovery=True,
        )


def test_change_worktree_recovery_requires_exact_reviewed_head(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    coordination = application._workspace_manager.show("change-a")
    shutil.rmtree(coordination.worktree_path)

    with pytest.raises(CoordinationConflictError, match="recovery reviewed head differs"):
        application.recover_change_worktree(
            "change-a",
            "a" * 40,
            confirmed_recovery=True,
        )

    assert not coordination.worktree_path.exists()


@pytest.mark.parametrize("malformed", [False, True])
def test_change_worktree_recovery_contains_unknown_custody_without_target_mutation(
    tmp_path: Path, *, malformed: bool
) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    coordination = application._workspace_manager.show("change-a")
    target_head = _git(application._workspace_manager.repository, "rev-parse", "HEAD")
    coordination_path = state_root / "coordination/changes/change-a.json"
    if malformed:
        coordination_path.write_bytes(b"{")
    else:
        coordination_path.unlink()
    shutil.rmtree(coordination.worktree_path)

    with pytest.raises(DeliveryRuntimeReconciliationError):
        application.recover_change_worktree(
            "change-a",
            coordination.last_reviewed_commit,
            confirmed_recovery=True,
        )

    assert not coordination.worktree_path.exists()
    assert (coordination_path.read_bytes() if coordination_path.exists() else None) == (b"{" if malformed else None)
    assert _git(application._workspace_manager.repository, "rev-parse", "HEAD") == target_head


def test_change_worktree_recovery_rejects_active_publication_lease(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    coordination = coordinator.show("change-a")
    now = datetime.now(UTC)
    with coordinator.publication_lock("change-a") as lock:
        coordinator.reserve_publication(
            "change-a",
            PublicationLease(
                operation_id="recovery-publication",
                owner_id="recovery-owner",
                expires_at=(now + timedelta(minutes=5)).isoformat(),
            ),
            lock,
            now=now.isoformat(),
        )
    shutil.rmtree(coordination.worktree_path)

    with pytest.raises(CoordinationConflictError, match="active publication lease"):
        application.recover_change_worktree(
            "change-a",
            coordination.last_reviewed_commit,
            confirmed_recovery=True,
        )

    assert not coordination.worktree_path.exists()


def test_change_worktree_cleanup_requires_terminal_authority(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )

    with pytest.raises(PortfolioApplicationError, match="requires an abandoned or completed Change"):
        application.cleanup_change_worktree("change-a")


def test_abandoned_readmitted_change_cleans_up_beside_an_earlier_completion(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    coordination = application._workspace_manager.show("change-a")
    application.abandon_change("change-a", "User stopped the Change")
    digest = hashlib.sha256(b"change-a").hexdigest()
    completed_at = datetime(2026, 8, 11, 13, tzinfo=UTC)
    earlier = CompletionReceipt.create(
        CompletionEvidence(
            change_id="change-a",
            finalization_receipt_id=digest,
            finalized_change_head=digest[:40],
            repository_identity="example/project",
            pull_request_identity=CompletionPullRequestIdentity(number=7, node_id="PR_node_7"),
            accepted_target_ref="main",
            accepted_merge_commit=digest[-40:],
            merged_at=completed_at,
            acceptance_observation_id=digest,
            check_observation_ids=(digest,),
            review_receipt_ids=(digest,),
            completed_at=completed_at,
        )
    )
    display = CompletionDisplayMetadata.create(
        change_id="change-a",
        completion_id=earlier.completion_id,
        title="Earlier delivery",
        outcome_titles=("Earlier result",),
        outcome_promises=("Deliver the earlier result.",),
    )
    store = CompletionReceiptStore(runtimes["change-a"]._target_root)
    for participant in (store.participant(earlier), store.display_participant(display)):
        participant.destination().parent.mkdir(parents=True, exist_ok=True)
        participant.destination().write_bytes(participant.content)

    row = application.list_retained_change_worktrees()[0]
    assert row.cleanup_eligible is True
    assert row.cleanup_blocked_reason is None
    assert runtimes["change-a"].completion_receipt() is None

    application.cleanup_abandoned_change_worktree("change-a")

    assert not coordination.worktree_path.exists()
    assert application.list_retained_change_worktrees() == ()
    assert store.read_bundle("change-a") is not None


def test_abandoned_change_worktree_cleanup_surfaces_lost_worktree_attention(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    coordination = application._workspace_manager.show("change-a")
    application.abandon_change("change-a", "User stopped the Change")
    _git(
        application._workspace_manager.repository,
        "worktree",
        "remove",
        "--force",
        str(coordination.worktree_path),
    )

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        application.cleanup_abandoned_change_worktree("change-a")

    assert ChangeWorktreeAttentionCode.WORKTREE_MISSING in raised.value.attention


def test_retained_inventory_turns_completion_conflict_into_typed_attention(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    runtime = runtimes["change-a"]

    with patch.object(
        runtime,
        "completion_receipt",
        side_effect=DeliveryRuntimeConflictError("completion receipt is inconsistent"),
    ):
        row = application.list_retained_change_worktrees()[0]

    assert row.cleanup_eligible is False
    assert row.cleanup_blocked_reason is DeliveryRetainedWorktreeCleanupBlockReason.COMPLETION_STATE_INCONSISTENT


def test_retained_inventory_blocks_active_writer_and_publication_lease(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    runtime = runtimes["change-a"]
    with (
        patch.object(runtime, "change_stage", return_value=DeliveryChangeStage.COMPLETED),
        patch.object(runtime, "completion_receipt", return_value=object()),
    ):
        writer = ChangeWriter(
            attempt_id="attempt-change-a",
            claim_id="claim-change-a",
            actor_id="builder",
            process_id="process-change-a",
            claimed_at="2026-08-04T00:00:00Z",
            job_id=1,
            kind="build",
        )
        coordinator.acquire("change-a", writer)
        writer_row = application.list_retained_change_worktrees()[0]
        assert writer_row.cleanup_blocked_reason is DeliveryRetainedWorktreeCleanupBlockReason.ACTIVE_WRITER

    released = coordinator.release("change-a", "claim-change-a")
    assert released.writer is None
    with coordinator.publication_lock("change-a") as lock:
        coordinator.reserve_publication(
            "change-a",
            PublicationLease(
                operation_id="publication-change-a",
                owner_id="owner-change-a",
                expires_at="2026-08-04T00:05:00Z",
            ),
            lock,
            now="2026-08-04T00:00:00Z",
        )
    with (
        patch.object(runtime, "change_stage", return_value=DeliveryChangeStage.COMPLETED),
        patch.object(runtime, "completion_receipt", return_value=object()),
    ):
        lease_row = application.list_retained_change_worktrees()[0]

    assert lease_row.cleanup_blocked_reason is DeliveryRetainedWorktreeCleanupBlockReason.ACTIVE_PUBLICATION_LEASE


def test_retained_inventory_reports_orphans_nonterminal_and_worktree_attention(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.PLANNING,
            "change-b": DeliveryStage.COMPLETED,
            "change-c": DeliveryStage.PLANNING,
        },
    )
    shutil.rmtree(state_root / "changes/change-a")
    attention_coordination = application._workspace_manager.show("change-b")
    _git(
        application._workspace_manager.repository,
        "worktree",
        "remove",
        "--force",
        str(attention_coordination.worktree_path),
    )
    runtime = runtimes["change-b"]
    with (
        patch.object(runtime, "change_stage", return_value=DeliveryChangeStage.COMPLETED),
        patch.object(runtime, "completion_receipt", return_value=object()),
    ):
        rows = application.list_retained_change_worktrees()

    by_id = {row.change_id: row for row in rows}
    assert by_id["change-a"].orphan is True
    assert by_id["change-a"].cleanup_blocked_reason is DeliveryRetainedWorktreeCleanupBlockReason.ORPHAN
    assert by_id["change-b"].orphan is False
    assert by_id["change-b"].cleanup_blocked_reason is DeliveryRetainedWorktreeCleanupBlockReason.WORKTREE_ATTENTION
    assert ChangeWorktreeAttentionCode.WORKTREE_MISSING in by_id["change-b"].attention
    assert by_id["change-c"].cleanup_blocked_reason is DeliveryRetainedWorktreeCleanupBlockReason.NONTERMINAL


def test_portfolio_operating_view_recommends_creation_when_no_work_exists(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(tmp_path, {})

    view = application.portfolio_operating_view()

    assert view.unfinished_change_count == 0
    assert tuple(item.kind.value for item in view.guidance) == ("create-change",)


def test_portfolio_operating_view_recommends_resuming_unadmitted_design(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(tmp_path, {})
    application.create_design_session("draft-change", b"intent\n", b"design\n")

    view = application.portfolio_operating_view()

    assert view.unfinished_change_count == 0
    assert view.statuses[0].change_id == "draft-change"
    assert view.statuses[0].admission.value == "unadmitted"
    assert view.statuses[0].stage == DeliveryChangeStage.DESIGN
    assert view.statuses[0].actionable_runtime is False
    assert view.statuses[0].diagnostic_code is None
    assert view.statuses[0].diagnostic_detail is None
    assert view.draft_design_change_ids == ("draft-change",)
    assert tuple(item.kind.value for item in view.guidance) == ("resume-design",)


def test_portfolio_reader_reconciles_admitted_change_after_warm_start(tmp_path: Path) -> None:
    reader, _reader_runtimes, _reader_coordinator, state_root = _portfolio(tmp_path, {})
    writer, _writer_coordinator, _writer_manager = _reopen_portfolio(tmp_path, state_root, {})
    intent = b"""# Admitted Delivery

```yaml target-contract
kind: decision
id: DEC-001
origin: approved
basis: fixture approval
statement: Fixture decision.
```

```yaml target-contract
kind: commitment
id: COM-001
class: agreed-path
decisions: [DEC-001]
statement: Preserve source-bound admission.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Observe admission
promise: Make persisted admission observable.
acceptance: ["AC-001: Admission is observable."]
commitments: [COM-001]
dependencies: []
```
"""
    writer.create_design_session("admitted-change", intent, b"# Architecture\n")
    admitted = writer.admit_delivery_change(
        DeliveryAdmissionRequest(
            change_id="admitted-change",
            expected_package_id=_approved_package_id(writer, "admitted-change"),
            active_claim_ids=(),
        )
    )

    delivery_root = state_root / "changes" / "admitted-change"
    persisted_frontier = DeliveryFrontier.model_validate_json(
        (delivery_root / "frontier.json").read_bytes(), strict=True
    )
    persisted_receipt = json.loads((delivery_root / "admission.json").read_bytes())
    assert persisted_frontier == admitted.frontier
    assert persisted_receipt["receipt_id"] == admitted.receipt.receipt_id

    view = reader.portfolio_read_view()

    assert tuple(group.change_id for group in view.groups) == ("admitted-change",)
    assert tuple(item.work_item_id for item in view.groups[0].items) == (
        *tuple(outcome.outcome_id for outcome in admitted.contract.outcomes),
        "admitted-change",
    )
    assert view.groups[0].outcome_total == len(admitted.contract.outcomes)
    assert view.groups[0].outcome_completed == 0
    assert view.operating.unfinished_change_count == 1
    assert view.operating.statuses[0].change_id == "admitted-change"
    assert view.operating.statuses[0].admission.value == "admitted"
    assert view.operating.statuses[0].stage == DeliveryChangeStage.BUILDING
    assert view.operating.statuses[0].actionable_runtime is True
    assert view.operating.statuses[0].diagnostic_code is None
    assert view.groups[0].items[0].progress.label == "Task plan not published"
    assert view.operating.draft_design_change_ids == ()
    assert view.operating.design_required_change_ids == ()
    assert tuple(item.kind.value for item in view.operating.guidance) == ("start-orchestration",)


def test_warm_reader_reconciles_change_admitted_by_second_application(tmp_path: Path) -> None:
    reader, _reader_runtimes, _reader_coordinator, state_root = _portfolio(tmp_path, {})
    reader.portfolio_read_view()
    writer, writer_coordinator, writer_manager = _reopen_portfolio(tmp_path, state_root, {})
    intent = b"""# Admitted Delivery

```yaml target-contract
kind: decision
id: DEC-001
origin: approved
basis: fixture approval
statement: Fixture decision.
```

```yaml target-contract
kind: commitment
id: COM-001
class: agreed-path
decisions: [DEC-001]
statement: Preserve source-bound admission.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Observe admission
promise: Make persisted admission observable.
acceptance: ["AC-001: Admission is observable."]
commitments: [COM-001]
dependencies: []
```
"""
    writer.create_design_session("late-change", intent, b"# Architecture\n")
    admitted = writer.admit_delivery_change(
        DeliveryAdmissionRequest(
            change_id="late-change",
            expected_package_id=_approved_package_id(writer, "late-change"),
            active_claim_ids=(),
        )
    )
    exact_head = writer_coordinator.show("late-change").last_reviewed_commit
    _runtime(state_root, admitted.contract, writer_manager, DeliveryStage.COMPLETED, exact_head)
    finalization = writer.finalize_change("late-change", _finalization_request("late-change", exact_head))
    writer_runtime = writer._runtimes["late-change"]
    writer_runtime.record_publication_identity(
        DeliveryChangePublicationIdentity(
            change_id="late-change",
            repository="example/project",
            number=7,
            node_id="PR_node_7",
            head_sha=exact_head,
        )
    )
    ready_payload = {
        "schema_version": 1,
        "operation_id": "ready-late-change",
        "change_id": "late-change",
        "finalization_id": finalization.finalization_id,
        "repository": "example/project",
        "number": 7,
        "node_id": "PR_node_7",
        "head_sha": exact_head,
        "draft": False,
        "observed_at": datetime(2026, 8, 11, 14, tzinfo=UTC),
        "provider_evidence_digest": "5" * 64,
    }
    writer_runtime.mark_awaiting_merge(
        PullRequestReadyReceipt(
            receipt_id=_receipt_id({**ready_payload, "observed_at": "2026-08-11T14:00:00Z"}),
            **ready_payload,
        )
    )

    outcomes = reader.reconcile_awaiting_acceptance()

    assert len(outcomes) == 1
    assert outcomes[0].change_id == "late-change"
    assert outcomes[0].status.value == "provider-unavailable"


def test_health_reconciliation_does_not_race_shared_runtime_admission(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    application.create_design_session(
        "change-b",
        b"""# change-b

```yaml target-contract
kind: commitment
id: COM-001
class: agreed-path
decisions: [DEC-001]
statement: Preserve concurrent runtime reconciliation.
```

```yaml target-contract
kind: decision
id: DEC-001
origin: approved
basis: fixture approval
statement: Fixture decision.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Reconcile concurrent admission
promise: Keep admitted runtime state available.
acceptance: ["AC-001: Concurrent health remains available."]
commitments: [COM-001]
dependencies: []
```
""",
        b"# Architecture\n",
    )
    admission_persisted = Event()
    allow_admission = Event()
    health_reconciling = Event()
    allow_health = Event()
    observed_lock = _ObservedLock()
    application._runtime_reconciliation_lock = observed_lock
    original_admit = application._authority_registry.admit
    original_reconcile = application._reconcile_existing_runtime

    def blocking_admit(request):
        result = original_admit(request)
        admission_persisted.set()
        assert allow_admission.wait(2)
        return result

    def blocking_reconcile(runtime, observation, *, initial_reconciliation):
        if not health_reconciling.is_set():
            health_reconciling.set()
            assert allow_health.wait(2)
        return original_reconcile(
            runtime,
            observation,
            initial_reconciliation=initial_reconciliation,
        )

    request = DeliveryAdmissionRequest(
        change_id="change-b",
        expected_package_id=_approved_package_id(application, "change-b"),
        active_claim_ids=(),
    )
    with (
        patch.object(application._authority_registry, "admit", side_effect=blocking_admit),
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        admitted = executor.submit(application.admit_delivery_change, request)
        assert admission_persisted.wait(2)
        with patch.object(application, "_reconcile_existing_runtime", side_effect=blocking_reconcile):
            health = executor.submit(application.delivery_health)
            assert health_reconciling.wait(2)
            observed_lock.observe_attempts.set()
            allow_admission.set()
            assert observed_lock.attempted.wait(2)
            assert observed_lock.acquired.wait(2)
            assert admitted.result(timeout=2).contract.change_id == "change-b"
            allow_health.set()
            assert health.result(timeout=2).status.value == "healthy"

    assert set(application._runtimes) == {"change-a", "change-b"}


def test_portfolio_reader_replaces_changed_runtime_without_active_claim(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    application.portfolio_read_view()
    previous_runtime = application._runtimes["change-a"]
    contract_path = state_root / "changes/change-a/contract.json"
    frontier_path = state_root / "changes/change-a/frontier.json"
    current_frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
    replacement = previous_runtime.contract.model_copy(update={"title": "Replacement authority \u00e9"})
    contract_path.write_bytes(_canonical(replacement))
    (state_root / "changes/change-a/admission.json").write_bytes(
        _canonical(
            _admission_receipt(
                replacement,
                current_frontier,
                _coordinator.show("change-a").last_reviewed_commit,
            )
        )
    )
    before = _file_bytes(state_root)

    view = application.portfolio_read_view()

    assert application._runtimes["change-a"] is not previous_runtime
    assert view.groups[0].title == "Replacement authority \u00e9"
    assert _file_bytes(state_root) == before


def test_portfolio_reader_defers_active_runtime_replacement_and_blocks_mutation(tmp_path: Path) -> None:
    application, _runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    application.acquire_frontier_work()
    previous_runtime = application._runtimes["change-a"]
    contract_path = state_root / "changes/change-a/contract.json"
    frontier_path = state_root / "changes/change-a/frontier.json"
    current_frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
    replacement = previous_runtime.contract.model_copy(update={"title": "Active replacement"})
    contract_path.write_bytes(_canonical(replacement))
    (state_root / "changes/change-a/admission.json").write_bytes(
        _canonical(_admission_receipt(replacement, current_frontier, coordinator.show("change-a").last_reviewed_commit))
    )

    view = application.portfolio_read_view()

    assert application._runtimes["change-a"] is previous_runtime
    assert view.groups == ()
    assert view.health.status.value == "attention"
    assert any(diagnostic.change_id == "change-a" for diagnostic in view.health.diagnostics)
    with pytest.raises(DeliveryRuntimeReconciliationError) as exc_info:
        _change_intent(
            application,
            "change-a",
            DeliveryChangeIntentKind.DEFER,
            "runtime replacement requires reconciliation",
            digest="0" * 64,
        )
    assert exc_info.value.code == "ERR_DELIVERY_RUNTIME_RECONCILIATION"
    assert exc_info.value.retry_safe is True


@pytest.mark.parametrize("mutation", ["malformed", "mid-write"])
def test_portfolio_reader_retains_prior_runtime_and_blocks_mutation_for_unavailable_entry(
    tmp_path: Path,
    mutation: str,
) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    application.portfolio_read_view()
    previous_runtime = application._runtimes["change-a"]
    frontier_path = state_root / "changes/change-a/frontier.json"
    if mutation == "malformed":
        frontier_path.write_bytes(b"not-json\n")
    else:
        frontier_path.unlink()
    before = _file_bytes(state_root)

    view = application.portfolio_read_view()

    assert application._runtimes["change-a"] is previous_runtime
    assert view.groups == ()
    assert view.health.status.value == "attention"
    assert any(diagnostic.change_id == "change-a" for diagnostic in view.health.diagnostics)
    assert view.operating.unfinished_change_count == 1
    assert view.operating.draft_design_change_ids == ()
    status = next(item for item in view.operating.statuses if item.change_id == "change-a")
    assert status.admission.value == "admitted"
    assert status.actionable_runtime is False
    assert status.diagnostic_code == "runtime_unavailable"
    assert status.diagnostic_detail is not None
    assert len(status.diagnostic_detail) <= 240
    assert application._discovered_changes["change-a"].diagnostic_code == "runtime_unavailable"
    assert any(diagnostic.change_id == "change-a" for diagnostic in view.health.diagnostics)
    with pytest.raises(DeliveryRuntimeReconciliationError) as exc_info:
        _change_intent(
            application, "change-a", DeliveryChangeIntentKind.DEFER, "runtime entry requires retry", digest="0" * 64
        )
    assert exc_info.value.retry_safe is True
    assert _file_bytes(state_root) == before


def test_portfolio_operating_view_counts_design_reentry_as_intervention(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.DESIGN},
    )

    view = application.portfolio_operating_view()

    assert tuple(item.item_key for item in view.interventions) == ("outcome:OUT-001",)
    assert view.statuses[0].admission.value == "admitted"
    assert view.statuses[0].stage == DeliveryChangeStage.DESIGN
    assert view.statuses[0].actionable_runtime is True
    assert view.design_required_change_ids == ("change-a",)
    assert view.draft_design_change_ids == ()
    assert tuple(item.kind.value for item in view.guidance) == ("intervene", "resume-design")


def test_portfolio_operating_view_recommends_orchestration_for_unclaimed_work(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING},
    )

    view = application.portfolio_operating_view()

    assert len(view.queued_for_orchestration) == 2
    assert tuple(item.kind.value for item in view.guidance) == ("start-orchestration",)


def test_portfolio_claim_suppresses_second_orchestration_recommendation(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING},
        execution_capacity=1,
    )
    acquired = application.acquire_frontier_work()
    assert len(acquired.launch_packages) == 1

    view = application.portfolio_operating_view()

    assert len(view.claimed) == 1
    assert len(view.queued_for_orchestration) == 1
    assert tuple(item.kind.value for item in view.guidance) == ("work-underway",)


def test_portfolio_keeps_deferred_change_visible_without_orchestration_queue(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    _change_intent(application, "change-a", DeliveryChangeIntentKind.DEFER, "wait for user review")

    view = application.portfolio_read_view()

    assert tuple(group.lifecycle.value for group in view.groups) == ("deferred",)
    assert view.operating.unfinished_change_count == 1
    assert view.operating.queued_for_orchestration == ()
    assert tuple(item.kind.value for item in view.operating.guidance) == ("intervene",)


def test_portfolio_projects_change_checkpoint_publication_state(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )

    state = application.show_change_checkpoint_publication("change-a")

    assert state == runtimes["change-a"].checkpoint_publication_state()
    assert state.change_id == "change-a"
    assert state.published_head is None
    assert state.pending_checkpoint is None


def test_portfolio_projects_current_pull_request_mergeability(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    application.finalize_change("change-a", _finalization_request("change-a", head))
    publication = DeliveryChangePublicationIdentity(
        change_id="change-a",
        repository="example/project",
        number=7,
        node_id="PR_7",
        head_sha=head,
    )
    runtimes["change-a"].record_publication_identity(publication)
    frontier_path = state_root / "changes/change-a/frontier.json"
    frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
    frontier_path.write_bytes(
        _canonical(frontier.model_copy(update={"published_head": head, "pending_checkpoint": None}))
    )
    observation = _publication_observation("change-a", head, mergeable=False, merge_state_status="dirty")
    publisher = Mock()
    publisher.observe_pull_request.return_value = observation
    application._draft_pull_request_publisher = publisher

    group = application.list_work_item_groups()[0]
    card = group.items[-1]
    detail = application.show_work_item_view("change-a", "publication")

    assert card.action.command == "/resolve-target-conflict change-a"
    assert detail.publication is not None
    assert detail.publication.mergeable is False
    assert detail.publication.merge_state_status == "dirty"
    publisher.observe_pull_request.assert_called_once_with(ObserveChangePublicationPullRequest(change_id="change-a"))


def test_reconcile_first_checkpoint_publishes_branch_creates_pr_and_drains(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(
            DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-001",
            ),
        ),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(request.published_head)
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    result = application.reconcile_change_checkpoint("change-a")
    replayed = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    snapshot = coordinator.show("change-a").design_package_snapshot
    assert snapshot is not None
    assert result.state.published_head == snapshot.snapshot_head
    assert result.state.pending_checkpoint is None
    assert replayed.reconciled
    assert replayed.attempted_head is None
    assert branch_publisher.publish.call_count == 1
    assert pull_request_publisher.publish.call_count == 1
    assert pull_request_publisher.update_generated_summary.call_count == 1
    request = pull_request_publisher.publish.call_args.args[0]
    assert request.published_head == snapshot.snapshot_head
    assert "## Goal" in request.generated_summary
    assert "## Intent" in request.generated_summary
    assert "## Promised Outcomes" in request.generated_summary
    assert "Promised result: Return one bounded launch package." in request.generated_summary
    assert "Outcome `OUT-001` verified" in request.generated_summary
    assert "Outcomes complete: 1 of 1" in request.generated_summary
    history = runtimes["change-a"].publication_history()
    assert history is not None
    assert history.current.number == 7
    assert history.current.head_sha == snapshot.snapshot_head


def test_background_checkpoint_failure_persists_error_and_waits_before_retry(tmp_path: Path) -> None:
    current = [datetime(2026, 8, 4, tzinfo=UTC)]

    def clock() -> str:
        return current[0].isoformat()

    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        clock=clock,
    )
    head = coordinator.show("change-a").last_reviewed_commit
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(
            DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME, outcome_id="OUT-001"),
        ),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE,
        "publish_change_branch",
        "Provider unavailable while publishing the Change branch.",
        retry_safe=True,
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = Mock()

    first = application.reconcile_pending_checkpoints()

    assert len(first) == 1
    assert first[0].error_code == PublicationProviderFailureCode.UNAVAILABLE
    recorded = first[0].state.pending_checkpoint
    assert recorded is not None
    assert recorded.attempt_count == 1
    assert recorded.last_attempted_at == current[0]
    assert recorded.last_error_detail == "Provider unavailable while publishing the Change branch."
    assert application.reconcile_pending_checkpoints() == ()
    manual = application.reconcile_change_checkpoint("change-a")
    assert manual.reconciled is False
    assert manual.error_code == PublicationProviderFailureCode.UNAVAILABLE
    assert branch_publisher.publish.call_count == 1

    current[0] += timedelta(seconds=5)
    second = application.reconcile_pending_checkpoints()

    assert len(second) == 1
    assert second[0].state.pending_checkpoint is not None
    assert second[0].state.pending_checkpoint.attempt_count == 2
    assert branch_publisher.publish.call_count == 2


def test_background_checkpoint_selection_excludes_review_required_merge(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    target_sync = ChangeTargetSyncReceipt.create(
        operation_id="review-required-sync",
        change_id="change-a",
        integration_target="main",
        expected_target="2" * 40,
        target_head="2" * 40,
        change_head_before=head,
        merged_head=head,
        merge_commit=False,
        review_required=True,
    )
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.EXPLICIT),),
    )
    path = state_root / "changes/change-a/frontier.json"
    frontier = DeliveryFrontier.model_validate_json(runtimes["change-a"].frontier_bytes(), strict=True)
    path.write_bytes(
        _canonical(frontier.model_copy(update={"target_sync_receipt": target_sync, "pending_checkpoint": pending}))
    )
    branch_publisher = Mock()
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = Mock()

    result = application.reconcile_pending_checkpoints()

    assert result == ()
    branch_publisher.publish.assert_not_called()


def test_reconcile_checkpoint_reports_bounded_escaped_automation_paths(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(request.published_head)
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher
    long_path = ".github/workflows/" + ("x" * 300) + ".yml"

    with patch.object(
        application._workspace_manager,
        "repository_automation_paths",
        return_value=(".github/workflows/<run>`\nname.yml", long_path),
    ):
        result = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    create_request = pull_request_publisher.publish.call_args.args[0]
    update_request = pull_request_publisher.update_generated_summary.call_args.args[0]
    summary = create_request.generated_summary
    assert summary == update_request.generated_summary
    assert "### Repository automation changed" in summary
    assert "<code>.github/workflows/&lt;run&gt;&#96;\\nname.yml</code>" in summary
    assert "x" * 300 not in summary
    assert summary.count("<code>") == 2


def test_reconcile_checkpoint_retains_attention_when_publication_baseline_is_unknown(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    coordination = coordinator.show("change-a")
    payload = coordination.model_dump(mode="json")
    payload.pop("publication_base_head")
    (state_root / "coordination/changes/change-a.json").write_text(json.dumps(payload), encoding="utf-8")
    branch_publisher = Mock()
    pull_request_publisher = Mock()
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    with pytest.raises(PublicationBaselineUnavailableError):
        application.reconcile_change_checkpoint("change-a")

    assert branch_publisher.publish.call_count == 0
    assert pull_request_publisher.publish.call_count == 0
    assert pull_request_publisher.update_generated_summary.call_count == 0
    retained = runtimes["change-a"].change_disposition()
    assert retained is not None
    assert retained.kind.value == "publication-attention"
    retained = runtimes["change-a"].checkpoint_publication_state().pending_checkpoint
    assert retained is not None
    assert retained.head == pending.head
    assert retained.triggers == pending.triggers
    assert retained.attempt_count == 1
    assert retained.last_error_code == "ERR_PUBLICATION_BASELINE_UNAVAILABLE"
    assert retained.last_error_detail is not None


def test_reconcile_checkpoint_preserves_baseline_error_when_attention_conflicts(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    coordination = coordinator.show("change-a")
    payload = coordination.model_dump(mode="json")
    payload.pop("publication_base_head")
    (state_root / "coordination/changes/change-a.json").write_text(json.dumps(payload), encoding="utf-8")
    runtimes["change-a"].capture_publication_attention(
        datetime(2026, 8, 12, tzinfo=UTC),
        ("existing-publication-attention",),
    )
    branch_publisher = Mock()
    pull_request_publisher = Mock()
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    with pytest.raises(PublicationBaselineUnavailableError):
        application.reconcile_change_checkpoint("change-a")

    assert branch_publisher.publish.call_count == 0
    assert pull_request_publisher.publish.call_count == 0
    retained = runtimes["change-a"].change_disposition()
    assert retained is not None
    assert retained.diagnostics == ("existing-publication-attention",)


def test_recover_publication_baseline_requires_confirmation_and_preserves_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    payload = coordination.model_dump(mode="json")
    payload.pop("publication_base_head")
    (state_root / "coordination/changes/change-a.json").write_text(json.dumps(payload), encoding="utf-8")
    runtime = runtimes["change-a"]
    attention = runtime.capture_publication_attention(
        datetime(2026, 8, 12, tzinfo=UTC),
        ("publication-baseline-unavailable",),
    )

    with pytest.raises(PortfolioApplicationError, match="explicit confirmation"):
        application.recover_publication_baseline(
            "change-a",
            coordination.last_reviewed_commit,
            coordination.target_head,
            "recover-baseline",
        )

    receipt = application.recover_publication_baseline(
        "change-a",
        coordination.last_reviewed_commit,
        coordination.target_head,
        "recover-baseline",
        confirmed_recovery=True,
    )

    assert receipt.change_id == "change-a"
    assert coordinator.show("change-a").publication_base_head == coordination.target_head
    assert runtime.change_disposition() == attention


def test_supersede_current_publication_preflights_baseline_before_provider_history(tmp_path: Path) -> None:
    application, _runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    payload = coordination.model_dump(mode="json")
    payload.pop("publication_base_head")
    (state_root / "coordination/changes/change-a.json").write_text(json.dumps(payload), encoding="utf-8")
    provider = Mock()
    application._draft_pull_request_publisher = provider

    with pytest.raises(PublicationBaselineUnavailableError):
        application.supersede_current_publication("change-a", "supersede-current")

    provider.read_publication_history.assert_not_called()


def test_later_checkpoint_reports_cumulative_automation_paths(
    tmp_path: Path,
) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    workflow_directory = coordination.worktree_path / ".github/workflows"
    workflow_directory.mkdir(parents=True)
    first_head = _commit_reviewed_head(
        application,
        coordination,
        ".github/workflows/first.yml",
        "name: first\n",
        "first automation checkpoint",
    )
    first_pending = DeliveryPendingCheckpoint(
        head=first_head,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
    )
    _set_checkpoint(runtimes["change-a"], state_root, first_pending)
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(request.published_head)
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    application.reconcile_change_checkpoint("change-a")

    second_head = _commit_reviewed_head(
        application,
        coordination,
        ".github/workflows/second.yml",
        "name: second\n",
        "second automation checkpoint",
    )
    second_pending = DeliveryPendingCheckpoint(
        head=second_head,
        triggers=(
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-001",
            ),
        ),
    )
    first_snapshot = coordinator.show("change-a").design_package_snapshot
    assert first_snapshot is not None
    _set_checkpoint(runtimes["change-a"], state_root, second_pending, published_head=first_snapshot.snapshot_head)
    branch_publisher.publish.side_effect = None
    branch_publisher.publish.return_value = _branch_receipt(second_head, first_snapshot.snapshot_head)
    pull_request_publisher.update_generated_summary.return_value = _summary_receipt(second_head)

    result = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    summary = pull_request_publisher.update_generated_summary.call_args.args[0].generated_summary
    assert "<code>.github/workflows/first.yml</code>" in summary
    assert "<code>.github/workflows/second.yml</code>" in summary


def test_supersede_publication_binds_git_provider_and_runtime_history(  # noqa: PLR0915 - scenario covers provider history.
    tmp_path: Path,
) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    runtime = runtimes["change-a"]
    coordination = coordinator.show("change-a")
    predecessor_head = coordination.last_reviewed_commit
    predecessor = _draft_receipt(predecessor_head)
    predecessor_identity = DeliveryChangePublicationIdentity(
        change_id="change-a",
        repository=predecessor.repository,
        number=predecessor.number,
        node_id=predecessor.node_id,
        head_sha=predecessor.head_sha,
    )
    runtime.record_publication_identity(predecessor_identity)
    runtime.capture_publication_attention(
        datetime(2026, 8, 12, tzinfo=UTC),
        ("published history requires correction",),
        publication_identity=predecessor_identity,
    )

    (coordination.worktree_path / ".github/workflows").mkdir(parents=True)
    (coordination.worktree_path / ".github/workflows/successor.yml").write_text("successor\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", ".github/workflows/successor.yml")
    _git(coordination.worktree_path, "commit", "-m", "successor publication")
    superseding_head = _git(coordination.worktree_path, "rev-parse", "HEAD")
    application._workspace_manager.record_reviewed("change-a", superseding_head)

    operation_id = "supersede-change-a"
    successor_branch = "owlbear/change/change-a+s1"
    git_receipt = ChangeBranchSupersessionReceipt(
        receipt_id="5" * 64,
        operation_id=operation_id,
        change_id="change-a",
        remote="origin",
        predecessor_branch=predecessor.head_branch,
        predecessor_head=predecessor.head_sha,
        successor_branch=successor_branch,
        superseding_head=superseding_head,
        target_branch="main",
    )
    successor = _draft_receipt(
        superseding_head,
        number=8,
        operation_id=operation_id,
        head_branch=successor_branch,
    )
    provider_payload = {
        "schema_version": 1,
        "operation_id": operation_id,
        "change_id": "change-a",
        "predecessor_receipt_id": predecessor.receipt_id,
        "predecessor_branch": predecessor.head_branch,
        "predecessor_head": predecessor.head_sha,
        "successor_receipt_id": successor.receipt_id,
        "successor_branch": successor.head_branch,
        "superseding_head": successor.head_sha,
        "repository": successor.repository,
        "successor_number": successor.number,
        "successor_node_id": successor.node_id,
        "base_branch": successor.base_branch,
        "provider_evidence_digest": successor.provider_evidence_digest,
        "predecessor_publication": predecessor.model_dump(mode="json"),
        "successor_publication": successor.model_dump(mode="json"),
    }
    provider_receipt = DraftPullRequestSupersessionReceipt(
        receipt_id=_receipt_id(provider_payload),
        **provider_payload,
    )
    initial_provider_history = _draft_history((predecessor,), (None,))
    successor_provider_history = _draft_history((predecessor, successor), (None, predecessor.receipt_id))
    branch_publisher = Mock()
    branch_publisher.supersede.return_value = git_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.target_branch = "main"
    pull_request_publisher.read_publication_history.side_effect = (
        initial_provider_history,
        successor_provider_history,
        successor_provider_history,
    )
    pull_request_publisher.supersede.return_value = provider_receipt
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    receipt = application.supersede_publication("change-a", predecessor.receipt_id, operation_id)
    replayed = application.supersede_publication("change-a", predecessor.receipt_id, operation_id)

    assert receipt == replayed
    assert (receipt.git_supersession, receipt.provider_supersession) == (git_receipt, provider_receipt)
    assert receipt.publication_history.current.number == 8
    assert len(receipt.publication_history.publications) == 2
    assert runtimes["change-a"].publication_history() == receipt.publication_history
    assert branch_publisher.supersede.call_count == 2
    assert pull_request_publisher.supersede.call_count == 2
    git_request = branch_publisher.supersede.call_args.args[0]
    assert git_request.expected_published_branch == predecessor.head_branch
    assert git_request.expected_published_head == predecessor.head_sha
    assert git_request.superseding_head == superseding_head
    provider_request = pull_request_publisher.supersede.call_args.args[0]
    assert provider_request.expected_predecessor_receipt_id == predecessor.receipt_id
    assert provider_request.successor_branch == successor_branch
    assert provider_request.superseding_head == superseding_head
    assert "## Goal" in provider_request.generated_summary
    assert "## Intent" in provider_request.generated_summary
    assert "## Promised Outcomes" in provider_request.generated_summary
    assert (
        f"Publication supersedes provider publication `{predecessor.receipt_id}`" in provider_request.generated_summary
    )
    assert "### Repository automation changed" in provider_request.generated_summary
    assert "<code>.github/workflows/successor.yml</code>" in provider_request.generated_summary

    _commit_reviewed_head(application, coordination, "later.txt", "later\n", "later reviewed head")

    with pytest.raises(PortfolioApplicationError, match="replay requires the stored successor head"):
        application.supersede_publication("change-a", predecessor.receipt_id, operation_id)

    assert (branch_publisher.supersede.call_count, pull_request_publisher.supersede.call_count) == (2, 2)


def test_supersede_current_publication_resolves_provider_receipt_before_delegating(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    predecessor = _draft_receipt("3" * 40)
    provider = Mock()
    provider.read_publication_history.return_value = _draft_history((predecessor,), (None,))
    application._draft_pull_request_publisher = provider
    expected = object()

    with patch.object(application, "supersede_publication", return_value=expected) as supersede:
        result = application.supersede_current_publication("change-a", "supersede-current")

    assert result is expected
    provider.read_publication_history.assert_called_once_with(ReadChangePublicationHistory(change_id="change-a"))
    supersede.assert_called_once_with("change-a", predecessor.receipt_id, "supersede-current")


def test_supersede_publication_requires_attention_bound_to_runtime_publication(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    runtime = runtimes["change-a"]
    predecessor_head = coordinator.show("change-a").last_reviewed_commit
    predecessor = _draft_receipt(predecessor_head)
    runtime.record_publication_identity(
        DeliveryChangePublicationIdentity(
            change_id="change-a",
            repository=predecessor.repository,
            number=predecessor.number,
            node_id=predecessor.node_id,
            head_sha=predecessor.head_sha,
        )
    )
    runtime.capture_publication_attention(
        datetime(2026, 8, 12, tzinfo=UTC),
        ("published history requires correction",),
    )
    branch_publisher = Mock()
    pull_request_publisher = Mock()
    pull_request_publisher.target_branch = "main"
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    with pytest.raises(PortfolioApplicationError, match="attention does not retain"):
        application.supersede_publication("change-a", predecessor.receipt_id, "supersede-change-a")

    branch_publisher.supersede.assert_not_called()
    pull_request_publisher.read_publication_history.assert_not_called()
    assert runtime.publication_history() is not None
    assert len(runtime.publication_history().publications) == 1


def test_supersede_publication_preserves_finalization_when_provider_fails(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    runtime = runtimes["change-a"]
    predecessor_head = coordinator.show("change-a").last_reviewed_commit
    finalization = application.finalize_change("change-a", _finalization_request("change-a", predecessor_head))
    predecessor = _draft_receipt(predecessor_head)
    predecessor_identity = DeliveryChangePublicationIdentity(
        change_id="change-a",
        repository=predecessor.repository,
        number=predecessor.number,
        node_id=predecessor.node_id,
        head_sha=predecessor.head_sha,
    )
    runtime.record_publication_identity(predecessor_identity)
    runtime.capture_publication_attention(
        datetime(2026, 8, 12, tzinfo=UTC),
        ("published history requires correction",),
        publication_identity=predecessor_identity,
    )
    coordination = coordinator.show("change-a")
    superseding_head = _commit_reviewed_head(
        application,
        coordination,
        "provider-failure.txt",
        "provider failure\n",
        "provider failure successor",
    )
    operation_id = "supersede-provider-failure"
    branch_publisher = Mock()
    branch_publisher.supersede.return_value = ChangeBranchSupersessionReceipt(
        receipt_id="5" * 64,
        operation_id=operation_id,
        change_id="change-a",
        remote="origin",
        predecessor_branch=predecessor.head_branch,
        predecessor_head=predecessor.head_sha,
        successor_branch="owlbear/change/change-a+s1",
        superseding_head=superseding_head,
        target_branch="main",
    )
    pull_request_publisher = Mock()
    pull_request_publisher.target_branch = "main"
    pull_request_publisher.read_publication_history.return_value = _draft_history((predecessor,), (None,))
    pull_request_publisher.supersede.side_effect = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE,
        operation_id,
        "provider unavailable",
        retry_safe=True,
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    with pytest.raises(PublicationProviderError, match="provider unavailable"):
        application.supersede_publication("change-a", predecessor.receipt_id, operation_id)

    assert runtime.finalization() == finalization
    assert runtime.finalization_invalidation() is None
    assert runtime.publication_history() is not None
    assert runtime.publication_history().current == predecessor_identity


def test_completed_outcome_repair_replay_does_not_republish_acknowledged_state(tmp_path: Path) -> None:
    application = PortfolioApplication.__new__(PortfolioApplication)
    runtime = Mock()
    runtime.bindings.return_value = (Mock(outcome_id="OUT-001"),)
    runtime.has_completed_outcome_repair.return_value = True
    runtime.prepare_completed_outcome_repair.return_value = sentinel.binding
    runtime.pending_state_publication.return_value = None
    application._coordinator = Mock()
    application._coordinator.acquisition_lock.return_value = nullcontext()
    application._checkpoint_lock_root = lambda _change_id: tmp_path / "checkpoint-lock"
    application._runtime = Mock(return_value=runtime)
    application._publish_delivery_state = Mock()
    request = Mock(outcome_id="OUT-001", attempt_id="repair-attempt")

    result = application.repair_completed_outcome("change-a", request)

    assert result is sentinel.binding
    application._publish_delivery_state.assert_not_called()


def test_completed_outcome_repair_requires_pending_retry_reservation() -> None:
    application = PortfolioApplication.__new__(PortfolioApplication)
    application._clock = lambda: "2026-08-12T00:00:00Z"
    episode_id = "a" * 64
    episode = Mock(
        episode_id=episode_id,
        attempt_ids=("failed-finalize",),
        failure_class=RetryFailureClass.MECHANICAL,
        outcome_ids=(digest(b"failed-finalize:failed"),),
    )
    pending = Mock(
        attempt_id="repair-attempt",
        episode_id=episode_id,
        kind="repair",
        failure_class=RetryFailureClass.MECHANICAL,
    )
    ledger = Mock()
    ledger.read.return_value = Mock(episodes=(episode,))
    ledger.pending_attempts.return_value = (pending,)
    runtime = Mock()
    runtime.retry_ledger.return_value = ledger
    request = PrepareCompletedOutcomeRepair(
        outcome_id="OUT-001",
        owning_task_id="task-001",
        episode_id=episode_id,
        attempt_id="repair-attempt",
        defect_code="proof-failure",
        finding_boundary="proof-procedure",
        original_action_id="failed-finalize",
        preservation_id="b" * 64,
        expected_frontier_digest="c" * 64,
    )

    application._validate_completed_outcome_repair_retry(runtime, request)

    pending.kind = "original"
    with pytest.raises(PortfolioApplicationError, match="pending mechanical retry reservation"):
        application._validate_completed_outcome_repair_retry(runtime, request)


def test_proof_procedure_repair_rejects_diagnostic_without_owner_observation() -> None:
    application = PortfolioApplication.__new__(PortfolioApplication)
    application._proof_attempt_store_factory = None
    report = Mock()

    with pytest.raises(PortfolioApplicationError, match="owner observation is unavailable"):
        application._require_owner_proof_attempt("change-a", report)


def test_proof_procedure_repair_accepts_only_exact_owner_attempt(tmp_path: Path) -> None:
    procedure = MaintainedProofProcedure(procedure_id="maintained-check", registration_digest="e" * 64)
    basis = ProofAttemptBasis(
        expected_contract_digest="c" * 64,
        expected_frontier_digest="d" * 64,
        expected_change_head="e" * 40,
        expected_reviewed_head="f" * 40,
    )
    observation = ProofAttemptObservation(
        proof_fingerprint_before="a" * 64,
        proof_fingerprint_after="b" * 64,
        paths=("generated.txt",),
        observed_at=datetime.now(UTC),
    )
    store = ProofAttemptStore(tmp_path, "change-a", (procedure,))
    store.record("attempt-1", procedure, basis, lambda: observation)

    def report_for(**updates):
        request = Mock(
            change_id="change-a",
            attempt_key="attempt-1",
            procedure_id=procedure.procedure_id,
            expected_contract_digest=basis.expected_contract_digest,
            expected_frontier_digest=basis.expected_frontier_digest,
            expected_change_head=basis.expected_change_head,
            expected_reviewed_head=basis.expected_reviewed_head,
            proof_fingerprint_before=observation.proof_fingerprint_before,
            proof_fingerprint_after=observation.proof_fingerprint_after,
            paths=observation.paths,
        )
        for key, value in updates.items():
            setattr(request, key, value)
        return Mock(request=request)

    application = PortfolioApplication.__new__(PortfolioApplication)
    application._proof_attempt_store_factory = lambda _change_id: store
    with pytest.raises(PortfolioApplicationError, match="owner-observed proof attempt"):
        application._require_owner_proof_attempt("change-b", report_for())
    with pytest.raises(PortfolioApplicationError, match="owner-observed proof attempt"):
        application._require_owner_proof_attempt("change-a", report_for(expected_frontier_digest="0" * 64))
    application._require_owner_proof_attempt("change-a", report_for())


def test_reconcile_checkpoint_rejects_summary_for_a_different_pull_request(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(request.published_head)
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head,
        number=8,
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    with pytest.raises(DeliveryRuntimeConflictError, match="does not match the current publication"):
        application.reconcile_change_checkpoint("change-a")

    history = runtimes["change-a"].publication_history()
    assert history is not None
    assert history.current.number == 7
    assert runtimes["change-a"].checkpoint_publication_state().pending_checkpoint is not None


def test_reconcile_derives_bounded_provider_text_from_authored_titles(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    runtime = runtimes["change-a"]
    head = coordinator.show("change-a").last_reviewed_commit
    runtime._contract = runtime.contract.model_copy(
        update={
            "title": f"  {'Title ' * 40}\x00{'Title ' * 40}  ",
            "outcomes": (
                runtime.contract.outcomes[0].model_copy(
                    update={"title": "Authored <!-- owlbear-change:forged --> title"}
                ),
            ),
        }
    )
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(
            DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-001",
            ),
        ),
    )
    _set_checkpoint(runtime, state_root, pending)
    contract_path = state_root / "changes/change-a/contract.json"
    contract_path.write_bytes(_canonical(runtime.contract))
    current_frontier = DeliveryFrontier.model_validate_json(
        (state_root / "changes/change-a/frontier.json").read_bytes(), strict=True
    )
    (state_root / "changes/change-a/admission.json").write_bytes(
        _canonical(_admission_receipt(runtime.contract, current_frontier, head))
    )
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(request.published_head)
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    result = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    request = pull_request_publisher.publish.call_args.args[0]
    assert len(request.title) == 256
    assert not request.title.startswith(" ")
    assert "\x00" not in request.title
    assert "owlbear-change:forged" not in request.generated_summary
    assert "Outcome `OUT-001` verified" in request.generated_summary


def test_reconcile_later_checkpoint_updates_summary_from_prior_published_head(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    prior_head = "1" * 40
    head = "2" * 40
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-001",
            ),
        ),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending, published_head=prior_head)
    branch_publisher = Mock()
    branch_publisher.publish.return_value = _branch_receipt(head, prior_head)
    pull_request_publisher = Mock()
    pull_request_publisher.update_generated_summary.return_value = _summary_receipt(head)
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    with patch.object(application._workspace_manager, "repository_automation_paths", return_value=()):
        result = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    assert branch_publisher.publish.call_args.args[0].expected_remote_head == prior_head
    assert pull_request_publisher.publish.call_count == 0
    assert pull_request_publisher.update_generated_summary.call_args.args[0].published_head == head


def test_reconcile_checkpoint_retains_newer_head_after_first_pr_creation(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    newer_head = "f" * 40
    triggers = (
        DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),
        DeliveryCheckpointTrigger(
            kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
            outcome_id="OUT-001",
        ),
    )
    frontier_path = _set_checkpoint(
        runtimes["change-a"],
        state_root,
        DeliveryPendingCheckpoint(head=head, triggers=triggers),
    )
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head
    )

    def create_pull_request(request):
        current = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
        frontier_path.write_bytes(
            _canonical(
                current.model_copy(
                    update={"pending_checkpoint": DeliveryPendingCheckpoint(head=newer_head, triggers=triggers)}
                )
            )
        )
        return _draft_receipt(request.published_head)

    pull_request_publisher.publish.side_effect = create_pull_request
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    result = application.reconcile_change_checkpoint("change-a")

    assert not result.reconciled
    snapshot = coordinator.show("change-a").design_package_snapshot
    assert snapshot is not None
    assert result.state.published_head == snapshot.snapshot_head
    assert result.state.pending_checkpoint is not None
    assert result.state.pending_checkpoint.head == newer_head
    assert tuple(trigger.kind for trigger in result.state.pending_checkpoint.triggers) == (
        DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
    )


def test_reconcile_checkpoint_records_remote_head_after_local_invalidation(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    first_trigger = DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK)
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(
            first_trigger,
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-001",
            ),
        ),
    )
    frontier_path = _set_checkpoint(runtimes["change-a"], state_root, pending)
    branch_publisher = Mock()

    def publish_branch(request):
        current = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
        frontier_path.write_bytes(
            _canonical(
                current.model_copy(
                    update={
                        "pending_checkpoint": DeliveryPendingCheckpoint(
                            head=None,
                            triggers=(first_trigger,),
                        )
                    }
                )
            )
        )
        return _branch_receipt(request.expected_published_head)

    branch_publisher.publish.side_effect = publish_branch
    pull_request_publisher = Mock()
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    result = application.reconcile_change_checkpoint("change-a")

    assert not result.reconciled
    snapshot = coordinator.show("change-a").design_package_snapshot
    assert snapshot is not None
    assert result.state.published_head == snapshot.snapshot_head
    assert result.state.pending_checkpoint == DeliveryPendingCheckpoint(head=None, triggers=(first_trigger,))
    assert pull_request_publisher.publish.call_count == 0


def test_reconcile_published_head_stops_after_concurrent_invalidation(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    first_trigger = DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK)
    pending = DeliveryPendingCheckpoint(head=head, triggers=(first_trigger,))
    frontier_path = _set_checkpoint(runtimes["change-a"], state_root, pending, published_head=head)
    branch_publisher = Mock()

    def verify_branch(_request):
        current = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
        frontier_path.write_bytes(
            _canonical(
                current.model_copy(
                    update={
                        "pending_checkpoint": DeliveryPendingCheckpoint(
                            head=None,
                            triggers=(first_trigger,),
                        )
                    }
                )
            )
        )
        return _branch_receipt(head, head)

    branch_publisher.publish.side_effect = verify_branch
    pull_request_publisher = Mock()
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    result = application.reconcile_change_checkpoint("change-a")

    assert not result.reconciled
    assert result.state.published_head == head
    assert result.state.pending_checkpoint == DeliveryPendingCheckpoint(head=None, triggers=(first_trigger,))
    assert pull_request_publisher.publish.call_count == 0
    assert pull_request_publisher.update_generated_summary.call_count == 0


def test_reconcile_serializes_administrative_invalidation_through_provider_work(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(
            DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-001",
            ),
        ),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    preview = application.preview_administrative_move("change-a", "OUT-001", DeliveryStage.PLANNING)
    move = AdministrativeDeliveryMove(
        move_id="move-during-reconcile",
        outcome_id="OUT-001",
        target=DeliveryStage.PLANNING,
        reason="Invalidate the reviewed result.",
        expected_version=preview.snapshot_version,
    )
    branch_started = Event()
    allow_branch = Event()
    move_started = Event()
    branch_publisher = Mock()

    def publish_branch(request):
        branch_started.set()
        if not allow_branch.wait(timeout=5):
            message = "test branch publication remained blocked"
            raise TimeoutError(message)
        return _branch_receipt(request.expected_published_head)

    def move_change():
        move_started.set()
        return application.administrative_move("change-a", move)

    branch_publisher.publish.side_effect = publish_branch
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(request.published_head)
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    with ThreadPoolExecutor(max_workers=2) as executor:
        reconcile_future = executor.submit(application.reconcile_change_checkpoint, "change-a")
        assert branch_started.wait(timeout=5)
        move_future = executor.submit(move_change)
        assert move_started.wait(timeout=5)
        assert not move_future.done()
        allow_branch.set()
        reconciled = reconcile_future.result(timeout=5)
        with pytest.raises(DeliveryRuntimeConflictError, match="preview is stale"):
            move_future.result(timeout=5)

    assert reconciled.reconciled
    fresh_preview = application.preview_administrative_move("change-a", "OUT-001", DeliveryStage.PLANNING)
    moved = application.administrative_move(
        "change-a",
        move.model_copy(update={"expected_version": fresh_preview.snapshot_version}),
    )
    assert moved.invalidated_outcome_ids == ("OUT-001",)
    assert application.show_work_item("change-a", "OUT-001").projection.stage.value == "planning"


def test_reconcile_checkpoint_replays_pr_after_lost_local_acknowledgment(tmp_path: Path) -> None:
    current = [datetime(2026, 8, 4, tzinfo=UTC)]

    def clock() -> str:
        return current[0].isoformat()

    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        clock=clock,
    )
    head = coordinator.show("change-a").last_reviewed_commit
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(request.published_head)
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher
    runtime = runtimes["change-a"]

    with (
        patch.object(
            runtime,
            "acknowledge_checkpoint_publication",
            side_effect=DeliveryRuntimeConflictError("interrupted acknowledgment"),
        ),
        pytest.raises(DeliveryRuntimeConflictError, match="interrupted acknowledgment"),
    ):
        application.reconcile_change_checkpoint("change-a")

    snapshot = coordinator.show("change-a").design_package_snapshot
    assert snapshot is not None
    assert runtime.checkpoint_publication_state().published_head == snapshot.snapshot_head
    waiting = application.reconcile_change_checkpoint("change-a")
    assert not waiting.reconciled
    assert branch_publisher.publish.call_count == 1
    assert pull_request_publisher.publish.call_count == 1
    current[0] += timedelta(seconds=5)
    replayed = application.reconcile_change_checkpoint("change-a")

    assert replayed.reconciled
    assert replayed.state.pending_checkpoint is None
    assert branch_publisher.publish.call_count == 2
    assert pull_request_publisher.publish.call_count == 2
    assert pull_request_publisher.update_generated_summary.call_count == 2
    assert (
        pull_request_publisher.publish.call_args_list[0].args[0]
        == pull_request_publisher.publish.call_args_list[1].args[0]
    )


def test_reconcile_first_pr_recovers_at_newer_head_after_provider_failure(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    first_head = coordinator.show("change-a").last_reviewed_commit
    second_head = "f" * 40
    pending = DeliveryPendingCheckpoint(
        head=first_head,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    provider = Mock()
    provider.read_repository.return_value = PublicationRepository(
        repository="example/project",
        default_branch="main",
    )
    pull_requests: list[PublicationPullRequest] = []
    create_attempts = 0

    def find_pull_request(_request):
        return pull_requests[0] if pull_requests else None

    def create_pull_request(request):
        nonlocal create_attempts
        create_attempts += 1
        if create_attempts == 1:
            raise PublicationProviderError(
                PublicationProviderFailureCode.UNAVAILABLE,
                "create_draft_pull_request",
                "provider unavailable",
                retry_safe=True,
            )
        pull_request = PublicationPullRequest(
            repository=request.repository,
            number=7,
            node_id="PR_node_7",
            head_branch=request.head_branch,
            head_sha=request.head_sha,
            base_branch=request.base_branch,
            title=request.title,
            body=request.body,
            draft=True,
            state="open",
            merged=False,
        )
        pull_requests.append(pull_request)
        return pull_request

    provider.find_pull_request.side_effect = find_pull_request
    provider.create_draft_pull_request.side_effect = create_pull_request
    provider.read_pull_request.side_effect = lambda _repository, _number: pull_requests[0]
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = DraftPullRequestPublisher(
        provider,
        repository="example/project",
        target_branch="main",
        state_root=tmp_path / "pull-requests",
    )

    with (
        patch.object(application._workspace_manager, "repository_automation_paths", return_value=()),
        pytest.raises(PublicationProviderError) as exc_info,
    ):
        application.reconcile_change_checkpoint("change-a")

    assert exc_info.value.code is PublicationProviderFailureCode.UNAVAILABLE
    snapshot = coordinator.show("change-a").design_package_snapshot
    assert snapshot is not None
    _set_checkpoint(
        runtimes["change-a"],
        state_root,
        pending.model_copy(update={"head": second_head}),
        published_head=snapshot.snapshot_head,
    )

    with patch.object(application._workspace_manager, "repository_automation_paths", return_value=()):
        result = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    assert result.draft_pull_request is not None
    assert result.draft_pull_request.head_sha == second_head
    assert result.generated_summary is not None
    assert create_attempts == 2
    assert provider.update_pull_request.call_count == 0


def test_reconcile_unanchored_checkpoint_waits_without_provider_calls(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    pending = DeliveryPendingCheckpoint(
        head=None,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    branch_publisher = Mock()
    pull_request_publisher = Mock()
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    result = application.reconcile_change_checkpoint("change-a")

    assert not result.reconciled
    assert result.attempted_head is None
    assert result.state.pending_checkpoint == pending
    assert branch_publisher.publish.call_count == 0
    assert pull_request_publisher.publish.call_count == 0


def test_delivery_loader_composes_validated_owners_from_authorized_root(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    application = load_delivery_application(
        _startup_config(),
        workspace_root=repository,
    )
    assert application.list_work_items() == ()
    assert not (runtime_root / "capacity.json").exists()
    assert not (runtime_root / "capacity-ledger.json").exists()
    assert application._execution_capacity == 8
    assert application._claim_timeout == timedelta(hours=1)
    assert not (repository / ".owlbear/target").exists()
    assert not (repository / ".owlbear/worktrees").exists()


def test_loader_composed_finalization_admits_descendant_and_replays_after_reload(tmp_path: Path) -> None:
    repository, runtime_root = _seed_loader_composed_completed_change(tmp_path)
    application = load_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=GitHubCliPublicationProvider(),
    )
    _attach_local_target(application, tmp_path)
    application.sync_change_with_current_target("change-a", "before-descendant")
    coordination = PortfolioCoordinator(runtime_root).show("change-a")
    exact_head = _commit_local_descendant(coordination, "loader-finalization.txt")

    context = application.show_finalization_context("change-a")

    assert context.ready_for_finalization is True
    assert context.change_head == exact_head
    finalization_request = _finalization_request("change-a", exact_head)
    finalization = application.finalize_change("change-a", finalization_request)
    assert finalization.exact_head == exact_head
    assert PortfolioCoordinator(runtime_root).show("change-a").last_reviewed_commit == exact_head

    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository, "config", f"url.{tmp_path / 'remote.git'}.insteadOf", "https://github.com/example/project.git")
    reloaded = load_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=GitHubCliPublicationProvider(),
    )
    reloaded_context = reloaded.show_finalization_context("change-a")

    assert reloaded_context.finalization_id == finalization.finalization_id
    assert reloaded_context.finalized_head == exact_head
    assert reloaded_context.reviewed_change_head == exact_head
    assert reloaded.finalize_change("change-a", finalization_request) == finalization


def _prepare_loader_finalized_change(application: PortfolioApplication, change_id: str) -> str:
    runtime = application._runtimes[change_id]
    application.sync_change_with_current_target(change_id, f"before-{change_id}")
    coordination = application._coordinator.show(change_id)
    exact_head = _commit_local_descendant(coordination, f"{change_id}-finalization.txt")
    finalization = application.finalize_change(change_id, _finalization_request(change_id, exact_head))
    publisher = application._draft_pull_request_publisher
    assert publisher is not None
    publisher.publish(
        CreateOrReconcileDraftPullRequest(
            change_id=change_id,
            operation_id=f"create-{change_id}",
            published_head=exact_head,
            title=f"Delivery {change_id}",
            generated_summary=f"Finalized {change_id}.",
        )
    )
    checkpoint = runtime.checkpoint_publication_state()
    assert checkpoint.pending_checkpoint is not None
    runtime.record_checkpoint_branch_publication(checkpoint, exact_head)
    runtime.acknowledge_checkpoint_publication(checkpoint.pending_checkpoint, exact_head)
    runtime.record_publication_identity(
        DeliveryChangePublicationIdentity(
            change_id=change_id,
            repository="example/project",
            number=7 if change_id == "change-a" else 8,
            node_id=f"PR_node_{7 if change_id == 'change-a' else 8}",
            head_sha=exact_head,
        )
    )
    state_publisher = application._delivery_state_publisher
    assert state_publisher is not None
    state_publisher.publish(
        change_id=change_id,
        package_id=application._package_store.read_verified(change_id).package_id,
        coordination=application._coordinator.show(change_id),
        runtime=runtime,
        admission=DeliveryAdmissionReceipt.model_validate_json(
            (application._target_root / "changes" / change_id / "admission.json").read_bytes()
        ),
        operation_id=f"seed-state-{change_id}",
        captured_at=datetime(2026, 8, 4, tzinfo=UTC),
    )
    runtime.acknowledge_pending_publication(hashlib.sha256(runtime.frontier_bytes()).hexdigest())
    assert runtime.pending_state_publication() is None
    assert finalization.exact_head == exact_head
    return exact_head


def _loader_composed_engine_fixture(tmp_path: Path):
    repository, runtime_root = _seed_loader_composed_completed_change(
        tmp_path,
        (
            ("change-a", DeliveryStage.COMPLETED),
            ("change-b", DeliveryStage.COMPLETED),
            ("change-c", DeliveryStage.PLANNING),
        ),
    )
    provider = _Provider(lose_draft_state_response=True)
    application = load_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    remote = _attach_local_target(application, tmp_path)
    head_a = _prepare_loader_finalized_change(application, "change-a")
    head_b = _prepare_loader_finalized_change(application, "change-b")
    return repository, runtime_root, remote, provider, application, head_a, head_b


def _advance_loader_target(application: PortfolioApplication) -> str:
    """Move the disposable remote-tracking target without changing Change custody."""
    repository = application._workspace_manager.repository
    base = _git(repository, "rev-parse", "refs/remotes/origin/main")
    tree = _git(repository, "rev-parse", f"{base}^{{tree}}")
    commit = subprocess.run(  # noqa: S603
        ("git", "-C", str(repository), "commit-tree", tree, "-p", base),  # noqa: S607
        input="registered target advance\n",
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    _git(repository, "update-ref", "refs/remotes/origin/main", commit)
    _git(repository, "push", "origin", f"{commit}:refs/heads/main")
    return commit


def _loader_registered_engine_action_fixture(
    tmp_path: Path,
    action_kind: Literal["reconcile-checkpoint", "sync-target", "observe-acceptance"],
) -> tuple[Path, Path, Path, _Provider, PortfolioApplication]:
    """Compose one registered continuation action from the canonical loader fixture."""
    repository, runtime_root, remote, provider, application, head_a, _head_b = _loader_composed_engine_fixture(tmp_path)
    provider.read_pull_request = Mock(wraps=provider.read_pull_request)
    provider.observe_checks = Mock(wraps=provider.observe_checks)
    runtime = application._runtimes["change-a"]
    if action_kind == "reconcile-checkpoint":
        published_head = runtime.checkpoint_publication_state().published_head
        _git(
            application._coordinator.show("change-a").worktree_path,
            "push",
            "origin",
            f"{head_a}:refs/heads/owlbear/change/change-a",
        )
        _set_checkpoint(
            runtime,
            runtime_root,
            DeliveryPendingCheckpoint(
                head=head_a,
                triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
            ),
            published_head=published_head,
        )
    elif action_kind == "sync-target":
        frontier_path = runtime_root / "changes" / "change-a" / "frontier.json"
        frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
        frontier_path.write_bytes(_canonical(frontier.model_copy(update={"finalization": None})))
        _git(
            application._coordinator.show("change-a").worktree_path,
            "push",
            "origin",
            f"{head_a}:refs/heads/owlbear/change/change-a",
        )
        _advance_loader_target(application)
    else:
        assert provider.pull_requests
    return repository, runtime_root, remote, provider, application


def _execute_with_result_publication_crash(
    application: PortfolioApplication,
    target_action: ChangeContinuationAction,
) -> None:
    original_finish = application._coordinator.finish_continuation_action

    def crash_at_result_publication(action, result, finished_at, *, release):
        if action.operation_id == target_action.operation_id:
            message = "injected result publication crash"
            raise RuntimeError(message)
        original_finish(action, result, finished_at, release=release)

    with (
        patch.object(application._coordinator, "finish_continuation_action", crash_at_result_publication),
        pytest.raises(RuntimeError, match="injected result publication crash"),
    ):
        _execute_engine(application, target_action)


def _make_provider_readback_unavailable(provider: _Provider, b_number: int) -> None:
    original_read = provider.read_pull_request
    fail_read = False

    def read_change_b(repository_name: str, number: int) -> PublicationPullRequest:
        if fail_read and number == b_number:
            raise PublicationProviderError(
                PublicationProviderFailureCode.UNAVAILABLE,
                "read_pull_request",
                "provider readback unavailable",
                retry_safe=False,
            )
        return original_read(repository_name, number)

    original_set = provider.set_pull_request_draft_state

    def mutate_change_b(request):
        nonlocal fail_read
        try:
            return original_set(request)
        finally:
            fail_read = True

    provider.read_pull_request = read_change_b
    provider.set_pull_request_draft_state = mutate_change_b


def _execute_loader_failure_case(
    fixture: tuple[Path, Path, Path, _Provider, PortfolioApplication, str, str],
    reloaded: PortfolioApplication,
    action_b: ChangeContinuationAction,
    failure_mode: str,
) -> tuple[PortfolioApplication, DeliveryEngineActionResult, object, object, object, str, bool]:
    repository, _runtime_root, remote, provider, _application, _head_a, _head_b = fixture
    runtime_b = reloaded._runtimes["change-b"]
    budget_before = runtime_b.retry_ledger().read()
    if failure_mode == "unknown-result":
        provider.lose_draft_state_response = False
        _execute_with_result_publication_crash(reloaded, action_b)
        assert provider.draft_state_calls == 2
        result_path = reloaded._coordinator.continuation_record_path("change-b", action_b.operation_id, result=True)
        assert (runtime_b.ready_receipt() is not None, not result_path.exists()) == (True, True)
        _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
        _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
        restarted = load_delivery_application(
            _startup_config(),
            workspace_root=repository,
            publication_provider=provider,
        )
        intent_path = restarted._coordinator.continuation_record_path("change-b", action_b.operation_id)
        started_path = intent_path.with_name("started.json")
        result_path = intent_path.with_name("result.json")
        worktree = restarted._coordinator.show("change-b").worktree_path
        before_read = {
            "intent": intent_path.read_bytes(),
            "started": started_path.read_bytes(),
            "result": result_path.read_bytes() if result_path.is_file() else None,
            "coordination": (restarted._coordinator.runtime_root / "coordination/changes/change-b.json").read_bytes(),
            "frontier": restarted._runtimes["change-b"].frontier_bytes(),
            "ledger": restarted._runtimes["change-b"].retry_ledger().read(),
            "workspace": _workspace_mutation_snapshot(worktree),
            "remote": _git(remote, "rev-parse", "refs/heads/owlbear/delivery-state"),
            "provider_calls": provider.draft_state_calls,
        }
        read_view = restarted.get_change("change-b")
        repeated_read_view = restarted.get_change("change-b")
        assert read_view.readiness.reason_code == "engine-action-interrupted"
        assert read_view.readiness.status == "blocked"
        assert not read_view.readiness.executable
        assert read_view.readiness.action is None
        assert "Delivery engine owner" in read_view.detail.card.next_step
        assert "all descendant writers and jobs" in read_view.detail.card.next_step
        assert repeated_read_view.readiness == read_view.readiness
        assert intent_path.read_bytes() == before_read["intent"]
        assert started_path.read_bytes() == before_read["started"]
        assert (result_path.read_bytes() if result_path.is_file() else None) == before_read["result"]
        assert (restarted._coordinator.runtime_root / "coordination/changes/change-b.json").read_bytes() == before_read[
            "coordination"
        ]
        assert restarted._runtimes["change-b"].frontier_bytes() == before_read["frontier"]
        assert restarted._runtimes["change-b"].retry_ledger().read() == before_read["ledger"]
        assert _workspace_mutation_snapshot(worktree) == before_read["workspace"]
        assert _git(remote, "rev-parse", "refs/heads/owlbear/delivery-state") == before_read["remote"]
        assert provider.draft_state_calls == before_read["provider_calls"]
        contained = _execute_engine(restarted, action_b)
    else:
        _make_provider_readback_unavailable(provider, 8)
        restarted = reloaded
        contained = _execute_engine(restarted, action_b)
        _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
        _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
        restarted = load_delivery_application(
            _startup_config(),
            workspace_root=repository,
            publication_provider=provider,
        )
    remote_state_head = _git(remote, "rev-parse", "refs/heads/owlbear/delivery-state")
    workspace = _workspace_mutation_snapshot(restarted._coordinator.show("change-b").worktree_path)
    budget_after = restarted._runtimes["change-b"].retry_ledger().read()
    return (
        restarted,
        contained,
        budget_before,
        budget_after,
        workspace,
        remote_state_head,
        failure_mode == "unknown-result",
    )


def _mutate_loader_workspace(worktree: Path, variant: str) -> Path:
    if variant == "dirty":
        path = worktree / "product.txt"
        path.write_text("foreign tracked changes\n", encoding="utf-8")
    elif variant == "staged":
        path = worktree / "staged.txt"
        path.write_text("pre-existing staged changes\n", encoding="utf-8")
        _git(worktree, "add", path.name)
    else:
        path = worktree / ".private-input"
        path.write_text("private input\n", encoding="utf-8")
    return path


def _assert_loader_stale_retry(
    application: PortfolioApplication,
    action: ChangeContinuationAction,
    now: list[datetime],
    budget_after_stale: object,
    stale_result: DeliveryEngineActionResult,
) -> None:
    ledger = application._runtimes["change-b"].retry_ledger()
    budget_after_wait = ledger.read()
    assert budget_after_wait == budget_after_stale
    stale_episode = next(
        episode for episode in budget_after_wait.episodes if action.operation_id in episode.attempt_ids
    )
    assert stale_episode.next_eligible_at is not None
    now[0] = datetime.fromisoformat(stale_episode.next_eligible_at) + timedelta(seconds=1)
    retried_action = _engine_action(application, "change-b")
    assert retried_action.operation_id != action.operation_id
    retry_budget = ledger.read()
    retry_episode = next(
        episode for episode in retry_budget.episodes if retried_action.operation_id in episode.attempt_ids
    )
    assert retry_episode.total_attempts == 2
    assert retry_episode.reset_count == 0
    assert action.operation_id in retry_episode.attempt_ids
    budget_before_replay = ledger.read()
    assert _execute_engine(application, action) == stale_result
    assert ledger.read() == budget_before_replay


def test_unscoped_start_marker_read_preserves_continuation_mutation_guard(tmp_path: Path) -> None:
    _repository, _runtime_root, _remote, _provider, application, _head_a, _head_b = _loader_composed_engine_fixture(
        tmp_path
    )
    action = _engine_action(application, "change-b")
    coordinator = application._coordinator

    assert not coordinator.continuation_start_recorded(action)
    with pytest.raises(CoordinationConflictError, match="continuation action custody"):
        coordinator.continuation_action_started(action)


@pytest.mark.parametrize("workspace_variant", ["dirty", "staged", "private"])
def test_loader_composed_engine_preflight_contains_workspace_variants(
    tmp_path: Path,
    workspace_variant: str,
) -> None:
    _repository, _runtime_root, remote, provider, application, _head_a, _head_b = _loader_composed_engine_fixture(
        tmp_path
    )
    now = [datetime.now(UTC)]

    def fixed_clock() -> str:
        return now[0].isoformat()

    application._clock = fixed_clock
    worktree = application._coordinator.show("change-b").worktree_path
    original_path_bytes = (worktree / "product.txt").read_bytes() if workspace_variant == "dirty" else None
    action = _engine_action(application, "change-b")
    changed_path = _mutate_loader_workspace(worktree, workspace_variant)
    workspace_before = _workspace_mutation_snapshot(worktree)
    budget_before = application._runtimes["change-b"].retry_ledger().read()
    reserved_episode = next(episode for episode in budget_before.episodes if action.operation_id in episode.attempt_ids)
    assert reserved_episode.total_attempts == 1
    assert reserved_episode.last_status == "reserved"
    remote_state_before = _git(remote, "rev-parse", "refs/heads/owlbear/delivery-state")
    sibling_frontier = application._runtimes["change-a"].frontier_bytes()
    sibling_publication = application._runtimes["change-a"].checkpoint_publication_state()

    result = _execute_engine(application, action)

    assert result.kind == "stale"
    assert result.reason_code == "readiness-changed"
    assert provider.draft_state_calls == 0
    assert application._runtimes["change-b"].ready_receipt() is None
    assert _workspace_mutation_snapshot(worktree) == workspace_before
    ledger = application._runtimes["change-b"].retry_ledger()
    budget_after_stale = ledger.read()
    stale_episode = next(
        episode for episode in budget_after_stale.episodes if action.operation_id in episode.attempt_ids
    )
    assert stale_episode.total_attempts == 1
    assert stale_episode.reset_count == 0
    assert stale_episode.last_status == "failed"
    assert digest(f"{action.operation_id}:failed".encode()) in stale_episode.outcome_ids
    assert action.operation_id not in {attempt.attempt_id for attempt in ledger.pending_attempts()}
    assert _git(remote, "rev-parse", "refs/heads/owlbear/delivery-state") == remote_state_before
    assert application._runtimes["change-a"].frontier_bytes() == sibling_frontier
    assert application._runtimes["change-a"].checkpoint_publication_state() == sibling_publication
    started_path = application._coordinator.continuation_record_path("change-b", action.operation_id).with_name(
        "started.json"
    )
    assert not started_path.exists()
    assert _execute_engine(application, action) == result
    if workspace_variant == "dirty":
        _git(worktree, "checkout", "--", changed_path.name)
    elif workspace_variant == "staged":
        _git(worktree, "reset", "HEAD", "--", changed_path.name)
        changed_path.unlink()
    else:
        changed_path.unlink()
    if workspace_variant == "dirty":
        assert changed_path.read_bytes() == original_path_bytes
    else:
        assert not changed_path.exists()
    assert _git(worktree, "status", "--porcelain") == ""
    _assert_loader_stale_retry(application, action, now, budget_after_stale, result)
    assert provider.draft_state_calls == 0


@pytest.mark.parametrize("failure_mode", ["unknown-result", "unknown-readback"])
def test_loader_composed_engine_replay_contains_unknown_owner_and_preserves_sibling_progress(  # noqa: PLR0915 - one parameterized loader oracle covers both unknown-result modes.
    tmp_path: Path,
    failure_mode: str,
) -> None:
    fixture = _loader_composed_engine_fixture(tmp_path)
    repository, _runtime_root, remote, provider, application, head_a, head_b = fixture

    action_a = _engine_action(application, "change-a")
    completed = _execute_engine(application, action_a)
    assert (
        completed.kind,
        completed.ready.head_sha if completed.ready is not None else None,
        provider.draft_state_calls,
    ) == ("completed", head_a, 1)

    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    reloaded = load_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    sibling_frontier = reloaded._runtimes["change-b"].frontier_bytes()
    sibling_publication = reloaded._runtimes["change-b"].checkpoint_publication_state()
    remote_state_head = _git(remote, "rev-parse", "refs/heads/owlbear/delivery-state")
    replayed = _execute_engine(reloaded, action_a)
    assert replayed == completed
    assert provider.draft_state_calls == 1
    assert reloaded.get_change("change-a").continuation_action is not None
    assert reloaded.get_change("change-a").continuation_action.finished_at is not None
    assert (
        reloaded._runtimes["change-b"].frontier_bytes(),
        reloaded._runtimes["change-b"].checkpoint_publication_state(),
    ) == (sibling_frontier, sibling_publication)
    assert _git(remote, "rev-parse", "refs/heads/owlbear/delivery-state") == remote_state_head
    assert reloaded._runtimes["change-b"].pending_state_publication() is None

    action_b = _engine_action(reloaded, "change-b")
    (
        restarted,
        contained,
        budget_before,
        budget_after,
        workspace_after_containment,
        remote_state_head_after_effect,
        unknown_result,
    ) = _execute_loader_failure_case(
        fixture,
        reloaded,
        action_b,
        failure_mode,
    )
    assert (contained.kind, provider.draft_state_calls) == ("blocked", 2)
    assert contained.reason_code == ("engine-action-interrupted" if unknown_result else "engine-action-failed")
    assert contained.ready is None
    assert contained.action == action_b
    assert contained.failure is not None
    if unknown_result:
        assert contained.failure.detail == "Original owner result is unknown."
    else:
        assert "provider readback unavailable" in contained.failure.detail
        assert "release custody" in contained.failure.retry_condition
        assert "replacement" in contained.failure.retry_condition
    assert restarted.get_change("change-b").continuation_action == action_b
    assert restarted.get_change("change-b").continuation_action.finished_at is None
    intent_path = restarted._coordinator.continuation_record_path("change-b", action_b.operation_id)
    result_path = restarted._coordinator.continuation_record_path("change-b", action_b.operation_id, result=True)
    intent_before = intent_path.read_bytes()
    result_before = result_path.read_bytes() if result_path.is_file() else None
    read_view = restarted.get_change("change-b")
    repeated_read_view = restarted.get_change("change-b")
    assert read_view.readiness.reason_code == (
        "engine-action-interrupted" if unknown_result else "engine-action-failed"
    )
    assert read_view.detail.card.next_step
    assert repeated_read_view.readiness == read_view.readiness
    assert intent_path.read_bytes() == intent_before
    assert (result_path.read_bytes() if result_path.is_file() else None) == result_before
    if unknown_result:
        assert "Delivery engine owner" in read_view.detail.card.next_step
        assert "all descendant writers and jobs" in read_view.detail.card.next_step
        assert "do not retry" in read_view.detail.card.next_step
    else:
        assert "publication owner" in read_view.detail.card.next_step
        assert "provider/readback failure" in read_view.detail.card.next_step
    if unknown_result:
        assert restarted._runtimes["change-b"].ready_receipt() is not None
    else:
        assert restarted._runtimes["change-b"].ready_receipt() is None
    budget_after = restarted._runtimes["change-b"].retry_ledger().read()
    if unknown_result:
        assert budget_after == budget_before
    else:
        assert budget_after.version == budget_before.version + 1

    repeated = _execute_engine(restarted, action_b)
    assert repeated == contained
    assert provider.draft_state_calls == 2
    assert restarted._runtimes["change-b"].retry_ledger().read() == budget_after
    assert (
        _workspace_mutation_snapshot(restarted._coordinator.show("change-b").worktree_path)
        == workspace_after_containment
    )
    assert _git(remote, "rev-parse", "refs/heads/owlbear/delivery-state") == remote_state_head_after_effect
    sibling = restarted.acquire_change_action(_continuation_request(restarted, "change-c"))
    assert sibling.kind == "acquired"
    assert sibling.launch is not None
    assert sibling.launch.change_id == "change-c"
    assert restarted._runtimes["change-b"].finalization().exact_head == head_b


def test_delivery_loader_uses_host_capacity_and_local_claim_timeout(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    host_config_path = repository / ".owlbear/delivery/runtime/host.json"
    host_config_path.parent.mkdir(parents=True)
    host_config_path.write_text(
        DeliveryHostConfig(
            schema_version=1,
            execution_capacity=3,
            claim_timeout_seconds=3600,
        ).model_dump_json(),
        encoding="utf-8",
    )
    (repository / ".owlbear/delivery/runtime/host.local.json").write_text(
        '{"execution_capacity": 5, "claim_timeout_seconds": 5}\n',
        encoding="utf-8",
    )

    application = load_delivery_application(_startup_config(), workspace_root=repository)

    assert application._execution_capacity == 5
    assert application._claim_timeout == timedelta(seconds=5)


@pytest.mark.parametrize(
    ("content", "field"),
    [
        ("not-json\n", "host_config"),
        ('{"schema_version": 1, "writer_capacity": 2}\n', "writer_capacity"),
        ('{"schema_version": 1, "execution_capacity": "3"}\n', "execution_capacity"),
        ('{"schema_version": 1, "claim_timeout_seconds": 0}\n', "claim_timeout_seconds"),
        ('{"schema_version": 1, "claim_timeout_seconds": "5"}\n', "claim_timeout_seconds"),
        ('{"schema_version": 1, "unknown": 3}\n', "unknown"),
    ],
)
def test_delivery_loader_rejects_invalid_host_capacity_before_ledger_mutation(
    tmp_path: Path,
    content: str,
    field: str,
) -> None:
    repository = _repository(tmp_path)
    host_config_path = repository / ".owlbear/delivery/runtime/host.json"
    host_config_path.parent.mkdir(parents=True)
    host_config_path.write_text(content, encoding="utf-8")

    with pytest.raises(DeliveryApplicationLoadError) as exc_info:
        load_delivery_application(_startup_config(), workspace_root=repository)

    assert exc_info.value.field == field
    assert "host.json" in exc_info.value.detail
    assert not (repository / ".owlbear/delivery/runtime/capacity.json").exists()
    assert not (repository / ".owlbear/delivery/runtime/capacity-ledger.json").exists()
    if field == "writer_capacity":
        assert exc_info.value.__cause__ is not None
        assert exc_info.value.__cause__.errors()[0]["type"] == "extra_forbidden"


@pytest.mark.parametrize(
    ("content", "field"),
    [
        ('{"claim_timeout_seconds": 0}\n', "claim_timeout_seconds"),
        ('{"claim_timeout_seconds": "5"}\n', "claim_timeout_seconds"),
        ('{"schema_version": null}\n', "state_version"),
        ('{"unknown": 3}\n', "unknown"),
    ],
)
def test_delivery_loader_rejects_invalid_host_local_config_before_ledger_mutation(
    tmp_path: Path,
    content: str,
    field: str,
) -> None:
    repository = _repository(tmp_path)
    host_local_config_path = repository / ".owlbear/delivery/runtime/host.local.json"
    host_local_config_path.parent.mkdir(parents=True)
    host_local_config_path.write_text(content, encoding="utf-8")

    with pytest.raises(DeliveryApplicationLoadError) as exc_info:
        load_delivery_application(_startup_config(), workspace_root=repository)

    assert exc_info.value.field == field
    assert "host.local.json" in exc_info.value.detail
    assert not (repository / ".owlbear/delivery/runtime/capacity-ledger.json").exists()


def test_delivery_loader_ignores_legacy_capacity_ledger(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    runtime_root.mkdir(parents=True)
    ledger_path = runtime_root / "capacity-ledger.json"
    ledger_path.write_text(
        CapacityLedger(capacity=2, change_ids=("change-a", "change-b")).model_dump_json(),
        encoding="utf-8",
    )
    before = ledger_path.read_bytes()
    host_config_path = runtime_root / "host.json"
    host_config_path.write_text(
        DeliveryHostConfig(schema_version=1, execution_capacity=1).model_dump_json(),
        encoding="utf-8",
    )
    _mark_current_format(runtime_root)

    application = load_delivery_application(_startup_config(), workspace_root=repository)

    assert application._execution_capacity == 1
    assert ledger_path.read_bytes() == before


def test_delivery_loader_does_not_translate_unrelated_coordination_conflict(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    with (
        patch(
            "owlbear_delivery.delivery_application_loader.PortfolioCoordinator",
            side_effect=CoordinationConflictError("unrelated coordination failure"),
        ),
        pytest.raises(CoordinationConflictError, match="unrelated coordination failure"),
    ):
        load_delivery_application(_startup_config(), workspace_root=repository)


def test_delivery_loader_isolates_contract_without_workspace_coordination(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    contract = _contract("change-a", b"intent", b"design")
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
            ),
        )
    )
    change_root = runtime_root / "changes/change-a"
    change_root.mkdir(parents=True)
    (change_root / "contract.json").write_bytes(_canonical(contract))
    (change_root / "frontier.json").write_bytes(_canonical(frontier))
    _mark_current_format(runtime_root)

    application = load_delivery_application(_startup_config(), workspace_root=repository)

    assert application.list_work_items() == ()


# An admission without a schema version is refused by the format gate; an owner-invalid one stays recoverable.
@pytest.mark.parametrize("admission_content", [None, b'{"schema_version":1}\n'])
def test_delivery_loader_allows_recoverable_admission_partial_state(
    tmp_path: Path,
    admission_content: bytes | None,
) -> None:
    repository = _repository(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    contract = _contract("change-a", b"intent", b"design")
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
            ),
        )
    )
    change_root = runtime_root / "changes/change-a"
    change_root.mkdir(parents=True)
    (change_root / "contract.json").write_bytes(_canonical(contract))
    (change_root / "frontier.json").write_bytes(_canonical(frontier))
    if admission_content is not None:
        (change_root / "admission.json").write_bytes(admission_content)
    _mark_current_format(runtime_root)

    application = load_delivery_application(_startup_config(), workspace_root=repository)

    assert application.list_work_items() == ()


def _admit_discovery_change(application: PortfolioApplication, change_id: str):
    intent = f"""# {change_id}

```yaml target-contract
kind: commitment
id: COM-001
class: agreed-path
decisions: [DEC-001]
statement: Preserve persisted admission evidence.
```

```yaml target-contract
kind: decision
id: DEC-001
origin: approved
basis: fixture approval
statement: Fixture decision.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Discover persisted authority
promise: Make persisted authority observable.
acceptance: ["AC-001: Admission is observable."]
commitments: [COM-001]
dependencies: []
```
""".encode()
    application.create_design_session(change_id, intent, b"# Architecture\n")
    return application.admit_delivery_change(
        DeliveryAdmissionRequest(
            change_id=change_id,
            expected_package_id=_approved_package_id(application, change_id),
            active_claim_ids=(),
        )
    )


def test_delivery_discovery_returns_valid_admission_and_stable_fingerprint(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(tmp_path, {})
    admitted = _admit_discovery_change(application, "discovered-change")

    observations = discover_persisted_changes(state_root)

    assert len(observations) == 1
    observation = observations[0]
    assert observation.change_id == "discovered-change"
    assert observation.admitted
    assert observation.admission == admitted.receipt
    assert observation.contract == admitted.contract
    assert observation.contract_fingerprint == contract_fingerprint(admitted.contract)
    assert observation.frontier == admitted.frontier
    assert observation.stage is DeliveryChangeStage.BUILDING
    assert observation.error is None
    assert observation.actionable_runtime
    assert observation.diagnostic_code is None


@pytest.mark.parametrize(
    ("mutation", "error_code"),
    [
        ("malformed", DeliveryDiscoveryErrorCode.FRONTIER_INVALID),
        ("mid-write", DeliveryDiscoveryErrorCode.FRONTIER_UNAVAILABLE),
    ],
)
def test_delivery_discovery_contains_one_bad_entry_and_preserves_unrelated_entries(
    tmp_path: Path,
    mutation: str,
    error_code: DeliveryDiscoveryErrorCode,
) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(tmp_path, {})
    _admit_discovery_change(application, "bad-change")
    _admit_discovery_change(application, "good-change")
    frontier_path = state_root / "changes/bad-change/frontier.json"
    if mutation == "malformed":
        frontier_path.write_bytes(b"not-json\n")
    else:
        frontier_path.unlink()

    observations = {observation.change_id: observation for observation in discover_persisted_changes(state_root)}

    assert set(observations) == {"bad-change", "good-change"}
    assert observations["bad-change"].error is not None
    assert observations["bad-change"].error.code == error_code
    assert observations["good-change"].error is None
    assert observations["good-change"].admitted


def test_delivery_discovery_contains_frontier_binding_mismatch(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(tmp_path, {})
    _admit_discovery_change(application, "bad-bindings")
    _admit_discovery_change(application, "good-change")
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-999",
                plan_scope_id="SCOPE-999",
            ),
        )
    )
    (state_root / "changes/bad-bindings/frontier.json").write_bytes(_canonical(frontier))

    observations = {observation.change_id: observation for observation in discover_persisted_changes(state_root)}

    assert observations["bad-bindings"].error is not None
    assert observations["bad-bindings"].error.code == DeliveryDiscoveryErrorCode.FRONTIER_BINDING_INVALID
    assert observations["good-change"].error is None


def test_delivery_discovery_detects_in_place_contract_replacement(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(tmp_path, {})
    admitted = _admit_discovery_change(application, "replaced-change")
    before = discover_persisted_changes(state_root)[0]
    replacement = admitted.contract.model_copy(update={"title": "Replacement authority"})
    (state_root / "changes/replaced-change/contract.json").write_bytes(_canonical(replacement))

    after = discover_persisted_changes(state_root)[0]

    assert before.contract_fingerprint is not None
    assert after.contract_fingerprint == contract_fingerprint(replacement)
    assert after.contract_fingerprint != before.contract_fingerprint
    assert after.admitted
    assert after.stage is DeliveryChangeStage.BUILDING
    assert after.diagnostic_code == "runtime_unavailable"
    assert not after.actionable_runtime


def test_delivery_discovery_retains_admission_for_unavailable_runtime(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(tmp_path, {})
    admitted = _admit_discovery_change(application, "unavailable-change")
    (state_root / "changes/unavailable-change/contract.json").unlink()

    observation = discover_persisted_changes(state_root)[0]

    assert observation.admission == admitted.receipt
    assert observation.frontier == admitted.frontier
    assert observation.stage is DeliveryChangeStage.BUILDING
    assert observation.diagnostic_code == "runtime_unavailable"
    assert observation.diagnostic_detail is not None
    assert len(observation.diagnostic_detail) <= 240
    assert not observation.actionable_runtime


def test_delivery_loader_injects_publication_provider_and_derives_check_head(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    provider = Mock()
    application = load_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    assert isinstance(application._change_branch_publisher, ChangeBranchPublisher)
    assert isinstance(application._draft_pull_request_publisher, DraftPullRequestPublisher)
    checks_request = ObserveChangePublicationChecks(
        change_id="change-a",
        published_head="1" * 40,
    )
    runtime = Mock()
    runtime.checkpoint_publication_state.return_value = DeliveryCheckpointPublicationState(
        change_id="change-a",
        published_head="1" * 40,
        pending_checkpoint=None,
    )

    with (
        patch.object(
            application._draft_pull_request_publisher,
            "observe_checks",
            return_value=sentinel.check_snapshot,
        ) as observe_checks,
        patch.object(application, "_runtime", return_value=runtime),
    ):
        assert application.observe_change_publication_checks("change-a") is sentinel.check_snapshot

    observe_checks.assert_called_once_with(checks_request)


def test_delivery_loader_without_provider_fails_closed_for_checkpoint_operations(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    application = load_delivery_application(_startup_config(), workspace_root=repository)
    assert isinstance(application._change_branch_publisher, ChangeBranchPublisher)
    with pytest.raises(PortfolioApplicationError, match="not configured"):
        application.reconcile_change_checkpoint("change-a")
    with pytest.raises(PortfolioApplicationError, match="not configured"):
        application.observe_change_publication_checks("change-a")


@pytest.mark.parametrize("symlinked_parent", [".owlbear", ".owlbear/delivery"])
def test_delivery_loader_rejects_symlinked_canonical_state_parent(
    tmp_path: Path,
    symlinked_parent: str,
) -> None:
    repository = _repository(tmp_path / "repository")
    external = tmp_path / "external"
    external.mkdir()
    parent = repository / symlinked_parent
    if symlinked_parent == ".owlbear/delivery":
        parent.parent.mkdir()
    parent.symlink_to(external, target_is_directory=True)

    with pytest.raises(DeliveryApplicationLoadError) as exc_info:
        load_delivery_application(
            _startup_config(),
            workspace_root=repository,
        )

    assert exc_info.value.field == "workspace_root"
    assert "symlink" in exc_info.value.detail
    assert not (external / "runtime").exists()


def test_delivery_loader_rejects_startup_from_linked_worktree(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    linked_worktree = tmp_path / "linked-worktree"
    _git(repository, "worktree", "add", "--detach", str(linked_worktree), "HEAD")

    with pytest.raises(DeliveryApplicationLoadError) as exc_info:
        load_delivery_application(
            _startup_config(),
            workspace_root=linked_worktree,
        )

    assert exc_info.value.field == "workspace_root"
    assert exc_info.value.detail == "Delivery must start from the primary Git worktree"
    # The controller lock is taken before Git validation (N02-A I1/I5); it is the only entry left behind.
    assert [path.name for path in (linked_worktree / ".owlbear/delivery/runtime").iterdir()] == ["controller.lock"]


def test_delivery_loader_rejects_git_and_state_identity_before_composition(tmp_path: Path) -> None:
    non_repository = tmp_path / "not-a-repository"
    non_repository.mkdir()
    runtime_root = non_repository / ".owlbear/delivery/runtime"
    with pytest.raises(DeliveryApplicationLoadError) as git_error:
        load_delivery_application(
            _startup_config(),
            workspace_root=non_repository,
        )
    assert git_error.value.field == "repository_root"
    assert [path.name for path in runtime_root.iterdir()] == ["controller.lock"]

    repository = _repository(tmp_path / "valid")
    state_root = repository / ".owlbear/delivery/runtime"
    change_root = state_root / "changes/change-a"
    change_root.mkdir(parents=True)
    contract = _contract("change-b", b"intent\n", b"design\n")
    (change_root / "contract.json").write_bytes(_canonical(contract))
    _mark_current_format(state_root)
    application = load_delivery_application(
        _startup_config(),
        workspace_root=repository,
    )
    health = application.delivery_health()
    assert health.status.value == "attention"
    assert any(
        diagnostic.change_id == "change-a" and diagnostic.code == "contract-identity-invalid"
        for diagnostic in health.diagnostics
    )
    assert application.list_work_items() == ()
    assert not (state_root / "capacity-ledger.json").exists()

    runtime_repository = _repository(tmp_path / "invalid-runtime")
    runtime_root = runtime_repository / ".owlbear/delivery/runtime"
    runtime_change = runtime_root / "changes/change-a"
    runtime_change.mkdir(parents=True)
    valid_contract = _contract("change-a", b"intent\n", b"design\n")
    (runtime_change / "contract.json").write_bytes(_canonical(valid_contract))
    (runtime_change / "frontier.json").write_bytes(b"not-json\n")
    _mark_current_format(runtime_root)
    application = load_delivery_application(
        _startup_config(),
        workspace_root=runtime_repository,
    )
    health = application.delivery_health()
    assert health.status.value == "attention"
    assert any(
        diagnostic.change_id == "change-a" and diagnostic.code == "frontier-invalid"
        for diagnostic in health.diagnostics
    )
    assert application.list_work_items() == ()
    assert not (runtime_root / "capacity-ledger.json").exists()


def test_design_session_read_and_revision_delegate_to_package_store(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(tmp_path, {})
    created = application.create_design_session("composed-delivery", b"intent\n", b"design\n")

    current = application.read_design_session("composed-delivery")
    revised = application.revise_design_session(
        "composed-delivery",
        current.package_id,
        b"revised intent\n",
        b"revised design\n",
    )

    assert current.package_id == created.package_id
    assert revised == application.read_design_session("composed-delivery")
    assert revised.intent_bytes == b"revised intent\n"
    assert revised.design_bytes == b"revised design\n"
    assert revised.authority_bytes == b""


def test_admitted_design_revision_is_rejected_without_package_mutation(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    current = application.read_design_session("change-a")

    with pytest.raises(DeliveryRevisionError, match="change-not-paused") as refused:
        application.revise_design_session(
            "change-a",
            current.package_id,
            b"changed intent\n",
            b"changed design\n",
        )

    assert refused.value.code == "ERR_DELIVERY_REVISION"
    assert application.read_design_session("change-a") == current


def test_returned_design_revision_requires_pause(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.DESIGN},
    )
    runtime = runtimes["change-a"]
    current = application.read_design_session("change-a")
    _change_intent(application, "change-a", DeliveryChangeIntentKind.DEFER, reason="Revise requirements")

    revised = application.revise_design_session(
        "change-a",
        current.package_id,
        b"changed intent\n",
        b"changed design\n",
    )

    assert revised.package_id != current.package_id
    assert revised.intent_bytes == b"changed intent\n"
    assert runtime.change_stage() is DeliveryChangeStage.DEFERRED


def _assert_composed_delivery_admission(
    application: PortfolioApplication,
    tmp_path: Path,
    state_root: Path,
) -> tuple[bytes, bytes, bytes, DeliveryContract]:
    intent = b"""# Composed Delivery

```yaml target-contract
kind: commitment
id: COM-001
class: agreed-path
decisions: [DEC-001]
statement: Preserve source ownership.
```

```yaml target-contract
kind: decision
id: DEC-001
origin: approved
basis: fixture approval
statement: Fixture decision.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Compose owners
promise: Delegate exact operations.
acceptance: ["AC-001: Delegation is observable."]
commitments: [COM-001]
dependencies: []
```
"""
    design = b"# Architecture\n"

    created = application.create_design_session("composed-delivery", intent, design)
    package_bytes = _file_bytes(tmp_path / "packages/composed-delivery")
    replayed = application.create_design_session("composed-delivery", intent, design)
    derived = application.derive_delivery_contract("composed-delivery")
    rederived = application.derive_delivery_contract("composed-delivery")

    assert replayed.package_id == created.package_id
    assert replayed.replayed
    assert _file_bytes(tmp_path / "packages/composed-delivery") == package_bytes
    with pytest.raises(DesignPackageConflictError, match="differs"):
        application.create_design_session("composed-delivery", intent + b"changed\n", design)
    assert _file_bytes(tmp_path / "packages/composed-delivery") == package_bytes
    assert rederived == derived
    assert derived.contract is not None
    assert not (state_root / "changes/composed-delivery").exists()

    product_head = _git(tmp_path / "repository", "rev-parse", "main")
    request = DeliveryAdmissionRequest(
        change_id="composed-delivery",
        expected_package_id=_approved_package_id(application, "composed-delivery"),
        active_claim_ids=(),
    )
    admitted = application.admit_delivery_change(request)
    admission_replay = application.admit_delivery_change(request)
    checkpoint = application.publish_design_checkpoint("composed-delivery")

    assert admission_replay.receipt == admitted.receipt
    assert admission_replay.contract == admitted.contract
    assert admission_replay.frontier == admitted.frontier
    assert admission_replay.replayed
    assert checkpoint.commit == admitted.receipt.checkpoint_commit
    assert checkpoint.replayed
    assert _git(tmp_path / "repository", "rev-parse", "main") == product_head
    listed = application.list_work_items()
    assert tuple((item.change_id, item.work_item_id) for item in listed) == (
        ("composed-delivery", "OUT-001"),
        ("composed-delivery", "composed-delivery"),
    )
    coordination = application._coordinator.show("composed-delivery")
    package_paths = {
        ".owlbear/delivery/packages/composed-delivery/authority.json",
        ".owlbear/delivery/packages/composed-delivery/design.md",
        ".owlbear/delivery/packages/composed-delivery/intent.md",
        ".owlbear/delivery/packages/composed-delivery/manifest.json",
    }
    assert set(_git(tmp_path / "repository", "ls-tree", "-r", "--name-only", coordination.branch).splitlines()) >= (
        package_paths
    )
    pending = application.show_change_checkpoint_publication("composed-delivery").pending_checkpoint
    assert pending is not None
    assert pending.head == coordination.last_reviewed_commit
    assert pending.triggers == (DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.ADMITTED_DESIGN),)
    assert application.acquire_frontier_work().launch_packages == ()
    return intent, design, admitted.contract_bytes, admitted.contract


def test_design_compilation_and_admission_delegate_without_extra_mutation(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(tmp_path, {})
    intent, design, admitted_contract_bytes, admitted_contract = _assert_composed_delivery_admission(
        application, tmp_path, state_root
    )

    delivery_root = state_root / "changes/composed-delivery"
    _change_intent(application, "composed-delivery", DeliveryChangeIntentKind.DEFER, reason="Revise requirements")
    admitted_bytes = _file_bytes(delivery_root)
    admitted_bytes.pop("state-publication.json")
    changed_intent = intent.replace(b"Preserve source ownership.", b"Preserve revised source ownership.")
    package_root = tmp_path / "packages/composed-delivery"
    (package_root / "intent.md").write_bytes(changed_intent)
    manifest = DesignPackageManifest.from_content(
        "composed-delivery",
        changed_intent,
        design,
        admitted_contract_bytes,
    )
    (package_root / "manifest.json").write_bytes(manifest.canonical_bytes())

    with pytest.raises(DeliveryAdmissionConflictError, match="active claims block"):
        application.admit_delivery_change(
            DeliveryAdmissionRequest(
                change_id="composed-delivery",
                expected_package_id=_approved_package_id(application, "composed-delivery"),
                active_claim_ids=("active-claim",),
                expected_frontier_digest=hashlib.sha256((delivery_root / "frontier.json").read_bytes()).hexdigest(),
                expected_design_package_snapshot_receipt_id=(
                    _coordinator.show("composed-delivery").design_package_snapshot.receipt_id
                ),
            )
        )
    after_refusal = _file_bytes(delivery_root)
    after_refusal.pop("state-publication.json")
    assert after_refusal == admitted_bytes

    coordination_before_revision = _coordinator.show("composed-delivery")
    frontier_digest = hashlib.sha256((delivery_root / "frontier.json").read_bytes()).hexdigest()
    replacement = application.admit_delivery_change(
        DeliveryAdmissionRequest(
            change_id="composed-delivery",
            expected_package_id=_approved_package_id(application, "composed-delivery"),
            active_claim_ids=(),
            expected_frontier_digest=frontier_digest,
            expected_design_package_snapshot_receipt_id=(
                coordination_before_revision.design_package_snapshot.receipt_id
                if coordination_before_revision.design_package_snapshot is not None
                else None
            ),
        )
    )

    coordination_after_revision = _coordinator.show("composed-delivery")
    revised_package = application.read_design_session("composed-delivery")
    assert replacement.contract != admitted_contract
    assert coordination_after_revision.design_package_snapshot is not None
    assert coordination_after_revision.design_package_snapshot.package_id == revised_package.package_id
    assert coordination_after_revision.design_package_snapshot.snapshot_head != (
        coordination_before_revision.design_package_snapshot.snapshot_head
    )
    assert (
        _git(
            coordination_after_revision.worktree_path,
            "merge-base",
            "--is-ancestor",
            coordination_before_revision.design_package_snapshot.snapshot_head,
            coordination_after_revision.design_package_snapshot.snapshot_head,
        )
        == ""
    )


def test_interrupted_first_design_admission_replays_after_workspace_ensure(tmp_path: Path) -> None:
    application, _runtimes, coordinator, state_root = _portfolio(tmp_path, {})
    change_id = "change-a"
    intent = b"""# Interrupted first admission

```yaml target-contract
kind: commitment
id: COM-001
class: agreed-path
decisions: [DEC-001]
statement: Preserve the admitted Design source.
```

```yaml target-contract
kind: decision
id: DEC-001
origin: approved
basis: fixture approval
statement: Fixture decision.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Complete first admission
promise: Register the workspace with the verified Design package.
acceptance: ["AC-001: The admitted Design snapshot is registered."]
commitments: [COM-001]
dependencies: []
```
"""
    design = b"# Architecture\n"
    application.create_design_session(change_id, intent, design)
    request = DeliveryAdmissionRequest(
        change_id=change_id,
        expected_package_id=_approved_package_id(application, change_id),
        active_claim_ids=(),
    )
    package_root = tmp_path / "packages" / change_id
    delivery_root = state_root / "changes" / change_id
    registry_before = _file_bytes(delivery_root)
    assert registry_before == {}

    with (
        patch.object(
            application._workspace_manager,
            "ensure",
            side_effect=RuntimeError("interrupted workspace registration"),
        ) as ensure,
        pytest.raises(RuntimeError, match="interrupted workspace registration"),
    ):
        application.admit_delivery_change(request)
    ensure.assert_called_once_with(change_id, recovery_reviewed_head=None)

    registry_after_interruption = _file_bytes(delivery_root)
    assert registry_after_interruption != registry_before
    assert coordinator.find_registered(change_id) is None
    authority_before_replay = {name: registry_after_interruption[name] for name in ("contract.json", "admission.json")}
    package_after_interruption = _file_bytes(package_root)
    assert package_after_interruption["intent.md"] == intent
    assert package_after_interruption["design.md"] == design

    replayed = application.admit_delivery_change(request)

    assert replayed.replayed
    registry_after_replay = _file_bytes(delivery_root)
    assert {name: registry_after_replay[name] for name in authority_before_replay} == authority_before_replay
    assert replayed.receipt == DeliveryAdmissionReceipt.model_validate_json(authority_before_replay["admission.json"])
    assert _file_bytes(package_root) == package_after_interruption
    coordination = coordinator.find_registered(change_id)
    assert coordination is not None
    snapshot = coordination.design_package_snapshot
    assert snapshot is not None
    package = application.read_design_session(change_id)
    assert snapshot.package_id == package.package_id
    assert package.intent_bytes == intent
    assert package.design_bytes == design
    assert snapshot.snapshot_head == coordination.last_reviewed_commit
    package_paths = {
        f".owlbear/delivery/packages/{change_id}/authority.json",
        f".owlbear/delivery/packages/{change_id}/design.md",
        f".owlbear/delivery/packages/{change_id}/intent.md",
        f".owlbear/delivery/packages/{change_id}/manifest.json",
    }
    tree_paths = _git(
        application._workspace_manager.repository,
        "ls-tree",
        "-r",
        "--name-only",
        coordination.branch,
    ).splitlines()
    assert set(tree_paths) >= package_paths


def _retain_reviewed_same_task_handoff(application, builder) -> None:
    """N10-H H7: a Builder commit retained by a same-task handoff, as while its person-only check is answered."""
    worktree = builder.worktree_path
    (worktree / "README.md").write_text("usage\n", encoding="utf-8")
    _git(worktree, "add", "README.md")
    _git(worktree, "commit", "-q", "-m", "docs: usage")
    retry = RetryDelivery(
        action="retry",
        outcome_id=builder.outcome_id,
        claim_id=builder.claim.claim_id,
        attempt_id=builder.claim.attempt_id,
        abandoned_commit=_git(worktree, "rev-parse", "HEAD"),
    )
    _settle_builder_handoff_attempt(
        application,
        builder.claim,
        DeliveryBuilderInvocationSettlement(
            change_id=builder.change_id,
            outcome_id=builder.outcome_id,
            claim_id=builder.claim.claim_id,
            attempt_id=builder.claim.attempt_id,
            task_id=builder.task_id,
            expected_last_reviewed_commit=builder.last_reviewed_commit,
            disposition="normal-return",
            request=retry,
        ),
    )


@pytest.mark.parametrize(
    "case",
    ["workspace-changed", "added-after-capture", "unmerged-index", "planning-route", "dirty-submodule", "same-task"],
)
def test_design_return_release_refusal_changes_nothing(tmp_path: Path, case: str) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    runtime = runtimes["change-a"]
    _completed_task, _original_task, _first_result, builder = _seed_two_task_builder(
        application, runtimes, coordinator, state_root
    )
    worktree = builder.worktree_path
    if case == "dirty-submodule":
        child = tmp_path / "child"
        child.mkdir()
        _git(child, "init", "-q")
        (child / "child.txt").write_text("committed child bytes\n", encoding="utf-8")
        _git(child, "add", "child.txt")
        _git(child, "-c", "user.name=Child", "-c", "user.email=child@example.invalid", "commit", "-q", "-m", "child")
        _git(worktree, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(child), "sub")
        _git(worktree, "commit", "-q", "-m", "add submodule")
        _git(worktree, "config", "submodule.recurse", "true")
        # A moved gitlink is all the parent capture records; the child edit beside it is not.
        (worktree / "sub" / "child.txt").write_text("committed child move\n", encoding="utf-8")
        _git(worktree / "sub", "-c", "user.name=Child", "-c", "user.email=child@example.invalid", "commit", "-qam", "m")
        (worktree / "sub" / "child.txt").write_text("uncommitted child edit\n", encoding="utf-8")
    target = DeliveryStage.PLANNING if case == "planning-route" else DeliveryStage.DESIGN
    if case == "same-task":
        _retain_reviewed_same_task_handoff(application, builder)
    else:
        _return_builder(application, builder, target=target, unmerged=case == "unmerged-index")
    _change_intent(application, "change-a", DeliveryChangeIntentKind.DEFER, reason="Revise requirements")
    current = application.read_design_session("change-a")

    def revise() -> object:
        return application.revise_design_session("change-a", current.package_id, b"revised intent\n", b"design\n")

    if case == "workspace-changed":
        (worktree / "untracked.txt").write_text("changed after the handoff\n", encoding="utf-8")
    if case == "added-after-capture":
        manager = application._workspace_manager
        run_git = manager._run_git

        def interrupt_reset(*arguments: str, **options: object) -> object:
            if arguments[2:4] == ("reset", "--hard"):
                message = "interrupted reset"
                raise RuntimeError(message)
            return run_git(*arguments, **options)

        with patch.object(manager, "_run_git", side_effect=interrupt_reset), pytest.raises(RuntimeError, match="reset"):
            revise()
        assert coordinator.show("change-a").dirty_worktree_quarantine is not None
        (worktree / "added.txt").write_text("added after capture\n", encoding="utf-8")
    before = (
        runtime.frontier_bytes(),
        coordinator.show("change-a"),
        _workspace_content_snapshot(worktree),
        _file_bytes(tmp_path / "packages" / "change-a"),
    )
    reason = {
        "planning-route": "custody-retained",
        "same-task": "custody-retained: OUT-001 retains a same-task Builder handoff for TASK-002; Resume the Change",
        "unmerged-index": "design-return-unmerged-index",
    }.get(case, "design-return-workspace-changed")

    with pytest.raises(DeliveryRevisionError, match=reason):
        revise()

    if case == "same-task":
        change = application.get_change("change-a")
        (retained,) = (outcome for outcome in change.unresolved_outcomes if outcome.builder_handoff)
        assert (retained.outcome_id, retained.builder_handoff.original_task_id) == ("OUT-001", "TASK-002")
        assert retained.builder_handoff.route == "same-task"

    assert (
        runtime.frontier_bytes(),
        coordinator.show("change-a"),
        _workspace_content_snapshot(worktree),
        _file_bytes(tmp_path / "packages" / "change-a"),
    ) == before


def _revision_intent(
    second: str = "AC-002: The report is retained.",
    *,
    extra_decisions: tuple[str, ...] = (),
    launch_decisions: str = "DEC-001",
) -> bytes:
    blocks = (
        "kind: decision\nid: DEC-001\norigin: approved\nbasis: package approval\nstatement: Revise in place.",
        *extra_decisions,
        (
            f"kind: commitment\nid: COM-001\nclass: agreed-path\ndecisions: [{launch_decisions}]\n"
            "statement: Keep launches."
        ),
        "kind: commitment\nid: COM-002\nclass: agreed-path\ndecisions: [DEC-001]\nstatement: Keep reports.",
        (
            "kind: outcome\nid: OUT-001\ntitle: Launch\npromise: Make the launch observable.\n"
            f'acceptance: ["AC-001: The launch is observable.", "{second}"]\ncommitments: [COM-001]\ndependencies: []'
        ),
        (
            "kind: outcome\nid: OUT-002\ntitle: Report\npromise: Retain the report.\n"
            'acceptance: ["AC-003: The report is complete."]\ncommitments: [COM-002]\ndependencies: []'
        ),
    )
    return ("# change-r\n\n" + "".join(f"```yaml target-contract\n{block}\n```\n\n" for block in blocks)).encode()


def _paused_revision_change(tmp_path: Path, *, pause: bool = True, covered: bool = False):
    """Admit an authored Change with one completed and one pending OUT-001 task and a completed OUT-002."""
    application, _runtimes, coordinator, state_root = _portfolio(tmp_path, {})
    application.create_design_session("change-r", _revision_intent(), b"# Architecture\n")
    admitted = application.admit_delivery_change(
        DeliveryAdmissionRequest(
            change_id="change-r",
            expected_package_id=_approved_package_id(application, "change-r"),
            active_claim_ids=(),
        )
    )
    head = coordinator.show("change-r").last_reviewed_commit
    launch, report = admitted.frontier.bindings
    completed = _task().model_copy(update={"task_id": "TASK-001", "plan_scope_id": launch.plan_scope_id})
    remaining = completed.model_copy(update={"task_id": "TASK-002", "dependency_ids": ("TASK-001",)})
    reported = completed.model_copy(
        update={
            "task_id": "TASK-003",
            "outcome_id": "OUT-002",
            "plan_scope_id": report.plan_scope_id,
            "commitment_ids": ("COM-002",),
        }
    )
    digest = admitted.contract_digest
    covers = (acceptance_criteria(admitted.contract)[0].ref,) if covered else ()
    seeded = admitted.frontier.model_copy(
        update={
            "bindings": (
                launch.model_copy(
                    update={
                        "stage": DeliveryStage.IMPLEMENTATION,
                        "tasks": (completed, remaining),
                        "results": (_task_result("RESULT-001", "change-r", digest, completed, head, covers=covers),),
                    }
                ),
                report.model_copy(
                    update={
                        "stage": DeliveryStage.COMPLETED,
                        "tasks": (reported,),
                        "results": (_task_result("RESULT-003", "change-r", digest, reported, head),),
                    }
                ),
            ),
            "published_head": head,
            "pending_checkpoint": None,
        }
    )
    change_root = state_root / "changes/change-r"
    (change_root / "frontier.json").write_bytes(_canonical(seeded))
    (change_root / "state-publication.json").unlink()
    if pause:
        _change_intent(application, "change-r", DeliveryChangeIntentKind.DEFER, reason="Revise requirements")
    return application, coordinator, state_root, seeded


def _revision_request(application: PortfolioApplication) -> DeliveryAdmissionRequest:
    """Return the request an agent can form: the package ID and the frontier digest from ``get_change``."""
    return DeliveryAdmissionRequest(
        change_id="change-r",
        expected_package_id=_approved_package_id(application, "change-r"),
        active_claim_ids=(),
        expected_frontier_digest=application.get_change("change-r").frontier_digest,
    )


def test_paused_change_revision_replans_changed_outcome_and_replays(tmp_path: Path) -> None:
    application, coordinator, state_root, seeded = _paused_revision_change(tmp_path)
    before = coordinator.show("change-r")
    current = application.read_design_session("change-r")
    revised_intent = _revision_intent("AC-002: The report is revised.")
    application.revise_design_session("change-r", current.package_id, revised_intent, current.design_bytes)
    request = _revision_request(application)

    activated = application.admit_change(request)
    replayed = application.admit_change(request)

    after = coordinator.show("change-r")
    replanned, unchanged = activated.frontier.bindings
    assert (activated.replayed, replayed.replayed) == (False, True)
    assert unchanged == seeded.bindings[1]
    assert replanned.stage is DeliveryStage.PLANNING
    assert replanned.tasks == seeded.bindings[0].tasks[:1]
    assert replanned.results == seeded.bindings[0].results
    assert replanned.return_context is not None
    assert replanned.return_context.locators == ("AC-002",)
    assert _git(tmp_path / "repository", "rev-list", "--parents", "-n", "1", after.last_reviewed_commit).split()[
        1:
    ] == [before.last_reviewed_commit]
    assert after.design_package_snapshot.package_id == application.read_design_session("change-r").package_id
    assert activated.frontier.change_deferral is None
    assert application._runtimes["change-r"].pending_state_publication() is not None
    assert len(list((state_root / "changes/change-r/revisions").iterdir())) == 1
    launches = application.acquire_frontier_work().launch_packages
    assert [(launch.outcome_id, launch.claim.worker_role) for launch in launches] == [
        ("OUT-001", DeliveryWorkerRole.PLANNER)
    ]


def test_revision_reports_decision_delta_and_plan_context_carries_decisions(tmp_path: Path) -> None:
    application, _coordinator, state_root, seeded = _paused_revision_change(tmp_path, pause=False)
    answered = DeliveryRequest(
        request_id="REQ-PATH",
        kind=DeliveryRequestKind.DECISION,
        outcome_id="OUT-001",
        summary="Choose the launch path",
        options=(DeliveryRequestOption(option_id="a", label="a"), DeliveryRequestOption(option_id="b", label="b")),
        resolution=DeliveryRequestResolution(selected_option_id="a", provenance="user-confirmed"),
    )
    launch, report = seeded.bindings
    (state_root / "changes/change-r/frontier.json").write_bytes(
        _canonical(
            seeded.model_copy(update={"bindings": (launch.model_copy(update={"requests": (answered,)}), report)})
        )
    )
    _change_intent(application, "change-r", DeliveryChangeIntentKind.DEFER, reason="Revise requirements")
    current = application.read_design_session("change-r")
    path_b = (
        'kind: decision\nid: DEC-002\norigin: decided\nbasis: askQuestions 2026-10-08 "Launch path?"\n'
        "statement: Launch through path b.\nsupersedes: [REQ-PATH]"
    )
    revised = _revision_intent("AC-002: The report is revised.", extra_decisions=(path_b,))
    application.revise_design_session("change-r", current.package_id, revised, current.design_bytes)

    derived = application.derive_delivery_contract("change-r")

    assert derived.decision_delta is not None
    assert [item.decision_id for item in derived.decision_delta.added] == ["DEC-002"]
    assert derived.decision_delta.superseded_request_ids == ("REQ-PATH",)
    assert derived.decision_delta.changed_admitted_ids == ()
    application.admit_change(_revision_request(application))
    (planner,) = application.acquire_frontier_work().launch_packages
    context = application.show_plan_context(
        "change-r", planner.outcome_id, planner.claim.attempt_id, planner.claim.claim_id
    )
    assert [(item.decision_id, item.origin.value) for item in context.decisions] == [
        ("DEC-001", "approved"),
        ("DEC-002", "decided"),
    ]
    assert [item.request_id for item in context.requests] == ["REQ-PATH"]
    assert context.superseded_request_ids == ("REQ-PATH",)
    returned = application.transition_delivery(
        "change-r",
        ReturnDelivery(
            action="return",
            outcome_id=planner.outcome_id,
            claim_id=planner.claim.claim_id,
            target=DeliveryStage.DESIGN,
            reason="The launch path needs another decision.",
            locators=("OUT-001",),
            source_boundary=derived.digest,
        ),
    )
    assert returned.stage is DeliveryStage.DESIGN
    assert [item.request_id for item in returned.requests] == ["REQ-PATH"]


@pytest.mark.parametrize("revision", ["delta", "zero-delta"])
def test_revision_replan_publishes_from_plan_context_alone(tmp_path: Path, revision: str) -> None:
    application, _coordinator, _state_root, seeded = _paused_revision_change(tmp_path, covered=True)
    current = application.read_design_session("change-r")
    retained = '"AC-001: The launch is observable.", "AC-002: The report is retained."'
    revised = (
        _revision_intent("AC-002: The report is revised.")
        if revision == "delta"
        else _revision_intent().replace(retained.encode(), b'"AC-001: The launch is observable."')
    )
    application.revise_design_session("change-r", current.package_id, revised, current.design_bytes)
    application.admit_change(_revision_request(application))
    (planner,) = application.acquire_frontier_work().launch_packages

    context = application.show_plan_context(
        "change-r", planner.outcome_id, planner.claim.attempt_id, planner.claim.claim_id
    ).model_dump(mode="json")

    retained_tasks = tuple(
        DeliveryTaskDefinition.model_validate_json(json.dumps(item)) for item in context["retained_tasks"]
    )
    open_ids = tuple(
        item["acceptance_id"] for item in context["coverage"] if item["status"] not in {"covered", "waived"}
    )
    delta = tuple(
        DeliveryTaskDefinition(
            task_id=f"TASK-NEW-{acceptance_id}",
            outcome_id=context["outcome"]["outcome_id"],
            plan_scope_id=context["launch"]["plan_scope_id"],
            title=f"Satisfy {acceptance_id}",
            result="The revised criterion holds.",
            commitment_ids=tuple(item["commitment_id"] for item in context["commitments"]),
            dependency_ids=(),
            required_outputs=("Revised behavior",),
            maintained_surfaces=("serve/delivery/src/owlbear_delivery/portfolio_application.py",),
            constraints=(),
            exclusions=(),
            acceptance_observations=(f"{acceptance_id}: the revised behavior is observable",),
            proof_boundaries=("PortfolioApplication.show_plan_context",),
        )
        for acceptance_id in open_ids
    )
    candidate = application.publish_delivery_plan(
        "change-r",
        PublishDeliveryPlan(
            outcome_id=planner.outcome_id, claim_id=planner.claim.claim_id, tasks=retained_tasks + delta
        ),
    )
    advanced = application.transition_delivery(
        "change-r",
        AdvanceDelivery(
            action="advance", outcome_id=planner.outcome_id, claim_id=planner.claim.claim_id, output=candidate.output
        ),
    )

    assert retained_tasks == seeded.bindings[0].tasks[:1]
    assert open_ids == (("AC-002",) if revision == "delta" else ())
    assert advanced.stage is (DeliveryStage.IMPLEMENTATION if revision == "delta" else DeliveryStage.COMPLETED)
    assert advanced.results == seeded.bindings[0].results


def test_cancelled_and_repeated_revisions_keep_distinct_history(tmp_path: Path) -> None:
    application, coordinator, state_root, _seeded = _paused_revision_change(tmp_path)
    original = application.read_design_session("change-r")
    head = coordinator.show("change-r").last_reviewed_commit
    revised = application.revise_design_session(
        "change-r", original.package_id, _revision_intent("AC-002: Cancelled."), original.design_bytes
    )
    application.revise_design_session("change-r", revised.package_id, original.intent_bytes, original.design_bytes)

    cancelled = application.admit_change(_revision_request(application))

    assert cancelled.contract_bytes == original.authority_bytes
    assert coordinator.show("change-r").last_reviewed_commit == head
    assert application.read_design_session("change-r").package_id == original.package_id
    _change_intent(application, "change-r", DeliveryChangeIntentKind.DEFER, reason="Revise again")
    current = application.read_design_session("change-r")
    application.revise_design_session(
        "change-r", current.package_id, _revision_intent("AC-002: Revised again."), current.design_bytes
    )

    application.admit_change(_revision_request(application))

    history = sorted(path.name for path in (state_root / "changes/change-r/revisions").iterdir())
    assert len(history) == 2
    assert {classify_kind(f"runtime/changes/change-r/revisions/{name}/frontier.json").kind_id for name in history} == {
        "revision_record"
    }
    assert history[0].split("-")[0] == history[1].split("-")[0] == hashlib.sha256(original.authority_bytes).hexdigest()


def test_cancel_interrupted_after_contract_publication_is_completed_by_resume(tmp_path: Path) -> None:
    """Documented limit (N04 plan G6): the retry is refused until the user's Resume, which finishes the cancel."""
    application, coordinator, state_root, seeded = _paused_revision_change(tmp_path)
    original = application.read_design_session("change-r")
    head = coordinator.show("change-r").last_reviewed_commit
    revised = application.revise_design_session(
        "change-r", original.package_id, _revision_intent("AC-002: Cancelled."), original.design_bytes
    )
    application.revise_design_session("change-r", revised.package_id, original.intent_bytes, original.design_bytes)
    request = _revision_request(application)
    publish = DeliveryAuthorityRegistry._publish_package_contract

    def crash_after_publication(registry: DeliveryAuthorityRegistry, change_id: str, compiled: object) -> str:
        publish(registry, change_id, compiled)
        raise _Crash

    with (
        patch.object(
            DeliveryAuthorityRegistry, "_publish_package_contract", autospec=True, side_effect=crash_after_publication
        ),
        pytest.raises(_Crash),
    ):
        application.admit_change(request)
    package_after_crash = _file_bytes(tmp_path / "packages/change-r")
    with pytest.raises(DeliveryRuntimeConflictError, match="requires resumption"):
        application.admit_change(request)
    _change_intent(application, "change-r", DeliveryChangeIntentKind.RESUME)

    coordination = coordinator.show("change-r")
    runtime = application._runtimes["change-r"]
    assert _file_bytes(tmp_path / "packages/change-r") == package_after_crash
    assert runtime.change_deferral() is None
    assert [binding.stage for binding in runtime.bindings()] == [binding.stage for binding in seeded.bindings]
    assert coordination.design_package_snapshot_intent is None
    assert coordination.last_reviewed_commit == head
    assert coordination.design_package_snapshot.package_id == original.package_id
    assert application.read_design_session("change-r").package_id == original.package_id
    assert not (state_root / "changes/change-r/revisions").exists()
    assert application.acquire_frontier_work().launch_packages


@pytest.mark.parametrize("child", ["snapshot", "unrelated"])
def test_interrupted_revision_snapshot_reports_only_unrelated_head_drift(tmp_path: Path, child: str) -> None:
    application, coordinator, _state_root, _seeded = _paused_revision_change(tmp_path)
    current = application.read_design_session("change-r")
    application.revise_design_session(
        "change-r", current.package_id, _revision_intent("AC-002: The report is revised."), current.design_bytes
    )
    request = _revision_request(application)
    crash = (
        patch("owlbear_delivery.workspace_snapshots.ChangeDesignPackageSnapshotReceipt.create", side_effect=_Crash)
        if child == "snapshot"
        else patch.object(application._workspace_manager, "_commit_design_package_snapshot", side_effect=_Crash)
    )
    with crash, pytest.raises(_Crash):
        application.admit_change(request)
    coordination = coordinator.show("change-r")
    observed = (
        _git(tmp_path / "repository", "rev-parse", coordination.branch)
        if child == "snapshot"
        else _commit_local_descendant(coordination, "unrelated.txt")
    )

    codes = {diagnostic.code for diagnostic in application.delivery_health().diagnostics}

    assert coordination.design_package_snapshot_intent is not None
    assert observed != coordination.last_reviewed_commit
    assert ("local-change-head-out-of-band" in codes) is (child == "unrelated")
    if child == "snapshot":
        assert application.admit_change(request).frontier.change_deferral is None


@pytest.mark.parametrize("case", ["pause-pending", "change-terminal", "publication-pending", "reviewed-head-moved"])
def test_requirement_revision_refusal_changes_nothing(tmp_path: Path, case: str) -> None:
    application, coordinator, state_root, _seeded = _paused_revision_change(
        tmp_path, pause=case in {"publication-pending", "reviewed-head-moved"}
    )
    change_root = state_root / "changes/change-r"
    current = application.read_design_session("change-r")
    revised = _revision_intent("AC-002: The report is revised.")
    if case == "pause-pending":
        assert application.acquire_frontier_work().launch_packages
        _change_intent(application, "change-r", DeliveryChangeIntentKind.DEFER, reason="Revise requirements")
    elif case == "change-terminal":
        _change_intent(application, "change-r", DeliveryChangeIntentKind.ABANDON, reason="Stop")
    else:
        current = application.revise_design_session("change-r", current.package_id, revised, current.design_bytes)
        application._replay_pending_state_publications("change-r")
        if case == "publication-pending":
            (change_root / "state-publication.json").write_bytes(
                _canonical(DeliveryPendingStatePublication.pending("1" * 64, "2" * 64))
            )
        else:
            _commit_local_descendant(coordinator.show("change-r"))
    branch = coordinator.show("change-r").branch
    repository = tmp_path / "repository"
    before = (
        _file_bytes(change_root),
        coordinator.coordination_bytes("change-r"),
        _file_bytes(tmp_path / "packages/change-r"),
        _git(repository, "rev-parse", branch),
    )

    def refused_call() -> object:
        if case in {"publication-pending", "reviewed-head-moved"}:
            return application.admit_change(_revision_request(application))
        return application.revise_design_session("change-r", current.package_id, revised, current.design_bytes)

    with pytest.raises(DeliveryRevisionError, match=case) as refused:
        refused_call()

    assert refused.value.reason == case
    assert before == (
        _file_bytes(change_root),
        coordinator.coordination_bytes("change-r"),
        _file_bytes(tmp_path / "packages/change-r"),
        _git(repository, "rev-parse", branch),
    )


def test_finalized_change_revision_requires_review_repair_and_clears_finalization(tmp_path: Path) -> None:
    application, runtime, _provider, _state, _exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    current = application.read_design_session("change-a")
    with pytest.raises(DeliveryRevisionError, match="change-finalized"):
        application.revise_design_session("change-a", current.package_id, _revision_intent(), current.design_bytes)
    application.prepare_review_repair("change-a")
    _change_intent(application, "change-a", DeliveryChangeIntentKind.DEFER, reason="Revise requirements")
    application.revise_design_session("change-a", current.package_id, _revision_intent(), current.design_bytes)

    activated = application.admit_change(
        DeliveryAdmissionRequest(
            change_id="change-a",
            expected_package_id=_approved_package_id(application, "change-a"),
            active_claim_ids=(),
            expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
        )
    )

    assert activated.frontier.finalization is None
    assert activated.frontier.finalization_invalidation is None
    assert activated.frontier.ready is None
    assert activated.frontier.change_deferral is None
    assert {binding.stage for binding in activated.frontier.bindings} == {DeliveryStage.PLANNING}


def test_admission_snapshots_design_before_initial_pull_request(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(tmp_path, {})
    intent = b"""# Initial package

## Problem And Product Promise

The initial package needs a published boundary.

Publish the stable package before workers run.

```yaml target-contract
kind: commitment
id: COM-001
class: agreed-path
decisions: [DEC-001]
statement: Preserve the admitted package.
```

```yaml target-contract
kind: decision
id: DEC-001
origin: approved
basis: admission fixture
statement: Fixture decision.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Publish initial package
promise: Publish the stable package before workers run.
acceptance: ["AC-001: The initial package is published."]
commitments: [COM-001]
dependencies: []
```
"""
    application.create_design_session("change-a", intent, b"# Architecture\n")
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(
        request.published_head,
        operation_id=request.operation_id,
    )
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head,
    )
    state_publisher = Mock()
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher
    application._delivery_state_publisher = state_publisher

    admission_request = DeliveryAdmissionRequest(
        change_id="change-a",
        expected_package_id=_approved_package_id(application, "change-a"),
        active_claim_ids=(),
    )
    admitted = application.admit_delivery_change(admission_request)
    replayed = application.admit_delivery_change(admission_request)

    coordination = coordinator.show("change-a")
    snapshot = coordination.design_package_snapshot
    assert snapshot is not None
    assert coordination.last_reviewed_commit == snapshot.snapshot_head
    assert admitted.frontier.published_head == snapshot.snapshot_head
    assert admitted.frontier.pending_checkpoint is None
    assert replayed.replayed
    assert replayed.frontier == admitted.frontier
    assert branch_publisher.publish.call_count == 1
    assert pull_request_publisher.publish.call_count == 1
    assert pull_request_publisher.update_generated_summary.call_count == 1
    assert state_publisher.publish.call_count == 1
    branch_request = branch_publisher.publish.call_args.args[0]
    assert branch_request.expected_published_head == snapshot.snapshot_head
    pull_request = pull_request_publisher.publish.call_args.args[0]
    assert pull_request.published_head == snapshot.snapshot_head
    assert "> The initial package needs a published boundary." in pull_request.generated_summary
    assert "> Publish the stable package before workers run." in pull_request.generated_summary
    assert "Promised result: Publish the stable package before workers run." in pull_request.generated_summary
    assert "Outcomes complete: 0 of 1" in pull_request.generated_summary
    assert "admitted Design package" in pull_request.generated_summary
    assert "Do not manually change this PR's draft/ready state or push to its branch." in pull_request.generated_summary
    assert "## Review And Merge" not in pull_request.generated_summary
    assert "/address-pr-feedback change-a" not in pull_request.generated_summary
    assert "merge this pull request in GitHub" not in pull_request.generated_summary
    package_paths = {
        ".owlbear/delivery/packages/change-a/authority.json",
        ".owlbear/delivery/packages/change-a/design.md",
        ".owlbear/delivery/packages/change-a/intent.md",
        ".owlbear/delivery/packages/change-a/manifest.json",
    }
    tree_paths = _git(
        application._workspace_manager.repository,
        "ls-tree",
        "-r",
        "--name-only",
        coordination.branch,
    ).splitlines()
    assert set(tree_paths) >= package_paths


def test_checkpoint_summary_renders_and_escapes_authored_change_content(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(tmp_path, {})
    intent = b"""# Safe summary

## Problem And Product Promise

The goal contains <tag>, @team, #123, and https://example.test.

The intent contains <script>, Fixes #456, @team, https://example.test/path, and `literal`.

```yaml target-contract
kind: commitment
id: COM-001
class: agreed-path
decisions: [DEC-001]
statement: Preserve safe summary rendering.
```

```yaml target-contract
kind: decision
id: DEC-001
origin: approved
basis: fixture approval
statement: Fixture decision.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: "Outcome <tag> @team #7"
promise: "Deliver <script> Fixes #8 @team https://example.test/path `literal`."
acceptance: ["AC-001: The authored content is rendered safely."]
commitments: [COM-001]
dependencies: []
```
"""
    application.create_design_session("change-a", intent, b"# Architecture\n")
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(
        request.published_head,
        operation_id=request.operation_id,
    )
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head,
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    application.admit_delivery_change(
        DeliveryAdmissionRequest(
            change_id="change-a",
            expected_package_id=_approved_package_id(application, "change-a"),
            active_claim_ids=(),
        )
    )

    summary = pull_request_publisher.publish.call_args.args[0].generated_summary
    assert "> The goal contains &lt;tag&gt;, &#64;team, &#35;123, and https&#58;&#47;&#47;example.test." in summary
    assert (
        "> The intent contains &lt;script&gt;, Fixes &#35;456, &#64;team, "
        "https&#58;&#47;&#47;example.test&#47;path, and &#96;literal&#96;."
    ) in summary
    assert "Outcome &lt;tag&gt; &#64;team &#35;7" in summary
    assert (
        "Promised result: Deliver &lt;script&gt; Fixes &#35;8 &#64;team "
        "https&#58;&#47;&#47;example.test&#47;path &#96;literal&#96;."
    ) in summary
    assert "<script>" not in summary
    assert "@team" not in summary
    assert "#123" not in summary
    assert "https://example.test" not in summary
    assert summary.count("## Delivery Status") == 1
    assert "Delivery finalization: recorded" not in summary


def test_checkpoint_summary_scopes_finalization_status_to_its_checkpoint(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    initial_head = coordinator.show("change-a").last_reviewed_commit
    _set_checkpoint(
        runtimes["change-a"],
        state_root,
        DeliveryPendingCheckpoint(
            head=initial_head,
            triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
        ),
    )
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(
        request.published_head,
        operation_id=request.operation_id,
    )
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head,
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    application.reconcile_change_checkpoint("change-a")
    first_summary = pull_request_publisher.update_generated_summary.call_args.args[0].generated_summary
    assert "Delivery finalization: recorded" not in first_summary

    _attach_local_target(application, tmp_path)
    application.sync_change_with_current_target("change-a", "before-summary-finalization")
    finalized_head = coordinator.show("change-a").last_reviewed_commit
    application.finalize_change("change-a", _finalization_request("change-a", finalized_head))
    application.reconcile_change_checkpoint("change-a")

    final_summary = pull_request_publisher.update_generated_summary.call_args.args[0].generated_summary
    assert f"As of reviewed checkpoint `{finalized_head}`:" in final_summary
    assert "Delivery finalization: recorded for this checkpoint" in final_summary
    assert "Independent exact-commit review: passed for this checkpoint" in final_summary
    assert "## Review And Merge" in final_summary
    assert "/address-pr-feedback change-a" in final_summary
    assert "merge this pull request in GitHub" in final_summary


def test_delivery_publication_and_transition_delegate_to_exact_runtimes(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.PLANNING,
            "change-b": DeliveryStage.IMPLEMENTATION,
            "change-c": DeliveryStage.PLANNING,
        },
    )
    plan_launch, build_launch, block_launch = application.acquire_frontier_work().launch_packages
    plan_request = PublishDeliveryPlan(
        outcome_id=plan_launch.outcome_id,
        claim_id=plan_launch.claim.claim_id,
        tasks=(_task(),),
    )

    plan = application.publish_delivery_plan("change-a", plan_request)
    assert application.publish_delivery_plan("change-a", plan_request) == plan
    advanced = application.transition_delivery(
        "change-a",
        AdvanceDelivery(
            action="advance",
            outcome_id="OUT-001",
            claim_id=plan_launch.claim.claim_id,
            output=plan.output,
        ),
    )
    assert advanced.stage == DeliveryStage.IMPLEMENTATION

    build_task = runtimes["change-b"].show_binding("OUT-001").tasks[0]
    product = build_launch.worktree_path / "product.txt"
    product.write_text("completed build\n", encoding="utf-8")
    _git(build_launch.worktree_path, "add", "product.txt")
    _git(build_launch.worktree_path, "commit", "-m", "complete build")
    completed_commit = _git(build_launch.worktree_path, "rev-parse", "HEAD")
    result_request = PublishDeliveryResult(
        outcome_id=build_launch.outcome_id,
        claim_id=build_launch.claim.claim_id,
        result=_task_result(
            "RESULT-PUBLIC",
            "change-b",
            runtimes["change-b"].authority_digest,
            build_task,
            completed_commit,
        ),
    )
    result = application.publish_delivery_result("change-b", result_request)
    assert application.publish_delivery_result("change-b", result_request) == result

    request = DeliveryRequest(
        request_id="request-public",
        kind=DeliveryRequestKind.DECISION,
        outcome_id="OUT-001",
        summary="Choose the exact source.",
        options=(DeliveryRequestOption(option_id="local", label="Local source"),),
    )
    blocked = application.transition_delivery(
        "change-c",
        BlockDelivery(
            action="block",
            outcome_id="OUT-001",
            claim_id=block_launch.claim.claim_id,
            block_id="block-public",
            reason="A source decision is required.",
            unblock_condition="The source is selected.",
            expected_evidence=("Selected source",),
            locators=("COM-001",),
            request=request,
        ),
    )
    assert blocked.requests == (request,)
    assert blocked.block is not None
    assert blocked.block.request_id == request.request_id


@pytest.mark.parametrize("interrupted", [False, True])
@pytest.mark.parametrize("crash_owner", ["workspace", "runtime"])
def test_submit_result_promotes_and_replays_exact_builder_result(
    tmp_path: Path, crash_owner: str, *, interrupted: bool
) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    launch = application.acquire_frontier_work().launch_packages[0]
    runtime = runtimes["change-a"]
    task = runtime.show_binding("OUT-001").tasks[0]
    product = launch.worktree_path / "product.txt"
    product.write_text("completed build\n", encoding="utf-8")
    _git(launch.worktree_path, "add", product.name)
    _git(launch.worktree_path, "commit", "-m", "complete build")
    completed_commit = _git(launch.worktree_path, "rev-parse", "HEAD")
    submission = DeliveryResultSubmission(
        change_id="change-a",
        outcome_id="OUT-001",
        claim_id=launch.claim.claim_id,
        result=_task_result(
            "RESULT-SUBMIT",
            "change-a",
            runtime.authority_digest,
            task,
            completed_commit,
        ),
    )

    application.publish_delivery_result(
        "change-a",
        PublishDeliveryResult(outcome_id=submission.outcome_id, claim_id=submission.claim_id, result=submission.result),
    )
    assert RetryLedger(state_root, "change-a").read().episodes[0].total_attempts == 1
    assert RetryLedger(state_root, "change-a").read().episodes[0].reset_count == 0

    if interrupted:
        runtime.publish_result(
            PublishDeliveryResult(
                outcome_id=submission.outcome_id, claim_id=submission.claim_id, result=submission.result
            )
        )
        original_commit = RuntimeTransaction.commit

        def interrupted_commit(transaction):
            def fail(stage):
                if stage == "after-first-publication":
                    message = "injected result persistence interruption"
                    raise OSError(message)

            original_commit(
                transaction,
                failure=fail
                if crash_owner == "workspace" or transaction._transaction_id.startswith("delivery-runtime-")
                else None,
            )

        with (
            patch.object(RuntimeTransaction, "commit", interrupted_commit),
            pytest.raises(OSError, match="injected result persistence"),
        ):
            application.submit_result(submission)
        application, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes)
        assert RetryLedger(state_root, "change-a").read().episodes[0].reset_count == (
            1 if crash_owner == "runtime" else 0
        )
    submitted = application.submit_result(submission)
    replayed = application.submit_result(submission)

    with pytest.raises(DeliveryRuntimeConflictError, match="original claim custody"):
        application.submit_result(submission.model_copy(update={"claim_id": "foreign-claim"}))

    assert submitted == replayed
    assert submitted.kind == "submitted"
    assert submitted.result_id == "RESULT-SUBMIT"
    assert submitted.binding.stage is DeliveryStage.COMPLETED
    assert submitted.binding.results == (submission.result,)
    episode = RetryLedger(state_root, "change-a").read().episodes[0]
    assert episode.total_attempts == 0
    assert episode.reset_count == 1
    assert episode.accepted_attempt_ids == (launch.claim.attempt_id,)
    (receipt_path,) = (state_root / "changes/change-a/result-receipts/OUT-001").glob("*.json")
    assert json.loads(receipt_path.read_bytes())["claim_id"] == launch.claim.claim_id
    before = runtime.frontier_bytes()
    custody = coordinator.show("change-a")
    receipt_path.unlink()
    with pytest.raises(DeliveryRuntimeReferenceError, match="original result claim receipt is unavailable"):
        application.submit_result(submission)
    assert runtime.frontier_bytes() == before
    assert coordinator.show("change-a") == custody
    assert not receipt_path.exists()


def test_submit_result_replays_when_another_task_holds_the_claim(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    plan_launch = application.acquire_frontier_work().launch_packages[0]
    second_task = _task().model_copy(
        update={
            "task_id": "TASK-002",
            "title": "Implement the second acquisition step",
        }
    )
    plan = application.publish_delivery_plan(
        "change-a",
        PublishDeliveryPlan(
            outcome_id="OUT-001",
            claim_id=plan_launch.claim.claim_id,
            tasks=(_task(), second_task),
        ),
    )
    application.transition_delivery(
        "change-a",
        AdvanceDelivery(
            action="advance",
            outcome_id="OUT-001",
            claim_id=plan_launch.claim.claim_id,
            output=plan.output,
        ),
    )
    build_launch = application.acquire_frontier_work().launch_packages[0]
    runtime = runtimes["change-a"]
    first_task = runtime.show_binding("OUT-001").tasks[0]
    product = build_launch.worktree_path / "product.txt"
    product.write_text("completed first build\n", encoding="utf-8")
    _git(build_launch.worktree_path, "add", product.name)
    _git(build_launch.worktree_path, "commit", "-m", "complete first build")
    completed_commit = _git(build_launch.worktree_path, "rev-parse", "HEAD")
    submission = DeliveryResultSubmission(
        change_id="change-a",
        outcome_id="OUT-001",
        claim_id=build_launch.claim.claim_id,
        result=_task_result(
            "RESULT-FIRST",
            "change-a",
            runtime.authority_digest,
            first_task,
            completed_commit,
        ),
    )

    first_submission = application.submit_result(submission)
    second_launch = application.acquire_frontier_work().launch_packages[0]
    before_frontier = runtime.frontier_bytes()
    before_coordination = coordinator.show("change-a")
    before_retry_ledger = RetryLedger(state_root, "change-a").read()
    replayed = application.submit_result(submission)

    assert second_launch.claim.task_id == "TASK-002"
    assert replayed.result_id == first_submission.result_id == "RESULT-FIRST"
    assert replayed.binding.active_claim is not None
    assert replayed.binding.active_claim.task_id == "TASK-002"
    assert runtime.frontier_bytes() == before_frontier
    assert coordinator.show("change-a") == before_coordination
    assert RetryLedger(state_root, "change-a").read() == before_retry_ledger


def test_transition_publishes_change_branch_before_delivery_state(
    tmp_path: Path,
) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    launch = application.acquire_frontier_work().launch_packages[0]
    runtime = runtimes["change-a"]
    task = runtime.show_binding("OUT-001").tasks[0]
    product = launch.worktree_path / "product.txt"
    product.write_text("completed build\n", encoding="utf-8")
    _git(launch.worktree_path, "add", product.name)
    _git(launch.worktree_path, "commit", "-m", "complete build")
    completed_commit = _git(launch.worktree_path, "rev-parse", "HEAD")
    result = _task_result(
        "RESULT-ORDERED",
        "change-a",
        runtime.authority_digest,
        task,
        completed_commit,
    )
    candidate = application.publish_delivery_result(
        "change-a",
        PublishDeliveryResult(
            outcome_id="OUT-001",
            claim_id=launch.claim.claim_id,
            result=result,
        ),
    )
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    state_publisher = Mock()

    def publish_state(**kwargs: object) -> object:
        assert branch_publisher.publish.call_count == 1
        assert kwargs["coordination"].last_reviewed_commit == completed_commit
        assert runtime.checkpoint_publication_state().published_head == completed_commit
        return object()

    state_publisher.publish.side_effect = publish_state
    application._change_branch_publisher = branch_publisher
    application._delivery_state_publisher = state_publisher

    advanced = application.transition_delivery(
        "change-a",
        AdvanceDelivery(
            action="advance",
            outcome_id="OUT-001",
            claim_id=launch.claim.claim_id,
            output=candidate.output,
        ),
    )

    assert advanced.stage == DeliveryStage.COMPLETED
    pending = runtime.checkpoint_publication_state().pending_checkpoint
    assert pending is not None
    assert pending.head == completed_commit
    assert state_publisher.publish.call_count == 1


def test_snapshot_repair_rejects_remote_head_mismatch_without_clearing_health(
    tmp_path: Path,
) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    runtime = runtimes["change-a"]
    reviewed_head = coordinator.show("change-a").last_reviewed_commit
    application._startup_health_diagnostics = (
        DeliveryHealthDiagnostic(
            source="remote-state",
            code="remote-state-reconciliation-required",
            detail="remote Change branch differs from Delivery-state snapshot: change-a",
            change_id="change-a",
            reason=DeliveryHealthReason.REMOTE_CHANGE_HEAD_MISMATCH,
        ),
    )
    application._reconcile_runtimes()
    state_publisher = Mock()
    state_publisher.read_snapshot_inventory.return_value = Mock(
        remote_head=reviewed_head,
        snapshots=(
            Mock(
                change_id="change-a",
                contract=runtime.contract,
                frontier=DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True),
            ),
        ),
    )
    application._delivery_state_publisher = state_publisher

    with pytest.raises(PortfolioApplicationError, match="diagnostic is absent or incompatible"):
        application.repair_delivery_state_snapshot(
            "change-a",
            "repair-remote-head-mismatch",
            confirmed_repair=True,
        )

    assert state_publisher.publish.call_count == 0
    assert application.delivery_health().status == DeliveryHealthStatus.ATTENTION


def test_out_of_band_head_recovery_preserves_commit_and_republishes_reviewed_state(
    tmp_path: Path,
) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    remote_head = coordination.last_reviewed_commit
    reviewed_head = _commit_reviewed_head(
        application,
        coordination,
        "reviewed.txt",
        "reviewed\n",
        "reviewed boundary",
    )
    frontier_path = state_root / "changes/change-a/frontier.json"
    frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
    frontier_path.write_bytes(_canonical(frontier.model_copy(update={"published_head": remote_head})))
    out_of_band_head = _commit_local_descendant(coordination, "out-of-band.txt")
    application._startup_health_diagnostics = (
        DeliveryHealthDiagnostic(
            source="remote-state",
            code="remote-state-reconciliation-required",
            detail="remote Change branch differs from Delivery-state snapshot: change-a",
            change_id="change-a",
            reason=DeliveryHealthReason.REMOTE_CHANGE_HEAD_MISMATCH,
            expected_head=reviewed_head,
            observed_head=remote_head,
            observed_local_head=out_of_band_head,
        ),
    )
    application._reconcile_runtimes()
    branch_publisher = Mock()
    branch_publisher.observe_remote_head.return_value = remote_head
    branch_publisher.publish.side_effect = _requested_branch_receipt
    state_publisher = Mock()
    state_publisher.publish.return_value = object()
    pull_request_publisher = Mock()
    pull_request_publisher.update_generated_summary.return_value = _summary_receipt(reviewed_head)
    application._change_branch_publisher = branch_publisher
    application._delivery_state_publisher = state_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    recovered = application.recover_out_of_band_head(
        "change-a",
        reviewed_head,
        remote_head,
        out_of_band_head,
        "recover-out-of-band-change-a",
        confirmed_recovery=True,
    )

    assert recovered.expected_reviewed_head == reviewed_head
    assert recovered.expected_remote_head == remote_head
    assert recovered.observed_branch_head == out_of_band_head
    assert recovered.preserved_head == out_of_band_head
    assert (
        _git(
            application._workspace_manager.repository,
            "rev-parse",
            recovered.preserved_ref,
        )
        == out_of_band_head
    )
    assert _git(application._workspace_manager.repository, "rev-parse", coordination.branch) == reviewed_head
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == reviewed_head
    assert runtimes["change-a"].checkpoint_publication_state().published_head == reviewed_head
    assert runtimes["change-a"].checkpoint_publication_state().pending_checkpoint is None
    assert application.delivery_health().status == DeliveryHealthStatus.HEALTHY
    assert branch_publisher.publish.call_count == 1
    assert state_publisher.publish.call_count == 1


def test_delivery_health_reports_clean_out_of_band_change_head(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    out_of_band_head = _commit_local_descendant(coordinator.show("change-a"), "out-of-band.txt")

    health = application.delivery_health()

    assert health.status == DeliveryHealthStatus.ATTENTION
    assert health.diagnostics == (
        DeliveryHealthDiagnostic(
            source="local-runtime",
            code="local-change-head-out-of-band",
            detail="Local Change branch is outside its reviewed Delivery boundary without adoption evidence.",
            change_id="change-a",
            reason=DeliveryHealthReason.LOCAL_CHANGE_HEAD_OUT_OF_BAND,
            resolution=DeliveryHealthResolution.AUTHORITY_GAP,
            expected_head=coordinator.show("change-a").last_reviewed_commit,
            observed_local_head=out_of_band_head,
        ),
    )


def test_work_item_queries_do_not_resolve_integration_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-b": DeliveryStage.COMPLETED, "change-a": DeliveryStage.PLANNING},
    )
    resolved = []
    integration_context = application._workspace_manager.integration_context

    def record_resolution(change_id: str):
        resolved.append(change_id)
        return integration_context(change_id)

    monkeypatch.setattr(application._workspace_manager, "integration_context", record_resolution)

    listed = application.list_work_items()
    shown = application.show_work_item("change-a", "OUT-001")
    grouped = application.list_work_item_groups()
    detailed = application.show_work_item_view("change-a", "outcome:OUT-001")
    serialized = json.dumps(
        {
            "listed": [item.model_dump(mode="json") for item in listed],
            "shown": shown.model_dump(mode="json"),
        }
    )

    assert tuple((item.change_id, item.work_item_id) for item in listed) == (
        ("change-a", "OUT-001"),
        ("change-b", "OUT-001"),
        ("change-b", "change-b"),
    )
    assert shown.acceptance == ("AC-001: The launch is observable.",)
    assert grouped[0].change_id == "change-a"
    assert detailed.card.work_item_id == "OUT-001"
    assert resolved == []
    assert "internal semantic body sentinel" not in serialized
    assert "internal completion body sentinel" not in serialized


def test_list_changes_returns_the_grouped_portfolio_read_view(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )

    listed = application.list_changes()
    direct = application.portfolio_read_view()

    assert listed == direct
    assert listed.groups[0].change_id == "change-a"


def test_acquire_actions_uses_the_existing_claim_authority(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )

    acquired = application.acquire_actions()

    assert len(acquired.launch_packages) == 1
    assert acquired.launch_packages[0].change_id == "change-a"


def test_put_design_creates_replays_and_cas_revises_authored_package(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(tmp_path, {})
    initial = application.put_design(
        DeliveryDesignPut(
            change_id="design-change",
            intent_bytes=b"initial intent\n",
            design_bytes=b"initial design\n",
        )
    )
    replayed = application.put_design(
        DeliveryDesignPut(
            change_id="design-change",
            intent_bytes=b"initial intent\n",
            design_bytes=b"initial design\n",
        )
    )
    revised = application.put_design(
        DeliveryDesignPut(
            change_id="design-change",
            expected_package_id=initial.package_id,
            intent_bytes=b"revised intent\n",
            design_bytes=b"initial design\n",
        )
    )

    assert replayed.replayed
    assert replayed.package_id == initial.package_id
    assert not revised.replayed
    assert revised.package_id != initial.package_id
    with pytest.raises(DesignPackageConflictError, match="changed before authored revision"):
        application.put_design(
            DeliveryDesignPut(
                change_id="design-change",
                expected_package_id=initial.package_id,
                intent_bytes=b"stale intent\n",
                design_bytes=b"initial design\n",
            )
        )


def test_put_design_rejects_revision_of_unpaused_admitted_change(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    current = application.read_design_session("change-a")

    with pytest.raises(DeliveryRevisionError, match="change-not-paused"):
        application.put_design(
            DeliveryDesignPut(
                change_id="change-a",
                expected_package_id=current.package_id,
                intent_bytes=b"changed intent\n",
                design_bytes=current.design_bytes,
            )
        )

    assert application.read_design_session("change-a") == current


def test_admit_change_uses_the_existing_source_bound_admission_authority(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(tmp_path, {})
    intent = b"""# Admission

```yaml target-contract
kind: commitment
id: COM-001
class: agreed-path
decisions: [DEC-001]
statement: Preserve the admitted package.
```

```yaml target-contract
kind: decision
id: DEC-001
origin: approved
basis: facade fixture
statement: Fixture decision.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Admit the Change
promise: Admit exact source authority.
acceptance: ["AC-001: Admission is observable."]
commitments: [COM-001]
dependencies: []
```
"""
    application.create_design_session("admit-change", intent, b"# Design\n")
    request = DeliveryAdmissionRequest(
        change_id="admit-change",
        expected_package_id=_approved_package_id(application, "admit-change"),
        active_claim_ids=(),
    )

    admitted = application.admit_change(request)

    assert admitted.contract.change_id == "admit-change"
    assert not admitted.replayed


def test_abandoned_publication_detail_projects_cleanup_eligibility(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )

    application.abandon_change("change-a", "User stopped the Change")

    detail = application.show_work_item_view("change-a", "publication")

    assert runtimes["change-a"].change_stage() == DeliveryChangeStage.ABANDONED
    assert detail.publication is not None
    assert detail.publication.worktree_cleanup is not None
    assert detail.publication.worktree_cleanup.eligible is True
    assert detail.publication.worktree_cleanup.blocked_reason is None
    assert detail.publication.worktree_cleanup.completion_id is None


def test_abandoned_change_is_removed_from_current_work_portfolio(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )

    application.abandon_change("change-a", "User stopped the Change")

    assert application.list_work_item_groups() == ()
    assert application.portfolio_operating_view().statuses == ()


def test_publication_detail_projects_preserved_target_sync_conflict(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    reviewed_head = coordinator.show("change-a").last_reviewed_commit
    conflict = ChangeTargetSyncConflictState.create(
        operation_id="sync-view",
        change_id="change-a",
        target_head="2" * 40,
        change_head_before=reviewed_head,
        conflict_paths=("src/app.py", "tests/test_app.py"),
    )
    runtimes["change-a"].capture_target_sync_conflict(
        "sync-view",
        "2" * 40,
        datetime.now(UTC),
        ("target synchronization merge conflict", "conflict-path:src/app.py"),
    )
    coordinator.update(coordinator.show("change-a").model_copy(update={"target_sync_conflict": conflict}))

    detail = application.show_work_item_view("change-a", "publication")

    assert detail.publication is not None
    assert detail.publication.target_sync_conflict is not None
    assert detail.publication.target_sync_conflict.model_dump() == {
        "conflict_id": conflict.conflict_id,
        "operation_id": conflict.operation_id,
        "target_head": conflict.target_head,
        "change_head_before": conflict.change_head_before,
        "conflict_paths": conflict.conflict_paths,
    }


def test_dirty_abandoned_publication_detail_blocks_cleanup(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    application.abandon_change("change-a", "User stopped the Change")
    (coordinator.show("change-a").worktree_path / "notes.txt").write_text("keep me\n", encoding="utf-8")

    detail = application.show_work_item_view("change-a", "publication")

    assert detail.publication is not None
    assert detail.publication.worktree_cleanup is not None
    assert detail.publication.worktree_cleanup.eligible is False
    assert detail.publication.worktree_cleanup.blocked_reason == "worktree-attention"


def test_operator_request_resolution_updates_context_and_resumed_plan(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    launch = application.acquire_frontier_work().launch_packages[0]
    state_publisher = Mock()
    state_publisher.publish.side_effect = [
        None,
        DeliveryStatePublicationError("state unavailable", retry_safe=True),
        None,
    ]
    application._delivery_state_publisher = state_publisher
    context = application.show_operator_context("change-a", "OUT-001")
    serialized_claim = context.active_claim.model_dump(mode="json") if context.active_claim else {}
    assert serialized_claim == {
        "attempt_id": launch.claim.attempt_id,
        "claim_id": launch.claim.claim_id,
        "started_at": launch.claim.started_at,
        "worker_role": "planner",
        "task_id": None,
        "owner_id": launch.claim.owner_id,
    }
    assert not {"process_id", "output", "reviewer_id"} & serialized_claim.keys()
    before = runtimes["change-a"].frontier_bytes()
    with pytest.raises(DeliveryRuntimeConflictError, match="execution identity"):
        _recover_claim(application, "change-a", "OUT-001", "stale-attempt", launch.claim.claim_id)
    assert runtimes["change-a"].frontier_bytes() == before

    request = DeliveryRequest(
        request_id="request-operator",
        kind=DeliveryRequestKind.DECISION,
        outcome_id="OUT-001",
        summary="Choose the source.",
        options=(DeliveryRequestOption(option_id="local", label="Use local source"),),
    )
    application.transition_delivery(
        "change-a",
        BlockDelivery(
            action="block",
            outcome_id="OUT-001",
            claim_id=launch.claim.claim_id,
            block_id="block-operator",
            reason="A decision is required.",
            unblock_condition="The source is selected.",
            expected_evidence=("Selected source",),
            locators=("COM-001",),
            request=request,
        ),
    )
    assert state_publisher.publish.call_count == 1
    pending = application.show_operator_context("change-a", "OUT-001")
    assert pending.block is not None
    assert not pending.block.resolved
    resolution = DeliveryRequestResolution(
        selected_option_id="local",
        response_text="Use the checked-in source.",
        provenance="user-confirmed",
    )
    with pytest.raises(DeliveryStatePublicationError, match="state unavailable"):
        application.resolve_request("change-a", request.request_id, resolution)
    resolved = application.resolve_request("change-a", request.request_id, resolution)
    assert resolved.resolution is not None
    assert state_publisher.publish.call_count == 3
    current = application.show_operator_context("change-a", "OUT-001")
    assert current.block is not None
    assert current.block.resolved
    application._clock = lambda: "2026-08-04T00:00:01Z"
    resumed = application.acquire_frontier_work().launch_packages[0]
    plan_context = application.show_plan_context(
        "change-a",
        "OUT-001",
        resumed.claim.attempt_id,
        resumed.claim.claim_id,
    )
    assert plan_context.requests[0].resolution == resolved.resolution


@pytest.mark.parametrize("dirty", [False, True])
def test_live_implementation_block_does_not_publish_or_release_without_exclusion(
    tmp_path: Path, *, dirty: bool
) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    launch = application.acquire_frontier_work().launch_packages[0]
    candidate_path = launch.worktree_path / "candidate.txt"
    candidate_path.write_text("preserved Builder candidate\n", encoding="utf-8")
    _git(launch.worktree_path, "add", candidate_path.name)
    _git(launch.worktree_path, "commit", "-m", "preserve Builder candidate")
    candidate_head = _git(launch.worktree_path, "rev-parse", "HEAD")
    request = DeliveryRequest(
        request_id="request-implementation",
        kind=DeliveryRequestKind.ACTION,
        outcome_id="OUT-001",
        summary="Repair the external runtime prerequisite.",
    )
    transition = BlockDelivery(
        action="block",
        outcome_id="OUT-001",
        claim_id=launch.claim.claim_id,
        block_id="block-implementation",
        reason="The external runtime prerequisite is unavailable.",
        unblock_condition="The prerequisite is repaired.",
        expected_evidence=("Successful implementation proof",),
        locators=("TASK-001",),
        request=request,
        resume_commit=candidate_head,
    )
    if dirty:
        candidate_path.write_text("staged Builder work\n", encoding="utf-8")
        _git(launch.worktree_path, "add", candidate_path.name)
        candidate_path.write_text("unstaged Builder work\n", encoding="utf-8")

    runtime = runtimes["change-a"]
    before_frontier = runtime.frontier_bytes()
    before_coordination = coordinator.show("change-a")
    before_workspace = _workspace_mutation_snapshot(launch.worktree_path)
    ledger = RetryLedger(state_root, "change-a")
    before_ledger = ledger.read()
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application.transition_delivery("change-a", transition)

    attention = runtime.show_binding("OUT-001").recovery_attention
    assert attention is not None
    assert attention.reason == "The external runtime prerequisite is unavailable."
    before = DeliveryFrontier.model_validate_json(before_frontier)
    after = DeliveryFrontier.model_validate_json(runtime.frontier_bytes())
    assert (
        after.model_copy(
            update={
                "bindings": tuple(binding.model_copy(update={"recovery_attention": None}) for binding in after.bindings)
            }
        )
        == before
    )
    assert coordinator.show("change-a") == before_coordination
    assert runtime.show_binding("OUT-001").active_claim_id == launch.claim.claim_id
    assert _git(launch.worktree_path, "rev-parse", "HEAD") == candidate_head
    assert application.show_operator_context("change-a", "OUT-001").block is None
    retained_frontier = runtime.frontier_bytes()
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application.transition_delivery("change-a", transition)
    assert runtime.frontier_bytes() == retained_frontier
    reopened, reopened_coordinator, _manager = _reopen_portfolio(tmp_path, state_root, runtimes)
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        reopened.transition_delivery("change-a", transition)
    _assert_contained_builder_views(reopened, transition, launch.claim)
    with pytest.raises(DeliveryRuntimeReferenceError):
        reopened.resolve_request(
            "change-a",
            request.request_id,
            DeliveryRequestResolution(response_text="Prerequisite repaired.", provenance="user-confirmed"),
        )
    with pytest.raises(DeliveryRuntimeConflictError):
        reopened.clear_block("change-a", "OUT-001", transition.block_id, "Repaired.", ("proof",))
    assert reopened.acquire_frontier_work().launch_packages == ()
    assert reopened._runtimes["change-a"].frontier_bytes() == retained_frontier
    assert reopened_coordinator.show("change-a") == before_coordination
    assert _workspace_mutation_snapshot(launch.worktree_path) == before_workspace
    assert ledger.read() == before_ledger


@pytest.mark.parametrize("action", ["block", "return"])
@pytest.mark.parametrize("foreign_identity", ["claim", "outcome", "head", "request-or-attempt"])
def test_foreign_builder_transition_cannot_publish_diagnostic_attention(
    tmp_path: Path, action: str, foreign_identity: str
) -> None:
    application, runtimes, coordinator, state_root, launch, transition = builder_transition_case(tmp_path, action)
    updates = {
        "claim": {"claim_id": "foreign-claim"},
        "outcome": {"outcome_id": "OUT-999"},
        "head": {"resume_commit" if action == "block" else "preserved_commit": "f" * 40},
        "request-or-attempt": (
            {"request": transition.request.model_copy(update={"outcome_id": "OUT-999"})}
            if isinstance(transition, BlockDelivery)
            else {"attempt_id": "foreign-attempt"}
        ),
    }
    transition = transition.model_copy(update=updates[foreign_identity])
    runtime = runtimes["change-a"]
    before_frontier = runtime.frontier_bytes()
    before_coordination = coordinator.show("change-a")
    before_workspace = _workspace_mutation_snapshot(launch.worktree_path)
    ledger = RetryLedger(state_root, "change-a")
    before_ledger = ledger.read()
    with pytest.raises(
        (DeliveryRuntimeConflictError, DeliveryRuntimeReferenceError, DeliveryWorkerExclusionRequiredError)
    ):
        application.transition_delivery("change-a", transition)
    assert runtime.frontier_bytes() == before_frontier
    assert coordinator.show("change-a") == before_coordination
    assert _workspace_mutation_snapshot(launch.worktree_path) == before_workspace
    assert ledger.read() == before_ledger


def test_requestless_clear_requires_evidence_and_exact_outcome(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    state_publisher = Mock()
    state_publisher.publish.side_effect = [
        None,
        DeliveryStatePublicationError("state unavailable", retry_safe=True),
        None,
    ]
    application._delivery_state_publisher = state_publisher
    launch = application.acquire_frontier_work().launch_packages[0]
    application.transition_delivery(
        "change-a",
        BlockDelivery(
            action="block",
            outcome_id="OUT-001",
            claim_id=launch.claim.claim_id,
            block_id="block-manual",
            reason="Verification is pending.",
            unblock_condition="Verification is recorded.",
            expected_evidence=("Verification locator",),
            locators=("RESULT-001",),
        ),
    )
    assert state_publisher.publish.call_count == 1
    before = runtimes["change-a"].frontier_bytes()
    with pytest.raises(ValueError, match="operator note and locators"):
        application.clear_block("change-a", "OUT-001", "block-manual", "Verified.", ())
    assert runtimes["change-a"].frontier_bytes() == before
    with pytest.raises(DeliveryStatePublicationError, match="state unavailable"):
        application.clear_block("change-a", "OUT-001", "block-manual", "Verified.", ("RESULT-001",))
    cleared = application.clear_block("change-a", "OUT-001", "block-manual", "Verified.", ("RESULT-001",))
    assert cleared.block is not None
    assert cleared.block.resolved
    assert state_publisher.publish.call_count == 3


def test_acquisition_replays_failed_portable_state_publication_before_new_claims(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    state_publisher = Mock()
    state_publisher.publish.side_effect = [
        DeliveryStatePublicationError("state unavailable", retry_safe=True),
        None,
    ]
    base_frontier = DeliveryFrontier.model_validate_json(runtimes["change-a"].frontier_bytes(), strict=True)
    state_publisher.read_snapshot_inventory.return_value = Mock(
        remote_head="remote-head",
        snapshots=(Mock(change_id="change-a", frontier=base_frontier),),
    )
    application._delivery_state_publisher = state_publisher
    launch = application.acquire_frontier_work().launch_packages[0]

    with pytest.raises(DeliveryStatePublicationError, match="state unavailable"):
        application.transition_delivery(
            "change-a",
            BlockDelivery(
                action="block",
                outcome_id=launch.outcome_id,
                claim_id=launch.claim.claim_id,
                block_id="block-replay",
                reason="Remote state is temporarily unavailable.",
                unblock_condition="Remote state publication succeeds.",
                expected_evidence=("Published state",),
                locators=("test_portfolio_application.py",),
            ),
        )

    assert runtimes["change-a"].pending_state_publication() is not None
    acquisition = application.acquire_frontier_work()

    assert acquisition.launch_packages == ()
    assert acquisition.failures == ()
    assert runtimes["change-a"].pending_state_publication() is None
    assert state_publisher.publish.call_count == 2


def test_acquisition_replays_pending_state_when_remote_matches_current_frontier(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    state_publisher = Mock()
    state_publisher.publish.side_effect = [
        DeliveryStatePublicationError("state unavailable", retry_safe=True),
        object(),
    ]
    application._delivery_state_publisher = state_publisher
    launch = application.acquire_frontier_work().launch_packages[0]
    with pytest.raises(DeliveryStatePublicationError, match="state unavailable"):
        application.transition_delivery(
            "change-a",
            BlockDelivery(
                action="block",
                outcome_id=launch.outcome_id,
                claim_id=launch.claim.claim_id,
                block_id="block-advanced-remote",
                reason="Remote state is temporarily unavailable.",
                unblock_condition="Remote state publication succeeds.",
                expected_evidence=("Published state",),
                locators=("test_portfolio_application.py",),
            ),
        )
    advanced_snapshot = DeliveryFrontier.model_validate_json(runtimes["change-a"].frontier_bytes(), strict=True)
    state_publisher.read_snapshot_inventory.return_value = Mock(
        remote_head="new-remote-head",
        snapshots=(Mock(change_id="change-a", frontier=advanced_snapshot),),
    )

    acquisition = application.acquire_frontier_work()

    assert acquisition.failures == ()
    assert runtimes["change-a"].pending_state_publication() is None
    assert state_publisher.publish.call_count == 2


def _fail_first_state_publication(application: PortfolioApplication, state_publisher: Mock) -> None:
    application._delivery_state_publisher = state_publisher
    launch = application.acquire_frontier_work().launch_packages[0]
    with pytest.raises(DeliveryStatePublicationError, match="state unavailable"):
        application.transition_delivery(
            "change-a",
            BlockDelivery(
                action="block",
                outcome_id=launch.outcome_id,
                claim_id=launch.claim.claim_id,
                block_id="block-first-publication",
                reason="Remote state is temporarily unavailable.",
                unblock_condition="Remote state publication succeeds.",
                expected_evidence=("Published state",),
                locators=("test_portfolio_application.py",),
            ),
        )


def test_acquisition_replays_first_state_publication_without_remote_snapshot(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    state_publisher = Mock()
    state_publisher.publish.side_effect = [
        DeliveryStatePublicationError("state unavailable", retry_safe=True),
        object(),
    ]
    state_publisher.read_snapshot_inventory.return_value = Mock(
        remote_head="remote-head",
        snapshots=(),
        diagnostics=(),
    )
    _fail_first_state_publication(application, state_publisher)

    acquisition = application.acquire_frontier_work()

    assert acquisition.failures == ()
    assert runtimes["change-a"].pending_state_publication() is None
    assert state_publisher.publish.call_count == 2
    assert state_publisher.publish.call_args.kwargs["expected_remote_head"] == "remote-head"


def test_acquisition_retains_pending_state_when_remote_snapshot_is_quarantined(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    state_publisher = Mock()
    state_publisher.publish.side_effect = [DeliveryStatePublicationError("state unavailable", retry_safe=True)]
    state_publisher.read_snapshot_inventory.return_value = Mock(
        remote_head="remote-head",
        snapshots=(),
        diagnostics=(Mock(change_id="change-a"),),
    )
    _fail_first_state_publication(application, state_publisher)

    acquisition = application.acquire_frontier_work()

    assert [failure.detail for failure in acquisition.failures] == [
        "remote Delivery snapshot is unavailable for pending replay"
    ]
    assert runtimes["change-a"].pending_state_publication() is not None
    assert state_publisher.publish.call_count == 1


def test_acquisition_reanchors_pending_publication_after_authority_revision(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    state_publisher = Mock()
    state_publisher.publish.return_value = object()
    previous_frontier = DeliveryFrontier.model_validate_json(runtimes["change-a"].frontier_bytes(), strict=True)
    previous_digest = hashlib.sha256(runtimes["change-a"].frontier_bytes()).hexdigest()
    state_publisher.read_snapshot_inventory.return_value = Mock(
        remote_head="remote-head",
        snapshots=(Mock(change_id="change-a", frontier=previous_frontier),),
    )
    application._delivery_state_publisher = state_publisher
    revised_frontier = previous_frontier.model_copy(update={"published_head": "a" * 40})
    runtimes["change-a"]._replace_content(
        runtimes["change-a"].frontier_bytes(),
        _canonical(revised_frontier),
        base_frontier_digest=previous_digest,
    )

    acquisition = application.acquire_frontier_work()

    assert len(acquisition.launch_packages) == 1
    assert acquisition.failures == ()
    assert runtimes["change-a"].pending_state_publication() is None
    assert state_publisher.publish.call_count == 1


def test_acquisition_reports_divergent_pending_publication_without_publisher(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    runtime = runtimes["change-a"]
    current = runtime.frontier_bytes()
    revised = _canonical(
        DeliveryFrontier.model_validate_json(current, strict=True).model_copy(update={"published_head": "a" * 40})
    )
    runtime._replace_content(current, revised, base_frontier_digest=hashlib.sha256(current).hexdigest())
    (state_root / "changes/change-a/state-publication.json").write_bytes(
        _canonical(
            DeliveryPendingStatePublication.pending(
                hashlib.sha256(current).hexdigest(),
                "0" * 64,
            )
        )
    )
    application._delivery_state_publisher = None

    acquisition = application.acquire_frontier_work()

    assert acquisition.launch_packages == ()
    assert len(acquisition.failures) == 1
    assert "publisher is unavailable" in acquisition.failures[0].detail
    assert (state_root / "changes/change-a/state-publication.json").exists()


def test_acquisition_acknowledges_pending_publication_when_remote_has_current_frontier(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    state_publisher = Mock()
    state_publisher.publish.return_value = object()
    previous_frontier = DeliveryFrontier.model_validate_json(runtimes["change-a"].frontier_bytes(), strict=True)
    previous_digest = hashlib.sha256(runtimes["change-a"].frontier_bytes()).hexdigest()
    revised_frontier = previous_frontier.model_copy(update={"published_head": "a" * 40})
    runtimes["change-a"]._replace_content(
        runtimes["change-a"].frontier_bytes(),
        _canonical(revised_frontier),
        base_frontier_digest=previous_digest,
    )
    current_frontier = DeliveryFrontier.model_validate_json(runtimes["change-a"].frontier_bytes(), strict=True)
    state_publisher.read_snapshot_inventory.return_value = Mock(
        remote_head="remote-head",
        snapshots=(Mock(change_id="change-a", frontier=current_frontier),),
    )
    application._delivery_state_publisher = state_publisher

    acquisition = application.acquire_frontier_work()

    assert len(acquisition.launch_packages) == 1
    assert acquisition.failures == ()
    assert runtimes["change-a"].pending_state_publication() is None
    assert state_publisher.publish.call_count == 1


def test_corrupt_publication_marker_does_not_block_independent_change(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING},
    )
    marker = state_root / "changes/change-a/state-publication.json"
    marker.write_text("{", encoding="utf-8")

    acquisition = application.acquire_frontier_work()

    assert tuple(launch.change_id for launch in acquisition.launch_packages) == ("change-b",)
    assert any(failure.change_id == "change-a" for failure in acquisition.failures)
    assert application.delivery_health().status.value == "attention"


def test_quarantined_change_pending_marker_is_not_replayed(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    marker_path = state_root / "changes/change-a/state-publication.json"
    marker_path.write_text(
        _canonical(
            DeliveryPendingStatePublication.pending(
                hashlib.sha256(runtimes["change-a"].frontier_bytes()).hexdigest(),
                hashlib.sha256(b"remote-base").hexdigest(),
            )
        ).decode(),
        encoding="utf-8",
    )
    application._runtime_reconciliation_errors["change-a"] = "quarantined for test"
    publisher = Mock()
    application._delivery_state_publisher = publisher

    acquisition = application.acquire_frontier_work()

    assert acquisition.launch_packages == ()
    assert acquisition.failures[0].change_id == "change-a"
    publisher.publish.assert_not_called()


def test_administrative_move_updates_live_projection_and_rejects_same_stage(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    state_publisher = Mock()
    application._delivery_state_publisher = state_publisher
    assert application.show_work_item("change-a", "OUT-001").projection.stage.value == "completed"
    preview = application.preview_administrative_move("change-a", "OUT-001", DeliveryStage.PLANNING)
    move = AdministrativeDeliveryMove(
        move_id="move-operator",
        outcome_id="OUT-001",
        target=DeliveryStage.PLANNING,
        reason="Operator evidence invalidated the reviewed result.",
        expected_version=preview.snapshot_version,
    )
    result = application.administrative_move("change-a", move)
    assert result.invalidated_outcome_ids == ("OUT-001",)
    assert application.show_work_item("change-a", "OUT-001").projection.stage.value == "planning"
    before = runtimes["change-a"].frontier_bytes()
    with pytest.raises(DeliveryRuntimeConflictError, match="earlier stage"):
        application.preview_administrative_move("change-a", "OUT-001", DeliveryStage.PLANNING)
    assert runtimes["change-a"].frontier_bytes() == before

    assert state_publisher.publish.call_count == 1


def test_administrative_move_rejects_active_outcome_claim(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    launch = application.acquire_frontier_work().launch_packages[0]
    preview = application.preview_administrative_move("change-a", "OUT-001", DeliveryStage.PLANNING)
    move = AdministrativeDeliveryMove(
        move_id="move-active-claim",
        outcome_id="OUT-001",
        target=DeliveryStage.PLANNING,
        reason="Invalidate the active result.",
        expected_version=preview.snapshot_version,
    )

    with pytest.raises(DeliveryRuntimeConflictError, match="active mutation claim"):
        application.administrative_move("change-a", move)

    assert runtimes["change-a"].show_binding("OUT-001").active_claim_id == launch.claim.claim_id


def _review_product_change(coordinator: PortfolioCoordinator, change_id: str, content: str) -> tuple[str, str]:
    coordination = coordinator.show(change_id)
    target_head = _git(coordination.worktree_path, "rev-parse", coordination.integration_target)
    (coordination.worktree_path / "product.txt").write_text(content, encoding="utf-8")
    _git(coordination.worktree_path, "add", "product.txt")
    _git(coordination.worktree_path, "commit", "-m", f"reviewed {change_id}")
    reviewed = _git(coordination.worktree_path, "rev-parse", "HEAD")
    coordinator.update(coordination.model_copy(update={"last_reviewed_commit": reviewed}))
    return target_head, reviewed


def _publish_merge_conflict_attention(
    runtimes: dict[str, DeliveryRuntime],
    state_root: Path,
    change_id: str,
    change_head: str,
    target_head: str,
) -> DeliveryIntegrationAttention:
    attention = DeliveryIntegrationAttention(
        attention_id="a" * 64,
        code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
        change_id=change_id,
        change_head=change_head,
        target_head=target_head,
        integration_target="main",
        diagnostics=("merge conflict",),
        retry_condition=(
            "Repair admission is retired; resolve the retained attention or recover the exact legacy claim."
        ),
    )
    runtime = runtimes[change_id]
    frontier_path = state_root / "changes" / change_id / "frontier.json"
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    frontier_path.write_bytes(_canonical(frontier.model_copy(update={"integration_attention": attention})))
    return attention


def _activate_legacy_integration_repair(
    application: PortfolioApplication,
    runtimes: dict[str, DeliveryRuntime],
    coordinator: PortfolioCoordinator,
    state_root: Path,
    change_id: str,
):
    claim = application._new_claim(DeliveryWorkerRole.INTEGRATION_REPAIRER, None)
    runtime = runtimes[change_id]
    frontier_path = state_root / "changes" / change_id / "frontier.json"
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    frontier_path.write_bytes(_canonical(frontier.model_copy(update={"integration_repair_claim": claim})))
    writer = ChangeWriter(
        attempt_id=claim.attempt_id,
        claim_id=claim.claim_id,
        actor_id=claim.owner_id,
        process_id=claim.process_id,
        claimed_at=claim.started_at,
        job_id=1,
        kind="repair",
    )
    coordination = coordinator.acquire(change_id, writer)
    assert coordination.writer == writer
    return claim


def test_acquisition_does_not_create_integration_repair_claim(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    _target_before, reviewed = _review_product_change(coordinator, "change-a", "change side\n")
    repository = tmp_path / "repository"
    (repository / "product.txt").write_text("target side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "concurrent target")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    target_head = _git(repository, "rev-parse", "main")
    application._workspace_manager.refresh_integration_target("change-a")
    _publish_merge_conflict_attention(runtimes, state_root, "change-a", reviewed, target_head)

    acquired = application.acquire_frontier_work()

    assert acquired.integration_attention[0].code == DeliveryIntegrationAttentionCode.MERGE_CONFLICT
    assert runtimes["change-a"].integration_repair_claim() is None
    assert coordinator.show("change-a").writer is None


def test_acquisition_does_not_refresh_target_head(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    initial_target = coordinator.show("change-a").target_head
    repository = tmp_path / "repository"
    (repository / "product.txt").write_text("target side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "concurrent target")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")

    application.acquire_frontier_work()

    assert coordinator.show("change-a").target_head == initial_target


def _prepare_legacy_integration_repair(tmp_path: Path):
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    _target_before, reviewed = _review_product_change(coordinator, "change-a", "change side\n")
    repository = tmp_path / "repository"
    (repository / "product.txt").write_text("target side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "concurrent target")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    target_head = _git(repository, "rev-parse", "main")
    application._workspace_manager.refresh_integration_target("change-a")
    _publish_merge_conflict_attention(runtimes, state_root, "change-a", reviewed, target_head)
    claim = _activate_legacy_integration_repair(application, runtimes, coordinator, state_root, "change-a")
    return application, runtimes, coordinator, state_root, reviewed, claim


def test_repair_recovery_preserves_worktree_without_reacquisition(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root, reviewed, first_claim = _prepare_legacy_integration_repair(
        tmp_path
    )
    worktree = coordinator.show("change-a").worktree_path
    directory_fd = os.open(worktree, os.O_RDONLY)
    try:
        original_directory = os.fstat(directory_fd)

        before = runtimes["change-a"].frontier_bytes()
        custody = coordinator.show("change-a")
        with pytest.raises(DeliveryWorkerExclusionRequiredError):
            application.recover_integration_repair_claim(
                "change-a",
                first_claim.attempt_id,
                first_claim.claim_id,
            )
        acquired = application.acquire_frontier_work()

        assert os.path.samestat(worktree.stat(), original_directory)
        assert _git(worktree, "rev-parse", "HEAD") == reviewed
        assert acquired.launch_packages == ()
        assert runtimes["change-a"].frontier_bytes() == before
        assert runtimes["change-a"].integration_repair_claim() == first_claim
        assert coordinator.show("change-a") == custody
    finally:
        os.close(directory_fd)


def _file_bytes(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_acquisition_returns_bounded_stage_packages_without_integration_work(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-d": DeliveryStage.COMPLETED,
            "change-b": DeliveryStage.IMPLEMENTATION,
            "change-a": DeliveryStage.PLANNING,
        },
    )

    acquired = application.acquire_frontier_work()

    assert tuple(package.change_id for package in acquired.launch_packages) == (
        "change-a",
        "change-b",
    )
    assert tuple(package.claim.worker_role for package in acquired.launch_packages) == (
        DeliveryWorkerRole.PLANNER,
        DeliveryWorkerRole.BUILDER,
    )
    assert acquired.failures == ()
    assert runtimes["change-d"].active_claims() == ()
    assert coordinator.show("change-a").writer is None
    assert coordinator.show("change-b").writer is not None
    assert not (state_root / "capacity.json").exists()

    plan_package, build_package = acquired.launch_packages
    plan_context = application.show_plan_context(
        plan_package.change_id,
        plan_package.outcome_id,
        plan_package.claim.attempt_id,
        plan_package.claim.claim_id,
    )
    build_context = application.show_build_context(
        build_package.change_id,
        build_package.outcome_id,
        build_package.claim.attempt_id,
        build_package.claim.claim_id,
    )
    assert plan_context.outcome.outcome_id == "OUT-001"
    assert build_context.task.task_id == "TASK-001"
    assert build_context.task_digest == build_context.task.digest
    assert build_context.model_dump(mode="json")["task_digest"] == build_context.task.digest
    with pytest.raises(DeliveryRuntimeConflictError, match="execution identity"):
        application.show_plan_context(
            plan_package.change_id,
            plan_package.outcome_id,
            "stale-attempt",
            plan_package.claim.claim_id,
        )
    serialized = "".join(json.dumps(model.model_dump(mode="json")) for model in (acquired, plan_context, build_context))
    for residue in ("intent prose sentinel", "design prose sentinel", '"reviews"', '"receipts"'):
        assert residue not in serialized.lower()


def test_writer_failure_leaves_started_exact_claim_without_false_launch(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.IMPLEMENTATION,
            "change-b": DeliveryStage.PLANNING,
        },
    )
    (tmp_path / "packages/change-b/intent.md").write_text("mutated source\n", encoding="utf-8")

    with patch.object(coordinator, "acquire", side_effect=CoordinationConflictError("injected writer failure")):
        acquired = application.acquire_frontier_work()

    assert acquired.launch_packages == ()
    assert len(acquired.failures) == 2
    failure = acquired.failures[0]
    active = runtimes["change-a"].active_claims()
    assert active[0][1].attempt_id == failure.attempt_id
    assert active[0][1].claim_id == failure.claim_id
    assert runtimes["change-b"].active_claims() == ()
    assert coordinator.show("change-a").writer is None
    before = runtimes["change-a"].frontier_bytes()
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        _recover_claim(application, "change-a", "OUT-001", failure.attempt_id, failure.claim_id)
    assert runtimes["change-a"].frontier_bytes() == before
    assert not (state_root / "capacity.json").exists()


def test_acquisition_retains_expired_planning_claim_at_inclusive_boundary(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
        clock=lambda: now[0],
    )
    first = application.acquire_frontier_work().launch_packages[0]

    now[0] = "2026-08-04T00:59:59Z"
    live = application.acquire_frontier_work()

    assert live.launch_packages == ()
    assert live.failures == ()
    assert runtimes["change-a"].active_claims() == (("OUT-001", first.claim),)

    now[0] = "2026-08-04T01:00:00Z"
    recovered = application.acquire_frontier_work()

    assert len(recovered.failures) == 1
    assert recovered.failures[0].code == DeliveryWorkerExclusionRequiredError.code
    assert recovered.recoveries == ()
    assert recovered.launch_packages == ()
    assert runtimes["change-a"].active_claims() == (("OUT-001", first.claim),)
    assert coordinator.show("change-a").writer is None
    assert not (state_root / "capacity.json").exists()


def test_acquisition_retains_expired_clean_builder_claim_without_relaunch(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
        clock=lambda: now[0],
    )
    first = application.acquire_frontier_work().launch_packages[0]
    (first.worktree_path / "product.txt").write_text("attempt\n", encoding="utf-8")
    _git(first.worktree_path, "add", "product.txt")
    _git(first.worktree_path, "commit", "-m", "attempt commit")
    attempt_commit = _git(first.worktree_path, "rev-parse", "HEAD")

    now[0] = "2026-08-04T01:00:00Z"
    stale = application.acquire_frontier_work()

    assert stale.launch_packages == ()
    assert stale.recoveries == ()
    assert len(stale.failures) == 1
    assert stale.failures[0].claim_id is None
    assert runtimes["change-a"].active_claims() == (("OUT-001", first.claim),)
    assert coordinator.show("change-a").writer == first.writer
    assert _git(first.worktree_path, "rev-parse", "HEAD") == attempt_commit


def test_acquisition_retains_expired_dirty_builder_claim_without_cleanup(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
        clock=lambda: now[0],
    )
    first = application.acquire_frontier_work().launch_packages[0]
    product = first.worktree_path / "product.txt"
    product.write_text("uncommitted attempt\n", encoding="utf-8")

    now[0] = "2026-08-04T01:00:00Z"
    stale = application.acquire_frontier_work()

    assert stale.launch_packages == ()
    assert stale.recoveries == ()
    assert len(stale.failures) == 1
    assert stale.failures[0].claim_id is None
    assert coordinator.show("change-a").writer == first.writer
    assert _git(first.worktree_path, "status", "--porcelain") != ""
    assert (first.worktree_path / "product.txt").read_text(encoding="utf-8") == "uncommitted attempt\n"


def test_expired_claim_recovery_failure_does_not_block_independent_change(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.IMPLEMENTATION,
            "change-b": DeliveryStage.PLANNING,
        },
        execution_capacity=2,
        clock=lambda: now[0],
    )
    initial = application.acquire_frontier_work()
    initial_by_change = {package.change_id: package for package in initial.launch_packages}

    now[0] = "2026-08-04T01:00:00Z"
    original_snapshot = application._workspace_manager.recovery_snapshot

    def fail_change_a(change_id: str, attempt_id: str) -> WorkspaceRecoverySnapshot:
        if change_id == "change-a":
            raise subprocess.CalledProcessError(1, ("git", "status"))
        return original_snapshot(change_id, attempt_id)

    with patch.object(application._workspace_manager, "recovery_snapshot", side_effect=fail_change_a):
        recovered = application.acquire_frontier_work()

    assert recovered.launch_packages == ()
    assert len(recovered.failures) == 2
    assert recovered.failures[0].change_id == "change-a"
    assert recovered.failures[0].claim_id is None
    assert recovered.recoveries == ()
    assert runtimes["change-a"].active_claims()
    assert runtimes["change-b"].active_claims()[0][1] == initial_by_change["change-b"].claim
    assert coordinator.show("change-a").writer == initial_by_change["change-a"].writer


def test_malformed_claim_timestamp_does_not_block_independent_change(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.PLANNING,
            "change-b": DeliveryStage.PLANNING,
        },
        execution_capacity=2,
        clock=lambda: "2026-08-04T01:00:00Z",
    )
    initial = application.acquire_frontier_work()
    initial_by_change = {package.change_id: package for package in initial.launch_packages}
    planner = initial_by_change["change-b"]
    application.transition_delivery(
        "change-b",
        BlockDelivery(
            action="block",
            outcome_id=planner.outcome_id,
            claim_id=planner.claim.claim_id,
            block_id="finished-planner",
            reason="Fixture planner returned a completed blocker.",
            unblock_condition="Fixture evidence is available.",
            expected_evidence=("fixture",),
            locators=("fixture",),
        ),
    )
    runtimes["change-b"].unblock("OUT-001", "finished-planner", "fixture evidence", ("fixture",))
    malformed_path = state_root / "changes/change-a/frontier.json"
    malformed = json.loads(malformed_path.read_bytes())
    malformed["bindings"][0]["active_claim"]["started_at"] = "not-a-timestamp"
    malformed_path.write_bytes((json.dumps(malformed, sort_keys=True, separators=(",", ":")) + "\n").encode())

    application._clock = lambda: "2026-08-04T01:00:01Z"
    recovered = application.acquire_frontier_work()

    assert tuple(package.change_id for package in recovered.launch_packages) == ("change-b",)
    assert len(recovered.failures) == 1
    failure = recovered.failures[0]
    assert failure.change_id == "change-a"
    assert failure.outcome_id == "OUT-001"
    assert failure.claim_id == initial_by_change["change-a"].claim.claim_id
    assert runtimes["change-a"].active_claims()
    assert coordinator.show("change-a").writer is None


def test_execution_capacity_allows_independent_builders_and_planners(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.IMPLEMENTATION,
            "change-b": DeliveryStage.IMPLEMENTATION,
            "change-c": DeliveryStage.PLANNING,
        },
        execution_capacity=3,
    )

    acquired = application.acquire_frontier_work()

    assert tuple(package.change_id for package in acquired.launch_packages) == ("change-a", "change-b", "change-c")
    assert acquired.failures == ()
    assert all(runtimes[change_id].active_claims() for change_id in ("change-a", "change-b", "change-c"))
    assert coordinator.show("change-a").writer is not None
    assert coordinator.show("change-b").writer is not None
    assert coordinator.show("change-c").writer is None
    assert not (state_root / "capacity.json").exists()


@pytest.mark.parametrize("stage", [DeliveryStage.PLANNING])
def test_read_only_claim_recovery_exclusion_required(tmp_path: Path, stage: DeliveryStage) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": stage})
    package = application.acquire_frontier_work().launch_packages[0]

    _assert_recovery_excluded(application, package)
    assert runtimes["change-a"].active_claims() == (("OUT-001", package.claim),)
    assert coordinator.show("change-a").writer is None
    assert not (state_root / "capacity.json").exists()


def test_acquisition_leaves_active_planning_claim_occupied_across_instances(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    interrupted = application.acquire_frontier_work().launch_packages[0]
    before_coordination = coordinator.show("change-a")
    assert not (state_root / "capacity.json").exists()

    reopened, _reopened_coordinator, _reopened_manager = _reopen_portfolio(
        tmp_path,
        state_root,
        runtimes,
        clock=lambda: "2026-08-04T00:00:00Z",
    )
    resumed = reopened.acquire_frontier_work()

    assert resumed.launch_packages == ()
    assert runtimes["change-a"].active_claims() == (("OUT-001", interrupted.claim),)
    assert coordinator.show("change-a") == before_coordination
    assert not (state_root / "capacity.json").exists()


def test_acquisition_leaves_dirty_build_claim_and_custody_unchanged(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    interrupted = application.acquire_frontier_work().launch_packages[0]
    (interrupted.worktree_path / "product.txt").write_text("uncommitted attempt\n", encoding="utf-8")
    before_coordination = coordinator.show("change-a")
    assert not (state_root / "capacity.json").exists()

    resumed = application.acquire_frontier_work()

    assert resumed.launch_packages == ()
    assert runtimes["change-a"].active_claims() == (("OUT-001", interrupted.claim),)
    assert runtimes["change-a"].show_binding("OUT-001").recovery_attention is None
    assert coordinator.show("change-a") == before_coordination
    assert not (state_root / "capacity.json").exists()
    assert (interrupted.worktree_path / "product.txt").read_text(encoding="utf-8") == "uncommitted attempt\n"


def test_acquisition_claims_dirty_builder_for_worker_triage(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    dirty_file = tmp_path / "worktrees/change-a/product.txt"
    dirty_file.write_text("uncommitted source\n", encoding="utf-8")

    acquired = application.acquire_frontier_work()

    assert acquired.failures == ()
    launch = acquired.launch_packages[0]
    assert launch.claim.worker_role == DeliveryWorkerRole.BUILDER
    assert launch.writer == coordinator.show("change-a").writer
    context = application.show_build_context(
        launch.change_id,
        launch.outcome_id,
        launch.claim.attempt_id,
        launch.claim.claim_id,
    )
    assert context.launch == launch
    assert runtimes["change-a"].active_claims() == (("OUT-001", launch.claim),)
    _assert_recovery_excluded(application, launch)
    assert _git(launch.worktree_path, "status", "--porcelain") != ""
    assert _git(launch.worktree_path, "rev-parse", "HEAD") == launch.last_reviewed_commit
    assert (launch.worktree_path / "product.txt").read_text() == "uncommitted source\n"
    assert runtimes["change-a"].active_claims() == (("OUT-001", launch.claim),)
    assert coordinator.show("change-a").writer == launch.writer


def test_acquisition_rejects_dirty_planner_before_claim(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    dirty_file = tmp_path / "worktrees/change-a/product.txt"
    dirty_file.write_text("uncommitted source\n", encoding="utf-8")

    acquired = application.acquire_frontier_work()

    assert acquired.launch_packages == ()
    assert len(acquired.failures) == 1
    failure = acquired.failures[0]
    assert failure.change_id == "change-a"
    assert failure.outcome_id == "OUT-001"
    assert failure.attempt_id is None
    assert failure.claim_id is None
    assert runtimes["change-a"].active_claims() == ()
    assert coordinator.show("change-a").writer is None
    assert dirty_file.read_text(encoding="utf-8") == "uncommitted source\n"


def test_clean_build_recovery_exclusion_required_before_workspace_reset(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    worktree = package.worktree_path
    (worktree / "product.txt").write_text("attempt\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")
    _git(worktree, "commit", "-m", "attempt commit")
    attempt_commit = _git(worktree, "rev-parse", "HEAD")

    with (
        patch.object(runtimes["change-a"], "remove_active_claim") as remove_claim,
        patch.object(application._workspace_manager, "restart") as restart,
    ):
        _assert_recovery_excluded(application, package)
    remove_claim.assert_not_called()
    restart.assert_not_called()
    assert _git(worktree, "rev-parse", "HEAD") == attempt_commit
    assert coordinator.show("change-a").writer == package.writer
    assert runtimes["change-a"].active_claims() == (("OUT-001", package.claim),)
    assert not (state_root / "capacity.json").exists()


@pytest.mark.parametrize("interruption", ["attempt-ref", "worktree-reset"])
def test_clean_build_recovery_exclusion_required_before_each_workspace_effect(
    tmp_path: Path, interruption: str
) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    product = package.worktree_path / "product.txt"
    product.write_text("attempt\n", encoding="utf-8")
    _git(package.worktree_path, "add", "product.txt")
    _git(package.worktree_path, "commit", "-m", "attempt commit")
    rejected = _git(package.worktree_path, "rev-parse", "HEAD")
    manager = application._workspace_manager
    original_git = manager._git

    def interrupt_after_git(*arguments: str, **kwargs) -> str:
        result = original_git(*arguments, **kwargs)
        checks = {
            "attempt-ref": arguments[:2]
            == ("update-ref", f"refs/owlbear/attempts/change-a/{package.claim.attempt_id}"),
            "worktree-reset": arguments[:2] == ("reset", "--hard"),
        }
        if checks[interruption]:
            message = "injected workspace interruption"
            raise RuntimeError(message)
        return result

    with patch.object(manager, "_git", side_effect=interrupt_after_git):
        _assert_recovery_excluded(application, package)
    assert _git(package.worktree_path, "rev-parse", "HEAD") == rejected
    assert runtimes["change-a"].active_claims() == (("OUT-001", package.claim),)
    assert coordinator.show("change-a").writer == package.writer
    assert not (state_root / "capacity.json").exists()


def test_dirty_build_recovery_exclusion_required_preserves_bytes_and_custody(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    product = package.worktree_path / "product.txt"
    product.write_text("uncommitted attempt\n", encoding="utf-8")
    branch_head = _git(package.worktree_path, "rev-parse", "HEAD")

    _assert_recovery_excluded(application, package)
    assert _git(package.worktree_path, "status", "--porcelain") != ""
    assert _git(package.worktree_path, "rev-parse", "HEAD") == package.last_reviewed_commit
    assert runtimes["change-a"].active_claims() == (("OUT-001", package.claim),)
    assert coordinator.show("change-a").writer == package.writer
    assert product.read_text(encoding="utf-8") == "uncommitted attempt\n"
    assert application.acquire_frontier_work().launch_packages == ()
    assert _git(package.worktree_path, "rev-parse", "HEAD") == branch_head


def test_dirty_build_recovery_exclusion_required_before_workspace_cleanup(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    dirty_file = package.worktree_path / "uncommitted.txt"
    dirty_file.write_text("preserve me\n", encoding="utf-8")
    with patch.object(runtimes["change-a"], "remove_active_claim") as remove_claim:
        _assert_recovery_excluded(application, package)
    remove_claim.assert_not_called()
    assert coordinator.show("change-a").dirty_worktree_quarantine is None
    assert _git(package.worktree_path, "status", "--porcelain") != ""
    assert _git(package.worktree_path, "rev-parse", "HEAD") == package.last_reviewed_commit
    assert runtimes["change-a"].active_claims() == (("OUT-001", package.claim),)
    assert coordinator.show("change-a").writer == package.writer
    assert dirty_file.read_text() == "preserve me\n"
    _assert_recovery_excluded(application, package)
    assert application.acquire_frontier_work().launch_packages == ()


def test_dirty_build_recovery_exclusion_required_across_application_restart(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    worktree = package.worktree_path
    (worktree / "product.txt").write_text("attempt\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")
    _git(worktree, "commit", "-m", "attempt commit")
    rejected = _git(worktree, "rev-parse", "HEAD")
    (worktree / "uncommitted.bin").write_bytes(b"preserve\x00\xff")

    with patch.object(coordinator, "release") as release:
        _assert_recovery_excluded(application, package)
    release.assert_not_called()
    reopened, _, _ = _reopen_portfolio(tmp_path, state_root, runtimes)
    _assert_recovery_excluded(reopened, package)
    assert (worktree / "uncommitted.bin").read_bytes() == b"preserve\x00\xff"
    assert _git(worktree, "rev-parse", "HEAD") == rejected
    assert runtimes["change-a"].active_claims() == (("OUT-001", package.claim),)
    assert coordinator.show("change-a").writer == package.writer


def test_dirty_build_recovery_retains_custody_when_preservation_fails(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    dirty_file = package.worktree_path / "uncommitted.bin"
    dirty_file.write_bytes(b"preserve\x00\xff")

    with patch.object(
        application._workspace_manager,
        "quarantine_dirty_worktree",
        side_effect=RuntimeError("injected preservation failure"),
    ) as preserve:
        _assert_recovery_excluded(application, package)
    preserve.assert_not_called()
    assert dirty_file.read_bytes() == b"preserve\x00\xff"
    assert runtimes["change-a"].active_claims() == (("OUT-001", package.claim),)
    assert coordinator.show("change-a").writer == package.writer
    assert not (state_root / "capacity.json").exists()
    assert coordinator.show("change-a").dirty_worktree_quarantine is None


def test_mismatched_build_custody_retains_current_writer_and_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    coordinator.release("change-a", package.claim.claim_id)
    mismatched = ChangeWriter(
        attempt_id="other-attempt",
        claim_id="other-claim",
        actor_id="other-owner",
        process_id="other-process",
        claimed_at="2026-08-04T00:01:00Z",
        job_id=2,
        kind="build",
    )
    coordinator.acquire("change-a", mismatched)

    _assert_recovery_excluded(application, package)
    assert runtimes["change-a"].active_claims()[0][1] == package.claim
    assert coordinator.show("change-a").writer == mismatched
    assert not (state_root / "capacity.json").exists()


def test_claim_recovery_exclusion_required_without_caller_confirmation(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    package = application.acquire_frontier_work().launch_packages[0]

    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application.recover_claim(
            package.change_id,
            package.outcome_id,
            package.claim.attempt_id,
            package.claim.claim_id,
        )

    assert runtimes["change-a"].active_claims() == ((package.outcome_id, package.claim),)


def test_repair_change_diagnoses_but_exclusion_required_to_apply(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
        clock=lambda: now[0],
    )
    package = application.acquire_frontier_work().launch_packages[0]
    now[0] = "2026-08-04T01:00:00Z"

    diagnosed = application.repair_change("change-a")
    assert diagnosed.proposal is not None
    proposal = diagnosed.proposal
    assert proposal.outcome_id == package.outcome_id
    assert proposal.claim_id == package.claim.claim_id

    assert "pending verified owner evidence" in proposal.summary
    assert "host/worker closure" in proposal.consequence
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application.repair_change("change-a", proposal.proposal_id)

    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application.repair_change("change-a", proposal.proposal_id, confirmed_lost=True)
    assert runtimes["change-a"].active_claims() == (("OUT-001", package.claim),)


def test_repair_facade_matches_existing_repair_proposal_authority(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
        clock=lambda: now[0],
    )
    package = application.acquire_frontier_work().launch_packages[0]
    now[0] = "2026-08-04T01:00:00Z"

    diagnosed = application.repair("change-a")

    assert diagnosed == application.repair_change("change-a")
    assert diagnosed.proposal is not None
    assert diagnosed.proposal.claim_id == package.claim.claim_id


@pytest.mark.parametrize("continuation", [False, True])
def test_get_change_composes_detail_health_and_repair_proposal(tmp_path: Path, *, continuation: bool) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
        clock=lambda: now[0],
    )
    if continuation:
        application.acquire_change_action(_continuation_request(application))
    else:
        application.acquire_frontier_work()
    now[0] = "2026-08-04T01:00:00Z"

    view = application.get_change("change-a")
    stopped = application.acquire_change_action(_continuation_request(application))
    assert stopped.readiness == view.readiness
    if continuation:
        assert stopped.kind == "busy"
        assert view.repair is None
        return
    assert stopped.kind == "unsupported"
    assert stopped.reason_code == "repair-required"

    assert view.change_id == "change-a"
    assert view.detail.card.work_item_id == "OUT-001"
    assert view.detail.promise
    assert view.health.status is DeliveryHealthStatus.HEALTHY
    assert view.repair is not None
    assert view.repair.proposal is not None
    assert view.repair.proposal.outcome_id == view.detail.card.work_item_id
    assert view.readiness.action is None


def test_get_change_retains_unresolved_outcome_evidence_with_publication_detail(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    launch = application.acquire_frontier_work().launch_packages[0]
    request = DeliveryRequest(
        request_id="request-visible",
        kind=DeliveryRequestKind.ACTION,
        outcome_id="OUT-001",
        summary="Supply the external evidence.",
    )
    application.transition_delivery(
        "change-a",
        BlockDelivery(
            action="block",
            outcome_id="OUT-001",
            claim_id=launch.claim.claim_id,
            block_id="block-visible",
            reason="External evidence is unavailable.",
            unblock_condition="The evidence is supplied.",
            expected_evidence=("Evidence locator",),
            locators=("TASK-001",),
            request=request,
        ),
    )
    runtimes["change-a"].queue_admitted_design_checkpoint(coordinator.show("change-a").last_reviewed_commit)

    view = application.get_change("change-a")

    assert view.detail.card.item_key == "publication"
    assert len(view.unresolved_outcomes) == 1
    unresolved = view.unresolved_outcomes[0]
    assert unresolved.outcome_id == "OUT-001"
    assert unresolved.requests[0].request_id == request.request_id
    assert unresolved.block is not None
    assert unresolved.block.block_id == "block-visible"


def test_get_change_scopes_health_diagnostics_to_requested_change(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    application._startup_health_diagnostics = (
        DeliveryHealthDiagnostic(
            source="test",
            code="other-change",
            detail="Other Change requires attention.",
            change_id="change-b",
        ),
        DeliveryHealthDiagnostic(
            source="test",
            code="portfolio-fault",
            detail="The Delivery portfolio requires attention.",
        ),
        DeliveryHealthDiagnostic(
            source="test",
            code="requested-change",
            detail="Requested Change requires attention.",
            change_id="change-a",
        ),
    )
    view = application.get_change("change-a")

    assert view.health.status is DeliveryHealthStatus.ATTENTION
    assert tuple(item.change_id for item in view.health.diagnostics) == (None, "change-a")


@pytest.mark.parametrize("stored", [17, 18])
def test_repair_stranded_frontier_preserves_raw_evidence_and_reconciles_publication(
    tmp_path: Path, stored: int
) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    frontier_path = state_root / "changes/change-a/frontier.json"
    payload = json.loads(frontier_path.read_bytes())
    payload["schema_version"] = stored
    binding = payload["bindings"][0]
    if stored == 17:
        binding.pop("retry_count")
        binding.pop("retry_fingerprint")
    binding["block"] = {
        "block_id": "BLOCK-001",
        "reason": "The previous pilot is stale.",
        "unblock_condition": "Run the revised pilot.",
        "expected_evidence": ["Pilot evidence"],
        "locators": ["REQ-001"],
        "request_id": "REQ-001",
        "resolution_note": "Revise the acceptance contract.",
        "resolution_locators": ["REQ-001"],
        "resume_commit": None,
    }
    binding["requests"] = [
        {
            "kind": "action",
            "options": [],
            "outcome_id": "OUT-001",
            "request_id": "REQ-001",
            "summary": "Complete the revised pilot.",
            "resolution": {
                "response_text": "Use the approved SharePoint and Confluence targets.",
                "selected_option_id": None,
            },
        }
    ]
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    frontier_path.write_bytes(raw)
    expected_digest = hashlib.sha256(raw).hexdigest()

    receipt = application.repair_stranded_frontier(
        "change-a",
        "REQ-001",
        expected_digest,
        "repair-frontier",
        confirmed_repair=True,
    )

    repaired = frontier_path.read_bytes()
    history_path = state_root / "changes/change-a/revisions" / expected_digest / "frontier.json"
    assert history_path.read_bytes() == raw
    assert json.loads(repaired)["schema_version"] == 19
    assert json.loads(repaired)["bindings"][0]["requests"][0]["resolution"]["provenance"] == "user-confirmed"
    pending = json.loads((frontier_path.parent / "state-publication.json").read_bytes())
    assert pending["frontier_digest"] == hashlib.sha256(repaired).hexdigest()
    assert (
        application.repair_stranded_frontier(
            "change-a",
            "REQ-001",
            expected_digest,
            "repair-frontier",
            confirmed_repair=True,
        )
        == receipt
    )


def test_propose_quarantined_snapshot_repair_returns_exact_publication_fences(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )

    class InventoryPublisher:
        def read_snapshot_inventory(self) -> DeliveryStateSnapshotInventory:
            return DeliveryStateSnapshotInventory(
                remote_head="a" * 40,
                diagnostics=(
                    DeliveryStateSnapshotDiagnostic(
                        change_id="change-a",
                        path=".owlbear/delivery/state/change-a/snapshot.json",
                        code="snapshot-identity-invalid",
                        detail="The snapshot identity is invalid.",
                        raw_digest="b" * 64,
                    ),
                ),
            )

    application._delivery_state_publisher = InventoryPublisher()

    proposal = application.propose_quarantined_delivery_state_snapshot_repair("change-a")

    assert proposal.change_id == "change-a"
    assert proposal.diagnostic_code == "snapshot-identity-invalid"
    assert proposal.expected_remote_head == "a" * 40
    assert proposal.snapshot_digest == "b" * 64
    assert proposal.requires_confirmation is True


def test_application_repairs_quarantined_snapshot_through_real_state_publisher(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    repository = tmp_path / "repository"
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "HEAD:refs/heads/main")
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")
    runtime = runtimes["change-a"]
    admission = DeliveryAdmissionReceipt.model_validate_json(
        (state_root / "changes/change-a/admission.json").read_bytes()
    )
    package = application.read_design_session("change-a")
    first = publisher.publish(
        change_id="change-a",
        package_id=package.package_id,
        coordination=coordinator.show("change-a"),
        runtime=runtime,
        admission=admission,
        operation_id="application-repair-one",
        captured_at=datetime(2026, 8, 23, tzinfo=UTC),
    )
    snapshot_path = ".owlbear/delivery/state/change-a/snapshot.json"
    original = publisher._git_blob(first.published_head, snapshot_path)
    corrupted_payload = json.loads(original)
    corrupted_payload["snapshot_id"] = "0" * 64
    corrupted = (json.dumps(corrupted_payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    corrupted_head = _commit_corrupt_snapshot(repository, first.published_head, "change-a", corrupted)
    _git(repository, "push", "origin", f"{corrupted_head}:refs/heads/owlbear/delivery-state", "--force")
    application._delivery_state_publisher = publisher
    application._startup_health_diagnostics = (
        DeliveryHealthDiagnostic(
            source="remote-state",
            code="snapshot-identity-invalid",
            detail="Remote Delivery snapshot is quarantined.",
            change_id="change-a",
            reason=DeliveryHealthReason.REMOTE_STATE_RECONCILIATION,
        ),
    )

    proposal = application.propose_quarantined_delivery_state_snapshot_repair("change-a")
    application._startup_health_diagnostics = (
        *application._startup_health_diagnostics,
        DeliveryHealthDiagnostic(
            source="remote-state",
            code="remote-state-reconciliation-required",
            detail="The Change branch is out of band.",
            change_id="change-a",
            reason=DeliveryHealthReason.REMOTE_CHANGE_HEAD_MISMATCH,
        ),
    )
    with pytest.raises(PortfolioApplicationError, match="unrelated Change diagnostics"):
        application.repair_quarantined_delivery_state_snapshot(
            "change-a",
            "application-repair-unrelated-diagnostic",
            confirmed_repair=True,
            expected_remote_head=proposal.expected_remote_head,
            expected_snapshot_digest=proposal.snapshot_digest,
            expected_diagnostic_code=proposal.diagnostic_code,
        )
    application._startup_health_diagnostics = (application._startup_health_diagnostics[0],)
    receipt = application.repair_quarantined_delivery_state_snapshot(
        "change-a",
        "application-repair-two",
        confirmed_repair=True,
        expected_remote_head=proposal.expected_remote_head,
        expected_snapshot_digest=proposal.snapshot_digest,
        expected_diagnostic_code=proposal.diagnostic_code,
    )

    repaired = publisher.read_snapshot("change-a")
    assert repaired is not None
    assert repaired.repaired_predecessor_digest == proposal.snapshot_digest
    assert receipt.snapshot_id == repaired.snapshot_id
    assert runtime.pending_state_publication() is None


def test_set_change_intent_routes_versioned_lifecycle_dispositions(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    initial = application.get_change("change-a")

    deferred = application.set_change_intent(
        DeliveryChangeIntent(
            change_id="change-a",
            kind=DeliveryChangeIntentKind.DEFER,
            expected_frontier_digest=initial.frontier_digest,
            reason="Wait for user review.",
        )
    )
    assert deferred.receipt.change_id == "change-a"
    assert deferred.kind is DeliveryChangeIntentKind.DEFER

    replayed_defer = application.set_change_intent(
        DeliveryChangeIntent(
            change_id="change-a",
            kind=DeliveryChangeIntentKind.DEFER,
            expected_frontier_digest=initial.frontier_digest,
            reason="Wait for user review.",
        )
    )
    assert replayed_defer == deferred

    with pytest.raises(PortfolioApplicationError, match="frontier changed"):
        application.set_change_intent(
            DeliveryChangeIntent(
                change_id="change-a",
                kind=DeliveryChangeIntentKind.DEFER,
                expected_frontier_digest=initial.frontier_digest,
                reason="A different reason.",
            )
        )

    with pytest.raises(PortfolioApplicationError, match="frontier changed"):
        application.set_change_intent(
            DeliveryChangeIntent(
                change_id="change-a",
                kind=DeliveryChangeIntentKind.RESUME,
                expected_frontier_digest=initial.frontier_digest,
            )
        )

    resumed = application.set_change_intent(
        DeliveryChangeIntent(
            change_id="change-a",
            kind=DeliveryChangeIntentKind.RESUME,
            expected_frontier_digest=deferred.frontier_digest,
        )
    )
    assert resumed.receipt == deferred.receipt
    abandoned = application.set_change_intent(
        DeliveryChangeIntent(
            change_id="change-a",
            kind=DeliveryChangeIntentKind.ABANDON,
            expected_frontier_digest=resumed.frontier_digest,
            reason="User stopped the Change.",
        )
    )
    assert abandoned.kind is DeliveryChangeIntentKind.ABANDON
    assert abandoned.receipt.change_id == "change-a"
    replayed_abandon = application.set_change_intent(
        DeliveryChangeIntent(
            change_id="change-a",
            kind=DeliveryChangeIntentKind.ABANDON,
            expected_frontier_digest=resumed.frontier_digest,
            reason="User stopped the Change.",
        )
    )
    assert replayed_abandon == abandoned
    with pytest.raises(PortfolioApplicationError, match="frontier changed"):
        application.set_change_intent(
            DeliveryChangeIntent(
                change_id="change-a",
                kind=DeliveryChangeIntentKind.ABANDON,
                expected_frontier_digest=resumed.frontier_digest,
                reason="A different reason.",
            )
        )


def test_answer_revalidates_frontier_and_replays_same_request_answer(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    launch = application.acquire_frontier_work().launch_packages[0]
    request = DeliveryRequest(
        request_id="request-answer",
        kind=DeliveryRequestKind.DECISION,
        outcome_id="OUT-001",
        summary="Choose the repair path.",
        options=(
            DeliveryRequestOption(option_id="repair", label="Repair the prerequisite"),
            DeliveryRequestOption(option_id="defer", label="Defer the prerequisite"),
        ),
    )
    application.transition_delivery(
        "change-a",
        BlockDelivery(
            action="block",
            outcome_id="OUT-001",
            claim_id=launch.claim.claim_id,
            block_id="block-answer",
            reason="The prerequisite is unavailable.",
            unblock_condition="The prerequisite is repaired.",
            expected_evidence=("Successful repair",),
            locators=("TASK-001",),
            request=request,
        ),
    )
    view = application.get_change("change-a")
    answer = DeliveryAnswer(
        change_id="change-a",
        request_id=request.request_id,
        resolution=DeliveryRequestResolution(selected_option_id="repair"),
        expected_frontier_digest=view.frontier_digest,
    )

    applied = application.answer(answer)
    replayed = application.answer(answer)

    assert applied == replayed
    assert applied.request.resolution == answer.resolution
    with pytest.raises(PortfolioApplicationError, match="exactly one selected option"):
        application.answer(
            answer.model_copy(
                update={
                    "resolution": DeliveryRequestResolution(
                        response_text="Repair it.",
                        provenance="user-confirmed",
                    )
                }
            )
        )
    different = answer.model_copy(update={"resolution": DeliveryRequestResolution(selected_option_id="defer")})
    with pytest.raises(PortfolioApplicationError, match="answer frontier changed"):
        application.answer(different)


def test_answer_clears_and_replays_requestless_block_evidence(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    launch = application.acquire_frontier_work().launch_packages[0]
    application.transition_delivery(
        "change-a",
        BlockDelivery(
            action="block",
            outcome_id="OUT-001",
            claim_id=launch.claim.claim_id,
            block_id="block-evidence",
            reason="External evidence is missing.",
            unblock_condition="Record the verified evidence.",
            expected_evidence=("Evidence locator",),
            locators=("operator",),
        ),
    )
    view = application.get_change("change-a")
    answer = DeliveryAnswer(
        change_id="change-a",
        kind=DeliveryAnswerKind.BLOCK,
        expected_frontier_digest=view.frontier_digest,
        outcome_id="OUT-001",
        block_id="block-evidence",
        operator_note="Verified externally.",
        locators=("evidence:123",),
    )

    applied = application.answer(answer)
    replayed = application.answer(answer)

    assert applied == replayed
    assert applied.binding is not None
    assert applied.binding.block is not None
    assert applied.binding.block.resolution_note == "Verified externally."


def test_answer_resolves_and_replays_change_disposition(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    disposition = runtimes["change-a"].capture_publication_attention(
        datetime(2026, 8, 4, 1, tzinfo=UTC),
        ("provider unavailable",),
    )
    view = application.get_change("change-a")
    answer = DeliveryAnswer(
        change_id="change-a",
        kind=DeliveryAnswerKind.DISPOSITION,
        expected_frontier_digest=view.frontier_digest,
        expected_disposition_id=disposition.disposition_id,
    )

    applied = application.answer(answer)
    replayed = application.answer(answer)

    assert applied == replayed
    assert applied.disposition is not None
    assert applied.disposition.disposition_id == disposition.disposition_id
