---
id: 906
title: fix watcher storm causing MCP server deadlock on kanban writes
status: archived
priority: medium
created: 2026-04-16T23:45:01.418957+00:00
updated: 2026-04-17T00:46:04.618134+00:00
tags:
- mcp
- stability
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Problem

`end_work()` writes to 3 files in `.owlbear/kanban/` sequentially (task file, archive move, activity log). VS Code file watcher fires for each change. The watcher event storm can freeze the renderer, which stops reading from the MCP server's stdout pipe. The pipe buffer fills, and `sys.stdout.write()` blocks — deadlock.

## Fix

1. Add `files.watcherExclude` with `.owlbear/kanban/**` to `.vscode/settings.json` and `seed/.vscode/settings.json` — breaks the watcher event chain.
2. Add missing `flush()` call in `activity_log.py` after `write()` — matches documented design spec.

## AC

- [ ] `files.watcherExclude` contains `.owlbear/kanban/**` in both settings files
- [ ] `activity_log.py` calls `f.flush()` after `f.write()`
- [ ] Existing activity log tests pass
[[2026-04-17]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| files.watcherExclude in .vscode/settings.json | L85: ".owlbear/kanban/**": true | PASS |
| files.watcherExclude in seed/.vscode/settings.json | L83: ".owlbear/kanban/**": true | PASS |
| activity_log.py calls f.flush() after f.write() | activity_log.py L31-32: f.write(...) then f.flush() | PASS |
| Existing activity log tests pass | 103 passed, 0 failed (scoped: test_actor_field_activity_log_811,_812, test_kanban_engine_activity_wiring_728, test_audit_wiring_164) | PASS |

### Test Results

- pytest (scoped): 103 passed, 0 failed, exit 0. activity_log module 100% coverage.
- pytest (full): hung on xdist worker teardown (exit 143, SIGTERM). Infrastructure issue (PluggyTeardownRaisedWarning: OSError "cannot send already closed"), not a task regression.
- ruff (task files): clean, exit 0
- ruff (full): 2 pre-existing violations in unrelated scope_transfer.py (S608, RUF100)

### Architect Quality: 4/5

Specific, verifiable AC with clear problem/fix causation chain. Minor gap: no explicit AC for "no pre-existing regressions" but covered by implicit test-pass requirement.

### Deduction Breakdown

- Missing reviewer evidence section: -.02
- All AC lines verified with specific evidence: no deduction
- Lint clean on task scope: no deduction
- Full suite xdist hang: infrastructure issue, not task-scoped — no deduction

### Confidence: .98

### Action: archive
