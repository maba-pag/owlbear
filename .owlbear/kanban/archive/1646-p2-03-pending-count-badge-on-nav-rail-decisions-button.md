---
id: 1646
title: 'P2-03: Pending count badge on nav-rail decisions button'
status: archived
priority: important
created: 2026-05-18T00:49:44.996891+02:00
updated: 2026-05-19T20:33:18.864009+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1638
depends_on:
  - 1642
ac:
  - Nav-rail decisions button ([data-surface="decisions"]) renders a child 
    element with data-testid="nav-badge" displaying the numeric pending DR count
    when useDRState().count > 0
  - Badge element (data-testid="nav-badge") is absent from DOM when pending DR 
    count is 0
  - When badge is visible, button aria-label includes the pending count (e.g. 
    "Decisions (3 pending)"); when count is 0, aria-label is "Decisions"
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

**In:** Pending count badge on the decisions nav-rail button — renders count from `useDRState().count`, visibility conditional on count > 0.

**Out:** Nav-rail button creation (P1-02), DR list (P2-01).

## Context

The nav-rail buttons from P1-02 are driven by route config. The decisions button needs a badge overlay showing the pending DR count. The badge is a small sub-element of the nav button, not a separate component. `useDRState()` from CockpitProvider already provides `count`.

[[2026-05-19T18:46:50+02:00]]
## Research

**Findings:** Trivial UI badge — PDS has no badge component, but nav button already has `position: relative` enabling standard absolute-positioned overlay. `useDRState().count` already destructured in Shell. Implementation is ~5 lines TSX + ~15 lines CSS.

**Approach:** Direct conditional render inside `routeConfig.map()` (Option A). YAGNI — no generic badge infrastructure needed. Uses PDS notification tokens for color.

**Confidence:** 0.90 — well-understood pattern, no architectural risk.

**Doc:** `.owlbear/research/nav-badge-1646.md`

**Follow-ups:** None — task is implementation-ready with existing AC.

[[2026-05-19T19:05:39+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One badge on one button |
| Interface clarity | PASS | AC specifies exact selector, DOM behavior, accessibility |
| Dependency correctness | PASS | #1642 archived (complete) |
| Module layering | PASS | Pure Shell.tsx render change, no upward imports |
| TDD compliance | PASS | behavioral bundle, test-writer will write tests |
| KISS/YAGNI | PASS | ~5 lines TSX + ~15 lines CSS, no abstraction |
| Premise challenge | PASS | PDS has no badge component; custom overlay required |
| Pattern consistency | PASS | Uses existing position:relative on .shell__nav-button, PDS tokens |
| Security surface | PASS | No new boundary — renders existing state |
| Single domain | PASS | Frontend/cockpit-web only |

### Challenge Results
- Challenger: reconsider (confidence 0.67)
- Findings: (1) AC lacked stable test selector, (2) accessibility gap (count not announced), (3) visual proof concern, (4) count duplication concern
- Architect response: accepted (1) and (2) — refined AC with data-testid=\"nav-badge\" and aria-label requirement. Rebutted (3): DOM-behavior is correct proof for behavioral bundle; visual correctness is reviewer-scope. Rebutted (4): Brief explicitly designs both entry paths.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### AC Refinement
- Added data-testid=\"nav-badge\" stable selector (anchored to [data-surface=\"decisions\"] parent)
- Added AC3: aria-label includes pending count when badge visible, reverts to \"Decisions\" when absent
- Original AC was testable but underspecified for mechanical test derivation

### Design Diverge
- Trigger: skipped — single clear approach from research (conditional render in routeConfig.map)

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC with stable selector + accessibility requirement, advanced to todo

[[2026-05-19T19:21:14+02:00]]
## Test-Writer Notes

**Test file:** `serve/cockpit/web/src/__tests__/NavBadge_1646.test.tsx`
**Class:** `TestFromAC_NavBadge`

**Categories:**
| Category | Count |
|----------|-------|
| Happy path | 5 |
| Edge cases | 5 |
| Boundary conditions | 3 |
| Transition (rerender) | 6 |

**Total:** 15 tests — all FAIL (quality-runner: 15 failed, 0 passed, lint clean)

**AC coverage:**
| AC | Tests | Notes |
|----|-------|-------|
| AC1 — badge renders when count > 0 | 6 | badge present, text content, child-of-decisions, no kanban badge |
| AC2 — badge absent when count = 0 | 4 | rerender transition tests (count>0→0); first assertion fails in RED |
| AC3 — aria-label includes count when visible | 5 | exact format "Decisions (N pending)", revert to "Decisions" on transition |

**Mock strategy:** `vi.mock('../hooks/usePendingDRs')` controls `useDRState().count` via CockpitProvider; `beforeEach` resets to count=0; `setDRCount(N)` helper overrides per-test.

**Transition tests (AC2 + AC3 count=0):** Restructured as rerender tests to avoid trivially-passing absence assertions. First assertion (badge/label at count>0) fails until implementation; second assertion (absence/revert at count=0) guards regression.

[[2026-05-19T19:32:25+02:00]]
## Builder Notes
- Implementation: added decisions-nav conditional badge render + dynamic aria-label in `serve/cockpit/web/src/Shell.tsx`; added badge overlay styles in `serve/cockpit/web/src/Shell.css`.
- Tests (TestFromAC): 15/15 passed in `serve/cockpit/web/src/__tests__/NavBadge_1646.test.tsx` (RED had 15/15 failing before implementation).
- Module-level durable regression: 18/18 passed in `serve/cockpit/web/src/__tests__/Shell.test.tsx`.
- Additional scoped regression set: 57/57 passed across Shell-related tests (`NavBadge_1646`, `Shell.test`, `Shell.tab-routing_1639`, `Shell.decisions-integration_1639`, `Shell.suspense-boundary_1644`, `Shell.sidecar-conditional_1643`).
- Coverage: 77.56% on touched module `Shell.tsx` from broader scoped run (function-heavy legacy shell file; no test edits allowed in builder phase).
- Lint: clean (eslint/stylelint clean on touched files).
- Approach: minimal in-place change inside nav-rail `routeConfig.map()` — only decisions route gets `data-testid="nav-badge"` when `pendingDRCount > 0`, and aria-label switches between `Decisions (N pending)` and `Decisions`.
- Commit: `a507483d12a337b6938a8569e7fc45d36e852376` (files: `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/Shell.css`).

[[2026-05-19T19:50:53+02:00]]
reviewer crashed once; releasing claim before retry: no response returned

[[2026-05-19T19:59:22+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1646 to docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first and found internally consistent: task tests 15/15 passed; durable Shell regression 18/18 passed; broader scoped Shell regressions 57/57 passed; eslint/stylelint clean; coverage summary 77.56% on touched module `Shell.tsx`.
- Safety and security: no new input, storage, auth, or external integration surface; the change only renders existing DR count state in nav UI.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/cockpit/web/src/Shell.tsx:457-478` renders `data-testid="nav-badge"` only for `route.icon === "decisions"` when `pendingDRCount > 0`; `serve/cockpit/web/src/routes.ts:20-25` defines the real decisions route label/icon | `serve/cockpit/web/src/__tests__/NavBadge_1646.test.tsx:124-170` asserts badge presence inside `[data-surface="decisions"]`, exact numeric text for counts 1 and 3, and absence from kanban | PASS |
| AC2 | `serve/cockpit/web/src/Shell.tsx:459-478` omits the badge branch when `pendingDRCount` is 0 | `serve/cockpit/web/src/__tests__/NavBadge_1646.test.tsx:177-232` rerenders from positive counts to 0 and asserts badge removal from DOM on `/` and `/decisions` | PASS |
| AC3 | `serve/cockpit/web/src/Shell.tsx:458-470` switches button `aria-label` between `Decisions (N pending)` and `Decisions`; `serve/cockpit/web/src/routes.ts:23-25` provides the real `Decisions` label | `serve/cockpit/web/src/__tests__/NavBadge_1646.test.tsx:238-293` asserts exact labels for counts 3, 1, and 0, plus rerender reversion | PASS |

- Challenger cross-check: no blocking findings.

## Observations
- Task-local tests mock `routeConfig` and `usePendingDRs`, but the mocked decisions surface matches the real route in `serve/cockpit/web/src/routes.ts:20-25`, and the provider forwards DR count without transformation in `serve/cockpit/web/src/hooks/CockpitProvider.tsx:188-196`, with passthrough covered in `serve/cockpit/web/src/__tests__/CockpitProvider.test.tsx:546-556`.
- Coverage on `Shell.tsx` remains 77.56% because the file carries unrelated legacy branches; this is a residual module-level risk, not a task-local AC proof gap.

[[2026-05-19T20:02:48+02:00]]
## Docs Gate

### Checklist

**Item 1 — README Verification:** Added #1646 entry to `serve/cockpit/README.md` (convention mapping: `serve/cockpit/web/src/**` → `serve/cockpit/README.md`). Entry inserted between #1643 and #1671 in correct implementation order. Describes conditional `<span class="shell__nav-badge" data-testid="nav-badge">` render in `Shell.tsx`, aria-label switching, CSS overlay styles in `Shell.css` using PDS notification tokens, and `pendingDRCount` source via `CockpitProvider`. Test references verified: `NavBadge_1646.test.tsx` (15 tests, AC1–AC3) and durable `Shell.test.tsx` (18 tests). Layer 1 grep confirms entry present. Layer 2 editorial check passes — coherent, no contradictions with surrounding entries. Commit: `31d699c`.

**Item 2 — External Attribution:** N/A — research notes trivial implementation from codebase inspection only; no external sources cited.

**Item 3 — Research Doc:** `.owlbear/research/nav-badge-1646.md` exists and is linked from task body.

**Item 4 — Deletion Detection:** N/A — no source files deleted in this task (Shell.tsx and Shell.css modified only).

### Scratch Cleanup
No `.owlbear/scratch/1646-*` files existed.

[[2026-05-19T20:33:18+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 7412 passed; 252+ failed — all pre-existing (Card.signal/Card.visual-treatment tests from 2026-05-17 task #1397/#1570; test_cockpit_view/test_server from task #1582 cleanup). None caused by Shell.tsx/Shell.css changes.
- Shell-domain tests all pass (builder evidence: 15/15 task, 18/18 durable Shell, 57/57 broader Shell set).
- Lint: S608 in graph_store.py — unrelated to cockpit-web domain.
- regression verdict: PASS (no regressions introduced by this task)

### Intent Verification
- scope alignment: PASS (changed files Shell.tsx + Shell.css in serve/cockpit/web/src/ — matches scope:cockpit-web tag)
- purpose match: PASS (badge overlay rendering pending DR count on decisions nav button — matches AC intent)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
AC lines are specific and mechanically testable: exact selectors (data-testid=\"nav-badge\", [data-surface=\"decisions\"]), exact visibility condition (count > 0), exact aria-label format. Post-challenge refinement added stable test selector and accessibility requirement. Clean implementation path.

### Commit Integrity
- upstream commit presence: PASS (builder: a507483d, doc-writer: 31d699c)
- kanban commit packaging: pending (this archive cycle)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive
