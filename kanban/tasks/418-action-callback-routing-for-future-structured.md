---
id: 418
title: Action callback routing for future structured Slack actions
status: archived
priority: nice-to-have
created: 2026-03-01T20:20:51.8671336+01:00
updated: 2026-03-03T16:40:10.0638509+01:00
started: 2026-03-01T20:24:09.6108524+01:00
completed: 2026-03-03T16:40:10.0638509+01:00
tags:
    - phase-13
    - slack
    - channels
class: standard
---

## Context
From #307 slack-structured-proposals-research.md.
Enables registering specific action handlers by action_id for Block Kit interactive messages, beyond the current text-bridge approach.

## Acceptance Criteria
- [ ] SlackChannel.__init__ initializes _action_callbacks: dict[str, Callable[[dict[str, Any]], Awaitable[None]]] = {} (async callbacks)
- [ ] SlackChannel.register_action(action_id: str, callback: Callable) → None — registers a handler for that action_id
- [ ] In _handle_socket_event, when processing block_actions: for each action, check _action_callbacks[action.get('action_id')]; if found, await callback(action); if not found, fall through to existing _message_queue.put(value) behavior
- [ ] Callbacks receive the full action dict (not just the value string)
- [ ] Unregistered action_ids continue to work exactly as today (backward compatible)
- [ ] Tests: register a callback for 'approve_action', simulate block_action event with action_id='approve_action', verify callback was invoked with action payload; verify unregistered action_id still goes to message queue

## Implementation Notes
- Modify _handle_socket_event interactive block at slack.py:247-263
- ~30 LOC: dict init + register_action method + dispatch in event handler
- Callback type: Callable[[dict[str, Any]], Awaitable[None]] (async)
- No external dependencies
