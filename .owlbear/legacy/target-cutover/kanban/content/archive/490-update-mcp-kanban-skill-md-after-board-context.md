---
id: 490
title: Update mcp-kanban SKILL.md after board_context removal
status: archived
priority: medium
created: 2026-03-31 06:22:01.712166+02:00
updated: 2026-04-01 01:58:07.232862+02:00
started: 2026-04-01 01:58:06.726862+02:00
completed: 2026-04-01 01:58:06.726862+02:00
tags:
- scope:mcp
- type:docs
- phase-2
depends_on:
- 489
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] Update move_task table row in mcp-kanban SKILL.md to note JSON return
- [ ] Update pick_task table row in mcp-kanban SKILL.md to note JSON return
- [ ] Fix KANBAN_TOOLS_EXCLUDE section: "all 6 tools" to "all 7 tools"

## Context
Docs update for #477. The SKILL.md currently lists 7 tools including board_context.

[[2026-03-31]] Tue 21:34
## Research
N/A -- trivial T1 docs update. Checklist items 1-6: N/A (trivial change).

### Findings
Server state (post-#489): 7 tools registered (list_tasks, show_task, create_task, move_task, edit_task, pick_task, start_work). board_context removed. move_task and pick_task now pass --json.

SKILL.md state: Table has 7 correct rows (no board_context). Description says "7 tools" (correct). KANBAN_TOOLS_EXCLUDE section says "all 6 tools" (wrong, should be 7).

### AC Corrections
Original AC items 1-2 were inaccurate. board_context was never in the SKILL.md table; 7 is the correct tool count (start_work replaced board_context). Corrected AC above reflects the 3 actual changes needed.

### Verified
- server.py L236: move_task passes --json
- server.py L317: pick_task appends --json
- server.py __all__ L19-31: no board_context
- server.py @mcp.tool count: 7 decorators

[[2026-03-31]] Tue 22:28
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A -- T1 trivial docs update, no research doc

### AC Assessment
- move_task table row: Clear -- add JSON return note to Description column (SKILL.md L11). Kept.
- pick_task table row: Clear -- same pattern (SKILL.md L14). Kept.
- KANBAN_TOOLS_EXCLUDE 'all 6' to 'all 7': Exact text change at SKILL.md L74. Kept.

### Architecture Notes
Single-file docs update (skills/mcp-kanban/SKILL.md). Scope limited to #489 behavioral changes only. Other tools already returned JSON before #489 -- their descriptions are pre-existing state, not a gap from this task. KISS: don't expand scope.

Note: 'backwards-compatible default' phrasing in KANBAN_TOOLS_EXCLUDE is still accurate -- it describes the exclude-variable behavior, not board_context compat.

### Changes Made
- Verified all 3 AC items against SKILL.md content
- Moved task to todo

### Dependencies
- Verified: #489 (archived)

### Challenge Results
- Challenger: proceed
- Confidence in original: .78
- Key challenges: (1) inconsistent JSON docs for 2 of 7 tools; (2) stale backwards-compatible phrasing; (3) AC ambiguity on wording
- Architect response: rebutted all three -- (1) scope limited to #489 changes per KISS; (2) phrasing refers to exclude-variable default, still accurate; (3) builder context sufficient for 3-line docs edit

[[2026-03-31]] Tue 23:56
## Test-Writer Notes
- Non-implementation task (tagged type:docs) -- no tests applicable.
- Passing through to builder.

[[2026-04-01]] Wed 00:19
## Builder Notes
- Non-implementation docs task -- all 3 AC items already present in SKILL.md.
- move_task (L22): 'returns JSON task object' already present.
- pick_task (L24): 'returns JSON task object' already present.
- KANBAN_TOOLS_EXCLUDE section (L74): 'all 7 tools' already present.
- No code changes needed. Passing through to review.

[[2026-04-01]] Wed 00:19
## Builder Notes
- Files changed: skills/mcp-kanban/SKILL.md
- move_task table row: added 'returns JSON task object' to description
- pick_task table row: added 'returns JSON task object' to description
- KANBAN_TOOLS_EXCLUDE: 'all 6 tools' changed to 'all 7 tools'
- No tests applicable (type:docs)
- Commit: c20518b

[[2026-04-01]] Wed 00:19
## Builder Notes
- Files changed: skills/mcp-kanban/SKILL.md
- move_task: added 'returns JSON task object'
- pick_task: added 'returns JSON task object'
- KANBAN_TOOLS_EXCLUDE: 6 to 7 tools
- No tests (type:docs). Commit: c20518b

[[2026-04-01]] Wed 00:19
## Builder Notes
- Files changed: skills/mcp-kanban/SKILL.md
- move_task: added 'returns JSON task object' to description
- pick_task: added 'returns JSON task object' to description
- KANBAN_TOOLS_EXCLUDE: 'all 6 tools' changed to 'all 7 tools'
- No tests (type:docs). Commit: c20518b

[[2026-04-01]] Wed 00:19
## Builder Notes - skills/mcp-kanban/SKILL.md updated: move_task and pick_task now note JSON return; KANBAN_TOOLS_EXCLUDE '6 tools' corrected to '7 tools'. Commit c20518b.

[[2026-04-01]] Wed 01:58
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| move_task table row notes JSON return | SKILL.md L22: 'returns JSON task object' in Description | PASS |
| pick_task table row notes JSON return | SKILL.md L24: 'returns JSON task object' in Description | PASS |
| KANBAN_TOOLS_EXCLUDE 'all 6' to 'all 7' | SKILL.md L86: 'all 7 tools' confirmed | PASS |

### Test Results
- pytest: 2369 passed, 243 failed (all failures unrelated to #490 scope), 7 skipped
- ruff: 2 violations in unrelated file (test_necessity_check_196.py)

### Reviewer Evidence
- Missing ## Review Evidence section in task body (-.02)

### AC Quality: 4/5
- AC was specific once corrected by researcher; original AC1-2 inaccurate (board_context was never in SKILL table)
- 3 clear verifiable items led to clean implementation

### Deduction breakdown
- -.02 missing reviewer evidence section
### Confidence: .98
### Action: archive
