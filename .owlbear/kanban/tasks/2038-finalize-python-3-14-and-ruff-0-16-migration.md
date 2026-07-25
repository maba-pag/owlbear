---
id: 2038
title: Finalize Python 3.14 and Ruff 0.16 migration
status: build
priority: high
created: 2026-07-25T03:08:35.587003+02:00
updated: 2026-07-25T03:08:35.587003+02:00
tags:
  - config
  - tooling
  - type:build
  - rigor:standard
parent:
depends_on: []
ac:
  - Existing Python floor/config changes and Ruff compatibility changes are 
    committed separately.
  - Manual and CI MegaLinter references are v9.6.0 while workspace Ruff remains 
    0.16.0 and MegaLinter Ruff remains 0.15.20.
  - Live and seeded hooks use the same narrow inline S607 suppressions and the 
    broad seed-only S607 ignore is removed.
  - D1xx rules are enabled except D105 and D107, with substantive missing 
    docstrings resolved.
  - Each requested package is committed separately without including unrelated 
    worktree changes.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Implement the user-directed dependency migration closure in reverse order: commit the already-validated Python floor/config and Ruff source changes separately; align manual MegaLinter to CI v9.6 while retaining bundled Ruff versions; synchronize live and seeded hook suppressions; enable the useful D1xx missing-docstring rules while excluding D105 and D107. Preserve unrelated concurrent worktree changes.