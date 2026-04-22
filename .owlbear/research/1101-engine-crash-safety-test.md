# Engine create_task Crash-Safety Test Design

> **Owning task:** #1101 — Engine create_task crash-safety test (AC-C51-engine)
> **Date:** 2026-04-22 **Status:** Complete

## 1. Context and Question

Task #1046 refined AC-C51 to storage-helper scope (`allocate_next_id`). The engine-level `create_task` in `engine.py` currently does `write_task` BEFORE `save_config` — the reverse of Brief C §3.3's crash-safe order. Once #1062 refactors `create_task` to use `allocate_next_id`, the engine path gains crash safety but no test verifies this at the integration level.

**Question:** What test strategy validates engine-level crash safety for `create_task` after the #1062 refactor?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | Brief C §3.3 ID allocation flow | `.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md` L241–270 | 1.0 — crash-safety spec |
| 2 | `engine.py::create_task` | `serve/kanban/src/owlbear_kanban/engine.py` L635–710 | 1.0 — current implementation |
| 3 | `storage.py::allocate_next_id` | `serve/kanban/src/owlbear_kanban/storage.py` L414–427 | 1.0 — target allocation function |
| 4 | AC-C51 storage-level test | `serve/kanban/tests/test_storage_io.py` L356–380 | 0.9 — pattern template |
| 5 | AC-C4 concurrent allocation test | `serve/kanban/tests/test_storage_io.py` L211–240 | 0.7 — threading pattern |
| 6 | `test_engine_storage.py` suite | `serve/kanban/tests/test_engine_storage.py` | 0.8 — engine test patterns |
| 7 | #1062 task body (C-17 GREEN) | kanban board | 0.9 — refactor scope |
| 8 | #1097 research (engine I/O routing) | kanban board + `.owlbear/research/1097-engine-io-storage-routing.md` | 0.6 — subsumption context |

## 3. Analysis

### Current vs. Post-Refactor Flow

| Step | Current `engine.py` (inline) | After #1062 (`allocate_next_id`) |
|------|------------------------------|----------------------------------|
| 1 | `flock(.next_id.lock)` | `allocate_next_id()` acquires flock internally |
| 2 | `load_config()` | `load_config()` (inside `allocate_next_id`) |
| 3 | `task_id = config.next_id` | `config.next_id += 1` |
| 4 | build `Task` record | `save_config()` — **config bumped first** |
| 5 | `write_task()` — task file first | flock released, `task_id` returned |
| 6 | `config.next_id += 1` | build `Task` record |
| 7 | `save_config()` — config second | `write_task()` — task file second |

**Key difference:** Post-refactor, `save_config` happens BEFORE `write_task` (inside `allocate_next_id`). Crash between them burns the ID — safe. Current order is reversed — crash between `write_task` and `save_config` leaves stale `next_id` → duplicate collision risk.

### Test Approach Comparison

| Approach | AC-1 (crash sim) | AC-2 (route verify) | Complexity | Risk |
|----------|-------------------|----------------------|------------|------|
| A: Patch `write_task` to raise | Mock `write_task` → `OSError` on 1st call, succeed on 2nd. Verify 2nd call gets burned_id+1 | Separate spy on `allocate_next_id` | Low | Patch target may shift if #1062 changes imports |
| B: State-corruption approach (like AC-C51) | Manually advance config, skip task write, call `engine.create_task` | Inspect engine code structure | Medium | Bypasses actual engine code path; weaker integration signal |
| C: Patch `atomic_write` at storage_io level | Fail the low-level atomic write after config is saved | Separate spy | Medium | Fragile — depends on call ordering of a private function |

**Recommendation: Approach A** (confidence: 0.85)

Approach A directly tests the engine's `create_task` method, patches at the correct abstraction boundary (`write_task`), and follows the established pattern from AC-C51 (source #4). Approach B is weaker because it doesn't exercise the engine code path. Approach C is fragile.

### AC-1 Test Skeleton

```
1. Create engine with tmp_path board (next_id=1001)
2. Patch storage.write_task to raise OSError on first call
3. Call engine.create_task("test") — expect OSError propagation
4. Verify config.next_id == 1002 (allocate_next_id already saved)
5. Unpatch write_task
6. Call engine.create_task("test2") — succeeds
7. Assert returned task.id == 1002 (burned 1001 skipped)
8. Assert no task file exists for ID 1001
```

### AC-2 Test Skeleton

```
1. Create engine with tmp_path board
2. Spy on storage.allocate_next_id (wraps real function)
3. Call engine.create_task("test")
4. Assert allocate_next_id called exactly once
5. Assert engine does NOT read config.next_id inline (no flock in engine)
```

### AC-3 Regression

Standard: new test file coexists with `test_engine_storage.py`. Run both suites together.

## 4. Recommendation

**Approach A — mock `write_task` at storage boundary** (confidence: 0.85).

- Matches existing AC-C51 pattern (state-then-verify) but at engine integration level.
- Test file: `serve/kanban/tests/test_engine_crash_safety.py` (or add to `test_engine_storage.py`).
- 2 test functions (AC-1, AC-2) + standard regression (AC-3).
- Depends on #1062 completing the `allocate_next_id` refactor first.
- Risk: if #1062 changes the import path of `write_task`, the patch target needs updating. Mitigated by patching at the `owlbear_kanban.storage` namespace.

**Challenge:** FALLBACK — task is T1 (test addition following established patterns). No architecture change, no new capability. Challenger invocation not warranted per confidence threshold (≥ 0.80).

## 5. Follow-up Tasks

This task IS the follow-up — it moves to backlog for test-writing. No additional tasks needed. The dependency on #1062 is already recorded.

**Tier classification:** T1 — Autonomous. Test addition following established crash-safety patterns. No architecture, security, or behavioral change.
