---
id: 985
title: Wire real retry executor into HookReactionRouter
status: archived
priority: needed
created: 2026-03-24T03:57:49.8782613+01:00
updated: 2026-03-24T17:23:30.7171659+01:00
started: 2026-03-24T17:23:30.7171659+01:00
completed: 2026-03-24T17:23:30.7171659+01:00
tags:
    - daemon
    - hooks
    - bootstrap
    - scope:core
    - type:build
parent: 956
depends_on:
    - 984
class: standard
---

Create make_retry_executor factory in daemon.py and wire it into the HookReactionRouter executors dict via late-binding from run_daemon(). See docs/research/hook-reaction-retry-delegation.md section 4 steps 3-6. AC: (1) make_retry_executor(state, kanban, config) returns Executor, (2) build_hooks or BootstrapResult exposes the executors dict, (3) run_daemon replaces noop retry with real executor, (4) retry executor validates task_id presence and skips non-task-scoped events, (5) integration test: hook reaction with retry action schedules a RetryEntry in OrchestratorState, (6) edge case: budget-exceeded payload skips retry.

[[2026-03-24]] Tue 17:03

## Research

Research doc: docs/research/retry-executor-wiring.md

Key findings:

- Option C (HookRegistry.reaction_executors attribute) is simplest wiring path (.85 confidence)
- Budget-exceeded detection requires emitting outcome 'budget_exceeded' from reconcile_tasks
- Deduplication is already handled by schedule_task_retry idempotency
- make_retry_executor factory lives in daemon.py alongside schedule_task_retry

Follow-up tasks created at ideation:

- #991: Expose reaction_executors dict from build_hooks via HookRegistry attribute
- #992: Implement make_retry_executor and wire into run_daemon
- #993: Emit outcome budget_exceeded from reconcile_tasks for BudgetExceededError

Sources: Celery retry docs, Temporal failure detection, Prefect automations (same as parent #956 research)
Attribution: docs/sources/overview.md updated with #985 section

[[2026-03-24]] Tue 17:23

## Architecture Review

**Verdict:** SPLIT

### AC Assessment

AC1 make_retry_executor returns Executor: Valid, moved to #992.
AC2 build_hooks or BootstrapResult exposes executors dict: Valid, touches core/hooks.py and bootstrap/hooks.py, moved to #991.
AC3 run_daemon replaces noop retry with real executor: Valid, depends on AC2. Moved to #992.
AC4 retry executor validates task_id and skips non-task events: Valid, moved to #992.
AC5 integration test: Baked into impl task; needs TDD split at architecture review of #992. Moved to #992.
AC6 budget-exceeded payload skips retry: Valid, independent concern. Moved to #993.

### Architecture Notes

This task bundles three distinct responsibilities across two domains (core and bootstrap). The researcher correctly decomposed it into three atomic children with precise AC from docs/research/retry-executor-wiring.md.

Decomposition:

# 991 (core with ancillary bootstrap): HookRegistry.reaction_executors attribute plus build_hooks one-line assignment

# 992 (bootstrap): make_retry_executor factory plus run_daemon wiring, depends on #991

# 993 (bootstrap): reconcile_tasks budget_exceeded emission, independent

Option C (HookRegistry attribute) is architecturally sound: optional (None by default), router closures capture executors by reference, run_daemon accesses agent.hooks. No signature changes, no BootstrapResult changes. Module layering correct.

### Changes Made

Deleting #985 (scope fully covered by #991, #992, #993).
Advisory: #991 and #993 have depends_on 985 in YAML frontmatter. After deletion, a human or planner must manually remove the dangling reference. kanban-md edit does not support editing depends_on.

### Dependencies

Verified: #984 (extract schedule_task_retry) is done.
Children: #991, #992 (depends on #991), #993 (independent).
TDD advisory: each child will need preceding test tasks when reaching architecture review.
