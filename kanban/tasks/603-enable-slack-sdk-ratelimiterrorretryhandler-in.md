---
id: 603
title: Enable Slack SDK RateLimitErrorRetryHandler in channels/slack.py
status: archived
priority: needed
created: 2026-03-06T12:13:25.1600148+01:00
updated: 2026-03-06T19:28:34.8929968+01:00
started: 2026-03-06T13:47:47.5573053+01:00
completed: 2026-03-06T19:28:34.8929968+01:00
tags:
    - resilience
    - channels
depends_on:
    - 600
class: standard
---

Add `RateLimitErrorRetryHandler(max_retry_count=1)` to the `AsyncWebClient` constructor in `channels/slack.py`. The SDK already ships `ConnectionErrorRetryHandler` by default. No tenacity decorator needed on Slack methods.

### AC
- [ ] `AsyncWebClient` constructor includes `retry_handlers=[RateLimitErrorRetryHandler(max_retry_count=1)]`
- [ ] Import: `from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler`
- [ ] No tenacity `@retry` decorator added to `send`, `send_blocks`, or `send_image`
- [ ] Test: mock `AsyncWebClient.chat_postMessage` raising `SlackApiError` with 429 status  verify SDK retries (handler registered)
- [ ] Existing `send_image` try/except fallback-to-text pattern unchanged

### Architecture notes
- Slack SDK's retry is a different mechanism from tenacity  intentional. The SDK respects Slack's `Retry-After` header natively.
- `ConnectionErrorRetryHandler` is enabled by default in `AsyncWebClient`  we only add `RateLimitErrorRetryHandler`
- depends_on #600 is soft  this task doesn't import `core/retry.py`, but logically belongs to the same initiative
- See `docs/research/retry-decorators.md` §3.4
