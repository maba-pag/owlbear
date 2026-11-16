"""Fixture-only tool transport: no SDK connection, model request or real subagent."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes.results import Gate
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps.disposable import Copy, _refs, _shared

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from owlbear_delivery_next.runtimes.sdk_adapter import Session


class FixtureStore(Store):
    """An unregistered, unshared store with explicit in-memory fixture settings."""

    def settings(self) -> config.Settings:
        """Never resolve the machine's installed settings or create a memory folder."""
        agent = config.Agent(model="fixture-scripted", effort="low", context="default", minutes=1, subagents=True)
        return config.resolve(
            None,
            config.Layer(
                agents={"project-auditor": agent, "audit-verifier": agent},
                load_user_instructions=False,
                load_user_skills=False,
                load_user_memory=False,
                guard_level="standard",
            ),
        )


@contextmanager
def opened(repo: Path, root: Path, commit: str) -> Iterator[Copy]:
    """Use only the builder clone's objects and remove only this detached worktree."""
    at = root / "repo"
    worktree.git(repo, "worktree", "add", "--quiet", "--detach", str(at), commit)
    try:
        yield Copy(repo, at, _refs(repo), _shared(repo))
    finally:
        worktree.git(repo, "worktree", "remove", "--force", str(at))


class Script:
    """Recorded submissions are separate from, and have no access to, replay expectations."""

    def __init__(self, path: Path) -> None:
        self.recorded = json.loads(path.read_text(encoding="utf-8"))
        self.refusals: list[str] = []

    def run(self, cfg: Session, stage: str) -> Run:
        """Deliver recorded tool arguments to the real Gate; only the last submit may settle."""
        if cfg.policy.write or cfg.policy.root != cfg.worktree or not (cfg.worktree / "repo" / ".git").is_file():
            msg = "fixture transport requires a read-only session above the audited repository"
            raise ValueError(msg)
        recorded = self.recorded[stage]
        done = Run(
            session_id=cfg.session_id,
            model_check="verified",
            termination=Termination(confirmed=True),
            detail="Fixture only: termination and model identity are simulated, not provider-verified.",
            usage={"credits": 0, "fixture": True},
            subagents=recorded.get("subagents", []),
        )
        gate = Gate(cfg, done, lambda **_event: None, lambda: None)
        calls = recorded["calls"]
        if not calls:
            msg = f"{stage}: fixture has no recorded submission"
            raise ValueError(msg)
        for index, arguments in enumerate(calls):
            text, accepted = gate.call(cfg.submit, arguments)
            final = index == len(calls) - 1
            if accepted != final or (not final and gate.done):
                msg = f"{stage} submission {index + 1}: unexpected Gate outcome: {text}"
                raise ValueError(msg)
            if not accepted:
                self.refusals.append(text)
        return done


def evidence(done: Run) -> dict[str, Any]:
    """Keep simulated identity and use visibly separate from live runtime evidence."""
    return {
        "session": done.session_id,
        "model": "fixture-scripted (simulated identity)",
        "termination": "simulated confirmed; no provider process started",
        "credits": 0,
        "subagents": done.subagents,
        "tool_calls": done.tool_calls,
    }
