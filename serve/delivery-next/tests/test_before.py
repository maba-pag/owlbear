import shlex
import socket
import subprocess
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import psutil
import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import evidence
from owlbear_delivery_next.change_contracts.models import (
    VISUAL,
    Brief,
    Change,
    Environment,
    Names,
    Plan,
    Step,
    StepKind,
    Task,
    VisualState,
)
from owlbear_delivery_next.change_contracts.preparation import Preparation
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_contracts.visual_records import PageError, VisualResult, VisualRound
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.impeccable import pack_files
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.settings.config import Layer
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import before, captures, check, prepare, visual

from .test_visual import commit, git, with_origin

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
HOME = VisualState(name="home", path="/", expect="The greeting is centred")
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def ui(tmp_path, change_repo, monkeypatch):
    """A Change whose page says "before" at the merge-base and "after" at its head, at the visual check."""
    work = with_origin(change_repo, tmp_path)
    commit(work, "site/index.html", "before")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/main")
    commit(work, "site/index.html", "after")
    port = free_port()
    monkeypatch.setattr(check, "free_port", lambda: port)  # the port Delivery picks, known to the test
    command = f"{sys.executable} -m http.server {{port}} --bind 127.0.0.1"
    env = Environment(check=VISUAL, command=command, directory="site", ready_url="http://127.0.0.1:{port}/")
    plan = Plan(tasks=[Task(id="t1", title="greet", scope=["site"])])
    names = Names(branch="owlbear/c1", target="main", worktree=str(work))
    brief = Brief(version=1, ui=True, visual=[HOME])
    c = Change(slug="c1", brief=brief, plan=plan, names=names, env=env, step=Step(kind=StepKind.CHECK, task=VISUAL))
    monkeypatch.setattr(visual, "CAPTURE", fetching)
    return c


def fetching(base, states, out, widths, **_k):
    """A capturer that stores what each state's URL answers, so a test can see which commit was rendered."""
    shots = []
    for s in states:
        with _LOCAL.open(base + s.path, timeout=5) as response:
            body = response.read()
        for w in widths:
            (out / f"{s.name}-{w}.png").write_bytes(body)
            seen = (PageError(state=s.name, version=s.version, width=w, kind="console", text="old"),)
            shots.append(visual.Shot(s.name, w, f"{s.name}-{w}.png", errors=seen))
    return shots


def served(c):
    """The URL the recipe answered at, with the port the fixture made Delivery pick."""
    return check.url(c.env.model_copy(update={"port": check.free_port()}))


def run(c, tmp_path, events, profile=None, widths=(1280, 1920)):
    return before.capture(
        c,
        Path(c.names.worktree),
        lambda b: tmp_path / "out" / b[:7],
        profile or Profile(),
        events.append,
        widths=widths,
    )


def worktrees(c):
    return git(Path(c.names.worktree), "worktree", "list", "--porcelain").count("worktree ")


class Host:
    maintenance = None
    record = None

    def activity(self, _slug):
        return Activity(host_up=True)


def test_due_once_per_visual_check_environment_unless_the_owners_answer_settles_its_round(ui):
    """D-01M6Q4B6VV4Z05WFQ1BD4X95HJ: each new environment's capture gets its own "before"; settling needs none."""
    assert before.due(ui)
    assert not before.due(ui.model_copy(update={"env": ui.env.model_copy(update={"launched_at": NOW})}))
    assert not before.due(ui.model_copy(update={"step": Step(kind=StepKind.CHECK, task="look")}))
    assert not before.due(ui.model_copy(update={"brief": Brief(version=1, ui=True)}))
    taken = VisualResult(head="base", tree="t", at=NOW)
    waived = VisualRound(number=1, head="h", tree="t", brief=ui.brief.version, before=taken.identity(), outcome="model",
                         model_waived=True, states={"home": 1}, criteria=evidence.criteria(ui),
                         pack=pack_files.identity(), at=NOW)  # fmt: skip
    for rounds, head, env, due in (
        ([], "h", ui.env, True),  # a new environment, no round to settle
        ([waived.model_copy(update={"model_waived": False})], "h", ui.env, True),  # a round judged again
        ([waived], "moved", ui.env, True),  # his waiver no longer matches the head
        ([waived], "h", ui.env, False),  # his waiver settles the round on the capture it judged
        ([waived.model_copy(update={"owner": ["owner-1"]})], "h", ui.env, True),  # a criterion withdrawn since
        ([], "h", ui.env.model_copy(update={"check": "look"}), False),  # a person check keeps the visual evidence
    ):
        c = ui.model_copy(update={"before": taken, "visual_rounds": rounds, "env": env})
        before.reset(c, head)
        assert (c.before is None) is due
    about = VisualState(name="about", path="/about.html", expect="About us")
    amended = ui.model_copy(update={"brief": ui.brief.model_copy(update={"visual": [HOME, about]})})
    amended.before = taken.model_copy(update={"states": {"home": 1, "about": 1}})
    # an amendment voided about's "after", its wording unchanged: the challenger named it
    amended.visual = VisualResult(head="h", tree="t", states={"home": 1, "about": 0}, passed=True, at=NOW,
                                  criteria=evidence.criteria(amended))  # fmt: skip
    before.reset(amended, "h")  # D-01M6GBBY578CY7F5N863EXHYEQ: home keeps its "after" and its "before"
    assert (amended.before.identity(), amended.before.states, before.due(amended)) == (
        taken.identity(),
        {"home": 1, "about": 0},
        True,
    )  # only about is captured again, on both sides


def test_the_states_are_rendered_at_the_merge_base_with_the_same_recipe_and_everything_is_removed(ui, tmp_path):
    events = []
    shots = run(ui, tmp_path, events)
    base = git(Path(ui.names.worktree), "merge-base", "HEAD", "origin/main")
    assert (shots.head, shots.files, shots.findings) == (base, ["home-1280.png", "home-1920.png"], [])
    assert [(e.width, e.text) for e in shots.errors] == [(1280, "old"), (1920, "old")]
    assert (tmp_path / "out" / base[:7] / "home-1920.png").read_text() == "before"
    pids = [int(p) for e in events if e["event"] == "pids" for p in e["pids"]]
    assert pids
    assert not any(psutil.pid_exists(p) and psutil.Process(p).status() != psutil.STATUS_ZOMBIE for p in pids)
    assert (check.answers(served(ui)), worktrees(ui)) == (False, 1)


def test_a_failing_install_is_a_note_and_nothing_is_launched(ui, tmp_path, monkeypatch):
    fail = f"{sys.executable} -c 'import sys; print(\"no registry\"); sys.exit(3)'"
    monkeypatch.setattr(before.worktree, "installs", lambda _p, scope: [(".", fail)] if scope == ["site"] else [])
    events = []
    shots = run(ui, tmp_path, events)
    assert (shots.files, len(events), worktrees(ui)) == ([], 1, 1)  # only the installer's PID is journaled
    assert shots.findings[0].endswith("failed: no registry")


def test_a_port_already_answering_is_a_note_and_nothing_is_launched(ui, tmp_path):
    import http.server  # noqa: PLC0415
    import threading  # noqa: PLC0415

    port = check.free_port()  # the port Delivery picks is taken by another server meanwhile
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        events = []
        shots = run(ui, tmp_path, events)
    finally:
        server.shutdown()
    assert (shots.files, shots.findings, events) == ([], [f"something else already answers at {served(ui)}"], [])


def test_a_recipe_ignoring_its_port_is_a_note_and_its_processes_are_stopped(ui, tmp_path, monkeypatch):
    monkeypatch.setattr(check, "READY_WITHIN", 1.0)
    command = f"{sys.executable} -m http.server {free_port()} --bind 127.0.0.1"  # a fixed port, not the assigned one
    ui.env = ui.env.model_copy(update={"command": command})
    events = []
    shots = run(ui, tmp_path, events)
    assigned = check.free_port()
    why = f"the preview did not answer on its assigned port {assigned} at http://127.0.0.1:{assigned}/"
    assert (shots.files, len(shots.findings)) == ([], 1)
    assert shots.findings[0].startswith(f"for the merge-base, {why}; it may use a fixed port; it printed: ")
    pid = int(next(iter(events[0]["pids"])))
    assert not (psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE)
    assert worktrees(ui) == 1


def gone(pid):
    return not (psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE)


def test_a_recipe_whose_leader_exits_leaving_a_child_has_the_child_stopped(ui, tmp_path, monkeypatch):
    monkeypatch.setattr(check, "READY_WITHIN", 20.0)  # its leader's exit ends the wait
    child = tmp_path / "child.pid"
    spawn = (
        "import subprocess, sys; "
        "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
        f"open({str(child)!r}, 'w').write(str(p.pid)); print('no database at TEST_DB')"
    )
    ui.env = ui.env.model_copy(update={"command": f"{sys.executable} -c {shlex.quote(spawn)}"})
    shots = run(ui, tmp_path, [])
    url = check.url(ui.env.model_copy(update={"port": check.free_port()}))
    said = f"the preview exited with status 0 before it answered at {url}; it printed: no database at TEST_DB"
    assert shots.findings == [f"for the merge-base, {said}"]  # D-01M64TXG1P1HMPQH7Q9CWAYSSW: what it said, whole
    assert gone(int(child.read_text()))


def test_a_capture_that_raises_still_stops_the_preview_and_removes_the_worktree(ui, tmp_path, monkeypatch):
    def broken(_base, _states, _out, _widths, **_k):
        missing = "no Chromium"
        raise RuntimeError(missing)

    monkeypatch.setattr(visual, "CAPTURE", broken)
    events = []
    shots = run(ui, tmp_path, events)
    assert (shots.files, shots.findings) == ([], ["RuntimeError: no Chromium"])
    assert all(gone(int(p)) for e in events for p in e["pids"])
    assert (check.answers(served(ui)), worktrees(ui)) == (False, 1)


def test_an_unwritable_screenshot_folder_is_a_note_not_a_crash(ui, tmp_path):
    (tmp_path / "blocked").write_text("a file where the folder should be")
    out = lambda b: tmp_path / "blocked" / b[:7]  # noqa: E731
    shots = before.capture(ui, Path(ui.names.worktree), out, Profile(), [].append, widths=(1280,))
    assert shots.files == []
    assert shots.findings[0].startswith(("FileExistsError", "NotADirectoryError"))
    assert worktrees(ui) == 1


def test_an_install_over_time_is_stopped_with_its_whole_group(ui, tmp_path, monkeypatch):
    child = tmp_path / "child.pid"
    spawn = (
        "import subprocess, sys, time; "
        "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
        f"open({str(child)!r}, 'w').write(str(p.pid)); time.sleep(60)"
    )
    slow = f"{sys.executable} -c {shlex.quote(spawn)}"
    monkeypatch.setattr(before.check, "WITHIN", 1.5)
    monkeypatch.setattr(before.worktree, "installs", lambda _p, _scope: [(".", slow)])
    events = []
    shots = run(ui, tmp_path, events)
    assert shots.findings == [f"`{shlex.join(shlex.split(slow))}` took over 2 s"]
    installer = int(next(iter(events[0]["pids"])))
    assert gone(installer)
    assert gone(int(child.read_text()))
    assert worktrees(ui) == 1


def test_the_runner_records_the_before_capture_and_the_page_serves_it(ui, tmp_path):
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), ui)
    none = Preparation(id="none", kind="data-only", seed="true", cleanup="true", isolation={"APP_ENV": "test"})
    assert (
        store.save(
            store.config_path,
            Layer,
            lambda layer: layer.model_copy(update={"preparations": [none]}),
            "setup",
            owner=True,
        )
        == ""
    )
    prepare._write(store, "c1", prepare.Prepared(check=VISUAL, option=none))  # noqa: SLF001 - as the preparer chose
    captures.at_merge_base(store, Lock("c1"), ui, Path(ui.names.worktree))
    c = store.read("c1")
    assert (c.before.files, c.before.findings, before.due(c)) == (
        ["home-1280.png", "home-1920.png", "home-2400.png"],
        [],
        False,
    )
    client = TestClient(
        api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"}
    )
    ok = client.get("/api/next/changes/c1/before/home-1280.png")
    assert (ok.status_code, ok.content) == (200, b"before")
    assert client.get("/api/next/changes/c1").json()["before"]["head"] == c.before.head
    for name in ("other-1280.png", "..%2Fhome-1280.png"):
        assert client.get(f"/api/next/changes/c1/before/{name}").status_code == 404


@pytest.mark.parametrize("site", ["merge-base", "test-copy", "capture"])
def test_a_before_capture_that_fails_keeps_its_whole_error(ui, tmp_path, monkeypatch, site, whole_error):
    """#895 K4: before :113, :71 and :135 keep the whole failure, a git command's whole stderr included."""
    failed = subprocess.CalledProcessError(1, "git merge-base", stderr=whole_error)
    real, prepare = before.worktree.git, None

    def git_failing(cwd, *args):
        if args[0] == "merge-base":
            raise failed
        return real(cwd, *args)

    def raising(*_a, **_k):
        raise (RuntimeError(whole_error) if site == "test-copy" else failed)

    if site == "merge-base":
        monkeypatch.setattr(before.worktree, "git", git_failing)
    elif site == "capture":
        monkeypatch.setattr(visual, "CAPTURE", raising)
    else:
        prepare = raising
    shots = before.capture(
        ui, Path(ui.names.worktree), lambda b: tmp_path / "out" / b[:7], Profile(), [].append, widths=(1280,),
        prepare=prepare,
    )  # fmt: skip
    git_error = f"CalledProcessError: Command 'git merge-base' returned non-zero exit status 1.\n{whole_error}"
    expected = {
        "merge-base": f"the merge-base could not be read: {git_error}",
        "test-copy": f"the test copy at the merge-base: RuntimeError: {whole_error}",
        "capture": git_error,
    }
    assert shots.findings == [expected[site]]
