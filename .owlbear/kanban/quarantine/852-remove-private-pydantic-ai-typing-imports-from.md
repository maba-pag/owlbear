---
id: 852
title: Remove private pydantic-ai typing imports from OwlBear
status: archived
priority: important
created: 2026-03-18T13:45:31.3408243+01:00
updated: 2026-03-23T17:54:00.9838527+01:00
started: 2026-03-23T17:54:00.9838527+01:00
completed: 2026-03-23T17:54:00.9838527+01:00
tags:
    - deps
    - agent
    - tooling
depends_on:
    - 854
claimed_by: builder
claimed_at: 2026-03-23T17:53:15.3901144+01:00
class: standard
---

Board cleanup only. The original import-hygiene work requested by this task is already present in the repository: src/owlbear/core/agent.py, src/owlbear/tools/hooked.py, and src/owlbear/safety/gate.py no longer use private pydantic_ai._* typing imports, and tests/test_pydantic_ai_typing_imports.py plus the existing history_processors runtime coverage already lock that contract down. This task now exists only to retire the stale backlog card without redispatching duplicate code changes.

## AC

- [ ] Append a one-line closure note to #852 stating that src/owlbear/core/agent.py, src/owlbear/tools/hooked.py, src/owlbear/safety/gate.py, and tests/test_pydantic_ai_typing_imports.py already satisfy the original public typing-import contract, and that #854 is the archived RED/source-of-truth task for that regression coverage.
- [ ] The closure note cites #854 and tests/test_pydantic_ai_typing_imports.py.
- [ ] Archive #852 after appending the closure note.
- [ ] No src/, tests/, or other kanban task files are modified.

[[2026-03-23]] Mon 16:57

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Closure note states the repo already satisfies the original import-hygiene contract and cites #854 plus tests/test_pydantic_ai_typing_imports.py | Precise, verifiable self-closure of a stale backlog task. | Keep |
| The closure note cites #854 and tests/test_pydantic_ai_typing_imports.py | Preserves provenance for why the implementation card is now closure-only. | Keep |
| Archive #852 after appending the closure note | Clear terminal state for the stale implementation card. | Keep |
| No src/, tests/, or other kanban task files are modified | Keeps the task in a single board-cleanup domain and avoids duplicate code churn. | Keep |

### Architecture Notes

- Verified current repo state already satisfies the original implementation scope: src/owlbear/tools/hooked.py and src/owlbear/safety/gate.py import RunContext from the public pydantic_ai package, and src/owlbear/core/agent.py defines a local HistoryProcessor alias using public RunContext and ModelMessage types.
- Verified a workspace search under src/owlbear finds no remaining TYPE_CHECKING imports from pydantic_ai._* modules.
- Verified tests/test_pydantic_ai_typing_imports.py now contains both the original import-hygiene assertions and stricter callable-shape checks for the HistoryProcessor alias, while tests/test_agent.py still carries the runtime forwarding contract.
- Verified #854 is archived, so the RED contract already exists and the live code/test state matches it.
- The original #852 scope spans both core/safety and tools domains, and the requested code changes are already present in HEAD. Re-dispatching it as implementation work would duplicate shipped behavior and create avoidable board churn.
- Rewriting #852 as a closure-only task is the narrowest correct action. No TDD predecessor is required because the rewritten task forbids src/ and test changes.

### Changes Made

- Claimed #852 as architect.
- Rewrote #852 into a self-closure board-cleanup task because the original implementation is already present in the repository.
- Appended this architecture review.
- Prepared #852 for backlog -> todo handoff as a closure-only task.

### Dependencies

- Added/Removed/Verified: verified #854 is archived and tests/test_pydantic_ai_typing_imports.py exists; no new board dependency is required.

[[2026-03-23]] Mon 17:09

## Test-Writer Notes

- Non-implementation task (board cleanup only) - AC explicitly forbids src/, tests/, or kanban task modifications.
- Architecture Review confirms: No TDD predecessor is required because the rewritten task forbids src/ and test changes.
- Passing through to builder for closure note and archive.

[[2026-03-23]] Mon 17:52
Closure: src/owlbear/core/agent.py, src/owlbear/tools/hooked.py, and src/owlbear/safety/gate.py already satisfy the original public typing-import contract; #854 is the archived RED/source-of-truth task and tests/test_pydantic_ai_typing_imports.py locks the regression coverage down.

[[2026-03-23]] Mon 17:53
Closure: src/owlbear/core/agent.py, src/owlbear/tools/hooked.py, and src/owlbear/safety/gate.py already satisfy the original public typing-import contract. #854 is the archived RED/source-of-truth task and tests/test_pydantic_ai_typing_imports.py locks the regression coverage down.
