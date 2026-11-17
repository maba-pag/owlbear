"""Change-scoped copy accounting and owner receipts for committed suppressions."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from owlbear_quality import ledger
from owlbear_quality.inspect import added

from owlbear_delivery_next.change_flow import worktree

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change


def _git(at: Path, args: list[str]) -> str:
    return worktree.git(at, *args)


def pending(c: Change, path: Path, folder: Path, span: tuple[str, str]) -> list[dict]:
    """One host-owned item for each added copy that this Change's acceptances do not cover."""
    found = []
    for addition in added(_git, path, *span):
        rows = ledger.counting(folder, addition.identity, scope=c.slug)
        accepted = sum(row["verdict"] == "accepted" for row in rows)
        refusals = [row for row in rows if row["verdict"] == "refused"]
        for n in range(max(0, addition.count - accepted)):
            place = addition.places[min(accepted + n, len(addition.places) - 1)]
            refusal = refusals[n] if n < len(refusals) else None
            found.append(
                {
                    "identity": addition.identity,
                    "copy": accepted + n + 1,
                    "place": f"{place.path}:{place.line}",
                    "places": [f"{p.path}:{p.line}" for p in addition.places],
                    "directive": place.directive,
                    "code": place.code,
                    "refusal": refusal,
                }
            )
    return found


def digest(items: list[dict]) -> str:
    """A shown set's identities, copy count and evidence, independent of line-number shifts."""
    text = json.dumps(sorted((i["identity"], i["copy"], i["directive"], i["code"]) for i in items))
    return hashlib.sha256(text.encode()).hexdigest() if items else ""


def accept(c: Change, folder: Path, commit: str, items: list[dict]) -> None:
    """Replace each shown refusal with an owner acceptance without erasing its history."""
    ledger.add(
        folder,
        [
            {
                "identity": item["identity"],
                "verdict": "accepted",
                "reason": "The owner approved this suppression in the shown change.",
                "by": "owner",
                "for": c.slug,
                "commit": commit,
                "place": item["place"],
                "replaces": [item["refusal"]["index"]] if item.get("refusal") else [],
            }
            for item in items
        ],
    )


def approved(c: Change, folder: Path, commit: str, items: list[dict]) -> list[dict]:
    """Consume only explicit, live Approve answers for the exact shown suppression set."""
    refused = [item for item in items if item["refusal"]]
    stamp = digest(refused)
    if stamp and any(
        q.cause
        and q.cause.endswith(f":suppressions-{stamp}")
        and q.answer
        and q.answer.option == "approve"
        and q.answer.superseded_at is None
        for q in c.questions
    ):
        accept(c, folder, commit, refused)
        return [item for item in items if not item["refusal"]]
    return items


def errors(items: list[dict]) -> list[str]:
    """One submit error, never a lint refusal, with every candidate place and complete refusal reason."""
    if not items:
        return []
    rows = [
        f"{', '.join(i['places'])}: {i['directive']}: "
        + (i["refusal"]["reason"] if i["refusal"] else "not yet judged for this Change")
        for i in items
    ]
    return [
        "suppressions: added copies need accepted verdicts for this Change. Commit, then call judge_exceptions. "
        "Fix a refused suppression in code or appeal once with request_approval.\n" + "\n".join(rows)
    ]
