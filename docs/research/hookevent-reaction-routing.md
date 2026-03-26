# HookEvent Reaction Routing

> **Owning task:** #950 - Implement config-driven HookEvent reaction routing with retry and escalation
> **Date:** 2026-03-23 **Status:** Complete

## 1. Context and Question

Task #950 asks for a config seam that routes HookEvent-triggered reactions into
notify, retry, or escalate behaviors with bounded retries and clear failure
routing. OwlBear already has those three behaviors, but each one lives in a
different runtime boundary: NotificationHook handles user alerts,
`reconcile_tasks()` handles bounded task retries, and `LoopDetector` handles
user escalation after repeated failures. The missing capability is therefore a
shared policy surface that composes those executors without turning HookRegistry
into a blocking control plane. [S5, S6, S7, S8]

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Prefect automations docs | .95 | Trigger plus action model, traced action failures, inferred targets, and notification actions |
| S2 | Prefect create automations guide | .95 | YAML/JSON automation schema showing explicit trigger and ordered actions |
| S3 | Celery task guide | .90 | Retry/backoff options, lifecycle handlers, and exhausted-retry behavior |
| S4 | Celery signals guide | .90 | Signal-based lifecycle observation and retry/failure events |
| S5 | OwlBear architecture standards | 1.0 | Hooks are observational, config belongs in config.py, and bootstrap owns cross-layer wiring |
| S6 | OwlBear `src/owlbear/core/hooks.py`, `src/owlbear/core/notification_hook.py`, `src/owlbear/bootstrap/hooks.py`, and `tests/test_notification_hook.py` | 1.0 | Real HookRegistry behavior plus current notification filtering and backend fallthrough |
| S7 | OwlBear `src/owlbear/config.py`, `src/owlbear/daemon.py`, and `tests/test_poll_dispatch.py` | 1.0 | Existing retry settings, exponential backoff, budget-exceeded bypass, and block-on-exhaustion behavior |
| S8 | OwlBear `src/owlbear/orchestrator/loop_detection.py` and `tests/test_loop_detection.py` | 1.0 | Existing escalation threshold and retry/skip/stop channel contract |

## 3. Analysis

### 3.1 What OwlBear already has

| Action | Current owner | What it already does | Gap |
|--------|---------------|----------------------|-----|
| `notify` | `NotificationHook` plus `build_hooks()` | Filters configured event names, tries backends in order, and logs backend failure without propagating it. [S5, S6] | Only supports event-name filtering; no shared policy layer chooses actions per event or payload. [S1, S2] |
| `retry` | `config.py` plus `reconcile_tasks()` | Applies bounded retries, exponential backoff, budget-exceeded bypass, and block-on-exhaustion for failed builder tasks. [S3, S7] | Only exists in the daemon's task-failure path; other hook events cannot reuse it declaratively. [S1, S4] |
| `escalate` | `LoopDetector` | Counts repeated failures and asks the user to retry, skip, or stop through the active channel. [S4, S8] | No hook-facing policy surface decides when escalation should follow a lifecycle event. [S1, S2] |
| Policy composition | Missing | OwlBear already has action executors. [S6, S7, S8] | No shared config decides which event and payload combinations should invoke which executor chain. [S1, S2] |

A good implementation should therefore reuse executors, not replace them. [S1,
S5, S7, S8]

### 3.2 Router placement options

| Option | Benefits | Risks | Verdict |
|--------|----------|-------|---------|
| Put routing inside `HookRegistry.emit()` | Smallest apparent diff | `emit()` awaits handlers, swallows exceptions, and the architecture standard explicitly says hooks are observational rather than blocking control flow. [S3, S5, S6] | Reject |
| Add a standalone `HookReactionRouter` wired from `bootstrap/hooks.py` | Matches Prefect's trigger-plus-actions shape, keeps config centralized, and allows protocol-based executor injection. [S1, S2, S5] | Requires a thin new router type and bootstrap wiring. [S5, S6] | Best |
| Keep adding direct conditionals at each call site | No new router type | Repeats policy across notification, daemon retry, and escalation paths, making drift likely and validation harder. [S1, S7, S8] | Reject |

### 3.3 Recommended model (.89 confidence)

- Add a new config model, preferably `hook_reactions: list[HookReactionRule] = []`, where each rule names explicit `events`, optional payload matchers such as `outcome == "failure"`, an ordered `actions` list, and an `on_failure` policy. Reuse event value strings instead of changing the `HookEvent` enum; Prefect's automation model uses explicit trigger/action objects and OwlBear already configures notifications by event name string. [S1, S2, S6]
- Implement a small `HookReactionRouter` as a normal hook handler registered from `bootstrap/hooks.py`. It should not live inside `HookRegistry`, and it should receive executor protocols via dependency injection so `core/` does not import `daemon.py` or `loop_detection.py`. [S5, S6, S7, S8]
- Treat actions as delegation only:
  - `notify` delegates to the existing notification backend chain, preserving first-success behavior and graceful backend fallthrough. [S1, S6]
  - `retry` delegates only when the payload is task-scoped and already supported by OwlBear's retry engine; it must keep `task_retry_max_attempts`, `task_retry_backoff_base`, and `task_retry_backoff_max` as the single source of truth. [S3, S5, S7]
  - `escalate` delegates to the existing retry/skip/stop channel-facing escalation behavior instead of inventing new escalation verbs. [S1, S4, S8]

### 3.4 Clear failure routing

| Failure case | Recommended behavior | Why |
|--------------|----------------------|-----|
| Unsupported rule or impossible action at startup | Fail validation and refuse registration. [S2, S5, S7] | `config.py` is the single source of truth, so invalid routing should fail early instead of becoming silent runtime drift. [S2, S5] |
| Notification backend failure | Preserve backend fallthrough; if all backends fail, log once and stop. [S1, S6] | OwlBear already has safe notification failure behavior, so the router should reuse it instead of wrapping another retry loop around it. [S5, S6] |
| Retry action cannot apply or exhausts budget | Reuse daemon behavior: budget exceeded blocks immediately, exhausted retries block the task, and missing task context should escalate rather than silently retry. [S3, S7, S8] | This preserves one retry engine and one set of terminal states. [S3, S7] |
| Escalation channel failure | Preserve the current safe fallback to skip/log. [S4, S8] | LoopDetector already defines this fallback, so the router should not invent a second failure path. [S4, S8] |
| Router or executor exception | Log once and stop; do not recursively emit `HookEvent.ON_ERROR` from the router. [S5, S6] | Changing HookRegistry error semantics would violate the observational-hook contract and risks reaction loops. [S5, S6] |

### 3.5 Scope recommendation

Initial scope should stay narrow: `task_complete`, `question_pending`,
`on_error`, and `budget_warning` are enough to prove the routing seam. Anything
richer than explicit event/payload matching would be premature; OwlBear does not
yet need a generic workflow DSL. [S1, S2, S6, S7]

## 4. Recommendation (.89 confidence)

Implement #950 as a thin policy-and-delegation layer, not a new executor
subsystem.

1. Keep `HookRegistry` unchanged and best-effort. [S5, S6]
2. Add validated reaction rules in `config.py` and wire a standalone router from `bootstrap/hooks.py`. [S1, S2, S5]
3. Reuse the existing notification, retry, and escalation executors through injected protocols. [S3, S5, S6, S7, S8]
4. Split delivery into schema/router, retry reuse, and notification/escalation integration so each task has one primary concern. [S5, S7, S8]

## 5. Follow-up Tasks

1. #955 - Define HookReaction policy schema and bootstrap router wiring.
   Priority rationale: unlocks a single policy surface without changing HookRegistry semantics.
   Dependencies: none.
   One-line AC: add validated `hook_reactions` config models plus a bootstrap-wired router that matches events and delegates to injected action executors without blocking HookRegistry.
   Created:

   ```powershell
   kanban\kanban-md.exe create "Define HookReaction policy schema and bootstrap router wiring" --priority important --status ideation --parent 950 --tags "agent,hooks,config,scope:core,type:build" --body "See docs/research/hookevent-reaction-routing.md section 5. AC: add validated hook_reactions config models plus a bootstrap-wired router that matches events and delegates to injected action executors without changing HookRegistry semantics."
   ```

2. #956 - Reuse daemon retry state for task-scoped HookReaction retries.
   Priority rationale: preserves one retry engine and keeps retry bounds in existing settings.
   Dependencies: #955.
   One-line AC: task-scoped failure reactions delegate to the existing retry scheduler and block-on-exhaustion path, continuing to honor `task_retry_max_attempts` and backoff settings instead of introducing new retry counters.
   Created:

   ```powershell
   kanban\kanban-md.exe create "Reuse daemon retry state for task-scoped HookReaction retries" --priority important --status ideation --parent 950 --depends-on 955 --tags "agent,hooks,daemon,scope:core,type:build" --body "See docs/research/hookevent-reaction-routing.md section 5. AC: task-scoped failure reactions delegate to the existing retry scheduler and block-on-exhaustion path, continuing to honor task_retry_max_attempts and backoff settings instead of introducing new retry counters."
   ```

3. #957 - Route HookReaction notification and escalation actions through existing executors.
   Priority rationale: keeps human-facing behavior aligned with current notification and loop-detection semantics.
   Dependencies: #955.
   One-line AC: route notify through configured notification backends and escalate through the existing channel-facing escalation path, with startup validation and non-recursive failure handling tests.
   Created:

   ```powershell
   kanban\kanban-md.exe create "Route HookReaction notification and escalation actions through existing executors" --priority important --status ideation --parent 950 --depends-on 955 --tags "agent,hooks,orchestrator,scope:core,type:build" --body "See docs/research/hookevent-reaction-routing.md section 5. AC: route notify through configured notification backends and escalate through the existing channel-facing escalation path, with startup validation and non-recursive failure handling tests."
   ```
