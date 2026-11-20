"""Configuration and durable callbacks for one worker session."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts import tools, user_config

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import ItemRef, StepKind
    from owlbear_delivery_next.change_contracts.permissions import Policy
    from owlbear_delivery_next.change_contracts.preparation import Preparing
    from owlbear_delivery_next.local_system import pds_skill
    from owlbear_delivery_next.local_system.processes import Pids
    from owlbear_delivery_next.runtimes import watch_feed


@dataclass(frozen=True)
class Journal:
    """Durable writes the runner makes under the Change lock as the step goes, so a killed runner leaves them."""

    event: Callable[[dict[str, Any]], None] = lambda _e: None
    delivered: Callable[[], None] = lambda: None
    replaced: Callable[[], str | None] = lambda: None
    now: Callable[[dict[str, Any]], None] = lambda _e: None  # the latest tool call, overwritten; not activity


@dataclass(frozen=True)
class Session:
    """Everything one step session needs; tools are bound here, never by agent-supplied identity (T2)."""

    kind: StepKind
    worktree: Path
    session_id: str
    message: str
    resume: bool
    policy: Policy
    observe: Callable[[], tools.Worktree]
    checks: tuple[str, ...]
    lint_commands: tuple[tuple[str, ...], ...] = ()
    quality: Callable[[], list[str]] | None = None
    packages: tuple[tuple[str, str], ...] = ()  # the profile's (package, check) pairs a plan's error hint names
    submit: tools.Spec = tools.SUBMIT
    scope: tuple[str, ...] = ()  # the approved brief scope a plan must keep to
    item: ItemRef | None = None  # the conversation item a build task answers, if any
    rejectable: tuple[str, ...] = ()  # finding keys a review repair's builder may reject (TD-124)
    rechecks: tuple[str, ...] = ()  # keys of rejected findings a review rechecks or reconsiders (TD-176, TD-193)
    cap: int = 20  # new findings a review may return: the loop's max findings, none in a rejections-only check
    plan_tasks: tuple[str, ...] = ()  # the plan tasks each final-review finding names (TD-216)
    changed: tuple[str, ...] = ()  # the files an Impeccable challenger judges one by one (TD-194)
    settled: tuple[str, ...] = ()  # finding keys the owner decided to fix: never rejected (TD-193)
    amendable: tuple[str, ...] = ()  # the brief items a premise may name in an amendment, as field:key (TD-185)
    repository: str = ""  # the host's confirmed project identity for project-scoped result admission
    targets: tuple[str, ...] = ()  # what a design judge's conflict may depart from: its round's states and criteria
    skills: Path | None = None  # the skill folder this session loads instead of the package's: a pack candidate's
    pds: pds_skill.Choice | None = None  # the project's PDS knowledge skill; when None, chosen from the worktree (#777)
    subagents: bool = False  # its role's setting: it may start built-in subagents (TD-374, TD-376)
    user: user_config.UserConfig = user_config.USER_OFF  # the owner's switches; off where a site sets none
    credit_limit: float | None = None  # the runtime's hard session limit; an experiment's ledger sets it (TD-178)
    model: str | None = None
    effort: str | None = None  # the SDK's reasoning effort
    context: str = "default"  # the model's context tier: "long" pins its long-context tier, else the runtime chooses
    limit: float | None = None  # seconds the session may run in total: its role's setting (TD-286), else its kind's
    fresh: str = ""  # first message of a replacement session: stored context plus the pending answer
    previous: Pids = field(default_factory=dict)  # PIDs earlier runners recorded for this session
    journal: Journal = field(default_factory=Journal)
    attachments: tuple[dict[str, str], ...] = ()  # blob attachments sent with the first message
    memory: Path | None = None  # the project's memory folder in the shared repository (TD-70, TD-72)
    ui: bool = False  # the Change has a user interface, so the role's design skills load too (TD-76)
    role: str = ""  # the agent role when not the step kind's, such as the design judge's
    job: str = ""  # a judge's label, when its job needs other skills than its role's (TD-166)
    judging: bool = False  # a verdict-only judgement, such as the reviewer's of screenshots: no question (TD-108)
    first_look: tools.Spec | None = None  # a judgement submitted before the final result, which does not end it
    reveal: str = ""  # what the first look's reply releases, such as the detector's findings
    helpers: tuple[tuple[tools.Spec, Callable[[tools.Args], str]], ...] = ()  # Delivery tools that answer, not end
    preparing: Preparing | None = None  # check preparation: the declared options a recipe is validated against
    watch: watch_feed.Watching | None = None  # a Change-owned session's watcher; None when the master switch is off
