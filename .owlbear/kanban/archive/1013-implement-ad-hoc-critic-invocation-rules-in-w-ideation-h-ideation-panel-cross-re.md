---
id: 1013
title: Implement ad-hoc Critic invocation rules in w-ideation + h-ideation-panel
  cross-ref
status: archived
priority: medium
created: 2026-04-18 23:33:06.671427+00:00
updated: 2026-04-19 14:10:48.245669+00:00
tags:
- type:improvement
- scope:skills
- ideation
parent:
depends_on:
- 1004
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
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
[[2026-04-19]]
## Builder Notes
- Non-implementation task — skill docs only.
- w-ideation SKILL.md: "Ad-hoc Critic Invocations" section already committed (commit 7c06be2f, prior cycle); confirmed all AC elements present (trigger principle, MAY, rate limit, tier gating, recording, worked example, additive note, verification checklist item).
- h-ideation-panel SKILL.md: cross-ref row + note committed in b186681c — table row for ad-hoc + pointer to w-ideation, no duplicate trigger logic.
- Commit: b186681c `docs(skills): ad-hoc Critic invocation rules in w-ideation + h-ideation-panel cross-ref (#1013, builder)`
- No pytest run needed (no Python changes). Ruff clean (no Python changes).
- All 5 AC lines verified present in working tree before commit.
[[2026-04-19]]
## Review Evidence

### Task Type
Docs-only (skill files) — no Python changes, no tests to run, no lint to run. Quality-Runner not invoked (no applicable scope). Code-reader pattern followed via direct file reads.

### Changed Files
- `share/skills/w-ideation/SKILL.md` (commit 7c06be2f + b186681c)
- `share/skills/h-ideation-panel/SKILL.md` (commit b186681c)

### Agent File Constraint Check
- `share/agents/ideation-critic.agent.md` — grep for "ad-hoc": no matches ✅
- `share/agents/ideator.agent.md` — grep for "ad-hoc": no matches ✅

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| w-ideation "Ad-hoc Critic Invocations" subsection present after "Adaptive Depth" | Section found at correct location in file; heading present | COVERED |
| Trigger principle (verbatim: "changes the problem boundary…MAY invoke") | w-ideation: "When a proposal changes the problem boundary, outcome set, or approach AFTER the corresponding fixed-boundary Critic has already run, the Mediator MAY invoke the Critic on the changed element." | COVERED |
| User-request path (explicit ask → invoke) | w-ideation "User-Request Path" subsection present | COVERED |
| MAY (not MUST) | "Mediator MAY invoke" — MAY used consistently, never MUST | COVERED |
| Rate limit: at most 1 ad-hoc per user turn (batch) | w-ideation: "At most one ad-hoc invocation per user turn. If multiple changes surface in a single statement, batch them into one focused Critic prompt." | COVERED |
| Tier gating table (Scratch: skip; Tool: judgment; Shared/Production: lean toward) | Table present with exact three rows matching spec | COVERED |
| Recording: same as fixed-boundary (decisions.md with rationale) | "Recording Treatment" section present; mirrors fixed-boundary pattern | COVERED |
| Silent resolution: self-triggered, nothing material → no mention | "Silent resolution" paragraph: "the Mediator does NOT surface this to the user. Continue without mentioning the check." | COVERED |
| Worked example (M5 walkthrough, audit-log artifact, Mediator self-trigger, end-to-end) | "Worked Example" section: M5 scenario, audit-log artifact, Critic invoked, findings presented, both accept and reject outcomes documented | COVERED |
| ADDITIVE note (not a replacement) | "Ad-hoc Critic invocations are **additive** to the four fixed-boundary standalone checks (after M1, M2, M4, M5). They do not replace them." | COVERED |
| h-ideation-panel: table row + note cross-ref to w-ideation, no duplicate trigger logic | Row "Ad-hoc (any moment) — see `w-ideation` → Ad-hoc Critic Invocations" present; note paragraph cross-refs trigger conditions, rate limiting, tier gating, worked example; no duplicate rules | COVERED |
| Verification checklist item added | "- [ ] Ad-hoc Critic invocations (if any) presented to user when material; silent resolution applied when non-material" present in checklist | COVERED |
| No changes to ideation-critic.agent.md or ideator.agent.md | grep confirms zero ad-hoc mentions in both files | COVERED |

### Deductions
None. All 13 verifiable assertions map directly to file content. Each assertion would produce a detectable absence if the element were missing.

### Verdict
Confidence: .96 → PASS
[[2026-04-19]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Skill docs only; copilot-instructions.md has no ideation/skills tables — no update needed |
| 2 | Module docstrings | No | N/A | No Python files changed |
| 3 | External attribution | No | N/A | All sources were internal codebase files (task body: "5 studied (all codebase)") |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Verified | `.owlbear/research/1004-ad-hoc-critic-invocation.md` exists; linked in task body; follow-ups noted as none |

### Files Updated
None — docs-only task with no documentation gaps found.

### Scratch Files
None found matching `.owlbear/scratch/1013-*`.

### Verification
- `## Review Evidence` section present, confidence .96 ✅
- `share/skills/w-ideation/SKILL.md` line 353: `## Ad-hoc Critic Invocations` after `## Adaptive Depth` (line 328) ✅
- h-ideation-panel: table row + additive note present, no duplicate trigger logic ✅
- Additive note, MAY, rate limit, tier gating, silent resolution, worked example, verification checklist item — all confirmed present via grep ✅
[[2026-04-19]]
## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| w-ideation \"Ad-hoc Critic Invocations\" subsection after Adaptive Depth | SKILL.md lines 353-407, after Adaptive Depth at 272-319 | PASS |\n| All required elements (trigger principle/MAY/rate limit/tier gating/recording/silent resolution/worked example/additive note) | Each element confirmed at specific lines: MAY at L364-365, rate limit L367, tier table L371-377, recording L379-384, silent resolution L375, worked example L385-391, additive L355 | PASS |\n| h-ideation-panel cross-ref row + note, no duplicate trigger logic | Table row L97, cross-ref note L99, no duplicate rules | PASS |\n| Worked example (M5 audit-log, end-to-end) | L385-391: artifact addition, Critic flags duplication, user decides | PASS |\n| No changes to ideation-critic.agent.md or ideator.agent.md | grep confirms zero ad-hoc mentions in both files | PASS |\n| Verification checklist item added | L416: ad-hoc Critic checklist item present | PASS |\n\n### Test Results\n- pytest: 664 passed, 27 failed (all pre-existing, outside task scope: cockpit_launch 19, outputschema_541 4, search_v2 1, phase_a_config 1, test_cockpit_launch 2)\n- ruff: clean\n\n### Architect Quality: 4/5\nSpecific AC with exact elements, placement constraints, and exclusions. Minor gap: ideator.agent.md subagent table discoverability deferred as follow-up (reasonable per architect override of challenger C1).\n\n### Deduction Breakdown\n- AC lines without evidence: 0 (all 6 verified) = no deduction\n- Lint violations: 0 = no deduction\n- AC quality score 4 (> 3) = no deduction\n- Reviewer evidence: present, detailed, 13 assertions mapped = no deduction\n- Full-suite failures in scope: 0 = no deduction\n\n### Confidence: .98\n### Action: archive