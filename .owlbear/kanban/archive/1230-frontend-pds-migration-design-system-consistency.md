---
id: 1230
title: Frontend — PDS migration (design system consistency)
status: archived
priority: medium
created: 2026-04-30 16:31:18.656061+00:00
updated: 2026-05-02T05:51:45.643920+00:00
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
[[2026-05-01]]
## Builder Notes
- Files changed (not committed): serve/cockpit/web/src/components/ConfirmDialog.tsx, serve/cockpit/web/src/components/ArchivalModal.tsx, serve/cockpit/web/src/components/ActivityTab.tsx, serve/cockpit/web/src/components/DetailTab.tsx, serve/cockpit/web/src/components/ResolveModal.tsx, serve/cockpit/web/src/components/HealthBadge.tsx, serve/cockpit/web/src/components/DRStatusIndicator.tsx, serve/cockpit/web/src/Shell.tsx
- RED verification (quality-runner): 54 failed / 54 total in serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx, lint clean.
- GREEN attempt result (quality-runner): 50 passed / 54 total, lint clean.

### Reject reason (test-assumption mismatch)
Remaining failures are in ArchivalModal tests that require state transitions via a raw native `<select>` handle while the same suite also asserts there must be no raw `<select>` after PDS migration.

Conflicting expectations in the same TestFromAC suite:
- `AC4 happy: ArchivalModal reason uses PSelect` asserts `container.querySelector('select')` is `null`.
- Other tests attempt to drive reason changes with:
  - `const select = container.querySelector('select')`
  - `if (select) fireEvent.change(select, ...)`
  and then assert refs/error UI that depends on that change.

Because `select` is required to be absent, those change events never fire, leaving reason-dependent UI unreachable in test execution.

### Failing tests (4)
- AC3 ArchivalModal error message uses PText > renders p-text[data-testid="archival-error"] for submission errors
- AC3 ArchivalModal refs hint uses PText > renders p-text for "Required - enter at least one task ID" hint when refs visible
- AC4 happy ArchivalModal refs input uses PInputText when visible > renders p-input-text for refs when reason requires refs
- AC4 boundary ArchivalModal labeled fields do not get hide-label > p-input-text for refs does NOT have hide-label

### Test-writer: what to fix
- Update ArchivalModal interaction steps in TestFromAC_PdsMigration_FormControls/Text to drive `p-select` (or a component-level helper) instead of querying native `select`.
- Keep no-raw-native-element assertions as-is (`querySelector('select') === null`) after migrating interaction helpers.
- Re-run suite to confirm those 4 tests become reachable and meaningful under PDS controls.
[[2026-05-01]]
## Test-Writer Notes
- Retry: fixed 7 ArchivalModal interaction helpers across TestFromAC_PdsMigration_Text and TestFromAC_PdsMigration_FormControls.
- Root cause: tests queried `container.querySelector('select')` (native element), which returns null after PDS migration to `p-select`. The `if (select)` guard prevented all state-change events from firing, leaving reason-dependent UI (refs input, refs hint, error) unreachable.
- Fix: replaced native `select` queries with `container.querySelector('p-select')` + `fireEvent(pSelect, new CustomEvent('change', { detail: { value: '...' }, bubbles: true }))` — matches the `readControlValue(event.detail?.value)` path in the component.
- All 54 tests now PASS against current implementation (builder's uncommitted changes are correct).
- Lint: ESLint clean, 0 violations.
- Commit: eb54c8dc — test: fix ArchivalModal interaction helpers for PDS migration (#1230, test-writer)
- Builder note: implementation files are already correct but uncommitted — builder should verify 54/54 pass then commit.
[[2026-05-01]]
## Builder Notes
- Implementation status: in-scope migration files remain updated for PDS components (`ConfirmDialog.tsx`, `ArchivalModal.tsx`, `ActivityTab.tsx`, `DetailTab.tsx`, `ResolveModal.tsx`, `HealthBadge.tsx`, `DRStatusIndicator.tsx`, `Shell.tsx`).
- RED baseline evidence: prior task history already recorded `PdsMigration_1230` as 54/54 failing before implementation.
- GREEN evidence (task-scoped): `serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx` is 54/54 passing.
- Frontend lint evidence: ESLint over changed TSX files and `PdsMigration_1230.test.tsx` is clean.
- Quality-runner note: for TSX files, `ruff` output is a known false-positive parser mismatch (Python linter over TypeScript), per `h-quality-runner` limitations.

### Reject reason (test-assumption mismatch in AC7 suites)
AC7 requires legacy regression suites to be green (`DetailTab.test`, `ArchivalModal_1241`, `ArchivalModal_1245`, `ResolveModal_1193`, `ResolveModal_plugins_1194`, `Shell.test`, `HealthBadge.test`, `DRStatusIndicator_1191`, `ActivityTab.test`). Scoped run shows 4 files failing with 44 failing tests total.

Observed blockers:
- `ArchivalModal_1241` expects native `select` and native `h3` (`reason select not found`, `querySelector('h3')` assertions), but this task’s AC explicitly migrates to `PSelect` and `PHeading`.
- `DetailTab.test` and `ResolveModal_plugins_1194.test` fail on web-component internals assumptions (`this.internals?.setValidity/setFormValue is not a function`) triggered by migrated PDS controls in test environment.
- `ResolveModal_plugins_1194.test` additionally fails plugin assertions (`expected [] to contain remarkGfm/rehypeSanitize`) in same regression pass.

### Test-writer: what to fix
- Update AC7 legacy suites to align with PDS migration contract (query/interact through `p-*` controls instead of native `input/select/textarea/h3`).
- Add/adjust test-environment shims for PDS form components that require ElementInternals APIs.
- Reconcile plugin expectations in `ResolveModal_plugins_1194.test` with current renderer/plugin wiring so AC7 can serve as a stable regression gate.

- Commit status: no builder commit in this pass because gate AC7 is still red under current test assumptions.
[[2026-05-02]]
## Test-Writer Notes
- Retry (AC7 legacy suite fixes): updated ArchivalModal_1241.test.tsx and DetailTab.test.tsx to align with PDS migration contract.
- Commit: 8142e272 — test: fix AC7 legacy suites for PDS migration (#1230, test-writer)

### Changes made

**ArchivalModal_1241.test.tsx:**
- Added `beforeAll` ElementInternals shim — newer jsdom has partial `attachInternals` lacking `setFormValue`; the conditional shim in vitest.setup.ts no longer applies. Fix: unconditional override in test file. This was the root cause of all 26 "p-select not found" failures (p-select componentWillLoad threw on mount).
- AC2: `querySelector('h3')` → `querySelector('p-heading')` (ArchivalModal uses PHeading after migration)
- AC3: Replaced `document.activeElement === select` with `HTMLElement.prototype.focus` spy to verify the component calls `.focus()` on p-select (jsdom does not update activeElement for PDS custom elements)
- AC4: `select?.options` → `pSelect?.querySelectorAll('option')` (options are native children of p-select)
- AC5 "shows" tests: `input[type="text"]` → `p-input-text`
- AC15 focus trap: Updated focusable selector to include `p-button/p-input-text/p-select/p-textarea`. Changed from `document.activeElement` assertion to `vi.spyOn(targetEl, 'focus')` + `tabIndex=0` trick to make custom elements focusable in jsdom.

**DetailTab.test.tsx:**
- Added same `beforeAll` ElementInternals shim.
- "renders title as input field": `input[data-field="title"]` → `p-input-text[data-field="title"]`
- "title input shows value": `input[data-field="title"].value` → `p-input-text[data-field="title"]` + `.value ?? getAttribute('value')` check
- "clicking toggle reveals textarea": `textarea[data-field="body"]` → `p-textarea[data-field="body"]`
- "save body includes edited content": `textarea` → `p-textarea` + `fireEvent(el, new CustomEvent('change', { detail: { value }, bubbles: true }))` matching readControlValue pattern

### AC7 suite results after fixes
| Suite | Result |
|-------|--------|
| DetailTab.test.tsx | ✅ 43/43 pass |
| ArchivalModal_1241.test.tsx | ⚠️ 2 fail (source regression — see below) |
| ArchivalModal_1245.test.tsx | ⚠️ 3 fail (source regression — see below) |
| ResolveModal_1193.test.tsx | ✅ 7/7 pass |
| ResolveModal_plugins_1194.test.tsx | ⚠️ 2 fail (source regression — see below) |
| Shell_966.test.tsx | ✅ pass |
| HealthBadge.test.tsx | ✅ pass |
| ActivityTab.test.tsx | ✅ pass |
| DRStatusIndicator_1191.test.tsx | ✅ pass |

**Total: 170 passed / 7 failed (source regressions, not test issues)**

### Builder: 3 source fixes required

**Fix 1 — ArchivalModal.tsx hint text (em dash):**
`ArchivalModal_1241` (AC10) and `ArchivalModal_1245` both require em dash `—` in the hint text.
The PDS migration introduced a regression: `<PText>Required - enter at least one task ID</PText>` must be `<PText>Required — enter at least one task ID</PText>`.

**Fix 2 — ResolveModal.tsx: restore ReactMarkdown plugins:**
Commit `66dd18b6` ("fix: update decision resolution endpoint") accidentally removed `remarkGfm`/`rehypeSanitize` from ResolveModal. They were correctly added in `9cf3a3b7` (#1194 builder). Restore:
```tsx
<ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
  {dr.body}
</ReactMarkdown>
```
Also restore the two imports (`import remarkGfm from 'remark-gfm'` and `import rehypeSanitize from 'rehype-sanitize'`).

After both fixes, all 9 AC7 suites should be green.
[[2026-05-02]]
## Builder Notes
- Implementation: restored markdown plugin wiring in [serve/cockpit/web/src/components/ResolveModal.tsx](serve/cockpit/web/src/components/ResolveModal.tsx).
- Fixes applied:
  - Re-added `remark-gfm` and `rehype-sanitize` imports.
  - Restored `<ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>` so plugin expectations in AC7 regression tests are satisfied.
- Tests:
  - Scoped task suite + AC7 regression suites: 231 passed, 0 failed, 0 skipped.
  - Included: `PdsMigration_1230`, `DetailTab`, `ArchivalModal_1241`, `ArchivalModal_1245`, `ResolveModal_1193`, `ResolveModal_plugins_1194`, `Shell_966`, `HealthBadge`, `DRStatusIndicator_1191`, `ActivityTab`.
- Coverage:
  - Overall scoped run: 91.78%.
  - `ResolveModal.tsx`: 93.26%.
  - `ArchivalModal.tsx`: 90.29%.
- Lint: ESLint clean (0 violations) on all in-scope migrated components.
- Commit: `8d48fb79e0322d7a193ce6ae8c10446d9f55ea81` (`fix: restore ResolveModal markdown plugins (#1230, builder)`).

### Evidence Summary
- Prior RED baseline for `PdsMigration_1230` (54/54 failing) is documented in earlier task history.
- Current GREEN verification confirms task tests and listed AC7 legacy suites are all passing after the source fix.

### Post-task Reflection
- Problems faced: retry-cycle context had stale mixed notes; the actionable blocker was narrowed by rerunning only the named failing suites.
- Workaround applied: trusted test-writer’s component-level diagnosis, then validated with quality-runner before and after code change.
- Pattern discovered: plugin-wiring regressions can hide behind unrelated PDS migration noise; focused suite selection isolates root cause quickly.
- Quality gap: task history carried contradictory interim states; scoped reruns are necessary to avoid false reject loops.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run: 245 passed, 0 failed, 0 skipped.
- Included suites: serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx, serve/cockpit/web/src/__tests__/DetailTab.test.tsx, serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx, serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx, serve/cockpit/web/src/__tests__/ResolveModal_1193.test.tsx, serve/cockpit/web/src/__tests__/ResolveModal_plugins_1194.test.tsx, serve/cockpit/web/src/__tests__/Shell.test.tsx, serve/cockpit/web/src/__tests__/HealthBadge.test.tsx, serve/cockpit/web/src/__tests__/DRStatusIndicator_1191.test.tsx, serve/cockpit/web/src/__tests__/ActivityTab.test.tsx.

### Diagnostics
- VS Code diagnostics: no errors in the 18 in-scope TSX source/test files.
- Lint: quality-runner lint is not meaningful for TSX; no Python files were in scope.

### Coverage
- Scoped aggregate coverage: 63.29%.
- Module detail: ActivityTab.tsx 89.06%, ArchivalModal.tsx 90.29%, ConfirmDialog.tsx 73.33%, DRStatusIndicator.tsx 92.59%, DetailTab.tsx 93.41%, HealthBadge.tsx 92.00%, ResolveModal.tsx 93.26%, Shell.tsx 75.00%.
- Per review protocol, the module percentages above are informational here. The changed PDS migration lines are directly exercised by the passing suites; low whole-file percentages on broader components are not the gate.

### AC Compliance
| AC | Evidence | Status |
|---|---|---|
| AC1: button elements replaced with PButton, appropriate variant per context | Source uses context-specific variants in serve/cockpit/web/src/components/ConfirmDialog.tsx:14-15, serve/cockpit/web/src/components/ActivityTab.tsx:50-62, serve/cockpit/web/src/components/ArchivalModal.tsx:270-279, serve/cockpit/web/src/components/DetailTab.tsx:186-214, serve/cockpit/web/src/components/ResolveModal.tsx:128-136, serve/cockpit/web/src/Shell.tsx:126. The TestFromAC suite only proves p-button presence and raw button absence in serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx:189-294; it never asserts the required variant values. A wrong variant would still pass. | FAIL |
| AC2: ArchivalModal and ResolveModal headings use PHeading tag=h3 | PHeading usage is present in serve/cockpit/web/src/components/ArchivalModal.tsx:222 and serve/cockpit/web/src/components/ResolveModal.tsx:67. The task suite checks p-heading presence, tag=h3, and no raw h3 in serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx:310-343. | PASS |
| AC3: listed standalone p elements replaced with PText | PText usage is present in serve/cockpit/web/src/components/ArchivalModal.tsx:248-283, serve/cockpit/web/src/components/DRStatusIndicator.tsx:35-47, and serve/cockpit/web/src/components/HealthBadge.tsx:34-45. The task suite checks PText presence and raw p absence in serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx:373-448. | PASS |
| AC4: text/select/textarea controls migrated to PInputText, PSelect, PTextarea; hideLabel where unlabeled | Structural migration and hide-label checks are present in serve/cockpit/web/src/components/DetailTab.tsx:121-176, serve/cockpit/web/src/components/ArchivalModal.tsx:225-262, serve/cockpit/web/src/components/ResolveModal.tsx:98-121 and are covered in serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx:469-597. Secondary note: DetailTab payload tests currently mutate body only, so title/priority propagation through readControlValue is thinner than ideal. | PASS |
| AC5: Card.tsx and Column.tsx unchanged structurally | grep_search for PDS imports/components in serve/cockpit/web/src/components/Card.tsx and serve/cockpit/web/src/components/Column.tsx returned no matches, and these files were not in the builder changed-file list. | PASS |
| AC6: KanbanBoard context menu not migrated in this task | KanbanBoard still renders the raw coordinate-positioned context menu at serve/cockpit/web/src/KanbanBoard.tsx:223-225, and grep_search found no PDS component imports in that file. | PASS |
| AC7: named regression suites green | quality-runner scoped run reported 245 passed, 0 failed across the named legacy suites plus the task-specific migration suite. | PASS |

### Pass 1 - Critical
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 variant-by-context contract | serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx:189-294 | No. The suite would still pass if tertiary buttons were changed to default buttons because it only asserts p-button presence / raw button absence. | LAX |
| AC2 heading migration | serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx:310-343 | Yes | COVERED |
| AC3 text migration | serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx:373-448 | Yes | COVERED |
| AC4 structural form migration and hideLabel | serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx:469-597 | Yes for structural migration; behavior proof is thinner in legacy DetailTab payload checks. | COVERED |
| AC7 regression suites green | quality-runner scoped run | Yes | COVERED |

#### Security Review
- No issues found. The reviewed files remain local UI/rendering code with sanitized ReactMarkdown usage in serve/cockpit/web/src/components/DetailTab.tsx:179 and serve/cockpit/web/src/components/ResolveModal.tsx:67.

#### Test Integrity
- No weakened or removed assertions found in the current file state.
- Small confidence deduction remains because I could confirm the builder commit exists in .git/logs (8d48fb79e0322d7a193ce6ae8c10446d9f55ea81) but I do not have a diff-backed immutability audit for every TestFromAC assertion.

#### Test Quality
- FAIL. Assertion specificity is WEAK for AC1 because the suite does not prove the explicit phrase appropriate variant per context. The implementation clearly distinguishes tertiary vs default buttons, but the tests do not assert those values.
- Additional proof-thinness: serve/cockpit/web/src/components/DetailTab.tsx:59, 122-133 serializes title and priority through readControlValue, while serve/cockpit/web/src/__tests__/DetailTab.test.tsx:123-135, 262, 530 only proves presence plus updated/body payload keys.

#### Data Safety
- No issues found.

#### Builder Process Quality
- FRICTION, not loop. Multiple builder/test-writer retries are present, but the approaches changed and there is no identical-approach repetition or tier-3 loop behavior.

### Required Follow-up
- Strengthen serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx so AC1 asserts the expected button variants per context instead of only asserting p-button presence.
- Recommended while the task is back with test-writer: add one DetailTab regression that mutates the migrated title and priority controls through the PDS event path and proves the edited values enter the POST payload.

### Deductions
- -0.08: AC1 variant contract is not discriminated by the TestFromAC suite.
- -0.02: no diff-backed TestFromAC immutability audit; commit existence only confirmed through .git/logs.
- -0.01: DetailTab title/priority payload proof is thinner than the migrated control wiring warrants.

### Verdict
- Confidence: 0.85
- FAIL -> todo
- Reason: implementation is green, diagnostics are clean, and the migration is present, but the review gate cannot pass because AC1's explicit variant-by-context contract is not actually proven by the current tests.

### Reflection
- Green frontend migrations can still be false greens when the suite asserts custom-element presence but not the contract encoded in attributes.
- For TSX reviews, VS Code diagnostics plus targeted Vitest runs are the meaningful gate; quality-runner lint is only context, not proof.
- When diff access is unavailable, .git/logs is enough to confirm commit presence but not enough for a full immutability audit.
[[2026-05-02]]
## Test-Writer Notes
- Retry (AC1 variant + AC4 payload proof): added 17 new tests — 14 variant assertions, 3 payload regression tests.
- Test file: serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx
- Classes modified: TestFromAC_PdsMigration_Buttons (17 new tests in 7 new describe blocks); new class TestFromAC_PdsMigration_DetailTabPayload (3 tests).
- Total after retry: 71 tests, all PASS against current implementation.
- Lint: ESLint clean (0 errors, 0 warnings on the test file).
- Commit: b27d046b — test: strengthen AC1 variant assertions and add DetailTab payload proof (#1230, test-writer)

### Gaps addressed
- AC1 variant gap: Added `.variant` DOM property assertions (NOT `getAttribute('variant')` — PDS v4 stores variant as a non-reflected DOM property) for cancel/toggle/filter/nav buttons (`tertiary`) and action buttons (`primary`) across all 6 in-scope components.
- AC4 payload gap: Added 3 tests in TestFromAC_PdsMigration_DetailTabPayload proving that title changes, priority changes, and both changes together via PDS CustomEvents (`detail.value` path) correctly enter the POST body on save.

### Step 1b.1 — Direct-to-Review Advance
- All reviewer gaps were test-proof gaps only; no implementation fixes were needed.
- All 17 new tests PASS against the current implementation (builder's implementation is already correct).
- Builder skip: test-only retry, all tests green.

### Key discovery
- PDS v4 `variant` prop is a DOM property on `p-button` elements (not a reflected HTML attribute). `getAttribute('variant')` always returns `null`. Access via `(el as HTMLElement & { variant: string }).variant`. This pattern is required for any future PDS v4 variant assertions in jsdom tests.
[[2026-05-02]]
## Builder Notes
- No code changes were made in this pass.
- Attempted mandatory GREEN verification via `quality-runner` (scoped task suite + AC7 suites + scoped lint).
- quality-runner reported execution failure: vitest/eslint hangs when invoked with file arguments in its environment, so no reliable pass/fail evidence could be produced.
- Per `r-pipeline-protocol` Tool Availability rule, builder cannot substitute direct local pytest/ruff/npm invocations when quality-runner is unavailable/failing.
- Releasing claim with failure so task can be retried once quality-runner execution is restored.

### quality-runner reported
- `npx vitest run` with file arguments: hang, exit 130 (SIGINT)
- `npx eslint` with file arguments: hang, exit 130 (SIGINT)
- `npx vitest run` without args: works (sanity check)
- Coverage: not collected
[[2026-05-02]]
## Builder Notes
- Implementation: no code changes in this pass (test-only verification cycle).
- Tests (quality-runner scoped): 262 passed, 0 failed, 0 skipped.
- Suites verified: `PdsMigration_1230`, `DetailTab`, `ArchivalModal_1241`, `ArchivalModal_1245`, `ResolveModal_1193`, `ResolveModal_plugins_1194`, `Shell`, `HealthBadge`, `DRStatusIndicator_1191`, `ActivityTab`.
- Lint: ruff reports TSX parse errors (tool/filetype mismatch); no Python files were in scope.
- Coverage: not collected by quality-runner for TSX in this run; acceptance gate satisfied by scoped green suites.
- Evidence summary: all AC7 named regression suites and task-specific migration suite are green in current workspace state.

### Post-task Reflection
- Problems faced: prior cycle was blocked on quality-runner file-arg instability and stale retry context.
- Workaround applied: reran a single scoped quality-runner pass using the full AC7 suite list plus task suite for deterministic evidence.
- Pattern discovered: frontend tasks need explicit handling of ruff/TSX mismatch to avoid false-negative gating.
- Quality gap: coverage evidence for TSX remains tool-limited in quality-runner; suite pass remains the reliable gate here.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run: 262 passed, 0 failed, 0 skipped.
- Suites executed: `PdsMigration_1230.test.tsx`, `DetailTab.test.tsx`, `ArchivalModal_1241.test.tsx`, `ArchivalModal_1245.test.tsx`, `ResolveModal_1193.test.tsx`, `ResolveModal_plugins_1194.test.tsx`, `Shell.test.tsx`, `HealthBadge.test.tsx`, `DRStatusIndicator_1191.test.tsx`, `ActivityTab.test.tsx`.

### Diagnostics
- VS Code diagnostics: no errors in the in-scope TSX source/test files.
- Lint: quality-runner lint is not meaningful for TSX here. Ruff produced only Python-parser `invalid-syntax` noise against `.tsx`, so it is not usable review evidence for this task.

### Coverage
- ConfirmDialog.tsx: 73.33%
- ArchivalModal.tsx: 90.29%
- ActivityTab.tsx: 89.06%
- DetailTab.tsx: 94.61%
- ResolveModal.tsx: 93.26%
- HealthBadge.tsx: 92.00%
- DRStatusIndicator.tsx: 92.59%
- Shell.tsx: 75.00%
- Scoped overall statements: 63.45%
- Coverage is informational here; the gate is proof quality on the migrated branches.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: `<button>` -> `<PButton>` with appropriate variant per context in ConfirmDialog, ArchivalModal, ActivityTab, DetailTab, ResolveModal, Shell | Live source uses the expected variants in `ConfirmDialog.tsx:14-15`, `ArchivalModal.tsx:270-279`, `ActivityTab.tsx:50-62`, `DetailTab.tsx:110,181,189,192,196,207-214`, `ResolveModal.tsx:128-136`, `Shell.tsx:126-129`. The strengthened task suite now proves many variants in `PdsMigration_1230.test.tsx:299-396`, but it still omits ActivityTab `filter-stuck` / `filter-released` and DetailTab `unclaim-action` / `unblock-action` / `conflict-refresh` / `conflict-overwrite`. A wrong variant on those uncovered buttons would stay green. | FAIL |
| AC2: `<h3>` -> `<PHeading tag="h3">` in ArchivalModal and ResolveModal | Source uses `PHeading` in `ArchivalModal.tsx:222` and `ResolveModal.tsx:82`. Task tests assert `p-heading`, `tag="h3"`, and no raw `h3` in `PdsMigration_1230.test.tsx:410-447`. | PASS |
| AC3: standalone `<p>` -> `<PText>` in ArchivalModal, DRStatusIndicator popover, HealthBadge popover | Source uses `PText` in `ArchivalModal.tsx:266,283`, `DRStatusIndicator.tsx:39`, and `HealthBadge.tsx:41`. Task tests assert `p-text` presence and raw `p` absence in `PdsMigration_1230.test.tsx:467-555`. | PASS |
| AC4: form controls migrated to `PInputText` / `PSelect` / `PTextarea`; `hideLabel` where no visible label exists | Source is migrated in `DetailTab.tsx:120-176`, `ArchivalModal.tsx:226-262`, and `ResolveModal.tsx:119-125`. The task and legacy suites now prove title/priority/body payload flow and ArchivalModal interaction, but proof is still incomplete: `DetailTab.tsx:147-163` migrated `depends_on`, `parent`, and `block_reason` to hidden-label `PInputText`, while tests only assert generic field presence for `depends_on` / `parent` in `DetailTab.test.tsx:144-151` and `PInputText` presence for `block_reason` in `PdsMigration_1230.test.tsx:705-708`; no test discriminates `PInputText` plus `hide-label` for all three. `ResolveModal.tsx:63-72,124-125` supports the PDS `detail.value` path, but `ResolveModal_1193.test.tsx:132,138` still drives only `target.value`. A regression limited to those unproved branches would stay green. | FAIL |
| AC5: Card.tsx and Column.tsx unchanged structurally | Source remains native/unchanged in `Card.tsx:20-56` and `Column.tsx:34-71`; no PDS migration was introduced there. | PASS |
| AC6: KanbanBoard context menu not migrated in this task | Source still uses the old coordinate-positioned raw menu in `KanbanBoard.tsx:223-234`. | PASS |
| AC7: named regression suites green | quality-runner independently executed the named suites and reported 262 passed, 0 failed, 0 skipped. | PASS |

### Pass 1 - Critical
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 variant-by-context contract | `PdsMigration_1230.test.tsx:299-396` | No. Several migrated buttons in ActivityTab and DetailTab have no variant assertion, so a wrong variant on those paths would still pass. | LAX |
| AC2 heading migration | `PdsMigration_1230.test.tsx:410-447` | Yes. | COVERED |
| AC3 text migration | `PdsMigration_1230.test.tsx:467-555` | Yes. | COVERED |
| AC4 form migration + hideLabel + PDS event path | `PdsMigration_1230.test.tsx:565-781`, `DetailTab.test.tsx:505-528`, `ArchivalModal_1241.test.tsx:95-99,525-565`, `ResolveModal_1193.test.tsx:114-154` | Partially. Title/priority/body and ArchivalModal branches are proved, but `depends_on` / `parent` / `block_reason` hide-label coverage and ResolveModal `detail.value` are still unproved. | LAX |
| AC7 named suites green | quality-runner scoped run | Yes. | COVERED |

#### Security Review
- No issues found. The UI changes do not add new injection, secret, path, or deserialization risk.
- Markdown rendering remains sanitized in `DetailTab.tsx:179` and `ResolveModal.tsx:83`, and plugin wiring is covered by `ResolveModal_plugins_1194.test.tsx:75-102`.

#### Test Integrity
- No weakened or removed assertions were visible in the current TestFromAC file state.
- Small confidence deduction remains because commit presence was confirmed via `.git/logs` for `8d48fb79e0322d7a193ce6ae8c10446d9f55ea81`, `b27d046b`, `8142e272`, and `eb54c8dc`, but I did not have a diff-backed immutability audit of every TestFromAC assertion.

#### Test Quality
- FAIL. The remaining weakness is branch completeness on AC-traceable branches, not assertion style.
- AC1 is still sampled rather than exhaustive: the task suite proves many button variants but not all migrated buttons in the scoped components.
- AC4 is still sampled rather than exhaustive: the task suite does not yet discriminate `PInputText` + `hide-label` for every unlabeled DetailTab text control, and it does not prove the PDS `detail.value` path for ResolveModal notes.

#### Data Safety
- No issues found.

#### Builder Process Quality
- FRICTION, not LOOP, in the implementation retries themselves. The implementation changed course across retries and the current code is green.
- However this is the second review failure recorded on the task, so the reviewer loop-breaker applies on routing.

### Required Follow-up
- Strengthen AC1 proof so all migrated ActivityTab and DetailTab buttons have discriminating variant assertions, including `filter-stuck`, `filter-released`, `unclaim-action`, `unblock-action`, `conflict-refresh`, and `conflict-overwrite`.
- Strengthen AC4 proof so `depends_on`, `parent`, and `block_reason` are each proved as `PInputText` with `hide-label` where applicable.
- Add a ResolveModal notes test that drives `p-textarea` through `CustomEvent.detail.value` and proves the submitted payload uses the updated notes.

### Deductions
- -0.08: AC1 proof still misses migrated button branches that are part of the component-level contract.
- -0.06: AC4 proof still misses migrated control/hideLabel branches and the ResolveModal PDS event path.
- -0.01: TestFromAC immutability audit is lower-confidence without a direct diff.

### Verdict
- Confidence: 0.84
- FAIL -> backlog
- Reason: the implementation is green and current source matches the migration intent, but the review gate still cannot pass because AC1 and AC4 are not fully discriminated by the tests. This is the second review failure on the task, so routing escalates to backlog per the loop-breaker rule.

### Reflection
- Green frontend suites are not enough when a component-level migration AC leaves unasserted buttons or controls inside the same scope.
- For TSX reviews, Vitest plus editor diagnostics are the meaningful checks; ruff-on-TSX output is noise.
- Comparing live component branches against the exact TestFromAC assertions is what surfaces false-green gaps on UI migration tasks.
[[2026-05-02]]
## Architecture Review (Re-review)

### Context
Task returned to backlog via loop-breaker after 2nd review failure (confidence 0.84). Implementation is green (262 pass, 0 fail). All failures are test-proof gaps, not implementation defects.

### AC Refinement
- **AC1 elevated to td:2** — "appropriate variant per context" requires per-button variant assertions, not just presence checks. The reviewer correctly identified this as a contract that td:1 cannot prove.
- **AC4 unchanged at td:2** — hideLabel map and PDS event path requirements added below.

### AC1 Variant Map (exhaustive — test-writer must assert each row)
| Component | Selector | Expected Variant |
|---|---|---|
| ConfirmDialog | 1st p-button (Cancel) | tertiary |
| ConfirmDialog | 2nd p-button (Confirm) | primary |
| ArchivalModal | [data-testid="archival-submit"] | primary |
| ArchivalModal | cancel p-button (no testid) | tertiary |
| ActivityTab | [data-testid="filter-active"] | tertiary |
| ActivityTab | [data-testid="filter-all"] | tertiary |
| ActivityTab | [data-testid="filter-blocked"] | tertiary |
| ActivityTab | [data-testid="filter-stuck"] | tertiary |
| ActivityTab | [data-testid="filter-released"] | tertiary |
| DetailTab | [data-testid="history-tab"] | tertiary |
| DetailTab | [data-testid="body-edit-toggle"] | tertiary |
| DetailTab | [data-testid="save-button"] | primary |
| DetailTab | [data-testid="move-backward"] | tertiary |
| DetailTab | [data-testid="unclaim-action"] | tertiary |
| DetailTab | [data-testid="unblock-action"] | tertiary |
| DetailTab | [data-testid="conflict-refresh"] | tertiary |
| DetailTab | [data-testid="conflict-overwrite"] | primary |
| ResolveModal | [data-testid="resolve-submit"] | primary |
| ResolveModal | [data-testid="resolve-cancel"] | tertiary |
| Shell | [data-surface="kanban"] | tertiary |

Note: PDS v4 `variant` is a DOM property (not reflected attribute). Access via `(el as HTMLElement & { variant: string }).variant`. `primary` means no explicit `variant` prop set (PDS default).

### AC4 HideLabel Map (exhaustive — test-writer must assert each row)
| Component | Selector | hide-label | Reason |
|---|---|---|---|
| DetailTab | p-input-text[data-field="title"] | true | No visible label |
| DetailTab | p-select[data-field="priority"] | true | No visible label |
| DetailTab | p-input-text[data-field="depends_on"] | true | No visible label |
| DetailTab | p-input-text[data-field="parent"] | true | No visible label |
| DetailTab | p-input-text[data-field="block_reason"] | true | Conditional; no visible label when shown |
| DetailTab | p-textarea[data-field="body"] | true | No visible label |
| ResolveModal | p-textarea[data-testid="resolve-notes"] | true | No visible label |
| ArchivalModal | p-select (reason) | false | Has visible label wrapper |
| ArchivalModal | p-input-text (refs) | false | Has visible label wrapper |

### AC4 PDS Event Path (test-writer must add)
ResolveModal notes textarea must be driven through `CustomEvent('change', { detail: { value: ... } })` on `p-textarea[data-testid="resolve-notes"]`, and the submitted payload must prove the updated notes content. This closes the `readControlValue(event.detail?.value)` proof gap.

### Remaining Gaps (from reviewer's 2nd review)
Already tested (no action needed): ConfirmDialog variants, ArchivalModal variants, DetailTab save/history/edit/backward variants, ResolveModal variants, Shell variant, title/priority/body hideLabel, resolve-notes hideLabel, ArchivalModal boundary (no hideLabel), DetailTab title+priority payload.

Missing (test-writer must add):
1. AC1: ActivityTab filter-stuck, filter-released variant assertions
2. AC1: DetailTab unclaim-action, unblock-action, conflict-refresh, conflict-overwrite variant assertions
3. AC4: DetailTab depends_on, parent, block_reason hideLabel assertions
4. AC4: ResolveModal notes PDS detail.value payload test

### Evaluation (unchanged from original review)
All 10 architecture criteria PASS — no structural changes since original approval. Design is direct element-to-PDS replacement with no new abstractions.

### Challenge Results
- Challenger: reconsider (0.44) — correctly noted that approval must not precede AC refinement
- Architect response: accepted. This re-review section lands the AC refinement BEFORE advancing. The variant map and hideLabel map are now in the task body as exhaustive references.

### Test Depth
- Max depth: td:2 (AC1 elevated from td:1, AC4 already td:2)
- Test-writer: PROCEED

### Verdict: APPROVE (re-approval with AC refinement)
### Action Taken: Elevated AC1 to td:2, added exhaustive variant map (20 rows) and hideLabel map (9 rows), added PDS event path requirement. Advancing to todo.
[[2026-05-02]]
Re-review after loop-breaker. AC refined with exhaustive variant map (20 buttons) and hideLabel map (9 controls), AC1 elevated to td:2, ResolveModal PDS event path requirement added. Challenger accepted (0.44 → reconsider): refinement landed before advancing. 4 specific test gaps enumerated for test-writer.
[[2026-05-02]]
## Test-Writer Notes
- Retry: added 10 tests for all 4 reviewer gaps. All pass against current impl.
- Builder skip: test-only retry, all tests green (81 passed, 0 failed).
- Commit: 31d7583d — test: fill reviewer gaps for AC1 variants and AC4 hideLabel/payload (#1230, test-writer)

### Gaps addressed (from reviewer Required Follow-up)

**AC1 — ActivityTab missing variants (2 tests):**
- `filter-stuck has variant="tertiary"`
- `filter-released has variant="tertiary"`

**AC1 — DetailTab missing variants (4 tests):**
- `unclaim-action has variant="tertiary"`
- `unblock-action has variant="tertiary" when task is blocked` (uses TASK_BLOCKED fixture)
- `conflict-refresh has variant="tertiary"` (triggers conflict modal via 409 fetch mock)
- `conflict-overwrite has variant="primary"` (triggers conflict modal via 409 fetch mock)

**AC4 — DetailTab hideLabel coverage (3 tests):**
- `p-input-text for depends_on has hide-label attribute`
- `p-input-text for parent has hide-label attribute`
- `p-input-text for block_reason has hide-label attribute when task is blocked`

**AC4 — ResolveModal notes payload proof (1 test):**
- `notes changed via CustomEvent detail.value appears in POST body on submit` — drives `p-textarea[data-testid="resolve-notes"]` with `CustomEvent('change', { detail: { value: ... } })` and asserts `payload.notes` in the POST body.

### Key pattern
- Conflict modal tests: call `renderDetailTab()` first (sets hanging-promise stub), then override `fetch` with 409 mock, click save, await microtask tick — matches existing payload test pattern.
- `conflict-overwrite` has no explicit variant prop; `.variant` property returns `'primary'` (PDS v4 default), confirmed by existing save-button test which uses the same pattern.
[[2026-05-02]]
## Builder Notes
- No source edits in this pass.
- Mandatory GREEN verification attempted via `quality-runner` on task suite + AC7 suites.
- quality-runner execution environment failed before meaningful assertions:
  - `ArchivalModal_1241.test.tsx` and `DetailTab.test.tsx` failed in `beforeAll` with `ReferenceError: HTMLElement is not defined`.
  - Remaining suites failed at render setup with `ReferenceError: document is not defined`.
- Result summary from quality-runner: 2 passed, 190 failed, 80 skipped; failures attributed to environment setup, not implementation-level assertions.
- Lint report returned clean; coverage unmeasurable because test runtime initialization failed.
- Per `r-pipeline-protocol` Tool Availability rule, builder cannot substitute direct local vitest/eslint commands for gate evidence when quality-runner execution is unavailable.
- Releasing claim with failure so task can be retried when quality-runner frontend jsdom execution is restored.
[[2026-05-02]]
## Infrastructure Fix — Quality-Runner Frontend Support
- quality-runner now has documented frontend protocol (`h-vitest-and-linting` skill).
- Agent updated with `h-vitest-and-linting` in `<required_reading>` and `<critical_rules>`.
- `h-quality-runner` updated with frontend detection (when `test_paths` contain `serve/cockpit/web/`).
- `r-pipeline-protocol` updated with environment fallback clause (retry with hint, then direct execution).
- Root cause: quality-runner ran vitest from repo root instead of `serve/cockpit/web/`, missing jsdom config.
- Next builder pickup should succeed with quality-runner frontend mode.
[[2026-05-02]]
## Builder Notes
- Implementation: no source changes in this pass (verification-only pickup after test-writer retry).
- Tests (quality-runner scoped): 272 passed, 0 failed, 0 skipped.
- Suites verified: `PdsMigration_1230`, `DetailTab`, `ArchivalModal_1241`, `ArchivalModal_1245`, `ResolveModal_1193`, `ResolveModal_plugins_1194`, `Shell`, `HealthBadge`, `DRStatusIndicator_1191`, `ActivityTab`.
- Lint: ESLint clean (0 violations) for in-scope migrated sources and task test file.
- Coverage: not collected by scoped frontend quality-runner run.
- Evidence summary: all AC7 named suites plus task-specific migration suite are green in current workspace state.

### Post-task Reflection
- Problems faced: task history had multiple stale failure states from prior quality-runner environment issues, so this pass required a fresh deterministic scoped run.
- Workaround applied: provided explicit frontend hint (`cd serve/cockpit/web`) in the quality-runner request to ensure jsdom-configured execution.
- Pattern discovered: for frontend verification-only retries, a single canonical scoped suite list avoids contradictory evidence between cycles.
- Quality gap: scoped run does not provide coverage; acceptance was gated by green suites + clean lint evidence.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run: 272 passed, 0 failed, 0 skipped.
- Suites executed: `PdsMigration_1230.test.tsx`, `DetailTab.test.tsx`, `ArchivalModal_1241.test.tsx`, `ArchivalModal_1245.test.tsx`, `ResolveModal_1193.test.tsx`, `ResolveModal_plugins_1194.test.tsx`, `Shell.test.tsx`, `HealthBadge.test.tsx`, `DRStatusIndicator_1191.test.tsx`, `ActivityTab.test.tsx`.

### Diagnostics
- VS Code diagnostics: no errors in the 18 in-scope TSX source/test files.
- Lint: quality-runner frontend lint clean (0 violations).

### Coverage
- quality-runner frontend coverage (broad buckets): overall 62.6%; `src/components` 69.63%; `src/hooks` 57.3%; `src` 54.54%; `src/utils/styles.ts` 100%; `src/api` 0%.
- Informational only: this frontend report is package-level, not diff-scoped per-file coverage. The migrated branches are directly exercised by the passing task suite and AC7 regression suites, so aggregate bucket percentages are not the gate here.

### Subagent Divergence
- code-reader reported stale AC4 gaps and treated AC5/AC6 as missing. Direct inspection of the latest task state supersedes those points:
  - `PdsMigration_1230.test.tsx` now includes ResolveModal `detail.value` payload proof at lines 777-790 and DetailTab title/priority payload proof at lines 810-868.
  - AC5 and AC6 are td:0/source-inspection lines, not missing test obligations.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: `<button>` -> `<PButton>` with appropriate variant per context | `PdsMigration_1230.test.tsx`: 301, 315, 332, 364, 422, 436 | Yes. All refined variant-map entries are asserted. ArchivalModal cancel is indirectly but completely proved because `ArchivalModal.tsx` renders exactly two `PButton`s (`archival-submit` at 271 and cancel at 279), and the suite asserts submit=`primary` plus existence of the single remaining `tertiary` button. | COVERED |
| AC2: `<h3>` -> `<PHeading tag="h3">` | `PdsMigration_1230.test.tsx`: 459, 470, 478, 494 | Yes | COVERED |
| AC3: standalone `<p>` -> `<PText>` | `PdsMigration_1230.test.tsx`: 511, 549, 569, 586 | Yes | COVERED |
| AC4: `PInputText` / `PSelect` / `PTextarea`, `hideLabel`, and PDS `detail.value` paths | `PdsMigration_1230.test.tsx`: 615, 627, 646, 658, 688, 702, 708, 714, 722, 728, 734, 740, 777, 810, 830, 849 | Yes | COVERED |
| AC5: Card.tsx / Column.tsx unchanged | td:0 | N/A - architect marked td:0; verified by source inspection | SKIP |
| AC6: KanbanBoard context menu not migrated | td:0 | N/A - architect marked td:0; verified by source inspection | SKIP |
| AC7: named regression suites green | quality-runner scoped run | Yes | COVERED |

#### Security Review
- No issues found. Markdown rendering remains sanitized in `DetailTab.tsx:179` and `ResolveModal.tsx:83`. No new secrets, injection sinks, path traversal, or unsafe deserialization were introduced in scope.

#### Test Integrity
- No weakened or removed assertions are visible in the current `TestFromAC_*` or named regression suites.
- Low-confidence caveat only: immutability is not diff-backed in this review. Commit presence was confirmed in `.git/logs` for builder commit `8d48fb79e0322d7a193ce6ae8c10446d9f55ea81` and test-writer commit `31d7583dfe7fc35ce83aae45bdfa5f405d5e9ffb`.

#### Test Quality
- Assertion specificity: STRONG. Exact variant/property assertions cover the refined AC1 map, and payload tests assert exact POST bodies for ResolveModal notes and DetailTab title/priority.
- Negative/error-path coverage: ADEQUATE. ArchivalModal error rendering is exercised at `PdsMigration_1230.test.tsx:511`, and the named AC7 suites cover surrounding regressions.
- Manual mutation reasoning: STRONG for the task contract. Flipping variants, removing `hideLabel`, or bypassing `detail.value` would break explicit assertions.
- Test independence: STRONG.
- Naming: STRONG.
- No WEAK dimensions.

#### Data Safety
- No issues found.

#### Builder Process Quality
- FRICTION, not LOOP. Earlier failures varied approach and were followed by an architecture re-review; the current pass has fresh green evidence and no repeated same-approach retry pattern.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `<button>` -> `<PButton>` with appropriate variant per context | Source: `ConfirmDialog.tsx:14-15`, `ArchivalModal.tsx:271-280`, `ActivityTab.tsx:50-62`, `DetailTab.tsx:110,181,186,189,192,196,208,214`, `ResolveModal.tsx:129,136`, `Shell.tsx:126`. Tests: `PdsMigration_1230.test.tsx`: 301, 315, 332, 364, 422, 436. | PASS |
| AC2: `<h3>` -> `<PHeading tag="h3">` in ArchivalModal and ResolveModal | Source: `ArchivalModal.tsx:222`, `ResolveModal.tsx:82`. Tests: `PdsMigration_1230.test.tsx`: 459, 470, 478, 494. | PASS |
| AC3: standalone `<p>` -> `<PText>` in ArchivalModal, DRStatusIndicator popover, HealthBadge popover | Source: `ArchivalModal.tsx:266,283`, `DRStatusIndicator.tsx:39`, `HealthBadge.tsx:41`. Tests: `PdsMigration_1230.test.tsx`: 511, 549, 569, 586. | PASS |
| AC4: form controls migrated to `PInputText` / `PSelect` / `PTextarea`; `hideLabel` where unlabeled; PDS `detail.value` path proved where relevant | Source: `ArchivalModal.tsx:226,254`, `DetailTab.tsx:59,71,90,121-176`, `ResolveModal.tsx:38,63,121-124`. Tests: `PdsMigration_1230.test.tsx`: 615, 627, 646, 658, 688, 702, 708, 714, 722, 728, 734, 740, 777, 810, 830, 849. | PASS |
| AC5: Card.tsx and Column.tsx unchanged structurally | Direct source inspection of `Card.tsx:1-61` and `Column.tsx:1-69` shows the existing raw `div`/`span`/`Card` drag-drop structure remains in place, with no PDS component migration. | PASS |
| AC6: KanbanBoard context menu not migrated in this task | Direct source inspection of `KanbanBoard.tsx:223-234` shows the raw fixed-position `<div data-testid="context-menu">` menu remains; no PDS flyout/popover migration was introduced. | PASS |
| AC7: all named regression suites green | Independent quality-runner scoped run reported 272 passed, 0 failed, 0 skipped across the task suite and all named legacy suites. | PASS |

### Deductions
- -0.02: no diff-backed TestFromAC immutability audit; commit presence only confirmed via `.git/logs`.
- -0.01: frontend coverage output is broad-bucket only, so diff-scoped confidence comes from explicit branch assertions rather than per-file percentages.

### Verdict
- Confidence: 0.94
- PASS -> docs
- Reason: independent frontend execution is green, diagnostics are clean, the refined AC1/AC4 proof gaps have been closed in the task suite, and the td:0 out-of-scope guarantees are satisfied by direct source inspection.

### Reflection
- For frontend reviews, broad coverage buckets are weaker evidence than explicit variant and payload assertions; the task suite is the real gate.
- Subagent findings still need synthesis against the live task state; stale cached concerns can linger after a test-only retry.
- td:0 AC lines should be checked by direct source inspection, not misclassified as missing tests.
[[2026-05-02]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | `serve/cockpit/README.md` has no section referencing PDS components, individual component files, or design system migration details. |
| 2 | Module docstrings | No | N/A | All changed files are `.tsx` TypeScript/React files — OUT of scope for Python docstring checking. |
| 3 | External attribution | No | N/A | Task used the existing PDS package already installed; no new external patterns sourced. |
| 4 | Research doc | No | N/A | No `.owlbear/research/` file referenced or produced for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` has `describes: serve/cockpit/src/**, serve/cockpit/web/src/**` — matches all 8 changed TSX files. Footer updated from `2026-05-02 (cb41d512)` to `2026-05-02 (791c7f37)`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/web/src/components/ConfirmDialog.tsx | OUT | N/A (application source, not docstring) |
| serve/cockpit/web/src/components/ArchivalModal.tsx | OUT | N/A |
| serve/cockpit/web/src/components/ActivityTab.tsx | OUT | N/A |
| serve/cockpit/web/src/components/DetailTab.tsx | OUT | N/A |
| serve/cockpit/web/src/components/ResolveModal.tsx | OUT | N/A |
| serve/cockpit/web/src/components/HealthBadge.tsx | OUT | N/A |
| serve/cockpit/web/src/components/DRStatusIndicator.tsx | OUT | N/A |
| serve/cockpit/web/src/Shell.tsx | OUT | N/A |
| share/diagrams/cockpit.excalidraw | IN | Updated (diagram footer) |

### Files Updated
- share/diagrams/cockpit.excalidraw — footer updated to `Last verified: 2026-05-02 (791c7f37)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found
[[2026-05-02]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: button to PButton with variant | Reviewer verified all 20 variant-map rows (PdsMigration_1230.test.tsx:299-436); spot-checked ConfirmDialog.tsx:14-15 (tertiary/primary) | PASS |
| AC2: h3 to PHeading tag=h3 | Reviewer: PdsMigration_1230.test.tsx:410-447; source ArchivalModal.tsx:222, ResolveModal.tsx:82 | PASS |
| AC3: p to PText | Reviewer: PdsMigration_1230.test.tsx:467-555; source confirmed | PASS |
| AC4: form controls + hideLabel + detail.value | Reviewer: PdsMigration_1230.test.tsx:565-849 including hideLabel and payload proof | PASS |
| AC5: Card/Column unchanged | Source inspection, no PDS imports | PASS |
| AC6: KanbanBoard context menu not migrated | Source inspection, raw menu remains | PASS |
| AC7: named regression suites green | quality-runner 272 pass / 0 fail on named suites; auditor full-suite confirms named suites pass | PASS |

### Test Results
- vitest (full suite): 840 passed, 5 failed, 0 skipped
- Failures: FilterPanel_1250 (component not built, #1250 RED tests), usePollingFetch_1227 x3 (unrelated task), ActivityTab_1156 x1 (cross-task regression from PDS migration on block_reason native query)
- eslint: 4 warnings in files outside task scope (KanbanBoard_933, Shell_1228, usePolling)
- Task-scoped suites (named in AC7): ALL GREEN

### Cross-task Regression Note
ActivityTab_1156.test.tsx:714 ("DetailTab block_reason input shows the block reason text") fails because it queries native `input[data-field="block_reason"].defaultValue` which is now `p-input-text` after PDS migration. This is a test-level regression (functionality is proven correct by PdsMigration_1230 tests). Not in AC7 enumerated suites. Follow-up needed: update ActivityTab_1156 to query PDS element.

### Architect Quality: 4/5
Strong AC with exhaustive variant/hideLabel maps after re-review refinement. Minor gap: AC7 fixed-suite list didn't catch ActivityTab_1156 cross-task regression. Overall well-scoped with proper exemptions and td escalation.

### Commit Integrity
- 8ff4f3fd: test: add failing tests for PDS migration (#1230, test-writer)
- eb54c8dc: test: fix ArchivalModal interaction helpers (#1230, test-writer)
- 8142e272: test: fix AC7 legacy suites (#1230, test-writer)
- 8d48fb79: fix: restore ResolveModal markdown plugins (#1230, builder)
- b27d046b: test: strengthen AC1 variant assertions (#1230, test-writer)
- 31d7583d: test: fill reviewer gaps for AC1 variants and AC4 (#1230, test-writer)
- 4b2d2a57: feat(tests) [UNTAGGED] contains the main PDS migration implementation bundled with integration tests. Process violation: no #1230 tag, misleading commit type.

### Deduction Breakdown
- -0.02: cross-task regression in ActivityTab_1156 (test-level, not functional; not in AC7 named suites)
- -0.02: main implementation commit untagged and bundled with unrelated work (process)

### Confidence: 0.96
### Action: archive