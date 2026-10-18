"""``owlbear install``, ``uninstall`` and ``doctor``: the command on the PATH, its completion and the login item.

Install runs from ``~/.owlbear/runtime``, writes the zsh completion into ``~/.owlbear/`` and asks separately
before the ``~/.local/bin/owlbear`` link and the login item (TD-258, TD-260). ``~/.zshrc`` is only named.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.machine_host import control, registry

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable

    from owlbear_delivery_next.machine_host.control import Say

COMPLETION = "completion.zsh"


def link_path() -> Path:
    """Where the command's link goes: a folder on most PATHs, never a system one."""
    return Path.home() / ".local" / "bin" / "owlbear"


def runtime() -> Path:
    """The installed runtime the command and the login item run from."""
    return local_home.root() / "runtime"


def install(say: Say, ask: Callable[[str], bool], parser: argparse.ArgumentParser) -> int:
    """Write the completion, then link the command and add the login item, each only after a yes."""
    command = local_home.stable(Path(sys.executable).parent / "owlbear")  # the alias, so updates keep it
    if not command.is_relative_to(runtime()):
        say(f"run this from the installed runtime: {runtime() / '.venv' / 'bin' / 'owlbear'} install")
        return 1
    import shtab  # noqa: PLC0415 - only install needs it

    path = local_home.root() / COMPLETION
    path.write_text(shtab.complete(parser, shell="zsh"))  # noqa: S604 - shtab's shell name
    say(f"completion written to {path}; to use it, add this line to ~/.zshrc: source {path}")
    target = link_path()
    if ask(f"Link {target} to {command}, so `owlbear` runs in any shell?"):
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink() or not target.exists():
            target.unlink(missing_ok=True)
            target.symlink_to(command)
            say(f"linked {target}" + ("" if shutil.which("owlbear") else f"; add {target.parent} to your PATH"))
        else:
            say(f"{target} exists and is no link; left as it is")
    if ask("Start OwlBear at login, paused until you press Resume?"):
        return control.autostart(say, on=True)
    return 0


def uninstall(say: Say) -> int:
    """Remove the login item and the command's link; the runtime and every project stay."""
    control.autostart(say, on=False)
    target = link_path()
    if target.is_symlink():
        target.unlink()
        say(f"removed {target}")
    (local_home.root() / COMPLETION).unlink(missing_ok=True)
    return 0


def doctor(say: Say, dropped: list[str]) -> int:
    """What the host's environment cannot do: git, gh and its login, and each project's readiness, with the fix."""
    from owlbear_delivery_next.runtimes import readiness  # noqa: PLC0415 - only doctor needs it
    from owlbear_delivery_next.state_store.store import Store, StoreError  # noqa: PLC0415

    for name in dropped:
        say(f"ignored from this shell: {name} (the host never sees it; a project's own Git settings decide)")
    failed = 0
    for tool in ("git", "gh"):
        if shutil.which(tool) is None:
            say(
                f"{tool}: not found on PATH · fix: install it, then run `owlbear autostart on` again for the login item"
            )
            failed += 1
    if shutil.which("gh"):
        done = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, check=False)  # noqa: S607
        if done.returncode:
            say("gh: not signed in from this environment · fix: gh auth login")
            failed += 1
    for p in registry.load().projects:
        try:
            checks = readiness.ready(Store.open(Path(p.path)), Path(p.path))
        except (StoreError, OSError) as exc:
            say(f"{p.path}: cannot be read: {exc}")
            failed += 1
            continue
        for c in checks:
            if not c.ok:
                say(f"{p.path}: {c.name}: {c.detail} · fix: {c.fix}")
                failed += 1
    say("all checks passed" if not failed else f"{failed} problem{'s' if failed > 1 else ''} found")
    return 1 if failed else 0
