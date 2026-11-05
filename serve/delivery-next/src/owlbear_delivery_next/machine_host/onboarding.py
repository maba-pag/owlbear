"""Add project on this machine (item 15): its probe, preflight and jobs, and what the Projects page lists of them."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.local_system import data_repo, local_home
from owlbear_delivery_next.machine_host import onboarding_end, onboarding_job, onboarding_probe
from owlbear_delivery_next.machine_host.onboarding_job import Job
from owlbear_delivery_next.machine_host.onboarding_stages import STAGES
from owlbear_delivery_next.state_store.layers import layered
from owlbear_delivery_next.state_store.store import MACHINE_SETTINGS, StoreError

if TYPE_CHECKING:
    from owlbear_delivery_next.machine_host.machine import Machine


class OnboardingError(Exception):
    """A request the jobs refuse; ``status`` is the HTTP answer."""

    def __init__(self, status: int, text: str) -> None:
        """Keep the answer's status and words."""
        super().__init__(text)
        self.status, self.text = status, text


class Onboarding:
    """The machine's Add project jobs, one per destination, read back from their receipts after a restart."""

    def __init__(self, machine: Machine) -> None:
        """No job is read until the first request needs them."""
        self.machine, self.lock = machine, threading.Lock()
        self.jobs: dict[str, Job] = {}
        self.unreadable: dict[str, str] = {}
        self.loaded = False

    def _why(self) -> str:
        """Why no stage starts now: an update's fence, or a stop."""
        m = self.machine
        return m.updating or ("OwlBear is stopping" if m.stopping.is_set() else "")

    def _job(self, receipt: dict[str, Any]) -> Job:
        stages = [(s["name"], STAGES[s["name"]]) for s in receipt["stages"]]
        return Job(receipt, stages, self.machine.say, self._why, context={"machine": self.machine})

    def _load(self) -> None:
        if self.loaded:
            return
        for receipt in onboarding_job.kept():
            if "unreadable" in receipt:
                self.unreadable[receipt["id"]] = receipt["unreadable"]
            else:
                self.jobs.setdefault(receipt["id"], self._job(receipt))
        self.loaded = True

    def probe(self, start: dict[str, Any]) -> dict[str, Any]:
        """What exists for the owner's start, with the Global labels and the merge methods allowed."""
        try:
            found = onboarding_probe.probe(start)
        except ValueError as exc:
            raise OnboardingError(422, str(exc)) from exc
        found["allowed"] = onboarding_end.merge_allowed(found)
        found["labels"], found["labels_error"] = _labels()
        with self.lock:
            self._load()
            job = self.jobs.get(onboarding_job.job_id(found["folder"], found.get("repository", "")))
            if job and job.receipt.get("ended") != "done":
                found["job"] = job.info()
        return found

    def preflight(self, plan: dict[str, Any]) -> list[str]:
        """What must hold before anything is created; each failure whole."""
        return onboarding_probe.preflight(plan)

    def start(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Run the approved plan; the same destination's unfinished job goes on instead of a second one."""
        if why := self._why():
            raise OnboardingError(503, why)
        if unknown := [s for s in plan.get("stages", []) if s not in STAGES]:
            raise OnboardingError(422, f"unknown stages: {', '.join(unknown)}")
        receipt = onboarding_job.new_receipt(plan, list(plan["stages"]))
        with self.lock:
            self._load()
            job = self.jobs.get(receipt["id"])
            if job is None or job.receipt.get("ended"):
                job = self.jobs[receipt["id"]] = self._job(receipt)
                job.save()
        job.go()
        return job.info()

    def get(self, ident: str) -> Job:
        """The job *ident*."""
        with self.lock:
            self._load()
            if (job := self.jobs.get(ident)) is None:
                raise OnboardingError(404, self.unreadable.get(ident) or f"no Add project run {ident}")
            return job

    def answer(self, ident: str, kind: str, value: Any) -> dict[str, Any]:  # noqa: ANN401 - the dialog's answer
        """The owner's answer to what the job waits for; it goes on from there."""
        job = self.get(ident)
        if job.waiting is None or job.waiting[0] != kind:
            raise OnboardingError(409, f"the run waits for {job.waiting[0] if job.waiting else 'nothing'}, not {kind}")
        job.go((kind, value))
        return job.info()

    def resume(self, ident: str) -> dict[str, Any]:
        """Resume or Retry: the stages not done, from the first."""
        if why := self._why():
            raise OnboardingError(503, why)
        job = self.get(ident)
        job.go()
        return job.info()

    def listed(self) -> list[dict[str, Any]]:
        """The runs the Projects page shows: unfinished ones with Resume, local-only ones with Publish."""
        with self.lock:
            self._load()
            jobs = list(self.jobs.values())
        out = [j.info() for j in jobs if j.receipt.get("ended") != "done"]
        return out + [{"id": i, "unreadable": why} for i, why in self.unreadable.items()]

    def working(self) -> list[str]:
        """What a stop or an update waits for: each running stage."""
        out = []
        for job in [j for j in list(self.jobs.values()) if j.running()]:
            stage = next((s["name"] for s in job.receipt["stages"] if s["state"] == "running"), "")
            out.append(f"Add project {job.plan.get('name', '')}: {stage}")
        return out


def _labels() -> tuple[list[str], str]:
    """Global's labels (C-16), which a new project inherits when its tick is on, and why they could not be read."""
    try:
        shared = data_repo.locate()
        glob = shared.global_path if shared else None
        return list(layered(glob, None, local_home.root() / MACHINE_SETTINGS).pr_labels or []), ""
    except (StoreError, data_repo.DataRepoError) as exc:
        return [], f"Global's labels could not be read: {failure(exc)}"
