---
id: 493
title: Add TOOLS_EXCLUDE config to knowledge and project MCP servers
status: archived
priority: medium
created: 2026-03-31 06:37:25.241201+02:00
updated: 2026-04-02 02:58:52.964543+02:00
started: 2026-04-02 02:58:52.515744+02:00
completed: 2026-04-02 02:58:52.515744+02:00
tags:
- scope:mcp
- ' type:build'
- ' phase-2'
depends_on:
- 473
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Add per-server TOOLS_EXCLUDE env var support to mcp-knowledge and mcp-project servers, matching the pattern from mcp-kanban (#473).

## Acceptance Criteria

- [ ] mcp-knowledge server.py: add `_apply_tool_exclusions(server)` that reads `KNOWLEDGE_TOOLS_EXCLUDE` env var (comma-separated tool names), calls `server.remove_tool()` per name, silently ignores invalid/unknown names
- [ ] mcp-project server.py: add `_apply_tool_exclusions(server)` that reads `PROJECT_TOOLS_EXCLUDE` env var (comma-separated tool names), calls `server.remove_tool()` per name, silently ignores invalid/unknown names
- [ ] Both `app_lifespan` functions call `_apply_tool_exclusions(_server)` before `yield`
- [ ] Default (no env var set): all tools registered (backward-compatible)
- [ ] `__all__` in both server modules updated to include `_apply_tool_exclusions`
- [ ] Tests for each server: exclude one tool, exclude multiple, exclude none, invalid/unknown name (4 scenarios x 2 servers)
- [ ] Docs updated: `skills/knowledge-ops/SKILL.md`, `skills/mcp-project/SKILL.md`, and `docs/setup-guide.md` document the new env vars (matching `skills/mcp-kanban/SKILL.md` Configuration section pattern)

## Design Notes

- Same pattern as #473 (KANBAN_TOOLS_EXCLUDE) applied to the other two servers
- Reference impl: `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` L72-90
- Reference test: `tests/test_kanban_tools_exclude_491.py`
- Reference docs: `skills/mcp-kanban/SKILL.md` L72-89
- Each server implements the same simple pattern independently (no shared library; package boundary rules enforce server isolation)
- ~12 LOC per server

## Dependencies

- Depends on #473 (pattern established in mcp-kanban, archived)

[[2026-04-01]] Wed 23:02
## Test-Writer Notes
- Test file: tests/test_tools_exclude_493.py
- Classes: TestFromAC_KnowledgeToolExclusions, TestFromAC_ProjectToolExclusions, TestFromAC_KnowledgeLifespanExclusion, TestFromAC_ProjectLifespanExclusion, TestFromAC_AllExports
- Tests per category: happy 8, edge 8, error 4, boundary 6, lifespan 8, exports 2
- Total: 30 tests (file fails at collection with ImportError — _apply_tool_exclusions not yet in either server)
- ruff: clean
- AC coverage:
  - KNOWLEDGE_TOOLS_EXCLUDE read, remove_tool called: test_exclude_single*, test_exclude_multiple*
  - PROJECT_TOOLS_EXCLUDE read, remove_tool called: TestFromAC_ProjectToolExclusions (same set)
  - Default no env var, no removals: test_no_env_var_remove_tool_never_called (both)
  - Invalid/unknown names silently ignored: test_invalid_tool_name_does_not_raise (both)
  - app_lifespan calls _apply_tool_exclusions before yield: TestFromAC_*LifespanExclusion
  - __all__ updated: TestFromAC_AllExports

[[2026-04-02]] Thu 01:56
## Review Evidence
pytest: 30 passed, 0 failed
ruff: clean
coverage: mcp-knowledge/server.py 61%, mcp-project/server.py 61% (pre-existing tool bodies; _apply_tool_exclusions fully exercised)
All 5 TestFromAC_* classes preserved unchanged.
All 13 AC lines verified: KNOWLEDGE_TOOLS_EXCLUDE read + remove_tool called; PROJECT_TOOLS_EXCLUDE read + remove_tool called; silently ignores invalid names; app_lifespan calls _apply_tool_exclusions before yield (both servers); default no-env backward compatible; __all__ updated in both; 30 tests pass (4 scenarios x 2 servers + edge/boundary); all 3 docs updated (knowledge-ops/SKILL.md L209-219, mcp-project/SKILL.md Configuration section, docs/setup-guide.md L179+206).
Security: safe. No new deps. Verdict: PASS .97

[[2026-04-02]] Thu 02:58
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| _apply_tool_exclusions in mcp-knowledge reads KNOWLEDGE_TOOLS_EXCLUDE | server.py L53-68, 10 unit tests | PASS |
| _apply_tool_exclusions in mcp-project reads PROJECT_TOOLS_EXCLUDE | server.py L44-59, 10 unit tests | PASS |
| Both app_lifespan call _apply_tool_exclusions before yield | knowledge L96, project L83, 8 lifespan tests | PASS |
| Default (no env var): all tools registered | empty-env tests confirm no removals | PASS |
| __all__ updated in both modules | knowledge L101, project L22, 2 export tests | PASS |
| Tests: 4 scenarios x 2 servers | 30 tests pass (test_tools_exclude_493.py) | PASS |
| Docs updated: knowledge-ops, mcp-project, setup-guide | grep confirms env vars documented in all 3 files | PASS |

### Test Results
- pytest (task): 30 passed, 0 failed
- pytest (full suite): 2256 passed, 355 failed (pre-existing RED-phase tests from other tasks, 0 from #493)
- ruff: all checks passed

### AC Quality Score: 5/5
AC was specific, complete, referenced pattern from #473. No builder improvisation needed.

### Reviewer Evidence
Present and detailed: .97 PASS verdict with per-AC-line verification.

### Deduction breakdown: none (all AC verified with evidence, lint clean, tests pass, reviewer evidence thorough)
### Confidence: 1.00
### Action: archive
