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


def ordered(rows: list[dict]) -> list[dict]:
    """A Change's verdicts for one identity as the gate counts them: acceptances cover copies first."""
    return sorted(rows, key=lambda row: row["verdict"] != "accepted")


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


def _one(item: dict) -> str:
    """One shown copy's identity, copy number and evidence, independent of line-number shifts."""
    text = json.dumps([item["identity"], item["copy"], item["directive"], item["code"]])
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def digest(items: list[dict]) -> str:
    """The shown copies, each by its own short digest, so an answer is known per suppression."""
    return "+".join(sorted(_one(i) for i in items))


def _answered(c: Change, option: str) -> set[str]:
    """The shown copies of every live answer of one kind to an appeal of this Change."""
    return {
        short
        for q in c.questions
        if q.cause and ":suppressions-" in q.cause and q.answer and q.answer.superseded_at is None
        if q.answer.option == option
        for short in q.cause.rpartition(":suppressions-")[2].split("+")
    }


def declined(c: Change, items: list[dict]) -> list[dict]:
    """Refused copies the owner already declined: a suppression is appealed once."""
    said = _answered(c, "decline")
    return [item for item in items if item["refusal"] and _one(item) in said]


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
                "directive": item.get("directive", ""),
                "replaces": [item["refusal"]["index"]] if item.get("refusal") else [],
            }
            for item in items
        ],
    )


def approved(c: Change, folder: Path, commit: str, items: list[dict]) -> list[dict]:
    """Consume only explicit, live Approve answers, each for exactly the copies its question showed."""
    said = _answered(c, "approve")
    covered = [item for item in items if item["refusal"] and _one(item) in said]
    if covered:
        accept(c, folder, commit, covered)
    return [item for item in items if item not in covered]


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
