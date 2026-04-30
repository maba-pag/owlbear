---
id: 1196
title: 'P1-XX: Add task_id input validation at MCP boundary for decisions.create_dr'
status: review
priority: needed
created: 2026-04-30T07:17:17.451013+00:00
updated: 2026-04-30T08:18:57.492989+00:00
tags:
- phase-1
- scope:kanban
parent: 1179
depends_on: []
blocked: false
block_reason:
claimed_by: near-hound
claimed_at: 2026-04-30T08:18:57.492989+00:00
archival_reason:
archival_refs: []
---

## Objective

Add input validation for the raw `task_id` parameter at the MCP boundary (`serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:429-449`) before it is forwarded to `decisions.create_dr`.

## Acceptance Criteria

- [ ] Numeric-only check rejects non-numeric / wildcard / empty `task_id` values at the MCP boundary layer with a `ToolError` before `decisions.create_dr` is called (td:2)
- [ ] Invalid `task_id` values return an MCP error response and never reach `decisions.create_dr` (td:2)
- [ ] Tests prove rejection of: empty string, wildcard (`*`), path-traversal (`../`), non-numeric strings (td:2)
- [ ] Valid numeric task IDs (string `"42"` or int `42`) are coerced to `int` before forwarding to `decisions.create_dr` (td:1)

## Context

- Architect loop-breaker cycle 7 ruling on #1180
- Parent: #1179
- Location: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` lines 429-449
- Downstream: `decisions.create_dr` expects `task_id: int` and uses it in filename construction
- Pattern: inline validation similar to the `request_type` check already present in `create_dr`

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Validates one parameter at one boundary |
| Interface clarity | PASS | Clear inputs (str/int), outputs (ToolError or int forwarded) |
| Dependency correctness | PASS | No deps needed; standalone boundary guard |
| Module layering | PASS | MCP layer validates before calling kanban engine layer |
| TDD compliance | PASS | Task will flow through test-writer (RED) → builder (GREEN) |
| KISS/YAGNI | PASS | Minimal inline check; no new abstraction needed |
| Premise challenge | PASS | Path-traversal via filename interpolation is a real vulnerability |
| Pattern consistency | PASS | Mirrors existing `request_type` inline check at same location |
| Security surface | PASS | This task IS the security boundary fix |
| Single domain | PASS | MCP boundary only (scope:kanban) |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| task_id contains `../` | Path traversal in DR filename | None (silent write) | NO → fixed by this task | File written outside decisions dir |
| task_id is empty | Empty filename segment | Possible OSError | NO → fixed by this task | Corrupted filename |
| task_id is `*` | Glob expansion in engine.edit_task | Unexpected match | NO → fixed by this task | Wrong task mutated |

### Design Diverge
- Skipped: single clear approach (inline validation before forwarding), no competing designs

### Challenge Results
- Challenger: reconsider (confidence 0.18)
- Architect response: rebutted — challenger misread context as code-review of completed work; task is in backlog awaiting implementation. Valid point about str→int coercion incorporated into refined AC4.

### Test Depth
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC4 to specify int coercion (not passthrough), added test-depth annotations, advancing to todo

[[2026-04-30]]
## Architecture Review

Reviewed MCP boundary for `create_dr` tool. Confirmed path-traversal vulnerability: raw `task_id` flows into `f"{task_id}-{slug}.md"` filename construction in `decisions.create_dr`. Refined AC4 to specify int coercion (downstream expects `task_id: int`). All 10 criteria PASS. Challenger rebutted (misread backlog task as completed work). Advancing to todo.
[[2026-04-30]]
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_1196.py
- Classes: TestFromAC_CreateDrTaskIdValidation
- Tests per category: happy 0, edge 2, error 5, boundary 1
- Total: 8 tests, all FAIL
- ruff: clean

AC coverage:
| AC line | Tests |
|---------|-------|
| AC1 (td:2): numeric-only check rejects invalid task_id with ToolError | test_empty_string_rejected, test_wildcard_rejected, test_path_traversal_rejected, test_non_numeric_string_rejected, test_mixed_alphanumeric_rejected |
| AC2 (td:2): invalid never reaches decisions.create_dr | test_wildcard_does_not_reach_decisions_create_dr, test_empty_string_does_not_reach_decisions_create_dr |
| AC3 (td:2): explicit rejection proof for each listed invalid value | covered by AC1 tests (empty, wildcard, path-traversal, non-numeric each have dedicated test) |
| AC4 (td:1): numeric string coerced to int | test_numeric_string_coerced_to_int_before_forwarding |

Failure reasons:
- Tests 1-7: pytest.raises(ToolError) → 'DID NOT RAISE' (no validation in current code)
- Test 8: '42' (str) forwarded as-is; isinstance(task_id, int) fails
[[2026-04-30]]
## Builder Notes
- Implementation: added MCP boundary validation/coercion for `create_dr(task_id)` in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py.
- Files changed: serve/mcp-kanban/src/owlbear_mcp_kanban/server.py
- Fixes applied:
  - Accept `task_id` as `str | int` at tool boundary.
  - Reject invalid values (`""`, `"*"`, `"../"`, non-numeric/mixed strings) with `ToolError("task_id must be numeric")` before engine-layer call.
  - Coerce valid numeric string IDs (e.g. `"42"`) to `int` before forwarding to `decisions.create_dr`.
  - Forward already-int IDs unchanged.
- Test results (quality-runner, scoped): 8 passed, 0 failed, 0 skipped for tests/test_mcp_kanban_1196.py.
- Coverage (quality-runner scoped report): `owlbear_mcp_kanban.server` reported 26% in scoped run context.
- Lint: clean (ruff clean for touched source + task test file).
- Durable module-level test file check: tests/test_mcp_kanban.py not present in workspace; durable single-file rerun skipped.
- Evidence summary: RED confirmed first (8 failing TestFromAC cases: missing ToolError + missing int coercion), then GREEN confirmed after single-file surgical patch.

### Reflection
- Boundary validation at MCP entrypoint is sufficient to block traversal/wildcard payloads before filesystem-sensitive downstream code.
- String-to-int coercion belongs at API boundary when downstream file naming assumes integer IDs.
- Scoped quality evidence is fast and reliable for AC closure, but module-percent coverage can underrepresent narrowly-scoped fixes in large files.

Commit:
- 4301b3d7 fix: validate create_dr task_id boundary (#1196, builder)