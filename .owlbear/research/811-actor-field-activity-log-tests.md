# Tests — Actor Field in Activity Log

> **Owning task:** #811 — Tests — actor field in activity log
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

Task #811 is the RED phase for adding an `actor` field to `activity.jsonl` entries. The tests must verify the new field exists, backward compat with old entries, default actor value, and field presence across all action types. The implementation (GREEN phase) is #812.

**Key question:** What test structure verifies the `actor` field contract while ensuring tests fail RED before implementation?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/kanban/src/owlbear_kanban/activity_log.py` | Codebase | 1.0 — Current `log_activity()` implementation |
| S2 | `serve/kanban/src/owlbear_kanban/engine.py` | Codebase | 1.0 — All 7 call sites to `log_activity()` |
| S3 | `tests/test_kanban_engine_activity.py` | Codebase | 0.9 — Existing RED tests for 4-field schema |
| S4 | `tests/test_kanban_engine_activity_wiring_728.py` | Codebase | 0.9 — Existing engine ↔ log wiring tests |
| S5 | `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` | Codebase | 0.9 — Brief specifying actor field design |
| S6 | `.owlbear/briefs/draft-kanban-web-gui-prep/synthesis.md` | Codebase | 0.8 — Ideation panel consensus on actor field |
| S7 | PocketPaw audit log (`pocketpaw.xyz/security/audit-log`) | External | 0.7 — JSONL audit log with `channel` field for source identity |
| S8 | tundere-ledger (`pypi.org/project/tundere-ledger`) | External | 0.6 — Python JSONL audit log with `actor_name` parameter |

## 3. Analysis

### Current State

| Aspect | Current | After #812 |
|--------|---------|------------|
| `log_activity()` signature | `(log_path, action, task_id, detail)` | `(log_path, action, task_id, detail, actor="engine")` |
| JSONL entry keys | `{timestamp, action, task_id, detail}` | `{timestamp, action, task_id, detail, actor}` |
| Existing entries (11,789) | No `actor` key | Unchanged — no migration |
| Consumer identity | In `detail` for claim/release only | Explicit `actor` field on all entries |

### Test Design Trade-offs

| Approach | Pros | Cons | Fit |
|----------|------|------|-----|
| A: New test file `test_actor_field_811.py` | Clean separation; single-responsibility | One more file in tests/ | Best — matches existing pattern |
| B: Add tests to existing `test_kanban_engine_activity.py` | Fewer files | Mixes two task IDs; RED/GREEN confusion | Rejected |
| C: Extend `test_kanban_engine_activity_wiring_728.py` | Co-locates related wiring tests | Wrong task ownership; AC drift | Rejected |

### Test Structure (Approach A)

| Test Class | AC Coverage | Tests (RED) |
|------------|-------------|-------------|
| `TestFromAC_ActorFieldPresent` | New entries include `actor` | `log_activity()` with default → entry has `actor` key; value is string |
| `TestFromAC_BackwardCompat` | Old entries without `actor` load OK | Write 4-field JSON manually, read back, no crash; missing key returns `None`/default |
| `TestFromAC_DefaultActorEngine` | Default is `"engine"` | Call `log_activity()` without `actor` → entry `actor == "engine"` |
| `TestFromAC_ActorAllActionTypes` | All 5 action types (create, edit, move, claim, release) | Engine methods produce entries with `actor` field for each action type |

### Backward Compatibility

No structured reader exists in `activity_log.py`. Consumers:
- **Tests:** `json.loads()` per line — tolerant of extra/missing keys
- **w-retro (PowerShell):** `ConvertFrom-Json` — ignores unknown fields, handles missing fields as `$null`

Backward compat testing strategy: write entries in old format (4 keys, no `actor`), verify `json.loads()` succeeds and that accessing `entry.get("actor")` returns `None`. This validates that any future reader code handles the gap gracefully.

### RED Gate

All tests call `log_activity()` with `actor` kwarg or assert `"actor" in entry` — both will fail because:
1. `log_activity()` does not accept `actor` parameter (TypeError)
2. Entries do not contain `actor` key (KeyError/AssertionError)

## 4. Recommendation (confidence: 0.90)

**Approach A: New test file** following existing patterns from S3/S4.
- File: `tests/test_actor_field_activity_log_811.py`
- 4 test classes, ~15-20 test methods
- Covers all 5 AC items
- Engine wiring tests need fixtures matching S4 pattern (`kanban_dir`, `engine`)

Challenge: FALLBACK — researcher mode, no challenger subagent available.

## 5. Follow-up Tasks

- **#812** (already exists) — GREEN implementation: add `actor` parameter to `log_activity()`, update engine call sites
- No additional tasks needed — the test/implementation pair is complete
