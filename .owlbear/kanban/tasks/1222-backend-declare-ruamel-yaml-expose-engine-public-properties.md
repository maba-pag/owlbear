---
id: 1222
title: Backend — declare ruamel.yaml + expose engine public properties
status: backlog
priority: needed
created: 2026-04-30 16:31:18.578610+00:00
updated: 2026-04-30T22:42:30.785601+00:00
tags:
- cockpit
- kanban-engine
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
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

[[2026-04-30]]
## Review Evidence
### Test Results
- quality-runner scoped gate: 9 passed, 0 failed, 0 skipped (`tests/test_engine_cockpit_deps_1222.py`)
- quality-runner adjacent regression cluster: 82 passed, 0 failed, 0 skipped (`tests/test_cockpit_read_api_1145.py`, `tests/test_cockpit_routes_1144.py`, `tests/test_cockpit_read_api_930.py`, `tests/test_cockpit_decisions_api_1190.py`, `tests/test_decisions_1218.py`)
- quality-runner full regression context: 3340 passed, 129 failed, 4 skipped; repo remains globally red outside this task

### Lint
- scoped gate: clean
- full regression context shows unrelated lint debt outside changed files:
  - `serve/knowledge/src/owlbear_knowledge/copilot_auth.py:106` (`T201`)
  - `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:274` (`PLC0415`)
  - `serve/mcp-memory/src/owlbear_mcp_memory/approve.py:136` (`ASYNC250`)
  - `serve/orchestrator/examples/hello_world.py:32` (`ANN401`)

### Coverage
- task-owned scoped run reported `overall_pct: 15` and explicitly noted that `owlbear_kanban.engine` / `owlbear_cockpit.deps` were not collected in that run; non-fatal warning: corrupted `.coverage` database from prior runs
- adjacent regression cluster reported module-wide `owlbear_kanban.engine: 27%`; treated as informational only because the review gate is diff-scoped, not module-wide
- reviewer assessment: no significant diff-scoped coverage gap. AC2 property bodies are executed directly by the task-owned suite; AC3 is proven by direct source assertion plus file inspection of the changed call sites

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `serve/cockpit/pyproject.toml` lists `ruamel.yaml` | `test_ruamel_yaml_in_cockpit_pyproject` | Yes — removing the dependency string fails the assertion | COVERED |
| `KanbanEngine` exposes read-only `tasks_dir` | `test_tasks_dir_property_accessible`, `test_tasks_dir_returns_expected_path`, `test_tasks_dir_is_read_only` | Yes — missing property, wrong path, or writable property all fail | COVERED |
| `KanbanEngine` exposes read-only `kanban_dir` | `test_kanban_dir_property_accessible`, `test_kanban_dir_returns_expected_path`, `test_kanban_dir_is_read_only` | Yes — missing property, wrong path, or writable property all fail | COVERED |
| `deps.py` uses public properties instead of private attrs | `test_deps_does_not_access_private_tasks_dir`, `test_deps_does_not_access_private_kanban_dir` | Yes — reintroducing `_tasks_dir` / `_kanban_dir` fails the negative source assertions | COVERED |
| No regressions introduced | td:0 by architect | td:0 | SKIPPED |

#### Security Review
- No issues found.
- Dependency addition is necessary, not speculative: `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:12-13` directly imports `ruamel.yaml` and `ruamel.yaml.error.YAMLError`.
- No new injection, path traversal, secret exposure, or unsafe deserialization paths were introduced by these changes.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `tests/test_engine_cockpit_deps_1222.py::TestFromAC_*` | No evidence of builder modification. Builder's recorded file list contains only `serve/cockpit/pyproject.toml`, `serve/kanban/src/owlbear_kanban/engine.py`, and `serve/cockpit/src/owlbear_cockpit/deps.py`; current test file still matches the test-writer's declared 9-test AC matrix. | PRESERVED |

#### Test Quality
- Assertion specificity: STRONG
- Negative/error-path coverage: ADEQUATE for td:1 smoke scope; read-only checks assert `AttributeError`, and AC3 uses negative source assertions
- Manual mutation reasoning: STRONG — removing the dependency, returning the wrong path, making the properties writable, or reintroducing private attr names would all fail
- Test independence: STRONG
- Descriptive naming: STRONG

#### Data Safety
- No issues found. The implementation adds read-only path accessors and replaces private path reads with public equivalents.

#### Implementation-Aware Test Gap Analysis
- No significant untested path found in the changed logic.
- `serve/kanban/src/owlbear_kanban/engine.py:525-531` and `:530-532` expose trivial property bodies exercised by the task-owned suite.
- `serve/cockpit/src/owlbear_cockpit/deps.py:44` and `:55` are trivial call-site substitutions from private attrs to public properties; the task-owned suite proves the contract textually, and the adjacent regression cluster stayed green.

#### Necessity Check
- PASS. `serve/cockpit/pyproject.toml:6` now declares `ruamel.yaml`, which is directly imported by cockpit code at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:12-13`.

#### Builder Process Quality
- CLEAN. Two `## Builder Notes` sections exist, but they reflect one implementation pass and one post-refinement verification pass, not repeated failed implementation loops.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `serve/cockpit/pyproject.toml` lists `ruamel.yaml` | `serve/cockpit/pyproject.toml:6`; direct cockpit import at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:12-13` | `test_ruamel_yaml_in_cockpit_pyproject` | PASS |
| `KanbanEngine` exposes `tasks_dir` and `kanban_dir` as public read-only properties | `serve/kanban/src/owlbear_kanban/engine.py:525-531` and `:530-532` | `test_tasks_dir_property_accessible`, `test_tasks_dir_returns_expected_path`, `test_tasks_dir_is_read_only`, `test_kanban_dir_property_accessible`, `test_kanban_dir_returns_expected_path`, `test_kanban_dir_is_read_only` | PASS |
| `serve/cockpit/src/owlbear_cockpit/deps.py` uses public properties instead of `engine._tasks_dir` / `engine._kanban_dir` | `serve/cockpit/src/owlbear_cockpit/deps.py:44` uses `engine.tasks_dir`; `serve/cockpit/src/owlbear_cockpit/deps.py:55` uses `engine.kanban_dir`; no private-attr matches remain in that file | `test_deps_does_not_access_private_tasks_dir`, `test_deps_does_not_access_private_kanban_dir` | PASS |
| No regressions introduced — task-owned suite passes green; any full-suite failures are demonstrably pre-existing and unrelated to changed files | Scoped gate 9/0 green; adjacent cockpit/decision regression cluster 82/0 green; full regression context remains red with unrelated lint violations in `serve/knowledge`, `serve/mcp-knowledge`, `serve/mcp-memory`, and `serve/orchestrator/examples` | td:0 | PASS |

### Deductions
- `-0.03` builder commit hash was not recorded in the task body, so changed-file scope was reconstructed from builder notes plus direct file inspection
- `-0.03` the full regression-context report returned counts but not a complete per-failure list; unrelatedness was established by changed-file isolation, green task-owned results, green adjacent regression results, and unrelated lint paths rather than exhaustive failure-by-failure mapping

### Verdict
- PASS -> docs | confidence 0.94

### Action
- Advanced to `docs`.
[[2026-04-30]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/cockpit/README.md` Dependencies table was missing `ruamel.yaml` — added row. `serve/kanban/README.md` KanbanEngine methods table lists methods only; new properties follow same pattern as existing `agent_name`/`revision` (not listed) — no change needed. |
| 2 | Module docstrings | Yes | N/A | `engine.py` new properties have adequate docstrings (`tasks_dir`: "Configured tasks directory for the active board." / `kanban_dir`: "Root kanban directory for the active board."). `deps.py` module docstring and all public function docstrings accurate and up to date. No changes needed. |
| 3 | External attribution | No | N/A | No external patterns or references used. |
| 4 | Research doc | No | N/A | No research doc produced. |
| 5 | Diagram maintenance | Yes | Updated | Four describes-matches: `cockpit.excalidraw` (serve/cockpit/src/**), `kanban.excalidraw` (serve/kanban/src/**), `mcp-topology.excalidraw` (serve/kanban/src/**), `project-overview.excalidraw` (serve/*/pyproject.toml). All footers updated to `Last verified: 2026-05-01 (f584b298)`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No deleted files. No orphaned IN-scope docs. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/pyproject.toml` | OUT (config) | N/A — prose doc updated instead |
| `serve/kanban/src/owlbear_kanban/engine.py` | IN (py docstrings) | Verified — docstrings adequate, no edit needed |
| `serve/cockpit/src/owlbear_cockpit/deps.py` | IN (py docstrings) | Verified — docstrings accurate, no edit needed |

### Files Updated
- `serve/cockpit/README.md` — added `ruamel.yaml` to Dependencies table
- `share/diagrams/cockpit.excalidraw` — footer updated
- `share/diagrams/kanban.excalidraw` — footer updated
- `share/diagrams/mcp-topology.excalidraw` — footer updated
- `share/diagrams/project-overview.excalidraw` — footer updated

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1222-* scratch files found)
[[2026-04-30]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| `serve/cockpit/pyproject.toml` lists `ruamel.yaml` | File line 6 confirmed by grep; committed in `927cce5a` (non-conformant message, no task attribution) | PASS |
| `KanbanEngine` exposes `tasks_dir` and `kanban_dir` as public read-only properties | `engine.py:525-532` confirmed by grep + file read; `@property` decorators present; committed in `151ab35d` (task 1221 builder scope) | PASS |
| `deps.py` uses public properties instead of private attrs | `deps.py:44,55` use `engine.tasks_dir` / `engine.kanban_dir` confirmed by grep; NO `_tasks_dir`/`_kanban_dir` present | PASS (uncommitted) |
| No regressions introduced | td:0 by architect; full suite 3340 passed / 129 failed / 4 skipped matches reviewer baseline exactly; all failures in `mcp-kanban` suites, none in changed files | PASS |

### Commit Integrity — FAIL
- `deps.py`: `git status --short` shows ` M` (modified in working tree, not staged, not committed). Source deliverable is UNCOMMITTED.
- `pyproject.toml`: committed in `927cce5a` with non-conformant message "Refactor code structure for improved readability and maintainability" — no task ID, no agent attribution; format violation.
- `engine.py` properties: committed in task 1221 builder scope (`151ab35d`), not in any 1222-attributed commit; attribution bleed.
- Task-1222 builder commit: ABSENT from git history for changed source files.

### Test Results
- task-owned scoped gate: 9 passed, 0 failed (confirmed by reviewer; matches `b9d6ecac` test-writer commit which is properly tagged)
- full suite (scratch log `q1222-output.log`): 3340 passed, 129 failed, 4 skipped — identical to reviewer baseline; all failures in `serve/mcp-kanban/tests/` and related MCP adapter suites, none in `serve/cockpit/` or `serve/kanban/`
- lint (task scope): clean; 4 pre-existing violations in unrelated packages (`serve/knowledge`, `serve/mcp-knowledge`, `serve/mcp-memory`, `serve/orchestrator`)

### Architect Quality: 4/5
AC1-AC3 specific and verifiable. AC4 required mid-cycle refinement from infeasible "all existing tests pass" to verifiable regression gate — one pass of architect re-work needed, correctly resolved.

### Deduction Breakdown
| Criterion | Deduction | Reason |
|-----------|-----------|--------|
| `deps.py` uncommitted source deliverable | -0.05 | Working-tree-only; unprotected; not in any git commit |
| `pyproject.toml` non-conformant commit | -0.02 | No task ID, no agent attribution in commit message `927cce5a` |
| `engine.py` committed under wrong task scope | -0.02 | Properties landed in `151ab35d` (#1221 builder), attribution bleed |

### Confidence: 0.91
### Action: reject to backlog

Builder must: (1) commit `deps.py` with a conformant message `fix: use public engine properties in cockpit deps (#1222, builder)`; (2) note the `pyproject.toml` and `engine.py` attribution gap in the builder notes for traceability. Implementation is correct — this is commit hygiene only.