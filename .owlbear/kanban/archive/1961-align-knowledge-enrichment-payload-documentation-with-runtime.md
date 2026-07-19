---
id: 1961
title: Align knowledge enrichment contract and worker information flow
status: archived
priority: high
created: 2026-07-20T00:33:28.413126+02:00
updated: 2026-07-20T01:16:40.104382+02:00
tags:
  - scope:knowledge
  - agent-ecosystem
  - contract
  - documentation
parent:
depends_on: []
ac:
  - 'AC1: `h-knowledge-ops` and `w-knowledge-enrichment` document the runtime entity
    and edge payload accepted by `store_enrichment`, verified by focused boundary
    tests.'
  - 'AC2: Knowledge-enricher receives the workflow and handbook through required reading
    and has the claim, stats, retry, store, and verification tools used by that workflow.'
  - 'AC3: Prompt, agent, and skills define empty queue as completion and do not claim
    concurrent-worker safety or claim-token fencing absent from runtime.'
  - 'AC4: Focused MCP knowledge tests, agent/skill validators, and targeted stale-contract
    searches pass.'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Make the agent-facing enrichment contract executable against the registered MCP parser and truthful about claim ownership. The runtime parser and store are the contract authorities.

## Scope
- `share/agents/knowledge-enricher.agent.md`
- `share/prompts/kb-enrich.prompt.md`
- `share/skills/h-knowledge-ops/SKILL.md`
- `share/skills/w-knowledge-enrichment/SKILL.md`
- focused MCP knowledge contract tests

## Boundaries
Do not redesign entity identity or silently claim concurrency guarantees absent from the runtime.

## Implementation Notes

Aligned the handbooks and workflow to the runtime local-reference payload: required entity `id`, required edge `source_id`/`target_id`, maintained entity/relation enums, and distinct confidence/weight/metadata fields. Added public `store_enrichment` contract coverage.

The subsequent information-flow audit found that `claim_token` is currently ignored by `store_enrichment`; runtime claim ownership is not fenced. Removed unsafe parallel-worker guidance and false missing/stale-token rejection claims. The worker is now explicitly single-worker and queue-driven until token fencing is implemented.

Evidence: focused enrichment and shaping contracts passed; final MCP knowledge gate passed; agent/skill validators, Ruff, formatting, stale-claim searches, and diff integrity passed.