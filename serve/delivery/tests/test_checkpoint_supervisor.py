from __future__ import annotations

from threading import Event

from owlbear_delivery.checkpoint_supervisor import DeliveryCheckpointSupervisor


class _Application:
    def __init__(self) -> None:
        self.calls = 0
        self.started = Event()
        self.release = Event()

    def reconcile_pending_checkpoints(self, *, limit: int) -> tuple[object, ...]:
        assert limit == 1
        self.calls += 1
        self.started.set()
        self.release.wait(2)
        return ()


def test_supervisor_retries_without_leaking_provider_failures() -> None:
    application = _Application()
    supervisor = DeliveryCheckpointSupervisor(application, interval_seconds=0.01, limit=1)
    supervisor.start()
    assert application.started.wait(1)
    assert supervisor.running
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
