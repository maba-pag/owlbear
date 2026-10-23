"""Code ships no settings defaults (the owner, 2026-10-23): unset values, their errors and the one-time carry."""

import json
import subprocess
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts.models import Brief, Change, Criterion, Plan, Step, StepKind, Task
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.settings import carried, config, roles
from owlbear_delivery_next.settings.config import GlobalLayer, Layer, SettingsUnset, resolve
from owlbear_delivery_next.state_store import settings_carry
from owlbear_delivery_next.state_store.store import read_layer
from owlbear_delivery_next.workflow_steps import unset_settings


@pytest.fixture
def no_base(monkeypatch):
    monkeypatch.setattr(config, "BASE", None)


@pytest.mark.usefixtures("no_base")
def test_a_setting_no_layer_sets_is_unset_and_listed_never_filled_from_code():
    empty = resolve(None, Layer())
    assert (empty.agents, empty.sessions, empty.watcher, empty.final_review) == ({}, None, None, None)
    assert {"agents.builder.model", "agents.watcher.effort", "sessions", "watcher", "runtimes.sdk"} <= set(
        empty.missing
    )
    assert empty.page()["agents"]["builder"]["model"] is None
    assert "sessions" not in empty.sources

    builder = carried.layer().agents["builder"]
    some = resolve(GlobalLayer(agents={"builder": builder}, sessions=3), Layer())
    assert (some.agent("builder").model, some.sessions, some.sources["sessions"]) == ("claude-opus-5.5", 3, "global")
    assert some.final_review is not None  # the final review inherits the builder's rounds
    with pytest.raises(SettingsUnset, match=r"agents\.reviewer\.model") as caught:
        roles.chosen(some, StepKind.REVIEW)
    assert all(k.startswith("agents.reviewer.") for k in caught.value.keys)
    with pytest.raises(SettingsUnset, match="pr_labels"):
        some.need("pr_marker", "pr_labels")
    assert "unset; fill it in" in roles.table(some)


def change(kind: StepKind) -> Change:
    return Change(
        slug="c1",
        brief=Brief(version=1, approved_version=1, challenged=1, criteria=[Criterion(id="AC-1", text="works")]),
        plan=Plan(tasks=[Task(id="t1", title="one", scope=["a"])]),
        step=Step(kind=kind, task="t1" if kind in {StepKind.BUILD, StepKind.REVIEW} else None),
    )


def test_a_step_that_needs_an_unset_setting_asks_the_owner_and_continues_once_filled():
    written: list[Change] = []
    store = SimpleNamespace(read=lambda _slug: change(StepKind.BUILD), write=lambda _lock, c: written.append(c))
    unset_settings.asked(store, SimpleNamespace(slug="c1"), SettingsUnset(["agents.builder.model"]))
    (question,) = written[0].questions
    assert question.cause == "state:build:settings-unset"
    assert "agents.builder.model" in question.text
    assert [o.id for o in question.options] == ["done", "pause"]


def _git(root, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


def test_todays_built_in_values_are_carried_into_global_once_keeping_what_it_sets(shared_repo):
    shared = DataRepo(shared_repo[0])
    shared.global_path.write_text(json.dumps({"format": 2, "agents": {"builder": {"model": "gpt-6-luna"}},
                                              "runtimes": {}, "widths": [1440]}))  # fmt: skip
    _git(shared.root, "add", "-A")
    _git(shared.root, "commit", "-qm", "an old global layer")
    assert settings_carry.due(shared)

    settings_carry.carry(shared)

    glob = read_layer(shared.global_path, GlobalLayer)
    assert (glob.agents["builder"].model, glob.agents["builder"].effort, glob.widths) == (
        "gpt-6-luna",
        "medium",
        [1440],
    )
    assert (glob.agents["watcher"].model, glob.sessions, glob.pr_marker, glob.curator_threshold) == (
        "gpt-6-luna", 2, True, 95)  # fmt: skip
    assert json.loads(shared.global_path.read_text())["format"] == config.CARRIED_FORMAT
    assert _git(shared.root, "log", "-1", "--format=%s") == "settings: today's built-in values carried into Global"
    assert _git(shared.root, "status", "--porcelain") == ""
    head = _git(shared.root, "rev-parse", "HEAD")
    assert (settings_carry.due(shared), settings_carry.carry(shared)) == (False, "")
    assert _git(shared.root, "rev-parse", "HEAD") == head  # once: nothing more


@pytest.mark.usefixtures("no_base")
def test_a_carried_global_resolves_every_setting(shared_repo):
    shared = DataRepo(shared_repo[0])
    settings_carry.carry(shared)  # no Global file yet: today's values in full
    assert resolve(read_layer(shared.global_path, GlobalLayer), Layer()).missing == []
