"""Tests for owlbear.config — OwlBearSettings."""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear.config import OwlBearSettings


class TestOwlBearSettingsDefaults:
    """Verify that OwlBearSettings instantiates with correct defaults."""

    def test_instantiation(self, default_settings: OwlBearSettings) -> None:
        """Settings object should instantiate without any arguments."""
        assert default_settings is not None

    def test_provider_default(self, default_settings: OwlBearSettings) -> None:
        """Default provider should be 'copilot'."""
        assert default_settings.provider == "copilot"

    def test_copilot_token_path_is_path(self, default_settings: OwlBearSettings) -> None:
        """copilot_token_path should be a Path object pointing under ~/.owlbear."""
        assert isinstance(default_settings.copilot_token_path, Path)
        assert default_settings.copilot_token_path.name == "copilot_token.json"

    def test_copilot_base_url_default(self, default_settings: OwlBearSettings) -> None:
        """Default Copilot base URL should be the individual API endpoint."""
        assert default_settings.copilot_base_url == "https://api.individual.githubcopilot.com"

    def test_chat_model_default(self, default_settings: OwlBearSettings) -> None:
        """Default chat model should be gpt-4o."""
        assert default_settings.chat_model == "gpt-4o"

    def test_debug_default_false(self, default_settings: OwlBearSettings) -> None:
        """Debug mode should be off by default."""
        assert default_settings.debug is False


class TestOwlBearSettingsEnvOverrides:
    """Verify that environment variables with OWLBEAR_ prefix override settings."""

    def test_provider_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_PROVIDER env var should override the provider field."""
        monkeypatch.setenv("OWLBEAR_PROVIDER", "copilot")
        settings = OwlBearSettings()
        assert settings.provider == "copilot"

    def test_debug_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_DEBUG=true should enable debug mode."""
        monkeypatch.setenv("OWLBEAR_DEBUG", "true")
        settings = OwlBearSettings()
        assert settings.debug is True

    def test_chat_model_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_CHAT_MODEL should override the chat model."""
        monkeypatch.setenv("OWLBEAR_CHAT_MODEL", "claude-sonnet-4")
        settings = OwlBearSettings()
        assert settings.chat_model == "claude-sonnet-4"

    def test_copilot_base_url_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_COPILOT_BASE_URL should override the base URL."""
        monkeypatch.setenv("OWLBEAR_COPILOT_BASE_URL", "https://custom.api.example.com")
        settings = OwlBearSettings()
        assert settings.copilot_base_url == "https://custom.api.example.com"
