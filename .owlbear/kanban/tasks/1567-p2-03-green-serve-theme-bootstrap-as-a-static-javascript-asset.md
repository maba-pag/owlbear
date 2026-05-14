---
id: 1567
title: 'P2-03 GREEN: Serve theme-bootstrap as a static JavaScript asset'
status: backlog
priority: needed
created: 2026-05-14T18:26:42.415783+00:00
updated: 2026-05-14T18:27:14.711852+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:build
  - bug
  - visual-remediation
parent: 1559
depends_on:
  - 1561
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context
Implements the failing proof from #1561. Source audit: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` section 4.

## Scope
In scope: Cockpit static serving behavior for `/theme-bootstrap.js` and regression compatibility with local PDS asset mode.
Out of scope: CDN asset delivery, theme redesign, and dashboard visual styling.

## Acceptance Criteria
AC-1: Given GET `/theme-bootstrap.js` against built Cockpit assets, Cockpit returns HTTP 200 with JavaScript MIME and a non-HTML body; verify with the named test from #1561.
AC-2: Given a browser loads Cockpit before React mount, the console has no `Unexpected token '<'` error for theme bootstrap; verify with Playwright console capture.
AC-3: Existing local PDS asset and CSP regression tests named in #1561 continue to pass; verify by quality-runner output.

Proof bundle: behavioral

## Evidence Expectations
Passing #1561 regression plus named PDS local-asset/CSP checks.