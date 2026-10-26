"""A finished Change's record in the project's shared folder (TD-148): brief, decisions, outcome, PR and spend.

Only finished Changes leave one; live state stays in the clone's store. The file is named after the second the brief
was approved and the slug, so a cleanup that runs again rewrites the same record and two clones' records stay apart.
Its decisions become decision files in the same commit (TD-419, `decision_archive`).
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import storage_io
from owlbear_delivery_next.local_system.data_repo import SAVE_SECONDS, DataRepoError
from owlbear_delivery_next.state_store import decision_archive, decision_batch, decision_sync, decision_transaction
from owlbear_delivery_next.state_store.decision_store import DecisionsUnavailable

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.github.provider import PullRequest
    from owlbear_delivery_next.state_store.store import Store

BRIEF = {"version", "title", "outcome", "scope", "non_goals", "decisions", "criteria", "ui", "visual"}


def save(
    store: Store,
    c: Change,
    pr: PullRequest | None,
    now: datetime,
    *,
    observed: PullRequest | None = None,
) -> str:
    """Write and publish the record of *c* and its decisions; what the owner should know when that fails, else nothing.

    *pr* is the proven intended delivery. *observed* retains a different terminal PR without delivery credit.
    A Change never approved leaves none: it has no approved brief, and no stable name for a record.
    """
    if not store.shared or c.brief.approved_at is None:
        return ""
    brief = c.brief.approved[-1] if c.brief.approved else c.brief
    outcome = "merged" if pr and pr.merged else "unchanged" if c.tests and c.tests.unchanged else "abandoned"
    record = {
        "slug": c.slug,
        "handle": c.handle,
        "finished": now.isoformat(timespec="seconds"),
        "outcome": outcome,
        "pr": {"number": pr.number, "url": pr.url, "merge_commit": pr.merge_commit_sha} if pr else None,
        "brief": brief.model_dump(mode="json", include=BRIEF),
        "decisions": [d.model_dump(mode="json", include={"text", "origin", "at"}) for d in c.decisions],
        "decisions_applied": sorted(c.decisions_baseline.said) if c.decisions_baseline else [],  # its impact (TD-428)
        "decisions_picked": {d.id: d.revision for d in brief.picked.decisions} if brief.picked else {},  # TD-459
        "spend": c.spend.model_dump(mode="json", exclude={"last"}),
        "tool_use": c.tool_use.model_dump(mode="json"),
    }
    if observed is not None:
        record["observed_pr"] = {
            "repository": observed.repository,
            "number": observed.number,
            "url": observed.url,
            "target": observed.base_branch,
            "branch": observed.head_branch,
            "merge_commit": observed.merge_commit_sha,
        }
    stem = f"{c.brief.approved_at:%Y%m%d-%H%M%S}-{c.slug}"
    path = store.shared.root / store.name / decision_archive.CHANGES / f"{stem}.json"
    text = json.dumps(record, indent=1) + "\n"
    message = f"changes: {store.name}: {c.slug} {outcome}"
    try:
        with store.shared.locked():
            decision_transaction.guard(store.shared)
            head, behind = decision_sync.prepare(store.shared, time.monotonic() + SAVE_SECONDS)
            if not head:
                return f"the record of {c.slug} was not saved: {behind}"[:300]
            planned, problems = decision_archive.plan(store.shared.root, store.name, c, stem, outcome)
            if problems:  # refused before any journal, folder or file: the record stays out with its decisions
                refusal = f"the record of {c.slug} was not saved; " + "; ".join(
                    [f"no decision of {c.slug} was archived", *problems]
                )
                return "; ".join(filter(None, [behind, refusal]))[:1000]
            storage_io.make_dirs(path.parent)
            writes = decision_archive.batch_files(planned)

            def publish(head: str, fence: Callable[[], None]) -> decision_transaction.Step:
                files, left = decision_archive.write_plan(planned, [], c.slug, fence, store.shared.root)
                if left:  # a decision refused: the record commits with none of the batch
                    return decision_transaction.Step(
                        f"the record of {c.slug} was not saved; " + "; ".join(left), refused=True
                    )
                decision_batch.replace_file(path, text.encode("utf-8"), fence, store.shared.root)
                sent = decision_sync.publish(
                    store.shared, [path, *files], message, time.monotonic() + SAVE_SECONDS, head
                )
                notice = "; ".join(filter(None, [sent.notice, *left]))
                return decision_transaction.Step(notice, unknown=sent.stale or sent.ambiguous, refused=sent.uncommitted)

            notice = decision_transaction.transaction(
                store.shared, store.name, message, [(path, text.encode("utf-8")), *writes], publish, head
            )
    except (DataRepoError, OSError, DecisionsUnavailable) as exc:
        return f"the record of {c.slug} was not saved: {exc}"[:300]
    return "; ".join(filter(None, [behind, notice]))[:1000]
