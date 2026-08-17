# Slack Rich Messaging — Images, Proposals, Status Updates

> **Owning task:** #297 — Slack rich messaging — images, proposals, status updates
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

SlackChannel currently sends plain text via `chat_postMessage(channel, text=...)`. For OwlBear's project management flow, we need: structured proposals (Block Kit), image/file uploads, status update formatting, threading, and optional interactive elements. Task #307 (interactive proposals with buttons) depends on this.

**Question:** What's the simplest way to add rich messaging to SlackChannel using `slack_sdk.web.async_client.AsyncWebClient`, without breaking the existing `ChannelPlugin` protocol or CLIChannel backward compatibility?

## 2. Sources Studied

| # | Source | URL | Relevance | What |
|---|--------|-----|-----------|------|
| 1 | Slack Block Kit — Blocks reference | <https://docs.slack.dev/reference/block-kit/blocks> | .95 | Block types: header, section, actions, divider, image, context. Max 50 blocks/message. |
| 2 | slack_sdk `AsyncWebClient.chat_postMessage` | <https://github.com/slackapi/python-slack-sdk> (v3.40.1) | .95 | Accepts `blocks`, `thread_ts`, `mrkdwn` params directly. Blocks as `list[dict]`. |
| 3 | slack_sdk `AsyncWebClient.files_upload_v2` | <https://github.com/slackapi/python-slack-sdk> (v3.40.1) | .90 | 3-step upload: `getUploadURLExternal` → upload → `completeUploadExternal`. Accepts `file` (path/bytes/IOBase), `channel`, `thread_ts`, `initial_comment`. |
| 4 | Slack Button element reference | <https://docs.slack.dev/reference/block-kit/block-elements/button-element> | .85 | `type: button` with `action_id`, `style` (primary/danger), `value`. In `actions` or `section.accessory`. |
| 5 | slack_sdk integration test — `sending_a_message.py` | <https://github.com/slackapi/python-slack-sdk/blob/main/integration_tests/samples/basic_usage/sending_a_message.py> | .85 | Official example: `chat_postMessage(blocks=[...])`, threading via `thread_ts=response["message"]["ts"]`. |
| 6 | Bolt Python AI Agent Template | <https://github.com/slack-samples/bolt-python-assistant-template> | .80 | Thread management, streaming responses, feedback buttons in AI assistant context. |
| 7 | Slack Block Kit — Section block | <https://docs.slack.dev/reference/block-kit/blocks/section-block> | .80 | Text + `fields` (2-col layout) + `accessory` (button, image, select). `mrkdwn` text type. |
| 8 | Slack Block Kit — Actions block | <https://docs.slack.dev/reference/block-kit/blocks/actions-block> | .80 | Up to 25 interactive elements: buttons, selects, date pickers. Sends `block_actions` payload. |

## 3. Analysis

### 3.1 Feature-to-API Mapping

| Feature | API Method | Params | Complexity |
|---------|-----------|--------|------------|
| Structured messages (proposals, status) | `chat_postMessage` | `blocks=list[dict]`, `text=` (fallback) | Low — dicts, no new deps |
| Image/file upload | `files_upload_v2` | `file=path\|bytes\|IOBase`, `channel=`, `initial_comment=`, `thread_ts=` | Low — built into AsyncWebClient |
| Threading | `chat_postMessage` | `thread_ts=parent_ts` | Trivial — one extra param |
| Markdown → mrkdwn | Manual conversion | `mrkdwn=True` on text objects | Low — regex substitutions |
| Interactive buttons | `chat_postMessage` with `actions` block | Buttons with `action_id` + handler for `interactive` Socket Mode events | Medium — requires event routing |
| Bot scope addition | Slack app config | `files:write` scope for uploads | Trivial — one-time config |

### 3.2 Approach Comparison — Protocol Extension Design

| Criterion | ChannelPlugin base extension (.40) | Mixin / separate protocol (.55) | Methods on SlackChannel only (.85) |
|-----------|-------------------------------------|----------------------------------|--------------------------------------|
| Backward compat | Breaks — all channels must implement | Clean — opt-in via isinstance | **Cleanest** — CLI unchanged |
| KISS | Low — abstract new methods | Medium — adds a protocol layer | **High** — concrete methods |
| YAGNI | Low — CLIChannel never sends images | Medium | **High** — only Slack needs it |
| Discoverability | High — protocol shows all ops | Medium — scattered | Medium — check SlackChannel |
| Duck typing fit | Poor | OK | **Good** — callers check `hasattr` or `isinstance(ch, SlackChannel)` |

### 3.3 Block Kit Template Patterns

**Proposal message (header + description + numbered options + context):**

```python
blocks = [
    {"type": "header", "text": {"type": "plain_text", "text": title}},
    {"type": "section", "text": {"type": "mrkdwn", "text": description}},
    {"type": "divider"},
    # One section per option
    {"type": "section", "text": {"type": "mrkdwn", "text": f"*1.* {option_1}"}},
    {"type": "section", "text": {"type": "mrkdwn", "text": f"*2.* {option_2}"}},
    {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "Reply with the option number or type your feedback."}],
    },
]
```

**Status update message (header + fields for progress):**

```python
blocks = [
    {"type": "header", "text": {"type": "plain_text", "text": f"Status: {task_title}"}},
    {
        "type": "section",
        "fields": [
            {"type": "mrkdwn", "text": f"*Task:*\n{task_name}"},
            {"type": "mrkdwn", "text": f"*Step:*\n{current_step}/{total_steps}"},
            {"type": "mrkdwn", "text": f"*Status:*\n{status_emoji} {status}"},
            {"type": "mrkdwn", "text": f"*ETA:*\n{eta}"},
        ],
    },
    {"type": "section", "text": {"type": "mrkdwn", "text": f"*Last action:* {last_tool}"}},
]
```

### 3.4 File Upload via `files_upload_v2`

AsyncWebClient provides `files_upload_v2` which handles the 3-step process internally:

1. `files.getUploadURLExternal` — gets a signed upload URL
2. HTTP PUT to the upload URL with file data
3. `files.completeUploadExternal` — finalizes and optionally shares to channel

```python
await self._web_client.files_upload_v2(
    file=path_or_bytes,  # str path, bytes, or IOBase
    channel=self._channel_id,
    title=caption or "image",
    initial_comment=caption,
    thread_ts=thread_ts,  # optional threading
)
```

**Required scope:** `files:write` (must be added to the Slack app config — not currently in our v1 scope list).

### 3.5 Threading Model

`chat_postMessage` returns `{"message": {"ts": "1234567890.123456"}}`. The `ts` value serves as the thread parent. All subsequent replies use `thread_ts=parent_ts`.

For OwlBear's use case:

- Each user request creates a parent message (the user's text or our acknowledgment)
- Progress updates and results reply in the thread
- `SlackChannel` tracks `_current_thread_ts: str | None` as state

### 3.6 Markdown → Slack mrkdwn Conversion

Slack uses `mrkdwn` (not standard Markdown). Key differences:

| Markdown | Slack mrkdwn |
|----------|-------------|
| `**bold**` | `*bold*` |
| `*italic*` | `_italic_` |
| `~~strike~~` | `~strike~` |
| `[text](url)` | `<url\|text>` |
| `# Heading` | No equivalent (use header block) |
| `` `code` `` | `` `code` `` (same) |
| ```` ```block``` ```` | ```` ```block``` ```` (same) |

A simple regex converter handles common cases. Edge cases (nested formatting) can be deferred.

### 3.7 Interactive Elements — Scoping Decision

**For #297:** No interactive elements (buttons, selects). Proposals use numbered text options with `receive()` for response — matching the current `AskUserToolset` pattern.

**For #307 (depends on #297):** Add `actions` blocks with buttons, handle `interactive` Socket Mode events via `_handle_socket_event`. This is a separate, more complex task.

**Rationale (YAGNI):** #297's AC says "numbered options, request for feedback" — this works with text-based responses today. Interactive buttons add event routing complexity that belongs in #307.

## 4. Recommendation (.85 confidence)

**Add `send_blocks()`, `send_image()`, and markdown-aware `send()` directly to `SlackChannel` — no protocol changes.** The `ChannelPlugin` protocol stays minimal (text-only). Rich methods are concrete on `SlackChannel`. Callers that need rich messaging use `isinstance(channel, SlackChannel)` or `hasattr(channel, 'send_blocks')`.

**Implementation plan (4 tasks):**

1. **Add `send_blocks()` to `SlackChannel`** — wraps `chat_postMessage(blocks=..., text=fallback)` with optional `thread_ts`
2. **Add `send_image()` to `SlackChannel`** — wraps `files_upload_v2(file=..., channel=..., initial_comment=...)`
3. **Add Block Kit template helpers** — `format_proposal_blocks(title, desc, options)` and `format_status_blocks(task, step, status, eta)` as pure functions
4. **Markdown-aware `send()`** — auto-convert common Markdown patterns to mrkdwn when sending via Slack (regex-based, ~20 LOC)

**What NOT to do (YAGNI):**

- Don't extend `ChannelPlugin` protocol — CLI and Voice channels don't need these methods
- Don't add interactive elements yet — that's #307's scope
- Don't build a full mrkdwn converter — handle `**bold**`, `*italic*`, `~~strike~~`, `[text](url)` only

**Required Slack app config change:** Add `files:write` bot scope for image uploads.

**Risk:** Slack's `files_upload_v2` is a 3-step process that can fail mid-flight. Mitigation: wrap in try/except, log warning, fall back to sending the caption as text.

## 5. Follow-up Tasks

See kanban commands below. Task structure follows a TDD pattern with test tasks preceding implementation tasks.

1. **Test `SlackChannel.send_blocks`** — mock `chat_postMessage`, verify blocks + text fallback, threading
2. **Implement `SlackChannel.send_blocks`** — `send_blocks(blocks, text_fallback, thread_ts=None)`
3. **Test `SlackChannel.send_image`** — mock `files_upload_v2`, verify file/bytes paths, caption, error fallback
4. **Implement `SlackChannel.send_image`** — `send_image(file_or_bytes, caption, thread_ts=None)`
5. **Test Block Kit template helpers** — pure function unit tests for proposal + status templates
6. **Implement Block Kit template helpers** — `format_proposal_blocks()`, `format_status_blocks()`
7. **Test mrkdwn conversion in `send()`** — verify bold/italic/strike/link conversions
8. **Implement mrkdwn-aware `send()`** — regex substitutions in `SlackChannel.send()`
