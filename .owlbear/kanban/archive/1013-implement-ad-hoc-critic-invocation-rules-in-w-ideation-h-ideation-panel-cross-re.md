---
id: 1013
title: Implement ad-hoc Critic invocation rules in w-ideation + h-ideation-panel
  cross-ref
status: in-progress
priority: important
created: 2026-04-18T23:33:06.671427+00:00
updated: 2026-04-19T13:24:06.475409+00:00
tags:
- type:improvement
- scope:skills
- ideation
parent:
depends_on:
- 1004
blocked: false
block_reason:
claimed_by: odd-rook
claimed_at: 2026-04-19T13:24:06.475409+00:00
---
## Problem
Ad-hoc Critic invocation (user-request + Mediator self-trigger) is not documented in the ideation workflow. Research doc `.owlbear/research/1004-ad-hoc-critic-invocation.md` establishes the gap and recommends Option D.

## Fix
1. **w-ideation SKILL.md** → Add "Ad-hoc Critic Invocations" subsection after "Adaptive Depth" containing:
   - Single structural trigger principle: "When a proposal changes the problem boundary, outcome set, or approach AFTER the corresponding fixed-boundary Critic has already run, the Mediator MAY invoke the Critic on the changed element."
   - User-request path (explicit ask → invoke)
   - MAY (not MUST) for self-trigger — Mediator judgment, consistent with tier calibration
   - Rate limit: at most 1 ad-hoc per user turn (batch multiple changes into one prompt)
   - Tier gating table (Scratch: skip; Tool: judgment; Shared/Production: lean toward invoking)
   - Recording: same as fixed-boundary (Critic returns to Mediator, Mediator presents to user; decisions influenced by findings recorded in decisions.md with rationale)
   - Silent resolution: if self-triggered Critic finds nothing material, continue without mentioning
   - Worked example from research doc (M5 walkthrough artifact addition scenario)
   - Explicit note: ADDITIVE to fixed-boundary checks, not a replacement
2. **h-ideation-panel SKILL.md** → "Standalone Critic Invocations" section: add one row/note acknowledging ad-hoc invocations exist and pointing to w-ideation for the full rule.
3. **w-ideation Verification Checklist** → Add: "Ad-hoc Critic invocations (if any) presented to user when material."

## Acceptance Criteria
- w-ideation has a new "Ad-hoc Critic Invocations" subsection with all elements listed above.
- h-ideation-panel references ad-hoc invocations with a cross-ref to w-ideation (no duplicate trigger logic).
- Worked example shows Mediator self-invocation scenario end-to-end.
- Rule explicitly states this is additive to fixed-boundary checks.
- No changes to ideation-critic.agent.md or ideator.agent.md.

## Context
Research: `.owlbear/research/1004-ad-hoc-critic-invocation.md`. Challenger revised recommendation from .88→.85; key revisions: collapsed 5 triggers to 1 principle, MUST→MAY, added tier gating, DRY-compliant placement.
[[2026-04-19]]
## Research

**Validation pass** — existing research doc from #1004 is current; implementation already present in working tree (uncommitted).

- Research doc: .owlbear/research/1004-ad-hoc-critic-invocation.md (from #1004, complete)
- Sources: 5 studied (all codebase), 4 high-relevance (reused from #1004)
- Recommendation: Option D confirmed — full rule in w-ideation, cross-ref in h-ideation-panel (confidence: 0.85)
- Follow-up tasks created: none — implementation exists in working tree, needs commit cycle
- Decision requests: none (T1 — autonomous skill file modification)

### AC Verification (working tree)

| AC | Status |
|----|--------|
| w-ideation "Ad-hoc Critic Invocations" subsection (trigger principle, MAY, rate limit, tier gating, recording, worked example) | ✅ present |
| h-ideation-panel cross-ref (table row + note, no duplicate logic) | ✅ present |
| Worked example (M5 audit-log scenario, end-to-end) | ✅ present |
| "Additive to fixed-boundary checks" explicit | ✅ present |
| No changes to ideation-critic.agent.md or ideator.agent.md | ✅ confirmed |
| Verification checklist item added | ✅ present |

### Builder note
Both `share/skills/w-ideation/SKILL.md` and `share/skills/h-ideation-panel/SKILL.md` have uncommitted changes implementing all AC items. The builder should commit these rather than re-implement.
[[2026-04-19]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: document ad-hoc Critic invocation rules across two related skill files |
| Interface clarity | PASS | AC specifies exact subsections, elements, cross-ref structure, and exclusions |
| Dependency correctness | PASS | #1004 (research) completed/archived; research doc exists |
| Module layering | PASS | w-ideation owns rules, h-ideation-panel cross-refs — no upward dependency |
| TDD compliance | N/A | Non-impl task (skill docs only) — needs `docs` pass-through tag |
| KISS/YAGNI | PASS | Minimal additions, DRY cross-ref pattern, no over-engineering |
| Premise challenge | PASS | Gap is real — ad-hoc Critic invocation was undocumented |
| Pattern consistency | PASS | Follows existing standalone Critic table pattern in h-ideation-panel |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Both files in ideation skill domain |

### Challenge Results
- Challenger: reconsider (confidence 0.60)
- Primary concern: ideator.agent.md subagent table doesn't mention ad-hoc path (C1)
- Architect response: OVERRIDDEN — AC scope was deliberately set by research challenger (.85); ideator's critical_rules direct to w-ideation skill where rules live; subagent table is quick-reference, not authority. Accepted minor discoverability risk. One-line table update is follow-up candidate, not blocker.
- Secondary concerns (C2–C4): minor edge cases — user-request path is self-explanatory, "material" judgment consistent with existing Mediator patterns, rate limit ambiguity unlikely to cause harm.

### Verdict: APPROVE
### Action Taken: Advanced to todo. Note: task needs `docs` pass-through tag added (no edit_task tool available to architect). Builder job is to commit existing working-tree changes per builder note in task body.
[[2026-04-19]]
## Test-Writer Notes
- Non-impl pass-through: AC references only SKILL.md files (`share/skills/w-ideation/SKILL.md`, `share/skills/h-ideation-panel/SKILL.md`).
- No Python source files, no testable interfaces, no implementation keywords in AC.
- Architect confirmed in task body: "Non-impl task (skill docs only)".
- All 5 AC lines are documentation-structure assertions (section presence, cross-ref, example text, rule wording) — not contract-testable via pytest.
- Passing through to builder.