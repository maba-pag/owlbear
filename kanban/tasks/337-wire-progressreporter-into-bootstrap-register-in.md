---
id: 337
title: Wire ProgressReporter into bootstrap — register in build_hooks with channel
status: archived
priority: needed
created: 2026-03-01T11:18:11.1742738+01:00
updated: 2026-03-01T17:10:07.1993845+01:00
started: 2026-03-01T11:21:38.2203704+01:00
completed: 2026-03-01T17:10:07.1993845+01:00
tags:
    - phase-12
    - daemon
    - channels
depends_on:
    - 336
class: standard
---

## Acceptance Criteria
- [ ] build_hooks() accepts optional channel and settings params for progress
- [ ] When progress_enabled=True: create ProgressReporter(channel, settings.progress_interval, settings.progress_detail)
- [ ] Register ProgressReporter on POST_TOOL_USE hook
- [ ] bootstrap() passes channel to build_hooks() after channel creation
- [ ] ProgressReporter.start() called at turn start (ON_MESSAGE hook or explicit call)
- [ ] ProgressReporter.stop() called in cleanup (finally block in daemon turn)
- [ ] When progress_enabled=False: no ProgressReporter created
- [ ] Integration test: bootstrap with progress_enabled and verify hook registration

See docs/progress-reporting-research.md S3.7, S4
