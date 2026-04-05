---
id: 749
title: Implement LessonsInjectionHook for session-start context
status: archived
priority: nice-to-have
created: 2026-03-12T10:48:10.5580119+01:00
updated: 2026-03-12T20:00:55.5410708+01:00
started: 2026-03-12T20:00:55.5410708+01:00
completed: 2026-03-12T20:00:55.5410708+01:00
tags:
    - hooks
    - agent
    - scope:core
class: standard
---

Implement a SESSION_START hook that reads recent curated lessons from .owlbear/lessons/ and injects them into agent context.

Ref: docs/research/olanetsoft-workflow.md (task #747)

AC:
- [ ] New hook class LessonsInjectionHook in src/owlbear/core/lessons_hook.py
- [ ] Reads .md files from configured lessons directory (default: workspace/.owlbear/lessons/)
- [ ] Token-budgeted injection (max 500 tokens) to prevent context bloat
- [ ] Registered in bootstrap/hooks.py alongside existing hooks
- [ ] Unit tests in tests/test_lessons_hook.py
- [ ] Gated behind settings.lessons_injection_enabled (default False)
