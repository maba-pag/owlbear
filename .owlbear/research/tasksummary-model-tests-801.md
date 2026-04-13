# TaskSummary Model — Testing Strategy

> **Owning task:** #801 — Tests — TaskSummary model
> **Date:** 2026-04-11 **Status:** Complete

## 1. Context and Question

Task #801 is the TDD RED phase for `TaskSummary`, a schema-validated list projection that replaces hand-built dicts in `server.py` (brief O2). Task #802 (GREEN) depends on these tests. Question: what tests are needed to fully cover the AC, and what will fail RED?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `serve/kanban/src/owlbear_kanban/models.py` — current TaskSummary (lines 93-101) | 1.0 |
| S2 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — list_tasks hand-built dict (lines 134-155) | 1.0 |
| S3 | `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` — AC for TaskSummary | 1.0 |
| S4 | `serve/mcp-kanban/tests/test_tool_annotations_494.py` — mcp-kanban test pattern | 0.8 |
| S5 | `tests/test_engine_package_boundary_817.py` — engine import test pattern | 0.7 |
| S6 | Pydantic v2 `model_fields` API — schema introspection for field presence/absence checks | 0.9 |

## 3. Analysis

### Current vs Required TaskSummary Schema

| Field | Current | Required | RED? |
|-------|---------|----------|------|
| id | ✓ int | ✓ int | PASS |
| title | ✓ str | ✓ str | PASS |
| status | ✓ str | ✓ str | PASS |
| priority | ✓ str | ✓ str | PASS |
| tags | ✓ list[str] | ✓ list[str] | PASS |
| blocked | ✓ bool | ✓ bool | PASS |
| block_reason | ✗ missing | ✓ str\|None | **FAIL** |
| claimed | ✗ (claimed_by) | ✓ bool | **FAIL** |
| parent | ✗ missing | ✓ int\|None | **FAIL** |
| depends_on | ✗ missing | ✓ list[int] | **FAIL** |
| claimed_by | ✓ str\|None | ✗ excluded | **FAIL** |
| body | ✗ absent | ✗ excluded | PASS |
| created | ✗ absent | ✗ excluded | PASS |
| updated | ✗ absent | ✗ excluded | PASS |
| claimed_at | ✗ absent | ✗ excluded | PASS |
| file | ✗ absent | ✗ excluded | PASS |

**5 tests fail RED** at schema level.

### Construction Gap: extra="allow" Leaks Fields

Current `TaskSummary` uses `extra="allow"`. When constructed from a full `Task.model_dump()`, extra fields (body, created, updated, etc.) are silently accepted and preserved. Tests must verify both:

1. **Schema level** — field not in `model_fields` (static check)
2. **Instance level** — field not in `model_dump()` after construction from Task (runtime check)

Instance-level exclusion tests will **FAIL RED** with `extra="allow"` — proper RED coverage.

### Test Structure

| Test Class | Tests | RED Count |
|------------|-------|-----------|
| `TestTaskSummarySchemaIncludes` | 10 parametrized (one per required field) | 4 FAIL |
| `TestTaskSummarySchemaExcludes` | 6 parametrized (one per excluded field) | 1 FAIL |
| `TestTaskSummaryFromTask` | construct from Task, verify claimed coercion, verify excluded fields absent | 3+ FAIL |
| `TestListTasksReturnsTaskSummary` | return type is list[TaskSummary], not list[dict] | 1 FAIL |

**Total RED failures: 9+** — satisfies "Tests fail RED before implementation."

### Test Placement

File: `tests/test_tasksummary_model_801.py` — follows workspace `test_{slug}_{id}.py` convention (S5 pattern). All tests are pure unit tests except the list_tasks test, which inspects the server function's return annotation.

### Dependency Note

#801 depends on #800 (rename TaskRecord → Task). The Task compat alias is already in place (S1), so this research and subsequent tests are unblocked.

## 4. Recommendation (confidence: 0.92)

Write tests in `tests/test_tasksummary_model_801.py` covering all 4 AC items. Use `model_fields` for schema checks, construct from `Task.model_dump()` for instance-level exclusion, and inspect `list_tasks` return annotation for projection type. All tests use standard pytest parametrize.

Challenge: skipped — test design, no design decision requiring challenger.
Tier: T1 — Autonomous (TDD RED test writing for a planned model change).

## 5. Follow-up Tasks

None created — #801 itself advances to backlog for TDD RED execution. #802 (GREEN) already exists and depends on #801.
