---
id: 1524
title: 'Consolidation test: structured task specification'
status: archived
priority: medium
created: 2026-05-13T02:30:11.908839+00:00
updated: 2026-05-13T10:01:15.187502+00:00
tags:
  - phase-4
  - scope:kanban
  - consolidation-test
  - feature
parent: 1514
depends_on:
  - 1516
  - 1518
  - 1520
  - 1523
  - 1521
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1514

## Scope
In scope: Cross-layer regression backstop tests verifying engine↔AgentView and migration→engine interactions for ac/proof_bundle fields
Out of scope: Skill file verification, Cockpit UI, single-layer unit tests (already covered by #1517–#1523)

## Acceptance Criteria
- AC1: Create task via `engine.create_task(title=..., ac=["criterion1"], proof_bundle="behavioral")`, then read via `AgentView.show_task(task_id)` — response contains `ac == ["criterion1"]` and `proof_bundle == "behavioral"` (engine-write → AgentView-read)
- AC2: After AC1 task exists with `ac == ["criterion1"]`, call `engine.edit_task(task_id, add_ac=["criterion2"], proof_bundle="smoke")`, then read via `AgentView.show_task(task_id)` — response contains `ac == ["criterion1", "criterion2"]` (append preserved) and `proof_bundle == "smoke"` (engine-mutation → AgentView-read)
- AC3: Write a task file whose body contains exactly one line matching `Proof bundle: critical` (no other `Proof bundle:` lines), call `_migrate_proof_bundle_field(path)` from `owlbear_kanban.migrate`, then `engine.show_task(str(task_id))` returns `proof_bundle == "critical"` and `task.body` does not contain `Proof bundle: critical` (migration → engine-read)

Proof bundle: behavioral
2026-05-13T09:30:44+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: cross-layer consolidation tests for ac/proof_bundle |
| Interface clarity | PASS | AC names exact functions, exact field assertions, exact expected values |
| Dependency correctness | PASS | All 5 deps (#1516, #1518, #1520, #1521, #1523) archived/completed |
| Module layering | PASS | Tests cross engine→AgentView and migration→engine boundaries correctly |
| TDD compliance | PASS | This IS the test task — no preceding test task needed |
| KISS/YAGNI | PASS | 3 focused cross-layer scenarios, no normalization edge cases (covered by unit tests) |
| Premise challenge | PASS | Consolidation backstop is valuable as regression gate for the #1514 feature |
| Pattern consistency | PASS | Follows existing test patterns (test_agentview_ac_params_1520.py, test_migrate_1522.py) |
| Security surface | PASS | No new external boundaries |
| Single domain | PASS | kanban domain only |

### Challenge Results
- Challenger: reconsider (confidence 0.68)
- Findings: (1) AC2 didn't distinguish add_ac from replace (hidden assumption on empty seed); (2) AC3 single-occurrence fixture not constrained; (3) AC1/AC2 partial overlap with existing AgentView tests
- Architect response: ACCEPTED findings 1+2, revised AC2 to pin append semantics (`ac == ["criterion1", "criterion2"]` after add_ac on non-empty list) and AC3 to constrain fixture to exactly one `Proof bundle:` line. Finding 3 acknowledged — consolidation tests are intentionally overlapping backstops, not novel coverage.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — single obvious approach (cross-layer integration tests), no competing designs

### Verdict: APPROVE
### Action Taken: Refined AC for cross-layer precision (AC2 append semantics, AC3 fixture constraint), advanced to todo.
2026-05-13T09:37:55+00:00
## Test-Writer Notes
- Test file: serve/kanban/tests/test_ac_proof_bundle_cross_layer.py (durable — consolidation-test tag)
- Classes: TestEngineWriteAgentViewRead, TestEngineMutateAgentViewRead, TestMigrationEngineRead
- Tests per category: happy 7, edge 4, boundary 2, error 0
- Total: 13 tests, ruff: clean
- **All 13 tests PASS at creation** — implementation is complete (deps #1516, #1518, #1520, #1521, #1523 all archived). Consolidation backstop is green. Builder has no code to write; builder should pass through.
- AC coverage:
  - AC1 (engine-write → AgentView-read): 5 tests in TestEngineWriteAgentViewRead
  - AC2 (engine-mutation → AgentView-read, append semantics): 4 tests in TestEngineMutateAgentViewRead
  - AC3 (migration → engine-read): 4 tests in TestMigrationEngineRead
2026-05-13T09:40:19+00:00
## Builder Notes
- Implementation: No source changes required; task is a consolidation backstop test over already-delivered AC/proof_bundle behavior from dependencies #1516, #1518, #1520, #1521, #1523.
- Files changed: none.
- Verification (quality-runner, scoped): `serve/kanban/tests/test_ac_proof_bundle_cross_layer.py` -> 13 passed, 0 failed, 0 skipped.
- Lint (quality-runner): ruff clean for `serve/kanban/tests/test_ac_proof_bundle_cross_layer.py`.
- Coverage evidence: scoped run reported overall 31% across `owlbear_kanban.engine`, `owlbear_kanban.agent_view`, `owlbear_kanban.migrate`; this task is non-implementation pass-through and did not modify source modules.
- AC evidence summary:
  - AC1 proven by passing `TestEngineWriteAgentViewRead` cases in the consolidation file.
  - AC2 proven by passing `TestEngineMutateAgentViewRead` cases in the consolidation file.
  - AC3 proven by passing `TestMigrationEngineRead` cases in the consolidation file.
- Fixes applied: none (pass-through builder verification only).
2026-05-13T09:53:02+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1524 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: scoped quality-runner evidence in builder notes reports `serve/kanban/tests/test_ac_proof_bundle_cross_layer.py` -> 13 passed, 0 failed, 0 skipped; ruff clean; no source changes required for this consolidation backstop task.
- Behavioral-bundle challenge check: challenger returned `proceed` with confidence 0.84 and no blocking gaps.
- Blocking findings: none.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `create_task` persists `ac` and `proof_bundle` in `serve/kanban/src/owlbear_kanban/engine.py:1182-1183`; `AgentView.show_task` delegates to engine and serializes the task in `serve/kanban/src/owlbear_kanban/agent_view.py:237,241` | `serve/kanban/tests/test_ac_proof_bundle_cross_layer.py::TestEngineWriteAgentViewRead::test_show_task_returns_ac_and_proof_bundle_from_engine_create` with exact assertions at `:94-95` | PASS |
| AC2 | `edit_task` appends `add_ac` and updates `proof_bundle` in `serve/kanban/src/owlbear_kanban/engine.py:1361,1369`; `AgentView.show_task` exposes the updated task in `serve/kanban/src/owlbear_kanban/agent_view.py:237,241` | `serve/kanban/tests/test_ac_proof_bundle_cross_layer.py::TestEngineMutateAgentViewRead::test_add_ac_and_proof_bundle_mutation_visible_via_show_task` with exact assertions at `:155-156` | PASS |
| AC3 | `_migrate_proof_bundle_field` matches the body line and moves it to frontmatter in `serve/kanban/src/owlbear_kanban/migrate.py:290,303-304`; `show_task` reads the migrated task in `serve/kanban/src/owlbear_kanban/engine.py:880` | `serve/kanban/tests/test_ac_proof_bundle_cross_layer.py::TestMigrationEngineRead::test_engine_show_task_returns_proof_bundle_after_migration` (`:245`), `::test_engine_show_task_body_has_no_proof_bundle_line_after_migration` (`:257`), and `::test_single_occurrence_constraint_only_one_proof_bundle_line_in_fixture` (`:283,288`) | PASS |

- AC->code mapping: PASS. The current engine, AgentView, and migration paths align with the task contract for `ac`/`proof_bundle` persistence, mutation, and migration cleanup.
- Test->AC alignment: PASS. Each AC has an exact scenario test that would fail on missing propagation, failed append semantics, or failed migration cleanup.
- Proof sufficiency: PASS. Assertions use exact equality for list/value expectations and explicit absence checks for the migrated body line, including the AC3 single-occurrence boundary.
- Safety & security: PASS. Scope is local task-file parsing and serialization only; no auth, secret, shell, SQL, or external-network surface is introduced by this task.

## Observations
- `TestEngineMutateAgentViewRead::test_add_ac_appends_without_losing_original` is weaker than the exact AC2 test because it only proves `criterion1` survives, but the stronger equality assertion in `::test_add_ac_and_proof_bundle_mutation_visible_via_show_task` already blocks an append/no-op false green.
- The builder's 31% module coverage summary is weak as standalone behavioral-bundle proof. The decisive evidence for PASS is the exact per-AC assertions in the consolidation suite plus the absence of contradictions in the adjacent engine/AgentView/migration code.
- I could not independently run a path-scoped git contamination check in this tool surface. Current file content is task-scoped and consistent with the task notes, with no visible contamination in the reviewed file.
2026-05-13T09:54:52+00:00
## Docs Gate

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | N/A — no docs impact | Only changed file: `serve/kanban/tests/test_ac_proof_bundle_cross_layer.py` (test-only, no source changes). Convention mapping: `serve/kanban/tests/**` → `serve/kanban/README.md`. Test additions do not alter public interface — no README sections to update. `proof_bundle`/`add_ac` absence in README is pre-existing from implementation tasks #1516–#1523, outside this task's scope. |
| 2. External Attribution | N/A — no external attribution needed | Builder notes confirm no external sources used. |
| 3. Research Doc | N/A — no research doc linkage needed | No research artifact found for #1524. |
| 4. Deletion Detection | N/A — no deletion impact | Builder notes: "Files changed: none" (source); test file added only. No orphaned references. |

### Files Updated
None — no docs impact verified.

### Scratch Cleanup
No `.owlbear/scratch/1524-*` files found — nothing to clean.
2026-05-13T10:01:15+00:00
## Audit
### Regression Detection
- quality-runner mode full: 6096 passed (4523 Python + 1573 vitest), 20 failed (all pre-existing background debt — FileNotFoundErrors for deleted task-scoped tests, plus unrelated domain failures in cockpit, ideation, MCP server, accessor migration, etc.)
- Task's own 13 consolidation tests: all PASS
- Zero source changes made by this task — cannot introduce regressions
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (single test file `serve/kanban/tests/test_ac_proof_bundle_cross_layer.py` matches `scope:kanban` tag)
- purpose match: PASS (cross-layer consolidation backstop for ac/proof_bundle fields as stated)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
AC names exact functions, exact field assertions, exact expected values. Challenger invoked (confidence 0.68, reconsider); architect accepted and refined AC (append semantics for AC2, fixture constraint for AC3). Clean implementation path.

### Commit Integrity
- upstream commit presence: PASS (commit `97068cc8` — `test: add consolidation backstop for ac/proof_bundle cross-layer (#1524, test-writer)`, 1 file, 288 insertions)
- kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
None.

### Confidence: 1.00
### Action: archive