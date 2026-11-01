"""Which PDS knowledge skill a session on a project preloads, chosen from its worktree (#777).

A project that depends on a PDS package gets the knowledge skill its installed package ships; a project whose
tracked files load PDS gets OwlBear's vendored skill when they name OwlBear's pinned release; any other is not a PDS
project. A PDS project without a usable skill gets none, with the reason.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from owlbear_delivery_next.local_system import preload

SCOPE = "@porsche-design-system"
FRAMEWORKS = ("js", "react", "angular", "vue")
PIN = "pds.json"  # the vendored release's pin, in the package
VENDORED = Path("pds", "skills", "pds-knowledge-js")  # OwlBear's vendored knowledge skill, in the package
MARKS = (  # a PDS CDN bundle's name, or the header OwlBear's vendored files carry
    r"porsche-design-system\.v([0-9]+\.[0-9]+\.[0-9]+)|@porsche-design-system/components-js ([0-9]+\.[0-9]+\.[0-9]+)"
)
NOTE = "This is a PDS project, but no PDS knowledge skill is loaded: "  # a first message's opening line
ROLES = frozenset({"design-judge", "reviewer", "challenger"})  # and the builder of a Change with a user interface


@dataclass(frozen=True)
class Choice:
    """The skill a PDS project's session preloads: its name and folder, or no folder and the reason."""

    name: str = ""
    folder: Path | None = None
    reason: str = ""


def package() -> Path:
    """The installed package's folder."""
    return Path(str(files("owlbear_delivery_next")))


def pinned(root: Path | None = None) -> str:
    """The PDS release the package at *root* (else the installed one) pins."""
    return str(json.loads(((root or package()) / PIN).read_text(encoding="utf-8"))["version"])


def wanted(role: str, *, ui: bool, skills: Path | None) -> bool:
    """Whether a session of *role* preloads a project's PDS skill; a pack candidate's sessions load only its own."""
    return skills is None and (role in ROLES or (role == "builder" and ui))


def choose(worktree: Path, root: Path | None = None) -> Choice | None:
    """The knowledge skill for the project at *worktree*: None for no PDS project, a folderless Choice for no skill."""
    return _installed(worktree) or _loaded(worktree, root or package())


def _installed(worktree: Path) -> Choice | None:
    try:
        manifest = json.loads((worktree / "package.json").read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    named = {**(manifest.get("dependencies") or {}), **(manifest.get("devDependencies") or {})}
    framework = next((f for f in FRAMEWORKS if f"{SCOPE}/components-{f}" in named), None)
    if framework is None:
        return None
    installed = worktree / "node_modules" / SCOPE / f"components-{framework}"
    try:
        version = json.loads((installed / "package.json").read_text(encoding="utf-8"))["version"]
    except OSError, ValueError, KeyError, TypeError:
        return Choice(reason="the project's PDS package is not installed")
    skill = installed / "skills" / f"pds-knowledge-{framework}"
    if not (skill / "SKILL.md").is_file():
        return Choice(reason=f"the project's PDS package {version} ships no knowledge skill")
    return Choice(name=preload.skill_name(skill), folder=skill)


def _loaded(worktree: Path, root: Path) -> Choice | None:
    found = subprocess.run(  # noqa: S603 - a fixed argument list, the pattern ours
        ["git", "-C", str(worktree), "grep", "-I", "-h", "-o", "-E", MARKS],  # noqa: S607 - git from PATH, as elsewhere
        capture_output=True,
        text=True,
        check=False,
    )
    versions = {m[0] or m[1] for m in re.findall(MARKS, found.stdout)} if found.returncode == 0 else set()
    if not versions:
        return None
    pin = pinned(root)
    if versions == {pin}:
        return Choice(name=preload.skill_name(root / VENDORED), folder=root / VENDORED)
    return Choice(reason=f"the project loads PDS {', '.join(sorted(versions))}; OwlBear's skill is for {pin}")


def noted(message: str, choice: Choice | None) -> str:
    """The first message, after one line saying why a PDS project's session has no knowledge skill."""
    if choice is None or choice.folder is not None:
        return message
    return f"{NOTE}{choice.reason}.\n\n{message}"
