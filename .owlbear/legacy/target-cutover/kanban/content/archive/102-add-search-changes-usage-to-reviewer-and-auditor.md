---
id: 102
title: Add search/changes usage to reviewer and auditor skill workflows
status: archived
priority: medium
created: 2026-03-28 13:34:47.158349+01:00
updated: 2026-03-29 03:41:32.701118+02:00
started: 2026-03-29 03:41:27.838056+02:00
completed: 2026-03-29 03:41:27.838056+02:00
tags:
- phase-2
- scope:agents
- docs
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria
- [ ] code-review SKILL.md: new Step 2 'Check source control changes' inserted between current Step 1 (Read and claim) and current Step 2 (Run tests). Uses get_changed_files with sourceControlState: ['staged', 'unstaged'] to list changed files. Records the file list for scoping subsequent steps (tests, lint, code reading). All subsequent steps renumbered (+1).
- [ ] task-verification SKILL.md: new bullet added to Step 2 (Verify each task) using get_changed_files to verify changed files align with task AC scope. Flags unexpected files outside the task's domain.
- [ ] Both steps reference the tool by its runtime name get_changed_files (not the #search/changes mention shorthand).

See docs/research/search-changes-skill-integration.md for details.

[[2026-03-28]] Sat 21:43
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| code-review new Step 2 | Original vague on placement. Refined to specify exact insertion point, tool name, and renumbering. | Rewritten |
| task-verification new bullet | Original vague on step vs bullet. Refined to specify integration into Step 2 with scope-check behavior. | Rewritten |
| Tool name reference | Clear as-is but tightened to specify runtime name vs mention shorthand. | Tightened |

### Architecture Notes
Docs-only task: modifies two SKILL.md files. No Python code, no .agent.md changes, no new dependencies. Both agents already have search tool set (confirmed in research doc). Risk is low, changes are additive.

TDD exception: deliverables are markdown workflow docs, not application code. No preceding test task required.

Single domain: scope:agents docs. No multi-domain concern.

### Changes Made
- Refined AC: specified exact step placement, tool runtime name, renumbering requirement
- No new tasks created (docs-only, no TDD pair needed)

### Dependencies
- None. Both skill files exist and are independently editable.

[[2026-03-28]] Sat 22:43
## Test-Writer Notes
- Non-implementation task (tagged docs) - no tests applicable.
- Deliverables are SKILL.md workflow docs, not application code (confirmed by Architecture Review).
- Passing through to builder.

[[2026-03-29]] Sun 01:30
## Builder Notes
- Files changed: .github/skills/code-review/SKILL.md, .github/skills/task-verification/SKILL.md
- Tests: N/A (docs-only task, non-impl pass-through)
- Lint: N/A
- Evidence: code-review SKILL.md: new Step 2 inserted (get_changed_files with staged+unstaged), steps 2-8 renumbered to 3-9, sub-steps 5.x renumbered 6.x, 6.x renumbered 7.x. task-verification SKILL.md: new bullet added to Step 2 for scope alignment check.
- Fixes applied: None

[[2026-03-29]] Sun 03:41
## Audit
### AC Verification
| AC Line | Evidence | Status |
|------|--------|------|
| AC1: code-review new Step 2 with get_changed_files, renumbered | SKILL.md Step 2 present, steps 3-9 renumbered | PASS |
| AC2: task-verification new bullet in Step 2 | Bullet present with scope-check behavior | PASS |
| AC3: runtime name get_changed_files used | Both files use get_changed_files | PASS |

### Test Results
- pytest: 440 passed, 55 failed (all pre-existing from other tasks)
- ruff: All checks passed (tests/)
- src/ ruff E902: pre-existing config issue (no src/ dir)

### Architect Quality
- AC specificity: 5/5 - exact insertion points, tool name, renumbering
- No edge case gaps (docs-only task)

### Confidence: .97
### Action: archive

-t

[[2026-03-29]] Sun 03:41
## Audit
### AC Verification
AC1 (code-review new Step 2): PASS - Step 2 present with get_changed_files, steps 3-9 renumbered
AC2 (task-verification new bullet): PASS - Bullet present with scope-check behavior
AC3 (runtime name): PASS - Both files use get_changed_files

### Test Results
- pytest: 440 passed, 55 failed (all pre-existing from other tasks)
- ruff: All checks passed

### Architect Quality: 5/5
### Confidence: .97
### Action: archive

[[2026-03-29]] Sun 03:41
## Audit
### AC Verification
AC1 (code-review new Step 2): PASS - Step 2 present with get_changed_files, steps 3-9 renumbered
AC2 (task-verification new bullet): PASS - Bullet present with scope-check behavior
AC3 (runtime name): PASS - Both files use get_changed_files

### Test Results
- pytest: 440 passed, 55 failed (all pre-existing from other tasks)
- ruff: All checks passed

### Architect Quality: 5/5
### Confidence: .97
### Action: archive
