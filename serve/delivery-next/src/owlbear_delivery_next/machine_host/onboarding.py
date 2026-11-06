"""Add project on this machine (item 15): its probe, preflight and jobs, and what the Projects page lists of them."""

from __future__ import annotations

import threading
from pathlib import Path
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
        try:
            method = onboarding_probe.resolved(found.get("repository", "")).prefs.merge_method
        except (StoreError, data_repo.DataRepoError) as exc:
            method, found["method_error"] = None, f"the merge method setting could not be read: {failure(exc)}"
        found["resolved_method"] = method.value if method else None
        with self.lock:
            self._load()
            job = self.jobs.get(onboarding_job.job_id(found["folder"], found.get("repository", "")))
            if job and not job.receipt.get("ended"):  # only an unfinished run resumes; a local-only one publishes
                found["job"] = job.info()
        return found

    def start(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Run the approved plan in place of every earlier run for its folder, refused while one of them runs.

        The plan comes from a probe made since, so its stages are what is left now and its choices the owner's latest.
        An earlier run ends there: a local-only one as published when this one goes to GitHub, any other as replaced,
        so a folder has one run the Projects page shows.
        """
        if why := self._why():
            raise OnboardingError(503, why)
        if unknown := [s for s in plan.get("stages", []) if s not in STAGES]:
            raise OnboardingError(422, f"unknown stages: {', '.join(unknown)}")
        receipt = onboarding_job.new_receipt(plan)
        with self.lock:
            self._load()
            earlier = [j for j in self.jobs.values() if j.plan["folder"] == plan["folder"]]
            if any(j.running() for j in earlier):
                raise OnboardingError(409, f"the run for {plan['folder']} is running: wait for it, then check again")
            job = self.jobs[receipt["id"]] = self._job(receipt)
            job.save()
            for old in [j for j in earlier if j.id != job.id and j.receipt.get("ended") in {"", "local"}]:
                local = old.receipt.get("ended") == "local"
                old.receipt["ended"] = "published" if local and plan.get("github") else "replaced"
                old.save()
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
        job = self._current(ident)
        if job.waiting is None or job.waiting[0] != kind:
            raise OnboardingError(409, f"the run waits for {job.waiting[0] if job.waiting else 'nothing'}, not {kind}")
        job.go((kind, value))
        return job.info()

    def resume(self, ident: str) -> dict[str, Any]:
        """Resume or Retry: the stages not done, from the first."""
        if why := self._why():
            raise OnboardingError(503, why)
        job = self._current(ident)
        job.go()
        return job.info()

    def _current(self, ident: str) -> Job:
        """The job *ident*, unless a newer run for its folder replaced it: a dialog still open on it can't revive it."""
        job = self.get(ident)
        if (ended := job.receipt.get("ended")) in {"replaced", "published"}:
            raise OnboardingError(
                409, f"this run was {ended} by a newer one for {job.plan['folder']}: close and look again"
            )
        return job

    def listed(self) -> list[dict[str, Any]]:
        """The runs the Projects page shows, unfinished or local only, each with the project registered at its folder.

        A registered project's run shows on that project's row; the others are listed apart.
        """
        with self.lock:
            self._load()
            jobs = list(self.jobs.values())
        out = [j.info() | {"project": onboarding_probe.registered_id(Path(j.plan["folder"]))} for j in jobs
               if j.receipt.get("ended") in {"", "local"}]  # fmt: skip
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
