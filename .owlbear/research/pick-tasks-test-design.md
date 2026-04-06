# Test Design: pick_tasks MCP Tool

> **Owning task:** #620 — Test: pick_tasks MCP tool gate logic and output format
> **Date:** 2026-04-05 **Status:** Complete

## 1. Context and Question

Task #620 is TDD RED phase for the `pick_tasks` MCP tool defined in #619/#621.
The tool doesn't exist yet — tests must exercise the contract specified in #621 AC.

**Questions:**
1. What mock pattern to use for `pick_tasks` tests?
2. What task JSON structure exercises all gate/sort/limit scenarios?
3. Are there edge cases beyond the AC?

## 2. Sources Studied

| # | Source | Relevance | What |
|---|--------|-----------|------|
| 1 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | 1.0 | Existing tool patterns, `_run_kanban` interface, `AppContext` |
| 2 | `serve/mcp-kanban/tests/test_start_work_470.py` | 1.0 | Canonical mock pattern: `patch("...server._run_kanban", AsyncMock)` |
| 3 | `tests/test_mcp_kanban_list_tasks_472.py` | .95 | List-style tool testing with JSON arrays |
| 4 | `serve/orchestrator/src/owlbear/planner/gates.py` | 1.0 | Gate logic being migrated: atomicity, TDD, clarity |
| 5 | `serve/orchestrator/src/owlbear/planner/selector.py` | 1.0 | Sort logic: PRIORITY_RANK, STATUS_RANK, cap |
| 6 | `tests/test_planner_gates.py` + `test_planner_gates_selector.py` | .90 | Gate test patterns and task builder fixtures |
| 7 | #619 task body (architecture decision) | 1.0 | Tool signature and design |
| 8 | #621 task body (implementation AC) | 1.0 | Implementation contract |

## 3. Analysis

### 3.1 Mock Pattern

All existing MCP kanban tests mock at `owlbear_mcp_kanban.server._run_kanban`.
The `pick_tasks` tool will call `_run_kanban` once with list flags
(`--json --unblocked --not-blocked --unclaimed`). The mock returns
`(json_string, "", 0)` containing a JSON array of task objects.

Pattern from `test_start_work_470.py` (source 2):
```python
mock_run = AsyncMock(return_value=(json_str, "", 0))
with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
    result = await pick_tasks(mcp_ctx, limit=5)
```

Single `_run_kanban` call (vs start_work's 4 calls) simplifies the mock.

### 3.2 Task JSON Structure for Gate Testing

`pick_tasks` will parse `list --json` output. Each task object needs fields
that gates inspect: `title` (atomicity), `status` + `body` (TDD), `body` (clarity).

Minimal task JSON fields from `list --json`:
```json
{"id": 1, "title": "...", "status": "todo", "priority": "important",
 "created": "...", "updated": "...", "tags": [], "depends_on": [],
 "class": "standard", "body": "- item", "file": "..."}
```

Gate behavior summary (from source 4):
| Gate | Trigger | Passes | Fails |
|------|---------|--------|-------|
| Atomicity | word-boundary "and" in title | `"Implement feature"` | `"Fix auth and caching"` |
| TDD | in-progress without `## Test-Writer Notes` | todo, or has notes | in-progress, no notes |
| Clarity | active status without bullet/numbered AC | has `- item`, or ideation/backlog | todo with prose only |

### 3.3 Sort Order

From source 5: `(PRIORITY_RANK[p], STATUS_RANK[s])` ascending.
- Priority: critical(0) < needed(1) < important(2) < nice-to-have(3) < someday(4)
- Status: done(0) < docs(1) < review(2) < in-progress(3) < todo(4) < backlog(5) < ideation(6)

AC says "critical+done-adjacent before someday+ideation" — matches the sort key.

### 3.4 Output Format

From #619: `{"dispatch": [{"task_id": int, "status": str}]}`
Only `task_id` and `status` — no agent mapping, no target_status.

### 3.5 Board Read Flags

From #621 AC: `_run_kanban` called with `--unblocked --not-blocked --unclaimed`.
This means blocked/claimed/archived tasks are excluded at the CLI level, not by gate
logic. Tests should verify these flags are passed to `_run_kanban`.

### 3.6 Edge Cases Beyond AC

| Case | Expected |
|------|----------|
| `_run_kanban` returns rc!=0 | ToolError raised |
| Malformed JSON from CLI | ToolError raised |
| All tasks fail gates | `{"dispatch": []}` |
| limit=0 or negative | Undefined in AC; test default behavior |

## 4. Recommendation (confidence: .90)

**T1 — Autonomous.** Standard test-writing task with well-established patterns.

Test file: `tests/test_pick_tasks_620.py`

Test classes:
1. `TestFromAC_PickTasksSignature` — import, parameter default (limit=25)
2. `TestFromAC_PickTasksBasicPick` — output format, task_id+status fields
3. `TestFromAC_PickTasksGateFiltering` — atomicity/TDD/clarity exclusion
4. `TestFromAC_PickTasksLimit` — limit=5 caps, default=25
5. `TestFromAC_PickTasksSortOrder` — priority+status sorting
6. `TestFromAC_PickTasksEdgeCases` — empty board, error handling
7. `TestFromAC_PickTasksBoardFlags` — `--unblocked --not-blocked --unclaimed` in args

Key design decision: tests mock `_run_kanban` (not gates directly) because the
tool's contract is end-to-end from MCP call to return value. Gate logic testing
through the tool exercises the migration correctness.

Challenge: N/A — trivial T1 test task, no recommendation to challenge.

## 5. Follow-up Tasks

No follow-up tasks needed. #620 is already scoped for the test-writer.
#621 (implementation) already exists and depends on #620.
