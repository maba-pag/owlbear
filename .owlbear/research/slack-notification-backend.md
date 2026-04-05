# SlackNotificationBackend Implementation Research

> **Owning task:** #978 — Implement SlackNotificationBackend
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

Task #978 (child of #952) requires a `SlackNotificationBackend` class satisfying the existing `NotificationBackend` protocol. The parent research (`docs/research/priority-routed-notifications.md`) established the design direction. This research validates feasibility, confirms the implementation pattern, and documents prior art for the specific Slack backend. [S1, S2]

Key questions:

1. What is the correct `AsyncWebClient` usage pattern for fire-and-forget notifications?
2. How should the backend handle missing Slack tokens?
3. What message formatting should be used (plain text vs mrkdwn)?
4. How does the backend interact with the existing `SlackChannel` adapter?

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | OwlBear `src/owlbear/core/notification_hook.py` | 1.0 | `NotificationBackend` protocol, existing `ConsoleBellBackend`/`WinSoundBackend` patterns |
| S2 | OwlBear `docs/research/priority-routed-notifications.md` | 1.0 | Parent research: two-tier design, ~40 LOC estimate, recommends `AsyncWebClient` |
| S3 | OwlBear `src/owlbear/channels/slack.py` | 1.0 | Production `AsyncWebClient` usage: import guard, `chat_postMessage`, `RateLimitErrorRetryHandler` |
| S4 | Slack SDK Web API docs | .90 | `AsyncWebClient.chat_postMessage(channel, text)` is the standard async pattern [S4a] |
| S5 | OwlBear `src/owlbear/config.py` | 1.0 | `slack_bot_token`, `slack_channel_id` fields; all-or-nothing validator |
| S6 | Prefect automations docs | .85 | Template-driven Slack notification blocks with event context — similar message formatting pattern |

## 3. Analysis

### 3.1 Protocol Contract

`NotificationBackend` requires exactly two members [S1]:

| Member | Signature | SlackNotificationBackend behavior |
|--------|-----------|-----------------------------------|
| `name` | `@property -> str` | Returns `"slack"` |
| `notify` | `async (message: str, event: HookEvent) -> bool` | Posts to Slack via `AsyncWebClient`; returns `True` on success, `False` on failure or missing tokens |

### 3.2 Constructor Injection vs Runtime Config Lookup

| Approach | KISS | Testability | Coupling |
|----------|:----:|:-----------:|:--------:|
| A. Inject `bot_token` + `channel_id` at construction | High | High — no config mock needed | Low |
| B. Accept `OwlBearSettings` reference | Low | Low — requires full settings object | High |
| C. Read env vars at `notify()` time | Low | Low — env manipulation in tests | High |

**Recommendation (.90):** Option A — constructor injection. `build_hooks()` extracts tokens from settings and passes strings. This matches `WinSoundBackend`'s zero-config pattern and keeps the backend testable with simple unit tests. [S1, S3]

### 3.3 Import Guard Pattern

`slack_sdk` is an optional dependency (`[slack]` extra). The backend must handle `ImportError` gracefully. The existing pattern in `channels/slack.py` [S3]:

```python
try:
    from slack_sdk.web.async_client import AsyncWebClient
except ImportError:
    AsyncWebClient = None  # type: ignore[assignment]
```

The backend should use the same guard at module level and return `False` in `notify()` when `AsyncWebClient is None`. [S3]

### 3.4 Message Formatting

| Approach | Readability | Complexity | Prior art |
|----------|:-----------:|:----------:|:---------:|
| A. Plain text with event label | High | Lowest | WinSoundBackend ignores message [S1] |
| B. mrkdwn with event label + context | High | Low | SlackChannel uses mrkdwn [S3]; Prefect templates [S6] |
| C. Block Kit structured message | Medium | High | YAGNI for notifications |

**Recommendation (.85):** Option B — the `message` parameter from the hook data dict is already formatted; prepend a bold event label (e.g., `*on_error*: {message}`). Use Slack's mrkdwn syntax since `chat_postMessage` supports it natively. No Block Kit — YAGNI for fire-and-forget alerts. [S1, S3, S6]

### 3.5 Error Handling

Consistent with existing backends [S1]: catch all exceptions, log warning, return `False`. Specifically:

- `ImportError` (no `slack_sdk`): return `False` immediately
- Missing tokens: return `False` immediately
- `SlackApiError` / network errors: log + return `False`
- No retry handler needed — `NotificationHook`'s fallthrough chain handles degradation [S1, S2]

### 3.6 Config Validator Interaction

`OwlBearSettings._validate_slack_all_or_nothing` requires all three Slack fields (`app_token`, `bot_token`, `channel_id`) or none. The notification backend only needs `bot_token` + `channel_id`. This means Slack notifications cannot be enabled without also configuring `app_token` (needed for Socket Mode). This is acceptable for now — if Slack tokens are set, they're always complete. If a "notifications-only" Slack mode is wanted later (no Socket Mode), the validator would need relaxing. This is a concern for #977, not #978. [S5]

### 3.7 Separation from SlackChannel

The backend must NOT import or reference `SlackChannel` or `ChannelPlugin`. It creates its own `AsyncWebClient` instance. This avoids coupling notification delivery to the active I/O channel and keeps the backend self-contained. [S2, S3]

## 4. Recommendation (.88 confidence)

Implement `SlackNotificationBackend` in `notification_hook.py` with:

1. Module-level import guard for `AsyncWebClient` (same pattern as `channels/slack.py`)
2. Constructor: `__init__(self, bot_token: str | None, channel_id: str | None)` — lazy client creation
3. `name` property returning `"slack"`
4. `notify()`: return `False` if tokens missing or import failed; format message as `*{event_label}*: {message}`; post via `chat_postMessage`; catch all errors → `False`
5. ~30-35 LOC implementation

No new follow-up tasks needed — the AC is already well-scoped.

## 5. Follow-up Tasks

No new tasks. The existing AC on #978 is sufficient. Design notes for #977 (config validator interaction) documented in §3.6 above.
