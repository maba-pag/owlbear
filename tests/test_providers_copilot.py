"""Tests for the Copilot LLM provider (owlbear.providers.copilot)."""

from __future__ import annotations

from unittest.mock import patch

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
        assert client._custom_headers["Copilot-Integration-Id"] == "vscode-chat"  # noqa: SLF001

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
