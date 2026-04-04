---
id: 596
title: 'Fix planner skill language: reconcile "does NOT claim" with end_work usage'
status: backlog
priority: nice-to-have
created: 2026-04-04T20:09:51.968555+02:00
updated: 2026-04-04T23:07:39.0300945+02:00
tags:
    - phase-2
    - ' scope:agent-config'
    - ' type:fix'
class: standard
---

## Acceptance Criteria

- [ ] w-task-decomposition/SKILL.md L15 revised from "does NOT claim a task" to language reflecting the actual behavior (claims parent task when dispatched, creates children)
- [ ] L92 `end_work` reference consistent with revised L15
- [ ] No functional changes to planner behavior

## Context

Research doc: docs/research/rescope-575-lifecycle-blocks.md (section 3e)
w-task-decomposition L15 says "does NOT claim a task" but L92 references `end_work` to "release the claim." The planner IS dispatched from the board via orchestrator and needs to claim. The language describes task-creation intent, not operational reality.

## Files

.github/skills/w-task-decomposition/SKILL.md

## Research
Research complete. Validation pass on existing docs/research/rescope-575-lifecycle-blocks.md section 3e.

Finding: L15 describes task-creation intent, not operational reality. Planner IS dispatched from board via orchestrator and needs to claim. Fix: replace 'does NOT claim' with conditional language, add start_work call for dispatch mode.

Classification: T1 autonomous. Confidence: .95

[[2026-04-04]] Sat 23:07
Research complete (.95). T1 autonomous fix: reconcile claim language in w-task-decomposition L15 with L94 end_work. Validation pass on existing research doc.
