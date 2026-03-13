---
id: 596
title: 'Research: ykdojo/claude-code-tips'
status: archived
priority: important
created: 2026-03-05T23:52:10.8646625+01:00
updated: 2026-03-10T21:02:49.9692457+01:00
started: 2026-03-06T22:55:16.2812793+01:00
completed: 2026-03-10T21:02:49.9692457+01:00
tags:
    - research
    - phase-research
    - scope:copilot
parent: 583
claimed_by: builder
claimed_at: 2026-03-10T20:34:45.2382448+01:00
class: standard
---

**Source:** https://github.com/ykdojo/claude-code-tips
Analyze for command-line tips, prompt engineering patterns, and developer workflow efficiencies.

**Status:** Research complete. Remaining work is cleanup and follow-up task creation.

**Acceptance Criteria:**
1. Delete duplicate research doc at `docs/research/claude-code-tips.md` (root copy). Keep only `docs/research/claude-code-tips.md`.
2. Correct follow-up task commands in `docs/research/claude-code-tips.md` section 5:
   - Follow-up #1 target: `agent-common.instructions.md` section Task coordination > Handoff / blocked (not nonexistent 'kanban-based-development skill').
   - Follow-up #2 target: `agent-common.instructions.md` section Terminal discipline (not nonexistent `terminal.instructions.md`).
3. Create corrected follow-up kanban tasks at `backlog` status, each with verifiable AC. Both are `nice-to-have` priority.
4. Verify `docs/sources/overview.md` entry exists for this repo (already present  verify only).
5. Verify ephemeral clone `docs/scratch/research/claude-code-tips/` is deleted (already done  verify only).

[[2026-03-10]] Tue 17:56

## Architecture Review (2026-03-10)
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Delete root duplicate | Verifiable, file confirmed to exist at both locations | Keep |
| 2. Correct follow-up targets in research doc | Verified: kanban-based-development skill does not exist, terminal.instructions.md does not exist. Correct targets: agent-common.instructions.md sections | Keep |
| 3. Create follow-up tasks at backlog, nice-to-have | Verifiable, priority appropriate for marginal improvements | Keep |
| 4. Verify sources entry | Already present at docs/sources/overview.md line 989 | Keep (verify-only) |
| 5. Verify clone deleted | Already confirmed False for docs/scratch/research/claude-code-tips | Keep (verify-only) |

### Architecture Notes
Research task  no code changes, no module impacts. Single domain (research). No TDD compliance needed.

**Research quality:** High. 7 patterns analyzed with comparison tables and confidence scores (0.40-0.85). Recommendations are appropriately scoped:
- Follow-up #1 (handoff template): Marginal improvement to existing handoff note structure in agent-common.instructions.md lines 40-43. Current template has 'Current state / Open questions / Next step'; proposal adds 'what-failed' tracking. nice-to-have.
- Follow-up #2 (command decomposition): Adds explicit guidance to Terminal discipline section. Currently only covers chaining and retry limits, not approval-gate decomposition. nice-to-have.

**Prior review issues (all resolved by AC rewrite):**
1. Duplicate research doc  AC #1 addresses
2. Follow-up #1 wrong target (kanban-based-development skill -> agent-common.instructions.md)  AC #2 addresses
3. Follow-up #2 wrong target (terminal.instructions.md -> agent-common.instructions.md)  AC #2 addresses

### Changes Made
- Rewrote task body with 5 verifiable AC reflecting current state (research done, cleanup remaining)
- Corrected all path references
- Moved to todo

### Dependencies
- None  standalone research task

[[2026-03-10]] Tue 18:11
## Test-Writer Notes
Non-implementation task (tagged research)  no tests applicable. Passing through to builder.

[[2026-03-10]] Tue 18:11
## Test-Writer Notes
Non-implementation task (tagged research) - no tests applicable. Passing through to builder.

[[2026-03-10]] Tue 19:44
## Review Evidence (2026-03-10)

### Test Results
N/A - research task, no Python code changes.

### Lint Results
N/A - research task, no Python code changes.

### Coverage
N/A - research task.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. Delete root duplicate | Test-Path docs/research/claude-code-tips.md = False | PASS |
| 2. Correct section 5 targets | Lines 104,106 target agent-common.instructions.md | PASS |
| 3. Create follow-up tasks | #728 and #729 at backlog, nice-to-have, with AC | PASS |
| 4. Verify sources entry | docs/sources/overview.md line 998 | PASS |
| 5. Verify clone deleted | Test-Path docs/scratch/research/claude-code-tips = False | PASS |

### Verdict: PASS (.95)
### Action: moved 596 review -> docs

[[2026-03-10]] Tue 20:34
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Research task, no behavior/API change to OwlBear |
| 2 | Docstrings | No | N/A | No Python modules created or modified |
| 3 | sources/overview.md | Yes | Pass | Entry verified at line 998 (ykdojo/claude-code-tips, All Rights Reserved) |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/claude-code-tips.md exists, linked in task body. Follow-ups #728 (handoff template) and #729 (command decomposition) at backlog, nice-to-have, with AC |
| 6 | No impact | Partial | N/A | Items 1,2,4 have no docs impact; items 3,5 verified |

### Files Updated
- None

### Scratch Files Cleaned
- None found (docs/scratch/596-* empty; root duplicate already deleted; clone already deleted)
