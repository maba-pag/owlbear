# Hook-Triggered Background Worker Pilot

> **Owning task:** #949 - Design hook-triggered background worker pilot for audit map testgaps and document flows
> **Date:** 2026-03-23 **Status:** Complete

## 1. Context and Question

Task #949 asks for one safe OwlBear pilot for Ruflo-style `audit`, `map`,
`testgaps`, or `document` automation without bypassing OwlBear's daemon,
hook, or approval boundaries. OwlBear already has an always-on daemon,
`HookRegistry`, lifecycle notifications, and one live `TASK_COMPLETE`
background consumer, but it does not yet have a general-purpose worker
supervisor. [S1, S4, S5]

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | ruvnet/ruflo README | .90 | Worker catalog (`audit`, `map`, `testgaps`, `document`) and hook-driven daemon framing |
| S2 | Python asyncio task docs | .95 | `create_task()` lifecycle, strong-reference requirement, cancellation, and timeout guidance |
| S3 | Python asyncio sync docs | .90 | `Semaphore` and `Event` patterns for bounded concurrency and cooperative shutdown |
| S4 | OwlBear `src/owlbear/daemon.py`, `src/owlbear/core/hooks.py`, `src/owlbear/bootstrap/hooks.py` | 1.0 | Real emitted events, payload shape, and current daemon or hook boundaries |
| S5 | OwlBear `src/owlbear/core/retrospective_hook.py` and `tests/test_retrospective_hook.py` | 1.0 | Existing `TASK_COMPLETE` background precedent and its current fire-and-forget tradeoff |
| S6 | OwlBear `src/owlbear/memory/knowledge/enrichment.py` and `docs/research/cooperative-cancellation.md` | .95 | Tracked background-task ownership, semaphore gating, and explicit cancel or drain precedent |
| S7 | OwlBear `src/owlbear/safety/gate.py` and `docs/research/approval-gates.md` | 1.0 | Approval gates belong in tool wrappers, not in hook exception paths |
| S8 | OwlBear `src/owlbear/core/subagent_hook.py`, `src/owlbear/core/notification_hook.py`, and `docs/research/agent-orchestrator.md` | .90 | Advisory-output patterns and the gap between defined hook types and emitted production events |

## 3. Analysis

### 3.1 Trigger Fit In Today's Runtime

| Trigger | Fits today? | Why |
|---------|:-----------:|-----|
| `TASK_COMPLETE` | Yes | `reconcile_tasks()` emits it with `{task_id, outcome}` and OwlBear already uses it for retrospective and notification flows. [S4, S5] |
| `SUBAGENT_COMPLETE` | No | OwlBear defines the payload and registers a verification hook, but no production emitters were found in `src/**`, so a pilot here would start by adding new plumbing rather than exercising an existing seam. [S4, S8] |
| `POST_TOOL_USE` | Partial | It is real, but it is too low-level and too chatty for audit or map style work, and approval-related hooks already depend on it for a different concern. [S4, S7] |

`TASK_COMPLETE` is therefore the only currently emitted hook that is both
high-level enough for work-product analysis and already aligned to the kanban
pipeline. [S4, S5]

### 3.2 Candidate Pilot Comparison

| Pilot | Inputs available on `TASK_COMPLETE` | Pipeline ownership risk | Overall fit |
|-------|-------------------------------------|-------------------------|-------------|
| Audit-map advisory | Task body, activity log, review notes, and task outcome are all available now. [S1, S4] | Low if output stays advisory and scratch-only. [S7, S8] | Best |
| Test-gap advisory | Possible, but weak today because OwlBear does not emit changed-file or subagent artifact context on completion. [S4, S8] | Medium; likely to produce noisy guesses without richer payloads. [S1, S8] | Wait |
| Documentation draft | Inputs are available, but this overlaps the writer gate and invites unreviewed tracked-doc edits. [S1, S7] | High. [S7, S8] | Reject for pilot |
| Repo map refresh | Ruflo has stronger file-oriented worker triggers than OwlBear currently exposes. [S1, S8] | Medium; full rescans per task completion are hard to bound. [S3, S6] | Reject for pilot |

The safest high-value pilot is an audit-map advisory: generate a concise,
scratch-only report that helps reviewers or humans see task risks, likely follow-up
areas, and missing evidence without mutating kanban state or tracked docs. [S1, S7, S8]

### 3.3 Execution Model Comparison

| Model | Strengths | Gaps | Verdict |
|-------|-----------|------|---------|
| Await the whole worker inside the hook callback | Simple control flow | `HookRegistry.emit()` awaits handlers, so slow work directly delays daemon progress; failures are logged and swallowed, which is the wrong safety boundary for approval concerns. [S4, S7] | Reject |
| Bare `asyncio.create_task()` | Non-blocking and already used by `RetrospectiveHook`. [S5] | Python docs warn that fire-and-forget tasks need strong references; there is no concurrency bound or drain path. [S2, S5] | Accept only as precedent |
| Supervised task set + semaphore + timeout + shutdown cancel or drain | Matches Python guidance and OwlBear's `GraphEnricher` pattern; keeps the daemon responsive while preserving task ownership. [S2, S3, S6] | Small amount of new infrastructure. [S5, S6] | Recommend |

### 3.4 Recommended Pilot and Safety Gates (.88 confidence)

Recommend one `TASK_COMPLETE` audit-map advisory worker with these gates:

1. Trigger only on `HookEvent.TASK_COMPLETE` with `outcome == "success"`. This uses a real production event and avoids speculative worker launches on failed or partial work. [S4, S5]
2. Keep the pilot disabled by default and require explicit opt-in, preferably a dedicated task tag such as `worker:audit-map` plus a config flag. That keeps event volume predictable and makes the pilot easy to scope during rollout. [S1, S4]
3. Hand off eligible runs to a tiny supervisor that owns a background-task set, `Semaphore(1)`, timeout, and shutdown cancel or drain path. This fixes the lifecycle gap in bare fire-and-forget scheduling. [S2, S3, S6]
4. Limit outputs to one scratch artifact such as `docs/scratch/{task_id}-audit-map.md` and an optional channel notification that points to that artifact. This follows OwlBear's existing advisory-hook pattern without stealing ownership of tracked deliverables. [S4, S8]
5. Forbid board mutations, status moves, claims, tracked-doc edits, and source-code writes from the pilot. Anything that changes durable workflow state must stay behind the existing human or agent approval pipeline. [S4, S7]
6. Treat auto-created tasks, auto-authored permanent docs, and implementation-aware test-gap generation as non-goals for this pilot. Those need richer completion payloads and a separate product decision. [S1, S4, S8]

## 4. Recommendation (.88 confidence)

Build the audit-map advisory worker first.

- It is the only candidate that fits OwlBear's currently emitted event surface without inventing new completion plumbing. [S4, S5]
- It creates useful reviewer-facing context while staying safely advisory, which keeps approval-gated board and file ownership intact. [S7, S8]
- It can reuse OwlBear's proven background-task pattern from knowledge enrichment instead of copying Ruflo's broader worker catalog or adding a queueing subsystem prematurely. [S1, S2, S6]

Test-gap and document workers should wait until OwlBear emits richer completion
context and the pilot proves the supervision pattern in production. [S4, S6, S8]

## 5. Follow-up Tasks

1. #953 - Add tracked background worker supervision for hook-triggered daemon tasks.
   One-line AC: introduce a small supervisor for hook-spawned daemon work that keeps strong task references, bounds concurrency, exposes shutdown cancel or drain behavior, and migrates `RetrospectiveHook` off bare `asyncio.create_task()`. [S2, S5, S6]

2. #954 - Implement the `TASK_COMPLETE` audit-map advisory worker pilot.
   Depends on: #953.
   One-line AC: opt-in successful tasks can produce a scratch-only audit-map report and optional notification through the supervised worker path, with no board mutation, no tracked-doc edits, and no source writes. [S1, S4, S7, S8]
