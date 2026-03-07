# Error Journal Dedup Key Research

> **Owning task:** #567 — Add dedup key to ErrorJournal entries
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

`ErrorJournal.log()` is append-only JSONL. When the daemon retries a
transient error (up to 3 attempts), `_recover_from_error` calls
`_log_to_journal` on each attempt, producing near-identical entries that
differ only in `attempt_number` and `action_taken`. The audit (I-3) flags
this as a minor issue since the journal is not yet wired into agent
learning. Question: how should we prevent duplicate entries?

Current `ErrorEntry` schema: `timestamp`, `error_type`, `tool_name`,
`exception_message`, `action_taken`, `attempt_number`, `resolved`,
`session_id`.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Sentry Issue Grouping docs | <https://docs.sentry.io/concepts/data-management/event-grouping/> | .90 |
| 2 | structlog processors / filtering | <https://www.structlog.org/en/stable/processors.html> | .60 |
| 3 | Python logging MemoryHandler | <https://docs.python.org/3/howto/logging-cookbook.html> | .40 |
| 4 | OwlBear `ErrorJournal` impl | `src/owlbear/memory/error_journal.py` | 1.0 |
| 5 | OwlBear daemon retry logic | `src/owlbear/daemon.py` L186-320 | 1.0 |
| 6 | OwlBear `JsonlStore` base class | `src/owlbear/core/jsonl_store.py` | 1.0 |

## 3. Analysis

### 3.1 What constitutes a "duplicate"?

In `_recover_from_error`, transient retries produce entries like:

| attempt | error_type | tool_name | exception_message | action_taken |
|---------|-----------|-----------|-------------------|--------------|
| 1 | transient | agent.turn | Connection reset | transient_retry |
| 2 | transient | agent.turn | Connection reset | transient_retry |
| 3 | transient | agent.turn | Connection reset | transient_retries_exhausted |

The core identity is `(error_type, tool_name, exception_message)`. Entries
with the same triple within a short window are duplicates of the same
incident.

### 3.2 Approach comparison

| Criterion | A: Hash + in-memory LRU | B: Caller-side log-once | C: Last-entry check | D: Sentry-style DB |
|-----------|------------------------|------------------------|---------------------|--------------------|
| Complexity | ~30 LOC | ~10 LOC daemon change | ~15 LOC | Overkill |
| KISS | High | Highest | Medium | Low |
| Loses detail | First-only, count lost | Loses per-attempt info | File I/O on every log | N/A |
| Rotation impact | None | None | Needs file read | N/A |
| Reusable | Any JsonlStore consumer | Daemon-specific | Any JsonlStore consumer | N/A |
| Thread-safe | Needs lock on dict | N/A (single-task async) | File read race risk | N/A |

### 3.3 Sentry's approach (Source 1)

Sentry computes a **fingerprint** from `(exception_type, exception_value,
stack_trace_frames)` and groups events with the same fingerprint into one
"issue." Their hierarchy: stack trace > exception > message. For our
simpler use case (no stack traces in ErrorEntry), a hash of
`(error_type, tool_name, exception_message)` is the analogous fingerprint.

### 3.4 structlog's approach (Source 2)

structlog uses **processor chains** where any processor can drop events
via `DropEvent`. No built-in dedup, but the pattern shows dedup as a
filter step before write — which maps to checking a cache before
`append()`.

## 4. Recommendation

**Option A: Hash + in-memory time-windowed cache** — confidence **.80**

1. Add `dedup_key: str` field to `ErrorEntry` — `sha256(error_type +
   tool_name + exception_message)[:16]`
2. Add `_recent: dict[str, float]` to `ErrorJournal` (key → timestamp),
   bounded to 128 entries via LRU eviction
3. `log()` computes `dedup_key`, checks if seen within
   `dedup_window_seconds` (default 60s, configurable)
4. If within window → skip append, return silently
5. If outside window or unseen → append normally, record in cache

**Why not Option B (caller-side)?** It's simpler but daemon-specific.
The dedup belongs in ErrorJournal so any future consumer gets it for
free. YAGNI concern is low — the added code is ~30 LOC.

**Risk:** In-memory cache resets on process restart, allowing one
duplicate per restart. Acceptable — ErrorJournal is per-daemon-lifetime.

**Rotation interaction:** None. Dedup reduces writes, rotation triggers
on entry count. Fewer writes = less frequent rotation. Compatible.

**query() interaction:** `dedup_key` becomes a useful filter dimension
(group errors by fingerprint). Add optional `dedup_key` param to
`query()`.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Add dedup_key field to ErrorEntry and dedup logic to ErrorJournal.log()" --priority nice-to-have --status todo --tags "resilience,scope:core" --body "Add dedup_key (sha256[:16] of error_type+tool_name+exc_message) to ErrorEntry. Add time-windowed in-memory cache to ErrorJournal. Skip append if same dedup_key seen within 60s (configurable). AC: 1) ErrorEntry has dedup_key field. 2) Duplicate log() calls within window produce single entry. 3) Calls outside window produce new entry. 4) Cache bounded to 128 entries. 5) query() accepts optional dedup_key filter. 6) Tests cover dedup, window expiry, cache eviction, rotation compat. See docs/error-journal-dedup-research.md."

kanban\kanban-md.exe create "Wire ErrorJournal into agent learning loop" --priority nice-to-have --status ideation --tags "resilience,scope:core,agent" --body "J-1 follow-up: ErrorJournal exists but is not yet consumed by agents for learning from past errors. With dedup in place, the journal is cleaner and ready for consumption. Research how agents should query the journal (per-tool error history, recent failures) and integrate into context injection. Depends on dedup task above."
```
