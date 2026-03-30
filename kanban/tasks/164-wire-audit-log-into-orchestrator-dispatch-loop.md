---
id: 164
title: Wire audit log into orchestrator dispatch loop
status: todo
priority: needed
created: 2026-03-29T19:44:23.6292421+02:00
updated: 2026-03-30T08:12:59.4360763+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:build
depends_on:
    - 163
    - 19
    - 146
    - 204
class: standard
---

Wire AuditLog into the orchestrator dispatch loop via constructor injection.
See docs/research/wire-audit-log-dispatch-loop.md for full analysis.

## Acceptance Criteria

- [ ] `AuditLog(Path(data/audit))` instantiated in dispatch loop constructor
- [ ] AuditLog passed via constructor injection (not global/singleton)
- [ ] `log_dispatch()` called before every `AcpClient.prompt()` call, producing DispatchEvent with: timestamp (ISO-8601), task_id, agent, prompt_summary (truncated to 100 chars), session_id
- [ ] `log_completion()` called after every `AcpClient.prompt()` returns or raises, producing CompletionEvent with: timestamp, task_id, agent, outcome (success/failure), duration_ms, files_changed, error (str or None)
- [ ] Duration measured via `time.monotonic()` before/after prompt(); delta converted to int milliseconds
- [ ] files_changed captured via `git diff --name-only` before/after dispatch; diff the two sets
- [ ] All audit calls wrapped in try/except: audit I/O errors logged as warning, never block dispatch loop
- [ ] Integration test (from #204) passes after implementation

## Architecture Notes

- **Pattern:** Constructor injection (matches ErrorJournal pattern in error_journal.py)
- **Hook points:** (1) constructor: create AuditLog, (2) pre-dispatch: log_dispatch before prompt(), (3) post-dispatch: log_completion after prompt() or on exception
- **session_id** from AcpClient.new_session() response
- **prompt_summary:** truncate format_prompt() output to 100 chars via slicing
- **No separate module** for wiring: hooks go directly in dispatch loop code (#146)

## Dependencies

- #163 (audit log module) -- archived
- #19 (ACP client) -- archived
- #146 (dispatch loop) -- must be implemented first
- #204 (TDD RED tests) -- must be written first

[[2026-03-30]] Mon 08:12
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| AuditLog instantiated in constructor | Precise, verifiable | Keep |
| Constructor injection (not global) | Precise, matches ErrorJournal pattern | Keep |
| log_dispatch before prompt() | All fields specified with types | Keep |
| log_completion after prompt() | Covers success and exception paths | Keep |
| time.monotonic() for duration | Specific measurement approach | Keep |
| git diff for files_changed | Specified strategy with before/after snapshot | Keep |
| try/except around audit calls | Failure isolation clearly specified | Keep |
| Integration test from #204 | TDD compliance via new test task | Added #204 |

### Architecture Notes
- Module layering: dispatch loop (application) imports owlbear.audit (domain). Correct direction.
- Pattern: constructor injection matches existing ErrorJournal pattern in error_journal.py.
- No new modules needed. Audit hooks go directly in dispatch loop code when #146 is implemented.
- Security: session_id and task_id are internal values (from planner). prompt_summary truncation prevents log bloat.
- Failure mode: audit I/O error caught silently. Single failure mode, well-specified.

### Changes Made
- Rewrote body with precise, verifiable AC (8 items, all testable pass/fail)
- Created #204 (Test: Wire audit log into dispatch loop) at todo
- Added #204 to depends_on (now: 163, 19, 146, 204)

### Dependencies
- Verified: #163 (archived), #19 (archived)
- Verified: #146 (backlog, blocking). Dispatch loop must exist before wiring.
- Added: #204 (TDD RED tests, todo). Test-writer writes failing tests first.

[[2026-03-30]] Mon 08:12
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| AuditLog instantiated in constructor | Precise, verifiable | Keep |
| Constructor injection (not global) | Precise, matches ErrorJournal pattern | Keep |
| log_dispatch before prompt() | All fields specified with types | Keep |
| log_completion after prompt() | Covers success and exception paths | Keep |
| time.monotonic() for duration | Specific measurement approach | Keep |
| git diff for files_changed | Specified strategy with before/after snapshot | Keep |
| try/except around audit calls | Failure isolation clearly specified | Keep |
| Integration test from #204 | TDD compliance via new test task | Added #204 |

### Architecture Notes
- Module layering: dispatch loop (application) imports owlbear.audit (domain). Correct direction.
- Pattern: constructor injection matches existing ErrorJournal pattern in error_journal.py.
- No new modules needed. Audit hooks go directly in dispatch loop code when #146 is implemented.
- Security: session_id and task_id are internal values (from planner). prompt_summary truncation prevents log bloat.
- Failure mode: audit I/O error caught silently. Single failure mode, well-specified.

### Changes Made
- Rewrote body with precise, verifiable AC (8 items, all testable pass/fail)
- Created #204 (Test: Wire audit log into dispatch loop) at todo
- Added #204 to depends_on (now: 163, 19, 146, 204)

### Dependencies
- Verified: #163 (archived), #19 (archived)
- Verified: #146 (backlog, blocking). Dispatch loop must exist before wiring.
- Added: #204 (TDD RED tests, todo). Test-writer writes failing tests first.
