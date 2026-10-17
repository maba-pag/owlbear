"""The design judge's result tools (TD-78, design skill research §3.5 slice 5): a first look, then a final verdict.

Its images come in blind pairs, ``<state>-<width>-A.png`` and ``-B.png``, in an order only Delivery knows; a state
without a comparable "before" comes as ``-A.png`` alone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import Field

from owlbear_delivery_next.tools import FIRST_LOOK, SCAN_DESIGN, Args, Spec, bounded

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery_next.tools import Worktree

SERIOUS = frozenset({"P0", "P1"})


class DesignFinding(Args):
    """One design problem in one image, with the rule it breaks."""

    image: str = bounded(80, "The image it is seen in", "home-1280-A.png")
    problem: str = bounded(500, "What is wrong and why it matters", "Card padding is 4px, cramped against its border")
    rule: str = bounded(120, "The owlbear-interface-design section or detector rule id it breaks", "Layout & Space")
    severity: Literal["P0", "P1", "P2", "P3"] = Field(
        description="P0 blocks the task, P1 a user would ask for help, P2 an annoyance, P3 polish", examples=["P2"]
    )


class Preference(Args):
    """Which image of one blind pair is better, and why."""

    pair: str = bounded(60, "The pair's name: its image names without -A.png or -B.png", "home-1280")
    better: Literal["A", "B", "equal"] = Field(description="The better image, or equal", examples=["A"])
    why: str = bounded(300, "The rule or principle that decides it", "B's hierarchy puts the action first")


class DesignLook(Args):
    """``submit_first_look``: the design judge's verdict from the images alone."""

    verdict: Literal["pass", "fail", "unsure"] = Field(
        description="fail: an image has a P0 or P1 problem or misses an owner criterion, or one image of a pair is "
        "clearly worse on a cited rule; unsure: only the owner can decide; pass otherwise. Delivery maps A and B "
        "back and decides what the Change did",
        examples=["pass"],
    )
    findings: list[DesignFinding] = Field(default_factory=list, max_length=30, description="Each design problem")
    preferences: list[Preference] = Field(
        default_factory=list,
        max_length=40,
        description="One per blind pair",
        examples=[[{"pair": "home-1280", "better": "equal", "why": "Same layout and type"}]],
    )
    doubt: str = Field(
        default="",
        max_length=500,
        description="For unsure: what only the owner can decide; empty otherwise",
        examples=["Is the brief's red meant to override the palette?"],
    )
    covered_paths: list[str] = Field(
        default_factory=list,
        max_length=80,
        description="Every image name you looked at",
        examples=[["home-1280-A.png"]],
    )


class DesignResult(DesignLook):
    """``submit_result`` for the design judge: the final verdict, after the detector's findings."""

    agreed: list[str] = Field(
        default_factory=list,
        max_length=60,
        description="Detector rule ids your findings share",
        examples=[["side-tab"]],
    )
    false_positives: list[str] = Field(
        default_factory=list,
        max_length=60,
        description="Detector rule ids that do not apply here, for example a font the brief names",
        examples=[["overused-font"]],
    )


FIRST = Spec(
    FIRST_LOOK,
    "Submit your own verdict from the images alone. Your turn goes on: the reply carries the detector's findings.",
    DesignLook,
    "result",
)
FINAL = Spec("submit_result", "Submit your final verdict once, after the detector's findings.", DesignResult, "result")


class ScanDesign(Args):
    """``scan_design``: UI source files of the worktree, offline."""

    paths: list[str] = Field(
        max_length=40, description="Repository-relative UI files to scan", examples=[["web/app.css"]]
    )


SCAN = Spec(
    SCAN_DESIGN,
    "Scan UI source files you changed with Delivery's design detector. Its findings are hints to weigh against "
    "owlbear-interface-design, never a verdict; the visual check scans the rendered pages. Your turn goes on.",
    ScanDesign,
    "result",
)


def pairs(images: Sequence[str]) -> list[str]:
    """The blind pairs among *images*: each stem that has both an A and a B image."""
    stems = {i.removesuffix("-A.png") for i in images if i.endswith("-A.png")}
    return sorted(s for s in stems if f"{s}-B.png" in images)


def check(look: DesignLook, tree: Worktree) -> list[str]:
    """Field errors of a verdict that does not match its findings, skips an image, or leaves a pair unjudged."""
    images, errors = tree.changed, []
    if look.verdict == "fail" and not look.findings and all(p.better == "equal" for p in look.preferences):
        errors.append("findings: empty - a fail names each problem, or a pair whose one image is clearly worse")
    if look.verdict == "pass" and any(f.severity in SERIOUS for f in look.findings):
        errors.append("verdict: pass with a P0 or P1 problem - use fail")
    if look.verdict == "unsure" and not look.doubt:
        errors.append("doubt: empty - an unsure verdict says what only the owner can decide")
    if missing := sorted(set(images) - set(look.covered_paths)):
        errors.append(f"covered_paths: missing {', '.join(missing[:5])} - look at every image and list it")
    errors += [f"findings: {f.image} is not one of your images" for f in look.findings if f.image not in images]
    judged = [p.pair for p in look.preferences]
    if sorted(judged) != pairs(images):
        errors.append(f"preferences: name each pair once - {', '.join(pairs(images)) or 'none'}")
    return errors
