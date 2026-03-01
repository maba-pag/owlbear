"""OwlBear application settings.

Uses pydantic-settings to load configuration from environment variables
(prefix ``OWLBEAR_``) with sensible defaults. Instantiate with
``OwlBearSettings()`` — no arguments required for local development.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import SecretStr, field_validator, model_validator
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
    agents_dir: Path = Path(__file__).parent / "agents"

    # --- Slack ---
    slack_app_token: SecretStr | None = None
    slack_bot_token: SecretStr | None = None
    slack_channel_id: str | None = None

    # --- Knowledge ---
    knowledge_db_path: Path = Path.home() / ".owlbear" / "knowledge.db"
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # --- Usage tracking ---
    usage_path: Path = Path.home() / ".owlbear" / "usage.jsonl"

    # --- Notifications ---
    notification_events: list[str] = ["task_complete", "question_pending", "on_error"]
    notification_backends: list[str] = ["bell", "sound"]

    # --- GitHub ---
    github_token: SecretStr | None = None
    github_owner: str | None = None
    github_repo: str | None = None

    # --- Observability ---
    otel_endpoint: str | None = None

    # --- Embedding ---
    embedding_idle_timeout: int = 600

    # --- Temporal memory ---
    temporal_decay_rate: float = 0.001
    temporal_recency_weight: float = 0.1

    # --- MCP servers ---
    mcp_servers: dict[str, dict[str, Any]] | None = None

    # --- Approval gates ---
    approval_policy: list[dict[str, Any]] = [
        {"tool_name": "git_push"},
        {"tool_name": "create_pr"},
        {"tool_name": "deploy"},
    ]
    approval_timeout: float = 120.0

    # --- Progress reporting ---
    progress_enabled: bool = True
    progress_interval: float = 30.0
    progress_detail: Literal["brief", "detailed"] = "brief"

    # --- Runtime ---
    debug: bool = False

    @field_validator("progress_interval")
    @classmethod
    def _validate_progress_interval(cls, v: float) -> float:
        """progress_interval must be strictly positive."""
        if v <= 0:
            msg = "progress_interval must be greater than 0"
            raise ValueError(msg)
        return v

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
