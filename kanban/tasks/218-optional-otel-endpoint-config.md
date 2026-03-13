---
id: 218
title: Optional OTel endpoint config
status: archived
priority: nice-to-have
created: 2026-02-28T01:11:20.6891568+01:00
updated: 2026-02-28T23:54:02.6548995+01:00
started: 2026-02-28T01:11:47.7706481+01:00
completed: 2026-02-28T23:54:02.6548995+01:00
tags:
    - phase-11
    - config
class: standard
---

Add optional OTel endpoint configuration to OwlBearSettings.

File: src/owlbear/config.py

AC:
- [ ] otel_endpoint: str | None = None field in OwlBearSettings
- [ ] Env var: OWLBEAR_OTEL_ENDPOINT
- [ ] Field under a '--- Observability ---' comment section
- [ ] When set, daemon bootstrap configures Logfire SDK with send_to_logfire=False and otel_endpoint as OTLP target
- [ ] When None, no OTel configuration (instrument_all is still a no-op)
- [ ] ~5 LOC in config.py + ~15 LOC conditional setup in daemon bootstrap

Depends on: #230 (test task), #216
See docs/research/agent-observability.md
