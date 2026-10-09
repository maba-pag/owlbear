"""N03-A stored-byte contract for a passive handoff stored at frontier 18 (section 1.7 S/N rows, I2).

The pre-N03 release wrote frontier 18, snapshot 2 and schema-1 evidence. These fixtures build a handoff with the
current owners from such a baseline, then store the local frontier exactly as that release left it.
"""

# ruff: noqa: SLF001

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from serve.delivery.tests.test_delivery_state import (
    _builder_return_restart_fixture,
    _BuilderReturnRestartFixture,
    _canonical_payload,
    _commit_corrupt_snapshot,
    _git,
    _healthy_restart,
    _settle_default_loader_planning_return,
)
from serve.delivery.tests.test_portfolio_application import _legacy_task_result

from owlbear_delivery import (
    BlockDelivery,
    DeliveryBuilderInvocationSettlement,
    DeliveryChangeIntent,
    DeliveryChangeIntentKind,
    DeliveryFrontier,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryWorkerRole,
)

_STATE_BRANCH = "owlbear/delivery-state"


def _legacy_frontier_payload(payload: dict[str, Any]) -> dict[str, Any]:
    frontier = DeliveryFrontier.model_validate_json(json.dumps(payload), strict=True)
    legacy = frontier.model_copy(
        update={
            "bindings": tuple(
                binding.model_copy(update={"results": tuple(_legacy_task_result(item) for item in binding.results)})
                for binding in frontier.bindings
            )
        }
    )
    return legacy.model_dump(mode="json") | {"schema_version": 18}


def _pre_n03_baseline(tmp_path: Path, change_id: str) -> _BuilderReturnRestartFixture:
    """Return the restart fixture after rewriting its remote snapshot and local frontier as pre-N03 records."""
    restart = _builder_return_restart_fixture(tmp_path, change_id)
    _git(restart.fresh, "config", "user.name", "Delivery State Test")
    _git(restart.fresh, "config", "user.email", "delivery-state@example.invalid")
    snapshot = json.loads(restart.remote_snapshot)
    snapshot["frontier"] = _legacy_frontier_payload(snapshot["frontier"])
    snapshot["schema_version"] = 2
    snapshot["snapshot_id"] = ""
    snapshot["snapshot_id"] = hashlib.sha256(_canonical_payload(snapshot)).hexdigest()
    content = _canonical_payload(snapshot)
    head = _commit_corrupt_snapshot(restart.fresh, restart.remote_state_head, change_id, content)
    _git(restart.fresh, "push", "origin", f"{head}:refs/heads/{_STATE_BRANCH}", "--force")
    _frontier_path(restart, change_id).write_bytes(_canonical_payload(snapshot["frontier"]))
    baseline = restart._replace(remote_state_head=head, remote_snapshot=content)
    return baseline._replace(application=_healthy_restart(baseline))


def _frontier_path(restart: _BuilderReturnRestartFixture, change_id: str) -> Path:
    return restart.fresh / ".owlbear/delivery/runtime/changes" / change_id / "frontier.json"


def _store_local_as_v18(restart: _BuilderReturnRestartFixture, change_id: str) -> bytes:
    """Store the passive handoff frontier exactly as the pre-N03 writer would have: version 18, same content."""
    path = _frontier_path(restart, change_id)
    payload = json.loads(path.read_bytes())
    assert payload["schema_version"] == 19
    stored = _canonical_payload(payload | {"schema_version": 18})
    path.write_bytes(stored)
    return stored


def _builder_handoff(restart: _BuilderReturnRestartFixture, change_id: str) -> None:
    launch = restart.application.acquire_frontier_work().launch_packages[0]
    assert launch.claim.worker_role is DeliveryWorkerRole.BUILDER
    (launch.worktree_path / "paused.txt").write_text("preserved Builder work\n", encoding="utf-8")
    _git(launch.worktree_path, "add", "paused.txt")
    _git(launch.worktree_path, "commit", "-m", "preserve Builder work")
    paused = restart.application.settle_worker_invocation(
        DeliveryBuilderInvocationSettlement(
            change_id=change_id,
            outcome_id=launch.outcome_id,
            claim_id=launch.claim.claim_id,
            attempt_id=launch.claim.attempt_id,
            task_id=launch.task_id,
            expected_last_reviewed_commit=launch.last_reviewed_commit,
            disposition="normal-return",
            request=BlockDelivery(
                action="block",
                outcome_id=launch.outcome_id,
                claim_id=launch.claim.claim_id,
                block_id="builder-pause-block",
                reason="A bounded decision is required.",
                unblock_condition="The user decides.",
                expected_evidence=("Decision",),
                locators=(launch.task_id,),
                request=DeliveryRequest(
                    request_id="builder-pause-decision",
                    kind=DeliveryRequestKind.DECISION,
                    outcome_id=launch.outcome_id,
                    summary="Choose the evidence source.",
                    options=(
                        DeliveryRequestOption(option_id="local", label="Use local evidence"),
                        DeliveryRequestOption(option_id="remote", label="Wait for remote evidence"),
                    ),
                ),
                resume_commit=_git(launch.worktree_path, "rev-parse", "HEAD"),
            ),
        ),
        host_id=launch.claim.owner_id,
        session_id=launch.claim.process_id,
    )
    assert paused.builder_handoff_context is not None
    assert paused.builder_handoff_context.route == "same-task"


def _intent(restart: _BuilderReturnRestartFixture, change_id: str, kind: DeliveryChangeIntentKind) -> None:
    application = _healthy_restart(restart)
    application.set_change_intent(
        DeliveryChangeIntent(
            change_id=change_id,
            kind=kind,
            expected_frontier_digest=hashlib.sha256(_frontier_path(restart, change_id).read_bytes()).hexdigest(),
            reason="Hold for review" if kind is DeliveryChangeIntentKind.DEFER else None,
        )
    )


def _intent_receipts(restart: _BuilderReturnRestartFixture, change_id: str) -> dict[str, bytes]:
    root = _frontier_path(restart, change_id).parent
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*.json"))
        if "before_frontier_digest" in json.loads(path.read_bytes())
    }


@pytest.mark.parametrize("route", ["builder", "planner"])
def test_defer_of_a_passive_v18_handoff_binds_the_stored_bytes_and_reloads(tmp_path: Path, route: str) -> None:
    change_id = f"stored-v18-{route}-handoff"
    restart = _pre_n03_baseline(tmp_path, change_id)
    snapshot = json.loads(restart.remote_snapshot)
    assert (snapshot["schema_version"], snapshot["frontier"]["schema_version"]) == (2, 18)
    if route == "builder":
        _builder_handoff(restart, change_id)
    else:
        settled = _settle_default_loader_planning_return(restart, change_id)
        assert settled.builder_handoff_context is not None
    stored = _store_local_as_v18(restart, change_id)
    assert _healthy_restart(restart)._runtimes[change_id].frontier_bytes() == stored
    assert _frontier_path(restart, change_id).read_bytes() == stored

    _intent(restart, change_id, DeliveryChangeIntentKind.DEFER)

    (deferral,) = (json.loads(content) for content in _intent_receipts(restart, change_id).values())
    assert deferral["schema_version"] == 2
    assert deferral["action"] == "defer"
    assert deferral["before_frontier_digest"] == hashlib.sha256(stored).hexdigest()
    assert deferral["before_frontier"]["schema_version"] == 18
    assert deferral["after_frontier"]["schema_version"] == 19
    assert json.loads(_frontier_path(restart, change_id).read_bytes())["schema_version"] == 19
    assert _healthy_restart(restart)._runtimes[change_id].change_deferral() is not None

    _intent(restart, change_id, DeliveryChangeIntentKind.RESUME)
    receipts = _intent_receipts(restart, change_id)
    resumed = next(json.loads(item) for item in receipts.values() if json.loads(item)["action"] == "resume")
    assert (resumed["before_frontier"]["schema_version"], resumed["after_frontier"]["schema_version"]) == (19, 19)
    reloaded = _healthy_restart(restart)
    assert reloaded._runtimes[change_id].change_deferral() is None
    assert _intent_receipts(restart, change_id) == receipts
    assert reloaded._runtimes[change_id].show_binding("OUT-001").builder_handoff_context is not None
