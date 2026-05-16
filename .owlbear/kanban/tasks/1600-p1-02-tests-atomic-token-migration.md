---
id: 1600
title: 'P1-02: Tests — atomic token migration'
status: research
priority: important
created: 2026-05-16T03:35:41.045394+00:00
updated: 2026-05-16T03:35:41.045394+00:00
tags:
  - frontend
  - pds
  - phase-1
parent: 1590
depends_on:
  - 1597
ac:
  - Tests assert zero --pds-* references in CSS and TSX source files under 
    serve/cockpit/web/src/
  - Tests assert tokens.css does not exist in the source tree
  - Tests assert light/dark theme toggle via useTheme hook functions correctly 
    (.scheme-dark/.scheme-light classes trigger PDS light-dark() cascade)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Scope: Failing tests for the atomic token migration. Tests cover: token references eliminated, tokens.css deleted, theme switching preserved, affected test files updated.
Out of scope: Actual migration implementation.