"""Delivery's settings (§3.13, R3, TD-52): global with per-project overrides, resolved field by field.

A layer leaves a field at ``None`` to inherit it: project, else global, else the built-in default. Any other
value overrides, including ``[]`` and ``False``. Only model, effort and context are applied today (TD-27); the other
fields are stored for the config page and stay inactive until routing, visibility and capture use them (TD-50).
"""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field, field_validator

from owlbear_delivery_next.models import Context, Effort, Record, Role
from owlbear_delivery_next.preparation import DataPermissions, Preparation
from owlbear_delivery_next.profile_record import named
from owlbear_delivery_next.roles import DEFAULTS
from owlbear_delivery_next.visual_records import DesignFailures  # noqa: TC001 - pydantic resolves it at runtime

CONFIG_FORMAT = 2  # format 2 replaced the seed command by declared preparation options (TD-96)
type RuntimeName = Literal["sdk", "window"]
type Category = Literal["browser"]
type Source = Literal["default", "global", "project"]
WIDTHS = (1280, 2400)  # the allowed screenshot width range (R7)
DEFAULT_WIDTHS = [1280, 1920, 2400]


class Agent(Record):
    """One agent's settings in a layer; ``None`` inherits."""

    model_config = ConfigDict(extra="forbid", strict=True)

    model: str | None = None
    effort: Effort | None = None
    context: Context | None = None
    runtime: RuntimeName | None = None
    visible: bool | None = None  # the agent "needs visibility" (TD-35)
    categories: list[Category] | None = None  # extra tool categories beyond the baseline (R5)

    @field_validator("model")
    @classmethod
    def _named(cls, v: str | None) -> str | None:
        return None if v is None else named(v)


class Layer(Record):
    """A project's overrides; also the base of the global layer."""

    model_config = ConfigDict(extra="forbid", strict=True)

    format: int = CONFIG_FORMAT
    agents: dict[Role, Agent] = Field(default_factory=dict)
    runtimes: dict[RuntimeName, bool] = Field(default_factory=dict)  # a runtime switched off or on
    widths: list[int] | None = None
    preparations: list[Preparation] | None = None  # TD-96: the project's test-copy options, owner-declared
    data: DataPermissions | None = None  # TD-96: the owner's standing permissions for those test copies
    design_failures: DesignFailures | None = None  # TD-78: a design judge's fail goes back, or to the owner

    @field_validator("format")
    @classmethod
    def _current(cls, v: int) -> int:
        if v != CONFIG_FORMAT:
            raise ValueError(f"a layer is written in format {CONFIG_FORMAT}")  # noqa: EM102, TRY003
        return v

    @field_validator("widths")
    @classmethod
    def _widths(cls, v: list[int] | None) -> list[int] | None:
        if v is not None and (not v or any(not WIDTHS[0] <= w <= WIDTHS[1] for w in v)):
            raise ValueError(f"widths must be a non-empty list, each {WIDTHS[0]} to {WIDTHS[1]}")  # noqa: EM102, TRY003
        return v

    @field_validator("preparations")
    @classmethod
    def _distinct(cls, v: list[Preparation] | None) -> list[Preparation] | None:
        if v is not None and len({o.id for o in v}) < len(v):
            raise ValueError("preparation option ids must be distinct")  # noqa: EM101, TRY003
        return v


class GlobalLayer(Layer):
    """The global settings; the visibility switch is global only (TD-35), test preparation per project (TD-96)."""

    visible: bool | None = None

    @field_validator("preparations", "data")
    @classmethod
    def _project_only(cls, v: object) -> object:
        if v is not None:
            raise ValueError("test preparation is a project setting")  # noqa: EM101, TRY003
        return v


class Effective(Record):
    """One agent's resolved settings."""

    model: str
    effort: Effort
    context: Context
    runtime: RuntimeName
    visible: bool
    categories: list[Category]


class Settings(Record):
    """Every setting resolved, with the layer each value came from, keyed ``agents.<role>.<field>``."""

    visible: bool
    agents: dict[Role, Effective]
    runtimes: dict[RuntimeName, bool]
    widths: list[int]
    preparations: list[Preparation] = Field(default_factory=list)
    data: DataPermissions = Field(default_factory=DataPermissions)
    design_failures: DesignFailures = "ask"
    sources: dict[str, Source]


def _defaults() -> GlobalLayer:
    agents = {
        role: Agent(model=rm.model, effort=rm.effort, context="default", runtime="sdk", visible=False, categories=[])
        for role, rm in DEFAULTS.items()
    }
    return GlobalLayer(visible=False, agents=agents, runtimes={"sdk": True, "window": True}, widths=DEFAULT_WIDTHS)


def _pick(key: str, sources: dict[str, Source], *values: tuple[Source, object]) -> object:
    """The first value that is not ``None``, from the project down to the default; records its source."""
    for source, value in values:
        if value is not None:
            sources[key] = source
            return value
    msg = f"no default for {key}"
    raise KeyError(msg)


def resolve(glob: GlobalLayer | None, project: Layer) -> Settings:
    """Resolve each field on its own: project, else global, else the built-in default."""
    base, glob, sources = _defaults(), glob or GlobalLayer(), dict[str, Source]()
    agents: dict[Role, Effective] = {}
    for role, default in base.agents.items():
        mine, theirs = project.agents.get(role) or Agent(), glob.agents.get(role) or Agent()
        agents[role] = Effective.model_validate(
            {
                name: _pick(
                    f"agents.{role}.{name}",
                    sources,
                    ("project", getattr(mine, name)),
                    ("global", getattr(theirs, name)),
                    ("default", getattr(default, name)),
                )
                for name in Effective.model_fields
            }
        )
    runtimes = {
        name: bool(
            _pick(
                f"runtimes.{name}",
                sources,
                ("project", project.runtimes.get(name)),
                ("global", glob.runtimes.get(name)),
                ("default", on),
            )
        )
        for name, on in base.runtimes.items()
    }
    widths = _pick("widths", sources, ("project", project.widths), ("global", glob.widths), ("default", base.widths))
    visible = _pick("visible", sources, ("global", glob.visible), ("default", base.visible))
    prep = _pick("preparations", sources, ("project", project.preparations), ("default", []))
    data = _pick("data", sources, ("project", project.data), ("default", DataPermissions()))
    design = _pick(
        "design_failures",
        sources,
        ("project", project.design_failures),
        ("global", glob.design_failures),
        ("default", "ask"),  # autonomous default (TD-78)
    )
    return Settings(
        visible=visible,
        agents=agents,
        runtimes=runtimes,
        widths=widths,
        preparations=prep,
        data=data,
        design_failures=design,
        sources=sources,
    )
