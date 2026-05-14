---
id: 1549
title: 'P3-08: impl — sidecar collapse toggle'
status: in-progress
priority: important
created: 2026-05-13T18:43:23.907745+00:00
updated: 2026-05-14T03:36:37.065836+00:00
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
archival_reason:
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