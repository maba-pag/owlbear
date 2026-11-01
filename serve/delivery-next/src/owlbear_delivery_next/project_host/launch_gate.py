"""Whether the host may start a runner or a check environment now: its code as loaded and every setting set."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import codebase
from owlbear_delivery_next.state_store import work_block

if TYPE_CHECKING:
    from owlbear_delivery_next.project_host.host import Host

RESTART = "Delivery's code changed since the host started; restart the host"


def stale(h: Host) -> bool:
    """Whether the package differs from what this host loaded, or cannot be read; checked again on every launch."""
    code = h.code()
    if code.startswith(codebase.UNREADABLE):
        reason = f"Delivery's code cannot be read: {code.removeprefix(codebase.UNREADABLE)}"
    else:
        reason = RESTART if code != h.record.code else None
    if reason != h.refused:
        h.say(f"no runner starts: {reason}" if reason else "Delivery's code is as loaded; runners start again")
        h.refused = reason
    return reason is not None


def blocked(h: Host) -> bool:
    """Whether a setting the project reads is unset or unreadable (D-01M61SBWK4VE4MNTD35TR0VPS8), read fresh.

    The log says so once, and once more when the owner's settings lift it.
    """
    why = work_block.of_store(h.store).text() or None
    if why != h.unset_said:
        h.say(f"no work starts: {why}" if why else "the settings are set; work starts again")
        h.unset_said = why
    return why is not None
