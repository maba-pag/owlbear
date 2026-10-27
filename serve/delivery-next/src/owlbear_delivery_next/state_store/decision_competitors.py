"""Which in-force successors compete with a decision just written, so a save flags them before any of them is active."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_decisions import LinkType
from owlbear_decisions.snapshot import CONFLICT

if TYPE_CHECKING:
    from owlbear_decisions import Decision, Entry, Finding

SUCCEEDS = (LinkType.REPLACES, LinkType.PROMOTED_FROM)  # the links that make a successor (TD-426)


def competitors(found: tuple[dict[str, Entry], list[Finding]], written: Decision) -> list[Entry]:
    """The unflagged in-force successors competing with *written*, or with it for what it replaces or promotes."""
    by_id, findings = found
    touched = {written.id, *(link.target for link in written.links if link.type in SUCCEEDS)}
    ids = {f.involves[0] for f in findings if f.rule == CONFLICT and touched.intersection(f.involves[1:])}
    return [e for i in sorted(ids) if (e := by_id.get(i)) is not None and not e.decision.conflict]
