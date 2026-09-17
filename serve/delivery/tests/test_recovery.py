"""Shared real-core recovery fixtures and fail-closed authority checks."""

# ruff: noqa: SLF001 - tests exercise the deliberately unregistered internal owner path.

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

import pytest
from serve.delivery.tests.test_portfolio_application import (
    _attach_local_target,
    _awaiting_acceptance_fixture,
    _continuation_request,
    _engine_action,
    _execute_engine,
    _failure_request,
    _file_bytes,
    _finalization_request,
    _git,
    _portfolio,
    _prepare_legacy_integration_repair,
    _reopen_portfolio,
    _task_result,
)

from owlbear_delivery import DeliveryResultSubmission, DeliveryStage
from owlbear_delivery.delivery_state import DeliveryStatePublisher
from owlbear_delivery.recovery import (
    DeliveryWorkerExclusionRequiredError,
    RecoveryEvidence,
    RecoveryEvidenceReference,
    RecoveryInvocation,
    journal_path,
)
from owlbear_delivery.runtime_transaction import RuntimeTransaction, TransactionConflictError


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
            "import pathlib,sys\n"
            "product=pathlib.Path(sys.argv[1])\n"
            "product.write_text('baseline\\n')\n"
            "print('writing',flush=True)\n"
            "command=sys.stdin.readline().strip()\n"
            "if command != 'close': product.write_text('late old write\\n')\n"
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


def test_verified_clean_finalizer_recovery_keeps_failed_history(tmp_path):
    application, runtimes, coordinator, state = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    host = _host(application)
    attempt = application.acquire_change_action(_continuation_request(application)).finalization.attempt
    report = application.report_finalization_failure(
        _failure_request(application, attempt_key=attempt.writer.attempt_id)
    )
    intent = application._propose_recovery("change-a")
    assert intent.failure_id == report.report_id
    receipt = application._complete_recovery("change-a", intent.recovery_id, host.seal(intent))
    assert runtimes["change-a"].finalization() is None
    assert coordinator.show("change-a").writer is None
    assert coordinator.show("change-a").finalization_attempt.finished_at == receipt.finished_at
    assert (state / journal_path("change-a", intent.recovery_id, "intent")).exists()
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


@pytest.mark.parametrize("interrupted", [False, True])
def test_verified_interrupted_ready_owner_readback_never_redispatches(tmp_path, interrupted):
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
    reference = host.seal(intent)
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
    assert application.acquire_change_action(_continuation_request(application)).kind == "busy"
    product.write_text("replacement-only\n")
    with pytest.raises(RuntimeError, match="cannot be dispatched again"):
        host.dispatch(launch.claim.claim_id)
    assert worker.stdin.closed
    assert worker.stdout.closed
    assert product.read_text() == "replacement-only\n"
    assert coordinator.show("change-a").writer == replacement.launch.writer


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
