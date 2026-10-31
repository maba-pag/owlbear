"""Why memory curation may not start for a folder: a setting unset or unreadable (D-01M61SBWK4VE4MNTD35TR0VPS8).

A folder is its project's memory, so a folder with a project layer counts all its project's settings beside the ones
curation itself reads outside any project; a folder with none has no project's work to hold, so only those count
(D-01M6A32JGMSYG3HQ58HF4QAB1T). This machine's settings count for every folder.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.settings import roles
from owlbear_delivery_next.settings.config import SettingsUnset
from owlbear_delivery_next.state_store import work_block
from owlbear_delivery_next.state_store.database import StoreError

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.settings.config import Settings
    from owlbear_delivery_next.state_store.curation_runs import FolderRun

LABEL = "memory-curation"


def unset(settings: Settings) -> str:
    """Why a run cannot start for unset settings: the curator's role, its threshold or a user-config switch; else ''."""
    try:
        agent = settings.agent(roles.SESSIONS[LABEL])
        settings.need("curator_threshold", *roles.USER_CONFIG)
    except SettingsUnset as exc:
        return str(exc)
    if agent.subagents is None:  # set per role: a run never guesses whether its subagents may start
        return f"agents.{roles.SESSIONS[LABEL]}.subagents is unset"
    return ""


def blocked(shared: DataRepo, folder: str, here: work_block.Block | None = None) -> str:
    """Why *folder*'s curation may not start; '' when it may. *here* is this machine's block, read now unless given."""
    try:
        own = unset(work_block.outside(shared))
    except StoreError as exc:
        return f"{work_block.UNREADABLE}{exc}"
    if own:
        return own
    if not shared.project_path(folder).exists():
        return (work_block.machine() if here is None else here).text()
    return work_block.of_folder(shared, folder, here).text()


def refusal(shared: DataRepo, folder: str, prior: FolderRun, started: datetime) -> FolderRun | None:
    """*folder*'s refused row, keeping what *prior* left pending and skipped; None when its curation may start."""
    if not (why := blocked(shared, folder)):
        return None
    return prior.model_copy(update={"state": "failed", "started_at": started, "ended_at": started, "reason": why})
