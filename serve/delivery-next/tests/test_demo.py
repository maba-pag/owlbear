"""``owlbear demo``'s data boundary: it serves its example world, never the owner's HOME, data or Copilot folder."""

from __future__ import annotations

import gc
import json
import os
import socket
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

from owlbear_delivery_next.change_contracts.models import Change
from owlbear_delivery_next.git.git_executable import resolve_git_executable
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.machine_host import command, demo, demo_home
from owlbear_delivery_next.state_store import project_home, registry
from owlbear_delivery_next.state_store.store import Lock, Store

TRAP = "sentinel"
CHILD = """import sys, types
from owlbear_delivery_next.machine_host import command
command.sys = types.SimpleNamespace(**{**vars(sys), "platform": "darwin"})  # CI runs on Linux
sys.exit(command.main([sys.argv[1], "--port", sys.argv[2]]))
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
    Store(project_home.located(clone)).write(Lock(change.slug), change)
    gc.collect()  # the store's connection closes: its database is checkpointed before the snapshot
    for place in (home / ".owlbear" / "data", data):
        (place / "config.json").parent.mkdir(parents=True, exist_ok=True)
        (place / "config.json").write_text(json.dumps({"format": 1, "github_account": TRAP}) + "\n")
        _repo(place, f"https://github.com/{TRAP}/{TRAP}-data.git")
    line = {"id": f"start:{TRAP}", "type": "start", "at": datetime.now(UTC).isoformat(), "run": TRAP, "agent": TRAP}
    (home / ".owlbear" / "spend").mkdir()
    (home / ".owlbear" / "spend" / f"spend-{datetime.now(UTC):%Y-%m}.jsonl").write_text(json.dumps(line) + "\n")
    for folder in (home / ".copilot", copilot):
        (folder / "session-state" / f"{TRAP}-session").mkdir(parents=True)
        (folder / "session-state" / f"{TRAP}-session" / "events.jsonl").write_text('{"type": "sentinel"}\n')


def _files(*roots: Path) -> dict[Path, bytes]:
    return {p: p.read_bytes() for root in roots for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink()}


def _get(url: str, token: str = "") -> str:
    answer = httpx.get(url, headers={"authorization": f"Bearer {token}"} if token else {}, timeout=10)
    answer.raise_for_status()
    return answer.text


def test_the_demo_serves_example_data_and_never_the_owners(tmp_path, monkeypatch) -> None:
    home, data, copilot, tmp = (tmp_path / n for n in ("owner-home", "owner-data", "owner-copilot", "tmp"))
    _owner(home, data, copilot, monkeypatch)
    marker, tools = tmp_path / "gh-was-called", tmp_path / "owner-bin"
    tools.mkdir()
    tmp.mkdir()
    (tools / "gh").write_text(f"#!/bin/sh\ntouch {marker}\nexit 1\n")
    (tools / "gh").chmod(0o755)
    before = _files(home, data, copilot)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = os.environ | {"HOME": str(home), "OWLBEAR_DATA": str(data), "COPILOT_HOME": str(copilot),
                        "TMPDIR": str(tmp), "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}"}  # fmt: skip
    child = subprocess.Popen(  # noqa: S603 - this interpreter runs the real command, no shell
        [sys.executable, "-c", CHILD, command.demo.__name__, str(port)],  # the command `demo` registers
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    said, stream = [], child.stdout
    try:
        while stream and not any("#token=" in s for s in said):
            said.append(stream.readline())
            assert said[-1], "".join(said)
        base, _, token = next(s for s in said if "#token=" in s).split()[-1].partition("/#token=")
        assert base == f"http://127.0.0.1:{port}"
        [ran] = list(tmp.glob("owlbear-demo-*"))
        answers = [_get(f"{base}/"), _get(f"{base}/api/next/projects", token)]
        projects = json.loads(answers[1])["projects"]
        configs = [_get(f"{base}/p/{p['id']}/api/next/config", token) for p in projects]
        for p in projects:
            answers += [
                _get(f"{base}/p/{p['id']}/api/next/{r}", token) for r in ("changes", "config/read", "config/models")
            ]
        auth = {"authorization": f"Bearer {token}"}
        refused = httpx.post(f"{base}/p/{projects[0]['id']}/api/next/config/read", headers=auth)
        stored = _files(ran)
        offline = subprocess.run(  # noqa: S603 - fixture git argv
            [resolve_git_executable(), "ls-remote", "https://github.com/example/example-shop.git"],
            env={"HOME": str(ran), "PATH": os.environ["PATH"]}, capture_output=True, text=True, check=False,
        )  # fmt: skip
    finally:
        child.terminate()
        out, _ = child.communicate(timeout=20)
    assert [str(p) for p, b in stored.items() if TRAP.encode() in b] == []
    assert [a for a in [*answers, *configs, "".join(said), out] if TRAP in a] == []
    after = _files(home, data, copilot)
    assert [str(p) for p in sorted(before.keys() | after.keys()) if before.get(p) != after.get(p)] == []
    assert (marker.exists(), demo_home.OFFLINE in offline.stderr, ran.exists()) == (False, True, False)
    assert [(p["name"], p["unset"], p["blocked"]) for p in projects] == [
        (name, [], "") for name, _ in demo_home.PROJECTS
    ]
    assert [json.loads(c)["notice"] for c in configs] == ["", ""]
    assert (refused.status_code, refused.json()["detail"]) == (403, demo.REFUSED)
    assert answers[0].index("sessionStorage.setItem") < answers[0].index('type="module"')
