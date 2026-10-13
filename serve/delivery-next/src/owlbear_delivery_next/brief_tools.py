"""The owner chat's brief tool: one fixed draft schema and the checks its schema cannot express (D4 §3.3, T3-T5)."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import Field

from owlbear_delivery_next import evidence
from owlbear_delivery_next.models import VISUAL
from owlbear_delivery_next.tools import Args, bounded, relative

type Criterion = Annotated[str, Field(min_length=10, max_length=500)]
NAME = r"^[a-z0-9][a-z0-9-]{0,39}$"


class PersonCheckDraft(Args):
    """One check only the owner can perform, done after the PR's CI passes."""

    name: str = Field(pattern=NAME, description="Short id of the check", examples=["preview"])
    steps: list[str] = bounded(10, "What the owner does, step by step", ["Open the preview page"])
    expect: str = bounded(300, "What the owner should see", "The page shows 'Hallo, Ada!'")
    visual: bool = Field(default=False, description="Whether the owner judges how the UI looks", examples=[True])


class VisualStateDraft(Args):
    """One page state the visual check renders and a reviewer judges from screenshots."""

    name: str = Field(pattern=NAME, description="Short id of the state", examples=["home"])
    path: str = Field(pattern=r"^/\S{0,199}$", description="URL path under the preview root", examples=["/settings"])
    expect: str = bounded(300, "What the rendered page must show", "The greeting is centred and readable")


class VisualStepDraft(Args):
    """One click or typing step before a state's screenshot, in order; runs only on the project's seeded data."""

    state: str = Field(pattern=NAME, description="Name of the state this step belongs to", examples=["search"])
    do: Literal["click", "type"] = Field(description="click a button or link, or type into a field", examples=["type"])
    target: str = bounded(120, "The control's visible name or the field's label, exactly as shown", "Search")
    text: str = Field(default="", max_length=300, description="What to type; empty for a click", examples=["Ada"])


STEPS = 10  # steps per state, so one state stays one short interaction


class VisualDraft(Args):
    """``save_visual_check``: set a shaping Change's UI flag, page states and their steps as a new brief version."""

    change: str = Field(pattern=r"^c\d{1,4}$", description="Handle of the Change", examples=["c3"])
    ui: bool = Field(description="Whether the Change changes what a page shows", examples=[True])
    states: list[VisualStateDraft] = Field(
        default_factory=list,
        max_length=6,
        description="Page states Delivery renders and a reviewer judges",
        examples=[[{"name": "search", "path": "/", "expect": "The results list shows Ada"}]],
    )
    steps: list[VisualStepDraft] = Field(
        default_factory=list,
        max_length=30,
        description="Clicks and typing before a state's screenshot, in order; needs the project's seed command",
        examples=[[{"state": "search", "do": "type", "target": "Search", "text": "Ada"}]],
    )


class BriefDraft(Args):
    """``save_brief``: create or revise one Change's brief draft; the host returns its handle or field errors."""

    change: str = Field(
        default="",
        pattern=r"^(c\d{1,4})?$",
        description="Handle of the Change to revise; empty for new",
        examples=["c3"],
    )
    title: str = bounded(100, "Short title of the Change", "Add a farewell function")
    outcome: str = bounded(2000, "What the owner has when it is done, in a few sentences", "farewell(name) exists", 20)
    criteria: list[Criterion] = bounded(
        10, "Acceptance criteria, each checkable by a test or command", ["farewell('Ada') returns 'Bye, Ada!'"]
    )
    scope: list[str] = bounded(20, "Repository-relative paths or directories the Change may touch", ["packages/app"])
    person_checks: list[PersonCheckDraft] = Field(
        default_factory=list,
        max_length=5,
        description="Checks only the owner can perform; empty when tests prove every criterion",
        examples=[[{"name": "preview", "steps": ["Open the preview"], "expect": "The greeting shows"}]],
    )
    ui: bool = Field(default=False, description="Whether the Change changes what a page shows", examples=[True])
    visual: list[VisualStateDraft] = Field(
        default_factory=list,
        max_length=6,
        description="Page states Delivery renders and a reviewer judges; required for a UI Change without "
        "a person-only check",
        examples=[[{"name": "home", "path": "/", "expect": "The greeting is centred"}]],
    )
    steps: list[VisualStepDraft] = Field(
        default_factory=list,
        max_length=30,
        description="Clicks and typing before a state's screenshot, in order",
        examples=[[{"state": "search", "do": "type", "target": "Search", "text": "Ada"}]],
    )


def _steps(brief: BriefDraft) -> list[str]:
    """Each step names a state of the brief, typing has text to type, and no state takes more than ``STEPS``."""
    names = {v.name for v in brief.visual}
    errors = [
        f"steps[{i}].state: {s.state} is not a state of this brief - use one of {sorted(names) or 'the states'}"
        for i, s in enumerate(brief.steps)
        if s.state not in names
    ]
    errors += [
        f'steps[{i}].text: empty - say what to type into "{s.target}"'
        for i, s in enumerate(brief.steps)
        if s.do == "type" and not s.text
    ]
    counts = {n: sum(s.state == n for s in brief.steps) for n in names}
    return errors + [f"steps: state {n} has {k} steps, over {STEPS}" for n, k in sorted(counts.items()) if k > STEPS]


def check_brief(brief: BriefDraft) -> list[str]:
    """Return field errors the schema cannot express: paths outside the repository, repeated entries."""
    errors = [
        f'scope[{i}]: {p} is not repository-relative - e.g. "packages/app"'
        for i, p in enumerate(brief.scope)
        if not relative(p)
    ]
    if len({c.strip().lower() for c in brief.criteria}) < len(brief.criteria):
        errors.append("criteria: repeated criterion - state each one once")
    if len({p.name for p in brief.person_checks}) < len(brief.person_checks):
        errors.append("person_checks: names repeat - give each check its own name")
    errors += [
        f'person_checks[{i}].name: "{VISUAL}" is reserved for the visual check - choose another name'
        for i, p in enumerate(brief.person_checks)
        if p.name == VISUAL
    ]
    if len({v.name for v in brief.visual}) < len(brief.visual):
        errors.append("visual: names repeat - give each state its own name")
    errors += [
        f'visual[{i}].path: {v.path} must stay under the preview root - e.g. "/settings"'
        for i, v in enumerate(brief.visual)
        if v.path.startswith("//") or ".." in PurePosixPath(v.path.split("?")[0]).parts
    ]
    person = any(p.visual for p in brief.person_checks)
    if evidence.need(ui=brief.ui, states=bool(brief.visual), person=person) == "unmet":
        errors.append(
            'visual: empty for a UI Change - add a state, e.g. {"name": "home", "path": "/", "expect": "..."}, '
            "or a person-only check with visual: true"
        )
    return errors + _steps(brief)
