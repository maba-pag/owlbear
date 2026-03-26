# Architecture Review for #779

**Verdict:** REFINE

## AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| src/owlbear/core/context_hook.py deleted | Precise, but incomplete on its own. The deletion also requires removing direct test references and the test-run elimination inventory entry. | Keep and expand surrounding AC. |
| ContextInjectionHook() removed from src/owlbear/bootstrap/hooks.py | Central invariant, but stale as a work item because src/owlbear/bootstrap/hooks.py already omits this registration today. | Keep as a must-remain-absent constraint, not new feature work. |
| tests/test_context_hook.py deleted or tests removed | Correct target, but "or tests removed" is ambiguous and misses the meta-test inventory cleanup in tests/test_run_elimination.py. | Rewrite. |
| ContextInjectionHook test removed from tests/test_session_hooks.py | Correct but incomplete; tests/test_hook_consumer_types.py also imports the soon-to-be-deleted module. | Rewrite. |
| SessionStartData.context field retained (other hooks may use it) | Precise and still required. tests/test_hook_payloads.py asserts the field remains on SessionStartData. | Keep. |
| All existing tests pass (no regressions) | Too broad and not mechanically useful for this scoped cleanup. | Replace with scoped pytest verification. |
| ruff clean | Too broad for the repo's existing lint debt. | Replace with scoped ruff verification. |

## Architecture Notes

- Live prompt injection already happens per turn via BoardContextProvider in src/owlbear/core/agent.py and bootstrap wiring in src/owlbear/bootstrap/__init__.py. This task must not add a second SESSION_START prompt path.
- src/owlbear/bootstrap/hooks.py already registers zero ContextInjectionHook handlers on SESSION_START. The cleanup scope is the dead module and its direct test references, not a new behavior change.
- Remaining direct references are in tests/test_context_hook.py, tests/test_session_hooks.py, tests/test_hook_consumer_types.py, and tests/test_run_elimination.py.
- SessionStartData.context in src/owlbear/core/hooks.py remains part of the generic SESSION_START payload contract and is still asserted by tests/test_hook_payloads.py.
- TDD predecessor #858 exists and was added as a dependency; this task stays in backlog because the contract needed tightening and the board already has overlapping cleanup tasks (#772 approved todo, #884 backlog).

## Changes Made

- Rewrote #779 from a loose cleanup note into a removal-only contract.
- Added dependency on #858.
- Recorded overlap with #772 and #884 while leaving this task in backlog.

## Dependencies

- Added/Removed/Verified: added #858; verified BoardContextProvider is already wired via src/owlbear/core/agent.py and src/owlbear/bootstrap/__init__.py; verified bootstrap no longer registers ContextInjectionHook; verified direct test references remain in tests/test_context_hook.py, tests/test_session_hooks.py, tests/test_hook_consumer_types.py, and tests/test_run_elimination.py; verified SessionStartData.context is still required by tests/test_hook_payloads.py.