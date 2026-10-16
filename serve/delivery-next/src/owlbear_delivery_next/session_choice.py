"""Which agent session a step runs in: the answer's, a repair chance's, a held run's, or a new one."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next import budgets, held, repairs, session_result

if TYPE_CHECKING:
    from owlbear_delivery_next.models import Change, Question, Task
    from owlbear_delivery_next.store import Lock, Store


def new_id(change: Change) -> str:
    """A fresh session id naming the Change, step kind, and task or mode."""
    s = change.step
    return f"{change.slug}-{s.kind}-{s.task or s.mode or 'all'}-{uuid.uuid4().hex[:8]}"


def opening(
    store: Store, lock: Lock, change: Change, task: Task | None
) -> tuple[Question | None, session_result.Run | None, str, bool]:
    """The answer to deliver, the held result processed in place of a session (TD-56), the repair, and resume.

    The step's session is set: the one the answer goes to, the repair chance's (TD-123), the held run's, or new.
    """
    s = change.step
    answer = next(
        (q for q in reversed(change.questions) if q.step == s.kind and q.answer and not q.effect_observed_at), None
    )
    accepted = held.take(store, lock, change)
    repair = "" if accepted or (answer and s.session) else repairs.session(change, task)
    resume = bool(answer and s.session) or bool(repair)
    if repair:
        s.session = repair
    elif not resume:
        s.session = accepted.session_id if accepted else new_id(change)
    return answer, accepted, repair, resume


def replaced(store: Store, lock: Lock, change: Change, repair: str) -> tuple[Change, str | None]:
    """A missing resumed session's replacement: a repair chance falls back for free (TD-175); else it is charged."""
    new, now = new_id(change), datetime.now(UTC)
    if repair:
        store.log(lock, change.slug, {"event": "repair-fallback", "at": now.isoformat(timespec="seconds"),
                                      "session": repair, "fresh": new})  # fmt: skip
    else:
        change, within = budgets.charge(change, session_result.missing_cause(change.step.kind), now)
        new = new if within else None
    change.step.session = new
    store.write(lock, change)
    return change, new
