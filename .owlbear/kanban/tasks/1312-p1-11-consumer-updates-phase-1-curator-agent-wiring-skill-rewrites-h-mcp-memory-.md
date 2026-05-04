---
id: 1312
title: 'P1-11: Consumer updates Phase 1 — Curator agent wiring + skill rewrites (h-mcp-memory,
  h-memory-structure, w-mem-curation)'
status: research
priority: needed
created: 2026-05-04T01:32:27.358510+00:00
updated: 2026-05-04T01:34:54.307004+00:00
tags:
- phase-2
- scope:agents
- memory
- mcp
parent: 1301
depends_on:
- 1307
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301

## Acceptance Criteria

- [ ] memory-curator.agent.md tools: include ob-memory/list_memories, ob-memory/read_memory, ob-memory/curate_memory, ob-memory/delete_memory
- [ ] vscode/memory removed from memory-curator.agent.md
- [ ] h-mcp-memory skill fully rewritten: 7 tool names, parameters, descriptions, usage patterns, examples
- [ ] h-memory-structure skill updated: new fields (source_agent, approved_at), renamed categories, state model
- [ ] w-mem-curation skill updated: new MCP tool names, auto-state logic documentation, guidance hints
- [ ] Curator can exercise full lifecycle: list -> read -> curate -> delete via MCP tools

## Scope

- In: curator agent file, 3 skill files (h-mcp-memory, h-memory-structure, w-mem-curation)
- Out: general pipeline agents (Phase 2-3, task #1313), review prompt, instruction stubs