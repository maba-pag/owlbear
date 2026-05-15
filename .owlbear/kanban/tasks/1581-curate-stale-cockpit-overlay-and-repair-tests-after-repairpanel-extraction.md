---
id: 1581
title: Curate stale Cockpit overlay and repair tests after RepairPanel 
  extraction
status: todo
priority: important
created: 2026-05-15T12:19:29.765021+00:00
updated: 2026-05-15T12:38:12.576525+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - quality
parent: 1559
depends_on:
  - 1569
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context

Task #1569 extracted `RepairPanel` out of `HealthBadge` into a Shell-mounted component and added canonical overlay proof in `overlay-behavior-1563.spec.ts` (E2E) plus `OverlayAnchoring_1569.test.tsx` (unit). During review, quality-runner verified that `HealthBadgeRepair.test.tsx` currently fails 6 tests against the superseded pre-#1569 contract (repair callback threading and RepairPanel-inside-popover assertions) and that both overlay spec filenames (`1563-overlay-behavior.spec.ts` and `overlay-behavior-1563.spec.ts`) currently exist in the E2E directory. The two E2E files have diverged: the canonical `overlay-behavior-1563.spec.ts` contains updated focus-wrap assertions while the stale `1563-overlay-behavior.spec.ts` retains older generic Tab-escape detection.

## Acceptance Criteria

- **AC-1:** Remove the stale duplicate Playwright spec `serve/cockpit/web/e2e/1563-overlay-behavior.spec.ts` so the canonical overlay proof surface is single-sourced in `overlay-behavior-1563.spec.ts`.
- **AC-2:** Update or retire stale assertions in `serve/cockpit/web/src/__tests__/HealthBadgeRepair.test.tsx` that still require `RepairPanel` inside the `HealthBadge` popover or `HealthBadge`-owned repair callback threading, aligning the suite to the extracted Shell-mounted `RepairPanel` architecture. Retain test suites that exercise RepairPanel's own props directly (e.g. `TestFromAC_RepairPanelOnSuccess`, `TestFromAC_RepairPanelPDS`, `TestFromAC_RepairConfirmCopyExact`) since those contracts remain live.
- **AC-3:** Verify the canonical frontend proof surface remains green with scoped runs covering `serve/cockpit/web/e2e/overlay-behavior-1563.spec.ts`, `serve/cockpit/web/src/__tests__/OverlayAnchoring_1569.test.tsx`, and the curated `HealthBadgeRepair.test.tsx`.

Proof bundle: existing
Existing proof scope: serve/cockpit/web/e2e/overlay-behavior-1563.spec.ts, serve/cockpit/web/src/__tests__/OverlayAnchoring_1569.test.tsx, serve/cockpit/web/src/__tests__/HealthBadgeRepair.test.tsx
2026-05-15T12:38:12+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: curate stale test artifacts after RepairPanel extraction |
| Interface clarity | PASS | AC names specific files, stale patterns (HealthBadge-owned), and retained suites |
| Dependency correctness | PASS | Added depends_on=[1569]; #1569 is in done status |
| Module layering | N/A | Test file modifications only |
| TDD compliance | N/A | Quality/curation task — existing proof bundle |
| KISS/YAGNI | PASS | Minimal scope: one file deletion, one test suite curation, one verification run |
| Premise challenge | PASS | Verified: E2E files diverged (canonical has wrap assertions, stale has generic Tab); HealthBadge no longer accepts corruptionCount/onRepairSuccess; RepairPanel is Shell-mounted (Shell.tsx:11,118-124) |
| Pattern consistency | PASS | Test curation follows established quality patterns |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Cockpit frontend only |
| User-action detection | NOT DETECTED | No physical-action signals |

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-1 (remove stale E2E spec) | PASS — file confirmed to exist with outdated assertions; canonical overlay-behavior-1563.spec.ts is the evolved version | Context tightened to note divergence |
| AC-2 (curate HealthBadgeRepair.test.tsx) | PASS — correctly scopes stale patterns (popover containment, HealthBadge-owned callback chain); explicitly retains valid direct-prop suites | Added retention guidance for TestFromAC_RepairPanelOnSuccess, PDS, ConfirmCopy |
| AC-3 (verify canonical proof green) | PASS after refinement — tightened from "curated repair-related unit suite" to "curated HealthBadgeRepair.test.tsx" to eliminate scope ambiguity across 6+ repair test files | Replaced vague reference with specific file |

### Challenge Results
- Challenger: reconsider (0.55)
- Findings: (1) E2E files diverged not identical — accepted, context corrected; (2) stale-suite overreach — AC-2 wording already correctly scoped, but added explicit retention list; (3) AC-3 scope ambiguity — accepted, tightened to name specific file; (4) missing proof-bundle metadata — accepted, added
- Architect response: accepted all actionable findings, refined task body accordingly

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: existing
- Existing proof scope: overlay-behavior-1563.spec.ts, OverlayAnchoring_1569.test.tsx, HealthBadgeRepair.test.tsx
- Test-writer: SKIP

### Refinements Applied
1. Context section: corrected "both exist" to document divergence (canonical has focus-wrap assertions, stale has generic Tab detection)
2. AC-2: added explicit retention guidance for live direct-prop test suites
3. AC-3: replaced "curated repair-related unit suite" with "curated HealthBadgeRepair.test.tsx"
4. Added Proof bundle: existing with explicit proof scope
5. Added depends_on: [1569]

### Verdict: APPROVE
### Action Taken: Refined AC-2/AC-3, added proof-bundle metadata, added dependency, advanced to todo