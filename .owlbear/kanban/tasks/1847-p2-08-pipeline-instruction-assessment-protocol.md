---
id: 1847
title: 'P2-08: Pipeline instruction — assessment protocol'
status: research
priority: needed
created: 2026-05-24T19:01:58.026379+02:00
updated: 2026-05-24T19:15:26.071648+02:00
tags:
  - phase-2
  - scope:memory
  - docs
parent: 1839
depends_on:
  - 1846
ac:
  - "`pipeline-agents.instructions.md` end_work protocol includes assessment instruction
    directing agents to call `assess_memories` for all recalled memories using the
    exact framing text specified in this task's body. No scoring mechanics are explained."
  - '`r-pipeline-protocol` SKILL.md post-task reflection references memory assessment
    as mandatory when recall_memory was called. Framed as quality categorization,
    not scoring mechanism.'
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1839

## Scope

Update pipeline instructions to include the memory assessment protocol for agents completing tasks.

### In Scope
- pipeline-agents.instructions.md: end_work assessment instruction
- r-pipeline-protocol SKILL.md: post-task reflection reference
- Opaque bucket framing (no score explanation to agents)
- Mandatory when memories were recalled

### Out of Scope
- MCP tool implementation (P2-07)
- Score mechanics (P2-02)
- Agent skill changes beyond protocol instructions

## Domain
share/instructions/ + share/skills/r-pipeline-protocol/



## Exact Framing Text (use verbatim)

> For each recalled memory entry, categorize your experience:
> - **Outstanding** — this entry's guidance was genuinely great for this task
> - **Used but unremarkable** — I applied or referenced this entry's guidance and it was adequate
> - **Didn't use** — I didn't apply or reference this entry's guidance
> - **Factually wrong** — this entry contains incorrect information
>
> \"Apply or reference\" includes: following guidance, avoiding a warned pitfall, or confirming your approach was correct.

This text is the product of deliberate design — do not rephrase or summarize it.
