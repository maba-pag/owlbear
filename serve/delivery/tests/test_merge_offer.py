# ruff: noqa: SLF001
"""N05-B1: merge offer, distinct waits, strict-proof target route, Check again and cleanup."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from serve.delivery.tests.test_portfolio_application import (
    _awaiting_acceptance_fixture,
    _continuation_request,
    _git,
    _reopen_portfolio,
)

from owlbear_delivery import ChangeBranchPublisher
from owlbear_delivery.delivery_runtime import DeliveryAcceptanceWaitingError
from owlbear_delivery.draft_pull_request import DraftPullRequestPublisher
from owlbear_delivery.merge_offer import (
    MergeBlockReason,
    MergeFacts,
    MergeOfferAuthority,
    decide_merge,
)
from owlbear_delivery.publication_provider import (
    PublicationCheck,
    PublicationCheckKind,
    PublicationCheckSnapshot,
    PublicationMergeEvidence,
    PublicationMergeMethod,
    PublicationMergeSettings,
    PublicationMergeStack,
    PublicationProviderError,
    PublicationProviderFailureCode,
    PublicationPullRequest,
    PublicationRepository,
)
from owlbear_delivery.recovery import RetryLedger
from owlbear_delivery.work_items import WorkItemActionKind, WorkItemNextActor
from owlbear_delivery_github.memory import InMemoryPublicationProvider

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery.portfolio_application import PortfolioApplication

_REPOSITORY = "example/project"
_HEAD = "a" * 40
_TARGET = "b" * 40
_DIGEST = "c" * 64


def _check(name: str = "unit", *, conclusion: str | None = "success", required: bool = True, **updates: object):
    return PublicationCheck(
        check_id=str(updates.pop("check_id", f"{name}-1")),
        kind=PublicationCheckKind.CHECK_RUN,
        name=name,
        head_sha=_HEAD,
        status=str(updates.pop("status", "completed" if conclusion is not None else "in_progress")),
        conclusion=conclusion,
        required=required,
        **updates,
    )


def _facts(*checks: PublicationCheck, evidence: dict[str, object] | None = None, **settings: object) -> MergeFacts:
    return MergeFacts(
        capable=True,
        evidence=PublicationMergeEvidence(
            repository=_REPOSITORY,
            number=7,
            node_id="PR_node_7",
            state="open",
            draft=False,
            merged=False,
            head_sha=_HEAD,
            base_branch="main",
        ).model_copy(update=evidence or {}),
        settings=PublicationMergeSettings(
            repository=_REPOSITORY,
            branch="main",
            allowed_methods=tuple(PublicationMergeMethod),
            viewer_can_push=True,
            rule_types=(),
            queue_required=False,
            strict_up_to_date_required=False,
            execution_scope_enforced=False,
        ).model_copy(update=settings),
        checks=PublicationCheckSnapshot(repository=_REPOSITORY, number=7, head_sha=_HEAD, checks=checks or (_check(),)),
        target_head=_TARGET,
    )


def _pull_request(state: str = "CLEAN", *, mergeable: bool | None = True, title: str = "Change A"):
    return PublicationPullRequest(
        repository=_REPOSITORY,
        number=7,
        node_id="PR_node_7",
        head_branch="owlbear/change/change-a",
        head_sha=_HEAD,
        base_branch="main",
        title=title,
        body="body",
        draft=False,
        state="open",
        merged=False,
        mergeable=mergeable,
        merge_state_status=state,
    )


_AUTHORITY = MergeOfferAuthority(
    repository=_REPOSITORY,
    number=7,
    node_id="PR_node_7",
    target_branch="main",
    exact_head=_HEAD,
    finalization_id=_DIGEST,
    ready_receipt_id="d" * 64,
    observation_count=2,
    review_id="e" * 64,
    proof_target=_TARGET,
)


@pytest.mark.parametrize(
    ("pull_request", "facts", "reason", "block"),
    [
        (_pull_request("dirty", mergeable=False), _facts(), "merge-blocked", MergeBlockReason.CONFLICTS),
        (_pull_request("CONFLICTING", mergeable=None), _facts(), "merge-blocked", MergeBlockReason.CONFLICTS),
        (_pull_request("BEHIND"), _facts(), "merge-blocked", MergeBlockReason.BEHIND),
        (_pull_request("UNKNOWN", mergeable=None), _facts(), "merge-checking", None),
        (_pull_request("BLOCKED"), _facts(), "merge-blocked", MergeBlockReason.PROTECTION),
        (_pull_request(), _facts(evidence={"draft": True}), "merge-blocked", MergeBlockReason.DRAFT),
        (_pull_request(), _facts(evidence={"state": "closed"}), "merge-blocked", MergeBlockReason.CLOSED),
        (
            _pull_request(),
            _facts(evidence={"stack": PublicationMergeStack(size=2, position=1, base_branch="main", base_sha=_TARGET)}),
            "merge-blocked",
            MergeBlockReason.STACKED,
        ),
        (_pull_request(), _facts(evidence={"base_branch": "release"}), "merge-blocked", MergeBlockReason.WRONG_BASE),
        (
            _pull_request(),
            _facts(allowed_methods=(PublicationMergeMethod.SQUASH,)),
            "merge-blocked",
            MergeBlockReason.METHOD_NOT_ALLOWED,
        ),
        (_pull_request(), _facts(queue_required=True), "merge-blocked", MergeBlockReason.QUEUE_REQUIRED),
        (_pull_request(), _facts(_check(conclusion="failure")), "merge-blocked", MergeBlockReason.CHECKS_FAILED),
        (_pull_request("BLOCKED"), _facts(_check(conclusion=None)), "checks-running", None),
        (_pull_request(), MergeFacts(capable=False), "merge-blocked", MergeBlockReason.CAPABILITY_UNAVAILABLE),
        (_pull_request(), None, "provider-unavailable", None),
        (_pull_request(), _facts(), "target-sync-required", None),
    ],
)
def test_known_unmergeable_pull_request_never_yields_an_offer(pull_request, facts, reason, block) -> None:
    authority = _AUTHORITY.model_copy(update={"proof_target": None}) if reason == "target-sync-required" else _AUTHORITY
    decision = decide_merge(authority, pull_request, facts)

    assert decision is not None
    assert (decision.reason, decision.block.reason if decision.block else None) == (reason, block)
    assert decision.offer is None


def test_offer_binds_provider_facts_and_required_check_conclusions_only() -> None:
    facts = _facts(_check("unit"), _check("lint", required=False, conclusion="failure"))
    offer = decide_merge(_AUTHORITY, _pull_request("unstable"), facts).offer

    assert offer is not None
    assert (offer.repository, offer.number, offer.node_id, offer.head_sha, offer.base_branch) == (
        _REPOSITORY,
        7,
        "PR_node_7",
        _HEAD,
        "main",
    )
    assert (offer.target_head, offer.finalization_id, offer.merge_method) == (_TARGET, _DIGEST, "merge")
    assert (offer.proof.proof_target, offer.proof.observation_count, offer.stack_size) == (_TARGET, 2, 1)
    assert offer.check_summary.model_dump() == {
        "required_passed": 1,
        "required_pending": 0,
        "required_failed": 0,
        "optional_failed": 1,
    }
    rerun = _facts(
        _check("unit", check_id="unit-2", completed_at=datetime(2026, 10, 4, tzinfo=UTC)),
        _check("lint", required=False, conclusion="success"),
    )
    assert decide_merge(_AUTHORITY, _pull_request("CLEAN", title="Renamed"), rerun).offer.offer_id == offer.offer_id
    neutral = _facts(_check("unit", conclusion="neutral"))
    assert decide_merge(_AUTHORITY, _pull_request(), neutral).offer.offer_id != offer.offer_id


def test_moved_target_stays_offerable_and_reports_both_targets() -> None:
    """U3 (b), amended 2026-10-07: the offer binds the current target and keeps the proof target visible."""
    moved = "f" * 40
    offer = decide_merge(_AUTHORITY, _pull_request(), _facts().model_copy(update={"target_head": moved})).offer

    assert offer is not None
    assert (offer.target_head, offer.proof.proof_target) == (moved, _TARGET)
    assert offer.offer_id != decide_merge(_AUTHORITY, _pull_request(), _facts()).offer.offer_id
    behind = decide_merge(_AUTHORITY, _pull_request("BEHIND"), _facts().model_copy(update={"target_head": moved}))
    assert (behind.reason, behind.block.reason, behind.offer) == ("merge-blocked", MergeBlockReason.BEHIND, None)


def _memory_awaiting_merge(
    tmp_path: Path, *, merge_state: str = "CLEAN", mark_ready: bool = True
) -> tuple[PortfolioApplication, object, InMemoryPublicationProvider, str, Path]:
    """Awaiting merge with a D1 provider whose target branch equals the proof target."""
    application, runtime, _mock, state, head, state_root = _awaiting_acceptance_fixture(
        tmp_path, sync_target=True, mark_ready=mark_ready
    )
    memory = InMemoryPublicationProvider()
    memory.add_repository(PublicationRepository(repository=_REPOSITORY, default_branch="main"))
    memory.pull_requests[(_REPOSITORY, 7)] = state["pull_request"].model_copy(
        update={"mergeable": True, "merge_state_status": merge_state}
    )
    memory.add_check_snapshot(
        PublicationCheckSnapshot(
            repository=_REPOSITORY,
            number=7,
            head_sha=head,
            checks=(_check().model_copy(update={"head_sha": head}),),
        )
    )
    memory.set_branch_head(_REPOSITORY, "main", runtime.target_sync_receipt().target_head)
    application._draft_pull_request_publisher = DraftPullRequestPublisher(
        memory, repository=_REPOSITORY, target_branch="main", state_root=tmp_path / "pull-requests"
    )
    application._publication_observation_cache.clear()
    return application, runtime, memory, head, state_root


def _acquire(application: PortfolioApplication):
    result = application.acquire_change_action(_continuation_request(application))
    if result.kind == "reconciled":
        result = application.acquire_change_action(_continuation_request(application))
    return result


def test_awaiting_merge_offers_approval_and_the_chat_shows_the_readiness_reason(tmp_path: Path) -> None:
    application, runtime, memory, head, _state_root = _memory_awaiting_merge(tmp_path)

    view = application.get_change("change-a")
    readiness = view.readiness

    assert (readiness.status, readiness.reason_code, readiness.next_actor) == (
        "waiting",
        "merge-approval-required",
        WorkItemNextActor.YOU,
    )
    offer = readiness.merge_offer
    assert (offer.head_sha, offer.target_head, offer.ready_receipt_id) == (
        head,
        memory.branch_heads[(_REPOSITORY, "main")],
        runtime.ready_receipt().receipt_id,
    )
    card = view.detail.card
    assert card.item_key == "publication"
    assert "merge" in card.next_step.lower()
    assert "GitHub" in card.next_step
    assert card.action.kind is WorkItemActionKind.OBSERVE_ACCEPTANCE
    result = _acquire(application)
    assert (result.kind, result.reason_code, result.engine_action) == ("waiting", "merge-approval-required", None)

    memory.pull_requests[(_REPOSITORY, 7)] = memory.pull_requests[(_REPOSITORY, 7)].model_copy(
        update={"merge_state_status": "DIRTY", "mergeable": False}
    )
    application._publication_observation_cache.clear()
    application._merge_facts_cache.clear()
    blocked = _acquire(application)
    assert (blocked.reason_code, blocked.readiness.merge_block.reason) == ("merge-blocked", MergeBlockReason.CONFLICTS)


def _expire_caches(application: PortfolioApplication) -> None:
    for cache in (application._publication_observation_cache, application._merge_facts_cache):
        for change_id, (_expiry, key, value) in tuple(cache.items()):
            cache[change_id] = (0.0, key, value)


@pytest.mark.parametrize("ready", [True, False], ids=["awaiting-merge", "draft"])
def test_expired_observation_is_reread_and_a_provider_outage_is_a_distinct_wait(tmp_path: Path, *, ready: bool) -> None:
    application, _runtime, _memory, _head, _state_root = _memory_awaiting_merge(tmp_path, mark_ready=ready)
    offered = "merge-approval-required" if ready else "ready"
    assert application.get_change("change-a").readiness.reason_code == offered
    _expire_caches(application)
    original = InMemoryPublicationProvider.read_pull_request
    with patch.object(InMemoryPublicationProvider, "read_pull_request", autospec=True, side_effect=original) as reads:
        assert application.get_change("change-a").readiness.reason_code == offered
    assert reads.call_count >= 1
    _expire_caches(application)
    outage = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE, "read_pull_request", "down", retry_safe=True
    )
    with patch.object(InMemoryPublicationProvider, "read_pull_request", side_effect=outage):
        readiness = application.get_change("change-a").readiness
        acquired = _acquire(application)

    assert (readiness.status, readiness.reason_code, readiness.executable, readiness.merge_offer) == (
        "waiting",
        "provider-unavailable",
        False,
        None,
    )
    assert readiness.progress == "waiting-for-service"
    assert (acquired.kind, acquired.reason_code, acquired.engine_action) == ("waiting", "provider-unavailable", None)
    _expire_caches(application)
    recovered = application.get_change("change-a").readiness
    assert (recovered.reason_code, recovered.executable) == (offered, not ready)
    if not ready:
        assert recovered.operation is WorkItemActionKind.MARK_READY


def test_provider_without_merge_protocol_is_capability_unavailable(tmp_path: Path) -> None:
    application, *_rest = _awaiting_acceptance_fixture(tmp_path, sync_target=True)

    view = application.get_change("change-a")

    assert view.readiness.reason_code == "merge-blocked"
    assert view.readiness.merge_block.reason is MergeBlockReason.CAPABILITY_UNAVAILABLE
    card = view.detail.card
    assert card.next_step.endswith("merge the pull request in GitHub.")


@pytest.mark.parametrize("head_changes", [True, False])
def test_newer_provider_target_keeps_the_finalized_offer_with_its_proof_target(
    tmp_path: Path, *, head_changes: bool
) -> None:
    application, runtime, memory, head, _state_root = _memory_awaiting_merge(tmp_path)
    repository = application._workspace_manager.repository
    application._change_branch_publisher = ChangeBranchPublisher(
        repository,
        application._coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "branch-operations",
    )
    proof_target = runtime.target_sync_receipt().target_head
    _git(repository, "push", "origin", f"{head}:refs/heads/owlbear/change/change-a")
    target = (
        _git(repository, "commit-tree", f"{proof_target}^{{tree}}", "-p", proof_target, "-m", "target advance")
        if head_changes
        else head
    )
    _git(repository, "push", "origin", f"{target}:refs/heads/main")
    _git(repository, "update-ref", "refs/remotes/origin/main", proof_target)
    memory.set_branch_head(_REPOSITORY, "main", target)
    application._merge_facts_cache.clear()

    view = application.get_change("change-a")
    readiness = view.readiness
    assert (readiness.reason_code, readiness.next_actor, readiness.executable) == (
        "merge-approval-required",
        WorkItemNextActor.YOU,
        False,
    )
    assert (readiness.merge_offer.target_head, readiness.merge_offer.proof.proof_target) == (target, proof_target)
    assert view.detail.card.next_step.startswith(f"Proven against main at {proof_target[:12]}; main is now at")
    acquired = _acquire(application)
    assert (acquired.kind, acquired.reason_code, acquired.engine_action) == ("waiting", "merge-approval-required", None)
    assert (runtime.finalization() is not None, runtime.ready_receipt() is not None) == (True, True)


def _with_clock(application: PortfolioApplication, now: list[datetime]) -> None:
    def clock() -> str:
        return now[0].isoformat()

    application._clock = clock


def _counted_reads():
    original = InMemoryPublicationProvider.read_pull_request
    return patch.object(InMemoryPublicationProvider, "read_pull_request", autospec=True, side_effect=original)


def _reopen_with_providers(tmp_path: Path, application, runtime, state_root, now: list[datetime]):
    reopened, _coordinator, _manager = _reopen_portfolio(tmp_path, state_root, {"change-a": runtime})
    reopened._draft_pull_request_publisher = application._draft_pull_request_publisher
    reopened._change_branch_publisher = application._change_branch_publisher
    _with_clock(reopened, now)
    return reopened


def test_check_again_reads_once_per_invocation_and_completion_cleans_the_worktree(tmp_path: Path) -> None:
    application, runtime, memory, head, state_root = _memory_awaiting_merge(tmp_path)
    now = [datetime(2026, 8, 4, tzinfo=UTC)]
    _with_clock(application, now)
    for seconds in (0, 1, 3):
        now[0] = datetime(2026, 8, 4, tzinfo=UTC) + timedelta(seconds=seconds)
        assert application.reconcile_awaiting_acceptance(("change-a",))[0].status.value == "waiting"
    now[0] += timedelta(days=1)
    for _ in range(2):
        with _counted_reads() as reads, pytest.raises(DeliveryAcceptanceWaitingError):
            application.observe_acceptance("change-a")
        assert reads.call_count == 1
    reopened = _reopen_with_providers(tmp_path, application, runtime, state_root, now)
    memory.merge_manually(_REPOSITORY, 7)
    with _counted_reads() as reads:
        assert reopened.reconcile_awaiting_acceptance(("change-a",))[0].status.value == "waiting"
    assert reads.call_count == 0
    with _counted_reads() as reads:
        receipt = reopened.observe_acceptance("change-a")
    assert reads.call_count == 1
    assert (receipt.finalized_change_head, reopened.observe_acceptance("change-a")) == (head, receipt)
    episode = RetryLedger(state_root, "change-a").read().episodes[0]
    assert (episode.explicit_observations, episode.reset_count) == (0, 1)
    assert reopened._coordinator.show("change-a").worktree_cleanup is not None
    assert all(item.change_id != "change-a" for item in reopened.list_retained_change_worktrees())


def test_unexpected_worktree_content_is_preserved_and_the_sweep_retries_once_per_process(tmp_path: Path) -> None:
    application, runtime, memory, _head, state_root = _memory_awaiting_merge(tmp_path)
    application._change_branch_publisher = ChangeBranchPublisher(
        application._workspace_manager.repository,
        application._coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "branch-operations",
    )
    worktree = application._coordinator.show("change-a").worktree_path
    stray = worktree / "unexpected.txt"
    stray.write_text("keep me\n", encoding="utf-8")
    memory.merge_manually(_REPOSITORY, 7)

    receipt = application.observe_acceptance("change-a")

    assert runtime.completion_receipt() == receipt
    retained = next(item for item in application.list_retained_change_worktrees() if item.change_id == "change-a")
    assert retained.cleanup_blocked_reason is not None
    application.reconcile_pending_checkpoints()
    assert stray.read_text(encoding="utf-8") == "keep me\n"
    stray.unlink()
    application.reconcile_pending_checkpoints()
    assert worktree.exists()
    now = [datetime(2026, 8, 4, tzinfo=UTC)]
    reopened = _reopen_with_providers(tmp_path, application, runtime, state_root, now)
    reopened.reconcile_pending_checkpoints()
    assert not worktree.exists()
    assert runtime.completion_receipt() == receipt
