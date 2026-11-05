"""Add project's run (item 15): one job per destination, its stages in order, its receipt under ``~/.owlbear``.

Each stage checks the real state before acting, so Retry and Resume never repeat an effect; the receipt records the
approved inputs, the intent before each effect and its result. A stage that needs the owner (a shared folder name, the
profile) waits with its question; a failure is kept whole, with Retry. There is no automated Undo.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.local_system import local_home, storage_io

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


class Waiting(Exception):  # noqa: N818 - not an error: the stage asks the owner and the job waits for his answer
    """A stage that needs the owner's answer; ``kind`` names the question and ``data`` what the dialog shows."""

    def __init__(self, kind: str, data: dict[str, Any]) -> None:
        """Keep the question."""
        super().__init__(kind)
        self.kind, self.data = kind, data


type Stage = Callable[[Job], dict[str, Any] | None]


def job_id(folder: str, repository: str) -> str:
    """One job per destination: the local folder and the GitHub target."""
    return hashlib.sha256(f"{folder}\n{repository.casefold()}".encode()).hexdigest()[:16]


def receipts() -> Path:
    """The folder of the jobs' receipts."""
    return local_home.root() / "onboarding"


@dataclass
class Job:
    """One Add project run: its approved plan, its stages' states and results, and what it waits for."""

    receipt: dict[str, Any]
    stages: list[tuple[str, Stage]]
    say: Callable[[str], object]
    fenced: Callable[[], str]
    answers: dict[str, Any] = field(default_factory=dict)
    waiting: tuple[str, dict[str, Any]] | None = None
    context: dict[str, Any] = field(default_factory=dict)  # what later stages read from earlier ones in this run
    thread: threading.Thread | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def id(self) -> str:
        """The job's id."""
        return self.receipt["id"]

    @property
    def plan(self) -> dict[str, Any]:
        """The approved inputs."""
        return self.receipt["plan"]

    def record(self, name: str) -> dict[str, Any]:
        """The receipt's record of stage *name*."""
        return next(s for s in self.receipt["stages"] if s["name"] == name)

    def result(self, name: str) -> dict[str, Any]:
        """What stage *name* recorded when it was done; nothing for a stage this run doesn't have."""
        found = next((s for s in self.receipt["stages"] if s["name"] == name), None)
        return (found or {}).get("result") or {}

    def intend(self, name: str, what: str) -> None:
        """Record the intent before an effect, so a crash after it is known on Resume."""
        self.record(name)["intent"] = what
        self.save()

    def save(self) -> None:
        """Write the receipt."""
        self.receipt["updated_at"] = datetime.now(UTC).isoformat()
        path = receipts() / f"{self.id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        storage_io.atomic_write(path, json.dumps(self.receipt, indent=2) + "\n")

    def running(self) -> bool:
        """Whether a stage runs now."""
        return self.thread is not None and self.thread.is_alive()

    def go(self, answer: tuple[str, Any] | None = None) -> None:
        """Run the stages that are not done, from the first; with *answer*, the owner's answer to what it waits for."""
        with self.lock:
            if self.running():
                return
            if answer is not None:
                self.answers[answer[0]] = answer[1]
            self.waiting = None
            self.thread = threading.Thread(target=self._run, name=f"onboarding-{self.id}", daemon=True)
            self.thread.start()

    def _run(self) -> None:
        for name, stage in self.stages:
            rec = self.record(name)
            if rec["state"] == "done":
                continue
            if why := self.fenced():
                rec.update(state="held", detail=why)
                self.save()
                return
            rec.update(state="running", detail="")
            self.save()
            try:
                result = stage(self)
            except Waiting as wait:
                self.waiting = (wait.kind, wait.data)
                rec.update(state="waiting", detail=wait.kind)
                self.save()
                return
            except Exception as exc:  # noqa: BLE001 - every failure is shown whole on the stage, with Retry
                rec.update(state="failed", detail=failure(exc))
                self.say(f"Add project {self.plan.get('name', '')}: {name} failed: {failure(exc)}")
                self.save()
                return
            rec.update(state="done", detail="", result=result or {})
            rec.pop("intent", None)
            self.save()
        self.receipt["ended"] = "local" if not self.plan.get("github") else "done"
        self.save()

    def info(self) -> dict[str, Any]:
        """What the dialog and the Projects page show."""
        return {
            "id": self.id,
            "plan": self.plan,
            "stages": [{k: s.get(k) for k in ("name", "state", "detail", "result")} for s in self.receipt["stages"]],
            "running": self.running(),
            "waiting": None if self.waiting is None else {"kind": self.waiting[0], **self.waiting[1]},
            "ended": self.receipt.get("ended", ""),
        }


def new_receipt(plan: dict[str, Any]) -> dict[str, Any]:
    """A receipt for a job not started yet."""
    now = datetime.now(UTC).isoformat()
    ident = job_id(plan["folder"], plan.get("repository", ""))
    stages = [{"name": n, "state": "pending", "detail": "", "result": {}} for n in plan["stages"]]
    return {"id": ident, "plan": plan, "stages": stages, "created_at": now, "updated_at": now, "ended": ""}


def kept() -> list[dict[str, Any]]:
    """Every receipt on disk; one that can't be read is returned as its error, for the Projects page."""
    out = []
    for path in sorted(receipts().glob("*.json")):
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            out.append({"id": path.stem, "unreadable": f"{path}: {failure(exc)}"})
    return out
