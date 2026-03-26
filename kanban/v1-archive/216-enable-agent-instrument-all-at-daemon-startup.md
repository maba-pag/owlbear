---
id: 216
title: Enable Agent.instrument_all() at daemon startup
status: archived
priority: important
created: 2026-02-28T01:11:15.1583152+01:00
updated: 2026-02-28T23:54:01.7600009+01:00
started: 2026-02-28T01:11:47.2419118+01:00
completed: 2026-02-28T23:54:01.7600009+01:00
tags:
    - phase-11
    - agent
class: standard
---

Call Agent.instrument_all() unconditionally at daemon startup. Zero-cost no-op when no TracerProvider configured.

File: src/owlbear/daemon.py (extend run_daemon) or src/bearclaw/cli.py (extend run_cmd)

AC:
- [ ] from pydantic_ai import Agent; Agent.instrument_all() called once at daemon startup
- [ ] Called before the daemon loop starts (in run_cmd or at top of run_daemon)
- [ ] No TracerProvider configuration — just enable instrumentation hooks
- [ ] No new dependencies (logfire is already bundled with pydantic-ai)
- [ ] Does not raise when no OTel backend configured (verified by test)
- [ ] ~5 LOC change

Depends on: #230 (test task)
See docs/research/agent-observability.md
