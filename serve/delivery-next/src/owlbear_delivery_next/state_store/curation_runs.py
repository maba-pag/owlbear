"""The machine's record of memory curation runs in ``~/.owlbear``, each folder's last one.

The machine's curation writes it; a project's Maintenance overview reads it. This module depends on no higher layer.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - a field's type

from pydantic import Field

from owlbear_delivery_next.change_contracts.memory_curation_tools import Judged  # noqa: TC001 - a field's type
from owlbear_delivery_next.change_contracts.models import Record

STATE = "curation.json"


class FolderRun(Record):
    """One folder's last run: its state, when, the curator's report and what it left as it was."""

    state: str = "never"  # waiting, running, done, failed
    started_at: datetime | None = None
    ended_at: datetime | None = None
    summary: str = ""
    reason: str = ""
    key: str = ""  # the ledger's source for an uncertain run; empty when an older host ended it before the ledger
    entries: list[Judged] = Field(default_factory=list)
    skipped: dict[str, str] = Field(default_factory=dict)  # entry id: its revision when the curator skipped it
    seen: dict[str, str] = Field(default_factory=dict)  # every entry still pending after the run: id to revision


class Runs(Record):
    """Every folder's last run, kept in ``~/.owlbear`` because it is this machine's work."""

    folders: dict[str, FolderRun] = Field(default_factory=dict)
    left: dict[int, float | None] = Field(default_factory=dict)  # a run's processes not yet confirmed gone
    left_key: str = ""  # the run whose lease records those processes; empty when none does
