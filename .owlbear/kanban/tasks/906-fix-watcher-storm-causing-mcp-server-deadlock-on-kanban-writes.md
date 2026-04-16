---
id: 906
title: fix watcher storm causing MCP server deadlock on kanban writes
status: done
priority: critical
created: 2026-04-16T23:45:01.418957+00:00
updated: 2026-04-16T23:45:01.418957+00:00
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