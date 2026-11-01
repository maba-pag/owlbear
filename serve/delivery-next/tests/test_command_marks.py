"""A runner's step marks what it starts (#752): its sessions' shell commands and its remote Git leaders."""

import asyncio
import contextlib
import contextvars
import os
import signal
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts.models import Change, Step, StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.tools import Worktree
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.git import remote_git
from owlbear_delivery_next.project_host.host import Host
from owlbear_delivery_next.runtimes import command_marks, sdk_adapter
from owlbear_delivery_next.state_store.store import Store


class _Session:
    def __init__(self, scripts: list[str]) -> None:
        self.scripts = scripts
        self.rpc = SimpleNamespace(instructions=SimpleNamespace(get_sources=self._sources),
                                   options=SimpleNamespace(update=self._update))  # fmt: skip

    async def _sources(self):
        return SimpleNamespace(sources=[])

    async def _update(self, params):
        self.scripts += [s.path for s in params.shell.init_scripts]
        return SimpleNamespace(success=True)

    async def send(self, _message, **_extra):
        self.scripts.append("send")


def _open(work: Path, kind: StepKind, role: str = "") -> list[str]:
    """The real opening of one session of *kind*, as the step's factory makes it; what it was given, in order."""
    scripts: list[str] = []
    cfg = sdk_adapter.Session(
        kind=kind, role=role, worktree=work, session_id="sid", message="go", resume=False, policy=Policy(work),
        observe=Worktree, checks=(), model="gpt-6-luna", journal=sdk_adapter.Journal(delivered=lambda: None),
    )  # fmt: skip

    async def scenario():
        st = sdk_adapter._Step(cfg, asyncio.get_running_loop())  # noqa: SLF001 - the real opening under test
        client = SimpleNamespace(create_session=lambda **_: asyncio.sleep(0, _Session(scripts)))
        await sdk_adapter._open(client, st)  # noqa: SLF001

    asyncio.run(scenario())
    return scripts


def _git(cwd: Path, *args: str) -> str:
    out = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return out.stdout.strip()


def _push(work: Path, remote: Path, ref: str) -> None:
    remote_git.run_remote_git(work, ["push", str(remote), f"HEAD:refs/heads/{ref}"], kind="write")


def test_a_runner_step_marks_its_sessions_and_journals_its_pushes(change_repo, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sdk_adapter, "session_options", command_marks.opened)  # undo conftest's no-op
    store = Store.open(change_repo)
    with store.lock("c1") as lock:
        store.write(
            lock, Change(slug="c1", step=Step(kind=StepKind.BUILD, started_at=datetime.now(UTC) - timedelta(seconds=5)))
        )
    remote, left = tmp_path / "remote.git", tmp_path / "left"
    _git(tmp_path, "init", "-q", "--bare", str(remote))
    hook = change_repo / _git(change_repo, "rev-parse", "--git-path", "hooks/pre-push")
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(f'#!/bin/sh\nsleep 300 </dev/null >/dev/null 2>&1 &\necho $! >> "{left}"\n')
    hook.chmod(0o755)
    opened: list[list[str]] = []

    def step(*_a) -> None:
        opened.extend([_open(change_repo, StepKind.BUILD), _open(change_repo, StepKind.PLAN, "challenger")])
        _push(change_repo, remote, "marked")

    def failing(*_a) -> None:
        msg = "the step failed"
        raise RuntimeError(msg)

    script = str(store.root / "changes" / "c1" / command_marks.SCRIPT)
    try:
        monkeypatch.setattr(runner, "_step", step)
        contextvars.copy_context().run(runner.main, ["c1", "--repo", str(change_repo)])
        assert opened == [[script, "send"], [script, "send"]]  # each session's script comes before its first message
        sleep = int(left.read_text().split()[0])
        journaled = {int(p) for e in store.events("c1") if e["event"] == "pids" for p in e["pids"]}
        assert os.getsid(sleep) in journaled  # Git's leader, whose session the hook's leftover is in
        assert (command_marks._active, remote_git.launched) == ([], None)  # noqa: SLF001 - nothing outlives the runner
        host = Host(store, change_repo, spawn=lambda _s: pytest.fail("a runner started beside the leftover"))
        host.say = lambda _text: None
        assert host.tick() == []
        assert str(sleep) in store.read("c1").blocked.action

        monkeypatch.setattr(runner, "_step", failing)
        with pytest.raises(RuntimeError, match="the step failed"):
            contextvars.copy_context().run(runner.main, ["c1", "--repo", str(change_repo)])
        assert (command_marks._active, remote_git.launched) == ([], None)  # noqa: SLF001

        before = len(store.events("c1"))
        assert _open(change_repo, StepKind.BUILD) == ["send"]  # outside a runner nothing marks commands
        _push(change_repo, remote, "unmarked")
        assert len(store.events("c1")) == before
    finally:
        for pid in left.read_text().split() if left.exists() else []:
            with contextlib.suppress(OSError):
                os.kill(int(pid), signal.SIGKILL)


@contextlib.contextmanager
def _zone(name: str):
    old = os.environ.get("TZ")
    os.environ["TZ"] = name
    time.tzset()
    try:
        yield
    finally:
        if old is None:
            del os.environ["TZ"]
        else:
            os.environ["TZ"] = old
        time.tzset()


def test_a_mark_in_new_yorks_repeated_hour_keeps_its_instant(tmp_path) -> None:
    second = datetime(2025, 11, 2, 6, 30, tzinfo=UTC)  # the second 01:30 in New York that night
    (tmp_path / command_marks.FILE).write_text(f"77 {second.strftime(command_marks.LSTART)}\n")
    with _zone("America/New_York"):
        assert command_marks.read(tmp_path, second) == {77: second.timestamp() + 1}


def test_a_shell_in_another_zone_marks_its_start_as_the_host_reads_it(change_repo) -> None:
    store = Store.open(change_repo)
    with store.lock("c1") as lock:
        store.write(lock, Change(slug="c1"))
        with command_marks.marking(store, lock, "c1"):
            script = command_marks.folder(store, "c1") / command_marks.SCRIPT
            env = {**os.environ, "TZ": "Pacific/Kiritimati"}  # UTC+14, the CLI's shell zone unlike the host's
            began = time.time()
            argv = ["/bin/bash", "-c", f'. "{script}"; echo $$']
            out = subprocess.run(  # noqa: S603
                argv, env=env, check=True, capture_output=True, text=True, timeout=30, start_new_session=True
            )
    marks = command_marks.read(command_marks.folder(store, "c1"), datetime.fromtimestamp(began, UTC))
    assert list(marks) == [int(out.stdout)]
    assert began < marks[int(out.stdout)] < time.time() + 2
