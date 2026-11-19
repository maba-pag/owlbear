"""The quality judge's flat, host-checked verdict contract."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Literal

from pydantic import Field

from owlbear_delivery_next.change_contracts import tools

if TYPE_CHECKING:
    from pathlib import Path


class ExceptionVerdict(tools.Args):
    """One verdict for a host-issued exception id."""

    id: str = tools.bounded(10, "Host-issued item id, 1-10 characters", "e1")
    verdict: Literal["accepted", "refused"] = Field(
        description="Exactly one verdict: accepted for a legitimate exception, otherwise refused", examples=["accepted"]
    )
    reason: str = tools.bounded(
        2000, "Evidence and reason for this verdict, 1-2000 characters", "The tool cannot see the generated binding."
    )


class ExceptionVerdicts(tools.Args):
    """Exactly one judgment for every supplied item."""

    verdicts: list[ExceptionVerdict] = tools.bounded(
        60,
        "Exactly one verdict per supplied id, 1-60 items, with no duplicates or unknown ids",
        [{"id": "e1", "verdict": "accepted", "reason": "The tool cannot see the generated binding."}],
    )


HELPER = tools.Spec(
    "judge_exceptions",
    "Judge this Change's new suppressions, with no arguments. Commit first: the host reads commits, not working "
    "edits. Your turn continues with each verdict and reason or a failed answer. Fix refused suppressions in code "
    "or appeal once with request_approval. Example: judge_exceptions().",
    tools.Args,
    "result",
)

SUBMIT = tools.Spec(
    "submit_result", "Submit exactly one verdict per host-issued exception id.", ExceptionVerdicts, "result"
)


def check(args: ExceptionVerdicts, root: Path) -> list[str]:
    """Enforce complete, exact coverage while the judge can still correct its result."""
    items = json.loads((root / "exceptions-context.json").read_text(encoding="utf-8"))["items"]
    expected, received = {item["id"] for item in items}, [v.id for v in args.verdicts]
    if set(received) != expected or len(received) != len(expected):
        return [f"verdicts.id: give exactly one verdict for each of {sorted(expected)}; received {received}"]
    return []
