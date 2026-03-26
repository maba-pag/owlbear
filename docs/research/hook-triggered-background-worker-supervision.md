# Hook-Triggered Background Worker Supervision

> **Owning task:** #953 - Add tracked background worker supervision for hook-triggered daemon tasks
> **Date:** 2026-03-23 **Status:** Complete

## 1. Context and Question

Task #953 is already the implementation follow-up from #949, so the question is
now narrow: what is the smallest supervision abstraction that keeps hook-spawned
daemon work owned, bounded, and cleanly shut down without turning
`HookRegistry` into a queue runner. OwlBear currently has one fire-and-forget
hook consumer (`RetrospectiveHook`) and one owned-background-task precedent
(`GraphEnricher`), so this task is about lifecycle fit more than feature
discovery. [S1, S4, S5, S7]

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Python asyncio task docs | .98 | Strong-reference guidance for `create_task()`, `TaskGroup` lifecycle, cancellation, and timeout behavior |
| S2 | Python asyncio sync docs | .95 | `Semaphore` and `Event` semantics for bounded concurrency and cooperative shutdown |
| S3 | aiohttp advanced docs | .88 | Tracked background-task cleanup and graceful shutdown patterns for long-lived async work |
| S4 | OwlBear `src/owlbear/core/retrospective_hook.py` and `tests/test_retrospective_hook.py` | 1.0 | Current fire-and-forget hook behavior, existing `shutdown_event` cancel seam, and current test surface |
| S5 | OwlBear `src/owlbear/core/hooks.py` | 1.0 | Hook emission semantics: handlers are awaited sequentially and failures are swallowed |
| S6 | OwlBear `src/owlbear/bootstrap/__init__.py`, `src/owlbear/bootstrap/_types.py`, `src/bearclaw/commands/daemon.py`, and `src/bearclaw/commands/chat.py` | 1.0 | Existing bootstrap cleanup registration and where shutdown callbacks are actually invoked |
| S7 | OwlBear `src/owlbear/memory/knowledge/enrichment.py` | .97 | Existing owned background-task set plus semaphore pattern already used in OwlBear |
| S8 | OwlBear `src/owlbear/daemon.py` | .93 | Shared shutdown-event and in-flight task cancellation patterns used during daemon teardown |

## 3. Analysis

### 3.1 Constraints already visible in OwlBear

| Constraint | Evidence | Impact |
|-----------|----------|--------|
| Hook handlers are awaited inline | `HookRegistry.emit()` awaits coroutine handlers in order, and `RetrospectiveHook.__call__` currently does eligibility work before it hands work off. [S4, S5] | The hook callback itself must stay short; slow work belongs behind a background handoff. [S3, S5] |
| Fire-and-forget tasks need ownership | Python warns that the loop keeps only weak task references, and `GraphEnricher` already keeps a task set plus discard callbacks. [S1, S7] | #953 needs an owned `set[Task]` and completion cleanup, not bare `create_task()`. [S1, S4] |
| Shutdown already has a cleanup seam | `BootstrapResult.cleanup` is invoked by both chat and daemon commands, and aiohttp recommends tracked background tasks that are cancelled or awaited during cleanup. [S3, S6] | The supervisor should expose a drain or cancel API that plugs into existing cleanup, not invent a second app-lifecycle system. [S3, S6] |
| Concurrency is already modeled with semaphores | Python documents `Semaphore` for bounded async access, and `GraphEnricher` already uses `async with self._bg_semaphore`. [S2, S7] | Use `Semaphore`, not ad hoc counters or a worker thread pool. [S2, S7] |

### 3.2 Supervisor shape options

| Option | Benefits | Risks | Verdict |
|--------|----------|-------|---------|
| Inline task-set logic inside `RetrospectiveHook` | Smallest local diff for today's single hook. [S4] | Duplicates lifecycle code when #954 adds another worker path and spreads cleanup plumbing across hook classes. [S4, S6, S7] | Too local |
| Reusable small supervisor object owning task set, semaphore, and shutdown | Matches Python task-ownership guidance and OwlBear's existing enrichment pattern while giving #953 and #954 one lifecycle surface. [S1, S2, S6, S7] | Adds one extra type. [S4, S7] | Best |
| Queue plus fixed worker pool | Strong backpressure and explicit worker loop ownership. [S2, S3] | YAGNI for one current hook and one pilot consumer; introduces queue lifecycle and error-handling states not required by the AC. [S3, S4, S7] | Overbuilt |
| Long-lived `asyncio.TaskGroup` | Structured wait-on-exit semantics. [S1] | `TaskGroup` is an async context manager, closes when inactive, and cancels siblings on first failure; that is awkward for long-lived observational hooks that should isolate failures. [S1, S5] | Reject |

### 3.3 Shutdown wiring options

| Option | Benefits | Risks | Verdict |
|--------|----------|-------|---------|
| Pass `shutdown_event` only | Reuses the existing per-operation cancel signal that retrospective ingestion already composes. [S4, S8] | Does not keep strong task references or guarantee a drain; cancellation stays purely cooperative. [S1, S4] | Insufficient alone |
| Register cleanup callback only | Deterministic teardown through `BootstrapResult.cleanup` with no daemon API change. [S3, S6] | Running work does not see shutdown intent until cleanup begins. [S1, S8] | Good but incomplete |
| Supervisor drain in bootstrap cleanup plus optional `shutdown_event` into work | Gives explicit ownership and wait-on-shutdown while preserving early cooperative cancel for in-flight work. [S1, S3, S4, S6, S8] | Slightly more plumbing. [S4, S6] | Best |

### 3.4 Testing scope for #953

- Keep the proof at the hook and bootstrap seam, not only daemon end-to-end:
  task ownership, `Semaphore` gating, cleanup cancel/drain, and
  `RetrospectiveHook` integration are the behavioral contract. [S2, S4, S6, S7]
- Preserve the existing `cancel=` composition behavior already asserted by the
  retrospective tests instead of replacing it with a new cancellation channel.
  [S1, S4]
- Do not widen #953 into a queue subsystem, retry engine, or multi-worker
  catalog. The pilot research already reserved those broader concerns for #954
  and later work. [S3, S4]

## 4. Recommendation (.92 confidence)

- Add one small reusable supervisor in `owlbear.core` rather than embedding task
  ownership directly inside `RetrospectiveHook`. Give it task-set ownership,
  `Semaphore`-bounded scheduling, and an async shutdown method that can cancel
  and/or drain outstanding tasks. [S1, S2, S6, S7]
- Keep `RetrospectiveHook.__call__` as eligibility filter plus supervisor
  handoff only. `HookRegistry.emit()` should remain observational and unchanged.
  [S4, S5]
- Wire the supervisor into OwlBear's existing bootstrap cleanup list, and keep
  the existing per-operation `cancel=` signal for ingest work when shutdown is
  already known. That uses the app lifecycle OwlBear already has instead of
  inventing another one. [S3, S4, S6, S8]
- Default hook-worker concurrency to `Semaphore(1)`. That satisfies the AC,
  matches the earlier pilot recommendation, and avoids queue machinery until the
  audit-map worker proves a real throughput need. [S2, S4, S7]
- Treat `TaskGroup` as the wrong default here. Its context-managed lifetime and
  fail-fast sibling cancellation are a better fit for nested subtasks than for
  independently emitted hook work. [S1, S5]

## 5. Risks and Follow-up Findings

| Finding | Why it matters | Action |
|---------|----------------|--------|
| `RetrospectiveHook.__call__` still reads `activity.jsonl` and shells out to `kanban-md show --json` before background handoff. [S4, S5] | Even after #953, `TASK_COMPLETE` emission would remain partly blocking, and that cost becomes more visible once #954 adds another worker consumer. | Create #964 to move retrospective eligibility metadata lookup behind a non-blocking seam. |

## 6. Follow-up Tasks

1. #964 - Keep TASK_COMPLETE retrospective scheduling non-blocking before background handoff.
   Priority rationale: preserves daemon responsiveness once #953 and #954 add
   supervised worker paths.
   Dependencies: #953.
   One-line AC: `RetrospectiveHook.__call__` must hand work off without
   synchronous `activity.jsonl` parsing or `kanban-md show` subprocess calls on
   the awaited hook path, with tests proving the metadata lookup happens behind
   a non-blocking seam.
   Created:

   ```powershell
   kanban\kanban-md.exe create "Keep TASK_COMPLETE retrospective scheduling non-blocking before background handoff" --priority important --status ideation --parent 953 --depends-on 953 --tags "agent,daemon,hooks,scope:core,type:build" --body "See docs/research/hook-triggered-background-worker-supervision.md section 5. AC: RetrospectiveHook.__call__ must hand work off without synchronous activity.jsonl parsing or kanban-md show subprocess calls on the awaited hook path, with tests proving the metadata lookup happens behind a non-blocking seam."
   ```
