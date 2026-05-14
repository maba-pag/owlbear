---
id: 1561
title: 'P2-02 RED: Guard theme-bootstrap static serving'
status: backlog
priority: needed
created: 2026-05-14T18:26:23.375667+00:00
updated: 2026-05-14T18:29:06.119076+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:test
  - bug
  - visual-remediation
parent: 1559
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context
Source of truth: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` section 4. `/theme-bootstrap.js` currently falls through to HTML even though the built asset exists.

## Scope
In scope: focused regression proof for serving the existing theme bootstrap asset from Cockpit.
Out of scope: PDS CDN mode, theme redesign, and visual styling changes.

## Acceptance Criteria
AC-1: Test-writer adds a focused test that requests `/theme-bootstrap.js` from Cockpit and observes HTTP 200 with JavaScript content type plus non-HTML response body; verify by quality-runner output for the named test.
AC-2: Test-writer records that the new test fails against the current implementation because `/theme-bootstrap.js` returns HTML or triggers a JavaScript parse error; verify by quality-runner evidence in the task body.
AC-3: Test-writer names the existing PDS local-asset CSP regression scope that must remain green after the fix; verify by artifact inspection of Test Evidence.

Proof bundle: behavioral

## Evidence Expectations
Named failing test, failing output, and listed CSP/local-asset regression scope.
2026-05-14T18:29:06+00:00
## Research

**Validation pass** — task created post-research from `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` §4/§10. Already at backlog.

### Key findings confirmed against code:
- `serve/cockpit/src/owlbear_cockpit/main.py` L122-131: only `/assets` and `/porsche-design-system` are static-mounted; catch-all `/{path:path}` returns `index.html` for `/theme-bootstrap.js`.
- `serve/cockpit/web/public/theme-bootstrap.js` exists and is copied to `dist/` during build.
- Test approach: TestClient GET `/theme-bootstrap.js` → assert 200, JS content-type, non-HTML body.

### CSP/local-asset regression scope (AC-3):
- `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`
- `tests/test_cockpit_pds_build_compat.py`
- `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts`

### Tier: T1 (bug fix, narrow scope). No DR needed.

Research is validated. Task is ready for architect review at backlog.