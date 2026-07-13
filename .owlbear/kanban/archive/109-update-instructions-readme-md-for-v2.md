---
id: 109
title: Update instructions/README.md for v2
status: archived
priority: medium
created: 2026-03-28 21:46:19.035227+01:00
updated: 2026-03-30 04:41:38.086520+02:00
started: 2026-03-30 04:40:53.863477+02:00
completed: 2026-03-30 04:40:53.863477+02:00
tags:
- phase-1
- scope:docs
- type:docs
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Update instructions/README.md to accurately describe the directory as the primary location for VS Code instruction files. Remove stale references to .github/instructions/.

## Acceptance Criteria
- [ ] Remove 'transition placeholder' text and .github/instructions/ reference
- [ ] Describe instructions/ as the primary and sole location for VS Code instruction files
- [ ] List all 4 files with applyTo scopes:
  - agent-common.instructions.md (applyTo: `**`) - Cross-agent rules
  - python.instructions.md (applyTo: `**/*.py`) - Python conventions
  - frontend.instructions.md (applyTo: `src/**/ui/**,...`) - Frontend conventions
  - research-docs.instructions.md (applyTo: `docs/research/*.md`) - Research guardrails
- [ ] Keep it under 20 lines
- [ ] No test task required (pure documentation, no .py files)

## Context
Research: docs/research/instructions-readme-update.md
Merged: #110 (redundant follow-up deleted)
Related: #111 (stale refs cleanup, separate scope)

[[2026-03-29]] Sun 01:19
## Architecture Review
**Verdict:** Approve (merged #110)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Remove placeholder text | Verifiable, pass/fail | Keep |
| Describe as primary location | Verifiable | Keep |
| List 4 files with applyTo | Verifiable, enumerated | Keep |
| Under 20 lines | Verifiable, measurable | Keep |

### Architecture Notes
Pure documentation task, single file (instructions/README.md). No code, no tests, no security surface. Verified 4 instruction files exist. Merged redundant #110 (identical scope). #111 remains separate for stale-ref cleanup across other files.

### Changes Made
- Refined AC from #110's more specific version
- Deleted #110 (redundant follow-up)
- Approved to todo

### Dependencies
- None required. #111 is related but independent.

[[2026-03-30]] Mon 03:21
## Review Evidence
Pure doc task. No tests required (AC explicit). Ruff N/A (no Python changed).
Changed: instructions/README.md (commit 746da29)
AC: Remove placeholder text PASS, Remove .github/ ref PASS, Describe as primary location PASS, 4 files listed with correct applyTo PASS, Under 20 lines (12 lines) PASS
Security: No code changed. Confidence: .96

[[2026-03-30]] Mon 03:57
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Pure README update, no behavior or API change |
| 2 | Docstrings | No | N/A | No Python modules touched |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/instructions-readme-update.md exists and linked in task body; follow-ups #111 created |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-30]] Mon 04:41
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 6cde020 | chore | kanban task+activity | #109 |
