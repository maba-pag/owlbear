"""Tests for owlbear.core.retry — TRANSIENT_RETRY decorator."""

from __future__ import annotations

import httpx
import pytest

from owlbear.core.retry import TRANSIENT_RETRY, _is_transient_http

# ---------------------------------------------------------------------------
# Predicate tests — _is_transient_http
# ---------------------------------------------------------------------------


class TestIsTransientHttp:
    """Verify _is_transient_http returns correct bool for each exception type."""

    def test_connect_error_is_transient(self) -> None:
        exc = httpx.ConnectError("connection refused")
        assert _is_transient_http(exc) is True

    def test_timeout_exception_is_transient(self) -> None:
        exc = httpx.TimeoutException("read timed out")
        assert _is_transient_http(exc) is True

    @pytest.mark.parametrize("status_code", [429, 502, 503, 504])
    def test_http_status_error_transient_codes(self, status_code: int) -> None:
        response = httpx.Response(status_code, request=httpx.Request("GET", "https://x"))
        exc = httpx.HTTPStatusError("err", request=response.request, response=response)
        assert _is_transient_http(exc) is True

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 500])
    def test_http_status_error_non_transient_codes(self, status_code: int) -> None:
        response = httpx.Response(status_code, request=httpx.Request("GET", "https://x"))
        exc = httpx.HTTPStatusError("err", request=response.request, response=response)
        assert _is_transient_http(exc) is False

    def test_value_error_not_transient(self) -> None:
        assert _is_transient_http(ValueError("bad")) is False

    def test_runtime_error_not_transient(self) -> None:
        assert _is_transient_http(RuntimeError("nope")) is False

    def test_base_exception_not_transient(self) -> None:
        assert _is_transient_http(KeyboardInterrupt()) is False


# ---------------------------------------------------------------------------
# Decorator integration tests — TRANSIENT_RETRY
# ---------------------------------------------------------------------------


class TestTransientRetry:
    """Verify TRANSIENT_RETRY retries transient errors and propagates others."""

    @pytest.mark.anyio
    async def test_retries_transient_then_succeeds(self) -> None:
        """Fails twice with transient error, then succeeds — 3 calls total."""
        call_count = 0

        @TRANSIENT_RETRY
        async def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                msg = "transient"
                raise httpx.ConnectError(msg)
            return "ok"

        result = await flaky()
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.anyio
    async def test_non_transient_propagates_immediately(self) -> None:
        """Non-transient exception propagates without retry — 1 call only."""
        call_count = 0

        @TRANSIENT_RETRY
        async def broken() -> str:
            nonlocal call_count
            call_count += 1
            msg = "permanent"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="permanent"):
            await broken()
        assert call_count == 1

    @pytest.mark.anyio
    async def test_exhausts_retries_and_reraises(self) -> None:
        """All 3 attempts fail — original exception is reraised."""
        call_count = 0

        @TRANSIENT_RETRY
        async def always_fails() -> str:
            nonlocal call_count
            call_count += 1
            msg = "timeout"
            raise httpx.TimeoutException(msg)

        with pytest.raises(httpx.TimeoutException, match="timeout"):
            await always_fails()
        assert call_count == 3
