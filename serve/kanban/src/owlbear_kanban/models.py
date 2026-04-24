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

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_kanban import errors as _errors

# Backward-compatible re-exports for existing imports from owlbear_kanban.models.
KANBAN_ERROR_CODES = _errors.KANBAN_ERROR_CODES
KanbanError = _errors.KanbanError
ValidationError = _errors.ValidationError
NotFoundError = _errors.NotFoundError
ConcurrencyError = _errors.ConcurrencyError
ConfigError = _errors.ConfigError
MigrationRequiredError = _errors.MigrationRequiredError


class BoardInfo(BaseModel):
    """Board identity sub-section of legacy config.yml (board.name, etc.)."""

    model_config = ConfigDict(extra="allow")

    name: str


class BoardDefaults(BaseModel):
    """Default-values sub-section of legacy config.yml."""

    model_config = ConfigDict(extra="allow")

    status: str = "research"
    priority: str = "important"


class BoardConfig(BaseModel):
    """Schema for .owlbear/kanban/config.yml.

    Accepts both the legacy schema (version/board/tasks_dir/statuses as list[dict])
    and the new Brief-C schema (flat statuses as list[str], entry_status, wave_size,
    etc.). A ``model_validator`` normalises legacy data to the new shape before
    field assignment. Unknown/vendor fields are preserved via extra='allow'.
    """

    model_config = ConfigDict(extra="allow")

    # Core fields — always present
    statuses: list[str]
    priorities: list[str]
    claim_timeout: str = "1h"
    next_id: int = 1

    # Directory layout — defaults cover new-schema boards; set from legacy schema
    tasks_dir: str = "tasks"
    archive_dir: str = "archive"

    # New schema fields
    entry_status: str = "research"
    wave_size: int = 4
    agent_map: dict[str, Any] = Field(default_factory=dict)
    agent_types: dict[str, Any] = Field(default_factory=dict)
    agent_compatibility: dict[str, Any] = Field(default_factory=dict)
    non_impl_tags: list[str] = Field(default_factory=list)
    archival_reasons: list[str] = Field(
        default_factory=lambda: [
            "completed",
            "deprecated",
            "dropped",
            "duplicate",
            "wontfix",
        ]
    )
    status_predicates: dict[str, Any] = Field(default_factory=dict)

    # Legacy fields — kept for read access; not written in new schema
    defaults: BoardDefaults = Field(default_factory=BoardDefaults)
    activity_log: bool = True  # enabled by default for new-schema boards

    @model_validator(mode="before")
    @classmethod
    def _normalise_legacy(cls, data: object) -> object:
        """Convert legacy schema to new schema before field assignment."""
        if not isinstance(data, dict):
            return data
        data = dict(data)

        # Normalise statuses: [{name: ...}, ...] or [{name: ...}, ...] → [str, ...]
        raw_statuses = data.get("statuses")
        if isinstance(raw_statuses, list) and raw_statuses:
            first = raw_statuses[0]
            if isinstance(first, dict):
                data["statuses"] = [
                    s.get("name", next(iter(s.values()), str(s)))
                    for s in raw_statuses
                    if isinstance(s, dict)
                ]

        # Propagate legacy defaults → entry_status
        defaults = data.get("defaults")
        if "entry_status" not in data and isinstance(defaults, dict):
            data["entry_status"] = defaults.get("status", "research")

        # Legacy tasks_dir/archive_dir passthrough (already present in dict; just keep)
        return data

    @property
    def status_names(self) -> list[str]:
        """Return statuses as a list of plain strings."""
        return self.statuses


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
    body: str | list = Field(
        default=""
    )  # list[Section] when constructed with parsed sections

    # Standard optional fields
    tags: list[str] = Field(default_factory=list)
    parent: int | None = None
    depends_on: list[int] = Field(default_factory=list)
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


class TaskSummary(BaseModel):
    """Lightweight task summary for list operations.

    Excludes ``body``, ``created``, and ``updated`` from the full Task schema.
    ``claimed`` is derived from ``claimed_at`` and ``dep_status`` is a
    read-time projection from dependency state. Dict-style read access
    (``summary["field"]``) is supported for MCP serialisation consumers.
    """

    model_config = ConfigDict(extra="ignore")

    id: int
    title: str
    status: str
    priority: str
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


# ---------------------------------------------------------------------------
# Engine projections — Brief B
# ---------------------------------------------------------------------------


class TaskFull(TaskSummary):
    """Full task projection returned by show/update operations."""

    created: str
    updated: str
    body: str | None = None


class DispatchEntry(BaseModel):
    """Dispatch projection for pick_tasks wave assignment."""

    model_config = ConfigDict(extra="ignore")

    id: int
    status: str
    priority: str
    title: str
    tags: list[str] = Field(default_factory=list)
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
