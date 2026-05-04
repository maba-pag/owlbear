---
id: 1304
title: 'P1-03: RED — State machine tests (transitions, auto-promote, auto-downgrade,
  scope gate, deletion)'
status: research
priority: needed
created: 2026-05-04T01:32:18.507736+00:00
updated: 2026-05-04T01:34:21.761749+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
parent: 1301
depends_on:
- 1303
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301\n\n## Acceptance Criteria\n\n- [ ] Tests assert pending -> curated when curate_memory provides scope_agents (auto-promote)\n- [ ] Tests assert pending curate rejected atomically when scope_agents missing (scope gate)\n- [ ] Tests assert curated -> curated on any field edit (stays curated)\n- [ ] Tests assert approved -> curated on any curate_memory call (unconditional auto-downgrade)\n- [ ] Tests assert approved_at set on approve, cleared on downgrade\n- [ ] Tests assert pending -> [removed] via hard-delete (file deleted from disk)\n- [ ] Tests assert curated/approved -> deleted via soft-delete (file retained, state=deleted)\n- [ ] Tests assert deleted is terminal (no transitions out, operations rejected)\n- [ ] Tests assert invalid transitions rejected (pending->approved directly, deleted->any)\n- [ ] All tests fail (RED state)\n\n## Scope\n\n- In: state transition logic, deletion semantics, scope gate validation\n- Out: tool parameter validation, MCP registration, git commits