"""Setup: readiness check, profile confirmation, and tracked writes only with consent (D4 §3.2, DR1, DR2, DR14)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next import profile
from owlbear_delivery_next.models import Profile, ProfileEntry
from owlbear_delivery_next.sdk_adapter import cli_path
from owlbear_delivery_next.store import Store

if TYPE_CHECKING:
    from collections.abc import Callable

type Probe = Callable[[list[str]], tuple[int, str]]
type Ask = Callable[[str], str]
TASK = "OwlBear Delivery host"
SERVER = "owlbear-delivery"
PUSH = frozenset({"WRITE", "MAINTAIN", "ADMIN"})


@dataclass(frozen=True)
class Check:
    """One readiness fact: ok, or one concrete fix."""

    name: str
    ok: bool
    detail: str
    fix: str = ""


def probe_in(cwd: Path) -> Probe:
    """Run one command in *cwd*, bounded; a missing program is exit 127."""

    def run(argv: list[str]) -> tuple[int, str]:
        try:
            done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=30, check=False)  # noqa: S603
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 127, str(exc)
        return done.returncode, (done.stdout + done.stderr).strip()

    return run


def reach(host: str) -> str | None:
    """None when ``https://<host>`` answers through the configured proxy, else the error."""
    try:
        urllib.request.urlopen(urllib.request.Request(f"https://{host}/", method="HEAD"), timeout=10).close()
    except urllib.error.HTTPError:
        return None
    except (urllib.error.URLError, OSError) as exc:
        return str(getattr(exc, "reason", exc))
    return None


def _network(host: str, error: str | None) -> Check:
    if error is None:
        return Check("network", ok=True, detail=f"https://{host} answers")
    fix = "Connect to the network or set HTTPS_PROXY, then run setup again"
    if "certificate" in error.lower():
        fix = "A proxy intercepts TLS: set SSL_CERT_FILE to your company's CA bundle, then run setup again"
    return Check("network", ok=False, detail=f"https://{host}: {error}"[:200], fix=fix)


def _github(host: str, probe: Probe) -> list[Check]:
    code, text = probe(["gh", "--version"])
    if code:
        return [Check("github cli", ok=False, detail=text[:120], fix="Install the GitHub CLI: https://cli.github.com")]
    out = [Check("github cli", ok=True, detail=text.splitlines()[0])]
    code, text = probe(["gh", "auth", "status", "--hostname", host])
    if code:
        return [
            *out,
            Check("github sign-in", ok=False, detail=text[-160:], fix=f"Run `gh auth login --hostname {host}`"),
        ]
    out.append(Check("github sign-in", ok=True, detail=f"signed in to {host}"))
    code, text = probe(["gh", "repo", "view", "--json", "nameWithOwner,viewerPermission"])
    try:
        repo = json.loads(text) if code == 0 else {}
    except ValueError:
        repo = {}
    detail = f"{repo.get('nameWithOwner')}: {repo.get('viewerPermission')}" if repo else text[-160:]
    fix = "Point `origin` at a GitHub repository you can push to (check with `gh repo view`)"
    return [*out, Check("repository", ok=repo.get("viewerPermission") in PUSH, detail=detail, fix=fix)]


def _signing(probe: Probe) -> Check:
    if probe(["git", "config", "--bool", "commit.gpgsign"])[1].strip() != "true":
        return Check("commit signing", ok=True, detail="not required")
    fmt = probe(["git", "config", "gpg.format"])[1].strip() or "openpgp"
    key = probe(["git", "config", "user.signingkey"])[1].strip()
    if not key:
        return Check(
            "commit signing", ok=False, detail=f"{fmt} required, no key", fix="Set `git config user.signingkey`"
        )
    if fmt == "ssh":
        path = Path(key.removeprefix("key::")).expanduser()
        text = key.removeprefix("key::") if key.startswith(("ssh-", "key::")) else None
        pub = text or (path if path.suffix == ".pub" else path.with_name(path.name + ".pub")).read_text()
        ok = pub.split()[1] in probe(["ssh-add", "-L"])[1]
        return Check(
            "commit signing", ok=ok, detail=f"ssh key {'in' if ok else 'not in'} the agent", fix=f"Run `ssh-add {path}`"
        )
    if fmt != "openpgp":
        return Check("commit signing", ok=True, detail=f"{fmt}: not verified by setup")
    sign = [
        "gpg",
        "--batch",
        "--yes",
        "--pinentry-mode",
        "error",
        "-u",
        key,
        "--clearsign",
        "-o",
        "/dev/null",
        "/dev/null",
    ]
    ok = probe(sign)[0] == 0
    fix = "Unlock your GPG key (`echo test | gpg --clearsign`), then run setup again"
    return Check("commit signing", ok=ok, detail=f"gpg key {key} {'unlocked' if ok else 'locked or missing'}", fix=fix)


def readiness(host: str, probe: Probe, network: str | None, copilot: str | None) -> list[Check]:
    """Every readiness fact, in the order a fix should be applied."""
    out = [_network(host, network), *_github(host, probe)]
    code, text = probe([copilot, "--version"]) if copilot else (127, "not found")
    fix = "Install the Copilot CLI (`npm install -g @github/copilot`) or set COPILOT_CLI_PATH"
    out.append(Check("copilot cli", ok=code == 0, detail=f"{copilot}: {text.splitlines()[0] if text else ''}", fix=fix))
    name, email = probe(["git", "config", "user.name"]), probe(["git", "config", "user.email"])
    ok = name[0] == email[0] == 0 and bool(name[1] and email[1])
    fix = 'Run `git config --global user.name "Your Name"` and `git config --global user.email you@example.com`'
    out.append(Check("git identity", ok=ok, detail=f"{name[1]} <{email[1]}>" if ok else "not set", fix=fix))
    return [*out, _signing(probe)]


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
    }
    return {**data, "mcpServers": {**data.get("mcpServers", {}), SERVER: server}}


def consent(
    path: Path, merge: Callable[[dict[str, Any]], dict[str, Any]], question: str, ask: Ask, *, yes: bool
) -> str:
    """Write the tracked file *path* only with the owner's consent; return what happened."""
    if not (yes or ask(f"{question} [y/N] ").strip().lower().startswith("y")):
        return f"not written (no consent): {path}"
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except OSError, ValueError:
        data = None
    if not isinstance(data, dict):
        return f"not written: {path} is not plain JSON; add the entry by hand"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(merge(data), indent=2) + "\n")
    return f"written: {path}"


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


def run(repo: Path, confirms: list[tuple[str, str]], *, yes: bool, ask: Ask = ask_tty) -> int:
    """Readiness, profile, consented writes; print each result and the start action."""
    store, python, say = Store.open(repo), sys.executable, lambda t: sys.stdout.write(t + "\n")
    prev = store.read_profile()
    host = profile.value(prev or Profile(), profile.HOST, "github.com")
    try:
        copilot: str | None = cli_path()
    except FileNotFoundError:
        copilot = None
    checks = readiness(host, probe_in(repo), reach(host), copilot)
    say("Readiness")
    say("\n".join(f"  {'ok ' if c.ok else 'FIX'} {c.name}: {c.detail}" for c in checks))
    if failed := [c for c in checks if not c.ok]:
        say(f"Next: {failed[0].fix}")
        return 1
    prof = profile.detect(repo, profile.provider(prev or Profile(), repo), prev)
    for key, value in confirms:
        prof = profile.confirm(prof, key, value, datetime.now(UTC))
    say(render(prof))
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
    question = f"Write the folder-open task '{TASK}' into the tracked file .vscode/tasks.json?"
    tasks = consent(repo / ".vscode" / "tasks.json", lambda d: with_task(d, python), question, ask, yes=yes)
    say(tasks)
    if tasks.startswith("written"):
        say(f"VS Code starts it in a trusted workspace when automatic tasks are allowed ({automatic_tasks()});")
        say(f"otherwise run the task '{TASK}' yourself.")
    else:
        say(f"Start Delivery yourself each time you open the project: {start}. Nothing advances until it runs.")
    question = "Register the Delivery chat server in the tracked file .mcp.json?"
    server = consent(repo / ".mcp.json", lambda d: with_server(d, python, repo), question, ask, yes=yes)
    say(server)
    if not server.startswith("written"):
        say("Add this server to your MCP configuration by hand: " + json.dumps(with_server({}, python, repo)))
    return 0
