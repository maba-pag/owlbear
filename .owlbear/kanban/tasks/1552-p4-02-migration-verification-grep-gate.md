---
id: 1552
title: 'P4-02: migration verification grep gate'
status: research
priority: important
created: 2026-05-13T18:43:53.193530+00:00
updated: 2026-05-13T18:43:53.193530+00:00
tags:
  - phase-4
  - scope:cockpit
  - test
  - frontend
parent: 1534
depends_on:
  - 1543
  - 1546
  - 1547
  - 1548
  - 1549
  - 1550
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Test assertion or script that greps source files for old `--pds-theme-light-*` token references and fails if any remain
- **Out:** Token rename implementation (done in P1-02 #1543 and downstream tasks)

## Acceptance Criteria

- AC-1: A Vitest assertion or shell script greps `.css`, `.tsx`, `.ts` files under `serve/cockpit/web/` (including Shell.css and test files) and fails if any `--pds-theme-light-*` reference remains
- AC-2: Grep scope covers source files, stylesheets, and test files — no blind spots for accidental old-token usage

Proof bundle: behavioral