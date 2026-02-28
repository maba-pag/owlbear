---
id: 229
title: Test ObservabilityHook JSONL event logging
status: archived
priority: important
created: 2026-02-28T01:18:45.9938202+01:00
updated: 2026-02-28T23:54:10.9100041+01:00
started: 2026-02-28T01:19:15.590473+01:00
completed: 2026-02-28T23:54:10.9100041+01:00
tags:
    - phase-11
    - agent
    - analytics
    - test
class: standard
---

TDD test task for #213. File: tests/test_observability_hook.py (new).

AC:
- [ ] Test ObservabilityHook writes JSONL event on SESSION_START
- [ ] Test ObservabilityHook writes JSONL event on PRE_TOOL_USE and POST_TOOL_USE
- [ ] Test POST_TOOL_USE event includes duration_ms (elapsed since matching PRE_TOOL_USE)
- [ ] Test event JSON schema: {timestamp, event_type, agent_name, tool_name, session_id, success, error, duration_ms}
- [ ] Test ON_ERROR event includes error details
- [ ] Test EventStore.load() deserializes all events from JSONL file
- [ ] Test EventStore.query(window=timedelta(hours=1)) filters by time
- [ ] Test EventStore.summary() returns {total_tool_calls, error_count, avg_tool_duration_ms, tools_by_frequency}
- [ ] Test EventStore.tool_stats() returns per-tool {call_count, error_count, avg_duration_ms}
- [ ] Test ObservabilityHook.register(hooks) registers on all 9 HookEvent types

File: tests/test_observability_hook.py
