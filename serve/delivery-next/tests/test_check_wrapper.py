"""The check launch's pid file (#752): a host that stops before recording the group finds it; no recipe runs."""

import contextlib
import os
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import psutil
import pytest

from owlbear_delivery_next.change_contracts.models import Environment
from owlbear_delivery_next.local_system import processes
from owlbear_delivery_next.workflow_steps import check


def env(command: str, **kw) -> Environment:
    return Environment(check="preview", command=command, directory=".", ready_url="http://127.0.0.1:9/", **kw)


def waited(path: Path) -> str:
    end = time.monotonic() + 10
    while not (text := path.read_text().strip() if path.exists() else "") and time.monotonic() < end:
        time.sleep(0.05)
    return text


def test_the_pid_written_is_the_recipes_after_exec(tmp_path: Path) -> None:
    pidfile = tmp_path / check.PIDFILE
    pidfile.write_text("1\n")  # an earlier launch's file is removed first
    proc = check.start(env("sleep 300"), tmp_path, tmp_path / "env.log", None, pidfile)
    assert proc is not None
    check.release(proc)
    try:
        assert int(waited(pidfile)) == proc.pid
        end = time.monotonic() + 10
        while psutil.Process(proc.pid).cmdline() != ["sleep", "300"] and time.monotonic() < end:
            time.sleep(0.05)
        assert psutil.Process(proc.pid).cmdline() == ["sleep", "300"]
    finally:
        proc.kill()


def test_a_recipe_never_runs_without_its_pid_file(tmp_path: Path) -> None:
    ran = tmp_path / "ran"
    proc = check.start(env(f"touch {ran}"), tmp_path, tmp_path / "env.log", None, tmp_path / "gone" / check.PIDFILE)
    assert proc is not None
    assert proc.wait(10) != 0
    assert not ran.exists()


def test_a_recipe_never_runs_when_its_host_stops_before_recording_the_group(tmp_path: Path) -> None:
    ran, pidfile = tmp_path / "ran", tmp_path / check.PIDFILE
    proc = check.start(env(f"touch {ran}"), tmp_path, tmp_path / "env.log", None, pidfile)
    assert proc is not None
    assert int(waited(pidfile)) == proc.pid
    time.sleep(0.5)
    assert not ran.exists()
    proc.stdin.close()  # what a host's exit does to the pipe
    assert proc.wait(10) != 0
    assert not ran.exists()


def test_an_install_runs_only_once_its_pid_is_journaled(tmp_path: Path) -> None:
    ran = tmp_path / "ran"

    def log(_event) -> None:
        time.sleep(1.0)  # an unjournaled install would have run by now
        assert not ran.exists()
        msg = "the runner died"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="the runner died"):
        check.run(["touch", str(ran)], tmp_path, log)
    time.sleep(0.5)
    assert not ran.exists()


def test_an_install_over_time_is_killed_though_the_process_table_is_unreadable(tmp_path: Path, monkeypatch) -> None:
    def unlisted(_ids):
        msg = "the process table cannot be listed"
        raise processes.UnlistedError(msg)

    pid = tmp_path / "pid"
    monkeypatch.setattr(check, "WITHIN", 1.0)
    monkeypatch.setattr(processes, "members", unlisted)
    note = check.run(["/bin/sh", "-c", f'echo $$ > "{pid}"; exec sleep 60'], tmp_path, lambda _e: None)
    leader = int(waited(pid))
    try:
        assert note.endswith("took over 1 s")
        assert not psutil.pid_exists(leader) or psutil.Process(leader).status() == psutil.STATUS_ZOMBIE
    finally:
        with contextlib.suppress(OSError):
            os.kill(leader, signal.SIGKILL)


def test_an_unlisted_table_while_awaiting_readiness_is_polled_again(monkeypatch) -> None:
    calls: list[int] = []

    def members(pgid: int, _leader: float | None = None) -> dict[int, str]:
        calls.append(pgid)
        if len(calls) == 1:
            msg = "the process table could not be listed"
            raise processes.UnlistedError(msg)
        return {pgid: "sleep"}

    monkeypatch.setattr(check, "answers", lambda _url: True)
    monkeypatch.setattr(check, "members", members)
    monkeypatch.setattr(check, "created", lambda _pid: 2.0)
    proc = SimpleNamespace(pid=900, returncode=None)
    assert check.ready(env("sleep 300"), proc) == {900: 2.0}
    assert calls == [900, 900]


def leaderless(tmp_path: Path, shell: str) -> tuple[Environment, list[int]]:
    """A launch whose leader exited and left two sleeps in its session, recovered from its pid file."""
    first, second = tmp_path / "first", tmp_path / "second"
    jobs = f"sleep 300 >/dev/null 2>&1 & echo $! > {first}; sleep 301 >/dev/null 2>&1 & echo $! > {second}'"
    e = env(f"{shell}{jobs}", launched_at=datetime.now(UTC))
    proc = check.start(e, tmp_path, tmp_path / "env.log", None, tmp_path / check.PIDFILE)
    assert proc is not None
    check.release(proc)
    proc.wait(10)
    sleeps = [int(waited(first)), int(waited(second))]
    assert all((os.getpgid(s) == proc.pid) == shell.startswith("sh ") for s in sleeps)
    found = check.recovered(e, tmp_path / check.PIDFILE)
    assert found.pgid == proc.pid
    return found, sleeps


@pytest.mark.parametrize("shell", ["sh -c '", "bash -c 'set -m; "])  # a job-control job runs in a group of its own
def test_a_leaderless_session_with_a_recorded_member_is_disposed_whole(tmp_path: Path, shell: str) -> None:
    e, sleeps = leaderless(tmp_path, shell)
    started = {s: psutil.Process(s).create_time() for s in sleeps}
    try:
        e = e.model_copy(update={"pids": e.pids | {sleeps[0]: started[sleeps[0]]}})  # as readiness records it
        assert check.dispose(e) == {}
        end = time.monotonic() + 5  # an exiting process has no group to list, yet psutil still sees it for a moment
        while any(processes.alive(s, t) for s, t in started.items()) and time.monotonic() < end:
            time.sleep(0.05)
        assert [processes.alive(s, t) for s, t in started.items()] == [False, False]
    finally:
        for s in sleeps:
            with contextlib.suppress(OSError):
                os.kill(s, signal.SIGKILL)


def test_a_leaderless_session_without_a_recorded_member_is_reported_not_signalled(tmp_path: Path, monkeypatch) -> None:
    e, sleeps = leaderless(tmp_path, "sh -c '")
    sent: list[int] = []
    try:
        with monkeypatch.context() as m:
            m.setattr(check, "GRACE", 0.1)
            m.setattr(os, "kill", lambda pid, _sig: sent.append(pid))
            m.setattr(os, "killpg", lambda pgid, _sig: sent.append(pgid))
            assert set(check.dispose(e)) == set(sleeps)  # its id may name another's session by now
        assert sent == []
    finally:
        for s in sleeps:
            with contextlib.suppress(OSError):
                os.kill(s, signal.SIGKILL)


def test_a_leader_without_a_recorded_start_proves_nothing(monkeypatch) -> None:
    leader = subprocess.Popen(["sh", "-c", "sleep 300 & wait"], start_new_session=True)  # noqa: S607
    sent: list[int] = []
    try:
        e = env("sleep 300", pgid=leader.pid, pids={leader.pid: None})  # its start time was unreadable at launch
        with monkeypatch.context() as m:
            m.setattr(check, "GRACE", 0.1)
            m.setattr(os, "kill", lambda pid, _sig: sent.append(pid))
            m.setattr(os, "killpg", lambda pgid, _sig: sent.append(pgid))
            assert leader.pid in check.dispose(e)  # its id may be another's by now
        assert sent == []
    finally:
        with contextlib.suppress(OSError):
            os.killpg(leader.pid, signal.SIGKILL)
        leader.wait(10)


def test_an_earlier_launchs_pid_file_is_ignored(tmp_path: Path) -> None:
    pidfile = tmp_path / check.PIDFILE
    pidfile.write_text(f"{os.getpid()}\n")
    e = env("sleep 300", launched_at=datetime.now(UTC))
    then = (e.launched_at - timedelta(seconds=60)).timestamp()
    os.utime(pidfile, (then, then))
    assert check.recovered(e, pidfile) is e
    assert check.recovered(e, tmp_path / "none") is e


@pytest.mark.parametrize("text", ["", "0", "-1", "x"])
def test_a_current_pid_file_without_a_process_id_is_refused(tmp_path: Path, text: str) -> None:
    pidfile = tmp_path / check.PIDFILE
    pidfile.write_text(text)
    with pytest.raises(ValueError, match="not a process id"):
        check.recovered(env("sleep 300", launched_at=datetime.now(UTC)), pidfile)


def test_a_reused_pid_is_never_signalled(tmp_path: Path, monkeypatch) -> None:
    code = "import subprocess, time; subprocess.Popen(['sleep', '300']); time.sleep(300)"
    other = subprocess.Popen([sys.executable, "-c", code], start_new_session=True)  # noqa: S603
    try:
        then = psutil.Process(other.pid).create_time() - 5
        pidfile = tmp_path / check.PIDFILE
        pidfile.write_text(f"{other.pid}\n")
        os.utime(pidfile, (then, then))
        e = env("sleep 300", launched_at=datetime.fromtimestamp(then, UTC))
        sent: list[tuple[str, int]] = []
        with monkeypatch.context() as m:
            m.setattr(os, "kill", lambda pid, _sig: sent.append(("kill", pid)))
            m.setattr(os, "killpg", lambda pgid, _sig: sent.append(("killpg", pgid)))
            assert processes.members({other.pid: then}) == {}
            found = check.recovered(e, pidfile)
            assert found.pgid == other.pid
            assert check.dispose(found) == {}
        assert sent == []
        assert other.poll() is None
    finally:
        with contextlib.suppress(OSError):
            os.killpg(other.pid, signal.SIGKILL)
        other.wait(10)
