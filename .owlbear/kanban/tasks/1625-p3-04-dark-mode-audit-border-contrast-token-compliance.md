---
id: 1625
title: 'P3-04: Dark mode audit — border contrast + token compliance'
status: todo
priority: important
created: 2026-05-16T03:37:44.735785+00:00
updated: 2026-05-16T16:20:10.991381+00:00
tags:
  - frontend
  - pds
  - phase-3
parent: 1590
depends_on:
  - 1614
  - 1615
  - 1616
  - 1617
  - 1618
ac:
  - In dark mode (.scheme-dark active), border-color on shell structural 
    elements (.shell__sidecar, .shell__nav-rail borders), Column, and 
    FilterPanel has >= 1.3:1 contrast ratio against adjacent background — 
    verified via Playwright computed-style assertions
  - No hardcoded color literals (hex, rgb(), hsl(), named colors) in 
    border-color declarations across src/**/*.css — all border colors use var() 
    references to CSS custom properties; `transparent` is exempt (layout 
    technique for state-indicator borders)
  - Computed border-color values differ between light (.scheme-light) and dark 
    (.scheme-dark) schemes on >= 2 structural border elements — confirms 
    intentional per-scheme token switching, not filter inversion
  - Card.css --pds-border-subtle (or post-migration successor) resolves to a 
    defined custom property value in both color schemes — no undefined var() 
    references in border declarations
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Border contrast, surface differentiation, ensure tokens use `light-dark()` correctly.

Scope: Dark mode audit only.
Out of scope: Focus-visible, motion, accessibility sweep.

[[2026-05-16T17:37:41+02:00]]
## Research
- Research doc: .owlbear/research/dark-mode-border-audit.md
- Sources: 7 studied, 5 high-relevance (PDS v4 docs + codebase)
- Recommendation: Token-first audit approach (confidence: 0.85)

### Key Findings
1. Zero hardcoded border-color values in authored CSS — all use `var(--pds-*)` tokens (AC-2 pre-satisfied)
2. Bug: `--pds-border-subtle` used in Card.css but defined nowhere — card chips have invisible borders
3. PDS v4 has no border-color tokens — uses `--p-color-contrast-*` for borders
4. Dark mode `contrast-low` border on surface ≈ 5.3:1 contrast — well above 1.3:1 threshold (AC-1)
5. Surface-to-canvas contrast in dark mode ≈ 1.16:1 — below 1.3:1, borders do the heavy lifting
6. Post token migration (#1603), all tokens will use native `light-dark()` — manual overrides eliminated

### Risk
Undefined `--pds-border-subtle` may not be caught by provenance map (#1597) since it's a missing definition, not an existing one. Flag to #1620 test expectations.

No follow-up tasks needed — existing chain (#1620 → #1625) covers scope.

[[2026-05-16T18:20:10+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Dark mode border audit only — no feature work |
| Interface clarity | PASS | AC names exact selectors, file scopes, and proof methods |
| Dependency correctness | PASS (after fix) | Added [1614-1618] to enforce post-migration ordering; original #1620 dep was dead (archived) |
| Module layering | PASS | CSS-only changes, no import concerns |
| TDD compliance | PASS | Test-writer will write RED tests at `todo`; proof_bundle=behavioral |
| KISS/YAGNI | PASS | Verification + fix pass, no new abstractions |
| Premise challenge | PASS | Research confirms real bugs (undefined --pds-border-subtle) and valid contrast concerns |
| Pattern consistency | PASS | Follows existing token-var pattern, Playwright computed-style pattern from pds-scheme-dark-1555.spec.ts |
| Security surface | PASS | No new system boundaries — CSS only |
| Single domain | PASS | Frontend/CSS domain only |

### Challenge Results
- Challenger: reconsider (confidence 0.34)
- Key findings accepted: (1) `transparent` exemption needed in AC-2, (2) dependency gap with #1603 not enforced — fixed by adding B2 deps, (3) AC vagueness — refined with concrete selectors
- Key findings rebutted: `.scheme-dark` test anchor is valid — always co-set with `[data-theme="dark"]` by theme-bootstrap.js
- Architect response: revised AC and dependencies, then approved

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — single clear approach (token audit + Playwright verification), no competing designs

### AC Refinements Applied
1. AC-1: Named exact structural selectors (.shell__sidecar, .shell__nav-rail, Column, FilterPanel), specified Playwright computed-style proof
2. AC-2: Scoped to src/**/*.css, defined \"hardcoded\" (hex/rgb/hsl/named), added `transparent` exemption
3. AC-3: Replaced vague \"intentional differentiation\" with concrete computed-style difference assertion on >=2 elements
4. AC-4 (new): Addresses undefined --pds-border-subtle bug from research — requires all var() border references to resolve

### Dependency Fix
- Removed dead dep on #1620 (archived/deprecated)
- Added [1614, 1615, 1616, 1617, 1618] — ensures all B2 impl (which transitively depend on #1603 token migration) completes before this task

### Verdict: APPROVE
### Action Taken: Refined AC (4 lines replacing original 3), restored B2 dependencies, advanced to todo
