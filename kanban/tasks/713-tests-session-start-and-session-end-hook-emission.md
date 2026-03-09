---
id: 713
title: 'Tests: SESSION_START and SESSION_END hook emission'
status: archived
priority: needed
created: 2026-03-09T19:16:05.8759624+01:00
updated: 2026-03-10T00:41:49.6751171+01:00
started: 2026-03-09T22:38:10.3902978+01:00
completed: 2026-03-10T00:41:49.6751171+01:00
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

[[2026-03-09]] Mon 20:09
## Test-Writer Notes
- Test file: tests/test_session_hooks.py
- Classes: TestFromAC_SessionStart, TestFromAC_SessionEnd, TestFromAC_ContextInjection
- Tests per category: happy 3, edge 0, error 2, boundary 1
- Total: 6 tests, all FAIL (TypeError  workspace_root param not yet added)
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| test_session_start_emitted | test_session_start_emitted | happy |
| test_session_end_emitted_on_normal_exit | test_session_end_emitted_on_normal_exit | happy |
| test_session_end_emitted_on_exception | test_session_end_emitted_on_exception | error |
| test_session_end_empty_session | test_session_end_empty_session | error |
| test_session_start_after_daemon_startup | test_session_start_after_daemon_startup | boundary |
| test_context_injection_hook_fires | test_context_injection_hook_fires | happy |

[[2026-03-09]] Mon 20:09
## Test-Writer Notes
- Test file: tests/test_session_hooks.py
- Classes: TestFromAC_SessionStart, TestFromAC_SessionEnd, TestFromAC_ContextInjection
- Tests per category: happy 3, edge 0, error 2, boundary 1
- Total: 6 tests, all FAIL (TypeError  workspace_root param not yet added)
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| test_session_start_emitted | test_session_start_emitted | happy |
| test_session_end_emitted_on_normal_exit | test_session_end_emitted_on_normal_exit | happy |
| test_session_end_emitted_on_exception | test_session_end_emitted_on_exception | error |
| test_session_end_empty_session | test_session_end_empty_session | error |
| test_session_start_after_daemon_startup | test_session_start_after_daemon_startup | boundary |
| test_context_injection_hook_fires | test_context_injection_hook_fires | happy |

[[2026-03-09]] Mon 21:28
## Builder Notes
- Files changed: src/owlbear/daemon.py (3 surgical edits)
- Tests: 6 passed (all TestFromAC), 0 modified
- Coverage: new SESSION_START/SESSION_END lines fully exercised by test_session_hooks.py
- Lint: ruff clean (PLR0915 + BLE001 suppressed with rationale)
- Regression: TestRunDaemon (7), TestDaemonStartupHook (4), TestSignalHandler (2) all pass
- Implementation: added workspace_root param to run_daemon, SESSION_START emit after DAEMON_STARTUP, SESSION_END emit in finally block with try/except fallback on session.load()

[[2026-03-09]] Mon 21:50
## Review Evidence (reviewer, 2026-03-09)

### Test Results
- pytest (scoped): 6 passed, 0 failed (test_session_hooks.py)
- Daemon regression: 13 passed (TestRunDaemon 7, TestDaemonStartupHook 4, TestSignalHandler 2  0 failures)

### Lint Results
- ruff: All checks passed! (src/owlbear/daemon.py + tests/test_session_hooks.py)

### Coverage
- daemon.py: 30% (scoped run  new SESSION_START/SESSION_END lines fully exercised; uncovered lines are heartbeat/autonomous/otel paths not relevant to this task)

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | All 6 tests check exact counts (==1), specific payload keys, and exact payload values (session_id, workspace_root, messages). No lazy asserts. |
| Negative/error paths | ADEQUATE | test_session_end_emitted_on_exception (RuntimeError in receive), test_session_end_empty_session (FileNotFoundError on session.load). 2 of 6 tests cover error paths. |
| Mutation reasoning | STRONG | Removing SESSION_START emit breaks 2 tests; removing SESSION_END emit breaks 3 tests; removing fallback breaks empty_session test; swapping ordering breaks after_daemon_startup test. |
| Test independence | STRONG | Each test creates own _MockChannel, _make_mock_agent, and uses tmp_path. No shared mutable state. |
| Descriptive names | STRONG | All names describe scenario+outcome: test_session_start_emitted, test_session_end_emitted_on_exception, test_context_injection_hook_fires. |

### Security Review
- No hardcoded secrets
- No injection vectors (payload values are str() conversions of internal paths)
- No path traversal (workspace_root only stringified in payload, no file I/O)
- No insecure deserialization
- No new dependencies
- No secret leakage in logs/errors
- BLE001 suppression in finally block justified: AC requires SESSION_END on *any* error

### Test Writer vs Builder Comparison
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_SessionStart::test_session_start_emitted | No change | PRESERVED |
| TestFromAC_SessionStart::test_session_start_after_daemon_startup | No change | PRESERVED |
| TestFromAC_SessionEnd::test_session_end_emitted_on_normal_exit | No change | PRESERVED |
| TestFromAC_SessionEnd::test_session_end_emitted_on_exception | No change | PRESERVED |
| TestFromAC_SessionEnd::test_session_end_empty_session | No change | PRESERVED |
| TestFromAC_ContextInjection::test_context_injection_hook_fires | No change | PRESERVED |

Note: test file is untracked (new) in git  created by test-writer, unmodified by builder.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| test_session_start_emitted: SESSION_START with {session_id, workspace_root} | Exact payload assertions at lines 90-96 of test file | TestFromAC_SessionStart::test_session_start_emitted | PASS |
| test_session_end_emitted_on_normal_exit: SESSION_END with {session_id, messages} | Exact payload assertions at lines 152-158 | TestFromAC_SessionEnd::test_session_end_emitted_on_normal_exit | PASS |
| test_session_end_emitted_on_exception: SESSION_END in finally block | RuntimeError injected, SESSION_END count == 1 at line 179 | TestFromAC_SessionEnd::test_session_end_emitted_on_exception | PASS |
| test_session_end_empty_session: messages fallback to [] | FileNotFoundError on load, messages == [] at line 198 | TestFromAC_SessionEnd::test_session_end_empty_session | PASS |
| test_session_start_after_daemon_startup: ordering | Real HookRegistry tracks emit order, index comparison at line 121 | TestFromAC_SessionStart::test_session_start_after_daemon_startup | PASS |
| test_context_injection_hook_fires: ContextInjectionHook populates context | Real hook registered, payload['context'] with 'instructions' and 'kanban_summary' keys at lines 283-285 | TestFromAC_ContextInjection::test_context_injection_hook_fires | PASS |

### Verdict: PASS (confidence .95)

[[2026-03-09]] Mon 22:38
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal hook emission added to daemon.py; no new behavior/API/convention visible to agents or users |
| 2 | Docstrings complete | Yes | Updated | Added workspace_root param docstring to run_daemon() |
| 3 | sources/overview.md | No | N/A | No external patterns adopted; SESSION_START/END follows existing DAEMON_STARTUP pattern |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | No | N/A | No research phase for this test+impl task |
| 6 | No impact (other) | -- | -- | Item 2 applied |

### Files Updated
- src/owlbear/daemon.py (docstring only: workspace_root param)

### Scratch Files Cleaned
- None (no scratch files found)

[[2026-03-10]] Tue 00:41
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| test_session_start_emitted | daemon.py L886-891: emits SESSION_START with {session_id, workspace_root}; test passes | PASS |
| test_session_end_emitted_on_normal_exit | daemon.py L985-990: emits SESSION_END with {session_id, messages} in finally; test passes | PASS |
| test_session_end_emitted_on_exception | finally block at L977+; test injects RuntimeError, asserts SESSION_END emitted; passes | PASS |
| test_session_end_empty_session | L978-983: try/except fallback to []; test simulates FileNotFoundError; passes | PASS |
| test_session_start_after_daemon_startup | DAEMON_STARTUP at L880, SESSION_START at L886 (after); test verifies ordering; passes | PASS |
| test_context_injection_hook_fires | Real ContextInjectionHook registered, SESSION_START triggers it, payload[context] has instructions+kanban_summary; passes | PASS |

### Test Results
- pytest (test_session_hooks.py): 6 passed
- daemon regression (test_daemon.py): 70 passed
- ruff: All checks passed

### Confidence: .97
### Action: archive
