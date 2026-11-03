"""Finishing an accepted curation run's apply that a stop cut short (#875), at the host's start and before a run's end.

`curation_tree.resume` does the work; this runs it for the machine's curation job, logs what it did and adds it to the
row of the folder whose apply it was, which the Maintenance page shows. The host goes on starting whatever it says.
"""

from __future__ import annotations

import logging
import subprocess
from typing import TYPE_CHECKING

from owlbear_delivery_next.machine_host import curation_tree
from owlbear_delivery_next.state_store.curation_runs import FolderRun

if TYPE_CHECKING:
    from owlbear_delivery_next.machine_host.curation import Curation

_log = logging.getLogger(__name__)


def recover(curation: Curation) -> curation_tree.Resumed | None:
    """Finish the cut-short apply of the machine's shared repository, if there is one; what it did, None if none."""
    try:
        shared = curation.shared()  # `DataRepoError`, a ValueError, while the repository is not cloned yet
        left = None if shared is None else curation_tree.resume(shared)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        _log.exception(  # its whole chain, once
            "memory curation: the apply a stop cut short could not be checked: %s: %s", type(exc).__name__, exc
        )
        return curation_tree.Resumed("", done=False, said=f"{type(exc).__name__}: {exc}")
    if left is None:
        return None
    level, did = (logging.WARNING, "finished") if left.done else (logging.ERROR, "could not finish")
    _log.log(level, "memory curation of %s: %s the apply a stop cut short: %s", left.folder, did, left.said)
    _noted(curation, left)
    return left


def _noted(curation: Curation, left: curation_tree.Resumed) -> None:
    """Add the outcome to the folder's row: the run whose apply it was, which a restart marked interrupted."""
    said = "were finished afterwards" if left.done else "could not be finished yet"
    with curation.lock:
        runs = curation.load()
        row = runs.folders.get(left.folder, FolderRun(state="failed"))
        reason = "; ".join(filter(None, (row.reason, f"its accepted edits {said}: {left.said}")))
        runs.folders[left.folder] = row.model_copy(update={"reason": reason})
        curation._write(runs)  # noqa: SLF001 - the job's own row file, under its lock
