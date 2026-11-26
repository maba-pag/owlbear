"""``owlbear demo``'s data boundary: it serves its example world, never the owner's HOME, data or Copilot folder."""

from __future__ import annotations

import contextlib
import gc
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytest

from owlbear_delivery_next.change_contracts.models import Change
from owlbear_delivery_next.git.git_executable import resolve_git_executable
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.machine_host import command, demo, demo_backlog, demo_changes, demo_home, demo_metrics
from owlbear_delivery_next.state_store import project_home, registry
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from collections.abc import Callable

TRAP = "sentinel"
CHILD = """import sys, types
from owlbear_delivery_next.machine_host import command
command.sys = types.SimpleNamespace(**{**vars(sys), "platform": "darwin"})  # CI runs on Linux
sys.exit(command.main([sys.argv[1]]))
"""


def _git(path: Path, *args: str) -> None:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run([resolve_git_executable(), *who, "-C", str(path), *args], check=True, capture_output=True)  # noqa: S603


def _repo(path: Path, origin: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "-b", "main")
    _git(path, "remote", "add", "origin", origin)
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "--allow-empty", "-m", TRAP)
    return path


def _owner(home: Path, data: Path, copilot: Path, monkeypatch) -> None:
    """The owner's places as a running OwlBear leaves them, each holding ``sentinel``."""
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(local_home, "root", lambda: home / ".owlbear")
    clone = _repo(home / "projects" / f"{TRAP}-project", f"https://github.com/{TRAP}/{TRAP}-project.git")
    registry.register(clone)
    fixture = Path(__file__).parent / "fixtures" / "c1_v4_waiting.json"
    change = Change.model_validate_json(fixture.read_text()).model_copy(update={"slug": f"{TRAP}-change"})
    store = Store(project_home.located(clone))
    with store.lock(change.slug) as lock:  # its persisted writer-lock file stays in the owner's home
        store.write(lock, change)
    for place in (home / ".owlbear" / "data", data):
        (place / "config.json").parent.mkdir(parents=True, exist_ok=True)
        (place / "config.json").write_text(json.dumps({"format": 1, "github_account": TRAP}) + "\n")
        _repo(place, f"https://github.com/{TRAP}/{TRAP}-data.git")
    trap = {"run": f"{TRAP}-run", "session": f"{TRAP}-session", "project": f"{TRAP}-project", "agent": TRAP}
    at = datetime.now(UTC).isoformat(timespec="seconds")
    ledger = "".join(
        json.dumps(trap | line) + "\n"
        for line in (
            {"id": f"start:{TRAP}", "type": "start", "at": at, "model": f"{TRAP}-model", "before": {}},
            {
                "id": f"end:{TRAP}",
                "type": "end",
                "at": at,
                "usage": {"credits": 99.0, "models": {}},
                "tools": {f"{TRAP}_tool": {"calls": 1}},
                "wrong": {},
            },
        )
    )
    for spend in (home / ".owlbear" / "spend", data / "spend"):
        spend.mkdir(parents=True)
        (spend / f"spend-{datetime.now(UTC):%Y-%m}.jsonl").write_text(ledger)
    for folder in (home / ".copilot", copilot):
        (folder / "session-state" / f"{TRAP}-session").mkdir(parents=True)
        (folder / "session-state" / f"{TRAP}-session" / "events.jsonl").write_text('{"type": "sentinel"}\n')


def _files(*roots: Path) -> dict[Path, bytes]:
    return {p: p.read_bytes() for root in roots for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink()}


def _get(url: str, token: str = "") -> str:
    answer = httpx.get(url, headers={"authorization": f"Bearer {token}"} if token else {}, timeout=10)
    answer.raise_for_status()
    return answer.text


class Child:
    """The demo's process and what it printed, read on a thread so the test never blocks on it."""

    def __init__(self, child: subprocess.Popen[str]) -> None:
        self.child, self.lines, self.said = child, queue.Queue[str](), list[str]()
        self.reader = threading.Thread(target=lambda: [self.lines.put(s) for s in child.stdout or ()], daemon=True)
        self.reader.start()

    def stop(self) -> None:
        """Stop and reap the child, then keep the rest of what it printed."""
        self.child.terminate()
        try:
            self.child.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.child.kill()
            self.child.wait()
        self.reader.join(timeout=5)
        while not self.lines.empty():
            self.said.append(self.lines.get())

    def wait[T](self, ready: Callable[[], T | None], seconds: float) -> T:
        """*ready*'s first answer within *seconds*, collecting the output; else the child is stopped and reaped."""
        deadline = time.monotonic() + seconds
        while (found := ready()) is None:
            if self.child.poll() is not None or time.monotonic() > deadline:
                self.stop()
                pytest.fail(f"the demo did not start (exit {self.child.returncode}):\n{''.join(self.said)}")
            with contextlib.suppress(queue.Empty):
                self.said.append(self.lines.get(timeout=0.2))
        return found


def _answer(url: str) -> str | None:
    try:
        return _get(url)
    except httpx.TransportError:
        return None


def test_the_demo_serves_example_data_and_never_the_owners(tmp_path, monkeypatch) -> None:
    home, data, copilot, tmp = (tmp_path / n for n in ("owner-home", "owner-data", "owner-copilot", "tmp"))
    _owner(home, data, copilot, monkeypatch)
    gc.collect()  # the fixture's store is unreachable now: its connection closes and checkpoints before the snapshot
    marker, tools = tmp_path / "gh-was-called", tmp_path / "owner-bin"
    tools.mkdir()
    tmp.mkdir()
    (tools / "gh").write_text(f"#!/bin/sh\ntouch {marker}\nexit 1\n")
    (tools / "gh").chmod(0o755)
    before = _files(home, data, copilot)
    env = os.environ | {"HOME": str(home), "OWLBEAR_DATA": str(data), "COPILOT_HOME": str(copilot),
                        "TMPDIR": str(tmp), "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}"}  # fmt: skip
    demo_run = Child(
        subprocess.Popen(  # noqa: S603 - this interpreter runs the real command, no shell
            [sys.executable, "-c", CHILD, command.demo.__name__],  # the command `demo` registers, on its default port
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    )
    said = demo_run.said
    try:
        printed = demo_run.wait(lambda: next((s for s in said if "#token=" in s), None), 60)
        base, _, token = printed.split()[-1].partition("/#token=")
        assert re.fullmatch(r"http://127\.0\.0\.1:[1-9]\d*", base), printed
        answers = [demo_run.wait(lambda: _answer(f"{base}/"), 30)]  # it prints before it listens
        [ran] = list(tmp.glob("owlbear-demo-*"))
        answers.append(_get(f"{base}/api/next/projects", token))
        projects = json.loads(answers[1])["projects"]
        configs = [_get(f"{base}/p/{p['id']}/api/next/config", token) for p in projects]
        for p in projects:
            answers += [
                _get(f"{base}/p/{p['id']}/api/next/{r}", token) for r in ("changes", "config/read", "config/models")
            ]
        ids = {p["name"]: p["id"] for p in projects}
        details = [_get(f"{base}/p/{ids[p]}/api/next/changes/{s}", token) for p, s in demo_changes.CHANGES]
        spend = _files(ran / ".owlbear" / "spend")
        metrics = {by: _get(f"{base}/api/next/metrics?by={by}", token) for by in ("agent", "model", "step", "day")}
        backlogs = [_get(f"{base}/p/{p['id']}/api/next/backlog", token) for p in projects]
        links = [_get(f"{base}/metrics?period=all&by=agent"), _get(f"{base}/backlog?reviews=open")]  # no token
        reconciled = [json.loads(m)["coverage"]["reconcile"]["state"] for m in metrics.values()]
        spent = _files(ran / ".owlbear" / "spend")
        refused = httpx.post(
            f"{base}/p/{projects[0]['id']}/api/next/config/read", headers={"authorization": f"Bearer {token}"}
        )
        stored = _files(ran)
        offline = subprocess.run(  # noqa: S603 - fixture git argv
            [resolve_git_executable(), "ls-remote", "--get-url", "https://github.com/example/example-shop.git"],
            cwd=ran, env={"HOME": str(ran), "PATH": os.environ["PATH"]}, capture_output=True, text=True, check=False,
        )  # fmt: skip
    finally:
        demo_run.stop()
    assert [str(p) for p, b in stored.items() if TRAP.encode() in b] == []
    shown = [*answers, *configs, *metrics.values(), *backlogs, *links, *details, "".join(said)]
    assert [a for a in shown if TRAP in a] == []
    assert [json.loads(d)["slug"] for d in details] == [s for _, s in demo_changes.CHANGES]
    after = _files(home, data, copilot)
    assert [str(p) for p in sorted(before.keys() | after.keys()) if before.get(p) != after.get(p)] == []
    assert any(p.name == "lock" and p.parent.name == f"{TRAP}-change" for p in before), "the writer lock is compared"
    assert (marker.exists(), offline.stdout.startswith(demo_home.OFFLINE), ran.exists()) == (False, True, False)
    assert ("running" in reconciled, spent) == (False, spend)
    assert [(p["name"], p["unset"], p["blocked"]) for p in projects] == [
        (name, [], "") for name, _ in demo_home.PROJECTS
    ]
    assert [json.loads(c)["notice"] for c in configs] == ["", ""]
    assert (refused.status_code, refused.json()["detail"]) == (403, demo.REFUSED)
    assert answers[0].index("sessionStorage.setItem") < answers[0].index('type="module"')
    _scenarios({by: json.loads(m) for by, m in metrics.items()}, projects, json.loads(backlogs[0]), links)


def _scenarios(found: dict[str, dict], projects: list[dict], backlog: dict, links: list[str]) -> None:
    """Both deep links' scripts in order, and the scenarios' rows under the served example projects."""
    page, unfolding = links
    assert page.index("sessionStorage.setItem") < page.index('type="module"')  # before the page asks the host
    assert (
        unfolding.index("sessionStorage.setItem")
        < unfolding.index(demo_backlog.OPEN)
        < unfolding.index('type="module"')
    )
    entries = backlog["entries"]
    reviews = [e["status"] for e in entries if e["suppression_review"]]
    assert (reviews.count("inbox") >= 3, set(reviews)) == (True, {"inbox", "open", "dropped"})
    assert {e["origin"] for e in entries} == {demo_home.PROJECTS[0][0]}  # every review links to the example shop
    assert [e for e in entries if e["status"] == "inbox" and not e["suppression_review"]] != []
    least = {"agent": 8, "model": 3, "step": 3, "day": 14}
    assert [by for by, n in least.items() if len(found[by]["rows"]) < n] == []
    choices = found["agent"]["choices"]
    assert (choices["projects"], choices["clones"]) == (
        sorted([[p["name"], p["name"]] for p in projects]),
        {p["id"]: p["name"] for p in projects},
    )
    tools = found["agent"]["tool_use"]
    outcomes = ("accepted", "invalid", "checks", "order", "unsplit", "lint", "late")
    assert len(tools["tools"]) >= 6
    assert [k for k in outcomes if not tools["totals"][k]] == []
    compaction = found["agent"]["compaction"]["rows"]
    assert len({r["agent"] for r in compaction if r["shares"]}) >= 3
    assert [r["agent"] for r in compaction if r["unshared"] and r["project"]] == ["builder"]
    assert [r["agent"] for r in compaction if r["logs"] and not r["compacted"] and r["project"]] != []
    context = {r["role"]: r for r in found["agent"]["context"]["roles"]}
    assert [r for r, x in context.items() if not x["latest"]] == ["updater"]
    assert {(x["latest"]["project"], x["latest"]["tier"]) for x in context.values() if x["latest"]} == {
        (p["name"], demo_metrics.TIER) for p in projects
    }
    assert [r for r, x in context.items() if x["errors"]] == ["preparer"]
    assert [r for r, x in context.items() if (x["latest"] or {}).get("kept") == demo_metrics.KEPT] == ["reviewer"]
