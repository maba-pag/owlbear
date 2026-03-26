---
id: 779
title: Remove dead ContextInjectionHook
status: backlog
priority: nice-to-have
created: 2026-03-13T14:22:35.8804748+01:00
updated: 2026-03-25T19:57:59.3962486+01:00
started: 2026-03-13T14:58:19.8658834+01:00
tags:
    - agent
    - scope:core
    - cleanup
depends_on:
    - 858
class: standard
---

Resolve the obsolete ContextInjectionHook path by removing the dead hook rather than wiring SESSION_START context into prompts. The live board-context injection path is already per-turn via BoardContextProvider in src/owlbear/core/agent.py and bootstrap wiring in src/owlbear/bootstrap/__init__.py.

## Goal

Remove dead ContextInjectionHook code and all direct test references without reintroducing session-start prompt injection.

## Scope

Core hook cleanup only. Preserve SessionStartData.context in src/owlbear/core/hooks.py for other SESSION_START hooks and future payload extensions. Do not change BoardContextProvider, OwlBearAgent.turn() instruction concatenation, bootstrap board-context wiring, or lessons injection behavior.

## AC

- [ ] src/owlbear/core/context_hook.py deleted
- [ ] src/owlbear/bootstrap/hooks.py does not import or register ContextInjectionHook
- [ ] No new SESSION_START prompt-injection path is added; board-state prompt injection remains exclusively the BoardContextProvider path already used by src/owlbear/core/agent.py and wired from src/owlbear/bootstrap/__init__.py
- [ ] src/owlbear/core/hooks.py retains SessionStartData.context unchanged
- [ ] tests/test_bootstrap.py keeps TestFromAC_ContextInjectionHookRemoval green without weakening assertions
- [ ] tests/test_context_hook.py deleted
- [ ] tests/test_session_hooks.py removes the ContextInjectionHook integration case
- [ ] tests/test_hook_consumer_types.py removes ContextInjectionHook-specific typed-consumer assertions and no-isinstance-guard assertions
- [ ] tests/test_run_elimination.py removes tests/test_context_hook.py from IN_SCOPE_FILES
- [ ] After the change, no test imports owlbear.core.context_hook or ContextInjectionHook
- [ ] Scoped verification passes: uv run pytest tests/test_bootstrap.py tests/test_hook_payloads.py tests/test_hook_consumer_types.py tests/test_session_hooks.py tests/test_run_elimination.py -q --tb=short
- [ ] Scoped verification passes: uv run ruff check src/owlbear/core/hooks.py src/owlbear/bootstrap/hooks.py tests/test_bootstrap.py tests/test_hook_payloads.py tests/test_hook_consumer_types.py tests/test_session_hooks.py tests/test_run_elimination.py

## Dependencies

- TDD RED task: #858
- Existing per-turn board-context path from #770/#771 remains the only prompt-injection path

[[2026-03-21]] Sat 03:25
## Architecture Review

See docs/scratch/779-architect.md for full review.
