---
id: 1313
title: 'P1-12: Consumer updates Phase 2-3 — All pipeline agents + instruction updates
  (save_memory, recall_memory rollout)'
status: research
priority: important
created: 2026-05-04T01:32:27.397472+00:00
updated: 2026-05-04T01:34:54.314862+00:00
tags:
- phase-2
- scope:agents
- memory
- mcp
parent: 1301
depends_on:
- 1312
- 1309
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301

## Acceptance Criteria

- [ ] All ~12 pipeline agents have ob-memory/save_memory and ob-memory/recall_memory in tools: array
- [ ] vscode/memory removed from all pipeline agent .agent.md files
- [ ] agent-common.instructions.md updated: recall_memory pre-flight pattern replaces old memory pattern
- [ ] r-pipeline-protocol skill updated: Knowledge Pre-flight section references save_memory/recall_memory
- [ ] No agent file references old tool names (query_memory, add_memory, update_entry, delete_entry)
- [ ] Big-bang replacement complete: no coexistence of old and new paths

## Scope

- In: all pipeline agent.md files, agent-common.instructions.md, r-pipeline-protocol skill
- Out: curator agent (done in #1312), review prompt (#1314), MCP server code