---
id: 1389
title: 'P2-14: Implement Cockpit decision viewport and resolution UX'
status: archived
priority: medium
created: 2026-05-06T01:04:52.300671+00:00
updated: 2026-05-09T11:56:27.035684+00:00
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
[[2026-05-09]]
## Refined Acceptance Criteria (v2)
Supersedes all prior AC sections — addresses reviewer rejection findings on AC2/AC4/AC5.

- [ ] AC1: The decision UI shows pending decisions with task link/context, agent or request type, age, body or preview content, and clear loading, error, and empty states. (td:2)
- [ ] AC2: Each resolution choice (approved, rejected, needs-info) has a `<PText>` consequence description structurally separate from its radio `<label>`. Each description conveys a distinct workflow outcome — approved describes proceeding, rejected describes stopping/returning, needs-info describes waiting. Tests assert consequence text contains keywords specific to each outcome (e.g. `/proceed|continue/i` for approved, `/stop|return|back/i` for rejected, `/wait|clarif/i` for needs-info), not word-count thresholds. (td:2)
- [ ] AC3: Accidental approval is not the easiest path, including no unsafe approved default. (td:2)
- [ ] AC4: ResolveModal submit and cancel controls use `<PButton>` (not raw `<button>`): submit with `variant="primary"`, cancel with `variant="secondary"`. Button labels are multi-word action descriptions. PDS typography (`<PText>`) is used for consequence descriptions within the response selector. (td:2)
- [ ] AC5: Decision workflow keyboard and focus behavior meets #1388 expectations (initial focus inside modal not on submit, Escape-to-close on modal and document, `aria-modal="true"`). Additionally, Shell integration proves the full open→close cycle: clicking a DecisionViewport item opens ResolveModal, and closing the modal (via cancel button or Escape) removes it from the DOM. (td:2)
- [ ] AC6: Expected decision errors use the frontend error contract from #1375. (td:1)
- [ ] AC7: The implementation satisfies #1388 without changing backend decision lifecycle semantics. (td:0)
- [ ] AC8: DecisionViewport is the primary decision listing surface accessible from the Shell, showing loading, error, and empty states from usePendingDRs. DRStatusIndicator popover is no longer the sole way to view pending decisions. (td:2)

## Re-review Architecture Notes

### Changes from v1
| AC | What changed | Why |
|---|---|---|
| AC2 | "explain consequences" → structural proof target with per-outcome keyword assertions | Reviewer found word-count tests non-discriminating; keywords catch regressions word-count doesn't |
| AC4 | "meaningful and PDS-compatible" (td:1) → explicit PButton requirement with variants (td:2) | ResolveModal uses raw `<button>` elements; PdsMigration_1230 expects `p-button` with `variant="primary"` (submit) and `variant="secondary"` (cancel); bumped to td:2 since builder must change implementation |
| AC5 | Added Shell-level close proof; preserved full #1388 expectations | Reviewer found Shell_1389 tests open modal but never verify close path; challenger caught initial draft dropped #1388 expectations — now explicitly enumerates them |

### PDS Migration Decision
ResolveModal action controls (`resolve-submit`, `resolve-cancel`) must use `<PButton>` with appropriate PDS variants. This is not new scope — AC4 already said "PDS-compatible" and PdsMigration_1230 expects it. The current raw `<button>` implementation is a defect against the existing PDS contract.

### Builder Guidance
- AC2: Consequence descriptions already contain correct text — no implementation change needed, only test assertion updates.
- AC4: Replace raw `<button>` with `<PButton>` in ResolveModal.tsx. Add `PButton` to PDS imports. Submit: `variant="primary"`. Cancel: `variant="secondary"`.
- AC5: Shell_1389 tests need close-path assertions: open modal via DecisionViewport click → close via cancel button → verify modal removed from DOM. Existing #1388 modal-level tests remain valid.

### Challenger Results
- Challenger: block (0.33)
- Key concerns: (1) source-of-truth — refined AC must be persisted in task body before advancing; (2) AC5 initial draft dropped #1388 expectations; (3) AC4 missing PButton variant specs; (4) AC2 keyword matching still similar to word-count
- Architect response: Accepted (1) — persisting refined AC v2 in this edit. Accepted (2) — AC5 v2 now explicitly enumerates #1388 expectations AND adds Shell close proof. Accepted (3) — AC4 v2 now specifies variant="primary" for submit, variant="secondary" for cancel. Partially accepted (4) — keyword matching is more discriminating than word count because it requires outcome-specific verbs, not arbitrary words; acknowledged limitation that current implementation already passes.

### Test Depth
- Max depth: 2
- Test-writer: PROCEED
[[2026-05-09]]
Re-review complete. Refined AC v2 addresses all three reviewer rejection findings: AC2 → keyword pattern assertions replacing word-count thresholds; AC4 → explicit PButton requirement with variant="primary" (submit) / variant="secondary" (cancel), bumped from td:1 to td:2; AC5 → Shell-level close proof added while preserving full #1388 expectations (focus, Escape, aria-modal). Challenger concerns addressed: source-of-truth persisted, AC5 expanded not narrowed, PButton variants specified. Advancing to todo.
[[2026-05-09]]
## Test-Writer Notes

**Retry cycle** — addressing reviewer rejection (AC2/AC4/AC5 proof gaps) via refined AC v2.

**Test file:** `serve/cockpit/web/src/__tests__/ResolveModalUX_1389.test.tsx`

**Class:** `TestFromAC_ResolveModalPDSButtons`

**Tests per category:**
| Category | Count |
|----------|-------|
| Happy path | 2 (p-button elements present) |
| Error paths | 2 (raw button elements absent) |
| Boundary | 2 (variant property exact values) |
| **Total** | **6** |

**Fail verification:** 6 failed, 0 passed. All fail with clean `AssertionError: expected null not to be null` — current `ResolveModal.tsx` uses raw `<button>` elements; `p-button[data-testid="resolve-submit"]` and `p-button[data-testid="resolve-cancel"]` are absent from DOM.

**Commit:** `5e5cc0e1` — test: add PButton variant RED tests for AC4 v2 (#1389, test-writer)

**AC Coverage (this file):**
| AC Line | Tests | Notes |
|---------|-------|-------|
| AC4 (td:2) — submit uses PButton variant="primary" | 3 tests | FAIL: raw button present, no p-button |
| AC4 (td:2) — cancel uses PButton variant="secondary" | 3 tests | FAIL: raw button present, no p-button |

**Pass-through AC lines (implementation already satisfies them):**
| AC Line | Why excluded | Coverage |
|---------|--------------|---------|
| AC2 v2 — keyword assertions | Current consequence text already matches `/proceed\|continue/i`, `/stop\|return\|back/i`, `/wait\|clarif/i` → new keyword tests would PASS | Existing `ResolveModalUX_1388` |
| AC5 v2 — Shell close cycle | Shell already has `{selectedDR ? <ResolveModal onClose={() => setSelectedDRId(null)} /> : null}`; close path is wired and functional → close-cycle tests would PASS | Existing `Shell_1389` + `ResolveModalUX_1388` |
| AC1, AC3, AC6, AC7, AC8 (td:0–2) | Covered by existing GREEN suites (DecisionViewport_1388, ResolveModalUX_1388, Shell_1389) | See prior test-writer notes |

**ESLint:** 0 errors, 0 warnings.

**Builder notes:**
- Replace `<button type="button" data-testid="resolve-submit">` with `<PButton data-testid="resolve-submit" variant="primary">` in ResolveModal.tsx
- Replace `<button type="button" data-testid="resolve-cancel">` with `<PButton data-testid="resolve-cancel" variant="secondary">` in ResolveModal.tsx
- Add PButton to PDS imports
- `disabled={response === ''}` prop moves to PButton (PDS PButton supports the `disabled` prop natively)
[[2026-05-09]]
## Builder Notes
- Implementation: migrated ResolveModal action controls to PDS buttons and preserved existing modal behavior.
- Files changed: `serve/cockpit/web/src/components/ResolveModal.tsx`.
- Fixes applied:
  - Added `PButton` import and replaced raw submit/cancel buttons with `<PButton>` controls.
  - Set submit control to `variant="primary"` and cancel control to `variant="secondary"`.
  - Kept `type`, `data-testid`, click handlers, and disabled behavior intact.
  - Added a submit element ref sync to reflect the `disabled` attribute on the rendered custom element for existing AC3 assertions.
  - Refactored response-change handling to a shared typed handler (`handleResponseChange`) and consolidated control-value parsing.
- Test results (quality-runner, scoped):
  - 5 files / 73 tests passed, 0 failed.
  - Suites: `ResolveModalUX_1389`, `ResolveModalUX_1388`, `ResolveModal_1193`, `DecisionViewport_1388`, `Shell_1389`.
- Coverage (quality-runner scoped):
  - `src/components/ResolveModal.tsx`: 94% statements, 62.96% branches, 100% functions, 95.91% lines.
- Lint status:
  - ESLint clean on `src/components/ResolveModal.tsx` and `src/__tests__/ResolveModalUX_1389.test.tsx` (0 issues).
- Validation:
  - TypeScript diagnostics: no errors in `serve/cockpit/web/src/components/ResolveModal.tsx`.
- Commit:
  - `8796bad0` — feat: migrate ResolveModal actions to PButton (#1389, builder)
[[2026-05-09]]
## Review Evidence
### Test Results
- quality-runner scoped gate: 84 passed, 0 failed across `ResolveModalUX_1389`, `ResolveModalUX_1388`, `ResolveModal_1193`, `DecisionViewport_1388`, `Shell_1389`, and `Shell_1192`.
- code-reader reviewed the current source/test surface for AC1-AC8. No security or data-safety issues were found.

### Lint Results
- ESLint clean on `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/components/ResolveModal.tsx`, and the six scoped test files.

### Coverage
- `src/components/ResolveModal.tsx`: 94% statements, 62.96% branches, 100% functions, 95.91% lines.
- `src/Shell.tsx`: 73.46% statements, 77.77% branches, 38.09% functions, 64.96% lines.
- The Shell module-level percentage is not the gating failure for this narrow task.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: decision UI shows pending decisions with context, metadata, body/preview, and loading/error/empty states | `DecisionViewport_1388.test.tsx:75,99,119,237,251` and `Shell_1389.test.tsx:198,208,254,272`; `Shell.tsx:200-204` | PASS |
| AC2: refined keyword-specific consequence assertions (not word-count thresholds) | `ResolveModalUX_1388.test.tsx:88-90,113-115,138-140` still use `wordCount`; `ResolveModalUX_1389.test.tsx:10` explicitly excludes AC2 v2; implementation text exists in `ResolveModal.tsx`, but the refined proof target is absent | FAIL |
| AC3: no unsafe approved default | `ResolveModalUX_1388.test.tsx:147,156,165,175`; `ResolveModal.tsx:26` | PASS |
| AC4: PButton controls, variants, multi-word labels, PText consequence typography | `ResolveModalUX_1389.test.tsx:69,89,98,114`; `ResolveModalUX_1388.test.tsx:193,204,215`; `ResolveModal.tsx:176-198` | PASS |
| AC5: modal keyboard/focus plus Shell open→close cycle | `ResolveModalUX_1388.test.tsx:228,242,251,258` proves modal-local behavior; `Shell_1389.test.tsx:297-311` proves open only, and `Shell_1389.test.tsx:314-334` only checks callback/no-throw. No Shell assertion proves cancel or Escape removes the modal from the DOM after opening, despite `Shell.tsx:272-276` and `ResolveModal.tsx:67-80,82-88`. | FAIL |
| AC6: expected decision errors use the frontend error contract from #1375 | `ResolveModal.tsx:44` calls `getResponseErrorMessage`; `api/errorMessage.ts:1-28` implements message/detail/fallback; `ResolveModal_1193.test.tsx:207-241` only proves the error node renders | PASS (low-confidence proof) |
| AC7: frontend-only implementation without backend lifecycle changes | `ResolveModal.tsx:38-41` and `ResolveModal_1193.test.tsx:132-171` keep the same endpoint/payload; no backend files are in scope | PASS |
| AC8: DecisionViewport is the primary Shell listing surface | `Shell_1389.test.tsx:198,203,208,254,272,297` and `DecisionViewport_1388.test.tsx:75,99,119`; `Shell.tsx:200-204` | PASS |

### Deductions
- `-0.08` AC2 still lacks the refined keyword-based outcome assertions and remains a false-green risk.
- `-0.06` AC5 still lacks Shell-level close-cycle proof after opening ResolveModal from DecisionViewport.
- `-0.02` AC6 proof is weak: tests only assert error-node presence, not message/detail/fallback behavior.

### Verdict
- Confidence: `0.84`
- FAIL. The implementation is largely correct, but the retry did not satisfy refined AC2 and AC5 at the proof level. A prior `## Review Evidence` rejection already exists in this task body, so this is a second review failure and the loop-breaker route is `backlog`.

### Action
- Reject to `backlog`.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Persist a concrete AC2 proof target and route the next test pass to replace word-count checks with keyword-specific outcome assertions for approved, rejected, and needs-info text | `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx`, `serve/cockpit/web/src/__tests__/ResolveModalUX_1389.test.tsx` | `ResolveModalUX_1388.test.tsx:88-90,113-115,138-140`; `ResolveModalUX_1389.test.tsx:10` |
| 2 | architect | Persist a concrete AC5 Shell proof target and route the next test pass to assert the open→close cycle, including cancel or Escape removing ResolveModal from the DOM after a DecisionViewport-triggered open | `serve/cockpit/web/src/__tests__/Shell_1389.test.tsx`, `serve/cockpit/web/src/Shell.tsx` | `Shell_1389.test.tsx:297-334`; `Shell.tsx:272-276` |
| 3 | architect | Decide whether AC6 needs explicit helper-branch assertions for message/detail/fallback or is acceptable as non-blocking debt, then narrow the next gate accordingly | `serve/cockpit/web/src/__tests__/ResolveModal_1193.test.tsx`, `serve/cockpit/web/src/api/errorMessage.ts` | `ResolveModal_1193.test.tsx:207-241`; `api/errorMessage.ts:1-28` |
[[2026-05-09]]

## Architecture Re-review (v3)

### Context
Third architect cycle. Two reviewer rejections (both 0.84-0.85 confidence) on proof quality, not implementation correctness. AC2, AC5 proof gaps; AC6 accepted as non-blocking.

### Decisions
| Follow-up | Decision | Rationale |
|---|---|---|
| AC2 keyword assertions | Builder test deliverable | Implementation text already matches keyword patterns (`/proceed\|continue/i`, `/stop\|return\|back/i`, `/wait\|clarif/i`). Test-writer correctly excluded (GREEN from start). Builder must replace word-count assertions with keyword regex in `ResolveModalUX_1388.test.tsx` |
| AC5 Shell close-cycle | Builder test deliverable | Shell close path wired (`onClose={() => setSelectedDRId(null)}`). Test-writer correctly excluded (GREEN from start). Builder must add close-cycle test to `Shell_1389.test.tsx` |
| AC6 helper internals | Non-blocking — accept as-is | `getResponseErrorMessage` internals are #1375's test scope. #1389 satisfies "use the contract" by calling the function |

### AC v3
No AC line text changes from v2. All 8 lines remain as written. Changes are routing-only.

### Test Routing
AC2 and AC5 require test-file updates that pass immediately against current implementation. These are **builder test deliverables**, not RED-phase tests. Test-writer should pass through with existing GREEN suites.

### Builder Proof-Refinement Deliverables
1. **AC2 — keyword assertions:** In `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx`, replace word-count threshold assertions (lines ~88-90, ~113-115, ~138-140) with keyword regex assertions: approved text matches `/proceed|continue/i`, rejected text matches `/stop|return|back/i`, needs-info text matches `/wait|clarif/i`. Remove `wordCount` / `toBeGreaterThanOrEqual` patterns; use `toMatch()` with the regex patterns.
2. **AC5 — Shell close-cycle:** In `serve/cockpit/web/src/__tests__/Shell_1389.test.tsx`, add a close-cycle test inside the existing `AC8: DecisionViewport onItemClick opens ResolveModal` describe block: (a) stub with DR_A in items, (b) render Shell, (c) click `[data-testid="dv-click-dr-001"]`, (d) assert `[data-testid="resolve-modal"]` present, (e) fire `keydown` Escape on `document`, (f) assert `[data-testid="resolve-modal"]` is null (removed from DOM).

### Challenger
Skipped — REFINE verdict, narrow scope, 3rd cycle with well-understood proof gaps.

### Verdict: APPROVE (REFINE — proof routing only)

[[2026-05-09]]
Architecture re-review v3 complete. No AC text changes — routing fix only. Two reviewer proof-gap rejections (AC2 word-count tests, AC5 missing Shell close-cycle) resolved as builder test deliverables: both pass immediately against correct implementation, so test-writer correctly excluded them from RED phase. AC6 helper-internals concern accepted as non-blocking (#1375 scope). Builder guidance: (1) replace word-count assertions with keyword regex in ResolveModalUX_1388, (2) add Escape-to-close cycle test in Shell_1389. Challenger skipped (REFINE, narrow 3rd-cycle scope).
[[2026-05-09]]
## Test-Writer Notes

**Retry cycle — pass-through per architecture v3.**

No new RED-phase tests written. The two remaining proof gaps are explicitly classified as **builder test deliverables** by the architect (v3 re-review) because both gaps pass immediately against the current implementation.

**Gap 1 — AC2 keyword assertions (`ResolveModalUX_1388.test.tsx`):**
- Lines 89–90, 114–115, 139–140 use `wordCount`/`toBeGreaterThanOrEqual` instead of keyword regex.
- This is a test *modification* (replacing assertions in an existing passing test), not a RED-phase addition.
- Architect instruction: builder replaces word-count patterns with `/proceed|continue/i` (approved), `/stop|return|back/i` (rejected), `/wait|clarif/i` (needs-info) using `toMatch()`.

**Gap 2 — AC5 Shell close-cycle (`Shell_1389.test.tsx`):**
- Line 308 checks only that the modal is present; no test verifies cancel or Escape removes `[data-testid="resolve-modal"]` from the DOM.
- Shell.tsx:272–276 already wires `onClose={() => setSelectedDRId(null)}`; a close-cycle test would pass immediately.
- Architect instruction: builder adds open→close assertion inside the `AC8: DecisionViewport onItemClick opens ResolveModal` describe block.

**Existing GREEN suites (all passing per prior builder/quality-runner evidence):**
- `ResolveModalUX_1388.test.tsx`, `ResolveModalUX_1389.test.tsx`, `ResolveModal_1193.test.tsx`
- `DecisionViewport_1388.test.tsx`, `Shell_1389.test.tsx`, `Shell_1192.test.tsx`

**AC coverage (no gaps in RED tests):**
| AC Line | Status |
|---------|--------|
| AC1 (td:2) | GREEN — `DecisionViewport_1388`, `Shell_1389` |
| AC2 (td:2) — keyword assertions | Builder test deliverable (test modification, not RED) |
| AC3 (td:2) | GREEN — `ResolveModalUX_1388` |
| AC4 (td:2) — PButton variants | GREEN — `ResolveModalUX_1389`, `ResolveModalUX_1388` |
| AC5 (td:2) — Shell close-cycle | Builder test deliverable (GREEN from start) |
| AC6 (td:1) | GREEN — `ResolveModal_1193` |
| AC7 (td:0) | Skipped per td:0 |
| AC8 (td:2) | GREEN — `Shell_1389` |
[[2026-05-09]]
## Builder Notes
- Scope: proof-refinement cycle per architecture v3; no implementation logic changes.
- Files changed:
  - serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx
  - serve/cockpit/web/src/__tests__/Shell_1389.test.tsx
- Fixes applied:
  - AC2 proof update: replaced word-count threshold assertions with outcome-specific keyword regex assertions.
    - approved description now asserts `/proceed|continue/i`
    - rejected description now asserts `/stop|return|back/i`
    - needs-info description now asserts `/wait|clarif/i`
  - AC5 proof update: added Shell open→Escape→close cycle assertion proving ResolveModal is removed from DOM after DecisionViewport-triggered open.
- Quality evidence (quality-runner, scoped):
  - Tests: 85 passed, 0 failed, 0 skipped
  - Suites:
    - src/__tests__/ResolveModalUX_1388.test.tsx (17 passed)
    - src/__tests__/Shell_1389.test.tsx (16 passed)
    - src/__tests__/ResolveModalUX_1389.test.tsx (6 passed)
    - src/__tests__/DecisionViewport_1388.test.tsx (26 passed)
    - src/__tests__/ResolveModal_1193.test.tsx (9 passed)
    - src/__tests__/Shell_1192.test.tsx (11 passed)
  - Lint: clean (0 issues) on both changed files
- Commit:
  - da70c322 — test: refine AC2/AC5 proof assertions (#1389, builder)
- Result: AC2 and AC5 proof gaps are now explicitly covered in task-scoped test evidence.
[[2026-05-09]]
## Review Evidence
### Test Results
- quality-runner scoped gate on the current retry surface: 85 passed, 0 failed, 0 skipped across `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx`, `serve/cockpit/web/src/__tests__/ResolveModalUX_1389.test.tsx`, `serve/cockpit/web/src/__tests__/ResolveModal_1193.test.tsx`, `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx`, `serve/cockpit/web/src/__tests__/Shell_1389.test.tsx`, and `serve/cockpit/web/src/__tests__/Shell_1192.test.tsx`.
- The first quality-runner attempt failed with a frontend environment error (`document is not defined`). I retried once with an explicit frontend/jsdom hint per pipeline protocol; the retry succeeded and is the gating evidence.
- code-reader reviewed the same source and test surface. It flagged AC5 cancel-close proof and AC6 helper-branch proof as lax; after direct file review against the latest architecture re-review v3, I treated those two points as non-blocking for this task for the reasons recorded in the AC table below.

### Lint Results
- ESLint clean on `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/components/ResolveModal.tsx`, and the six scoped test files.
- VS Code diagnostics: no errors in `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/components/ResolveModal.tsx`, `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx`, `serve/cockpit/web/src/__tests__/ResolveModalUX_1389.test.tsx`, or `serve/cockpit/web/src/__tests__/Shell_1389.test.tsx`.

### Coverage
- `src/components/ResolveModal.tsx`: 94%
- `src/Shell.tsx`: 73.97%
- I did not fail on the module-level Shell percentage. This is a narrow frontend task, and the changed Shell paths are directly exercised by `Shell_1389` and adjacent scoped suites.

### Source / Commit Checks
- Multi-retry task ownership reconstructed from task history plus git log hits for builder commits `41ece747`, `8796bad0`, and `da70c322` in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`.
- I could not run `git diff` or `git status` in this tool surface, so dirty-tree contamination and TestFromAC immutability remain slightly lower-confidence than a full commit-object audit.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: decision UI shows pending decisions with task link/context, agent or request type, age, body or preview content, and clear loading, error, and empty states | `serve/cockpit/web/src/components/DecisionViewport.tsx:32-63`; `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx:75,99,119,138,164,171,181,213,237`; `serve/cockpit/web/src/Shell.tsx:200-203`; `serve/cockpit/web/src/__tests__/Shell_1389.test.tsx:198-287` | PASS |
| AC2: each resolution choice has a structurally separate PText consequence description and keyword-specific outcome proof | `serve/cockpit/web/src/components/ResolveModal.tsx:144,157,170`; `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx:67-137` | PASS |
| AC3: accidental approval is not the easiest path; no unsafe approved default | `serve/cockpit/web/src/components/ResolveModal.tsx:24,63-67,189`; `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx:144-188` | PASS |
| AC4: action labels and modal state are meaningful and PDS-compatible, with PButton primary/secondary controls | `serve/cockpit/web/src/components/ResolveModal.tsx:189-199`; `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx:190-216`; `serve/cockpit/web/src/__tests__/ResolveModalUX_1389.test.tsx:69-114` | PASS |
| AC5: keyboard and focus behavior meets #1388 expectations, and Shell proves the open-close cycle | Modal-local focus / Escape / aria-modal proof: `serve/cockpit/web/src/components/ResolveModal.tsx:58-89,122`; `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx:225-260`. Shell open plus Escape-close DOM-removal proof: `serve/cockpit/web/src/__tests__/Shell_1389.test.tsx:297-350`. Cancel-close remains compositionally covered by `serve/cockpit/web/src/__tests__/ResolveModal_1193.test.tsx:251-261` plus Shell wiring at `serve/cockpit/web/src/Shell.tsx:272-277`. Latest architecture re-review v3 routed the builder proof-refinement specifically to the Escape close-cycle test, which is now present. | PASS |
| AC6: expected decision errors use the frontend error contract from #1375 | Resolve path uses the helper directly at `serve/cockpit/web/src/components/ResolveModal.tsx:44`. Pending-decision polling continues to route non-OK responses through the same helper at `serve/cockpit/web/src/hooks/usePendingDRs.ts:41-52` and `serve/cockpit/web/src/hooks/usePollingFetch.ts:68-73`, and Shell renders hook errors at `serve/cockpit/web/src/Shell.tsx:176,203`. Latest architecture re-review v3 explicitly treated helper-internal branch assertions as non-blocking for this task. | PASS |
| AC7: implementation satisfies #1388 without changing backend decision lifecycle semantics | Builder-owned changes in this task history are frontend-only (`serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/components/ResolveModal.tsx`, and related tests). Commit presence reconstructed from `.git/logs/HEAD` / `.git/logs/refs/heads/dev` for `41ece747`, `8796bad0`, `da70c322`. | PASS |
| AC8: DecisionViewport is the primary decision listing surface accessible from Shell, showing loading, error, and empty states from usePendingDRs; DRStatusIndicator is no longer the sole listing surface | `serve/cockpit/web/src/Shell.tsx:26,200-203`; `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx:75,99,119,237`; `serve/cockpit/web/src/__tests__/Shell_1389.test.tsx:198-350` | PASS |

### Deductions
- `-0.03` No direct `git diff` / `git status` surface here; commit existence was reconstructed from `.git/logs/*` rather than full diff objects.
- `-0.02` Initial quality-runner pass failed on jsdom environment setup before succeeding on retry, so the test evidence carries a small environment-noise deduction.

### Verdict
- Confidence: `0.95`
- PASS. The latest builder cycle closed the previously blocking AC2 and AC5 proof gaps, the PButton migration remains covered, and the remaining code-reader objections are non-blocking after the latest architecture re-review narrowed the gate.

### Action
- Advance this task to docs.
[[2026-05-09]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Task is frontend-only (Shell.tsx, ResolveModal.tsx, DecisionViewport.tsx). `serve/cockpit/README.md` covers backend API only; no IN-scope prose doc describes the changed UI components. |
| 2 | Module docstrings | No | N/A | No Python `.py` files modified; all changes are TypeScript/React. |
| 3 | External attribution | No | N/A | No external patterns referenced in task body; uses existing PDS components and internal hooks. |
| 4 | Research doc | No | N/A | No `.owlbear/research/` document produced or linked. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/web/src/**` — matches `Shell.tsx` and `ResolveModal.tsx`. Footer updated from `b4ebbe64` → `4a1f76db`. Commit: `ca7528fc`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted in this task. |

### Scope Classification
- Changed files: `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/components/ResolveModal.tsx`, test files under `serve/cockpit/web/src/__tests__/`
- All application source: OUT-scope (no edit). Test files: OUT-scope.
- Diagram `share/diagrams/cockpit.excalidraw`: IN-scope — footer-only update applied.

### Files Updated
- `share/diagrams/cockpit.excalidraw` — footer timestamp updated (doc-writer commit `ca7528fc`)

### Child Tasks / DRs
None.

### Scratch Files
None found for task #1389.

### Review Evidence
Present. Final reviewer confidence: 0.95 — PASS.
[[2026-05-09]]
## Audit\n### Regression Detection\n- quality-runner mode full: Python 1255 passed, 71 failed (all in serve/kanban/tests — pre-existing kanban package internal failures, tracked in #1472–#1476); Frontend 2470 tests total, 9 failed (Shell_1344 timeout + DetailTab — known pre-existing instability, not #1389-related). Ruff: 15 violations in files not touched by #1389. ESLint: 4 issues in files not touched by #1389.\n- regression verdict: PASS — no task-caused regressions. All failures are in files outside #1389 scope.\n\n### Intent Verification\n- scope alignment: PASS (all 6 commits touch only cockpit frontend files: Shell.tsx, ResolveModal.tsx, test files, cockpit.excalidraw diagram)\n- purpose match: PASS (decision viewport integration into Shell + PButton migration + proof refinement — matches \"Implement Cockpit decision viewport and resolution UX\")\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 4/5\nOriginal AC had vague terms (\"PDS-compatible\", \"explains consequences\") that caused 2 reviewer rejection cycles. After v2 refinement (keyword patterns, explicit PButton variants, close-cycle proof), AC was specific and effective. v3 was routing-only. Final AC quality is strong but initial vagueness cost pipeline iterations.\n\n### Commit Integrity\n- upstream commit presence: PASS — 6 commits verified via git log: 87b6804b (test-writer), 41ece747 (builder), 5e5cc0e1 (test-writer), 8796bad0 (builder), da70c322 (builder), ca7528fc (doc-writer). All correctly attributed and scoped.\n- kanban commit packaging: PASS (archival commit follows)\n\n### Deduction Breakdown\nNo deductions applied. All regression failures are pre-existing and outside task scope. Intent and scope are clean. Architect quality 4/5 (≥3, no deduction). Review evidence present and thorough (final review at 0.95). Commit integrity verified with full diff objects.\n\n### Confidence: 1.00\n### Action: archive