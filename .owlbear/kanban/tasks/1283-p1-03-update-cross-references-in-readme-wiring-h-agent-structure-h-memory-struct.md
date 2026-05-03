---
id: 1283
title: 'P1-03: Update cross-references in README, WIRING, h-agent-structure, h-memory-structure'
status: backlog
priority: needed
created: 2026-05-02T16:01:10.613477+00:00
updated: 2026-05-03T11:18:27.407184+00:00
tags:
- phase-1
- scope:docs
- shared-layer
parent: 1280
depends_on:
- 1282
blocked: false
block_reason:
claimed_at: 2026-05-03T11:18:27.407184+00:00
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

[[2026-05-02]]
## Research
- Research doc: .owlbear/research/p1-03-cross-reference-update.md
- Sources: 9 studied, 7 high-relevance
- Recommendation: T1 autonomous — 5 files, ~7 line changes (confidence: 0.92)
- Follow-up tasks created: none (this task IS the implementation task)
- Decision requests: none
- Dependency added: depends_on #1282 (must complete first to know new description text)

### Key findings
- 2 description references need updating after #1282 (README.md:97, h-agent-structure:344)
- agent-ecosystem.instructions.md applyTo extension requires 4 mirror updates (README.md, h-agent-structure, WIRING.md ×2)
- h-memory-structure § Memory Governance reference is SAFE (§3 stays in file)
- WIRING.md filename references are SAFE (filename unchanged)
- Challenge: skipped (trivial cross-reference inventory)