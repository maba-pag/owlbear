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
from owlbear_delivery_next.change_contracts.visual_records import PageError
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import before, check, prepare, visual

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
HOME = VisualState(name="home", path="/", expect="The greeting is centred")
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def git(cwd, *args):
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


def commit(work, name, text):
    (work / name).parent.mkdir(parents=True, exist_ok=True)
    (work / name).write_text(text)
    git(work, "add", name)
    git(work, "commit", "-q", "-m", f"edit {name}")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(autouse=True)
def git_env(tmp_path, monkeypatch):
    (tmp_path / "gitconfig").write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")


@pytest.fixture
def ui(tmp_path, monkeypatch):
    """A Change whose page says "before" at the merge-base and "after" at its head, at the visual check."""
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(work))
    commit(work, "site/index.html", "before")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/main")
    git(work, "switch", "-q", "-c", "owlbear/c1")
    commit(work, "site/index.html", "after")
    port = free_port()
    command = f"{sys.executable} -m http.server {port} --bind 127.0.0.1"
    env = Environment(check=VISUAL, command=command, directory="site", ready_url=f"http://127.0.0.1:{port}/")
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


def test_due_only_once_before_the_visual_preview_starts(ui):
    assert before.due(ui)
    assert not before.due(ui.model_copy(update={"env": ui.env.model_copy(update={"launched_at": NOW})}))
    assert not before.due(ui.model_copy(update={"step": Step(kind=StepKind.CHECK, task="look")}))
    assert not before.due(ui.model_copy(update={"brief": Brief(version=1, ui=True)}))


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
    assert (check.answers(ui.env.ready_url), worktrees(ui)) == (False, 1)


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

    port = int(ui.env.ready_url.rsplit(":", 1)[1].strip("/"))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        events = []
        shots = run(ui, tmp_path, events)
    finally:
        server.shutdown()
    assert (shots.files, shots.findings, events) == ([], [f"something else already answers at {ui.env.ready_url}"], [])


def test_a_recipe_that_never_answers_is_a_note_and_its_processes_are_stopped(ui, tmp_path, monkeypatch):
    monkeypatch.setattr(check, "READY_WITHIN", 1.0)
    command = f"{sys.executable} -c 'import time; time.sleep(60)'"
    ui.env = ui.env.model_copy(update={"command": command})
    events = []
    shots = run(ui, tmp_path, events)
    assert (shots.files, shots.findings) == (
        [],
        [f"the recipe did not answer at {ui.env.ready_url} for the merge-base"],
    )
    pid = int(next(iter(events[0]["pids"])))
    assert not (psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE)
    assert worktrees(ui) == 1


def gone(pid):
    return not (psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE)


def test_a_capture_that_raises_still_stops_the_preview_and_removes_the_worktree(ui, tmp_path, monkeypatch):
    def broken(_base, _states, _out, _widths, **_k):
        missing = "no Chromium"
        raise RuntimeError(missing)

    monkeypatch.setattr(visual, "CAPTURE", broken)
    events = []
    shots = run(ui, tmp_path, events)
    assert (shots.files, shots.findings) == ([], ["RuntimeError: no Chromium"])
    assert all(gone(int(p)) for e in events for p in e["pids"])
    assert (check.answers(ui.env.ready_url), worktrees(ui)) == (False, 1)


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
    store.update_config(lambda layer: layer.model_copy(update={"preparations": [none]}))
    prepare._write(store, "c1", prepare.Prepared(check=VISUAL, option=none))  # noqa: SLF001 - as the preparer chose
    runner._before(store, Lock("c1"), ui, Path(ui.names.worktree))  # noqa: SLF001
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
