# Slack Sender Validation Research

> **Owning task:** #526 — Add sender validation to Slack message queue
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

SEC-15 identified that `SlackChannel._handle_socket_event()` enqueues raw DM text with no sender check. The `user` field from the Slack event payload is available but ignored. Any Slack user who can DM the bot gets their messages fed directly as agent prompts.

**Question:** What is the minimal, KISS-aligned approach to validate message senders, rate-limit incoming messages, and log all activity?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Slack `message.im` event reference | <https://docs.slack.dev/reference/events/message.im> | .95 — confirms `user` field in DM event payload |
| 2 | Slack Events API docs | <https://docs.slack.dev/apis/events-api> | .85 — event structure, `user` field, `bot_message` subtype, server-side rate limits (30K/workspace/60min) |
| 3 | Slack Security Best Practices | <https://docs.slack.dev/authentication/best-practices-for-security> | .90 — "validate message source", rate-limiting guidance, logging recommendations, prompt injection mitigation |
| 4 | Slack `message` event subtypes | <https://docs.slack.dev/reference/events/message> | .80 — `bot_message` subtype has no `user` field; subtypes to filter |
| 5 | Bolt for Python event listening | <https://docs.slack.dev/tools/bolt-python/concepts/event-listening> | .70 — subtype filtering pattern (`bot_message` filter) |

## 3. Current State (Codebase)

In `src/owlbear/channels/slack.py` L283-290:

```python
if event.get("type") == "message" and event.get("channel_type") == "im":
    text = event.get("text", "")
    await self._message_queue.put(text)  # raw — no sender check
```

**Gaps:**

- `event["user"]` is present but never read
- Bot messages (`subtype: "bot_message"`) are not filtered — risk of bot-to-bot loops
- No rate limiting on incoming messages
- Only `logger.debug` — no audit-level logging of sender identity
- No config field for allowed user IDs

## 4. Analysis

### 4.1 Sender Validation Approach

| Criterion | A: Config allowlist (.85) | B: Trust all (.30) | C: Dynamic API lookup (.40) |
|-----------|--------------------------|--------------------|-----------------------------|
| Complexity | ~15 LOC in handler | 0 LOC | ~30 LOC + API call per msg |
| KISS | High | Highest | Low |
| Security | Strong — explicit allow | None — status quo | Medium — validates existence |
| Config burden | One-time list of user IDs | None | None |
| Performance | O(1) set lookup | N/A | HTTP call per message |
| YAGNI risk | Low — needed per SEC-15 | N/A | High — overkill for small team |

**Recommendation (.85): Option A — Config allowlist.**
Add `slack_allowed_user_ids: list[str]` to `OwlBearSettings`. In the event handler, check `event.get("user")` against a `frozenset`. Empty list = accept all (backwards compatible). Also filter out messages with `subtype` (bot messages have no `user` field or have `subtype: "bot_message"`).

### 4.2 Rate Limiting Approach

| Criterion | A: Sliding window counter (.80) | B: External library (.45) |
|-----------|----------------------------------|---------------------------|
| Complexity | ~15 LOC, `dict[str, deque]` | New dependency |
| KISS | High | Medium |
| Deps | None — stdlib only | `aiolimiter` or `limits` |
| Configurability | `slack_rate_limit_per_minute` | Same |
| YAGNI risk | Low | High — adds dependency for one use |

**Recommendation (.80): Option A — Sliding window counter.**
In-memory `dict[user_id, deque[float]]` with timestamps. Check count in last 60s window. Config: `slack_rate_limit_per_minute: int = 30` (0 = disabled). No external dependencies.

### 4.3 Logging Approach

| Criterion | A: Structured INFO log (.85) | B: Dedicated audit log (.50) |
|-----------|------------------------------|------------------------------|
| Complexity | 2 log calls in handler | New file handler, rotation |
| Aligns with | Existing `logger` pattern | Task #525 audit log |
| Sensitive data | Log user_id + msg length, NOT content | Same |
| KISS | High | Low — #525 handles this later |

**Recommendation (.85): Option A — Structured INFO logging.**
Log sender `user_id` and message length at `INFO` level for accepted messages. Log `WARNING` for rejected messages (unauthorized sender or rate-limited). Do NOT log message content — it may contain sensitive data. Task #525 (security audit log) will later add structured audit logging infrastructure.

## 5. Implementation Plan

Changes span 3 files:

1. **`config.py`** — Add `slack_allowed_user_ids: list[str] = []` and `slack_rate_limit_per_minute: int = 30`
2. **`slack.py`** — In `__init__`, accept `allowed_user_ids` and `rate_limit_per_minute`. In `_handle_socket_event`:
   - Skip messages with `subtype` (filters bot messages, edits, etc.)
   - Check `user` against allowlist (if non-empty)
   - Check rate limit counter
   - Log accepted/rejected at INFO/WARNING
3. **`bootstrap.py`** — Pass new config fields to `SlackChannel()`

Test coverage: mock event payloads with allowed/disallowed user IDs, bot messages, rate limit exceeded.

## 6. Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| User forgets to set allowed IDs | Medium | Empty list = accept all; log warning at startup if empty |
| Rate limit too aggressive | Low | Default 30/min is generous; configurable |
| Bot-to-bot loop via DM | Low | Filter messages with any `subtype` field |

## 7. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement Slack sender validation" --priority needed --tags "security,channels,phase-9" --body "Add allowed_user_ids config + allowlist check in _handle_socket_event. Filter bot_message subtype. See docs/research/slack-sender-validation.md S4.1. AC: (1) slack_allowed_user_ids in config, (2) unauthorized senders rejected with WARNING log, (3) bot messages filtered, (4) empty allowlist accepts all."

kanban\kanban-md.exe create "Add Slack message rate limiting" --priority nice-to-have --tags "security,channels,phase-9" --body "Add slack_rate_limit_per_minute config + sliding window counter in _handle_socket_event. See docs/research/slack-sender-validation.md S4.2. AC: (1) rate limit config field, (2) messages exceeding rate are dropped with WARNING log, (3) 0 disables rate limit."

kanban\kanban-md.exe create "Add Slack message audit logging" --priority nice-to-have --tags "security,channels,phase-9" --body "Log sender user_id and message length at INFO level in _handle_socket_event. Log WARNING for rejected messages. Do NOT log content. See docs/research/slack-sender-validation.md S4.3. AC: (1) accepted messages logged at INFO with user_id, (2) rejected messages logged at WARNING with reason."
```
