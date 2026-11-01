"""The check launch's pid file (#752): a host that stops before recording the group finds it; no recipe runs."""

import contextlib
import os
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

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


@pytest.mark.parametrize("shell", ["sh -c '", "bash -c 'set -m; "])  # a job-control job runs in a group of its own
def test_a_launch_whose_leader_is_gone_is_disposed_from_its_pid_file(tmp_path: Path, shell: str) -> None:
    left = tmp_path / "left"
    e = env(f"{shell}sleep 300 >/dev/null 2>&1 & echo $! > {left}'", launched_at=datetime.now(UTC))
    proc = check.start(e, tmp_path, tmp_path / "env.log", None, tmp_path / check.PIDFILE)
    assert proc is not None
    check.release(proc)
    proc.wait(10)
    sleep = int(waited(left))
    started = psutil.Process(sleep).create_time()
    assert (os.getpgid(sleep) == proc.pid) == shell.startswith("sh ")
    try:
        found = check.recovered(e, tmp_path / check.PIDFILE)
        assert found.pgid == proc.pid
        assert check.dispose(found) == {}
        assert processes.alive(sleep, started) is False
    finally:
        with contextlib.suppress(OSError):
            os.kill(sleep, signal.SIGKILL)


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
