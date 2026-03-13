"""Copilot LLM provider integration.

Creates an :class:`openai.AsyncOpenAI` client configured for the GitHub
Copilot API, using device-flow OAuth tokens and the required
Copilot-Integration-Id header.  HTTP requests are guarded by a
:class:`~owlbear.core.circuit_breaker.CircuitBreakerTransport` (fast-fail
when the API is down) wrapping
:class:`pydantic_ai.retries.AsyncTenacityTransport` (retry transient
errors 429/502/503/504).
"""

from __future__ import annotations

import httpx
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.retries import AsyncTenacityTransport, RetryConfig, wait_retry_after
from tenacity import retry_if_exception_type, stop_after_attempt, wait_exponential

from owlbear.auth.copilot import derive_base_url, load_token
from owlbear.config import OwlBearSettings
from owlbear.core.circuit_breaker import CircuitBreaker, CircuitBreakerTransport

_COPILOT_INTEGRATION_HEADER = {"Copilot-Integration-Id": "vscode-chat"}

_TRANSIENT_STATUS_CODES: frozenset[int] = frozenset({429, 502, 503, 504})

# Module-level breaker so state persists across client recreations (e.g. auth refresh).
_copilot_breaker = CircuitBreaker()


def _validate_transient_response(response: httpx.Response) -> None:
    """Raise :class:`httpx.HTTPStatusError` only for transient status codes.

    Transient codes (429, 502, 503, 504) are raised so the
    :class:`AsyncTenacityTransport` can retry them.  All other status
    codes — including permanent errors (400, 404, 422) and auth errors
    (401, 403) — pass through untouched so callers can handle them.
    """
    if response.status_code in _TRANSIENT_STATUS_CODES:
        response.raise_for_status()


def _build_retry_transport(
    *,
    inner_transport: httpx.AsyncBaseTransport | None = None,
) -> AsyncTenacityTransport:
    """Build an :class:`AsyncTenacityTransport` with OwlBear retry policy.

    - Max 3 attempts
    - Exponential backoff: base 1 s, multiplier 2, max 30 s
    - Respects ``Retry-After`` header on 429 responses
    - Retries :class:`httpx.HTTPStatusError` (transient codes),
      :class:`httpx.ConnectError`, and :class:`httpx.TimeoutException`
    - Re-raises the original exception after exhausting retries

    Args:
        inner_transport: Optional custom inner transport (useful for testing).

    Returns:
        Configured :class:`AsyncTenacityTransport`.
    """
    config = RetryConfig(
        retry=retry_if_exception_type(
            (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
        ),
        stop=stop_after_attempt(3),
        wait=wait_retry_after(
            fallback_strategy=wait_exponential(multiplier=2, min=1, max=30),
            max_wait=30,
        ),
        reraise=True,
    )
    kwargs: dict = {"config": config, "validate_response": _validate_transient_response}
    if inner_transport is not None:
        kwargs["wrapped"] = inner_transport
    return AsyncTenacityTransport(**kwargs)


async def create_copilot_client(settings: OwlBearSettings | None = None) -> AsyncOpenAI:
    """Create an AsyncOpenAI client configured for the Copilot API.

    Loads the cached token from disk, derives the API base URL from the
    token's ``proxy-ep`` field, and returns an :class:`AsyncOpenAI` client
    with the appropriate headers.

    Args:
        settings: Optional settings override. Uses defaults when ``None``.

    Returns:
        Configured AsyncOpenAI client.

    Raises:
        RuntimeError: If no valid Copilot token is cached.
    """
    settings = settings or OwlBearSettings()
    token_data = load_token(settings.copilot_token_path)

    if token_data is None:
        msg = "No valid Copilot token found. Run 'bearclaw auth login' first."
        raise RuntimeError(msg)

    token = token_data["token"]
    base_url = derive_base_url(token)

    transport = CircuitBreakerTransport(
        _build_retry_transport(),
        breaker=_copilot_breaker,
    )
    http_client = httpx.AsyncClient(
        transport=transport,
        timeout=httpx.Timeout(600, connect=5),
    )

    return AsyncOpenAI(
        api_key=token,
        base_url=f"{base_url}/v1",
        default_headers=_COPILOT_INTEGRATION_HEADER,
        http_client=http_client,
    )


async def create_copilot_model(
    settings: OwlBearSettings | None = None,
    *,
    openai_client: AsyncOpenAI | None = None,
) -> OpenAIChatModel:
    """Create a PydanticAI-compatible model backed by the Copilot API.

    Calls :func:`create_copilot_client` to obtain an ``AsyncOpenAI`` client,
    wraps it in an :class:`OpenAIProvider`, and returns an
    :class:`OpenAIChatModel` ready to pass to ``Agent()`` or
    ``OwlBearAgent()``.

    Args:
        settings: Optional settings override. Uses defaults when ``None``.
        openai_client: Pre-created client to reuse. When ``None``,
            a new client is created via :func:`create_copilot_client`.

    Returns:
        Configured OpenAIChatModel instance.

    Raises:
        RuntimeError: If no valid Copilot token is cached.
    """
    settings = settings or OwlBearSettings()
    client = openai_client or await create_copilot_client(settings)
    provider = OpenAIProvider(openai_client=client)
    return OpenAIChatModel(settings.chat_model, provider=provider)


# Future extensibility — add create_lmstudio_client() for local LM Studio provider
