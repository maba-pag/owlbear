# Two-Tier Priority Notification Config for OwlBearSettings

> **Owning task:** #977 — Add two-tier priority notification config to OwlBearSettings
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

Task #977 (child of #952) adds four new config fields that split notifications into urgent and info tiers. The parent research (`docs/research/priority-routed-notifications.md`) validated the two-tier approach (.82 confidence). This doc covers config-layer implementation specifics: field design, backend name validation, and deprecation mechanism for the flat `notification_events`/`notification_backends` fields.

Key questions:

1. How should backend names be validated at config time?
2. What Pydantic mechanism best handles the flat → tiered field deprecation?
3. What defaults produce backward-compatible behavior?

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Grafana notification policies | .85 | Label-based routing with contact-point inheritance; validates tier-routing as a standard pattern |
| S2 | Pydantic `Field(deprecated=...)` docs | .95 | Native deprecation: emits `DeprecationWarning` on access; `deprecated=str` for custom message |
| S3 | Pydantic `model_validator(mode='after')` docs | .90 | Post-init hook for cross-field mapping; correct tool for old → new field migration |
| S4 | OwlBear `_ALLOWED_ACTIONS` pattern (`src/owlbear/config.py:33`) | 1.0 | Frozenset + `field_validator` for closed-set validation — existing internal precedent |
| S5 | OwlBear `NotificationHook` (`src/owlbear/core/notification_hook.py`) | 1.0 | Current backend names: `"bell"` (ConsoleBellBackend), `"sound"` (WinSoundBackend) |
| S6 | Parent research (`docs/research/priority-routed-notifications.md`) | 1.0 | Two-tier design decision, event classification, SlackNotificationBackend plan |
| S7 | OwlBear `HookEvent` enum (`src/owlbear/core/hooks.py:148-161`) | 1.0 | All 11 event values for tier classification |
| S8 | OwlBear `TestFromAC_QuestionPendingDefaultCleanup` (`tests/test_config.py:644`) | 1.0 | Live-emitter guard: default events must be emitted by real code |

## 3. Analysis

### 3.1 Backend Name Validation

| Option | Approach | KISS | Extensibility | Verdict |
|--------|----------|:----:|:-------------:|---------|
| A. `_KNOWN_BACKENDS` frozenset | Like `_ALLOWED_ACTIONS`; field_validator rejects unknowns | High | Requires code change to add backend | **Recommend** |
| B. No validation | Trust `build_hooks()` to skip unknown names | High | Fully open | Reject — typos pass silently |
| C. Plugin registry | Dynamic backend discovery at import time | Low | Fully open | Reject — YAGNI |

Known backends for the validation set: `{"bell", "sound", "slack"}`. "slack" is included because sibling task #978 is landing `SlackNotificationBackend` — the config should accept it before the backend exists (graceful fallthrough at runtime). "toast" is deferred per parent research. [S4, S5, S6]

### 3.2 Deprecation Mechanism

| Option | How | Pros | Cons | Verdict |
|--------|-----|------|------|---------|
| A. Pydantic `Field(deprecated=...)` + `model_validator` | Mark old fields deprecated; map old → new in `model_validator(mode='after')` | Native warning support; backward-compatible; env vars still work | Requires `warnings.catch_warnings()` in validator to suppress internal access warnings | **Recommend** |
| B. Remove old fields | Drop `notification_events`/`notification_backends` | Clean break | Breaks existing `OWLBEAR_NOTIFICATION_EVENTS` env var users | Reject |
| C. Old fields as aliases | Compute new from old via `computed_field` | No validator needed | Aliases don't support deprecation warnings; confusing semantics | Reject |

The `model_validator(mode='after')` maps old → new only when the old fields are explicitly set but the new fields are at defaults. When new fields are set explicitly, old fields are ignored. This matches Grafana's inheritance model where child policy settings override parent defaults. [S1, S2, S3]

### 3.3 Default Values

| Field | Default | Rationale |
|-------|---------|-----------|
| `notification_urgent_events` | `["on_error", "budget_warning", "question_pending"]` | Blocking/critical events needing immediate attention [S6, S7] |
| `notification_urgent_backends` | `["slack", "sound", "bell"]` | Full chain: remote push → audible → visual [S5, S6] |
| `notification_info_events` | `["task_complete"]` | Informational only — no urgency [S6, S7] |
| `notification_info_backends` | `["bell"]` | Minimal — just a terminal flash [S5, S6] |
| `notification_events` (deprecated) | `["task_complete", "on_error"]` | Unchanged for backward compat [S5] |
| `notification_backends` (deprecated) | `["bell", "sound"]` | Unchanged for backward compat [S5] |

### 3.4 Backward-Compat Mapping Logic

```
model_validator(mode='after'):
    if old fields were explicitly set AND new fields are at defaults:
        map notification_events → notification_urgent_events
        map notification_backends → notification_urgent_backends
    # else: new fields take priority; old fields ignored
```

Detection of "explicitly set" uses `model_fields_set` — the set of field names provided at construction time (or via env vars). [S3]

### 3.5 Event Name Validation

Current `notification_events` does **not** validate event names at config time — `NotificationHook.register()` logs a warning for unknown events at runtime (line 126). The new tier fields should follow the same pattern for consistency. Config-time event validation would couple `config.py` to `HookEvent`, breaking the leaf-module invariant from #955/#969. [S5, S8]

## 4. Recommendation (.85 confidence)

Implement #977 using:

1. `_KNOWN_BACKENDS = frozenset({"bell", "sound", "slack"})` with `field_validator` on both backend fields [S4].
2. `Field(deprecated="Use notification_urgent_* and notification_info_* fields")` on old fields [S2].
3. `model_validator(mode='after')` with `warnings.catch_warnings()` for backward-compat mapping [S3].
4. No config-time event name validation (preserves leaf-module invariant) [S8].

Risks:

| Risk | Severity | Mitigation |
|------|----------|------------|
| `model_fields_set` detection misses env var overrides | Low | pydantic-settings populates `model_fields_set` for env-sourced values — verified in existing test `test_notification_events_env_override` |
| `warnings.catch_warnings()` in validator suppresses real deprecation signals | Low | Scope suppression to the three-line validator block only |
| Adding "slack" before #978 lands | None | Backend chain falls through gracefully; `build_hooks()` (#979) only instantiates backends it knows |

## 5. Follow-up Tasks

No new tasks needed — #977 AC is complete and implementable as stated. Sibling tasks #978 (SlackNotificationBackend) and #979 (build_hooks wiring) handle remaining work.

**AC refinement for architect review:**

- Validate `notification_urgent_backends` and `notification_info_backends` against `_KNOWN_BACKENDS = {"bell", "sound", "slack"}`
- Use `Field(deprecated="Use notification_urgent_* and notification_info_* fields")`
- Use `model_validator(mode='after')` with `model_fields_set` to detect explicit old-field usage
- No config-time event name validation (preserves leaf-module invariant)
- Env vars: `OWLBEAR_NOTIFICATION_URGENT_EVENTS`, `OWLBEAR_NOTIFICATION_URGENT_BACKENDS`, etc.
