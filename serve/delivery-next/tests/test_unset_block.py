"""No work starts for a project while a setting it reads is unset or unreadable (#808), on a two-project machine.

Only the process boundary is faked: runner spawns and check-environment starts are recorded per project.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.models import (
    Change,
    Environment,
    Exit,
    Names,
    PersonCheck,
    Plan,
    Question,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.change_contracts.preparation import Preparation
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow.loop import StepResult, apply
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import Host, RunnerRecord
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import Layer, Prefs
from owlbear_delivery_next.state_store import machine_settings
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps import check, prepare

if TYPE_CHECKING:
    from pathlib import Path

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
GAP = "prefs.ci_poll_seconds"
UNSET = f"no work starts: settings unset: {GAP}; fill them in on the Settings page"


class Project:
    """A registered clone's real store and host; its runners and check environments are recorded, not run."""

    def __init__(self, root: Path) -> None:
        root.mkdir()
        for args in (["init", "-q"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty",
                                      "-m", "i"]):  # fmt: skip
            subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607
        self.store, self.worktree, self.live, self.spawned = Store.open(root), root / "wt", set[int](), list[str]()
        self.worktree.mkdir()
        self.host = Host(self.store, root, spawn=self.spawn, scan=lambda _p, _s: {}, group=lambda _g: {})
        self.host.alive = lambda pid, _created: pid in self.live
        self.store.write_profile(Profile(version=1))

    def spawn(self, slug: str) -> RunnerRecord:
        self.spawned.append(slug)
        self.live.add(pid := 100 + len(self.spawned))
        return RunnerRecord(pid=pid, created=1.0, started_at=NOW)

    def save(self, c: Change) -> None:
        with self.store.lock(c.slug) as lock:
            self.store.write(lock, c)

    def layer(self, **update: object) -> None:
        saved = self.store.save(self.store.config_path, Layer, lambda la: la.model_copy(update=update), "t", owner=True)
        assert saved == ""

    def due(self) -> None:
        """A build step due, a question open and a person check whose environment is due to launch."""
        plan, names = Plan(tasks=[Task(id="t1", title="greet")]), Names(worktree=str(self.worktree))
        self.save(Change(slug="build", plan=plan, step=Step(kind=StepKind.BUILD, task="t1"), names=names))
        asked = Change(slug="asked", plan=plan, step=Step(kind=StepKind.BUILD, task="t1"), names=names)
        self.save(apply(asked, StepResult(exit=Exit.ASK, question=Question(step=StepKind.BUILD, text="lang?")), NOW))
        env = Environment(check="preview", command="npm run preview", directory=".", ready_url="http://127.0.0.1:4/")
        done = Plan(tasks=[Task(id="t1", title="greet", done=True)])
        self.save(Change(slug="check", plan=done, checks=[PersonCheck(id="preview", steps=["open it"])],
                         step=Step(kind=StepKind.CHECK, task="preview"), env=env, names=names))  # fmt: skip
        none = Preparation(id="none", kind="data-only", seed="true", cleanup="true", isolation={"APP_ENV": "test"})
        self.layer(preparations=[none])
        prepare._write(self.store, "check", prepare.Prepared(check="preview", option=none, ready=True))  # noqa: SLF001


@pytest.fixture
def started(monkeypatch) -> list[str]:
    """The worktrees whose check environment started."""
    roots: list[str] = []

    def start(_e, root, _log, _env=None):
        roots.append(str(root))
        return SimpleNamespace(pid=900)

    monkeypatch.setattr(check, "dispose", lambda _e: {})
    monkeypatch.setattr(check, "start", start)
    monkeypatch.setattr(check, "ready", lambda e, _proc: e.pids | {901: 2.0})
    monkeypatch.setattr(check, "created", lambda _pid: 2.0)
    return roots


@pytest.fixture
def a_b(tmp_path, monkeypatch) -> tuple[Project, Project]:
    """A leaves the CI poll interval unset; B sets it in its own layer. Both have work due."""
    prefs = config.BASE.prefs.model_copy(update={"ci_poll_seconds": None})
    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"prefs": prefs}))
    a, b = Project(tmp_path / "a"), Project(tmp_path / "b")
    b.layer(prefs=Prefs(ci_poll_seconds=20))
    a.due()
    b.due()
    assert (a.store.settings().missing, b.store.settings().missing, machine_settings.current().missing) == (
        [GAP], [], [],
    )  # fmt: skip
    return a, b


def test_the_scheduler_starts_nothing_for_a_project_with_an_unset_setting_until_it_is_set(a_b, started, capsys):
    a, b = a_b
    a.host.tick(NOW)
    b.host.tick(NOW)
    assert (a.spawned, started.count(str(a.worktree))) == ([], 0), "A did not start"
    assert (b.spawned, started) == (["build"], [str(b.worktree)])
    assert (a.host.grants, a.host.launches) == ({}, {})  # no session slot asked for, no launch counted
    approval = TestClient(api.create_app(a.store, "tok", a.host), base_url="http://127.0.0.1",
                          headers={"authorization": "Bearer tok"})  # fmt: skip
    answer = {"question": "q1", "text": "German", "kind": "event"}
    assert approval.post("/api/next/changes/asked/answers", json=answer).status_code == 200
    a.host.tick(NOW)
    a.host.tick(NOW)
    assert (a.store.read("asked").questions[0].answer.text, a.spawned) == ("German", [])  # recorded, nothing started
    assert capsys.readouterr().out.count(UNSET) == 1

    a.layer(prefs=Prefs(ci_poll_seconds=20))
    a.host.tick(NOW)
    assert (sorted(a.spawned), started.count(str(a.worktree))) == (["asked", "build"], 1)
    assert "the settings are set; work starts again" in capsys.readouterr().out


def test_an_ended_runner_of_a_blocked_project_is_confirmed_gone_and_none_follows(a_b, started):
    a, _ = a_b
    a.live.add(500)
    record = RunnerRecord(pid=500, created=1.0, started_at=NOW)
    (a.store.root / "changes" / "build" / "runner.json").write_text(record.model_dump_json())
    a.host.tick(NOW)
    assert a.host.runner("build").pid == 500  # running work goes on
    a.live.clear()
    a.host.tick(NOW)
    assert (a.host.runner("build"), a.spawned, started) == (None, [], [])


def test_an_unset_update_check_interval_holds_both_projects(a_b, started, monkeypatch, capsys):
    a, b = a_b
    a.layer(prefs=Prefs(ci_poll_seconds=20))
    update = {"update_check_hours_pds": None}
    monkeypatch.setattr(machine_settings, "BASE", machine_settings.BASE.model_copy(update=update))
    a.host.tick(NOW)
    b.host.tick(NOW)
    assert (a.spawned, b.spawned, started) == ([], [], [])
    assert capsys.readouterr().out.count("no work starts: settings unset: machine.update_check_hours_pds;") == 2


def test_an_unreadable_project_layer_holds_that_project_alone_and_names_why(a_b, started, capsys):
    a, b = a_b
    a.store.config_path.write_text("{not json")
    a.host.tick(NOW)
    b.host.tick(NOW)
    assert (a.spawned, b.spawned, started) == ([], ["build"], [str(b.worktree)])
    assert "no work starts: settings can't be read: state of config is unreadable" in capsys.readouterr().out
