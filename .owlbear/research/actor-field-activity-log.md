# Add Actor Field to Activity Log

> **Owning task:** #812 — Add actor field to activity log
> **Date:** 2026-04-12  **Status:** Complete

## 1. Context and Question

Task #812 (Phase 1 of the Kanban Engine Restructuring brief) adds an `actor` field
to `activity.jsonl` entries. This enables multi-consumer attribution — distinguishing
engine-originated mutations from future GUI or CLI consumers.

Current entry schema: `{"timestamp", "action", "task_id", "detail"}` (4 fields).
Target schema: add `"actor"` (5 fields). Old entries without the field must remain
readable (no migration).

## 2. Sources Studied

| # | Source | Rel. | What |
|---|--------|:----:|------|
| 1 | `serve/kanban/src/owlbear_kanban/activity_log.py` | .95 | Current `log_activity()` — 4-param signature, appends JSONL |
| 2 | `serve/kanban/src/owlbear_kanban/engine.py` L285–495 | .95 | 7 call sites: create, block, unblock, edit, move, claim, release |
| 3 | `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` | .90 | Brief mandates `actor` in Phase 1; engine is multi-consumer foundation |
| 4 | `tests/test_kanban_engine_activity.py` L56–63 | .90 | `test_entry_has_exactly_four_keys` — will break, must update |
| 5 | `share/skills/w-retro/SKILL.md` L113 | .80 | Retro workflow reads JSONL via `ConvertFrom-Json` — dynamic fields OK |
| 6 | `serve/kanban/src/owlbear_kanban/__init__.py` | .75 | `log_activity` is private (not in `__all__`) — no public API break |

## 3. Analysis

### 3.1 Implementation Trade-offs

| Approach | Pros | Cons | Fit |
|----------|------|------|:---:|
| A. Keyword param `actor="engine"` | Backward-compatible, minimal diff, KISS | None significant | .92 |
| B. Positional param | Breaks all existing call sites & tests immediately | Forces explicit passing | .30 |
| C. Inject actor via engine constructor only | Cleaner but prevents per-call override | Limits future consumers | .50 |

### 3.2 Call Site Impact (7 sites in `engine.py`)

| Line | Action | Current call | Actor value |
|------|--------|-------------|-------------|
| 285 | create | `log_activity(path, "create", id, title)` | Pass explicitly |
| 380 | block | `log_activity(path, "block", id, reason)` | Pass explicitly |
| 382 | unblock | `log_activity(path, "unblock", id, "")` | Pass explicitly |
| 391 | edit | `log_activity(path, "edit", id, fields)` | Pass explicitly |
| 429 | move | `log_activity(path, "move", id, transition)` | Pass explicitly |
| 470 | claim | `log_activity(path, "claim", id, agent)` | Pass explicitly |
| 495 | release | `log_activity(path, "release", id, agent)` | Pass explicitly |

AC requires "all engine call sites pass `actor` param". The value to pass is not
prescribed — default `"engine"` is sufficient for now. Future consumers (GUI) will
pass a different value.

### 3.3 Backward Compatibility

- Old JSONL entries: `json.loads()` returns a dict without `"actor"`. Consumers must
  treat `actor` as optional (`.get("actor")` or absent key).
- `w-retro` PowerShell pipeline: `ConvertFrom-Json` creates dynamic PSObject — new
  field appears automatically, no breakage.
- Python API: keyword param with default — existing callers work unchanged.

### 3.4 Test Impact

| Test file | Impact |
|-----------|--------|
| `test_kanban_engine_activity.py` L57 | `test_entry_has_exactly_four_keys` asserts 4 keys — must update to 5 |
| `test_kanban_engine_activity_wiring_728.py` | No exact-key assertions — unaffected |
| #811 tests (not yet written) | Will validate actor field presence, default, backward compat |

## 4. Recommendation (.92 confidence)

**Approach A** — keyword parameter `actor: str = "engine"`.

- Signature: `def log_activity(log_path, action, task_id, detail, *, actor="engine")`
- Entry dict: add `"actor": actor`
- All 7 engine call sites pass `actor` explicitly per AC
- Update `test_entry_has_exactly_four_keys` to expect 5 keys including `actor`

Challenge: FALLBACK — trivial T1 change, no challenger needed.

## 5. Follow-up Tasks

- #811 (existing) — RED tests for actor field
- #812 (this task) — advances to backlog for implementation

**Tier: T1 — Autonomous.** Simple field addition, no architecture/security/breaking changes.

Affected files (3):
- `serve/kanban/src/owlbear_kanban/activity_log.py`
- `serve/kanban/src/owlbear_kanban/engine.py`
- `tests/test_kanban_engine_activity.py`
