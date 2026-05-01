---
id: 1230
title: Frontend — PDS migration (design system consistency)
status: in-progress
priority: nice-to-have
created: 2026-04-30 16:31:18.656061+00:00
updated: 2026-05-01T21:22:43.026869+00:00
tags:
- cockpit
- frontend
- design
parent:
depends_on:
- 1225
- 1228
- 1229
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Replace raw HTML elements with Porsche Design System v4 components for visual consistency. Follows established pattern in RepairPanel.tsx (PButton, PSpinner, PText imports from `@porsche-design-system/components-react`).

## Acceptance Criteria
- [ ] `<button>` elements replaced with `<PButton>` (appropriate variant per context) — applies to ConfirmDialog, ArchivalModal, ActivityTab, DetailTab, ResolveModal, Shell.tsx (td:1)
- [ ] `<h3>` headings in ArchivalModal and ResolveModal replaced with `<PHeading tag="h3">` (td:1)
- [ ] Standalone `<p>` in ArchivalModal, DRStatusIndicator popover, HealthBadge popover replaced with `<PText>` — `<span>` inside Card, Column, badge labels are exempt (td:1)
- [ ] Form controls migrated: `<input type="text">` → `<PInputText>`, `<select>` → `<PSelect>`, `<textarea>` → `<PTextarea>` — in DetailTab, ArchivalModal, ResolveModal; use `hideLabel` prop where no visible label exists (td:2)
- [ ] Card.tsx and Column.tsx: NO structural changes — preserve drag-drop integrity from #1229 (td:0)
- [ ] Context menu in KanbanBoard.tsx: NO migration in this task (td:0)
- [ ] All affected suites green: DetailTab.test, ArchivalModal_1241.test, ArchivalModal_1245.test, ResolveModal_1193.test, ResolveModal_plugins_1194.test, Shell.test, HealthBadge.test, DRStatusIndicator_1191.test, ActivityTab.test (td:1)

## Scope
**In scope:** ConfirmDialog.tsx, ArchivalModal.tsx, ActivityTab.tsx, DetailTab.tsx, ResolveModal.tsx, Shell.tsx, HealthBadge.tsx, DRStatusIndicator.tsx
**Out of scope:** Card.tsx, Column.tsx, KanbanBoard.tsx (context menu), RepairPanel.tsx (already migrated)

## Notes
- PDS v4 component names verified against `node_modules/@porsche-design-system/components-react/esm/public-api.mjs`
- Context menu migration deferred — PDS PFlyout/PPopover require anchor elements, incompatible with coordinate-positioned right-click pattern without research
- Follow-up: context menu PDS migration (requires architectural investigation of PFlyout/PPopover applicability)

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: swap raw HTML → PDS components across in-scope files |
| Interface clarity | PASS | AC names exact components, files, and exemptions |
| Dependency correctness | PASS | 1225/1228/1229 all archived; Card/Column explicitly exempted to protect #1229 drag-drop |
| Module layering | PASS | No new imports beyond existing PDS package; same barrel import pattern as RepairPanel |
| TDD compliance | PASS | td:2 on form controls, td:1 on buttons/text/headings, specific test suites named |
| KISS/YAGNI | PASS | No new abstractions — direct element-to-component swaps |
| Premise challenge | PASS | PDS already installed/configured; RepairPanel proves pattern; consistency gap is real |
| Pattern consistency | PASS | Follows RepairPanel.tsx import and usage pattern |
| Security surface | PASS | No new boundaries — PDS components wrap same native elements |
| Single domain | PASS | Frontend design-system domain only |

### Challenger Results
- Confidence: 0.34 (initial draft) → issues addressed
- Critical fix: PTextFieldWrapper/PSelectWrapper/PTextareaWrapper → PInputText/PSelect/PTextarea (verified in public-api.mjs)
- Critical fix: task body updated with refined AC (was still showing original)
- Moderate fix: form migration elevated to td:2
- Moderate fix: Card/Column/KanbanBoard explicitly exempted
- Moderate fix: Shell.tsx added to scope; specific test suites enumerated
- Minor fix: span exemption made concrete (Card, Column, badge labels)
[[2026-05-01]]
APPROVED after AC refinement. Original AC used wrong PDS v4 component names and lacked scope boundaries. Refined: verified component exports against public-api.mjs (PInputText/PSelect/PTextarea not wrappers), explicit Card/Column/KanbanBoard exemptions, form migration elevated to td:2, specific test suites enumerated. Context menu deferred as follow-up (requires research on PFlyout/PPopover anchor constraints).
[[2026-05-01]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx
- Classes: TestFromAC_PdsMigration_Buttons, TestFromAC_PdsMigration_Headings, TestFromAC_PdsMigration_Text, TestFromAC_PdsMigration_FormControls
- Tests per category (AC4 td:2): happy 12, edge 4, boundary 2
- Total: 54 tests, all FAIL (0 passed)
- ruff: N/A (TypeScript); ESLint: clean (0 errors, 0 warnings)

### AC Coverage

| AC | td | Tests |
|----|----|----|
| AC1: `<button>` → `<PButton>` (ConfirmDialog, ArchivalModal, ActivityTab, DetailTab, ResolveModal, Shell) | 1 | 16 tests across 6 components |
| AC2: `<h3>` → `<PHeading tag="h3">` (ArchivalModal, ResolveModal) | 1 | 8 tests |
| AC3: `<p>` → `<PText>` (ArchivalModal error, refs hint, DRStatusIndicator empty, HealthBadge empty) | 1 | 8 tests |
| AC4: Form controls → PInputText/PSelect/PTextarea; hideLabel where unlabeled | 2 | 22 tests (happy+edge+boundary) |
| AC5: Card/Column no change | 0 | skipped (td:0) |
| AC6: KanbanBoard context menu no change | 0 | skipped (td:0) |
| AC7: All affected suites green | 1 | covered by existing suites (regression CI gate) |

### Failure Pattern
All 54 tests fail because components render raw HTML (`<button>`, `<h3>`, `<p>`, `<input>`, `<select>`, `<textarea>`) instead of PDS custom elements (`p-button`, `p-heading`, `p-text`, `p-input-text`, `p-select`, `p-textarea`). Tests asserting PDS element presence return null; tests asserting raw element absence fail because raw elements are present.

### Note on AC7
"All affected suites green" is a builder constraint enforced by the CI gate and existing suites. No new tests added for AC7 — existing suites (DetailTab.test, ArchivalModal_1241, ArchivalModal_1245, ResolveModal_1193, etc.) serve as the regression guard.