---
id: 679
title: Add cleanup policy for .owlbear/scratch directory
status: backlog
priority: someday
created: 2026-04-08T18:35:53.3462402+02:00
updated: 2026-04-08T18:35:53.3462402+02:00
tags:
    - scope:ops
    - ' type:chore'
    - ' source:analysis'
class: standard
---

## Context

`.owlbear/scratch/` contains 500+ temp files (diagnostic scripts, test outputs, board scans, dispatch plans) spanning task IDs #1–#996. No cleanup mechanism exists. Files grow without bounds.

## Acceptance Criteria

- [ ] AC1: Add a cleanup mechanism that removes scratch files older than 30 days
- [ ] AC2: Mechanism should be invokable manually (not automatic) — e.g. a script or curator subtask
- [ ] AC3: Cleanup preserves files from the last 30 days to maintain recent debugging context
- [ ] AC4: `.owlbear/scratch/` is gitignored (verify — if not, add it)
