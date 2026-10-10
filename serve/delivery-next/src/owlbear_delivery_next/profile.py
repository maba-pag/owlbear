"""Detect, confirm and re-read the project profile: GitHub facts, CI, rules and merge settings (D4 §3.2, DR1)."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import yaml

from owlbear_delivery_next.git.git_executable import resolve_git_executable
from owlbear_delivery_next.github.gh import GhProvider
from owlbear_delivery_next.github.provider import MergeMethod
from owlbear_delivery_next.models import Profile, ProfileEntry

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from owlbear_delivery_next.github.provider import Provider, Rules

HOST, REPO, DEFAULT = "github:host", "github:repository", "github:default-branch"
METHODS, PUSH = "github:merge-methods", "github:can-push"
RULES, REQUIRED, QUEUE = "github:rules", "github:required-checks", "github:merge-queue"
WORKFLOWS, DECLARED = "ci:workflows", "ci:declared"
METHOD, DELETE, HOOKS = "merge:method", "cleanup:delete-remote-branch", "git:pre-push-hook"
POLL, WINDOW = "poll:ci-seconds", "ci:start-window-seconds"
SETTINGS = {METHOD: "", DELETE: "no", POLL: "20", WINDOW: "300"}  # owner settings; kept across re-detection
CONFIRMED = "owner confirmed"
_PREFERRED = (MergeMethod.SQUASH, MergeMethod.MERGE, MergeMethod.REBASE)
CI_EVENTS = frozenset({"pull_request", "pull_request_target", "merge_group"})
HEAD_EVENTS = frozenset({"pull_request", "pull_request_target"})  # their checks report on the PR head
NODE_LOCKS = (("package-lock.json", "npm", "npm ci"), ("pnpm-lock.yaml", "pnpm", "pnpm install --frozen-lockfile"))
NO_TEST = 'echo "Error: no test specified"'


def _node(repo: Path, d: str) -> tuple[ProfileEntry, ProfileEntry]:
    lock = next(((f, tool, cmd) for f, tool, cmd in NODE_LOCKS if (repo / d / f).is_file()), None)
    install = (
        _entry("known", lock[2], f"{d}/{lock[0]}") if lock else _entry("unknown", "", f"{d}: no npm or pnpm lockfile")
    )
    try:
        test = json.loads((repo / d / "package.json").read_text()).get("scripts", {}).get("test", "")
    except OSError, ValueError, AttributeError:
        test = ""
    ok = isinstance(test, str) and test and not test.startswith(NO_TEST)
    tool = lock[1] if lock else "npm"
    evidence = f"{d}/package.json scripts.test"
    check = _entry("known", f"{tool} test", evidence) if ok else _entry("unknown", "", f"{evidence}: none")
    return install, check


def _python(repo: Path, d: str) -> tuple[ProfileEntry, ProfileEntry]:
    locked = (repo / d / "uv.lock").is_file()
    install = (
        _entry("known", "uv sync --locked", f"{d}/uv.lock") if locked else _entry("unknown", "", f"{d}: no uv.lock")
    )
    pytest = locked and "[tool.pytest" in (repo / d / "pyproject.toml").read_text(errors="replace")
    evidence = f"{d}/pyproject.toml [tool.pytest]"
    return install, _entry("known", "uv run pytest", evidence) if pytest else _entry("unknown", "", f"{evidence}: none")


def package_entries(repo: Path) -> dict[str, ProfileEntry]:
    """Install and check commands per tracked package manifest; an undetected command is unknown, never assumed."""
    files = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
        [resolve_git_executable(), "ls-files", "*package.json", "*pyproject.toml"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.splitlines()
    entries: dict[str, ProfileEntry] = {}
    for f in files:
        path = PurePosixPath(f)
        d = str(path.parent)
        install, check = (_node if path.name == "package.json" else _python)(repo, d)
        entries |= {f"install:{d}": install, f"check:{d}": check}
    return entries


def _entry(state: str, value: str, evidence: str) -> ProfileEntry:
    return ProfileEntry(state=state, value=value, evidence=evidence)  # type: ignore[arg-type]


@dataclass(frozen=True)
class Workflow:
    """One workflow's trigger events and job check names; None where the file does not resolve them."""

    events: frozenset[str] | None
    jobs: tuple[str, ...] | None


def _events(on: object) -> frozenset[str] | None:
    match on:
        case str():
            return frozenset({on})
        case list() | dict() if all(isinstance(e, str) for e in on):
            return frozenset(on)
    return None


def _jobs(jobs: object) -> tuple[str, ...] | None:
    if not isinstance(jobs, dict) or not jobs:
        return None
    found = []
    for key, job in jobs.items():
        if not isinstance(job, dict) or "uses" in job or "strategy" in job:
            return None  # reusable-workflow and matrix jobs report under derived names
        name = job.get("name", key)
        if not isinstance(name, str) or "${{" in name:
            return None
        found.append(name)
    return tuple(found)


def workflow(text: str) -> Workflow:
    """Parse one workflow file: its ``on`` events and each job's ``name`` or key."""
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError:
        return Workflow(None, None)
    if not isinstance(doc, dict):
        return Workflow(None, None)
    on = doc["on"] if "on" in doc else doc.get(True)  # YAML 1.1 reads a bare `on` key as true
    return Workflow(_events(on), _jobs(doc.get("jobs")))


def workflows(repo: Path) -> dict[str, Workflow]:
    """Return every workflow of *repo* by file name."""
    paths = sorted((repo / ".github" / "workflows").glob("*.y*ml"))
    return {p.name: workflow(p.read_text(errors="replace")) for p in paths}


def ci_entries(flows: dict[str, Workflow]) -> dict[str, ProfileEntry]:
    """CI workflows and declared check names; an unresolved trigger or name is unknown, never "no CI"."""
    ci = {n: w for n, w in flows.items() if w.events is None or w.events & CI_EVENTS}
    triggers = [n for n, w in ci.items() if w.events is None]
    on_head = {n: w for n, w in ci.items() if w.events and w.events & HEAD_EVENTS}
    names = [n for n, w in on_head.items() if w.jobs is None]
    declared = ", ".join(dict.fromkeys(j for w in on_head.values() for j in w.jobs or ())) or "none"
    flow_ev = f"unresolved trigger: {', '.join(triggers)}" if triggers else ".github/workflows CI triggers"
    job_ev = f"unresolved check names: {', '.join(names + triggers)}" if names or triggers else "jobs"
    return {
        WORKFLOWS: _entry("unknown" if triggers else "known", ", ".join(ci) or "none", flow_ev),
        DECLARED: _entry("unknown" if names or triggers else "known", declared, job_ev),
    }


def pre_push_hook(repo: Path) -> tuple[bool, str]:
    """Whether an executable pre-push hook is installed, and Git's hooks path for it."""
    out = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
        [resolve_git_executable(), "rev-parse", "--git-path", "hooks/pre-push"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    path = repo / out if out else None
    return bool(path and path.is_file() and os.access(path, os.X_OK)), out


def _hook(repo: Path) -> ProfileEntry:
    present, out = pre_push_hook(repo)
    return _entry("known", "present" if present else "none", f"git hooks path: {out or 'unknown'}")


def rule_entries(rules: Rules) -> dict[str, ProfileEntry]:
    """Profile entries of effective rules; an HTTP 403 leaves every one unknown with GitHub's message."""
    if rules.state == "unknown":
        return {k: _entry("unknown", "", rules.evidence) for k in (RULES, REQUIRED, QUEUE)}
    return {
        RULES: _entry("known", ", ".join(rules.types) or "none", rules.evidence),
        REQUIRED: _entry("known", ", ".join(rules.required_checks) or "none", rules.evidence),
        QUEUE: _entry("known", "yes" if rules.queue_required else "no", rules.evidence),
    }


def detect(repo: Path, gh: Provider, previous: Profile | None) -> Profile:
    """Detect the profile; owner settings, install and allow entries and still-valid confirmations are kept."""
    prev = previous or Profile()
    r = gh.read_repository()
    host = urlparse(r.url).hostname or "github.com"
    methods = ", ".join(r.methods)
    entries = {
        HOST: _entry("known", host, "gh repo view"),
        REPO: _entry("known", r.repository, "gh repo view"),
        DEFAULT: _entry("known", r.default_branch, "gh repo view"),
        METHODS: _entry("known", methods or "none", "gh repo view"),
        PUSH: _entry("known", "yes" if r.can_push else "no", "gh repo view viewerPermission"),
        **ci_entries(workflows(repo)),
        HOOKS: _hook(repo),
        **package_entries(repo),
        **rule_entries(gh.read_rules(r.repository, r.default_branch)),
    }
    for key, default in SETTINGS.items():
        old = prev.entries.get(key)
        entries[key] = old or _entry("known", default, "default")
    if not entries[METHOD].value or entries[METHOD].value not in r.methods:
        chosen = next((m for m in _PREFERRED if m in r.methods), "")
        entries[METHOD] = _entry("known" if chosen else "unsupported", chosen, f"allowed: {methods or 'none'}")
    for key, old in prev.entries.items():
        new = entries.get(key)
        if new is None or (old.evidence.startswith(CONFIRMED) and old.evidence.endswith(f"observed: {new.evidence}")):
            entries[key] = old
    changed = entries != prev.entries
    return prev.model_copy(update={"entries": entries, "version": prev.version + 1 if changed else prev.version})


def confirm(profile: Profile, key: str, value: str, now: datetime) -> Profile:
    """Record the owner's confirmation of one entry; it holds while GitHub's observation stays the same."""
    old = profile.entries.get(key) or _entry("unknown", "", "not detected")
    entry = _entry("known", value, f"{CONFIRMED} {now:%Y-%m-%d}; observed: {old.evidence}")
    entries = {**profile.entries, key: entry}
    return profile.model_copy(update={"entries": entries, "version": profile.version + 1, "confirmed_at": now})


def reread(profile: Profile, gh: Provider, branch: str) -> tuple[list[str], Rules]:
    """Re-read effective rules and required checks; return each difference from the profile and the rules."""
    rules = gh.read_rules(value(profile, REPO), branch)
    diffs = []
    for key, new in rule_entries(rules).items():
        old = profile.entries.get(key)
        if old is None:
            diffs.append(f"{key}: not in the profile, now {new.value or new.state}")
        elif old.evidence.startswith(CONFIRMED):
            if not old.evidence.endswith(f"observed: {new.evidence}"):
                diffs.append(f"{key}: confirmed '{old.value}', GitHub now reports {new.evidence}")
        elif (old.state, old.value) != (new.state, new.value):
            diffs.append(f"{key}: profile '{old.value or old.state}', now '{new.value or new.state}'")
    return diffs, rules


def value(profile: Profile, key: str, default: str = "") -> str:
    """Return one entry's value, or *default* when it is absent or empty."""
    entry = profile.entries.get(key)
    return entry.value if entry and entry.value else default


def names(profile: Profile, key: str) -> tuple[str, ...]:
    """Return a comma-separated entry as names; ``none`` and unknown entries give none."""
    entry = profile.entries.get(key)
    if entry is None or entry.state != "known" or entry.value in {"", "none"}:
        return ()
    return tuple(n.strip() for n in entry.value.split(",") if n.strip())


def known(profile: Profile, key: str) -> bool:
    """Whether one entry is known, by detection or by the owner's confirmation."""
    entry = profile.entries.get(key)
    return entry is not None and entry.state == "known"


def provider(profile: Profile, repo: Path) -> GhProvider:
    """Return the ``gh`` provider for the profile's host, run in *repo*."""
    return GhProvider(repo, host=value(profile, HOST, "github.com"))
