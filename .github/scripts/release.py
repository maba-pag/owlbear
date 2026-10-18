"""Versions from merges (self-update design section 8; TD-302, TD-306, TD-315): tag labelled merges to main.

Walks main's first-parent history after the frontier, the newest commit a version tag peels to but never before
``FLOOR``, in merge order. A merge whose pull request carries ``release:minor`` or ``release:major`` becomes the next
version once its own push CI passed; one without either label, or without its pull request, is passed over. The walk
stops at the first labelled merge whose CI has not passed, which a later run continues. Only with ``RELEASE_TAGS=on``
does it tag; otherwise it reports what it would tag (TD-315).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from typing import Protocol

FLOOR = "941ee5d9d692532e9184350eb4f6b079a9b96699"  # the last merge before pushes to main ran CI
LABELS = {"release:major": "major", "release:minor": "minor"}  # major wins when both are set
VERSION = re.compile(r"v(\d+)(?:\.(\d+))?")
BOT = ("-c", "user.name=github-actions[bot]", "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com")


class GitHub(Protocol):
    """What the walk reads from GitHub."""

    def pull(self, sha: str) -> dict | None:
        """The pull request merged into main with exactly this merge commit."""
        ...

    def ci(self, sha: str) -> str:
        """The commit's own CI: ``success``, ``failure``, or ``pending`` while none has completed."""
        ...


@dataclass
class Step:
    """One merge's outcome in this run."""

    sha: str
    action: str  # "tag", "pass" or "stop"
    tag: str = ""
    why: str = ""


def git(*args: str) -> str:
    """Run one git command in the checkout and return its output."""
    done = subprocess.run(["git", *args], capture_output=True, text=True, check=True)  # noqa: S603, S607
    return done.stdout.strip()


def versions() -> list[tuple[str, tuple[int, int]]]:
    """Each version tag's commit and number; ``vN`` counts as ``(N, 0)``."""
    found = []
    for line in git(
        "for-each-ref", "refs/tags/v*", "--format=%(refname:short) %(objectname) %(*objectname)"
    ).splitlines():
        name, obj, peeled = [*line.split(), ""][:3]
        if m := VERSION.fullmatch(name):
            found.append((peeled or obj, (int(m[1]), int(m[2] or 0))))
    return found


def merges(floor: str, tip: str) -> list[tuple[str, bool]]:
    """First-parent commits after *floor* up to *tip*, oldest first, each with whether it is a merge."""
    lines = git("rev-list", "--first-parent", "--reverse", "--parents", f"{floor}..{tip}").splitlines()
    return [(parts[0], len(parts) > 2) for parts in (line.split() for line in lines)]  # noqa: PLR2004


def following(highest: tuple[int, int], kind: str) -> tuple[str, tuple[int, int]]:
    """The next version after *highest*: ``vX+1`` for a major one, ``vX.Y+1`` for a minor one."""
    major, minor = highest
    return (f"v{major + 1}", (major + 1, 0)) if kind == "major" else (f"v{major}.{minor + 1}", (major, minor + 1))


def plan(gh: GitHub, floor: str, tip: str) -> list[Step]:
    """Decide each merge after the frontier against the tags as they are now."""
    tags = versions()
    tagged = {sha for sha, _ in tags}
    walk = merges(floor, tip)
    start = max((i + 1 for i, (sha, _) in enumerate(walk) if sha in tagged), default=0)
    highest = max((v for _, v in tags), default=(0, 0))
    steps = []
    for sha, merge in walk[start:]:
        pr = gh.pull(sha) if merge else None
        kinds = {LABELS[label["name"]] for label in (pr or {}).get("labels", []) if label["name"] in LABELS}
        if not kinds:
            why = "not a merge" if not merge else "no pull request" if pr is None else f"#{pr['number']} has no label"
            steps.append(Step(sha, "pass", why=why))
            continue
        if (ci := gh.ci(sha)) != "success":
            steps.append(Step(sha, "stop", why=f"#{pr['number']}: its CI is {ci}"))
            break
        name, highest = following(highest, "major" if "major" in kinds else "minor")
        steps.append(Step(sha, "tag", tag=name, why=f"#{pr['number']} {pr['title']}"))
    return steps


def tag(step: Step) -> None:
    """Create the annotated tag and push it, never forced: an existing name fails the run."""
    git(*BOT, "tag", "-a", step.tag, "-m", f"{step.tag}: {step.why}", step.sha)
    git("push", "origin", f"refs/tags/{step.tag}")


class Api:
    """GitHub's REST API with the workflow's token."""

    def __init__(self, repo: str, token: str, base: str = "https://api.github.com") -> None:
        self.repo, self.token, self.base = repo, token, base

    def _get(self, path: str) -> object:
        request = urllib.request.Request(  # noqa: S310 - the API's own https URL
            f"{self.base}/repos/{self.repo}/{path}",
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return json.load(response)

    def pull(self, sha: str) -> dict | None:
        """The pull request merged into main with exactly this merge commit."""
        found = self._get(f"commits/{sha}/pulls")
        return next((p for p in found if p.get("merge_commit_sha") == sha and p["base"]["ref"] == "main"), None)

    def ci(self, sha: str) -> str:
        """The latest run of the ``CI`` check on this commit."""
        runs = self._get(f"commits/{sha}/check-runs?check_name=CI&filter=latest")["check_runs"]
        if not runs or any(r["status"] != "completed" for r in runs):
            return "pending"
        return "success" if all(r["conclusion"] == "success" for r in runs) else "failure"


def main() -> int:
    """Walk, then tag or only report; the report goes to the job summary."""
    api = os.environ.get("GITHUB_API_URL") or "https://api.github.com"
    gh = Api(os.environ["GITHUB_REPOSITORY"], os.environ["GH_TOKEN"], api)
    live = os.environ.get("RELEASE_TAGS") == "on"
    mode = "tagging" if live else "dry run: nothing is tagged"
    lines = [f"Release walk after {FLOOR[:9]} to {git('rev-parse', '--short', 'HEAD')}, {mode}"]
    for step in plan(gh, FLOOR, "HEAD"):
        if step.action == "tag" and live:
            tag(step)
        verb = {"tag": "tagged" if live else "would tag", "pass": "passed over", "stop": "stopped at"}[step.action]
        lines.append(f"- {verb} {step.sha[:9]}{f' as {step.tag}' if step.tag else ''}: {step.why}")
    report = "\n".join(lines) + "\n"
    sys.stdout.write(report)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as out:  # noqa: PTH123
            out.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
