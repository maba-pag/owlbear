"""The host's launch of a person check's environment once its preparing Builder is gone (TD-24, TD-96)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import Recipe
from owlbear_delivery_next.change_flow import loop, worktree
from owlbear_delivery_next.workflow_steps import before, check, prepare

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.project_host.host import Host
    from owlbear_delivery_next.state_store.store import Lock


def launch(h: Host, lock: Lock, c: Change, now: datetime) -> Change:
    """Launch the check environment after the preparing Builder is gone; pending once it answers."""
    e = c.env
    if e is None or h.env_action(c) != "launch" or before.due(c) or prepare.due(h.store, c):
        return c  # the runner renders the "before" states, then prepares the test copy (TD-24, TD-96)
    if (left := h.clear(c, e)) is None or left:
        h.mark(c, left, now)  # never a second group beside one that may still run
        return c
    root = Path(c.names.worktree)
    recipe = tools.CheckRecipe(command=e.command, directory=e.directory, ready_url=e.ready_url, summary="host")
    errors = tools.check_recipe(recipe, tools.Worktree("", ""), root)
    if (env := prepare.environ(h.store, c)) is None:  # the test copy's explicit environment (TD-96)
        errors.append("the check has no test preparation; nothing launches without one")
    if errors:
        c.env = c.recipe = None
        h.say(f"{c.slug}: check environment failed: {'; '.join(errors)}")
        return loop.apply(c, check.failed("; ".join(errors)), now)
    c.env = e = e.model_copy(update={"pids": {}, "pgid": None, "ready_at": None, "launched_at": datetime.now(UTC)})
    h.store.write(lock, c)
    log = h.store.root / "changes" / c.slug / "env.log"
    if proc := check.start(e, root, log, env):
        c.env = e = e.model_copy(update={"pgid": proc.pid, "pids": {proc.pid: check.created(proc.pid)}})
        h.store.write(lock, c)
    pids = check.ready(e, proc) if proc else None
    if pids is None:
        if (left := h.clear(c, e)) is None or left:
            h.mark(c, left, now)
            return c
        c.env = c.recipe = None
        h.say(f"{c.slug}: check environment failed: no answer at {e.ready_url}")
        return loop.apply(c, check.failed(f"no answer at {e.ready_url}"), now)
    c.env = e.model_copy(update={"pids": pids, "ready_at": datetime.now(UTC)})
    c.recipe = Recipe(
        check=e.check,
        command=e.command,
        directory=e.directory,
        ready_url=e.ready_url,
        inputs=worktree.launch_inputs(root, e.directory),
    )
    h.say(f"{c.slug}: check environment ready at {e.ready_url}, group {e.pgid}, PIDs {sorted(pids)}")
    return loop.apply(c, check.pending(c, c.env), now)
