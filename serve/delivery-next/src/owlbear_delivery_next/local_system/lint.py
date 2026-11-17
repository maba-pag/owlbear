"""One Delivery session's lint budget, refusals and activity log."""

from __future__ import annotations

from time import monotonic
from typing import TYPE_CHECKING

from owlbear_quality import run as runner

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path, PurePosixPath

BUDGET = 180
SHOWN = 60
REFUSALS = 5
TIMEOUT = runner.TIMEOUT


def _shown(output: str) -> str:
    lines = output.splitlines() or ["(no output)"]
    more = f"\n... {len(lines) - SHOWN} more lines" if len(lines) > SHOWN else ""
    return "\n".join(lines[:SHOWN]) + more


class Lint:
    """One session's lint; a linter that breaks the same way twice is skipped, so a broken tool never traps it."""

    def __init__(self, log: Callable[..., None]) -> None:
        """Bind the step's activity log."""
        self.log = log
        self.broken: dict[tuple[str, PurePosixPath], str] = {}  # each linter's last breakage in this session
        self.skipped: dict[tuple[str, PurePosixPath], str] = {}  # linters that broke the same way twice
        self.refused = 0

    def check(self, root: Path, changed: Sequence[str]) -> list[str]:
        """Lint the changed files that still exist; return one submit error per failing linter."""
        errors = self._check(root, changed)
        if errors and self.refused >= REFUSALS:
            self.log(event="lint-unresolved", errors=[e.split("\n", 1)[0] for e in errors])
            return []
        self.refused += bool(errors)
        return errors

    def _check(self, root: Path, changed: Sequence[str]) -> list[str]:
        """Lint the changed files that still exist; return one submit error per failing linter."""
        linters, skipped = runner.plan(root, [f for f in dict.fromkeys(changed) if (root / f).is_file()])
        errors, ran, end = [], [], monotonic() + BUDGET
        for linter in linters:
            if why := self._skip(linter, end):
                skipped.append(why)
                continue
            out = runner.run(root, linter, min(TIMEOUT, end - monotonic()))
            ran.append({"tool": linter.name, "files": list(linter.files), "state": out.state})
            errors += self._error(linter, out)
        if ran or skipped:
            self.log(event="lint", ran=ran, skipped=skipped, passed=not errors)
        return errors

    def _skip(self, linter: runner.Linter, end: float) -> str:
        if (reason := self.skipped.get((linter.name, linter.home))) is not None:
            return f"{linter.name}: skipped for this session, it broke twice ({reason})"
        if monotonic() >= end:
            return f"{linter.name}: not run, the {BUDGET} s lint budget for this submit is spent"
        return ""

    def _error(self, linter: runner.Linter, out: runner.Outcome) -> list[str]:
        where, shown = runner.few(linter.files), _shown(out.output)
        if out.state == "passed":
            return []
        if out.state == "failed":
            return [f"lint: {linter.name} found problems in {where} - fix them, commit, then submit again:\n{shown}"]
        if self.broken.get(key := (linter.name, linter.home)) == out.reason:
            self.skipped[key] = out.reason
            self.log(event="lint-skipped", tool=linter.name, reason=out.reason)
            return []
        self.broken[key] = out.reason
        advice = "if your change caused it, fix it and submit again; if the tool is broken, submit again and Delivery"
        return [f"lint: {linter.name} could not run ({out.reason}) on {where} - {advice} skips it:\n{shown}"]
