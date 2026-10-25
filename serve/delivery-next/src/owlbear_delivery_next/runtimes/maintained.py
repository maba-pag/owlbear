"""SDK runs owned by maintenance: admission is durable before SDK entry; uncertain results keep their lease."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import maintenance

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.runtimes.sdk_adapter import Session
    from owlbear_delivery_next.runtimes.session_result import Run


def run_owned(  # noqa: PLR0913 - owner, session and work are the inputs; the admission identity is three fields
    owner: maintenance.Maintenance,
    cfg: Session,
    execute: Callable[[Session], Run],
    *,
    project: str,
    slot: str,
    kind: maintenance.Kind,
) -> Run:
    """Enter SDK only after admission is durable; keep its lease after every exception or uncertain result."""
    try:
        ident = owner.begin(project, slot, kind, str(cfg.worktree))
    except BaseException:
        owner.slots.give(project, slot)  # SDK entry has not happened
        raise

    def event(found: dict[str, object]) -> None:
        if found.get("event") == "pids":
            raw = found.get("pids")
            maintenance.Lease.identities(raw)
            if not isinstance(raw, dict):
                raise maintenance.MaintenanceError("the SDK returned invalid process identities")  # noqa: TRY003, EM101
            owner.record(ident, {int(pid): born for pid, born in raw.items()})
        cfg.journal.event(found)

    try:
        done = execute(replace(cfg, journal=replace(cfg.journal, event=event)))
    except BaseException as primary:
        try:
            owner.failed(ident, primary)
        except BaseException as cleanup:  # noqa: BLE001 - recorded for any exit, then re-raised
            primary.add_note(f"maintenance ownership also failed to persist ({type(cleanup).__name__})")
        raise
    owner.finished(ident, done)
    return done
