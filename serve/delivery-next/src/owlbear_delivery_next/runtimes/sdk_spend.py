"""A step session's lines in the spend ledger (D-01M5XCDF6G60VG5GHTWF5QSSDE): its start and its end.

The start comes before the first send, the end whatever ended the run. Both are queued for the ledger's writer
thread, so the step's event loop never waits for them.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.state_store import spend_ledger

if TYPE_CHECKING:
    from owlbear_delivery_next.runtimes.sdk_adapter import _Step


def meter(st: _Step, sid: str, agent: str) -> None:
    """The run's ``start`` line in the spend ledger, before its first send: from here it may spend credits."""
    st.metered = uuid.uuid4().hex
    before = None if "error" in st.billed else st.billed
    spend_ledger.started(st.metered, sid, agent=agent, job=st.cfg.job, model=st.cfg.model, before=before)


def final(st: _Step, usage: dict[str, Any]) -> None:
    """The run's last usage, read once its tasks settled and before its disconnect: what the ledger records.

    The step's own usage, which Delivery's model check proved, takes it only when both were read and it adds no
    model that check would not have allowed: the step's own and those its subagents billed. A step whose usage was
    unread stays so for that check, and the ledger still gets what could be read; a run cut short gets it as its own.
    """
    st.spent = usage if "error" not in usage else (st.run.usage or usage)
    if not st.run.usage:
        st.run.usage = usage
        return
    if "error" in usage or "error" in st.run.usage:
        return
    allowed = set(st.run.usage.get("models") or {}) | st.watch.child_models() | {st.cfg.model}
    grew = (usage.get("credits") or 0.0) >= (st.run.usage.get("credits") or 0.0)
    if grew and set(usage.get("models") or {}) <= allowed:
        st.run.usage = usage


def metered(st: _Step, *, interrupted: bool) -> None:
    """The run's ``end`` line in the spend ledger, whatever ended it; queued, so the event loop never waits for it.

    Its usage is the one read after its tasks settled (``final``), else the step's own, else unread.
    """
    if not st.metered:
        return
    usage = st.spent or st.run.usage or {"error": "not read"}
    ending = "interrupted" if interrupted else str(st.run.ending)
    reached = st.run.ending == "credit-limit"  # proven by its usage (``session_result.limit_reached``)
    children = sum(1 for s in st.watch.report() if s.get("allowed"))
    spend_ledger.ended(st.metered, st.run.session_id, usage=usage, ending=ending, limit=st.cfg.credit_limit,
                       stopped="reached" if reached else "", stopped_by="session" if reached else "",
                       subagents=children)  # fmt: skip
