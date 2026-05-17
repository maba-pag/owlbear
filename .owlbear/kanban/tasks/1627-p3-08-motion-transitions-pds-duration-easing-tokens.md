---
id: 1627
title: 'P3-08: Motion/transitions — PDS duration + easing tokens'
status: in-progress
priority: important
created: 2026-05-16T03:37:44.829874+00:00
updated: 2026-05-16T18:14:26.567314+00:00
tags:
  - frontend
  - pds
  - phase-3
parent: 1590
depends_on: []
ac:
  - 'All 3 authored transition declarations use var(--p-duration-sm) for duration
    and var(--p-ease-in-out) for easing: Shell.css .shell (grid-template-columns),
    Shell.css .icon-button (background, border-color), Card.css .card (box-shadow)'
  - Zero transition:all declarations in authored CSS (regression guard)
  - "Tests assert PDS token usage for each migrated declaration: update SidecarCollapse_1549
    regex from '250ms ease' to var(--p-duration-sm)/var(--p-ease-in-out); add assertions
    for .icon-button and .card transitions"
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

PDS duration/easing tokens for state changes (expand/collapse, route transitions).

Scope: Motion/transitions only.
Out of scope: Dark mode, focus-visible, accessibility sweep.

[[2026-05-16T18:18:37+02:00]]
## Research
- Research doc: .owlbear/research/1627-pds-motion-tokens.md
- Sources: 5 studied, 4 high-relevance
- Recommendation: Replace 3 hardcoded transitions with PDS v4 tokens (--p-duration-sm + --p-ease-in-out) (confidence: 0.78)
- AC1 corrected: original referenced --p-transition-duration (internal override) and --p-transition-timing-function (nonexistent); replaced with --p-duration-sm/md and --p-ease-in-out/in/out
- AC2: already satisfied (zero transition:all)
- AC3: N/A for single-route SPA; added qualifier
- Challenge: reconsider — challenger flagged 120→250ms UX change on micro-interactions. Accepted as PDS-aligned (PDS recommends duration-sm for hover effects). Dropped prefers-reduced-motion as out-of-scope (#1628).
- Test impact: SidecarCollapse_1549 test locks current transition regex; must update during implementation
- Commit: 94516868



## Builder Guidance
- The 120ms→250ms bump on hover transitions is intentional (PDS recommends --p-duration-sm for hover effects)
- SidecarCollapse_1549.test.tsx L153 regex must be updated to match token vars instead of hardcoded values
- Card.css.test.ts currently has no transition assertions — add coverage
- prefers-reduced-motion is OUT OF SCOPE (owned by #1628)

[[2026-05-16T19:16:05+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Motion/transition token migration only |
| Interface clarity | PASS | AC now specifies exact declarations + exact tokens |
| Dependency correctness | PASS | Removed dead dep on archived #1622; no remaining deps |
| Module layering | PASS | CSS-only change, no import concerns |
| TDD compliance | PASS | proof_bundle=behavioral; builder writes tests (AC3 encodes coverage) |
| KISS/YAGNI | PASS | 3 declarations, 2 token vars — minimal |
| Premise challenge | PASS | PDS adoption mandates token usage |
| Pattern consistency | PASS | Uses PDS v4 custom properties per design system docs |
| Security surface | PASS | No system boundaries affected |
| Single domain | PASS | Frontend only |

### Challenge Results
- Challenger: reconsider (0.67)
- Findings: AC1 selector-ambiguous, AC3 untestable, proof surface narrow, dep drift
- Architect response: ACCEPTED — refined AC1 to bind tokens to specific selectors, dropped untestable AC3 (N/A route transitions), replaced with concrete test-coverage AC, removed dead dependency on archived #1622

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (test task #1622 was deprecated into this impl task; builder writes tests per AC3)

### Verdict: APPROVE
### Action Taken: Refined AC (3 lines), removed dead dep #1622, added builder guidance, advanced to todo

[[2026-05-16T20:14:26+02:00]]
## Test-Writer Notes

**Test file:** `serve/cockpit/web/src/__tests__/PdsMotionTokens_1627.test.tsx`
**Modified:** `serve/cockpit/web/src/__tests__/SidecarCollapse_1549.test.tsx` (AC3: updated transition regex from '250ms ease' to PDS tokens)
**Commit:** b6a66a9f

### Test class: `TestFromAC_PdsMotionTokens_1627`

| Category | Tests |
|----------|-------|
| Happy path | icon-button uses var(--p-duration-sm); icon-button uses var(--p-ease-in-out); card uses var(--p-duration-sm); card uses var(--p-ease-in-out) |
| Boundary/regression | icon-button no hardcoded ms; card no hardcoded ms |
| **Total** | **6 tests, all FAIL** (AssertionError) |

### AC Coverage

| AC | Tests |
|----|-------|
| AC-1 .shell grid-template-columns | SidecarCollapse_1549 updated regex — asserts var(--p-duration-sm) var(--p-ease-in-out) |
| AC-1 .icon-button background/border-color | 3 tests in PdsMotionTokens_1627 |
| AC-1 .card box-shadow | 3 tests in PdsMotionTokens_1627 |
| AC-2 zero transition:all | Already satisfied by current CSS (no transition:all exists) — no RED test possible; builder must not introduce any |
| AC-3 test assertions in place | SidecarCollapse_1549 updated + new file covers all 3 declarations |

### Fail Verification
quality-runner scoped run: 6/6 FAIL with AssertionError. lint: clean (ESLint exit 0).
