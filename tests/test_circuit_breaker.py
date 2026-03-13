"""Tests for owlbear.core.circuit_breaker -- CircuitBreaker + CircuitBreakerTransport.

Test companion for #515.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest

from owlbear.core.circuit_breaker import CircuitBreaker, CircuitBreakerTransport, CircuitOpenError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_breaker(
    fail_max: int = 5,
    reset_timeout: float = 60.0,
) -> CircuitBreaker:
    """Create a CircuitBreaker with test-friendly defaults."""
    return CircuitBreaker(
        fail_max=fail_max,
        reset_timeout=reset_timeout,
    )


def _transient_http_error(status: int = 503) -> httpx.HTTPStatusError:
    """Build a transient HTTPStatusError."""
    resp = httpx.Response(status, request=httpx.Request("GET", "https://api.example.com"))
    return httpx.HTTPStatusError("service unavailable", request=resp.request, response=resp)


# ---------------------------------------------------------------------------
# CircuitBreaker -- state machine
# ---------------------------------------------------------------------------


class TestCircuitBreakerInitialState:
    """CB-1: Initial state is CLOSED, allowing calls through."""

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self) -> None:
        breaker = _make_breaker()
        assert breaker.state == "closed"

    @pytest.mark.asyncio
    async def test_closed_state_allows_calls(self) -> None:
        breaker = _make_breaker()
        # before_call should not raise when closed
        await breaker.before_call()


class TestClosedToOpen:
    """CB-2: Consecutive transient failures at threshold open the circuit."""

    @pytest.mark.asyncio
    async def test_failures_below_threshold_stay_closed(self) -> None:
        breaker = _make_breaker(fail_max=5)
        for _ in range(4):
            await breaker.on_failure(_transient_http_error())
        assert breaker.state == "closed"

    @pytest.mark.asyncio
    async def test_failures_at_threshold_open_circuit(self) -> None:
        breaker = _make_breaker(fail_max=5)
        for _ in range(5):
            await breaker.on_failure(_transient_http_error())
        assert breaker.state == "open"

    @pytest.mark.asyncio
    async def test_success_resets_failure_counter(self) -> None:
        breaker = _make_breaker(fail_max=5)
        for _ in range(4):
            await breaker.on_failure(_transient_http_error())
        await breaker.on_success()
        # After a success, counter resets; 4 more failures should not trip
        for _ in range(4):
            await breaker.on_failure(_transient_http_error())
        assert breaker.state == "closed"


class TestOpenState:
    """CB-3: OPEN state raises CircuitOpenError immediately."""

    @pytest.mark.asyncio
    async def test_open_raises_circuit_open_error(self) -> None:
        breaker = _make_breaker(fail_max=1)
        await breaker.on_failure(_transient_http_error())
        assert breaker.state == "open"
        with pytest.raises(CircuitOpenError):
            await breaker.before_call()


class TestOpenToHalfOpen:
    """CB-4: After reset_timeout, circuit transitions to HALF_OPEN."""

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_timeout(self) -> None:
        breaker = _make_breaker(fail_max=1, reset_timeout=0.05)
        await breaker.on_failure(_transient_http_error())
        assert breaker.state == "open"
        await asyncio.sleep(0.06)
        # After timeout, before_call should not raise (half-open probe)
        await breaker.before_call()
        assert breaker.state == "half_open"


class TestHalfOpenTransitions:
    """CB-5/6: HALF_OPEN success -> CLOSED, failure -> OPEN."""

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self) -> None:
        breaker = _make_breaker(fail_max=1, reset_timeout=0.05)
        await breaker.on_failure(_transient_http_error())
        await asyncio.sleep(0.06)
        await breaker.before_call()  # transitions to half_open
        assert breaker.state == "half_open"
        await breaker.on_success()
        assert breaker.state == "closed"

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self) -> None:
        breaker = _make_breaker(fail_max=1, reset_timeout=0.05)
        await breaker.on_failure(_transient_http_error())
        await asyncio.sleep(0.06)
        await breaker.before_call()  # transitions to half_open
        assert breaker.state == "half_open"
        await breaker.on_failure(_transient_http_error())
        assert breaker.state == "open"


class TestNonTransientErrors:
    """CB-7: Non-transient errors do NOT increment failure counter."""

    @pytest.mark.asyncio
    async def test_auth_error_does_not_count(self) -> None:
        breaker = _make_breaker(fail_max=2)
        # 401 is an auth error, not transient
        auth_err = httpx.HTTPStatusError(
            "unauthorized",
            request=httpx.Request("GET", "https://api.example.com"),
            response=httpx.Response(401, request=httpx.Request("GET", "https://api.example.com")),
        )
        await breaker.on_failure(auth_err)
        await breaker.on_failure(auth_err)
        await breaker.on_failure(auth_err)
        # Circuit should still be closed -- auth errors are non-transient
        assert breaker.state == "closed"

    @pytest.mark.asyncio
    async def test_permanent_error_does_not_count(self) -> None:
        breaker = _make_breaker(fail_max=2)
        perm_err = httpx.HTTPStatusError(
            "bad request",
            request=httpx.Request("GET", "https://api.example.com"),
            response=httpx.Response(400, request=httpx.Request("GET", "https://api.example.com")),
        )
        await breaker.on_failure(perm_err)
        await breaker.on_failure(perm_err)
        await breaker.on_failure(perm_err)
        assert breaker.state == "closed"


# ---------------------------------------------------------------------------
# CircuitBreakerTransport
# ---------------------------------------------------------------------------


class TestCircuitBreakerTransportClosed:
    """CB-8: Transport delegates to inner transport when circuit is closed."""

    @pytest.mark.asyncio
    async def test_delegates_to_inner_transport(self) -> None:
        inner = AsyncMock(spec=httpx.AsyncBaseTransport)
        inner.handle_async_request.return_value = httpx.Response(200)
        transport = CircuitBreakerTransport(inner)

        request = httpx.Request("POST", "https://api.example.com/v1/chat")
        response = await transport.handle_async_request(request)

        inner.handle_async_request.assert_called_once_with(request)
        assert response.status_code == 200


class TestCircuitBreakerTransportFailurePaths:
    """CB-9a: Transport translates HTTP outcomes into breaker signals."""

    @pytest.mark.asyncio
    async def test_transport_records_failure_on_inner_exception(self) -> None:
        """ConnectError from inner transport advances breaker fail counter."""
        inner = AsyncMock(spec=httpx.AsyncBaseTransport)
        inner.handle_async_request.side_effect = httpx.ConnectError("connection refused")
        breaker = CircuitBreaker(fail_max=2, reset_timeout=60.0)
        transport = CircuitBreakerTransport(inner, breaker=breaker)

        request = httpx.Request("POST", "https://api.example.com/v1/chat")

        with pytest.raises(httpx.ConnectError):
            await transport.handle_async_request(request)

        # One failure recorded; one more should open the circuit
        assert breaker.state == "closed"
        assert breaker._fail_counter == 1

    @pytest.mark.asyncio
    async def test_transport_detects_transient_status_code(self) -> None:
        """Inner transport returns 503 → breaker records failure via on_failure."""
        inner = AsyncMock(spec=httpx.AsyncBaseTransport)
        inner.handle_async_request.return_value = httpx.Response(
            503, request=httpx.Request("GET", "https://api.example.com")
        )
        breaker = CircuitBreaker(fail_max=2, reset_timeout=60.0)
        transport = CircuitBreakerTransport(inner, breaker=breaker)

        request = httpx.Request("GET", "https://api.example.com")
        response = await transport.handle_async_request(request)

        # Response is still returned (caller decides what to do)
        assert response.status_code == 503
        # But breaker should have recorded a failure
        assert breaker._fail_counter == 1


class TestCircuitBreakerTransportOpen:
    """CB-9: Transport raises CircuitOpenError when circuit is open."""

    @pytest.mark.asyncio
    async def test_raises_circuit_open_error_when_open(self) -> None:
        inner = AsyncMock(spec=httpx.AsyncBaseTransport)
        breaker = CircuitBreaker(fail_max=1, reset_timeout=60.0)
        transport = CircuitBreakerTransport(inner, breaker=breaker)

        # Trip the breaker
        await breaker.on_failure(_transient_http_error())
        assert breaker.state == "open"

        request = httpx.Request("POST", "https://api.example.com/v1/chat")
        with pytest.raises(CircuitOpenError):
            await transport.handle_async_request(request)

        # Inner transport should NOT have been called
        inner.handle_async_request.assert_not_called()


# ---------------------------------------------------------------------------
# classify_error integration
# ---------------------------------------------------------------------------


class TestClassifyCircuitOpenError:
    """CB-10: classify_error(CircuitOpenError()) returns PERMANENT."""

    def test_circuit_open_error_is_permanent(self) -> None:
        from owlbear.core.errors import ErrorCategory, classify_error

        exc = CircuitOpenError()
        assert classify_error(exc) is ErrorCategory.PERMANENT
