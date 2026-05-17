---
id: 1628
title: 'P3-10: Accessibility sweep'
status: in-progress
priority: important
created: 2026-05-16T03:37:44.860840+00:00
updated: 2026-05-16T18:21:38.304521+00:00
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
archival_reason:
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
