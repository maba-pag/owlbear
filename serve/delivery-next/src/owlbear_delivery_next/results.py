"""One step's result tools, shared by every runtime: validate each call and accept the first valid ending."""

from __future__ import annotations

import subprocess
import threading
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next import design_tools, disputes, lint, preparation, tools

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.sdk_adapter import Session
    from owlbear_delivery_next.session_result import Ending, Run

    Checked = tuple[tools.Args | None, list[str], tools.Worktree | None]  # parsed call, its errors, the tree read

ENDED = "The step has already ended. Stop now."
ACCEPTED = "Accepted. Your step has ended: stop now and start nothing else."
# The window's autopilot nudges a turn that ends without task_complete, on a model Delivery did not choose (live).
ACCEPTED_WINDOW = "Accepted. Your step has ended: call `task_complete` once now, then stop and start nothing else."


class Gate:
    """The step's result: the first accepted call or ending wins; later calls never change it (T3-T5)."""

    def __init__(self, cfg: Session, run: Run, log: Callable[..., None], ended: Callable[[], None]) -> None:
        """Bind the step's bounds, its run record, its activity log and the wake-up for its waiter."""
        self.cfg, self.run, self.log, self.ended = cfg, run, log, ended
        self.done = False
        self.lint = lint.Lint(log)
        self._lock = threading.Lock()
        self._linting = threading.Lock()

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

    def wrong_model(self, detail: str) -> None:
        """A turn or call on another model: whatever was submitted is void and the step reruns once (TD-94)."""
        self.run.model_check = "mismatch"
        self.revoke(f"wrong model: {detail}")

    @property
    def specs(self) -> tuple[tools.Spec, ...]:
        """The step's tools: its submit tool, a first look if it has one, its helpers, a question unless a judge's."""
        first = (self.cfg.first_look,) if self.cfg.first_look else ()
        helpers = tuple(spec for spec, _ in self.cfg.helpers)
        ask = (tools.ASK,) if tools.asks(self.cfg.role, judging=self.cfg.judging) else ()
        return self.cfg.submit, *first, *helpers, *ask, tools.PREMISE, tools.MISSING

    def call(self, spec: tools.Spec, arguments: Any) -> tuple[str, bool]:  # noqa: ANN401 - the agent's JSON arguments
        """Validate one call; return the text the agent reads and whether it was accepted."""
        if (helper := dict(self.cfg.helpers).get(spec)) is not None:
            return self._help(spec, helper, arguments)
        checked = self._checked(spec, arguments)
        with self._lock:  # an ending that came while the result was linted wins
            text, ok = self._late(spec) if checked is None or self.done else self._settle(spec, *checked)
        if self.done:
            self.ended()
        return text, ok

    def _help(
        self,
        spec: tools.Spec,
        helper: Callable[[tools.Args], str],
        arguments: Any,  # noqa: ANN401 - the agent's JSON arguments
    ) -> tuple[str, bool]:
        """A helper answers and the step goes on; its rejected calls never count toward ending the step."""
        if self.done:
            return ENDED, False
        args, errors = tools.parse(spec.model, arguments)
        self.log(event="tool", tool=spec.name, accepted=not errors, errors=errors)
        if args is None:
            return "Rejected. Fix each field, then call again:\n" + "\n".join(f"- {e}" for e in errors), False
        return helper(args), True

    def _checked(self, spec: tools.Spec, arguments: Any) -> Checked | None:  # noqa: ANN401 - the agent's JSON
        """Validate under the lock, then lint outside it, so no ending or revocation waits on a linter (TD-87)."""
        with self._lock:
            if self.done:  # before any check: a late call never touches the accepted head
                return None
            args, errors, tree = self._check(spec, arguments)
        if tree is not None and not errors and isinstance(args, tools.BuildResult):
            with self._linting:
                errors = self.lint.check(self.cfg.worktree, tree.changed)
        return args, errors, tree

    def _check(self, spec: tools.Spec, arguments: Any) -> Checked:  # noqa: ANN401 - the agent's JSON arguments
        args, errors = tools.parse(spec.model, arguments)
        if args is None:
            return None, errors, None
        errors, tree = tools.check_question(args) if isinstance(args, tools.AskQuestion) else [], None
        if spec is self.cfg.submit or spec is self.cfg.first_look:
            order = self._order(spec)
            more, tree = (order, None) if order else self._check_result(args)
            errors += more
        return args, errors, tree

    def _late(self, spec: tools.Spec) -> tuple[str, bool]:
        self.log(event="tool", tool=spec.name, accepted=False, errors=["the step has already ended"])
        return ENDED, False

    def _settle(
        self, spec: tools.Spec, args: tools.Args | None, errors: list[str], tree: tools.Worktree | None
    ) -> tuple[str, bool]:
        if tree is not None:
            self.run.head = None if errors else tree.head
        read = list(args.covered_paths) if isinstance(args, tools.ReviewResult) else []  # evidence, not coverage
        self.log(event="tool", tool=spec.name, accepted=not errors, errors=errors, **({"read": read} if read else {}))
        if errors:
            self.run.invalid += not all(e.startswith("lint: ") for e in errors)  # lint has its own limit (TD-87)
            if self.run.invalid >= tools.INVALID_LIMIT:
                self._finish("invalid", None, "; ".join(errors)[:300])
            lines = "\n".join(f"- {e}" for e in errors)
            return f"Rejected. Fix each field, then call again:\n{lines}", False
        if spec is self.cfg.first_look:  # recorded, and the turn goes on with what it releases
            self.run.first = args
            return f"Recorded. {self.cfg.reveal}".strip(), True
        self._finish(spec.ending, args, "")
        return ACCEPTED_WINDOW if self.run.runtime == "window" else ACCEPTED, True

    def _order(self, spec: tools.Spec) -> list[str]:
        """A first look comes once, and before the final result."""
        first, submit = self.cfg.first_look, self.cfg.submit
        if first is None:
            return []
        if spec is first and self.run.first is not None:
            return [f"{first.name}: already recorded - submit your final verdict with {submit.name}"]
        if spec is submit and self.run.first is None:
            return [f"{submit.name}: first submit your own verdict with {first.name}"]
        return []

    def _check_result(self, args: tools.Args) -> tuple[list[str], tools.Worktree | None]:
        try:
            tree = self.cfg.observe()
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            return [f"changes: the worktree could not be read ({type(exc).__name__}); try again"], None
        cfg = self.cfg
        if isinstance(args, design_tools.DesignLook):
            return design_tools.check(args, tree), tree
        if isinstance(args, tools.CheckRecipe):  # TD-96, TD-107: a declared, permitted option and setup edits only
            return preparation.check(args, tree, cfg.policy.root, cfg.preparing or preparation.Preparing()), tree
        errors = tools.check_result(
            args, tree, cfg.checks, cfg.policy.root, cfg.scope, cfg.item, visual=bool(cfg.attachments)
        )
        return errors + disputes.check(args, tree, cfg.rejectable, cfg.rechecks), tree
