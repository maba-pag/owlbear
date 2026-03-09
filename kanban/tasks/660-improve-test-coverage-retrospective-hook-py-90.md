---
id: 660
title: 'Improve test coverage: retrospective_hook.py (90%)'
status: done
priority: important
created: 2026-03-08T01:59:20.1621693+01:00
updated: 2026-03-08T04:01:20.0078479+01:00
started: 2026-03-08T04:01:20.0078479+01:00
completed: 2026-03-08T04:01:20.0078479+01:00
tags:
    - coverage-sprint
    - hooks
    - test
class: standard
---

## Coverage Gap
Current: 90% (11 of 109 statements uncovered)
Missing lines: 94, 118, 143, 150, 153-154, 157, 159, 185-187

## Acceptance Criteria
- [ ] Coverage >= 95% for src/owlbear/core/retrospective_hook.py
- [ ] Tests cover uncovered branches in the RetroFindings structured agent flow
- [ ] Tests cover the fire-and-forget asyncio.create_task path
- [ ] Tests cover edge cases: trivial task filtering, KG ingestion errors
- [ ] All new tests pass, ruff clean
