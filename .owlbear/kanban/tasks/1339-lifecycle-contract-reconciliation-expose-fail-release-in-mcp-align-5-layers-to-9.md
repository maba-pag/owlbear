---
id: 1339
title: Reconcile MCP lifecycle tools, guidance, and 9-tool contract
status: backlog
priority: needed
created: 2026-05-04T15:00:05.806598+00:00
updated: 2026-05-04T18:45:09+00:00
tags:
- sync-blocker
- mcp-kanban
- docs
parent:
depends_on:
- 1343
- 1349
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Engine, AgentView, MCP, handbook, README, guidance text, and parameter metadata disagree about lifecycle outcomes and the MCP tool surface. The deployment contract is now confirmed: MCP exposes 9 tools including `create_dr`, and `end_work` supports five outcomes: `success`, `fail`, `reject`, `block`, and `release`.

Decision: expose both `fail` (records failure and releases work) and `release` (silent unclaim) in MCP.

## Acceptance Criteria

1. MCP `end_work` handler accepts `outcome="fail"` and routes to the existing failure lifecycle path.
2. MCP `end_work` handler accepts `outcome="release"` and routes to task claim release without recording failure.
3. MCP server schema/metadata names all five outcomes: `success`, `fail`, `reject`, `block`, `release`.
4. `share/skills/h-mcp-kanban/SKILL.md` lists 9 tools and includes `create_dr` in the tool table.
5. `share/skills/h-mcp-kanban/SKILL.md` documents all five `end_work` outcomes with concise use-when guidance.
6. `serve/mcp-kanban/README.md` matches the 9-tool and 5-outcome contract.
7. `AgentView._BLOCK_AR_HINT` and MCP guidance text refer to the canonical `create_dr` tool, not the stale `scribe agent` wording.
8. MCP parameter metadata patches match actual tool signatures; remove stale/nonexistent patched params and document JSON arrays as arrays, not comma-separated strings.
9. MCP status and priority metadata is either derived from board config or intentionally schema-light; no stale hard-coded `_STATUSES` / `_PRIORITIES` lists can drift from live board config.
10. The lifecycle parameter matrix is explicit and consistent across code, tests, README, and handbook, including the currently tested behavior that valid `success + move_to` is accepted unless a new decision deliberately changes that contract.
11. Tests prevent false greens from generic substring matches such as bare `fail` appearing in unrelated failure prose.
12. Existing MCP behavior tests pass after contract reconciliation.

## Key Files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py`
- `serve/kanban/src/owlbear_kanban/agent_view.py`
- `share/skills/h-mcp-kanban/SKILL.md`
- `serve/mcp-kanban/README.md`
- `tests/test_mcp_end_work_fail_1339.py`

## Audit Evidence

- Live MCP server exposes 9 tools, but the handbook still says 8.
- `EndWorkParams` includes `fail`, but the server tool signature omits it.
- Guidance has already moved toward `create_dr`, while `AgentView._BLOCK_AR_HINT` still mentions the scribe agent.
- Parameter metadata patches still describe older tool params that no longer match the live signatures.
- MCP server metadata currently hard-codes status and priority vocabulary even though the kanban board config is the authority.
- Existing tests/prose conflict around `success + move_to`; newer tests allow valid `move_to`, while older language implies stricter behavior.

## Test-Writer Notes

Existing RED file: `tests/test_mcp_end_work_fail_1339.py`.

Keep table/section tests specific. For example, a documentation test for `fail` should match a table row or explicit outcome section, not any occurrence of the substring in failure-handling prose.

## Source

Deployment audit reconciliation, 2026-05-04.