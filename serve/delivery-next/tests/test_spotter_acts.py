"""What a Spotter finding does (Improvement design §4): the acting rules by their boundaries, and each unit's arm."""

from __future__ import annotations

import asyncio
import dataclasses
import json
import stat
import subprocess
import sys
from typing import Any

import pytest

from owlbear_delivery_next.improvement import acts, spotter
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.state_store import spotter_arms

ACTIONS = {"hand-off-fitness": "refuse-hand-off", "course-and-constraints": "steer",
           "outside-state-changes": "show-owner", "irreversible-harm": "stop-and-resume"}  # fmt: skip


async def _never(_record: spotter.Record, _act: acts.Act) -> None:
    raise AssertionError  # decide never dispatches


def ctx(**kw: Any) -> spotter.Context:
    base = spotter.Context(project="p", change="c1", step="build", looks=("hand-off",), sample_rate=0, verbose=False,
                           model="m", effort="medium", limit=0.75, actions=ACTIONS, arm="steered", cap=2,
                           act=_never)  # fmt: skip
    return dataclasses.replace(base, **kw)


def decided(category: str, look: str = "hand-off", *, sent: int = 0, unresolved: dict | None = None,
            **kw: Any) -> tuple[str, str]:  # fmt: skip
    record = spotter.Record(id="r1", at="2026-11-02T00:00:00+00:00", project="p", change="c1", step="build",
                            session="s-1", look=look, call="c", cutoff=3, probability=1.0, category=category,
                            note="Run the tests first.")  # fmt: skip
    act = acts.decide(record, look, ctx(**kw), sent, unresolved or {})
    return act.act, act.why


@pytest.mark.parametrize(
    ("category", "look", "kw", "expected"),
    [
        ("course-and-constraints", "sample", {}, ("none", "record-only look")),
        ("course-and-constraints", "state-change", {}, ("none", "record-only look")),
        ("irreversible-harm", "sample", {}, ("stop-and-resume", "setting")),  # harm acts from any look
        ("course-and-constraints", "plan", {"sent": 1}, ("steer", "setting")),  # the cap's last note
        ("course-and-constraints", "plan", {"sent": 2}, ("none", "cap")),  # its first note over
        ("hand-off-fitness", "hand-off", {"sent": 2}, ("refuse-hand-off", "setting")),  # refusals are never capped
        ("irreversible-harm", "plan", {"sent": 2}, ("stop-and-resume", "setting")),  # nor harm
        ("outside-state-changes", "hand-off", {}, ("show-owner", "setting")),  # shown, never sent
        ("course-and-constraints", "plan", {"arm": "silent"}, ("none", "arm")),
        ("irreversible-harm", "plan", {"arm": "silent"}, ("stop-and-resume", "setting")),  # harm acts in both arms
        (
            "course-and-constraints",
            "plan",
            {"arm": "silent", "actions": {"course-and-constraints": "stop-and-ask"}},
            ("stop-and-ask", "setting"),
        ),  # asking the owner is no discretionary action
        ("course-and-constraints", "plan", {"actions": {"course-and-constraints": "record"}}, ("none", "setting")),
        (
            "course-and-constraints",
            "plan",
            {"unresolved": {("course-and-constraints", "plan"): "delivered"}},
            ("ask", "repeat"),
        ),
        (
            "course-and-constraints",
            "plan",
            {"unresolved": {("course-and-constraints", "plan"): "asked"}},
            ("none", "asked"),
        ),
        (
            "course-and-constraints",
            "hand-off",
            {"unresolved": {("course-and-constraints", "plan"): "delivered"}},
            ("steer", "setting"),
        ),  # another look kind is no repeat
    ],
)
def test_a_finding_acts_by_its_setting_its_look_its_arm_the_cap_and_its_repeats(category, look, kw, expected) -> None:
    assert decided(category, look, **kw) == expected


def test_show_owner_is_never_sent_to_the_agent() -> None:
    answer = json.dumps({"category": "outside-state-changes", "note": "Pushes main.", "evidence": ["e1"]})

    async def judge(_card: dict[str, Any], _ctx: spotter.Context, spend: Any) -> str:
        spend.part().ended(None, confirmed=True)
        return answer

    async def main() -> None:
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge)
        spot.handed_off("call-1", {})
        await spot.drain()

    asyncio.run(main())
    assert spotter.WORK.settled(5)
    [act] = acts.acts(spotter.root()).values()
    assert (act.act, act.delivery, act.error) == ("show-owner", "", "")  # ``_never`` was not awaited


def test_an_acting_context_without_its_arm_or_cap_is_refused() -> None:
    with pytest.raises(ValueError, match="arm"):
        ctx(arm=None)
    with pytest.raises(ValueError, match="cap"):
        ctx(cap=None)
    ctx(act=None, arm=None, cap=None)  # not acting: neither is read


def test_an_arm_is_drawn_once_and_kept_when_a_fresh_interpreter_reopens_it_with_another_share() -> None:
    assert spotter_arms.arm("chg:p/never", 0) == "silent"
    assert spotter_arms.arm("chg:p/always", 100) == "steered"
    code = ("from owlbear_delivery_next.state_store import spotter_arms; "
            "print(spotter_arms.arm('chg:p/never', 100), spotter_arms.arm('chat:s-1', 100))")  # fmt: skip
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.split()  # noqa: S603
    assert out == ["silent", "steered"]
    assert spotter_arms.arm("chat:s-1", 0) == "steered"  # the child's draw is kept here too
    path = local_home.root() / "spotter" / "arms.json"
    assert (stat.S_IMODE(path.parent.stat().st_mode), stat.S_IMODE(path.stat().st_mode)) == (0o700, 0o600)
    kept = json.loads(path.read_text())
    assert {u: a["arm"] for u, a in kept.items()} == {"chg:p/never": "silent", "chg:p/always": "steered",
                                                       "chat:s-1": "steered"}  # fmt: skip
