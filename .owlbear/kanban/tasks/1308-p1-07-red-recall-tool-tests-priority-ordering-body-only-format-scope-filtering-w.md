---
id: 1308
title: 'P1-07: RED — Recall tool tests (priority ordering, body-only format, scope
  filtering, wildcard block)'
status: backlog
priority: needed
created: 2026-05-04T01:32:18.553275+00:00
updated: 2026-05-04T14:50:43.935480+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
parent: 1301
depends_on:
- 1305
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301

## Acceptance Criteria

- [ ] Tests assert recall returns entries where agent name is in scope_agents
- [ ] Tests assert recall includes entries where scope_agents=["*"] (universal)
- [ ] Tests assert recall excludes entries where scope_agents=[] (unscoped)
- [ ] Tests assert recall with agent="*" is code-blocked (rejected with error)
- [ ] Tests assert return format is body-only: title as ## heading, content below, no metadata
- [ ] Tests assert ordering: approved entries first, then curated entries fill remaining slots
- [ ] Tests assert limit parameter works (default 20)
- [ ] All tests fail (RED state)

## Scope

- In: recall_memory query behavior, result format, filtering, ordering
- Out: other 6 tools (already in #1306/#1307), git integration, consumer wiring
[[2026-05-04]]
## Research

Research gate passed — trivial-scope RED task with prescriptive AC and established patterns.

### Findings
1. `recall_memory` does not exist yet in `owlbear_mcp_memory.tools` — ImportError guarantees RED
2. Expected signature (from #1309 AC): `recall_memory(ctx, *, agent: str, categories: list | None = None, limit: int | None = None) -> str`
3. Return format: concatenated "## {title}\n{content}" strings, not metadata dicts
4. Ordering: approved (state_rank 0) before curated (state_rank 1)
5. Scope filtering: include entries where agent in scope_agents OR scope_agents=["*"]; exclude scope_agents=[]
6. Wildcard block: agent="*" raises ToolError
7. Test pattern: follow test_state_machine_1304.py (mock engine, mock ctx, _make_entry factory)

### Implementation approach for test-writer
- File: tests/test_recall_memory_1308.py
- Import recall_memory from owlbear_mcp_memory.tools (causes ImportError = RED guarantee)
- 7 test classes mapping 1:1 to ACs
- Use same _make_ctx/_make_entry helpers as test_state_machine_1304.py
- All tests async (pytest-asyncio)

No research doc needed — no design decisions or trade-offs involved. AC is fully prescriptive.