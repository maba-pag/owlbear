# ruff: noqa: SLF001
"""N05-B2: one approval sends one request; readback-only settlement, owner fence and crash replay."""

from __future__ import annotations

import contextlib
import hashlib
import json
import threading
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from mcp import Client
from serve.delivery.tests.test_merge_offer import (
    _REPOSITORY,
    _acquire,
    _check,
    _counted_reads,
    _memory_awaiting_merge,
    _reopen_with_providers,
    _with_clock,
)

from owlbear_delivery import ChangeBranchPublisher
from owlbear_delivery.application_merge import (
    ERR_MERGE_IN_PROGRESS,
    ERR_MERGE_OFFER_STALE,
    ERR_MERGE_UNAVAILABLE,
    DeliveryMergeError,
)
from owlbear_delivery.application_models import (
    DeliveryActionBusyError,
    DeliveryChangeIntent,
    DeliveryChangeIntentKind,
    PortfolioApplicationError,
)
from owlbear_delivery.delivery_runtime import DeliveryAcceptanceWaitingError
from owlbear_delivery.merge_approval import (
    ApproveChangeMerge,
    MergeAttemptRecord,
    MergeAttemptState,
    MergeAttemptStore,
    MergeRace,
    settle_merge_attempt,
)
from owlbear_delivery.portfolio_application import PortfolioApplication
from owlbear_delivery.publication_provider import (
    PendingMergeRequest,
    PublicationCheckSnapshot,
    PublicationMergeEvidence,
    PublicationMergeMethod,
    PublicationMergeRefusal,
    PublicationMergeRefusalReason,
    PublicationMergeRequestResult,
    PublicationMergeRequestStatus,
    PublicationMergeStack,
    PublicationProviderError,
    PublicationProviderFailureCode,
)
from owlbear_delivery.work_items import WorkItemNextActor
from owlbear_delivery_github.memory import InMemoryPublicationProvider
from owlbear_delivery_mcp.target_server import assemble_target_server

if TYPE_CHECKING:
    from pathlib import Path

_HEAD = "a" * 40
_TARGET = "b" * 40
_OTHER = "9" * 40
_DIGEST = "c" * 64


class _Crash(BaseException):
    """A process death at one boundary: nothing after it runs."""


def _offer_id(application: PortfolioApplication) -> str:
    readiness = application.get_change("change-a").readiness
    assert readiness.reason_code == "merge-approval-required", readiness.reason_code
    return readiness.merge_offer.offer_id


def _approve(application: PortfolioApplication, offer_id: str | None = None, submission: str = "dialog-1"):
    return application.approve_merge(
        ApproveChangeMerge(
            change_id="change-a",
            offer_id=offer_id or _offer_id(application),
            submission_id=submission,
            host_id="host-1",
            session_id="cockpit",
        )
    )


def _attempt(state_root: Path) -> MergeAttemptRecord:
    (attempt,) = MergeAttemptStore(state_root, "change-a").attempts()
    return attempt


def _completions(state_root: Path) -> list[Path]:
    return [path for path in (state_root / "completions/change-a").glob("*.json") if path.name != "display.json"]


def _update_pull_request(memory: InMemoryPublicationProvider, **update: object) -> None:
    key = (_REPOSITORY, 7)
    memory.pull_requests[key] = memory.pull_requests[key].model_copy(update=update)


def _record(state: MergeAttemptState = MergeAttemptState.RELEASED, **update: object) -> MergeAttemptRecord:
    return MergeAttemptRecord(
        approval_id=_DIGEST,
        change_id="change-a",
        offer_id=_DIGEST,
        submission_id="dialog-1",
        host_id="host-1",
        session_id="cockpit",
        approved_at="2026-10-05T00:00:00Z",
        repository=_REPOSITORY,
        number=7,
        node_id="PR_node_7",
        head_sha=_HEAD,
        base_branch="main",
        target_head=_TARGET,
        finalization_id=_DIGEST,
        ready_receipt_id=_DIGEST,
        merge_method=PublicationMergeMethod.MERGE,
        state=state,
    ).model_copy(update=update)


def _evidence(
    *, merged: bool = False, state: str = "open", head: str = _HEAD, base: str = "main", parent: str = _TARGET
):
    return PublicationMergeEvidence(
        repository=_REPOSITORY,
        number=7,
        node_id="PR_node_7",
        state="closed" if merged else state,
        draft=False,
        merged=merged,
        head_sha=head,
        base_branch=base,
        merge_commit_sha="e" * 40 if merged else None,
        merge_commit_parents=(parent, head) if merged else (),
        merged_at=datetime(2026, 10, 5, tzinfo=UTC) if merged else None,
    )


def _pending(method: str = "merge") -> PublicationMergeRequestResult:
    return PublicationMergeRequestResult(
        status=PublicationMergeRequestStatus.PENDING,
        pending=PendingMergeRequest(
            request_id="uuid-1",
            expected_head_sha=_HEAD,
            merge_method=method,
            merge_action="direct_merge",
            bypass_rules=False,
        ),
    )


_REFUSED = PublicationMergeRequestResult(
    status=PublicationMergeRequestStatus.REFUSED,
    refusal=PublicationMergeRefusal(reason=PublicationMergeRefusalReason.RULES_FAILED),
)
_UNAVAILABLE = PublicationMergeRequestResult(status=PublicationMergeRequestStatus.UNAVAILABLE)
_S = MergeAttemptState


@pytest.mark.parametrize(
    ("start", "evidence", "result", "state", "extra"),
    [
        pytest.param(_S.PENDING, _evidence(merged=True), None, _S.MERGED, {"race": MergeRace.NONE}, id="S1"),
        pytest.param(_S.INTENT, _evidence(merged=True), None, _S.MERGED, {"race": MergeRace.NONE}, id="S1-intent"),
        pytest.param(
            _S.RELEASED,
            _evidence(merged=True, parent=_OTHER),
            None,
            _S.MERGED,
            {"race": MergeRace.TARGET_ADVANCED},
            id="S1-target-advanced",
        ),
        pytest.param(
            _S.RELEASED,
            _evidence(merged=True, base="release"),
            None,
            _S.MERGED,
            {"race": MergeRace.SCOPE_CHANGED},
            id="S1-scope-changed",
        ),
        pytest.param(_S.PENDING, _evidence(merged=True, head=_OTHER), None, _S.HEAD_CHANGED, {}, id="S2"),
        pytest.param(_S.INTENT, _evidence(), None, _S.NOT_SENT, {}, id="S3"),
        pytest.param(_S.INTENT, None, None, _S.NOT_SENT, {}, id="S3-read-failed"),
        pytest.param(_S.RELEASED, _evidence(), _REFUSED, _S.REFUSED, {"refusal_reason": "rules-failed"}, id="S4"),
        pytest.param(
            _S.RELEASED,
            _evidence(),
            _pending("squash"),
            _S.REFUSED,
            {"refusal_reason": "foreign-request"},
            id="S4-foreign-409",
        ),
        pytest.param(_S.PENDING, _evidence(state="closed"), _pending(), _S.CLOSED, {}, id="S6-over-S5"),
        pytest.param(_S.PENDING, _evidence(head=_OTHER), _pending(), _S.HEAD_CHANGED, {}, id="S7-over-S5"),
        pytest.param(_S.RELEASED, _evidence(), _pending(), _S.PENDING, {"request_id": "uuid-1"}, id="S5"),
        pytest.param(_S.PENDING, _evidence(), _UNAVAILABLE, _S.PENDING, {}, id="S8-uuid-404"),
        pytest.param(_S.RELEASED, None, None, _S.RELEASED, {}, id="S8-read-failed"),
        pytest.param(_S.REFUSED, _evidence(merged=True), None, _S.REFUSED, {}, id="terminal-unchanged"),
    ],
)
def test_settlement_rows_apply_in_match_order(start, evidence, result, state, extra) -> None:
    settled = settle_merge_attempt(_record(start), evidence, result)

    assert settled.state is state
    assert {key: getattr(settled, key) for key in extra} == extra


def test_one_approval_sends_one_fenced_request_and_completes_once(tmp_path: Path) -> None:
    application, _runtime, memory, head, state_root = _memory_awaiting_merge(tmp_path)
    states_at_send = []
    original = InMemoryPublicationProvider._submit_merge

    def submit(provider, request):
        states_at_send.append(_attempt(state_root).state)
        return original(provider, request)

    with patch.object(InMemoryPublicationProvider, "_submit_merge", autospec=True, side_effect=submit):
        approved = _approve(application)

    assert states_at_send == [MergeAttemptState.RELEASED]
    assert [json.loads(body) for body in memory.merge_request_bodies] == [
        {"bypass_rules": False, "merge_action": "direct_merge", "merge_method": "merge", "sha": head}
    ]
    assert (approved.attempt.state, approved.attempt.request_id, approved.completion_id) == (
        MergeAttemptState.PENDING,
        "merge-request-1",
        None,
    )
    assert _approve(application, approved.attempt.offer_id).attempt == approved.attempt
    readiness = application.get_change("change-a").readiness
    assert (readiness.reason_code, readiness.next_actor, readiness.executable) == (
        "merge-in-progress",
        WorkItemNextActor.NONE,
        False,
    )
    assert readiness.merge_attempt.pr_url == f"https://github.com/{_REPOSITORY}/pull/7"
    memory.execute_pending_merges()

    outcome = application.reconcile_awaiting_acceptance(("change-a",))[0]

    assert outcome.status.value == "completed", outcome
    assert (_attempt(state_root).state, _attempt(state_root).race) == (MergeAttemptState.MERGED, MergeRace.NONE)
    assert application.observe_acceptance("change-a").completion_id == outcome.completion_id
    assert len(_completions(state_root)) == 1
    assert application._coordinator.show("change-a").worktree_cleanup is not None
    assert len(memory.merge_request_bodies) == 1


def _stack(memory, _head, target):
    memory.set_stack(_REPOSITORY, 7, PublicationMergeStack(size=2, position=1, base_branch="main", base_sha=target))


def _checks(conclusion):
    def apply(memory, head, _target):
        check = _check(conclusion=conclusion).model_copy(update={"head_sha": head})
        memory.add_check_snapshot(
            PublicationCheckSnapshot(repository=_REPOSITORY, number=7, head_sha=head, checks=(check,))
        )

    return apply


_INVALID_OFFERS = {
    "head-changed": lambda memory, _head, _target: _update_pull_request(memory, head_sha=_OTHER),
    "target-advanced": lambda memory, _head, _target: memory.set_branch_head(_REPOSITORY, "main", _OTHER),
    "check-failed": _checks("failure"),
    "check-pending": _checks(None),
    "stale-offer-id": lambda _memory, _head, _target: None,
    "stacked": _stack,
    "wrong-base": lambda memory, _head, _target: _update_pull_request(memory, base_branch="release"),
    "draft": lambda memory, _head, _target: _update_pull_request(memory, draft=True),
    "closed": lambda memory, _head, _target: _update_pull_request(memory, state="closed"),
    "provider-down": lambda _memory, _head, _target: None,
}


@pytest.mark.parametrize("case", sorted(_INVALID_OFFERS))
def test_an_offer_invalid_at_execution_sends_nothing_and_writes_no_attempt(tmp_path: Path, case: str) -> None:
    application, runtime, memory, head, state_root = _memory_awaiting_merge(tmp_path)
    offer_id = "0" * 64 if case == "stale-offer-id" else _offer_id(application)
    _INVALID_OFFERS[case](memory, head, runtime.target_sync_receipt().target_head)
    outage = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE, "read_pull_request", "down", retry_safe=True
    )

    with (
        patch.object(
            InMemoryPublicationProvider,
            "read_pull_request",
            autospec=True,
            side_effect=outage if case == "provider-down" else InMemoryPublicationProvider.read_pull_request,
        ),
        pytest.raises(DeliveryMergeError) as refused,
    ):
        _approve(application, offer_id)

    # A retargeted PR no longer matches its bound publication, so the fresh read itself refuses.
    unavailable = case in {"provider-down", "wrong-base"}
    assert refused.value.code == (ERR_MERGE_UNAVAILABLE if unavailable else ERR_MERGE_OFFER_STALE)
    assert refused.value.readiness is not None
    if case == "stale-offer-id":
        assert refused.value.readiness.merge_offer.offer_id != offer_id
    assert memory.merge_request_bodies == []
    assert MergeAttemptStore(state_root, "change-a").attempts() == ()


def test_concurrent_approvals_from_two_processes_send_one_request_and_complete_once(tmp_path: Path) -> None:
    application, runtime, memory, _head, state_root = _memory_awaiting_merge(tmp_path)
    offer_id = _offer_id(application)
    other = _reopen_with_providers(tmp_path, application, runtime, state_root, [datetime(2026, 8, 4, tzinfo=UTC)])
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def approve(target: PortfolioApplication, submission: str) -> None:
        barrier.wait()
        try:
            outcomes.append(_approve(target, offer_id, submission).attempt.state.value)
        except DeliveryMergeError as exc:
            outcomes.append(exc.code)

    threads = [threading.Thread(target=approve, args=item) for item in ((application, "a"), (other, "b"))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == sorted(["pending", ERR_MERGE_IN_PROGRESS])
    assert len(memory.merge_request_bodies) == 1
    memory.execute_pending_merges()
    receipts = {target.observe_acceptance("change-a").completion_id for target in (application, other)}
    assert len(receipts) == 1
    assert len(_completions(state_root)) == 1


@pytest.mark.parametrize("refusal", ["provider-refused", "foreign-request"])
def test_a_refused_request_ends_the_approval_and_a_new_approval_is_accepted(tmp_path: Path, refusal: str) -> None:
    application, _runtime, memory, head, state_root = _memory_awaiting_merge(tmp_path)
    if refusal == "provider-refused":
        memory.next_merge_refusal = PublicationMergeRefusal(
            reason=PublicationMergeRefusalReason.NOT_MERGEABLE, http_status=405, message="not mergeable"
        )
    else:
        memory.add_foreign_merge_request(
            _REPOSITORY,
            7,
            PendingMergeRequest(
                request_id="foreign-1",
                expected_head_sha=head,
                merge_method="squash",
                merge_action="direct_merge",
                bypass_rules=False,
            ),
        )

    refused = _approve(application)

    assert (refused.attempt.state, refused.attempt.refusal_reason) == (
        MergeAttemptState.REFUSED,
        "not-mergeable" if refusal == "provider-refused" else "foreign-request",
    )
    memory.merge_requests.clear()
    again = _approve(application, submission="dialog-2")
    assert again.attempt.state is MergeAttemptState.PENDING
    assert len(memory.merge_request_bodies) == 2
    assert len(MergeAttemptStore(state_root, "change-a").attempts()) == 2


@pytest.mark.parametrize(
    ("case", "path", "expected"),
    [
        ("pending", "background", MergeAttemptState.PENDING),
        ("lost-response", "explicit", MergeAttemptState.RELEASED),
        ("closed", "explicit", MergeAttemptState.CLOSED),
        ("moved-head", "background", MergeAttemptState.HEAD_CHANGED),
    ],
)
def test_every_acceptance_path_settles_the_attempt_after_a_restart(
    tmp_path: Path, case: str, path: str, expected: MergeAttemptState
) -> None:
    application, runtime, memory, _head, state_root = _memory_awaiting_merge(tmp_path)
    memory.lose_next_merge_response = case == "lost-response"
    try:
        _approve(application)
    except PublicationProviderError:
        assert case == "lost-response"
    reopened = _reopen_with_providers(tmp_path, application, runtime, state_root, [datetime(2026, 8, 4, tzinfo=UTC)])
    if case == "closed":
        _update_pull_request(memory, state="closed")
    elif case == "moved-head":
        _update_pull_request(memory, head_sha=_OTHER)

    if path == "background":
        outcome = reopened.reconcile_awaiting_acceptance(("change-a",))[0]
        assert outcome.status.value == ("head-moved" if case == "moved-head" else "waiting"), outcome
    else:
        with pytest.raises(DeliveryAcceptanceWaitingError if case == "lost-response" else PortfolioApplicationError):
            reopened.observe_acceptance("change-a")

    assert _attempt(state_root).state is expected
    if expected in {MergeAttemptState.PENDING, MergeAttemptState.RELEASED}:
        with pytest.raises(DeliveryMergeError):
            reopened._require_no_merge_in_flight("change-a")
    else:
        reopened._require_no_merge_in_flight("change-a")
    if case == "closed":
        assert reopened._runtimes["change-a"].change_disposition().acceptance_reason.value == "closed-unmerged"


def _advance_target(memory: InMemoryPublicationProvider) -> None:
    memory.set_branch_head(_REPOSITORY, "main", _OTHER)
    memory.execute_pending_merges()


def _retarget(memory: InMemoryPublicationProvider) -> None:
    memory.set_branch_head(_REPOSITORY, "release", memory.branch_heads[(_REPOSITORY, "main")])
    _update_pull_request(memory, base_branch="release")
    memory.execute_pending_merges()


def _manual_after_advance(memory: InMemoryPublicationProvider) -> None:
    memory.set_branch_head(_REPOSITORY, "main", _OTHER)
    memory.merge_manually(_REPOSITORY, 7)


@pytest.mark.parametrize(
    ("merge", "race", "diagnostic"),
    [
        (_advance_target, MergeRace.TARGET_ADVANCED, "target-advanced-during-merge"),
        (_manual_after_advance, MergeRace.TARGET_ADVANCED, "target-advanced-during-merge"),
        # The bound publication refuses a retargeted PR's read, so no observation exists to attach attention to.
        (_retarget, MergeRace.SCOPE_CHANGED, None),
    ],
)
def test_a_raced_merge_is_attention_never_completion(tmp_path: Path, merge, race, diagnostic) -> None:
    application, runtime, memory, _head, state_root = _memory_awaiting_merge(tmp_path)
    approved = _approve(application)
    merge(memory)

    outcome = application.reconcile_awaiting_acceptance(("change-a",))[0]

    assert outcome.status.value == ("attention" if diagnostic else "provider-unavailable"), outcome
    assert (_attempt(state_root).state, _attempt(state_root).race) == (MergeAttemptState.MERGED, race)
    if diagnostic:
        assert f"{diagnostic}:{approved.attempt.approval_id}" in runtime.change_disposition().diagnostics
    assert (runtime.merged_pull_request_latch(), runtime.completion_receipt()) == (None, None)
    assert application._coordinator.show("change-a").worktree_cleanup is None
    frontier, attempt = runtime.frontier_bytes(), _attempt(state_root)
    with pytest.raises((PortfolioApplicationError, PublicationProviderError, DeliveryAcceptanceWaitingError)):
        application.observe_acceptance("change-a")
    assert (runtime.frontier_bytes(), _attempt(state_root)) == (frontier, attempt)


_INTER_READ_FLIPS = {
    "merged": InMemoryPublicationProvider.execute_pending_merges,
    "target-advanced": _advance_target,
    "closed": lambda memory: _update_pull_request(memory, state="closed"),
    "moved-head": lambda memory: _update_pull_request(memory, head_sha=_OTHER),
}


_INTER_READ_EXPECTED = {
    "merged": ("completed", MergeAttemptState.MERGED, MergeRace.NONE, None),
    "target-advanced": ("attention", MergeAttemptState.MERGED, MergeRace.TARGET_ADVANCED, "identity-mismatch"),
    "closed": ("attention", MergeAttemptState.CLOSED, None, "closed-unmerged"),
    "moved-head": ("head-moved", MergeAttemptState.HEAD_CHANGED, None, None),
}


@pytest.mark.parametrize("path", ["background", "explicit"])
@pytest.mark.parametrize("flip", sorted(_INTER_READ_FLIPS))
def test_a_provider_change_between_the_settlement_and_acceptance_reads_settles_the_attempt_first(
    tmp_path: Path, path: str, flip: str
) -> None:
    background, expected, race, reason = _INTER_READ_EXPECTED[flip]
    application, runtime, memory, _head, state_root = _memory_awaiting_merge(tmp_path)
    assert _approve(application).attempt.state is MergeAttemptState.PENDING
    publisher = application._draft_pull_request_publisher
    observe = publisher.observe_pull_request
    flips = [_INTER_READ_FLIPS[flip]]

    def flip_then_observe(request):
        while flips:
            flips.pop()(memory)
        return observe(request)

    with patch.object(publisher, "observe_pull_request", side_effect=flip_then_observe):
        if path == "background":
            status = application.reconcile_awaiting_acceptance(("change-a",))[0].status.value
        else:
            try:
                status = "completed" if application.observe_acceptance("change-a").completion_id else None
            except PortfolioApplicationError:
                status = "refused"

    completed = flip == "merged"
    assert flips == []
    assert status == (background if path == "background" or completed else "refused")
    assert (_attempt(state_root).state, _attempt(state_root).race) == (expected, race)
    assert len(_completions(state_root)) == int(completed)
    assert (runtime.merged_pull_request_latch() is not None) is completed
    assert (application._coordinator.show("change-a").worktree_cleanup is not None) is completed
    if reason is not None:
        assert runtime.change_disposition().acceptance_reason.value == reason
    if race is MergeRace.TARGET_ADVANCED:
        diagnostics = runtime.change_disposition().diagnostics
        assert any(item.startswith("target-advanced-during-merge:") for item in diagnostics)
    assert len(memory.merge_request_bodies) == 1


@pytest.mark.asyncio
async def test_an_unknown_merge_waits_for_the_user_and_check_again_reads_once(tmp_path: Path) -> None:
    application, runtime, memory, _head, state_root = _memory_awaiting_merge(tmp_path)
    start = datetime(2026, 8, 4, tzinfo=UTC)
    now = [start]
    _with_clock(application, now)
    memory.lose_next_merge_response = True
    with pytest.raises(PublicationProviderError):
        _approve(application)
    for seconds in (0, 1, 3):
        now[0] = start + timedelta(seconds=seconds)
        assert application.reconcile_awaiting_acceptance(("change-a",))[0].status.value == "waiting"
    now[0] += timedelta(days=1)

    readiness = application.get_change("change-a").readiness
    assert (readiness.reason_code, readiness.next_actor, readiness.merge_attempt.state) == (
        "merge-response-unknown",
        WorkItemNextActor.YOU,
        "released",
    )
    assert _acquire(application).kind == "human"
    with _counted_reads() as reads:
        application.reconcile_awaiting_acceptance(("change-a",))
    assert reads.call_count == 0
    async with Client(assemble_target_server(application)) as client:
        with _counted_reads() as reads:
            still = await client.call_tool("observe_acceptance", {"change_id": "change-a"})
    # One read set per Check again: the settlement's merge evidence and the acceptance observation.
    assert (still.is_error, reads.call_count, _attempt(state_root).state) == (True, 2, MergeAttemptState.RELEASED)
    reopened = _reopen_with_providers(tmp_path, application, runtime, state_root, now)
    memory.execute_pending_merges()
    async with Client(assemble_target_server(reopened)) as client:
        with _counted_reads() as reads:
            merged = await client.call_tool("observe_acceptance", {"change_id": "change-a"})

    assert (merged.is_error, reads.call_count) == (False, 2)
    assert _attempt(state_root).state is MergeAttemptState.MERGED
    assert (len(_completions(state_root)), len(memory.merge_request_bodies)) == (1, 1)


def test_abandon_stays_allowed_while_the_merge_is_unknown(tmp_path: Path) -> None:
    application, runtime, memory, _head, state_root = _memory_awaiting_merge(tmp_path)
    memory.lose_next_merge_response = True
    with pytest.raises(PublicationProviderError):
        _approve(application)

    application.set_change_intent(
        DeliveryChangeIntent(
            change_id="change-a",
            kind=DeliveryChangeIntentKind.ABANDON,
            expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            reason="Merge outcome unknown",
        )
    )

    assert runtime.change_abandonment() is not None
    assert (_attempt(state_root).state, len(memory.merge_request_bodies)) == (MergeAttemptState.RELEASED, 1)


_FENCED_OWNERS = {
    "sync_change_with_target": lambda app, _head: app.sync_change_with_target("change-a", _OTHER, "sync-1"),
    "mark_change_ready": lambda app, _head: app.mark_current_change_ready("change-a"),
    "prepare_review_repair": lambda app, _head: app.prepare_review_repair("change-a"),
    "adopt_external_head": lambda app, head: app.adopt_external_head("change-a", head, _OTHER, "adopt-1"),
    "promote_external_head": lambda app, head: app.promote_external_head("change-a", head, "promote-1"),
    "reconcile_finalization_head": lambda app, _head: app.reconcile_finalization_head("change-a"),
}


@pytest.mark.parametrize("owner", sorted(_FENCED_OWNERS))
def test_owners_refuse_before_any_effect_while_a_merge_is_unsettled(tmp_path: Path, owner: str) -> None:
    application, runtime, memory, head, _state_root = _memory_awaiting_merge(tmp_path)
    _approve(application)
    frontier, coordination = runtime.frontier_bytes(), application._coordinator.show("change-a")
    pull_requests = dict(memory.pull_requests)

    with _counted_reads() as reads, pytest.raises(DeliveryMergeError) as refused:
        _FENCED_OWNERS[owner](application, head)

    assert refused.value.code == ERR_MERGE_IN_PROGRESS
    assert reads.call_count == 0
    assert (runtime.frontier_bytes(), application._coordinator.show("change-a")) == (frontier, coordination)
    assert (memory.pull_requests, len(memory.merge_request_bodies)) == (pull_requests, 1)


def _crash_writing_released(store, record, *, expected):
    if record.state is MergeAttemptState.RELEASED:
        raise _Crash
    return _ORIGINAL_WRITE(store, record, expected=expected)


_ORIGINAL_WRITE = MergeAttemptStore.write
_ORIGINAL_SUBMIT = InMemoryPublicationProvider._submit_merge


def _submit_then_crash(provider, request):
    _ORIGINAL_SUBMIT(provider, request)
    raise _Crash


def _merged_on_request(provider, request):
    provider.merge_manually(request.repository, request.number)
    return _ORIGINAL_SUBMIT(provider, request)


_CRASHES = {
    "before-released": lambda: patch.object(
        MergeAttemptStore, "write", autospec=True, side_effect=_crash_writing_released
    ),
    "after-released": lambda: patch.object(
        InMemoryPublicationProvider, "_submit_merge", autospec=True, side_effect=_submit_then_crash
    ),
    "after-merged": lambda: patch.object(PortfolioApplication, "observe_acceptance", side_effect=_Crash),
    "after-completion": lambda: patch.object(
        PortfolioApplication, "_cleanup_completed_worktree_best_effort", side_effect=_Crash
    ),
}


@pytest.mark.parametrize("boundary", sorted(_CRASHES))
def test_a_crash_at_each_outcome_changing_boundary_replays_to_one_outcome(tmp_path: Path, boundary: str) -> None:
    application, runtime, memory, _head, state_root = _memory_awaiting_merge(tmp_path)
    application._change_branch_publisher = ChangeBranchPublisher(
        application._workspace_manager.repository,
        application._coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "branch-operations",
    )
    offer_id = _offer_id(application)
    merged_on_request = (
        patch.object(InMemoryPublicationProvider, "_submit_merge", autospec=True, side_effect=_merged_on_request)
        if boundary == "after-merged"
        else contextlib.nullcontext()
    )

    def run_until_crash() -> None:
        _approve(application, offer_id)
        memory.execute_pending_merges()
        application.reconcile_awaiting_acceptance(("change-a",))

    with merged_on_request, _CRASHES[boundary](), pytest.raises(_Crash):
        run_until_crash()
    now = [datetime(2026, 8, 4, tzinfo=UTC)]
    reopened = _reopen_with_providers(tmp_path, application, runtime, state_root, now)

    if boundary == "before-released":
        assert memory.merge_request_bodies == []
        reopened.reconcile_awaiting_acceptance(("change-a",))
        assert _attempt(state_root).state is MergeAttemptState.NOT_SENT
        assert _offer_id(reopened) == offer_id
        return
    if boundary == "after-released":
        assert reopened.reconcile_awaiting_acceptance(("change-a",))[0].status.value == "waiting"
        assert _attempt(state_root).state is MergeAttemptState.RELEASED
        memory.execute_pending_merges()
        now[0] += timedelta(days=1)
    if boundary == "after-completion":
        reopened.reconcile_pending_checkpoints()
        assert reopened._coordinator.show("change-a").worktree_cleanup is not None
    else:
        assert reopened.observe_acceptance("change-a").finalized_change_head == _attempt(state_root).head_sha
    assert _attempt(state_root).state is MergeAttemptState.MERGED
    assert (len(_completions(state_root)), len(memory.merge_request_bodies)) == (1, 1)


_START = datetime(2026, 8, 4, tzinfo=UTC)


def _reconcile_reads(*hosts: PortfolioApplication) -> list[int]:
    counts = []
    for host in hosts:
        with _counted_reads() as reads:
            host.reconcile_awaiting_acceptance(("change-a",))
        counts.append(reads.call_count)
    return counts


def test_an_approval_after_exhausted_reads_is_observed_until_completion(tmp_path: Path) -> None:
    application, _runtime, memory, _head, state_root = _memory_awaiting_merge(tmp_path)
    now = [_START]
    _with_clock(application, now)
    for seconds in (0, 1, 3):
        now[0] = _START + timedelta(seconds=seconds)
        application.reconcile_awaiting_acceptance(("change-a",))
    now[0] = _START + timedelta(hours=1)
    assert _approve(application).attempt.state is MergeAttemptState.PENDING

    for minutes in (1, 2, 9):
        now[0] = _START + timedelta(hours=1, minutes=minutes)
        assert _reconcile_reads(application)[0] > 0
        assert application.get_change("change-a").readiness.reason_code == "merge-in-progress"
    now[0] = _START + timedelta(hours=1, minutes=11)
    assert application.get_change("change-a").readiness.reason_code == "merge-response-unknown"
    memory.execute_pending_merges()
    now[0] += timedelta(minutes=1)

    assert application.reconcile_awaiting_acceptance(("change-a",))[0].status.value == "completed"
    assert (len(_completions(state_root)), len(memory.merge_request_bodies)) == (1, 1)


def test_a_merged_approval_converges_after_repeated_read_failures_and_a_restart(tmp_path: Path) -> None:
    application, runtime, memory, _head, state_root = _memory_awaiting_merge(tmp_path)
    now = [_START]
    _with_clock(application, now)
    _approve(application)
    memory.execute_pending_merges()
    outage = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE, "observe_pull_request", "down", retry_safe=True
    )
    publisher = application._draft_pull_request_publisher

    with patch.object(publisher, "observe_pull_request", side_effect=outage):
        for step in range(5):
            now[0] = _START + timedelta(seconds=31 * step)
            outcome = application.reconcile_awaiting_acceptance(("change-a",))[0]
            assert outcome.status.value == "provider-unavailable", outcome
    assert (_attempt(state_root).state, runtime.completion_receipt()) == (MergeAttemptState.MERGED, None)
    reopened = _reopen_with_providers(tmp_path, application, runtime, state_root, now)
    now[0] += timedelta(seconds=31)

    assert reopened.reconcile_awaiting_acceptance(("change-a",))[0].status.value == "completed"
    assert (len(_completions(state_root)), len(memory.merge_request_bodies)) == (1, 1)


def test_hosts_share_one_merge_observation_cadence(tmp_path: Path) -> None:
    application, runtime, _memory, _head, state_root = _memory_awaiting_merge(tmp_path)
    now = [_START]
    _with_clock(application, now)
    _approve(application)
    other = _reopen_with_providers(tmp_path, application, runtime, state_root, now)

    first = _reconcile_reads(application, other, application, other)
    now[0] = _START + timedelta(seconds=31)
    second = _reconcile_reads(other, application, other)

    assert first[0] > 0
    assert (first[1:], second) == ([0, 0, 0], [first[0], 0, 0])


def test_check_again_reads_without_extending_the_approval_window(tmp_path: Path) -> None:
    application, _runtime, memory, _head, _state_root = _memory_awaiting_merge(tmp_path)
    now = [_START]
    _with_clock(application, now)
    memory.lose_next_merge_response = True
    with pytest.raises(PublicationProviderError):
        _approve(application)

    now[0] = _START + timedelta(hours=23, minutes=59)
    with _counted_reads() as reads, pytest.raises(DeliveryAcceptanceWaitingError):
        application.observe_acceptance("change-a")
    assert reads.call_count > 0
    now[0] = _START + timedelta(hours=24, minutes=1)

    assert _reconcile_reads(application) == [0]
    with _counted_reads() as reads, pytest.raises(DeliveryAcceptanceWaitingError):
        application.observe_acceptance("change-a")
    assert reads.call_count > 0


def test_an_observation_interrupted_after_the_merge_settles_recovers_after_a_restart(tmp_path: Path) -> None:
    application, runtime, memory, _head, state_root = _memory_awaiting_merge(tmp_path)
    now = [_START]
    _with_clock(application, now)
    _approve(application)
    memory.execute_pending_merges()

    with (
        patch.object(PortfolioApplication, "_observe_acceptance_once", side_effect=_Crash),
        pytest.raises(_Crash),
    ):
        application.reconcile_awaiting_acceptance(("change-a",))
    assert (_attempt(state_root).state, runtime.completion_receipt()) == (MergeAttemptState.MERGED, None)
    reopened = _reopen_with_providers(tmp_path, application, runtime, state_root, now)
    now[0] = _START + timedelta(seconds=31)

    assert reopened.reconcile_awaiting_acceptance(("change-a",))[0].status.value == "completed"
    assert (len(_completions(state_root)), len(memory.merge_request_bodies)) == (1, 1)


def test_retained_custody_skips_only_that_change_in_the_acceptance_batch(tmp_path: Path) -> None:
    application, *_ = _memory_awaiting_merge(tmp_path)
    busy = DeliveryActionBusyError("selected Change retains engine action custody: continue-1")

    with patch.object(application, "_runtime", side_effect=busy):
        outcome = application._reconcile_awaiting_acceptance_change("change-a")

    assert (outcome.status.value, outcome.code) == ("skipped", "ERR_DELIVERY_RECONCILIATION_BUSY")
