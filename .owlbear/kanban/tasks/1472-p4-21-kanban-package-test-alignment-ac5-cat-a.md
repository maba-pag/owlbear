---
id: 1472
title: 'P4-21: Kanban package test alignment (AC5 Cat-A)'
status: todo
priority: critical
created: 2026-05-09T08:46:53.913029+00:00
updated: 2026-05-09T11:51:53.378247+00:00
tags:
- phase-4
- scope:tests
- topology
- type:test
parent: 1439
depends_on: []
blocked: false
block_reason:
claimed_at: 2026-05-09T11:51:53.378247+00:00
archival_reason:
archival_refs: []
---


## Context
Parent #1439 collapsed configurable kanban topology into product constants. AC1-4 implementation is committed and working. This subtask remediates ~71 test failures in `serve/kanban/tests/` caused by the refactor.

## Scope
In scope: all failing tests in `serve/kanban/tests/`.
Out of scope: root-level tests (`tests/`), consumer package tests (`serve/mcp-kanban/tests/`).

## Acceptance Criteria
1. All tests in `serve/kanban/tests/` pass (`uv run pytest serve/kanban/tests/` exits 0) after aligning test expectations with the topology-constant refactor. (td:2)

## Breaking Changes to Align With
1. `load_config(kanban_dir)` no longer raises `FileNotFoundError` when config.yml is absent — returns a `BoardConfig` built from `PRODUCT_TOPOLOGY` constants. Only reads `next_id` from config.yml when present.
2. `save_config(config, kanban_dir)` persists only `next_id` to config.yml, not topology fields.
3. `BoardConfig` topology values (statuses, priorities, agent_map, non_impl_tags, archival_reasons, etc.) are product-owned constants. Custom values in config.yml are ignored.
4. Canonical status tuple: (research, backlog, todo, in-progress, review, docs, done). No "released" status.

## Key Files (~71 failures)
- test_storage.py — custom BoardConfig construction, config round-trip
- test_storage_1050.py — save_config round-trip, allocate_next_id
- test_storage_io.py — AC-C51 crash safety with save_config
- test_engine_coverage_1068.py — custom config with "released" status, session tests
- test_engine_init_1068.py — custom BoardConfig construction
- test_engine_coverage_1110.py — session lifecycle
- test_engine_archived_edit_1120.py — save_config format verification
- test_engine_activity.py — session state filtering
- test_engine_atomicity_1104.py — sweep operations
- test_engine_storage.py — sweep operations
- test_list_sessions.py — session filtering with "released"

## Mechanical Patterns
- Replace custom BoardConfig topology field overrides with product-topology values or remove them (topology is now product-owned)
- Update config round-trip assertions: save_config persists only `next_id`, not full topology
- Replace "released" status references with valid product-topology statuses
- Update status ordering assertions to match canonical tuple
- Remove `FileNotFoundError` expectations for absent config.yml — load_config now returns defaults

## Pipeline Note
Tests already exist and fail (RED). Builder updates test expectations to match the new API contract (GREEN). No separate test-writer step needed — this IS the test remediation.

[[2026-05-09]]

## Builder Guidance: "released" status disambiguation
Some test files use "released" in two distinct contexts:
- **Topology status** (test_engine_coverage_1068.py): tests that construct BoardConfig with "released" as a custom status. These should use a valid product-topology status (e.g., "done") instead.
- **Session state** (test_list_sessions.py, test_engine_activity.py): tests that filter sessions by "released" state. If "released" is a session lifecycle state (not a task status), verify whether it still exists in the session model before replacing it. If session state uses the same status enum, replace with a valid topology status.

The key files list covers the primary failures but the AC applies to ALL files in `serve/kanban/tests/` (~35 files). Unlisted files like test_corruption.py, test_engine_end_work_1077.py, and test_engine_reads_1069.py may also have topology-coupled failures — check and fix all.
[[2026-05-09]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: fix test failures in `serve/kanban/tests/` |
| Interface clarity | PASS | Single clear AC: all tests pass. Body provides breaking changes, key files, mechanical patterns |
| Dependency correctness | PASS | No dependencies — siblings (#1473–#1475) target different directories, parallelizable |
| Module layering | PASS | Test-only changes, no source modifications |
| TDD compliance | PASS | Failing tests ARE the RED phase; tag changed to `type:test` for test-writer pass-through |
| KISS/YAGNI | PASS | Mechanical remediation, no new abstractions |
| Premise challenge | PASS | Required by auditor rejection of parent #1439 (498 failures / 92 files) |
| Pattern consistency | PASS | Aligns with test-remediation patterns |
| Security surface | N/A | Test-only changes |
| Single domain | PASS | kanban domain only |
| Failure Mode Map | N/A | Test-fixing task, no production codepaths |
| Decision-request verification | N/A | No research doc |
| User-action detection | SKIP | Counter-signal C1: AC defines testable outcome (pytest exits 0) |

### Refinements Applied
1. **Tag swap:** `type:refactor` → `type:test` to enable test-writer pass-through. Existing failing tests ARE the RED phase; builder remediates directly.
2. **Builder guidance added:** Disambiguated "released" as topology status vs. session state — two distinct contexts requiring different remediation approaches.
3. **Scope note added:** Key files list is guidance, not scope boundary. AC covers all ~35 files in `serve/kanban/tests/`, including unlisted topology-coupled files.

### Challenge Results
- Challenger: reconsider (confidence 0.68)
- 4 challenges raised: (1) routing tag mismatch — ACCEPTED, fixed with type:test swap; (2) scope evidence — REBUTTED, AC covers all files in directory; (3) "released" contract distinction — PARTIALLY ACCEPTED, added builder guidance; (4) proof shape / weakening risk — REBUTTED, caught by reviewer step
- 3 blind spots: failure count unverified (AC doesn't depend on count), routing pattern shared across siblings (each gets own review), suite weakening (reviewer catches)
- Architect response: incorporated challenges 1 and 3 into refinements, rebutted 2 and 4 with evidence

### Test Depth
- AC1: td:2 (already annotated — multiple files, multiple patterns, edge cases)
- Test-writer: SKIP (type:test tag — pass-through)

### Verdict: APPROVE → todo
AC is clear and verifiable. Architecture is sound (test-only, well-scoped). Routing fixed for pipeline compatibility.
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged type:test) — no tests applicable.
- Passing through to builder.
[[2026-05-09]]
## Builder Notes
- Claimed task and executed RED verification on `serve/kanban/tests/`.
- Result: `71 failed, 1255 passed` (pytest), plus `3` ruff violations (F811 import redefinitions) in test files.
- No source-code changes made.
- No test changes made.

### Why Rejected
This task is test-remediation, but the failing set is dominated by obsolete `TestFromAC_*` assertions that now contradict product-owned topology behavior (`load_config` ignores topology in `config.yml`, grouped submodels on `BoardConfig`, canonical statuses include `docs`, no `released`).

Builder-mode constraints for this run prohibit modifying `TestFromAC_*` classes. The required remediation is primarily inside those classes (assertions and expectations), so implementation is infeasible without test-writer ownership.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Rewrite obsolete config-validation assertions to topology-constant contract (no `entry_status`/`terminal_status` root fields; grouped pipeline/policy access; load_config defaults) | serve/kanban/tests/test_engine_init_1067.py, serve/kanban/tests/test_engine_init_1068.py | pytest failures: `DID NOT RAISE ConfigError`, `AttributeError: BoardConfig has no attribute entry_status/terminal_status/archival_reasons` |
| 2 | test-writer | Replace `released` status expectations with canonical status model and current session/action semantics | serve/kanban/tests/test_engine_coverage_1068.py, serve/kanban/tests/test_list_sessions.py, serve/kanban/tests/test_engine_activity.py | pytest failures: `assert 'release' == 'released'`, `assert 'released' in cfg.statuses` |
| 3 | test-writer | Update pick_tasks expectations to current dispatch behavior (agent map values, wave assembly, default caps/sorting contracts where changed) | serve/kanban/tests/test_engine_pick_tasks_1074.py, serve/kanban/tests/test_engine_pick_tasks_1076.py | pytest failures across AC22/AC23 assertions showing mismatched expected waves/agents/order |
| 4 | test-writer | Adjust migration/storage expectations to next_id-only config persistence and current migration summaries | serve/kanban/tests/test_migrate.py, serve/kanban/tests/test_storage.py, serve/kanban/tests/test_storage_1050.py | pytest failures: legacy field expectations, Already/Migrated count assumptions, archive path/file assumptions |
| 5 | test-writer | Fix lint-only import redefinition violations | serve/kanban/tests/test_corruption.py, serve/kanban/tests/test_storage.py | ruff F811 violations |

### Evidence Summary
- RED baseline command: `uv run pytest serve/kanban/tests/ -q --tb=line -n 0`
- Failing nodes: 71 across 15 files.
- Key categories: obsolete topology validation expectations, removed/relocated BoardConfig fields, non-canonical status `released`, migration output assumptions, and stale fixture path assumptions.
