"""A PDS update run's kept context (#777): what a waiting or restarted run needs to go on, and its next action."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.impeccable_runs import pack_publish, pack_repair

type Action = Literal["audit", "browser", "update", "challenge", "recheck", "reconsider", "wait", "publish"]
NEXT: dict[str, Action] = {
    "challenge": "challenge", "recheck": "recheck", "end": "wait", "dispute": "wait",
    "reconsider": "reconsider", "update": "update", "pass": "publish",
}  # fmt: skip
CANDIDATE, BASE, UPDATER, AUDIT, HEAD = "candidate", "base", "updater", "audit", "head"  # under the run's workspace
FOLDERS = (CANDIDATE, BASE, UPDATER, AUDIT, HEAD)
MARKER = "Opened by OwlBear Delivery for a PDS update."


class Context(BaseModel):
    """The candidate's versions and identities, the gates' evidence, the rounds' words and the next action."""

    model_config = ConfigDict(extra="forbid")

    version: str  # the release the candidate vendors
    old: str  # the base's pinned release
    why: str  # the pull request's title and the commit's subject
    diff: str  # the release's evidence: its changelog and the deprecations' diff
    checkout: dict[str, str]  # the package's checkout: its root, repository and the base pinned for the commit
    candidate: str  # C: the pin, vendored tree and served files, fixed once the candidate is made
    removed: list[str] = Field(default_factory=list)  # repository paths only the base's pin had
    vendored: str = ""  # the pinned files the release adds, changes and removes
    source: str = ""  # S as the merge gate last passed it
    audited: str = ""  # the S the audit last passed, its follow-ups aside
    browsed: str = ""  # the S the browser tests last passed
    findings: list[str] = Field(default_factory=list)  # the last audit's, for the updater
    failures: list[str] = Field(default_factory=list)  # browser tests the candidate broke, for the updater
    follow_ups: dict[str, str] = Field(default_factory=dict)  # the last audit's follow-ups by identity, for the owner
    followed: list[str] = Field(default_factory=list)  # the follow-ups the owner continued without changing
    sessions: int = 0  # updater sessions so far, each counted against the round policy
    summary: str = ""  # the updater's reports so far
    accepted: str = ""  # the identity the owner activated without a pass
    after: Action = "challenge"  # what follows the updater's session once the audit and browser tests pass
    publication: pack_publish.Publication | None = None
    repair: pack_repair.Repair = Field(default_factory=pack_repair.Repair)
    next: Action = "audit"
