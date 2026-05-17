---
id: 1618
title: 'P2-11: Complex integrations — modals → PModal'
status: review
priority: important
created: 2026-05-16T03:37:02.326584+00:00
updated: 2026-05-16T20:31:36.195692+00:00
tags:
  - frontend
  - pds
  - phase-2
parent: 1590
depends_on: []
ac:
  - ConfirmDialog, ResolveModal, and ArchivalModal render via PModal; 
    hand-rolled focus trap, Tab cycling, position:fixed overlay, and z-index 
    removed from all three
  - 'Focus behavior preserved per modal: (a) all three trap Tab within modal boundary
    on open; (b) ResolveModal returns focus to DR trigger button on close; (c) ArchivalModal
    returns focus to originating task card on close (context-menu opener is destroyed
    — use PModal onDismiss + explicit fallback target); (d) ConfirmDialog returns
    focus to the action button that opened it'
  - 'Dismiss policy per modal: ConfirmDialog uses role=alertdialog, disableBackdropClick=true,
    dismissButton=false (Escape + in-body Cancel/Confirm only); ResolveModal and ArchivalModal
    allow backdrop click, Escape, dismiss button (X), and in-body Cancel/Close button'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Custom modals → PModal. Focus trapping, focus return, dismiss behavior preserved.

Scope: Complex integrations (modals) only.
Out of scope: Simple swaps, cards, sidecar IA, filter panel.

## Research
- Research doc: .owlbear/research/1618-modal-pmodal-migration.md
- Sources: 7 studied, 5 high-relevance
- Recommendation: Proceed with PModal migration using per-modal dismiss policy (confidence: 0.75)
- Follow-up tasks created: none (test task #1613 already exists)
- Decision requests: none

## Challenge Results
- Challenger: reconsider (0.38 confidence in original)
- Key challenges: AC-3 backdrop dismiss contradiction, focus-return evidence gap, test regression surface undercounted, PModal dismiss button default, shadow DOM selectors
- Researcher response: revised — accepted 4 of 7 challenges. Reduced confidence from .85 to .75. Added per-modal dismiss policy map (ConfirmDialog = alertdialog pattern, no backdrop dismiss). Confirmed focus return via MDN + 2 independent sources. Documented test regression surface and shadow DOM risk.

[[2026-05-16T17:29:29+02:00]]
Research complete. Doc: .owlbear/research/1618-modal-pmodal-migration.md. PModal migration is feasible — native <dialog> provides focus trap, focus return, Escape dismiss, backdrop. Key finding: per-modal dismiss policy required (ConfirmDialog = alertdialog pattern with disableBackdropClick, others allow full dismiss). ~135 LOC of duplicated a11y code eliminated across 4 files. Shadow DOM test selector risk documented. Commit: 94c4a452.

[[2026-05-16T18:08:46+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Modal→PModal migration only; 3 named components |
| Interface clarity | PASS | Per-modal dismiss policy and focus-return targets now explicit in AC |
| Dependency correctness | PASS | No runtime deps; test task #1613 deprecated (existing E2E covers baseline) |
| Module layering | PASS | Components consume PModal from PDS package; no upward imports |
| TDD compliance | PASS | overlay-behavior-1563.spec.ts + KeyboardA11y_1395.test.tsx cover baseline; builder updates selectors |
| KISS/YAGNI | PASS | Removes ~135 LOC duplication; no new abstractions |
| Premise challenge | PASS | PModal wraps native <dialog> — correct platform primitive |
| Pattern consistency | PASS | Other PDS components already imported from @porsche-design-system/components-react |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Frontend/component layer only |

### Challenge Results
- Challenger: reconsider (0.64 confidence)
- Key challenges: (1) AC-3 blanket dismiss vs per-modal policy, (2) AC-2 not mechanically verifiable per modal, (3) ArchivalModal disappearing-trigger focus-return edge case, (4) caller contracts unclear, (5) dismiss paths incomplete
- Architect response: Accepted challenges 1-3, 5. Rewrote all three AC lines to be per-modal specific and mechanically verifiable. AC-2(c) now explicitly names the disappearing-trigger case and requires onDismiss + fallback target. For (4): component prop interfaces (onClose, onRefresh, onResolved) are preserved; only internal focus-management props (returnFocusTo, previousFocusRef) are removed since PModal handles them. This is clarified in the body context.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: overlay-behavior-1563.spec.ts (E2E focus trap + return), KeyboardA11y_1395.test.tsx (ConfirmDialog focus), ResolveModalUX.pds-buttons.test.tsx, KanbanBoard.archive-handler.test.tsx
- Test-writer: PROCEED (builder must update existing test selectors for shadow DOM + add dismiss-policy assertions)

### Builder Guidance
- Reference per-modal config map in research doc §3.3
- ArchivalModal: native <dialog> focus return will fail because context-menu opener is destroyed before close. Wire PModal onDismiss to focus `archivalReturnFocusRef.current` (the task card) in KanbanBoard.tsx
- Shadow DOM: Playwright accesses shadow DOM by default; Vitest/Testing Library may need shadow-aware queries for unit tests
- Existing test suites that will need selector updates: overlay-behavior-1563.spec.ts, KeyboardA11y_1395.test.tsx, ResolveModalUX.pds-buttons.test.tsx, KanbanBoard.archive-handler.test.tsx

[[2026-05-16T18:44:42+02:00]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/PModalMigration_1618.test.tsx`
- Class: `TestFromAC_PModalMigration`
- Commit: `912ef5e4`

### Tests per category (27 total, all FAIL)

| Category | Count | AC |
|----------|------:|-----|
| Happy path (p-modal rendered, open) | 6 | AC-1, AC-3 |
| Edge cases (no hand-rolled div, no position:fixed) | 6 | AC-1 |
| Error paths (dismiss event does not fire wrong callback) | 4 | AC-2 |
| Boundary conditions (dismiss fires correct callback, focus fallback) | 11 | AC-2, AC-3 |

### AC coverage

| AC line | Tests |
|---------|-------|
| AC-1: all three render via p-modal, no position:fixed, no div[role="dialog"] | 9 (3 per modal) |
| AC-2: dismiss event calls correct callback, no wrong callback; ArchivalModal focus fallback | 7 |
| AC-2(c): fallback target focus() called on dismiss | 1 |
| AC-3: ConfirmDialog alertdialog+disableBackdropClick+no dismissButton | 4 |
| AC-3: ResolveModal/ArchivalModal allow all dismiss methods | 6 |

### RED verification
quality-runner: 27 failed, 0 passed. ESLint: clean.

[[2026-05-16T19:53:27+02:00]]
## Builder Notes
Files changed:
- serve/cockpit/web/src/components/ConfirmDialog.tsx
- serve/cockpit/web/src/components/ResolveModal.tsx
- serve/cockpit/web/src/components/ArchivalModal.tsx

Implementation summary:
- Migrated `ConfirmDialog`, `ResolveModal`, and `ArchivalModal` root wrappers from hand-rolled `<div role="dialog">` overlays to `PModal`.
- Removed custom modal Tab-cycling / focus-trap keyboard handlers and inline fixed-overlay styles from all three components.
- Wired dismiss callbacks per AC:
  - ConfirmDialog: `onDismiss -> onCancel`, `disableBackdropClick=true`, `dismissButton=false`, `aria.role=alertdialog`.
  - ResolveModal: `onDismiss -> onClose`, open PModal with existing submit/close action wiring unchanged.
  - ArchivalModal: `onDismiss` now performs explicit fallback focus (`returnFocusTo?.focus()`) before `onClose()`.
- Preserved existing action callback contracts (`onCancel`, `onConfirm`, `onClose`, `onResolved`, `onRefresh`).

Quality evidence (quality-runner):
- RED gate before implementation:
  - serve/cockpit/web/src/__tests__/PModalMigration_1618.test.tsx
  - Result: 27 failed / 0 passed (as expected), eslint clean.
- GREEN verification after implementation:
  - serve/cockpit/web/src/__tests__/PModalMigration_1618.test.tsx
  - Result: 27 passed / 0 failed, eslint clean.
- Regression-focused scoped verification:
  - serve/cockpit/web/src/__tests__/PModalMigration_1618.test.tsx
  - serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx
  - serve/cockpit/web/src/__tests__/ResolveModalUX.pds-buttons.test.tsx
  - serve/cockpit/web/src/__tests__/KanbanBoard.archive-handler.test.tsx
  - Result: 64 passed / 0 failed, eslint clean on touched component files.

Additional note:
- A proof-scope attempt including Playwright E2E (`overlay-behavior-1563.spec.ts`) was blocked by pre-existing workspace TypeScript build errors in unrelated files (`Card.tsx`, `DetailTab.tsx`).

Commit:
- 2fbc8e12
- feat: migrate complex modals to PModal (#1618, builder)
