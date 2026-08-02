---
id: 664
title: Add architect user-action gate rule and post-AR fast-path to w-arch-review
status: archived
priority: medium
created: 2026-04-06T16:39:08.3017247+02:00
updated: 2026-04-07T02:10:42.0009029+02:00
started: 2026-04-07T02:10:42.0009029+02:00
completed: 2026-04-07T02:10:42.0009029+02:00
tags:
    - phase-3
    - scope:agent-config
    - type:docs
parent: 661
depends_on:
    - 663
class: standard
---

## Objective\nAdd two rules to w-arch-review skill: (1) detection + AR creation for `type:user-action` tasks, (2) post-AR fast-path for completed action requests.\n\n## Context\nFrom #661 research: architect must block `type:user-action` tasks with an action request and fast-approve after `## Action Completed` is written to the body.\n\n## Acceptance Criteria\n- [ ] w-arch-review Step 3 adds BLOCK verdict for `type:user-action` tasks: create AR via scribe, block, end_work(outcome=\"block\")\n- [ ] w-arch-review adds detection heuristics: AC contains physical actions, references external systems, no testable Python interfaces + requires human observation\n- [ ] w-arch-review adds post-AR fast-path: when body contains `## Action Completed` + `type:user-action` tag → verify AC checkboxes → APPROVE\n- [ ] Detection heuristics are concrete enough for deterministic application (not judgment-based)\n\n## Files Affected\n- share/skills/w-arch-review/SKILL.md

[[2026-04-06]] Mon 23:09
## Research
- Research doc: .owlbear/research/architect-user-action-gate-rules.md
- Sources: 6 studied, 6 high-relevance (all internal — #661 research, r-pipeline-protocol §5, agent-common, w-arch-review, #663 body, #597 evidence)
- Recommendation: 4 insertions to w-arch-review/SKILL.md — (1) Step 0 fast-path, (2) Step 2 criterion 13 with deterministic M/S/C heuristic rule, (3) Step 3 BLOCK verdict row, (4) verification checklist item (confidence: .90)
- Follow-up tasks created: none (this task IS the final piece of #661 decomposition)
- Decision requests: none (T1 — documenting existing convention)

### Insertion Points
1. **Step 0** after "Decomposition detection": user-action fast-path — body contains `## Action Completed` + `type:user-action` tag → verify AC → APPROVE (skip Steps 1-3)
2. **Step 2** new criterion 13: deterministic detection heuristics — M1 (no testable Python interface) + M2 (human observation required) + ≥1 signal (physical verbs, external systems, manual steps) + no counter-signals (Python interface, test assertions, conflicting tag)
3. **Step 3** new BLOCK row: `type:user-action` detected → create AR via scribe → block → end_work(outcome="block")
4. **Verification checklist**: new item for user-action detection and handling

### Challenge
SKIPPED — trivial docs task completing fully-designed convention (#661 research, .78→revised, challenger-processed)

[[2026-04-06]] Mon 23:40
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concept (user-action handling) added to one file (w-arch-review/SKILL.md). 4 insertions are all facets of the same feature |
| Interface clarity | PASS | AC1 specifies BLOCK verdict + actions, AC2 lists heuristic signals, AC3 defines trigger conditions + outcome, AC4 sets quality constraint |
| Dependency correctness | PASS | depends_on: [663] — archived. r-pipeline-protocol §5 User-Action Tasks subsection exists (L203-244), agent-common detection table exists (L24-36) |
| Module layering | N/A | Documentation only |
| TDD compliance | PASS | Tagged type:docs — test-writer pass-through |
| KISS/YAGNI | PASS | 4 targeted insertions to one file, minimal scope per research doc |
| Premise challenge | PASS | Convention designed in #661 research, documented by #663. w-arch-review is the architect's procedural guide — these rules close the gap that caused #597's 4+ futile cycles |
| Pattern consistency | PASS | Insertions follow existing w-arch-review structure: Step 0 pre-flight (after decomposition detection), Step 2 numbered criterion, Step 3 verdict table row, verification checklist item |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | All agent-config/pipeline-documentation domain |

### AC Assessment
| AC Line | Verifiable? | Action |
|---------|------------|--------|
| AC1: Step 3 BLOCK verdict for type:user-action (create AR via scribe, block, end_work) | Yes — check Step 3 verdict table for new BLOCK row with specified actions | None |
| AC2: Detection heuristics (physical actions, external systems, no testable Python, human observation) | Yes — check Step 2 for criterion listing these signals | None |
| AC3: Post-AR fast-path (## Action Completed + type:user-action -> verify AC -> APPROVE) | Yes — check Step 0 for fast-path paragraph with trigger conditions and outcome | None |
| AC4: Heuristics deterministic (not judgment-based) | Yes — research doc provides M1/M2/S1-S3/C1-C3 rule with binary outcome and application order; reviewer can verify mechanical application | None |

### Architecture Notes
- Insertion points verified against live w-arch-review/SKILL.md (250 lines, no existing user-action handling)
- Step 0 fast-path after "Decomposition detection" is the right location — conceptually a "task already resolved" check, parallel to decomposition detection
- Step 2 criterion 13 with M/S/C framework from research doc (.owlbear/research/architect-user-action-gate-rules.md §3) provides the deterministic rule AC4 requires
- Step 3 BLOCK verdict joins APPROVE/REFINE/SPLIT/MERGE/REJECT — completes the verdict set
- r-pipeline-protocol §5 User-Action Tasks (L203-244) is the authoritative reference; w-arch-review rules implement the architect-specific gate documented there
- No cross-references or imports at risk; the skill file is self-contained prose

### Challenge Results
- Challenger: FALLBACK — challenger agent not available in current session
- Architect assessment: all criteria PASS, AC is verifiable and specific, documentation-only scope (type:docs tag present), convention fully designed and challenged in #661 research

### Verdict: APPROVE
### Action Taken: Advanced to todo. No AC refinements needed — all 4 lines are specific, verifiable, and aligned with the research doc's insertion plan.

[[2026-04-07]] Tue 00:11
## Test-Writer Notes
- Non-impl pass-through: config/docs only
- Tag: `type:docs` — authoritative non-implementation signal
- Files affected: `share/skills/w-arch-review/SKILL.md` only (SKILL.md — no Python interface)
- AC scan: all 4 AC lines describe insertions to a SKILL.md prose file. No keywords: `implement`, `function`, `class`, `src/`, `.py`, `endpoint`, `API`
- No testable Python interfaces exist or are implied
- No tests written; no tests applicable

[[2026-04-07]] Tue 00:44
## Builder Notes
- Files changed: `share/skills/w-arch-review/SKILL.md` (1 file, 11 insertions, 1 deletion)
- Task type: `type:docs` — non-impl pass-through. No Python code touched.
- All 4 AC insertions applied and verified:
  1. **Step 0 user-action fast-path** (L23): `type:user-action` + `## Action Completed` → verify AC checkboxes → `end_work(outcome="success")`, skip Steps 1–3
  2. **Step 2 criterion 13** (L56–64): M/S/C heuristic rule (C1-C3 counter-signals, M1+M2 mandatory, S1-S3 signals, binary outcome with application order)
  3. **Step 3 BLOCK verdict row** (L87): `type:user-action` detected → scribe AR → `end_work(outcome="block")`
  4. **Verification checklist** (L135, L137): updated criteria count to 13; added `type:user-action` blocks check
- Commit: 3298ea0 — `docs(skills): add user-action gate rules and fast-path to w-arch-review #664`
- Tests: non-impl pass-through — no tests applicable
- Lint: no Python files modified — ruff N/A
- Coverage: N/A

[[2026-04-07]] Tue 01:05
## Review Evidence

**Task type:** `type:docs` — no Python code, no tests, no lint applicable.

**Tests:** N/A (non-implementation pass-through)
**Lint:** N/A (no .py files modified)
**Coverage:** N/A

### AC Compliance

| AC | Evidence location | Status |
|----|-------------------|--------|
| AC1: Step 3 BLOCK verdict for `type:user-action` (scribe AR → block → end_work("block")) | Step 3 verdict table: new BLOCK row with correct trigger condition and exact actions specified | ✅ PASS |
| AC2: Detection heuristics — physical actions (S1), external systems (S2), no testable Python (M1), human observation (M2) | Step 2 criterion 13: M/S/C rule lists all four required heuristic signals across M1, M2, S1, S2 (S3 also present) | ✅ PASS |
| AC3: Fast-path trigger: `type:user-action` tag + `## Action Completed` → verify AC checkboxes → APPROVE | Step 0 User-action fast-path paragraph: exact trigger conditions, verify-checkboxes action, end_work("success"), skip Steps 1–3 | ✅ PASS |
| AC4: Heuristics deterministic (not judgment-based) | Criterion 13 uses M/S/C framework with explicit application order (C1-C3 exit first, then M1+M2 both required, then ≥1 S1-S3), binary outcome — fully mechanical | ✅ PASS |

**Verification checklist insertions:** "All 13 Step 2 criteria evaluated" (count updated from 12); "`type:user-action` tasks blocked (BLOCK verdict) rather than approved" (new item). Both present.

**TestFromAC modifications:** None possible — docs task.
**Deductions:** 0

**Confidence: .97 → PASS**

[[2026-04-07]] Tue 01:08
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | SKILL.md is the deliverable; copilot-instructions.md has no entries for w-arch-review or user-action — no update required |
| 2 | Module docstrings | No | N/A | No .py files touched |
| 3 | External attribution | No | N/A | All 6 sources internal (#661, r-pipeline-protocol, agent-common, w-arch-review, #663, #597) |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Verified | .owlbear/research/architect-user-action-gate-rules.md exists; linked in task body; follow-ups: none (task is final piece of #661 decomposition) |

### Implementation Spot-Check
- Step 0 user-action fast-path: present — `type:user-action` + `## Action Completed` → verify AC → end_work("success"), skip Steps 1–3 ✅
- Step 2 criterion 13: present — M/S/C rule with C1-C3 counter-signals, M1+M2 mandatory, ≥1 S1-S3, binary outcome with application order ✅
- Step 3 BLOCK verdict: present — `type:user-action` detected (Step 2 criterion 13) → scribe AR → end_work("block") ✅
- Verification checklist: "All 13 Step 2 criteria evaluated" (count updated from 12); "`type:user-action` tasks blocked (BLOCK verdict) rather than approved" (new item) ✅

### Files Updated
None — all documentation lives in the deliverable file itself (SKILL.md).

### Scratch Files
None found matching `.owlbear/scratch/664-*` — clean.

[[2026-04-07]] Tue 02:10
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Step 3 BLOCK verdict for type:user-action (scribe AR, block, end_work("block")) | Step 3 verdict table: new BLOCK row at L87 with correct trigger and actions | PASS |
| AC2: Detection heuristics (physical actions, external systems, no testable Python, human observation) | Step 2 criterion 13 at L56-64: M1, M2, S1-S3 signals + C1-C3 counter-signals | PASS |
| AC3: Post-AR fast-path (type:user-action + Action Completed section, verify AC, APPROVE) | Step 0 User-action fast-path at L23: exact trigger conditions, verify-checkboxes, end_work("success"), skip Steps 1-3 | PASS |
| AC4: Heuristics deterministic (not judgment-based) | Criterion 13 M/S/C framework: C1-C3 exit first, M1+M2 both required, 1+ S1-S3, binary outcome with application order | PASS |

### Test Results
- pytest: 3380 passed, 422 failed (all pre-existing, 0 in task scope), 18 skipped. test_planner_gates.py excluded (pre-existing import error)
- ruff: N/A (no .py files modified)

### Architect Quality: 5/5
AC was specific with 4 verifiable insertion points backed by research doc. Builder needed zero improvisation.

### Deduction Breakdown
- AC lines without evidence: 0
- Lint violations: 0 (N/A)
- AC quality score 3 or below: no (5/5)
- Missing reviewer evidence: no (present, detailed, .97 PASS)
- Full-suite failures in task scope: 0

### Confidence: 1.00
### Action: archive

### Commit Verified
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 3298ea0 | docs | share/skills/w-arch-review/SKILL.md | #664 |
