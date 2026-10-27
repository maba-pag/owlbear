"""Today's built-in settings, written into the Global layer once (the owner, 2026-10-23).

Code ships no settings defaults: every value comes from Global, this machine or the project, and an unset one is an
error that refuses the steps needing it. These are the values that were built in until then. The update that
removed them writes them where the Global layer leaves a field unset, once, in one commit
(``state_store.settings_carry``); resolution never reads them. A setting added later starts unset
(D-01M5MZKEPW6WCSM8SZ6DH783EN). ``MACHINE`` fills Global's machine settings where the first machine's own leave
them unset; each machine then clears its own, so every machine follows Global (the owner, 2026-10-23).

The credit limits came later (D-01M5XCD49YHHR1NQKKY8TQD0C3, 2026-10-27): each is written into Global once at five times
its expected cost, by the format-16 upgrade of an existing Global (``state_store.settings_carry.limits``) or by the
carry of a fresh one. Every expected cost is a marked assumption until Retro measures it:

- A look: 0.15 credits. Assumption, from the pilot's looks on the current prompt line (gpt-6-luna, medium, one
  tool-less call each): 0.128 on average over the dev moments (0.064 to 0.193), 0.151 to 0.156 on the holdout (at most
  0.225); a live hand-off look cost 0.07. A verbose look adds at most five sentences. Limit 0.75.
- A Retro run: 4 credits. Assumption, not measured: Retro is not built. One hindsight judgement with Sol (medium) over
  a moment and its whole continuation cost 2.4 credits in the pilot (199.4 for 83); a run is taken to be one such
  judgement over a finished Change's compacted step sessions plus grading its Spotter records. Limit 20. A run that
  checks all 85 candidate cases at about 1 credit each would reach it: the owner checks them in batches, or raises it.
- A paid replay run of Spotter cases: 17.7 credits. Assumption: the cases' seed gives 53 dev cases and 6 synthetic
  ones, 59 scored test cases; a regression looks at each twice (the current examples and the proposed ones) at 0.15
  a look; a failed look's one rerun is within the rounding; a holdout run (about 34 cases, twice) costs about 10.
  Five times is 88.5, rounded up: limit 90.
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
LOOK_CREDIT_LIMIT, RETRO_RUN_CREDIT_LIMIT, REPLAY_RUN_CREDIT_LIMIT = 0.75, 20.0, 90.0  # five times the assumed costs
MACHINE = MachineValues(
    channel="minor", update_when_idle=True, update_while_paused=True, curate_after_merge="on", curate_when_idle="on",
    sessions=4, retro_run_credit_limit=RETRO_RUN_CREDIT_LIMIT, replay_run_credit_limit=REPLAY_RUN_CREDIT_LIMIT,
)  # fmt: skip


def layer() -> GlobalLayer:
    """The built-in values as a complete Global layer."""
    rounds = RoundPolicy(max_rounds=3, max_findings=10, last_round_at=4, ask_owner_at=7).model_dump()
    agents = {
        role: Agent(
            model=rm.model, effort=rm.effort, context=rm.context, minutes=MINUTES[role], subagents=True, **rounds,
        )
        for role, rm in MODELS.items()
    }  # fmt: skip
    return GlobalLayer(
        agents=agents, widths=[1280, 1920, 2400], design_failures="ask", pr_labels=[], pr_marker=True, sessions=2,
        spotter=Spotter(switch="on", look_credit_limit=LOOK_CREDIT_LIMIT), curator_threshold=95,
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
    return GlobalLayer.model_validate(top | {"agents": {r: a.model_dump() for r, a in agents.items()}})
