"""TD-96 test preparation: the options a project declares, the owner's data permissions, and their validation.

A check never runs on live: it runs on a test copy that one declared option prepares. A live copy is exported and
masked once into a frozen snapshot, which is restored into the isolated test environment before each capture; test
data is seeded on top or alone. The owner's standing permissions bound which options may run (TD-102 restrictions).
"""

from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Literal

from pydantic import ConfigDict, Field, ValidationInfo, field_validator, model_validator

from owlbear_delivery_next import tools
from owlbear_delivery_next.models import Record

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

type Kind = Literal["live-copy", "live-copy-plus-data", "data-only"]
LIVE: frozenset[str] = frozenset({"live-copy", "live-copy-plus-data"})
HELD: frozenset[str] = LIVE  # kinds refused until the owner releases them
HELD_REASON = (
    "live-copy preparation is held until the owner confirms how isolation from live is proven (review 2026-10-15)"
)
COMMAND_LIMIT = 300
SNAPSHOT = "OWLBEAR_SNAPSHOT"  # the snapshot folder every command of a live copy is given
VARIABLE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")


def _command(v: str, name: str) -> str:
    if v and not (len(v.strip()) <= COMMAND_LIMIT and shlex.split(v)):
        raise ValueError(f"{name} must be one command of 1 to {COMMAND_LIMIT} characters")  # noqa: EM102, TRY003
    return v


class Preparation(Record):
    """One declared way to prepare a check's test copy; every command runs without a shell in the worktree root."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,39}$")
    kind: Kind
    export: str = ""  # live copies: writes the live data into the folder $OWLBEAR_SNAPSHOT names
    masking: str = ""  # masks the exported snapshot in place, before it is frozen
    restore: str = ""  # loads the snapshot into the isolated test environment; data only: resets it
    seed: str = ""  # adds test data after the restore
    cleanup: str  # removes what the check created in the test environment; always runs at the end
    isolation: dict[str, str] = Field(default_factory=dict)  # variables pointing the app at test resources
    data_classes: list[str] = Field(default_factory=list)  # the kinds of data it copies, e.g. "customers"
    copies_keys: bool = False  # its export copies keys or secrets
    setup_globs: list[str] = Field(default_factory=list)  # test-system setup files the preparer may edit (TD-107)

    @field_validator("export", "masking", "restore", "seed", "cleanup")
    @classmethod
    def _one(cls, v: str, info: ValidationInfo) -> str:
        return _command(v, info.field_name or "command")

    @field_validator("isolation")
    @classmethod
    def _names(cls, v: dict[str, str]) -> dict[str, str]:
        if bad := [k for k in v if not VARIABLE.fullmatch(k) or k.startswith("OWLBEAR_")]:
            raise ValueError(f"isolation names environment variables; not {', '.join(bad)}")  # noqa: EM102, TRY003
        return v

    @field_validator("setup_globs")
    @classmethod
    def _inside(cls, v: list[str]) -> list[str]:
        if bad := [g for g in v if not tools.relative(g)]:
            raise ValueError(f"setup_globs must be repository-relative; not {', '.join(bad)}")  # noqa: EM102, TRY003
        return v

    @model_validator(mode="after")
    def _kind(self) -> Preparation:
        """Each kind names exactly the commands it runs."""
        live = self.kind in LIVE
        needs = {"cleanup": True, "export": live, "restore": live, "seed": self.kind != "live-copy"}
        if missing := [n for n, need in needs.items() if need and not getattr(self, n).strip()]:
            raise ValueError(f"a {self.kind} option needs {', '.join(missing)}")  # noqa: EM102, TRY003
        if not live and (self.export or self.masking or self.copies_keys):
            raise ValueError("a data-only option exports, masks and copies nothing")  # noqa: EM101, TRY003
        if self.kind == "live-copy" and self.seed:
            raise ValueError("a live-copy option adds no data; use live-copy-plus-data")  # noqa: EM101, TRY003
        if live and not self.data_classes:
            raise ValueError("a live copy names the data classes it copies")  # noqa: EM101, TRY003
        return self


class DataPermissions(Record):
    """The owner's standing permissions for this project's test copies; the defaults permit no live data."""

    model_config = ConfigDict(extra="forbid", strict=True)

    data_classes: list[str] = Field(default_factory=list)  # data classes a test copy may hold
    unmasked: list[str] = Field(default_factory=list)  # data classes a live copy may keep unmasked
    keys: bool = False  # whether keys or secrets may be copied
    isolation: list[str] = Field(default_factory=list)  # variables every option must point at test resources
    retention: Literal["delete", "keep"] = "delete"  # the snapshot after the check; keep: until the next export


def refusals(option: Preparation, rules: DataPermissions, live: Mapping[str, str]) -> list[str]:
    """Why the owner's permissions refuse *option*; *live* is the environment the app would otherwise read."""
    why = [HELD_REASON] if option.kind in HELD else []
    if denied := sorted(set(option.data_classes) - set(rules.data_classes)):
        why.append(f"data classes {', '.join(denied)} are not permitted")
    if option.copies_keys and not rules.keys:
        why.append("it copies keys or secrets, which are not permitted")
    if not option.isolation:
        why.append("it declares no isolation")
    if lacking := sorted(set(rules.isolation) - set(option.isolation)):
        why.append(f"its isolation lacks {', '.join(lacking)}")
    for name, value in sorted(option.isolation.items()):
        if not value.strip():
            why.append(f"its isolation {name} is empty")
        elif value == live.get(name):
            why.append(f"its isolation {name} equals the live value")
    if option.kind in LIVE and not option.masking and (bare := sorted(set(option.data_classes) - set(rules.unmasked))):
        why.append(f"it copies {', '.join(bare)} without masking")
    return why


def safe(options: Sequence[Preparation], rules: DataPermissions, live: Mapping[str, str]) -> list[Preparation]:
    """The declared options the permissions allow."""
    return [o for o in options if not refusals(o, rules, live)]


@dataclass(frozen=True)
class Preparing:
    """What a preparer's recipe is validated against: the declared options, permissions and the head it started at."""

    options: tuple[Preparation, ...] = ()
    rules: DataPermissions = field(default_factory=DataPermissions)
    head: str = ""  # HEAD when the session started; the preparer commits nothing
    found: tuple[str, ...] = ()  # uncommitted paths when it started: they stay, the preparer's own edits do not
    live: Mapping[str, str] = field(default_factory=lambda: dict(os.environ))

    def option(self, name: str) -> Preparation | None:
        """The declared option *name*."""
        return next((o for o in self.options if o.id == name), None)


def setup(path: str, globs: Sequence[str]) -> bool:
    """Whether *path* is a test-system setup file one of *globs* names (TD-107)."""
    return any(PurePosixPath(path).full_match(g) for g in globs)


def check(recipe: tools.CheckRecipe, tree: tools.Worktree, root: Path, ctx: Preparing) -> list[str]:
    """Field errors of a recipe: its option is declared and permitted, its edits are setup files, nothing committed."""
    ids = ", ".join(o.id for o in ctx.options)
    option = ctx.option(recipe.preparation)
    errors = []
    if ctx.head and tree.head != ctx.head:
        errors.append(
            f"changes: HEAD moved from {ctx.head[:12]}; you commit nothing - undo your commit and keep the setup "
            "edits uncommitted"
        )
    if not recipe.preparation and ctx.options:
        errors.append(f"preparation: empty - pick one of {ids}; a check never runs on live data")
    elif recipe.preparation and not ctx.options:
        errors.append("preparation: this project declares no preparation options - leave it empty")
    elif recipe.preparation and option is None:
        errors.append(f"preparation: {recipe.preparation} is not a declared option - use one of {ids}")
    elif option and (why := refusals(option, ctx.rules, ctx.live)):
        errors.append(f"preparation: {option.id} is not permitted ({'; '.join(why)}) - pick another or ask")
    if option and not recipe.reason.strip():
        errors.append("reason: empty - say why this option gives the check the data it needs")
    return errors + tools.check_recipe(recipe, tree, root, option.setup_globs if option else ())
