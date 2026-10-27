"""A step session's lines in the spend ledger (D-01M5XCDF6G60VG5GHTWF5QSSDE): its start and its end.

The start comes before the first send, the end whatever ended the run. Both are queued for the ledger's writer
thread, so the step's event loop never waits for them.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.runtimes.sdk_usage import unexpected_models
from owlbear_delivery_next.runtimes.session_result import limit_reached
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

    A run cut short takes it as its own. A step whose usage was read takes it under the same rules as Delivery's
    model check: the models that grew since the step began must be its own or those its subagents billed, else the
    step is a wrong model; a credit limit reached by then is its stop (``limit_reached``). A step whose usage was
    unread stays so. A failed read leaves the step's earlier usage to Delivery and gives the ledger that sample marked
    ``incomplete``: a lower bound, which ``spend_reconcile`` completes from the runtime's own log.
    """
    if "error" in usage:
        earlier = st.run.usage
        st.spent = earlier | {"incomplete": usage["error"]} if earlier and "error" not in earlier else earlier or usage
        st.run.usage = earlier or usage
        return
    st.spent = usage
    if st.run.usage and "error" in st.run.usage:
        return
    if (usage.get("credits") or 0.0) < (st.run.usage.get("credits") or 0.0):
        return  # an earlier read cannot be undone by a lower one
    if st.run.usage and (wrong := sorted(set(unexpected_models(st.billed, usage, st.cfg.model))
                                         - st.watch.child_models())):  # fmt: skip
        st.gate.wrong_model(f"the usage names {', '.join(wrong)}, the step needs {st.cfg.model}")
    st.run.usage = usage
    limit_reached(st.run, st.cfg.credit_limit)


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
