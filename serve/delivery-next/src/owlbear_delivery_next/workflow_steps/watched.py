"""The watcher of a Change-owned session (W1a): on by the master switch, with the places its reports are judged by.

The session's own folder is its worktree, given when it runs. Guarded besides: every worktree in Delivery's worktrees
folder, every Change's state folder but this Change's own, and the project's main checkout with its Git folder, found
from the session's folder. Exempt (TD-46): temporary folders, the user's tool caches and Delivery's own state.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import watch_policy
from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.git_files import git_common_dir
from owlbear_delivery_next.runtimes import watch_feed
from owlbear_delivery_next.state_store import project_home, watch_reports

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.settings.config import Settings
    from owlbear_delivery_next.state_store.store import Lock, Store


def watching(  # noqa: PLR0913, PLR0917 - the session's Change, step, settings and folder, and the runner's log
    store: Store, lock: Lock, step: str, settings: Settings, at: Path, note: Callable[[str], None]
) -> watch_feed.Watching | None:
    """The watcher of a session of *lock*'s Change in *at*; None when the master switch ``watcher`` is off.

    *note* writes a line to the runner's log, where what the database could not take is told.

    Raises:
        SettingsUnset: No layer sets the master switch.
    """
    settings.need("watcher")
    if not settings.watcher:
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
    return watch_feed.Watching(lock.slug, step, places, partial(watch_reports.Writer, store.db, lock, note=note))
