---
id: 972
title: Create anti-pattern taxonomy reference file
status: archived
priority: nice-to-have
created: 2026-03-24T00:07:33.997887+01:00
updated: 2026-03-24T00:34:43.3735669+01:00
started: 2026-03-24T00:34:43.3735669+01:00
completed: 2026-03-24T00:34:43.3735669+01:00
tags:
    - ui
    - agent
    - scope:copilot
    - docs
    - type:docs
parent: 938
depends_on:
    - 971
class: standard
---

## Context

Implement the anti-pattern taxonomy as a reference file in the frontend-design skill package.

## Acceptance Criteria

- [ ] Add references/anti-patterns.md with two-tier classification (universal blockers vs taste heuristics)
- [ ] Universal blockers section includes WCAG SC citations for each item (2.4.7, 1.4.3, 2.5.5, 3.3.2, etc.)
- [ ] Taste heuristics section frames items as illustrative examples of AI-slop, not absolute bans
- [ ] Add anti-patterns row to SKILL.md reference table
- [ ] Add attribution header referencing NOTICE.md
- [ ] Update _EXPECTED_REFERENCE_FILES in tests/test_frontend_design_skill.py to include anti-patterns.md
- [ ] All existing tests still pass

See docs/research/frontend-anti-pattern-taxonomy.md for details.
