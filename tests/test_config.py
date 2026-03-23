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

    @staticmethod
    def _clear_slack(mp: pytest.MonkeyPatch) -> None:
        """Remove all Slack env vars so each test controls exactly which are set."""
        mp.delenv("OWLBEAR_SLACK_APP_TOKEN", raising=False)
        mp.delenv("OWLBEAR_SLACK_BOT_TOKEN", raising=False)
        mp.delenv("OWLBEAR_SLACK_CHANNEL_ID", raising=False)

    def test_only_app_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._clear_slack(monkeypatch)
        monkeypatch.setenv("OWLBEAR_SLACK_APP_TOKEN", "xapp-1-A111-222-abc")
        with pytest.raises(ValidationError, match="Slack"):
            OwlBearSettings()

    def test_only_bot_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._clear_slack(monkeypatch)
        monkeypatch.setenv("OWLBEAR_SLACK_BOT_TOKEN", "xoxb-111-222-abc")
        with pytest.raises(ValidationError, match="Slack"):
            OwlBearSettings()

    def test_only_channel_id_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._clear_slack(monkeypatch)
        monkeypatch.setenv("OWLBEAR_SLACK_CHANNEL_ID", "C12345678")
        with pytest.raises(ValidationError, match="Slack"):
            OwlBearSettings()

    def test_app_and_bot_without_channel_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._clear_slack(monkeypatch)
        monkeypatch.setenv("OWLBEAR_SLACK_APP_TOKEN", "xapp-1-A111-222-abc")
        monkeypatch.setenv("OWLBEAR_SLACK_BOT_TOKEN", "xoxb-111-222-abc")
        with pytest.raises(ValidationError, match="Slack"):
            OwlBearSettings()

    def test_app_and_channel_without_bot_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._clear_slack(monkeypatch)
        monkeypatch.setenv("OWLBEAR_SLACK_APP_TOKEN", "xapp-1-A111-222-abc")
        monkeypatch.setenv("OWLBEAR_SLACK_CHANNEL_ID", "C12345678")
        with pytest.raises(ValidationError, match="Slack"):
            OwlBearSettings()

    def test_bot_and_channel_without_app_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._clear_slack(monkeypatch)
        monkeypatch.setenv("OWLBEAR_SLACK_BOT_TOKEN", "xoxb-111-222-abc")
        monkeypatch.setenv("OWLBEAR_SLACK_CHANNEL_ID", "C12345678")
        with pytest.raises(ValidationError, match="Slack"):
            OwlBearSettings()


class TestKnowledgeSettingsDefaults:
    """Verify Knowledge-related fields have correct defaults."""

    def test_knowledge_db_path_default(self, default_settings: OwlBearSettings) -> None:
        """Default knowledge_db_path should be ~/.owlbear/knowledge.db."""
        expected = Path.home() / ".owlbear" / "knowledge.db"
        assert default_settings.knowledge_db_path == expected
        assert isinstance(default_settings.knowledge_db_path, Path)

    def test_embedding_model_default(self, default_settings: OwlBearSettings) -> None:
        """Default embedding model should be BAAI/bge-small-en-v1.5."""
        assert default_settings.embedding_model == "BAAI/bge-small-en-v1.5"


class TestKnowledgeSettingsEnvOverrides:
    """Verify Knowledge env var overrides work."""

    def test_knowledge_db_path_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_KNOWLEDGE_DB_PATH should override knowledge_db_path."""
        monkeypatch.setenv("OWLBEAR_KNOWLEDGE_DB_PATH", "/opt/data/custom.db")
        settings = OwlBearSettings()
        assert settings.knowledge_db_path == Path("/opt/data/custom.db")

    def test_embedding_model_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_EMBEDDING_MODEL should override embedding_model."""
        monkeypatch.setenv("OWLBEAR_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        settings = OwlBearSettings()
        assert settings.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"


class TestNotificationSettingsDefaults:
    """Verify notification fields have correct defaults."""

    def test_notification_events_default(self, default_settings: OwlBearSettings) -> None:
        """Default notification_events must be [task_complete, on_error]."""
        assert default_settings.notification_events == [
            "task_complete",
            "on_error",
        ]

    def test_notification_backends_default(self, default_settings: OwlBearSettings) -> None:
        """Default notification_backends should be bell, sound (priority order)."""
        assert default_settings.notification_backends == ["bell", "sound"]


class TestNotificationSettingsEnvOverrides:
    """Verify notification env var overrides work."""

    def test_notification_events_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_NOTIFICATION_EVENTS should override notification_events."""
        monkeypatch.setenv("OWLBEAR_NOTIFICATION_EVENTS", '["on_error"]')
        settings = OwlBearSettings()
        assert settings.notification_events == ["on_error"]

    def test_notification_backends_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_NOTIFICATION_BACKENDS should override notification_backends."""
        monkeypatch.setenv("OWLBEAR_NOTIFICATION_BACKENDS", '["toast","slack"]')
        settings = OwlBearSettings()
        assert settings.notification_backends == ["toast", "slack"]

    def test_notification_events_custom_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Custom notification_events list should be accepted."""
        monkeypatch.setenv(
            "OWLBEAR_NOTIFICATION_EVENTS",
            '["task_complete","session_start"]',
        )
        settings = OwlBearSettings()
        assert settings.notification_events == ["task_complete", "session_start"]


# ---------------------------------------------------------------------------
# GitHub settings
# ---------------------------------------------------------------------------


class TestGitHubSettingsDefaults:
    """Verify GitHub fields default to None."""

    def test_github_token_default_none(self, default_settings: OwlBearSettings) -> None:
        assert default_settings.github_token is None

    def test_github_owner_default_none(self, default_settings: OwlBearSettings) -> None:
        assert default_settings.github_owner is None

    def test_github_repo_default_none(self, default_settings: OwlBearSettings) -> None:
        assert default_settings.github_repo is None


class TestGitHubSettingsEnvOverrides:
    """Verify GitHub env var overrides work."""

    def test_github_token_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_GITHUB_TOKEN should set github_token as SecretStr."""
        monkeypatch.setenv("OWLBEAR_GITHUB_TOKEN", "ghp_test123")
        settings = OwlBearSettings()
        assert isinstance(settings.github_token, SecretStr)
        assert settings.github_token.get_secret_value() == "ghp_test123"

    def test_github_owner_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_GITHUB_OWNER should override github_owner."""
        monkeypatch.setenv("OWLBEAR_GITHUB_OWNER", "my-org")
        settings = OwlBearSettings()
        assert settings.github_owner == "my-org"

    def test_github_repo_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_GITHUB_REPO should override github_repo."""
        monkeypatch.setenv("OWLBEAR_GITHUB_REPO", "my-repo")
        settings = OwlBearSettings()
        assert settings.github_repo == "my-repo"


# ---------------------------------------------------------------------------
# Temporal memory settings — task #224 / #212
# ---------------------------------------------------------------------------


class TestTemporalSettingsDefaults:
    """Verify temporal memory fields have correct defaults."""

    def test_temporal_decay_rate_default(self, default_settings: OwlBearSettings) -> None:
        """Default temporal_decay_rate should be 0.001 (29-day half-life)."""
        assert default_settings.temporal_decay_rate == 0.001

    def test_temporal_recency_weight_default(self, default_settings: OwlBearSettings) -> None:
        """Default temporal_recency_weight should be 0.1."""
        assert default_settings.temporal_recency_weight == 0.1


class TestTemporalSettingsEnvOverrides:
    """Verify temporal env var overrides work."""

    def test_temporal_decay_rate_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_TEMPORAL_DECAY_RATE=0.01 should change setting."""
        monkeypatch.setenv("OWLBEAR_TEMPORAL_DECAY_RATE", "0.01")
        settings = OwlBearSettings()
        assert settings.temporal_decay_rate == 0.01


# ---------------------------------------------------------------------------
# Progress reporting settings — task #334
# ---------------------------------------------------------------------------


class TestProgressSettingsDefaults:
    """Verify progress reporting fields have correct defaults."""

    def test_progress_enabled_default_true(self, default_settings: OwlBearSettings) -> None:
        """progress_enabled should default to True."""
        assert default_settings.progress_enabled is True

    def test_progress_interval_default(self, default_settings: OwlBearSettings) -> None:
        """progress_interval should default to 30.0 seconds."""
        assert default_settings.progress_interval == 30.0

    def test_progress_detail_default_brief(self, default_settings: OwlBearSettings) -> None:
        """progress_detail should default to 'brief'."""
        assert default_settings.progress_detail == "brief"


class TestProgressSettingsEnvOverrides:
    """Verify progress env var overrides work."""

    def test_progress_enabled_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_PROGRESS_ENABLED=false should disable progress."""
        monkeypatch.setenv("OWLBEAR_PROGRESS_ENABLED", "false")
        settings = OwlBearSettings()
        assert settings.progress_enabled is False

    def test_progress_interval_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_PROGRESS_INTERVAL=60 should override interval."""
        monkeypatch.setenv("OWLBEAR_PROGRESS_INTERVAL", "60")
        settings = OwlBearSettings()
        assert settings.progress_interval == 60.0

    def test_progress_detail_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_PROGRESS_DETAIL=detailed should override detail level."""
        monkeypatch.setenv("OWLBEAR_PROGRESS_DETAIL", "detailed")
        settings = OwlBearSettings()
        assert settings.progress_detail == "detailed"


class TestProgressSettingsValidation:
    """Verify progress field validation rules."""

    def test_progress_interval_must_be_positive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """progress_interval <= 0 should raise ValidationError."""
        monkeypatch.setenv("OWLBEAR_PROGRESS_INTERVAL", "0")
        with pytest.raises(ValidationError, match="progress_interval"):
            OwlBearSettings()

    def test_progress_interval_negative_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Negative progress_interval should raise ValidationError."""
        monkeypatch.setenv("OWLBEAR_PROGRESS_INTERVAL", "-5")
        with pytest.raises(ValidationError, match="progress_interval"):
            OwlBearSettings()

    def test_progress_detail_invalid_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """progress_detail must be 'brief' or 'detailed'."""
        monkeypatch.setenv("OWLBEAR_PROGRESS_DETAIL", "verbose")
        with pytest.raises(ValidationError):
            OwlBearSettings()


# ---------------------------------------------------------------------------
# Knowledge context tokens — task #424 / #407
# ---------------------------------------------------------------------------


class TestKnowledgeContextTokensDefault:
    """Verify knowledge_context_tokens defaults to 2000."""

    def test_default_value(self, default_settings: OwlBearSettings) -> None:
        """knowledge_context_tokens should default to 2000."""
        assert default_settings.knowledge_context_tokens == 2000


class TestKnowledgeContextTokensEnvOverride:
    """Verify OWLBEAR_KNOWLEDGE_CONTEXT_TOKENS env var overrides the default."""

    def test_env_override_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_KNOWLEDGE_CONTEXT_TOKENS=500 should be accepted."""
        monkeypatch.setenv("OWLBEAR_KNOWLEDGE_CONTEXT_TOKENS", "500")
        settings = OwlBearSettings()
        assert settings.knowledge_context_tokens == 500


class TestKnowledgeContextTokensValidation:
    """Verify knowledge_context_tokens must be > 0."""

    def test_zero_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """knowledge_context_tokens = 0 should raise ValidationError."""
        monkeypatch.setenv("OWLBEAR_KNOWLEDGE_CONTEXT_TOKENS", "0")
        with pytest.raises(ValidationError, match="knowledge_context_tokens"):
            OwlBearSettings()

    def test_negative_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """knowledge_context_tokens = -1 should raise ValidationError."""
        monkeypatch.setenv("OWLBEAR_KNOWLEDGE_CONTEXT_TOKENS", "-1")
        with pytest.raises(ValidationError, match="knowledge_context_tokens"):
            OwlBearSettings()


# ---------------------------------------------------------------------------
# Screenshot mode settings — task #394
# ---------------------------------------------------------------------------


class TestScreenshotModeDefault:
    """Verify screenshot_mode defaults to 'on_error'."""

    def test_screenshot_mode_default(self, default_settings: OwlBearSettings) -> None:
        """screenshot_mode should default to 'on_error'."""
        assert default_settings.screenshot_mode == "on_error"


class TestScreenshotModeEnvOverride:
    """Verify OWLBEAR_SCREENSHOT_MODE env var overrides the default."""

    def test_screenshot_mode_auto(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_SCREENSHOT_MODE=auto should be accepted."""
        monkeypatch.setenv("OWLBEAR_SCREENSHOT_MODE", "auto")
        settings = OwlBearSettings()
        assert settings.screenshot_mode == "auto"

    def test_screenshot_mode_manual(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_SCREENSHOT_MODE=manual should be accepted."""
        monkeypatch.setenv("OWLBEAR_SCREENSHOT_MODE", "manual")
        settings = OwlBearSettings()
        assert settings.screenshot_mode == "manual"

    def test_screenshot_mode_on_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_SCREENSHOT_MODE=on_error should be accepted."""
        monkeypatch.setenv("OWLBEAR_SCREENSHOT_MODE", "on_error")
        settings = OwlBearSettings()
        assert settings.screenshot_mode == "on_error"


class TestScreenshotModeValidation:
    """Verify screenshot_mode rejects invalid values."""

    def test_invalid_screenshot_mode_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Invalid screenshot_mode value should raise ValidationError."""
        monkeypatch.setenv("OWLBEAR_SCREENSHOT_MODE", "always")
        with pytest.raises(ValidationError):
            OwlBearSettings()


# ---------------------------------------------------------------------------
# Field description metadata — task #477
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Kroki / diagram settings — task #620
# ---------------------------------------------------------------------------


class TestKrokiServerUrlDefault:
    """Verify kroki_server_url defaults to 'https://kroki.io'."""

    def test_kroki_server_url_default(self, default_settings: OwlBearSettings) -> None:
        """kroki_server_url should default to 'https://kroki.io'."""
        assert default_settings.kroki_server_url == "https://kroki.io"


class TestKrokiServerUrlEnvOverride:
    """Verify OWLBEAR_KROKI_SERVER_URL env var overrides the default."""

    def test_kroki_server_url_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_KROKI_SERVER_URL should override the default."""
        monkeypatch.setenv("OWLBEAR_KROKI_SERVER_URL", "http://localhost:8000")
        settings = OwlBearSettings()
        assert settings.kroki_server_url == "http://localhost:8000"


class TestFieldDescriptions:
    """Every OwlBearSettings field must have a non-empty Field description."""

    def test_all_fields_have_descriptions(self) -> None:
        """Iterate model_fields and assert every field has a non-empty description."""
        missing: list[str] = []
        for name, field_info in OwlBearSettings.model_fields.items():
            if not field_info.description:
                missing.append(name)
        assert not missing, f"Fields missing description: {', '.join(missing)}"


# ---------------------------------------------------------------------------
# Numeric config field validators — task #840 / #547
# ---------------------------------------------------------------------------


class TestFromAC_TemporalDecayRateValidator:  # noqa: N801
    """temporal_decay_rate must be validated to the range [0, 1]."""

    def test_temporal_decay_rate_below_zero_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """temporal_decay_rate < 0 must raise ValidationError."""
        monkeypatch.setenv("OWLBEAR_TEMPORAL_DECAY_RATE", "-0.001")
        with pytest.raises(ValidationError, match="temporal_decay_rate"):
            OwlBearSettings()

    def test_temporal_decay_rate_above_one_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """temporal_decay_rate > 1 must raise ValidationError."""
        monkeypatch.setenv("OWLBEAR_TEMPORAL_DECAY_RATE", "1.001")
        with pytest.raises(ValidationError, match="temporal_decay_rate"):
            OwlBearSettings()

    def test_temporal_decay_rate_default_accepted(self, default_settings: OwlBearSettings) -> None:
        """Default 0.001 is within [0, 1]; validator must be configured on the field."""
        field = OwlBearSettings.model_fields["temporal_decay_rate"]
        assert field.metadata, "temporal_decay_rate must have ge/le constraints configured"
        assert default_settings.temporal_decay_rate == 0.001


class TestFromAC_TemporalRecencyWeightValidator:  # noqa: N801
    """temporal_recency_weight must be validated to the range [0, 1]."""

    def test_temporal_recency_weight_below_zero_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """temporal_recency_weight < 0 must raise ValidationError."""
        monkeypatch.setenv("OWLBEAR_TEMPORAL_RECENCY_WEIGHT", "-0.001")
        with pytest.raises(ValidationError, match="temporal_recency_weight"):
            OwlBearSettings()

    def test_temporal_recency_weight_above_one_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """temporal_recency_weight > 1 must raise ValidationError."""
        monkeypatch.setenv("OWLBEAR_TEMPORAL_RECENCY_WEIGHT", "1.001")
        with pytest.raises(ValidationError, match="temporal_recency_weight"):
            OwlBearSettings()

    def test_temporal_recency_weight_default_accepted(
        self, default_settings: OwlBearSettings
    ) -> None:
        """Default 0.1 is within [0, 1]; validator must be configured on the field."""
        field = OwlBearSettings.model_fields["temporal_recency_weight"]
        assert field.metadata, "temporal_recency_weight must have ge/le constraints configured"
        assert default_settings.temporal_recency_weight == 0.1


class TestFromAC_EmbeddingIdleTimeoutValidator:  # noqa: N801
    """embedding_idle_timeout must be >= 0 (explicitly accepts 0)."""

    def test_embedding_idle_timeout_negative_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """embedding_idle_timeout < 0 must raise ValidationError."""
        monkeypatch.setenv("OWLBEAR_EMBEDDING_IDLE_TIMEOUT", "-1")
        with pytest.raises(ValidationError, match="embedding_idle_timeout"):
            OwlBearSettings()

    def test_embedding_idle_timeout_zero_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """embedding_idle_timeout = 0 (disable idle unloading) must be accepted."""
        field = OwlBearSettings.model_fields["embedding_idle_timeout"]
        assert field.metadata, "embedding_idle_timeout must have ge constraint configured"
        monkeypatch.setenv("OWLBEAR_EMBEDDING_IDLE_TIMEOUT", "0")
        settings = OwlBearSettings()
        assert settings.embedding_idle_timeout == 0

    def test_embedding_idle_timeout_default_accepted(
        self, default_settings: OwlBearSettings
    ) -> None:
        """Default 600 is >= 0; validator must be configured on the field."""
        field = OwlBearSettings.model_fields["embedding_idle_timeout"]
        assert field.metadata, "embedding_idle_timeout must have ge constraint configured"
        assert default_settings.embedding_idle_timeout == 600


class TestFromAC_ApprovalTimeoutValidator:  # noqa: N801
    """approval_timeout must be > 0 (strictly positive)."""

    def test_approval_timeout_zero_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """approval_timeout = 0 must raise ValidationError (must be strictly > 0)."""
        monkeypatch.setenv("OWLBEAR_APPROVAL_TIMEOUT", "0")
        with pytest.raises(ValidationError, match="approval_timeout"):
            OwlBearSettings()

    def test_approval_timeout_negative_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """approval_timeout < 0 must raise ValidationError."""
        monkeypatch.setenv("OWLBEAR_APPROVAL_TIMEOUT", "-1")
        with pytest.raises(ValidationError, match="approval_timeout"):
            OwlBearSettings()

    def test_approval_timeout_default_accepted(self, default_settings: OwlBearSettings) -> None:
        """Default 120.0 is > 0; validator must be configured on the field."""
        field = OwlBearSettings.model_fields["approval_timeout"]
        assert field.metadata, "approval_timeout must have gt constraint configured"
        assert default_settings.approval_timeout == 120.0


# ---------------------------------------------------------------------------
# Browser nested env config — task #843 (RED tests for #553)
# ---------------------------------------------------------------------------


class TestFromAC_BrowserNestedEnvHeadless:  # noqa: N801
    """AC1: OWLBEAR_BROWSER__HEADLESS=true must set settings.browser.headless."""

    def test_browser_headless_via_nested_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_BROWSER__HEADLESS=true should populate settings.browser.headless."""
        monkeypatch.setenv("OWLBEAR_BROWSER__HEADLESS", "true")
        settings = OwlBearSettings()
        assert settings.browser.headless is True

    def test_browser_headless_false_via_nested_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_BROWSER__HEADLESS=false should set headless to False."""
        monkeypatch.setenv("OWLBEAR_BROWSER__HEADLESS", "false")
        settings = OwlBearSettings()
        assert settings.browser.headless is False


class TestFromAC_BrowserNestedEnvCdpPort:  # noqa: N801
    """AC2: OWLBEAR_BROWSER__CDP_PORT=9223 must set settings.browser.cdp_port."""

    def test_browser_cdp_port_via_nested_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_BROWSER__CDP_PORT=9223 should populate settings.browser.cdp_port."""
        monkeypatch.setenv("OWLBEAR_BROWSER__CDP_PORT", "9223")
        settings = OwlBearSettings()
        assert settings.browser.cdp_port == 9223


class TestFromAC_BrowserNestedEnvPartialUpdate:  # noqa: N801
    """AC3: Setting one nested field preserves other BrowserConfig defaults."""

    def test_headless_preserves_cdp_port_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Setting headless via env must leave cdp_port at default 9222."""
        monkeypatch.setenv("OWLBEAR_BROWSER__HEADLESS", "true")
        settings = OwlBearSettings()
        assert settings.browser.cdp_port == 9222

    def test_headless_preserves_timeout_ms_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Setting headless via env must leave timeout_ms at default 30_000."""
        monkeypatch.setenv("OWLBEAR_BROWSER__HEADLESS", "true")
        settings = OwlBearSettings()
        assert settings.browser.timeout_ms == 30_000

    def test_cdp_port_preserves_headless_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Setting cdp_port via env must leave headless at default False."""
        monkeypatch.setenv("OWLBEAR_BROWSER__CDP_PORT", "9223")
        settings = OwlBearSettings()
        assert settings.browser.headless is False


class TestFromAC_FlatEnvRegressionGuard:  # noqa: N801
    """AC4: Existing flat OWLBEAR_DEBUG=true still works after nested delimiter is added."""

    def test_flat_debug_env_still_works(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_DEBUG=true must still set settings.debug — regression guard."""
        monkeypatch.setenv("OWLBEAR_DEBUG", "true")
        settings = OwlBearSettings()
        assert settings.debug is True


# ---------------------------------------------------------------------------
# TDD RED: question_pending default hook cleanup (#968)
# ---------------------------------------------------------------------------


class TestFromAC_QuestionPendingDefaultCleanup:
    """Default notification_events excludes question_pending; explicit config accepts it."""

    def test_default_notification_events_excludes_question_pending(self) -> None:
        """Default notification_events must be exactly [task_complete, on_error]."""
        assert OwlBearSettings().notification_events == ["task_complete", "on_error"]

    def test_env_var_question_pending_explicit_opt_in_while_default_excludes_it(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Default must not include question_pending; env var can still add it explicitly."""
        # Guard: default must not include question_pending (fails until builder's fix)
        assert "question_pending" not in OwlBearSettings().notification_events
        # Main: env var override that includes question_pending is still accepted
        monkeypatch.setenv(
            "OWLBEAR_NOTIFICATION_EVENTS",
            '["task_complete", "question_pending"]',
        )
        settings = OwlBearSettings()
        assert "question_pending" in settings.notification_events

    def test_direct_constructor_question_pending_explicit_opt_in_while_default_excludes_it(
        self,
    ) -> None:
        """Default must not include question_pending; direct constructor can still add it."""
        # Guard: default must not include question_pending (fails until builder's fix)
        assert "question_pending" not in OwlBearSettings().notification_events
        # Main: direct constructor with question_pending is still accepted
        explicit = OwlBearSettings(notification_events=["task_complete", "question_pending"])
        assert "question_pending" in explicit.notification_events

    def test_default_notification_events_subset_of_live_emitted_hook_events(self) -> None:
        """Regression: default notification_events must be a subset of HookEvent members
        passed to .emit() call sites in src/owlbear.

        This prevents dead default events (events registered by default but never
        actually emitted by runtime code) from reaching users.
        """
        import ast
        from pathlib import Path

        src_root = Path(__file__).resolve().parent.parent / "src" / "owlbear"
        emitted_attrs: set[str] = set()

        for py_file in src_root.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                # Match obj.emit(...)
                if not (isinstance(node.func, ast.Attribute) and node.func.attr == "emit"):
                    continue
                # First positional arg must be HookEvent.SOMETHING
                if not node.args:
                    continue
                first_arg = node.args[0]
                if (
                    isinstance(first_arg, ast.Attribute)
                    and isinstance(first_arg.value, ast.Name)
                    and first_arg.value.id == "HookEvent"
                ):
                    emitted_attrs.add(first_arg.attr.lower())

        default_events = OwlBearSettings().notification_events
        missing = set(default_events) - emitted_attrs
        assert not missing, (
            f"Default notification_events contains events never emitted in src/owlbear: "
            f"{sorted(missing)!r}.  Live emitted events: {sorted(emitted_attrs)}"
        )
