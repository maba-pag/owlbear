---
id: 91
title: Update python.instructions.md for v2 layout
status: archived
priority: medium
created: 2026-03-28 01:40:33.702672+01:00
updated: 2026-03-29 05:03:40.081676+02:00
started: 2026-03-29 05:03:35.737124+02:00
completed: 2026-03-29 05:03:35.737124+02:00
tags:
- phase-1
- docs
- scope:build
depends_on:
- 35
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Update python.instructions.md project layout and testing sections to complete the v2 alignment.

## Acceptance Criteria
- [ ] Project layout section lists both source (`packages/*/src/`) and test (`packages/*/tests/`) locations alongside root `tests/`
- [ ] Testing section documents `--import-mode=importlib` and dual testpaths (`tests/` + `packages/`)
- [ ] No leftover v1 path references (`src/owlbear/`, `src/bearclaw/`)

## Context
Depends on #35 (v2 test infrastructure, archived). File already references `packages/*/src/` but is missing `packages/*/tests/` and import-mode docs.

[[2026-03-29]] Sun 01:19
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Layout lists packages/*/src/ and packages/*/tests/ | Clear, verifiable by grep | Refined to include root tests/ |
| Testing documents import-mode and testpaths | Clear, verifiable against pyproject.toml | Refined to specify exact values |
| No v1 path references | Clear, verifiable by grep | Added as safeguard |

### Architecture Notes
- Docs-only task editing instructions/python.instructions.md - no code, no TDD needed
- File already partially v2-aligned (packages/*/src/ present, no v1 refs)
- Builder should reference pyproject.toml lines 17-20 for exact config values
- Sibling task #90 updates pytest-and-linting skill separately - no overlap

### Changes Made
- Refined AC: added explicit AC3 (no v1 refs), tightened AC1/AC2 with specific values
- Updated objective to reflect partial completion state

### Dependencies
- Verified: #35 (v2 test infrastructure) archived
- No new dependencies needed

[[2026-03-29]] Sun 01:56
## Test-Writer Notes
- Non-implementation task (tagged docs) - no tests applicable.
- Docs-only: editing instructions/python.instructions.md only.
- Architecture Review confirms no TDD needed.
- Passing through to builder.

[[2026-03-29]] Sun 05:03
## Audit

See docs/scratch/91-auditor.md for full evidence.

Confidence: .97 | Action: archive

See docs/scratch/91-auditor.md for full evidence.
