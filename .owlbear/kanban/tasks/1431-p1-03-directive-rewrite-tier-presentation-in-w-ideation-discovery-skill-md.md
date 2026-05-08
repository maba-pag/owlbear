---
id: 1431
title: 'P1-03: Directive rewrite + tier presentation in w-ideation-discovery/SKILL.md'
status: review
priority: needed
created: 2026-05-08T01:00:48.482707+00:00
updated: 2026-05-08T13:15:37.907599+00:00
tags:
- phase-1
- scope:shared
- ideation
- ux
- agent
parent: 1428
depends_on:
- 1429
blocked: false
block_reason:
claimed_at: 2026-05-08T13:15:37.907599+00:00
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
[[2026-05-08]]


## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One file, two related directive rewrites (both jargon→purpose in same skill) |
| Interface clarity | PASS | All 6 AC lines specify exact changes with grep verification |
| Dependency correctness | PASS | #1429 archived — Communication Patterns + vocabulary table exist in h-ideation |
| Module layering | PASS | w-ideation-discovery references h-ideation (workflow→handbook direction) |
| TDD compliance | PASS | Prose-only; `agent` pass-through tag added |
| KISS/YAGNI | PASS | Minimal scope — two directive rewrites + verification checklist updates |
| Premise challenge | PASS | Parent brief documents real jargon leakage; before/after Pair 5 grounds the handoff rewrite |
| Pattern consistency | PASS | Follows same co-located `**Narrate as:**` pattern as sibling #1430 |
| Security surface | PASS | No system boundaries — markdown skill file only |
| Single domain | PASS | Ideation agent instructions |

### Builder Guidance
- Step 3 rewrite scope includes verification checklist line 142 (`@ideation-mediator` reference) — AC5 grep covers it
- Step 1.5: section heading can retain "Investment Tier" for navigability; narration instructions must use conversational calibration from h-ideation § Transition Patterns
- Verification checklist line 137 should align with the conversational framing (e.g., "depth calibration confirmed" rather than raw "Investment Tier confirmed")
- Before/After Pair 5 in the brief (`.owlbear/briefs/draft-ideation-ux/brief.md`) is the primary behavioral spec for the handoff rewrite

### Test Depth
- AC1: td:0 (prose rewrite)
- AC2: td:0 (prose rewrite)
- AC3: td:0 (prose annotation)
- AC4: td:0 (behavioral equivalence — reviewer/grep verified)
- AC5: td:0 (grep verification)
- AC6: td:0 (reference check)
- Max depth: 0
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — all td:0
- Architect response: N/A

### Verdict: APPROVE
### Action Taken: Added `agent` pass-through tag. Advancing to todo.
[[2026-05-08]]
Architecture review complete. All 10 criteria PASS. Prose-only task (all td:0), test-writer SKIP. Added `agent` pass-through tag. Challenger skipped per td:0 rule.
[[2026-05-08]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- All 6 AC lines also annotated `td:0` (prose rewrites, grep verification, reference checks — no testable Python interfaces).
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Files changed: `share/skills/w-ideation-discovery/SKILL.md`
- Fixes applied:
  - Rewrote Step 1.5 tier presentation to conversational depth calibration using `h-ideation` `Communication Patterns` wording.
  - Rewrote Step 3 handoff guidance to purpose-framed language (what is complete, what opens next, and how to start).
  - Added co-located `**Narrate as:**` handoff example phrase with concrete `/ideation-mediate` invocation.
  - Updated verification checklist to require purpose-framed handoff instead of handle-based reference.
- Behavioral equivalence evidence:
  - Handoff still includes explicit Phase 2 command and artifact-path expectations; only narration framing changed.
- Grep evidence:
  - `@ideation-mediator|Investment Tier:` in `share/skills/w-ideation-discovery/SKILL.md` => no matches.
- Quality evidence (quality-runner scoped):
  - Tests: 0 passed, 0 failed (no task-scoped tests for prose-only change)
  - Lint: clean=true, violations=[]
  - Coverage: N/A (no Python module touched)
- Local diagnostics:
  - VS Code errors for changed file: none
- Commit:
  - `29341853` `feat: rewrite discovery narration directives (#1431, builder)`