---
id: 204
title: 'Test: Wire audit log into dispatch loop'
status: todo
priority: needed
created: 2026-03-30T08:11:23.2576692+02:00
updated: 2026-03-30T08:11:23.2576692+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:test
    - test
depends_on:
    - 146
class: standard
---

TDD RED tests for #164 (wire audit log into dispatch loop).

## Acceptance Criteria

- [ ] Test: AuditLog instantiated in dispatch loop constructor via injection (not global)
- [ ] Test: log_dispatch() called before AcpClient.prompt(), producing DispatchEvent with timestamp, task_id, agent, prompt_summary (max 100 chars), session_id
- [ ] Test: log_completion() called after AcpClient.prompt() returns, producing CompletionEvent with timestamp, task_id, agent, outcome, duration_ms, files_changed, error
- [ ] Test: duration_ms uses monotonic clock (time.monotonic delta converted to int ms)
- [ ] Test: files_changed populated via git diff before/after dispatch
- [ ] Test: audit I/O error in log_dispatch does not propagate (dispatch continues)
- [ ] Test: audit I/O error in log_completion does not propagate (dispatch continues)
- [ ] Test: full integration round-trip produces DispatchEvent + CompletionEvent in session JSONL
- [ ] All tests fail (RED phase) before builder implements #164

## Notes

- Mock AcpClient.prompt() and git subprocess for unit tests
- Use tmp_path for JSONL file assertions
- Follow existing test pattern in tests/test_audit_log.py
- Depends on #146 (dispatch loop interface must exist to write meaningful tests)
