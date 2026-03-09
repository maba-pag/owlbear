---
id: 713
title: 'Tests: SESSION_START and SESSION_END hook emission'
status: todo
priority: needed
created: 2026-03-09T19:16:05.8759624+01:00
updated: 2026-03-09T19:17:46.830138+01:00
tags:
    - scope:core
    - hooks
    - test
    - type:test
class: standard
---

TDD RED tests for #711. Test scenarios:

- [ ] test_session_start_emitted: mock agent.hooks.emit, call run_daemon with a CliChannel that returns None immediately, assert SESSION_START emitted with payload keys {session_id, workspace_root}
- [ ] test_session_end_emitted_on_normal_exit: same setup, assert SESSION_END emitted with {session_id, messages}
- [ ] test_session_end_emitted_on_exception: inject error into channel_loop, assert SESSION_END still emitted in finally block
- [ ] test_session_end_empty_session: session file does not exist, assert messages falls back to empty list (no crash)
- [ ] test_session_start_after_daemon_startup: verify SESSION_START is emitted after DAEMON_STARTUP (ordering)
- [ ] test_context_injection_hook_fires: register ContextInjectionHook, emit SESSION_START, verify data['context'] populated

depends_on: none
Blocked-by: none
