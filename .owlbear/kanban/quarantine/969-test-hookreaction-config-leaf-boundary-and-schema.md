---
id: 969
title: Test HookReaction config leaf boundary and schema ownership
status: archived
priority: important
created: 2026-03-23T13:03:04.2447092+01:00
updated: 2026-03-23T21:45:15.4359783+01:00
started: 2026-03-23T21:45:08.0747141+01:00
completed: 2026-03-23T21:45:08.0747141+01:00
tags:
    - agent
    - hooks
    - test
    - config
    - scope:core
    - type:test
parent: 950
class: standard
---

Write tests FIRST for HookReaction config leaf boundary and schema ownership.

## AC

- [ ] File: updated tests/test_config.py
- [ ] File: updated tests/test_hook_reaction_router.py
- [ ] Test: source inspection proves src/owlbear/config.py does not import any owlbear module, including src/owlbear/core/hook_reaction_router.py
- [ ] Test: HookReactionRule and any hook_reaction action/schema types used by OwlBearSettings are declared in src/owlbear/config.py, and OwlBearSettings parses hook_reactions into those config-owned models while preserving rule and action order
- [ ] Test: HookReactionRouter consumes config-owned rule objects without defining a duplicate HookReactionRule schema in src/owlbear/core/hook_reaction_router.py
- [ ] ruff clean

## Architecture

- This RED task protects the config.py leaf invariant from architecture-standards.
- Router matching, registration, and executor error-handling behavior remain covered by #965.
Research: docs/research/hookreaction-schema-router-wiring.md

[[2026-03-23]] Mon 15:59

## Architecture Review

**Verdict:** Approved

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| File: updated tests/test_config.py | Matches the existing repo split: OwlBearSettings and config invariants already live in tests/test_config.py | Kept |
| File: updated tests/test_hook_reaction_router.py | Matches the dedicated router contract file introduced by #965, so schema-ownership assertions stay with the router surface | Kept |
| Test: source inspection proves src/owlbear/config.py does not import any owlbear module, including src/owlbear/core/hook_reaction_router.py | Precise, mechanically verifiable guard for the config leaf invariant from architecture-standards | Kept |
| Test: HookReactionRule and any hook_reaction action/schema types used by OwlBearSettings are declared in src/owlbear/config.py, and OwlBearSettings parses hook_reactions into those config-owned models while preserving rule and action order | Precise ownership contract for the config models and the order-preserving parse behavior that #955 must implement | Kept |
| Test: HookReactionRouter consumes config-owned rule objects without defining a duplicate HookReactionRule schema in src/owlbear/core/hook_reaction_router.py | Correctly protects the config-to-core dependency direction and complements, rather than duplicates, the behavior coverage already provided by #965 | Kept |
| ruff clean | Standard RED gate for the touched test files | Kept |

### Architecture Notes

- src/owlbear/config.py currently imports HookReactionRule from src/owlbear/core/hook_reaction_router.py, which violates the config leaf rule in architecture-standards. This RED task is aimed at the correct failure seam.
- tests/test_config.py already contains AST/source-inspection regression guards, so it is the right place to prove config.py has no owlbear imports.
- tests/test_hook_reaction_router.py is already the focused router-contract file from #965, so adding schema-ownership assertions there preserves the existing test boundary instead of spreading router checks into bootstrap tests.
- This remains one focused core-domain task: it protects the hook-reaction schema ownership boundary between config.py and core/, not multiple unrelated concerns.

### Changes Made

- Claimed #969 for architecture review.
- Verified the research doc and current seams in src/owlbear/config.py, src/owlbear/core/hook_reaction_router.py, tests/test_config.py, and tests/test_hook_reaction_router.py.
- Approved #969 for RED implementation.

### Dependencies

- Verified: #955 depends on #969.
- Verified: #965 is already archived, so #969 extends the existing router test file without creating parallel RED overlap.
- Verified: docs/research/hookreaction-schema-router-wiring.md remains the governing design input.

[[2026-03-23]] Mon 16:52

## Test-Writer Notes

- Test file: tests/test_config.py (class TestFromAC_ConfigLeafHookReactionSchema)
- Test file: tests/test_hook_reaction_router.py (class TestFromAC_RouterConsumesConfigOwnedRules)
- Classes: TestFromAC_ConfigLeafHookReactionSchema, TestFromAC_RouterConsumesConfigOwnedRules
- Tests per category: happy 1, edge 0, error 2, boundary 5
- Total: 8 tests, all FAIL checkmark
- ruff: clean
- AC coverage:
  AC1 (config.py has no owlbear imports): test_config_source_has_no_owlbear_imports [error]
  AC2 (HookReactionRule ClassDef in config.py): test_hook_reaction_rule_class_defined_in_config_source [boundary]
  AC2 (module ownership): test_hook_reaction_rule_module_attribute_is_owlbear_config [boundary]
  AC2 (parse + rule order): test_settings_parses_hook_reactions_preserving_rule_order [happy]
  AC2 (parse + action order): test_settings_parses_hook_reactions_preserving_action_order_within_rule [boundary]
  AC3 (no ClassDef in router): test_hook_reaction_rule_not_class_defined_in_router_source [error]
  AC3 (router rule module-owned by config): test_hook_reaction_rule_referenced_by_router_is_config_owned [boundary]
  AC3 (end-to-end with config-owned rule): test_router_registers_and_dispatches_with_config_owned_rule [boundary]

[[2026-03-23]] Mon 17:35

## Builder Notes

- Files changed: src/owlbear/config.py, src/owlbear/core/hook_reaction_router.py
- Change: Moved HookReactionRule class definition (and _ALLOWED_ACTIONS constant) from hook_reaction_router.py into config.py; hook_reaction_router.py now imports HookReactionRule from owlbear.config; removed pydantic import from router (no longer needed there)
- Tests: 8/8 TestFromAC tests pass (test_config.py::TestFromAC_ConfigLeafHookReactionSchema + test_hook_reaction_router.py::TestFromAC_RouterConsumesConfigOwnedRules); 296 passed in broader suite
- Coverage: 97% on hook_reaction_router.py; config.py HookReactionRule class fully covered
- Lint: ruff clean (import sort + line-length auto-fixed)
- Evidence: All 8 TestFromAC tests FAILED before, 8 PASSED after; ruff All checks passed

[[2026-03-23]] Mon 17:50

## Review Evidence

### Review: #969 - Test HookReaction config leaf boundary and schema ownership

### Test Results

- pytest AC classes: 8 passed, 0 failed (2 optional-dependency warnings).
- pytest broader related files: 123 passed, 0 failed (2 optional-dependency warnings).
- Commands run: uv run pytest tests/test_config.py::TestFromAC_ConfigLeafHookReactionSchema tests/test_hook_reaction_router.py::TestFromAC_RouterConsumesConfigOwnedRules -q --tb=short ; uv run pytest tests/test_config.py tests/test_hook_reaction_router.py -q --tb=short

### Lint Results

- Repo-wide lint: uv run ruff check src/ tests/ reports existing unrelated RUF100 debt (216 findings).
- Task-scoped lint: uv run ruff check src/owlbear/config.py src/owlbear/core/hook_reaction_router.py tests/test_config.py tests/test_hook_reaction_router.py -> All checks passed.

### Coverage

- AC-class coverage run: src/owlbear/config.py 72%, src/owlbear/core/hook_reaction_router.py 84%.
- Broader related-file coverage run: src/owlbear/config.py 79%, src/owlbear/core/hook_reaction_router.py 97%.
- Coverage context: config.py is a large shared settings module; task-introduced HookReactionRule ownership/wiring behavior is directly exercised by the new TestFromAC tests and existing HookReactionRule schema tests.

### Pass 1 - Critical Checks

- Test-writer AC coverage: COVERED for all AC lines.
  - AC no owlbear imports in config.py -> test_config_source_has_no_owlbear_imports.
  - AC HookReactionRule owned by config + OwlBearSettings order preservation -> four TestFromAC_ConfigLeafHookReactionSchema tests.
  - AC router consumes config-owned rules and no duplicate class -> three TestFromAC_RouterConsumesConfigOwnedRules tests.
  - AC ruff clean -> task-scoped ruff command passes.
- Security review: no secrets, injection sinks, unsafe deserialization, or new dependency risk in builder diff.
- Test integrity: PRESERVED.
  - Evidence: git diff --name-only 6a3b6f7..04e2685 -- tests/test_config.py tests/test_hook_reaction_router.py produced no output (builder did not modify TestFromAC files).
- Test quality: STRONG (specific AST and ownership assertions, explicit order checks, async dispatch assertions, descriptive naming, independent tests).
- Data safety: no new integrity/concurrency/persistence risks introduced.
- Implementation-aware test gaps: none significant for moved schema/router wiring; existing TestFromAC_HookReactionRuleSchema coverage remains active after move.

### AC Compliance

- File update ACs: satisfied by test-writer commit 6a3b6f7 touching tests/test_config.py and tests/test_hook_reaction_router.py.
- Config leaf import AC: satisfied by passing source-inspection test and direct source scan (no from/import owlbear in src/owlbear/config.py).
- Config-owned schema + parse/order AC: satisfied by passing ownership/order tests and current source definitions in src/owlbear/config.py.
- Router consumes config-owned schema AC: satisfied by passing router ownership/dispatch tests and router import from owlbear.config.
- Ruff clean AC: satisfied at task scope.

### Verdict

- PASS
- Confidence: .93

### Action Taken

- Append review evidence and advance #969 from review to docs.

[[2026-03-23]] Mon 18:17

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Internal refactor; no new behavior, API convention, or tech stack table changed |
| 2 | Docstrings complete | Yes | Updated | hook_reaction_router.py module docstring corrected to say Provides HookReactionRouter; re-exports HookReactionRule from owlbear.config. HookReactionRule class docstring in config.py is complete. All other public methods have docstrings. |
| 3 | sources/overview.md | No | N/A | No new external patterns; #955 research already attributed all HookReaction sources |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/hookreaction-schema-router-wiring.md exists and linked from task body |
| 6 | Scratch files cleaned | N/A | Pass | No docs/scratch/969-* files found |

### Files Updated

- src/owlbear/core/hook_reaction_router.py (module docstring only; commit 8e7d9a0)

### Scratch Files Cleaned

- None

[[2026-03-23]] Mon 18:17

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Internal refactor; no new behavior, API convention, or tech stack table changed |
| 2 | Docstrings complete | Yes | Updated | hook_reaction_router.py module docstring corrected to say Provides HookReactionRouter; re-exports HookReactionRule from owlbear.config. HookReactionRule class docstring in config.py is complete. All other public methods have docstrings. |
| 3 | sources/overview.md | No | N/A | No new external patterns; #955 research already attributed all HookReaction sources |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/hookreaction-schema-router-wiring.md exists and linked from task body |
| 6 | Scratch files cleaned | N/A | Pass | No docs/scratch/969-* files found |

### Files Updated

- src/owlbear/core/hook_reaction_router.py (module docstring only; commit 8e7d9a0)

### Scratch Files Cleaned

- None

[[2026-03-23]] Mon 21:45

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| File: updated tests/test_config.py | TestFromAC_ConfigLeafHookReactionSchema at L723, 5 tests | PASS |
| File: updated tests/test_hook_reaction_router.py | TestFromAC_RouterConsumesConfigOwnedRules at L521, 3 tests | PASS |
| Test: config.py no owlbear imports | test_config_source_has_no_owlbear_imports passes; grep confirms zero owlbear imports in config.py | PASS |
| Test: HookReactionRule declared in config.py + order preservation | 4 tests (class ClassDef, **module**, rule order, action order) all pass; HookReactionRule at config.py L36 | PASS |
| Test: Router consumes config-owned rules, no duplicate | 3 tests (no ClassDef in router, config **module**, e2e dispatch) all pass; router imports from owlbear.config L26 | PASS |
| ruff clean | uv run ruff check on 4 task files -> All checks passed | PASS |

### Test Results

- pytest (task-scoped): 8 passed, 0 failed
- pytest (full suite): pre-existing failures only (numpy compat, bootstrap unpack, other RED tests); none touch #969 files
- ruff (task-scoped): All checks passed

### Architect Quality

- AC specificity: 5/5 â€” mechanically verifiable via AST source inspection
- Edge case coverage: complete â€” structural invariants are binary
- Design direction: accurate seam identification, productive
- AC quality score: 5

### Confidence: .97

### Action: archive

[[2026-03-23]] Mon 21:45

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| b2c5c78 | chore | tests/test_config.py, tests/test_hook_reaction_router.py | #969 |
