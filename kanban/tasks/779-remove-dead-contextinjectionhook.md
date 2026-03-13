---
id: 779
title: Remove dead ContextInjectionHook
status: backlog
priority: nice-to-have
created: 2026-03-13T14:22:35.8804748+01:00
updated: 2026-03-13T15:00:36.991394+01:00
started: 2026-03-13T14:58:19.8658834+01:00
tags:
    - agent
    - scope:core
    - cleanup
claimed_by: researcher
claimed_at: 2026-03-13T15:00:36.991394+01:00
class: standard
---

Delete ContextInjectionHook class, bootstrap registration, and tests since both outputs (instructions, kanban_summary) have zero readers. instructions is redundant with ContextManager; kanban_summary is superseded by BoardContextProvider (#770/#771). See docs/research/context-injection-hook-dead-code.md.

AC:
- [ ] src/owlbear/core/context_hook.py deleted
- [ ] ContextInjectionHook() removed from src/owlbear/bootstrap/hooks.py
- [ ] tests/test_context_hook.py deleted or tests removed
- [ ] ContextInjectionHook test removed from tests/test_session_hooks.py
- [ ] SessionStartData.context field retained (other hooks may use it)
- [ ] All existing tests pass (no regressions)
- [ ] ruff clean
