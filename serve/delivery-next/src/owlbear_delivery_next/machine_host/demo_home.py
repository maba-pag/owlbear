"""The demo's temporary home: the owner's data replaced, GitHub cut off, the example world seeded in it.

``isolate`` runs before the host's modules, some of which read HOME when imported (this one's imports do not): a
fresh temporary folder becomes HOME, ``OWLBEAR_DATA``, ``COPILOT_HOME`` and ``GIT_CONFIG_*`` are dropped, Git resolves
every ``https://github.com/`` address to a missing path, and a ``gh`` that only fails comes first on PATH. ``seed``
then writes, in that home, the shared data checkout with a complete Global layer, this machine's settings, the two
registered example projects and their six example Changes. Their GitHub-shaped origins never reach GitHub: the data
checkout pushes to a local bare repository and the write account is chosen offline.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from owlbear_delivery_next.git.access import Access
from owlbear_delivery_next.git.git_executable import resolve_git_executable
from owlbear_delivery_next.github import account
from owlbear_delivery_next.github.provider import MergeMethod
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.machine_host import demo_changes
from owlbear_delivery_next.settings import carried
from owlbear_delivery_next.settings.config import Agent, GlobalLayer, MemoryValues, Prefs
from owlbear_delivery_next.settings.improvement import CATEGORIES, Spotter
from owlbear_delivery_next.state_store import registry

GITHUB, OFFLINE = "https://github.com/", "/nonexistent/offline-in-demo/"
DATA = "https://github.com/example/owlbear-data.git"
PROJECTS = (  # (name, fixed clone id): each start registers them under the same ids
    ("example-shop", "e0a1b2c3d4e5f601"),
    ("example-docs", "e0a1b2c3d4e5f602"),
)


def isolate() -> Path:
    """A fresh HOME for this process, the owner's data and Copilot folders dropped, Git and ``gh`` kept off GitHub."""
    home = Path(tempfile.mkdtemp(prefix="owlbear-demo-")).resolve()
    os.environ["HOME"] = str(home)
    for name in ("OWLBEAR_DATA", "COPILOT_HOME", *(n for n in os.environ if n.startswith("GIT_CONFIG_"))):
        os.environ.pop(name, None)
    (home / ".gitconfig").write_text(
        f'[url "{OFFLINE}"]\n\tinsteadOf = {GITHUB}\n[user]\n\tname = OwlBear demo\n\temail = demo@example.invalid\n'
    )
    os.environ |= {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": f"url.{OFFLINE}.insteadOf",
                   "GIT_CONFIG_VALUE_0": GITHUB}  # fmt: skip
    tools = home / "bin"
    tools.mkdir()
    (tools / "gh").write_text('#!/bin/sh\necho "gh is offline in the OwlBear demo" >&2\nexit 1\n')
    (tools / "gh").chmod(0o755)
    os.environ["PATH"] = f"{tools}{os.pathsep}{os.environ.get('PATH', '')}"
    return home


def seed(home: Path) -> None:
    """The write account chosen offline, the shared data settled, the example projects registered with their Changes."""
    account.resolve = _offline  # before any Store opens: its adopt publishes the project's claim
    shared = DataRepo(_checkout(home / ".owlbear" / "data", DATA, home / "remotes" / "owlbear-data.git"))
    shared.global_path.write_text(_global().model_dump_json(indent=2, exclude_none=True) + "\n")
    if why := shared.publish(shared.global_path, "global: the demo's example settings"):
        msg = f"the demo's example settings could not be published: {why}"
        raise RuntimeError(msg)
    registry.save(registry.Machine(settings_moved=True))
    clones = {}
    for name, pid in PROJECTS:
        clone = _checkout(home / "projects" / name, f"https://github.com/example/{name}.git")
        folder = registry.store_of(clone)
        folder.mkdir(mode=0o700)
        (folder / "clone-id").write_text(pid + "\n")
        registry.register(clone)
        clones[name] = clone
    demo_changes.seed(clones)


def _offline(setting: str, origin: account.Origin, *, until: float | None = None) -> Access:
    """``account.resolve`` without ``gh``: the configured login, or the fallback for the repository owner."""
    del until
    if origin == account.Origin.LOCAL:
        return Access.LOCAL
    login = account.FALLBACK if setting == account.REPOSITORY_OWNER else setting
    return Access(login, "chosen offline in the demo", origin.host, f"demo-{login}", "gh")


def _global() -> GlobalLayer:
    """A complete Global layer: the carried values and every setting that came later, so nothing is unset."""
    base = carried.layer()
    agents = base.agents | {
        role: base.agents["curator"].model_copy(update={"model": "gpt-6.1-sol", "effort": "medium"})
        for role in ("retro", "retro-review", "auditor", "project-auditor", "audit-verifier", "quality-judge")
    }
    agents["shaper"] = base.agents["shaper"].model_copy(update={"challenge_wait": 15})
    agents["repairer"] = Agent(minutes=40, subagents=True)
    machine = carried.MACHINE.model_copy(update={
        "retro_after_change": "on", "retro_when_idle": "on", "enrolled_chats": [],
        "update_check_hours_owlbear": 24, "update_check_hours_pds": 24, "update_check_hours_impeccable": 24,
    })  # fmt: skip
    return base.model_copy(update={
        "agents": agents, "machine": machine, "machine_moved": True, "guard_level": "strict",
        "github_account": "repository-owner",
        **dict.fromkeys(("load_user_instructions", "load_user_skills", "load_user_memory"), False),
        "prefs": Prefs(merge_method=MergeMethod.SQUASH, delete_remote_branch=False, ci_poll_seconds=20,
                       ci_start_window_seconds=300, ask_before_merge=False),
        "memory": MemoryValues(outstanding_boost=0.1, unremarkable_penalty=0.01, stale_factor=50, purge_days=30,
                               preflight_cap=5, preflight_budget=2000, recall_limit=20, explore_slots=2,
                               challenge_slots=2),
        "spotter": Spotter(switch="on", steer_share=0, intervention_cap=1, verbose="off", looks=["hand-off"],
                           look_credit_limit=0.75, **dict.fromkeys(CATEGORIES.values(), "record")),
    })  # fmt: skip


def _git(cwd: Path, *args: str) -> None:

    subprocess.run(  # noqa: S603 - fixed git argv
        [resolve_git_executable(), *args], cwd=cwd, check=True, capture_output=True
    )


def _checkout(path: Path, origin: str, remote: Path | None = None) -> Path:
    """A local repository with one commit whose ``origin`` names *origin*; Git reaches *remote* for it, or nothing."""
    path.mkdir(parents=True)
    _git(path, "init", "-q", "-b", "main")
    _git(path, "remote", "add", "origin", origin)
    _git(path, "commit", "-q", "--allow-empty", "-m", "start")
    if remote:  # the longer insteadOf wins over HOME's rule that keeps GitHub unreachable
        _git(path.parent, "init", "-q", "--bare", "-b", "main", str(remote))
        _git(path, "config", f"url.{remote}.insteadOf", origin)
        _git(path, "push", "-q", "-u", "origin", "HEAD")
    return path.resolve()
