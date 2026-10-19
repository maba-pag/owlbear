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
CI = ".github/workflows/ci.yml"
VERSION = re.compile(r"v(\d+)(?:\.(\d+))?")
TAGGER = {"name": "github-actions[bot]", "email": "41898282+github-actions[bot]@users.noreply.github.com"}


class GitHub(Protocol):
    """What the walk reads from GitHub."""

    def pull(self, sha: str) -> dict | None:
        """The pull request merged into main with exactly this merge commit."""
        ...

    def ci(self, sha: str) -> str:
        """The commit's own CI: ``success``, ``failure``, or ``pending`` while none has completed."""
        ...

    def create(self, name: str, sha: str, message: str) -> None:
        """Create the annotated tag *name* on *sha*, never moving an existing one."""
        ...


@dataclass
class Step:
    """One merge's outcome in this run."""

    sha: str
    action: str  # "tag", "pass" or "stop"
    tag: str = ""
    why: str = ""


def git(*args: str) -> str:
    """Run one git command in the checkout and return its output; a failure prints git's own message."""
    done = subprocess.run(["git", *args], capture_output=True, text=True, check=False)  # noqa: S603, S607
    if done.returncode:
        sys.stderr.write(done.stderr)
        done.check_returncode()
    return done.stdout.strip()


def tags() -> dict[str, str]:
    """Each version-like tag's name and the commit it peels to."""
    found = {}
    for line in git(
        "for-each-ref", "refs/tags/v*", "--format=%(refname:short) %(objectname) %(*objectname)"
    ).splitlines():
        name, obj, peeled = [*line.split(), ""][:3]
        found[name] = peeled or obj
    return found


def versions() -> list[tuple[str, tuple[int, int]]]:
    """Each version tag's commit and number; ``vN`` counts as ``(N, 0)``."""
    return [(sha, (int(m[1]), int(m[2] or 0))) for name, sha in tags().items() if (m := VERSION.fullmatch(name))]


def unpaired() -> list[tuple[str, str]]:
    """A major's missing partner, ``vN`` for ``vN.0`` or the reverse, with the commit it belongs on (TD-392)."""
    found = tags()
    missing = []
    for name, sha in found.items():
        if (m := VERSION.fullmatch(name)) and int(m[1]) > 0 and m[2] in (None, "0"):
            partner = f"v{m[1]}" if m[2] else f"v{m[1]}.0"
            if partner not in found:
                missing.append((partner, sha))
    return missing


def merges(floor: str, tip: str) -> list[tuple[str, bool]]:
    """First-parent commits after *floor* up to *tip*, oldest first, each with whether it is a merge."""
    lines = git("rev-list", "--first-parent", "--reverse", "--parents", f"{floor}..{tip}").splitlines()
    return [(parts[0], len(parts) > 2) for parts in (line.split() for line in lines)]  # noqa: PLR2004


def following(highest: tuple[int, int], kind: str) -> tuple[str, tuple[int, int]]:
    """The next version after *highest*: ``vX+1.0`` for a major one, ``vX.Y+1`` for a minor one."""
    major, minor = highest
    return (f"v{major + 1}.0", (major + 1, 0)) if kind == "major" else (f"v{major}.{minor + 1}", (major, minor + 1))


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


def tag(gh: GitHub, step: Step) -> None:
    """Create the step's annotated tags through GitHub; an existing name fails the run.

    A major version ``vN.0`` also gets ``vN`` on the same commit (TD-392). GitHub refuses the workflow token a git
    push of a tag whose commit's workflow files differ from every branch tip, so the tags are made through the API.
    """
    names = [step.tag, step.tag.removesuffix(".0")] if step.tag.endswith(".0") else [step.tag]
    for name in names:
        gh.create(name, step.sha, f"{name}: {step.why}")


class Api:
    """GitHub's REST API with the workflow's token."""

    def __init__(self, repo: str, token: str, base: str = "https://api.github.com") -> None:
        self.repo, self.token, self.base = repo, token, base

    def _call(self, path: str, body: dict | None = None) -> object:
        request = urllib.request.Request(  # noqa: S310 - the API's own https URL
            f"{self.base}/repos/{self.repo}/{path}",
            data=None if body is None else json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json"},
            method="GET" if body is None else "POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return json.load(response)

    def create(self, name: str, sha: str, message: str) -> None:
        """The tag object first, then its ref; GitHub answers 422 for a ref that exists, which fails the run."""
        tag = {"tag": name, "message": message, "object": sha, "type": "commit", "tagger": TAGGER}
        made = self._call("git/tags", tag)
        self._call("git/refs", {"ref": f"refs/tags/{name}", "sha": made["sha"]})

    def pull(self, sha: str) -> dict | None:
        """The pull request merged into main with exactly this merge commit."""
        found = self._call(f"commits/{sha}/pulls")
        return next((p for p in found if p.get("merge_commit_sha") == sha and p["base"]["ref"] == "main"), None)

    def ci(self, sha: str) -> str:
        """The newest run of the CI workflow for this merge's own push to main."""
        found = self._call(f"actions/runs?head_sha={sha}&event=push&branch=main&per_page=100")["workflow_runs"]
        runs = [r for r in found if r.get("path") == CI]
        if not runs or (run := max(runs, key=lambda r: r["id"]))["status"] != "completed":
            return "pending"
        return "success" if run["conclusion"] == "success" else "failure"


def main() -> int:
    """Walk, then tag or only report; the report goes to the job summary."""
    api = os.environ.get("GITHUB_API_URL") or "https://api.github.com"
    gh = Api(os.environ["GITHUB_REPOSITORY"], os.environ["GH_TOKEN"], api)
    live = os.environ.get("RELEASE_TAGS") == "on"
    mode = "tagging" if live else "dry run: nothing is tagged"
    lines = [f"Release walk after {FLOOR[:9]} to {git('rev-parse', '--short', 'HEAD')}, {mode}"]
    for name, sha in unpaired():
        if live:
            gh.create(name, sha, f"{name}: the partner of a major version (TD-392)")
        lines.append(f"- {'tagged' if live else 'would tag'} {sha[:9]} as {name}: the missing partner of a major")
    for step in plan(gh, FLOOR, "HEAD"):
        if step.action == "tag" and live:
            tag(gh, step)
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
