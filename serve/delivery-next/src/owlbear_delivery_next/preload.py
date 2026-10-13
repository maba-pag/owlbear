"""What each worker role starts with: its tools (TD-69), the project's memory (TD-70, TD-72) and preloaded skills.

The tools are those its agent file names. Mandatory material loads at session start; only situational references
stay on demand (§3.13 Q-B). The skills ship in the package's ``worker_skills`` folder under Delivery-unique names,
apart from the owner's chat skill.
"""

from __future__ import annotations

import sys
from importlib.resources import files
from importlib.util import find_spec
from pathlib import Path
from typing import Any

ROOT = "worker_skills"
CHAT = "delivery"  # the owner's chat skill, shipped in the package's skills folder, never in this one
REQUIRED: dict[str, tuple[str, ...]] = {
    "builder": ("owlbear-module-design", "owlbear-acceptance"),
    "planner": ("owlbear-acceptance", "owlbear-module-design"),
    "reviewer": ("owlbear-acceptance", "owlbear-module-design"),
}
UI: dict[str, tuple[str, ...]] = {"builder": ("owlbear-ui-design",)}  # added when the brief has a UI (TD-76)
MEMORY = "owlbear-memory"  # the memory server's name; agent files name its tools as owlbear-memory/<tool>
MEMORY_MODULE = "owlbear_memory_mcp"  # run as the workspace's .vscode/mcp.json runs it
MEMORY_DIR = "OWLBEAR_MEMORY_DIR"  # the memory server's store folder


def agent_file(role: str) -> tuple[dict[str, str], str]:
    """The role's agent file: its front matter fields and its prose."""
    text = files("owlbear_delivery_next").joinpath("agents", f"{role}.md").read_text(encoding="utf-8")
    _, front, body = text.split("---", 2)
    return {k.strip(): v.strip() for k, v in (line.split(":", 1) for line in front.strip().splitlines())}, body


def tools(role: str) -> list[str]:
    """The runtime tools the role may use, as its agent file names them; Delivery adds its result tools."""
    names = agent_file(role)[0].get("tools", "").strip("[]")
    return [n.strip() for n in names.split(",") if n.strip()]


def memory(store: Path | None) -> dict[str, Any] | None:
    """The memory server for the project's memory folder *store* in the shared repository (TD-72).

    None without a shared repository or when the server is not installed: the agents then go on without memory.
    """
    if store is None or find_spec(MEMORY_MODULE) is None:
        return None
    command = {"command": sys.executable, "args": ["-m", MEMORY_MODULE]}
    return command | {"env": {MEMORY_DIR: str(store)}, "tools": ["*"]}


def directory() -> Path:
    """The folder the runtime searches for Delivery's worker skills."""
    return Path(str(files("owlbear_delivery_next").joinpath(ROOT)))


def text(name: str) -> str:
    """One skill's ``SKILL.md``."""
    return (directory() / name / "SKILL.md").read_text(encoding="utf-8")


def _named(name: str) -> bool:
    try:
        head = text(name).split("---", 2)[1]
    except OSError, IndexError:
        return False
    return any(line.split(":", 1)[1].strip() == name for line in head.splitlines() if line.startswith("name:"))


def required(role: str, *, ui: bool = False) -> tuple[str, ...]:
    """The skills a session of *role* preloads; a Change with a user interface adds the role's design skills."""
    return (*REQUIRED.get(role, ()), *(UI.get(role, ()) if ui else ()))


def missing(role: str, *, ui: bool = False) -> list[str]:
    """The role's skills Delivery cannot preload: absent, or named otherwise in their front matter."""
    return [name for name in required(role, ui=ui) if not _named(name)]
