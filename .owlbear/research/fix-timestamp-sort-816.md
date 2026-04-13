# Fix Timestamp Sort

> **Owning task:** #816 — Fix timestamp sort
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

`engine.py` sorts tasks by `created`/`updated` via string comparison (`tasks.sort(key=lambda t: t.created)`). Timestamps are stored as strings to preserve Go 7-digit nanosecond format. String comparison produces wrong ordering when timestamps have different timezone offsets because lexicographic order doesn't account for UTC normalization.

**Question:** What's the correct, minimal fix that preserves string round-trip fidelity?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Python datetime docs | docs.python.org/3/library/datetime.html | 1.0 — confirms `fromisoformat()` handles arbitrary fractional digits (truncated to 6), aware datetime comparison normalizes to UTC |
| DEV Community — ISO 8601 sorting | dev.to/adnauseum/sorting-iso-8601-timestamps-5am2 | 0.8 — article + comments confirm string sort fails across timezones |
| Empirical test (Python 3.12.13) | local workspace | 1.0 — verified Go 7-digit, 9-digit, mixed-offset parsing and comparison |
| Codebase: engine.py claim_task | serve/kanban/src/owlbear_kanban/engine.py L462 | 1.0 — existing `fromisoformat()` precedent for `claimed_at` |
| Codebase: models.py | serve/kanban/src/owlbear_kanban/models.py L1-8 | 1.0 — documents intentional string storage for round-trip fidelity |

## 3. Analysis

### Bug Evidence

Empirical test on Python 3.12.13:

- String sort of `['...+02:00', '...+00:00', '...-05:00']` produces chronologically wrong order
- `datetime.fromisoformat()` sort produces correct chronological order
- `datetime` aware comparison normalizes to UTC: `dt_a == dt_b` returns `True` for same instant at different offsets

### Go 7-digit Handling

`fromisoformat()` accepts 7+ fractional digits, truncates to microsecond (6 digits). Truncation is parse-only — stored string unchanged. Sub-microsecond precision loss is irrelevant for sort ordering.

### Approach Comparison

| Approach | Change Size | Correctness | Round-trip Fidelity | KISS |
|----------|-------------|-------------|---------------------|------|
| **A: Parse in sort key** | 2 lines | Correct across offsets | Preserved | Yes |
| B: Cache parsed datetime | ~30 LOC | Correct | Preserved | No — over-engineered |
| C: Normalize to UTC on write | ~10 LOC | Correct | **Broken** — changes stored format | No |

## 4. Recommendation

**Approach A** — parse timestamps in sort key lambda. Confidence: **0.92**

```python
elif sort == "created":
    tasks.sort(key=lambda t: datetime.fromisoformat(t.created))
elif sort == "updated":
    tasks.sort(key=lambda t: datetime.fromisoformat(t.updated))
```

Rationale: existing pattern (claim_task L462), minimal change, preserves stored format, board size makes parse cost negligible.

Challenge: FALLBACK — challenger agent not available in tool allowlist

## 5. Follow-up Tasks

No new tasks needed. #815 (RED tests) and #816 (GREEN implementation) already exist as a TDD pair. Research confirms the implementation approach for #816.

**Tier:** T1 — Bug fix. No new capability, no architecture change, no security impact.

## 6. Validation Pass (2026-04-13)

Research doc validated against current codebase. Implementation already in place.

| AC Item | Status | Evidence |
|---------|--------|----------|
| Sort parses to `datetime` via `fromisoformat()` | ✅ Done | `engine.py` L252-255 |
| Handles Go 7-digit + Python 6-digit formats | ✅ Done | Python 3.12 `fromisoformat()` accepts 1-7 fractional digits; verified empirically |
| Stored format unchanged (string round-trip) | ✅ Done | Sort uses datetime as key only; `_NoTimestampLoader` + `str` field preserve originals |
| Correct ordering across mixed TZ offsets | ✅ Done | `test_sort_by_created_mixed_tz_offsets` + `test_sort_by_updated_mixed_tz_offsets` pass GREEN |
| #815 tests pass GREEN | ⚠️ 10/11 | `test_sort_round_trip_string_fidelity` has a test defect (accesses `created` on `TaskSummary` which drops it) — this is #815 scope |
| Existing MCP tests pass (O4) | ⚠️ Pre-existing failures | 102 kanban test failures exist but **none caused by the timestamp sort fix** — all are pre-existing (removed `_run_kanban`, changed `AppContext` constructor, etc.) |

### Key Finding

The implementation for #816 is **already complete**. The 2-line fix at `engine.py` L252-255 matches the recommended Approach A exactly. The remaining test defect (`TaskSummary` missing `created` attribute) is a #815 test authoring bug, not a code defect in the sort logic.
