---
id: 884
title: Resolve ContextInjectionHook dead code by removing the hook
status: archived
priority: nice-to-have
created: 2026-03-13T10:40:31.8341587+01:00
updated: 2026-03-25T19:57:53.9601776+01:00
started: 2026-03-13T14:09:46.3517339+01:00
completed: 2026-03-25T19:57:53.9601776+01:00
tags:
    - agent
    - scope:core
    - bug
    - cleanup
depends_on:
    - 858
class: standard
---

Resolve the obsolete ContextInjectionHook path by removing the hook rather than wiring kanban_summary into prompts. The live board-context injection path is already per-turn via BoardContextProvider in src/owlbear/core/agent.py and bootstrap wiring in src/owlbear/bootstrap/__init__.py; do not add a second SESSION_START prompt path.

## Goal

Remove the dead ContextInjectionHook and its obsolete tests.

## Scope

Core hook cleanup only. Preserve SessionStartData.context in src/owlbear/core/hooks.py for other SESSION_START hooks and future payload extensions. Do not change BoardContextProvider, agent turn concatenation, or lessons injection behavior.

## AC

- [ ] src/owlbear/core/context_hook.py deleted
- [ ] src/owlbear/bootstrap/hooks.py no longer imports or registers ContextInjectionHook
- [ ] No new SESSION_START prompt-injection path is added; board-state prompt injection remains exclusively the BoardContextProvider path already used by src/owlbear/core/agent.py and wired from src/owlbear/bootstrap/__init__.py
- [ ] src/owlbear/core/hooks.py retains SessionStartData.context unchanged
- [ ] tests/test_bootstrap.py stops expecting a default ContextInjectionHook SESSION_START registration and instead verifies the obsolete handler is absent
- [ ] tests/test_context_hook.py removed
- [ ] tests/test_session_hooks.py removes the ContextInjectionHook integration case
- [ ] tests/test_hook_consumer_types.py removes ContextInjectionHook-specific typed-consumer assertions
- [ ] Scoped verification passes: uv run pytest tests/test_bootstrap.py tests/test_session_hooks.py tests/test_hook_consumer_types.py tests/test_lessons_hook.py tests/test_hook_payloads.py -q --tb=short
- [ ] Scoped verification passes: uv run ruff check src/owlbear/bootstrap/hooks.py src/owlbear/core/hooks.py tests/test_bootstrap.py tests/test_session_hooks.py tests/test_hook_consumer_types.py tests/test_lessons_hook.py tests/test_hook_payloads.py

## Dependencies

- TDD RED task: #858
- Existing per-turn board-context path from #770/#771 remains the only prompt-injection path

[[2026-03-13]] Fri 14:22

## Research

- Doc: docs/research/context-injection-hook-dead-code.md
- Both outputs (instructions, kanban_summary) are dead: zero readers in src/
- instructions redundant with ContextManager (DRY violation)
- kanban_summary superseded by BoardContextProvider (#770/#771)
- Recommendation (.90): Remove hook entirely (Option A)
- Overlapping backlog task: #779 (not modified in this review)
- Confidence: .90

## Architecture Review

__Verdict:__ REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Either remove the dead code or wire it through. | Not verifiable and now architecturally incorrect. src/owlbear/core/agent.py and src/owlbear/bootstrap/__init__.py already use BoardContextProvider as the live prompt-injection path. | Rewrote #772 into a removal-only implementation task and added RED predecessor #858. |
| Research points to #779 while #772 remained active. | Overlapping implementation scope exists on the board. Cross-task boundary prevented merge/delete work in this invocation. | Recorded #779 as overlapping and kept #772 as the refined surviving contract. |

### Architecture Notes

- src/owlbear/core/context_hook.py writes data[context] but the current codebase has zero production readers for that payload.
- src/owlbear/bootstrap/hooks.py is the only production registration site for ContextInjectionHook.
- src/owlbear/core/agent.py and src/owlbear/bootstrap/__init__.py already establish the per-turn BoardContextProvider path; adding SESSION_START prompt wiring would create a second, staler injection mechanism.
- The research follow-up understated the test blast radius. Removal must also update tests/test_hook_consumer_types.py in addition to tests/test_context_hook.py and tests/test_session_hooks.py.
- Single domain verified: core hook cleanup only. No new board-context feature work is included.

### Failure Mode Map

| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| build_hooks() SESSION_START registration | Obsolete ContextInjectionHook remains registered | none | No in current state; task removes it | Dead code remains wired and stale behavior/tests stay in place |
| lessons-enabled SESSION_START path | Removing the obsolete hook accidentally suppresses LessonsInjectionHook registration | none | Must be covered by #858 and existing lessons tests | Session-start lessons context missing when the feature is enabled |
| typed hook consumer tests | Stale imports/assertions for ContextInjectionHook remain after module deletion | ImportError / assertion failure | Must be updated in task scope | Targeted test suite fails despite correct runtime cleanup |

### Changes Made

- Created #858 as the TDD RED predecessor for removal behavior.
- Rewrote #772 title/body from ambiguous wire-or-remove wording to a removal-only contract.
- Added depends_on: #858.
- Added cleanup tag.
- Preserved the research note and recorded overlap with #779 without modifying #779.

### Dependencies

- Added: #858.
- Verified: src/owlbear/core/agent.py and src/owlbear/bootstrap/__init__.py already provide the live BoardContextProvider path.
- Noted: #779 overlaps in scope but was not merged in this single-task review.

[[2026-03-25]] Wed 19:57

## Board Triage (2026-03-25)

Archived as duplicate of #779.
