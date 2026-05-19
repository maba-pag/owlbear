---
id: 971
title: Add RED tests for anti-pattern taxonomy reference
status: archived
priority: nice-to-have
created: 2026-03-24T00:07:25.8570092+01:00
updated: 2026-03-24T00:34:37.7312806+01:00
started: 2026-03-24T00:34:37.7312806+01:00
completed: 2026-03-24T00:34:37.7312806+01:00
tags:
    - ui
    - agent
    - test
    - scope:copilot
    - type:test
parent: 938
class: standard
---

## Context

Verify that the anti-pattern taxonomy reference file exists, is integrated into the skill, and contains the required two-tier structure.

## Acceptance Criteria

- [ ] Test asserts references/anti-patterns.md exists in the skill package
- [ ] Test asserts SKILL.md reference table includes anti-patterns.md
- [ ] Test asserts file contains both universal blockers and taste heuristics sections
- [ ] Test asserts file references NOTICE.md or cites prior art attribution
- [ ] Update _EXPECTED_REFERENCE_FILES to include anti-patterns.md

See docs/research/frontend-anti-pattern-taxonomy.md for details.
