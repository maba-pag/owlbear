"""The Updates page's PDS update (#777): one host job at a time on this machine, its stages and its last run.

It shares the Impeccable update's job (``pack_job``): its record, its machine lock and its admission of pull requests,
with PDS's own record, branches and stages. Its stages: notice, candidate and diff here, then the audit, the updater,
the browser tests and the challenger's rounds (``run``), and the way into ``main`` (``publish``). Until the merge
nothing in ``main`` changes, and the running checkout never does.
"""

from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.round_records import RoundLoop
from owlbear_delivery_next.github.gh import GhProvider
from owlbear_delivery_next.impeccable import pack_files, pack_git
from owlbear_delivery_next.impeccable_runs import pack_admission, pack_job, pack_progress
from owlbear_delivery_next.pds_runs import browser, diff, pin, publish, repair, run
from owlbear_delivery_next.pds_runs.context import FOLDERS, Context
from owlbear_delivery_next.state_store import pds_run_record
from owlbear_delivery_next.workflow_steps import sessions

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.github.provider import Provider
    from owlbear_delivery_next.runtimes.sdk_adapter import Session
    from owlbear_delivery_next.runtimes.session_result import Run
    from owlbear_delivery_next.state_store.store import Store

STAGES = (
    ("notice", "Notice: newer release on npm"),
    ("candidate", "Candidate: pin, vendored tree and served files"),
    ("diff", "Diff: changelog and deprecations"),
    ("audit", "Deprecation audit of the pages"),
    ("update", "Updater: the pages against the release"),
    ("browser", "Browser tests"),
    ("challenger", "Challenger on the release and the pages"),
    ("commit", "Commit: one commit on a PDS branch"),
    ("push", "Push the branch"),
    ("pull-request", "Pull request to main"),
    ("merge", "CI and merge"),
)
PDS = pack_admission.Kind(lambda root: pds_run_record.observed(root), "pds/", "PDS")  # noqa: PLW0108 - read late


@dataclass
class Live:
    """What a PDS update reaches outside: npm, the browser tests, model sessions, git and GitHub. Tests replace each."""

    package: Path = field(default_factory=pin.package)
    fetch: Callable[[str, float], bytes] = pack_files.fetch
    browser: Callable[[Path, tuple[str, ...]], browser.Result] = browser.run
    session: Callable[[Store, Session], Run] = sessions.run
    git: pack_git.Git = pack_git.git
    github: Callable[[Path], Provider] = GhProvider
    sleep: Callable[[float], None] = time.sleep
    poll: float = 30.0  # seconds between looks at the pull request's checks
    ci_wait: float = 3600.0  # seconds CI may take at one head before the owner is asked


class Job(pack_job.Job):
    """The project's PDS update: start one, answer it, read its state."""

    FILE, RUNS, STAGES, KIND = pds_run_record.FILE, pds_run_record.RUNS, STAGES, "pds"
    CONTEXT = Context
    ADMISSION = PDS
    REPAIR = repair.PDS
    ACTIONS = pack_progress.PDS_ACTIONS
    HOLDER = " (PDS update)"
    BUSY = "an update runs for {who}; one update runs at a time on this machine"

    def __init__(self, store: Store, live: Live | None = None) -> None:
        """Read the last run, as an Impeccable update's job does, with PDS's own reach outside."""
        super().__init__(store, live or Live())

    def _stages(self) -> str | None:
        version = self.do("notice", lambda: run.notice(self), op="pds-notice")
        with self.lock:
            self.state["release"] = version  # an ended run's record drops its context; Updates still reads this
        ctx, release, before = self.do(
            "candidate", lambda: run.prepare(self, version), lambda out: f"PDS {out[0].old} to {version}",
            op="pds-candidate",
        )  # fmt: skip
        ctx.diff = self.do(
            "diff", lambda: diff.evidence(before, release.tree, ctx.old, version), lambda d: f"{len(d)} characters",
            op="pds-diff",
        )  # fmt: skip
        return run.begin(self, ctx)

    def _resume(self) -> str | None:
        with self.lock:
            ctx = Context.model_validate(self.state["context"])
            lp = RoundLoop.model_validate(self.state["loop"])
        checking = ctx.repair.phase == "checking"  # an agent's repair of the pages, checked before it is pushed
        if ctx.publication and ctx.publication.commit and not checking:  # GitHub first: the base may have moved on
            return publish.republish(self, ctx, lp)
        run.unchanged(self, ctx)
        return run.advance(self, ctx, lp)

    def _decided(  # noqa: PLR0913 - the open questions, the answer, and the run it changes
        self,
        questions: list[dict[str, Any]],
        q: dict[str, Any],
        option: str,
        *,
        note: str,
        ctx: Context,
        lp: RoundLoop,
    ) -> list[dict[str, Any]]:
        return run.decided(questions, q, option, note=note, ctx=ctx, lp=lp)

    def _removable(self, workspace: Path) -> bool:
        """A workspace goes unless the ledger keeps it or a session's folder in it."""
        if self.maintenance is None:
            return True
        kept = [workspace, *(workspace / f for f in FOLDERS)]
        return not any(self.maintenance.retained(str(p)) for p in kept)

    def _finish(self, state: str, reason: str, *, keep: bool = False) -> None:
        super()._finish(state, reason, keep=keep)
        if not self.workspace.exists():  # the records of its worktrees go with it
            with contextlib.suppress(pack_files.PackError, OSError):
                self.live.git(self.live.package.resolve(), ["worktree", "prune"])
