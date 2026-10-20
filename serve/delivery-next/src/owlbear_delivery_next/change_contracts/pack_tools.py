"""The design pack challenger's result (TD-194): its verdict, with one judgement for each file the updater changed."""

from __future__ import annotations

from collections import Counter
from typing import Literal

from pydantic import Field

from owlbear_delivery_next.change_contracts import tools


class Change(tools.Args):
    """Your judgement of one file the updater changed: whether the upgrade needs the change."""

    path: str = tools.bounded(200, "The file's path as your message lists it", "skills/owlbear-design/SKILL.md")
    needed: Literal["yes", "no", "unsure"] = Field(
        description="yes if the upgrade needs the change; no if not (raise a finding to undo it); unsure if only the "
        "owner can decide",
        examples=["yes"],
    )
    what: str = tools.bounded(300, "What changed, in one line", "renamed the glow rule to match upstream")
    suspicious: str = tools.bounded(300, "Why the change may not be needed by the upgrade, or none", "none")


class PackReview(tools.ReviewResult):
    """``submit_result`` for a full round of the design pack challenger."""

    changes: list[Change] = Field(
        default_factory=list,
        max_length=60,
        description="Exactly one entry for each file your message lists as changed by the updater",
        examples=[
            [{"path": "golden/expected.json", "needed": "yes", "what": "glow rule renamed", "suspicious": "none"}]
        ],
    )


REVIEW = tools.Spec(
    "submit_result", "Submit your verdict once, with one judgement per changed file.", PackReview, "result"
)


def check(result: PackReview, changed: tuple[str, ...]) -> list[str]:
    """Errors of ``changes``: one entry for each listed path, none missing, repeated or unlisted."""
    seen = Counter(c.path for c in result.changes)
    missing = [p for p in changed if p not in seen]
    extra = sorted(p for p in seen if p not in changed)
    twice = sorted(p for p, n in seen.items() if n > 1)
    errors = [f"changes: no entry for {', '.join(missing)}"] if missing else []
    errors += [f"changes: {', '.join(extra)} is not listed as changed"] if extra else []
    return errors + ([f"changes: {', '.join(twice)} answered more than once"] if twice else [])
