---
id: 492
title: Improve bootstrap error reporting with structured startup summary
status: archived
priority: important
created: 2026-03-04T07:38:07.6659001+01:00
updated: 2026-03-09T20:33:22.09716+01:00
started: 2026-03-06T23:23:21.4960048+01:00
completed: 2026-03-09T20:33:22.09716+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

SUPERSEDED: Split into #668 (impl), #669 (tests), #670 (config). Original scope combined data model, 9 exception-site modifications, severity classification, config setting, and channel delivery -- too many concerns for one task. See docs/bootstrap-startup-summary-research.md for full research.

[[2026-03-09]] Mon 20:33
## Audit
SUPERSEDED parent task. Split into #668, #669, #670  all three archived (.97 confidence).
No AC of its own; all implementation was delegated to child tasks.

### Verification
- #668 (impl): archived
- #669 (tests): archived
- #670 (config): archived
- Full suite: 1334 passed, 2 skipped, 1 pre-existing failure
- Ruff: 3 pre-existing issues, none from this task

### Confidence: .97
### Action: archive
