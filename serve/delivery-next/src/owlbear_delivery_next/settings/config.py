"""Delivery's settings (§3.13, R3, TD-52): global with per-project overrides, resolved field by field.

A layer leaves a field at ``None`` to inherit it: project, else this machine, else global. Code ships no defaults
(the owner, 2026-10-23): a field no layer sets is unset, listed in ``Settings.missing`` and shown as an error on the
Settings page. While one is unset, or a layer can't be read, nothing starts for the project (``work_block``, #808); a
step already running that needs it refuses (``SettingsUnset``). Any other value overrides, including ``[]`` and
``False``. Only model, effort and context are applied today (TD-27); the other
fields are stored for the config page and stay inactive until their features use them (TD-50).
"""

from __future__ import annotations

from typing import Any, Literal, get_args

from pydantic import ConfigDict, Field, field_validator, model_validator

from owlbear_delivery_next.change_contracts.models import Context, Effort, Record, Role
from owlbear_delivery_next.change_contracts.preparation import DataPermissions, Preparation
from owlbear_delivery_next.change_contracts.profile_record import named
from owlbear_delivery_next.change_contracts.round_records import RoundPolicy
from owlbear_delivery_next.change_contracts.visual_records import (
    DesignFailures,  # noqa: TC001 - pydantic resolves it at runtime
)
from owlbear_delivery_next.github.provider import MergeMethod  # noqa: TC001 - pydantic resolves it at runtime
from owlbear_delivery_next.settings import improvement
from owlbear_delivery_next.settings.improvement import Spotter

CONFIG_FORMAT = 19  # 3 renamed the designer to design-judge (TD-169); 4 minutes; 5 PR labels; 6 subagents; 7 sessions;
# 8 the test reviewer and curator roles; 9 the watcher's role and switch; 10 no code defaults; 11 Global's machine part;
# 12 the watcher became the Spotter (role and settings), with the retro roles (2026-10-25);
# 13 the five unset-by-default preferences and their one-time import marker;
# 14 the Spotter's on/off switch and its four categories' actions replace its mode (2026-10-26);
# 15 no window runtime settings: its switches, visibility and tool categories go (2026-10-26);
# 16 credit limits per look and run replace the daily budgets, written into Global once (2026-10-27);
# 17 the user-config switches for Delivery steps (2026-10-27);
# 18 the machine's three update check intervals (D-01M63CCVRK8ZKFENY9F4A2K11A);
# 19 Copilot Memory in Delivery's sessions (D-01M69EBRBBW97001KZ43C0BJM1)
CARRIED_FORMAT = 10  # a Global layer below it has not had the built-in values carried in (``settings_carry.carry``)
ROLES: tuple[Role, ...] = get_args(Role.__value__)
type Source = Literal["default", "global", "machine", "project", "builder"]
type Channel = Literal["minor", "major"]  # every minor version, or major versions only (TD-300)
type Curate = Literal["off", "on", "paused"]  # an automatic curation trigger: off, on, or on even while paused
HOURS = 720  # the longest update check interval: 30 days
WIDTHS = (1280, 2400)  # the allowed screenshot width range (R7)
MINUTES = (1, 480)  # the allowed session time limit range (TD-286)
LABEL = 50  # GitHub's longest label name


class Agent(Record):
    """One agent's settings in a layer; ``None`` inherits."""

    model_config = ConfigDict(extra="forbid", strict=True)

    model: str | None = None
    effort: Effort | None = None
    context: Context | None = None
    max_rounds: int | None = None  # TD-209: the challenge loops of this role's work
    max_findings: int | None = None
    last_round_at: int | None = None
    ask_owner_at: int | None = None
    minutes: int | None = None  # TD-286: one session's total running time
    subagents: bool | None = None  # TD-374, TD-376: its sessions may start built-in subagents

    @field_validator("model")
    @classmethod
    def _named(cls, v: str | None) -> str | None:
        return None if v is None else named(v)

    @field_validator("minutes")
    @classmethod
    def _minutes(cls, v: int | None) -> int | None:
        if v is not None and not MINUTES[0] <= v <= MINUTES[1]:
            raise ValueError(f"minutes must be {MINUTES[0]} to {MINUTES[1]}")  # noqa: EM102, TRY003
        return v


class FinalReview(Record):
    """The final review's round values in a layer; ``None`` inherits, down to the builder's (TD-211)."""

    model_config = ConfigDict(extra="forbid", strict=True)

    max_rounds: int | None = None
    max_findings: int | None = None
    last_round_at: int | None = None
    ask_owner_at: int | None = None


class Prefs(Record):
    """The five merge, cleanup and polling preferences (R15); each layer may set any, none has a code default."""

    model_config = ConfigDict(extra="forbid", strict=True)

    merge_method: MergeMethod | None = Field(default=None, strict=False)  # the API sends the enum's value as text
    delete_remote_branch: bool | None = None
    ci_poll_seconds: int | None = None
    ci_start_window_seconds: int | None = None
    ask_before_merge: bool | None = None


PREF_KEYS: tuple[str, ...] = tuple(Prefs.model_fields)


class Layer(Record):
    """A project's overrides; also the base of the global layer."""

    model_config = ConfigDict(extra="forbid", strict=True)

    format: int = CONFIG_FORMAT
    prefs: Prefs | None = None  # R15: layered per field, project over machine over global; never a code default
    prefs_imported: bool = False  # R15: the legacy import filled this project layer; a retry never fills again
    roles_moved: bool = False  # the old profile's roles were merged in the same write; kept by every later write
    agents: dict[Role, Agent] = Field(default_factory=dict)
    widths: list[int] | None = None
    preparations: list[Preparation] | None = None  # TD-96: the project's test-copy options, owner-declared
    data: DataPermissions | None = None  # TD-96: the owner's standing permissions for those test copies
    design_failures: DesignFailures | None = None  # TD-78: a design judge's fail goes back, or to the owner
    final_review: FinalReview | None = None  # TD-211
    pr_labels: list[str] | None = None  # TD-308: on every PR OwlBear opens; a project's list replaces the global one
    pr_marker: bool | None = None  # TD-308: the "Opened by OwlBear Delivery" line, switched per project
    # D-01M5YE4P5317N1HWD0QN6N05E0: Delivery steps load the owner's own instructions and skills; no code default
    load_user_instructions: bool | None = None
    load_user_skills: bool | None = None
    load_user_memory: bool | None = None  # D-01M69EBRBBW97001KZ43C0BJM1: Copilot Memory in Delivery's sessions
    sessions: int | None = Field(default=None, ge=1)  # TD-336: agent sessions at once in a project, layered
    spotter: Spotter | None = None  # Improvement's Spotter (design §4); a project may set its own, e.g. switch it off

    @field_validator("format")
    @classmethod
    def _current(cls, v: int) -> int:
        if v != CONFIG_FORMAT:
            raise ValueError(f"a layer is written in format {CONFIG_FORMAT}")  # noqa: EM102, TRY003
        return v

    @field_validator("pr_labels")
    @classmethod
    def _labels(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and (len(set(v)) < len(v) or any(not 0 < len(x) <= LABEL or x != x.strip() for x in v)):
            msg = f"labels must be distinct, each 1 to {LABEL} characters without outer spaces"
            raise ValueError(msg)
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


class WideLayer(Layer):
    """A layer above the project, global or this machine's: project-only settings are refused (TD-96, TD-308)."""

    @field_validator("preparations", "data")
    @classmethod
    def _project_only(cls, v: object) -> object:
        if v is not None:
            raise ValueError("test preparation is a project setting")  # noqa: EM101, TRY003
        return v


class MachineValues(Record):
    """The machine settings (TD-243): Global's for every machine, or one machine's own in ``machine.json``.

    ``None`` inherits: this machine's value, else Global's, else unset (D-01M5MZKEPPVMFC9HK795MMG91B).
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    channel: Channel | None = None
    update_when_idle: bool | None = None  # TD-288
    update_while_paused: bool | None = None
    curate_after_merge: Curate | None = None  # automatic memory curation per trigger (the owner, 2026-10-23)
    curate_when_idle: Curate | None = None
    sessions: int | None = Field(default=None, ge=1)  # TD-336: agent sessions at once on the machine, all projects
    retro_run_credit_limit: improvement.Credits | None = (
        None  # Improvement (design §5): credits one Retro run may spend
    )
    replay_run_credit_limit: improvement.Credits | None = None  # credits one paid replay run of Spotter cases may spend
    retro_after_change: Curate | None = None  # Retro after a Change ends, like curation's triggers
    retro_when_idle: Curate | None = None  # Retro over finished enrolled chats when idle
    enrolled_chats: list[str] | None = None  # workspace folders whose chats the Spotter and Retro may read; [] is none
    # Hours between timed update checks. Unset: only launch and hand checks, and no project's work starts (#808).
    update_check_hours_owlbear: int | None = Field(default=None, ge=1, le=HOURS)
    update_check_hours_pds: int | None = Field(default=None, ge=1, le=HOURS)
    update_check_hours_impeccable: int | None = Field(default=None, ge=1, le=HOURS)

    @field_validator("enrolled_chats")
    @classmethod
    def _folders(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and (len(set(v)) < len(v) or any(not x.startswith("/") or x != x.strip() for x in v)):
            raise ValueError("enrolled chats are distinct absolute workspace folders")  # noqa: EM101, TRY003
        return v


class GlobalLayer(WideLayer):
    """The global settings; the curator's threshold is global only (TD-400)."""

    curator_threshold: int | None = Field(default=None, ge=50, le=100)  # percent: the curator decides alone at or above
    machine: MachineValues | None = None  # every machine's settings, each machine may set its own
    machine_moved: bool | None = None  # a machine's settings were moved in once (2026-10-23); no machine copies again


class MachineLayer(WideLayer):
    """This machine's preferences, local in ``~/.owlbear``, between the global and the project layer (TD-336)."""


class Effective(Record):
    """One agent's resolved settings; a field its role does not use (``used``) may be unset."""

    model: str | None
    effort: Effort | None
    context: Context | None
    max_rounds: int | None
    max_findings: int | None
    last_round_at: int | None
    ask_owner_at: int | None
    minutes: int | None
    subagents: bool | None

    @model_validator(mode="after")
    def _rounds(self) -> Effective:
        values = self.model_dump(include=set(RoundPolicy.model_fields))
        if None not in values.values():
            RoundPolicy.model_validate(values)
        return self


LOOPED: tuple[Role, ...] = ("shaper", "planner", "builder", "updater")  # whose work runs a challenge loop (TD-209)
UNTIMED: tuple[Role, ...] = ("shaper", "spotter")  # the shaping chat has no session limit; a Spotter look is no session


def used(role: Role) -> tuple[str, ...]:
    """The fields *role*'s work reads and needs set."""
    timed = () if role in UNTIMED else ("minutes", "subagents")
    return ("model", "effort", "context", *timed, *(tuple(RoundPolicy.model_fields) if role in LOOPED else ()))


class SettingsUnset(Exception):  # noqa: N818 - says what happened
    """A step needs settings no layer sets; the owner fills them in on the Settings page."""

    def __init__(self, keys: list[str]) -> None:
        self.keys = keys
        super().__init__(f"settings unset: {', '.join(keys)}; fill them in on the Settings page")


class Settings(Record):
    """Every setting resolved, with the layer each value came from, keyed ``agents.<role>.<field>``.

    ``agents`` holds the roles whose every used field (``used``) is set; ``roles`` holds every role's values, ``None``
    where unset, for the Settings page. A general field no layer sets is ``None``. ``missing`` lists every unset key a
    step reads.
    """

    agents: dict[Role, Effective]
    roles: dict[Role, dict[str, Any]]
    widths: list[int] | None
    preparations: list[Preparation] = Field(default_factory=list)
    data: DataPermissions = Field(default_factory=DataPermissions)
    design_failures: DesignFailures | None = None
    final_review: RoundPolicy | None = None
    pr_labels: list[str] | None = None
    pr_marker: bool | None = None
    load_user_instructions: bool | None = None  # D-01M5YE4P5317N1HWD0QN6N05E0: unset refuses a step's session
    load_user_skills: bool | None = None
    load_user_memory: bool | None = None
    sessions: int | None = None
    prefs: Prefs = Field(default_factory=Prefs)  # R15: each field None where no layer sets it
    spotter: Spotter = Field(default_factory=Spotter)
    curator_threshold: int | None = None
    sources: dict[str, Source]
    missing: list[str] = Field(default_factory=list)
    final_values: dict[str, int | None] = Field(default_factory=dict, exclude=True)  # the page's, set or not

    def need(self, *keys: str) -> None:
        """Raise ``SettingsUnset`` when any of *keys*, or a key under it (``agents.builder``), is unset."""
        found = [m for m in self.missing if any(m == k or m.startswith(f"{k}.") for k in keys)]
        if found:
            raise SettingsUnset(found)

    def agent(self, role: Role) -> Effective:
        """The role's resolved settings; ``SettingsUnset`` when any of them is unset."""
        self.need(f"agents.{role}")
        return self.agents[role]

    def page(self) -> dict[str, Any]:
        """The settings as the page reads them: every role, ``None`` where unset; and the Spotter's allowed actions."""
        return self.model_dump(mode="json", exclude={"roles"}) | {
            "agents": self.roles,
            "final_review": self.final_values,
            "spotter_actions": {improvement.CATEGORIES[c]: list(a) for c, a in improvement.ALLOWED.items()},
        }


BASE: GlobalLayer | None = None  # a layer under Global; empty in production (no code defaults), tests set one


def pref(settings: Settings, key: str) -> Any:  # noqa: ANN401 - each key has its own type; callers know which
    """One preference's value; ``SettingsUnset`` while no layer sets it (R15: no code default fills it in)."""
    settings.need(f"prefs.{key}")
    return getattr(settings.prefs, key)


def _pick(key: str, sources: dict[str, Source], *values: tuple[Source, object]) -> object:
    """The first value that is not ``None``, from the project down to Global; records its source, else ``None``."""
    for source, value in values:
        if value is not None:
            sources[key] = source
            return value
    return None


def resolve(glob: GlobalLayer | None, project: Layer, machine: MachineLayer | None = None) -> Settings:
    """Resolve each field on its own: project, else this machine's, else global (TD-336); unset where none sets it."""
    glob, sources = glob or GlobalLayer(), dict[str, Source]()
    here = machine or MachineLayer()
    layers: list[tuple[Source, Layer]] = [("project", project), ("machine", here), ("global", glob)]
    if BASE is not None:
        layers.append(("default", BASE))
    wide = [(s, layer) for s, layer in layers if s != "project"]
    roles = {
        role: {
            name: _pick(f"agents.{role}.{name}", sources, *((s, getattr(layer.agents.get(role) or Agent(), name))
                                                                for s, layer in layers))
            for name in Effective.model_fields
        }
        for role in ROLES
    }  # fmt: skip
    every = {r: Effective.model_validate(v) for r, v in roles.items()}  # set round values hold together, used or not
    agents = {r: e for r, e in every.items() if all(roles[r][n] is not None for n in used(r))}
    general = {
        key: _pick(key, sources, *((s, getattr(layer, key)) for s, layer in layers))
        for key in (
            "widths",
            "design_failures",
            "pr_labels",
            "pr_marker",
            "load_user_instructions",
            "load_user_skills",
            "load_user_memory",
            "sessions",
        )
    }
    spotter, unset = improvement.resolve(lambda key, *values: _pick(key, sources, *values), layers)
    general["curator_threshold"] = _pick(  # global only (TD-400)
        "curator_threshold", sources, *((s, layer.curator_threshold) for s, layer in wide if s != "machine")
    )
    prep = _pick("preparations", sources, ("project", project.preparations), ("default", []))
    data = _pick("data", sources, ("project", project.data), ("default", DataPermissions()))
    final = {
        name: _pick(
            f"final_review.{name}",
            sources,
            *((s, getattr(layer.final_review or FinalReview(), name)) for s, layer in layers),
            ("builder", roles["builder"][name]),
        )
        for name in RoundPolicy.model_fields
    }
    prefs = {
        key: _pick(f"prefs.{key}", sources, *((s, getattr(layer.prefs or Prefs(), key)) for s, layer in layers))
        for key in PREF_KEYS
    }
    missing = [f"agents.{r}.{n}" for r, v in roles.items() for n in used(r) if v[n] is None]
    missing += [k for k, v in general.items() if v is None]
    missing += [f"prefs.{k}" for k, v in prefs.items() if v is None]
    missing += [f"final_review.{n}" for n, v in final.items() if v is None]
    missing += unset
    return Settings(
        **general,
        prefs=Prefs.model_validate(prefs),
        spotter=spotter,
        agents=agents,
        roles=roles,
        preparations=prep,
        data=data,
        final_review=RoundPolicy.model_validate(final) if None not in final.values() else None,
        final_values=final,
        sources=sources,
        missing=missing,
    )
