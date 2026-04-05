# HookRegistry reaction_executors TDD RED Tests

> **Owning task:** #994 — Test: HookRegistry reaction_executors attribute (TDD RED)
> **Parent task:** #991 — Expose reaction_executors dict from build_hooks via HookRegistry attribute
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

Task #994 is the TDD RED companion of #991. Validates that the AC is testable,
the target test files exist and accept the new classes, and tests will fail on
HEAD (no `reaction_executors` attribute exists yet in source).

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | `src/owlbear/core/hooks.py` HookRegistry `__init__` (L177) | 1.0 | Only sets `_handlers`; no `reaction_executors` attribute [S1] |
| S2 | `src/owlbear/bootstrap/hooks.py` `build_hooks()` (L27-85) | 1.0 | Creates executors dict locally (L62-65) but does not expose it [S2] |
| S3 | `tests/test_hooks.py` (7 test classes, ends at L186) | 1.0 | Target file for HookRegistry attribute tests [S3] |
| S4 | `tests/test_bootstrap.py` `TestFromAC_BuildHooksHookReactions` (L3035) | 1.0 | Existing pattern for build_hooks reaction tests [S4] |
| S5 | `tests/test_955_hook_reaction_schema_bootstrap.py` `TestFromAC_955_BuildHooksReturnContract` (L212) | 1.0 | Existing 2-tuple return-contract tests [S5] |
| S6 | `docs/research/expose-reaction-executors.md` | 1.0 | Parent research doc, section 3.3 testing strategy [S6] |
| S7 | `src/owlbear/core/hook_reaction_router.py` HookReactionRouter (L38-104) | 1.0 | Router stores `_executors` dict; registration is via `.register(hooks)` [S7] |

## 3. Analysis

### 3.1 Theoretical validity

The AC specifies 8 concrete test methods across 2 classes, each with a single
assertion target. Every test maps directly to an AC line in #991. Sound.

### 3.2 RED phase feasibility

`reaction_executors` does not exist in any source file (`grep` confirmed). Tests
accessing `HookRegistry().reaction_executors` will raise `AttributeError` on
HEAD. Tests asserting `build_hooks()` returns a registry with that attribute will
also fail. RED phase requirement (AC3) is automatically satisfied. [S1, S2]

### 3.3 Architecture fit

| Dimension | Assessment |
|-----------|------------|
| Target files exist | `tests/test_hooks.py` and `tests/test_bootstrap.py` both exist and are active |
| Import paths clear | `from owlbear.core.hooks import HookRegistry` (test_hooks.py L9); `from owlbear.bootstrap.hooks import build_hooks` (test_bootstrap.py L15) |
| Naming convention | `TestFromAC_991_*` follows project pattern (`TestFromAC_{parent}_{Topic}`) |
| No cross-class dependencies | The 2 test classes are independent; registry attribute tests don't need build_hooks |
| Identity check (AC line 2e) | Router constructor stores `_executors` by reference [S7]; the `is` check is valid because `build_hooks` should pass the same dict to both router and registry |

### 3.4 Test placement and patterns

| AC Test | Existing pattern to follow | File |
|---------|---------------------------|------|
| `test_reaction_executors_defaults_to_none` | `TestHookRegistryClear.test_clear` — instantiate bare `HookRegistry()` [S3] | `test_hooks.py` |
| `test_reaction_executors_is_settable` | Direct attribute assignment, standard Python protocol test | `test_hooks.py` |
| `test_reaction_executors_is_dict_when_reactions_configured` | `TestFromAC_BuildHooksHookReactions` — create OwlBearSettings with hook_reactions, call build_hooks [S4] | `test_bootstrap.py` |
| `test_reaction_executors_none_when_no_reactions` | Same pattern, empty hook_reactions [S4, S5] | `test_bootstrap.py` |
| `test_reaction_executors_is_same_object_passed_to_router` | Need to patch/capture HookReactionRouter constructor arg and assert `is` [S7] | `test_bootstrap.py` |
| `test_build_hooks_return_contract_still_two_tuple` | `TestFromAC_955_BuildHooksReturnContract.test_build_hooks_with_reactions_returns_tuple` [S5] | `test_bootstrap.py` |

### 3.5 Risk assessment

| Risk | Likelihood | Mitigation |
|------|:----------:|------------|
| Import path changes before test-writer runs | Low | #991 AC says only 2 lines change; no import paths affected |
| Router identity test is fragile | Low | `build_hooks` creates the dict locally; test patches `HookReactionRouter.__init__` to capture the arg |

## 4. Recommendation (.90 confidence)

Approve task #994 for test-writer. The AC is concrete, each test method maps
to a verifiable behavior in #991, both target files exist, and RED phase is
guaranteed because the attribute doesn't exist in source. No blockers.

The test-writer should follow the `OwlBearSettings` + `build_hooks()` pattern
from `TestFromAC_BuildHooksHookReactions` [S4] for the bootstrap tests, and the
bare `HookRegistry()` instantiation pattern from `TestHookRegistrySync` [S3] for
the core attribute tests.

## 5. Follow-up Tasks

No new tasks needed — #994 is itself the follow-up from #991's architect review.
The test-writer picks up #994 directly.
