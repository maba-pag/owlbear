"""OwlBear application settings.

Uses pydantic-settings to load configuration from environment variables
(prefix ``OWLBEAR_``) with sensible defaults. Instantiate with
``OwlBearSettings()`` — no arguments required for local development.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings


class OwlBearSettings(BaseSettings):
    """Central configuration for the OwlBear daemon and CLI.

    All fields can be overridden via environment variables with the
    ``OWLBEAR_`` prefix. For example, ``OWLBEAR_DEBUG=true`` enables
    debug mode.
    """

    model_config = {"env_prefix": "OWLBEAR_"}

    # --- LLM provider ---
    provider: Literal["copilot"] = Field(
        default="copilot",
        description="LLM provider backend. Currently only 'copilot' is supported.",
    )
    copilot_token_path: Path = Field(
        default=Path.home() / ".owlbear" / "copilot_token.json",
        description="Path to the cached GitHub Copilot OAuth token JSON file.",
    )
    copilot_base_url: str = Field(
        default="https://api.individual.githubcopilot.com",
        description="Base URL for the GitHub Copilot API.",
    )
    chat_model: str = Field(
        default="gpt-4o",
        description="Model identifier sent to the LLM provider for chat completions.",
    )

    # --- Directories ---
    config_dir: Path = Field(
        default=Path.home() / ".owlbear",
        description="Root directory for OwlBear configuration and state files.",
    )
    agents_dir: Path = Field(
        default=Path(__file__).parent / "agents",
        description="Directory containing agent definition YAML files.",
    )
    project_root: Path = Field(
        default=Path.home() / "projects",
        description="Root directory under which new projects are scaffolded.",
    )

    # --- Slack ---
    slack_app_token: SecretStr | None = Field(
        default=None,
        description=(
            "Slack app-level token (xapp-...) for Socket Mode."
            " All three Slack fields must be set together."
        ),
    )
    slack_bot_token: SecretStr | None = Field(
        default=None,
        description=(
            "Slack bot user OAuth token (xoxb-...). All three Slack fields must be set together."
        ),
    )
    slack_channel_id: str | None = Field(
        default=None,
        description=(
            "Slack channel ID to post messages to. All three Slack fields must be set together."
        ),
    )

    # --- Knowledge ---
    knowledge_db_path: Path = Field(
        default=Path.home() / ".owlbear" / "knowledge.db",
        description="Path to the SQLite knowledge graph database.",
    )
    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="HuggingFace model identifier for text embeddings.",
    )
    knowledge_context_tokens: int = Field(
        default=2000,
        description="Token budget for per-turn knowledge context injection. Must be > 0.",
    )

    # --- Usage tracking ---
    usage_path: Path = Field(
        default=Path.home() / ".owlbear" / "usage.jsonl",
        description="Path to the JSONL file for LLM usage tracking.",
    )

    # --- Notifications ---
    notification_events: list[str] = Field(
        default=["task_complete", "question_pending", "on_error"],
        description="Event names that trigger user notifications.",
    )
    notification_backends: list[str] = Field(
        default=["bell", "sound"],
        description="Notification delivery backends in priority order.",
    )

    # --- GitHub ---
    github_token: SecretStr | None = Field(
        default=None,
        description="GitHub personal access token for API operations.",
    )
    github_owner: str | None = Field(
        default=None,
        description="GitHub repository owner (user or org) for API operations.",
    )
    github_repo: str | None = Field(
        default=None,
        description="GitHub repository name for API operations.",
    )

    # --- Observability ---
    otel_endpoint: str | None = Field(
        default=None,
        description="OpenTelemetry collector endpoint URL. None disables tracing export.",
    )

    # --- Embedding ---
    embedding_idle_timeout: int = Field(
        default=600,
        description=(
            "Seconds of inactivity before the embedding model is unloaded from memory. >= 0."
        ),
    )

    # --- Knowledge graph ---
    knowledge_graph_expansion: bool = Field(
        default=True,
        description="Enable graph-neighbor expansion in knowledge retrieval results.",
    )
    inter_doc_graph_building: bool = Field(
        default=False,
        description="Enable cross-document edge inference via embedding similarity and LLM.",
    )

    # --- Temporal memory ---
    temporal_decay_rate: float = Field(
        default=0.001,
        description=(
            "Exponential decay rate for temporal memory scoring. Higher values decay faster. >= 0."
        ),
    )
    temporal_recency_weight: float = Field(
        default=0.1,
        description="Weight of recency score in temporal memory ranking. 0.0-1.0.",
    )

    # --- MCP servers ---
    mcp_servers: dict[str, dict[str, Any]] | None = Field(
        default=None,
        description="MCP server configurations keyed by server name. None disables MCP.",
    )

    # --- Approval gates ---
    approval_policy: list[dict[str, Any]] = Field(
        default=[
            {"tool_name": "git_push"},
            {"tool_name": "create_pr"},
            {"tool_name": "deploy"},
            {"tool_name": "run_command"},
        ],
        description="List of tool-name patterns that require user approval before execution.",
    )
    approval_timeout: float = Field(
        default=120.0,
        description="Seconds to wait for user approval before timing out. > 0.",
    )

    # --- Progress reporting ---
    progress_enabled: bool = Field(
        default=True,
        description="Enable periodic progress reports during long-running agent tasks.",
    )
    progress_interval: float = Field(
        default=30.0,
        description="Seconds between progress reports. Must be > 0.",
    )
    progress_detail: Literal["brief", "detailed"] = Field(
        default="brief",
        description="Level of detail in progress reports: 'brief' or 'detailed'.",
    )

    # --- Browser / screenshots ---
    screenshot_mode: Literal["auto", "manual", "on_error"] = Field(
        default="on_error",
        description="When to capture browser screenshots: 'auto', 'manual', or 'on_error'.",
    )

    # --- Diagrams (Kroki) ---
    kroki_server_url: str = Field(
        default="https://kroki.io",
        description="Base URL of the Kroki diagram rendering server.",
    )

    # --- Autonomous mode ---
    autonomous_mode: bool = Field(
        default=False,
        description="Enable autonomous poll-dispatch-reconcile loop alongside the channel loop.",
    )
    poll_interval: float = Field(
        default=30.0,
        description="Seconds between poll ticks in autonomous mode. Must be > 0.",
    )
    max_concurrent_tasks: int = Field(
        default=3,
        description="Maximum concurrent autonomous tasks. Must be > 0.",
    )

    # --- Context condenser ---
    condenser_enabled: bool = Field(
        default=False,
        description="Enable LLM-summarizing context condenser for long conversations.",
    )
    condenser_max_events: int = Field(
        default=120,
        description="Message count threshold that triggers context condensation.",
    )

    # --- Heartbeat ---
    heartbeat_enabled: bool = Field(
        default=False,
        description="Enable proactive heartbeat wakeups via HEARTBEAT.md.",
    )
    heartbeat_interval: int = Field(
        default=1800,
        description="Seconds between heartbeat ticks. Must be > 0.",
    )
    heartbeat_active_hours: tuple[int, int] = Field(
        default=(8, 22),
        description="UTC hour window (start, end) for heartbeat ticks.",
    )

    # --- Runtime ---
    debug: bool = Field(
        default=False,
        description="Enable debug mode with verbose logging.",
    )

    @field_validator("heartbeat_interval")
    @classmethod
    def _validate_heartbeat_interval(cls, v: int) -> int:
        """heartbeat_interval must be strictly positive."""
        if v <= 0:
            msg = "heartbeat_interval must be greater than 0"
            raise ValueError(msg)
        return v

    @field_validator("poll_interval")
    @classmethod
    def _validate_poll_interval(cls, v: float) -> float:
        """poll_interval must be strictly positive."""
        if v <= 0:
            msg = "poll_interval must be greater than 0"
            raise ValueError(msg)
        return v

    @field_validator("max_concurrent_tasks")
    @classmethod
    def _validate_max_concurrent_tasks(cls, v: int) -> int:
        """max_concurrent_tasks must be strictly positive."""
        if v <= 0:
            msg = "max_concurrent_tasks must be greater than 0"
            raise ValueError(msg)
        return v

    @field_validator("progress_interval")
    @classmethod
    def _validate_progress_interval(cls, v: float) -> float:
        """progress_interval must be strictly positive."""
        if v <= 0:
            msg = "progress_interval must be greater than 0"
            raise ValueError(msg)
        return v

    @field_validator("knowledge_context_tokens")
    @classmethod
    def _validate_knowledge_context_tokens(cls, v: int) -> int:
        """knowledge_context_tokens must be strictly positive."""
        if v <= 0:
            msg = "knowledge_context_tokens must be greater than 0"
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
