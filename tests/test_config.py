"""Tests for owlbear.config — OwlBearSettings."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

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


class TestSlackSettingsDefaults:
    """Verify Slack fields default to None."""

    def test_slack_app_token_default_none(self, default_settings: OwlBearSettings) -> None:
        assert default_settings.slack_app_token is None

    def test_slack_bot_token_default_none(self, default_settings: OwlBearSettings) -> None:
        assert default_settings.slack_bot_token is None

    def test_slack_channel_id_default_none(self, default_settings: OwlBearSettings) -> None:
        assert default_settings.slack_channel_id is None


class TestSlackSettingsAllSet:
    """All three Slack fields set should work fine."""

    def test_all_slack_fields_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_SLACK_APP_TOKEN", "xapp-1-A111-222-abc")
        monkeypatch.setenv("OWLBEAR_SLACK_BOT_TOKEN", "xoxb-111-222-abc")
        monkeypatch.setenv("OWLBEAR_SLACK_CHANNEL_ID", "C12345678")
        settings = OwlBearSettings()
        assert isinstance(settings.slack_app_token, SecretStr)
        assert settings.slack_app_token.get_secret_value() == "xapp-1-A111-222-abc"
        assert isinstance(settings.slack_bot_token, SecretStr)
        assert settings.slack_bot_token.get_secret_value() == "xoxb-111-222-abc"
        assert settings.slack_channel_id == "C12345678"


class TestSlackSettingsPartialRaises:
    """If any Slack field is set, all three must be set — otherwise ValidationError."""

    def test_only_app_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_SLACK_APP_TOKEN", "xapp-1-A111-222-abc")
        with pytest.raises(ValidationError, match="Slack"):
            OwlBearSettings()

    def test_only_bot_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_SLACK_BOT_TOKEN", "xoxb-111-222-abc")
        with pytest.raises(ValidationError, match="Slack"):
            OwlBearSettings()

    def test_only_channel_id_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_SLACK_CHANNEL_ID", "C12345678")
        with pytest.raises(ValidationError, match="Slack"):
            OwlBearSettings()

    def test_app_and_bot_without_channel_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_SLACK_APP_TOKEN", "xapp-1-A111-222-abc")
        monkeypatch.setenv("OWLBEAR_SLACK_BOT_TOKEN", "xoxb-111-222-abc")
        with pytest.raises(ValidationError, match="Slack"):
            OwlBearSettings()

    def test_app_and_channel_without_bot_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_SLACK_APP_TOKEN", "xapp-1-A111-222-abc")
        monkeypatch.setenv("OWLBEAR_SLACK_CHANNEL_ID", "C12345678")
        with pytest.raises(ValidationError, match="Slack"):
            OwlBearSettings()

    def test_bot_and_channel_without_app_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_SLACK_BOT_TOKEN", "xoxb-111-222-abc")
        monkeypatch.setenv("OWLBEAR_SLACK_CHANNEL_ID", "C12345678")
        with pytest.raises(ValidationError, match="Slack"):
            OwlBearSettings()
