"""Circuit breaker for transient API failures.

Implements the standard closed → open → half-open state machine to
fast-fail when an upstream API (e.g. Copilot) is experiencing sustained
outages, preventing cascading retry delays.

:class:`CircuitBreaker` — async-safe state machine with configurable
``fail_max`` and ``reset_timeout``.

:class:`CircuitBreakerTransport` — :class:`httpx.AsyncBaseTransport`
wrapper that guards every HTTP call with a circuit breaker.

:class:`CircuitOpenError` — raised when the circuit is open;
classified as ``PERMANENT`` by :func:`owlbear.core.errors.classify_error`
so daemon-level retry does not fire.

See ``docs/circuit-breaker.md`` for design rationale.
"""

from __future__ import annotations

import asyncio
import time
from typing import Literal

import httpx

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

State = Literal["closed", "open", "half_open"]


class CircuitOpenError(Exception):
    """Raised when the circuit breaker is open and rejecting calls."""


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


class CircuitBreaker:
    """Async-safe circuit breaker with three states.

    Args:
        fail_max: Consecutive transient failures before opening.
        reset_timeout: Seconds to wait in open state before probing.
    """

    def __init__(
        self,
        fail_max: int = 5,
        reset_timeout: float = 60.0,
    ) -> None:
        self._fail_max = fail_max
        self._reset_timeout = reset_timeout

        self._state: State = "closed"
        self._fail_counter: int = 0
        self._opened_at: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> State:
        """Current breaker state."""
        return self._state

    async def before_call(self) -> None:
        """Gate check before making an outbound call.

        Raises:
            CircuitOpenError: If the circuit is open and reset timeout
                has not elapsed.
        """
        async with self._lock:
            if self._state == "closed":
                return

            if self._state == "open":
                elapsed = time.monotonic() - self._opened_at
                if elapsed >= self._reset_timeout:
                    self._state = "half_open"
                    return
                raise CircuitOpenError

            # half_open — allow probe calls through
            return

    async def on_success(self) -> None:
        """Record a successful call. Resets failure counter."""
        async with self._lock:
            self._fail_counter = 0
            if self._state == "half_open":
                self._state = "closed"

    async def on_failure(self, exc: Exception) -> None:
        """Record a failed call. Only transient errors trip the breaker."""
        from owlbear.core.errors import ErrorCategory, classify_error  # noqa: PLC0415

        if classify_error(exc) is not ErrorCategory.TRANSIENT:
            return

        async with self._lock:
            if self._state == "half_open":
                self._state = "open"
                self._opened_at = time.monotonic()
                return

            self._fail_counter += 1
            if self._fail_counter >= self._fail_max:
                self._state = "open"
                self._opened_at = time.monotonic()


# ---------------------------------------------------------------------------
# Transport wrapper
# ---------------------------------------------------------------------------

_TRANSIENT_STATUS_CODES: frozenset[int] = frozenset({429, 502, 503, 504})


class CircuitBreakerTransport(httpx.AsyncBaseTransport):
    """``httpx.AsyncBaseTransport`` that wraps an inner transport with circuit-breaker protection.

    Args:
        inner: The transport to delegate to when the circuit is closed.
        breaker: Optional :class:`CircuitBreaker` instance. A default
            breaker is created if not provided.
    """

    def __init__(
        self,
        inner: httpx.AsyncBaseTransport,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self._inner = inner
        self._breaker = breaker or CircuitBreaker()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Delegate to inner transport, guarded by the circuit breaker."""
        await self._breaker.before_call()

        try:
            response = await self._inner.handle_async_request(request)
        except Exception as exc:
            await self._breaker.on_failure(exc)
            raise

        if response.status_code in _TRANSIENT_STATUS_CODES:
            err = httpx.HTTPStatusError(
                f"Server error {response.status_code}",
                request=request,
                response=response,
            )
            await self._breaker.on_failure(err)
        else:
            await self._breaker.on_success()

        return response
