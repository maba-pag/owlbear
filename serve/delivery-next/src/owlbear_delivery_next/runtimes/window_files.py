"""The harness key of the owner's VS Code settings, which New Change's shaping chat needs (TD-83).

``chat.defaultToCopilotHarness`` must be true when a window starts, or the chat opens as a Local chat. Delivery adds
that one line to the owner's ``.vscode/settings.json`` for as long as a shaping chat takes to open and takes it out
again afterwards (``add_harness``, ``remove_harness``); every other byte the owner wrote stays.
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import text_files

if TYPE_CHECKING:
    from pathlib import Path

HARNESS = "chat.defaultToCopilotHarness"
HARNESS_LINE = f'\n  "{HARNESS}": true'  # the one line Delivery adds to an owner's settings
HARNESS_ADDED = re.compile(re.escape(HARNESS_LINE) + ",?")
SETTINGS = ".vscode/settings.json"


class SettingsError(ValueError):
    """The owner's VS Code settings cannot be written safely."""


def _opening(text: str) -> int | None:
    """Just after the opening brace of ``text``'s object, past leading comments; None when it is no object."""
    lines = text.splitlines(keepends=True)
    first = next((i for i, ln in enumerate(lines) if ln.strip() and not ln.lstrip().startswith("//")), None)
    if first is None or not lines[first].lstrip().startswith("{"):
        return None
    return sum(len(ln) for ln in lines[:first]) + lines[first].index("{") + 1


@dataclass(frozen=True)
class Added:
    """Delivery's harness line in an owner's settings, and whether Delivery made the file and its folder."""

    file: bool
    folder: bool


def add_harness(folder: Path) -> Added | None:
    """Add the harness key to the owner's ``folder`` settings, every other byte kept; None when they name it already.

    Nothing else changes in the owner's folder, git metadata included.
    """
    path = folder / SETTINGS
    if part := text_files.linked_part(folder, path):
        raise SettingsError(f"{part} is a symbolic link; Delivery writes nothing through it")  # noqa: EM102, TRY003
    try:
        old = path.read_text()
    except FileNotFoundError:
        made = not path.parent.exists()
        path.parent.mkdir(exist_ok=True)
        with path.open("x") as f:  # never over a file the owner just created
            f.write("{" + HARNESS_LINE + "\n}\n")
        return Added(file=True, folder=made)
    if f'"{HARNESS}"' in old:
        return None
    if (at := _opening(old)) is None:
        raise SettingsError(f"{SETTINGS} is not a JSON object; set {HARNESS} by hand")  # noqa: EM102, TRY003
    comma = "" if old[at:].lstrip().startswith("}") else ","
    text_files.replace_text(path, old[:at] + HARNESS_LINE + comma + old[at:])
    return Added(file=False, folder=False)


def remove_harness(folder: Path, added: Added) -> str:
    """Take Delivery's harness line out again, keeping what the owner changed meanwhile; what failed, or ''."""
    path = folder / SETTINGS
    try:
        rest, found = HARNESS_ADDED.subn("", path.read_text(), count=1)
        if not found:
            return ""
        if added.file and rest == "{\n}\n":
            path.unlink()
            if added.folder:
                with contextlib.suppress(OSError):  # a folder the owner filled meanwhile stays
                    path.parent.rmdir()
        else:
            text_files.replace_text(path, rest)
    except FileNotFoundError:
        return ""
    except OSError as exc:
        return f"could not remove {HARNESS} from {SETTINGS} ({exc}); remove it by hand"
    return ""
