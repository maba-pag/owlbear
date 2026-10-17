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

import yaml

ROOT = "worker_skills"
CHAT = "delivery"  # the owner's chat skill, shipped in the package's skills folder, never in this one
REQUIRED: dict[str, tuple[str, ...]] = {
    "builder": ("owlbear-module-design", "owlbear-acceptance"),
    "planner": ("owlbear-acceptance", "owlbear-module-design"),
    "reviewer": ("owlbear-acceptance", "owlbear-module-design", "owlbear-findings"),
    "challenger": ("owlbear-acceptance", "owlbear-module-design", "owlbear-findings"),
    "designer": ("owlbear-ui-design", "owlbear-ui-review"),
    "preparer": (),  # its discovery order lives in its agent file, its only consumer (reuse study v2, 3.3)
    "updater": (),  # it edits the pack's skills as files; preloading their old text would argue with its edits
}
UI: dict[str, tuple[str, ...]] = {"builder": ("owlbear-ui-design",)}  # added when the brief has a UI (TD-76)
MEMORY = "owlbear-memory"  # the memory server's name; agent files name its tools as owlbear-memory/<tool>
MEMORY_MODULE = "owlbear_memory_mcp"  # run as the workspace's .vscode/mcp.json runs it
MEMORY_DIR = "OWLBEAR_MEMORY_DIR"  # the memory server's store folder


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
    """The role's agent file: its front matter fields and its prose."""
    return front_matter(files("owlbear_delivery_next").joinpath("agents", f"{role}.md").read_text(encoding="utf-8"))


def tools(role: str) -> list[str]:
    """The runtime tools the role may use, as its agent file names them; Delivery adds its result tools."""
    return [str(name) for name in agent_file(role)[0].get("tools") or []]


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


def text(name: str, folder: Path | None = None) -> str:
    """One skill's ``SKILL.md``, from *folder* (a pack candidate's) or the package's."""
    return ((folder or directory()) / name / "SKILL.md").read_text(encoding="utf-8")


def _named(name: str, folder: Path | None = None) -> bool:
    try:
        return front_matter(text(name, folder))[0].get("name") == name
    except OSError, ValueError, yaml.YAMLError:
        return False


def required(role: str, *, ui: bool = False) -> tuple[str, ...]:
    """The skills a session of *role* preloads; a Change with a user interface adds the role's design skills."""
    return (*REQUIRED.get(role, ()), *(UI.get(role, ()) if ui else ()))


def missing(role: str, *, ui: bool = False, folder: Path | None = None) -> list[str]:
    """The role's skills Delivery cannot preload from *folder*: absent, or named otherwise in their front matter."""
    return [name for name in required(role, ui=ui) if not _named(name, folder)]
