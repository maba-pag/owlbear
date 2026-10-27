"""What each worker role starts with: its tools (TD-69), the project's memory (TD-70, TD-72) and preloaded skills.

The tools are those its agent file names. Mandatory material loads at session start; only situational references
stay on demand (§3.13 Q-B). Every skill ships in the package's ``skills`` folder under a Delivery-unique name (TD-170),
the owner's chat skill among them; a step sees only its own role's.
"""

from __future__ import annotations

import os
import sys
from importlib.resources import files
from importlib.util import find_spec
from pathlib import Path
from typing import Any

import yaml

ROOT = "skills"
CHAT = "owlbear-change-shaping"  # the owner's chat skill: only the shaper loads it
REQUIRED: dict[str, tuple[str, ...]] = {
    "builder": ("owlbear-module-design", "owlbear-acceptance-criteria"),
    "planner": ("owlbear-acceptance-criteria", "owlbear-module-design"),
    "reviewer": ("owlbear-acceptance-criteria", "owlbear-module-design", "owlbear-review-judgment"),
    "challenger": ("owlbear-acceptance-criteria", "owlbear-module-design", "owlbear-review-judgment"),
    "design-judge": ("owlbear-interface-design", "owlbear-design-review"),
    "preparer": (),  # its discovery order lives in its agent file, its only consumer (reuse study v2, 3.3)
    "updater": (),  # it edits the pack's skills as files; preloading their old text would argue with its edits
    "test-reviewer": ("owlbear-review-judgment",),  # evidence and operating context; no code to design
    "test-curator": ("owlbear-review-judgment",),
    "curator": (),  # its automatic workflow lives in its agent file; it judges memory, not code
    "spotter": (),  # one look at an agent's work, no code to design
    "retro": (),  # whole finished tasks with hindsight, no code to design
    "retro-review": ("owlbear-review-judgment",),  # challenges Retro's proposals
}
UI: dict[str, tuple[str, ...]] = {"builder": ("owlbear-interface-design",)}  # added when the brief has a UI (TD-76)
JUDGED = ("owlbear-acceptance-criteria", "owlbear-review-judgment")  # no code to judge: no module design (TD-166)
JOBS: dict[str, tuple[str, ...]] = dict.fromkeys(
    ("visual-review", "brief-challenge", "brief-reconsider", "amendment-challenge"), JUDGED
)
MEMORY = "owlbear-memory"  # the memory server's name; agent files name its tools as owlbear-memory/<tool>
MEMORY_MODULE = "owlbear_memory_mcp"  # run as the workspace's .vscode/mcp.json runs it
MEMORY_DIR = "OWLBEAR_MEMORY_DIR"  # the memory server's store folder
MEMORY_GLOBAL = "OWLBEAR_MEMORY_GLOBAL_DIR"  # the shared repository's Global memory, read beside it (TD-241)
COPILOT_HOME = "COPILOT_HOME"  # the Copilot runtime's user folder, when not ~/.copilot


def front_matter(doc: str) -> tuple[dict[str, Any], str]:
    """A Markdown file's YAML front matter and the prose after it (TD-269).

    Raises:
        ValueError: The file opens no front matter, or it is not a mapping.
        yaml.YAMLError: The front matter is not YAML.
    """
    head, end, body = doc.removeprefix("---\n").partition("\n---")
    meta = yaml.safe_load(head) if doc.startswith("---\n") and end else None
    if not isinstance(meta, dict):
        msg = "no front matter mapping"
        raise ValueError(msg)  # noqa: TRY004 - a file without front matter is bad input, not a wrong type
    return meta, body


def agent_file(role: str) -> tuple[dict[str, Any], str]:
    """The role's agent file, ``agents/owlbear-<role>.agent.md`` (TD-169): its front matter fields and its prose."""
    path = files("owlbear_delivery_next").joinpath("agents", f"owlbear-{role}.agent.md")
    return front_matter(path.read_text(encoding="utf-8"))


def tools(role: str) -> list[str]:
    """The runtime tools the role may use, as its agent file names them; Delivery adds its result tools."""
    return [str(name) for name in agent_file(role)[0].get("tools") or []]


def memory(store: Path | None) -> dict[str, Any] | None:
    """The memory server for the project's memory folder *store* in the shared repository (TD-72).

    The agents read the repository's Global memory beside it, ``<shared>/memory/`` (TD-241), and write only to it.
    None without a shared repository or when the server is not installed: the agents then go on without memory.
    """
    if store is None or find_spec(MEMORY_MODULE) is None:
        return None
    command = {"command": sys.executable, "args": ["-m", MEMORY_MODULE]}
    env = {MEMORY_DIR: str(store), MEMORY_GLOBAL: str(global_memory(store))}
    return command | {"env": env, "tools": ["*"]}


def global_memory(store: Path) -> Path:
    """Global memory, ``<shared>/memory``, beside the project's memory folder *store*, ``<shared>/<name>/memory``."""
    return store.parent.parent / "memory"


def directory() -> Path:
    """The folder the runtime searches for Delivery's worker skills."""
    return Path(str(files("owlbear_delivery_next").joinpath(ROOT)))


def text(name: str, folder: Path | None = None) -> str:
    """One skill's ``SKILL.md``, from *folder* (a pack candidate's) or the package's."""
    return ((folder or directory()) / name / "SKILL.md").read_text(encoding="utf-8")


def _named(name: str, folder: Path | None = None) -> bool:
    try:
        return front_matter(text(name, folder))[0].get("name") == name
    except OSError, ValueError, yaml.YAMLError:
        return False


def required(role: str, *, ui: bool = False, job: str = "") -> tuple[str, ...]:
    """The skills a session of *role* preloads for its *job*; a Change with a user interface adds design skills."""
    return (*JOBS.get(job, REQUIRED.get(role, ())), *(UI.get(role, ()) if ui else ()))


def folders(role: str, *, ui: bool = False, job: str = "", folder: Path | None = None) -> list[str]:
    """One folder per skill the session preloads, so it sees no other (TD-166)."""
    return [str((folder or directory()) / name) for name in required(role, ui=ui, job=job)]


def missing(role: str, *, ui: bool = False, job: str = "", folder: Path | None = None) -> list[str]:
    """The role's skills Delivery cannot preload from *folder*: absent, or named otherwise in their front matter."""
    return [name for name in required(role, ui=ui, job=job) if not _named(name, folder)]


def copilot_home() -> Path:
    """The runtime's user folder, with the owner's instructions and skills: ``$COPILOT_HOME``, else ``~/.copilot``."""
    return Path(found) if (found := os.environ.get(COPILOT_HOME)) else Path.home() / ".copilot"

