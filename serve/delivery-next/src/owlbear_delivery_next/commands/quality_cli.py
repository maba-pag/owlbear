"""Run the project's confirmed lint command, or discovered tools, without a running host."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_quality import run as runner
from owlbear_quality import trees

from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.settings import profile

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.profile_record import Profile


def changed(root: Path, ref: str) -> list[str]:
    """Existing files changed from the merge-base, staged or not, and nonignored untracked files."""
    base = trees.git(root, "merge-base", "HEAD", ref).strip()
    tracked = trees.git(root, "diff", "--name-only", "--no-renames", "--diff-filter=ACMT", "-z", base, "--")
    untracked = trees.git(root, "ls-files", "--others", "--exclude-standard", "-z")
    return sorted({p for p in (tracked + untracked).split("\0") if p and (root / p).is_file()})


def run(repo: Path, prof: Profile, base: str = "") -> int:
    """Print every linter result; problems exit 1, tools that cannot run exit 2."""
    try:
        root = Path(trees.git(repo, "rev-parse", "--show-toplevel").strip())
        target = base or profile.value(prof, profile.DEFAULT)
        if not target:
            sys.stderr.write("No target branch in the profile; pass --base REF.\n")
            return 2
        ref = base or worktree.tracking(root, target)
        paths = changed(root, ref)
        linters, skipped = runner.plan(root, paths, profile.lint_commands(prof))
        for reason in skipped:
            sys.stdout.write(f"skipped: {reason}\n")
        result = 0
        for linter in linters:
            out = runner.run(root, linter)
            sys.stdout.write(f"{linter.name}: {out.state}" + (f" ({out.reason})" if out.reason else "") + "\n")
            if out.output:
                sys.stdout.write(out.output + "\n")
            result = max(result, {"passed": 0, "failed": 1, "broken": 2}[out.state])
        if not paths:
            sys.stdout.write("No changed files to lint.\n")
    except (OSError, RuntimeError, ValueError) as exc:
        sys.stderr.write(f"quality lint in {repo}: {type(exc).__name__}: {exc}\n")
        return 2
    return result
