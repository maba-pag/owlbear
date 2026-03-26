# Deduplicate Notify Delivery: NotificationHook vs HookReactionRouter

> **Owning task:** #963 — Deduplicate notify delivery between NotificationHook and HookReactionRouter
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

When both `NotificationHook` and `HookReactionRouter` observe the same event,
and the reaction rule includes a `notify` action, a single lifecycle event
produces two user notifications. The question is: what deduplication strategy
keeps exactly one notification per event while preserving legacy-only and
reaction-driven configurations? [S1, S2, S3, S4, S5, S6]

### Current state

- `NotificationHook` registers on events from `settings.notification_events`
  (default `["task_complete", "on_error"]`). Each handler tries backends in
  order; first success stops the chain. [S5]
- `HookReactionRouter` registers on events from `settings.hook_reactions[*].events`.
  Its `notify` executor is currently a noop (pending #957). [S5, S6]
- `HookRegistry.emit()` calls ALL handlers in registration order. Both fire
  for overlapping events. [S5]

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Prometheus AlertManager docs | .90 | Routing trees, inhibition rules, grouping — single notification path per alert |
| S2 | Prefect automations docs | .85 | Independent trigger/action automations; no built-in dedup between automations |
| S3 | Celery signals docs | .70 | Independent signal handlers; no built-in dedup |
| S4 | docs/research/hookevent-reaction-routing.md | 1.0 | Original reaction-routing research recommending notify delegation to existing backends |
| S5 | `src/owlbear/core/notification_hook.py`, `src/owlbear/core/hook_reaction_router.py`, `src/owlbear/bootstrap/hooks.py` | 1.0 | Current dual-path registration flow |
| S6 | `src/owlbear/config.py` (OwlBearSettings) | 1.0 | `notification_events` and `hook_reactions` fields |

## 3. Analysis

### 3.1 Deduplication strategies

| Option | Description | Pros | Cons | KISS | Verdict |
|--------|-------------|------|------|:----:|---------|
| A: Assembly-time event exclusion | `build_hooks()` removes events covered by reaction `notify` rules from `NotificationHook.notification_events` | Zero runtime overhead; deterministic; preserves legacy when no reactions | `match`-conditional rules may suppress unconditionally | High | **Best** |
| B: Remove NotificationHook entirely | Generate implicit reaction rules from `notification_events`; route everything through router | Single path; no dedup needed | Breaking change; requires #957 complete; complex migration | Med | Too wide for #963 |
| C: Runtime dedup tracking | Both paths deliver; backend layer deduplicates via per-event-per-tick state | Both paths coexist | Adds mutable state; timing-sensitive; hard to test | Low | Reject |
| D: Inhibition flag | Router sets a flag on payload before NotificationHook runs | Matches AlertManager inhibition pattern | Requires handler ordering; couples two independent handlers | Low | Reject |

AlertManager avoids duplicates by routing each alert to exactly one receiver
via a routing tree — not by running multiple receivers and deduplicating after
the fact. [S1] Option A matches this pattern at assembly time. Prefect's model
allows duplicate automations to fire independently, which is inappropriate for
OwlBear's single-user notification UX. [S2]

### 3.2 The `match` predicate subtlety

Option A must handle conditional vs unconditional rules:

| Reaction config | `NotificationHook` behavior | Risk |
|-----------------|----------------------------|------|
| `notify` with no `match` (unconditional) | Safe to exclude event from legacy path | None |
| `notify` with `match` (conditional) | If excluded, non-matching payloads lose notification | Silent notification loss |

Two sub-approaches:

| Sub-option | Rule | Complexity | Risk |
|------------|------|:----------:|------|
| A1: Exclude only for unconditional rules | Skip legacy only when at least one `notify` rule for that event has no `match` | Low | Conditional-only events still go through both paths — acceptable because the reaction only fires when matched |
| A2: Exclude always | If any rule mentions the event + `notify`, legacy is suppressed | Lowest | Conditional rules lose notifications for non-matching payloads |

**A1** is the right balance: unconditional reaction rules supersede legacy; conditional rules coexist safely because the legacy path handles the default case. The only scenario where both fire is when a conditional `match` succeeds AND the legacy path fires for the same event — but this can only happen if the user explicitly chose a conditional rule alongside the legacy path, which signals intentional overlap. [S1, S4]

### 3.3 Dependency analysis

| Dependency | Status | Impact on #963 |
|-----------|--------|----------------|
| #955 (schema + router) | done (docs) | Provides `HookReactionRule`, `HookReactionRouter`, and `build_hooks()` wiring |
| #957 (real notify executor) | ideation | The router's `notify` executor must be real for dedup to matter |

# 963 should add `depends_on: [955, 957]`. The dedup logic is meaningful only
after #957 wires a real notify executor. However, the assembly-time exclusion
in `build_hooks()` can be implemented now — it's safe even with noop executors
(excluded events just get no notification, same as current noop behavior).

## 4. Recommendation (.88 confidence)

Implement assembly-time event exclusion (Option A1) in `build_hooks()`:

1. Before constructing `NotificationHook`, compute `reaction_notify_events`:
   events covered by any reaction rule that includes `notify` without a `match`
   predicate. [S4, S5]
2. Filter `notification_events` to exclude `reaction_notify_events`. [S5, S6]
3. Pass the filtered list to `NotificationHook`. [S5]
4. When no `hook_reactions` are configured, behavior is identical to today. [S5]

Implementation scope: ~15 lines in `build_hooks()`, no new types. Tests cover
legacy-only, reaction-only, and mixed configurations. [S5]

Risk: if a user expects both paths to fire, the implicit suppression is
surprising. Mitigate by logging a `DEBUG` message when events are excluded.

## 5. Follow-up Tasks

1. Implement assembly-time notify dedup in `build_hooks()` — implement the
   event-exclusion logic, add depends_on #957 to #963, and write tests for
   legacy-only, reaction-driven, mixed, and conditional-match configurations.

   This is the implementation task for #963 itself. The existing task already
   has the correct AC. **Action:** update #963 `depends_on` to include #957,
   since dedup is meaningful only after real executors are wired.

   ```powershell
   kanban\kanban-md.exe edit 963 --depends-on 955,957
   ```
