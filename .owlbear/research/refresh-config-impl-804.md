# Add refresh_config + fix config staleness — Implementation Research

> **Owning task:** #804 — Add refresh_config + fix config staleness
> **Date:** 2026-04-11 **Status:** Complete

## 1. Context and Question

Task #804 is the GREEN implementation half (paired with #803 RED tests) for `refresh_config()` and config staleness in `KanbanEngine`. Key question: **what implementation work is needed, given the current engine code?**

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `serve/kanban/src/owlbear_kanban/engine.py` L106-113 | 1.0 | `refresh_config()` already implemented: reloads via `load_config()`, updates `_config`, `_tasks_dir`, `_archive_dir` |
| 2 | `serve/kanban/src/owlbear_kanban/engine.py` L248-285 | 1.0 | `create_task()` already reloads config via `load_config()` at call start; updates `self._config` + derived state after save |
| 3 | `serve/kanban/src/owlbear_kanban/engine.py` L86-91 | 0.9 | `_priority_rank()` and `_status_rank()` computed from `self._config` on each call — no cached maps to invalidate |
| 4 | `serve/kanban/src/owlbear_kanban/engine.py` L39 | 0.8 | `_ARCHIVE_DIR_NAME = "archive"` — constant, not config-derived |
| 5 | `tests/test_config_staleness_fix_828.py` | 0.9 | Existing tests cover `create_task` staleness (next_id sync, tasks_dir update) |
| 6 | `.owlbear/research/refresh-config-tests-803.md` | 0.8 | Sibling task research confirmed implementation predates tests |
| 7 | `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` | 0.7 | Brief §Phase 1 defines `refresh_config()` and staleness fix as work items |

## 3. Analysis

### AC vs. current implementation

| AC | Status | Evidence |
|----|--------|----------|
| `refresh_config()` reloads config, updates `_config` + derived state | **Done** | engine.py L106-113: `load_config()` → assigns `_config`, `_tasks_dir`, `_archive_dir` |
| `create_task` calls `refresh_config()` or equivalent | **Done** | engine.py L248: `config = load_config(...)` at top; L280-283: `self._config = config` + derived state after save |
| `_status_rank()` / `_priority_rank()` use new config after refresh | **Done** | Both methods (L87-91) derive from `self._config` on each call — no cached rank maps exist |
| #803 tests pass GREEN | **Pending** | Child #840 (in-progress) writes the 6 test cases; implementation exists to pass them |
| Existing MCP tests pass | **Unverified** | Needs builder verification pass |

### DRY analysis: should `create_task` call `refresh_config()`?

The AC says "or equivalent" — the current pattern is **preferable** to calling `refresh_config()`:

| Approach | Atomicity | Failure safety |
|----------|-----------|----------------|
| Current: `config = load_config()` → mutate local → `save_config()` → assign `self._config = config` | Local variable isolates mutation | If `save_config()` fails, `self._config` is unchanged |
| Refactored: `self.refresh_config()` → mutate `self._config.next_id` → `save_config()` | Mutates `self._config` before save | If `save_config()` fails, `self._config.next_id` is dirty |

**Recommendation:** Keep current pattern. The local-variable approach provides better failure isolation.

### `archive_dir` note

`_archive_dir` is derived from the constant `_ARCHIVE_DIR_NAME = "archive"` (L39), not from config. Both `refresh_config()` and `create_task` update it, but the value never changes. Harmless — not worth refactoring.

### Scope boundary: `move_task` staleness

`move_task()` validates status against `self._config.statuses` but does **not** call `refresh_config()`. If config changes externally, `move_task` uses stale status list until the consumer calls `refresh_config()`. This is **by design** per the brief — `refresh_config()` is the consumer-invoked mechanism; auto-refresh on every operation is not specified.

## 4. Recommendation

**No new code needed.** All AC points are already implemented. The GREEN phase for #804 is a **verification pass**: confirm #803 tests pass, confirm MCP tests pass, code review the existing implementation against the AC.

Confidence: **0.92** — implementation is clear, well-structured, and matches all AC points. Minor uncertainty: #840 tests not yet complete (in-progress), so GREEN verification can't run yet.

Challenge: FALLBACK — T1 trivial finding (implementation already exists), challenger not invoked.

## 5. Follow-up Tasks

No new implementation tasks needed. #804 builder should:
1. Wait for #803 (dependency) — blocked until #840 tests land
2. Run #803 tests: `uv run pytest tests/test_refresh_config_803.py -v`
3. Run MCP tests: `uv run pytest tests/ -m "not api" -q --tb=short`
4. Verify code matches AC, advance
