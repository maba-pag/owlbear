---
id: 364
title: Unit tests for all error recovery paths
status: archived
priority: important
created: 2026-03-01T20:12:17.7836927+01:00
updated: 2026-03-03T15:03:00.8250557+01:00
started: 2026-03-01T20:22:28.2068586+01:00
completed: 2026-03-03T15:03:00.8250557+01:00
tags:
    - phase-13
    - test
    - reliability
class: standard
---

From #306 error-recovery.md. Tests for: error classification (all categories), HTTP retry (transient, auth, permanent), tool-level retry in HookedToolset, daemon structured recovery, human escalation flow, error journal (log + query + rotation), structured ToolError feedback. AC: >= 90%% coverage for core/errors.py, tools/hooked.py retry logic, daemon recovery, error_journal.py. Depends on #306, #357-#363.
