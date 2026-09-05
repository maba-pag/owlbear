"""Background reconciliation for durable Delivery checkpoint obligations."""

from __future__ import annotations

from contextlib import suppress
from threading import Event, Thread
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear_delivery.portfolio_application import PortfolioApplication


class DeliveryCheckpointSupervisor:
    """Retry pending checkpoint publication while a Delivery host is alive."""

    def __init__(
        self,
        application: PortfolioApplication,
        *,
        interval_seconds: float = 5.0,
        limit: int = 8,
    ) -> None:
        if interval_seconds <= 0:
            message = "checkpoint supervisor interval must be positive"
            raise ValueError(message)
        if limit < 1:
            message = "checkpoint supervisor limit must be positive"
            raise ValueError(message)
        self._application = application
        self._interval_seconds = interval_seconds
        self._limit = limit
        self._stop = Event()
        self._thread: Thread | None = None

    @property
    def running(self) -> bool:
        """Return whether the supervisor thread is currently alive."""
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start one idempotent checkpoint reconciliation loop."""
        if self.running:
            return
        self._stop.clear()
        self._thread = Thread(
            target=self._run,
            name="owlbear-delivery-checkpoints",
            daemon=True,
        )
        self._thread.start()

    def stop(self, *, timeout_seconds: float = 10.0) -> None:
        """Request shutdown and wait briefly for an in-flight reconciliation."""
        if timeout_seconds < 0:
            message = "checkpoint supervisor timeout cannot be negative"
            raise ValueError(message)
        self._stop.set()
        thread = self._thread
        if thread is None:
            return
        thread.join(timeout_seconds)
        if not thread.is_alive():
            self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            with suppress(Exception):  # Persisted checkpoint state owns failure diagnostics.
                self._application.reconcile_pending_checkpoints(limit=self._limit)
            self._stop.wait(self._interval_seconds)


__all__ = ["DeliveryCheckpointSupervisor"]
