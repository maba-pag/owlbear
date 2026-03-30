---
id: 148
title: Wire ErrorJournal into AcpClient when v2 error infrastructure exists
status: backlog
priority: nice-to-have
created: 2026-03-29T18:53:05.705807+02:00
updated: 2026-03-29T20:24:47.5149544+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:build
depends_on:
    - 184
class: standard
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
