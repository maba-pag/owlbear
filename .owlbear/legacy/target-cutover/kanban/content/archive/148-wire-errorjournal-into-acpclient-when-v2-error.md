---
id: 148
title: Wire ErrorJournal into AcpClient when v2 error infrastructure exists
status: archived
priority: medium
created: 2026-03-29 18:53:05.705807+02:00
updated: 2026-04-04 07:09:52.740465+02:00
started: 2026-04-04 07:09:26.939511+02:00
completed: 2026-04-04 07:09:26.939511+02:00
tags:
- phase-2
- scope:orchestrator
- type:build
depends_on:
- 184
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Integrate ErrorJournal logging into AcpClient error paths via Protocol-based interface.

## AC
- [ ] `_ErrorLogger` Protocol defined in acp_client.py with `log_error(*, category, method, message)` method
- [ ] AcpClient accepts optional `_ErrorLogger` in constructor (default None)
- [ ] All 6 catch blocks call `_log_error()` helper before re-raising AcpClientError
- [ ] No-op when error_logger is None (current behavior preserved)
- [ ] Unit tests verify log_error() called on error for each method and error type

Depends on #184 (v2 ErrorJournal module).
See docs/research/errorjournal-acpclient-wiring.md and docs/research/acp-client-wrapper-validation.md SS3.4.

[[2026-03-29]] Sun 20:24
## Research
- Protocol-based interface recommended (follows existing _CancelSignal pattern in acp_client.py)
- v2 has zero error persistence infrastructure, prerequisite task #184 created
- Implementation is ~20 LOC once #184 exists (Protocol + constructor param + helper + 6 catch calls)
- Sync logging in async catch blocks is acceptable (sub-ms per error-journal-async.md)
- No JsonlStore base needed yet (YAGNI, matches orchestrator-audit-log.md conclusion)
- AC refined: Protocol-based _ErrorLogger, 6 catch blocks, explicit test requirements
- See docs/research/errorjournal-acpclient-wiring.md for full analysis

[[2026-04-03]] Fri 01:09
## Architecture Review
**Verdict:** BLOCK (premise challenge -- already implemented)
**DR Verification:** N/A -- not research-driven

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| _ErrorLogger Protocol in acp_client.py | Already exists (lines 42-46), implemented by #521 | Redundant |
| AcpClient accepts optional _ErrorLogger | Already exists (constructor line 95), implemented by #521 | Redundant |
| All 6 catch blocks call _log_error() | Already exists (initialize/new_session/prompt, 6 blocks), implemented by #521 | Redundant |
| No-op when error_logger is None | Already exists (if-guard in each block), implemented by #521 | Redundant |
| Unit tests verify log_error() | Already exists (TestFromAC_ErrorLoggerWiring, 8 tests), implemented by #521 | Redundant |

### Architecture Notes
Premise challenge: the entire scope of #148 was implemented, tested, reviewed, and archived as task #521 (Test: Wire ErrorJournal into AcpClient). #521 completed the full TDD cycle (RED + GREEN) in a single test-task flow, producing the _ErrorLogger Protocol, constructor wiring, all 6 catch-block integrations, and 8 unit tests. Auditor archived #521 at confidence 1.0 on 2026-04-02.

Evidence:
- acp_client.py lines 42-46: _ErrorLogger Protocol
- acp_client.py line 95: error_logger kwarg
- acp_client.py lines 120-131, 143-155, 175-187: 6 guarded log_error calls
- test_acp_client.py lines 505-633: TestFromAC_ErrorLoggerWiring (8 tests, all passing)
- #521 audit: 42 passed, confidence 1.0, archived

Nothing remains for a builder to implement. Task is fully redundant.

### Changes Made
- Blocked to ideation: fully implemented by #521

### Dependencies
- #184 (ErrorJournal module): archived, complete
- #521 (ErrorLogger wiring): archived, complete -- covers all #148 AC

### Challenge Results
- Challenge: SKIPPED (BLOCK verdict)
