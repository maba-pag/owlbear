---
id: 1308
title: 'P1-07: RED — Recall tool tests (priority ordering, body-only format, scope
  filtering, wildcard block)'
status: research
priority: needed
created: 2026-05-04T01:32:18.553275+00:00
updated: 2026-05-04T01:34:21.788810+00:00
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