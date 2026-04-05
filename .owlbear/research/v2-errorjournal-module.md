# v2 ErrorJournal Module Design Validation

> **Owning task:** #184 — Create v2 ErrorJournal module with append-only JSONL persistence
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #184 asks to port ErrorJournal to v2 as a standalone module with inline
JSONL persistence. v1 has a 126 LOC ErrorJournal inheriting from JsonlStore[T]
with 8-field ErrorEntry. The v2 port simplifies to 5 fields and removes the
base class dependency (YAGNI). This research validates the design, confirms
prior art alignment, and verifies the AC is implementation-ready.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | v1 ErrorJournal implementation | `v1/src/owlbear/memory/error_journal.py` | 1.0 |
| 2 | v1 JsonlStore[T] base class | `v1/src/owlbear/core/jsonl_store.py` | .90 |
| 3 | Pydantic TypeAdapter docs | <https://docs.pydantic.dev/latest/concepts/type_adapter/> | .90 |
| 4 | jsonlines library (JSONL patterns) | <https://jsonlines.readthedocs.io/en/latest/> | .70 |
| 5 | ErrorJournal-AcpClient wiring research | `docs/research/errorjournal-acpclient-wiring.md` | .95 |
| 6 | Orchestrator audit log research | `docs/research/orchestrator-audit-log.md` | .85 |
| 7 | JsonlStore base class research | `docs/research/jsonl-store-base-class.md` | .80 |
| 8 | ErrorJournal async-safety research | `docs/research/error-journal-async.md` | .75 |

## 3. Analysis

### 3.1 Field Simplification (v1 vs v2)

| Field | v1 ErrorEntry | v2 ErrorEntry (AC) | Rationale |
|-------|--------------|-------------------|-----------|
| `timestamp` | str | str | Keep — when the error occurred |
| `error_type` | str | Renamed `category` | Aligns with AcpClient's `ErrorCategory` enum values |
| `tool_name` | str | Renamed `method` | v2 consumer is AcpClient methods, not tools |
| `exception_message` | str | Renamed `message` | Shorter, clearer |
| `session_id` | str | str | Keep — correlates errors within a session |
| `action_taken` | str | Dropped | YAGNI — v2 AcpClient doesn't track actions |
| `attempt_number` | int | Dropped | YAGNI — retry tracking is caller's concern |
| `resolved` | bool | Dropped | YAGNI — no resolution tracking in v2 |

The 5-field model aligns with the `_ErrorLogger` Protocol in the wiring
research (Source 5 §3.3): `category`, `method`, `message` come from the
caller; `timestamp` and `session_id` are set by the journal.

### 3.2 Inline JSONL vs JsonlStore Base

| Criterion | Inline JSONL (.90) | JsonlStore[T] base (.60) |
|-----------|-------------------|-------------------------|
| New code | ~60 LOC (self-contained) | ~90 LOC (base + subclass) |
| KISS | High — no inheritance | Medium — generic base |
| YAGNI | High — 1 consumer today | Low — premature for 1 consumer |
| Future path | Extract base when 2nd store appears | Ready now |
| Precedent | Audit log #163 uses same approach | v1 used base class (3 consumers) |

Sources 5, 6, and 7 all converge on inline JSONL for v2: no JsonlStore base
until a second store actually exists. The audit log research (Source 6 §3.3)
reached the same conclusion independently.

### 3.3 Rotation Strategy

v1 uses 10,000 max entries; AC specifies 5,000 default. The approach is
identical: after each `log()`, check count; if over limit, load all entries,
keep last N, rewrite file. This is O(n) but runs only at the boundary — for
a 5,000-entry cap with single-line JSONL, the rewrite is sub-100ms on any
modern disk (Source 8 §2 confirms single-line writes are sub-ms).

### 3.4 Frozen Model Pattern

The audit log task (#163) uses `ConfigDict(frozen=True)` for its event models,
matching `voice/protocol.py`. ErrorEntry should follow the same pattern for
consistency — immutable records prevent accidental mutation after logging.

### 3.5 Dependencies

Pydantic is available transitively via `agent-client-protocol` (orchestrator's
only dependency). No new deps needed. `TypeAdapter` is the correct
serialization tool — create once in `__init__`, reuse in `log()` and `load()`
(Source 3 recommends this for performance).

### 3.6 Testing Strategy

| Test case | What it validates |
|-----------|------------------|
| `test_log_appends_entry` | Single entry round-trip via log() then load() |
| `test_load_empty_file` | Returns `[]` when file doesn't exist |
| `test_load_empty_existing_file` | Returns `[]` when file exists but is empty |
| `test_rotation_at_boundary` | At max+1 entries, file is trimmed to max |
| `test_rotation_preserves_recent` | After rotation, newest entries survive |
| `test_multiple_log_calls` | Entries accumulate across calls |

All tests use `tmp_path` fixture. No mocking needed — real file I/O is the
point. Coverage target: 100% of ErrorJournal methods.

## 4. Recommendation (.90 confidence)

**AC is implementation-ready.** The 5-field frozen Pydantic model with inline
JSONL persistence is the correct design for v2. Two refinements for the
architect/builder:

1. Use `ConfigDict(frozen=True)` on ErrorEntry (matches audit log pattern)
2. Use module-level `TypeAdapter[ErrorEntry]` (per Pydantic docs, create once)

**Risks:**

| Risk | Mitigation |
|------|------------|
| Code duplication with audit log JSONL logic | Extract JsonlStore[T] base when 3rd consumer appears |
| Rotation reads entire file synchronously | 5,000 entries ~ 500KB — acceptable per async-safety research |
| No query() method in AC | YAGNI — add when a consumer needs it |

## 5. Follow-up Tasks

No new tasks needed — #184 AC is complete and #148 (wiring) already exists
with dependency on #184. Task advances to backlog.
