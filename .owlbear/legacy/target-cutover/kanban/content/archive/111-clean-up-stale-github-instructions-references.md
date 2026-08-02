---
id: 111
title: Clean up stale .github/instructions/ references
status: archived
priority: medium
created: 2026-03-28 22:24:22.933331+01:00
updated: 2026-03-30 04:50:20.127222+02:00
started: 2026-03-30 04:47:07.550699+02:00
completed: 2026-03-30 04:47:07.550699+02:00
tags:
- phase-1
- scope:docs
- type:docs
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Remove the last stale .github/instructions/ reference in active files.

## AC

- [ ] .github/prompts/agent-audit.prompt.md L15: change .github/instructions/*.instructions.md to instructions/*.instructions.md
- [ ] Grep verify: no remaining .github/instructions/ references in active files (exclude kanban task history, board snapshots, research docs, and instructions/README.md historical note)

## Context

Found during #109 research. See docs/research/stale-github-instructions-refs.md.
Original AC items for docs/decisions/README.md (DROPPED, not stale) and scripts/setup.py (DEFERRED to #29) were corrected by research.

[[2026-03-29]] Sun 04:19
## Architecture Review
**Verdict:** Approve

### AC Assessment

AC Line | Assessment | Action
agent-audit.prompt.md L15 fix | Confirmed stale by research + grep | Keep
Grep verify | Standard verification step | Keep

### Architecture Notes
This is a docs-only cleanup task (type:docs, scope:docs). The only change is a path reference in a .prompt.md file. No application code, no interfaces, no security surface. The research doc (docs/research/stale-github-instructions-refs.md) thoroughly validated all original AC items: AC1 DROPPED (was .github/skills, not instructions), AC3 DEFERRED to #29 (setup.py has test/mapping implications). TDD exemption: no application code to test. Grep verification in AC2 serves as the acceptance gate.

### Changes Made
- Rewrote task body with corrected AC per research findings
- Dropped AC1 (docs/decisions/README.md) and AC3 (scripts/setup.py deferred to #29)

### Dependencies
- None required. #29 will handle the setup.py mapping cleanup.

[[2026-03-29]] Sun 04:47
## Test-Writer Notes
- Non-implementation task (tagged type:docs, scope:docs) - no tests applicable.
- Architect noted TDD exemption: no application code to test.
- Passing through to builder.

## Test-Writer Notes - Non-implementation (type:docs) - no tests applicable. Architect noted TDD exemption. Passing through to builder.

[[2026-03-29]] Sun 19:00
## Builder Notes
- Files changed: .github/prompts/agent-audit.prompt.md (1 line fix)
- Tests: N/A (type:docs, TDD exemption per architect)
- Lint: N/A (no Python changes)
- Evidence: Changed `.github/instructions/*.instructions.md` -> `instructions/*.instructions.md` at L15
- Grep verify: All remaining matches are gitignored scratch/archive files or tests/test_port_instruction_files.py (intentional migration-verification test, not stale)
- Commit: 0adf2f7

[[2026-03-30]] Mon 03:48
## Docs Gate - Checklist: all N/A except research doc (exists at docs/research/stale-github-instructions-refs.md, PASS). No Python changes, no CLI changes, no external patterns, no scratch files. Files Updated: None.

-t

[[2026-03-30]] Mon 04:47
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| agent-audit.prompt.md L15 fix | Confirmed at L15: instructions/*.instructions.md (commit 0adf2f7, 1 file 1 line) | PASS |
| Grep verify no stale refs | grep_search: all matches in board.json, board_state.json, candidates.json, output.json (excluded per AC) | PASS |

### Test Results
- pytest: 1109 passed, 139 failed (all pre-existing RED-phase), 6 errors (pre-existing) - none in task scope
- ruff: N/A (no Python changes)

### Architect Quality
- AC specificity: exact file + line reference, clear exclusion criteria
- Edge case coverage: N/A (single-line docs fix)
- AC quality score: 5/5

### Deduction breakdown: none - both AC items verified with evidence
### Confidence: 1.0
### Action: archive

[[2026-03-30]] Mon 04:47
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| ea927df | chore | kanban task+activity | #111 |

[[2026-03-30]] Mon 04:49
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| agent-audit.prompt.md L15 fix | L15 reads instructions/*.instructions.md, commit 0adf2f7 | PASS |
| Grep verify no remaining refs | All matches in gitignored board snapshots (board.json, board_state.json, etc.), not active files | PASS |

### Test Results
- pytest: 889 passed, 136 failed (all pre-existing, none in task scope), 3 collection errors (planner/voice modules)
- ruff: N/A (no Python changes)

### Architect Quality
- AC specificity: Exact file, line, change specified. Proper grep exclusion clause.
- Edge case coverage: N/A (single-line docs fix)
- AC quality score: 5/5

### Deduction breakdown: none
### Confidence: 1.0
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 8f9d3c3 | chore | kanban/tasks/111-*.md | #111 |
