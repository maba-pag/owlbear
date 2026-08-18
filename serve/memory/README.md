# owlbear-memory — Memory Primitives

Transport-free memory primitives for the OwlBear pipeline. Provides Pydantic models,
domain error types, and atomic file I/O for markdown-backed memory entries — no HTTP or
CLI dependency. Suitable for embedding in MCP servers and the Cockpit backend.

**Use this guide when:** you need to extend file-backed memory storage, entry lifecycle rules, or the
engine API used by MCP and Cockpit.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

---

## Launch / Usage

Import and use directly:

```python
from owlbear_memory import MemoryEngine, MemoryEntry, MemoryCategory, MemoryState
from owlbear_memory import NotFoundError, ConcurrencyError, ValidationError, TransitionError
from owlbear_memory.storage import read_entry, write_entry, delete_entry
from pathlib import Path

# High-level engine (recommended for most callers)
memory_dir = Path(".owlbear/memory")
engine = MemoryEngine(memory_dir)
entries = engine.get_entries()  # mtime-gated reload
entry = engine.save(
    title="My entry",
    content="...",
    categories=[MemoryCategory.DOMAIN_KNOWLEDGE],
    confidence=0.9,
    source_agent="builder",
    scope_agents=[],
)

# Low-level storage (use for direct file manipulation only)
entry_path = memory_dir / "my-entry.md"
entry = read_entry(entry_path)
write_entry(entry_path, entry, memory_dir=memory_dir)
delete_entry(entry_path, memory_dir=memory_dir)
```

---

## Configuration

The package reads no environment variables and has no standalone launch command. Pass the
workspace memory directory to `MemoryEngine` or the storage functions explicitly. Consumer
workspaces conventionally use `.owlbear/memory`; the directory is created when the engine first
starts or writes an entry. The `owlbear-memory-mcp` adapter owns MCP configuration and user-facing
lifecycle operations.

---

## Models

### `MemoryEntry`

Pydantic `BaseModel` representing a single markdown-backed memory entry.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | `str` | UUIDv4 string |
| `title` | `str` | Non-blank |
| `content` | `str` | Max 1024 characters |
| `categories` | `list[MemoryCategory]` | At least one required |
| `confidence` | `float` | Range 0.7–1.0 |
| `state` | `MemoryState` | Default: `pending` |
| `outstanding_count` | `int` | Default: `0`; incremented by assessment tool when entry was outstanding |
| `unremarkable_count` | `int` | Default: `0`; incremented by assessment tool when entry was unremarkable |
| `didnt_use_count` | `int` | Default: `0`; incremented by assessment tool when entry was skipped |
| `score` | `float` | Default: `0.0`; initialized to `confidence` on `save()` |
| `scope_agents` | `list[str]` | Default: `[]` |
| `source_agent` | `str` | Non-blank; frozen after creation |
| `created_at` | `str` | Timezone-aware ISO 8601 timestamp |
| `updated_at` | `str` | Timezone-aware ISO 8601 timestamp |
| `approved_at` | `str \| None` | Timezone-aware ISO 8601 timestamp; optional |
| `contested_by_task` | `str \| None` | Task ID that triggered the first factually-wrong confirmation; `None` until first confirmation; cleared on `resolve()` |

### `MemoryCategory` (StrEnum)

| Value | Meaning |
| --- | --- |
| `domain-knowledge` | Facts about a domain |
| `behaviour` | Agent behavioural norms |
| `pitfall` | Known failure modes or anti-patterns |
| `process` | Workflow or procedural knowledge |
| `tool-usage` | How to use a tool correctly |
| `goal` | Objectives the agent should pursue |
| `personality` | Tone or persona traits |
| `preference` | User or project preferences |
| `env-context` | Environmental or workspace context |

### `MemoryState` (StrEnum)

| Value | Meaning |
| --- | --- |
| `pending` | Newly created, awaiting curation |
| `curated` | Reviewed and refined |
| `approved` | Accepted for active use |
| `contested` | Under dispute; visible in recall; field edits preserve this state — use `resolve()` to return to approved |
| `disputed` | Challenged as incorrect; excluded from recall; field edits preserve this state — use `resolve()` to return to approved |
| `stale` | Flagged as potentially outdated; excluded from recall; field edits preserve this state — use `resolve()` to return to approved |
| `deleted` | Logically deleted (file may still exist) |

---

## Storage Primitives

All storage functions enforce path containment (resolved path must be within
`memory_dir`) and symlink rejection before any I/O.

### `read_entry(path: Path) -> MemoryEntry | None`

Reads one memory entry file. Returns `None` for any of:

- Symlink or non-existent file
- File larger than 8 192 bytes (`> 8KB`)
- YAML parse error or missing frontmatter
- Pydantic validation failure

Never raises on malformed input (lenient read contract).

### `write_entry(path: Path, entry: MemoryEntry | dict, *, memory_dir: Path) -> None`

Writes one memory entry file atomically:

1. Validates `entry` via Pydantic (strict — raises `PydanticValidationError` on failure)
2. Asserts path containment and rejects symlinks (raises `ValueError` on violation)
3. Writes content to a same-directory temp file via `mkstemp`, then replaces the target
   with `Path.replace()` (atomic on POSIX)

### `delete_entry(path: Path, *, memory_dir: Path) -> None`

Removes one memory entry file. Raises `NotFoundError` if the file does not exist.
Raises `ValueError` on containment or symlink violations.

---

## Error Types

| Exception | Raised when |
| --- | --- |
| `NotFoundError` | An entry file does not exist |
| `ConcurrencyError` | Optimistic concurrency validation fails (caller use) |
| `ValidationError` | User input or payload validation fails (caller use) |
| `TransitionError` | A memory state transition is not permitted (caller use) |

---

## Engine

### `MemoryEngine`

Orchestrates storage primitives with state-machine enforcement, optimistic concurrency
control (OCC), and mtime-based caching. This is the primary entry point for consumers
that need to read or mutate memory entries.

```python
engine = MemoryEngine(memory_dir)  # memory_dir created if absent
```

#### Scoring Constants

| Constant | Value | Meaning |
| --- | --- | --- |
| `OUTSTANDING_BOOST` | `0.1` | Score boost per outstanding assessment |
| `UNREMARKABLE_PENALTY` | `0.01` | Score penalty per unremarkable assessment |
| `STALE_THRESHOLD` | `50` | Total assessments above which an entry is considered stale |

#### `compute_score(confidence, outstanding_count, unremarkable_count) → float`

Computes a memory entry score:

```text
score = confidence + (outstanding_count × OUTSTANDING_BOOST) − (unremarkable_count × UNREMARKABLE_PENALTY)
```

Exported from the `owlbear_memory` package top-level.

#### `check_slot_efficiency(entry: MemoryEntry) → bool`

Returns `True` when `didnt_use` slots dominate assessed slots:

```text
entry.didnt_use_count > STALE_THRESHOLD × max(entry.outstanding_count + entry.unremarkable_count, 1)
```

Exported from the `owlbear_memory` package top-level. Used internally by `MemoryEngine.try_stale_transition`.

| Method | Signature | Notes |
| --- | --- | --- |
| `get_entries()` | `() → list[MemoryEntry]` | Reparsed only when directory mtime changes |
| `get_entry(id)` | `(str) → MemoryEntry` | Raises `NotFoundError` |
| `save(...)` | `(title, content, categories, confidence, source_agent, scope_agents) → MemoryEntry` | Creates pending entry; initializes `score = confidence`, all counters to `0`; no OCC |
| `approve(id, expected_updated_at)` | `(str, str) → MemoryEntry` | curated → approved; raises `TransitionError` / `ConcurrencyError` |
| `resolve(id, expected_updated_at)` | `(str, str) → MemoryEntry` | contested/disputed/stale → approved; sets `approved_at`; raises `TransitionError` / `ConcurrencyError` |
| `record_factually_wrong(id, task_id, expected_updated_at)` | `(str, str, str \| None) → MemoryEntry` | approved/curated → contested (stores `contested_by_task`, clears `approved_at`); contested + same `task_id` → no-op; contested + different `task_id` → disputed; raises `ValidationError` (empty/whitespace `task_id`), `TransitionError` (non-voteable state), `ConcurrencyError` (OCC mismatch, evaluated before state guard) |
| `record_assessment(entry_id, bucket, expected_updated_at)` | `(str, str, str \| None) → MemoryEntry` | Increments the specified counter (`outstanding`, `unremarkable`, or `didnt_use`); recomputes `score` via `compute_score`; calls `try_stale_transition` when slot-efficiency threshold exceeded. Raises `TransitionError` (non-voteable state), `ConcurrencyError` (OCC mismatch), `ValidationError` (invalid bucket). `expected_updated_at` optional — pass `None` to skip OCC check. |
| `edit(id, fields, expected_updated_at)` | `(str, EditPayload, str) → MemoryEntry` | State-machine rules apply; contested/disputed/stale preserve their state while fields are updated; deleted entries are blocked; raises `TransitionError` / `ConcurrencyError` |
| `delete(id, expected_updated_at)` | `(str, str) → MemoryEntry` | Hard-delete for pending, soft-delete for curated/approved/contested/disputed/stale; raises `TransitionError` / `ConcurrencyError` |
| `try_stale_transition(entry)` | `(MemoryEntry) → MemoryEntry` | Calls `check_slot_efficiency`; when True and state in {approved, curated, contested}, writes state=stale with refreshed updated_at. Returns unchanged entry (no error) when predicate is False or state is ineligible. No OCC. Logs INFO on transition. |
| `load()` | `() → list[MemoryEntry]` | Force full reparse; skips malformed files (lenient) |

#### State Machine

| From | Action | To | Notes |
| --- | --- | --- | --- |
| `pending` | `edit` (scope_agents non-empty) | `curated` | |
| `pending` | `edit` (scope_agents absent/empty) | `pending` | Field update only |
| `pending` | `delete` | (removed) | Hard-delete: file removed from disk |
| `curated` | `approve` | `approved` | Sets `approved_at` |
| `curated` | `edit` | `curated` | Field update only |
| `curated` | `delete` | `deleted` | Soft-delete |
| `approved` | `record_factually_wrong` | `contested` | Stores `contested_by_task`; clears `approved_at` |
| `curated` | `record_factually_wrong` | `contested` | Stores `contested_by_task` |
| `contested` | `record_factually_wrong` (same `task_id`) | `contested` | No-op; returns entry unchanged |
| `contested` | `record_factually_wrong` (different `task_id`) | `disputed` | Excluded from recall; clears `contested_by_task` |
| `approved` | `edit` | `curated` | Clears `approved_at` |
| `approved` | `delete` | `deleted` | Soft-delete |
| `contested` | `resolve` | `approved` | Sets `approved_at` |
| `disputed` | `resolve` | `approved` | Sets `approved_at` |
| `stale` | `resolve` | `approved` | Sets `approved_at`; resets only `didnt_use_count` to `0`; preserves other counters |
| `contested` | `delete` | `deleted` | Soft-delete |
| `disputed` | `delete` | `deleted` | Soft-delete |
| `stale` | `delete` | `deleted` | Soft-delete |
| `contested`/`disputed`/`stale` | `edit` | (unchanged) | Field update only; preserves the exceptional state |
| any | `approve`/`edit`/`delete` when `deleted` | — | Raises `TransitionError` |
| `approved`/`curated`/`contested` | `try_stale_transition` (auto) | `stale` | Fires when `check_slot_efficiency` returns True; no OCC |
| `stale`/`disputed`/`deleted`/`pending` | `try_stale_transition` | (unchanged) | Predicate False or ineligible state — no-op, no error |

#### OCC

All mutation methods (`approve`, `resolve`, `edit`, `delete`) accept `expected_updated_at` (str).
`record_factually_wrong` and `record_assessment` also accept `expected_updated_at` but it is optional (`str | None`); pass `None` to skip the OCC check.
If a non-`None` value does not match the on-disk `entry.updated_at`, `ConcurrencyError` is
raised. `save()` creates new entries and does not require an OCC token.

#### Lenient Read

`get_entries()` and `load()` skip unparseable files and track the count of skipped
files in `engine.parse_errors`. When duplicate UUIDs are found across files, the entry
with the later `updated_at` (parsed chronologically) is kept and a warning is logged.

### `MtimeScanCache`

Lightweight directory-mtime tracker. `has_changed()` returns `True` on first call and
whenever the directory `mtime_ns` differs from the last recorded value.

```python
cache = MtimeScanCache(memory_dir)
cache.has_changed()  # True (first call)
cache.has_changed()  # False (mtime unchanged)
```

---

## Dependencies

| Package | Purpose |
| --- | --- |
| `pydantic >= 2.13.4` | Model validation |
| `ruamel.yaml >= 0.19.1` | Safe YAML parsing for frontmatter |
