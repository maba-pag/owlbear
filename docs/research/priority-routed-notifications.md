# Priority-Routed Notifications for Daemon and Pipeline Events

> **Owning task:** #952 — Add priority-routed notifications for daemon and pipeline events
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

OwlBear's `NotificationHook` treats all events the same — one backend chain (bell → sound), first-success semantics, no severity differentiation. Task #952 asks: classify events by priority and route urgent events differently from informational events across CLI and Slack channels. The Ruflo analysis (#947, section 3.4) identified this as a medium-value pattern worth adapting once workers and reactions increase event volume. [S1, S5, S6]

Key questions:
1. How do alerting systems route notifications by severity?
2. What priority tiers suit OwlBear's event set?
3. How should priority routing integrate with the existing `NotificationHook` + `HookReactionRouter`?
4. What new backends are needed (Slack, toast)?

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Grafana notification policies | .90 | Label-based routing tree, severity matching to contact points, inheritance, mute timings |
| S2 | Prefect automations | .85 | Trigger + action model, notification blocks (Slack, Teams, Email), template-driven messages |
| S3 | OwlBear `src/owlbear/core/notification_hook.py` | 1.0 | Current backend chain, first-success semantics, event filtering |
| S4 | OwlBear `src/owlbear/core/hook_reaction_router.py` | 1.0 | Config-driven event+match routing with injected executors (currently noop) |
| S5 | OwlBear `docs/research/ruflo-analysis.md` | 1.0 | Priority-routed notifications identified as a medium-value adaptation pattern |
| S6 | OwlBear `docs/research/notification-hook.md` | 1.0 | Prior research: backend priority chain, toast libs, config design, SlackNotificationBackend recommended |
| S7 | OwlBear `docs/research/hookevent-reaction-routing.md` | 1.0 | HookReactionRouter design, notify/retry/escalate delegation, dedup concern (#963) |
| S8 | OwlBear `src/owlbear/bootstrap/hooks.py` | 1.0 | Current wiring: single NotificationHook, HookReactionRouter with noop executors |

## 3. Analysis

### 3.1 OwlBear Event Priority Classification

| Event | Default Priority | Rationale |
|-------|:----------------:|-----------|
| `on_error` | urgent | Runtime failure needs immediate user attention [S3, S6] |
| `budget_warning` | urgent | Cost threshold crossed — user must decide to continue [S3, S6] |
| `question_pending` | urgent | Daemon is blocked waiting for user input [S3, S6] |
| `task_complete` | info | Task finished normally — informational only [S3, S6] |
| `daemon_startup` | info | Daemon started — no action required [S3] |
| `session_start` | silent | Internal lifecycle — no notification [S3] |
| `session_end` | silent | Internal lifecycle — no notification [S3] |

### 3.2 Design Options

| Option | Description | KISS | Integration Cost | Verdict |
|--------|-------------|:----:|:----------------:|---------|
| A. Two-tier config with separate NotificationHook instances | `notification_urgent_events` + `notification_info_events` in config; `build_hooks()` creates two hooks with different backend chains | High | Low — extends existing pattern, no new types | **Recommend** |
| B. Priority field on HookReactionRule match | Route via `match: {priority: "urgent"}` in reaction rules; add priority to event payloads | Medium | Medium — requires payload changes across all emit sites | Reject (YAGNI) |
| C. Grafana-style routing tree | Label matchers, child policies, inheritance | Low | High — far too complex for 11 events | Reject |
| D. Single hook with per-backend event filter | Each `NotificationBackend` declares which event priorities it handles | Medium | Medium — protocol change | Reject (over-design) |

### 3.3 Option A Detail (.82 confidence)

Config additions to `OwlBearSettings`:

```
notification_urgent_events: list[str] = ["on_error", "budget_warning", "question_pending"]
notification_urgent_backends: list[str] = ["slack", "sound", "bell"]
notification_info_events: list[str] = ["task_complete"]
notification_info_backends: list[str] = ["bell"]
```

`build_hooks()` wires two `NotificationHook` instances — one for urgent (Slack → sound → bell), one for informational (bell only). The existing `notification_events` + `notification_backends` fields become the urgent tier (backward-compatible rename). [S3, S6, S8]

### 3.4 New Backend Requirements

| Backend | Needed For | Exists? | Dependency | Effort |
|---------|-----------|---------|------------|--------|
| `SlackNotificationBackend` | Urgent tier — phone push | No | `slack_sdk` (already in stack) | ~40 LOC |
| `WindowsToastBackend` | Urgent tier — desktop toast | No | `windows-toasts` (optional extra) | ~50 LOC |
| `ConsoleBellBackend` | Info tier — always available | Yes | None | 0 |
| `WinSoundBackend` | Urgent tier — system sound | Yes | None (stdlib) | 0 |

The Slack backend wraps `channel.send()` from an injected `ChannelPlugin` reference when the active channel is Slack—or uses `AsyncWebClient` directly when Slack tokens are configured but the active channel is CLI. This avoids coupling `NotificationHook` to the bidirectional channel contract. [S3, S6]

### 3.5 Deduplication with HookReactionRouter (#963)

Task #963 already tracks the concern that `notify` actions from `HookReactionRouter` could double-fire alongside `NotificationHook`. Priority routing must coordinate: if a `HookReactionRule` includes `notify` for an event, the tier-based `NotificationHook` should yield. The simplest approach: when `hook_reactions` include any rule with `notify` for a given event, `build_hooks()` excludes that event from both tier lists. This keeps dedup at the wiring layer, not the runtime. [S4, S7, S8]

### 3.6 Interaction with Existing Tasks

| Task | Relationship | Impact |
|------|:------------:|--------|
| #955 | Prerequisite satisfied | Schema + router landed; noop executors in place |
| #957 | Sibling — wires real executors | Priority routing's Slack backend could be the `notify` executor for #957 |
| #963 | Sibling — dedup concern | Priority routing wiring must respect dedup boundary |

## 4. Recommendation (.82 confidence)

Implement two-tier priority routing (Option A) with a `SlackNotificationBackend`:

1. Add `notification_urgent_events`, `notification_urgent_backends`, `notification_info_events`, and `notification_info_backends` to `OwlBearSettings`. Deprecate the flat `notification_events`/`notification_backends` by mapping them as the urgent tier default. [S3, S6, S8]
2. Implement `SlackNotificationBackend` in `notification_hook.py` — inject Slack tokens from config, send via `AsyncWebClient`. Keep it independent of `ChannelPlugin` to avoid coupling notification delivery to the active I/O channel. [S3, S6]
3. Wire two `NotificationHook` instances in `build_hooks()` — urgent and info tier, each with its own backend chain and event list. [S8]
4. Defer `WindowsToastBackend` to a separate optional-extra task — it adds a pywinrt dependency and is lower priority than Slack. [S6]

Risks:
| Risk | Severity | Mitigation |
|------|----------|------------|
| Slack backend adds coupling to `config.py` Slack tokens | Low | Backend returns `False` when tokens missing — transparent fallthrough |
| Notification fatigue from too many urgent events | Medium | Default urgent list is narrow (3 events); user-configurable |
| Dedup race with #957/#963 | Low | #963 tracks this; wiring-layer exclusion keeps it simple |

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Add two-tier priority notification config to OwlBearSettings" --priority important --status ideation --parent 952 --depends-on 955 --tags "config,hooks,scope:core,type:build" --body "See docs/research/priority-routed-notifications.md. AC: add notification_urgent_events, notification_urgent_backends, notification_info_events, and notification_info_backends fields to OwlBearSettings with backward-compatible defaults; validate backend names; deprecate flat notification_events/notification_backends by mapping them to the urgent tier."

kanban\kanban-md.exe create "Implement SlackNotificationBackend" --priority important --status ideation --parent 952 --tags "hooks,slack,scope:core,type:build" --body "See docs/research/priority-routed-notifications.md. AC: add a SlackNotificationBackend class satisfying NotificationBackend protocol that sends via AsyncWebClient using injected Slack tokens from config; returns False when tokens are missing; includes message formatting with event label and task context; tested with mocked AsyncWebClient."

kanban\kanban-md.exe create "Wire two-tier NotificationHook instances in build_hooks" --priority important --status ideation --parent 952 --depends-on 955 --tags "hooks,bootstrap,scope:core,type:build" --body "See docs/research/priority-routed-notifications.md. AC: build_hooks() creates two NotificationHook instances (urgent tier with slack+sound+bell, info tier with bell only) using the new OwlBearSettings fields; events configured under hook_reactions with notify action are excluded from both tiers to avoid double-delivery (#963); tested with both tiers firing independently."
```
