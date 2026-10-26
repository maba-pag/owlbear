"""The watcher of a Change-owned session (W1a): on by the Spotter's switch, with the places its reports are judged by.

The Spotter's looks at the session (Improvement design §4) get what the runner knows when the step starts: the
Spotter's settings (its categories' actions among them) and role, the machine's daily budget, the Change's unfinished
plan tasks and the decisions in force the step's worker has.

The session's own folder is its worktree, given when it runs. Guarded besides: every worktree in Delivery's worktrees
folder, every Change's state folder but this Change's own, and the project's main checkout with its Git folder, found
from the session's folder. Exempt (TD-46): temporary folders, the user's tool caches and Delivery's own state.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import watch_policy
from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.improvement import spotter
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.git_files import git_common_dir
from owlbear_delivery_next.runtimes import step_decisions, watch_feed
from owlbear_delivery_next.settings.config import SettingsUnset
from owlbear_delivery_next.state_store import machine_settings, project_home, watch_reports
from owlbear_delivery_next.state_store.database import StoreError

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.settings.config import Settings
    from owlbear_delivery_next.state_store.store import Lock, Store


def watching(  # noqa: PLR0913, PLR0917 - the session's Change, step, settings and folder, the runner's log, budget
    store: Store, lock: Lock, step: str, settings: Settings, at: Path, note: Callable[[str], None], budget: int | None
) -> watch_feed.Watching | None:
    """The watcher of a session of *lock*'s Change in *at*; None when the Spotter is switched off.

    *note* writes a line to the runner's log, where what the database could not take is told. *budget* is what
    ``needed`` returned before the step recorded anything (None: switched off), so nothing is read again here.
    """
    if budget is None:
        return None
    store.db.check()  # the writer's bounded writes need the database open
    home, changes = Path.home(), store.root / "changes"
    guarded = [worktree.data_root(), changes, *sorted(local_home.root().glob(f"{project_home.PROJECTS}/*/changes"))]
    if (clone := project_home.checkout(store.root.name)) is not None:  # the registered clone, wherever its git is
        guarded.append(clone)
    with contextlib.suppress(subprocess.CalledProcessError, OSError):
        common = git_common_dir(at)
        guarded += [common.parent, common] if common.name == ".git" else [common]
    exempt = (*watch_policy.exempt(home, os.environ), local_home.root(), store.root)
    tmp = Path(os.environ["TMPDIR"]) if os.environ.get("TMPDIR") else None
    places = watch_policy.Places(tuple(dict.fromkeys(guarded)), (changes / lock.slug,), exempt, home, tmp)
    writer = partial(watch_reports.Writer, store.db, lock, note=note)
    return watch_feed.Watching(lock.slug, step, places, writer, spot(store, lock, step, settings, budget))


def needed(settings: Settings) -> int | None:
    """Check every setting a watched session needs before a step records anything; the Spotter's budget, or None off.

    Switched off, a step needs nothing else of the Spotter: its other settings may stay unset (the page still shows
    them), with its role and budget.

    Raises:
        SettingsUnset: The Spotter's switch is unset or, when it is on, another of its settings (each category's
            action among them), its role or the machine's Spotter budget.
    """
    settings.need("spotter.switch")
    if settings.spotter.switch == "off":
        return None
    settings.need("spotter", "agents.spotter")
    if (budget := machine_settings.current().spotter_budget) is None:
        raise SettingsUnset(["spotter_budget"])
    return budget


def spot(store: Store, lock: Lock, step: str, settings: Settings, budget: int) -> spotter.Context:
    """What the Spotter's looks at a session of *lock*'s Change get; it is on and ``needed`` gave *budget*."""
    s, role, gaps = settings.spotter, settings.agent("spotter"), []
    try:
        change = store.read(lock.slug)
    except StoreError as exc:  # a look never stops a step: it goes without the plan
        change, gaps = None, [f"the Change's plan could not be read ({exc})"]
    plan = change.plan if change is not None else None
    return spotter.Context(
        project=store.root.name,
        change=lock.slug,
        step=step,
        looks=tuple(s.looks or ()),
        sample_rate=s.sample_rate or 0,
        verbose=s.verbose_on(datetime.now(UTC).date()),
        model=role.model or "",
        effort=role.effort or "",
        budget=budget,
        context=role.context or "",
        actions=s.actions(),
        open_work=tuple(t.title for t in plan.tasks if not t.done) if plan else (),
        decisions=tuple(line for line in step_decisions.held() if line.strip()),
        gaps=tuple(gaps),
    )
