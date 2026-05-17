---
id: 1628
title: 'P3-10: Accessibility sweep'
status: archived
priority: important
created: 2026-05-16T03:37:44.860840+00:00
updated: 2026-05-17T10:09:57.399149+02:00
tags:
  - frontend
  - pds
  - phase-3
parent: 1590
depends_on: []
ac:
  - Playwright E2E test runs @axe-core/playwright with 
    .withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']) on board view, sidecar 
    detail view, and all overlay surfaces (ArchivalModal, ResolveModal, 
    ConfirmDialog, FilterPanel, CleanupPanel, RepairPanel, HealthBadge popover, 
    DRStatusIndicator popover) — zero violations
  - Existing accessibility-1395.spec.ts suite continues to pass (no regressions 
    introduced)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1590.

Keyboard navigation, ARIA labels on custom controls, color contrast verification.

Scope: Accessibility sweep only.
Out of scope: Dark mode token audit, focus-visible styling, motion tokens.

[[2026-05-16T18:14:06+02:00]]
## Research
- Research doc: .owlbear/research/accessibility-sweep-1628.md
- Sources: 7 studied, 5 high-relevance (≥0.90)
- Recommendation: T1 autonomous — existing a11y infrastructure is comprehensive (confidence: 0.85)

Key findings:
1. @axe-core/playwright already installed and used in 3 E2E test files
2. accessibility-1395.spec.ts covers 4 views (board, detail, DR, repair) + keyboard/landmark at 4 viewports
3. All 15 components have ARIA attributes; semantic HTML landmarks in Shell
4. PDS v4 components provide built-in WCAG 2.2 AA compliance
5. PdsMigration.test.tsx verifies zero raw form elements remain
6. Gap is configuration only: add .withTags() for WCAG 2.1 AA precision
7. Likely 0–3 violations to fix post-B2 migration
8. Test-writer task #1623 was archived/deprecated into this task

[[2026-05-16T19:09:00+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Accessibility verification sweep only |
| Interface clarity | PASS (after refinement) | AC now names explicit surfaces and axe tag scope |
| Dependency correctness | PASS | #1623 archived/deprecated into this task; depends_on is empty; B2 tasks are upstream via parent planning graph |
| Module layering | PASS | E2E test only — no production module imports |
| TDD compliance | PASS | proof_bundle=behavioral → test-writer writes RED phase for this task |
| KISS/YAGNI | PASS | Minimal scope — run axe scan, fix violations |
| Premise challenge | PASS | Accessibility verification is a stated redesign constraint (Brief constraint #8) |
| Pattern consistency | PASS | Uses existing @axe-core/playwright pattern from accessibility-1395.spec.ts |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Frontend E2E only |

### AC Refinement
- Collapsed redundant AC2 (accessible names) and AC3 (color contrast) into AC1 — both are WCAG 2.1 AA sub-rules verified by the same axe scan; separate lines were not independently verifiable
- Added explicit surface list to AC1 per challenger finding (scope gap)
- Added .withTags() specification per research recommendation
- Added regression gate AC2 (existing suite passes)

### Challenge Results
- Challenger: reconsider (0.64)
- Findings: AC scope ambiguity (valid → fixed), AC2/AC3 redundancy (valid → collapsed), RED lineage concern (rebutted), coverage gap (valid → fixed)
- Architect response: accepted scope/redundancy findings, refined AC accordingly; rebutted RED lineage — behavioral proof_bundle ensures test-writer processes this task normally regardless of #1623 deprecation

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED

### Builder Guidance
- Use .withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']) for WCAG 2.1 AA precision
- Key violation categories to watch: button-name, label, link-name (accessible names); color-contrast (SC 1.4.3)
- Research estimates 0–3 violations post-B2 migration; PDS components provide built-in compliance
- Overlay surfaces include all modal/popover components listed in AC1
- Existing accessibility-1395.spec.ts uses default (all rules) scope — keep as stricter regression gate; new test uses WCAG-scoped tags

### Design Diverge
- Skipped: single valid approach (axe-core scan with WCAG tags); no competing designs

### Verdict: APPROVE
### Action Taken: Refined AC (collapsed redundant lines, added explicit surface scope and tag configuration), approved to todo

[[2026-05-16T19:15:55+02:00]]
Architecture review complete. Refined AC: collapsed 3 redundant lines into 2 independently verifiable criteria (scoped axe scan + regression gate). Added explicit surface list and .withTags() scope per challenger findings. Proof bundle: behavioral confirmed.

[[2026-05-16T20:21:38+02:00]]
## Test-Writer Notes

**Test file:** `serve/cockpit/web/e2e/accessibility-sweep-1628.spec.ts`

**Class:** `TestFromAC_WcagSweep` — 10 tests, all FAIL ✓

### Tests by category

| Category | Tests |
|----------|-------|
| Happy-path axe scan | board view, sidecar detail view (2) |
| Overlay surfaces | DRStatusIndicator popover, HealthBadge popover, FilterPanel, ResolveModal, ArchivalModal, ConfirmDialog, CleanupPanel confirm dialog, RepairPanel confirm dialog (8) |

### AC coverage

| AC line | Tests | Count |
|---------|-------|-------|
| AC1: board view | board view passes wcag2.1 aa axe scan | 1 |
| AC1: sidecar detail view | sidecar detail view passes wcag2.1 aa axe scan | 1 |
| AC1: DRStatusIndicator popover | dr status indicator popover passes wcag2.1 aa axe scan | 1 |
| AC1: HealthBadge popover | health badge popover passes wcag2.1 aa axe scan | 1 |
| AC1: FilterPanel | filter panel open state passes wcag2.1 aa axe scan | 1 |
| AC1: ResolveModal | resolve modal passes wcag2.1 aa axe scan | 1 |
| AC1: ArchivalModal | archival modal passes wcag2.1 aa axe scan | 1 |
| AC1: ConfirmDialog | confirm dialog passes wcag2.1 aa axe scan | 1 |
| AC1: CleanupPanel | cleanup panel confirm dialog passes wcag2.1 aa axe scan | 1 |
| AC1: RepairPanel | repair panel confirm dialog passes wcag2.1 aa axe scan | 1 |
| AC2: regression gate | no new tests — existing accessibility-1395.spec.ts is proof | 0 |

**Total: 10 tests, 0 passed, 10 FAIL** ✓

### Fail evidence

quality-runner confirmed all 10 tests fail. Representative violations from board view test:
- `[critical — aria-allowed-attr]` aria-expanded not allowed on p-button
- `[serious — aria-prohibited-attr]` aria-label prohibited on p-button without role
- `[critical — button-name]` buttons without discernible text

All violations are WCAG 2.1 AA rule failures caught by `.withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa'])`.

### Builder prerequisite — pre-existing build blocker

`npm run build` fails with `TS2339: Property 'p-accordion' does not exist on type 'JSX.IntrinsicElements'` in `DetailTab.tsx` (lines 198, 223). The `p-accordion` web component is missing from `src/vite-env.d.ts` IntrinsicElements. **The builder must add this declaration before the build works.** E2E tests were verified by running `npx vite build` (bypasses `tsc -b`) + `npm run preview` for RED confirmation.

Fix required in `src/vite-env.d.ts`:
```ts
'p-accordion': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
  heading?: string
  compact?: boolean | string
  open?: boolean | string
}
```

### AC2 note

AC2 (regression gate: existing accessibility-1395.spec.ts continues to pass) cannot have RED tests written for it — regression gates are verified by running the existing suite unchanged. The builder must not break accessibility-1395.spec.ts.

### ESLint

Clean (exit 0). No violations.

[[2026-05-17T06:34:15+02:00]]
## Builder Notes
- Implementation: updated accessibility semantics and heading structure across `serve/cockpit/web/src/KanbanBoard.tsx`, `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/components/FilterPanel.tsx`, `serve/cockpit/web/src/components/RepairPanel.tsx`, `serve/cockpit/web/src/components/DecisionViewport.tsx`, `serve/cockpit/web/src/components/DetailTab.tsx`, and `serve/cockpit/web/src/vite-env.d.ts`.
- Fixes applied:
  - Replaced invalid ARIA usage on PDS host controls in task surfaces (filter toggle and nav control now native buttons; removed unsupported host-level ARIA attributes where required).
  - Fixed RepairPanel confirm interaction semantics by removing click handler from non-interactive wrapper and moving action to the button.
  - Removed `role="button"` misuse from decision item `<article>` cards.
  - Corrected heading semantics for sidecar sections (`Details`/`Actions`) and ensured page-level `<h1>` presence without breaking landmark structure.
  - Added `compact?: boolean | string` to `p-accordion` JSX intrinsic typing to satisfy existing build usage.
- Tests: 22 Playwright tests passed (`accessibility-sweep-1628.spec.ts` + `accessibility-1395.spec.ts`), 0 failed.
- Coverage: N/A (Playwright E2E verification; quality-runner reported no coverage module output for this scope).
- ruff/eslint: lint clean (quality-runner lint status clean).
- Evidence summary: RED verified first (10/10 AC tests failing), then GREEN verification passed with regression gate intact and no lint violations.
- Commit: `66be913c1dd22d51223ab7d1283686a750c15e72` (`feat: complete accessibility sweep surfaces (#1628, builder)`).

[[2026-05-17T08:00:18+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1628 -> docs | AC mapped to code and evidence sufficient.
- Blocking findings: none.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1: Playwright E2E runs `@axe-core/playwright` with `.withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa'])` on board view, sidecar detail view, and all named overlay surfaces with zero violations | Remediations align with the RED failures and scanned surfaces: `serve/cockpit/web/src/KanbanBoard.tsx:281-285` (native filter toggle + `aria-expanded`/`aria-controls`), `serve/cockpit/web/src/Shell.tsx:214,225,265-268,326-327,424-425` (page `h1`, mounted scan/repair controls, native nav button, sidecar `h2` headings), `serve/cockpit/web/src/components/RepairPanel.tsx:71-74,102` (dialog semantics + confirm action on button), `serve/cockpit/web/src/components/DecisionViewport.tsx:54,62-63` (interactive link, non-interactive article), `serve/cockpit/web/src/components/DetailTab.tsx:57-58,167,197,210` (accordion metadata attrs and `h3` section headings), `serve/cockpit/web/src/vite-env.d.ts:39-42` (`p-accordion` intrinsic typing). VS Code diagnostics on touched source/test files were clean. | `serve/cockpit/web/e2e/accessibility-sweep-1628.spec.ts:49` defines the required WCAG 2.1 AA tag set. The suite proves all required surfaces through distinct tests at `:219`, `:233`, `:251`, `:270`, `:289`, `:307`, `:328`, `:355`, `:383`, and `:407`; each scan uses `.withTags(WCAG_TAGS).analyze()` at `:226`, `:244`, `:263`, `:282`, `:300`, `:321`, `:348`, `:376`, `:394`, and `:431` and asserts `violations` equals `[]`. Surface setup assertions prevent false-green scans by requiring the relevant UI state to be visible before analysis. | PASS |
| AC2: Existing `accessibility-1395.spec.ts` suite continues to pass with no regressions | No code-path conflict found in the touched files; editor diagnostics were clean on the touched frontend files and both E2E specs. | The regression gate remains defined in `serve/cockpit/web/e2e/accessibility-1395.spec.ts:157,169,186,210,253,270,295,333,371`. Builder evidence in the task body reports 22 Playwright tests passed across `accessibility-sweep-1628.spec.ts` and `accessibility-1395.spec.ts`, with 0 failures and clean lint. | PASS |
- Challenger cross-check: reviewer challenged the initial PASS on whether AC1's `CleanupPanel`/`RepairPanel` names covered only overlay-confirm states. That concern is not blocking here because the task-local proof packet explicitly scopes those names to the overlay dialogs in `serve/cockpit/web/e2e/accessibility-sweep-1628.spec.ts:16-17` and again in the dedicated surface sections at `serve/cockpit/web/e2e/accessibility-sweep-1628.spec.ts:380-423`.

## Observations
- The frontmatter AC uses component names (`CleanupPanel`, `RepairPanel`) while the executable proof packet consistently means the confirm-dialog overlay states. The ambiguity is resolved for this task by the test-writer spec, but future ACs should name the exact state directly to avoid unnecessary review churn.

[[2026-05-17T08:55:12+02:00]]
## Docs Gate

**Verdict:** PASS

### Checklist

| Item | Status | Evidence |
|------|--------|----------|
| README Verification | FIXED | `serve/cockpit/README.md` was missing the #1628 entry. Added 15-line bullet documenting ARIA fixes, heading semantic corrections, RepairPanel/DecisionViewport changes, `vite-env.d.ts` typing, and test evidence (`e2e/accessibility-sweep-1628.spec.ts` 10 tests + `e2e/accessibility-1395.spec.ts` regression gate). Layer 1: grep confirms #1628 present, no stale references. Layer 2: editorial read — coherent, matches review evidence, style-consistent with adjacent entries. |
| External Attribution | N/A | `.owlbear/sources/overview.md` already has "Accessibility Sweep Research (Task #1628)" with 3 sources (Playwright a11y docs, PDS v4 component accessibility, axe-core rule docs). No update required. |
| Research Doc | N/A | `.owlbear/research/accessibility-sweep-1628.md` exists and is referenced in the task body. No update required. |
| Deletion Detection | N/A | No source files deleted. No orphaned references. |

### Files Updated

- `serve/cockpit/README.md` — added #1628 accessibility sweep bullet in the Frontend Surface accessibility section (commit `34b57b44`)

### Scratch Cleanup

8 scratch files deleted: `1628-accessibility-sweep.log`, `1628-e2e-ac1.log`, `1628-e2e-scoped.log`, `1628-e2e-test.log`, `1628-eslint-output.txt`, `1628-eslint.log`, `1628-playwright-output.txt`, `1628-tsc-errors.txt`

[[2026-05-17T10:09:57+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 4624 passed (pytest+vitest combined scope); vitest full-suite hit OOM (environment, not regression); pytest showed 5 pre-existing failures in unrelated domains (engine rebind, mcp lifecycle, schema roundtrip, dead code sweep, shell sidecar)
- E2E scoped run: 20/22 passed; 2 failures confirmed caused by POST-#1628 commits — `281883df` (#1617) added `role=\"textbox\"` to PInputSearch without `aria-label` (FilterPanel), and a dialog a11y gap from concurrent task changes. Verified by diffing `66be913c..HEAD -- serve/cockpit/web/src/components/FilterPanel.tsx`. Shell sidecar test (`test_cockpit_shell_sidecar_1568`) also pre-existing (confirmed by checking out pre-builder state).
- regression verdict: PASS (no regressions attributable to #1628)

### Intent Verification
- scope alignment: PASS (all 7 changed files in `serve/cockpit/web/src/` — KanbanBoard, Shell, DecisionViewport, DetailTab, FilterPanel, RepairPanel, vite-env.d.ts — all cockpit frontend domain)
- purpose match: PASS (ARIA attribute corrections, heading semantic fixes, RepairPanel interaction semantics, p-accordion typing — directly addresses WCAG 2.1 AA accessibility sweep purpose)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
- AC specificity: AC1 names exact surfaces, WCAG tag configuration, and zero-violation threshold. AC2 is a clear regression gate. Both independently verifiable.
- Edge case coverage: Minor gap — CleanupPanel/RepairPanel naming ambiguity (component names vs overlay-confirm states) noted by reviewer as observation. Resolved within task by test-writer spec but could cause future review churn.
- Design direction: Builder guidance was actionable (specific tag set, violation categories, existing pattern reference).

### Commit Integrity
- upstream commit presence: PASS — builder `66be913c` (7 files), doc-writer `34b57b44` (cockpit README), test-writer `f5746938` (E2E spec). All reachable from HEAD.
- kanban commit packaging: pending (this archival cycle)

### Deduction Breakdown
No deductions applied.
- Regression: PASS (0 task-attributable failures)
- Intent: PASS
- Lint: clean (eslint 0, ruff 0)
- AC quality: 4/5 (no deduction; threshold is ≤3)
- Reviewer evidence: present, detailed PASS with AC mapping and challenger cross-check
- Evidence integrity: no concerns

### Confidence: 1.00
### Action: archive
