---
id: 1734
title: Restore recent Cockpit tasks to board
status: archived
priority: medium
created: 2026-05-23T04:16:00+0200
updated: 2026-05-24T10:50:01.730844+02:00
tags:
  - cockpit-perfect-ui
  - scope:kanban-tasks
  - ux-feedback
  - task-metadata
  - kanban
parent:
depends_on: []
ac:
  - Verify recent Cockpit task files that should appear in Cockpit are absent
    from `/api/tasks`.
  - Convert malformed recent task metadata to the canonical board-visible field.
  - Preserve each task's existing status, evidence, and narrative content.
  - Verify Cockpit `/api/tasks` includes the restored recent task IDs.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## User Feedback Context
The user asked that tasks be created before work so they appear on the Kanban board. The #1733 screenshot sweep showed the Cockpit board still ending at #1727. API checks against a fresh Cockpit backend confirmed `/api/tasks` contains IDs 1677 through 1727 and omits #1728 through #1733.

## Evaluation Notes
- Classification: observed current workflow harm, not theoretical debt.
- Current harm: the board misses completed and active Cockpit polish work, so the Cockpit UI cannot be trusted as the task ledger for this session.
- Likely root cause: recent task files use `labels:` while board-visible Cockpit tasks use canonical `tags:` metadata.
- Product value: restoring the task ledger has higher value than another cosmetic pass because it makes subsequent screenshot sweeps and task tracking honest.

## Evidence Before Fix
- Fresh backend on `http://127.0.0.1:8425` reported `/api/tasks` count 51 with IDs `1677..1727` and no #1728-#1733.
- Screenshot evidence: `.owlbear/scratch/1716-wide-cockpit/1733-kanban-desktop.png` shows 51 done tasks and no active #1733 task.

## Evidence After Fix
- Converted recent task frontmatter from invalid priorities (`medium`, `high`) to configured priorities (`important`, `needed`) and from non-canonical `labels:` to board-visible `tags:` where present.
- Verified a fresh Cockpit backend on `http://127.0.0.1:8426` returned `/api/tasks` count 58 with IDs #1728 through #1734 present.
- Verified #1728, #1730, #1731, #1732, and #1733 preserve their existing statuses and evidence bodies.
- Current-data screenshot evidence: `.owlbear/scratch/1716-wide-cockpit/1733-kanban-desktop.png` now shows #1733 and #1734 in In Progress and reports 58 tasks.