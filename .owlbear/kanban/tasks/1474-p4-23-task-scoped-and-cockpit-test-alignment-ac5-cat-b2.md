---
id: 1474
title: 'P4-23: Task-scoped and cockpit test alignment (AC5 Cat-B2)'
status: backlog
priority: critical
created: 2026-05-09T08:46:53.940620+00:00
updated: 2026-05-09T15:18:27.096168+00:00
tags:
- phase-4
- type:refactor
- scope:tests
- topology
- test
parent: 1439
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Context
Parent #1439 collapsed configurable kanban topology into product constants. AC1-4 implementation is committed and working. This subtask remediates ~390 failures across task-scoped test files (test_*_NNNN.py) and cockpit tests in `tests/`.

## Scope
In scope: all failing tests in `tests/` EXCEPT the 4 durable config test files (Cat-B1 / #1473) and 3 non-topology frontend verification files.
Out of scope: tests/test_config_loader.py, tests/test_config_authority.py, tests/test_config_schema.py, tests/test_config_grouped.py (Cat-B1), tests/test_cockpit_pds_build_compat_1364.py, tests/test_cockpit_pds_build_compat_1365.py, tests/test_cockpit_react_compiler.py (non-topology frontend tests), serve/kanban/tests/ (Cat-A), serve/mcp-kanban/tests/ (Cat-C).

## Acceptance Criteria
1. All task-scoped and cockpit tests in `tests/` (excluding 4 durable config files AND 3 non-topology frontend files) pass after aligning with the topology-constant refactor. Verify: `uv run pytest tests/ --ignore=tests/test_config_loader.py --ignore=tests/test_config_authority.py --ignore=tests/test_config_schema.py --ignore=tests/test_config_grouped.py --ignore=tests/test_cockpit_pds_build_compat_1364.py --ignore=tests/test_cockpit_pds_build_compat_1365.py --ignore=tests/test_cockpit_react_compiler.py` exits 0. (td:2)

## Breaking Changes to Align With
1. `load_config` returns product defaults instead of raising `FileNotFoundError` when config.yml absent.
2. `save_config` persists only `next_id`.
3. `BoardConfig` topology values are product-fixed constants from `PRODUCT_TOPOLOGY`.
4. Canonical status tuple: (research, backlog, todo, in-progress, review, docs, done).

## Mechanical Pattern (proven on 5 files, 77 tests green)
Every test file with `_CONFIG_YAML` containing topology fields needs the same fix: replace the full topology YAML with `next_id: 1` only. The assertions in these files test current cockpit code behavior and do NOT need changes — they pass once the engine initializes correctly.

Find `_CONFIG_YAML = """\` blocks containing `statuses:`, `priorities:`, `agent_map:`, etc. Replace entire `_CONFIG_YAML` value with:
```python
_CONFIG_YAML = """\
next_id: 1
"""
```

Builder already proved this pattern on: test_cockpit_cache_populate.py, test_cockpit_cache_sse_1346.py, test_cockpit_cache_sse_1401.py, test_cockpit_decisions_api_1190.py, test_cockpit_error_envelope_1370.py.

## Scale Note
This is the largest subtask (~390 failures across many files). The patterns are mechanical and repetitive. Task-scoped test files (test_*_NNNN.py) are for archived tasks — their fixtures need topology-constant alignment but they remain valid regression tests and must NOT be deleted.

## Pipeline Note
Tests already exist and fail (RED). Builder updates test expectations to match the new API contract (GREEN). No separate test-writer step needed.

[[2026-05-09]]

## Architecture Re-Review (post-builder rejection)

### Builder Rejection Analysis
Builder fixed 5 files (77 passing) with topology-fixture alignment, then ran AC command: 399 failed / 2882 passed / 4 skipped. Builder concluded scope exceeds "mechanical topology alignment" and recommended splitting into topology-fixture, error-envelope, mutation-route, and frontend categories.

**Architect finding: builder's multi-domain categorization is incorrect.** Evidence:
1. Builder successfully fixed `test_cockpit_error_envelope_1370.py` (an error envelope test) with ONLY topology-fixture alignment → 77 tests green. Proves error envelope tests fail because of stale `_CONFIG_YAML`, not error envelope contract changes.
2. Read `test_cockpit_error_envelope_1371.py:L170-190` and `test_cockpit_mutation_api_1135.py:L310-320` — both assert `{code, message}` format (the CURRENT contract): `"detail" not in body`, `body.get("code") == "ERR_STALE"`. Root cause is fixture initialization failure, not assertion mismatch.
3. Three frontend files have zero `config.yml` references — they run npm subprocess commands. Tasks #1364/#1365/#1015 are archived; these are stale-docstring regression tests. Excluded from AC as non-topology.

### AC Refinement
- Added 3 `--ignore` entries to AC verification command for non-topology frontend files
- Updated Scope section to document all 7 exclusions
- Added Mechanical Pattern section with proven fix and file list

### Evaluation (delta from prior review)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Unchanged — topology-fixture alignment only |
| Interface clarity | PASS (refined) | AC excludes 3 non-topology frontend files |
| Dependency correctness | PASS | No new dependencies |
| KISS/YAGNI | PASS | Mechanical pattern, no over-engineering |
| Premise challenge | PASS | Builder's own 5-file success proves the pattern works |

### Challenge Results
- Challenger: block (confidence 0.24) — raised: (1) AC not updated in task body, (2) no recorded proof of narrowed command, (3) unsupported causal leap re error envelope, (4) frontend task status (archived, not incomplete).
- Architect response:
  - **ACCEPTED (1):** AC updated via body replace.
  - **REBUTTED (2):** Architecture review defines the gate; the builder proves it.
  - **REBUTTED (3):** Read actual assertions — they test CURRENT contract. Builder's own 1370 fix (identical patterns) with ONLY fixture alignment → 77 green is conclusive.
  - **ACCEPTED (4):** Corrected premise — tasks are archived, not incomplete. Exclusion rationale: npm subprocess tests with zero topology dependency.

### Test Depth
- AC1: td:2 (unchanged, already annotated)
- Test-writer: SKIP (pass-through via `test` tag)

### Verdict: APPROVE → todo

[[2026-05-09]]
Architecture re-review after builder rejection. Builder's multi-domain split recommendation was incorrect — read actual assertions in error envelope and mutation tests: they test CURRENT contract ({code, message} format) and fail only because of stale _CONFIG_YAML fixtures. Builder's own fix of test_cockpit_error_envelope_1370.py with ONLY fixture alignment → 77 green is conclusive proof. Refined AC: excluded 3 non-topology frontend files (npm subprocess tests for archived tasks #1364/#1365/#1015). Added Mechanical Pattern section with proven fix. Challenger raised 4 issues (block, 0.24): accepted 2 (AC updated, frontend premise corrected), rebutted 2 (arch review doesn't run builder commands; error envelope assertions test current contract).
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged `test`) — no tests applicable.
- Passing through to builder.
- Rationale: tests already exist and fail (RED). Builder aligns them with the topology-constant refactor (GREEN). Task body explicitly marks test-writer as SKIP.
[[2026-05-09]]
## Builder Notes
- Attempted mechanical topology-fixture alignment exactly per task guidance: replaced in-scope `_CONFIG_YAML` topology blocks with `next_id: 1` across all matching files in `tests/` (excluding durable config file `tests/test_config_loader.py` per AC exclusions).
- Verification (quality-runner, scoped to AC command ignores) remained unchanged at **3042 passed / 204 failed / 0 skipped** before and after mechanical pass.
- Representative persistent failures are outside topology-fixture initialization and indicate broader contract drift (examples):
  - `tests/test_engine_accessor_migration.py::TestFromAC_SubmodelAccessPaths::test_engine_source_contains_pipeline_wave_size`
  - `tests/test_mcp_memory_1266.py::TestFromAC_MemoryEntryModel::test_valid_entry_created_with_new_fields`
  - `tests/test_state_machine.py::TestFromAC_StoreLearning::test_store_learning_returns_pending_state`
  - `tests/test_engine_validation_push.py::TestFromAC_ValidateStatusPredicate::test_unsatisfied_predicate_raises`
  - `tests/test_cockpit_models.py::TestFromAC_TaskDetailKeysConstantFix::test_task_detail_keys_does_not_contain_claimed_by`
- Lint status: `ruff` clean on `tests/`.
- Coverage snapshot from scoped run: 66% overall (not a gating signal here because AC pass condition itself is not reachable under current failure mix).
- No GREEN commit made; task rejected due AC/coverage of failure categories being broader than stated mechanical scope.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope #1474 into topology-only fixture alignment vs non-topology contract/regression buckets, each with explicit AC and verification command | tests/ | quality-runner scoped run stayed at 204 failures pre/post mechanical pass |
| 2 | architect | Add explicit include/exclude test manifests (or `-k` selectors) for #1474 so builder verification covers only intended failing domains | tests/ | Persistent failures in memory/state-machine/accessor-model suites not explained by topology fixture guidance |
| 3 | architect | Create follow-up tasks for non-topology failures now blocking AC pass (engine accessor migration, memory entry model, state-machine/validation, cockpit model contract) | tests/test_engine_accessor_migration.py, tests/test_mcp_memory_1266.py, tests/test_state_machine.py, tests/test_engine_validation_push.py, tests/test_cockpit_models.py | unchanged failures after full topology fixture rewrite |

[[2026-05-09]]


## AC Revision (Second Architecture Re-Review)

**Supersedes AC1 above.** Builder and reviewer: use the verification commands from THIS section.

### Root Cause Analysis

Builder's second attempt applied the mechanical fix but the AC verification command (`uv run pytest tests/ --ignore=<7 files>`) caught 204 failures from tests unrelated to topology. Codebase audit confirms:
- 21 test files in `tests/` still contain unfixed topology YAML (various constant names: `_BASE_CONFIG`, `_GROUPED_CONFIG`, `_KANBAN_CONFIG`, `_CONFIG_TEMPLATE`, `_PREDICATE_CONFIG`, `_LEGACY_CONFIG_YAML`, `_BASE_CONFIG_COMPLETE`, `_BASE_CONFIG_WITH_DOCS`)
- 6 of those 21 have dual failure modes (topology fixture + unimplemented feature or broken premise); they will still fail after mechanical fix
- ~40 test files in `tests/` fail for domains entirely outside kanban topology (memory engine, knowledge, browser, agent scope, dead code cleanup, etc.)

### Revised AC

**AC1 (td:2):** Apply mechanical topology-fixture alignment to all 21 files listed below. Replace all topology fields in config YAML blocks with `next_id: N` only (preserving original next_id value; default to 1 if absent). Verify:
```bash
grep -rn 'statuses:\|priorities:\|agent_map:\|entry_status:\|terminal_status:\|wave_size:\|agent_types:\|agent_compatibility:\|non_impl_tags:\|archival_reasons:\|status_predicates:\|claim_timeout:\|schema:\s*grouped\|pipeline:\|agents:\|policy:\|defaults:\|archive_dir:\|tasks_dir:\|activity_log:' \
  tests/test_engine_end_work_fail.py tests/test_schema_roundtrip.py tests/test_engine_create_edit_1203.py \
  tests/test_dispatch_gate_port.py tests/test_cockpit_launch.py tests/test_pick_tasks_resolve.py \
  tests/test_engine_create_edit_1072.py tests/test_engine_dep_lookup.py tests/test_engine_occ.py \
  tests/test_engine_lazy_agent_map.py tests/test_engine_cockpit_view.py tests/test_support_migration.py \
  tests/test_engine_release_note.py tests/test_engine_dispatch_validation.py tests/test_engine_end_work.py \
  tests/test_engine_ble001.py tests/test_engine_accessor_migration.py tests/test_engine_validation_push.py \
  tests/test_engine_release_task_occ.py tests/test_config_cleanup.py tests/test_end_work_success.py
```
returns empty (exit 1, no matches).

**AC2 (td:2):** After fix, run pytest on the 15 files expected to pass (21 minus 6 dual-issue exclusions):
```bash
uv run pytest \
  tests/test_engine_end_work_fail.py \
  tests/test_engine_create_edit_1203.py \
  tests/test_dispatch_gate_port.py \
  tests/test_cockpit_launch.py \
  tests/test_pick_tasks_resolve.py \
  tests/test_engine_create_edit_1072.py \
  tests/test_engine_dep_lookup.py \
  tests/test_engine_occ.py \
  tests/test_engine_lazy_agent_map.py \
  tests/test_engine_cockpit_view.py \
  tests/test_support_migration.py \
  tests/test_engine_release_note.py \
  tests/test_engine_end_work.py \
  tests/test_engine_ble001.py \
  tests/test_engine_release_task_occ.py
```
exits 0.

**Bounded latitude (AC2 only):** If up to 3 of the 15 files still fail after the mechanical fix for reasons unrelated to topology fixtures, the builder may exclude them from the AC2 command AND document each with: (a) file name, (b) root cause category, (c) representative failing assertion. These become follow-up tasks. If >3 fail, reject for re-scoping.

### 21-File Manifest

**Fix and verify (15 files):**
| # | File | Config constant(s) |
|---|------|--------------------|
| 1 | tests/test_engine_end_work_fail.py | `_BASE_CONFIG` |
| 2 | tests/test_engine_create_edit_1203.py | `_BASE_CONFIG` |
| 3 | tests/test_dispatch_gate_port.py | `_BASE_CONFIG`, `_BASE_CONFIG_WITH_DOCS` |
| 4 | tests/test_cockpit_launch.py | `_KANBAN_CONFIG` |
| 5 | tests/test_pick_tasks_resolve.py | `_BASE_CONFIG` |
| 6 | tests/test_engine_create_edit_1072.py | `_BASE_CONFIG` |
| 7 | tests/test_engine_dep_lookup.py | `_BASE_CONFIG` |
| 8 | tests/test_engine_occ.py | `_BASE_CONFIG` |
| 9 | tests/test_engine_lazy_agent_map.py | `_BASE_CONFIG_COMPLETE` + 3 other variants (lines 71,107,141) |
| 10 | tests/test_engine_cockpit_view.py | `_BASE_CONFIG` |
| 11 | tests/test_support_migration.py | `_GROUPED_CONFIG` |
| 12 | tests/test_engine_release_note.py | `_BASE_CONFIG` |
| 13 | tests/test_engine_end_work.py | `_BASE_CONFIG` |
| 14 | tests/test_engine_ble001.py | `_BASE_CONFIG` |
| 15 | tests/test_engine_release_task_occ.py | `_BASE_CONFIG` |

**Fix but exclude from verification (6 files — dual topology + non-topology failure):**
| # | File | Non-topology root cause |
|---|------|------------------------|
| 16 | tests/test_engine_accessor_migration.py | Tests sub-model access paths (config.pipeline.statuses) not yet implemented |
| 17 | tests/test_engine_validation_push.py | Tests per-board predicates; PRODUCT_TOPOLOGY has empty status_predicates |
| 18 | tests/test_engine_dispatch_validation.py | Injects invalid topology via config YAML to test rejection; load_config now ignores YAML topology |
| 19 | tests/test_end_work_success.py | Tests end_work success path derivation (RED test for #1336, unimplemented) |
| 20 | tests/test_config_cleanup.py | Tests agent_name removal from KanbanEngine.__init__ (RED test for #1343, unimplemented) |
| 21 | tests/test_schema_roundtrip.py | `_LEGACY_CONFIG_YAML` tests migration from v9 format; migration premise broken by topology collapse |

### Mechanical Pattern (expanded)

All config blocks above use different constant names but the same fix applies. Replace the ENTIRE multi-line string value with `next_id: N` only. The constant NAME stays unchanged. Examples:

```python
# BEFORE (any variant name)
_BASE_CONFIG = """\
statuses:
  - research
  ...many topology fields...
next_id: 100
"""

# AFTER
_BASE_CONFIG = """\
next_id: 100
"""
```

For files with MULTIPLE config constants (test_dispatch_gate_port.py has `_BASE_CONFIG` and `_BASE_CONFIG_WITH_DOCS`; test_engine_lazy_agent_map.py has 4 variants), fix ALL constants in the file.

For test_engine_dispatch_validation.py: the `_CONFIG_TEMPLATE` uses `dedent()` and `{statuses_yaml}` / `{priorities_yaml}` placeholders. Replace the entire template with `next_id: 1\n` (the template is only consumed by `_make_board` which writes config.yml).

### Test Depth
- AC1: td:2 (grep verification)
- AC2: td:2 (pytest verification)
- Test-writer: SKIP (pass-through via `test` tag)

[[2026-05-09]]
## Architecture Review (Second Re-Review)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Topology-fixture alignment only — 21 files, one mechanical pattern |
| Interface clarity | PASS (refined) | Explicit 21-file manifest with config constant names; 6 dual-issue files excluded with documented root causes |
| Dependency correctness | PASS | No dependencies; parent #1439 AC1-4 committed |
| Module layering | N/A | Test fixtures only |
| TDD compliance | PASS | Pass-through via `test` tag; tests already exist (RED→GREEN) |
| KISS/YAGNI | PASS | Mechanical find-replace, no over-engineering |
| Premise challenge | PASS | Builder's own 5-file proof confirms pattern; codebase audit found 16 more unfixed files |
| Pattern consistency | PASS | Same pattern used across all variant config names |
| Security surface | N/A | Test fixtures only |
| Single domain | PASS | Kanban topology alignment across all files |

### Challenge Results
- Challenger: block (confidence 0.29) — raised 5 issues: (1) no published file manifest, (2) verification gate still shows old 7-file ignore, (3) fixture-shape diversity (BASE_CONFIG, GROUPED_CONFIG, etc.), (4) special-case exclusions not operationalized, (5) unbounded latitude clause
- Architect response:
  - **ACCEPTED (1):** Published complete 21-file manifest with config constant names in task body
  - **ACCEPTED (2):** Replaced old AC1 with two-part revised AC (grep gate + focused pytest on 15 files)
  - **ACCEPTED (3):** Manifest includes all variant names; mechanical pattern section shows universal fix
  - **ACCEPTED (4):** 6 exclusions documented with specific non-topology root causes
  - **ACCEPTED (5):** Latitude capped at max 3 files, each requiring: file name, root cause category, representative assertion. >3 triggers rejection

### Test Depth
- AC1: td:2 (grep verification)
- AC2: td:2 (pytest on 15 files)
- Test-writer: SKIP (pass-through via `test` tag)

### Verdict: APPROVE → todo
Refined AC with complete 21-file manifest, frozen verification commands, and bounded latitude clause. Previous AC verification command was too broad (caught 204 non-topology failures). New AC2 runs pytest on exactly 15 newly-fixed files expected to pass after mechanical topology-fixture alignment.
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged `test`) — no tests applicable. Second pass-through.
- Passing through to builder.
- Rationale: tests already exist in `tests/` and fail (RED). Builder applies mechanical topology-fixture alignment to the 21-file manifest (AC1 + AC2). Revised AC explicitly states "Test-writer: SKIP (pass-through via `test` tag)". No new test file needed.
[[2026-05-09]]
## Builder Notes
- Implementation: applied the mechanical topology-fixture alignment across the full 21-file manifest by replacing topology-heavy config fixture blocks/templates with `next_id`-only values (preserving declared `next_id` values where present).
- AC1 gate: topology-key grep no longer isolates to a clean fixture-only zero state because several files still include key names in assertion/message literals and migration-intent source checks; gate interpretation is ambiguous after mechanical rewrite.
- AC2 verification command executed on the 15-file pass set: **exit 1**.
- Test results: **290 passed, 19 failed**.
- Lint: `ruff` clean on all touched files.
- Coverage: not reported as gate evidence because AC2 pass gate itself failed.
- Commit: none (rejected path).

Representative AC2 failures (from 19 total):
- `tests/test_dispatch_gate_port.py::TestFromAC_BucketCompatibilityRegressionGuard::test_incompatible_agent_buckets_go_to_different_waves`
- `tests/test_engine_ble001.py::TestFromAC_PickTasksWarningLogs::test_pick_tasks_import_error_is_caught_and_logged`
- `tests/test_engine_create_edit_1203.py::TestFromAC_EmptyTitleErrorCode::{empty_title,whitespace_title}`
- `tests/test_pick_tasks_resolve.py::TestFromAC_PickTasksResolveIntegration::{test_resolve_runs_before_task_filtering,test_no_pending_drs_pick_tasks_works,test_no_decisions_directory_pick_tasks_works}`
- `tests/test_engine_lazy_agent_map.py` (12 failures across `TestFromAC_PickTasksValidatesAgentMap` and `TestFromAC_McpPickTasksRaisesForIncompleteAgentMap`)
- `tests/test_engine_end_work.py::TestFromAC_GuidanceExact::test_reject_backwards_multi_step_guidance_exact_list`

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reconcile AC1/AC2 contradiction between “remove topology fields mechanically” and behavior tests that depend on non-default topology semantics (agent_map completeness, bucket compatibility, dispatch/missing-entry error paths) | tests/test_dispatch_gate_port.py, tests/test_engine_lazy_agent_map.py, tests/test_pick_tasks_resolve.py, tests/test_engine_ble001.py | AC2 run: 19 failures after full mechanical rewrite; bounded latitude (>3) exceeded |
| 2 | architect | Publish a fixture-scope-safe AC1 matcher that excludes assertion/doc/message strings and code-inspection literals, or replace grep gate with structural check limited to config fixture constants | tests/test_engine_accessor_migration.py, tests/test_support_migration.py, tests/test_engine_dispatch_validation.py | Current key grep catches non-fixture literals/messages, making AC1 pass criterion non-deterministic |
| 3 | architect | Split verification into topology-fixture-only suites vs topology-dependent behavioral suites, with explicit include lists and expected verdicts per bucket | tests/test_engine_lazy_agent_map.py, tests/test_dispatch_gate_port.py, tests/test_engine_end_work.py, tests/test_engine_create_edit_1203.py | AC2 “15 files expected to pass” not reachable under current fixture rewrite contract |
| 4 | architect | Clarify whether mixed-purpose constants in same file (example: compatibility/bucket configs) must be exempted from next_id-only rewrite | tests/test_dispatch_gate_port.py | Post-rewrite regression in bucket compatibility test indicates non-mechanical behavior coupling |
