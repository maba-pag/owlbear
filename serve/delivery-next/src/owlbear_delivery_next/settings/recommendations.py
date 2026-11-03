"""A copy of the owner's Global that Settings' Use recommended button offers as drafts.

Resolution never reads it, and no migration writes it, so code still ships no defaults.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.round_records import RoundPolicy
from owlbear_delivery_next.github.provider import MergeMethod
from owlbear_delivery_next.settings.carried import LOOK_CREDIT_LIMIT, REPLAY_RUN_CREDIT_LIMIT
from owlbear_delivery_next.settings.config import LOOPED, Agent, GlobalLayer, MachineValues, Prefs, used
from owlbear_delivery_next.settings.improvement import Spotter

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Effort, Role

# Model, effort, minutes: maintained for today's roles, independently of the historical one-time carry.
AGENTS: dict[Role, tuple[str, Effort, int]] = {
    "planner": ("claude-opus-5.5", "high", 30),
    "builder": ("claude-opus-5.5", "medium", 40),
    "reviewer": ("gpt-6.1-sol", "xhigh", 20),
    "challenger": ("gpt-6.1-sol", "high", 20),
    "design-judge": ("claude-opus-5.5", "high", 20),
    "preparer": ("claude-haiku-5.5", "low", 30),
    "shaper": ("claude-opus-5.5", "medium", 40),
    "updater": ("claude-opus-5.5", "high", 40),
    "test-reviewer": ("gpt-6.1-sol", "medium", 20),
    "test-curator": ("claude-opus-5.5", "high", 40),
    "picker": ("gpt-6.1-sol", "medium", 10),
    "curator": ("gpt-6.1-sol", "high", 20),
    "spotter": ("gpt-6-luna", "medium", 1),
    "retro": ("gpt-6.1-sol", "high", 20),
    "retro-review": ("gpt-6.1-sol", "high", 20),
    "auditor": ("gpt-6.1-sol", "high", 40),
}


def page() -> dict[str, object]:
    """A complete current suggestion set; optional dates and project-specific test preparation stay empty."""
    rounds = RoundPolicy(max_rounds=3, max_findings=10, last_round_at=4, ask_owner_at=7).model_dump()
    agents = {
        role: Agent(
            model=model,
            effort=effort,
            context="long" if role in ("design-judge", "shaper") else "default",  # the owner chose the long tier
            minutes=minutes if "minutes" in used(role) else None,
            subagents=True if "subagents" in used(role) else None,
            **(rounds if role in LOOPED else {}),
        )
        for role, (model, effort, minutes) in AGENTS.items()
    }
    return GlobalLayer(
        agents=agents,
        widths=[1280, 1920, 2400],
        design_failures="ask",
        pr_labels=[],
        pr_marker=True,
        load_user_instructions=False,
        load_user_skills=False,
        load_user_memory=False,
        guard_level="lenient",
        sessions=2,
        curator_threshold=95,
        prefs=Prefs(
            merge_method=MergeMethod.SQUASH,
            delete_remote_branch=False,
            ci_poll_seconds=20,
            ci_start_window_seconds=300,
            ask_before_merge=False,
        ),
        spotter=Spotter(
            switch="on",
            hand_off_fitness="record",
            course_and_constraints="record",
            outside_state_changes="record",
            irreversible_harm="stop-and-ask",
            steer_share=80,
            intervention_cap=5,
            verbose="off",
            looks=["hand-off", "plan", "state-change", "sample"],
            sample_rate=80,
            look_credit_limit=LOOK_CREDIT_LIMIT,
        ),
        machine=MachineValues(
            channel="minor",
            update_when_idle=True,
            update_while_paused=True,
            curate_after_merge="on",
            curate_when_idle="on",
            sessions=4,
            retro_run_credit_limit=61.0,  # 5 times the larger measured real run, 12.15 credits
            replay_run_credit_limit=REPLAY_RUN_CREDIT_LIMIT,
            retro_after_change="on",
            retro_when_idle="on",
            enrolled_chats=[],
            update_check_hours_owlbear=3,
            update_check_hours_pds=12,
            update_check_hours_impeccable=12,
        ),
    ).model_dump(mode="json", exclude_none=True, exclude={"format", "prefs_imported", "roles_moved", "machine_moved"})
