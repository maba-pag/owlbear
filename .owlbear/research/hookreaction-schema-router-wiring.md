# HookReaction Schema and Router Wiring

> **Owning task:** #955 - Define HookReaction policy schema and bootstrap router wiring
> **Date:** 2026-03-23 **Status:** Complete

## 1. Context and Question

Task #955 needs the concrete shape of `hook_reactions` and the exact wiring seam
for a router that delegates to existing executors without changing
`HookRegistry` semantics. The earlier #950 research established the high-level
direction, but not the narrow schema, the layering-safe validation point, or the
minimum viable rule surface. [S1, S2, S3, S4, S5, S6, S7, S8]

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Prefect automations docs | .95 | Trigger/action model, ordered actions, and inferred-target automation patterns |
| S2 | Prefect create automations guide | .95 | YAML/JSON automation schema with explicit event triggers and action lists |
| S3 | Pydantic models docs | .90 | Nested models, concrete container guidance, and `extra` handling |
| S4 | Pydantic validators docs | .90 | Field/model validators and startup-safe validation patterns |
| S5 | Pydantic settings docs | .95 | `env_nested_delimiter`, nested complex parsing, and partial update behavior |
| S6 | OwlBear architecture standards and `src/owlbear/config.py` | 1.0 | Config stays a leaf module; settings already use nested settings parsing |
| S7 | OwlBear `src/owlbear/core/hooks.py`, `src/owlbear/core/notification_hook.py`, and `src/owlbear/bootstrap/hooks.py` | 1.0 | Observational hook contract, string event registration precedent, and current bootstrap wiring |
| S8 | OwlBear `src/owlbear/daemon.py` and `src/owlbear/orchestrator/loop_detection.py` | 1.0 | Retry and escalation executors live above `core/` and must be injected |

## 3. Analysis

### 3.1 Constraints already visible in OwlBear

| Constraint | Evidence | Impact |
|-----------|----------|--------|
| `config.py` must stay a leaf module | Config is the single settings source of truth and should not import higher layers. [S5, S6] | `hook_reactions` cannot depend on `HookEvent` directly inside `config.py`; event names must be validated later. [S6, S7] |
| Hooks are observational | `HookRegistry.emit()` logs and swallows handler failures by design. [S1, S6, S7] | Routing belongs in a standalone handler, not inside `HookRegistry.emit()`. [S6, S7] |
| String event registration already exists | `NotificationHook.register()` resolves configured strings to `HookEvent` during bootstrap registration. [S5, S7] | `hook_reactions` should reuse the same registration-time validation seam. [S5, S6, S7] |
| Retry and escalation live outside `core/` | Task retry is in `daemon.py`; escalation is in `loop_detection.py`. [S6, S8] | The router must use injected executor protocols instead of importing runtime owners. [S6, S8] |

### 3.2 Schema options

| Option | Benefits | Risks | Verdict |
|--------|----------|-------|---------|
| `list[dict[str, Any]]` free-form rules | Lowest upfront code | Weak validation, poor editor help, and runtime drift on unknown keys. [S2, S3, S4] | Reject |
| Rich discriminated action DSL | Matches Prefect's broader action-object style and leaves room for future parameters. [S1, S2] | YAGNI for OwlBear's current `notify`/`retry`/`escalate` executors, which need little or no per-action config today. [S6, S8] | Too wide for #955 |
| Minimal typed rule model with string events, shallow matchers, and ordered action kinds | Strong startup validation, fits existing settings patterns, and keeps the first router contract small. [S2, S3, S4, S5] | Leaves richer action parameters for later work. [S1, S2] | Best |

Prefect justifies explicit trigger/action structure instead of free-form dicts,
while Pydantic makes OwlBear's smaller typed model cheap to validate. OwlBear
does not yet need Prefect's richer per-action object surface. [S1, S2, S3, S4]

### 3.3 Router placement

| Option | Benefits | Risks | Verdict |
|--------|----------|-------|---------|
| Inline routing closures inside `build_hooks()` | Small apparent diff | Hides policy in assembly code and makes matching logic harder to test in isolation. [S6, S7] | Reject |
| `HookReactionRouter` class in `core/`, registered from `build_hooks()` | Matches existing hook objects such as `NotificationHook`, keeps bootstrap as assembly root, and keeps logic testable. [S1, S6, S7, S8] | Requires one new core type plus injected executor protocols. [S6, S8] | Best |
| Modify `HookRegistry` to understand reactions | Centralizes routing | Breaks the observational-hook contract and couples registry mechanics to policy. [S1, S6, S7] | Reject |

## 4. Recommendation (.91 confidence)

- Use `hook_reactions: list[HookReactionRule] = []`, where each rule has
  non-empty `events: list[str]`, optional shallow equality `match`, and ordered
  `actions` limited to `notify`, `retry`, and `escalate`. Reject unknown keys
  and empty rules with normal Pydantic validation. [S2, S3, S4, S5]
- Keep `events` as strings in `config.py`. Validate them at startup by
  converting each configured name to `HookEvent` inside router registration,
  the same seam currently used by `NotificationHook.register()`. This avoids a
  second event enum and preserves config layering. [S5, S6, S7]
- Implement a standalone `HookReactionRouter` in `core/` with injected
  executor protocols. `build_hooks()` should instantiate it and register one
  handler per configured event. `HookRegistry` itself should remain unchanged.
  [S1, S6, S7, S8]
- Keep matching intentionally narrow for #955: event name plus scalar payload
  equality only. No expression language, no templating DSL, and no nested
  workflow engine. That keeps the seam aligned with KISS/YAGNI while still
  unlocking #956 and #957. [S1, S2, S3, S4]
- Limit the proof scope to live emitted events such as `task_complete`,
  `on_error`, and `budget_warning`. `question_pending` exists in the enum and
  default notification config, but this research found no current emission site
  in `src/`. [S6, S7]

## 5. Risks and Follow-up Findings

| Finding | Why it matters | Action |
|---------|----------------|--------|
| `question_pending` is configured as a default notification event but is not emitted anywhere in `src/`. [S6, S7] | Default config and router examples can promise behavior the runtime never produces. | Create #962 to remove the dead default surface until an emitter exists. |
| Router-driven `notify` can double-fire alongside the legacy `NotificationHook` path if both observe the same event. [S6, S7] | A single lifecycle event could produce duplicate user notifications. | Create #963 to deduplicate notification delivery when `notify` moves behind reactions. |

## 6. Follow-up Tasks

1. #962 - Remove dead question_pending default hook configuration.
   Priority rationale: cleans a false-positive default before the new router
   multiplies the same drift into another config surface.
   Dependencies: none.
   One-line AC: remove `question_pending` from default notification and
   HookReaction example surfaces until the codebase actually emits that hook
   event, with tests proving the default event set references only live
   emissions.
   Created:

   ```powershell
   kanban\kanban-md.exe create "Remove dead question_pending default hook configuration" --priority important --status ideation --parent 955 --tags "agent,hooks,config,scope:core,type:build" --body "See docs/research/hookreaction-schema-router-wiring.md section 5. AC: remove question_pending from default notification and HookReaction example surfaces until the codebase actually emits that hook event, with tests proving the default event set references only live emissions."
   ```

2. #963 - Deduplicate notify delivery between NotificationHook and HookReactionRouter.
   Priority rationale: avoids a user-facing regression when reaction-driven
   `notify` is introduced on top of the existing notification hook.
   Dependencies: #955.
   One-line AC: when a HookReaction rule includes `notify`, a single lifecycle
   event yields at most one user notification by reusing one backend chain or
   suppressing the legacy NotificationHook path, with tests for legacy-only and
   reaction-driven configurations.
   Created:

   ```powershell
   kanban\kanban-md.exe create "Deduplicate notify delivery between NotificationHook and HookReactionRouter" --priority important --status ideation --parent 957 --depends-on 955 --tags "agent,hooks,config,scope:core,type:build" --body "See docs/research/hookreaction-schema-router-wiring.md section 5. AC: when a HookReaction rule includes notify, a single lifecycle event yields at most one user notification by reusing one backend chain or suppressing the legacy NotificationHook path, with tests for legacy-only and reaction-driven configurations."
   ```
