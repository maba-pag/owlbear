"""One step's result tools, shared by every runtime: validate each call and accept the first valid ending."""

from __future__ import annotations

import subprocess
import threading
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next import tools

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.sdk_adapter import Session
    from owlbear_delivery_next.session_result import Ending, Run

ENDED = "The step has already ended. Stop now."
ACCEPTED = "Accepted. Your step has ended: stop now and start nothing else."


class Gate:
    """The step's result: the first accepted call or ending wins; later calls never change it (T3-T5)."""

    def __init__(self, cfg: Session, run: Run, log: Callable[..., None], ended: Callable[[], None]) -> None:
        """Bind the step's bounds, its run record, its activity log and the wake-up for its waiter."""
        self.cfg, self.run, self.log, self.ended = cfg, run, log, ended
        self.done = False
        self._lock = threading.Lock()

    def finish(self, ending: Ending, payload: tools.Args | None = None, detail: str = "") -> bool:
        """End the step once and close the gate; the first ending is kept. Return whether it had already ended."""
        with self._lock:
            was = self.done
            self._finish(ending, payload, detail)
        self.ended()
        return was

    def _finish(self, ending: Ending, payload: tools.Args | None, detail: str) -> None:
        if not self.done:
            self.done, self.run.ending, self.run.payload, self.run.detail = True, ending, payload, detail

    def revoke(self, detail: str) -> None:
        """End the step as an error even after an accepted result: a turn on another model voids it (TD-32)."""
        with self._lock:
            self.done = True
            self.run.ending, self.run.payload, self.run.head, self.run.detail = "error", None, None, detail[:300]
        self.ended()

    @property
    def specs(self) -> tuple[tools.Spec, ...]:
        """The step's tools: its submit tool, ``ask_question``, ``report_wrong_premise`` and ``report_missing_tool``."""
        return self.cfg.submit, tools.ASK, tools.PREMISE, tools.MISSING

    def call(self, spec: tools.Spec, arguments: Any) -> tuple[str, bool]:  # noqa: ANN401 - the agent's JSON arguments
        """Validate one call; return the text the agent reads and whether it was accepted."""
        with self._lock:
            text, ok = self._call(spec, arguments)
        if self.done:
            self.ended()
        return text, ok

    def _call(self, spec: tools.Spec, arguments: Any) -> tuple[str, bool]:  # noqa: ANN401 - the agent's JSON arguments
        if self.done:  # before any check: a late call never touches the accepted head
            self.log(event="tool", tool=spec.name, accepted=False, errors=["the step has already ended"])
            return ENDED, False
        args, errors = tools.parse(spec.model, arguments)
        if args is not None:
            errors = tools.check_question(args) if isinstance(args, tools.AskQuestion) else []
            errors += self._check_result(args) if spec is self.cfg.submit else []
        read = list(args.covered_paths) if isinstance(args, tools.ReviewResult) else []  # evidence, not coverage
        self.log(event="tool", tool=spec.name, accepted=not errors, errors=errors, **({"read": read} if read else {}))
        if errors:
            self.run.invalid += 1
            if self.run.invalid >= tools.INVALID_LIMIT:
                self._finish("invalid", None, "; ".join(errors)[:300])
            lines = "\n".join(f"- {e}" for e in errors)
            return f"Rejected. Fix each field, then call again:\n{lines}", False
        self._finish(spec.ending, args, "")
        return ACCEPTED, True

    def _check_result(self, args: tools.Args) -> list[str]:
        try:
            tree = self.cfg.observe()
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            return [f"changes: the worktree could not be read ({type(exc).__name__}); try again"]
        cfg = self.cfg
        errors = tools.check_result(
            args, tree, cfg.checks, cfg.policy.root, cfg.scope, cfg.item, visual=bool(cfg.attachments)
        )
        self.run.head = None if errors else tree.head
        return errors
