---
id: 1005
title: 'Planner: add askQuestions tool + explicit mode prefix convention'
status: research
priority: important
created: 2026-04-18T21:54:25.167093+00:00
updated: 2026-04-18T21:54:25.167093+00:00
tags:
- type:improvement
- scope:agents
parent: 998
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Problem
planner.agent.md lacks `vscode/askQuestions` and has no explicit mode detection for user-invoked vs dispatch contexts. The current "parent task ID" detection is natural-language inference and unreliable (failed in #973).

## Changes Required
1. Add `vscode/askQuestions` to planner.agent.md tools list.
2. Replace the existing dual-mode detection with explicit mode prefix convention:
   - `Plan and create: #{id} — ...` → dispatch mode (claim task, auto-create subtasks)
   - `Plan: ...` (default) → user mode (present plan → askQuestions → create on approve)
3. Update the `<critical_rules>` execution mode section with the new prefix convention.
4. Document fallback: if mode unclear, default to approval mode (safe default).
5. Add `<examples>` showing both prefix patterns.

## Acceptance Criteria
- planner.agent.md has `vscode/askQuestions` in tools list.
- Execution mode section documents the explicit prefix convention with both modes.
- Default (no "and create" prefix) uses askQuestions for approval before creating tasks.
- "Plan and create" prefix skips approval and auto-creates.
- Fallback to approval mode when prefix is ambiguous.

## Affected Files
- `share/agents/planner.agent.md`

## Context
See `.owlbear/research/998-planner-askquestions-approval.md` for trade-off analysis.