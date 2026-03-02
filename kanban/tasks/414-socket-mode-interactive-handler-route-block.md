---
id: 414
title: Socket Mode interactive handler — route block_actions to message queue
status: backlog
priority: needed
created: 2026-03-01T20:20:16.9654856+01:00
updated: 2026-03-01T20:24:04.711965+01:00
started: 2026-03-01T20:24:04.711965+01:00
tags:
    - phase-13
    - slack
    - channels
class: standard
---

From #307 slack-structured-proposals-research.md. Extend _handle_socket_event in slack.py to handle request.type == 'interactive'. Acknowledge envelope, extract block_actions payload, put action value on _message_queue (button-to-text bridge). AC: Button clicks (approve/deny/option) routed as text strings to existing receive() flow; interactive payloads acknowledged; non-interactive events unaffected. Depends on #307.
