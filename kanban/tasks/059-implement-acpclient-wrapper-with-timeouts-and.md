---
id: 59
title: Implement AcpClient wrapper with timeouts and error classification
status: ideation
priority: needed
created: 2026-03-26T19:27:25.5707168+01:00
updated: 2026-03-28T01:51:02.1020121+01:00
tags:
    - phase-1
    - scope:orchestrator
    - type:build
depends_on:
    - 58
    - 46
    - 94
class: standard
---

## Objective
Wrap ACP SDK ClientSideConnection with per-method timeouts and error classification.

## AC
- [ ] Wraps initialize (30s), new_session (15s), prompt (300s) with asyncio.wait_for
- [ ] Catches RequestError and classifies by code per acp-error-handling-strategy.md SS3.5
- [ ] Sends session/cancel on timeout or external CancelSignal
- [ ] Detects BrokenPipeError and EOF as TRANSIENT (trigger respawn)
- [ ] Logs errors to ErrorJournal when available

Depends on: #58 (ProcessSupervisor). See docs/research/acp-error-handling-strategy.md SS3.3, SS3.4.
