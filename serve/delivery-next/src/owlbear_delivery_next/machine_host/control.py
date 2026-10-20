"""What the ``owlbear`` command does to the machine host: start, stop, status, logs, doctor, login item, install.

The host runs detached from the shell that starts it; its log is ``~/.owlbear/host.log``. The login item and the
command link are written only with the owner's consent (TD-258, TD-260); nothing touches ``~/.zshrc``.
"""

from __future__ import annotations

import json
import os
import plistlib
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.machine_host import serve
from owlbear_delivery_next.project_host.api import link

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.project_host.host import HostRecord

LABEL = "com.owlbear.host"
LOG = "host.log"
WAIT = 20.0  # seconds a start waits for the host's address
STOPPING = 120.0  # seconds a stop waits: the drain, then the schedulers' current passes
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))
type Say = Callable[[str], None]


def plist_path() -> Path:
    """Where the login item lives."""
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def argv(*, run: bool = False) -> list[str]:
    """The machine host's process: this interpreter and the one dispatcher; paused unless *run*."""
    return [str(local_home.stable(Path(sys.executable))), "-m", "owlbear_delivery_next", "machine"] + ["--run"] * run


def start(say: Say, *, paused: bool = False) -> int:
    """Start the machine host in the background unless it runs; success only once its API answers."""
    child = None
    if serve.running() is None:
        home = local_home.root()
        home.mkdir(mode=0o700, parents=True, exist_ok=True)
        with (home / LOG).open("ab") as out:
            child = subprocess.Popen(  # noqa: S603 - this interpreter and a fixed module
                argv(run=not paused), cwd=home, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                start_new_session=True,
            )  # fmt: skip
    deadline = time.monotonic() + WAIT
    while time.monotonic() < deadline:
        if (listed := projects()) is not None:  # an API answers with the token its host wrote: this or another's
            started = child is not None and child.poll() is None
            held = "paused until you press Resume" if listed["paused"] else "running"
            said = f"OwlBear started, {held}" if started else "OwlBear is running"
            say(f"{said}: {link(serve.running())}")
            return 0
        if child is not None and child.poll() is not None and serve.running() is None:
            say(f"OwlBear ended at once (exit {child.returncode}); see `owlbear logs`")
            return 1
        time.sleep(0.2)
    say(f"OwlBear did not answer within {WAIT:.0f} s; see `owlbear logs`")
    return 1


def _identified() -> HostRecord | None:
    """The running host's record once it names its process; a host still starting has none yet."""
    deadline = time.monotonic() + WAIT
    while (rec := serve.running()) is not None and rec.pid <= 0 and time.monotonic() < deadline:
        time.sleep(0.2)
    return rec


def stop(say: Say) -> int:
    """Stop the machine host; steps that run finish on their own (TD-282)."""
    rec = _identified()
    if rec is None:
        say("OwlBear is not running")
        return 0
    if rec.pid <= 0:  # never a signal to a process group
        say("OwlBear is still starting and has not said which process it is; try again")
        return 1
    os.kill(rec.pid, signal.SIGTERM)
    deadline = time.monotonic() + STOPPING
    while time.monotonic() < deadline:
        if serve.running() is None:
            say("OwlBear stopped; running steps finish on their own")
            return 0
        time.sleep(0.2)
    say(f"OwlBear (process {rec.pid}) is still stopping; see `owlbear logs`")
    return 1


def projects() -> dict[str, Any] | None:
    """The running host's project list, or None when it does not run or answer."""
    return _api("projects")


def _api(path: str, method: str = "GET") -> dict[str, Any] | None:
    rec = serve.running()
    if not (rec and rec.token):
        return None
    request = urllib.request.Request(  # noqa: S310 - the loopback address the host wrote
        f"{rec.url}api/next/{path}", method=method, headers={"Authorization": f"Bearer {rec.token}"}
    )
    try:
        with _LOCAL.open(request, timeout=10) as response:
            return json.load(response)
    except OSError, ValueError:
        return None


def update(say: Say, wait: float = 1800.0) -> int:
    """Run updates now (TD-352, TD-353) and follow the update until it ends or the new version took over.

    It waits on while the update waits for running steps; another process answering at the address is the new one.
    """
    before = serve.running()
    state = _api("update", "POST")
    if state is None or before is None:
        say("OwlBear is not running; `owlbear start` starts it")
        return 1
    seen, deadline = "", time.monotonic() + wait
    while time.monotonic() < deadline:
        line = f"{state['phase']}{f' {state["version"]}' if state.get('version') else ''}: {state['detail']}"
        if line != seen:
            say(line)
            seen = line
        if state["phase"] in {"current", "failed", "refused"}:
            return 0 if state["phase"] == "current" else 1
        time.sleep(1)
        rec = serve.running()
        if rec is not None and rec.pid not in {before.pid, 0} and (listed := projects()) and listed.get("updated"):
            say(f"OwlBear now runs {listed['updated']}")
            return 0
        if rec is not None and rec.pid == before.pid and (now := _api("update")) is not None:
            state = now
    say("the update still runs; see `owlbear logs`")
    return 1


def status(say: Say) -> int:
    """Whether OwlBear runs, its address, pause and projects, and the login item."""
    rec = serve.running()
    say(f"OwlBear is running: {link(rec)}" if rec else "OwlBear is not running; `owlbear start` starts it")
    if (listed := projects()) is not None:
        if listed["paused"]:
            say(f"paused: {listed['waiting']} Changes would continue; press Resume on its page")
        for p in listed["projects"]:
            say(f"  {p['name']}: {p['state']}" + (f" · {p['reason']}" if p.get("reason") else "") + f" · {p['path']}")
    say(f"login item: {autostarts()}")
    return 0


def logs(say: Say, lines: int) -> int:
    """The end of the host's log."""
    try:
        text = (local_home.root() / LOG).read_text(errors="replace")
    except FileNotFoundError:
        say("no log yet: OwlBear has not run")
        return 0
    say("\n".join(text.splitlines()[-lines:]))
    return 0


def autostarts() -> str:
    """The login item's state as ``launchctl`` reports it."""
    if not plist_path().exists():
        return "off"
    done = subprocess.run(  # noqa: S603 - fixed launchctl arguments
        ["/bin/launchctl", "print", f"gui/{os.getuid()}/{LABEL}"], capture_output=True, check=False
    )
    return "on" if done.returncode == 0 else "written, but macOS has not loaded it (System Settings > Login Items)"


def autostart(say: Say, *, on: bool) -> int:
    """Write and load the login item, or unload and remove it."""
    path, domain = plist_path(), f"gui/{os.getuid()}"
    subprocess.run(["/bin/launchctl", "bootout", f"{domain}/{LABEL}"], capture_output=True, check=False)  # noqa: S603
    if not on:
        path.unlink(missing_ok=True)
        say("OwlBear no longer starts at login")
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    log = str(local_home.root() / LOG)
    item = {
        "Label": LABEL,
        "ProgramArguments": argv(),
        "RunAtLoad": True,
        "WorkingDirectory": str(local_home.root()),
        "EnvironmentVariables": {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin")
        },  # git and gh as this shell finds them
        "StandardOutPath": log,
        "StandardErrorPath": log,
    }
    path.write_bytes(plistlib.dumps(item))
    command = ["/bin/launchctl", "bootstrap", domain, str(path)]
    done = subprocess.run(command, capture_output=True, check=False)  # noqa: S603
    if done.returncode:
        said = done.stderr.decode(errors="replace").strip()
        say(f"login item written to {path}, but macOS refused to load it ({said}); `owlbear start` still works")
        return 1
    say("OwlBear starts at login, paused until you press Resume")
    return 0
