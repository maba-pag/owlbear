---
id: 772
title: 'Fix ContextInjectionHook: wire kanban_summary to system prompt'
status: archived
priority: nice-to-have
created: 2026-03-13T10:40:31.8341587+01:00
updated: 2026-03-25T19:57:46.6416865+01:00
started: 2026-03-13T14:09:46.3517339+01:00
completed: 2026-03-25T19:57:46.6416865+01:00
tags:
    - agent
    - scope:core
    - bug
depends_on:
    - 858
class: standard
---

ContextInjectionHook stores kanban_summary in event data['context'] but this is NOT wired into the agent system prompt. Either remove the dead code or wire it through. See docs/research/compact-board-context.md S3.3.

[[2026-03-13]] Fri 14:22
## Research
- Doc: docs/research/context-injection-hook-dead-code.md
- Both outputs (instructions, kanban_summary) are dead: zero readers in src/
- instructions redundant with ContextManager (DRY violation)
- kanban_summary superseded by BoardContextProvider (#770/#771)
- Recommendation (.90): Remove hook entirely (Option A)
- Follow-up: #779 (Remove dead ContextInjectionHook) at ideation
- Confidence: .90

[[2026-03-21]] Sat 02:55
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| ContextInjectionHook stores kanban_summary in event data['context'] but this is not wired into the agent system prompt | Accurate dead-code observation. src/owlbear/core/context_hook.py still writes data['context'], and src/ has no readers for that payload. | Keep as background only |
| Either remove the dead code or wire it through | Not verifiable and architecturally obsolete. src/owlbear/core/agent.py already injects board context per turn via BoardContextProvider, and src/owlbear/bootstrap/hooks.py no longer registers ContextInjectionHook. | Rewrite to removal-only cleanup contract |
| See docs/research/compact-board-context.md S3.3 | Useful historical pointer, but docs/research/context-injection-hook-dead-code.md is the direct research artifact for this task and explicitly recommends removal. | Narrow to the direct removal recommendation |

### Architecture Notes
- BoardContextProvider in src/owlbear/core/agent.py already owns the live board-context injection path. Reintroducing session-start kanban_summary wiring would create a second, stale, inferior path.
- build_hooks() in src/owlbear/bootstrap/hooks.py already registers zero ContextInjectionHook handlers on SESSION_START. That runtime absence is the behavior to preserve.
- The remaining dead artifacts are src/owlbear/core/context_hook.py and direct test references in tests/test_context_hook.py, tests/test_session_hooks.py, tests/test_hook_consumer_types.py, and tests/test_run_elimination.py.
- Preserve SessionStartData.context in src/owlbear/core/hooks.py. tests/test_hook_payloads.py still encodes that generic SESSION_START payload contract, and removal of the hook does not justify removing the field.
- TDD compliance is satisfied by #858, which provides the RED/behavioral guard that ContextInjectionHook must stay unregistered in bootstrap. This task is the implementation cleanup that follows that test contract.
- No failure-mode table is needed here because the current runtime no longer routes through ContextInjectionHook; this task removes dead code and obsolete direct tests rather than adding a new production codepath.

### Refined Builder Contract
- Delete src/owlbear/core/context_hook.py.
- After the change, no file under src/ imports or references owlbear.core.context_hook or ContextInjectionHook.
- Preserve the current bootstrap behavior: src/owlbear/bootstrap/hooks.py continues to register zero ContextInjectionHook handlers on SESSION_START.
- Delete tests/test_context_hook.py and remove the ContextInjectionHook-specific sections from tests/test_session_hooks.py and tests/test_hook_consumer_types.py.
- After the change, no test imports owlbear.core.context_hook or ContextInjectionHook.
- Update tests/test_run_elimination.py so IN_SCOPE_FILES no longer references tests/test_context_hook.py.
- Retain SessionStartData.context in src/owlbear/core/hooks.py.
- Do not modify src/owlbear/core/agent.py, src/owlbear/core/board_context.py, src/owlbear/bootstrap/__init__.py, or OwlBearSettings in this task.
- Keep tests/test_bootstrap.py::TestFromAC_ContextInjectionHookRemoval green without weakening assertions.
- Task-scoped pytest covering tests/test_bootstrap.py, tests/test_hook_payloads.py, tests/test_hook_consumer_types.py, tests/test_session_hooks.py, and tests/test_run_elimination.py passes.
- ruff check passes for every changed file.

### Changes Made
- Claimed #772 as architect.
- Added dependency on #858 as the required RED predecessor.
- Approved #772 using the refined cleanup contract above because the original title/body are stale relative to the current codebase and research.
- Left duplicate backlog task #779 untouched per cross-task boundary rules.

### Dependencies
- Added/Removed/Verified: added #858; verified src/owlbear/core/agent.py already injects board context per turn; verified src/owlbear/bootstrap/hooks.py already omits ContextInjectionHook registration; verified src/owlbear/core/context_hook.py remains as dead code; verified duplicate cleanup task #779 exists but was not modified.

[[2026-03-25]] Wed 19:57
## Board Triage (2026-03-25)
Archived as won't-do: research concluded hook should be removed (not wired). See #779 for the removal task.
