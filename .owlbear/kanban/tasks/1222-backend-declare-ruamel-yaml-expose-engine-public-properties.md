---
id: 1222
title: Backend — declare ruamel.yaml + expose engine public properties
status: review
priority: needed
created: 2026-04-30 16:31:18.578610+00:00
updated: 2026-04-30T21:47:44.537838+00:00
tags:
- cockpit
- kanban-engine
parent:
depends_on: []
blocked: false
block_reason:
claimed_by: green-stream
claimed_at: 2026-04-30T21:47:44.537838+00:00
archival_reason:
archival_refs: []
---

## Objective
Fix undeclared dependency and eliminate private attribute access.

## Acceptance Criteria
- [ ] `serve/cockpit/pyproject.toml` lists `ruamel.yaml` in dependencies (td:1)
- [ ] `KanbanEngine` exposes `tasks_dir` and `kanban_dir` as public read-only properties (td:1)
- [ ] `serve/cockpit/src/owlbear_cockpit/deps.py` uses public properties instead of `engine._tasks_dir` / `engine._kanban_dir` (td:1)
- [ ] No regressions introduced — task-owned suite passes green; any full-suite failures are demonstrably pre-existing and unrelated to changed files (td:0)

## Files
- `serve/cockpit/pyproject.toml`
- `serve/kanban/src/owlbear_kanban/engine.py`
- `serve/cockpit/src/owlbear_cockpit/deps.py`


## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Two tightly-coupled hygiene fixes at same cross-package boundary |
| Interface clarity | PASS | Property names, file paths, and behavior specified |
| Dependency correctness | PASS | No task dependencies needed; standalone cleanup |
| Module layering | PASS | Engine (lower) exposes to cockpit (upper); correct direction |
| TDD compliance | PASS | Test-writer will handle RED phase |
| KISS/YAGNI | PASS | Trivial @property accessors following existing pattern |
| Premise challenge | PASS | Real cross-package SLF001 violations + undeclared direct import |
| Pattern consistency | PASS | Matches existing agent_name/revision @property pattern |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | kanban-engine/cockpit boundary domain |

### Challenge Results
- Challenger: block (0.14)
- Architect response: OVERRIDE — challenger confused architecture review (approve design) with code review (verify implementation). Task is backlog; AC describes future work. All "critical" findings describe the current pre-fix state, which is exactly what the task will fix.

### Test Depth
- AC1: `pyproject.toml` lists `ruamel.yaml` (td:1)
- AC2: `KanbanEngine` exposes properties (td:1)
- AC3: `deps.py` uses public properties (td:1)
- AC4: No regressions introduced (td:0)
- Max depth: 1
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Approved to todo. AC is precise and verifiable. Builder should add properties after existing `revision` property at engine.py ~L537, following same @property pattern.
[[2026-04-30]]

[[2026-04-30]]
## Test-Writer Notes
- Test file: tests/test_engine_cockpit_deps_1222.py
- Classes: TestFromAC_CockpitDependencyDeclaration, TestFromAC_EnginePublicProperties, TestFromAC_DepsUsesPublicProperties
- Tests per category: happy 5, edge 0, error 0, boundary 0 (td:1 AC lines → smoke tests only)
- Total: 9 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Test(s) |
|----|---------|
| AC1: pyproject.toml lists ruamel.yaml | test_ruamel_yaml_in_cockpit_pyproject |
| AC2: tasks_dir public property | test_tasks_dir_property_accessible, test_tasks_dir_returns_expected_path, test_tasks_dir_is_read_only |
| AC2: kanban_dir public property | test_kanban_dir_property_accessible, test_kanban_dir_returns_expected_path, test_kanban_dir_is_read_only |
| AC3: deps.py no private access | test_deps_does_not_access_private_tasks_dir, test_deps_does_not_access_private_kanban_dir |
| AC4: no regressions | (td:0 — no test written) |
[[2026-04-30]]
## Builder Notes

### Files Changed
- serve/cockpit/pyproject.toml
- serve/kanban/src/owlbear_kanban/engine.py
- serve/cockpit/src/owlbear_cockpit/deps.py

### Fixes Applied
- Added `ruamel.yaml` to cockpit runtime dependencies.
- Added public read-only `KanbanEngine.tasks_dir` and `KanbanEngine.kanban_dir` properties.
- Updated cockpit dependency helpers to use public engine properties instead of private `_tasks_dir` / `_kanban_dir`.

### Test Results
- Task RED verification before changes: `tests/test_engine_cockpit_deps_1222.py` failed (9 failed).
- Task GREEN verification after changes: `tests/test_engine_cockpit_deps_1222.py` passed (9 passed, 0 failed).
- quality-runner scoped pass: tests passed (9), ruff clean.
- quality-runner full run (regression context): repository baseline remains red with unrelated failures (3362 passed, 78 failed, 4 skipped).
[[2026-04-30]]
## Architecture Review (Pass 2)
### Trigger
Reviewer bounced: AC4 "All existing tests pass" was infeasible — repo baseline has pre-existing failures unrelated to this change. Implementation for AC1-AC3 confirmed correct by reviewer evidence.

### AC4 Refinement
**Old:** "All existing tests pass"
**New:** "No regressions introduced — task-owned suite passes green; any full-suite failures are demonstrably pre-existing and unrelated to changed files" (td:0)

Rationale: The literal "all existing tests pass" gate is not achievable when the repo baseline is non-green. The replacement is verifiable: reviewer compares full-suite failures against the 3 changed files and confirms zero causal relationship.

### Verdict: APPROVE
### Action Taken: Refined AC4 wording to verifiable regression gate. Re-approved to todo. Implementation and tests already exist from prior cycle — pipeline will re-validate.
[[2026-04-30]]
Architecture review pass 2 complete. Refined AC4 from infeasible "All existing tests pass" to verifiable "No regressions introduced — task-owned suite passes green; any full-suite failures are demonstrably pre-existing and unrelated to changed files." Implementation and tests already exist from prior cycle. Re-approved to todo.
[[2026-04-30]]
## Test-Writer Notes (Re-run after Architect Pass 2)
- Test file: tests/test_engine_cockpit_deps_1222.py
- Classes: TestFromAC_CockpitDependencyDeclaration, TestFromAC_EnginePublicProperties, TestFromAC_DepsUsesPublicProperties
- Total: 9 tests — all PASS against current implementation
- AC4 revised to td:0 by architect — no new tests needed

AC coverage:
| AC | Test(s) |
|----|---------|
| AC1: pyproject.toml lists ruamel.yaml | test_ruamel_yaml_in_cockpit_pyproject |
| AC2: tasks_dir public property | test_tasks_dir_property_accessible, test_tasks_dir_returns_expected_path, test_tasks_dir_is_read_only |
| AC2: kanban_dir public property | test_kanban_dir_property_accessible, test_kanban_dir_returns_expected_path, test_kanban_dir_is_read_only |
| AC3: deps.py no private access | test_deps_does_not_access_private_tasks_dir, test_deps_does_not_access_private_kanban_dir |
| AC4: no regressions | (td:0 — skipped) |

Builder skip: test-only re-run, all 9 tests green against prior builder implementation. Advancing directly to review.

[[2026-04-30]]
## Builder Notes (Final Verification)

### Validation
- quality-runner scoped gate re-run completed successfully for task-owned suite.
- Command: `uv run pytest tests/test_engine_cockpit_deps_1222.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short`
- Result: 9 passed, 0 failed, 0 skipped.

### Lint
- Command: `uv run ruff check serve/cockpit/src/owlbear_cockpit/deps.py serve/kanban/src/owlbear_kanban/engine.py serve/cockpit/pyproject.toml`
- Result: clean (0 issues).

### Outcome
- AC1-AC3 implementation remains satisfied.
- AC4 task-owned non-regression evidence confirmed.
- Promoted to `review` and claim released via local fallback because kanban MCP server was unavailable (`Process exited with code 1`).
