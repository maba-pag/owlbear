"""OwlBear application settings.

Uses pydantic-settings to load configuration from environment variables
(prefix ``OWLBEAR_``) with sensible defaults. Instantiate with
``OwlBearSettings()`` — no arguments required for local development.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings


class OwlBearSettings(BaseSettings):
    """Central configuration for the OwlBear daemon and CLI.

    All fields can be overridden via environment variables with the
    ``OWLBEAR_`` prefix. For example, ``OWLBEAR_DEBUG=true`` enables
    debug mode.
    """

    model_config = {"env_prefix": "OWLBEAR_"}

    # --- LLM provider ---
    provider: Literal["copilot"] = "copilot"
    copilot_token_path: Path = Path.home() / ".owlbear" / "copilot_token.json"
    copilot_base_url: str = "https://api.individual.githubcopilot.com"
    chat_model: str = "gpt-4o"

    # --- Directories ---
    config_dir: Path = Path.home() / ".owlbear"

    # --- Slack ---
    slack_app_token: SecretStr | None = None
    slack_bot_token: SecretStr | None = None
    slack_channel_id: str | None = None

    # --- Runtime ---
    debug: bool = False

    @model_validator(mode="after")
    def _validate_slack_all_or_nothing(self) -> OwlBearSettings:
        """If any Slack field is set, all three must be set."""
        fields = {
            "slack_app_token": self.slack_app_token,
            "slack_bot_token": self.slack_bot_token,
            "slack_channel_id": self.slack_channel_id,
        }
        set_fields = {k for k, v in fields.items() if v is not None}
        if set_fields and set_fields != set(fields):
            missing = set(fields) - set_fields
            msg = (
                f"Slack configuration is incomplete — set all three fields or none. "
                f"Missing: {', '.join(sorted(missing))}"
            )
            raise ValueError(msg)
        return self
