"""A design pack update's steps as it records them (``pack_job``): each stage's work as an invocation, and its log.

Each run of a stage is a new invocation of its operation (``pack_progress``): its result, words and identity are kept
in the run's state with the stage's latest result, and logged. A failure ends the run with the stage named.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.pack_runs import pack_progress
from owlbear_delivery_next.pack_runs.pack_run import Stopped
from owlbear_delivery_next.pack_runs.pack_state import LOG
from owlbear_delivery_next.pack_runs.pack_state import now as _now

if TYPE_CHECKING:
    import threading
    from collections.abc import Callable


class Steps:
    """The job's record of its steps; the job keeps the state and saves it."""

    lock: threading.Lock
    state: dict[str, Any]

    def _save(self) -> None:
        raise NotImplementedError

    def log(self, line: str) -> None:
        """One line of the run's log, kept with its state."""
        with self.lock:
            self._log(line)
            self._save()

    def _log(self, line: str) -> None:
        self.state["log"] = [*self.state["log"], f"{_now()} {line}"][-LOG:]

    def stage(self, name: str, result: str, detail: str = "") -> None:
        """One stage's latest result, shown with a legacy record's stages and logged; invocations keep each run."""
        self._step(None, name, result, detail)

    def _step(self, inv: dict[str, Any] | None, name: str, result: str, detail: str = "", identity: str = "") -> None:
        """One stage's result in its slot and, when the run keeps them, in its invocation *inv*; saved, then logged."""
        with self.lock:
            if inv is not None:
                pack_progress.closed(self.state["invocations"], inv, result, detail, identity)
            stage = next(s for s in self.state["stages"] if s["name"] == name)
            stage["result"], stage["detail"] = result, detail[:4000]
            self.state["stage"] = name if result == "running" else self.state["stage"]
            self._save()
        self.log(f"{name}: {result}{f': {detail.splitlines()[0][:300]}' if detail else ''}")

    def _begin(self, name: str, op: str, round_: int | None, identity: str) -> dict[str, Any] | None:
        """A new invocation of *op*, running in stage *name*; None for a legacy run, which invents no history."""
        with self.lock:
            invocations = self.state.get("invocations")
            inv = None
            if invocations is not None:
                inv = pack_progress.opened(invocations, name, op, round_=round_, identity=identity)
            stage = next(s for s in self.state["stages"] if s["name"] == name)
            stage["result"], stage["detail"], self.state["stage"] = "running", "", name
            self._save()
        self.log(f"{name}: running")
        return inv

    def note(self, name: str, op: str, result: str, detail: str, identity: str = "") -> None:
        """An invocation that ran nothing, such as a replay reused for an unchanged identity; logged."""
        with self.lock:
            invocations = self.state.get("invocations")
            if invocations is not None:
                inv = pack_progress.opened(invocations, name, op, identity=identity, result=result)
                inv["detail"] = detail[:4000]
                self._save()
        self.log(f"{name}: {pack_progress.words(op, result)}")

    def identified(self, identity: str) -> None:
        """The candidate the last invocation made, once known: evidence about an earlier candidate is stale now."""
        with self.lock:
            invocations = self.state.get("invocations")
            if invocations:
                pack_progress.identified(invocations, invocations[-1], identity)
                self._save()

    def do[T](  # noqa: PLR0913 - the stage, its work and words, and what the invocation is
        self,
        name: str,
        work: Callable[[], T],
        said: Callable[[T], str] = str,
        hold: type[Exception] | None = None,
        *,
        op: str = "",
        round_: int | None = None,
        identity: str | Callable[[T], str] = "",
        judged: Callable[[T], str] | None = None,
    ) -> T:
        """Run one stage's work as a new invocation of its operation: its result shown, any failure ending the run.

        The operation *op* is the stage *name* by default; a failure names the stage. *judged* says what the work came
        to: "passed" by default, "completed" for a session whose candidate it does not judge, "findings" for a verdict
        with findings. *identity* is the candidate or head it ran on, or reads it from the result. A failure of the
        *hold* kind is raised as it is, for the owner to decide.
        """
        inv = self._begin(name, op or name, round_, identity if isinstance(identity, str) else "")
        try:
            out = work()
        except Stopped as exc:
            self._step(inv, name, "passed" if exc.current else "failed", exc.reason)
            raise
        except Exception as exc:
            if hold is not None and isinstance(exc, hold):
                self._step(inv, name, getattr(exc, "result", "failed"), str(exc))  # held for the owner, or failed
                raise
            reason = f"{name}: {type(exc).__name__}: {exc}"[:2000]  # any failure stops the run, its stage named
            self._step(inv, name, "failed", reason)
            raise Stopped(reason) from exc
        made = identity(out) if callable(identity) else ""
        self._step(inv, name, judged(out) if judged else "passed", said(out), made)
        return out
