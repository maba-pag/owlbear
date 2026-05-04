---
id: 1309
title: 'P1-08: GREEN — Recall implementation (scope filtering, priority ordering,
  body-only format, wildcard block)'
status: backlog
priority: needed
created: 2026-05-04T01:32:27.284697+00:00
updated: 2026-05-04T20:06:52.790338+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
- merged
parent: 1301
depends_on:
- 1308
- 1307
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301

## Acceptance Criteria

- [ ] recall_memory MCP tool registered with parameter schema (agent: required string, categories: optional list, limit: optional int default 20)
- [ ] Agent-scope filtering: returns entries where agent name in scope_agents OR scope_agents=["*"]
- [ ] Unscoped exclusion: entries with scope_agents=[] never returned
- [ ] Wildcard block: agent="*" rejected with descriptive error message
- [ ] Body-only format: each entry rendered as "## {title}
{content}" with no metadata
- [ ] Priority ordering: approved entries sorted before curated entries
- [ ] Limit respected: returns at most N entries (default 20)
- [ ] All #1308 tests pass

## Scope

- In: recall_memory handler, query logic, result formatting
- Out: mutation tools (done in #1307), git integration, consumer wiring
[[2026-05-04]]
MERGED into #1308. The builder for #1308 already implemented recall_memory (commit 26f65acd) — all 1309 AC is satisfied by the existing implementation in serve/mcp-memory/src/owlbear_mcp_memory/tools.py:280-324. Task is redundant. Dependencies (1313, 1315) redirected to 1308.