"""A bounded review, with each complete judge batch durable before the next starts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.audit_runs import record, suppression_items, suppression_publish, workspace
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store import spend_ledger
from owlbear_delivery_next.state_store.store import StoreError
from owlbear_delivery_next.workflow_steps import exceptions

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.audit_runs.job import Audits

BATCHES = 10
RETAINED = "Completed verdicts remain recorded."


def review(audits: Audits, state: dict, save: Callable[[], None]) -> None:
    """The caller owns one project audit and its maintenance-bound judge runner."""
    if audits.repo is None or audits.maintenance is None:
        msg = "Suppression review requires the project's clone and maintenance owner"
        raise RuntimeError(msg)
    store = audits.store
    where = spend_ledger.Where.of(store, job="Suppression review")
    with workspace.opened(audits.maintenance, audits.repo, state["commit"]) as copy:
        items = suppression_items.scan(copy.path, profile.lint_commands(store.read_profile() or Profile()))
        state.update(inventory=items, counts=suppression_items.counts(store.root, items), phase="judging suppressions")
        save()
        try:
            authority = exceptions.chat_authority(store)
        except (StoreError, OSError, ValueError, RuntimeError) as exc:
            authority = {"failed": failure(exc)}
        if "failed" in authority:
            state["judging_reason"] = str(authority["failed"])
        else:
            pending = [i for i in suppression_items.joined(store.root, items) if not i["judgment"]]
            for offset in range(0, min(len(pending), BATCHES * exceptions.LIMIT), exceptions.LIMIT):
                batch = [
                    {k: v for k, v in i.items() if k != "judgment"} for i in pending[offset : offset + exceptions.LIMIT]
                ]
                try:
                    said, done = exceptions.Judge(store, run=audits.run, folder=copy.path.parent)(
                        copy.path,
                        batch,
                        where,
                        authority | {"for": "review", "commit": state["commit"]},
                    )
                finally:
                    workspace.inspect(copy, state["commit"])
                if done:
                    state["session"] = done.session_id
                    state["subagents"].extend(done.subagents)
                state["counts"] = suppression_items.counts(store.root, items)
                save()
                if "failed" in said:
                    state["judging_reason"] = str(said["failed"])
                    break
    suppression_publish.prepare(store, state)
    state.update(state="publishing", phase="opening issues")
    save()


def finish(state: dict) -> None:
    """Publication can finish even when a later judge batch failed."""
    reason = state.get("judging_reason", "")
    state.update(
        state="failed" if reason else "done",
        phase="",
        reason=f"{reason}\n{RETAINED}" if reason else "",
        ended_at=record.now(),
    )
