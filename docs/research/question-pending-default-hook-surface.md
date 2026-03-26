# question_pending Default Hook Surface

> **Owning task:** #962 - Remove dead question_pending default hook configuration
> **Date:** 2026-03-23 **Status:** Complete

## 1. Context and Question

Task #962 asks whether OwlBear should keep `question_pending` in default
notification and HookReaction example surfaces when `src/` defines the enum
value but does not emit it anywhere at runtime. The decision also needs a scope
boundary: remove only the dead default surface, or remove the enum and
synthetic coverage too. [S1, S2, S5, S6]

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Prefect events docs | .90 | Event definitions and automations that trigger on observed matching events |
| S2 | Prefect automations docs | .90 | Trigger/action model tied to event occurrence, including notification actions |
| S3 | Celery signals guide | .85 | Signal lists and handlers attached to concrete dispatched lifecycle signals |
| S4 | GitHub Actions event triggers docs | .80 | Supported trigger/activity tables and unsupported-event notes for runtime-triggered workflows |
| S5 | OwlBear `src/owlbear/config.py`, `src/owlbear/core/hooks.py`, `src/owlbear/core/notification_hook.py`, `src/owlbear/tools/ask_user.py`, `src/owlbear/safety/gate.py`, and `src/owlbear/daemon.py` | 1.0 | Current default config, enum, registration seam, actual emit sites, and missing human-wait emitters |
| S6 | OwlBear `docs/research/hookreaction-schema-router-wiring.md`, `docs/research/typed-hook-payloads.md`, `docs/research/notification-hook.md`, and `docs/architecture.md` | 1.0 | Prior research and docs showing how `question_pending` became user-facing despite no current emitter |

## 3. Analysis

### 3.1 Current OwlBear state

| Finding | Evidence | Impact |
|---------|----------|--------|
| `notification_events` still defaults to `task_complete`, `question_pending`, `on_error` | `config.py` default list and matching config tests. [S5] | Default notifications promise a human-wait event that runtime code does not currently produce. [S1, S2, S5] |
| `HookEvent.QUESTION_PENDING` exists, but `src/` has no `emit(HookEvent.QUESTION_PENDING, ...)` site | `core/hooks.py` defines the enum; `daemon.py`, `agent.py`, `hooked.py`, and `gate.py` emit other events only. [S5] | Registration succeeds, but the default handler is dead by construction. [S1, S3, S5] |
| The real human-wait boundaries are `AskUserToolset` and `ApprovalGateToolset` | Both send prompts and await `channel.receive()` without emitting `QUESTION_PENDING`. [S5] | If OwlBear wants this event later, these are the concrete seams to instrument. [S2, S5] |
| Documentation and tests still normalize the dead surface | Prior docs call `QUESTION_PENDING` a NotificationHook event, and typed-payload research already marks it as not yet emitted. [S5, S6] | The codebase currently mixes available enum member with live default event. [S5, S6] |

### 3.2 Option comparison

| Option | Benefits | Risks | Verdict |
|--------|----------|-------|---------|
| Keep `question_pending` in defaults and examples | Zero code churn today | Leaves user-facing config and examples attached to an event that never fires; prior-art systems attach automations only to emitted or supported events. [S1, S2, S3, S4] | Reject |
| Remove it from defaults and example surfaces, keep the enum for now | Smallest diff, fixes misleading defaults, and preserves low-level hook compatibility while scope stays on #962. [S1, S2, S5, S6] | Leaves one inert enum member and synthetic coverage in place until a later task resolves it. [S5, S6] | Best |
| Remove the enum and all synthetic coverage immediately | Eliminates the dead symbol entirely | Expands scope into hook API churn, observability tests, and historical docs without being required to fix the false default. [S3, S5, S6] | Too wide for #962 |

### 3.3 Recommended test posture

| Test seam | Why |
|-----------|-----|
| Static or source-inspection test: default notification events are a subset of events actually emitted in `src/` | Prevents future dead defaults from landing again. [S1, S4, S5] |
| Bootstrap default-registration test: default `build_hooks()` registers notification handlers only for live default events | Confirms the user-visible default wiring matches the config surface. [S2, S5] |
| Preserve generic enum and registry tests for `QUESTION_PENDING` until a later task either emits it or deletes it | Keeps #962 surgical instead of turning it into a public hook API cleanup. [S3, S5, S6] |

## 4. Recommendation (.93 confidence)

- Remove `question_pending` from `OwlBearSettings.notification_events` defaults
  and any HookReaction or architecture examples that are meant to show live
  runtime defaults. [S1, S2, S5, S6]
- Keep `HookEvent.QUESTION_PENDING` for now. The enum member is inert, but
  removing it now is broader API cleanup than the task requires. [S3, S5, S6]
- Reintroduce `question_pending` only when OwlBear emits it from a real
  human-wait seam, not as speculative configuration. `AskUserToolset` and
  `ApprovalGateToolset` are the correct future emitters. [S2, S5, S6]
- Add one regression test that derives or inventories live emit sites, so dead
  default events fail before they become user-facing examples again. [S1, S4, S5]

## 5. Follow-up Tasks

1. #967 - Emit `QUESTION_PENDING` from AskUserToolset and ApprovalGateToolset.
   Priority rationale: restores the event only when OwlBear has a real
   human-wait producer instead of keeping a misleading default today.
   Dependencies: #962.
   One-line AC: `AskUserToolset` and `ApprovalGateToolset` emit
   `HookEvent.QUESTION_PENDING` immediately before awaiting human input, with
   tests proving `NotificationHook` and `ObservabilityHook` receive the live
   event without reintroducing dead defaults.
   Created:

   ```powershell
   kanban\kanban-md.exe create "Emit QUESTION_PENDING from AskUserToolset and ApprovalGateToolset" --priority important --status ideation --parent 955 --depends-on 962 --tags "agent,hooks,ask_user,approval,scope:core,type:build" --body "See docs/research/question-pending-default-hook-surface.md section 5. AC: AskUserToolset and ApprovalGateToolset emit HookEvent.QUESTION_PENDING immediately before awaiting human input, with tests proving NotificationHook and ObservabilityHook receive the live event without reintroducing dead defaults."
   ```
