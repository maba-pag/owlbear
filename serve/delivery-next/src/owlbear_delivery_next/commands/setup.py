"""Setup: profile confirmation and consented untracked local writes, after readiness (D4 §3.2, DR1, DR2, DR14)."""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.design_packs import design_pack
from owlbear_delivery_next.local_system import data_repo, git_files, local_home, text_files
from owlbear_delivery_next.runtimes import readiness, window_files
from owlbear_delivery_next.settings import profile, roles
from owlbear_delivery_next.state_store import prefs_import, profile_repair, profile_share, roles_move
from owlbear_delivery_next.state_store.profile_errors import SharedSyncError, SourceChangedError
from owlbear_delivery_next.state_store.store import RoleSourceError, Store, StoreError

if TYPE_CHECKING:
    from collections.abc import Callable

type Ask = Callable[[str], str]
type Choice = Literal["yes", "no", "ask"]
TASK = "OwlBear Delivery host"
SERVER = "owlbear-delivery"
ASKS = 3  # folder names setup asks for before it stops


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
        if (
            e.state == "unknown"
            and key not in profile.SETTINGS
            and not yes
            and (value := ask(f"{key} is unknown ({e.evidence}). Value you confirm: "))
        ):
            prof = profile.confirm(prof, key, value, now)
    unknown = [k for k, e in prof.entries.items() if e.state == "unknown" and k not in profile.SETTINGS]
    if not (yes or ask("Confirm this profile? [y/N] ").lower().startswith("y")):
        return prof.model_copy(update={"confirmed_at": None}), unknown
    by = ProfileEntry(state="known", value="--yes" if yes else "prompt", evidence=f"owner confirmed {now:%Y-%m-%d}")
    entries = {**prof.entries, "setup:confirmed-by": by}
    return prof.model_copy(update={"entries": entries, "confirmed_at": now, "version": prof.version + 1}), unknown


def without_task(data: dict[str, Any]) -> dict[str, Any]:
    """tasks.json without the folder-open host task an earlier setup wrote (TD-281)."""
    return {**data, "tasks": [t for t in data.get("tasks", []) if not (isinstance(t, dict) and t.get("label") == TASK)]}


def has_task(path: Path) -> bool:
    """Whether *path* holds the earlier folder-open host task."""
    try:
        data = json.loads(path.read_text())
    except OSError, ValueError:
        return False
    return isinstance(data, dict) and any(isinstance(t, dict) and t.get("label") == TASK for t in data.get("tasks", []))


def with_server(data: dict[str, Any], python: str, repo: Path) -> dict[str, Any]:
    """.mcp.json with the chat server entry."""
    server = {
        "type": "stdio",
        "command": python,
        "args": ["-m", "owlbear_delivery_next", "mcp", "--repo", str(repo)],
        "tools": ["*"],
    }
    return {**data, "mcpServers": {**data.get("mcpServers", {}), SERVER: server}}


def user_mcp(home: Path) -> Path:
    """The user's VS Code MCP configuration."""
    base = home / ("Library/Application Support" if sys.platform == "darwin" else ".config")
    return base / "Code" / "User" / "mcp.json"


def _loose_json(text: str) -> object:
    """JSON as VS Code writes its own files: line comments, block comments and trailing commas allowed."""
    text = re.sub(r'("(?:\\.|[^"\\])*")|//[^\n]*|/\*.*?\*/', lambda m: m[1] or "", text, flags=re.DOTALL)
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", text))


def _serves(servers: object, repo: Path) -> bool:
    """Whether one of *servers* is Delivery's chat server for *repo*."""
    entries = servers.values() if isinstance(servers, dict) else []
    return any(
        isinstance(e, dict) and isinstance(args := e.get("args"), list)
        and "owlbear_delivery_next" in args and "mcp" in args and str(repo) in args
        for e in entries
    )  # fmt: skip


def registered(repo: Path, home: Path | None = None) -> bool:
    """Whether the chat server of *repo* is registered: in its ``.mcp.json`` or the user's MCP configuration."""
    for path, key in ((repo / ".mcp.json", "mcpServers"), (user_mcp(home or Path.home()), "servers")):
        try:
            data = _loose_json(path.read_text())
        except OSError, ValueError:
            continue
        if isinstance(data, dict) and _serves(data.get(key), repo):
            return True
    return False


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


def _saved(store: Store, say: Callable[[str], object]) -> tuple[Profile | None, bool, str, str]:
    """The saved profile setup may replace, as ``(prev, unreadable, source, target)``.

    *source* is the digest of this clone's old profile file when its role overrides cannot be inspected, or ``absent``
    when only the shared profile is unreadable; *target* is the digest of the shared profile it is confirmed against.
    Readability and those digests come from one observation of the same bytes, taken now, so a stale open-time error
    never offers a replacement for a file that reads. A readable profile is never replaced for its old roles.
    """
    reason: StoreError | None = None
    try:
        prev = store.read_profile()
    except StoreError as exc:  # setup replaces a profile it cannot read; confirming saves the new one
        prev, reason = None, exc
    digest, now = roles_move.snapshot(store.root / profile_share.PROFILE)
    # unshared: the shared profile is this same local file, so its target is the bytes just observed
    target, target_now = roles_move.snapshot(profile_share.path(store)) if store.shared else (digest, now)
    if now is None:
        if store.deferred_roles is not None:
            msg = "the old profile can be read now; run setup again to review it"
            raise StoreError(msg)
        if reason is None:
            return prev, False, "", ""
        if store.shared and digest == profile_share.ABSENT:  # the shared profile alone is unreadable
            return _shared_only(target, target_now, reason, say)
        if target_now is None:  # the destination reads now: the error came from elsewhere, so nothing is replaced
            msg = f"the saved profile could not be read ({reason}) and reads now; nothing was replaced; run setup again"
            raise StoreError(msg)
        if not target:
            raise target_now
        _announce(reason, say)
        return None, True, digest, target
    if prev is not None or not digest:  # a readable shared profile with an unreadable clone file: open refuses it
        raise now
    if not target:  # the shared profile cannot be read to a digest: its own error is the explanation
        raise target_now or now
    _announce(reason or now, say)
    return None, True, digest, target


def _shared_only(
    target: str, target_now: RoleSourceError | None, reason: StoreError, say: Callable[[str], object]
) -> tuple[Profile | None, bool, str, str]:
    """The replacement of a shared profile that is unreadable while the clone has no profile to bind."""
    if target_now is None:  # it reads now: the new bytes were not what the owner was shown, so nothing is replaced
        if target == profile_share.ABSENT:
            raise reason
        msg = "the shared profile can be read now; run setup again to review it"
        raise StoreError(msg)
    if not target:
        raise target_now
    _announce(reason, say)
    return None, True, profile_share.ABSENT, target


def _announce(cause: Exception, say: Callable[[str], object]) -> None:
    say(f"The saved profile cannot be read ({cause}); detecting a new one.")
    say(
        "Confirming replacement discards the unreadable profile, including any unrecoverable legacy role "
        "overrides; declining keeps it."
    )


def run(
    repo: Path,
    confirms: list[tuple[str, str]],
    *,
    yes: bool,
    local_files: Choice = "ask",
    ask: Ask = ask_tty,
) -> int:
    """Readiness, profile, consented writes; print each result and the start action.

    ``yes`` confirms the profile only (TD-11): the local files need their own answer, given by flag or asked;
    without a terminal an unasked answer is no. The command line claims the project's shared folder first
    (``project_folder``).
    """
    store, python, say = (
        Store.open(repo, repair=True),
        str(local_home.stable(Path(sys.executable))),
        lambda t: sys.stdout.write(t + "\n"),
    )
    if receipt := profile_repair.pending(store):  # an owner-confirmed replacement that was not yet published
        if not _publish_repair(store, receipt, say, resumed=True):
            return 1
        return _settle(store, receipt.profile, say, _project_files(repo, python, local_files, ask, say))
    prev, unreadable, source, target = _saved(store, say)
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
    if source:
        receipt = profile_repair.stage(store, prof, source, target)
        if not _publish_repair(store, receipt, say, resumed=False):
            return 1
    else:
        store.write_profile(prof, replace_unreadable=unreadable)
    return _settle(store, prof, say, _project_files(repo, python, local_files, ask, say))


def _project_files(
    repo: Path, python: str, local_files: Choice, ask: Ask, say: Callable[[str], object]
) -> Callable[[], None]:
    given, local_ask = local_files == "yes", ask if local_files == "ask" else lambda _q: ""
    return partial(write_project_files, repo, python, local_ask, say, given=given)


def _publish_repair(
    store: Store, receipt: profile_repair.Receipt, say: Callable[[str], object], *, resumed: bool
) -> bool:
    """Publish the owner's confirmed replacement of an unreadable old profile; False after saying why it did not."""
    try:
        notice = profile_repair.publish(store, receipt, resumed=resumed)
    except (SourceChangedError, SharedSyncError) as exc:
        say(str(exc))
        return False
    if notice:  # the replacement is staged and kept for the next setup: nothing is retired yet
        say(notice)
        say("The replacement is kept; run setup again to publish it.")
        return False
    return True


def _settle(store: Store, prof: Profile, say: Callable[[str], object], project_files: Callable[[], None]) -> int:
    prefs_import.run(store)
    say(f"Profile v{prof.version} confirmed and saved in {store.root}")
    project_files()
    if not readiness.shaper_path(Path.home()).exists():
        say("New Change needs the shaper in ~/.copilot: run `owlbear install` and let it link the shaper (TD-335).")
    return 0


def write_project_files(repo: Path, python: str, ask: Ask, say: Callable[[str], object], *, given: bool) -> None:
    """The chat server and the harness key, each written only with its own consent; an earlier host task goes.

    Opening a window never starts Delivery (TD-281): OwlBear runs once per machine and serves the projects
    added on its page.
    """
    tasks = repo / ".vscode" / "tasks.json"
    if has_task(tasks):
        question = f"Remove the folder-open task '{TASK}' an earlier setup wrote into .vscode/tasks.json?"
        say(consent(repo, tasks, without_task, question, ask, yes=given).replace("written", "rewritten", 1))
    say("Delivery runs in OwlBear: run `owlbear start`, then add this project on its page.")
    question = "Register the Delivery chat server in .mcp.json (kept out of git)?"
    server = consent(repo, repo / ".mcp.json", lambda d: with_server(d, python, repo), question, ask, yes=given)
    say(server)
    if not server.startswith("written"):
        snippet = json.dumps(with_server({}, python, repo)["mcpServers"])
        say(f'Add this under "servers" in your user-level MCP configuration (MCP: Open User Configuration): {snippet}')
    question = f"Set {window_files.HARNESS} in .vscode/settings.json for New Change's Copilot chat (kept out of git)?"
    settings = repo / window_files.SETTINGS  # the window reads the key only when it starts (TD-275)
    say(consent(repo, settings, lambda d: {**d, window_files.HARNESS: True}, question, ask, yes=given))
