---
id: 1283
title: 'P1-03: Update cross-references in README, WIRING, h-agent-structure, h-memory-structure'
status: research
priority: needed
created: 2026-05-02T16:01:10.613477+00:00
updated: 2026-05-02T16:08:43.802978+00:00
tags:
- phase-1
- scope:docs
- shared-layer
parent: 1280
depends_on:
- 1282
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1280 and `.owlbear/briefs/draft-neutral-shared/brief.md`

## Acceptance Criteria

- [ ] share/README.md has no dangling references to content removed from owlbear-system.instructions.md
- [ ] share/WIRING.md has no dangling references to removed content
- [ ] h-agent-structure SKILL.md "Current stubs" table updated if it referenced moved content
- [ ] h-memory-structure SKILL.md updated if it referenced owlbear-system.instructions.md by OwlBear-specific content
- [ ] No broken internal links introduced by the split
- [ ] Tests from #1281 pass for the cross-reference assertions

## Scope

- IN: share/README.md, share/WIRING.md, h-agent-structure/SKILL.md, h-memory-structure/SKILL.md
- OUT: owlbear-system.instructions.md itself (#1282), init.py (#1284)


**Additional scope (from research File 20):** Extend `agent-ecosystem.instructions.md` applyTo to also cover `.owlbear/agents/**,.owlbear/skills/**,.owlbear/instructions/**,.owlbear/prompts/**` so consumers writing to local `.owlbear/` paths get the structural conventions.