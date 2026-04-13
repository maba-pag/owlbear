# Task #845 — TaskSummary adoption test redundancy

> **Owning task:** #845 — Tests — TaskSummary adoption in server.py list_tasks
> **Date:** 2026-04-12  **Status:** Complete

## 1. Context and Question

Task #845 calls for RED tests verifying that `list_tasks` uses `TaskSummary`. The architecture review rejected it as redundant (commit `3703469e` / #802 already delivered the implementation). This research validates that rejection and checks for residual quality issues in existing test coverage.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `server.py:105-153` — list_tasks handler + outputSchema patch | 1.0 |
| 2 | `owlbear_kanban/models.py:90-116` — TaskSummary definition | 1.0 |
| 3 | `test_mcp_adapter_slimming_819.py:175-189` — list_tasks type assertion | 0.9 |
| 4 | `test_kanban_mcp_migration.py:210-295` — TestFromAC_ListTasks suite | 1.0 |
| 5 | Pydantic v2 BaseModel `__iter__` / `__contains__` behavior (verified empirically) | 0.9 |

## 3. Analysis

### 3a. AC vs codebase state

| AC | Implemented? | Existing test? | Notes |
|----|-------------|----------------|-------|
| AC1: list_tasks uses TaskSummary | YES — `server.py:133` | `test_mcp_adapter_slimming_819.py:176` | Passes GREEN |
| AC2: includes 10 fields | YES — model fields | Implicit via AC1 test | Would pass GREEN |
| AC3: excludes body/created/updated/claimed_by/claimed_at/file | PARTIAL — `created`/`updated` ARE included by design | `test_kanban_mcp_migration.py:232` | **False positive** (see 3b) |
| AC4: claimed bool from claimed_by | YES — `_coerce_claimed` validator | `test_kanban_mcp_migration.py:247` | **BROKEN test** (see 3b) |
| AC5: outputSchema matches TaskSummary | YES — `server.py:147` | None dedicated | Would pass GREEN |

### 3b. Stale migration tests (critical finding)

When `list_tasks` return type changed from `list[dict]` to `list[TaskSummary]`, two tests in `test_kanban_mcp_migration.py::TestFromAC_ListTasks` became invalid:

| Test | Issue | Severity |
|------|-------|----------|
| `test_list_tasks_claimed_bool_derived_from_claimed_by` | Uses `result[0]["claimed"]` — `TaskSummary` has no `__getitem__`. **TypeError at runtime.** | BROKEN (1 test failure) |
| `test_list_tasks_strips_body_and_timestamp_fields` | Uses `field not in row` — Pydantic v2 `__iter__` yields `(k,v)` tuples, so `str in model` is ALWAYS False. Verified empirically: `"x" in M(x=1)` → `False`. | FALSE POSITIVE (0 assertion value) |

### 3c. AC3 status (corrected)

AC3 is factually correct. `TaskSummary` does NOT include `created` or `updated` — its docstring explicitly states "Excludes body, claimed_by, created, and updated from the full Task schema." Earlier analysis misread the model; the 3rd arch review corrected this.

## 4. Recommendation

**Close #845 as redundant.** All AC items are already implemented and covered by tests elsewhere. New tests would pass GREEN immediately — no RED phase is possible. Confidence: 0.92.

The real quality issue is the two stale migration tests. A follow-up task addresses this.

Challenge: SKIPPED — redundancy verdict, no competing options to challenge.

## 5. Follow-up Tasks

- **Fix stale `TestFromAC_ListTasks` migration tests** — fix `__getitem__` TypeError and `in`-operator false positive in `test_kanban_mcp_migration.py` (see follow-up task).
