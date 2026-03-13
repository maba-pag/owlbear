---
id: 334
title: Add progress config to OwlBearSettings — progress_enabled, interval, detail
status: archived
priority: needed
created: 2026-03-01T11:17:39.7562006+01:00
updated: 2026-03-01T17:10:04.7975+01:00
started: 2026-03-01T11:21:04.4349153+01:00
completed: 2026-03-01T17:10:04.7975+01:00
tags:
    - phase-12
    - daemon
    - channels
    - config
class: standard
---

## Acceptance Criteria
- [ ] Add to OwlBearSettings: progress_enabled: bool = True
- [ ] Add to OwlBearSettings: progress_interval: float = 30.0 (seconds between updates)
- [ ] Add to OwlBearSettings: progress_detail: Literal['brief', 'detailed'] = 'brief'
- [ ] Env vars: OWLBEAR_PROGRESS_ENABLED, OWLBEAR_PROGRESS_INTERVAL, OWLBEAR_PROGRESS_DETAIL
- [ ] Unit test: default values, env var override, validation (interval must be > 0)

See docs/research/progress-reporting.md S3.8
