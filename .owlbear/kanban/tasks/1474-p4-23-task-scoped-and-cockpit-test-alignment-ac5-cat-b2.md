---
id: 1474
title: 'P4-23: Task-scoped and cockpit test alignment (AC5 Cat-B2)'
status: in-progress
priority: critical
created: 2026-05-09T08:46:53.940620+00:00
updated: 2026-05-09T10:12:34.867557+00:00
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
In scope: all failing tests in `tests/` EXCEPT the 4 durable config test files (those are Cat-B1 / #1473).
Out of scope: tests/test_config_loader.py, tests/test_config_authority.py, tests/test_config_schema.py, tests/test_config_grouped.py (Cat-B1), serve/kanban/tests/ (Cat-A), serve/mcp-kanban/tests/ (Cat-C).

## Acceptance Criteria
1. All task-scoped and cockpit tests in `tests/` (excluding the 4 durable config files) pass after aligning with the topology-constant refactor. Verify: `uv run pytest tests/ --ignore=tests/test_config_loader.py --ignore=tests/test_config_authority.py --ignore=tests/test_config_schema.py --ignore=tests/test_config_grouped.py` exits 0 with no new failures. (td:2)

## Breaking Changes to Align With
1. `load_config` returns product defaults instead of raising `FileNotFoundError` when config.yml absent.
2. `save_config` persists only `next_id`.
3. `BoardConfig` topology values are product-fixed constants from `PRODUCT_TOPOLOGY`.
4. Canonical status tuple: (research, backlog, todo, in-progress, review, docs, done).

## Mechanical Patterns (apply across all files)
- **BoardConfig fixture construction**: Replace stale custom topology values (statuses, priorities, agent_map, etc.) with product-topology values, or remove topology field overrides entirely since they are now product-owned.
- **Custom status lists**: Replace non-canonical statuses with product-topology statuses.
- **Config fixture YAML files**: Update fixture config.yml files to match next_id-only format (topology fields no longer persisted).
- **Status ordering assertions**: Align with product-topology ordering.
- **FileNotFoundError expectations**: load_config now returns defaults; remove/update these assertions.

## Scale Note
This is the largest subtask (~390 failures across many files). The patterns are mechanical and repetitive. Task-scoped test files (test_*_NNNN.py) are for archived tasks — their fixtures need topology-constant alignment but they remain valid regression tests and must NOT be deleted.

## Pipeline Note
Tests already exist and fail (RED). Builder updates test expectations to match the new API contract (GREEN). No separate test-writer step needed.

[[2026-05-09]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: update task-scoped + cockpit tests for topology-constant alignment |
| Interface clarity | PASS | Single AC with clear pytest verification command |
| Dependency correctness | PASS | Layer 1 parallel — no shared conftest fixtures, no cross-task file overlap |
| Module layering | N/A | Test-only changes |
| TDD compliance | N/A | This IS the test remediation (RED already exists) |
| KISS/YAGNI | PASS | Mechanical fixture updates, no over-engineering |
| Premise challenge | PASS | Parent #1439 topology refactor broke ~390 tests — remediation required |
| Pattern consistency | PASS | Follows decomposition from parent #1439 planning |
| Security surface | N/A | Test-only changes |
| Single domain | PASS | Tests domain only |
| Failure Mode Map | N/A | Test-only changes |
| Decision-request verification | N/A | No research doc |
| User-action detection | SKIP | C1: AC defines testable pytest command |

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1 (td:2): pytest exits 0 on tests/ minus 4 config files | Verifiable, precise verification command, correct exclusion list | No change needed |

### Refinement Applied
- **Added `test` tag** to trigger test-writer pass-through. Task body Pipeline Note says "No separate test-writer step needed" — the `test` tag enforces this via pipeline routing rules. Without it, `type:refactor` + `scope:tests` would NOT trigger automatic pass-through at the test-writer gate.

### Challenge Results
- Challenger: block (confidence 0.42) — raised 5 issues: (1) pipeline routing tag mismatch (critical), (2) scope atomicity (moderate), (3) coupling evidence (moderate), (4) scope definition (moderate), (5) AC precision (minor).
- Architect response:
  - **ACCEPTED (1):** Added `test` tag for correct pipeline routing.
  - **ACCEPTED (5):** "exits 0 with no new failures" is redundant — "exits 0" is the binding gate. Minor wording issue, no AC rewrite needed since "exits 0" is unambiguous.
  - **REBUTTED (2):** All ~390 failures share one root cause (topology-constant refactor). Fix patterns are identical across files (align fixtures with product-topology values). Further decomposition would create many micro-tasks with identical patterns — more orchestration overhead than value.
  - **REBUTTED (3):** Inter-module coupling (e.g., test_cockpit_mutation_api_1135.py → test_cockpit_mutation_api.py) is WITHIN Cat-B2 scope. Builder updates both files. Not a cross-task conflict.
  - **REBUTTED (4):** Including test_kanban_topology_1439.py (68 passing parent tests) in the sweep is intentional as a regression check. If Cat-B2 changes break parent tests, we want to catch that.

### Codebase Context
- `PRODUCT_TOPOLOGY` exists at `serve/kanban/src/owlbear_kanban/topology.py:32` (17 categories, confirmed)
- No topology fixtures in root `conftest.py` or `tests/conftest.py` (doesn't exist)
- ~54 task-scoped files + ~36 cockpit test files in `tests/` — all in scope except 4 Cat-B1 exclusions
- Cat-A (`serve/kanban/tests/`) and Cat-C (`serve/mcp-kanban/tests/`) are excluded by the pytest command targeting only `tests/`
- Breaking changes documented in task body are accurate and match committed AC1-4 implementation

### Test Depth
- AC1: td:2 (already annotated, correct — ~390 failures across multiple patterns)
- Test-writer: SKIP (pass-through via `test` tag)

### Verdict: APPROVE → todo
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged `test`) — no tests applicable.
- Pipeline Note confirms: "Tests already exist and fail (RED). Builder updates test expectations to match the new API contract (GREEN). No separate test-writer step needed."
- Passing through to builder.