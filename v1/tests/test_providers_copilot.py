"""Tests for the Copilot LLM provider (owlbear.providers.copilot)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from owlbear.config import OwlBearSettings


class TestCreateCopilotClient:
    """Test create_copilot_client() factory function."""

    @pytest.mark.asyncio
    async def test_returns_async_openai_with_correct_api_key(self) -> None:
        """Valid cached token → AsyncOpenAI client with token as api_key."""
        from owlbear.providers.copilot import create_copilot_client

        token_data = {
            "token": "tid=abc;exp=9999999999;proxy-ep=proxy.individual.githubcopilot.com",
            "expires_at": 9999999999,
        }
        with patch("owlbear.providers.copilot.load_token", return_value=token_data):
            client = await create_copilot_client()

        assert client.api_key == token_data["token"]

    @pytest.mark.asyncio
    async def test_returns_client_with_derived_base_url(self) -> None:
        """Base URL should be derived from token proxy-ep field."""
        from owlbear.providers.copilot import create_copilot_client

        token_data = {
            "token": "tid=abc;exp=9999999999;proxy-ep=proxy.individual.githubcopilot.com",
            "expires_at": 9999999999,
        }
        with patch("owlbear.providers.copilot.load_token", return_value=token_data):
            client = await create_copilot_client()

        assert str(client.base_url) == "https://api.individual.githubcopilot.com/v1/"

    @pytest.mark.asyncio
    async def test_returns_client_with_copilot_integration_header(self) -> None:
        """Client default headers should include Copilot-Integration-Id."""
        from owlbear.providers.copilot import create_copilot_client

        token_data = {
            "token": "tid=abc;exp=9999999999;proxy-ep=proxy.individual.githubcopilot.com",
            "expires_at": 9999999999,
        }
        with patch("owlbear.providers.copilot.load_token", return_value=token_data):
            client = await create_copilot_client()

        # AsyncOpenAI stores custom headers; check via _custom_headers
        assert client._custom_headers["Copilot-Integration-Id"] == "vscode-chat"

    @pytest.mark.asyncio
    async def test_raises_runtime_error_when_no_token(self) -> None:
        """No cached token → RuntimeError with helpful message."""
        from owlbear.providers.copilot import create_copilot_client

        with (
            patch("owlbear.providers.copilot.load_token", return_value=None),
            pytest.raises(RuntimeError, match="No valid Copilot token"),
        ):
            await create_copilot_client()

    @pytest.mark.asyncio
    async def test_uses_custom_settings(self, tmp_path) -> None:
        """Custom settings object is forwarded to load_token."""
        from owlbear.providers.copilot import create_copilot_client

        custom_path = tmp_path / "custom_token.json"
        settings = OwlBearSettings(copilot_token_path=custom_path)

        token_data = {
            "token": "tid=x;exp=9999999999;proxy-ep=proxy.example.com",
            "expires_at": 9999999999,
        }
        with patch("owlbear.providers.copilot.load_token", return_value=token_data) as mock_load:
            client = await create_copilot_client(settings)

        mock_load.assert_called_once_with(custom_path)
        assert client.api_key == token_data["token"]

    @pytest.mark.asyncio
    async def test_defaults_settings_when_none(self) -> None:
        """When settings=None, a default OwlBearSettings is created."""
        from owlbear.providers.copilot import create_copilot_client

        token_data = {
            "token": "tid=x;exp=9999999999;proxy-ep=proxy.individual.githubcopilot.com",
            "expires_at": 9999999999,
        }
        with patch("owlbear.providers.copilot.load_token", return_value=token_data) as mock_load:
            await create_copilot_client(None)

        # Should have been called with the default path
        default_settings = OwlBearSettings()
        mock_load.assert_called_once_with(default_settings.copilot_token_path)

    @pytest.mark.asyncio
    async def test_base_url_fallback_when_no_proxy_ep(self) -> None:
        """Token without proxy-ep → uses DEFAULT_COPILOT_BASE."""
        from owlbear.providers.copilot import create_copilot_client

        token_data = {
            "token": "tid=abc;exp=9999999999",
            "expires_at": 9999999999,
        }
        with patch("owlbear.providers.copilot.load_token", return_value=token_data):
            client = await create_copilot_client()

        assert str(client.base_url) == "https://api.individual.githubcopilot.com/v1/"


class TestCreateCopilotModel:
    """Test create_copilot_model() bridge function."""

    @pytest.mark.asyncio
    async def test_returns_openai_chat_model(self) -> None:
        """create_copilot_model returns an OpenAIChatModel instance."""
        from pydantic_ai.models.openai import OpenAIChatModel

        from owlbear.providers.copilot import create_copilot_model

        mock_client = MagicMock()
        with patch(
            "owlbear.providers.copilot.create_copilot_client",
            return_value=mock_client,
        ):
            model = await create_copilot_model()

        assert isinstance(model, OpenAIChatModel)

    @pytest.mark.asyncio
    async def test_forwards_chat_model_from_settings(self) -> None:
        """settings.chat_model is used as the model name."""
        from owlbear.providers.copilot import create_copilot_model

        settings = OwlBearSettings(chat_model="gpt-4.1")
        mock_client = MagicMock()
        with patch(
            "owlbear.providers.copilot.create_copilot_client",
            return_value=mock_client,
        ):
            model = await create_copilot_model(settings)

        assert model.model_name == "gpt-4.1"

    @pytest.mark.asyncio
    async def test_propagates_runtime_error_when_no_token(self) -> None:
        """RuntimeError from create_copilot_client propagates unchanged."""
        from owlbear.providers.copilot import create_copilot_model

        with (
            patch(
                "owlbear.providers.copilot.create_copilot_client",
                side_effect=RuntimeError("No valid Copilot token"),
            ),
            pytest.raises(RuntimeError, match="No valid Copilot token"),
        ):
            await create_copilot_model()

    @pytest.mark.asyncio
    async def test_wraps_client_in_openai_provider(self) -> None:
        """The returned model uses an OpenAIProvider wrapping the client."""
        from pydantic_ai.providers.openai import OpenAIProvider

        from owlbear.providers.copilot import create_copilot_model

        mock_client = MagicMock()
        with patch(
            "owlbear.providers.copilot.create_copilot_client",
            return_value=mock_client,
        ):
            model = await create_copilot_model()

        assert isinstance(model._provider, OpenAIProvider)


# ---------------------------------------------------------------------------
# Helpers for retry transport tests
# ---------------------------------------------------------------------------

_TOKEN_DATA = {
    "token": "tid=abc;exp=9999999999;proxy-ep=proxy.individual.githubcopilot.com",
    "expires_at": 9999999999,
}


def _make_response(status_code: int, headers: dict[str, str] | None = None) -> httpx.Response:
    """Build a minimal httpx.Response for testing."""
    return httpx.Response(
        status_code=status_code,
        headers=headers or {},
        request=httpx.Request("GET", "https://example.com"),
    )


class TestRetryTransportConfig:
    """Verify that create_copilot_client wires an AsyncTenacityTransport."""

    @pytest.mark.asyncio
    async def test_client_uses_retry_transport(self) -> None:
        """AsyncOpenAI's http_client should use AsyncTenacityTransport."""
        from pydantic_ai.retries import AsyncTenacityTransport

        from owlbear.providers.copilot import create_copilot_client

        with patch("owlbear.providers.copilot.load_token", return_value=_TOKEN_DATA):
            client = await create_copilot_client()

        transport = client._client._transport
        assert isinstance(transport, AsyncTenacityTransport)

    @pytest.mark.asyncio
    async def test_validate_response_is_set(self) -> None:
        """The transport's validate_response callback should be set."""
        from pydantic_ai.retries import AsyncTenacityTransport

        from owlbear.providers.copilot import create_copilot_client

        with patch("owlbear.providers.copilot.load_token", return_value=_TOKEN_DATA):
            client = await create_copilot_client()

        transport = client._client._transport
        assert isinstance(transport, AsyncTenacityTransport)
        assert transport.validate_response is not None


class TestRetryTransientCodes:
    """Transient status codes (429, 502, 503, 504) trigger retry."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [429, 502, 503, 504])
    async def test_transient_codes_are_retried(self, status_code: int) -> None:
        """Transient HTTP codes trigger retries up to max attempts."""
        from owlbear.providers.copilot import _validate_transient_response

        response = _make_response(status_code)
        with pytest.raises(httpx.HTTPStatusError):
            _validate_transient_response(response)


class TestPermanentCodesPropagateImmediately:
    """Permanent errors (400, 404, 422) and auth errors (401, 403) pass through."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [400, 404, 422])
    async def test_permanent_codes_not_raised_by_validator(self, status_code: int) -> None:
        """Permanent HTTP codes are NOT raised by the validator (pass through)."""
        from owlbear.providers.copilot import _validate_transient_response

        response = _make_response(status_code)
        # Should NOT raise — permanent errors pass through the transport
        _validate_transient_response(response)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [401, 403])
    async def test_auth_codes_not_raised_by_validator(self, status_code: int) -> None:
        """Auth HTTP codes are NOT raised by the validator (handled at daemon layer)."""
        from owlbear.providers.copilot import _validate_transient_response

        response = _make_response(status_code)
        # Should NOT raise — auth errors handled by daemon layer
        _validate_transient_response(response)

    @pytest.mark.asyncio
    async def test_success_codes_pass_through(self) -> None:
        """2xx responses pass through without raising."""
        from owlbear.providers.copilot import _validate_transient_response

        response = _make_response(200)
        _validate_transient_response(response)


class TestRetryAfterHeader:
    """429 responses with Retry-After header should be respected."""

    @pytest.mark.asyncio
    async def test_retry_after_seconds_header_present_in_exception(self) -> None:
        """When 429 has Retry-After header, it's available in the raised exception."""
        from owlbear.providers.copilot import _validate_transient_response

        response = _make_response(429, headers={"Retry-After": "5"})
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            _validate_transient_response(response)

        assert exc_info.value.response.headers.get("Retry-After") == "5"


class TestRetryConfig:
    """Verify the retry configuration parameters."""

    @pytest.mark.asyncio
    async def test_max_3_retry_attempts(self) -> None:
        """The transport should be configured for max 3 attempts."""
        from tenacity import stop_after_attempt

        from owlbear.providers.copilot import create_copilot_client

        with patch("owlbear.providers.copilot.load_token", return_value=_TOKEN_DATA):
            client = await create_copilot_client()

        transport = client._client._transport
        # The stop config should be stop_after_attempt(3)
        assert isinstance(transport.config["stop"], stop_after_attempt)
        assert transport.config["stop"].max_attempt_number == 3

    @pytest.mark.asyncio
    async def test_reraise_is_true(self) -> None:
        """After exhausting retries, the original exception should be re-raised."""
        from owlbear.providers.copilot import create_copilot_client

        with patch("owlbear.providers.copilot.load_token", return_value=_TOKEN_DATA):
            client = await create_copilot_client()

        transport = client._client._transport
        assert transport.config.get("reraise") is True

    @pytest.mark.asyncio
    async def test_retry_covers_transient_exception_types(self) -> None:
        """Retry should trigger on HTTPStatusError, ConnectError, and TimeoutException."""
        from tenacity.retry import retry_if_exception_type

        from owlbear.providers.copilot import create_copilot_client

        with patch("owlbear.providers.copilot.load_token", return_value=_TOKEN_DATA):
            client = await create_copilot_client()

        transport = client._client._transport
        retry_config = transport.config["retry"]
        assert isinstance(retry_config, retry_if_exception_type)
        # Must cover all three transient exception types
        assert retry_config.exception_types == (
            httpx.HTTPStatusError,
            httpx.ConnectError,
            httpx.TimeoutException,
        )


class TestExistingClientBehaviorPreserved:
    """Ensure retry transport doesn't break existing client properties."""

    @pytest.mark.asyncio
    async def test_api_key_still_correct(self) -> None:
        """Client still has the correct API key after adding retry transport."""
        from owlbear.providers.copilot import create_copilot_client

        with patch("owlbear.providers.copilot.load_token", return_value=_TOKEN_DATA):
            client = await create_copilot_client()

        assert client.api_key == _TOKEN_DATA["token"]

    @pytest.mark.asyncio
    async def test_base_url_still_correct(self) -> None:
        """Client still has the correct base URL after adding retry transport."""
        from owlbear.providers.copilot import create_copilot_client

        with patch("owlbear.providers.copilot.load_token", return_value=_TOKEN_DATA):
            client = await create_copilot_client()

        assert str(client.base_url) == "https://api.individual.githubcopilot.com/v1/"

    @pytest.mark.asyncio
    async def test_copilot_header_still_present(self) -> None:
        """Client still has the Copilot-Integration-Id header."""
        from owlbear.providers.copilot import create_copilot_client

        with patch("owlbear.providers.copilot.load_token", return_value=_TOKEN_DATA):
            client = await create_copilot_client()

        assert client._custom_headers["Copilot-Integration-Id"] == "vscode-chat"


class TestRetryTransportIntegration:
    """Integration-level tests: verify retry actually happens end-to-end."""

    @pytest.mark.asyncio
    async def test_retries_on_502_then_succeeds(self) -> None:
        """Transport retries on 502 and succeeds on next attempt."""
        from owlbear.providers.copilot import _build_retry_transport

        calls: list[int] = []

        async def mock_handle(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            if len(calls) < 2:
                return httpx.Response(502, request=request)
            return httpx.Response(200, request=request)

        mock_inner = AsyncMock(spec=httpx.AsyncBaseTransport)
        mock_inner.handle_async_request = mock_handle

        transport = _build_retry_transport(inner_transport=mock_inner)

        request = httpx.Request("GET", "https://example.com")
        response = await transport.handle_async_request(request)

        assert response.status_code == 200
        assert len(calls) == 2  # first 502 + second 200

    @pytest.mark.asyncio
    async def test_exhausts_retries_on_persistent_503(self) -> None:
        """Transport raises after max retries on persistent 503."""
        from owlbear.providers.copilot import _build_retry_transport

        calls: list[int] = []

        async def mock_handle(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            return httpx.Response(503, request=request)

        mock_inner = AsyncMock(spec=httpx.AsyncBaseTransport)
        mock_inner.handle_async_request = mock_handle

        transport = _build_retry_transport(inner_transport=mock_inner)

        request = httpx.Request("GET", "https://example.com")
        with pytest.raises(httpx.HTTPStatusError):
            await transport.handle_async_request(request)

        assert len(calls) == 3  # max 3 attempts

    @pytest.mark.asyncio
    async def test_does_not_retry_on_404(self) -> None:
        """Transport does NOT retry on 404 — passes through immediately."""
        from owlbear.providers.copilot import _build_retry_transport

        calls: list[int] = []

        async def mock_handle(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            return httpx.Response(404, request=request)

        mock_inner = AsyncMock(spec=httpx.AsyncBaseTransport)
        mock_inner.handle_async_request = mock_handle

        transport = _build_retry_transport(inner_transport=mock_inner)

        request = httpx.Request("GET", "https://example.com")
        response = await transport.handle_async_request(request)

        assert response.status_code == 404
        assert len(calls) == 1  # no retry

    @pytest.mark.asyncio
    async def test_does_not_retry_on_401(self) -> None:
        """Transport does NOT retry on 401 — auth errors pass through."""
        from owlbear.providers.copilot import _build_retry_transport

        calls: list[int] = []

        async def mock_handle(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            return httpx.Response(401, request=request)

        mock_inner = AsyncMock(spec=httpx.AsyncBaseTransport)
        mock_inner.handle_async_request = mock_handle

        transport = _build_retry_transport(inner_transport=mock_inner)

        request = httpx.Request("GET", "https://example.com")
        response = await transport.handle_async_request(request)

        assert response.status_code == 401
        assert len(calls) == 1  # no retry

    @pytest.mark.asyncio
    async def test_connect_error_triggers_retry(self) -> None:
        """Transport retries on ConnectError twice then succeeds."""
        from owlbear.providers.copilot import _build_retry_transport

        calls: list[int] = []

        async def mock_handle(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            if len(calls) < 3:
                msg = "connection refused"
                raise httpx.ConnectError(msg)
            return httpx.Response(200, request=request)

        mock_inner = AsyncMock(spec=httpx.AsyncBaseTransport)
        mock_inner.handle_async_request = mock_handle

        transport = _build_retry_transport(inner_transport=mock_inner)

        request = httpx.Request("GET", "https://example.com")
        response = await transport.handle_async_request(request)

        assert response.status_code == 200
        assert len(calls) == 3  # 2 ConnectError + 1 success

    @pytest.mark.asyncio
    async def test_timeout_exception_triggers_retry(self) -> None:
        """Transport retries on TimeoutException twice then succeeds."""
        from owlbear.providers.copilot import _build_retry_transport

        calls: list[int] = []

        async def mock_handle(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            if len(calls) < 3:
                msg = "read timed out"
                raise httpx.TimeoutException(msg)
            return httpx.Response(200, request=request)

        mock_inner = AsyncMock(spec=httpx.AsyncBaseTransport)
        mock_inner.handle_async_request = mock_handle

        transport = _build_retry_transport(inner_transport=mock_inner)

        request = httpx.Request("GET", "https://example.com")
        response = await transport.handle_async_request(request)

        assert response.status_code == 200
        assert len(calls) == 3  # 2 TimeoutException + 1 success
