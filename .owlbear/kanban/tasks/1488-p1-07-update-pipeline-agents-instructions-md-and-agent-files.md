---
id: 1488
title: 'P1-07: Update pipeline-agents.instructions.md and agent files'
status: backlog
priority: needed
created: 2026-05-11T09:00:01.154177+00:00
updated: 2026-05-11T09:03:05.494557+00:00
tags:
- pipeline
- convention
- scope:instructions
- agent
parent: 1481
depends_on:
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

## Acceptance Criteria

1. `pipeline-agents.instructions.md` references proof-bundle instead of td:N in all relevant sections
2. Agent files (builder.agent.md, reviewer.agent.md) dispatch tables updated to reference proof-bundle
3. No td:N terminology in instruction or agent file prose

## Scope

- In: `share/instructions/pipeline-agents.instructions.md`, `share/agents/*.agent.md`
- Out: skill files (covered by earlier tasks)

Proof bundle: skip
Brief: see parent #1481