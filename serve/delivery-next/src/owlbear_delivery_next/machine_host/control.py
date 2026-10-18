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

LABEL = "com.owlbear.host"
LOG = "host.log"
WAIT = 20.0  # seconds a start waits for the host's address
STOPPING = 120.0  # seconds a stop waits: the drain, then the schedulers' current passes
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))
type Say = Callable[[str], None]


def plist_path() -> Path:
    """Where the login item lives."""
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def argv() -> list[str]:
    """The machine host's process: this interpreter and the one dispatcher."""
    return [sys.executable, "-m", "owlbear_delivery_next", "machine"]


def start(say: Say) -> int:
    """Start the machine host in the background unless it runs; say its address either way."""
    if rec := serve.running():
        say(f"OwlBear is running: {link(rec) or '(starting)'}")
        return 0
    home = local_home.root()
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (home / LOG).open("ab") as out:
        subprocess.Popen(  # noqa: S603 - this interpreter and a fixed module
            argv(), cwd=home, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, start_new_session=True
        )
    deadline = time.monotonic() + WAIT
    while time.monotonic() < deadline:
        if (rec := serve.running()) and rec.token:
            say(f"OwlBear started, paused until you press Resume: {link(rec)}")
            return 0
        time.sleep(0.2)
    say(f"OwlBear did not answer within {WAIT:.0f} s; see `owlbear logs`")
    return 1


def stop(say: Say) -> int:
    """Stop the machine host; steps that run finish on their own (TD-282)."""
    rec = serve.running()
    if rec is None:
        say("OwlBear is not running")
        return 0
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
    rec = serve.running()
    if not (rec and rec.token):
        return None
    request = urllib.request.Request(  # noqa: S310 - the loopback address the host wrote
        f"{rec.url}api/next/projects", headers={"Authorization": f"Bearer {rec.token}"}
    )
    try:
        with _LOCAL.open(request, timeout=10) as response:
            return json.load(response)
    except OSError, ValueError:
        return None


def status(say: Say) -> int:
    """Whether OwlBear runs, its address, pause and projects, and the login item."""
    rec = serve.running()
    say(f"OwlBear is running: {link(rec)}" if rec else "OwlBear is not running; `owlbear start` starts it")
    if (listed := projects()) is not None:
        if listed["paused"]:
            say(f"paused since it started: {listed['waiting']} Changes would continue; press Resume on its page")
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
    done = subprocess.run(["/bin/launchctl", "bootstrap", domain, str(path)], capture_output=True, check=False)  # noqa: S603
    if done.returncode:
        said = done.stderr.decode(errors="replace").strip()
        say(f"login item written to {path}, but macOS refused to load it ({said}); `owlbear start` still works")
        return 1
    say("OwlBear starts at login, paused until you press Resume")
    return 0
