---
id: 1389
title: 'P2-14: Implement Cockpit decision viewport and resolution UX'
status: backlog
priority: needed
created: 2026-05-06T01:04:52.300671+00:00
updated: 2026-05-09T05:40:02.345719+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:fix
- frontend
- decisions
- ux
parent: 1363
depends_on:
- 1388
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Implement a central Cockpit decision viewport and safer resolution UX.

## Problem Evidence
- DRStatusIndicator is a tiny decision count popover rather than a central decision viewport.
- ResolveModal defaults to approved, has terse lower-case choices, and lacks a visible consequence summary.
- Pending decisions need clear task context, body preview, and loading/error/empty states.

## Acceptance Criteria
- The decision UI shows pending decisions with task link/context, agent or request type, age, body or preview content, and clear loading, error, and empty states.
- Resolution choices explain consequences for approved, rejected, and needs-info outcomes.
- Accidental approval is not the easiest path, including no unsafe approved default.
- Action labels and modal state are meaningful and PDS-compatible.
- Decision workflow keyboard and focus behavior meets the expectations captured in #1388, with final global accessibility verification left to a separate task.
- Expected decision errors use the frontend error contract from #1375.
- The implementation satisfies #1388 without changing backend decision lifecycle semantics.

## Scope
- In scope: Cockpit frontend decision viewport and resolution-modal UX.
- Out of scope: backend decision lifecycle from #1385, data/refetch plumbing from #1387, task detail workflows, global accessibility audit, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1388.

[[2026-05-09]]


## Refined Acceptance Criteria
Supersedes original AC above — td annotations added, Shell integration line added.

- [ ] The decision UI shows pending decisions with task link/context, agent or request type, age, body or preview content, and clear loading, error, and empty states. (td:2)
- [ ] Resolution choices explain consequences for approved, rejected, and needs-info outcomes. (td:2)
- [ ] Accidental approval is not the easiest path, including no unsafe approved default. (td:2)
- [ ] Action labels and modal state are meaningful and PDS-compatible. (td:1)
- [ ] Decision workflow keyboard and focus behavior meets the expectations captured in #1388, with final global accessibility verification left to a separate task. (td:2)
- [ ] Expected decision errors use the frontend error contract from #1375. (td:1)
- [ ] The implementation satisfies #1388 without changing backend decision lifecycle semantics. (td:0)
- [ ] DecisionViewport is the primary decision listing surface accessible from the Shell, showing loading, error, and empty states from usePendingDRs. DRStatusIndicator's popover list is no longer the sole way to view pending decisions. (td:2)

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Focused on decision viewport + resolution UX in cockpit frontend |
| Interface clarity | PASS after REFINE | Original AC omitted Shell integration; AC8 added for DecisionViewport placement in Shell |
| Dependency correctness | PASS | #1388 (test counterpart) archived/done; #1375 (error contract) archived/done; no missing deps |
| Module layering | PASS | Frontend components only; no upward imports; uses existing hooks (usePendingDRs) and utilities (getResponseErrorMessage) |
| TDD compliance | PASS | Test files exist: DecisionViewport_1388.test.tsx, ResolveModalUX_1388.test.tsx; all GREEN. AC8 (td:2) will get new tests from test-writer |
| KISS/YAGNI | PASS | Minimal scope; components already built; Shell integration is the remaining deliverable |
| Premise challenge | PASS | Audit identified real UX problems: popover-only decision viewing, unsafe default approval, terse labels |
| Pattern consistency | PASS | PDS components, React hooks, Shell layout patterns followed |
| Security surface | PASS | No new system boundaries; error sanitization via getResponseErrorMessage; XSS prevention via rehype-sanitize in markdown rendering |
| Single domain | PASS | Cockpit frontend only |

### Builder Notes
- DecisionViewport.tsx and ResolveModal.tsx are already implemented and pass #1388 tests. Primary deliverable is Shell integration (AC8).
- Shell.tsx destructures {count, items, error, refetch} from usePendingDRs but not isLoading. Add isLoading to support DecisionViewport's loading state. This is not new data plumbing (out of scope per #1387) — it uses an existing hook field.
- Existing Shell tests (Shell_1192.test.tsx, PdsMigration_1230.test.tsx) reference DRStatusIndicator. May need updates if DRStatusIndicator's popover is replaced.
- DRStatusIndicator has a duplicate formatAge function (also in DecisionViewport) — tech debt, separate concern.

### Challenge Results
- Challenger: reconsider (0.59)
- Key concerns: (1) AC8 complexity underestimated as td:1; (2) Shell test impact from DRStatusIndicator changes; (3) supplementing ambiguity; (4) isLoading not wired in Shell
- Architect response: Accepted (1) — AC8 upgraded to td:2; accepted (2) — noted in builder notes; accepted (3) — reworded to "no longer the sole way"; addressed (4) — isLoading is existing hook output, not new plumbing

### Test Depth
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Added td annotations to all AC lines. Added AC8 for Shell integration (td:2). Challenger concerns addressed. Advancing to todo.

[[2026-05-09]]
Architecture review complete. Refined AC: added td annotations to all 7 original lines (td:0 through td:2), added AC8 (td:2) for Shell integration — DecisionViewport must be the primary decision listing surface, replacing DRStatusIndicator's popover as the sole viewing path. Challenger returned reconsider (0.59); accepted key concerns: upgraded AC8 from td:1 to td:2, noted Shell test impact (Shell_1192, PdsMigration_1230) in builder notes, clarified isLoading wiring is existing hook output not new plumbing. All 10 architecture criteria PASS. Components already implemented and tested; primary builder deliverable is Shell integration.
[[2026-05-09]]
## Test-Writer Notes

**Test file:** `serve/cockpit/web/src/__tests__/Shell_1389.test.tsx`

**Class:** `TestFromAC_DecisionViewportShellIntegration`

**Test counts by category:**
| Category | Count |
|----------|-------|
| Happy path | 6 |
| Edge cases | 4 |
| Error paths | 3 |
| Boundary conditions | 2 |
| **Total** | **15** |

**Fail verification:** 15 failed, 0 passed. Root cause confirmed: `Shell` does not import or render `DecisionViewport`, so all assertions targeting the mock call count and `[data-testid="decision-viewport"]` DOM presence fail.

**AC Coverage:**
| AC Line | Tests |
|---------|-------|
| AC8 (td:2) — Shell renders DecisionViewport as primary listing surface | ✓ covered (15 tests) |
| AC8 (td:2) — isLoading passed from usePendingDRs to DecisionViewport | ✓ covered |
| AC8 (td:2) — error passed from usePendingDRs to DecisionViewport | ✓ covered |
| AC8 (td:2) — DecisionViewport visible unconditionally (not only via popover click) | ✓ covered |
| AC8 (td:2) — onItemClick wired (triggers ResolveModal) | ✓ covered |
| AC1–AC7 (all td:0/td:1/td:2) | Previously covered by #1388 tests (DecisionViewport_1388, ResolveModalUX_1388 — all GREEN) |

**ESLint:** 0 errors, 0 warnings.

**Builder notes:**
- Must import `DecisionViewport` from `./components/DecisionViewport` into Shell.tsx
- Must destructure `isLoading` from `usePendingDRs()` return value
- Must render `<DecisionViewport items={...} isLoading={...} error={...} onItemClick={setSelectedDRId} />` in Shell layout
- Component must be unconditionally visible (not gated behind a popover click)
- Existing Shell tests (Shell_1192, PdsMigration_1230) may need updates if DRStatusIndicator popover list is removed
[[2026-05-09]]
## Builder Notes
- Implementation: integrated DecisionViewport into Shell and wired it to `usePendingDRs` state in `serve/cockpit/web/src/Shell.tsx`.
- Files changed: `serve/cockpit/web/src/Shell.tsx`.
- Fixes applied:
  - Added `DecisionViewport` import in Shell.
  - Updated `usePendingDRs` destructuring to include `isLoading` (`pendingDRLoading`).
  - Rendered `DecisionViewport` in Shell sidecar as an always-visible listing surface.
  - Passed `items`, `isLoading`, `error`, and `onItemClick={setSelectedDRId}` to DecisionViewport.
  - Kept `DRStatusIndicator` in status bar so popover is supplemental, not sole listing path.
- Test results (quality-runner evidence):
  - RED verification before implementation: `serve/cockpit/web/src/__tests__/Shell_1389.test.tsx` -> 0 passed / 15 failed.
  - GREEN scoped verification after implementation: `serve/cockpit/web/src/__tests__/Shell_1389.test.tsx` + `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx` + `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx` -> 58 passed / 0 failed.
  - Additional Shell regression scope: Shell suites excluding known unrelated `Shell_1344` instability -> 125 passed / 0 failed.
- Coverage:
  - `Shell.tsx` in broader Shell scope: 88.26% statements, 88.88% branches, 71.42% functions, 85.40% lines.
  - Focused 1389 scope reports lower module-wide percentages because `Shell.tsx` has legacy branches outside AC8 paths.
- Lint status:
  - ESLint clean for `serve/cockpit/web/src/Shell.tsx` and `serve/cockpit/web/src/__tests__/Shell_1389.test.tsx` (0 errors, 0 warnings).
- Commit:
  - `41ece747` — feat: integrate DecisionViewport in Shell (#1389, builder)
[[2026-05-09]]
## Review Evidence
### Test Results
- Scoped quality-runner gate: 69 passed, 0 failed across `serve/cockpit/web/src/__tests__/Shell_1389.test.tsx`, `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx`, `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx`, and `serve/cockpit/web/src/__tests__/Shell_1192.test.tsx`.
- Contextual quality-runner pass: 142 passed, 8 failed when `serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx` was added. That file self-identifies as a RED-phase legacy suite and task `#1230` is not present on the current board, so I treated it as regression context rather than the gating suite for `#1389`.

### Lint Results
- ESLint clean on `serve/cockpit/web/src/Shell.tsx` and the four scoped test files above.

### Coverage
- `src/Shell.tsx`: 73.46% statements, 77.77% branches, 38.09% functions, 64.96% lines.
- I did not fail on module-level coverage. This is a narrow Shell integration task and the rejection is about proof quality, not line-count coverage.

### Source / Commit Checks
- Builder commit `41ece747` is present in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`.
- TestFromAC integrity is only low-confidence because I do not have a commit-object diff in this tool surface. Current file contents show no visible weakening in the reviewed test files.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| Decision UI shows pending decisions with task link/context, agent or request type, age, body/preview content, and loading/error/empty states | `serve/cockpit/web/src/components/DecisionViewport.tsx:52-63`; `serve/cockpit/web/src/Shell.tsx:200-204`; `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx`; `serve/cockpit/web/src/__tests__/Shell_1389.test.tsx:240-283` | PASS |
| Resolution choices explain consequences for approved/rejected/needs-info | Implementation copy is present in `serve/cockpit/web/src/components/ResolveModal.tsx:134`, `:147`, `:160`, but the test proof in `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx:67-140` only checks separate `p-text` elements and minimum word counts | FAIL (proof quality) |
| Accidental approval is not the easiest path, including no unsafe approved default | `serve/cockpit/web/src/components/ResolveModal.tsx:26`; `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx:147-188` | PASS |
| Action labels and modal state are meaningful and PDS-compatible | `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx:193-212` only proves labels have more than one word. It does not settle the concrete meaning of `PDS-compatible`, and the broader legacy context still expects `p-button` actions while `serve/cockpit/web/src/components/ResolveModal.tsx:173-184` renders raw `button` elements | FAIL (proof / AC interpretation) |
| Decision workflow keyboard and focus behavior meets #1388 expectations | Modal-level behavior exists in `serve/cockpit/web/src/components/ResolveModal.tsx:67-80` and `:112`, and isolated modal tests exist in `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx:228-242`; however Shell integration coverage in `serve/cockpit/web/src/__tests__/Shell_1389.test.tsx:297-314` stops at opening the modal and never proves the `onClose` path wired at `serve/cockpit/web/src/Shell.tsx:270-276` | FAIL (proof gap) |
| Expected decision errors use the frontend error contract from #1375 | `serve/cockpit/web/src/hooks/usePollingFetch.ts:2` and `:69-71` route non-OK polling responses through `getResponseErrorMessage`, and Shell renders the hook error at `serve/cockpit/web/src/Shell.tsx:176` | PASS |
| Implementation satisfies #1388 without changing backend decision lifecycle semantics | Builder scope is frontend-only (`serve/cockpit/web/src/Shell.tsx`); no backend decision lifecycle files changed | PASS |
| DecisionViewport is the primary decision listing surface from Shell; DRStatusIndicator is no longer the sole surface | `serve/cockpit/web/src/Shell.tsx:200-204`; `serve/cockpit/web/src/__tests__/Shell_1389.test.tsx:240-314` | PASS |

### Deductions
- `-0.07` Existing tests for AC2 and AC4 are structurally weak: they reduce “explains consequences” and “meaningful” to `p-text` presence plus word-count thresholds.
- `-0.05` Shell integration tests do not prove close/focus behavior after opening the modal from DecisionViewport, so a broken `onClose` path in Shell could still false-green.
- `-0.03` TestFromAC immutability check is low-confidence without a diff object.

### Verdict
- Confidence: `0.85`
- FAIL. The implementation appears largely correct, but the proof surface is below reviewer threshold because AC2/AC4 assertions are too weak and AC5 is not proven through the Shell workflow integration.

### Action
- Reject to `backlog`. This is a test/AC quality failure, not a clean builder-only defect.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC2 and AC4 into discriminating proof targets that reject vague consequence copy and define what `PDS-compatible` means for ResolveModal actions | `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx`, `serve/cockpit/web/src/components/ResolveModal.tsx` | Review findings on AC2/AC4; `ResolveModalUX_1388.test.tsx:67-140`, `:193-212`; `ResolveModal.tsx:173-184` |
| 2 | architect | Refine AC5 review expectations so Shell-level integration must prove close/focus behavior after opening ResolveModal from DecisionViewport | `serve/cockpit/web/src/__tests__/Shell_1389.test.tsx`, `serve/cockpit/web/src/Shell.tsx` | `Shell_1389.test.tsx:297-314`; `Shell.tsx:270-276` |
| 3 | architect | Decide whether the legacy PDS migration expectation for ResolveModal action controls is now part of this task’s contract or explicitly out of scope, then hand back a clarified gate | `serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx`, `serve/cockpit/web/src/components/ResolveModal.tsx`, task `#1389` AC text | `PdsMigration_1230.test.tsx:274-279`; `ResolveModal.tsx:173-184` |