from __future__ import annotations

from threading import Event

from owlbear_delivery.checkpoint_supervisor import DeliveryCheckpointSupervisor


class _Application:
    def __init__(self, *, fail_first: bool = False) -> None:
        self.calls = 0
        self.fail_first = fail_first
        self.started = Event()
        self.release = Event()

    def reconcile_pending_checkpoints(self, *, limit: int) -> tuple[object, ...]:
        assert limit == 1
        self.calls += 1
        self.started.set()
        if self.fail_first and self.calls == 1:
            failure = "transient checkpoint failure"
            raise RuntimeError(failure)
        self.release.wait(2)
        return ()


def test_supervisor_retries_without_leaking_provider_failures() -> None:
    application = _Application(fail_first=True)
    supervisor = DeliveryCheckpointSupervisor(application, interval_seconds=0.01, limit=1)
    supervisor.start()
    assert application.started.wait(1)
    assert supervisor.running
    application.release.set()
    supervisor.stop(timeout_seconds=1)
    assert application.calls >= 1
    assert not supervisor.running


def test_supervisor_keeps_running_after_reconciliation_exception() -> None:
    application = _Application(fail_first=True)
    supervisor = DeliveryCheckpointSupervisor(application, interval_seconds=0.01, limit=1)
    supervisor.start()

    assert application.started.wait(1)
    application.release.set()
    supervisor.stop(timeout_seconds=1)

    assert application.calls >= 1
    assert not supervisor.running


def test_supervisor_start_and_stop_are_idempotent() -> None:
    application = _Application()
    application.release.set()
    supervisor = DeliveryCheckpointSupervisor(application, interval_seconds=0.01)
    supervisor.start()
    supervisor.start()
    supervisor.stop(timeout_seconds=1)
    supervisor.stop(timeout_seconds=1)
    assert not supervisor.running


class _AcceptanceApplication:
    def __init__(self) -> None:
        self.checkpoints = 0
        self.acceptance = 0
        self.ticked = Event()

    def reconcile_pending_checkpoints(self, *, limit: int) -> tuple[object, ...]:
        assert limit == 1
        self.checkpoints += 1
        if self.checkpoints >= 5:
            self.ticked.set()
        return ()

    def reconcile_awaiting_acceptance(self, *, limit: int) -> tuple[object, ...]:
        assert limit == 1
        self.acceptance += 1
        failure = "provider unavailable"
        raise RuntimeError(failure)


def test_supervisor_observes_acceptance_on_its_own_cadence_despite_failures() -> None:
    application = _AcceptanceApplication()
    supervisor = DeliveryCheckpointSupervisor(
        application, interval_seconds=0.01, acceptance_interval_seconds=60, limit=1
    )
    supervisor.start()
    assert application.ticked.wait(1)
    supervisor.stop(timeout_seconds=1)

    assert application.checkpoints >= 5
    assert application.acceptance == 1
