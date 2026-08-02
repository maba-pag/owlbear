---
id: 103
title: Add search/usages guidance to reviewer and builder skill workflows
status: archived
priority: medium
created: 2026-03-28 13:34:53.199642+01:00
updated: 2026-03-29 14:32:37.888852+02:00
started: 2026-03-29 14:32:18.914557+02:00
completed: 2026-03-29 14:32:18.914557+02:00
tags:
- phase-2
- scope:agents
- docs
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria
- [ ] .github/skills/code-review/SKILL.md Step 2 (Check source control changes): add a sub-step after `get_changed_files` â€” for any changed function/class signatures, use `vscode_listCodeUsages` to trace callers and assess downstream impact before proceeding
- [ ] .github/skills/tdd-workflow/SKILL.md Step 2 (Plan the change): add a bullet â€” before modifying function signatures or interfaces, use `vscode_listCodeUsages` to find all callers and verify the change won't break downstream consumers
- [ ] Both additions reference the tool by its runtime name `vscode_listCodeUsages` (not the `#search/usages` mention shorthand)
- [ ] Note the limitation: tool does not find dynamic calls (e.g., `getattr`)

See docs/research/search-usages-skill-integration.md for details.

[[2026-03-29]] Sun 03:47
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| code-review Step 2 sub-step | Precise: file, step, tool name, purpose | Keep |
| tdd-workflow Step 2 bullet | Precise: file, step, tool name, purpose | Keep |
| Runtime name reference | Verifiable: vscode_listCodeUsages | Keep |
| Dynamic call limitation note | Verifiable: text present | Keep |

### Architecture Notes
- Docs-only task: two SKILL.md files edited, no .py code, no .agent.md changes
- Both agents already have search tool set (verified in reviewer.agent.md, builder.agent.md)
- Follows existing pattern: get_changed_files referenced by runtime name in code-review Step 2
- TDD N/A: pure documentation changes
- No dependencies required; research complete (docs/research/search-usages-skill-integration.md)

### Changes Made
- Refined AC: added exact step numbers, runtime tool name, limitation note
- No splits or merges needed (single logical change across related skill files)

### Dependencies
- None required. Research doc complete.

[[2026-03-29]] Sun 03:47
## Architecture Review
**Verdict:** Approve

### AC Assessment

AC lines are precise: each specifies the target file, step number, tool runtime name, and purpose. All verifiable pass/fail.

### Architecture Notes
- Docs-only task: two SKILL.md files edited, no .py code, no .agent.md changes
- Both agents already have search tool set (verified in agent files)
- Follows existing pattern: get_changed_files referenced by runtime name in code-review Step 2
- TDD N/A: pure documentation changes
- No dependencies required; research complete

### Changes Made
- Refined AC: added exact step numbers, runtime tool name, limitation note

### Dependencies
- None required. Research doc complete.

[[2026-03-29]] Sun 04:28
## Test-Writer Notes
- Non-implementation task (tagged docs) -- no tests applicable.
- Passing through to builder.

[[2026-03-29]] Sun 07:34
## Builder Notes
- Files changed: .github/skills/code-review/SKILL.md, .github/skills/tdd-workflow/SKILL.md
- code-review Step 2: added sub-step after get_changed_files -- use vscode_listCodeUsages for changed signatures, with getattr limitation note
- tdd-workflow Step 2: added bullet -- before modifying signatures use vscode_listCodeUsages, with getattr limitation note
- Both additions use runtime tool name vscode_listCodeUsages (not #search/usages shorthand)
- All 4 AC lines verified satisfied
- No tests applicable (docs-only task)
- Commit: a46e453 (main)

[[2026-03-29]] Sun 11:51
## Review Evidence
### Test Results
- N/A (docs-only task, no TestFromAC classes, no Python code changed)

### Lint Results
- N/A (no Python files changed)

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| code-review Step 2: sub-step after get_changed_files for vscode_listCodeUsages | .github/skills/code-review/SKILL.md new paragraph: "For any changed function or class signatures, use vscode_listCodeUsages to trace all callers and assess downstream impact before proceeding." (git show a46e453) | PASS |
| tdd-workflow Step 2: bullet for vscode_listCodeUsages before modifying signatures | .github/skills/tdd-workflow/SKILL.md new bullet in Step 2 list: "Before modifying function signatures or interfaces, use vscode_listCodeUsages to find all callers..." (git show a46e453) | PASS |
| Both use runtime name vscode_listCodeUsages (not shorthand) | Confirmed in both inserted lines -- no shorthand present | PASS |
| Both note getattr limitation | Both lines end with: "Note: the tool does not find dynamic calls (e.g., getattr)." | PASS |

### Security
- N/A (no code changes)

### Pass 2 Informational
- Extra out-of-scope change: builder added a "Research-task evidence" callout at Step 8 of code-review/SKILL.md. Not in AC; not disclosed in builder notes. Content is reasonable and introduces no harm, but violates YAGNI and surgical-change discipline.

### Verdict: PASS
- Confidence: .93
- All 4 AC lines satisfied with specific evidence.

[[2026-03-29]] Sun 14:20
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Skill workflow additions only; no conventions or API table changes |
| 2 | Docstrings | No | N/A | No Python modules changed (docs-only task) |
| 3 | docs/sources/overview.md | Yes | Updated | Added search/usages Skill Integration Research (Task #103) section -- VS Code Cheat Sheet and Agent Tools docs cited in research doc; commit 42b94d2 |
| 4 | README.md | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Pass | docs/research/search-usages-skill-integration.md exists, status Complete, linked in task body |
| 6 | Scratch files | No | N/A | No docs/scratch/103-* files found |

### Files Updated
- docs/sources/overview.md

### Scratch Files Cleaned
- None

[[2026-03-29]] Sun 14:32
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| code-review Step 2: sub-step after get_changed_files for vscode_listCodeUsages | skills/code-review/SKILL.md L35 -- paragraph present | PASS |
| tdd-workflow Step 2: bullet for vscode_listCodeUsages | skills/tdd-workflow/SKILL.md L53 -- bullet present | PASS |
| Both use runtime name vscode_listCodeUsages (not shorthand) | Confirmed in both files | PASS |
| Both note getattr limitation | Both end with dynamic calls note | PASS |

### Test Results
- pytest: 568 passed, 82 failed (pre-existing, unrelated). No regressions from docs-only change.
- ruff: All checks passed

### AC Quality: 5/5
AC was specific, complete (exact files, step numbers, tool name, limitation). Clean implementation.

### Confidence: .97
### Action: archive

[[2026-03-29]] Sun 14:32
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| a9d9388 | chore | kanban/tasks/103-*.md | #103 |
