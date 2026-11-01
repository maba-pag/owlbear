"""A step's processes found by hierarchy (#752): real shells leave real survivors, and only members are read."""

import contextlib
import os
import signal
import subprocess
import time
from pathlib import Path

import psutil

from owlbear_delivery_next.local_system import processes
from owlbear_delivery_next.workflow_steps import check

SLEEP = "sleep 300 >/dev/null 2>&1"


def shell(script: str) -> list[int]:
    """Run *script* under bash leading a new session; the pids it prints, its own first."""
    argv = ["/bin/bash", "-c", f"echo $$; {script}"]
    out = subprocess.run(argv, check=True, start_new_session=True, capture_output=True, text=True, timeout=10)  # noqa: S603
    return [int(x) for x in out.stdout.split()]


def end(pids: list[int]) -> None:
    for p in pids:
        with contextlib.suppress(OSError):
            os.kill(p, signal.SIGKILL)


def test_every_leftover_of_a_marked_command_is_found() -> None:
    leader, *left = shell(
        f"{SLEEP} & echo $!; nohup {SLEEP} & echo $!; ( {SLEEP} & echo $! ); env -i {SLEEP} & echo $!; "
        f"set -m; {SLEEP} & echo $!"
    )
    try:
        assert len(left) == 5
        job = left[-1]
        assert (os.getpgid(job), os.getsid(job)) == (job, leader)  # the job leads its own group, in the session
        bound = time.time()
        assert set(processes.members({leader: bound})) == set(left)
    finally:
        end(left)


def test_a_job_left_by_a_recorded_leader_is_found_by_its_session(tmp_path: Path) -> None:
    events: list[dict] = []
    job = tmp_path / "job"
    argv = ["/bin/bash", "-c", f'set -m; {SLEEP} & echo $! > "{job}"']
    assert check.run(argv, tmp_path, events.append) == ""
    pid = int(job.read_text())
    try:
        ((leader, born),) = ((int(p), t) for p, t in events[0]["pids"].items())
        assert os.getpgid(pid) != leader
        assert os.getsid(pid) == leader
        assert set(processes.members({leader: born})) == {pid}
    finally:
        end([pid])


def test_a_member_of_a_recycled_group_still_counts_by_its_session() -> None:
    group = subprocess.Popen(  # noqa: S603 - a recorded session whose job leads its own group
        ["/bin/bash", "-c", f"set -m; {SLEEP} & echo $!; wait"],
        start_new_session=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    job = int(group.stdout.readline())
    try:
        assert (os.getpgid(job), os.getsid(job)) == (job, group.pid)
        found = processes.members({job: 0.0, group.pid: time.time()})  # 0.0: the job's group id reads as recycled
        assert set(found) == {group.pid, job}
    finally:
        end([job, group.pid])
        group.wait()


def test_only_pgid_and_sid_are_read_for_non_members(monkeypatch) -> None:
    member = subprocess.Popen(["/bin/sleep", "300"], start_new_session=True)
    unrelated = subprocess.Popen(["/bin/sleep", "300"], start_new_session=True)
    group = subprocess.Popen(  # noqa: S603 - a leader whose child leads nothing
        ["/bin/bash", "-c", f"{SLEEP} & echo $!; wait"], start_new_session=True, stdout=subprocess.PIPE, text=True
    )
    non_leader = int(group.stdout.readline())
    read: list[int] = []

    class Spy(psutil.Process):
        def __init__(self, pid: int) -> None:
            read.append(pid)
            super().__init__(pid)

    try:
        with monkeypatch.context() as m:
            m.setattr(psutil, "Process", Spy)
            found = processes.members({member.pid: time.time(), non_leader: 0.0})  # 0.0: any start reads as newer
        assert set(found) == {member.pid}
        assert set(read) == {member.pid}  # the others, the recorded non-leader too, gave only their pgid and sid
    finally:
        end([member.pid, unrelated.pid, non_leader, group.pid])
        for proc in (member, unrelated, group):
            proc.wait()
