"""Where an accepted proposal lands (#716, Improvement design §6): the destination shown before the owner confirms.

A proposal's projects come from its findings' units: a Change unit (``chg:<project id>:<slug>``) names its project, a
chat names none, a synthetic unit names the clone folder its spec stands for. ``resolve`` then reads the proposal's
kind and target:

- a Spotter case becomes a case;
- a lesson becomes a pending memory in its one project's folder of the shared repository, or OwlBear's when its
  findings are not all one project's, scoped to the agents the target names;
- anything OwlBear ships (a tool, Delivery, a look, the Spotter, a shipped agent or skill) becomes an issue in
  OwlBear's public repository; a name in the one project's clone becomes an entry in that project's backlog; anything
  else an entry in the backlog of no project.

Synthetic proposals publish only to the sandbox (owlbear-sandbox): its memory folder and backlog, or an issue marked
synthetic and closed at once. Without the sandbox registered they resolve to an error and cannot be accepted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.local_system import codebase, preload

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

SANDBOX = "owlbear-sandbox"  # the clone folder synthetic proposals publish to
OWLBEAR = "owlbear"  # OwlBear's own folder in the shared repository
REPOSITORY = re.sub(r"^https://github\.com/|\.git$", "", codebase.URL)
MEMORY = 1_024  # characters a memory's content holds (owlbear_memory MemoryEntry)
OWN = ("tool:", "delivery:", "look:", "spotter:")  # targets that are always OwlBear's own


@dataclass(frozen=True)
class Place:
    """A registered project: its folder in the shared repository and its clone."""

    folder: str
    clone: Path | None


def units_of() -> dict[str, str]:
    """The unit of every finding and grade, by id: what a proposal's findings are read through."""
    found = {f["id"]: f.get("unit", "") for f in store.all_findings()}
    return found | {g["id"]: g.get("unit", "") for g in store.grades(synthetic=True)}


def _sandbox(places: Mapping[str, Place]) -> str:
    return next((pid for pid, p in places.items() if p.clone is not None and p.clone.name == SANDBOX), "")


def _project(uid: str, places: Mapping[str, Place], known: Mapping[str, Any]) -> str:
    """The registered project *uid* stands for, or ``""``."""
    if uid.startswith("chg:"):
        pid = uid.split(":")[1]
        return pid if pid in places else ""
    if uid.startswith("syn:") and (name := (known.get(uid) or {}).get("project")):
        return next((pid for pid, p in places.items() if p.clone is not None and p.clone.name == name), "")
    return ""


def projects(snap: Mapping[str, Any], places: Mapping[str, Place], units: Mapping[str, str]) -> list[str]:
    """The registered projects each finding of *snap* stands for, ``""`` for one standing for none, in order."""
    known = store.known()
    return [_project(units.get(f, ""), places, known) for f in snap["findings"]]


def _agents(folder: Path) -> dict[str, str]:
    try:
        found = sorted(folder.glob("*.agent.md"))
        return {p.name.removesuffix(".agent.md"): p.read_text() for p in found}
    except OSError:
        return {}


def shipped() -> set[str]:
    """The agent and skill names OwlBear ships: each agent with and without its ``owlbear-`` prefix, each skill."""
    agents = _agents(Path(str(files("owlbear_delivery_next").joinpath("agents"))))
    return preload.shipped() | set(agents) | {a.removeprefix("owlbear-") for a in agents}


def in_clone(target: str, clone: Path | None) -> bool:
    """Whether *target* (``agent:``, ``skill:`` or ``prompt:`` and a name) is a file of the project's *clone*."""
    kind, _, name = target.partition(":")
    if clone is None or not name or "/" in name or name.startswith("."):
        return False
    github = clone / ".github"
    path = {
        "agent": github / "agents" / f"{name}.agent.md",
        "skill": github / "skills" / name,
        "prompt": github / "prompts" / f"{name}.prompt.md",
    }.get(kind)
    return path is not None and path.exists()


def roles(target: str, clone: Path | None) -> list[str]:
    """The agents a lesson about *target* is scoped to; none leaves it unscoped, for the curator to scope.

    An agent is its own role; a skill or prompt is scoped to the agents whose file names it, the project's agent
    files when it has any, else OwlBear's.
    """
    kind, _, name = target.partition(":")
    if kind == "agent" and name:
        return [name.removeprefix("owlbear-")]
    if kind not in {"skill", "prompt"} or not name:
        return []
    agents = _agents(clone / ".github" / "agents") if clone is not None else {}
    agents = agents or _agents(Path(str(files("owlbear_delivery_next").joinpath("agents"))))
    return sorted({a.removeprefix("owlbear-") for a, text in agents.items() if name in text})


def _one(found: Iterable[str]) -> str:
    """The one project every finding stands for, or ``""``."""
    every = set(found)
    return next(iter(every)) if len(every) == 1 else ""


def resolve(
    snap: Mapping[str, Any], places: Mapping[str, Place], shared_root: Path, units: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """Where *snap* lands once accepted, by its kind and target; *units* from ``units_of``, read when not given.

    Raises:
        RetroError: A synthetic proposal while the sandbox is not registered, or a lesson too long for a memory.
    """
    kind, target = snap.get("kind", ""), str(snap.get("target") or "")
    synthetic = snap.get("provenance") == "synthetic"
    if kind == "spotter-case":
        return {"kind": "case", "record": snap.get("record", ""), "call": snap.get("call", ""), "synthetic": synthetic}
    pid = _sandbox(places) if synthetic else _one(projects(snap, places, units if units is not None else units_of()))
    if synthetic and not pid:
        msg = f"synthetic proposals publish only to the sandbox; register ~/Projects/{SANDBOX}"
        raise store.RetroError(msg)
    place = places.get(pid)
    clone = place.clone if place else None
    if kind == "lesson":
        body = str((snap.get("publishable") or {}).get("body") or "")
        if len(body) > MEMORY:
            msg = f"too long for a memory ({len(body)} characters, {MEMORY} at most): redirect it to shorten"
            raise store.RetroError(msg)
        folder = place.folder if place else OWLBEAR
        return {
            "kind": "memory",
            "project": pid,
            "folder": str(shared_root / folder / "memory"),
            "roles": roles(target, clone),
            "recommended": "project" if place else "global",
        }
    if target.startswith(OWN) or target.partition(":")[2] in shipped():
        return {"kind": "issue", "repository": REPOSITORY, "synthetic": synthetic}
    if synthetic or (place and in_clone(target, clone)):
        return {"kind": "backlog", "project": pid, "folder": place.folder if place else ""}
    return {"kind": "backlog", "project": "", "folder": ""}
