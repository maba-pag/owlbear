"""The leftovers of a runner's last step: its recorded processes and everything in their groups and sessions (#752)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import processes
from owlbear_delivery_next.runtimes import command_marks
from owlbear_delivery_next.workflow_steps import check

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.project_host.host import Host, RunnerRecord
    from owlbear_delivery_next.project_host.runner_end import Found


def survivors(h: Host, c: Change, rec: RunnerRecord | None) -> Found | str:
    """Processes of the last step still present, or why they could not be looked for.

    The runner and the remote Git leaders it recorded, and the groups its shell commands marked, are looked up as
    groups and sessions: a process of the step is found wherever it runs, and one the step did not start never counts.
    """
    since = rec.started_at if rec else c.step.started_at
    pids: dict[int, float | None] = {rec.pid: rec.created} if rec else {}
    for e in h.store.events(c.slug) if since else []:
        if e.get("event") == "pids" and datetime.fromisoformat(e["at"]) >= since - timedelta(seconds=1):
            pids |= {int(p): t for p, t in e["pids"].items()}
    found: Found = {p: "" for p, t in pids.items() if h.alive(p, t) is not False}
    try:
        marks = command_marks.read(command_marks.folder(h.store, c.slug), since) if since else {}
    except (OSError, ValueError) as exc:
        return f"the step's command marks could not be read: {exc}"
    try:
        found |= h.members(marks | pids)  # a recorded start time wins over a mark's
    except processes.UnlistedError as exc:
        return f"the step's processes could not be looked for: {exc}"
    return {p: v for p, v in found.items() if not (c.env and check.owned(c.env, p))}
