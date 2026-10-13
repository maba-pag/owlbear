"""Skills Delivery preloads into each worker role's context before its first turn (item 6).

Mandatory material loads at session start; only situational references stay on demand (§3.13 Q-B). The skills
ship in the package's ``worker_skills`` folder under Delivery-unique names, apart from the owner's chat skill.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

ROOT = "worker_skills"
CHAT = "delivery"  # the owner's chat skill, shipped in the package's skills folder, never in this one
REQUIRED: dict[str, tuple[str, ...]] = {
    "builder": ("owlbear-module-design", "owlbear-acceptance"),
    "planner": ("owlbear-acceptance", "owlbear-module-design"),
    "reviewer": ("owlbear-acceptance", "owlbear-module-design"),
}


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


def missing(role: str) -> list[str]:
    """The role's skills Delivery cannot preload: absent, or named otherwise in their front matter."""
    return [name for name in REQUIRED.get(role, ()) if not _named(name)]
