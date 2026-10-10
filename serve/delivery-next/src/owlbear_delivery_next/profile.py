"""Detect, confirm and re-read the project profile: GitHub facts, CI, rules and merge settings (D4 §3.2, DR1)."""

from __future__ import annotations

import os
import re
import subprocess
from typing import TYPE_CHECKING
from urllib.parse import urlparse

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
_JOB = re.compile(r"^(\s+)([A-Za-z0-9_-]+):\s*$")
_NAME = re.compile(r"^\s+name:\s*(.+?)\s*$")


def _entry(state: str, value: str, evidence: str) -> ProfileEntry:
    return ProfileEntry(state=state, value=value, evidence=evidence)  # type: ignore[arg-type]


def jobs(text: str) -> list[str]:
    """Return the check names of a workflow's jobs: each job's ``name`` or, without one, its key."""
    found: list[str] = []
    inside, job, body = False, None, None
    for line in text.splitlines():
        indent = len(line) - len(line.lstrip())
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if indent == 0:
            inside = line.rstrip() == "jobs:"
        elif inside and (job is None or indent == job):
            if m := _JOB.match(line):
                job, body = indent, None
                found.append(m[2])
        elif inside and found and indent == (body := body or indent) and (n := _NAME.match(line)):
            found[-1] = n[1].strip("'\"")
    return found


def workflows(repo: Path) -> dict[str, list[str]]:
    """Return the pull-request workflows of *repo* and their job check names."""
    found = {}
    for path in sorted((repo / ".github" / "workflows").glob("*.y*ml")):
        text = path.read_text(errors="replace")
        if re.search(r"^\s*pull_request(_target)?\b", text, re.MULTILINE) or "[pull_request" in text:
            found[path.name] = jobs(text)
    return found


def _hook(repo: Path) -> ProfileEntry:
    git = resolve_git_executable()
    out = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
        [git, "rev-parse", "--git-path", "hooks/pre-push"], cwd=repo, capture_output=True, text=True, check=False
    ).stdout.strip()
    path = repo / out if out else None
    present = bool(path and path.is_file() and os.access(path, os.X_OK))
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
    flows = workflows(repo)
    host = urlparse(r.url).hostname or "github.com"
    methods = ", ".join(r.methods)
    entries = {
        HOST: _entry("known", host, "gh repo view"),
        REPO: _entry("known", r.repository, "gh repo view"),
        DEFAULT: _entry("known", r.default_branch, "gh repo view"),
        METHODS: _entry("known", methods or "none", "gh repo view"),
        PUSH: _entry("known", "yes" if r.can_push else "no", "gh repo view viewerPermission"),
        WORKFLOWS: _entry("known", ", ".join(flows) or "none", ".github/workflows with a pull_request trigger"),
        DECLARED: _entry("known", ", ".join(dict.fromkeys(j for js in flows.values() for j in js)) or "none", "jobs"),
        HOOKS: _hook(repo),
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
