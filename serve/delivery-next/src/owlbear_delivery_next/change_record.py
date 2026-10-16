"""A finished Change's record in the project's shared folder (TD-148): brief, decisions, outcome, PR and spend.

Only finished Changes leave one; live state stays in the clone's store. The file is named after the second the brief
was approved and the slug, so a cleanup that runs again rewrites the same record and two clones' records stay apart.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from owlbear_delivery_next.data_repo import DataRepoError
from owlbear_delivery_next.storage_io import atomic_write

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.github.provider import PullRequest
    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.store import Store

BRIEF = {"version", "title", "outcome", "scope", "non_goals", "decisions", "criteria", "ui", "visual"}


def save(store: Store, c: Change, pr: PullRequest | None, now: datetime) -> str:
    """Write and publish the record of *c*; what the owner should know when that fails, else nothing.

    A Change never approved leaves none: it has no approved brief, and no stable name for a record.
    """
    if not store.shared or c.brief.approved_at is None:
        return ""
    brief = c.brief.approved[-1] if c.brief.approved else c.brief
    outcome = "merged" if pr and pr.merged else "abandoned"
    record = {
        "slug": c.slug,
        "handle": c.handle,
        "finished": now.isoformat(timespec="seconds"),
        "outcome": outcome,
        "pr": {"number": pr.number, "url": pr.url, "merge_commit": pr.merge_commit_sha} if pr else None,
        "brief": brief.model_dump(mode="json", include=BRIEF),
        "decisions": [d.model_dump(mode="json", include={"text", "origin", "at"}) for d in c.decisions],
        "spend": c.spend.model_dump(mode="json", exclude={"last"}),
    }
    path = store.shared.root / store.name / "changes" / f"{c.brief.approved_at:%Y%m%d-%H%M%S}-{c.slug}.json"
    try:
        with store.shared.locked():
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(path, json.dumps(record, indent=1) + "\n")
            return store.shared.publish(path, f"changes: {store.name}: {c.slug} {outcome}")
    except (DataRepoError, OSError) as exc:
        return f"the record of {c.slug} was not saved: {exc}"[:300]
