---
id: 88
title: Enforce scratch dir for agent temp files
status: archived
priority: medium
created: 2026-03-27 22:03:20.819724+01:00
updated: 2026-03-28 03:12:21.215223+01:00
started: 2026-03-28 03:12:17.074134+01:00
completed: 2026-03-28 03:12:17.074134+01:00
tags:
- tooling
- agent
- scope:core
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

1. Delete root-level stale files: builder-notes-task6.md, kanban_show_30.txt, kanban_show_57.txt, pytest_err.txt, pytest_out.txt, pytest_output.txt, task-list.json, tasklist.json, tasklist2.json. All are untracked and safe to remove.
2. Create docs/scratch/.instructions.md (tracked) containing: (a) file placement rule - all agent temp/debug output goes to docs/scratch/{task-id}-{desc}.{ext}, (b) cleanup rule - delete docs/scratch/{task-id}-* files before marking task done, (c) at least two naming convention examples.
3. In .gitignore: add !docs/scratch/.instructions.md exception (docs/scratch/ is gitignored, so without this the new file will not be tracked).
4. In .gitignore: add patterns to prevent root-level temp file recurrence. At minimum cover *_err.txt and *_out.txt (parallel to existing *_output.txt), plus root-scoped patterns for kanban_show_*.txt, tasklist*.json, task-list*.json. After changes, git check-ignore on each of the 9 stale filenames in AC-1 must return a match.
5. No legitimate project files are modified or deleted (README.md, SECURITY.md, .editorconfig, .pre-commit-config.yaml, package-lock.json, Owlbear.code-profile, copilot-debug.log, etc.)

[[2026-03-27]] Fri 22:15
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
AC-1: Precise file list, all verified untracked via git ls-files. Pass.
AC-2: docs/scratch/.instructions.md does not exist yet (confirmed). copilot-instructions.md line 164 already references it. Creation is correct. Pass.
AC-3: docs/scratch/ is gitignored. Without exception, new file would be invisible to git. Critical detail. Pass.
AC-4: git check-ignore confirms only 1 of 9 stale files is caught by current patterns. New patterns needed. Verification criterion (git check-ignore) is mechanical. Pass.
AC-5: Guard rail. Explicit safe-list provided. Pass.

### Architecture Notes
- No code changes, no module layering concerns. Pure config/docs/cleanup task.
- TDD not applicable: no Python source changes, only file operations and config edits.
- No test task needed. Reviewer verifies by filesystem state and git check-ignore.
- Existing gitignore patterns (*_output.txt, *_result.txt, *_run.txt) set precedent for new *_err.txt and *_out.txt patterns.
- Builder must use / prefix for root-scoped patterns (e.g. /kanban_show_*.txt) to avoid unintended matches in subdirectories for non-generic patterns.
- copilot-instructions.md file placement table already documents the rule; docs/scratch/.instructions.md serves as point-of-use reinforcement.

### Changes Made
- Rewrote AC from vague mixed criteria to 5 precise verifiable items
- Removed ambiguity: changed 'moved or deleted if stale' to 'delete' (all confirmed untracked)
- Removed 'optionally' from gitignore requirement (gap is real: 8 of 9 files uncovered)
- Added gitignore exception requirement for new .instructions.md file

### Dependencies
- None. Task is self-contained.

## Builder Notes
- Files changed: .gitignore; docs/scratch/.instructions.md
- Files removed (untracked cleanup): builder-notes-task6.md; kanban_show_30.txt; kanban_show_57.txt; pytest_err.txt; pytest_out.txt; pytest_output.txt; task-list.json; tasklist.json; tasklist2.json
- Tests: 38 passed in tests/test_scratch_dir_enforcement.py; coverage 97 percent on tests/test_scratch_dir_enforcement.py
- Lint: ruff clean for tests/test_scratch_dir_enforcement.py
- Evidence: git check-ignore matched all nine stale filenames; docs/scratch/.instructions.md is not ignored
- Fixes applied: Added scratch instructions file and root temp-file ignore patterns; deleted stale root temp files

[[2026-03-28]] Sat 03:12
## Audit
### AC Verification
| AC | Evidence | Status |
|------|----------|--------|
| AC-1: Delete 9 stale root files | Test-Path confirms all 9 GONE; 38 tests pass | PASS |
| AC-2: docs/scratch/.instructions.md | File exists with placement rule, cleanup rule, 2 naming examples | PASS |
| AC-3: gitignore exception | !docs/scratch/.instructions.md present in .gitignore L57 | PASS |
| AC-4: gitignore patterns | git check-ignore matches all 9 filenames; *_err.txt, *_out.txt, /kanban_show_*.txt, /tasklist*.json, /task-list*.json, /builder-notes-*.md all present | PASS |
| AC-5: Safe files unchanged | 11 safe paths verified via parametrized tests | PASS |

### Test Results
- pytest (task-specific): 38 passed, 0 failed
- pytest (full suite): 149 passed, 45 failed (pre-existing RED tests from other tasks: rename_todo_to_todos, resolve_memory_file_uri, argument_hints, disable_model_invocation), 2 collection errors (pre-existing missing modules)
- ruff: All checks passed

### Architect Quality
- AC specificity: Excellent. Each AC item has mechanical verification criteria.
- Edge case coverage: AC-5 guard rail covers accidental deletion. AC-4 uses git check-ignore as verification.
- Design direction: Architect notes guided builder correctly (root-scoped patterns, v1 pattern precedent).
- AC quality score: 5/5

### Upstream Commits
- 7b7e2f4 test: add failing tests for scratch dir enforcement (#88, test-writer)
- 954b307 chore: enforce scratch dir temp-file rules (#88, builder)

### Confidence: .97
### Action: archive
