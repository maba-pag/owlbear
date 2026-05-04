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

Brief: see parent #1301\n\n## Acceptance Criteria\n\n- [ ] memory-curator.agent.md tools: include ob-memory/list_memories, ob-memory/read_memory, ob-memory/curate_memory, ob-memory/delete_memory\n- [ ] vscode/memory removed from memory-curator.agent.md\n- [ ] h-mcp-memory skill fully rewritten: 7 tool names, parameters, descriptions, usage patterns, examples\n- [ ] h-memory-structure skill updated: new fields (source_agent, approved_at), renamed categories, state model\n- [ ] w-mem-curation skill updated: new MCP tool names, auto-state logic documentation, guidance hints\n- [ ] Curator can exercise full lifecycle: list -> read -> curate -> delete via MCP tools\n\n## Scope\n\n- In: curator agent file, 3 skill files (h-mcp-memory, h-memory-structure, w-mem-curation)\n- Out: general pipeline agents (Phase 2-3, task #1313), review prompt, instruction stubs