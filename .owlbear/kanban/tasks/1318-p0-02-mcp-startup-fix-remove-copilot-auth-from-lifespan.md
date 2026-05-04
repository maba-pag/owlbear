---
id: 1318
title: 'P0-02: MCP startup fix — remove copilot_auth from lifespan'
status: research
priority: critical
created: 2026-05-04T05:48:37.751521+00:00
updated: 2026-05-04T10:15:38.001657+00:00
tags:
- phase-0
- scope:mcp-knowledge
- knowledge
parent: 1316
depends_on:
- 1317
blocked: false
block_reason:
claimed_at: 2026-05-04T10:15:38.001657+00:00
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.2)

## Acceptance Criteria

- [ ] copilot_auth.py removed from MCP server lifespan — no import, no device-flow
- [ ] IngestPipeline starts with extractor=None; vector search works without LLM
- [ ] Server starts cleanly with `search_knowledge` returning results for ingested content (O1)
- [ ] Cached token at ~/.owlbear/copilot_token.json cleaned up if present
- [ ] All #1317 tests pass green

## Scope

- **In scope:** MCP server lifespan cleanup, copilot_auth removal, test_copilot_server_wiring_888 updates
- **Out of scope:** Entity extraction (agent workers), browser integration, tool surface changes