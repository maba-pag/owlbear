# HookReaction Notify and Escalate Executor Wiring

> **Owning task:** #957 — Route HookReaction notification and escalation actions through existing executors
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

Task #957 replaces the noop `notify` and `escalate` executors in
`bootstrap/hooks.py` with real implementations that delegate to existing
OwlBear systems. The `HookReactionRouter` (from #955) already supports
injected executor protocols — the question is how to wire them. [S1, S2]

## 2. Sources Studied

| ID  | Source | Relevance | What |
|-----|--------|:---------:|------|
| S1  | OwlBear `src/owlbear/core/notification_hook.py` | 1.0 | `NotificationBackend` protocol and first-success backend chain |
| S2  | OwlBear `src/owlbear/core/hook_reaction_router.py` | 1.0 | Router executor protocol: `Callable[[dict[str, Any]], Any]` |
| S3  | OwlBear `src/owlbear/bootstrap/hooks.py` | 1.0 | Current noop wiring and `build_hooks()` signature (receives `channel`) |
| S4  | OwlBear `src/owlbear/orchestrator/loop_detection.py` | 1.0 | `LoopDetector.escalate()` — interactive send+receive via channel |
| S5  | OwlBear `src/owlbear/core/hooks.py` | 1.0 | `HookRegistry.emit()` — sequential, awaits handlers, swallows exceptions |
| S6  | OwlBear architecture standards (SKILL.md) | 1.0 | Hooks are observational, not blocking control flow |
| S7  | Prefect automations docs | .95 | Trigger→action model; `send-notification` action delegates to backends |
| S8  | Celery signals guide | .90 | Signal handlers receive `**kwargs`; separate from retry engine state |

## 3. Analysis

### 3.1 Notify executor options

| Option | Approach | Pros | Cons | Score |
|--------|----------|------|------|:-----:|
| A | Reuse `NotificationHook.__call__()` as executor | Zero new code | Double-filters events (router + hook both filter); confusing config (user must set both `notification_events` AND `hook_reactions`) [S1, S5] | .55 |
| B | Factory taking `list[NotificationBackend]` | First-success chain preserved; no double-filtering; ~15 LOC [S1, S7] | Creates backends list twice (once for NotificationHook, once for executor) | .85 |
| C | Direct `channel.send()` | Simplest | Skips backend chain; no bell/sound distinction [S1] | .45 |

### 3.2 Escalate executor options

| Option | Approach | Pros | Cons | Score |
|--------|----------|------|------|:-----:|
| A | Wrap `LoopDetector.escalate()` | Reuses full interactive flow | Blocks hook pipeline (send+receive); violates "hooks are observational" [S4, S5, S6]; creates separate LoopDetector state from daemon's instance | .40 |
| B | `channel.send()` notification-only | Non-blocking; preserves hook contract [S6, S8]; ~10 LOC | No interactive response — user must act through existing daemon escalation | .80 |
| C | Schedule via `HookWorkerSupervisor` | Full async escalation | Needs supervisor injection in `build_hooks()`; shared LoopDetector state; YAGNI [S6] | .50 |

### 3.3 Startup validation

| What | How | Source |
|------|-----|--------|
| `notify` backends non-empty | Assert in factory at bootstrap | [S1, S3] |
| `escalate` channel present | If `channel is None`, log warning and use noop | [S3, S4] |
| Event string resolution | Already handled by `register()` raising `ValueError` | [S2] |

### 3.4 Failure handling (already solved)

The router's `_make_handler()` catches each executor exception, logs it,
and continues to the next action without re-emitting `ON_ERROR`. [S2, S6]
Tests should verify this contract holds for real executors.

## 4. Recommendation (.85 confidence)

**Notify:** Option B — backend-chain factory. Create a `_make_notify_executor(backends)` function in `bootstrap/hooks.py` that returns an async callable iterating backends in first-success order. Matches the `NotificationHook` pattern without double-filtering. [S1, S7]

**Escalate:** Option B — channel.send() only. Create a `_make_escalate_executor(channel)` function that sends an escalation alert message. The daemon's `LoopDetector` retains ownership of interactive escalation. [S4, S6, S8]

**Retry:** Leave as noop. That's #956's scope.

**Wiring:** Replace the noop dict in `build_hooks()` with factory-produced executors, using the `settings` and `channel` parameters already available. [S3]

### Risk: Backend lifecycle

Both executors capture references at bootstrap time. If a backend or channel
becomes unavailable later, the executor will fail and the router will log+swallow. This is acceptable — the same failure mode exists in `NotificationHook` today. [S1, S5]

## 5. Follow-up Tasks

No additional tasks needed. #957 is atomic and the analysis above provides
sufficient implementation guidance. The AC should be refined to:

> Replace noop `notify` executor with backend-chain factory and noop `escalate`
> executor with channel.send()-based factory in `bootstrap/hooks.py`. Leave
> `retry` as noop (#956). Startup: warn if escalate has no channel. Tests:
> real executor wiring, backend fallthrough, channel.send() delegation,
> failure isolation, non-recursive ON_ERROR.

Files scoped: `src/owlbear/bootstrap/hooks.py`, tests.
