---
id: 584
title: 'Research: openai/symphony'
status: archived
priority: important
created: 2026-03-05T23:50:29.3138583+01:00
updated: 2026-03-07T18:08:08.3972022+01:00
started: 2026-03-06T21:12:52.0403902+01:00
completed: 2026-03-07T18:08:08.3972022+01:00
tags:
    - research
    - phase-research
    - scope:agent
parent: 580
class: standard
---

**Source:** https://github.com/openai/symphony (Apache-2.0)
Analyzed for multi-agent delegation, orchestration patterns, and task execution logic.

**Research doc:** See docs/research/symphony.md

**Key findings:**
- Poll-dispatch-reconcile daemon pattern (poll tick -> reconcile running -> validate -> fetch candidates -> sort -> dispatch)
- Workspace isolation per task with lifecycle hooks
- Continuation turns: re-check task state after completion, send continuation prompt
- Exponential backoff retry at task level: min(10000 * 2^(attempt-1), max_backoff_ms)
- Reconciliation: stall detection + state refresh each tick
- WORKFLOW.md: YAML front matter config + Liquid template prompt
- ExecPlan (PLANS.md): self-contained living execution documents

**Recommendation (.85 confidence):** Adopt poll-dispatch-reconcile as OwlBear autonomous mode. Skip workspace isolation (single-repo), Linear adapter, HTTP dashboard.

**Follow-up tasks:** 4 kanban tasks proposed in docs/research/symphony.md S5

**Research checklist:**
- [x] Theoretical validity - Sound, proven at OpenAI scale (1500+ PRs)
- [x] Prior art - 3 sources (Symphony repo, Harness Engineering blog, Codex ExecPlans)
- [x] Technical feasibility - Python asyncio + PydanticAI + kanban-md CLI, no blockers
- [x] Architecture fit - Extends existing run_daemon() loop, HookRegistry, BootstrapResult
- [x] Implementation approach - Documented in research doc S3.2 and S4
