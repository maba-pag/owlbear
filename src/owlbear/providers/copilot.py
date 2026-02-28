"""Copilot LLM provider integration.

Creates an :class:`openai.AsyncOpenAI` client configured for the GitHub
Copilot API, using device-flow OAuth tokens and the required
Copilot-Integration-Id header.
"""

from __future__ import annotations

from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from owlbear.auth.copilot import derive_base_url, load_token
from owlbear.config import OwlBearSettings

_COPILOT_INTEGRATION_HEADER = {"Copilot-Integration-Id": "vscode-chat"}


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

    return AsyncOpenAI(
        api_key=token,
        base_url=f"{base_url}/v1",
        default_headers=_COPILOT_INTEGRATION_HEADER,
    )


async def create_copilot_model(settings: OwlBearSettings | None = None) -> OpenAIChatModel:
    """Create a PydanticAI-compatible model backed by the Copilot API.

    Calls :func:`create_copilot_client` to obtain an ``AsyncOpenAI`` client,
    wraps it in an :class:`OpenAIProvider`, and returns an
    :class:`OpenAIChatModel` ready to pass to ``Agent()`` or
    ``OwlBearAgent()``.

    Args:
        settings: Optional settings override. Uses defaults when ``None``.

    Returns:
        Configured OpenAIChatModel instance.

    Raises:
        RuntimeError: If no valid Copilot token is cached.
    """
    settings = settings or OwlBearSettings()
    client = await create_copilot_client(settings)
    provider = OpenAIProvider(openai_client=client)
    return OpenAIChatModel(settings.chat_model, provider=provider)


# Future extensibility — add create_lmstudio_client() for local LM Studio provider
