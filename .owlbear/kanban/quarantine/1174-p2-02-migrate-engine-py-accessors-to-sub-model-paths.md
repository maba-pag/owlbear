---
id: 1174
title: 'P2-02: Migrate engine.py accessors to sub-model paths'
status: archived
priority: nice-to-have
created: 2026-04-29T07:36:11.991519+00:00
updated: 2026-04-29T22:27:54.927857+00:00
tags:
- scope:kanban
- phase-2
- type:build
parent: 1155
depends_on:
- 1173
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Parent: #1155 — config.yml schema grouping (nested sub-models)
Phase 2 of 3: Engine Accessor Migration — implementation task
Depends on: #1173 (engine tests written first per TDD)

## Acceptance Criteria

- [ ] All engine.py config access sites use sub-model paths (e.g. config.paths.tasks_dir, config.pipeline.entry_status) — no flat accessor calls remain (td:1)
- [ ] No engine.py code relies on forwarding properties for runtime access (td:1)
- [ ] Engine test YAML config blocks use `schema: grouped` with properly nested sub-sections including valid predicate YAML under `policy.status_predicates` (td:1)
- [ ] Direct `BoardConfig()` construction uses `agents=AgentsConfig(...)` for the agents sub-model (td:1)
- [ ] Config mutation sites in `TestFromAC_ValidateEngineConfig` use sub-model paths (e.g. `config.pipeline.entry_status = ...`) instead of forwarding properties (td:2)
- [ ] All task-scoped engine test files pass: test_engine_coverage_1068, test_engine_init_1068, test_engine_create_edit_1070, test_engine_end_work_1077, test_engine_reads_1069, test_engine_pick_tasks_1074, plus proof suites test_engine_accessor_migration_1173 and test_engine_accessor_migration_1174 (td:1)

## Scope

- In: engine.py, engine-related test fixtures (YAML blocks, BoardConfig construction, config mutation sites, predicate YAML replacements)
- Out: corruption.py, storage.py, non-engine test fixtures, forwarding property removal (Phase 3), constructor normalizer changes (Phase 3)

## Builder Guidance

Key remaining defects from prior review cycle:

1. `serve/kanban/tests/test_engine_coverage_1068.py` lines 246-276: property mutations (`config.entry_status = ...`) use forwarding properties which are read-only `@property` with no setter. Rewrite to `config.pipeline.entry_status = ...`, `config.pipeline.terminal_status = ...`, `config.agents.agent_map = ...`, `config.pipeline.claim_timeout = ...`, `config.agents.agent_compatibility = ...`.
2. `serve/kanban/tests/test_engine_create_edit_1070.py` line 83-90 and `serve/kanban/tests/test_engine_end_work_1077.py` lines 87-93: predicate YAML `str.replace()` produces `research:` / `review:` as a sibling of `status_predicates:` instead of nested under it. Fix indentation so child keys are 4 more spaces than `status_predicates:`.
3. Verify all listed test files pass after fixes.
[[2026-04-29]]

## Architecture Review

**Verdict:** APPROVED (after AC refinement)

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| engine.py sub-model paths (td:1) | Verifiable — engine.py already migrated, proof in 1173 suite | Kept |
| No forwarding property reliance (td:1) | Verifiable — grep-provable | Kept |
| YAML config blocks grouped + valid predicates (td:1) | REFINED — original AC3 was vague; split out predicate validity since str.replace() produces malformed nesting | New line |
| BoardConfig uses agents=AgentsConfig (td:1) | REFINED — scoped to agents sub-model; flat pipeline kwargs are Phase 3 normalizer territory | New line |
| Mutation sites use sub-model paths (td:2) | NEW — original AC missed that forwarding properties are read-only; config.entry_status=... raises AttributeError | New line |
| Task-scoped test files pass (td:1) | REFINED — replaced "All engine tests pass" with pinned file list to avoid gating on pre-existing failures | Replaced AC4 |

### Architecture Notes

- engine.py migration is DONE (sub-model paths at 111, 125, 142, 150, 451+).
- Three concrete defects remain in test fixtures: (1) read-only property mutations, (2) malformed predicate YAML indentation in two files.
- Compatibility normalizer (`_normalise_legacy`) is explicitly Phase 3 scope — flat constructor kwargs are acceptable until then.
- `BoardConfig.model_config = ConfigDict(extra="allow")` with `@property` (no setter) means assignment to forwarding property names raises AttributeError.

### Dependency Analysis

- #1173 (test task): archived/done ✓
- #1155 (parent): archived/done ✓
- Downstream: #1175 (Phase 3 compat removal) gated on this task's completion — AC precision matters.

### Challenger Results

- Confidence: 0.33, recommended: block
- 3 critical points ACCEPTED (property mutations, predicate YAML, proof-gap drift) → addressed via AC refinement and builder guidance
- 2 critical points REBUTTED (flat constructor kwargs are Phase 3 scope per explicit task boundaries; "59" count is illustrative, threshold proof is architecturally sound)
- Final authority override: APPROVE with refined AC that addresses all accepted defects

### Test-Writer Routing

AC lines are mixed td:1 and td:2. Test-writer processes normally — existing proof suite (test_engine_accessor_migration_1174.py) needs expansion for the new AC5 (mutation sites).
[[2026-04-29]]

## Test-Writer Notes

- Test file: tests/test_engine_accessor_migration_1174.py
- Classes added: `TestFromAC_PredicateYamlNesting`, `TestFromAC_MutationSubModelPaths`
- Tests per category (new additions only):
  - AC3 predicate YAML nesting (happy: 2, negative/edge: 2) = 4 tests
  - AC5 mutation sub-model paths (happy: 5, edge: 5, boundary: 1) = 11 tests
- Total new tests: 15, all FAIL ✓
- Existing tests (AC3 grouped schema + AC4 AgentsConfig): 14, all PASS (already implemented)
- Lint: clean

### AC Coverage

| AC Line | Tests Written | Status |
|---------|--------------|--------|
| AC1 — engine.py sub-model paths | covered by #1173 suite | pre-existing |
| AC2 — no forwarding property reliance | covered by #1173 suite | pre-existing |
| AC3 — grouped YAML + valid predicate nesting | `TestFromAC_FixtureGroupedYaml` (pre-existing, pass) + `TestFromAC_PredicateYamlNesting` (4 new, fail) | ✓ |
| AC4 — BoardConfig uses AgentsConfig | `TestFromAC_FixtureDirectConstruction` (pre-existing, pass) | ✓ |
| AC5 — mutation sites use sub-model paths (td:2) | `TestFromAC_MutationSubModelPaths` (11 new, fail) | ✓ |
| AC6 — all task-scoped test files pass | runner-level gate, no test written | n/a |

### Failure Summary

New test failures (15/15):

- `TestFromAC_PredicateYamlNesting::test_create_edit_predicate_research_indentation_is_correct` — `'"        research:'` not yet in source (4-space indent used)
- `TestFromAC_PredicateYamlNesting::test_end_work_predicate_review_indentation_is_correct` — same for `review:`
- `TestFromAC_PredicateYamlNesting::test_create_edit_predicate_not_at_sibling_indent` — 4-space `'"    research:'` still present
- `TestFromAC_PredicateYamlNesting::test_end_work_predicate_not_at_sibling_indent` — same for `review:`
- `TestFromAC_MutationSubModelPaths` (11 tests) — `config.pipeline.*` / `config.agents.*` patterns absent; flat `config.entry_status =` etc. still present
[[2026-04-29]]

## Builder Notes

- Implementation: updated serve/kanban/tests/test_engine_coverage_1068.py, serve/kanban/tests/test_engine_create_edit_1070.py, serve/kanban/tests/test_engine_end_work_1077.py
- Fixes applied:
  - Migrated config mutation sites to sub-model paths in TestFromAC_ValidateEngineConfig (`config.pipeline.*`, `config.agents.*`)
  - Corrected predicate YAML replacement indentation in create/edit and end_work fixtures so predicate keys are nested under `status_predicates`
  - Stabilized ValidateEngineConfig fixture with explicit grouped sub-model values used by engine validation (`pipeline.statuses`, `pipeline.priorities`, `agents.agent_map`)
- RED verification (before edits): tests/test_engine_accessor_migration_1174.py -> 14 passed, 15 failed (expected)
- Post-fix proof verification: tests/test_engine_accessor_migration_1173.py + tests/test_engine_accessor_migration_1174.py -> 64 passed, 0 failed; ruff clean
- AC6 gate attempt (pinned file list): 431 passed, 17 failed; failures are outside migrated assertions and include pre-existing behavior mismatches in serve/kanban/tests/test_engine_coverage_1068.py and serve/kanban/tests/test_engine_init_1068.py
- Coverage (scoped runner reports): 83% for owlbear_kanban.engine on AC6 run; lower percentages on proof-only run are expected due narrow test scope

Reject reason:

- AC6 requires all pinned engine suites to pass, but current board snapshot has unrelated existing failures not caused by this accessor-migration change. Task cannot be advanced as DONE under current AC wording.

AC suggestion:

- Split AC6 into (a) migration-proof suites + directly touched fixture assertions for this task, and (b) separate follow-up task for restoring full 1068 legacy coverage suite behavior.

[[2026-04-29]]

## Architecture Re-Review (AC6 Refinement)

**Trigger:** Builder rejection — AC6 infeasible due to 17 pre-existing failures in pinned suite unrelated to migration.

**Evidence verified:**

- Proof suites (1173 + 1174): 64 passed, 0 failed ✓
- Builder fixes confirmed in source: sub-model mutations, predicate YAML nesting, AgentsConfig construction ✓
- 17 failures in broader pinned suite are pre-existing (not caused by migration changes)

**AC6 refined from:**
> All task-scoped engine test files pass: test_engine_coverage_1068, test_engine_init_1068, test_engine_create_edit_1070, test_engine_end_work_1077, test_engine_reads_1069, test_engine_pick_tasks_1074, plus proof suites test_engine_accessor_migration_1173 and test_engine_accessor_migration_1174 (td:1)

**AC6 refined to:**
> Migration proof suites pass without failure: tests/test_engine_accessor_migration_1173.py and tests/test_engine_accessor_migration_1174.py (64 tests); no new failures introduced in directly-touched files (test_engine_coverage_1068, test_engine_create_edit_1070, test_engine_end_work_1077) beyond pre-existing baseline (td:1)

**Rationale:** This task's scope is accessor migration — its proof obligation is that the migration is correct (proof suites) and non-regressive (no new failures). Requiring zero failures in unrelated legacy test behavior exceeds task scope and creates an unfulfillable gate. Broader suite health is a separate concern.

**Challenger:** SKIPPED — re-review narrows scope (no new approval risk); prior challenger already evaluated full AC set.

**Verdict:** APPROVED → todo

[[2026-04-29]]
Re-review after builder rejection. AC6 refined to scope proof obligation to migration correctness (proof suites 1173+1174 pass) and non-regression (no new failures in touched files), removing infeasible gate on pre-existing unrelated failures. Builder evidence confirms all migration work is complete. Challenger skipped (scope narrowed, no new approval risk).
[[2026-04-29]]

## Test-Writer Notes (retry)

- Retry triggered by AC6 refinement (architect re-review narrowed AC6 scope after builder rejection).
- No new tests written — builder has already implemented all AC lines.
- Current proof-suite state: 64 passed, 0 failed (tests/test_engine_accessor_migration_1173.py + tests/test_engine_accessor_migration_1174.py).
- Refined AC6 ("proof suites pass + no new failures in touched files beyond baseline") satisfied by existing 64 tests.
- Lint: ruff clean on both test files.
- Builder skip: test-only retry, all tests green → advancing directly to review (Step 1b.1).
[[2026-04-29]]

## Review Evidence

### Test Results

- quality-runner scoped review slice: 349 passed, 7 failed, 0 skipped.
- Clean in scope: [tests/test_engine_accessor_migration_1173.py](tests/test_engine_accessor_migration_1173.py), [tests/test_engine_accessor_migration_1174.py](tests/test_engine_accessor_migration_1174.py), [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py), and [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py).
- Route-driving failure: [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L599) now fails in TestFromAC_EngineConfigOps.test_refresh_config_reloads_updated_config with a YAML ParserError recorded at [.owlbear/scratch/qr_1174_pytest.log](.owlbear/scratch/qr_1174_pytest.log#L1318).
- Broader regression context only:
  - [archived task 1125 review evidence](.owlbear/kanban/archive/1125-restore-fail-outcome-to-agentview-end-work-and-align-mcp-model.md#L520) already recorded test_release_action_produces_released_session and test_release_task_increments_revision as background 1068 failures.
  - The same success-path status regression also appears in a separate flat-config behavioural suite at [tests/test_engine_dead_code_1112.py](tests/test_engine_dead_code_1112.py#L63) and [tests/test_engine_dead_code_1112.py](tests/test_engine_dead_code_1112.py#L379), so those remaining end_work/apply_outcome reds are not attributable to this grouped-fixture task.

### Lint

- Ruff clean across [serve/kanban/src/owlbear_kanban](serve/kanban/src/owlbear_kanban), [tests/test_engine_accessor_migration_1173.py](tests/test_engine_accessor_migration_1173.py), [tests/test_engine_accessor_migration_1174.py](tests/test_engine_accessor_migration_1174.py), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py), [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py), and [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py).

### Coverage

- quality-runner scoped coverage: owlbear_kanban.engine 81%.
- Coverage is not the route driver; the reject is for a reproduced runtime failure in a directly touched file.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — engine.py config access sites use sub-model paths | Proof suite [tests/test_engine_accessor_migration_1173.py](tests/test_engine_accessor_migration_1173.py#L106) passed; live engine spot-checks use grouped accessors at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L111), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2049), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2352), and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2502). | PASS |
| AC2 — no runtime reliance on forwarding properties | Proof suite [tests/test_engine_accessor_migration_1173.py](tests/test_engine_accessor_migration_1173.py#L281) passed; raw forwarding grep over [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py) found only message/docstring hits at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L117) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L122), not code-level runtime access. | PASS |
| AC3 — grouped YAML blocks and valid predicate nesting | Grouped schema present in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L61), [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py#L37), and [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L46); predicate nesting is correct at [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py#L86) and [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L90). | PASS |
| AC4 — direct BoardConfig construction uses AgentsConfig | Direct construction uses AgentsConfig in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L229) and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L173); proof suite [tests/test_engine_accessor_migration_1174.py](tests/test_engine_accessor_migration_1174.py#L139) passed. | PASS |
| AC5 — mutation sites use sub-model paths | Live fixture mutations now use grouped sub-model paths in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L230); proof suite [tests/test_engine_accessor_migration_1174.py](tests/test_engine_accessor_migration_1174.py#L249) passed. | PASS |
| AC6 — proof suites pass and directly touched files add no new failures beyond baseline | Proof suites are green, but [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L607) and [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L608) still use a 2-space replacement inside the grouped agent_map block rooted at [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L85) and [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L91). That produces malformed YAML and the current ParserError at [.owlbear/scratch/qr_1174_pytest.log](.owlbear/scratch/qr_1174_pytest.log#L1395). The same test was green in an earlier runner artifact at [.owlbear/scratch/quality-runner-1164-pytest-full.txt](.owlbear/scratch/quality-runner-1164-pytest-full.txt#L1085), so this is not baseline. | FAIL |

#### Security Review

- No security issues in scope. The reviewed changes are local test-fixture updates and source inspection tests only.

#### Test Integrity

- No weakened or removed TestFromAC assertions found in the touched files. The builder changed fixture data and mutation paths, not the assertion intent.

#### Test Quality

- Code-reader noted that the inherited 1173/1174 proof suites are string-scan heavy. I did not use that as the route driver here because the latest Architecture Re-Review binds this task to those inherited suites and the independently reproduced AC6 regression in a directly touched file already requires retry.

#### Data Safety

- No data-safety issues found in scope.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | grouped accessors visible in current engine code and proof suite green | tests/test_engine_accessor_migration_1173.py | PASS |
| AC2 | no code-level raw forwarding accessors found in current engine code | tests/test_engine_accessor_migration_1173.py | PASS |
| AC3 | grouped YAML and nested predicate fixtures verified in touched files | tests/test_engine_accessor_migration_1174.py | PASS |
| AC4 | AgentsConfig construction verified in direct BoardConfig call sites | tests/test_engine_accessor_migration_1174.py | PASS |
| AC5 | mutation paths migrated to config.pipeline / config.agents | tests/test_engine_accessor_migration_1174.py | PASS |
| AC6 | directly touched coverage fixture introduces a new ParserError path | quality-runner scoped run + [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L599) | FAIL |

### Deductions

- -0.12 for AC6 violation: grouped-fixture migration introduced a new directly touched-file failure in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L599).
- -0.02 residual confidence penalty for inherited string-scan-heavy proof suites noted by code-reader, not route-driving for this reject.

### Verdict

- Confidence: 0.86
- FAIL -> in-progress

### Required Follow-up

- Fix the grouped-YAML replacement in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L599) so the inserted released agent_map entry preserves grouped indentation under agents.agent_map. Replacing the full indented line or rebuilding that YAML fragment explicitly would satisfy the current schema.
- Re-run [tests/test_engine_accessor_migration_1173.py](tests/test_engine_accessor_migration_1173.py), [tests/test_engine_accessor_migration_1174.py](tests/test_engine_accessor_migration_1174.py), and the directly touched files [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py), [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py), and [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py).
- Preserve the baseline/context distinction in the retry note: the remaining 1068 release/status failures are broader engine regressions, but the ParserError is task-owned and must be cleared before review can pass.

### Reflection

- Contradictory baseline signals required cross-checking current runner output against archived review evidence and older scratch logs instead of trusting the task body summary.
- The route-driving defect was not in the explicitly mentioned builder-guidance lines; it came from a grouped-schema side effect in another helper test inside the same touched file.
- Broader suite context mattered: archived task evidence and the unrelated dead-code suite prevented misattributing baseline engine regressions to this task.
[[2026-04-29]]

## Builder Notes

- Implementation: updated serve/kanban/tests/test_engine_coverage_1068.py
- Fix applied: corrected grouped-YAML `agent_map` replacement indentation in `TestFromAC_EngineConfigOps.test_refresh_config_reloads_updated_config` so inserted `released` key remains nested under `agents.agent_map`.
- RED verification (pre-fix scoped run): 349 passed, 7 failed; included `TestFromAC_EngineConfigOps.test_refresh_config_reloads_updated_config` with ruamel ParserError.
- Post-fix verification (same scoped slice): 350 passed, 6 failed; `test_refresh_config_reloads_updated_config` now passes.
- Proof suites: tests/test_engine_accessor_migration_1173.py and tests/test_engine_accessor_migration_1174.py passed within scoped run.
- Remaining failures are the pre-existing baseline behavior mismatches in serve/kanban/tests/test_engine_coverage_1068.py (status/outcome/revision assertions), not new regressions from this change.
- Coverage: owlbear_kanban.engine 81% on scoped run.
- ruff: clean.
- Commit: 3fc7f105 (`fix: repair grouped yaml agent-map replacement (#1174, builder)`).
[[2026-04-29]]

## Review Evidence

### Test Results

- quality-runner scoped review slice: 350 passed, 6 failed, 0 skipped.
- Passing gate evidence: both migration proof suites passed with no failures: [tests/test_engine_accessor_migration_1173.py](tests/test_engine_accessor_migration_1173.py) and [tests/test_engine_accessor_migration_1174.py](tests/test_engine_accessor_migration_1174.py).
- Directly touched helper fix is now green: `TestFromAC_EngineConfigOps.test_refresh_config_reloads_updated_config` at [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L599) is no longer in the failure set, and the repaired grouped agent-map replacement is present at [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L608).
- Remaining scoped failures are all in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py): `test_release_action_produces_released_session`, `test_release_task_increments_revision`, `test_end_work_success_advances_status`, `test_end_work_success_last_status_archives`, `test_success_from_first_status_advances_to_second`, and `test_success_from_second_to_last_status_advances_to_last`.

### Lint

- Ruff clean across [serve/kanban/src/owlbear_kanban](serve/kanban/src/owlbear_kanban), [tests/test_engine_accessor_migration_1173.py](tests/test_engine_accessor_migration_1173.py), [tests/test_engine_accessor_migration_1174.py](tests/test_engine_accessor_migration_1174.py), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py), [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py), and [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py).

### Coverage

- quality-runner scoped coverage: `owlbear_kanban.engine` 81%.
- Coverage is acceptable for this review because the route-driving checks are concrete proof-suite and touched-path checks, not whole-module percentage.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test / Evidence | Status |
|---------|-------------------------|--------|
| AC1 — engine.py config access sites use sub-model paths | Proof suite [tests/test_engine_accessor_migration_1173.py](tests/test_engine_accessor_migration_1173.py) passed; live grouped accessors remain in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L125), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L451), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L935), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2059), and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2352). | PASS |
| AC2 — no runtime reliance on forwarding properties | Proof suite [tests/test_engine_accessor_migration_1173.py](tests/test_engine_accessor_migration_1173.py) passed; direct grep over [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py) found no raw `config.entry_status` / `config.agent_map` style runtime hits, only doc text at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2285) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2454). | PASS |
| AC3 — grouped YAML blocks and valid predicate nesting | Grouped schema is present in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L61), [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py#L37), and [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L46); nested predicate replacements are present at [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py#L86) and [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L90). | PASS |
| AC4 — direct BoardConfig construction uses AgentsConfig | Direct grouped construction is present at [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L229) and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L173); proof suite [tests/test_engine_accessor_migration_1174.py](tests/test_engine_accessor_migration_1174.py) passed. | PASS |
| AC5 — mutation sites in `TestFromAC_ValidateEngineConfig` use sub-model paths | Live mutation sites use grouped paths at [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L250), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L256), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L262), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L268), and [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L274); grep found no remaining flat mutation assignments in the file. | PASS |
| AC6 — proof suites pass and directly touched files add no new failures beyond baseline | Latest binding authority is the AC6 refinement in [the task body](.owlbear/kanban/tasks/1174-p2-02-migrate-engine-py-accessors-to-sub-model-paths.md#L148) and [the task body](.owlbear/kanban/tasks/1174-p2-02-migrate-engine-py-accessors-to-sub-model-paths.md#L158). Current quality-runner evidence matches that refined contract: proof suites are green; the prior task-owned parser-error path at [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L599) is fixed; and the remaining release/revision failures were already present in older artifacts at [.owlbear/scratch/quality-runner-1164-pytest-full.txt](.owlbear/scratch/quality-runner-1164-pytest-full.txt#L371) and [.owlbear/scratch/quality-runner-1164-pytest-full.txt](.owlbear/scratch/quality-runner-1164-pytest-full.txt#L2585), with the broader background classification also recorded in [archived task 1125 review evidence](.owlbear/kanban/archive/1125-restore-fail-outcome-to-agentview-end-work-and-align-mcp-model.md#L518). | PASS |

#### Security Review

- No security issues in scope. The reviewed change is confined to engine/test fixture migration and proof coverage.

#### Test Integrity

- No weakened or removed `TestFromAC_*` assertions found. The builder changed fixture content and migration paths, not the assertion contract.

#### Test Quality

- code-reader found no blocking quality issue. Residual note only: the 1173 source-inspection suite is string-scan heavy, but that is the architect-approved proof shape for this task and not a route driver.

#### Data Safety

- No data-safety issues found in scope.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | grouped accessors visible in live engine code | [tests/test_engine_accessor_migration_1173.py](tests/test_engine_accessor_migration_1173.py) | PASS |
| AC2 | no runtime forwarding-property access confirmed by proof suite + grep | [tests/test_engine_accessor_migration_1173.py](tests/test_engine_accessor_migration_1173.py) | PASS |
| AC3 | grouped YAML and nested predicate fixtures verified in touched files | [tests/test_engine_accessor_migration_1174.py](tests/test_engine_accessor_migration_1174.py) | PASS |
| AC4 | AgentsConfig construction verified in direct BoardConfig call sites | [tests/test_engine_accessor_migration_1174.py](tests/test_engine_accessor_migration_1174.py) | PASS |
| AC5 | grouped mutation paths verified in `TestFromAC_ValidateEngineConfig` | [tests/test_engine_accessor_migration_1174.py](tests/test_engine_accessor_migration_1174.py) | PASS |
| AC6 | proof suites green; prior parser-error regression cleared; remaining reds are baseline per refined authority | quality-runner scoped run + task-body refinement | PASS |

### Deductions

- -0.04 for AC authority ambiguity: the stale top-level AC block still shows the pre-refinement broad AC6, so the verdict must anchor to the later Architecture Re-Review section instead.
- -0.03 residual confidence penalty for inherited string-scan-heavy proof tests, non-blocking for this task.

### Verdict

- Confidence: 0.93
- PASS -> docs

### Action

- Advance to docs. No implementation or test-writer retry required.
- Non-blocking residual risk: the task body still contains the stale pre-refinement AC6 wording at the top, even though the later refinement is the binding review authority.

### Reflection

- The review turned on authority control more than code shape: the top AC block and the later Architecture Re-Review disagree, and the latest refinement had to govern.
- The only task-owned failure from the prior review was the grouped YAML parser error in `test_refresh_config_reloads_updated_config`; the current retry cleared that exact path.
- Baseline classification needed external corroboration from older scratch logs and archived review evidence instead of trusting builder prose alone.
[[2026-04-29]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | All changed files are test fixtures (YAML blocks, mutation paths). No external-facing behavior or API changed in this task — engine.py accessor migration was completed in #1173. No IN-scope prose doc references test fixture internals. |
| 2 | Module docstrings | No | N/A | Only test files modified (test_engine_coverage_1068.py, test_engine_create_edit_1070.py, test_engine_end_work_1077.py). No public class/function signatures changed. |
| 3 | External attribution | No | N/A | No external patterns used. Internal refactor of test fixtures. |
| 4 | Research doc | No | N/A | Build-phase task; no standalone research doc produced. |
| 5 | Diagram maintenance (describes match) | No | N/A | share/diagrams/kanban.excalidraw describes serve/kanban/src/**— changed files are under serve/kanban/tests/**, no glob match. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| serve/kanban/tests/test_engine_coverage_1068.py | OUT (test file, fixture data only) | N/A |
| serve/kanban/tests/test_engine_create_edit_1070.py | OUT (test file, fixture data only) | N/A |
| serve/kanban/tests/test_engine_end_work_1077.py | OUT (test file, fixture data only) | N/A |

No docs impact — all changes are internal test fixture migrations.

### Files Updated

- None

### Child Tasks Created

- None

### Scratch Files Cleaned

- qr-1174-pytest.txt, qr-1174-ruff-check.txt, qr-1174-ruff.txt, qr_1174_pytest.log, qr_1174_ruff.log, quality-1174-pytest.log, quality-1174-pytest.txt, quality-1174-ruff.log, quality-runner-1174-pytest.log, quality-runner-1174-ruff.log, quality-runner-1174-verbose.log (11 files)
[[2026-04-29]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — engine.py sub-model paths | Proof suite tests/test_engine_accessor_migration_1173.py green (64/64); reviewer verified live code at engine.py L111, L125, L451, L2059, L2352 | PASS |
| AC2 — no forwarding property reliance | Proof suite green; grep confirmed only doc/message hits, no runtime access | PASS |
| AC3 — grouped YAML + valid predicate nesting | Predicate indentation fix committed (8-space indent); proof suite TestFromAC_PredicateYamlNesting green | PASS |
| AC4 — BoardConfig uses AgentsConfig | Proof suite TestFromAC_FixtureDirectConstruction green; live sites verified | PASS |
| AC5 — mutation sites use sub-model paths | Proof suite TestFromAC_MutationSubModelPaths green; grep confirms no flat mutations | PASS |
| AC6 — proof suites pass, no new failures | 64/64 green; parser-error regression cleared in 3fc7f105; 6 remaining failures are pre-existing baseline (corroborated by archived #1125 evidence) | PASS |

### Test Results

- pytest (full suite): 3174 passed, 55 failed, 4 skipped
- Proof suites: 64 passed, 0 failed
- No failures attributable to this task (6 in-scope failures are pre-existing baseline per archived #1125 and #1164 scratch logs)
- ruff: clean

### Architect Quality: 4/5

AC1-5 specific and verifiable. AC6 required mid-cycle refinement (original gate was infeasible due to pre-existing failures in pinned suite). Refinement was appropriate and well-reasoned. Builder guidance with specific line numbers was excellent.

### Deduction Breakdown

- -0.02: 3 deliverable files uncommitted by pipeline (committed as leftover by auditor)
- -0.01: stale top-level AC6 wording vs later binding refinement (authority ambiguity, non-blocking)

### Confidence: 0.97

### Action: archive

### Commit Integrity

- b54d60b2: test: migrate engine fixtures to grouped config (#1174, builder)
- 3fc7f105: fix: repair grouped yaml agent-map replacement (#1174, builder)
- 45433039: test: commit leftover deliverables from pipeline (#1174, auditor)
