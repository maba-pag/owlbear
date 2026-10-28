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

from owlbear_delivery_next.local_system import data_place, data_repo, local_home, preload
from owlbear_delivery_next.machine_host import control
from owlbear_delivery_next.runtimes import copilot_cli, readiness
from owlbear_delivery_next.state_store import registry

if TYPE_CHECKING:
    from collections.abc import Callable

    from cyclopts import App

    from owlbear_delivery_next.machine_host.control import Say

COMPLETION = "completion.zsh"
TOOLS = ("git", "gh", "uv")  # besides the Copilot CLI, which skips VS Code's shim


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
    found = data_place.describe()
    if found.root is not None:
        say(f"kept: your shared data at {found.root}; uninstalling never removes it")
        for line in data_place.inventory(data_repo.DataRepo(found.root)):
            say(f"  only there: {line}")
    elif found.kind == "problem":
        say(f"shared data: {found.problem}; nothing of it was removed")
    return 0


def _fails(command: list[str]) -> str | None:
    """None when *command* exits 0, else its first output line or the error."""
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)  # noqa: S603
    except (OSError, subprocess.TimeoutExpired) as exc:
        return str(exc)
    lines = (done.stdout + done.stderr).strip().splitlines()
    return None if done.returncode == 0 else (lines or [f"exit {done.returncode}"])[0]


def _tools(say: Say) -> int:
    """How many of git, gh, uv and the Copilot CLI this shell cannot find or run; uv updates OwlBear."""
    failed = 0
    for tool in TOOLS:
        if (path := shutil.which(tool)) is None:
            say(
                f"{tool}: not found on PATH · fix: install it, then run `owlbear autostart on` again for the login item"
            )
            failed += 1
        elif error := _fails([path, "--version"]):
            say(f"{tool}: {path} does not run: {error} · fix: reinstall it")
            failed += 1
    try:
        copilot = copilot_cli.cli_path()
    except FileNotFoundError as exc:
        say(f"copilot: {exc}")
        return failed + 1
    if error := _fails([copilot, "--version"]):
        say(f"copilot: {copilot} does not run: {error} · fix: {copilot_cli.FIX}")
        failed += 1
    return failed


def _login_item(say: Say) -> int:
    """How many tools the login item cannot find; the host it starts sees only its saved environment."""
    if (env := control.saved_env()) is None:
        return 0
    saved, cli = env.get("PATH", ""), env.get("COPILOT_CLI_PATH")
    missing = [tool for tool in TOOLS if shutil.which(tool, path=saved) is None]
    if (shutil.which(cli, path=saved) if cli else copilot_cli.find(saved)) is None:
        missing.append(f"copilot at its COPILOT_CLI_PATH {cli}" if cli else "copilot")
    for tool in missing:
        say(f"login item: {tool} not found · fix: run `owlbear autostart on` from a shell where it runs")
    return len(missing)


def _data(say: Say) -> int:
    """1 when the shared data repository the machine is set to cannot be used; its warning is said either way."""
    found = data_place.describe()
    if found.kind == "problem":
        say(f"{found.line} · fix: `owlbear data` shows it")
    elif found.warning:
        say(f"shared data: {found.warning}")
    return int(found.kind == "problem")


def doctor(say: Say, dropped: list[str]) -> int:
    """What the host's environment cannot do: its tools, gh's login, the login item and each project's readiness."""
    from owlbear_delivery_next.runtimes import readiness  # noqa: PLC0415 - only doctor needs it
    from owlbear_delivery_next.state_store.store import Store, StoreError  # noqa: PLC0415

    for name in dropped:
        say(f"ignored from this shell: {name} (the host never sees it; a project's own Git settings decide)")
    failed = _tools(say)
    if shutil.which("gh"):
        done = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, check=False)  # noqa: S607
        if done.returncode:
            say("gh: not signed in from this environment · fix: gh auth login")
            failed += 1
    failed += _login_item(say)
    failed += _data(say)
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
