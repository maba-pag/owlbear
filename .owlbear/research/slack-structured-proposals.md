# Slack Structured Proposals — Block Kit for Interactive Decisions

> **Owning task:** #307 — Slack structured proposals — Block Kit for interactive decisions
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

Task #297 (Slack rich messaging, archived/done) added `send_blocks()`, `send_image()`, and Block Kit templates (`format_proposal_blocks`, `format_status_blocks`) to `SlackChannel`. These are **read-only** — the user sees proposals but replies by typing text.

Task #307 asks: how do we make these proposals **interactive** — with buttons for approve/deny, option selection, progress updates — and route Slack button clicks back to the agent decision loop?

Key sub-questions:

1. How does Socket Mode deliver interactive payloads (button clicks)?
2. How should button clicks integrate with the existing `ChannelPlugin` protocol and `ApprovalGateToolset`?
3. How do we manage threaded conversations per project/task?
4. What's the fallback for non-interactive channels?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Slack Socket Mode — interactive features | <https://docs.slack.dev/apis/events-api/using-socket-mode/#interactivity> | .95 | `type: "interactive"` envelope, `block_actions` payload, `envelope_id` ack |
| Slack Button element reference | <https://docs.slack.dev/reference/block-kit/block-elements/button-element> | .90 | `action_id`, `value`, `style` (primary/danger), `confirm` dialog |
| Bolt for Python — action listener | <https://docs.slack.dev/tools/bolt-python/concepts/actions> | .85 | `@app.action("action_id")` pattern, `ack()` + `say()` response |
| Bolt Python AI Agent Template | <https://github.com/slack-samples/bolt-python-assistant-template> | .75 | Thread-based AI assistant pattern, message-per-thread model |
| Existing OwlBear `SlackChannel` | `src/owlbear/channels/slack.py` | .95 | Current `_handle_socket_event` only handles `events_api` type |
| Existing `ApprovalGateToolset` | `src/owlbear/safety/gate.py` | .90 | Uses `channel.send(str)` + `channel.receive() -> str` protocol |

## 3. Analysis

### 3.1 Socket Mode Interactive Payload Flow

When a user clicks a Block Kit button, Slack delivers via Socket Mode:

```
envelope: { type: "interactive", envelope_id: "...", payload: { type: "block_actions", ... } }
```

Current `_handle_socket_event` only handles `request.type == "events_api"`. Interactive payloads arrive with `request.type == "interactive"`. The handler must be extended to acknowledge and route these.

The `payload.actions[0]` contains: `action_id`, `value`, `block_id`, `type: "button"`. The `value` field carries semantic meaning (e.g., `"approve"`, `"deny"`, `"option_1"`).

### 3.2 Architecture: Button-to-Text Bridge vs. Extended Protocol

| Criterion | A: Extend ChannelPlugin | B: Button→Text Bridge | C: InteractiveChannel |
|-----------|------------------------|----------------------|----------------------|
| ChannelPlugin breakage | All adapters | None | None (optional protocol) |
| ApprovalGate changes | Rewrite send/receive | None | Minor (isinstance check) |
| Complexity | High | Low | Medium |
| KISS score | Low | **High** | Medium |
| Future extensibility | Good | Limited | Good |
| Implementation effort | ~200 LOC | ~80 LOC | ~120 LOC |

**Recommendation (.85 confidence): Option B — Button→Text Bridge**

The bridge approach translates button clicks into text strings on the existing `_message_queue`. When a user clicks "Approve", the handler puts `"yes"` on the queue. The `ApprovalGateToolset` works unchanged — it already listens for `"yes"/"no"` text responses. This is maximally KISS.

For the **send** side, `SlackChannel` gains a `send_approval()` / `send_proposal()` method that internally calls `send_blocks()` with interactive button templates. Non-Slack channels fall back to `send()` with text equivalents. The decision of which to call belongs to the caller (e.g., `ApprovalGateToolset` does `isinstance(channel, SlackChannel)` check or a capability query).

### 3.3 Interactive Template Design

**Proposal template** — header, description, option buttons, feedback context:

```python
# actions block with buttons per option
{
    "type": "actions",
    "block_id": "proposal_{id}",
    "elements": [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "1. OAuth flow"},
            "action_id": "proposal_opt_1",
            "value": "1",
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "2. PAT token"},
            "action_id": "proposal_opt_2",
            "value": "2",
        },
    ],
}
```

**Approval template** — action description, approve/deny buttons, reason context:

```python
{
    "type": "actions",
    "block_id": "approval_{id}",
    "elements": [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Approve"},
            "action_id": "approval_approve",
            "value": "yes",
            "style": "primary",
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Deny"},
            "action_id": "approval_deny",
            "value": "no",
            "style": "danger",
        },
    ],
}
```

**Progress template** — emoji-based progress bar, current step, ETA:

```python
# Progress bar: ▓▓▓▓░░░░░░ 40%
{
    "type": "section",
    "text": {"type": "mrkdwn", "text": "*Task:* Deploy service\n▓▓▓▓░░░░░░ 4/10\n*Status:* running\n*ETA:* ~3 min"},
}
```

### 3.4 Threaded Conversations

| Criterion | Per-channel thread registry | Per-message thread_ts passthrough |
|-----------|---------------------------|-----------------------------------|
| Automatic thread grouping | Yes | No, caller must track |
| State management | `dict[str, str]` in SlackChannel | None |
| Complexity | Low | Lower |
| KISS score | High | Higher |

**Recommendation (.75 confidence): Thread registry in SlackChannel**

A `_thread_registry: dict[str, str]` maps `{context_key -> thread_ts}`. The channel captures `ts` from `chat_postMessage` responses to auto-thread subsequent messages. The context key is `"{project_id}:{task_id}"` or similar. This requires modifying `send_blocks()` to return (or store) the message `ts`.

### 3.5 Fallback for Non-Interactive Channels

Templates already produce both Block Kit blocks and text fallbacks. The pattern:

1. Template functions return both `blocks: list[dict]` and `text_fallback: str`
2. `SlackChannel` sends blocks via `send_blocks()`
3. `CLIChannel` (and others) send `text_fallback` via `send()`
4. The caller uses a helper: `if hasattr(channel, 'send_blocks'): ... else: channel.send(...)`

This avoids changing the `ChannelPlugin` protocol while providing rich Slack UX.

### 3.6 Event Handler Extension

The existing `_handle_socket_event` needs a second branch:

```python
elif request.type == "interactive":
    response = SocketModeResponse(envelope_id=request.envelope_id)
    await client.send_socket_mode_response(response)
    payload = request.payload
    if payload.get("type") == "block_actions":
        for action in payload.get("actions", []):
            value = action.get("value", "")
            await self._message_queue.put(value)
```

This is the minimal bridge: button `value` → message queue → existing receive() flow.

## 4. Recommendation (.85 confidence)

**Adopt the Button→Text Bridge pattern (Option B).**

- Extend `_handle_socket_event` to handle `type: "interactive"` with `block_actions`
- Add interactive template functions: `format_interactive_proposal_blocks()`, `format_approval_blocks()`, `format_progress_blocks()` (emoji bar)
- Add thread registry to `SlackChannel` for per-project/task threading
- Keep `ChannelPlugin` protocol unchanged
- Caller-side logic determines whether to use rich blocks or text fallback

**Risks:**

- Button→text bridge loses structured data (e.g., which specific button was clicked vs. just the value). Mitigation: encode semantic meaning in `value` field, add `action_id` routing for future needs.
- Thread registry adds state to `SlackChannel`. Mitigation: simple dict, cleared on disconnect.

## 5. Follow-up Tasks

1. **Interactive templates** — Add `format_interactive_proposal_blocks()`, `format_approval_blocks()`, `format_progress_blocks()` to `slack_templates.py`
2. **Socket Mode interactive handler** — Extend `_handle_socket_event` in `slack.py` to route `type: "interactive"` → message queue
3. **Thread registry** — Add `_thread_registry` to `SlackChannel`, modify `send_blocks()` to capture `ts`, add `get_or_create_thread()` method
4. **Approval gate Slack enrichment** — Teach `ApprovalGateToolset` to use `send_blocks()` when the channel supports it (isinstance check or duck-typing)
5. **Text fallback helpers** — Add `format_proposal_text()`, `format_approval_text()`, `format_progress_text()` for non-interactive channels
6. **Action callback routing** — Add `_action_callbacks: dict[str, Callable]` for future structured action handling beyond text bridging
7. **Unit tests** — Mock interactive payloads, template output validation, thread registry, fallback paths
