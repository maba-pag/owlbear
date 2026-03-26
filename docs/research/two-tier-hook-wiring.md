# Two-Tier NotificationHook Wiring in build_hooks()

> **Owning task:** #979 — Wire two-tier NotificationHook instances in build_hooks
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #979 requires `build_hooks()` to create two `NotificationHook` instances — an urgent tier (slack+sound+bell) and an info tier (bell only) — using config fields from #977. The parent research validated two-tier routing (.82 confidence) [S1]. This doc covers three implementation concerns: (1) backend name → instance resolution, (2) dedup coordination with #963, and (3) reaction router backend selection.

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | `docs/research/priority-routed-notifications.md` | 1.0 | Parent research: Option A two-tier design, .82 confidence |
| S2 | Grafana notification policies docs | .90 | Routing tree maps severity labels to contact points; each policy has its own receiver chain |
| S3 | Python `logging` module (Handlers section) | .85 | Different handlers per severity level — "send error+ to stdout, critical to email" is the canonical two-tier pattern |
| S4 | `docs/research/notify-dedup-notificationhook-vs-router.md` | 1.0 | Option A1: assembly-time exclusion of unconditional notify events |
| S5 | `src/owlbear/bootstrap/hooks.py` | 1.0 | Current single-tier wiring; `_make_notify_executor` shares backend list |
| S6 | `src/owlbear/core/notification_hook.py` | 1.0 | `SlackNotificationBackend(bot_token, channel_id)` constructor |
| S7 | `src/owlbear/config.py` | 1.0 | `slack_bot_token: SecretStr`, `slack_channel_id: str`; #977 will add tier fields |
| S8 | `docs/research/two-tier-notification-config.md` | 1.0 | Config field design: `_KNOWN_BACKENDS`, tier field defaults |

## 3. Analysis

### 3.1 Backend Name Resolution

Current `build_hooks()` hard-codes `[ConsoleBellBackend(), WinSoundBackend()]`. The new tier config uses string names (`["slack", "sound", "bell"]`). A name→instance mapping is needed. [S5, S7, S8]

| Option | Description | KISS | Extensibility | Verdict |
|--------|-------------|:----:|:-------------:|---------|
| A. Inline dict in build_hooks | `{"bell": ConsoleBellBackend(), ...}` — resolve per tier | High | Low (add to dict) | **Recommend** |
| B. Registry/factory module | Separate module with `get_backend(name)` | Med | High | Reject (YAGNI — 3 backends) |
| C. Keep hard-coded lists | Ignore config backend names | High | None | Reject (defeats config purpose) |

Option A: build a `_backend_pool` dict once, then select per tier. `SlackNotificationBackend` takes `bot_token` and `channel_id` from `settings`; returns `False` gracefully when tokens are `None`. [S6, S7]

```
pool = {
    "bell": ConsoleBellBackend(),
    "sound": WinSoundBackend(),
    "slack": SlackNotificationBackend(
        bot_token=settings.slack_bot_token.get_secret_value() if settings.slack_bot_token else None,
        channel_id=settings.slack_channel_id,
    ),
}
urgent_backends = [pool[n] for n in settings.notification_urgent_backends if n in pool]
info_backends = [pool[n] for n in settings.notification_info_backends if n in pool]
```

Unknown names silently skip (validated at config time by `_KNOWN_BACKENDS` from #977). [S8]

### 3.2 Dedup Coordination with #963

# 979's AC includes: "events configured under hook_reactions with notify action are excluded from both tiers." #963's AC implements assembly-time exclusion for the single legacy tier. These overlap. [S4, S5]

| Sequencing | Description | Rework Risk | Verdict |
|------------|-------------|:-----------:|---------|
| A. #963 first, #979 extends | #963 adds helper; #979 applies it to both tiers | Low — helper survives, call site changes | **Recommend** |
| B. #979 absorbs #963 | #979 implements dedup from scratch for both tiers; #963 closed as dup | None | Viable but larger scope |
| C. Independent | Both implement separately | High — duplicate logic | Reject |

**Option A (.85 confidence)**: #963 extracts a `_reaction_covered_events(reactions)` helper returning `set[str]` of events covered by unconditional notify rules. #979 calls it once and filters both tier event lists. The helper is ~5 lines; the call-site change in #979 is trivial. Add `depends_on: [977, 963]` to #979. [S4]

### 3.3 Reaction Router Backend Selection

The `_make_notify_executor(backends)` builds the reaction router's notify chain. Currently it uses the same backends as the single `NotificationHook`. With two tiers, a choice is needed. [S5]

| Option | Backends | Rationale | Verdict |
|--------|----------|-----------|---------|
| A. Urgent backends | Full chain (slack+sound+bell) | Reaction rules are user-configured, likely important | **Recommend** |
| B. All backends merged | Union of both tier chains | Over-notifies | Reject |
| C. New config field | `notification_reaction_backends` | YAGNI | Reject |

Urgent tier backends are the natural choice — they represent the highest-fidelity notification path. If a user configures a reaction with `notify`, they expect the full channel. [S2, S3]

### 3.4 Implementation Sketch (~25 lines in build_hooks)

1. Build `_backend_pool` dict from known backend classes + Slack settings
2. Resolve urgent backends and info backends from config fields
3. Call `_reaction_covered_events()` (from #963) to get excluded event set
4. Filter urgent events and info events, removing excluded
5. Register urgent `NotificationHook` (if events remain)
6. Register info `NotificationHook` (if events remain)
7. Pass urgent backends to `_make_notify_executor()`

### 3.5 Testing Strategy

| Test Case | Assertion |
|-----------|-----------|
| Urgent tier fires on urgent event | Urgent backends called; info backends not called |
| Info tier fires on info event | Info backends called; urgent backends not called |
| Dedup exclusion applied to both | Excluded event triggers neither tier |
| Empty tier (all excluded) | No handler registered for that tier |
| No hook_reactions (backward compat) | Both tiers register all their events |
| Slack tokens absent | SlackNotificationBackend returns False, chain falls through |
| Unknown backend name in config | Silently skipped (config validator prevents this) |

## 4. Recommendation (.85 confidence)

Implement two-tier wiring (Option A from §3.1, A from §3.2, A from §3.3):

1. Build backend pool dict with name→instance mapping. Slack tokens from `settings`. [S6, S7]
2. Resolve tier backends from config string lists. [S8]
3. Use #963's `_reaction_covered_events()` helper for dedup on both tiers. [S4]
4. Pass urgent backends to reaction router's notify executor. [S5]
5. Add `depends_on: [977, 963]` to #979.

Risks:

| Risk | Severity | Mitigation |
|------|----------|------------|
| #977 not yet landed (config fields missing) | Blocking | Hard dependency; cannot implement without tier fields |
| SlackNotificationBackend constructed even when Slack unused | Low | Returns False immediately when tokens absent [S6] |
| Reaction router notify chain differs from all tiers | Low | Matches Grafana pattern: explicit routing uses full contact point [S2] |

## 5. Follow-up Tasks

AC refinement for #979 (execute below). No new tasks needed — existing #977 and #963 cover prerequisites.
