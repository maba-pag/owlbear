"""A step session's lines in the spend ledger (D-01M5XCDF6G60VG5GHTWF5QSSDE): its start and its end.

The start comes before the first send, the end whatever ended the run. Both are queued for the ledger's writer
thread, so the step's event loop never waits for them.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from owlbear_delivery_next.state_store import spend_ledger

if TYPE_CHECKING:
    from owlbear_delivery_next.runtimes.sdk_adapter import _Step


def meter(st: _Step, sid: str, agent: str) -> None:
    """The run's ``start`` line in the spend ledger, before its first send: from here it may spend credits."""
    st.metered = uuid.uuid4().hex
    before = None if "error" in st.billed else st.billed
    spend_ledger.started(st.metered, sid, agent=agent, job=st.cfg.job, model=st.cfg.model, before=before)


def metered(st: _Step, *, interrupted: bool) -> None:
    """The run's ``end`` line in the spend ledger, whatever ended it; queued, so the event loop never waits for it.

    A run cut short (cancelled or shut down) has the usage its teardown read before the disconnect, or an unread one.
    """
    if not st.metered:
        return
    usage = st.run.usage or {"error": "not read"}
    ending = "interrupted" if interrupted else str(st.run.ending)
    stopped = "credit-limit" if st.run.ending == "credit-limit" else ""
    children = sum(1 for s in st.watch.report() if s.get("allowed"))
    spend_ledger.ended(st.metered, st.run.session_id, usage=usage, ending=ending, limit=st.cfg.credit_limit,
                       stopped=stopped, subagents=children)  # fmt: skip
