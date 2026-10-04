"""Shared real-core recovery fixtures and fail-closed authority checks."""

# ruff: noqa: SLF001 - tests exercise the deliberately unregistered internal owner path.

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier
from typing import Any
from unittest.mock import Mock, patch

import pytest
from serve.delivery.tests.test_checkpoint_publication_regressions import _CONFIG as _LOADER_CONFIG
from serve.delivery.tests.test_checkpoint_publication_regressions import _SNAPSHOT_PATH as _LOADER_SNAPSHOT_PATH
from serve.delivery.tests.test_checkpoint_publication_regressions import _relabel_as_snapshot_2, _store_v18
from serve.delivery.tests.test_delivery_state import _admission
from serve.delivery.tests.test_portfolio_application import (
    _attach_local_target,
    _awaiting_acceptance_fixture,
    _builder_retry_handoff_setup,
    _canonical,
    _commit_reviewed_head,
    _continuation_request,
    _engine_action,
    _execute_engine,
    _failure_request,
    _file_bytes,
    _finalization_request,
    _git,
    _legacy_task_result,
    _portfolio,
    _prepare_legacy_integration_repair,
    _reopen_portfolio,
    _seed_loader_composed_completed_change,
    _settle_builder_handoff_attempt,
    _task,
    _task_result,
)

from owlbear_delivery import (
    BlockDelivery,
    CompletedOutcomeRepairReceipt,
    CreateOrReconcileDraftPullRequest,
    DeliveryChangePublicationIdentity,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryResultSubmission,
    DeliveryRuntimeReferenceError,
    DeliveryStage,
    DraftPullRequestPublisher,
    PortfolioApplicationError,
    PrepareCompletedOutcomeRepair,
    PreservationRejectedError,
    PublicationCheckSnapshot,
    RetryDelivery,
    ReturnDelivery,
)
from owlbear_delivery.delivery_application_loader import load_delivery_application
from owlbear_delivery.delivery_runtime import (
    DeliveryFinalization,
    DeliveryFinalizationReceipt,
    DeliveryFrontier,
    DeliveryLegacyObservationReceipt,
    DeliveryReviewReceipt,
    DeliveryRuntime,
    DeliveryTaskResult,
)
from owlbear_delivery.delivery_state import DeliveryStatePublisher
from owlbear_delivery.portfolio_application import DeliveryLaunchPackage
from owlbear_delivery.publication_provider import PublicationPullRequest, PublicationRepository
from owlbear_delivery.recovery import (
    DeliveryWorkerExclusionRequiredError,
    RecoveryEvidence,
    RecoveryEvidenceReference,
    RecoveryIntent,
    RecoveryInvocation,
    RecoveryReceipt,
    RetryEpisodeKey,
    RetryFailureClass,
    RetryLedger,
    UnavailableRecoveryEvidenceProvider,
    digest,
    encoded,
    journal_path,
)
from owlbear_delivery.runtime_models import _model_content, _receipt_digest
from owlbear_delivery.runtime_transaction import RuntimeTransaction, TransactionConflictError, TransactionParticipant
from owlbear_delivery.work_items import WorkItemActionKind


def test_completed_outcome_repair_receipt_create_preserves_legacy_call_forms() -> None:
    request = PrepareCompletedOutcomeRepair(
        outcome_id="OUT-001",
        owning_task_id="TASK-001",
        episode_id="episode-1",
        attempt_id="attempt-1",
        defect_code="worker-failure",
        finding_boundary="implementation",
        original_action_id="action-1",
        preservation_id="a" * 64,
        expected_frontier_digest="b" * 64,
    )
    previous_task_ids = ("TASK-000",)
    previous_result_ids = ("RESULT-000",)
    finished_at = "2026-09-28T09:00:00Z"
    positional = CompletedOutcomeRepairReceipt.create(
        "change-a",
        request,
        "repair-task",
        previous_task_ids,
        previous_result_ids,
        finished_at,
    )
    keyword = CompletedOutcomeRepairReceipt.create(
        change_id="change-a",
        request=request,
        repair_task_id="repair-task",
        previous_task_ids=previous_task_ids,
        previous_result_ids=previous_result_ids,
        finished_at=finished_at,
    )
    mixed = CompletedOutcomeRepairReceipt.create(
        "change-a",
        request,
        "repair-task",
        previous_task_ids=previous_task_ids,
        previous_result_ids=previous_result_ids,
        finished_at=finished_at,
    )

    assert positional == keyword == mixed


_LEGACY_RECOVERY_ID = "11c924b869f40f9d4c0118de57ab8648d3578df9c3ffea4ddd9bcabb1867c12f"
_LEGACY_INTENT_JSON = (
    b'{"schema_version":1,"invocation":{"schema_version":1,"request":{"change_id":"change-a",'
    b'"owner_id":"legacy-owner","attempt_id":"legacy-attempt","outcome_id":"OUT-001","kind":"claim",'
    b'"contract_digest":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
    b'"exact_head":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",'
    b'"target_head":"cccccccccccccccccccccccccccccccccccccccc","branch":"owlbear/change/change-a",'
    b'"worktree":"/legacy/worktree","repository":"/legacy/repository","runtime_root":"/legacy/runtime",'
    b'"integration_target":"release","publication_repository":null,'
    b'"mutation_channels":["managed-filesystem","shared-git-metadata-and-refs","git-remotes",'
    b'"delivery-runtime","publication-provider"]},"host_instance":"legacy-host",'
    b'"host_generation":"legacy-generation","invocation_id":"legacy-invocation"},'
    b'"frontier_digest":"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",'
    b'"coordination_digest":"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",'
    b'"exact_head":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",'
    b'"target_head":"cccccccccccccccccccccccccccccccccccccccc",'
    b'"workspace_fingerprint":"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",'
    b'"owner_record":"legacy owner record","failure_id":null,"effect_receipt_id":null,'
    b'"engine_result_digest":null,"proposal_id":null,"kind":"clean-claim"}\n'
)
_A5_INTENT_JSON = _LEGACY_INTENT_JSON.replace(
    b'"engine_result_digest":null,"proposal_id":null,"kind":"clean-claim"',
    b'"engine_result_digest":null,"proposal_id":null,'
    b'"maintained_surfaces":["legacy-surface-a","legacy-surface-b"],'
    b'"last_write_provenance":["attempt:legacy-attempt","change-head:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",'
    b'"frontier:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd","owner:legacy-owner",'
    b'"result:RESULT-001:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"],"kind":"clean-claim"',
)
_A5_RECOVERY_ID = hashlib.sha256(_A5_INTENT_JSON).hexdigest()
_LEGACY_EVIDENCE_JSON = (
    b'{"schema_version":1,"reference":{"reference":"opaque-'
    b'11c924b869f40f9d4c0118de57ab8648d3578df9c3ffea4ddd9bcabb1867c12f"},'
    b'"recovery_id":"11c924b869f40f9d4c0118de57ab8648d3578df9c3ffea4ddd9bcabb1867c12f",'
    b'"invocation":{"schema_version":1,"request":{"change_id":"change-a","owner_id":"legacy-owner",'
    b'"attempt_id":"legacy-attempt","outcome_id":"OUT-001","kind":"claim",'
    b'"contract_digest":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
    b'"exact_head":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",'
    b'"target_head":"cccccccccccccccccccccccccccccccccccccccc","branch":"owlbear/change/change-a",'
    b'"worktree":"/legacy/worktree","repository":"/legacy/repository","runtime_root":"/legacy/runtime",'
    b'"integration_target":"release","publication_repository":null,'
    b'"mutation_channels":["managed-filesystem","shared-git-metadata-and-refs","git-remotes",'
    b'"delivery-runtime","publication-provider"]},"host_instance":"legacy-host",'
    b'"host_generation":"legacy-generation","invocation_id":"legacy-invocation"},'
    b'"status":"excluded","scope":"invocation-all-descendants-all-tool-jobs"}\n'
)
_LEGACY_RECEIPT_JSON = (
    b'{"schema_version":1,"recovery_id":"11c924b869f40f9d4c0118de57ab8648d3578df9c3ffea4ddd9bcabb1867c12f",'
    b'"evidence":{"schema_version":1,"reference":{"reference":"opaque-'
    b'11c924b869f40f9d4c0118de57ab8648d3578df9c3ffea4ddd9bcabb1867c12f"},'
    b'"recovery_id":"11c924b869f40f9d4c0118de57ab8648d3578df9c3ffea4ddd9bcabb1867c12f",'
    b'"invocation":{"schema_version":1,"request":{"change_id":"change-a","owner_id":"legacy-owner",'
    b'"attempt_id":"legacy-attempt","outcome_id":"OUT-001","kind":"claim",'
    b'"contract_digest":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
    b'"exact_head":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",'
    b'"target_head":"cccccccccccccccccccccccccccccccccccccccc","branch":"owlbear/change/change-a",'
    b'"worktree":"/legacy/worktree","repository":"/legacy/repository","runtime_root":"/legacy/runtime",'
    b'"integration_target":"release","publication_repository":null,'
    b'"mutation_channels":["managed-filesystem","shared-git-metadata-and-refs","git-remotes",'
    b'"delivery-runtime","publication-provider"]},"host_instance":"legacy-host",'
    b'"host_generation":"legacy-generation","invocation_id":"legacy-invocation"},'
    b'"status":"excluded","scope":"invocation-all-descendants-all-tool-jobs"},'
    b'"stages":["proposed","excluded","reconciled","completed"],"preservation":"clean-no-restoration",'
    b'"owner_effect":"no-workspace-effect","owner_observation_id":null,"finished_at":"2026-08-02T00:04:00Z"}\n'
)


class EvidenceHost:
    """Controlled host port: references resolve against its independent issued registry."""

    def __init__(self):
        self.invocations = {}
        self.evidence = {}
        self.verifications = 0

    def register(self, request):
        invocation = RecoveryInvocation(
            request=request,
            host_instance="controlled-host",
            host_generation="generation-1",
            invocation_id=f"invocation-{len(self.invocations)}",
        )
        self.invocations[request.owner_id] = invocation
        return invocation

    def seal(self, intent, status="closed"):
        assert self.invocations[intent.invocation.request.owner_id] == intent.invocation
        reference = RecoveryEvidenceReference(reference=f"opaque-{intent.recovery_id}")
        self.evidence[reference.reference] = RecoveryEvidence(
            reference=reference, recovery_id=intent.recovery_id, invocation=intent.invocation, status=status
        )
        return reference

    def verify(self, reference, intent):
        self.verifications += 1
        return self.evidence.get(reference.reference) or RecoveryEvidence(
            reference=reference, recovery_id=intent.recovery_id, invocation=intent.invocation, status="unknown"
        )


def test_legacy_recovery_fixture_replays_excluded_receipt_after_restart(tmp_path: Path) -> None:
    journal_root = tmp_path / "changes" / "change-a" / "recovery-receipts" / _LEGACY_RECOVERY_ID
    journal_root.mkdir(parents=True)
    intent_path = journal_root / "intent.json"
    evidence_path = journal_root / "evidence.json"
    receipt_path = journal_root / "receipt.json"
    intent_path.write_bytes(_LEGACY_INTENT_JSON)
    evidence_path.write_bytes(_LEGACY_EVIDENCE_JSON)
    receipt_path.write_bytes(_LEGACY_RECEIPT_JSON)

    intent = RecoveryIntent.model_validate_json(_LEGACY_INTENT_JSON)
    evidence = RecoveryEvidence.model_validate_json(_LEGACY_EVIDENCE_JSON)
    receipt = RecoveryReceipt.model_validate_json(_LEGACY_RECEIPT_JSON)
    assert intent.uses_legacy_encoding
    assert intent.recovery_id == _LEGACY_RECOVERY_ID
    assert encoded(intent) == _LEGACY_INTENT_JSON
    assert evidence.recovery_id == receipt.recovery_id == intent.recovery_id
    assert evidence.status == receipt.evidence.status == "excluded"
    assert encoded(evidence) == _LEGACY_EVIDENCE_JSON
    assert encoded(receipt) == _LEGACY_RECEIPT_JSON

    restarted_intent = RecoveryIntent.model_validate_json(intent_path.read_bytes())
    restarted_receipt = RecoveryReceipt.model_validate_json(receipt_path.read_bytes())
    assert restarted_intent.recovery_id == _LEGACY_RECOVERY_ID
    assert restarted_receipt.recovery_id == restarted_intent.recovery_id
    assert restarted_receipt.evidence.status == "excluded"

    tampered = _LEGACY_INTENT_JSON.replace(b'"owner_record":"legacy owner record"', b'"owner_record":"tampered"')
    assert RecoveryIntent.model_validate_json(tampered).recovery_id != _LEGACY_RECOVERY_ID


def test_a5_recovery_fixture_preserves_bytes_and_directional_authority() -> None:
    intent = RecoveryIntent.model_validate_json(_A5_INTENT_JSON)
    assert not intent.uses_legacy_encoding
    assert intent.recovery_id == _A5_RECOVERY_ID
    assert encoded(intent) == _A5_INTENT_JSON

    upgraded = intent.model_copy(
        update={
            "admitted_task_id": "TASK-001",
            "admitted_task_digest": "d" * 64,
            "admitted_task_scope": ("src/file.py",),
            "admitted_paths": (),
        }
    )
    assert intent.authority_matches(upgraded)
    assert not upgraded.authority_matches(intent)
    assert not upgraded.authority_matches(
        upgraded.model_copy(update={"last_write_provenance": ("tampered-old-provenance",)})
    )


@pytest.mark.parametrize("dirty", [False, True, "ignored", "replay"])
def test_legacy_incomplete_intent_completes_against_current_provenance(tmp_path: Path, *, dirty: bool | str) -> None:
    application, _runtimes, coordinator, state = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    host = _host(application)
    application.acquire_change_action(_continuation_request(application))
    current = application._propose_recovery("change-a")
    current_path = state / journal_path("change-a", current.recovery_id, "intent")
    legacy_bytes = (
        current.model_dump_json(
            exclude={
                "maintained_surfaces",
                "last_write_provenance",
                "admitted_task_id",
                "admitted_task_digest",
                "admitted_task_scope",
                "admitted_paths",
            }
        )
        + "\n"
    ).encode()
    legacy = RecoveryIntent.model_validate_json(legacy_bytes)
    assert legacy.uses_legacy_encoding
    assert encoded(legacy) == legacy_bytes
    assert legacy.recovery_id == hashlib.sha256(legacy_bytes).hexdigest()
    assert legacy.recovery_id != current.recovery_id
    assert legacy.authority_matches(current)
    assert not legacy.authority_matches(legacy.model_copy(update={"owner_record": "tampered"}))
    current_path.unlink()
    legacy_path = state / journal_path("change-a", legacy.recovery_id, "intent")
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_bytes(legacy_bytes)

    if dirty == "replay":
        receipt = application._complete_recovery("change-a", legacy.recovery_id, host.seal(legacy))
        (coordinator.show("change-a").worktree_path / "shared.txt").write_text("dirty\n", encoding="utf-8")
        with (
            patch.object(
                coordinator, "forget_verified_exclusion", wraps=coordinator.forget_verified_exclusion
            ) as forget,
            patch.object(application, "_require_legacy_recovery_clean") as legacy_guard,
        ):
            assert application._complete_recovery("change-a", legacy.recovery_id, host.seal(legacy)) == receipt
        forget.assert_not_called()
        legacy_guard.assert_not_called()
        return
    if dirty == "ignored":
        worktree = coordinator.show("change-a").worktree_path
        exclude = Path(_git(worktree, "rev-parse", "--git-path", "info/exclude"))
        if not exclude.is_absolute():
            exclude = worktree / exclude
        exclude.write_text("ignored-recovery.txt\n", encoding="utf-8")
        (worktree / "ignored-recovery.txt").write_text("ignored\n", encoding="utf-8")
    elif dirty:
        (coordinator.show("change-a").worktree_path / "shared.txt").write_text("dirty\n", encoding="utf-8")
    if dirty:
        with pytest.raises(DeliveryWorkerExclusionRequiredError):
            application._complete_recovery("change-a", legacy.recovery_id, host.seal(legacy))
        return

    receipt = application._complete_recovery("change-a", legacy.recovery_id, host.seal(legacy))

    assert receipt.recovery_id == legacy.recovery_id
    assert receipt.evidence.recovery_id == legacy.recovery_id
    assert coordinator.show("change-a").recovery_owner_id is None
    assert current.authority_matches(current.model_copy(update={"maintained_surfaces": ("changed",)})) is False


@pytest.mark.parametrize("dirty", [False, True, "replay"])
def test_a5_incomplete_intent_completes_against_current_provenance(tmp_path: Path, *, dirty: bool | str) -> None:
    """Old clean journals replay; dirty preservation remains separately admission-gated."""
    application, _runtimes, coordinator, state = _portfolio(
        tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION}, include_downstream=True
    )
    host = _host(application)
    application.acquire_change_action(_continuation_request(application))
    current = application._propose_recovery("change-a")
    legacy_surfaces = (
        "serve/delivery/src/owlbear_delivery/delivery_runtime.py",
        "serve/delivery/src/owlbear_delivery/portfolio_application.py",
    )
    legacy_provenance = (
        f"attempt:{current.invocation.request.attempt_id}",
        f"change-head:{current.exact_head}",
        f"frontier:{current.frontier_digest}",
        f"owner:{current.invocation.request.owner_id}",
    )
    old_intent = current.model_copy(
        update={
            "maintained_surfaces": legacy_surfaces,
            "last_write_provenance": legacy_provenance,
        }
    )
    old_bytes = (
        old_intent.model_dump_json(
            exclude={
                "admitted_task_id",
                "admitted_task_digest",
                "admitted_task_scope",
                "admitted_paths",
            }
        )
        + "\n"
    ).encode()
    old_intent = RecoveryIntent.model_validate_json(old_bytes)
    assert not old_intent.uses_legacy_encoding
    assert encoded(old_intent) == old_bytes
    assert (
        old_intent.authority_matches(current.model_copy(update={"last_write_provenance": ("tampered-old-provenance",)}))
        is False
    )
    current_path = state / journal_path("change-a", current.recovery_id, "intent")
    current_path.unlink()
    old_path = state / journal_path("change-a", old_intent.recovery_id, "intent")
    old_path.parent.mkdir(parents=True)
    old_path.write_bytes(old_bytes)

    if dirty == "replay":
        receipt = application._complete_recovery("change-a", old_intent.recovery_id, host.seal(old_intent))
        (coordinator.show("change-a").worktree_path / "shared.txt").write_text("dirty\n", encoding="utf-8")
        with (
            patch.object(
                coordinator, "forget_verified_exclusion", wraps=coordinator.forget_verified_exclusion
            ) as forget,
            patch.object(application, "_require_legacy_recovery_clean") as legacy_guard,
        ):
            assert application._complete_recovery("change-a", old_intent.recovery_id, host.seal(old_intent)) == receipt
        forget.assert_not_called()
        legacy_guard.assert_not_called()
        return
    if dirty:
        (coordinator.show("change-a").worktree_path / "shared.txt").write_text("dirty\n", encoding="utf-8")
        with pytest.raises(DeliveryWorkerExclusionRequiredError):
            application._complete_recovery("change-a", old_intent.recovery_id, host.seal(old_intent))
        return

    receipt = application._complete_recovery("change-a", old_intent.recovery_id, host.seal(old_intent))

    assert receipt.recovery_id == old_intent.recovery_id
    assert coordinator.show("change-a").recovery_owner_id is None


def test_a5_recovery_intent_identity_survives_admitted_authority_fields(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    _host(application)
    application.acquire_change_action(_continuation_request(application))
    current = application._propose_recovery("change-a")
    prior = current
    prior_bytes = (
        prior.model_dump_json(
            exclude={
                "admitted_task_id",
                "admitted_task_digest",
                "admitted_task_scope",
                "admitted_paths",
            }
        )
        + "\n"
    ).encode()
    persisted = RecoveryIntent.model_validate_json(prior_bytes)

    assert not persisted.uses_legacy_encoding
    assert encoded(persisted) == prior_bytes
    assert persisted.recovery_id == hashlib.sha256(prior_bytes).hexdigest()
    assert persisted.maintained_surfaces == current.maintained_surfaces
    assert persisted.last_write_provenance == current.last_write_provenance
    assert persisted.authority_matches(current)
    assert not persisted.authority_matches(
        current.model_copy(update={"maintained_surfaces": ("tampered-old-surface",)})
    )
    assert not persisted.authority_matches(
        current.model_copy(update={"last_write_provenance": ("tampered-old-provenance",)})
    )
    assert not persisted.authority_matches(persisted.model_copy(update={"maintained_surfaces": ("legacy-surface",)}))


def test_recovery_intent_binds_only_the_active_task_authority(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
        include_downstream=True,
    )
    host = _host(application)
    launch = application.acquire_frontier_work().launch_packages[0]
    intent = application._propose_recovery("change-a")

    claim = runtimes["change-a"].active_claims()[0][1]
    task = next(task for task in runtimes["change-a"].show_binding("OUT-001").tasks if task.task_id == claim.task_id)
    assert intent.admitted_task_id is None
    assert intent.admitted_task_digest is None
    assert intent.admitted_task_scope == ()
    assert intent.admitted_paths == ()
    assert intent.maintained_surfaces == tuple(
        sorted(
            {
                surface
                for binding in runtimes["change-a"].bindings()
                for candidate in binding.tasks
                for surface in candidate.maintained_surfaces
            }
        )
    )
    assert f"owner:{intent.invocation.request.owner_id}" in intent.last_write_provenance
    assert f"attempt:{intent.invocation.request.attempt_id}" in intent.last_write_provenance

    receipt = application._complete_recovery("change-a", intent.recovery_id, host.seal(intent))
    preservation = application._workspace_manager.capture_preservation("change-a", intent.recovery_id)
    assert receipt.recovery_id == intent.recovery_id
    assert preservation.recovery_id == intent.recovery_id
    assert preservation.maintained_surfaces == intent.maintained_surfaces
    assert intent.authority_matches(intent.model_copy(update={"admitted_task_digest": "d" * 64})) is False
    assert coordinator.show("change-a").recovery_owner_id is None
    assert launch.claim.task_id == task.task_id


def test_clean_claim_recovery_refuses_retained_builder_handoff_before_writes(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    (
        application,
        runtime,
        _coordinator,
        _state_root,
        original,
        _branch_head,
        _before_workspace,
        settlement,
    ) = _builder_retry_handoff_setup(tmp_path, now, add_workspace_changes=False)
    host = _host(application)
    settled = _settle_builder_handoff_attempt(application, original.claim, settlement)
    handoff = settled.builder_handoff_context
    assert handoff is not None

    now[0] = "2026-08-04T01:00:00Z"
    resumed_result = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert resumed_result.launch is not None
    resumed = resumed_result.launch
    assert resumed.claim.task_id == handoff.original_task_id
    assert resumed.builder_handoff_context == handoff

    binding = runtime.show_binding(resumed.outcome_id)
    assert binding.active_claim == resumed.claim
    assert binding.builder_handoff_context == handoff
    intent = application._propose_recovery("change-a")
    assert intent.kind == "clean-claim"
    reference = host.seal(intent, "excluded")
    evidence = host.verify(reference, intent)
    receipt = RecoveryReceipt(
        recovery_id=intent.recovery_id,
        evidence=evidence,
        owner_effect="no-workspace-effect",
        finished_at=now[0],
    )

    before = recovery_effect_snapshot(application)
    pending_before = runtime.pending_state_publication()
    with (
        patch.object(application._workspace_manager, "prepare_recovery_release") as prepare_release,
        patch.object(runtime, "_replace_content") as replace_content,
        pytest.raises(DeliveryWorkerExclusionRequiredError),
    ):
        runtime.complete_recovery(intent, receipt)

    prepare_release.assert_not_called()
    replace_content.assert_not_called()
    assert recovery_effect_snapshot(application) == before
    assert runtime.pending_state_publication() == pending_before


@pytest.mark.parametrize(
    "surface",
    ["serve/delivery/**", "serve/delivery/", "not an exact path", "./source.py", "../source.py"],
)
def test_recovery_rejects_noncanonical_task_surface_descriptors(tmp_path: Path, surface: str) -> None:
    application, _runtimes, coordinator, _state = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    task = _task().model_copy(update={"maintained_surfaces": (surface,)})

    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application._exact_task_scope(task, coordinator.show("change-a").worktree_path)


def test_recovery_rejects_noncanonical_dirty_path_before_admission(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    task = _task().model_copy(update={"maintained_surfaces": ("src",)})

    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application._recovery_admission_fields(
            task,
            ("src/file with space.py",),
            coordinator.show("change-a").worktree_path,
        )


def test_clean_recovery_skips_ambiguous_task_surface_admission(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    task = _task().model_copy(update={"maintained_surfaces": ("serve/delivery/**",)})

    assert application._recovery_admission_fields(
        task,
        (),
        coordinator.show("change-a").worktree_path,
    ) == (None, None, (), ())
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application._recovery_admission_fields(
            task,
            ("serve/delivery/module.py",),
            coordinator.show("change-a").worktree_path,
        )


@pytest.mark.parametrize("surface", ["serve/delivery/", "not an exact path", "serve/delivery/**"])
def test_clean_recovery_ignores_ambiguous_task_scope(tmp_path: Path, surface: str) -> None:
    application, _runtimes, _coordinator, _state = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    _host(application)
    application.acquire_change_action(_continuation_request(application))
    task = _task().model_copy(update={"maintained_surfaces": (surface,)})

    with patch.object(
        type(application),
        "_recovery_admitted_task",
        staticmethod(lambda _runtime, _owner, _kind: task),
    ):
        intent = application._propose_recovery("change-a")

    assert intent.admitted_task_id is None
    assert intent.admitted_task_digest is None
    assert intent.admitted_task_scope == ()
    assert intent.admitted_paths == ()


def test_recovery_uses_canonical_directory_scope_for_exact_dirty_paths(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    worktree = coordinator.show("change-a").worktree_path
    (worktree / "serve" / "delivery").mkdir(parents=True)
    task = _task().model_copy(update={"maintained_surfaces": ("serve/delivery",)})

    assert application._exact_task_scope(task, worktree) == ("serve/delivery",)
    admitted = application._recovery_admission_fields(
        task,
        ("serve/delivery/src/module.py",),
        worktree,
    )
    assert admitted[2:] == (("serve/delivery",), ("serve/delivery/src/module.py",))


def test_recovery_does_not_expand_file_scope_after_directory_replacement(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    worktree = coordinator.show("change-a").worktree_path
    (worktree / "src").mkdir()
    (worktree / "src" / "file.py").write_text("file\n", encoding="utf-8")
    task = _task().model_copy(update={"maintained_surfaces": ("src/file.py",)})
    scope, kinds = application._exact_task_scope_details(task, worktree)
    (worktree / "src" / "file.py").unlink()
    (worktree / "src" / "file.py").mkdir()

    assert scope == ("src/file.py",)
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application._exact_task_scope_details(task, worktree, kinds)
    assert not application._scope_admits_path(
        worktree,
        scope[0],
        "src/file.py/secret",
        scope_kind=kinds[scope[0]],
    )


def test_recovery_rejects_symlink_task_scope(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    worktree = coordinator.show("change-a").worktree_path
    (worktree / "src").mkdir()
    (worktree / "link").symlink_to("src", target_is_directory=True)
    task = _task().model_copy(update={"maintained_surfaces": ("link",)})

    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application._exact_task_scope(task, worktree)


def test_recovery_rejects_root_scope_as_an_ambiguous_directory(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    task = _task().model_copy(update={"maintained_surfaces": (".",)})

    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application._exact_task_scope(task, coordinator.show("change-a").worktree_path)


def test_recovery_intent_validates_nested_admitted_paths_by_component_boundary() -> None:
    payload = RecoveryIntent.model_validate_json(_A5_INTENT_JSON).model_dump()
    payload.update(
        {
            "admitted_task_id": "TASK-001",
            "admitted_task_digest": "d" * 64,
            "admitted_task_scope": ("serve/delivery",),
            "admitted_paths": ("serve/delivery/src/module.py",),
        }
    )

    intent = RecoveryIntent.model_validate(payload)

    assert intent.admitted_paths == ("serve/delivery/src/module.py",)
    payload["admitted_paths"] = ("serve/delivery-extra/module.py",)
    with pytest.raises(ValueError, match="within the admitted task scope"):
        RecoveryIntent.model_validate(payload)


def completed_recovery_restart_case(tmp_path: Path, kind: str):
    """Reload completed owner journals before public replay with the same host authority."""
    application, operation, request, unchanged = completed_recovery_case(tmp_path, kind)
    host = application._recovery_evidence_provider
    protected = recovery_effect_snapshot(application, "change-a")
    restarted, _coordinator, _manager = _reopen_portfolio(
        tmp_path,
        application._coordinator.runtime_root,
        application._runtimes,
    )
    assert recovery_effect_snapshot(restarted, "change-a") == protected
    restarted._recovery_evidence_provider = host

    def unchanged_after_restart() -> None:
        unchanged()
        assert recovery_effect_snapshot(restarted, "change-a") == protected

    return restarted, operation, request, unchanged_after_restart, host


def _tree_snapshot(root: Path) -> tuple[tuple[str, str, bytes | str | None], ...]:
    if not root.exists() and not root.is_symlink():
        return ((root.name, "absent", None),)
    entries = []
    for path in (root, *sorted(root.rglob("*"))):
        if path.is_symlink():
            entries.append((path.relative_to(root.parent).as_posix(), "symlink", path.readlink().as_posix()))
        elif path.is_dir():
            entries.append((path.relative_to(root.parent).as_posix(), "directory", None))
        elif path.is_file():
            entries.append((path.relative_to(root.parent).as_posix(), "file", path.read_bytes()))
        else:
            entries.append((path.relative_to(root.parent).as_posix(), "other", None))
    return tuple(entries)


def recovery_journal_snapshot(application, change_id: str) -> tuple[tuple[str, str, bytes | str | None], ...]:
    change_root = application._coordinator.runtime_root / "changes" / change_id
    return tuple(
        entry for journal in ("invocations", "recovery-receipts") for entry in _tree_snapshot(change_root / journal)
    )


def recovery_effect_snapshot(application, change_id: str = "change-a") -> tuple[object, ...]:
    runtime = application._runtimes[change_id]
    coordination = application._coordinator.show(change_id)
    worktree = coordination.worktree_path
    index = Path(_git(worktree, "rev-parse", "--path-format=absolute", "--git-path", "index"))
    retry_ledger = runtime.retry_ledger()
    coordination_record = application._coordinator.runtime_root / "coordination/changes" / f"{change_id}.json"
    return (
        runtime.frontier_bytes(),
        coordination,
        coordination_record.read_bytes(),
        _file_bytes(worktree),
        index.read_bytes(),
        _git(worktree, "show-ref"),
        _git(worktree, "rev-parse", "HEAD"),
        retry_ledger.read(),
        _tree_snapshot(retry_ledger.summary_path.parent),
        recovery_journal_snapshot(application, change_id),
    )


class ProcessEvidenceHost(EvidenceHost):
    """Own the controlled invocation's entire process/job graph below the evidence port."""

    def __init__(self, orphan_child):
        super().__init__()
        self.orphan_child = orphan_child
        self.processes = {}
        self.closed = set()

    def dispatch(self, owner_id):
        if owner_id in self.processes:
            message = "issued invocation cannot be dispatched again"
            raise RuntimeError(message)
        invocation = self.invocations[owner_id]
        code = (
            "import pathlib,subprocess,sys\n"
            "product=pathlib.Path(sys.argv[1])\n"
            "product.write_text('baseline\\n')\n"
            "print('writing',flush=True)\n"
            "for command in sys.stdin:\n"
            " command=command.strip()\n"
            " if command == 'close': break\n"
            " if command == 'write':\n"
            "  product.write_text('late old write\\n')\n"
            "  subprocess.run(['git','update-ref','refs/owlbear/test-worker','HEAD'],cwd=product.parent,check=True)\n"
            " elif command == 'write-next':\n"
            "  product.write_text('late old write after restart\\n')\n"
            "  subprocess.run(['git','update-ref','refs/owlbear/test-worker','HEAD'],cwd=product.parent,check=True)\n"
            " elif command == 'restore':\n"
            "  product.write_text('baseline\\n')\n"
            "  subprocess.run(['git','update-ref','-d','refs/owlbear/test-worker'],cwd=product.parent,check=True)\n"
            " print(command,flush=True)\n"
            "print('all-jobs-closed',flush=True)\n"
        )
        product = Path(invocation.request.worktree) / "product.txt"
        command = (sys.executable, "-c", code, str(product))
        if self.orphan_child:
            parent_code = "import subprocess,sys\nsubprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]])\n"
            command = (sys.executable, "-c", parent_code, code, str(product))
        worker = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)  # noqa: S603
        self.processes[owner_id] = worker
        assert worker.stdout.readline().strip() == "writing"
        if self.orphan_child:
            assert worker.wait(timeout=5) == 0
        return worker

    def close(self, owner_id):
        if owner_id in self.closed:
            return
        worker = self.processes[owner_id]
        output, _ = worker.communicate("close\n", timeout=5)
        assert output.strip() == "all-jobs-closed"
        # communicate joins the issued parent and drains EOF from the orphan's
        # inherited job channel. Parent exit alone does not set this registry entry.
        assert worker.stdin.closed
        assert worker.stdout.closed
        self.closed.add(owner_id)

    def reference(self, intent):
        return RecoveryEvidenceReference(reference=f"process-owner-{intent.recovery_id}")

    def verify(self, reference, intent):
        owner_id = intent.invocation.request.owner_id
        known = self.invocations.get(owner_id) == intent.invocation and owner_id in self.processes
        status = "closed" if known and owner_id in self.closed else "still-running"
        if not known or reference != self.reference(intent):
            status = "unknown"
        return RecoveryEvidence(
            reference=reference, recovery_id=intent.recovery_id, invocation=intent.invocation, status=status
        )


def absent_host_process_case(tmp_path: Path):
    """Keep an issued descendant alive while a fresh application lacks its evidence host."""
    application, runtimes, _coordinator, state = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    host = ProcessEvidenceHost(orphan_child=True)
    application._recovery_evidence_provider = host
    launch = application.acquire_frontier_work().launch_packages[0]
    try:
        worker = host.dispatch(launch.claim.claim_id)
        protected = recovery_effect_snapshot(application, "change-a")
        reopened, _coordinator, _manager = _reopen_portfolio(
            tmp_path,
            state,
            runtimes,
            clock=lambda: "2030-01-01T00:00:00Z",
        )
        assert recovery_effect_snapshot(reopened, "change-a") == protected
        assert isinstance(reopened._recovery_evidence_provider, UnavailableRecoveryEvidenceProvider)
        exact_head = _git(launch.worktree_path, "rev-parse", "HEAD")

        def signal(command: str, expected_content: bytes) -> None:
            worker.stdin.write(f"{command}\n")
            worker.stdin.flush()
            assert worker.stdout.readline().strip() == command
            assert (launch.worktree_path / "product.txt").read_bytes() == expected_content
            if command.startswith("write"):
                assert _git(launch.worktree_path, "rev-parse", "refs/owlbear/test-worker") == exact_head

        signal("write", b"late old write\n")

        def restart():
            return _reopen_portfolio(
                tmp_path,
                state,
                runtimes,
                clock=lambda: "2030-01-01T00:00:00Z",
            )[0]

    except BaseException:
        if launch.claim.claim_id in host.processes and launch.claim.claim_id not in host.closed:
            host.close(launch.claim.claim_id)
        raise
    else:
        return reopened, host, worker, launch, restart, recovery_effect_snapshot, signal


def _host(application):
    host = EvidenceHost()
    application._recovery_evidence_provider = host
    return host


def completed_recovery_case(tmp_path: Path, kind: str):
    """Complete the actual owner transaction before testing public receipt-only replay."""
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, _state = _portfolio(
        tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION}, clock=lambda: now[0]
    )
    host = _host(application)
    launch = application.acquire_frontier_work().launch_packages[0]
    now[0] = "2026-08-04T01:00:00Z"
    proposal = application.repair("change-a").proposal
    intent = application._propose_recovery("change-a")
    application._complete_recovery("change-a", intent.recovery_id, host.seal(intent))
    if kind == "proposal":
        operation = "repair"
        request = {"change_id": "change-a", "proposal_id": proposal.proposal_id, "confirmed_lost": False}
    else:
        operation = "recover_claim"
        request = {
            "change_id": "change-a",
            "outcome_id": "OUT-001",
            "attempt_id": launch.claim.attempt_id,
            "claim_id": launch.claim.claim_id,
            "confirmed_lost": True,
        }
    before, custody = runtimes["change-a"].frontier_bytes(), coordinator.show("change-a")
    content = _file_bytes(launch.worktree_path)
    refs = _git(launch.worktree_path, "show-ref")

    def unchanged():
        assert runtimes["change-a"].frontier_bytes() == before
        assert coordinator.show("change-a") == custody
        assert _file_bytes(launch.worktree_path) == content
        assert _git(launch.worktree_path, "show-ref") == refs

    return application, operation, request, unchanged


def test_completed_outcome_repair_replays_with_retry_authority_and_preserves_result(
    tmp_path: Path,
) -> None:
    """Exercise the engine repair route after a real failed finalizer recovery."""
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, _state = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        clock=lambda: now[0],
        include_downstream=True,
    )
    host = _host(application)
    launch = application.acquire_change_action(_continuation_request(application))
    assert launch.kind == "acquired"
    assert launch.finalization is not None
    finalizer = launch.finalization.attempt
    original_action_id = finalizer.writer.attempt_id
    failure = _failure_request(application, attempt_key=original_action_id)
    report = application.report_finalization_failure(failure)

    recovery_intent = application._propose_recovery("change-a")
    application._complete_recovery("change-a", recovery_intent.recovery_id, host.seal(recovery_intent))
    assert coordinator.show("change-a").writer is None
    preservation = application._workspace_manager.capture_preservation("change-a", recovery_intent.recovery_id)

    now[0] = "2026-08-04T00:00:02Z"
    key = RetryEpisodeKey.engine(
        "change-a",
        "finalize",
        finalizer.exact_head,
        application._workspace_manager.observed_target_head(),
        None,
    )
    reservation = (
        runtimes["change-a"]
        .retry_ledger(clock=lambda: now[0])
        .reserve(
            key,
            failure_class=RetryFailureClass.MECHANICAL,
            now=now[0],
            attempt_id="repair-attempt",
            automatic=True,
            operation_alias="repair-attempt",
        )
    )
    assert reservation.allowed
    before = runtimes["change-a"].frontier_bytes()
    downstream_before = runtimes["change-a"].show_binding("OUT-002")
    request = PrepareCompletedOutcomeRepair(
        outcome_id="OUT-001",
        owning_task_id="TASK-001",
        episode_id=reservation.episode_id,
        attempt_id=reservation.attempt_id,
        defect_code=report.request.code.value,
        finding_boundary="implementation",
        original_action_id=original_action_id,
        preservation_id=preservation.preservation_id,
        expected_frontier_digest=hashlib.sha256(before).hexdigest(),
    )

    with pytest.raises(PortfolioApplicationError, match="proof-procedure repair requires a proof-mutation diagnostic"):
        application.repair_completed_outcome(
            "change-a", request.model_copy(update={"finding_boundary": "proof-procedure"})
        )
    with pytest.raises(DeliveryRuntimeReferenceError, match="task ownership is absent"):
        application.repair_completed_outcome("change-a", request.model_copy(update={"owning_task_id": "TASK-002"}))

    binding = application.repair_completed_outcome("change-a", request)
    assert binding.stage.value == "implementation"
    assert tuple(task.task_id for task in binding.tasks[:1]) == ("TASK-001",)
    assert len(binding.tasks) == 2
    assert binding.tasks[1].task_id.startswith("repair-")
    assert tuple(result.result_id for result in binding.results) == ("RESULT-001",)
    assert runtimes["change-a"].show_binding("OUT-002") == downstream_before

    reopened, reopened_coordinator, _manager = _reopen_portfolio(
        tmp_path,
        _state,
        runtimes,
        clock=lambda: now[0],
    )
    replayed = reopened.repair_completed_outcome("change-a", request)
    assert replayed == reopened._runtime("change-a").show_binding("OUT-001")
    assert tuple(result.result_id for result in replayed.results) == ("RESULT-001",)
    assert reopened._runtime("change-a").show_binding("OUT-002") == downstream_before
    assert reopened_coordinator.show("change-a").writer is None


def test_completed_repair_result_resumes_original_finalizer_after_restart(  # noqa: PLR0915 - full restart lifecycle proof.
    tmp_path: Path,
) -> None:
    """Prove the reviewed Builder repair settles only its linked finalizer episode."""
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, _provider, _provider_state, _exact_head, state = _awaiting_acceptance_fixture(tmp_path)
    runtimes = {"change-a": runtime}
    application._clock = lambda: now[0]
    invalidation = application.prepare_review_repair("change-a")
    _commit_reviewed_head(
        application,
        application._workspace_manager.show("change-a"),
        "review-repair.txt",
        "review repair\n",
        "review repair",
    )
    host = _host(application)
    first = application.acquire_change_action(_continuation_request(application))
    if first.kind == "reconciled":
        first = application.acquire_change_action(_continuation_request(application))
    assert first.kind == "acquired"
    original = first.finalization.attempt
    original_action_id = original.writer.attempt_id
    report = application.report_finalization_failure(_failure_request(application, attempt_key=original_action_id))
    recovery_intent = application._propose_recovery("change-a")
    application._complete_recovery("change-a", recovery_intent.recovery_id, host.seal(recovery_intent))
    preservation = application._workspace_manager.capture_preservation("change-a", recovery_intent.recovery_id)
    now[0] = "2026-08-04T00:00:02Z"
    key = RetryEpisodeKey.engine(
        "change-a",
        "finalize",
        original.exact_head,
        application._workspace_manager.observed_target_head(),
        invalidation.finalization_id,
    )
    repair_reservation = (
        runtimes["change-a"]
        .retry_ledger(clock=lambda: now[0])
        .reserve(
            key,
            failure_class=RetryFailureClass.MECHANICAL,
            now=now[0],
            attempt_id="repair-attempt",
            automatic=True,
            operation_alias="repair-attempt",
        )
    )
    before = runtimes["change-a"].frontier_bytes()
    request = PrepareCompletedOutcomeRepair(
        outcome_id="OUT-001",
        owning_task_id="TASK-001",
        episode_id=repair_reservation.episode_id,
        attempt_id=repair_reservation.attempt_id,
        defect_code=report.request.code.value,
        finding_boundary="implementation",
        original_action_id=original_action_id,
        preservation_id=preservation.preservation_id,
        expected_frontier_digest=hashlib.sha256(before).hexdigest(),
    )
    repair_binding = application.repair_completed_outcome("change-a", request)
    receipt_root = state / "changes" / "change-a" / "recovery-receipts"
    receipt_entry = next(entry for entry in receipt_root.iterdir() if entry.is_dir())
    symlink_name = "f" * 64 if receipt_entry.name != "f" * 64 else "e" * 64
    symlink_entry = receipt_root / symlink_name
    symlink_entry.symlink_to(receipt_entry, target_is_directory=True)
    try:
        assert application.repair_completed_outcome("change-a", request) == repair_binding
    finally:
        symlink_entry.unlink()
    before_restart = RetryLedger(state, "change-a").episode(key)
    assert before_restart is not None
    assert before_restart.total_attempts == 2
    assert before_restart.reset_count == 0
    assert digest(f"{request.attempt_id}:succeeded".encode()) not in before_restart.outcome_ids
    assert request.attempt_id in {item.attempt_id for item in RetryLedger(state, "change-a").pending_attempts()}

    reopened, _reopened_coordinator, _manager = _reopen_portfolio(
        tmp_path,
        state,
        runtimes,
        clock=lambda: now[0],
    )
    continuation = reopened.acquire_change_action(_continuation_request(reopened))
    if continuation.kind == "reconciled":
        continuation = reopened.acquire_change_action(_continuation_request(reopened))
    assert continuation.kind == "acquired"
    builder = continuation.launch
    assert builder is not None
    assert builder.claim.worker_role.value == "builder"
    task = next(
        item
        for item in reopened._runtime("change-a").show_binding(builder.outcome_id).tasks
        if item.task_id == builder.claim.task_id
    )
    _git(builder.worktree_path, "commit", "--allow-empty", "-m", "accept completed-outcome repair")
    completed_commit = _git(builder.worktree_path, "rev-parse", "HEAD")
    submission = DeliveryResultSubmission(
        change_id="change-a",
        outcome_id=builder.outcome_id,
        claim_id=builder.claim.claim_id,
        result=_task_result(
            "repair-result",
            "change-a",
            reopened._runtime("change-a").authority_digest,
            task,
            completed_commit,
        ),
    )
    accepted = reopened.submit_result(submission)
    assert accepted.result_id == "repair-result"

    restarted, restarted_coordinator, _manager = _reopen_portfolio(
        tmp_path,
        state,
        runtimes,
        clock=lambda: now[0],
    )
    readiness = restarted.get_change("change-a").readiness
    assert readiness.operation is WorkItemActionKind.FINALIZE
    assert readiness.attempts == 2
    resumed = restarted.acquire_change_action(_continuation_request(restarted))
    if resumed.kind == "reconciled":
        resumed = restarted.acquire_change_action(_continuation_request(restarted))
    assert resumed.kind == "acquired"
    resumed_finalizer = resumed.finalization.attempt
    assert resumed_finalizer.writer.attempt_id != original_action_id
    assert restarted_coordinator.show("change-a").finalization_attempt == resumed_finalizer
    assert RetryLedger(state, "change-a").repair_binding_for_original_attempt(original_action_id) is not None
    assert (
        RetryLedger(state, "change-a").repair_binding_for_original_attempt(resumed_finalizer.writer.attempt_id) is None
    )
    resumed_episode = RetryLedger(state, "change-a").episode(key)
    assert resumed_episode is not None
    assert resumed_episode.episode_id == key.identity
    assert resumed_episode.total_attempts == 3
    assert resumed_episode.reset_count == 0
    assert digest(f"{request.attempt_id}:succeeded".encode()) in resumed_episode.outcome_ids
    assert digest(f"{original_action_id}:failed".encode()) in resumed_episode.outcome_ids


@pytest.mark.parametrize("writer_recorded", [False, True])
def test_verified_activation_recovery_and_restart(tmp_path, writer_recorded):
    application, runtimes, coordinator, state = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    host = _host(application)
    acquire = coordinator.acquire

    def fail(change_id, writer, **kwargs):
        if writer_recorded:
            acquire(change_id, writer, **kwargs)
        message = "writer persistence failed"
        raise OSError(message)

    with patch.object(coordinator, "acquire", fail):
        stopped = application.acquire_change_action(_continuation_request(application))
    assert stopped.reason_code == "claim-activation-failed"
    claim = runtimes["change-a"].active_claims()[0][1]
    intent = application._propose_recovery("change-a")
    reference = host.seal(intent)
    receipt = application._complete_recovery("change-a", intent.recovery_id, reference)
    assert receipt.owner_effect == "no-workspace-effect"
    assert runtimes["change-a"].active_claims() == ()
    assert coordinator.show("change-a").writer is None
    reopened, _, _ = _reopen_portfolio(tmp_path, state, runtimes)
    reopened._recovery_evidence_provider = host
    before = runtimes["change-a"].frontier_bytes()
    assert reopened._complete_recovery("change-a", intent.recovery_id, reference) == receipt
    assert reopened.recover_claim("change-a", "OUT-001", claim.attempt_id, claim.claim_id).status.value == "recovered"
    assert runtimes["change-a"].frontier_bytes() == before
    result = reopened.acquire_change_action(_continuation_request(reopened))
    if result.kind == "reconciled":
        result = reopened.acquire_change_action(_continuation_request(reopened))
    assert result.kind == "acquired"
    assert result.launch.claim.claim_id != claim.claim_id
    assert application.acquire_change_action(_continuation_request(application)).kind == "busy"
    runtime = runtimes["change-a"]
    late = DeliveryResultSubmission(
        change_id="change-a",
        outcome_id="OUT-001",
        claim_id=claim.claim_id,
        result=_task_result(
            "late-result",
            "change-a",
            runtime.authority_digest,
            runtime.show_binding("OUT-001").tasks[0],
            intent.exact_head,
        ),
    )
    with pytest.raises(RuntimeError):
        application.submit_result(late)
    assert runtime.active_claims() == (("OUT-001", result.launch.claim),)


def _reopen_excluded_recovery(tmp_path, runtimes, host, intent, receipt):
    reopened, coordinator, _manager = _reopen_portfolio(
        tmp_path, Path(intent.invocation.request.runtime_root), runtimes
    )
    reference = receipt.evidence.reference
    frontier = runtimes["change-a"].frontier_bytes()
    custody = coordinator.show("change-a")
    assert not reopened.get_change("change-a").readiness.executable
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        coordinator.prepare_runtime_custody_guard("change-a")
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        reopened._complete_recovery("change-a", intent.recovery_id, reference)
    assert runtimes["change-a"].frontier_bytes() == frontier
    assert coordinator.show("change-a") == custody
    reopened._recovery_evidence_provider = host
    host.seal(intent, "closed")
    assert reopened._complete_recovery("change-a", intent.recovery_id, reference) == receipt
    coordinator.prepare_runtime_custody_guard("change-a")
    return reopened, coordinator


@pytest.mark.parametrize("evidence_status", ["closed", "excluded"])
def test_verified_clean_finalizer_recovery_keeps_failed_history(tmp_path, evidence_status):
    application, runtimes, coordinator, state = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    host = _host(application)
    attempt = application.acquire_change_action(_continuation_request(application)).finalization.attempt
    report = application.report_finalization_failure(
        _failure_request(application, attempt_key=attempt.writer.attempt_id)
    )
    intent = application._propose_recovery("change-a")
    assert intent.failure_id == report.report_id
    reference = host.seal(intent, evidence_status)
    receipt = application._complete_recovery("change-a", intent.recovery_id, reference)
    assert runtimes["change-a"].finalization() is None
    assert coordinator.show("change-a").writer is None
    assert coordinator.show("change-a").finalization_attempt.finished_at == receipt.finished_at
    assert (state / journal_path("change-a", intent.recovery_id, "intent")).exists()
    if evidence_status == "excluded":
        application, coordinator = _reopen_excluded_recovery(tmp_path, runtimes, host, intent, receipt)
    else:
        waiting = application.acquire_change_action(_continuation_request(application))
        assert waiting.finalization is None
        assert waiting.readiness.reason_code == "retry-backoff"
        application._clock = lambda: "2026-08-04T00:00:01Z"
    with pytest.raises(RuntimeError):
        application.finalize_change(
            "change-a", _finalization_request("change-a", attempt.exact_head, attempt.writer.attempt_id)
        )
    replacement = application.acquire_change_action(_continuation_request(application))
    assert replacement.kind == "acquired"
    assert replacement.finalization.attempt.writer.claim_id != attempt.writer.claim_id
    with pytest.raises(RuntimeError):
        application.finalize_change(
            "change-a", _finalization_request("change-a", attempt.exact_head, attempt.writer.attempt_id)
        )
    assert coordinator.show("change-a").writer == replacement.finalization.attempt.writer


@pytest.mark.parametrize("stored", [18, 19])
def test_clean_finalizer_recovery_of_a_stored_v18_frontier_records_one_marker_on_its_published_base(
    tmp_path: Path, stored: int
) -> None:
    application, runtimes, _coordinator, state = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    runtime = runtimes["change-a"]
    repository = application._workspace_manager.repository
    _attach_local_target(application, tmp_path)
    frontier_path = state / "changes/change-a/frontier.json"
    if stored == 18:
        _store_v18(frontier_path)
    application._delivery_state_publisher = DeliveryStatePublisher(
        repository, remote="origin", state_branch="owlbear/delivery-state"
    )
    state_head = application._publish_delivery_state("change-a", runtime, "v18-recovery-baseline").published_head
    if stored == 18:
        state_head = _relabel_as_snapshot_2(repository, state_head)
    snapshot = json.loads(_git(repository, "show", f"{state_head}:.owlbear/delivery/state/change-a/snapshot.json"))
    application._delivery_state_publisher = None
    host = _host(application)
    attempt = application.acquire_change_action(_continuation_request(application)).finalization.attempt
    application.report_finalization_failure(_failure_request(application, attempt_key=attempt.writer.attempt_id))
    intent = application._propose_recovery("change-a")
    before = frontier_path.read_bytes()
    assert json.loads(before)["schema_version"] == stored

    application._complete_recovery("change-a", intent.recovery_id, host.seal(intent, "closed"))

    written = frontier_path.read_bytes()
    assert json.loads(written)["schema_version"] == 19
    marker = runtime.pending_state_publication()
    if stored == 19:
        assert written == before
        assert marker is None
        return
    assert marker is not None
    assert marker.base_frontier_digest == runtime.publication_base_digest(before)
    assert (
        marker.base_frontier_digest
        == hashlib.sha256(
            (json.dumps(snapshot["frontier"], sort_keys=True, separators=(",", ":")) + "\n").encode()
        ).hexdigest()
    )
    assert marker.frontier_digest == hashlib.sha256(written).hexdigest()

    reopened, _reopened_coordinator, _manager = _reopen_portfolio(tmp_path, state, runtimes)
    assert reopened.get_change("change-a").change_id == "change-a"
    assert reopened._runtimes["change-a"].pending_state_publication() == marker
    reopened._delivery_state_publisher = DeliveryStatePublisher(
        repository, remote="origin", state_branch="owlbear/delivery-state"
    )
    assert reopened._replay_pending_state_publications() == ()
    _git(repository, "fetch", "origin", "+refs/heads/owlbear/delivery-state:refs/remotes/origin/owlbear/delivery-state")
    published = _git(repository, "rev-parse", "refs/remotes/origin/owlbear/delivery-state")
    assert _git(repository, "rev-list", "--count", f"{state_head}..{published}") == "1"
    republished = json.loads(_git(repository, "show", f"{published}:.owlbear/delivery/state/change-a/snapshot.json"))
    assert republished["schema_version"] == 3
    assert republished["parent_snapshot_id"] == snapshot["snapshot_id"]
    assert reopened._runtimes["change-a"].pending_state_publication() is None
    assert reopened._replay_pending_state_publications() == ()
    _git(repository, "fetch", "origin", "+refs/heads/owlbear/delivery-state:refs/remotes/origin/owlbear/delivery-state")
    assert _git(repository, "rev-parse", "refs/remotes/origin/owlbear/delivery-state") == published


def _legacy_finalization(
    finalization: DeliveryFinalizationReceipt, results: tuple[DeliveryTaskResult, ...]
) -> DeliveryFinalizationReceipt:
    """Return the same finalization as a D03 schema-2 record holding only schema-1 evidence."""
    observation_values = {
        "schema_version": 1,
        "change_id": finalization.change_id,
        "task_or_finalization_id": finalization.operation_id,
        "step_id": None,
        "exact_commit": finalization.exact_head,
        "observation_kind": "pytest",
        "command_or_procedure": "Portfolio finalization exact-head check",
        "exit_status_or_artifact_locator": "exit:0",
        "observer_or_runner_identity": "pytest",
        "observed_at": finalization.finalized_at,
    }
    observation = DeliveryLegacyObservationReceipt.model_construct(observation_id="0" * 64, **observation_values)
    review_values = {
        "schema_version": 1,
        "exact_commit": finalization.exact_head,
        "author_id": finalization.review.author_id,
        "reviewer_id": finalization.review.reviewer_id,
        "disposition": "pass",
        "evidence": finalization.review.evidence,
        "reviewed_at": finalization.review.reviewed_at,
    }
    review = DeliveryReviewReceipt.model_construct(review_id="0" * 64, **review_values)
    return DeliveryFinalizationReceipt.create(
        DeliveryFinalization(
            schema_version=2,
            operation_id=finalization.operation_id,
            change_id=finalization.change_id,
            exact_head=finalization.exact_head,
            authority_digest=finalization.authority_digest,
            result_digests=tuple(hashlib.sha256(_model_content(result)).hexdigest() for result in results),
            observations=(
                DeliveryLegacyObservationReceipt(
                    observation_id=_receipt_digest(observation, "observation_id"), **observation_values
                ),
            ),
            review=DeliveryReviewReceipt(review_id=_receipt_digest(review, "review_id"), **review_values),
            finalized_at=finalization.finalized_at,
        )
    )


def _store_as_schema_18(frontier_path: Path, frontier: DeliveryFrontier) -> bytes:
    """Store ``frontier`` as schema 18; the retained model refuses any N03 content at that version (I2)."""
    payload = frontier.model_dump(mode="json") | {"schema_version": 18}
    content = _canonical(DeliveryFrontier.model_validate_json(json.dumps(payload), strict=True))
    frontier_path.write_bytes(content)
    return content


def _store_d03_records(frontier_path: Path) -> bytes:
    """Rebuild every typed result and finalization from the retained legacy models, then store schema 18."""
    frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
    bindings = tuple(
        binding.model_copy(update={"results": tuple(_legacy_task_result(item) for item in binding.results)})
        for binding in frontier.bindings
    )
    finalization = frontier.finalization
    if finalization is not None:
        finalization = _legacy_finalization(
            finalization, tuple(item for binding in bindings for item in binding.results)
        )
    return _store_as_schema_18(
        frontier_path, frontier.model_copy(update={"bindings": bindings, "finalization": finalization})
    )


def _acknowledge_local_markers(runtime: DeliveryRuntime) -> None:
    """Drop the setup's local markers; the fixture publishes the resulting state itself."""
    marker = runtime.pending_state_publication()
    if marker is not None:
        runtime.acknowledge_pending_publication(marker.frontier_digest)
    assert runtime.pending_state_publication() is None


def _mock_pull_request_publisher(tmp_path: Path, exact_head: str) -> DraftPullRequestPublisher:
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
                "<!-- owlbear-change:change-a -->\n\n<!-- owlbear-generated:start -->\n"
                "Finalized Change A.\n<!-- owlbear-generated:end -->\n"
            ),
            draft=True,
            state="open",
            merged=False,
        )
    }
    provider = Mock()
    provider.read_repository.return_value = PublicationRepository(repository="example/project", default_branch="main")
    provider.find_pull_request.side_effect = lambda *_args, **_kwargs: state["pull_request"]
    provider.create_draft_pull_request.side_effect = lambda _request: state["pull_request"]
    provider.read_pull_request.side_effect = lambda _repository, _number: state["pull_request"]
    provider.observe_checks.return_value = PublicationCheckSnapshot(
        repository="example/project", number=7, head_sha=exact_head, checks=()
    )

    def set_draft_state(request: Any) -> PublicationPullRequest:
        state["pull_request"] = state["pull_request"].model_copy(update={"draft": request.draft})
        return state["pull_request"]

    provider.set_pull_request_draft_state.side_effect = set_draft_state
    return DraftPullRequestPublisher(
        provider, repository="example/project", target_branch="main", state_root=tmp_path / "pull-requests"
    )


def _d03_ready_readback_owner(application: Any, tmp_path: Path, frontier_path: Path) -> Any:
    """Finalize, publish the draft PR, and let a D03-era mark-ready owner lose its engine result."""
    runtime = application._runtimes["change-a"]
    exact_head = application._workspace_manager.show("change-a").last_reviewed_commit
    application.finalize_change("change-a", _finalization_request("change-a", exact_head, runtime=runtime))
    publisher = _mock_pull_request_publisher(tmp_path, exact_head)
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
    runtime.record_publication_identity(
        DeliveryChangePublicationIdentity(
            change_id="change-a", repository="example/project", number=7, node_id="PR_node_7", head_sha=exact_head
        )
    )
    _acknowledge_local_markers(runtime)
    _store_d03_records(frontier_path)
    host = _host(application)
    action = _engine_action(application)
    invoke = application._invoke_engine_owner

    def lose_result(retained: Any) -> None:
        invoke(retained)
        raise KeyboardInterrupt

    with patch.object(application, "_invoke_engine_owner", side_effect=lose_result), pytest.raises(KeyboardInterrupt):
        _execute_engine(application, action)
    ready = runtime.ready_receipt()
    assert ready is not None
    assert ready.finalization_id == runtime.finalization().finalization_id
    _acknowledge_local_markers(runtime)
    # The D03 owner wrote the ready receipt at schema 18; only legacy records are present to store.
    _store_as_schema_18(frontier_path, DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True))
    return host


def _d03_finalizer_workspace(tmp_path: Path, kind: str) -> tuple[Path, Path, str, Any]:
    """Seed a loader workspace whose remote snapshot 2 holds the local D03 (schema-18) frontier.

    Returns the repository, the runtime root, the relabeled state head and, for ready-readback, the
    seeding application whose process host and draft PR provider observed the lost owner.
    """
    repository, runtime_root = _seed_loader_composed_completed_change(tmp_path)
    remote = tmp_path / "state-remote.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    _git(repository, "push", "origin", "HEAD:refs/heads/main")
    frontier_path = runtime_root / "changes/change-a/frontier.json"
    seeding = load_delivery_application(_LOADER_CONFIG, workspace_root=repository)
    state_publisher = seeding._delivery_state_publisher
    assert state_publisher is not None
    seeding._delivery_state_publisher = None
    runtime = seeding._runtimes["change-a"]
    seeding.sync_change_with_target("change-a", seeding._workspace_manager.observed_target_head(), "sync-d03")
    _acknowledge_local_markers(runtime)
    if kind == "ready-readback":
        seeding._recovery_evidence_provider = _d03_ready_readback_owner(seeding, tmp_path, frontier_path)
    else:
        _store_d03_records(frontier_path)
    published = state_publisher.publish(
        change_id="change-a",
        package_id=seeding._package_store.read_verified("change-a").package_id,
        coordination=seeding._workspace_manager.show("change-a"),
        runtime=runtime,
        admission=_admission(runtime, seeding._workspace_manager, "change-a"),
        operation_id="d03-finalizer-state",
        captured_at=datetime(2026, 8, 4, tzinfo=UTC),
    )
    state_head = _relabel_as_snapshot_2(repository, published.published_head)
    return repository, runtime_root, state_head, seeding if kind == "ready-readback" else None


def _assert_default_loader_republishes_once(repository: Path, state_head: str, marker: object) -> str:
    """Reload through the default loader, replay the marker once, and converge on a second reload."""
    snapshot_2 = json.loads(_git(repository, "show", f"{state_head}:{_LOADER_SNAPSHOT_PATH}"))
    reloaded = load_delivery_application(_LOADER_CONFIG, workspace_root=repository)
    assert "state-publication-pending" in [item.code for item in reloaded.delivery_health().diagnostics]
    assert reloaded.get_change("change-a").change_id == "change-a"
    assert reloaded._runtimes["change-a"].pending_state_publication() == marker
    assert reloaded._replay_pending_state_publications() == ()
    _git(repository, "fetch", "origin", "+refs/heads/owlbear/delivery-state:refs/remotes/origin/owlbear/delivery-state")
    republished_head = _git(repository, "rev-parse", "refs/remotes/origin/owlbear/delivery-state")
    assert _git(repository, "rev-list", "--count", f"{state_head}..{republished_head}") == "1"
    republished = json.loads(_git(repository, "show", f"{republished_head}:{_LOADER_SNAPSHOT_PATH}"))
    assert republished["schema_version"] == 3
    assert republished["parent_snapshot_id"] == snapshot_2["snapshot_id"]

    converged = load_delivery_application(_LOADER_CONFIG, workspace_root=repository)
    assert converged._runtimes["change-a"].pending_state_publication() is None
    assert converged._replay_pending_state_publications() == ()
    _git(repository, "fetch", "origin", "+refs/heads/owlbear/delivery-state:refs/remotes/origin/owlbear/delivery-state")
    assert _git(repository, "rev-parse", "refs/remotes/origin/owlbear/delivery-state") == republished_head
    return republished_head


@pytest.mark.parametrize("kind", ["clean-finalizer", "ready-readback"])
def test_v18_finalizer_recovery_reloads_through_the_default_loader_and_republishes_once(
    tmp_path: Path, kind: str
) -> None:
    repository, runtime_root, state_head, owner = _d03_finalizer_workspace(tmp_path, kind)
    frontier_path = runtime_root / "changes/change-a/frontier.json"
    snapshot_2 = json.loads(_git(repository, "show", f"{state_head}:{_LOADER_SNAPSHOT_PATH}"))
    stored = frontier_path.read_bytes()
    assert json.loads(stored)["schema_version"] == 18
    nested = _nested_receipt_ids(stored)

    application = load_delivery_application(_LOADER_CONFIG, workspace_root=repository)
    loaded = application._runtimes["change-a"]
    assert loaded.frontier_bytes() == stored
    assert loaded.pending_state_publication() is None
    application._delivery_state_publisher = None
    if owner is not None:
        # The process host that observed the lost owner keeps its evidence across the controller reload.
        host = owner._recovery_evidence_provider
        application._recovery_evidence_provider = host
        application._draft_pull_request_publisher = owner._draft_pull_request_publisher
    else:
        host = _host(application)
        acquired = application.acquire_change_action(_continuation_request(application))
        assert acquired.finalization is not None, acquired.readiness.model_dump_json()
        attempt = acquired.finalization.attempt
        application.report_finalization_failure(_failure_request(application, attempt_key=attempt.writer.attempt_id))
    intent = application._propose_recovery("change-a")
    assert intent.kind == kind
    assert frontier_path.read_bytes() == stored

    receipt = application._complete_recovery("change-a", intent.recovery_id, host.seal(intent, "closed"))

    written = frontier_path.read_bytes()
    assert json.loads(written)["schema_version"] == 19
    assert _nested_receipt_ids(written) == nested
    marker = loaded.pending_state_publication()
    assert marker is not None
    remote_base = hashlib.sha256(
        (json.dumps(snapshot_2["frontier"], sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    assert marker.base_frontier_digest == loaded.publication_base_digest(stored) == remote_base
    assert marker.frontier_digest == hashlib.sha256(written).hexdigest()
    recovery_records = _recovery_records(runtime_root, intent.recovery_id)
    assert encoded(receipt) == recovery_records["receipt"]

    _assert_default_loader_republishes_once(repository, state_head, marker)

    assert json.loads(_git(repository, "show", f"{state_head}:{_LOADER_SNAPSHOT_PATH}")) == snapshot_2
    assert _recovery_records(runtime_root, intent.recovery_id) == recovery_records
    assert frontier_path.read_bytes() == written


def _nested_receipt_ids(content: bytes) -> dict[str, object]:
    frontier = json.loads(content)
    finalization = frontier.get("finalization") or {}
    return {
        "head": finalization.get("exact_head") or "",
        "results": [
            (result["review"]["review_id"], [item["observation_id"] for item in result["observations"]])
            for binding in frontier["bindings"]
            for result in binding.get("results", [])
        ],
        "finalization": finalization.get("finalization_id"),
        "ready": (frontier.get("ready") or {}).get("receipt_id"),
    }


def _recovery_records(runtime_root: Path, recovery_id: str) -> dict[str, bytes]:
    return {
        record: (runtime_root / journal_path("change-a", recovery_id, record)).read_bytes()
        for record in ("intent", "evidence", "receipt")
    }


@pytest.mark.parametrize("exhausted", [False, True])
def test_review_repair_finalizer_readiness_and_acquisition_share_retry_identity(  # noqa: PLR0915
    tmp_path: Path, *, exhausted: bool
) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, _provider, _state, _exact_head, state_root = _awaiting_acceptance_fixture(tmp_path)
    application._clock = lambda: now[0]
    host = _host(application)
    invalidation = application.prepare_review_repair("change-a")
    coordination = application._workspace_manager.show("change-a")
    repaired_head = _commit_reviewed_head(
        application,
        coordination,
        "review-fix.txt",
        "review fix\n",
        "repair review",
    )

    acquired = application.acquire_change_action(_continuation_request(application))
    if acquired.kind == "reconciled":
        acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.kind == "acquired"
    attempt = acquired.finalization.attempt
    assert attempt.exact_head == repaired_head
    assert application.report_finalization_failure(_failure_request(application, attempt_key=attempt.writer.attempt_id))
    intent = application._propose_recovery("change-a")
    application._complete_recovery("change-a", intent.recovery_id, host.seal(intent))

    key = RetryEpisodeKey.engine(
        "change-a",
        "finalize",
        repaired_head,
        application._workspace_manager.observed_target_head(),
        invalidation.finalization_id,
    )
    episode = RetryLedger(state_root, "change-a").episode(key)
    assert episode is not None
    assert episode.total_attempts == 1
    if exhausted:
        for timestamp in ("2026-08-04T00:00:01Z", "2026-08-04T00:00:03Z"):
            now[0] = timestamp
            retry = application.acquire_change_action(_continuation_request(application))
            if retry.kind == "reconciled":
                retry = application.acquire_change_action(_continuation_request(application))
            assert retry.kind == "acquired"
            retry_attempt = retry.finalization.attempt
            assert application.report_finalization_failure(
                _failure_request(application, attempt_key=retry_attempt.writer.attempt_id)
            )
            retry_intent = application._propose_recovery("change-a")
            application._complete_recovery("change-a", retry_intent.recovery_id, host.seal(retry_intent))
        episode = RetryLedger(state_root, "change-a").episode(key)
        assert episode is not None
        assert episode.total_attempts == 3
    repair_binding_reads = []
    original_repair_bindings = RetryLedger.repair_bindings
    expected_repair_binding_reads = [] if exhausted else [False]

    def read_repair_bindings(ledger, *, recover_transactions=True):
        repair_binding_reads.append(recover_transactions)
        return original_repair_bindings(ledger, recover_transactions=recover_transactions)

    with patch.object(RetryLedger, "repair_bindings", read_repair_bindings):
        readiness = application.get_change("change-a").readiness
    assert repair_binding_reads == [False]
    assert readiness.reason_code == ("retry-exhausted" if exhausted else "retry-backoff")
    assert readiness.attempts == (3 if exhausted else 1)
    assert readiness.next_eligible_at == ("2026-08-04T00:00:01Z" if not exhausted else None)
    assert not readiness.executable
    snapshot = application._delivery_snapshot(runtime)
    projector = application._read_projector(snapshot)
    card = application._selected_change_card(snapshot, projector.group_view().items)
    assert card.readiness is not None
    pending_path = state_root / "readiness-pending.txt"
    pending_transaction = RuntimeTransaction(
        state_root,
        f"readiness-pending-{exhausted}",
        (TransactionParticipant(state_root, Path("readiness-pending.txt"), b"must-not-appear"),),
    )

    def interrupt(stage: str) -> None:
        if stage == "after-first-publication":
            message = "injected pending readiness transaction"
            raise OSError(message)

    with pytest.raises(OSError, match="injected pending readiness transaction"):
        pending_transaction.commit(failure=interrupt)
    pending_manifests = tuple((path, path.read_bytes()) for path in (state_root / "transactions").glob("*.yaml"))
    assert pending_manifests
    assert pending_path.read_bytes() == b"must-not-appear"
    repair_binding_reads.clear()
    with patch.object(RetryLedger, "repair_bindings", read_repair_bindings):
        readiness = application._with_retry_readiness(snapshot, card, card.readiness)
    assert repair_binding_reads == expected_repair_binding_reads
    assert pending_path.read_bytes() == b"must-not-appear"
    assert tuple((path, path.read_bytes()) for path, _content in pending_manifests) == pending_manifests
    assert readiness.attempts == (3 if exhausted else 1)

    blocked = application.acquire_change_action(_continuation_request(application))
    assert blocked.kind == ("unsupported" if exhausted else "waiting")
    assert blocked.reason_code == ("retry-exhausted" if exhausted else "retry-backoff")
    assert blocked.readiness is not None
    assert blocked.readiness.attempts == (3 if exhausted else 1)
    if exhausted:
        assert blocked.readiness.operation is None
        assert blocked.readiness.next_actor.value == "agent"
        assert blocked.readiness.prompt is not None
        assert blocked.readiness.prompt.startswith("/inspect-change change-a Diagnose the exhausted retry episode")
    assert RetryLedger(state_root, "change-a").episode(key).total_attempts == (3 if exhausted else 1)
    assert runtime.finalization() is None


def test_finalizer_budget_survives_recovery_reports_and_restart(tmp_path):
    now = "2026-08-04T00:00:00Z"
    application, runtimes, coordinator, state = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED, "change-b": DeliveryStage.COMPLETED},
        clock=lambda: now,
    )
    host = _host(application)
    for seconds in ("00", "01", "03"):
        now = f"2026-08-04T00:00:{seconds}Z"
        acquired = application.acquire_change_action(_continuation_request(application))
        assert acquired.finalization is not None, acquired
        attempt = acquired.finalization.attempt
        application.report_finalization_failure(_failure_request(application, attempt_key=attempt.writer.attempt_id))
        intent = application._propose_recovery("change-a")
        application._complete_recovery("change-a", intent.recovery_id, host.seal(intent, "closed"))
        assert coordinator.show("change-a").writer is None
        assert not application.get_change("change-a").readiness.executable
    reopened, _, _ = _reopen_portfolio(tmp_path, state, runtimes, clock=lambda: now)
    assert reopened.get_change("change-a").readiness.reason_code == "retry-exhausted"
    assert reopened.get_change("change-a").readiness.attempts == 3
    assert reopened.acquire_change_action(_continuation_request(reopened)).finalization is None
    assert reopened.acquire_change_action(_continuation_request(reopened, "change-b")).finalization is not None


def test_finalizer_recovery_reconciles_interrupted_report_accounting(tmp_path):
    application, _runtimes, _coordinator, state = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    host = _host(application)
    attempt = application.acquire_change_action(_continuation_request(application)).finalization.attempt
    with patch.object(RetryLedger, "record_failure", side_effect=OSError("injected accounting interruption")):
        application.report_finalization_failure(_failure_request(application, attempt_key=attempt.writer.attempt_id))
    assert RetryLedger(state, "change-a").read().episodes[0].last_status == "reserved"
    intent = application._propose_recovery("change-a")
    application._complete_recovery("change-a", intent.recovery_id, host.seal(intent, "closed"))
    episode = RetryLedger(state, "change-a").read().episodes[0]
    assert episode.total_attempts == 1
    assert episode.last_status == "failed"
    assert episode.next_eligible_at == "2026-08-04T00:00:01Z"
    assert application.get_change("change-a").readiness.reason_code == "retry-backoff"


@pytest.mark.parametrize("interrupted", [False, True])
@pytest.mark.parametrize("evidence_status", ["closed", "excluded"])
def test_verified_interrupted_ready_owner_readback_never_redispatches(tmp_path, interrupted, evidence_status):
    application, runtime, provider, _state, _head, state_root = _awaiting_acceptance_fixture(tmp_path, mark_ready=False)
    _attach_local_target(application, tmp_path)
    application._delivery_state_publisher = DeliveryStatePublisher(
        application._workspace_manager.repository, remote="origin", state_branch="owlbear/delivery-state"
    )
    application._publish_delivery_state("change-a", runtime, "baseline-before-ready")
    host = _host(application)
    action = _engine_action(application)
    invoke = application._invoke_engine_owner

    def lose_result(retained):
        invoke(retained)
        if interrupted:
            raise KeyboardInterrupt
        message = "lost result after completed effect"
        raise RuntimeError(message)

    with patch.object(application, "_invoke_engine_owner", side_effect=lose_result):
        if interrupted:
            with pytest.raises(KeyboardInterrupt):
                _execute_engine(application, action)
        else:
            failed = _execute_engine(application, action)
            assert failed.kind == "blocked"
    result_path = application._coordinator.continuation_record_path("change-a", action.operation_id, result=True)
    original = result_path.read_bytes() if result_path.exists() else None
    intent = application._propose_recovery("change-a")
    reference = host.seal(intent, evidence_status)
    mutations = provider.set_pull_request_draft_state.call_count
    receipt = application._complete_recovery("change-a", intent.recovery_id, reference)
    assert receipt.owner_effect == "ready-receipt-readback"
    assert provider.set_pull_request_draft_state.call_count == mutations == 1
    assert (result_path.read_bytes() if result_path.exists() else None) == original
    if interrupted:
        with pytest.raises(RuntimeError):
            _execute_engine(application, action)
    else:
        assert _execute_engine(application, action) == failed
    reopened, _, _ = _reopen_portfolio(tmp_path, state_root, {"change-a": runtime})
    reopened._recovery_evidence_provider = host
    assert reopened._complete_recovery("change-a", intent.recovery_id, reference) == receipt
    if evidence_status == "excluded":
        _reopen_excluded_recovery(tmp_path, {"change-a": runtime}, host, intent, receipt)
        assert provider.set_pull_request_draft_state.call_count == mutations
        assert (result_path.read_bytes() if result_path.exists() else None) == original


def test_failed_finalizer_cannot_use_legacy_restart_or_reviewed_release(tmp_path):
    application, _runtimes, coordinator, _state = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    attempt = application.acquire_change_action(_continuation_request(application)).finalization.attempt
    application.report_finalization_failure(_failure_request(application, attempt_key=attempt.writer.attempt_id))
    manager = application._workspace_manager
    worktree = coordinator.show("change-a").worktree_path
    _git(worktree, "commit", "--allow-empty", "-m", "unpromoted proof effect")
    head, before = _git(worktree, "rev-parse", "HEAD"), _git(worktree, "show-ref")
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        manager.restart("change-a", attempt.writer.attempt_id, head)
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        manager.complete_reviewed("change-a", attempt.writer.claim_id, head)
    assert _git(worktree, "show-ref") == before
    assert coordinator.show("change-a").writer == attempt.writer
    assert coordinator.show("change-a").last_reviewed_commit == attempt.exact_head


def test_claim_only_activation_cannot_recreate_old_workers_worktree(tmp_path):
    application, runtimes, coordinator, _state = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    with patch.object(coordinator, "acquire", side_effect=OSError("failed")):
        application.acquire_change_action(_continuation_request(application))
    assert runtimes["change-a"].active_claims()
    coordination = coordinator.show("change-a")
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application.recover_change_worktree("change-a", coordination.last_reviewed_commit, confirmed_recovery=True)
    assert coordinator.show("change-a") == coordination


def test_evidence_owner_failure_and_forged_completed_receipt_never_release(tmp_path):
    application, runtimes, coordinator, state = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    host = _host(application)
    launch = application.acquire_change_action(_continuation_request(application)).launch
    intent = application._propose_recovery("change-a")
    reference = host.seal(intent)
    with (
        patch.object(host, "verify", side_effect=OSError("host unavailable")),
        pytest.raises(DeliveryWorkerExclusionRequiredError),
    ):
        application._complete_recovery("change-a", intent.recovery_id, reference)
    from owlbear_delivery.recovery import RecoveryReceipt, encoded  # noqa: PLC0415

    forged = RecoveryReceipt(
        recovery_id=intent.recovery_id,
        evidence=host.evidence[reference.reference],
        owner_effect="no-workspace-effect",
        finished_at="2026-08-04T01:00:00Z",
    )
    (state / journal_path("change-a", intent.recovery_id, "receipt")).write_bytes(encoded(forged))
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application.recover_claim("change-a", "OUT-001", launch.claim.attempt_id, launch.claim.claim_id)
    assert runtimes["change-a"].active_claims() == (("OUT-001", launch.claim),)
    assert coordinator.show("change-a").writer == launch.writer


def test_malformed_coordination_keeps_recovery_contained(tmp_path):
    application, runtimes, _coordinator, state = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    host = _host(application)
    application.acquire_change_action(_continuation_request(application))
    intent = application._propose_recovery("change-a")
    path = state / "coordination/changes/change-a.json"
    path.write_bytes(b"{")
    frontier = runtimes["change-a"].frontier_bytes()
    with pytest.raises(RuntimeError):
        application._complete_recovery("change-a", intent.recovery_id, host.seal(intent))
    assert path.read_bytes() == b"{"
    assert runtimes["change-a"].frontier_bytes() == frontier


def test_recovery_intent_fences_normal_release_restart_and_prepared_writers(tmp_path):
    application, runtimes, coordinator, state = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    _host(application)
    launch = application.acquire_change_action(_continuation_request(application)).launch
    manager = application._workspace_manager
    prepared_guard = manager.prepare_runtime_custody_guard("change-a")
    intent = application._propose_recovery("change-a")
    assert coordinator.show("change-a").recovery_owner_id == launch.claim.claim_id
    before = runtimes["change-a"].frontier_bytes()
    refs = _git(launch.worktree_path, "show-ref")
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        coordinator.release("change-a", launch.claim.claim_id)
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        manager.restart("change-a", launch.claim.attempt_id, intent.exact_head)
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        manager.complete_reviewed("change-a", launch.claim.claim_id, intent.exact_head)
    runtime = runtimes["change-a"]
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application.submit_result(
            DeliveryResultSubmission(
                change_id="change-a",
                outcome_id="OUT-001",
                claim_id=launch.claim.claim_id,
                result=_task_result(
                    "late-pending-result",
                    "change-a",
                    runtime.authority_digest,
                    runtime.show_binding("OUT-001").tasks[0],
                    intent.exact_head,
                ),
            )
        )
    with pytest.raises(TransactionConflictError):
        RuntimeTransaction(state, "stale-before-recovery-guard", (prepared_guard,)).commit()
    assert runtimes["change-a"].frontier_bytes() == before
    assert _git(launch.worktree_path, "show-ref") == refs
    assert coordinator.show("change-a").writer == launch.writer


@pytest.mark.parametrize("status", ["unknown", "unavailable", "still-running"])
def test_owner_evidence_exclusion_required_without_verified_closure(tmp_path, status):
    application, runtimes, coordinator, _state = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    host = _host(application)
    application.acquire_change_action(_continuation_request(application))
    intent = application._propose_recovery("change-a")
    frontier, custody = runtimes["change-a"].frontier_bytes(), coordinator.show("change-a")
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application._complete_recovery("change-a", intent.recovery_id, host.seal(intent, status))
    assert runtimes["change-a"].frontier_bytes() == frontier
    assert coordinator.show("change-a") == custody


def test_verified_exclusion_is_revalidated_after_restart(tmp_path):
    application, runtimes, coordinator, state = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    host = _host(application)
    launch = application.acquire_change_action(_continuation_request(application)).launch
    intent = application._propose_recovery("change-a")
    reference = host.seal(intent, "excluded")
    receipt = application._complete_recovery("change-a", intent.recovery_id, reference)
    reopened, _, _ = _reopen_portfolio(tmp_path, state, runtimes)
    reopened._recovery_evidence_provider = host
    assert reopened._complete_recovery("change-a", intent.recovery_id, reference) == receipt
    host.seal(intent, "unknown")
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        reopened.recover_claim("change-a", "OUT-001", launch.claim.attempt_id, launch.claim.claim_id)
    assert coordinator.show("change-a").writer is None


@pytest.mark.parametrize("crash", [None, "evidence", "receipt"])
def test_restart_cannot_use_exclusion_receipt_without_current_host_verification(tmp_path, crash):
    application, runtimes, coordinator, state = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    host = _host(application)
    launch = application.acquire_change_action(_continuation_request(application)).launch
    intent = application._propose_recovery("change-a")
    reference = host.seal(intent, "excluded")
    commit = RuntimeTransaction.commit

    def fail(transaction, **kwargs):
        def interrupt(point):
            if point == "after-first-publication":
                raise KeyboardInterrupt

        if any(part.relative_path.name == f"{crash}.json" for part in transaction._participants):
            kwargs["failure"] = interrupt
        return commit(transaction, **kwargs)

    if crash:
        with patch.object(RuntimeTransaction, "commit", fail), pytest.raises(KeyboardInterrupt):
            application._complete_recovery("change-a", intent.recovery_id, reference)
    else:
        application._complete_recovery("change-a", intent.recovery_id, reference)
    reopened, _, _ = _reopen_portfolio(tmp_path, state, runtimes)
    frontier, custody = runtimes["change-a"].frontier_bytes(), coordinator.show("change-a")
    assert (intent.recovery_id in custody.recovery_exclusions) == (crash != "evidence")
    readiness = reopened.get_change("change-a").readiness
    assert not readiness.executable
    if crash != "evidence":
        assert readiness.reason_code == "coordination-unavailable"
        assert readiness.prompt == (
            "/repair-delivery Diagnose Change change-a read-only; preserve existing custody and journals. "
            "This does not repair authority or prove host/worker closure. Do not stop a worker, retry, release "
            "custody, or dispatch a replacement. The responsible owner must establish any missing authority "
            "through a supported path before Delivery can resume; this diagnostic does not supply that authority."
        )
        item = reopened.show_work_item_view("change-a", "outcome:OUT-001")
        assert item.readiness.reason_code == "coordination-unavailable"
        assert item.readiness.prompt == readiness.prompt
    assert reopened.acquire_change_action(_continuation_request(reopened)).kind != "acquired"
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        reopened._coordinator.prepare_runtime_custody_guard("change-a")
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        reopened._complete_recovery("change-a", intent.recovery_id, reference)
    assert runtimes["change-a"].frontier_bytes() == frontier
    assert coordinator.show("change-a") == custody
    reopened._recovery_evidence_provider = host
    host.seal(intent, "closed")
    receipt = reopened._complete_recovery("change-a", intent.recovery_id, reference)
    assert receipt.evidence.status == "excluded"
    replacement = reopened.acquire_change_action(_continuation_request(reopened))
    if replacement.kind == "reconciled":
        replacement = reopened.acquire_change_action(_continuation_request(reopened))
    assert replacement.kind == "acquired"
    assert replacement.launch.claim.claim_id != launch.claim.claim_id
    assert reopened.acquire_change_action(_continuation_request(reopened)).kind == "busy"


def test_closed_engine_without_owner_effect_receipt_stays_contained(tmp_path):
    application, runtime, provider, _state, _head, _root = _awaiting_acceptance_fixture(tmp_path, mark_ready=False)
    _host(application)
    action = _engine_action(application)
    coordinator = application._coordinator
    with coordinator.continuation_execution(action):
        coordinator.start_continuation_action(action)
    failed = _execute_engine(application, action)
    assert failed.kind == "blocked"
    assert runtime.ready_receipt() is None
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application._propose_recovery("change-a")
    assert coordinator.show("change-a").continuation_action == action
    provider.set_pull_request_draft_state.assert_not_called()


@pytest.mark.parametrize(
    "override",
    [
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
    ],
)
def test_recovery_application_entry_rejects_inherited_git_overrides_before_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    override: str,
) -> None:
    application, _runtimes, coordinator, _state = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    manager = application._workspace_manager
    coordination = coordinator.show("change-a")
    alternate = tmp_path / "alternate-worktree"
    _git(
        manager.repository,
        "worktree",
        "add",
        "--detach",
        str(alternate),
        _git(manager.repository, "rev-parse", coordination.branch),
    )
    (coordination.worktree_path / "shared.txt").write_text("managed dirty\n", encoding="utf-8")
    monkeypatch.setenv(override, str(alternate))

    with pytest.raises(PreservationRejectedError, match="inherited Git repository/index overrides"):
        application._propose_recovery("change-a")


@pytest.mark.parametrize("orphan_child", [False, True])
def test_process_exclusion_then_verified_all_jobs_close_admits_one_replacement(tmp_path, orphan_child):
    application, runtimes, coordinator, state = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    host = ProcessEvidenceHost(orphan_child)
    application._recovery_evidence_provider = host
    launch = application.acquire_change_action(_continuation_request(application)).launch
    product = launch.worktree_path / "product.txt"
    worker = host.dispatch(launch.claim.claim_id)
    try:
        reopened, _, _ = _reopen_portfolio(tmp_path, state, runtimes, clock=lambda: "2030-01-01T00:00:00Z")
        reopened._recovery_evidence_provider = host
        intent = reopened._propose_recovery("change-a")
        reference = host.reference(intent)
        with pytest.raises(DeliveryWorkerExclusionRequiredError):
            reopened._complete_recovery("change-a", intent.recovery_id, reference)
        assert reopened.acquire_change_action(_continuation_request(reopened)).kind == "busy"
        worker.stdin.write("write\n")
        worker.stdin.flush()
        assert worker.stdout.readline().strip() == "write"
        assert product.read_text() == "late old write\n"
        assert _git(launch.worktree_path, "rev-parse", "refs/owlbear/test-worker") == intent.exact_head
        assert coordinator.show("change-a").writer == launch.writer
        assert reopened.acquire_change_action(_continuation_request(reopened)).kind == "busy"
        worker.stdin.write("restore\n")
        worker.stdin.flush()
        assert worker.stdout.readline().strip() == "restore"
        host.close(launch.claim.claim_id)
        receipt = reopened._complete_recovery("change-a", intent.recovery_id, reference)
    finally:
        host.close(launch.claim.claim_id)
    assert receipt.evidence.status == "closed"
    replacement = reopened.acquire_change_action(_continuation_request(reopened))
    if replacement.kind == "reconciled":
        replacement = reopened.acquire_change_action(_continuation_request(reopened))
    assert replacement.kind == "acquired"
    assert replacement.launch.claim.claim_id != launch.claim.claim_id
    existing_owner = application.acquire_change_action(_continuation_request(application))
    assert existing_owner.kind == "busy", existing_owner.model_dump_json()
    assert existing_owner.reason_code == "active-custody"
    assert existing_owner.readiness.reason_code == "active-custody"
    product.write_text("replacement-only\n")
    refs = _git(launch.worktree_path, "show-ref")
    with pytest.raises(RuntimeError, match="cannot be dispatched again"):
        host.dispatch(launch.claim.claim_id)
    assert worker.stdin.closed
    assert worker.stdout.closed
    assert product.read_text() == "replacement-only\n"
    assert _git(launch.worktree_path, "show-ref") == refs
    assert "refs/owlbear/test-worker" not in refs
    assert coordinator.show("change-a").writer == replacement.launch.writer


def test_absent_host_still_writing_descendant_stays_contained_across_restarts(tmp_path: Path) -> None:
    reopened, host, _worker, launch, restart, snapshot, signal = absent_host_process_case(tmp_path)

    def assert_contained(application) -> tuple[object, ...]:
        before = snapshot(application)
        view = application.get_change("change-a")
        assert not view.readiness.executable
        diagnosis = application.repair("change-a")
        assert diagnosis.proposal is not None
        with pytest.raises(DeliveryWorkerExclusionRequiredError):
            application.repair("change-a", diagnosis.proposal.proposal_id)
        with pytest.raises(DeliveryWorkerExclusionRequiredError):
            application.recover_claim(
                "change-a",
                "OUT-001",
                launch.claim.attempt_id,
                launch.claim.claim_id,
                confirmed_lost=True,
            )
        acquisition = application.acquire_change_action(_continuation_request(application))
        assert acquisition.kind == "unsupported"
        assert acquisition.reason_code == "repair-required"
        assert acquisition.readiness.reason_code == "active-custody"
        assert application._coordinator.show("change-a").writer.claim_id == launch.claim.claim_id
        assert launch.claim.claim_id not in host.closed
        assert snapshot(application) == before
        return before

    try:
        first_snapshot = assert_contained(reopened)
        signal("write-next", b"late old write after restart\n")
        after_signaled_write = snapshot(reopened)
        assert after_signaled_write[:3] == first_snapshot[:3]
        assert after_signaled_write[3] != first_snapshot[3]
        assert after_signaled_write[4:] == first_snapshot[4:]
        restarted = restart()
        assert snapshot(restarted) == after_signaled_write
        assert_contained(restarted)
    finally:
        host.close(launch.claim.claim_id)


def _assert_refused_handoff_frontier(
    before: bytes,
    after: bytes,
    launch: DeliveryLaunchPackage,
    request: BlockDelivery | ReturnDelivery | RetryDelivery,
) -> None:
    if isinstance(request, RetryDelivery):
        before_frontier = json.loads(before)
        after_frontier = json.loads(after)
        before_binding = next(item for item in before_frontier["bindings"] if item["outcome_id"] == launch.outcome_id)
        after_binding = next(item for item in after_frontier["bindings"] if item["outcome_id"] == launch.outcome_id)
        assert after_binding["retry_diagnostic"] == {
            "code": "ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED",
            "attempt_id": launch.claim.attempt_id,
            "transition": request.model_dump(mode="json"),
        }
        assert "retry_diagnostic" not in before_binding
        after_binding.pop("retry_diagnostic")
        assert after_frontier == before_frontier
        return
    before_frontier = json.loads(before)
    after_frontier = json.loads(after)
    before_binding = next(item for item in before_frontier["bindings"] if item["outcome_id"] == launch.outcome_id)
    after_binding = next(item for item in after_frontier["bindings"] if item["outcome_id"] == launch.outcome_id)
    assert before_binding["recovery_attention"] is None
    assert after_binding["recovery_attention"] == {
        "attempt_id": launch.claim.attempt_id,
        "claim_id": launch.claim.claim_id,
        "reason": request.reason,
        "worktree_path": str(launch.worktree_path),
        "branch_head": launch.last_reviewed_commit,
        "worktree_head": launch.last_reviewed_commit,
        "last_reviewed_commit": launch.last_reviewed_commit,
        "writer_claim_id": launch.claim.claim_id,
        "custody_retained": True,
        "retry_condition": (
            "Diagnostic only: the current Builder retains custody. Host worker-exclusion evidence is missing; "
            "no transition or restart is authorized. Resume requires verified exclusion through a supported "
            "host recovery path, whose availability is not established by this diagnostic."
        ),
        "diagnostic_transition": request.model_dump(mode="json"),
    }
    after_binding["recovery_attention"] = None
    assert after_frontier == before_frontier


@pytest.mark.parametrize("transition_kind", ["block", "return", "retry"])
def test_active_builder_handoff_requires_worker_exclusion(tmp_path: Path, transition_kind: str) -> None:
    application, host, _worker, launch, _restart, snapshot, signal = absent_host_process_case(tmp_path)
    signal("restore", b"baseline\n")
    before = snapshot(application)
    if transition_kind == "block":
        request = BlockDelivery(
            action="block",
            outcome_id=launch.outcome_id,
            claim_id=launch.claim.claim_id,
            block_id="blocked-check",
            reason="A prerequisite needs a decision.",
            unblock_condition="The user answers the request.",
            expected_evidence=("answer",),
            locators=("TASK-001",),
            request=DeliveryRequest(
                request_id="request-1",
                kind=DeliveryRequestKind.DECISION,
                outcome_id=launch.outcome_id,
                summary="Choose the supported prerequisite.",
                options=(DeliveryRequestOption(option_id="continue", label="Continue"),),
            ),
            resume_commit=launch.last_reviewed_commit,
        )
    elif transition_kind == "return":
        request = ReturnDelivery(
            action="return",
            outcome_id=launch.outcome_id,
            claim_id=launch.claim.claim_id,
            target=DeliveryStage.PLANNING,
            reason="The implementation premise needs revision.",
            locators=("TASK-001",),
            preserved_commit=launch.last_reviewed_commit,
            attempt_id=launch.claim.attempt_id,
        )
    else:
        request = RetryDelivery(
            action="retry",
            outcome_id=launch.outcome_id,
            claim_id=launch.claim.claim_id,
            abandoned_commit=launch.last_reviewed_commit,
            attempt_id=launch.claim.attempt_id,
        )

    try:
        with pytest.raises(DeliveryWorkerExclusionRequiredError):
            application.transition_delivery("change-a", request)

        after_refusal = snapshot(application)
        _assert_refused_handoff_frontier(before[0], after_refusal[0], launch, request)
        assert after_refusal[1:] == before[1:]
        assert application._coordinator.show("change-a").writer.claim_id == launch.claim.claim_id
        signal("write", b"late old write\n")
        after_write = snapshot(application)
        assert after_write[:3] == after_refusal[:3]
        assert after_write[3] != before[3]
        assert after_write[4] == before[4]
        assert after_write[5] != before[5]
        assert after_write[6:] == before[6:]
    finally:
        host.close(launch.claim.claim_id)


@pytest.mark.parametrize("fault_record", ["intent", "evidence", "receipt"])
@pytest.mark.parametrize("step", ["before-publication", "after-first-publication", "before-manifest-cleanup"])
def test_recovery_crash_at_authority_step_retains_or_completes_exactly(tmp_path, fault_record, step):
    application, runtimes, coordinator, state = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    host = _host(application)
    launch = application.acquire_change_action(_continuation_request(application)).launch
    commit = RuntimeTransaction.commit

    def fail(transaction, **kwargs):
        def crash(point):
            if point == step:
                raise KeyboardInterrupt

        if any(
            part.relative_path.name == f"{fault_record}.json" and "recovery-receipts" in part.relative_path.parts
            for part in transaction._participants
        ):
            kwargs["failure"] = crash
        return commit(transaction, **kwargs)

    if fault_record == "intent":
        with patch.object(RuntimeTransaction, "commit", fail), pytest.raises(KeyboardInterrupt):
            application._propose_recovery("change-a")
        intent = application._propose_recovery("change-a")
        reference = host.seal(intent)
    else:
        intent = application._propose_recovery("change-a")
        reference = host.seal(intent)
        with patch.object(RuntimeTransaction, "commit", fail), pytest.raises(KeyboardInterrupt):
            application._complete_recovery("change-a", intent.recovery_id, reference)
    reopened, _, _ = _reopen_portfolio(tmp_path, state, runtimes)
    reopened._recovery_evidence_provider = host
    if fault_record != "receipt":
        assert runtimes["change-a"].active_claims() == (("OUT-001", launch.claim),)
        assert coordinator.show("change-a").writer == launch.writer
    receipt = reopened._complete_recovery("change-a", intent.recovery_id, reference)
    assert reopened._complete_recovery("change-a", intent.recovery_id, reference) == receipt
    assert runtimes["change-a"].active_claims() == ()
    assert coordinator.show("change-a").writer is None


def test_concurrent_verified_recovery_wait_does_not_hold_portfolio_lock(tmp_path):
    application, runtimes, coordinator, state = _portfolio(
        tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION, "change-b": DeliveryStage.PLANNING}
    )
    host = _host(application)
    application.acquire_change_action(_continuation_request(application))
    intent = application._propose_recovery("change-a")
    reference = host.seal(intent)
    reopened, _, _ = _reopen_portfolio(tmp_path, state, runtimes)
    reopened._recovery_evidence_provider = host
    entered, proceed = Barrier(3), Barrier(3)
    verify = host.verify

    def wait(ref, proposed):
        entered.wait(timeout=10)
        proceed.wait(timeout=10)
        return verify(ref, proposed)

    host.verify = wait
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [
            pool.submit(instance._complete_recovery, "change-a", intent.recovery_id, reference)
            for instance in (application, reopened)
        ]
        entered.wait(timeout=10)
        try:
            assert application.acquire_change_action(_continuation_request(application, "change-b")).kind == "acquired"
        finally:
            proceed.wait(timeout=10)
        receipts = [result.result(timeout=10) for result in results]
    assert receipts[0] == receipts[1]
    assert coordinator.show("change-a").writer is None


@pytest.mark.parametrize(
    "drift",
    ["host-generation", "invocation", "claim", "partial-scope", "head", "target", "frontier", "dirty", "unknown"],
)
def test_wrong_evidence_or_changed_fences_never_release(tmp_path, drift):
    application, _runtimes, coordinator, state = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    host = _host(application)
    launch = application.acquire_change_action(_continuation_request(application)).launch
    intent = application._propose_recovery("change-a")
    reference = host.seal(intent)
    if drift in {"host-generation", "invocation", "claim"}:
        updates = {"host_generation": "other"} if drift == "host-generation" else {"invocation_id": "other"}
        if drift == "claim":
            updates = {"request": intent.invocation.request.model_copy(update={"owner_id": "other"})}
        host.evidence[reference.reference] = host.evidence[reference.reference].model_copy(
            update={"invocation": intent.invocation.model_copy(update=updates)}
        )
    elif drift == "partial-scope":
        host.evidence[reference.reference] = host.evidence[reference.reference].model_copy(
            update={"scope": "parent-pid-only"}
        )
    elif drift == "head":
        _git(launch.worktree_path, "commit", "--allow-empty", "-m", "new unpromoted head")
    elif drift == "target":
        repository = application._workspace_manager.repository
        _git(repository, "commit", "--allow-empty", "-m", "new target")
        _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    elif drift == "frontier":
        path = state / "changes/change-a/frontier.json"
        path.write_bytes(b"{")
    elif drift == "dirty":
        (launch.worktree_path / "product.txt").write_text("unknown private edits\n")
    else:
        reference = RecoveryEvidenceReference(reference="forged-unknown")
    before = (state / "changes/change-a/frontier.json").read_bytes()
    custody = coordinator.show("change-a")
    with pytest.raises((DeliveryWorkerExclusionRequiredError, RuntimeError, ValueError)):
        application._complete_recovery("change-a", intent.recovery_id, reference)
    assert (state / "changes/change-a/frontier.json").read_bytes() == before
    assert coordinator.show("change-a") == custody


def recovery_case(tmp_path: Path, kind: str):
    """Prepare real custody without launching a service or configuring a provider."""
    now = ["2026-08-04T00:00:00Z"]
    if kind == "integration":
        application, runtimes, coordinator, _state, _head, claim = _prepare_legacy_integration_repair(tmp_path)
        operation = "recover_integration_repair_claim"
        request = {"change_id": "change-a", "attempt_id": claim.attempt_id, "claim_id": claim.claim_id}
    else:
        stage = DeliveryStage.PLANNING if kind == "planner" else DeliveryStage.IMPLEMENTATION
        application, runtimes, coordinator, _state = _portfolio(tmp_path, {"change-a": stage}, clock=lambda: now[0])
        launch = application.acquire_frontier_work().launch_packages[0]
        operation = "recover_claim"
        request = {
            "change_id": launch.change_id,
            "outcome_id": launch.outcome_id,
            "attempt_id": launch.claim.attempt_id,
            "claim_id": launch.claim.claim_id,
            "confirmed_lost": True,
        }
        if kind == "proposal":
            now[0] = "2026-08-04T01:00:00Z"
            proposal = application.repair("change-a").proposal
            assert proposal is not None
            operation = "repair"
            request = {"change_id": "change-a", "proposal_id": proposal.proposal_id, "confirmed_lost": True}
    coordination = coordinator.show("change-a")
    worktree = coordination.worktree_path
    product = worktree / "product.txt"
    product.write_bytes(b"staged bytes\n")
    _git(worktree, "add", "product.txt")
    product.write_bytes(b"different worktree bytes\n")
    (worktree / "private-untracked.bin").write_bytes(b"preserve\x00\xff")
    index = Path(_git(worktree, "rev-parse", "--path-format=absolute", "--git-path", "index"))
    index_bytes = index.read_bytes()
    frontier = runtimes["change-a"].frontier_bytes()
    content = _file_bytes(worktree)
    refs = _git(worktree, "show-ref")

    def unchanged():
        assert runtimes["change-a"].frontier_bytes() == frontier
        assert coordinator.show("change-a") == coordination
        assert index.read_bytes() == index_bytes
        assert _file_bytes(worktree) == content
        assert _git(worktree, "show-ref") == refs

    return application, operation, request, unchanged


@pytest.mark.parametrize("kind", ["planner", "builder", "integration", "proposal"])
def test_public_recovery_exclusion_required(tmp_path: Path, kind: str) -> None:
    application, operation, request, unchanged = recovery_case(tmp_path, kind)
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        getattr(application, operation)(**request)
    unchanged()


def test_recovery_caller_cannot_supply_forged_evidence(tmp_path: Path) -> None:
    application, operation, request, unchanged = recovery_case(tmp_path, "builder")
    with pytest.raises(TypeError, match="evidence"):
        getattr(application, operation)(**request, evidence={"closed": True})
    unchanged()
