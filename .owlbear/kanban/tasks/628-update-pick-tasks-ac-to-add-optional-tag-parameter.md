---
id: 628
title: Update pick_tasks AC to add optional tag parameter
status: ideation
priority: needed
created: 2026-04-05T10:41:53.2291189+02:00
updated: 2026-04-05T10:41:53.2291189+02:00
tags:
    - scope:mcp
    - phase-2
    - type:build
parent: 619
depends_on:
    - 621
class: standard
---

## Acceptance Criteria

- #621 AC updated: tool signature becomes `pick_tasks(limit: int = 25, tag: str | None = None) → dict`
- `tag` parameter passed through to `_run_kanban` as `--tag {value}` when not None
- Default `None` preserves zero-config semantics
- #619 architecture decision body updated to reflect the tag parameter
- #620 test design updated if tests assume no tag parameter

## Context

Research (.owlbear/research/wire-pick-tasks-orchestrator.md §3.3) found that the orchestrator needs tag-based scope filtering for user commands like "Orchestrate: phase-2". Without a tag parameter, pick_tasks returns all eligible tasks and the orchestrator can't filter without 25 show_task calls.

T2 advisory — modifies the "zero-config" design principle from #619. The tag param is a minimal _run_kanban passthrough, not orchestrator logic leaking into the tool.
