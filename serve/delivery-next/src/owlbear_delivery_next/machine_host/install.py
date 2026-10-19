"""``owlbear install``, ``uninstall`` and ``doctor``: the command, its completion, the shaper and the login item.

Install runs from ``~/.owlbear/runtime``, writes the zsh completion into ``~/.owlbear/`` and asks separately
before the ``~/.local/bin/owlbear`` link, the shaper's links in ``~/.copilot`` and the login item (TD-258, TD-260,
TD-335). ``~/.zshrc`` is only named.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import local_home, preload
from owlbear_delivery_next.machine_host import control, registry
from owlbear_delivery_next.runtimes import readiness

if TYPE_CHECKING:
    from collections.abc import Callable

    from cyclopts import App

    from owlbear_delivery_next.machine_host.control import Say

COMPLETION = "completion.zsh"


def link_path() -> Path:
    """Where the command's link goes: a folder on most PATHs, never a system one."""
    return Path.home() / ".local" / "bin" / "owlbear"


def runtime() -> Path:
    """The installed runtime the command and the login item run from."""
    return local_home.root() / "runtime"


def shaper_links() -> list[tuple[Path, Path]]:
    """Each ``~/.copilot`` link the shaper needs and what it names, through the runtime alias (TD-165, TD-335)."""
    package = local_home.stable(Path(str(files("owlbear_delivery_next"))) / "__init__.py").parent
    skill = Path.home() / ".copilot" / "skills" / preload.CHAT
    return [
        (readiness.shaper_path(Path.home()), package / "agents" / readiness.SHAPER),
        (skill, package / "skills" / preload.CHAT),
    ]


def _link(link: Path, target: Path) -> str:
    """Point *link* at *target*, over an earlier link but never over a file or folder."""
    if link.exists() and not link.is_symlink():
        return f"{link} exists and is no link; left as it is"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.unlink(missing_ok=True)
    link.symlink_to(target)
    return f"linked {link}"


def install(say: Say, ask: Callable[[str], bool], app: App) -> int:
    """Write the completion, then link the command and the shaper and add the login item, each only after a yes."""
    command = local_home.stable(Path(sys.executable).parent / "owlbear")  # the alias, so updates keep it
    if not command.is_relative_to(runtime()):
        say(f"run this from the installed runtime: {runtime() / '.venv' / 'bin' / 'owlbear'} install")
        return 1
    path = local_home.root() / COMPLETION
    script = app.generate_completion(shell="zsh")  # noqa: S604 - the script's shell; it is static (TD-263)
    path.write_text(f"{script}\ncompdef _cyclopts_owlbear owlbear  # sourced, not autoloaded: register it\n")
    say(f"completion written to {path}; to use it, add this line to ~/.zshrc after compinit: source {path}")
    target = link_path()
    if ask(f"Link {target} to {command}, so `owlbear` runs in any shell?"):
        said = _link(target, command)
        hint = said.startswith("linked") and not shutil.which("owlbear")
        say(said + (f"; add {target.parent} to your PATH" if hint else ""))
    if ask(f"Link the shaper and its skill into {Path.home() / '.copilot'}, so New Change finds them anywhere?"):
        for link, to in shaper_links():
            say(_link(link, to))
    if ask("Start OwlBear at login, paused until you press Resume?"):
        return control.autostart(say, on=True)
    return 0


def uninstall(say: Say) -> int:
    """Remove the login item and the links install made; the runtime and every project stay."""
    control.autostart(say, on=False)
    ours = [link for link, to in shaper_links() if link.is_symlink() and link.readlink() == to]  # never the owner's
    for target in [link_path(), *ours]:
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
