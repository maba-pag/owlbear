---
id: 1339
title: 'Lifecycle contract reconciliation: expose fail+release in MCP, align 5 layers
  to 9 tools'
status: in-progress
priority: needed
created: 2026-05-04T15:00:05.806598+00:00
updated: 2026-05-04T15:40:01.595750+00:00
tags:
- sync-blocker
- mcp-kanban
- docs
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Engine, AgentView, MCP, handbook, and README disagree on outcomes and tool count. MCP removed `fail` but pipeline protocol documents it. `create_dr` is tool #9 but missing from handbook table.

Decision (confirmed): Expose both `fail` (records failure) and `release` (silent unclaim) in MCP. Official tool count is 9 (including create_dr).

## Acceptance Criteria

1. MCP server end_work handler accepts `outcome="fail"` and routes to engine.end_work(outcome="fail")
2. MCP server end_work handler still accepts `outcome="release"` and routes to engine.release_task()
3. h-mcp-kanban/SKILL.md Tool Summary table lists 9 tools (add create_dr row)
4. h-mcp-kanban/SKILL.md outcome documentation lists all 5 outcomes: success, reject, fail, block, release — each with "use when" guidance
5. mcp-kanban/README.md matches (9 tools, 5 outcomes documented)
6. No regression in passing MCP tests; currently-red guidance tests that expected fail behavior pass
7. AgentView already supports both — verify no changes needed there

## Key Files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- `serve/kanban/src/owlbear_kanban/agent_view.py`
- `share/skills/h-mcp-kanban/SKILL.md`
- `serve/mcp-kanban/README.md`

## Source

Finding 4 in `.owlbear/research/kanban-mcp-deployment-audit.md`
[[2026-05-04]]
## Test-Writer Notes

**Test file:** `tests/test_mcp_end_work_fail_1339.py`

**Classes and distribution:**

| Class | Category | Tests | AC |
|---|---|---|---|
| `TestFromAC_EndWorkFailOutcome` | boundary/happy | 2 | AC1 |
| `TestFromAC_EndWorkOutcomeSpec` | boundary | 2 | AC1+AC2 |
| `TestFromAC_SkillDocToolCount` | error (missing doc) | 2 | AC3 |
| `TestFromAC_SkillDocEndWorkOutcomes` | error (missing doc) | 3 | AC4 |
| `TestFromAC_ReadmeEndWorkOutcomes` | error (missing doc) | 3 | AC5 |

**Total: 12 tests — all FAIL (verified via pytest: 12 failed, 0 passed)**

**AC Coverage:**

| AC | Description | Covered? | Notes |
|---|---|---|---|
| AC1 | MCP server end_work accepts outcome="fail" | ✓ | Type hint Literal check; 5-value count check |
| AC2 | Literal["fail"] added alongside existing values | ✓ | checks both fail∈args AND release∈args |
| AC3 | SKILL.md tool count = 9, create_dr row present | ✓ | two failing tests |
| AC4 | SKILL.md end_work Outcome table has fail row | ✓ | table-row-specific regex (not substring match) |
| AC5 | README.md end_work Outcomes section has fail | ✓ | three failing tests |
| AC6 | Covered via AC1 type hint tests | ✓ | schema derives from Literal |
| AC7 | AgentView already supports fail+release | skip | already-passing behavior; testing would produce green tests |

**Ruff:** clean (exit 0)

**Key test-writer technique:** SKILL.md tests use `| \`fail\`` table-cell pattern rather than bare `"fail" in section` to avoid false-positive match on "On failure: raises ToolError" prose.