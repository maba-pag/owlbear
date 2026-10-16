"""Setup: profile confirmation and consented untracked local writes, after readiness (D4 §3.2, DR1, DR2, DR14)."""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from owlbear_delivery_next import data_repo, design_pack, git_files, profile, readiness, roles, text_files
from owlbear_delivery_next.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.store import Store, StoreError

if TYPE_CHECKING:
    from collections.abc import Callable

type Ask = Callable[[str], str]
type Choice = Literal["yes", "no", "ask"]
TASK = "OwlBear Delivery host"
SERVER = "owlbear-delivery"
ASKS = 3  # folder names setup asks for before it stops


def _install(text: str, path: Path, what: str) -> str:
    """Write *text* to the user-level *path*; never over another file of that name (one without ``save_brief``)."""
    try:
        old = path.read_text(encoding="utf-8") if path.exists() else text
        if old != text and "save_brief" not in old:
            kind = what.rsplit(maxsplit=1)[-1]
            return f"{what} not installed: {path} holds another {kind} of that name; move it, then run setup again"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return f"{what} not installed: {path}: {exc}"
    return f"{what} installed for you only (not tracked): {path}"


def install_skill(home: Path) -> str:
    """Install the chat skill where Copilot loads personal skills."""
    text = files("owlbear_delivery_next").joinpath("skills", "delivery", "SKILL.md").read_text(encoding="utf-8")
    return _install(text, home / ".copilot" / "skills" / "delivery" / "SKILL.md", "chat skill")


def install_agent(home: Path) -> str:
    """Install the shaping chat's agent file for this user only; Delivery selects it by its URI."""
    text = files("owlbear_delivery_next").joinpath("chat_agents", readiness.SHAPER).read_text(encoding="utf-8")
    return _install(text, readiness.shaper_path(home), "shaper agent")


def recommendations(prof: Profile) -> list[str]:
    """Branch rules worth turning on for automatic merging; advice only, never blocking."""
    tips = {
        profile.STRICT: "turn on 'Require branches to be up to date before merging' for the target branch",
        profile.RESOLUTION: "turn on 'Require conversation resolution before merging' for the target branch",
    }
    return [tip for key, tip in tips.items() if profile.value(prof, key) == "no"]


def render(prof: Profile) -> str:
    """The profile grouped by known, unknown and unsupported, with evidence."""
    lines = [f"Project profile v{prof.version}"]
    for state in ("known", "unknown", "unsupported"):
        found = [(k, e) for k, e in sorted(prof.entries.items()) if e.state == state]
        lines += [f"  {state}:"] * bool(found)
        lines += [f"    {k} = {e.value!r} ({e.evidence})" for k, e in found]
    return "\n".join(lines)


def confirm(prof: Profile, ask: Ask, *, yes: bool) -> tuple[Profile, list[str]]:
    """Ask for unknown entries and record the owner's confirmation; ``--yes`` never confirms an unknown entry."""
    now = datetime.now(UTC)
    for key, e in sorted(prof.entries.items()):
        if e.state == "unknown" and not yes and (value := ask(f"{key} is unknown ({e.evidence}). Value you confirm: ")):
            prof = profile.confirm(prof, key, value, now)
    unknown = [k for k, e in prof.entries.items() if e.state == "unknown"]
    if not (yes or ask("Confirm this profile? [y/N] ").lower().startswith("y")):
        return prof.model_copy(update={"confirmed_at": None}), unknown
    by = ProfileEntry(state="known", value="--yes" if yes else "prompt", evidence=f"owner confirmed {now:%Y-%m-%d}")
    entries = {**prof.entries, "setup:confirmed-by": by}
    return prof.model_copy(update={"entries": entries, "confirmed_at": now, "version": prof.version + 1}), unknown


def with_task(data: dict[str, Any], python: str) -> dict[str, Any]:
    """tasks.json with the folder-open host task replacing any earlier one."""
    task = {
        "label": TASK,
        "type": "process",
        "command": python,
        "args": ["-m", "owlbear_delivery_next.cli", "--repo", "${workspaceFolder}", "host"],
        "isBackground": True,
        "problemMatcher": [],
        "runOptions": {"runOn": "folderOpen"},
    }
    tasks = [t for t in data.get("tasks", []) if not (isinstance(t, dict) and t.get("label") == TASK)]
    return {"version": "2.0.0", **data, "tasks": [*tasks, task]}


def with_server(data: dict[str, Any], python: str, repo: Path) -> dict[str, Any]:
    """.mcp.json with the chat server entry."""
    server = {
        "type": "stdio",
        "command": python,
        "args": ["-m", "owlbear_delivery_next.mcp_server", "--repo", str(repo)],
        "tools": ["*"],
    }
    return {**data, "mcpServers": {**data.get("mcpServers", {}), SERVER: server}}


def consent(  # noqa: PLR0913 - the file, its merge and the owner's answer
    repo: Path, path: Path, merge: Callable[[dict[str, Any]], dict[str, Any]], question: str, ask: Ask, *, yes: bool
) -> str:
    """Write the untracked file *path* only with the owner's consent and exclude it locally; never a tracked one."""
    if why := refused(repo, path):
        return why
    if not (yes or ask(f"{question} [y/N] ").strip().lower().startswith("y")):
        return f"not written (no consent): {path}"
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except OSError, ValueError:
        data = None
    if not isinstance(data, dict):
        return f"not written: {path} is not plain JSON; add the entry by hand"
    path.parent.mkdir(exist_ok=True)
    if why := refused(repo, path):  # it may have been added or linked while the owner answered
        return why
    text_files.replace_text(path, json.dumps(merge(data), indent=2) + "\n")
    git_files.exclude(repo, path)
    return f"written: {path} (kept out of git by .git/info/exclude)"


def refused(repo: Path, path: Path) -> str | None:
    """Why *path* must not be written: a symbolic link on its way inside *repo*, or tracked."""
    if linked := text_files.linked_part(repo, path):
        return f"not written: {linked} is a symbolic link; add the entry by hand"
    if not git_files.untracked(repo, path):
        return f"not written: {path} is tracked, and Delivery commits nothing into the project"
    return None


def automatic_tasks() -> str:
    """The user's ``task.allowAutomaticTasks`` setting, as far as setup can read it."""
    base = Path.home() / ("Library/Application Support" if sys.platform == "darwin" else ".config")
    settings = base / "Code" / "User" / "settings.json"
    found = re.search(r'"task\.allowAutomaticTasks"\s*:\s*"(\w+)"', settings.read_text()) if settings.exists() else None
    return found[1] if found else "not set (VS Code asks on first open)"


def ask_tty(question: str) -> str:
    """Ask on a terminal; without one, every answer is no."""
    if not sys.stdin.isatty():
        return ""
    try:
        return input(question)
    except EOFError:
        return ""


def project_folder(repo: Path, chosen: str, ask: Ask, say: Callable[[str], object]) -> bool:
    """Claim the project's folder in the shared repository; on a collision the owner names it (TD-98).

    The repository's name is the default; ``chosen`` (``--folder``) replaces it and is never asked again. False when
    no usable name was given; a folder the repository already claims is kept, renamed only on the settings page.
    """
    ident = data_repo.identity(repo)
    try:
        shared = data_repo.locate()
        held = shared.claimed(ident) if shared else None
    except data_repo.DataRepoError:
        return True  # opening the store reports it
    if shared is None or held:
        if held and chosen and chosen != held:
            say(f"This project's shared settings folder is {held}; rename it on the settings page.")
        return True
    name, asked = chosen or data_repo.project_name(repo), 0
    while True:
        if not (why := shared.refusal(name, ident)):
            try:
                with shared.locked():
                    if shared.claim(name, ident):
                        shared.publish(shared.root / name / data_repo.CLAIM, f"settings: the folder {name} is {ident}")
            except data_repo.DataRepoError as exc:
                why = str(exc)
            else:
                say(f"Shared settings folder: {shared.root / name}")
                return True
        say(f"{why}.")
        if chosen or asked == ASKS or not (name := ask("Folder name for this project in the shared settings: ")):
            break
        name, asked = name.strip(), asked + 1
    say("Run setup again with --folder NAME, a folder name no other repository uses.")
    return False


def run(  # noqa: PLR0913 - one answer per consent
    repo: Path,
    confirms: list[tuple[str, str]],
    *,
    yes: bool,
    local_files: Choice = "ask",
    skill: Choice = "ask",
    ask: Ask = ask_tty,
) -> int:
    """Readiness, profile, consented writes; print each result and the start action.

    ``yes`` confirms the profile only (TD-11): the local files and the user-level skill each need their own
    answer, given by flag or asked; without a terminal an unasked answer is no. The command line claims the
    project's shared folder first (``project_folder``).
    """
    store, python, say = Store.open(repo), sys.executable, lambda t: sys.stdout.write(t + "\n")
    try:
        prev = store.read_profile()
    except StoreError as exc:  # setup replaces a profile it cannot read; confirming saves the new one
        say(f"The saved profile cannot be read ({exc}); detecting a new one.")
        prev = None
    checks = readiness.check(repo, prev)
    say("Readiness")
    say("\n".join(f"  {'ok ' if c.ok else 'FIX'} {c.name}: {c.detail}" for c in checks))
    if failed := [c for c in checks if not c.ok]:
        say(f"Next: {failed[0].fix}")
        return 1
    prof = profile.detect(repo, profile.provider(prev or Profile(), repo), prev)
    for key, value in confirms:
        prof = profile.confirm(prof, key, value, datetime.now(UTC))
    say(render(prof))
    say(roles.table(store.settings()))
    say(design_pack.status())
    for tip in recommendations(prof):
        say(f"TIP {tip}")
    prof, unknown = confirm(prof, ask, yes=yes)
    if unknown:
        hint = "Confirm with --confirm KEY=VALUE; unknown rules keep merging human-assisted"
        say(f"Left unknown: {', '.join(sorted(unknown))}. {hint}")
    if prof.confirmed_at is None:
        say("Profile not confirmed; nothing was saved. Run setup again to confirm it.")
        return 1
    store.write_profile(prof)
    say(f"Profile v{prof.version} confirmed and saved in {store.root}")
    start = f"`{python} -m owlbear_delivery_next.cli --repo {repo} host`"
    question = f"Write the folder-open task '{TASK}' into .vscode/tasks.json (kept out of git)?"
    given, local_ask = local_files == "yes", ask if local_files == "ask" else lambda _q: ""
    tasks = consent(
        repo, repo / ".vscode" / "tasks.json", lambda d: with_task(d, python), question, local_ask, yes=given
    )
    say(tasks)
    if tasks.startswith("written"):
        say(f"VS Code starts it in a trusted workspace when automatic tasks are allowed ({automatic_tasks()});")
        say(f"otherwise run the task '{TASK}' yourself.")
    else:
        say(f"Start Delivery yourself each time you open the project: {start}. Nothing advances until it runs.")
    question = "Register the Delivery chat server in .mcp.json (kept out of git)?"
    server = consent(repo, repo / ".mcp.json", lambda d: with_server(d, python, repo), question, local_ask, yes=given)
    say(server)
    if not server.startswith("written"):
        snippet = json.dumps(with_server({}, python, repo)["mcpServers"])
        say(f'Add this under "servers" in your user-level MCP configuration (MCP: Open User Configuration): {snippet}')
    path, agent = Path.home() / ".copilot" / "skills" / "delivery" / "SKILL.md", readiness.shaper_path(Path.home())
    question = f"Install the Delivery chat skill at {path} and its shaper agent at {agent}, for you only? [y/N] "
    if not (skill == "yes" or (skill == "ask" and ask(question).strip().lower().startswith("y"))):
        say(f"chat skill and shaper agent not installed (no consent): {path}, {agent}")
        say("Run setup with --skill yes to install them.")
        return 0
    say(install_skill(Path.home()))
    say(install_agent(Path.home()))
    say("To share it with this repository, copy that folder to .github/skills/delivery/ and commit it yourself.")
    return 0
