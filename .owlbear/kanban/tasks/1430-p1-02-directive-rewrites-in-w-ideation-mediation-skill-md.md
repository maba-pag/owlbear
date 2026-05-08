---
id: 1430
title: 'P1-02: Directive rewrites in w-ideation-mediation/SKILL.md'
status: review
priority: needed
created: 2026-05-08T01:00:48.467318+00:00
updated: 2026-05-08T13:15:28.958515+00:00
tags:
- phase-1
- scope:shared
- ideation
- ux
- agent
parent: 1428
depends_on: []
blocked: false
block_reason:
claimed_at: 2026-05-08T13:15:28.958515+00:00
archival_reason:
archival_refs: []
---

## Objective

Rewrite 3 narration directives in `share/skills/w-ideation-mediation/SKILL.md` to replace jargon-narrating instructions with purpose-framed alternatives. Add co-located `**Narrate as:**` annotations.

Brief: see parent #1428. Full brief at `.owlbear/briefs/draft-ideation-ux/brief.md`.

## Scope

**In:** 3 directive rewrites in w-ideation-mediation/SKILL.md:
1. Step 1.5 — currently instructs "Tell the user you are switching..." → rewrite to purpose-framed announcement
2. Step 2 — currently instructs "Tell the user which late-domain panelists..." → rewrite to purpose-framed roster introduction
3. Disclosure Ladder — add depth-control verbal cues from h-ideation § Communication Patterns

**Out:** Discovery workflow (#1431). Agent files (#1432). h-ideation foundation (#1429).

## Acceptance Criteria

- [ ] Step 1.5 directive rewritten: no longer instructs agent to name internal switching mechanism; instead instructs purpose-framed announcement (what's happening + why)
- [ ] Step 2 directive rewritten: no longer instructs agent to enumerate panelist agent names; instead instructs purpose-framed introduction (which reviews + why those angles)
- [ ] Disclosure Ladder updated with verbal cues from h-ideation § Depth-Control Verbal Cues
- [ ] Each rewritten directive has a co-located `**Narrate as:**` annotation with a concrete example phrase
- [ ] Behavioral equivalence: same information reaches the user (which reviews, what's happening next) — only framing changes
- [ ] Grep verification: `grep -n "M3.5\|O15\|ideation-architect\|ideation-security" share/skills/w-ideation-mediation/SKILL.md` — hits in narration guidance positions carry explanatory context or appear in technical routing (not user-facing phrasing)
- [ ] References h-ideation § Communication Patterns for vocabulary (cross-reference, not duplication)
[[2026-05-08]]


## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | 3 directive rewrites + Disclosure Ladder cues, all in one file, all same change type |
| Interface clarity | PASS | AC names exact lines (Step 1.5 line 5, Step 2 line 2, Disclosure Ladder), format (`**Narrate as:**`), and grep verification command |
| Dependency correctness | PASS | Removed stale dep on #1429 (task record absent from board). Deliverable (Communication Patterns section in h-ideation/SKILL.md line 182+) is already in place with vocabulary table, narration principles, transition patterns, boundary heuristic, and depth-control verbal cues |
| Module layering | N/A | Markdown skill files only |
| TDD compliance | PASS | Non-implementation task (markdown prose). Added `agent` pass-through tag for test-writer skip |
| KISS/YAGNI | PASS | Minimal scope: 3 directive rewrites + 1 Disclosure Ladder update. No new abstractions |
| Premise challenge | PASS | Jargon leakage is a real observed problem (brief Pairs 1-6 demonstrate concrete failure modes). Communication Patterns section provides the replacement vocabulary |
| Pattern consistency | PASS | Follows the brief's approach (mechanism 2: directive rewrites with co-located annotations) |
| Security surface | N/A | No system boundaries affected |
| Single domain | PASS | Ideation/UX only |

### Design Diverge
- Trigger: skipped — single clear approach (rewrite directives per brief specification)

### Challenge Results
- Challenger: SKIPPED — all td:0

### Test Depth
- All AC lines: td:0 (markdown prose edits, grep-verified)
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Removed stale dependency on non-existent #1429 (deliverable already in place). Added `agent` pass-through tag. Advanced to todo.
[[2026-05-08]]
Architecture review complete. All criteria PASS. Removed stale dep #1429 (task record absent, deliverable already in place in h-ideation/SKILL.md). Added `agent` pass-through tag. All AC lines td:0 — test-writer SKIP.
[[2026-05-08]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- All AC lines td:0 (markdown prose edits, grep-verified). Architecture review confirms test-writer SKIP.
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Verified pass-through marker in `## Test-Writer Notes` ("Non-implementation task").
- Passing through to review per `w-tdd-green` Step 0a.