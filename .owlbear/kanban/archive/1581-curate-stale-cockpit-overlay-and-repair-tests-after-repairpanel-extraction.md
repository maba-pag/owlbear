---
id: 1581
title: Curate stale Cockpit overlay and repair tests after RepairPanel 
  extraction
status: archived
priority: important
created: 2026-05-15T12:19:29.765021+00:00
updated: 2026-05-15T13:55:01.095840+00:00
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
archival_reason: completed
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
2026-05-15T13:01:52+00:00
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Existing proof scope: serve/cockpit/web/e2e/overlay-behavior-1563.spec.ts, serve/cockpit/web/src/__tests__/OverlayAnchoring_1569.test.tsx, serve/cockpit/web/src/__tests__/HealthBadgeRepair.test.tsx
- Passing through to builder.
2026-05-15T13:25:07+00:00
## Builder Notes
- Proof bundle: existing (implemented/curated without TestFromAC RED gate)
- Files changed:
  - serve/cockpit/web/src/__tests__/HealthBadgeRepair.test.tsx
  - serve/cockpit/web/e2e/1563-overlay-behavior.spec.ts (deleted)
- Fixes applied:
  - Removed stale HealthBadge-owned repair assertions tied to pre-#1569 architecture:
    - retired `TestFromAC_HealthBadgePopoverRepair`
    - retired `TestFromAC_HealthBadgeRepairPropChain`
  - Kept live direct-RepairPanel contracts as required:
    - `TestFromAC_RepairPanelOnSuccess`
    - `TestFromAC_RepairPanelPDS`
    - `TestFromAC_RepairConfirmCopyExact`
  - Deleted duplicate stale Playwright spec `serve/cockpit/web/e2e/1563-overlay-behavior.spec.ts`; canonical proof remains `serve/cockpit/web/e2e/overlay-behavior-1563.spec.ts`
- Verification (quality-runner, scoped) after final deletion:
  - tests: 42 passed, 0 failed, 0 skipped
  - lint: clean=true, violations=[]
  - exit codes: vitest=0, playwright=0, eslint=0
- Evidence summary:
  - AC-1 satisfied by deleting stale duplicate overlay spec.
  - AC-2 satisfied by curating `HealthBadgeRepair.test.tsx` to extracted Shell-mounted RepairPanel architecture while preserving listed live suites.
  - AC-3 satisfied by scoped proof run over:
    - serve/cockpit/web/e2e/overlay-behavior-1563.spec.ts
    - serve/cockpit/web/src/__tests__/OverlayAnchoring_1569.test.tsx
    - serve/cockpit/web/src/__tests__/HealthBadgeRepair.test.tsx
- Commits:
  - f046d44f test: curate stale cockpit overlay and repair specs (#1581, builder)
  - 97c129d8 test: remove stale overlay behavior duplicate spec (#1581, builder)
2026-05-15T13:27:41+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1581 -> docs | AC mapped to code and evidence sufficient.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | Only one overlay-behavior spec remains in the workspace: `serve/cockpit/web/e2e/overlay-behavior-1563.spec.ts` (file search). Builder deletion commit is present in `.git/logs/HEAD:3196` (`97c129d8`). | Canonical proof file remains at `serve/cockpit/web/e2e/overlay-behavior-1563.spec.ts`; scoped proof target matches task body. | PASS |
| AC-2 | `RepairPanel` is Shell-mounted at `serve/cockpit/web/src/Shell.tsx:132-135`; `HealthBadge` owns only its anchored popover at `serve/cockpit/web/src/components/HealthBadge.tsx:14`, `:92`, `:97`; `RepairPanel` still owns the direct contracts exercised by the retained suite at `serve/cockpit/web/src/components/RepairPanel.tsx:42`, `:71`, `:86`, `:118`, `:172`. | `serve/cockpit/web/src/__tests__/HealthBadgeRepair.test.tsx:125`, `:155`, `:191` retain the live direct-RepairPanel suites; grep over that file returned no matches for retired stale test names `TestFromAC_HealthBadgePopoverRepair` and `TestFromAC_HealthBadgeRepairPropChain`. | PASS |
| AC-3 | Canonical proof files are present and typecheck/diagnostics-clean. | Builder notes report scoped quality-runner proof over `overlay-behavior-1563.spec.ts`, `OverlayAnchoring_1569.test.tsx`, and `HealthBadgeRepair.test.tsx` with `42 passed, 0 failed, 0 skipped`, `lint: clean=true`, exit codes `vitest=0`, `playwright=0`, `eslint=0`. Direct review confirmed the canonical spec still contains wrap/focus-return assertions at `serve/cockpit/web/e2e/overlay-behavior-1563.spec.ts:434`, `:509`, `:544`, `:620`; `OverlayAnchoring_1569.test.tsx` still covers anchored positioning and cleanup modal semantics at `:89`, `:140`, `:177`, `:196`, `:215`, `:233`; `HealthBadgeRepair.test.tsx` still covers refetch/onSuccess/exact-copy proof at `:81`, `:107`, `:133`, `:143`, `:198`, `:209`. | PASS |
- Builder evidence review: sufficient and internally consistent for an `existing` proof bundle; no independent quality-runner rerun was required.
- Independent checks performed: reviewed files show no diagnostics (`get_errors` clean for the canonical proof surface and adjacent component files); builder commits exist in git logs at `.git/logs/HEAD:3195-3196`.

## Observations
- `serve/cockpit/web/src/__tests__/HealthBadgeRepair.test.tsx:54` still has a stale helper comment that says "Renders HealthBadge..." even though the file now exercises `RepairPanel` directly. This is non-blocking because the executable assertions were curated correctly, but it is misleading documentation inside the test file.
- No safety/security concerns were in scope for this task and no new risk surface was introduced by the review target.
2026-05-15T13:39:27+00:00
## Docs Gate

**Verdict:** PASS — no docs impact.

**Convention mapping:** `serve/cockpit/web/src/__tests__/**` + `serve/cockpit/web/e2e/**` → `serve/cockpit/README.md`

**Item 1 — README Verification:** Full read of `serve/cockpit/README.md` performed. Layer 1 grep: no references to deleted `1563-overlay-behavior.spec.ts` or `HealthBadgeRepair.test.tsx` in any README. Canonical references (`overlay-behavior-1563.spec.ts`, `OverlayAnchoring_1569.test.tsx`) remain valid and untouched. Layer 2 editorial: #1569 section description of RepairPanel extraction accurately reflects current architecture; no contradictions introduced by this task. No updates needed.

**Item 2 — External Attribution:** N/A — no external sources used.

**Item 3 — Research Doc:** N/A — no research file created.

**Item 4 — Deletion Detection:** `1563-overlay-behavior.spec.ts` deleted. Grep across all `.md` files returned zero public-doc references to this path. No orphaned documentation references. No follow-up task needed.

**Scratch cleanup:** No `1581-*` scratch files existed.

**Reviewer observation (non-blocking):** Stale helper comment at `HealthBadgeRepair.test.tsx:54` ("Renders HealthBadge...") is inside a test file, out of scope for the docs gate. Pre-existing; noted as non-blocking by reviewer.
2026-05-15T13:55:01+00:00
## Audit
### Regression Detection
- Full Python suite: 4562 passed, 226 failed, 14 skipped, 5 errors. All 226 failures are in unrelated modules (engine dispatch, path neutrality, reviewer rewrite, MCP lifecycle, knowledge stats, cockpit delivery gate, shell sidecar, react compiler). None are in files touched by #1581.
- Frontend proof surface (independent rerun): HealthBadgeRepair.test.tsx 10 passed, OverlayAnchoring_1569.test.tsx 13 passed, overlay-behavior-1563.spec.ts 19 passed. Total 42 passed, 0 failed.
- Regression verdict: PASS (no regressions attributable to this task)

### Intent Verification
- Scope alignment: PASS (both changed files are within scope:cockpit/frontend domain; HealthBadgeRepair.test.tsx curated, 1563-overlay-behavior.spec.ts deleted)
- Purpose match: PASS (stale test artifacts removed and canonical proof surface preserved, matching stated AC purpose)
- Extraneous scope: none
- Boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
AC lines were specific (named exact files, exact stale patterns, exact retained suites), included proper retention guidance to prevent over-deletion, and challenge findings were addressed. Clean implementation path with no ambiguity.

### Commit Integrity
- Upstream commit presence: PASS (f046d44f curates HealthBadgeRepair.test.tsx; 97c129d8 removes stale duplicate spec; both reference #1581 with builder attribution)
- Commit scope: PASS (f046d44f: 1 file, 4 ins/140 del; 97c129d8: 1 file, 681 del; no extraneous files)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive