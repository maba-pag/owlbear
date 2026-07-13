---
id: 114
title: Apply python.instructions.md v2 layout edits
status: archived
priority: medium
created: 2026-03-29 00:44:20.598112+01:00
updated: 2026-03-29 03:27:04.209054+02:00
started: 2026-03-29 01:46:10.993091+01:00
completed: 2026-03-29 03:27:04.209054+02:00
tags:
- phase-1
- docs
- scope:build
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Apply three targeted edits to instructions/python.instructions.md identified by #91 research.

## Acceptance Criteria
- [ ] Project layout Tests line reads: tests/ at workspace root + packages/*/tests/ per package
- [ ] Testing section documents --import-mode=importlib (avoids sys.path mutation, allows duplicate test names across packages)
- [ ] Testing section documents dual testpaths: [tests, packages]
- [ ] No source code changes (docs-only edit)
- [ ] File stays under 60 lines

## Context
See docs/research/python-instructions-v2-update.md for full analysis.
Research task: #91. Sibling: #90 (pytest-and-linting skill update).

[[2026-03-29]] Sun 01:45
## Research
N/A trivial gate: upstream research from #91 is complete. See docs/research/python-instructions-v2-update.md.
Verified: pyproject.toml confirms importlib mode, dual testpaths. 5 packages have duplicate test_package.py. Sources logged. AC is specific, docs-only, under 60 lines.

[[2026-03-29]] Sun 03:26
## Architecture Review
**Verdict:** Merge (delete as redundant)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Project layout Tests line | Identical to #91 AC1 | Covered by #91 |
| import-mode=importlib | Identical to #91 AC2 | Covered by #91 |
| Dual testpaths | Identical to #91 AC2 | Covered by #91 |
| No source code changes | Implied by #91 (docs-only task) | Covered by #91 |
| File stays under 60 lines | Minor, not in #91 | Low-risk omission |

### Architecture Notes
This task duplicates #91 (Update python.instructions.md for v2 layout), which is already in-progress with architect review and test-writer sign-off complete. Both tasks target the same file (instructions/python.instructions.md) with the same edits from the same research (docs/research/python-instructions-v2-update.md). #114 was created as a follow-up from #91 research, but #91 itself already serves as the implementation task.

### Changes Made
- Deleted #114 as redundant (merged into surviving #91)

### Dependencies
- Surviving task: #91 (in-progress, covers all AC)
