---
id: 165
title: Fix broken skill paths in frontend prompts
status: archived
priority: medium
created: 2026-03-29 19:49:17.606228+02:00
updated: 2026-03-30 00:47:07.955020+02:00
started: 2026-03-29 20:16:38.075644+02:00
completed: 2026-03-30 00:46:31.186467+02:00
tags:
- phase-1
- scope:docs
- type:docs
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Fix broken relative paths in .github/prompts/frontend-*.prompt.md files. After #117 deleted .github/skills/, the ../skills/ references resolve to the deleted directory instead of root skills/.

## AC
- [ ] frontend-audit.prompt.md: change `../skills/` to `../../skills/` (2 refs at L14-15)
- [ ] frontend-normalize.prompt.md: change `../skills/` to `../../skills/` (1 ref at L15)
- [ ] frontend-polish.prompt.md: change `../skills/` to `../../skills/` (5 refs at L16, L18-21)
- [ ] Verify corrected paths resolve to existing files

## Context
See docs/research/github-v1-cleanup.md sec 3. Broken by #117 (.github/skills/ deletion).

[[2026-03-29]] Sun 20:41
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| audit: 2 refs L14-15 | Verified via grep -- 2 matches confirmed | None |
| normalize: 1 ref L15 | Verified via grep -- 1 match confirmed | None |
| polish: was 4 refs, actually 5 at L16,L18-21 | Count corrected in body | Refined to 5 |
| Verify paths resolve | All 6 target files confirmed to exist | None |

### Architecture Notes
Simple find-replace of `../skills/` to `../../skills/` in 3 prompt.md files. No code, no tests, no layering concerns. All target files under skills/frontend-design/ confirmed present. No TDD needed (type:docs, scope:docs).

### Changes Made
- Corrected AC ref count for polish file: 4 to 5

### Dependencies
- #117 (.github/skills/ deletion): done -- confirmed .github/skills/ no longer exists

[[2026-03-29]] Sun 21:10
## Test-Writer Notes
- Non-implementation task (tagged type:docs) -- no tests applicable.
- Passing through to builder.

[[2026-03-29]] Sun 22:11
## Builder Notes
- Files changed: .github/prompts/frontend-audit.prompt.md, frontend-normalize.prompt.md, frontend-polish.prompt.md
- Tests: N/A (type:docs task, no automated tests)
- Lint: N/A
- Evidence: All 8 ../skills/ refs replaced with ../../skills/; all 6 target skill files confirmed to exist; 0 bare ../skills/ remaining; commit 6f9f047
- Fixes applied: ../skills/ to ../../skills/ (2 refs audit, 1 normalize, 5 polish)

[[2026-03-29]] Sun 23:58
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Path fix in prompt files; no behavior or convention change |
| 2 | Docstrings | No | N/A | No Python files modified |
| 3 | sources/overview.md | No | N/A | No external patterns used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | docs/research/github-v1-cleanup.md exists and referenced in task body |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/165-* files found)

[[2026-03-30]] Mon 00:46
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| audit: 2 refs L14-15 | L14,L15 both use ../../skills/ | PASS |
| normalize: 1 ref L15 | L15 uses ../../skills/ | PASS |
| polish: 5 refs L16,L18-21 | All 5 lines use ../../skills/ | PASS |
| Paths resolve to files | All 6 target files confirmed via Test-Path | PASS |

### Test Results
- pytest: 870 passed, 64 pre-existing failures (none related to #165)
- ruff: All checks passed

### AC Quality: 5/5
AC was specific with exact file names, line numbers, and ref counts. Led to clean implementation.

### Confidence: .97
### Action: archived

### Upstream Commit
- 6f9f047 docs: fix broken skill paths in frontend prompts (#165, builder)

[[2026-03-30]] Mon 00:47
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| c458889 | chore | kanban/tasks/165-*.md | #165 |
