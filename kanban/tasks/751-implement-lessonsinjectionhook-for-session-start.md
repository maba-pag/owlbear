---
id: 751
title: Implement LessonsInjectionHook for session-start context
status: backlog
priority: nice-to-have
created: 2026-03-12T10:48:47.8860851+01:00
updated: 2026-03-12T10:49:00.4618273+01:00
tags:
    - hooks
    - agent
    - scope:core
class: standard
---

Implement a SESSION_START hook that reads recent curated lessons from .owlbear/lessons/ and injects them into agent context.

Ref: docs/research/olanetsoft-workflow-research.md (task #747)

AC:
- [ ] New hook class LessonsInjectionHook in src/owlbear/core/lessons_hook.py
- [ ] Reads .md files from configured lessons directory (default: workspace/.owlbear/lessons/)
- [ ] Token-budgeted injection (max 500 tokens) to prevent context bloat
- [ ] Registered in bootstrap/hooks.py alongside existing hooks
- [ ] Unit tests in tests/test_lessons_hook.py
- [ ] Gated behind settings.lessons_injection_enabled (default False)
