---
id: 1531
title: Body newline normalization at MCP kanban ingress
status: in-progress
priority: important
created: 2026-05-13T12:28:14.408067+00:00
updated: 2026-05-13T14:06:02.435381+00:00
tags:
  - type:feature
  - scope:mcp-kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_at: 2026-05-13T14:06:02.435381+00:00
archival_reason:
archival_refs: []
---
## Summary

Three-step escape-protected normalization of literal `\\n` (double-escape corruption) at the MCP kanban server ingress boundary. Applies to all 5 text body parameters across 4 tools. Guidance message informs agent when normalization occurs, referencing the documented escape convention.

## Brief

See `.owlbear/briefs/draft-body-newline-normalization/brief.md` for the full design.

## Acceptance Criteria

- [ ] `_normalize_escaped_newlines()` in `server.py` implements three-step protect/normalize/restore
- [ ] All 5 text body parameters normalized before engine calls
- [ ] Guidance message appended when normalization occurs (all 4 tools including `create_dr`)
- [ ] Guidance append is positionally after existing guidance wiring
- [ ] Escape convention works: `\\\\n` in JSON → preserved as literal `\\n` in stored file
- [ ] Tool descriptions document normalization behavior and escape convention
- [ ] Existing MCP kanban tests pass
2026-05-13T12:29:29+00:00
## Planning\n### Decomposition: Body newline normalization at MCP kanban ingress\n- Tasks created: 2\n- Dependency layers: 2\n- Phase: 1\n\n### Task List\n| ID | Title | Priority | Depends On | Tags |\n|----|-------|----------|------------|------|\n| 1532 | P1-01: Tests for body newline normalization at MCP kanban ingress | critical | — | phase-1, scope:mcp-kanban, type:test |\n| 1533 | P1-02: Implement body newline normalization at MCP kanban ingress | critical | 1532 | phase-1, scope:mcp-kanban, type:feature |\n\n### Dependency Graph\n```mermaid\ngraph LR\n  1532[\"#1532 Tests\"] --> 1533[\"#1533 Implement\"]\n```
2026-05-13T12:40:36+00:00
## Architecture Review\n\nDecomposed parent task — planner completed decomposition into #1532 (RED tests) and #1533 (GREEN impl). Verified against codebase:\n\n- `_coerce_to_str()` at L44 confirms placement anchor for `_normalize_escaped_newlines()`\n- `create_task` has no guidance wiring (new); `edit_task`/`end_work` have existing pattern; `create_dr` returns dict\n- 5 params × 4 tools correctly scoped\n- Sentinel approach sound (null bytes can't arrive via JSON MCP transport)\n- Single-file change (server.py) respects module layering\n\n### Verdict: APPROVE (decomposition complete)\n### Action Taken: Advanced parent after verifying subtask structure and brief correctness
2026-05-13T14:05:30+00:00
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_newline_norm_1531.py
- Classes: TestFromAC_NormalizeHelper, TestFromAC_CreateTaskNormalization, TestFromAC_EditTaskNormalization, TestFromAC_EndWorkNormalization, TestFromAC_CreateDrNormalization, TestFromAC_GuidancePositioning, TestFromAC_PassthroughNoNormalization, TestFromAC_ToolDescriptions
- Tests per category: happy 14, edge 8, error 0, boundary 5, passthrough 5, tool-meta 6 (via AC 7)
- Total: 39 tests, all FAIL (ImportError or AssertionError)
- ruff: clean
- AC coverage:
  - AC 1 (_normalize_escaped_newlines helper) → TestFromAC_NormalizeHelper (12 tests)
  - AC 2 (all 5 params normalized) → TestFromAC_Create/Edit/EndWork/CreateDr (3+5+3+3 tests)
  - AC 3 (guidance appended when changed) → tested in each tool class
  - AC 4 (create_dr guidance key) → TestFromAC_CreateDrNormalization
  - AC 5 (guidance positionally after existing) → TestFromAC_GuidancePositioning (2 tests)
  - AC 5/6 (escape convention \\\\n → \\n preserved) → tested in each tool class
  - AC 6 (passthrough: no guidance when unchanged) → TestFromAC_PassthroughNoNormalization (5 tests — anchored with _normalize_escaped_newlines import)
  - AC 7 (tool descriptions mention normalization + escape convention) → TestFromAC_ToolDescriptions (6 tests)