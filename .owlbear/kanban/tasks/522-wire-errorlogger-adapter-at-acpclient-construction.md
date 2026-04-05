---
id: 522
title: Wire ErrorLogger adapter at AcpClient construction sites
status: ideation
priority: nice-to-have
created: 2026-04-01T15:15:04.1613975+02:00
updated: 2026-04-01T15:15:04.1613975+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:build
depends_on:
    - 148
class: standard
---

## Objective
Create an _ErrorLogger adapter bridging ErrorJournal to the _ErrorLogger Protocol and pass it at AcpClient construction sites.

## AC
- [ ] Adapter class (or closure) implementing _ErrorLogger Protocol that delegates to ErrorJournal.log() with bound session_id
- [ ] session_id strategy for pre-session errors (initialize, new_session): use sentinel value 'pre-session' or empty string (builder decides, document choice)
- [ ] AcpClient construction in dispatch loop passes error_logger= adapter instance
- [ ] ErrorJournal file path sourced from orchestrator config or workspace-relative default
- [ ] Unit tests verify adapter delegates correctly
- [ ] No changes to acp_client.py (dependency on #148 for Protocol definition)

Follow-up from #148 arch review. Without this task, _ErrorLogger injection is dead code.
See docs/research/errorjournal-acpclient-wiring.md.
