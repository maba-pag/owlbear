---
id: 218
title: Sync non-impl tag list cross-references across skill files
status: archived
priority: medium
created: 2026-03-30 14:54:54.311161+02:00
updated: 2026-04-03 03:31:16.912296+02:00
started: 2026-04-03 03:30:39.447178+02:00
completed: 2026-04-03 03:30:39.447178+02:00
tags:
- scope:agents
- quality
- type:config
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria
- [ ] Each file containing the non-impl tag list has a cross-reference comment (`NON_IMPL_TAGS` keyword) pointing to `skills/dispatch-planning/SKILL.md` agent dispatch table as the authoritative list
- [ ] The authoritative comment in `skills/dispatch-planning/SKILL.md` (near L17) lists all secondary locations: `skills/tdd-red/SKILL.md`, `skills/arch-review/SKILL.md`, `.github/prompts/agent-audit.prompt.md`
- [ ] The internal `$nonImpl` array comment in `skills/dispatch-planning/SKILL.md` (near L149) references all 3 secondary files (currently missing arch-review)
- [ ] `grep NON_IMPL_TAGS` returns exactly 4 operational files (dispatch-planning, tdd-red, arch-review, agent-audit)
- [ ] Adding a new non-impl tag requires updating only one authoritative location plus following the cross-references

## Context
See docs/research/non-impl-tag-cross-references.md for recommended pattern. Created from #215 research.
Note: Research identified 3 files but arch-review SKILL.md is a 4th location added during implementation.
Most AC items are pre-satisfied (commit ba36a0a). Builder verifies and fixes L149 internal comment.

[[2026-04-03]] Fri 00:00
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A -- not research-driven (T1 config change)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Cross-ref comment in each file | Clear, verifiable. Already satisfied in 4 files. | Kept |
| Authoritative comment lists secondaries | Verifiable. dispatch-planning L17-20 lists 3 secondaries. | Kept |
| Internal nonImpl ref all secondaries | Verifiable. L149 omits arch-review -- builder fixes. | ADDED |
| grep returns exactly 4 files | Verifiable. Currently returns 4 matches. | Updated from 3 to 4 |
| Single authoritative update location | Process-verifiable by pattern inspection. | Kept |

### Architecture Notes
Non-impl task -- edits markdown/skill files only. Tags quality + type:config ensure test-writer pass-through.
Most AC pre-satisfied (commit ba36a0a). One gap: dispatch-planning L149 omits arch-review. Builder verifies and fixes.
Researcher identified 3 files; arch-review is a 4th location. AC refined to 4-file scope.

### Changes Made
- Refined AC: 3 files to 4, added L149 internal comment AC item

### Dependencies
- None

### Challenge Results
- Challenger: reconsider (confidence .70)
- Key challenges: (1) AC said 3 files but 4 exist, (2) L149 omits arch-review, (3) task 329 AC stale
- Architect response: accepted 1+2, refined AC. Challenge 3 out of scope.

[[2026-04-03]] Fri 00:41
## Test-Writer Notes
- Non-implementation task (tagged quality, type:config) -- no tests applicable.
- AC edits markdown/skill files only. No Python implementation deliverables.
- Passing through to builder.

[[2026-04-03]] Fri 01:44
## Builder Notes
- Non-implementation task (markdown/skill files only)
- Files changed: skills/dispatch-planning/SKILL.md (1 line)
- Fix: L149 internal comment updated to include arch-review SKILL.md in See-also list
- All AC verified: L17 authoritative comment lists 3 secondaries; L149 now references all 3; grep NON_IMPL_TAGS returns 4 operational files (dispatch-planning x2, tdd-red, arch-review + agent-audit in .github/)
- Commit: 6ebfadc (chore: sync NON_IMPL_TAGS internal comment to reference arch-review)
- Pre-existing working-tree changes to dispatch-planning (lines 93-109, Action requests simplification) preserved as unstaged -- not this task's scope

[[2026-04-03]] Fri 02:30
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal comment markers added to skill files -- no behavior or API change |
| 2 | Docstrings | No | N/A | No Python modules changed -- markdown-only task |
| 3 | sources/overview.md | No | N/A | No external patterns or repos used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | docs/research/non-impl-tag-cross-references.md exists and linked in task body (#215 research) |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/218-* files found)

[[2026-04-03]] Fri 02:30
## Docs Gate
Checklist: all items N/A (markdown-only task, no behavior change, no Python modules, no external sources, no CLI changes). Research doc exists at docs/research/non-impl-tag-cross-references.md. No scratch files. Files updated: None.

[[2026-04-03]] Fri 03:30
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Cross-ref in each file | NON_IMPL_TAGS at tdd-red L26, arch-review L147, agent-audit L107, dispatch-planning L17 | PASS |
| Authoritative lists secondaries | dispatch-planning L17-20 names tdd-red, arch-review, agent-audit | PASS |
| Internal nonImpl refs all 3 | dispatch-planning L98 names tdd-red, arch-review, agent-audit | PASS |
| grep returns 4 operational files | 4 operational matches confirmed (dispatch-planning x2, tdd-red, arch-review, agent-audit) | PASS |
| Single authoritative update point | Secondaries say 'Update there first, then sync here'; authoritative lists all | PASS |

### Test Results
- pytest: 3135 passed, 247 failed (all pre-existing, none in task scope; test_skill_frontmatter 25/25 pass)
- ruff: 3 pre-existing errors (E902, PT018 x2), none in task scope

### AC Quality: 4/5
AC was specific and verifiable. Line number reference (L149) drifted to L98 due to file evolution, but builder found it without difficulty.

### Deduction breakdown
- Start: 1.0
- Missing reviewer evidence section: -.02
- Final: .98

### Confidence: .98
### Action: archive

[[2026-04-03]] Fri 03:30
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Cross-ref in each file | NON_IMPL_TAGS at tdd-red L26, arch-review L147, agent-audit L107, dispatch-planning L17 | PASS |
| Authoritative lists secondaries | dispatch-planning L17-20 names tdd-red, arch-review, agent-audit | PASS |
| Internal nonImpl refs all 3 | dispatch-planning L98 names tdd-red, arch-review, agent-audit | PASS |
| grep returns 4 operational files | 4 operational matches confirmed (dispatch-planning x2, tdd-red, arch-review, agent-audit) | PASS |
| Single authoritative update point | Secondaries say 'Update there first, then sync here'; authoritative lists all | PASS |

### Test Results
- pytest: 3135 passed, 247 failed (all pre-existing, none in task scope; test_skill_frontmatter 25/25 pass)
- ruff: 3 pre-existing errors (E902, PT018 x2), none in task scope

### AC Quality: 4/5
AC was specific and verifiable. Line number reference (L149) drifted to L98 due to file evolution, but builder found it without difficulty.

### Deduction breakdown
- Start: 1.0
- Missing reviewer evidence section: -.02
- Final: .98

### Confidence: .98
### Action: archive

[[2026-04-03]] Fri 03:31
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 962ec1c | chore | kanban/tasks/218-*.md | #218 |
