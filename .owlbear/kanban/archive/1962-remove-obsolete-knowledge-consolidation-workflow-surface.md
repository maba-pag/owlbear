---
id: 1962
title: Remove obsolete knowledge consolidation workflow surface
status: archived
priority: high
created: 2026-07-20T00:33:28.432841+02:00
updated: 2026-07-20T01:03:23.215769+02:00
tags:
  - scope:knowledge
  - agent-ecosystem
  - api-cleanup
  - documentation
parent:
depends_on: []
ac:
  - 'AC1: The knowledge enrichment prompt and workflow describe Phase 1 extraction
    only, and artifact inspection finds no instruction to pull or store consolidation
    candidates.'
  - 'AC2: The MCP knowledge stats maintained type and runtime output omit `consolidation_candidates_remaining`,
    verified by focused stats tests.'
  - 'AC3: Knowledge architecture documentation and agent guidance consistently state
    deterministic canonical identity as the cross-source behavior, verified by targeted
    repository search.'
  - 'AC4: Focused MCP knowledge tests and ecosystem validators pass after removal.'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Remove agent and API guidance for the rejected Phase 2 consolidation architecture. Canonical identity is the maintained cross-source model.

## Scope
- `share/prompts/kb-enrich.prompt.md`
- `share/skills/w-knowledge-enrichment/SKILL.md`
- MCP knowledge stats types/output and their tests
- maintained knowledge architecture references when needed for coherence

## Boundaries
Do not reintroduce SAME_AS, candidate review, or compatibility machinery. Assess whether removing the stats field is a breaking maintained API change; prefer direct removal because the repository policy does not retain legacy surfaces.



## Implementation Notes

Completed directly without pipeline dispatch. Removed Phase 2 consolidation instructions from the enrichment prompt/workflow, removed dual-mode claims from the MCP package README, and removed the hard-coded `consolidation_candidates_remaining` field from the typed and runtime stats response. Canonical identity remains the maintained cross-source model.

Evidence: stale consolidation surface search returned no matches in maintained knowledge guidance/API files; focused stats contract and final integrated gate passed.
