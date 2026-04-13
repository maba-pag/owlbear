# Tests — Timestamp Sort Fix

> **Owning task:** #815 — Tests — timestamp sort fix
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

The kanban engine sorts `created`/`updated` fields via lexicographic string
comparison (`engine.py` L199–202). Timestamps are stored as plain `str` to
preserve Go 7-digit nanosecond format. String sort breaks with mixed timezone
offsets because it ignores UTC normalization.

**Question:** What test cases are needed to expose the bug and verify the fix
for all AC dimensions (mixed TZ offsets, mixed precision, round-trip fidelity)?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `serve/kanban/src/owlbear_kanban/engine.py` L199–202 — sort key code | 1.0 |
| S2 | `serve/kanban/src/owlbear_kanban/models.py` — `Task.created`/`updated` as `str` | 1.0 |
| S3 | `serve/kanban/src/owlbear_kanban/task_io.py` — `_NoTimestampLoader`, round-trip preservation | 1.0 |
| S4 | `tests/test_kanban_engine_listing.py` — existing sort tests (same-TZ only) | 1.0 |
| S5 | Python 3.12 `datetime.fromisoformat()` docs — handles 1–7 fractional digits | 0.9 |
| S6 | Brief `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` — fix strategy | 0.8 |

## 3. Analysis

### Bug Demonstration

| Task | Timestamp (stored) | UTC equivalent | String rank | Correct rank |
|------|--------------------|----------------|-------------|--------------|
| A | `2026-01-01T12:00:00+02:00` | 10:00 UTC | 2nd (`12` > `11`) | 1st (earlier) |
| B | `2026-01-01T11:00:00+00:00` | 11:00 UTC | 1st (`11` < `12`) | 2nd (later) |

String sort: B, A. Correct sort: A, B. **Bug confirmed.**

### `fromisoformat()` Verification (Python 3.12)

Verified locally:
- 7-digit Go nanoseconds (`...1234567+02:00`): parsed OK, 7th digit truncated to µs.
- 6-digit Python microseconds (`...123456+00:00`): parsed OK.
- Timezone-aware comparison normalizes to UTC correctly.
- Sub-microsecond truncation is immaterial for sort ordering.

### Test Matrix

| AC | Test Case | Key Assertion |
|----|-----------|---------------|
| AC1 | `created` sort with mixed TZ offsets (+02:00 vs +00:00) | Order matches UTC chronology, not string order |
| AC2 | `updated` sort with mixed TZ offsets | Same as AC1 for `updated` |
| AC3 | Sort with Go 7-digit + Python 6-digit mixed timestamps | Correct chronological order despite format differences |
| AC4 | Round-trip: timestamps unchanged after list_tasks | `task.created` string == original string after engine ops |

### Implementation Notes

- Tests belong in `tests/test_kanban_engine_listing.py`, extending `TestFromAC_SortByField`.
- Existing `_task_content` helper supports `created`/`updated` kwargs — no new helpers needed.
- Tests must fail RED with current string-sort implementation (AC5).
- Paired task #816 implements the fix (depends on #815).

## 4. Recommendation

Write 4 test methods in the existing test class. No new test file needed.
Confidence: **0.92** — straightforward TDD RED with well-understood bug.

Challenge: FALLBACK — researcher mode, no challenger subagent configured.

## 5. Follow-up Tasks

- #816 (existing) — Fix timestamp sort (depends on #815, already created)
- No additional follow-up tasks needed; the test/impl pair is complete.
