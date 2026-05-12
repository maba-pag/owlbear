---
id: 1496
title: 'Cockpit: Replace PDS appendChild monkeypatch with property trap on document.porscheDesignSystem.cdn'
status: todo
priority: important
created: 2026-05-12T02:37:00.298093+00:00
updated: 2026-05-12T09:39:24.129970+00:00
tags:
  - cockpit
  - frontend
parent: 1495
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Replace the global `Element.prototype.appendChild` monkeypatch in main.tsx with an `Object.defineProperty` trap on `document.porscheDesignSystem.cdn` that always returns `window.location.origin` as the URL. This eliminates prototype pollution, handles the double `load()` call from PorscheDesignSystemProvider, and correctly redirects all PDS asset URLs (JS chunks and non-JS assets like icons/flags) to localhost. See `.owlbear/research/1495-pds-v4-local-hosting.md` for full analysis.

## Acceptance Criteria

1. `installPdsRuntimeScriptRewrite()` function, its call site, and the `PDS_CDN_SCRIPT` regex are removed from main.tsx
2. Before `load()` is called, an `Object.defineProperty` trap on `document.porscheDesignSystem.cdn` ensures that reading `cdn.url` returns `window.location.origin` regardless of PDS `load()` assignments
3. The post-bootstrap `document.porscheDesignSystem` reassignment block (current main.tsx lines 38-41) is removed — the property trap replaces this fixup
4. E2E tests in `pds-runtime-csp.spec.ts` pass without modification

Proof bundle: behavioral

## Research
- Research doc: .owlbear/research/1496-pds-property-trap.md
- Sources: 8 studied, 5 high-relevance
- Recommendation: Proceed with Object.defineProperty trap on document.porscheDesignSystem.cdn (confidence: 0.82)
- Follow-up tasks created: #1510 (sync PDS local assets with npm version, at research)
- Decision requests: none

## Challenge Results
- Challenger: block (confidence in original: 0.30)
- Key challenges: trap lifetime after post-bootstrap fixup, version mismatch 4.0.0 vs 4.1.0, contradictory test evidence
- Researcher response: revised — accepted version mismatch as orthogonal pre-existing issue (#1510), rebutted trap lifetime concern (post-bootstrap fixup IS the code being removed), accepted test evidence as supporting trap approach (icon CDN violations prove appendChild monkeypatch is incomplete)
- Final confidence after rebuttal: 0.82

## Key Findings
1. PDS load() uses direct assignment: document[s].cdn = { url, prefixes } — interceptable by defineProperty setter
2. componentsReady() Proxy has only a set trap using Reflect.set — our getter/setter survives
3. Current appendChild monkeypatch is incomplete: only intercepts HTMLScriptElement, not icon/flag asset URLs
4. Pre-existing version mismatch: npm 4.1.0 vs public/ v4.0.0 core chunk + missing icon files — separate follow-up #1510
5. Post-bootstrap fixup (lines 38-41) must be removed as part of implementation — it replaces the trapped namespace
2026-05-12T09:39:24+00:00
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: replace monkeypatch with property trap in main.tsx |
| Interface clarity | PASS | AC specifies concrete function/regex removal, trap mechanism, and regression gate |
| Dependency correctness | PASS | No dependencies. Pre-existing asset mismatch tracked separately as #1510 |
| Module layering | PASS | Frontend-only change, no cross-layer concerns |
| TDD compliance | PASS | Behavioral bundle → test-writer writes RED phase tests |
| KISS/YAGNI | PASS | ~15 LOC replacement, simpler than current ~25 LOC + fixup |
| Premise challenge | PASS | PDS v4 has no native self-hosting config (confirmed by research + GitHub issue #2701) |
| Pattern consistency | PASS | Boot-time side effects in main.tsx follow existing pattern |
| Security surface | PASS | Removes prototype pollution (code hygiene improvement), no new attack surface |
| Single domain | PASS | Cockpit frontend only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| defineProperty trap | PDS changes cdn property structure in future version | N/A (runtime) | No — pinned at 4.1.0 | PDS assets load from CDN instead of localhost |
| Proxy wrapping by componentsReady() | Future PDS adds get trap that shadows our getter | N/A (runtime) | No — verified compatible with current 4.1.0 | Same as above |

### AC Refinement

Rewrote original AC to fix B3 violation ("correctly" banned word in AC-4) and add specificity:
- AC-1: Names concrete function (`installPdsRuntimeScriptRewrite`), call site, and regex (`PDS_CDN_SCRIPT`)
- AC-2: Specifies trap mechanism, timing (before `load()`), and observable invariant
- AC-3: Identifies post-bootstrap fixup block by line reference
- AC-4: Regression gate on existing E2E suite

### Design Diverge
- Skipped — single valid approach (property trap). Research already evaluated 3 options (property trap, scoped patch + trap, keep current) and selected Option A with challenger validation.

### Challenge Results
- Challenger: reconsider (confidence: 0.66)
- Key findings: AC-1/AC-3 are structural checks not input→output pairs; E2E doesn't directly test trap mechanism; version mismatch understated
- Architect response: rebutted — structural removal AC is standard for refactoring tasks; behavioral proof bundle triggers TDD RED phase where test-writer writes trap-specific unit tests; version mismatch is pre-existing/orthogonal (#1510); consolidation test not needed (different files/concerns between #1496 and #1497)
- Override justification: all moderate-severity findings are addressed by the existing proof bundle workflow. No blocking architectural defects.

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: behavioral
- Test-writer: PROCEED
- Guidance for test-writer: Write a jsdom unit test that (1) installs the property trap, (2) simulates PDS load() cdn assignment, (3) asserts cdn.url returns window.location.origin. E2E in pds-runtime-csp.spec.ts covers regression.

### Verdict: APPROVE
### Action Taken: Refined AC (B3 fix, specificity improvements), assigned proof bundle behavioral, advanced backlog → todo.