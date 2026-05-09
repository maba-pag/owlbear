---
id: 1474
title: 'P4-23: Task-scoped and cockpit test alignment (AC5 Cat-B2)'
status: in-progress
priority: critical
created: 2026-05-09T08:46:53.940620+00:00
updated: 2026-05-09T13:04:50.639610+00:00
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