# Tests — Server pick_tasks Thin Wrapper

> **Owning task:** #825 — Tests — Server pick_tasks thin wrapper
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

Phase 3, step 3 of the kanban engine restructuring. After #824 creates `dispatch.py` with `pick_dispatchable()`, we need RED tests expressing the desired thin-wrapper behavior of `server.py`'s `pick_tasks` before #826 performs the slimming.

**Questions:** (1) What test structure covers all 5 ACs? (2) How to mock `pick_dispatchable` at the server level? (3) How to express "no inline gating logic" as a test? (4) Which tests should fail RED vs pass as regression guards?

## 2. Sources Studied

| # | Source | Rel. | What taken |
|---|--------|:----:|------------|
| S1 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L323-397 | .95 | Current inline `pick_tasks` implementation: `_check_pick_gates`, 6 `_PICK_*` constants, sort+cap+format |
| S2 | `tests/test_kanban_mcp_migration.py` L595-834 | .95 | Engine-based `pick_tasks` tests and `_make_engine_app_ctx` helper pattern |
| S3 | `serve/kanban/src/owlbear_kanban/models.py` L58-88 | .90 | `Task` model fields (`id`, `title`, `status`, `priority`, etc.) — return type of `pick_dispatchable` |
| S4 | `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` Phase 3 | .90 | Outcome O3: `pick_dispatchable` importable without MCP; no inline gating in server |
| S5 | `.owlbear/kanban/tasks/826-slim-server-pick-tasks-to-thin-wrapper.md` | .90 | GREEN step AC: server calls `pick_dispatchable`, no `_check_pick_gates`, no rank maps |
| S6 | `tests/test_pick_tasks.py` | .80 | Legacy tests (uses `_run_kanban` mock, now broken); comprehensive gate/sort/limit coverage provides coverage baseline |

## 3. Analysis

### 3.1 Test Category Matrix

| Category | Tests | RED/PASS rationale |
|----------|-------|--------------------|
| **AC1: Delegation** — server calls `pick_dispatchable()` | 4 tests | **RED** — `server.py` has no `pick_dispatchable` import; `patch` raises `AttributeError` |
| **AC2: No inline gating** — constants/functions removed | 3 tests | **RED** — `_check_pick_gates`, 6 `_PICK_*` constants still present |
| **AC3: Response format** — dispatch wrapper structure preserved | 4 tests | **PASS** — tests current behavior; regression guard for #826 |
| **AC4: MCP contract** — annotations and signature preserved | 3 tests | **PASS** — tests current state; regression guard for #826 |

### 3.2 Delegation Mocking Strategy

| Option | Approach | Risk | Recommendation |
|--------|----------|------|:--------------:|
| A. `patch("owlbear_mcp_kanban.server.pick_dispatchable")` | Patches at server module import site | Fails cleanly with `AttributeError` in RED | **(rec:)** .88 |
| B. `patch("owlbear_kanban.dispatch.pick_dispatchable")` | Patches at source module | Less precise — doesn't prove server imports it | .60 |
| C. `patch.object(dispatch_module, "pick_dispatchable")` | Requires import of dispatch module in test | Adds coupling to import path | .55 |

**Recommendation: Option A** (.88). The `AttributeError` on RED is the clearest failure signal. When #826 adds `from owlbear_kanban.dispatch import pick_dispatchable` to server.py, the patch target becomes valid.

### 3.3 "No Inline Gating" Detection Strategy

| Option | Approach | Risk | Recommendation |
|--------|----------|------|:--------------:|
| A. `hasattr(server_module, name)` | Checks module-level attributes | Misses local/nested definitions | .70 |
| B. `inspect.getsource()` substring search | Reads full source text | Fragile to comments mentioning old names | .60 |
| C. Both `hasattr` + `dir()` checks | Belt and suspenders | Slightly verbose but thorough | **(rec:)** .85 |

**Recommendation: Option C** (.85). Check `hasattr` for the function/constants. Per #826 AC: "No `_check_pick_gates`, no rank maps" — these are module-level symbols easily checked via `hasattr`.

### 3.4 Detailed Test Specification

**AC1 — Delegation tests (4 tests, all RED):**

```
test_pick_tasks_delegates_to_pick_dispatchable
  → patch pick_dispatchable, call pick_tasks(ctx), assert called_once
  → RED: AttributeError — server has no pick_dispatchable attribute

test_pick_tasks_passes_default_limit_to_pick_dispatchable
  → call pick_tasks(ctx), assert pick_dispatchable called with limit=25
  → RED: same

test_pick_tasks_passes_custom_limit_to_pick_dispatchable
  → call pick_tasks(ctx, limit=5), assert called with limit=5
  → RED: same

test_pick_tasks_passes_tag_to_pick_dispatchable
  → call pick_tasks(ctx, tag="phase-3"), assert called with tag="phase-3"
  → RED: same
```

**AC2 — No inline gating (3 tests, all RED):**

```
test_no_check_pick_gates_in_server
  → assert not hasattr(server_module, "_check_pick_gates")
  → RED: function still defined

test_no_pick_rank_maps_in_server
  → assert not hasattr for _PICK_PRIORITY_RANK, _PICK_STATUS_RANK
  → RED: constants still defined

test_no_pick_gate_constants_in_server
  → assert not hasattr for _PICK_AC_PATTERN, _PICK_CLARITY_STATUSES, _PICK_NON_IMPL_TAGS
  → RED: constants still defined
```

**AC3 — Response format (4 tests, all PASS):**

```
test_response_is_dispatch_dict
  → result has "dispatch" key, value is list

test_dispatch_entries_have_task_id_and_status
  → each entry has exactly {"task_id": int, "status": str}

test_task_id_is_integer
  → task_id values are int, not str

test_empty_board_returns_empty_dispatch
  → no tasks → {"dispatch": []}
```

**AC4 — MCP contract (3 tests, all PASS):**

```
test_pick_tasks_registered_in_mcp
  → "pick_tasks" in registered tool names

test_pick_tasks_has_read_only_hint
  → readOnlyHint=True

test_pick_tasks_has_idempotent_hint
  → idempotentHint=True
```

### 3.5 Test File Placement

| Option | Path | Rationale |
|--------|------|-----------|
| A. `tests/test_server_pick_tasks_thin_wrapper_825.py` | Follows `{slug}_{task_id}` convention | **(rec:)** |
| B. Extend `tests/test_kanban_mcp_migration.py` | Adds to existing migration test file | File already 830+ lines |

### 3.6 Helper Reuse

Existing helpers from `test_kanban_mcp_migration.py` (`_make_engine_app_ctx`, `_make_mcp_ctx`, `_make_mock_engine`) provide the correct engine-based `AppContext` pattern. Import or duplicate (file already exports them as module-level functions).

**Recommendation:** Duplicate the 3 helpers (~20 LOC). Test files should be self-contained per project convention.

## 4. Recommendation

**Test file:** `tests/test_server_pick_tasks_thin_wrapper_825.py` with 14 tests across 4 test classes.

**Confidence: 0.88** — High confidence. Standard TDD RED approach using well-established mock patterns from this codebase. Clear RED failure modes for AC1 (AttributeError) and AC2 (hasattr assertions). AC3/AC4 tests serve as regression guards.

**Risk:** If #826 builder imports `pick_dispatchable` differently than `from owlbear_kanban.dispatch import pick_dispatchable`, the patch target needs adjustment. Mitigated by the AC2 source inspection tests as a backup signal.

Challenge: FALLBACK — challenger subagent not available in this context.

## 5. Follow-up Tasks

- Task created at `research` status for test-writer to implement the 14-test file.
