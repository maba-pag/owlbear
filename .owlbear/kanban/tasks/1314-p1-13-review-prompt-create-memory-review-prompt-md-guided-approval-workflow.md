---
id: 1314
title: 'P1-13: Review prompt — Create memory-review.prompt.md (guided approval workflow)'
status: research
priority: important
created: 2026-05-04T01:32:27.475911+00:00
updated: 2026-05-04T01:34:54.321078+00:00
tags:
- phase-2
- scope:prompts
- memory
- mcp
parent: 1301
depends_on:
- 1312
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301\n\n## Acceptance Criteria\n\n- [ ] memory-review.prompt.md created in share/prompts/\n- [ ] Prompt presents curated entries for user review (list -> read -> decide)\n- [ ] User can approve (approve_memory), request changes (curate_memory), or reject (delete_memory)\n- [ ] Batch commit instruction: all mutations committed at end of review session\n- [ ] Tools listed in prompt frontmatter: ob-memory/list_memories, ob-memory/read_memory, ob-memory/approve_memory, ob-memory/curate_memory, ob-memory/delete_memory\n- [ ] Prompt is self-contained: works without prior context\n\n## Scope\n\n- In: prompt file creation, guided workflow design\n- Out: MCP server code, agent wiring (done in #1312/#1313), tool implementation