---
id: 415
title: Slack thread registry — per-project/task threading
status: backlog
priority: important
created: 2026-03-01T20:20:25.959236+01:00
updated: 2026-03-01T20:24:06.020606+01:00
started: 2026-03-01T20:24:06.020606+01:00
tags:
    - phase-13
    - slack
    - channels
class: standard
---

From #307 slack-structured-proposals-research.md. Add _thread_registry: dict[str, str] to SlackChannel mapping context_key (project_id:task_id) to thread_ts. Modify send_blocks() to capture ts from chat_postMessage response. Add get_or_create_thread() method. AC: Subsequent messages in same context auto-thread; thread_ts captured from first message; get_or_create_thread returns existing or starts new thread. Depends on #307.
