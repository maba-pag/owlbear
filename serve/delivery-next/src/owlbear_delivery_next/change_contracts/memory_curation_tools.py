"""The memory curator's one Delivery tool (item 5 slice 4, TD-292, TD-400): its report on each entry it judged."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from owlbear_delivery_next.change_contracts import tools

type Action = Literal["promoted", "edited", "pruned", "made global", "kept", "skipped"]


class Judged(tools.Args):
    """One entry the curator judged: what it did, its confidence in that, and why it skipped one."""

    entry_id: str = tools.bounded(
        64, "The entry's id as list_memories shows it", "0b5c6d1e-1234-4abc-8def-1234567890ab"
    )
    action: Action = Field(description="What you did to it; skipped when your confidence was below the threshold")
    confidence: int = Field(ge=0, le=100, description="Your confidence, in percent, in everything you would do to it")
    reason: str = Field(
        default="", max_length=300, description="Why you skipped it, or which side of a conflict stands; else empty"
    )


class MemoryCurationResult(tools.Args):
    """``submit_result`` for one automatic memory curation run."""

    entries: list[Judged] = Field(max_length=500, description="Every entry you judged, once each; empty for none")
    summary: str = tools.bounded(300, "One line: what you promoted, pruned, made global and skipped", "2 promoted")


SUBMIT = tools.Spec(
    "submit_result", "Submit your report once, after committing your changes.", MemoryCurationResult, "result"
)
