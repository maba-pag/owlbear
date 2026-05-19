---
id: 955
title: Implement HookReaction policy schema and bootstrap router wiring
status: archived
priority: important
created: 2026-03-23T03:22:41.9450761+01:00
updated: 2026-03-24T03:57:03.3446666+01:00
started: 2026-03-24T03:56:57.9058326+01:00
completed: 2026-03-24T03:56:57.9058326+01:00
tags:
    - agent
    - hooks
    - config
    - scope:core
    - type:build
parent: 950
depends_on:
    - 965
    - 969
class: standard
---

See docs/research/hookevent-reaction-routing.md section 5 and docs/research/hookreaction-schema-router-wiring.md. This task implements only the typed HookReaction schema and the router/bootstrap registration seam that downstream tasks reuse.

## AC

- [ ] Files: src/owlbear/config.py, src/owlbear/core/hook_reaction_router.py, src/owlbear/bootstrap/hooks.py
- [ ] src/owlbear/config.py declares HookReactionRule and any supporting hook_reaction action/schema types with Pydantic validation for non-empty events, non-empty actions, optional shallow scalar match values only, and rejection of unknown keys
- [ ] OwlBearSettings exposes hook_reactions with a default empty list, preserves configured rule and action order, and src/owlbear/config.py remains a true leaf module that does not import any owlbear module, including src/owlbear/core/hook_reaction_router.py, HookEvent, HookRegistry, daemon modules, loop_detection, or notification backends
- [ ] Allowed action kinds in this task are exactly notify, retry, and escalate as typed config values; this task does not add a more general workflow DSL, regex matching, nested-path matching, or templating
- [ ] src/owlbear/core/hook_reaction_router.py defines only a standalone HookReactionRouter plus injected executor protocol(s) or equivalent protocol-backed action mapping, consumes config-owned rule objects, and does not define a second HookReactionRule schema or import daemon.py, loop_detection.py, channel modules, or bootstrap code
- [ ] Router matching is limited to emitted event name plus shallow top-level scalar equality against payload keys, and configured actions run in listed order only for matching rules
- [ ] Router failures and executor exceptions are logged and swallowed without changing HookRegistry best-effort semantics and without recursively emitting HookEvent.ON_ERROR
- [ ] src/owlbear/bootstrap/hooks.py validates configured event strings by resolving them to HookEvent during router registration, fails hook construction on invalid hook_reactions event names, and keeps existing NotificationHook registration behavior intact
- [ ] build_hooks() keeps its current return contract, and default settings with no hook_reactions continue to build hooks successfully without requiring retry or escalation integrations from downstream tasks
- [ ] This task does not implement daemon retry reuse (#956), notification or escalation executor reuse (#957), question_pending cleanup (#962), or notification deduplication (#963)
- [ ] All tests from #965 and #969 pass
- [ ] ruff clean

## Scope Boundaries

- Schema ownership for hook_reactions stays in src/owlbear/config.py so config.py remains a leaf module.
- Retry executor reuse remains in #956.
- Notification and escalation executor reuse remains in #957.
- Remove dead question_pending defaults in #962.
- Deduplicate notify delivery in #963.

## Research

- Recommendation (.91 confidence): keep hook_reactions as a minimal typed rule model with string event names validated during router registration; implement a standalone HookReactionRouter in core/ and register it from bootstrap/hooks.py; keep matching to shallow scalar equality rather than adding a workflow DSL.
- Key findings:
  - config.py is a leaf module, so hook_reactions should not import HookEvent; validate configured event strings at bootstrap registration, reusing the NotificationHook.register() seam.
  - HookRegistry.emit() is observational and must stay unchanged; routing belongs in a separate handler object.
  - question_pending exists in config defaults and HookEvent, but this research found no current emission site in src/.
  - Router-driven notify can double-fire alongside the legacy NotificationHook path unless delivery is deduplicated.
- Follow-up tasks created:
  - #962 Remove dead question_pending default hook configuration
  - #963 Deduplicate notify delivery between NotificationHook and HookReactionRouter
  - #969 Test HookReaction config leaf boundary and schema ownership
- Attribution updated: docs/sources/overview.md

[[2026-03-23]] Mon 13:05

## Architecture Review

**Verdict:** Refine

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| config.py declares validated hook_reaction models | The task already pointed in this direction, but the archived RED task and current code path still leave room for config.py to import schema from core, which violates the config leaf rule in architecture-standards | Tightened the AC to require config-owned schema types and created #969 to enforce that boundary in RED |
| OwlBearSettings exposes hook_reactions while config.py remains a leaf module | The previous wording banned several higher-layer imports but still allowed config.py to depend on src/owlbear/core/hook_reaction_router.py | Rewrote the AC to forbid any owlbear import from config.py, including the current core schema import path |
| core/hook_reaction_router.py defines the standalone router | The prior AC did not explicitly forbid duplicating HookReactionRule inside core/, which is the layering drift now visible in src/owlbear/core/hook_reaction_router.py | Tightened the router AC so core owns routing behavior only and consumes config-owned rule objects |
| All tests from #965 pass | #965 covers router behavior, matching, and bootstrap registration, but it does not mechanically guard schema ownership or config leaf imports | Added #969 as an additional RED predecessor and updated the pass condition to require both #965 and #969 |

### Architecture Notes

- Architecture standards make src/owlbear/config.py a leaf node with no owlbear imports, so HookReaction schema ownership must stay in config.py and flow downward into core/ rather than the reverse.
- The router still belongs in src/owlbear/core/hook_reaction_router.py and registration still belongs in src/owlbear/bootstrap/hooks.py, following the existing seams in src/owlbear/core/hooks.py and src/owlbear/core/notification_hook.py.
- This remains one core-domain feature; config.py and bootstrap/hooks.py are ancillary seams for the router, not separate domains requiring another split.
- The missing issue is architectural guardrails, not scope breadth, so a refine plus a focused RED follow-up is sufficient.

### Changes Made

- Created #969 Test HookReaction config leaf boundary and schema ownership.
- Rewrote #955 AC to require config-owned schema types and a true config leaf boundary.
- Added dependency: #955 depends on #969.
- Released the architect claim after refinement.

### Dependencies

- Added: #969 as an additional RED predecessor for the schema-ownership constraint.
- Verified: #965 remains the predecessor for router behavior, matching, and bootstrap registration coverage.
- Verified: #956 and #957 still depend on #955.
- Verified: #962 and #963 remain separate follow-up tasks outside #955 scope.

[[2026-03-23]] Mon 21:50

## Architecture Review

**Verdict:** Approved

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Files: config.py, hook_reaction_router.py, bootstrap/hooks.py | Clear file scope, matches implementation | Kept |
| config.py declares HookReactionRule with Pydantic validation | Precise: non-empty events/actions, scalar match, extra=forbid. Verified at config.py:36-86 | Kept |
| OwlBearSettings exposes hook_reactions, config.py stays leaf | Verified: zero owlbear imports in config.py; hook_reactions field at line 319 | Kept |
| Allowed actions exactly notify, retry, escalate | Verified: _ALLOWED_ACTIONS frozenset at config.py:33 | Kept |
| Router defines standalone class, consumes config-owned rules | Verified: imports HookReactionRule from owlbear.config; no daemon/channel/bootstrap imports | Kept |
| Matching limited to shallow scalar equality, actions in order | Verified: _make_handler at hook_reaction_router.py:82-104 | Kept |
| Router failures logged and swallowed, no recursive ON_ERROR | Verified: except BLE001 block at hook_reaction_router.py:99-104 | Kept |
| bootstrap/hooks.py validates event strings via HookEvent() | Verified: register() at hook_reaction_router.py:67 raises ValueError | Kept |
| build_hooks() keeps return contract, empty default works | Verified: conditional block at bootstrap/hooks.py:58-66, default=[] | Kept |
| Does not implement #956, #957, #962, #963 | Scope boundaries explicit; noop executors are correct stubs | Kept |
| All tests from #965 and #969 pass | Both tasks archived with full pipeline evidence | Kept |
| ruff clean | Standard lint gate | Kept |

### Architecture Notes

- config.py leaf constraint verified: zero owlbear imports. HookReactionRule schema ownership correctly stays in config.py and flows downward.
- hook_reaction_router.py imports only owlbear.config (runtime) and owlbear.core.hooks (TYPE_CHECKING + deferred in register()). Module layering: config -> core -> bootstrap respected.
- Router uses injected Executor callables (protocol-backed), keeping it decoupled from concrete retry/notification/escalation backends.
- build_hooks() uses_noop executors as placeholders; real executors come from #956 (retry) and #957 (notify/escalate). Correct separation.
- NotificationHook registration preserved before router registration at bootstrap/hooks.py:53-66.
- Implementation already exists from #965 pipeline. Builder/reviewer/auditor will verify against #955 AC.

### Failure Mode Map

| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| register() event resolution | Invalid event string | ValueError | Yes - fail-fast at startup | Startup blocked, must fix config |
| _make_handler dispatch | Executor raises | Exception (BLE001) | Yes - logged + swallowed | Other actions still run, best-effort preserved |
| _make_handler dispatch | Executor missing from map | None check | Yes - skipped silently | No-op until downstream task wires real executor |

### Changes Made

- Approved #955 to todo.

### Dependencies

- Verified: #965 (router behavior tests) archived
- Verified: #969 (config leaf boundary tests) archived
- Verified: #956 and #957 at ideation, correctly downstream
- No new dependencies needed

[[2026-03-23]] Mon 21:50

## Architecture Review

**Verdict:** Approved

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Files: config.py, hook_reaction_router.py, bootstrap/hooks.py | Clear file scope, matches implementation | Kept |
| config.py declares HookReactionRule with Pydantic validation | Precise: non-empty events/actions, scalar match, extra=forbid. Verified at config.py:36-86 | Kept |
| OwlBearSettings exposes hook_reactions, config.py stays leaf | Verified: zero owlbear imports in config.py; hook_reactions field at line 319 | Kept |
| Allowed actions exactly notify, retry, escalate | Verified: _ALLOWED_ACTIONS frozenset at config.py:33 | Kept |
| Router defines standalone class, consumes config-owned rules | Verified: imports HookReactionRule from owlbear.config; no daemon/channel/bootstrap imports | Kept |
| Matching limited to shallow scalar equality, actions in order | Verified: _make_handler at hook_reaction_router.py:82-104 | Kept |
| Router failures logged and swallowed, no recursive ON_ERROR | Verified: except BLE001 block at hook_reaction_router.py:99-104 | Kept |
| bootstrap/hooks.py validates event strings via HookEvent() | Verified: register() at hook_reaction_router.py:67 raises ValueError | Kept |
| build_hooks() keeps return contract, empty default works | Verified: conditional block at bootstrap/hooks.py:58-66, default=[] | Kept |
| Does not implement #956, #957, #962, #963 | Scope boundaries explicit; noop executors are correct stubs | Kept |
| All tests from #965 and #969 pass | Both tasks archived with full pipeline evidence | Kept |
| ruff clean | Standard lint gate | Kept |

### Architecture Notes

- config.py leaf constraint verified: zero owlbear imports. HookReactionRule schema ownership correctly stays in config.py and flows downward.
- hook_reaction_router.py imports only owlbear.config (runtime) and owlbear.core.hooks (TYPE_CHECKING + deferred in register()). Module layering: config -> core -> bootstrap respected.
- Router uses injected Executor callables (protocol-backed), keeping it decoupled from concrete retry/notification/escalation backends.
- build_hooks() uses_noop executors as placeholders; real executors come from #956 (retry) and #957 (notify/escalate). Correct separation.
- NotificationHook registration preserved before router registration at bootstrap/hooks.py:53-66.
- Implementation already exists from #965 pipeline. Builder/reviewer/auditor will verify against #955 AC.

### Failure Mode Map

| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| register() event resolution | Invalid event string | ValueError | Yes - fail-fast at startup | Startup blocked, must fix config |
| _make_handler dispatch | Executor raises | Exception (BLE001) | Yes - logged + swallowed | Other actions still run, best-effort preserved |
| _make_handler dispatch | Executor missing from map | None check | Yes - skipped silently | No-op until downstream task wires real executor |

### Changes Made

- Approved #955 to todo.

### Dependencies

- Verified: #965 (router behavior tests) archived
- Verified: #969 (config leaf boundary tests) archived
- Verified: #956 and #957 at ideation, correctly downstream
- No new dependencies needed

## Test-Writer Notes

- Test file: tests/test_955_hook_reaction_schema_bootstrap.py
- Classes:
  TestFromAC_955_RouterModuleIsolation
  TestFromAC_955_AllowedActionsExactSet
  TestFromAC_955_BuildHooksReturnContract
  TestFromAC_955_ExecutorMissingFromMap
  TestFromAC_955_HookReactionRuleCanonicalImport
- Tests per category: happy 14, error 7, boundary 5, source-inspection 3
- Total: 29 tests, all PASS on HEAD
- ruff: clean
- Special case: Implementation predates this test phase.
  Architecture review (2026-03-23) confirmed: Implementation already exists
  from the #965 pipeline. All tests pass immediately because the implementation
  satisfies the full #955 AC. Builder role is verification, not new implementation.
- AC coverage:
  AC2 (HookReactionRule Pydantic validation): TestFromAC_955_HookReactionRuleCanonicalImport (6 tests)
  AC4 (exactly notify/retry/escalate): TestFromAC_955_AllowedActionsExactSet (7 tests)
  AC5 (router import isolation): TestFromAC_955_RouterModuleIsolation (5 tests)
  AC6 (executor missing silently skipped): TestFromAC_955_ExecutorMissingFromMap (4 tests)
  AC9 (build_hooks return contract + noop executors): TestFromAC_955_BuildHooksReturnContract (7 tests)
  AC11 (all #965 and #969 tests pass): Verified 49/49 pass separately

[[2026-03-23]] Mon 23:22

## Builder Notes

- Files changed: None (verification-only pass; implementation already present).
- Tests: 78 passed, 2 warnings on AC-scoped suite; coverage run executed with bare --cov.
- Lint: ruff clean (task-scoped).
- Evidence: `uv run pytest tests/test_955_hook_reaction_schema_bootstrap.py tests/test_hook_reaction_router.py::TestFromAC_HookReactionRuleSchema tests/test_hook_reaction_router.py::TestFromAC_HookReactionRouterRegistration tests/test_hook_reaction_router.py::TestFromAC_HookReactionRouterMatching tests/test_hook_reaction_router.py::TestFromAC_HookReactionRouterErrorHandling tests/test_hook_reaction_router.py::TestFromAC_RouterConsumesConfigOwnedRules tests/test_bootstrap.py::TestFromAC_OwlBearSettingsHookReactions tests/test_bootstrap.py::TestFromAC_BuildHooksHookReactions tests/test_config.py::TestFromAC_ConfigLeafHookReactionSchema -q --tb=short` -> `78 passed, 2 warnings in 2.41s`; `uv run ruff check src/owlbear/config.py src/owlbear/core/hook_reaction_router.py src/owlbear/bootstrap/hooks.py tests/test_955_hook_reaction_schema_bootstrap.py tests/test_hook_reaction_router.py tests/test_bootstrap.py tests/test_config.py` -> `All checks passed!`; coverage highlights from scoped run: `src/owlbear/core/hook_reaction_router.py` 100%, `src/owlbear/bootstrap/hooks.py` 80%, `src/owlbear/config.py` 76%.
- Fixes applied: None (task is already implemented from predecessor pipeline; builder performed GREEN verification only).
- Notes: Test-writer marked this as a pre-implemented special case for #955, so no new implementation diff was required in this builder pass.

[[2026-03-24]] Tue 00:11

## Review Evidence

### Test Results

- pytest scope: 78 passed, 2 optional-dependency warnings.

- ruff scope: All checks passed.

- coverage scope: src/owlbear/core/hook_reaction_router.py 100%, src/owlbear/bootstrap/hooks.py 80%, src/owlbear/config.py 76% (not the rejection basis).

### Findings

- FAIL: HookReactionRule._scalar_match_values() at src/owlbear/config.py:80 only rejects dict/list, but AC line 2 requires scalar-only match values.

- Test gap: RED mapping at kanban/tasks/965-test-hookreaction-policy-schema-and-bootstrap.md:89-91 claims non-scalar coverage, but the actual tests only cover dict/list at tests/test_hook_reaction_router.py:125, tests/test_hook_reaction_router.py:135, and tests/test_955_hook_reaction_schema_bootstrap.py:418.

- TestFromAC integrity: git log for tests/test_955_hook_reaction_schema_bootstrap.py shows only commit 67ed969; the current worktree diff is formatting-only, so the fail is implementation + coverage, not builder weakening.

- Other scoped checks passed: event registration fail-fast, order preservation, config ownership, router isolation, and build_hooks noop/default behavior.

### Verdict

- FAIL -> todo until match validation rejects tuple/set/object-style non-scalars and a compensating test is added.

[[2026-03-24]] Tue 00:12

## Review Evidence

### Test Results

- pytest scope: 78 passed, 2 optional-dependency warnings.

- ruff scope: All checks passed.

- coverage scope: src/owlbear/core/hook_reaction_router.py 100%, src/owlbear/bootstrap/hooks.py 80%, src/owlbear/config.py 76% (not the rejection basis).

### Findings

- FAIL: HookReactionRule._scalar_match_values() at src/owlbear/config.py:80 only rejects dict/list, but AC line 2 requires scalar-only match values.

- Test gap: RED mapping at kanban/tasks/965-test-hookreaction-policy-schema-and-bootstrap.md:89-91 claims non-scalar coverage, but the actual tests only cover dict/list at tests/test_hook_reaction_router.py:125, tests/test_hook_reaction_router.py:135, and tests/test_955_hook_reaction_schema_bootstrap.py:418.

- TestFromAC integrity: git log for tests/test_955_hook_reaction_schema_bootstrap.py shows only commit 67ed969; the current worktree diff is formatting-only, so the fail is implementation + coverage, not builder weakening.

- Other scoped checks passed: event registration fail-fast, order preservation, config ownership, router isolation, and build_hooks noop/default behavior.

### Verdict

- FAIL -> todo until match validation rejects tuple/set/object-style non-scalars and a compensating test is added.

- Direct runtime check: constructing HookReactionRule with match value (1, 2) succeeded and printed a tuple-valued match instead of raising.

[[2026-03-24]] Tue 00:32

## Test-Writer Notes (retry)

- Retry reason: reviewer HIGH-severity finding — _scalar_match_values() only rejects dict/list; tuples, frozensets, sets, and custom objects bypass validation

- Added class: TestFromAC_955_ScalarMatchBoundary in tests/test_955_hook_reaction_schema_bootstrap.py

- New tests: 4 FAIL (tuple, frozenset, set, custom object), 4 PASS (int/str/None/bool scalars still accepted)

- Preserved: 33 existing tests — all PASS (old PASS baseline preserved)

- Total in file: 37 tests. 4 fail, 33 pass

- ruff: clean

- AC coverage gap addressed: AC line 2 — scalar-only match values now tested for full non-scalar type range

[[2026-03-24]] Tue 01:47

## Builder Notes

- Files changed: src/owlbear/config.py
- Tests (RED before fix): `uv run pytest tests/test_955_hook_reaction_schema_bootstrap.py -q --tb=short` -> 4 failed, 33 passed, 2 warnings (tuple/frozenset/set/custom-object match values did not raise ValidationError).
- Tests (GREEN): `uv run pytest tests/test_955_hook_reaction_schema_bootstrap.py -q --tb=short` -> 37 passed, 2 warnings.
- Scoped AC regression: `uv run pytest tests/test_955_hook_reaction_schema_bootstrap.py tests/test_hook_reaction_router.py::TestFromAC_HookReactionRuleSchema tests/test_hook_reaction_router.py::TestFromAC_HookReactionRouterRegistration tests/test_hook_reaction_router.py::TestFromAC_HookReactionRouterMatching tests/test_hook_reaction_router.py::TestFromAC_HookReactionRouterErrorHandling tests/test_hook_reaction_router.py::TestFromAC_RouterConsumesConfigOwnedRules tests/test_bootstrap.py::TestFromAC_OwlBearSettingsHookReactions tests/test_bootstrap.py::TestFromAC_BuildHooksHookReactions tests/test_config.py::TestFromAC_ConfigLeafHookReactionSchema -q --tb=short` -> 86 passed, 2 warnings.
- Coverage (bare --cov, scoped): `uv run pytest tests/test_955_hook_reaction_schema_bootstrap.py tests/test_hook_reaction_router.py::TestFromAC_HookReactionRuleSchema tests/test_hook_reaction_router.py::TestFromAC_HookReactionRouterRegistration tests/test_hook_reaction_router.py::TestFromAC_HookReactionRouterMatching tests/test_hook_reaction_router.py::TestFromAC_HookReactionRouterErrorHandling tests/test_hook_reaction_router.py::TestFromAC_RouterConsumesConfigOwnedRules tests/test_bootstrap.py::TestFromAC_OwlBearSettingsHookReactions tests/test_bootstrap.py::TestFromAC_BuildHooksHookReactions tests/test_config.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short` -> 169 passed, 2 warnings; src/owlbear/config.py 79%, src/owlbear/core/hook_reaction_router.py 100%, src/owlbear/bootstrap/hooks.py 80%.
- Lint: `uv run ruff check src/owlbear/config.py src/owlbear/core/hook_reaction_router.py src/owlbear/bootstrap/hooks.py tests/test_955_hook_reaction_schema_bootstrap.py tests/test_hook_reaction_router.py tests/test_bootstrap.py tests/test_config.py` -> All checks passed.
- Fixes applied: HookReactionRule match-value validation now accepts only scalar primitives (str/int/float/bool/None) and rejects all other non-scalar types, closing the reviewer-reported tuple/set/frozenset/custom-object gap.

[[2026-03-24]] Tue 02:11

## Review Evidence

### Test Results

- pytest scope: `uv run pytest tests/test_955_hook_reaction_schema_bootstrap.py tests/test_hook_reaction_router.py::TestFromAC_HookReactionRuleSchema tests/test_hook_reaction_router.py::TestFromAC_HookReactionRouterRegistration tests/test_hook_reaction_router.py::TestFromAC_HookReactionRouterMatching tests/test_hook_reaction_router.py::TestFromAC_HookReactionRouterErrorHandling tests/test_hook_reaction_router.py::TestFromAC_RouterConsumesConfigOwnedRules tests/test_bootstrap.py::TestFromAC_OwlBearSettingsHookReactions tests/test_bootstrap.py::TestFromAC_BuildHooksHookReactions tests/test_config.py::TestFromAC_ConfigLeafHookReactionSchema -q --tb=short` -> 86 passed, 2 warnings (`qdrant_client` optional deps).

- ruff scope: `uv run ruff check src/owlbear/config.py src/owlbear/core/hook_reaction_router.py src/owlbear/bootstrap/hooks.py tests/test_955_hook_reaction_schema_bootstrap.py tests/test_hook_reaction_router.py tests/test_bootstrap.py tests/test_config.py` -> All checks passed.

- coverage scope: bare `--cov` run reports src/owlbear/core/hook_reaction_router.py 100%, src/owlbear/config.py 79%, src/owlbear/bootstrap/hooks.py 80%; low file totals are dominated by unrelated branches in large modules, so I paired this with focused source inspection and runtime checks.

- supplemental runtime checks: float match values are accepted; default hook_reactions lists are not shared across OwlBearSettings instances.

### Test-Writer AC Coverage

| AC area | Mapped tests | Would fail if AC violated? | Verdict |

|---------|--------------|----------------------------|---------|

| Schema validation | `TestFromAC_HookReactionRuleSchema`, `TestFromAC_955_HookReactionRuleCanonicalImport`, `TestFromAC_955_ScalarMatchBoundary` | Yes | COVERED |

[[2026-03-24]] Tue 02:13

## Review Evidence (continued)

### AC Compliance

- PASS: Schema validation. HookReactionRule is defined in src/owlbear/config.py and _scalar_match_values() at src/owlbear/config.py:77 now rejects tuple, frozenset, set, and custom-object match values. Focused tests: TestFromAC_HookReactionRuleSchema, TestFromAC_955_HookReactionRuleCanonicalImport, and TestFromAC_955_ScalarMatchBoundary. Supplemental runtime check confirmed float scalar values are accepted.

- PASS: OwlBearSettings wiring. hook_reactions is declared on OwlBearSettings at src/owlbear/config.py:321, order-preservation is covered by tests/test_bootstrap.py:2981 and tests/test_config.py:723, and a direct runtime check confirmed default hook_reactions lists are not shared between instances.

- PASS: Allowed actions. _ALLOWED_ACTIONS at src/owlbear/config.py:33 remains exactly notify, retry, and escalate, with rejection tests in TestFromAC_955_AllowedActionsExactSet.

- PASS: Router isolation and ownership. src/owlbear/core/hook_reaction_router.py imports config-owned rules at line 26, exposes only HookReactionRouter plus the re-export at line 33, and the isolation and ownership checks pass in TestFromAC_955_RouterModuleIsolation and TestFromAC_RouterConsumesConfigOwnedRules.

- PASS: Matching and execution semantics. src/owlbear/core/hook_reaction_router.py:75-101 preserves shallow top-level equality, declared action order, swallowed executor failures, and no recursive ON_ERROR emission. These behaviors are covered by TestFromAC_HookReactionRouterMatching and TestFromAC_HookReactionRouterErrorHandling.

- PASS: Bootstrap wiring. src/owlbear/bootstrap/hooks.py:53-64 preserves NotificationHook registration, resolves event strings through router registration, and keeps build_hooks() working with local noop executors only. This satisfies the no-#956/#957/#962/#963 leakage boundary.

- PASS: Verification gates. Scoped pytest passed 86 tests with 2 optional-dependency warnings, scoped ruff passed cleanly, and the bare --cov scoped run reported src/owlbear/core/hook_reaction_router.py 100 percent, src/owlbear/config.py 79 percent, and src/owlbear/bootstrap/hooks.py 80 percent. The lower file totals are in unrelated branches of large modules and did not correspond to a surviving task defect after source inspection plus runtime checks.

### Test Integrity

- PASS: TestFromAC coverage was preserved. Git history for tests/test_955_hook_reaction_schema_bootstrap.py shows only test-writer commits 67ed969 and c79876d. Builder commit be9fb91 touched only src/owlbear/config.py.

### Test Quality

- Assertion specificity: ADEQUATE.

- Negative and error-path coverage: STRONG.

- Manual mutation resistance: ADEQUATE.

- Test independence: STRONG.

- Descriptive names: STRONG.

### Verdict

- PASS. Confidence .93.

[[2026-03-24]] Tue 02:13

## Review Evidence (continued)

### AC Compliance

- PASS: Schema validation. HookReactionRule is defined in src/owlbear/config.py and _scalar_match_values() at src/owlbear/config.py:77 now rejects tuple, frozenset, set, and custom-object match values. Focused tests: TestFromAC_HookReactionRuleSchema, TestFromAC_955_HookReactionRuleCanonicalImport, and TestFromAC_955_ScalarMatchBoundary. Supplemental runtime check confirmed float scalar values are accepted.

- PASS: OwlBearSettings wiring. hook_reactions is declared on OwlBearSettings at src/owlbear/config.py:321, order-preservation is covered by tests/test_bootstrap.py:2981 and tests/test_config.py:723, and a direct runtime check confirmed default hook_reactions lists are not shared between instances.

- PASS: Allowed actions. _ALLOWED_ACTIONS at src/owlbear/config.py:33 remains exactly notify, retry, and escalate, with rejection tests in TestFromAC_955_AllowedActionsExactSet.

- PASS: Router isolation and ownership. src/owlbear/core/hook_reaction_router.py imports config-owned rules at line 26, exposes only HookReactionRouter plus the re-export at line 33, and the isolation/ownership checks pass in TestFromAC_955_RouterModuleIsolation and TestFromAC_RouterConsumesConfigOwnedRules.

- PASS: Matching and execution semantics. src/owlbear/core/hook_reaction_router.py:75-101 preserves shallow top-level equality, declared action order, swallowed executor failures, and no recursive ON_ERROR emission. These behaviors are covered by TestFromAC_HookReactionRouterMatching and TestFromAC_HookReactionRouterErrorHandling.

- PASS: Bootstrap wiring. src/owlbear/bootstrap/hooks.py:53-64 preserves NotificationHook registration, resolves event strings through router registration, and keeps build_hooks() working with local noop executors only. This satisfies the no-#956/#957/#962/#963 leakage boundary.

- PASS: Verification gates. Scoped pytest passed 86 tests with 2 optional-dependency warnings, scoped ruff passed cleanly, and the bare --cov scoped run reported src/owlbear/core/hook_reaction_router.py 100 percent, src/owlbear/config.py 79 percent, and src/owlbear/bootstrap/hooks.py 80 percent. The lower file totals are in unrelated branches of large modules and did not correspond to a surviving task defect after source inspection plus runtime checks.

### Test Integrity

- PASS: TestFromAC coverage was preserved. Git history for tests/test_955_hook_reaction_schema_bootstrap.py shows only test-writer commits 67ed969 and c79876d. Builder commit be9fb91 touched only src/owlbear/config.py.

### Test Quality

- Assertion specificity: ADEQUATE.

- Negative and error-path coverage: STRONG.

- Manual mutation resistance: ADEQUATE.

- Test independence: STRONG.

- Descriptive names: STRONG.

### Verdict

- PASS. Confidence .93.

[[2026-03-24]] Tue 03:11

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |

|---|-------|----------|--------|----------|

[[2026-03-24]] Tue 03:56

## Audit

### AC Verification

| AC Line | Evidence | Status |

|---------|----------|--------|

| Files limited to config/router/bootstrap | Spot-checked all 3 files, commit log confirms | PASS |

| Config-owned schema, scalar-only match | Allowlist at config.py:34, validator at :77-86, runtime-tested by reviewer | PASS |

| OwlBearSettings default/order/leaf, config.py is leaf | grep for owlbear imports in config.py: zero matches | PASS |

| Allowed actions exactly notify/retry/escalate | _ALLOWED_ACTIONS frozenset at config.py:33 | PASS |

| Router standalone, consumes config-owned rules, no forbidden imports | hook_reaction_router.py imports only owlbear.config + TYPE_CHECKING hooks | PASS |

| Matching: shallow equality, actions in order | _make_handler at hook_reaction_router.py:82-104 | PASS |

| Router failures logged/swallowed, no recursive ON_ERROR | except BLE001 block at hook_reaction_router.py:96-101 | PASS |

| Bootstrap validates event strings, preserves NotificationHook | bootstrap/hooks.py:53-64 | PASS |

| build_hooks() return contract, empty default works | Conditional block at bootstrap/hooks.py:58-66 | PASS |

| No #956/#957/#962/#963 implementation leakage | noop executors only at bootstrap/hooks.py:61-66 | PASS |

| All #965/#969 tests pass | 86 scoped tests passed | PASS |

| ruff clean | All checks passed | PASS |

### Test Results

- pytest scoped: 86 passed, 2 optional-dependency warnings

- pytest full suite: 4103 passed, 98 failed (all failures in unrelated modules: RED tests #921/#925, stale fixtures, pre-existing)

- ruff: All checks passed

### Architect Quality

- AC specificity: High. Two-pass architect review (REFINE -> APPROVED) produced measurable, verifiable AC lines.

- Edge case coverage: Adequate. Scalar-match gap was identified by reviewer, not the AC, but the AC did correctly specify scalar-only.

- Design direction: Strong. config leaf constraint, router isolation, and noop executor stubs guided builder cleanly.

- AC quality score: 4/5

### Confidence: .96

### Action: archive
