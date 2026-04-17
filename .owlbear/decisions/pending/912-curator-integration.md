# Curator Pipeline Integration Pattern

**Task:** #912 — Test lifecycle management  
**Decision needed by:** User  
**Created:** 2026-04-17

## Context

The test-curator agent processes task-scoped test files post-archive — promoting contract-level assertions to durable module-level files and removing transient scaffolding. The curator must **never gate** the next task dispatch.

The question: **how does the curator get invoked?**

## Options

### (a) Parallel dispatch

The orchestrator dispatches the test-curator alongside non-test-touching agents immediately after archiving a task. The curator runs in parallel with the next task's researcher/architect phase.

| Dimension | Assessment |
|-----------|------------|
| **Latency** | Low — curation starts immediately after archive |
| **Complexity** | Medium — orchestrator needs dispatch logic for post-archive agents |
| **Interference risk** | Low — curator touches only `tests/` files; next task's researcher/architect don't touch tests |
| **Conflict window** | Moderate — if the next task reaches test-writer before curator finishes, both touch `tests/`. Curator writes `test_{module}.py`, test-writer writes `test_{module}_{task_id}.py` — different files, no conflict. |

### (b) Queue-based

The curator maintains its own work queue (e.g., a file listing archived task IDs). A separate process or manual trigger processes the queue periodically.

| Dimension | Assessment |
|-----------|------------|
| **Latency** | Variable — depends on trigger frequency |
| **Complexity** | High — requires queue infrastructure, separate trigger mechanism |
| **Interference risk** | Lowest — fully decoupled from pipeline |
| **Conflict window** | None — runs on its own schedule |

### (c) Archive-triggered

The orchestrator auto-dispatches the curator immediately when `end_work` archives a task. Synchronous but non-blocking (fire and forget).

| Dimension | Assessment |
|-----------|------------|
| **Latency** | Lowest — immediate |
| **Complexity** | Low — single dispatch call in orchestrator's archive handler |
| **Interference risk** | Same as (a) |
| **Conflict window** | Same as (a) |

### (d) Separate orchestrator cycle

A dedicated curator cycle runs after N archives accumulate (e.g., every 5 tasks). The orchestrator checks the archive count and dispatches the curator in its own orchestration pass.

| Dimension | Assessment |
|-----------|------------|
| **Latency** | Medium — up to N tasks of delay |
| **Complexity** | Low — counter + threshold check |
| **Interference risk** | Low — runs during a natural pause |
| **Conflict window** | Low — batched processing reduces overlap probability |

## Recommendation

Option **(c) Archive-triggered** for simplicity: add a single `dispatch(test-curator, task_id)` call to the orchestrator's archive path. Non-blocking, immediate, minimal infrastructure. Fall back to **(d) Separate orchestrator cycle** if testing shows interference.

## Decision

_Pending user input._
