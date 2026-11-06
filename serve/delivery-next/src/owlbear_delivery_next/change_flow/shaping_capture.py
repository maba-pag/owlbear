"""The capture of a shaping draft's current pages (D-01M61V2GR0C6JV2R6KJ0WR4PNB, D-01M6Q56RXK85C5T4AG7R051X6N).

A saved UI draft with states and a render recipe asks for one capture of the target's pages. It renders on a declared
test preparation, and the shaper and the owner write the expectations against its pictures; approval waits until it
has ended, with pictures or with reasons. Its key holds only what the pictures show: an expectation edit, or a moving
target, captures nothing again. A capture that left a state without pictures is asked for again by the next save.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.visual_records import ShapingCapture

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Brief, Change

CAPTURING = "its current pages are still being captured"


def key(b: Brief) -> str:
    """What the draft's pictures show: its recipe, preparation option, and each state's name, path and steps."""
    shown = {
        "recipe": b.recipe.model_dump() if b.recipe else None,
        "preparation": b.preparation,
        "states": [[s.name, s.path, [x.model_dump() for x in s.steps]] for s in b.visual],
    }
    return hashlib.sha256(json.dumps(shown, sort_keys=True).encode()).hexdigest()


def needed(b: Brief) -> bool:
    """Whether a draft's pages are captured in shaping: it changes a page, has states and a recipe."""
    return b.ui and bool(b.visual) and b.recipe is not None


def requested(c: Change) -> ShapingCapture | None:
    """The capture a just-saved draft has: its own if it holds, else a new request; None when it needs none."""
    b, s = c.brief, c.shaped
    if not needed(b):
        return None
    k = key(b)
    if s is not None and s.key == k and (s.result is None or not s.result.findings):
        return s  # still capturing, or captured whole: the same pictures
    return ShapingCapture(key=k)


def starting(b: Brief) -> list[str]:
    """The preparer's starting recipe: the one the brief's current pages were captured with, if any."""
    if (r := b.recipe) is None:
        return []
    said = (
        f"Start from the recipe the brief's current pages were captured with: command `{r.command}`, directory "
        f"`{r.directory}`, ready_url `{r.ready_url}`. Verify it in this worktree; return it, or adjusted if this "
        "Change renamed what it runs, keeping `{port}`."
    )
    return [said]


def owed(c: Change) -> bool:
    """Whether a runner captures the draft's pages now: requested while the Change is shaped."""
    return c.step.kind == StepKind.SHAPE and not c.finished_at and c.shaped is not None and c.shaped.result is None


def waiting(c: Change) -> str:
    """Why approval waits for the capture of the current draft, or ""; a capture that ended, either way, holds none."""
    b, s = c.brief, c.shaped
    if not needed(b):
        return ""
    return CAPTURING if s is None or s.key != key(b) or s.result is None else ""
