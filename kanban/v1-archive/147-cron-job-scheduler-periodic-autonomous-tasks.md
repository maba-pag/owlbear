---
id: 147
title: Cron job scheduler — periodic autonomous tasks
status: ideation
priority: someday
created: 2026-02-27T14:59:53.7566789+01:00
updated: 2026-03-21T13:18:29.995062+01:00
started: 2026-03-01T20:09:00.7665231+01:00
tags:
    - daemon
    - phase-14
depends_on:
    - 124
blocked: true
block_reason: 'Research gap: recurring automation model conflicts with existing prompt-runner, deterministic-service, board-SOP, and human-gated patterns.'
class: standard
---

Schedule recurring tasks: knowledge graph updates (re-crawl sources), codebase health checks (run tests, lint), upstream update scanning, analytics aggregation.

Simple cron-like scheduling stored in config. The daemon (bearclaw run) checks the schedule and triggers agent tasks. Each scheduled task is just a prompt sent to the appropriate agent.

[[2026-03-21]] Sat 13:18
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Schedule recurring tasks: knowledge graph updates, codebase health checks, upstream update scanning, analytics aggregation | Bundles multiple product areas with different execution models. Knowledge refresh already has a deterministic orchestrator, recurring audits already use board-driven SOPs, and analytics is a separate human-gated feature area. | Return to research; split or redefine after a single recurring-work model is chosen. |
| Simple cron-like scheduling stored in config | Vague and currently conflicts with the concrete recurring-SOP pattern already on the board (for example #579), where schedule metadata lives with the task rather than in OwlBearSettings. No config schema or scheduling semantics are specified. | Research and specify one source of truth for recurring schedules. |
| The daemon (bearclaw run) checks the schedule and triggers agent tasks | Missing precise integration with run_daemon() and its existing TaskGroup-managed periodic runners. It does not say whether this is a new runner, a poll_loop extension, or a reuse of heartbeat-style behavior. | Research and rewrite with explicit lifecycle and interface boundaries. |
| Each scheduled task is just a prompt sent to the appropriate agent | Conflicts with existing deterministic APIs and governance. Knowledge refresh should reuse RefreshOrchestrator, recurring audits already create board subtasks, and #146 explicitly says self-improvement remains human-gated and never autonomous. | Research the execution model before implementation. |

### Architecture Notes
- Existing periodic behavior is already split by execution model:
  - src/owlbear/heartbeat.py runs prompt-driven agent turns.
  - src/owlbear/memory/knowledge/refresh.py exposes deterministic refresh operations.
  - kanban task #579 stores recurring audit schedule and execution protocol on the board.
- src/owlbear/daemon.py already wires heartbeat, consolidation, and autonomous poll_loop as separate runners. A new recurring system must define which pattern it extends instead of blending all three.
- The only existing agent explicitly described as periodic maintenance is curator. The other examples in this task do not map cleanly to existing autonomous agent surfaces.
- Dependency #124 is satisfied, but the controlling blocker is architectural: the task needs research that chooses between config-driven prompt scheduling, deterministic service scheduling, and board-driven recurring SOPs.

### Changes Made
- Claimed #147 as architect-147
- Appended an architecture review documenting the recurring-work model conflict
- Moved #147 from backlog to ideation and blocked it pending research on recurring execution model

### Dependencies
- Verified: #124 is archived and sufficient as the daemon prerequisite
- Reviewed patterns: src/owlbear/daemon.py, src/owlbear/heartbeat.py, src/owlbear/memory/knowledge/refresh.py, task #146, task #579
