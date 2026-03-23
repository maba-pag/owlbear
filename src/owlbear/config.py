"""OwlBear application settings.

Uses pydantic-settings to load configuration from environment variables
(prefix ``OWLBEAR_``) with sensible defaults. Instantiate with
``OwlBearSettings()`` — no arguments required for local development.
"""

from __future__ import annotations

import dataclasses
import functools
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, SecretStr, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings

from owlbear.core.hook_reaction_router import HookReactionRule  # noqa: TC001

if TYPE_CHECKING:
    from collections.abc import Sequence


_MAX_PORT = 65535


class BrowserConfig(BaseModel, frozen=True):
    """Configuration for the browser automation tool.

    Attributes:
        allowed_urls: Regex patterns for URLs the browser may navigate to.
            An empty list means *all* URLs are allowed (subject to blocklist).
        blocked_urls: Regex patterns for URLs the browser must never visit.
        headless: Whether to launch the browser without a visible window.
        viewport: ``(width, height)`` in pixels.  Both must be positive.
        timeout_ms: Navigation timeout in milliseconds.  Must be >= 0.
        cdp_endpoint: CDP HTTP endpoint URL (localhost/127.0.0.1 only).
        cdp_port: Default CDP debugging port (1-65535).
        browser_executable: Override path for the browser binary.
        auto_launch: Whether to auto-launch browser if CDP unavailable.
        content_scan_mode: Content injection scan mode (``'strict'``,
            ``'warn'``, or ``'off'``).  Default ``'warn'``.
        profile_name: Optional name for a cookie-persistence profile.
            Must be set together with *profile_dir* or both left ``None``.
        profile_dir: Optional directory where cookie profile JSON files
            are stored.  Must be set together with *profile_name* or both
            left ``None``.
    """

    allowed_urls: list[str] = []
    blocked_urls: list[str] = []
    headless: bool = False
    viewport: tuple[int, int] = (1280, 720)
    timeout_ms: int = 30_000
    cdp_endpoint: str | None = None
    cdp_port: int = 9222
    browser_executable: str | None = None
    auto_launch: bool = True
    content_scan_mode: Literal["strict", "warn", "off"] = "warn"
    profile_name: str | None = None
    profile_dir: Path | None = None

    # --- validators ---

    @field_validator("allowed_urls", "blocked_urls", mode="before")
    @classmethod
    def _validate_regex_patterns(cls, patterns: list[str], info: object) -> list[str]:
        """Ensure every pattern is a compilable regular expression."""
        for idx, pattern in enumerate(patterns):
            try:
                re.compile(pattern)
            except re.error as exc:
                field = getattr(info, "field_name", "urls")
                msg = f"Item {idx} in {field} is not a valid regex: {exc}"
                raise ValueError(msg) from exc
        return patterns

    @field_validator("timeout_ms", mode="after")
    @classmethod
    def _timeout_non_negative(cls, value: int) -> int:
        """Timeout must be zero or positive."""
        if value < 0:
            msg = "timeout_ms must be >= 0"
            raise ValueError(msg)
        return value

    @field_validator("cdp_endpoint", mode="after")
    @classmethod
    def _cdp_endpoint_localhost_only(cls, value: str | None) -> str | None:
        """CDP endpoint must be http://localhost or http://127.0.0.1."""
        if value is None:
            return value
        try:
            parsed = urlparse(value)
        except Exception as exc:
            msg = "cdp_endpoint is not a valid URL"
            raise ValueError(msg) from exc
        if parsed.scheme != "http":
            msg = "cdp_endpoint must use http:// scheme"
            raise ValueError(msg)
        if parsed.hostname not in ("localhost", "127.0.0.1"):
            msg = "cdp_endpoint must target localhost or 127.0.0.1"
            raise ValueError(msg)
        return value

    @field_validator("cdp_port", mode="after")
    @classmethod
    def _cdp_port_valid_range(cls, value: int) -> int:
        """CDP port must be between 1 and 65535 inclusive."""
        if not (1 <= value <= _MAX_PORT):
            msg = f"cdp_port must be between 1 and {_MAX_PORT}"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _viewport_positive(self) -> BrowserConfig:
        """Both viewport dimensions must be strictly positive."""
        w, h = self.viewport
        if w <= 0 or h <= 0:
            msg = "viewport width and height must be positive integers"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _profile_both_or_neither(self) -> BrowserConfig:
        """profile_name and profile_dir must both be set or both be None."""
        if (self.profile_name is None) != (self.profile_dir is None):
            msg = "profile_name and profile_dir must both be set or both be None"
            raise ValueError(msg)
        return self


@dataclasses.dataclass(frozen=True)
class RigorProfile:
    """Quality-vs-speed preset for agent task execution."""

    review_enabled: bool
    tdd_depth: Literal["full", "smoke", "none"]
    turn_budget: int


RIGOR_LEAN = RigorProfile(review_enabled=False, tdd_depth="smoke", turn_budget=15)
RIGOR_STANDARD = RigorProfile(review_enabled=True, tdd_depth="full", turn_budget=30)
RIGOR_THOROUGH = RigorProfile(review_enabled=True, tdd_depth="full", turn_budget=50)


class OwlBearSettings(BaseSettings):
    """Central configuration for the OwlBear daemon and CLI.

    All fields can be overridden via environment variables with the
    ``OWLBEAR_`` prefix. For example, ``OWLBEAR_DEBUG=true`` enables
    debug mode. Nested models use the ``__`` delimiter, e.g.
    ``OWLBEAR_BROWSER__HEADLESS=true`` sets ``settings.browser.headless``.
    """

    model_config = {
        "env_prefix": "OWLBEAR_",
        "env_nested_delimiter": "__",
        "nested_model_default_partial_update": True,
    }

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
    slack_allowed_user_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Slack user IDs allowed to interact with the bot."
            " Empty list (default) allows all senders."
        ),
    )
    slack_rate_limit_per_minute: int = Field(
        default=30,
        description=(
            "Maximum messages accepted per user per minute via Slack. 0 disables rate limiting."
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
        default=["task_complete", "on_error"],
        description="Event names that trigger user notifications.",
    )
    notification_backends: list[str] = Field(
        default=["bell", "sound"],
        description="Notification delivery backends in priority order.",
    )
    hook_reactions: list[HookReactionRule] = Field(
        default=[],
        description="Ordered list of hook reaction rules (events, match, actions).",
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
        ge=0,
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
    ingest_bg_concurrency: int = Field(
        default=5,
        description="Maximum concurrent background graph-enrichment tasks per ingest pipeline.",
    )

    # --- Temporal memory ---
    temporal_decay_rate: float = Field(
        default=0.001,
        ge=0.0,
        le=1.0,
        description=(
            "Exponential decay rate for temporal memory scoring. Higher values decay faster. >= 0."
        ),
    )
    temporal_recency_weight: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
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
        gt=0.0,
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
    browser: BrowserConfig = Field(
        default_factory=BrowserConfig,
        description="Nested browser configuration (BrowserConfig model).",
    )
    screenshot_mode: Literal["auto", "manual", "on_error"] = Field(
        default="on_error",
        description="When to capture browser screenshots: 'auto', 'manual', or 'on_error'.",
    )

    # --- Content safety ---
    wrap_web_content: bool = Field(
        default=True,
        description=(
            "Wrap web-fetched content in <untrusted_web_content> sentinel tags. "
            "Security-on by default; disable only for trusted sources."
        ),
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
    stale_task_timeout: float = Field(
        default=300.0,
        description=(
            "Seconds before an in-progress task is considered stale"
            " and auto-cancelled. Must be > 0."
        ),
    )
    task_retry_max_attempts: int = Field(
        default=5,
        description="Maximum retry attempts per task before blocking. Must be > 0.",
    )
    task_retry_backoff_base: float = Field(
        default=10.0,
        description="Base delay (seconds) for exponential backoff. Must be > 0.",
    )
    task_retry_backoff_max: float = Field(
        default=320.0,
        description="Maximum backoff delay (seconds). Must be > 0.",
    )
    lint_gate_enabled: bool = Field(
        default=True,
        description=(
            "Quality gate: run ruff after builder completion. "
            "Defaults to True (quality gate, not feature flag — "
            "see architecture-standards config section)."
        ),
    )

    # --- Board context ---
    board_context_enabled: bool = Field(
        default=True,
        description="Inject kanban board state into agent turn instructions.",
    )

    # --- Startup summary ---
    log_startup_summary: bool = Field(
        default=True,
        description="Send startup summary to channel after bootstrap completes.",
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

    # --- Consolidation ---
    consolidation_enabled: bool = Field(
        default=False,
        description="Enable periodic cross-document insight consolidation (feature-flagged off).",
    )
    consolidation_interval: int = Field(
        default=1800,
        description="Seconds between consolidation ticks. Must be > 0.",
    )

    # --- Session memory ---
    session_memory_enabled: bool = Field(
        default=False,
        description=(
            "Persist an LLM-generated session summary to .owlbear/session-memory.md on session end."
        ),
    )

    # --- Lessons injection ---
    lessons_injection_enabled: bool = Field(
        default=False,
        description=(
            "Inject curated lessons from .owlbear/lessons/ into agent context on session start."
        ),
    )

    # --- Pre-hydration ---
    prehydration_enabled: bool = Field(
        default=False,
        description=(
            "Enable context pre-hydration for agent dispatch "
            "(fetch URLs and read files from task body)."
        ),
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

    # --- Rigor profiles ---
    rigor_profiles: dict[str, RigorProfile] = Field(
        default={
            "lean": RIGOR_LEAN,
            "standard": RIGOR_STANDARD,
            "thorough": RIGOR_THOROUGH,
        },
        description="Named quality-vs-speed presets for agent task execution.",
    )
    default_rigor: str = Field(
        default="standard",
        description="Default rigor profile key. Must exist in rigor_profiles.",
    )

    # --- Budget ---
    budget_limit_usd: float | None = Field(
        default=None,
        description="Maximum USD spend before raising BudgetExceededError. None = unlimited.",
    )

    # --- Runtime ---
    debug: bool = Field(
        default=False,
        description="Enable debug mode with verbose logging.",
    )

    @field_validator("budget_limit_usd")
    @classmethod
    def _validate_budget_limit_usd(cls, v: float | None) -> float | None:
        """budget_limit_usd must be strictly positive when set."""
        if v is not None and v <= 0:
            msg = "budget_limit_usd must be greater than 0"
            raise ValueError(msg)
        return v

    @field_validator("default_rigor")
    @classmethod
    def _validate_default_rigor(cls, v: str, info: ValidationInfo) -> str:
        """default_rigor must be a key in rigor_profiles."""
        profiles = info.data.get("rigor_profiles")
        if profiles is not None and v not in profiles:
            msg = f"default_rigor {v!r} not found in rigor_profiles keys: {sorted(profiles)}"
            raise ValueError(msg)
        return v

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

    @field_validator("stale_task_timeout")
    @classmethod
    def _validate_stale_task_timeout(cls, v: float) -> float:
        """stale_task_timeout must be strictly positive."""
        if v <= 0:
            msg = "stale_task_timeout must be greater than 0"
            raise ValueError(msg)
        return v

    @field_validator("task_retry_max_attempts")
    @classmethod
    def _validate_task_retry_max_attempts(cls, v: int) -> int:
        """task_retry_max_attempts must be strictly positive."""
        if v <= 0:
            msg = "task_retry_max_attempts must be greater than 0"
            raise ValueError(msg)
        return v

    @field_validator("task_retry_backoff_base")
    @classmethod
    def _validate_task_retry_backoff_base(cls, v: float) -> float:
        """task_retry_backoff_base must be strictly positive."""
        if v <= 0:
            msg = "task_retry_backoff_base must be greater than 0"
            raise ValueError(msg)
        return v

    @field_validator("task_retry_backoff_max")
    @classmethod
    def _validate_task_retry_backoff_max(cls, v: float) -> float:
        """task_retry_backoff_max must be strictly positive."""
        if v <= 0:
            msg = "task_retry_backoff_max must be greater than 0"
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

    @field_validator("ingest_bg_concurrency")
    @classmethod
    def _validate_ingest_bg_concurrency(cls, v: int) -> int:
        """ingest_bg_concurrency must be strictly positive."""
        if v < 1:
            msg = "ingest_bg_concurrency must be >= 1"
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


@functools.cache
def get_settings() -> OwlBearSettings:
    """Return the cached :class:`OwlBearSettings` singleton.

    Uses :func:`functools.cache` so repeated calls return the same instance.
    Call ``get_settings.cache_clear()`` to force a fresh instance on the
    next invocation (useful in tests or after environment changes).
    """
    return OwlBearSettings()


def resolve_rigor_profile(
    settings: OwlBearSettings,
    task_tags: Sequence[str],
) -> RigorProfile:
    """Resolve a rigor profile from task tags.

    Extracts the first ``rigor:*`` tag and returns the matching profile
    from ``settings.rigor_profiles``. Falls back to the default profile.
    """
    for tag in task_tags:
        if tag.startswith("rigor:"):
            key = tag[len("rigor:") :]
            if key in settings.rigor_profiles:
                return settings.rigor_profiles[key]
    return settings.rigor_profiles[settings.default_rigor]
