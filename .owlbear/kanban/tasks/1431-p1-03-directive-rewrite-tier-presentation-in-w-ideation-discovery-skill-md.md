---
id: 1431
title: 'P1-03: Directive rewrite + tier presentation in w-ideation-discovery/SKILL.md'
status: todo
priority: needed
created: 2026-05-08T01:00:48.482707+00:00
updated: 2026-05-08T01:01:49.028937+00:00
tags:
- phase-1
- scope:shared
- ideation
- ux
parent: 1428
depends_on:
- 1429
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Rewrite 1 narration directive in `share/skills/w-ideation-discovery/SKILL.md`: Step 3 handoff instruction + Step 1.5 tier presentation. Replace jargon-narrating instructions with purpose-framed alternatives.

Brief: see parent #1428. Full brief at `.owlbear/briefs/draft-ideation-ux/brief.md`.

## Scope

**In:** Directive rewrites in w-ideation-discovery/SKILL.md:
1. Step 3 — currently instructs "End Phase 1 by naming @ideation-mediator..." → rewrite to purpose-framed handoff (what completed + what opens next + how to start)
2. Step 1.5 — tier presentation currently uses raw "Investment Tier: X" → rewrite to conversational calibration ("This feels like a [tier] problem — [plain meaning]. Sound right?")

**Out:** Mediation workflow (#1430). Agent files (#1432). h-ideation foundation (#1429).

## Acceptance Criteria

- [ ] Step 3 handoff directive rewritten: no longer instructs agent to name @ideation-mediator by handle; instead instructs purpose-framed handoff (what's done, what's next, invocation command)
- [ ] Step 1.5 tier presentation rewritten: uses conversational calibration pattern from h-ideation § Transition Patterns
- [ ] Co-located `**Narrate as:**` annotation with concrete example phrase for handoff
- [ ] Behavioral equivalence: user still receives handoff artifacts location and invocation command — only framing changes
- [ ] Grep verification: `grep -n "@ideation-mediator\|Investment Tier:" share/skills/w-ideation-discovery/SKILL.md` — hits in narration guidance carry purpose framing, not bare protocol references
- [ ] References h-ideation § Communication Patterns for vocabulary