# Non-Blocking Retrospective Hook Handoff

> **Owning task:** #964 — Keep TASK_COMPLETE retrospective scheduling non-blocking before background handoff
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

`RetrospectiveHook.__call__` is awaited inline by `HookRegistry.emit()` [S5].
Before handing work to the `HookWorkerSupervisor`, it calls two blocking
methods on the awaited path: `_count_rejections()` (synchronous file I/O
parsing `activity.jsonl`) [S4 L201-229] and `_get_priority()` (synchronous
`subprocess.run()` shelling out to `kanban-md show --json`) [S4 L231-250].
These block both the event loop and the hook emission pipeline.

The question: what is the smallest change that moves all metadata lookup behind
the supervisor handoff, keeping `__call__` instant?

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Python `asyncio.to_thread` docs | .95 | Official guidance for offloading blocking I/O to thread pool without blocking the event loop |
| S2 | Python `asyncio.create_subprocess_exec` docs | .93 | Async subprocess API; precedent for non-blocking subprocess in asyncio |
| S3 | OwlBear `context_hook.py` (`_read_instructions`, `_run_kanban`) | 1.0 | Existing OwlBear pattern: `asyncio.to_thread` for file read [L87], `create_subprocess_exec` for kanban-md [L101] |
| S4 | OwlBear `retrospective_hook.py` | 1.0 | Current blocking implementation: `_count_rejections` [L201], `_get_priority` [L231], `__call__` [L162] |
| S5 | OwlBear `hooks.py` `HookRegistry.emit()` | 1.0 | Emit semantics: handlers awaited in order; slow handler blocks all subsequent handlers [L275-282] |
| S6 | OwlBear `hook_worker_supervisor.py` | 1.0 | Supervisor `schedule()` is non-blocking (creates task + returns) [L39-59] |
| S7 | OwlBear `board_context.py` `_fetch_board_state()` | .90 | Additional `create_subprocess_exec` precedent for kanban-md [L85] |
| S8 | aiohttp background tasks docs | .85 | Tracked background task + cleanup context pattern; confirms handler-to-task handoff as standard |

## 3. Analysis

### 3.1 Approach comparison

| Criterion | A: Move eligibility into bg task (.85) | B: A + async I/O in bg task (.75) | C: Keep eligibility in `__call__` + async I/O (.55) |
|-----------|---------------------------------------|----------------------------------|-----------------------------------------------------|
| `__call__` returns instantly | Yes | Yes | No — still awaited during file read + subprocess |
| AC satisfied | Yes — metadata off awaited path | Yes | No — metadata still on awaited path |
| Event loop blocked (bg task) | Briefly (~100ms for I/O + subprocess) | No | N/A |
| KISS alignment | Highest — smallest diff | Medium — adds async conversions | Low — changes calling convention, more complex |
| New dependencies | None | None (stdlib only) | None |
| Wasted bg tasks for filtered work | Minor — eligibility check is fast | Minor | None |
| Existing precedent | `_LazyCoroutine` + `supervisor.schedule()` already used [S4, S6] | `context_hook.py` patterns [S3, S7] | No direct precedent |
| Testability | Straightforward: mock supervisor, assert `schedule()` called, verify no sync I/O in `__call__` | Same + verify async APIs used | Complex: must verify awaited path timeline |

### 3.2 Behavioral impact of Approach A

With `Semaphore(1)`, moving eligibility into the background task means
ineligible tasks briefly occupy the semaphore slot [S6]. Impact is negligible:
`TASK_COMPLETE` events are infrequent (one per completed kanban task),
eligibility checks are fast (~100ms total), and the expensive agent run
(seconds) dominates [S4 L252]. [S1, S6]

### 3.3 Event loop health consideration

Approach A still does synchronous file I/O and `subprocess.run()` inside the
background task, which blocks the event loop thread for ~100ms per invocation.
For a daemon with sub-second responsiveness goals, this is borderline
acceptable but worth addressing. [S1, S3]

However, wrapping the sync calls in `asyncio.to_thread` / replacing with
`create_subprocess_exec` inside the background task is a separate,
incremental improvement that can follow as Approach B. YAGNI applies: the
current daemon handles one conversation at a time, so a 100ms event-loop
block during background retrospective eligibility is not a practical issue
today. [S1, S5, S6]

## 4. Recommendation (.85 confidence)

**Approach A: Move eligibility checks into the background task.**

1. Restructure `__call__` to only validate `outcome == "success"` and
   `task_id` non-empty, then immediately `supervisor.schedule()` (or
   `create_task()` fallback). No file I/O or subprocess calls remain on the
   awaited path. [S4, S5, S6]
2. Create a new async wrapper (e.g. `_run_with_eligibility(task_id)`) that
   calls `_count_rejections` and `_get_priority` before
   `_run_retrospective`. If the task is ineligible, return early. [S4]
3. Tests must prove: (a) `__call__` does not call `_count_rejections` or
   `_get_priority` directly, (b) the scheduled background work does call
   them, (c) ineligible tasks are still filtered (just inside the bg task).

**Risk:** A 100ms event-loop block inside the background task from sync I/O.
Acceptable for current single-conversation daemon; if multi-conversation
support lands, follow up with `to_thread`/`create_subprocess_exec` wrapping.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Move RetrospectiveHook eligibility checks behind supervisor handoff" --priority needed --status ideation --depends-on 953 --tags "agent,daemon,hooks,scope:core,type:build" --body "AC:\n1. RetrospectiveHook.__call__ must not call _count_rejections or _get_priority on the awaited hook path.\n2. A new async wrapper (e.g. _run_with_eligibility) runs eligibility checks plus _run_retrospective inside the background task.\n3. Tests must prove: (a) __call__ returns before any file I/O or subprocess call, (b) eligibility filtering still works (ineligible tasks filtered inside bg task), (c) existing cancellation and supervisor integration behavior preserved.\n4. Files: src/owlbear/core/retrospective_hook.py, tests/test_retrospective_hook.py.\nSee docs/research/non-blocking-retrospective-hook-handoff.md for analysis."
```
