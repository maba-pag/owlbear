"""A stuck step's repair: the one entry point for a cause and the step's evidence (#1065, #1066).

Setup problems arrive here once (D-01M6RT5QHWHB0ZHBBY0BE34FBE); #1062, #1064 and a red CI after publishing will hand
their causes to ``start`` too. Until Delivery's repair session lands (#1066), the Change stops naming the cause, so the
owner sees a setup problem rather than a brief that needs a change; clearing the stop runs the step again.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.failures import kind_of
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, Outcome, Stop

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.models import Change


def start(c: Change, cause: str, evidence: str, now: datetime) -> None:
    """Repair the step *c* is on, stopped by *cause*; *evidence* is what the step reported, whole."""
    reason = f"needs repair: {evidence}"
    c.stop = Stop(
        kind=ErrorKind(kind_of(cause)), reason=reason, action=f"Resolve {cause}", resume="the step runs again", at=now
    )
    c.outcome = Outcome(exit=Exit.STOP, cause=cause, reason=reason, who="you", at=now)
