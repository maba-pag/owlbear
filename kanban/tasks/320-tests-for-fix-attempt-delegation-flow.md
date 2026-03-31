---
id: 320
title: Tests for fix-attempt delegation flow
status: ideation
priority: needed
created: 2026-03-30T20:38:27.954547+02:00
updated: 2026-03-30T20:38:27.954547+02:00
tags:
    - scope:agents
    - test
    - phase-2
depends_on:
    - 318
class: standard
---

AC:
1. Unit tests verify retry_hint construction from error output
2. Test fix-attempt input contract validation
3. Test builder delegates after exactly 2 failures (not 1, not 3)
4. Test FIXED result triggers final verify + continue
5. Test FAILED result triggers BLOCK
6. Test fix-attempt never receives kanban tools
See docs/research/fresh-context-retry-builder.md
