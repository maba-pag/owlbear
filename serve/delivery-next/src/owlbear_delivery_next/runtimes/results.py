"""One step's result tools, shared by every runtime: validate each call and accept the first valid ending."""

from __future__ import annotations

import subprocess
import threading
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts import curation_tools, pack_tools, preparation, tool_schema, tools
from owlbear_delivery_next.change_flow import disputes
from owlbear_delivery_next.impeccable import design_tools
from owlbear_delivery_next.local_system import lint
from owlbear_delivery_next.runtimes import amendments

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.runtimes.sdk_adapter import Session
    from owlbear_delivery_next.runtimes.session_result import Ending, Run

    # parsed call, its errors, the tree read and what refused it: invalid arguments, failed checks or the wrong order
    Checked = tuple[tools.Args | None, list[str], tools.Worktree | None, str]

ENDED = "The step has already ended. Stop now."
ACCEPTED = "Accepted. Your step has ended: stop now and start nothing else."


class Gate:
    """The step's result: the first accepted call or ending wins; later calls never change it (T3-T5)."""

    def __init__(self, cfg: Session, run: Run, log: Callable[..., None], ended: Callable[[], None]) -> None:
        """Bind the step's bounds, its run record, its activity log and the wake-up for its waiter."""
        self.cfg, self.run, self.log, self.ended = cfg, run, log, ended
        self.done = False
        self.stopped = False  # a stop or error tears the step down: no call settles, and no lock is taken to say so
        self.expired: Callable[[], bool] | None = None
        self.lint = lint.Lint(log)
        self._refused: set[str] = set()  # the tools whose last call was refused, so their next call is a retry
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

    def _closed(self) -> bool:
        if self.stopped:
            return True
        if not self.done and self.expired is not None and self.expired():
            self._finish("deadline", None, "step deadline")
        return self.done

    def revoke(self, detail: str) -> None:
        """End the step as an error even after an accepted result: a turn on another model voids it (TD-32)."""
        with self._lock:
            self.done = True
            self.run.ending, self.run.payload, self.run.head, self.run.detail = "error", None, None, detail
            self.run.changed = []
            self.run.changed = []
        self.ended()

    def wrong_model(self, detail: str) -> None:
        """A turn or call on another model: whatever was submitted is void and the step reruns once (TD-94)."""
        self.run.model_check = "mismatch"
        self.revoke(f"wrong model: {detail}")

    @property
    def specs(self) -> tuple[tools.Spec, ...]:
        """The step's tools: its submit tool, a first look if it has one, its helpers, a question unless a judge's."""
        if self.cfg.role == tools.PICKER:
            return (self.cfg.submit,)
        first = (self.cfg.first_look,) if self.cfg.first_look else ()
        helpers = tuple(spec for spec, _ in self.cfg.helpers)
        ask = (tools.ASK,) if tools.asks(self.cfg.role, judging=self.cfg.judging) else ()
        return self.cfg.submit, *first, *helpers, *ask, tools.PREMISE, tools.MISSING

    def call(self, spec: tools.Spec, arguments: Any) -> tuple[str, bool]:  # noqa: ANN401 - the agent's JSON arguments
        """Validate one call; return the text the agent reads and whether it was accepted."""
        with self._lock:
            closed = self._closed()
        if closed:
            self.ended()
        if (helper := dict(self.cfg.helpers).get(spec)) is not None:
            return self._help(spec, helper, arguments)
        checked = self._checked(spec, arguments)
        with self._lock:  # an ending that came while the result was linted wins
            text, ok = self._late(spec) if checked is None or self._closed() else self._settle(spec, *checked)
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
            with self._lock:
                self._tally(spec.name, "late")
            return ENDED, False
        args, errors = tool_schema.parse(spec.model, arguments)
        with self._lock:
            closed = self._closed()
            self.log(
                event="tool",
                tool=spec.name,
                accepted=not (closed or errors),
                errors=["the step has already ended"] if closed else errors,
            )
            closed = self._closed()
            self._tally(spec.name, "late" if closed else "rejected" if errors else "", "invalid")  # a schema only
        if closed:
            self.ended()
            return ENDED, False
        if args is None:
            return "Rejected. Fix each field, then call again:\n" + "\n".join(f"- {e}" for e in errors), False
        return helper(args), True

    def _checked(self, spec: tools.Spec, arguments: Any) -> Checked | None:  # noqa: ANN401 - the agent's JSON
        """Validate under the lock, then lint outside it, so no ending or revocation waits on a linter (TD-87)."""
        with self._lock:
            if self._closed():  # before any check: a late call never touches the accepted head
                return None
            args, errors, tree, kind = self._check(spec, arguments)
        if tree is not None and not errors and isinstance(args, tools.BuildResult):
            with self._linting:
                errors = self.lint.check(self.cfg.worktree, tree.changed)
        return args, errors, tree, kind

    def _check(self, spec: tools.Spec, arguments: Any) -> Checked:  # noqa: ANN401 - the agent's JSON arguments
        args, errors = tool_schema.parse(spec.model, arguments)
        if args is None:
            return None, errors, None, "invalid"
        errors, tree = tools.check_question(args) if isinstance(args, tools.AskQuestion) else [], None
        errors += amendments.check(args, self.cfg.amendable)  # a premise's proposed wording (TD-179)
        order: list[str] = []
        if spec is self.cfg.submit or spec is self.cfg.first_look:
            order = self._order(spec)
            more, tree = (order, None) if order else self._check_result(args)
            errors += more
        return args, errors, tree, "order" if order else "checks"  # the wrong moment outweighs other errors

    def _late(self, spec: tools.Spec) -> tuple[str, bool]:
        self.log(event="tool", tool=spec.name, accepted=False, errors=["the step has already ended"])
        self._tally(spec.name, "late")
        return ENDED, False

    def _tally(self, name: str, outcome: str, kind: str = "") -> None:
        """Count one call of *name* in the run: its outcome field, if any, and whether it retries a refusal.

        A ``rejected`` call also counts its *kind* (``invalid``, ``checks`` or ``order``), a part of ``rejected``.
        """
        n = self.run.tool_calls.setdefault(name, {})
        n["calls"] = n.get("calls", 0) + 1
        if name in self._refused:
            n["retries"] = n.get("retries", 0) + 1
        for field in (outcome, kind if outcome == "rejected" else ""):
            if field:
                n[field] = n.get(field, 0) + 1
        if outcome in {"rejected", "lint"}:
            self._refused.add(name)
        else:
            self._refused.discard(name)

    def _settle(
        self, spec: tools.Spec, args: tools.Args | None, errors: list[str], tree: tools.Worktree | None, kind: str
    ) -> tuple[str, bool]:
        read = list(args.covered_paths) if isinstance(args, tools.ReviewResult) else []  # evidence, not coverage
        self.log(event="tool", tool=spec.name, accepted=not errors, errors=errors, **({"read": read} if read else {}))
        if self._closed():
            return self._late(spec)
        if tree is not None:
            self.run.head, self.run.changed = (None, []) if errors else (tree.head, list(tree.changed))
        linted = bool(errors) and all(e.startswith("lint: ") for e in errors)
        self._tally(spec.name, "lint" if linted else "rejected" if errors else "", kind)
        if errors:
            self.run.invalid += not linted  # lint has its own limit (TD-87)
            if self.run.invalid >= tools.INVALID_LIMIT:
                self._finish("invalid", None, "; ".join(errors)[:300])
            lines = "\n".join(f"- {e}" for e in errors)
            return f"Rejected. Fix each field, then call again:\n{lines}", False
        if spec is self.cfg.first_look:  # recorded, and the turn goes on with what it releases
            self.run.first = args
            return f"Recorded. {self.cfg.reveal}".strip(), True
        self._finish(spec.ending, args, "")
        return ACCEPTED, True

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
        if isinstance(args, curation_tools.TestCurationResult):  # TD-339: committed, clean, only tests
            return curation_tools.check(args, tree), tree
        errors = tools.check_result(
            args,
            tree,
            cfg.checks,
            cfg.policy.root,
            cfg.scope,
            cfg.item,
            visual=bool(cfg.attachments),
            packages=cfg.packages,
        )
        found = disputes.check(
            args, tree, cfg.rejectable, cfg.rechecks, settled=cfg.settled, cap=cfg.cap, tasks=cfg.plan_tasks
        )
        if isinstance(args, pack_tools.PackReview):  # TD-194: one judgement per file the updater changed
            found += pack_tools.check(args, cfg.changed)
        return errors + found, tree
