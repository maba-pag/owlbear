---
id: 230
title: Test instrument_all and OTel endpoint config
status: archived
priority: important
created: 2026-02-28T01:18:54.9516679+01:00
updated: 2026-02-28T23:54:11.6395668+01:00
started: 2026-02-28T01:19:16.1004253+01:00
completed: 2026-02-28T23:54:11.6395668+01:00
tags:
    - phase-11
    - agent
    - config
    - test
class: standard
---

TDD test task for #216 and #218. Files: tests/test_daemon.py (extend), tests/test_config.py (extend).

AC:
- [ ] Test Agent.instrument_all() is called during daemon bootstrap (mock verify)
- [ ] Test instrument_all() call does not raise when no TracerProvider configured
- [ ] Test OwlBearSettings().otel_endpoint is None by default
- [ ] Test OWLBEAR_OTEL_ENDPOINT='http://localhost:4318' sets otel_endpoint
- [ ] Test otel_endpoint field is Optional[str] with None default

Files: tests/test_daemon.py, tests/test_config.py
