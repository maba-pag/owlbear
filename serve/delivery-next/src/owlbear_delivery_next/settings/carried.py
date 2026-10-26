"""Today's built-in settings, written into the Global layer once (the owner, 2026-10-23).

Code ships no settings defaults: every value comes from Global, this machine or the project, and an unset one is an
error that refuses the steps needing it. These are the values that were built in until then. The update that
removed them writes them where the Global layer leaves a field unset, once, in one commit
(``state_store.settings_carry``); resolution never reads them. A setting added later starts unset
(D-01M5MZKEPW6WCSM8SZ6DH783EN). ``MACHINE`` fills Global's machine settings where the first machine's own leave
them unset; each machine then clears its own, so every machine follows Global (the owner, 2026-10-23).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.profile_record import RoleModel
from owlbear_delivery_next.change_contracts.round_records import RoundPolicy
from owlbear_delivery_next.settings.config import Agent, GlobalLayer, MachineValues
from owlbear_delivery_next.settings.improvement import Spotter

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Role

MODELS: dict[Role, RoleModel] = {
    "planner": RoleModel(model="claude-opus-5.5", effort="high"),
    "builder": RoleModel(model="claude-opus-5.5", effort="medium"),
    "reviewer": RoleModel(model="gpt-6.1-sol", effort="xhigh"),
    "challenger": RoleModel(model="gpt-6.1-sol", effort="high"),
    "design-judge": RoleModel(model="claude-opus-5.5", effort="high"),
    "preparer": RoleModel(model="claude-haiku-5.5", effort="low"),
    "shaper": RoleModel(model="claude-opus-5.5", effort="medium"),
    "updater": RoleModel(model="claude-opus-5.5", effort="high"),
    "test-reviewer": RoleModel(model="gpt-6.1-sol", effort="medium"),
    "test-curator": RoleModel(model="claude-opus-5.5", effort="high", context="long"),
    "picker": RoleModel(model="gpt-6.1-sol", effort="medium"),
    "curator": RoleModel(model="gpt-6.1-sol", effort="high"),
    "spotter": RoleModel(model="gpt-6-luna", effort="medium"),  # the watcher's: the owner's benchmark pick (2026-10-23)
}
MINUTES: dict[Role, int] = {
    "planner": 30, "builder": 40, "reviewer": 20, "challenger": 20, "design-judge": 20, "preparer": 30,
    "shaper": 40, "updater": 40, "test-reviewer": 20, "test-curator": 40, "picker": 10, "curator": 20, "spotter": 1,
}  # fmt: skip
MACHINE = MachineValues(
    channel="minor", update_when_idle=True, update_while_paused=True, curate_after_merge="on", curate_when_idle="on",
    sessions=4,
)  # fmt: skip


def layer() -> GlobalLayer:
    """The built-in values as a complete Global layer."""
    rounds = RoundPolicy(max_rounds=3, max_findings=10, last_round_at=4, ask_owner_at=7).model_dump()
    agents = {
        role: Agent(
            model=rm.model, effort=rm.effort, context=rm.context, runtime="sdk", visible=False, categories=[],
            minutes=MINUTES[role], subagents=True, **rounds,
        )
        for role, rm in MODELS.items()
    }  # fmt: skip
    return GlobalLayer(
        agents=agents, runtimes={"sdk": True, "window": True}, widths=[1280, 1920, 2400], design_failures="ask",
        pr_labels=[], pr_marker=True, sessions=2, spotter=Spotter(mode="learning"), visible=False, curator_threshold=95,
    )  # fmt: skip


def filled(glob: GlobalLayer) -> GlobalLayer:
    """*glob* with every field it leaves unset taken from the built-in values; what it sets stays.

    Its machine settings are the first machine's move's (``settings_carry.move``).
    """
    base = layer()
    agents = {
        role: Agent.model_validate(base.agents[role].model_dump() | (glob.agents.get(role) or Agent()).model_dump(
            exclude_none=True))
        for role in base.agents
    }  # fmt: skip
    top = base.model_dump(exclude={"agents"}) | glob.model_dump(exclude={"agents", "format"}, exclude_none=True)
    top["runtimes"] = base.runtimes | glob.runtimes
    return GlobalLayer.model_validate(top | {"agents": {r: a.model_dump() for r, a in agents.items()}})
