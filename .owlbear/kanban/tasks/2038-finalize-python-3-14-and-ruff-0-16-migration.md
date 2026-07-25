---
id: 2038
title: Finalize Python 3.14 and Ruff 0.16 migration
status: verify
priority: high
created: 2026-07-25T03:08:35.587003+02:00
updated: 2026-07-25T03:31:08.970852+02:00
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

[[2026-07-25T03:31:08+02:00]]
## Builder Notes

Implemented the requested reverse-order migration closure in five isolated package commits:

- `9e954c3fd`: Python 3.14.6 floor, manifests, documentation, Renovate policy, floor test, and lock.
- `803150128`: previously validated Ruff 0.16 source/format compatibility and test-stability changes.
- `f7d8d4b84`: manual MegaLinter aligned to CI v9.6.0; workspace Ruff remains 0.16.0 and MegaLinter v9.6 retains bundled Ruff 0.15.20.
- `5023bf431`: live/seed hook sources synchronized with narrow inline S607 suppressions; broad seed exception removed.
- `eca60a7a1`: enabled D100/D101/D102/D103/D104/D106, retained D105/D107 exceptions, and added meaningful public API docstrings.

### Proof

- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: 332 files already formatted.
- `uv run ruff check . --select D100,D101,D102,D103,D104,D106`: passed.
- Focused floor/hook suite: 72 passed.
- Challenger affected-area sweep: 776 passed.
- YAML validation: passed.
- `uv lock --check`: resolved 166 packages.
- `diff -ru --exclude='__pycache__' .owlbear/hooks seed/.owlbear/hooks`: identical.
- Commit inspection confirms each package is isolated and unrelated memory, VS Code, and delivery-pipeline changes remain uncommitted.

The aggregate main-worktree suite currently has five native-runtime transaction failures caused by concurrent admitted delivery-graph state. A clean current-HEAD baseline reproduces the deterministic native-runtime failures before applying the lint package; an earlier uncontaminated validation of the exact dependency/Ruff migration passed 4,073 tests. No current follow-up is required for this task.
