# Fix test_engine_crash_safety_1101.py routing drift — 4 failures

> **Owning task:** #1140 — Fix test_engine_crash_safety_1101.py routing drift — 4 failures
> **Date:** 2026-04-26 **Status:** Complete

## 1. Context and Question

`serve/kanban/tests/test_engine_crash_safety_1101.py` has 4 failing tests. Task description says "routing expectations don't match current engine code." Need to identify the actual root cause and fix approach.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `test_engine_crash_safety_1101.py` (full file) | Codebase | 1.0 |
| 2 | `engine.py` L867-950 (`create_task`) | Codebase | 1.0 |
| 3 | `storage.py` L547-558 (`allocate_next_id`) | Codebase | 0.9 |
| 4 | `models.py` L88-93 (`_validate_agent_map`) | Codebase | 0.9 |
| 5 | `test_engine_move_claim.py` L50-90 (working fixture) | Codebase | 0.8 |

## 3. Analysis

### 3.1 Failure Diagnosis

All 4 tests fail identically at `KanbanEngine(kanban_dir)` — never reaching any routing assertion:

```
ConfigError: agent_map missing status entries: ['research', 'backlog', 'todo', 'in-progress', 'review', 'docs', 'done']
```

**Root cause:** The fixture `_CONFIG_YAML` uses a legacy schema (`version: 10`, `board:` wrapper) that lacks `agent_map`, `entry_status`, `terminal_status`, `wave_size`, `agent_types`, `agent_compatibility`, `non_impl_tags`, `archival_reasons`, and `status_predicates` — all required by current `BoardConfig` validation.

### 3.2 Routing Status

The tests were written as RED-phase, expecting the engine to still allocate IDs inline. The engine has already been refactored:

| Evidence | Location |
|----------|----------|
| `storage.allocate_next_id(self._kanban_dir)` | engine.py L930 |
| `allocate_next_id` persists config before returning | storage.py L553-556 |
| `write_task` called AFTER `allocate_next_id` returns | engine.py L940 |

Once the config fixture is corrected, all 4 routing assertions should pass without changes.

### 3.3 Patch Target Audit

| Test | Patch target | Engine access pattern | Correct? |
|------|-------------|----------------------|----------|
| AC-1 crash | `owlbear_kanban.engine.write_task` | Direct import (`from … import write_task`) | Yes |
| AC-2a config-saved | `owlbear_kanban.engine.write_task` | Same | Yes |
| AC-2b routing | `owlbear_kanban.storage.allocate_next_id` | Module-attr (`storage.allocate_next_id(…)`) | Yes |
| AC-3 regression | `owlbear_kanban.storage.allocate_next_id` | Same | Yes |

### 3.4 Fix Approach

| Step | Action |
|------|--------|
| 1 | Replace `_CONFIG_YAML` with current-schema fixture (model: `test_engine_move_claim.py` `_BASE_CONFIG`) |
| 2 | Add `docs` status and agent_map entry (original test had 7 statuses) |
| 3 | Keep `next_id: 1001` (test assertions depend on this value) |
| 4 | Update module docstring and per-test docstrings — remove "Currently FAILS" language |
| 5 | Run suite, verify all 4 green + no regressions |

## 4. Recommendation (confidence: 0.92)

**T1 — autonomous fix.** Config fixture update only. No mock/spy changes, no engine changes. Effort: Low (was Medium in task description).

Working fixture template exists in `test_engine_move_claim.py` — pattern proven, just needs `docs` status added and `next_id` set to 1001.

Challenge: FALLBACK — single clear root cause, no competing options to challenge.

## 5. Follow-up Tasks

No additional follow-up tasks needed — this task is already scoped correctly. Effort estimate should be revised from Medium to Low in the task body.
