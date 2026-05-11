---
id: 1490
title: 'P1-07: Cross-cutting td:N cleanup in instructions and agents'
status: backlog
priority: important
created: 2026-05-11T09:00:35.655841+00:00
updated: 2026-05-11T09:00:55.437013+00:00
tags:
- pipeline
- convention
- scope:skills
parent: 1481
depends_on:
- 1482
- 1483
- 1484
- 1485
- 1486
- 1487
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria\n\n1. `pipeline-agents.instructions.md` references proof-bundle taxonomy instead of td:N\n2. Relevant agent `.agent.md` files (builder, reviewer) reference proof-bundle in dispatch tables\n3. Final grep verification: no `(td:N)` or `td:0`/`td:1`/`td:2` annotations remain in any active skill, instruction, or agent file\n\n## Scope\n\n- In: `share/instructions/pipeline-agents.instructions.md`, agent files with td:N references\n- Out: Archived tasks, brief documents (historical references are fine)\n\nProof bundle: skip\nBrief: see parent #1481