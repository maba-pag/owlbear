"""Engine-internal Pydantic models for the native kanban engine.

BoardConfig  — schema for .owlbear/kanban/config.yml (accepts old and new schemas)
Task         — schema for task file frontmatter + markdown body
TaskSummary  — lightweight projection for list_tasks() results
Section      — parsed markdown section (heading + content)
ActivityEvent — one structured entry in activity.jsonl
ActivityCompactionResult — result of compact_activity_log()
SessionRecord — one agent work session derived from activity.jsonl
RepairOutcome — result of attempt_repair()
ConcurrencyError — raised when write_task_if_unchanged detects a stale version

Timestamps are stored as plain strings to avoid Go nanosecond → Python
microsecond precision drift on round-trips.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from owlbear_kanban import errors as _errors
from owlbear_kanban._duration import _parse_duration
from owlbear_kanban._naming import validate_config_path_containment

# Backward-compatible re-exports for existing imports from owlbear_kanban.models.
KANBAN_ERROR_CODES = _errors.KANBAN_ERROR_CODES
KanbanError = _errors.KanbanError
ValidationError = _errors.ValidationError
NotFoundError = _errors.NotFoundError
ConcurrencyError = _errors.ConcurrencyError
ConfigError = _errors.ConfigError
MigrationRequiredError = _errors.MigrationRequiredError


def _validate_status_and_priority(statuses: list[str], priorities: list[str]) -> None:
    if not statuses:
        raise ConfigError(
            code="ERR_INVALID_STATUS",
            user_message="config.statuses must contain at least one status",
        )
    if not priorities:
        raise ConfigError(
            code="ERR_INVALID_PRIORITY",
            user_message="config.priorities must contain at least one priority",
        )


def _validate_entry_and_terminal(statuses: list[str], entry_status: str, terminal_status: str) -> None:
    if entry_status not in statuses:
        raise ConfigError(
            code="ERR_ENTRY_STATUS_INVALID",
            user_message=f"entry_status {entry_status!r} must be one of statuses: {statuses}",
        )
    if terminal_status not in statuses or terminal_status != statuses[-1]:
        raise ConfigError(
            code="ERR_TERMINAL_STATUS_INVALID",
            user_message=(f"terminal_status {terminal_status!r} must equal statuses[-1] ({statuses[-1]!r})"),
        )


def _validate_agent_compatibility(compatibility: dict[str, Any]) -> None:
    compatibility_sets: dict[str, set[str]] = {}
    for agent, peers in compatibility.items():
        if not isinstance(peers, list):
            raise ConfigError(
                code="ERR_INVALID_STATUS",
                user_message=f"agent_compatibility[{agent!r}] must be a list[str]",
            )
        compatibility_sets[agent] = {str(peer) for peer in peers}

    for agent, peers in compatibility_sets.items():
        for peer in peers:
            reverse = compatibility_sets.get(peer)
            if reverse is None or agent not in reverse:
                raise ConfigError(
                    code="ERR_INVALID_STATUS",
                    user_message=(
                        f"agent_compatibility must be symmetric: {agent!r} -> {peer!r} requires {peer!r} -> {agent!r}"
                    ),
                )


class BoardInfo(BaseModel):
    """Board identity sub-section of legacy config.yml (board.name, etc.)."""

    model_config = ConfigDict(extra="allow")

    name: str


class BoardDefaults(BaseModel):
    """Default-values sub-section of legacy config.yml."""

    model_config = ConfigDict(extra="allow")

    status: str = "shape"
    priority: str = "medium"


class PathsConfig(BaseModel):
    """Grouped paths sub-model."""

    model_config = ConfigDict(extra="forbid")

    tasks_dir: str = "tasks"
    archive_dir: str = "archive"

    @field_validator("tasks_dir", "archive_dir")
    @classmethod
    def _validate_board_relative_paths(cls, value: str) -> str:
        validate_config_path_containment(value)
        return value


class PipelineConfig(BaseModel):
    """Grouped pipeline sub-model."""

    model_config = ConfigDict(extra="forbid")

    entry_status: str = "shape"
    terminal_status: str = "collect"
    statuses: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)
    wave_size: int = 4
    claim_timeout: str = "1h"
    default_priority: str = "medium"


class AgentsConfig(BaseModel):
    """Grouped agents sub-model."""

    model_config = ConfigDict(extra="forbid")

    agent_map: dict[str, Any] = Field(default_factory=dict)
    agent_types: dict[str, Any] = Field(default_factory=dict)
    agent_compatibility: dict[str, Any] = Field(default_factory=dict)


class PolicyConfig(BaseModel):
    """Grouped policy sub-model."""

    model_config = ConfigDict(extra="forbid")

    non_impl_tags: list[str] = Field(default_factory=list)
    archival_reasons: frozenset[str] = Field(
        default_factory=lambda: frozenset(
            {
                "completed",
                "deprecated",
                "dropped",
                "duplicate",
                "wontfix",
            }
        )
    )
    status_predicates: dict[str, Any] = Field(default_factory=dict)


class BoardConfig(BaseModel):
    """Schema for .owlbear/kanban/config.yml.

    Accepts three schema variants, all normalised before field assignment:

    - **Grouped** (canonical): ``schema: grouped`` with nested sub-model sections
      (``paths``, ``pipeline``, ``agents``, ``policy``).
    - **Flat** (transitional): string statuses with flat top-level keys such as
      ``tasks_dir``, ``entry_status``, and ``wave_size``.
    - **Legacy**: dict-based ``statuses`` list (``[{name: ...}]``) from the old
      board schema.

    A ``model_validator`` normalises all variants to the grouped shape before
    field assignment. Unknown/vendor fields are preserved via ``extra='allow'``.
    """

    model_config = ConfigDict(extra="allow")

    # Core fields — always present
    statuses: list[str]
    priorities: list[str]
    next_id: int = 1

    # Grouped schema fields
    paths: PathsConfig = Field(default_factory=PathsConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)

    # Legacy fields — kept for read access; not written in new schema
    defaults: BoardDefaults = Field(default_factory=BoardDefaults)
    activity_log: bool = True  # enabled by default for new-schema boards

    @model_validator(mode="before")
    @classmethod
    def _normalise_legacy(cls, data: object) -> object:  # noqa: C901, PLR0912, PLR0915
        """Convert legacy schema to new schema before field assignment.

        .. note:: Legacy migration path only.

           In production, ``config_loader.load_config`` constructs ``BoardConfig``
           from ``PRODUCT_TOPOLOGY`` constants, bypassing this validator entirely.
           This code is exercised only when loading pre-topology ``config.yml``
           files (migration) or calling ``BoardConfig.model_validate()`` directly.

        Root-level ``statuses`` and ``priorities`` are authoritative. In grouped
        config input, explicit ``pipeline.statuses``/``pipeline.priorities``
        must match root-level values; conflicts are rejected.
        """
        if not isinstance(data, dict):
            return data
        data = dict(data)

        grouped_keys = {"paths", "pipeline", "agents", "policy"}
        has_grouped_sections = any(key in data for key in grouped_keys)
        schema_value = data.get("schema")
        is_grouped_schema = schema_value == "grouped"

        if not is_grouped_schema and isinstance(data.get("pipeline"), dict):
            pipeline_claim_timeout = data["pipeline"].get("claim_timeout")
            if "claim_timeout" not in data and isinstance(pipeline_claim_timeout, str):
                data["claim_timeout"] = pipeline_claim_timeout

        if has_grouped_sections and not is_grouped_schema:
            grouped_section_names = {key for key in grouped_keys if key in data}
            pipeline_only_claim_timeout = (
                grouped_section_names == {"pipeline"}
                and isinstance(data.get("pipeline"), dict)
                and set(data["pipeline"].keys()) <= {"claim_timeout"}
            )
            if pipeline_only_claim_timeout:
                has_grouped_sections = False

        if has_grouped_sections and not is_grouped_schema:
            has_flat_keys = any(
                key in data
                for key in (
                    "tasks_dir",
                    "archive_dir",
                    "entry_status",
                    "terminal_status",
                    "wave_size",
                    "claim_timeout",
                    "default_priority",
                    "agent_map",
                    "agent_types",
                    "agent_compatibility",
                    "non_impl_tags",
                    "archival_reasons",
                    "status_predicates",
                )
            )
            if has_flat_keys:
                raise ConfigError(
                    code="ERR_INVALID_STATUS",
                    user_message=("config.yml mixes flat and grouped keys without schema: grouped"),
                )

        # Normalise statuses: [{name: ...}, ...] or [{name: ...}, ...] → [str, ...]
        raw_statuses = data.get("statuses")
        if isinstance(raw_statuses, list) and raw_statuses:
            first = raw_statuses[0]
            if isinstance(first, dict):
                data["statuses"] = [
                    s.get("name", next(iter(s.values()), str(s))) for s in raw_statuses if isinstance(s, dict)
                ]

        # Legacy passthrough keys are only synthesized for non-grouped input.
        defaults = data.get("defaults")
        if not is_grouped_schema:
            # Propagate legacy defaults → entry_status/default_priority
            if "entry_status" not in data and isinstance(defaults, dict):
                data["entry_status"] = defaults.get("status", "shape")
            if "default_priority" not in data and isinstance(defaults, dict):
                data["default_priority"] = defaults.get("priority", "medium")

            # Legacy boards often omit agent_map entirely; derive a permissive
            # status-complete map only in that case so explicit {} still fails.
            if "agent_map" not in data and ("version" in data or "board" in data or isinstance(defaults, dict)):
                statuses = data.get("statuses")
                if isinstance(statuses, list):
                    data["agent_map"] = {status: [] for status in statuses if isinstance(status, str)}

        if is_grouped_schema:
            paths = data.get("paths")
            if not isinstance(paths, dict):
                data["paths"] = {
                    "tasks_dir": data.get("tasks_dir", "tasks"),
                    "archive_dir": data.get("archive_dir", "archive"),
                }

            pipeline = data.get("pipeline")
            if not isinstance(pipeline, dict):
                data["pipeline"] = {
                    "entry_status": data.get("entry_status", "shape"),
                    "terminal_status": data.get("terminal_status", "collect"),
                    "statuses": data.get("statuses", []),
                    "priorities": data.get("priorities", []),
                    "wave_size": data.get("wave_size", 4),
                    "claim_timeout": data.get("claim_timeout", "1h"),
                    "default_priority": data.get("default_priority", "medium"),
                }
            else:
                had_pipeline_statuses = "statuses" in pipeline
                had_pipeline_priorities = "priorities" in pipeline
                pipeline.setdefault("statuses", data.get("statuses", []))
                pipeline.setdefault("priorities", data.get("priorities", []))

                root_statuses = data.get("statuses")
                if had_pipeline_statuses and pipeline.get("statuses") != root_statuses:
                    raise ConfigError(
                        code="ERR_CONFLICT_STATUS",
                        user_message=(
                            "config.pipeline.statuses conflicts with config.statuses: "
                            f"pipeline.statuses={pipeline.get('statuses')!r}, "
                            f"config.statuses={root_statuses!r}"
                        ),
                    )

                root_priorities = data.get("priorities")
                if had_pipeline_priorities and pipeline.get("priorities") != root_priorities:
                    raise ConfigError(
                        code="ERR_CONFLICT_STATUS",
                        user_message=(
                            "config.pipeline.priorities conflicts with config.priorities: "
                            f"pipeline.priorities={pipeline.get('priorities')!r}, "
                            f"config.priorities={root_priorities!r}"
                        ),
                    )

            agents = data.get("agents")
            if not isinstance(agents, dict):
                data["agents"] = {
                    "agent_map": data.get("agent_map", {}),
                    "agent_types": data.get("agent_types", {}),
                    "agent_compatibility": data.get("agent_compatibility", {}),
                }

            policy = data.get("policy")
            if not isinstance(policy, dict):
                data["policy"] = {
                    "non_impl_tags": data.get("non_impl_tags", []),
                    "archival_reasons": data.get(
                        "archival_reasons",
                        [
                            "completed",
                            "deprecated",
                            "dropped",
                            "duplicate",
                            "wontfix",
                        ],
                    ),
                    "status_predicates": data.get("status_predicates", {}),
                }
        else:
            data["paths"] = {
                "tasks_dir": data.get("tasks_dir", "tasks"),
                "archive_dir": data.get("archive_dir", "archive"),
            }
            data["pipeline"] = {
                "entry_status": data.get("entry_status", "shape"),
                "terminal_status": data.get("terminal_status", "collect"),
                "statuses": data.get("statuses", []),
                "priorities": data.get("priorities", []),
                "wave_size": data.get("wave_size", 4),
                "claim_timeout": data.get("claim_timeout", "1h"),
                "default_priority": data.get("default_priority", "medium"),
            }
            data["agents"] = {
                "agent_map": data.get("agent_map", {}),
                "agent_types": data.get("agent_types", {}),
                "agent_compatibility": data.get("agent_compatibility", {}),
            }
            data["policy"] = {
                "non_impl_tags": data.get("non_impl_tags", []),
                "archival_reasons": data.get(
                    "archival_reasons",
                    ["completed", "deprecated", "dropped", "duplicate", "wontfix"],
                ),
                "status_predicates": data.get("status_predicates", {}),
            }

        data.setdefault("schema", "grouped")

        # Legacy tasks_dir/archive_dir passthrough (already present in dict; just keep)
        return data

    @property
    def status_names(self) -> list[str]:
        """Return statuses as a list of plain strings."""
        return self.statuses

    @model_validator(mode="after")
    def _validate_semantics(self) -> BoardConfig:
        """Validate semantic invariants required by engine and direct model usage."""
        _validate_status_and_priority(self.statuses, self.priorities)
        _validate_entry_and_terminal(self.statuses, self.pipeline.entry_status, self.pipeline.terminal_status)
        _parse_duration(self.pipeline.claim_timeout)
        _validate_agent_compatibility(self.agents.agent_compatibility)

        return self


class Task(BaseModel):
    """Schema for a kanban task file — frontmatter fields plus markdown body.

    Timestamp fields (created, updated, claimed_at) are stored as ``str``
    to avoid Go 7-digit nanosecond → Python 6-digit microsecond truncation.

    Unknown YAML frontmatter keys (e.g. ``class``, ``started``,
    ``completed``) are preserved via extra='allow'.
    """

    model_config = ConfigDict(extra="allow")

    # Required fields
    id: int
    title: str
    status: str
    priority: str
    created: str
    updated: str
    # body can be str (raw markdown) or list[Section] (pre-parsed, Brief C in-memory)
    body: str | list = Field(default="")  # list[Section] when constructed with parsed sections

    # Standard optional fields
    tags: list[str] = Field(default_factory=list)
    parent: int | None = None
    depends_on: list[int] = Field(default_factory=list)
    ac: list[str] = Field(default_factory=list)
    proof_bundle: str | None = None
    blocked: bool = False
    block_reason: str | None = None

    # Claim field — Brief C uses claimed_at only
    claimed_at: str | None = None

    # Archive fields added in Brief C
    archival_reason: str | None = None
    archival_refs: list[int] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _drop_projection_only_fields(cls, data: object) -> object:
        """Remove projection-only fields that must never be stored on Task."""
        if isinstance(data, dict):
            data = dict(data)
            data.pop("dep_status", None)
        return data

    @field_validator("proof_bundle")
    @classmethod
    def _normalize_proof_bundle(cls, value: str | None) -> str | None:
        """Normalize proof bundle casing and canonical modifier ordering."""
        if value is None:
            return None
        parts = [part.strip().lower() for part in value.split("+") if part.strip()]
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0]

        base_rank = {
            "skip": 0,
            "existing": 1,
            "smoke": 2,
            "behavioral": 3,
            "critical": 4,
        }
        bundle_tokens = [part for part in parts if part in base_rank]
        if bundle_tokens:
            base = max(bundle_tokens, key=lambda token: base_rank[token])
            parts.remove(base)
        else:
            base = parts.pop(0)

        return "+".join([base, *sorted(parts)])


class TaskSummary(BaseModel):
    """Lightweight task summary for list operations.

    Excludes ``body`` and ``created`` from the full Task schema.
    ``claimed`` is derived from ``claimed_at`` and ``dep_status`` is a
    read-time projection from dependency state. Dict-style read access
    (``summary["field"]``) is supported for MCP serialisation consumers.
    """

    model_config = ConfigDict(extra="ignore")

    id: int
    title: str
    status: str
    priority: str
    updated: str
    tags: list[str] = Field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None
    claimed_at: str | None = None
    claimed: bool = False
    archival_reason: str | None = None
    archival_refs: list[int] = Field(default_factory=list)
    dep_status: str | None = None
    parent: int | None = None
    depends_on: list[int] = Field(default_factory=list)
    proof_bundle: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_claimed(cls, data: object) -> object:
        """Derive boolean claimed from claimed_at only.

        Brief-B projections drop claimed_by and compute claimed from the
        presence of claimed_at.
        """
        if isinstance(data, dict):
            data = dict(data)
            data.pop("claimed_by", None)
            claimed_at = data.get("claimed_at")
            data["claimed"] = claimed_at is not None
        return data

    def __getitem__(self, key: str) -> object:
        """Allow dict-style read access for MCP serialisation consumers."""
        return getattr(self, key)


# ---------------------------------------------------------------------------
# Storage types — Brief C additions
# ---------------------------------------------------------------------------


class Section(BaseModel):
    """One parsed section of a task body (heading + content)."""

    model_config = ConfigDict(frozen=True)

    heading: str | None
    level: int
    content: str


class ActivityEvent(BaseModel):
    """One structured entry in activity.jsonl."""

    model_config = ConfigDict(extra="allow")

    timestamp: str
    task_id: int | None = None
    action: str
    source: str
    detail: str
    # Optional: status of the task at time of claim event
    task_status_at_start: str | None = None


class ActivityCompactionResult(BaseModel):
    """Result of compact_activity_log()."""

    before_bytes: int
    after_bytes: int
    records_compacted: int


class SessionRecord(BaseModel):
    """One agent work session derived from activity.jsonl."""

    task_id: int | None
    task_status_at_start: str | None = None
    agent: str | None = None
    state: str
    started_at: str
    ended_at: str | None = None
    outcome: str | None = None
    duration: float | None = None
    duration_s: float | None = None


class RepairOutcome(BaseModel):
    """Result of attempt_repair() — one corrupt file's repair outcome."""

    task_id: int | None
    file_path: str
    code: str
    action: Literal["fixed", "quarantined", "failed"]
    detail: str | None = None


class CleanupResult(BaseModel):
    """Result of maintenance cleanup operations."""

    released_claim_ids: list[int] = Field(default_factory=list)
    archived_task_ids: list[int] = Field(default_factory=list)
    duplicate_removed_ids: list[int] = Field(default_factory=list)
    skipped_items: list[dict[str, str]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Engine projections — Brief B
# ---------------------------------------------------------------------------


class TaskFull(TaskSummary):
    """Full task projection returned by show/update operations."""

    created: str
    updated: str
    body: str | None = None
    ac: list[str] = Field(default_factory=list)


class DispatchEntry(BaseModel):
    """Dispatch projection for pick_tasks wave assignment."""

    model_config = ConfigDict(extra="ignore")

    id: int
    status: str
    priority: str
    title: str
    tags: list[str] = Field(default_factory=list)
    proof_bundle: str | None = None
    agent: str


class Wave(BaseModel):
    """One dispatch wave with zero-based index and selected tasks."""

    index: int
    tasks: list[DispatchEntry] = Field(default_factory=list)


class ListTasksResponse(BaseModel):
    """Envelope for list_tasks results."""

    tasks: list[TaskSummary]
    guidance: list[str]
    missing_ids: list[int] | None = None


class ShowTaskResponse(TaskFull):
    """Envelope for show_task results with section-miss diagnostics."""

    missing_sections: list[str] | None = None
    guidance: list[str]


class PickTasksResponse(BaseModel):
    """Envelope for pick_tasks results."""

    waves: list[Wave] = Field(default_factory=list)
    guidance: list[str]


class SingleTaskResponse(TaskFull):
    """Envelope for single-task mutation/read responses."""

    guidance: list[str] = Field(default_factory=list)
