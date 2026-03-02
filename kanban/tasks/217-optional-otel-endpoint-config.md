---
id: 217
title: Optional OTel endpoint config
status: archived
priority: nice-to-have
created: 2026-02-28T01:11:15.754098+01:00
updated: 2026-03-02T09:14:09.4843024+01:00
started: 2026-03-01T18:12:51.0187598+01:00
completed: 2026-03-02T09:14:09.4843024+01:00
tags:
    - config
    - phase-14
class: standard
---

OWLBEAR_OTEL_ENDPOINT field in OwlBearSettings. See docs/agent-observability-research.md.

Research: N/A — already implemented. otel_endpoint field exists in config.py L59. daemon.py configure_otel() uses it. This task is complete.

Resolution: The field already exists in OwlBearSettings as otel_endpoint: str | None = None. The daemon's run_daemon() accepts and uses it via configure_otel(). No further work needed.
