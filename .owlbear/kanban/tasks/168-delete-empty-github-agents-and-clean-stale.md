---
id: 168
title: Delete empty .github/agents/ and clean stale settings
status: archived
priority: important
created: 2026-03-29T19:49:32.5532584+02:00
updated: 2026-03-29T20:41:37.2836416+02:00
started: 2026-03-29T20:41:37.2836416+02:00
completed: 2026-03-29T20:41:37.2836416+02:00
tags:
    - phase-1
    - scope:docs
    - type:build
class: standard
---

## Objective
Remove the empty .github/agents/ directory and clean up stale references in settings files.

## AC
- [ ] Delete .github/agents/ directory (confirmed empty)
- [ ] Remove .github/agents entry from .vscode/settings.json chat.agentFilesLocations
- [ ] Remove .github/agents mapping from scripts/setup.py L35
- [ ] Remove .github/instructions mapping from scripts/setup.py L42
- [ ] Verify setup.py tests still pass

## Context
See docs/research/github-v1-cleanup.md sec 3.
