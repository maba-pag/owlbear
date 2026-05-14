---
id: 1549
title: 'P3-08: impl — sidecar collapse toggle'
status: archived
priority: important
created: 2026-05-13T18:43:23.907745+00:00
updated: 2026-05-14T04:25:21.203817+00:00
tags:
  - phase-3
  - scope:cockpit
  - css
  - frontend
parent: 1534
depends_on:
  - 1541
  - 1543
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** CSS transition for sidecar collapse/expand animation, `data-sidecar-collapsed` attribute bridge from React state to CSS, sidecar content overflow handling during transition
- **Out:** Toggle button semantics (delivered by #1541), React state management (delivered by #1541), default-open state (delivered by #1541), sidecar content styling (DetailTab/ActivityTab done separately), responsive breakpoints (mobile), toggle button visual styling
- **Prerequisite overlap:** #1541 delivered the toggle button, ARIA semantics (`aria-expanded`, `aria-controls`, `aria-hidden`), and React state; this task adds only the CSS visual collapse behavior

## Acceptance Criteria

- AC-1: Shell.tsx sets `data-sidecar-collapsed` attribute on the `.shell` grid container element when `isSidecarCollapsed` is true; attribute is absent when the sidecar is expanded
- AC-2: Shell.css declares `transition: grid-template-columns 250ms ease` on `.shell`; `.shell[data-sidecar-collapsed]` sets `grid-template-columns` to `56px 1fr 0fr` (desktop) and `56px minmax(0, 1fr) 0fr` (tablet breakpoint 768px–1023px)
- AC-3: Shell.css applies `overflow: hidden` on the sidecar content region (`.shell__sidecar` or equivalent selector) to prevent content spill during the grid column transition

Proof bundle: behavioral

## Builder Guidance
- **#1541 overlap:** Toggle button, React state (`isSidecarCollapsed`), `aria-expanded`, `aria-controls`, and `aria-hidden` are already implemented in Shell.tsx (lines 45, 159-167). Do NOT duplicate or rewrite these — add only the `data-sidecar-collapsed` attribute and CSS changes.
- **Data attribute placement:** Apply `data-sidecar-collapsed={isSidecarCollapsed || undefined}` on the `.shell` container div (the grid parent), not on the sidecar element — `grid-template-columns` is a container property.
- **CSS technique:** Use `0fr` (not `0` or `0px`) for the collapsed column — `grid-template-columns` requires consistent track units for transition interpolation.
- **Tablet breakpoint:** The existing `@media (min-width: 768px) and (max-width: 1023px)` query uses `56px minmax(0, 1fr) 240px`; add a nested `.shell[data-sidecar-collapsed]` selector with `56px minmax(0, 1fr) 0fr`.
- **Mobile:** No changes needed — mobile is already single-column with no sidecar column.
- **overflow: hidden** on `.shell__sidecar` prevents content from being visible during the `0fr` → `360px` transition.
- **Test file from #1541:** `SidecarCollapse_1541.test.tsx` (8 tests, all GREEN) covers ARIA semantics. The test-writer for this task will add CSS source-contract tests for AC-2 and AC-3, plus a behavioral test for AC-1.
- **Files to change:** Shell.tsx (1 attribute addition), Shell.css (transition + collapse selectors + overflow)

## Research
- Research doc: .owlbear/research/1549-sidecar-collapse-toggle-impl.md
- Sources: 7 studied, 4 high-relevance (S1–S3, S5)
- Recommendation: Animate sidecar collapse via `grid-template-columns` transition on `.shell` container. Change from `56px 1fr 360px` → `56px 1fr 0fr` with `transition: grid-template-columns 250ms ease`. State driven by `data-sidecar-collapsed` attribute on `.shell` div. Toggle button styled as inline SVG chevron matching nav-rail pattern. Content overflow hidden during transition. 93%+ browser support confirmed. (confidence: 0.88)
- Challenge: FALLBACK — direct application of established CSS Grid animation pattern, low architectural risk
- Tier: T1 — CSS + minor JSX change, no new dependencies, no architecture impact
- No follow-up tasks needed; task #1549 is itself the implementation task
2026-05-14T03:26:22+00:00
## Architecture Review

### Changes from Original
Rewrote all 3 AC lines and scope section. Original ACs overlapped with #1541 (toggle button, state management, default-open) which is archived/complete. Refined to focus exclusively on CSS visual collapse behavior. Added builder guidance for #1541 overlap awareness.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | CSS visual collapse only — ARIA/state split to #1541 |
| Interface clarity | PASS (refined) | AC-1: data attribute bridge; AC-2: transition + collapse selectors with exact values; AC-3: overflow handling |
| Dependency correctness | PASS | #1541 archived (tests + ARIA semantics), #1543 archived (token architecture) |
| Module layering | PASS | Frontend CSS + 1 JSX attribute, no cross-layer |
| TDD compliance | PASS | #1541 tests are GREEN (ARIA); test-writer will add CSS source-contract tests for refined ACs |
| KISS/YAGNI | PASS | Minimal CSS changes (~10 lines CSS + 1 JSX attribute), no abstractions |
| Premise challenge | PASS | Brief deliverable #6 (sidecar collapse toggle); #1541 covers semantics, this covers visuals |
| Pattern consistency | PASS | CSS Grid animation pattern (S1, S3 in research); CSS source-contract tests follow #1543 token architecture pattern |
| Security surface | N/A | Static CSS, no system boundaries |
| Single domain | PASS | Frontend/cockpit CSS only |

### Challenge Results
- Challenger: FALLBACK — subagent returned no response
- Architect response: proceeding with refinement-based approval; task is T1 (CSS + minor JSX), low architectural risk, single established approach from research

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (CSS source-contract + behavioral tests for refined ACs)

### Design Diverge
- Trigger: skipped — single dominant approach (CSS Grid `grid-template-columns` transition with `0fr`), 93%+ browser support, no competing designs

### Verdict: APPROVE (after AC refinement)
### Action Taken: Rewrote ACs to remove #1541 overlap, specified exact CSS selectors/values/breakpoints, added builder guidance for data-attribute placement and CSS technique. Advanced to todo.
2026-05-14T03:36:37+00:00
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/SidecarCollapse_1549.test.tsx`
- Class: `TestFromAC_SidecarCollapse_1549`
- Tests per category: happy (1), round-trip/boundary (1), CSS source-contract (4)
- Total: **6 tests, all FAIL** (quality-runner confirmed, exit code 1, lint clean)

### AC Coverage
| AC | Tests | Failure reason |
|----|-------|---------------|
| AC-1: `data-sidecar-collapsed` on `.shell` when collapsed | 2 | Attribute not set in Shell.tsx |
| AC-2: transition + collapsed `grid-template-columns` (desktop + tablet) | 3 | Rules absent from Shell.css |
| AC-3: `overflow: hidden` on `.shell__sidecar` | 1 | Currently `overflow: auto` in Shell.css |

### Test approach
- AC-1 behavioral: `render(Shell)` + `fireEvent.click(toggle)` + assert `.shell.hasAttribute('data-sidecar-collapsed')`
- AC-2/AC-3 CSS source-contract: `readFileSync(Shell.css)` + regex parsing helpers (pattern from TokenArchitecture_1543 test)
- `extractSelectorBlock` uses negative lookahead `(?![a-zA-Z0-9_\\-\\[])` to prevent `.shell` matching `.shell__sidecar` or `.shell[data-sidecar-collapsed]`

### Commit
`31a4c083` — test: sidecar collapse CSS contract tests (#1549, test-writer)
2026-05-14T03:46:05+00:00
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/Shell.tsx
  - serve/cockpit/web/src/Shell.css

- Implementation summary:
  - Added `data-sidecar-collapsed={isSidecarCollapsed || undefined}` to the `.shell` grid container in `Shell.tsx` (AC-1).
  - Added `transition: grid-template-columns 250ms ease` on `.shell` and collapsed selectors using `0fr` tracks in `Shell.css`:
    - desktop: `.shell[data-sidecar-collapsed] { grid-template-columns: 56px 1fr 0fr; }`
    - tablet media query: `.shell[data-sidecar-collapsed] { grid-template-columns: 56px minmax(0, 1fr) 0fr; }` (AC-2)
  - Updated `.shell__sidecar` to `overflow: hidden` to prevent spill during transition (AC-3).

- Test results (quality-runner):
  - RED verification (pre-impl): `SidecarCollapse_1549.test.tsx` -> 0 passed, 6 failed; lint clean.
  - Module baseline (pre-impl): `Shell.test.tsx` -> 18 passed, 0 failed; lint clean.
  - GREEN verification (post-impl):
    - `SidecarCollapse_1549.test.tsx` + `Shell.test.tsx` -> 24 passed, 0 failed, 0 skipped.
    - Lint: clean (eslint 0), stylelint 0.

- Coverage:
  - Frontend scoped quality-runner report did not emit coverage metrics for this run (not required by AC/proof bundle for frontend contract tests).

- Fixes applied during GREEN:
  - One same-context retry after initial GREEN run showed a single failing tablet source-contract selector extraction.
  - Adjusted tablet selector formatting in `Shell.css` to satisfy the test helper’s exact selector-block extraction pattern; re-verified GREEN.

- Commit:
  - `c4b9227a` — feat: implement sidecar collapse css behavior (#1549, builder)
2026-05-14T04:07:29+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1549 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence review: Builder notes covered changed files, scoped test/lint results, and implementation summary, but the behavioral-bundle coverage section was missing from the task record. Reviewer independently ran scoped quality-runner on `serve/cockpit/web/src/__tests__/SidecarCollapse_1549.test.tsx` and `serve/cockpit/web/src/__tests__/Shell.test.tsx` with lint on `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/Shell.css`, and both test files. Result: 24 passed, 0 failed, 0 skipped; vitest 0, eslint 0, stylelint 0; coverage overall 28.11 with `Shell.tsx` 83.33 and `Shell.css` 0; errors none.
- AC evidence map:

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/Shell.tsx:46` initializes `isSidecarCollapsed` to expanded/open state; `serve/cockpit/web/src/Shell.tsx:96` binds `data-sidecar-collapsed={isSidecarCollapsed || undefined}` on the `.shell` grid container. | `serve/cockpit/web/src/__tests__/SidecarCollapse_1549.test.tsx:125-153` proves attribute appears on collapse and is removed on expand round-trip; adjacent existing proof in `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:54-72` proves default state starts expanded/open. | PASS |
| AC-2 | `serve/cockpit/web/src/Shell.css:8` declares `transition: grid-template-columns 250ms ease`; `serve/cockpit/web/src/Shell.css:16-17` defines desktop collapsed columns `56px 1fr 0fr`; `serve/cockpit/web/src/Shell.css:96-97` defines tablet collapsed columns `56px minmax(0, 1fr) 0fr`. | `serve/cockpit/web/src/__tests__/SidecarCollapse_1549.test.tsx:160-188` performs selector-scoped CSS contract checks for the transition plus desktop/tablet collapsed selectors. | PASS |
| AC-3 | `serve/cockpit/web/src/Shell.css:46-48` applies `overflow: hidden` on `.shell__sidecar`. | `serve/cockpit/web/src/__tests__/SidecarCollapse_1549.test.tsx:193-195` verifies the sidecar selector block contains `overflow: hidden`. | PASS |
- Adversarial cross-check: challenger raised evidence-quality concerns around missing recorded coverage and formatter-sensitive CSS extraction; code-reader confirmed these are non-blocking observations and found no AC-to-code, test-to-AC, proof-sufficiency, or safety failures.

## Observations
- `serve/cockpit/web/src/__tests__/SidecarCollapse_1549.test.tsx:53-67` uses a selector extractor that is somewhat formatting-sensitive for nested CSS selectors. This is adequate for the current source-contract AC, but future whitespace-only reformatting around the tablet selector at `serve/cockpit/web/src/Shell.css:96-97` could create a false-red test.
- `Shell.css` showing 0 in frontend coverage is not a blocking issue for this task because AC-2 and AC-3 are declaration contracts proved by selector-scoped CSS source assertions rather than JS line instrumentation.
- No safety/security concerns found in scope; the change is limited to local UI state and CSS declarations with no input, auth, storage, or external integration surface.
2026-05-14T04:09:06+00:00
## Docs Gate

**Verdict: PASS**

### Convention Mapping
`serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/Shell.css` → `serve/cockpit/README.md`

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| README Verification | N/A — no update needed | README covers package at API/surface level; CSS transitions and `data-sidecar-collapsed` are implementation details not surfaced there. Layer 1: no removed symbols/commands/flags. Layer 2: README fully coherent and accurate post-change. |
| External Attribution | PASS | Sources already recorded at `.owlbear/sources/overview.md` lines 4660–4667 under "Sidecar Collapse Toggle Implementation Research (Task #1549)" with 4 source entries (CSS-Tricks, CanIUse, CodePen, Codidact). |
| Research Doc | PASS | `.owlbear/research/1549-sidecar-collapse-toggle-impl.md` confirmed present; linked from task body. |
| Deletion Detection | N/A — no deletions | Builder modified Shell.tsx and Shell.css only; no files removed; no orphaned references. |

### Scratch Cleanup
No `.owlbear/scratch/1549-*` files found.

### Files Modified
None — no doc updates required.
2026-05-14T04:25:21+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: 4603 passed, 20 failed, 14 skipped, 5 errors (timeouts)\n- All 20 failures are pre-existing in unrelated Python domains: `test_cockpit_view.py` (KanbanTestCleanup, TestFileImportUpdates), `test_server.py` (StatusNamesDictFormBug), `test_engine_accessor_migration.py` (SubmodelAccessPaths), `test_ideation_diagram.py` (bridge element names), `test_cockpit_pds_build_compat.py` (vitest subprocess timeouts)\n- Task #1549 changed only frontend files (Shell.tsx, Shell.css) — no Python code touched. Zero task-induced regressions.\n- Lint: clean (ruff 0)\n- regression verdict: PASS\n\n### Intent Verification\n- scope alignment: PASS (changes confined to Shell.tsx and Shell.css in serve/cockpit/web/src/ — cockpit frontend CSS domain)\n- purpose match: PASS (data-sidecar-collapsed attribute bridge + CSS grid-template-columns transition + overflow hidden — matches stated AC purpose)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 4/5\nACs were specific with exact CSS selectors, values, and breakpoints. Builder guidance explicitly mapped #1541 overlap to prevent duplication. Scope boundaries clearly delineated. Minor gap: challenger FALLBACK rather than substantive, though T1/low-risk justified proceeding. AC refinement (full rewrite of all 3 ACs) documented and effective.\n\n### Commit Integrity\n- upstream commit presence: PASS — `31a4c083` (test-writer: 1 file, 201 insertions) and `c4b9227a` (builder: 2 files, 11+2 lines) both present with proper format (test:/feat:, #1549 ref, agent attribution)\n- kanban commit packaging: pending (post-end_work)\n\n### Deduction Breakdown\nNo deductions applied. All criteria clean.\n\n### Confidence: 1.00\n### Action: archive