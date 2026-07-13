---
id: 1297
title: 'P1-01: Core removal — delete orchestrator package and owlbear-project.json
  infrastructure'
status: archived
priority: medium
created: 2026-05-02T19:40:07.773168+00:00
updated: 2026-05-02T23:32:51.248858+00:00
tags:
- cleanup
parent: 1296
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Delete the dead `serve/orchestrator/` package, its test infrastructure, and `owlbear-project.json` generation code. All changes must land in a single atomic commit because `test_package_boundary.py` validates bidirectionally (fails on stale ALLOWED_IMPORTS entries AND on missing entries).

Brief: see parent #1296 and `.owlbear/briefs/draft-dead-code-sweep/brief.md`

## Scope

### Delete
- `serve/orchestrator/` (entire directory)
- `tests/fixtures/mock_acp_agent.py`
- `.owlbear/scripts/e2e_smoke.py`
- `owlbear-project.json` (root)
- `seed/owlbear-project.json`

### Edit
- `pyproject.toml` — remove `"serve/orchestrator/src"` from ruff `src` list; remove `"owlbear_orchestrator"` from coverage `source_pkgs`
- `tests/test_package_boundary.py` — remove `"owlbear"` and `"owlbear_orchestrator"` from `ALLOWED_IMPORTS`; update docstring
- `setup/init.py` — remove `_write_project_json()` function, dispatch block, and frozenset entry
- `serve/knowledge/src/owlbear_knowledge/scope_transfer.py` — gut `resolve_global_db_path()` body, replace with `raise NotImplementedError("global DB path resolution removed — see #1296")`

### Regenerate
- Run `uv lock` to sync lockfile

### Out of scope
- Doc/skill edits (task #1298)
- Diagram edits (task #1299)
- Any reference to the live VS Code `orchestrator.agent.md` — that stays

## AC

1. `serve/orchestrator/` directory does not exist
2. `tests/fixtures/mock_acp_agent.py` does not exist
3. `.owlbear/scripts/e2e_smoke.py` does not exist
4. `owlbear-project.json` (root) does not exist
5. `seed/owlbear-project.json` does not exist
6. `grep -r "serve/orchestrator" pyproject.toml tests/ setup/ serve/knowledge/` returns zero hits
7. `uv sync` succeeds
8. `uv run pytest tests/test_package_boundary.py` passes
9. `uv run ruff check pyproject.toml tests/test_package_boundary.py setup/init.py serve/knowledge/src/owlbear_knowledge/scope_transfer.py` passes
10. All changes in a single commit (atomic — no intermediate broken state)
[[2026-05-02]]
## Test-Writer Notes
- Test file: tests/test_core_removal_1297.py
- Classes: TestFromAC_CoreRemoval
- Tests per category: happy 0, edge 2 (env-var path, resolve with empty dir), error 0, boundary 0; structural 12
- Total: 14 tests, all FAIL
- ruff: clean

### AC Coverage

| AC | Test(s) |
|----|---------|
| AC1 — serve/orchestrator/ absent | test_orchestrator_dir_absent |
| AC2 — mock_acp_agent.py absent | test_mock_acp_agent_absent |
| AC3 — e2e_smoke.py absent | test_e2e_smoke_absent |
| AC4 — root owlbear-project.json absent | test_root_project_json_absent |
| AC5 — seed/owlbear-project.json absent | test_seed_project_json_absent |
| AC6 — no serve/orchestrator refs in pyproject.toml | test_no_serve_orchestrator_in_pyproject |
| AC6 — no serve/orchestrator refs in tests/ | test_no_serve_orchestrator_in_tests_dir |
| AC8 — ALLOWED_IMPORTS no 'owlbear' key | test_allowed_imports_no_owlbear_namespace |
| AC8 — ALLOWED_IMPORTS no 'owlbear_orchestrator' key | test_allowed_imports_no_owlbear_orchestrator |
| scope edit — _write_project_json removed from init.py | test_write_project_json_not_in_init |
| scope edit — owlbear-project.json not in _SKIP_IF_EXISTS_REL | test_project_json_not_in_skip_if_exists_rel |
| scope edit — dispatch block removed from init.py | test_project_json_dispatch_removed_from_init |
| scope edit — resolve_global_db_path raises NotImplementedError | test_resolve_global_db_path_raises |
| scope edit — raises even with OWLBEAR_GLOBAL_KB_PATH set | test_resolve_global_db_path_raises_with_env_var |

### Notes for builder
- test_no_serve_orchestrator_in_tests_dir also catches tests/test_deny_non_doc_writes.py line 145 (uses serve/orchestrator as test-input data — needs updating to a different Python path)
- AC7 (uv sync) and AC9 (ruff check) are CI/subprocess concerns not covered by unit tests
- AC10 (atomic commit) is procedural, not testable
[[2026-05-02]]
## Builder Notes
- Implementation completed for requested scope edits and deletions:
  - Deleted: serve/orchestrator/ (entire package), tests/fixtures/mock_acp_agent.py, .owlbear/scripts/e2e_smoke.py, owlbear-project.json, seed/owlbear-project.json
  - Updated: pyproject.toml, tests/test_package_boundary.py, setup/init.py, serve/knowledge/src/owlbear_knowledge/scope_transfer.py, tests/test_deny_non_doc_writes.py
  - Regenerated lockfile: uv.lock via `uv lock`
- RED verification (quality-runner): 14/14 TestFromAC tests failed before implementation.
- GREEN verification (quality-runner): 13 passed, 1 failed.
- Remaining failure:
  - tests/test_core_removal_1297.py::TestFromAC_CoreRemoval::test_no_serve_orchestrator_in_tests_dir
  - Evidence: it scans all tests/*.py except itself and still finds `serve/orchestrator` in tests/test_dead_code_sweep_1296.py
- Lint status (quality-runner scoped): clean for setup/init.py, serve/knowledge/src/owlbear_knowledge/scope_transfer.py, tests/test_package_boundary.py, tests/test_deny_non_doc_writes.py.

Test-writer: please update the AC6 tests-dir scan expectation to account for existing parent-task TestFromAC file tests/test_dead_code_sweep_1296.py (or update that file in your cycle so it no longer contains the literal). Current builder implementation is blocked by cross-test-string mismatch, not source behavior.
[[2026-05-02]]
## Test-Writer Notes
- Retry: fixed `test_no_serve_orchestrator_in_tests_dir` exclusion list.
- Root cause: test excluded only itself but not `tests/test_dead_code_sweep_1296.py`, which legitimately contains `"serve/orchestrator"` as string literals in its own assertions (it tests that *other* locations don't reference the path).
- Fix: added `test_dead_code_sweep_1296.py` to the `excluded` set alongside the self-exclusion.
- Verification: 14/14 tests pass. All existing tests preserved, no new tests added.
- Builder skip: test-only retry, all tests green.
[[2026-05-02]]
DONE #1297 -> review | 45 passed, ruff clean

## Builder Notes
- Implemented scope-complete core removal and cleanup for #1297.
- Effective code-change commit: 0e9a5aef (`fix: remove dead orchestrator package and project-json infra (#1297, builder)`).
- Files removed in commit:
  - serve/orchestrator/ (entire package)
  - tests/fixtures/mock_acp_agent.py
  - .owlbear/scripts/e2e_smoke.py
  - owlbear-project.json
  - seed/owlbear-project.json
- Files updated in commit:
  - pyproject.toml
  - tests/test_package_boundary.py
  - setup/init.py
  - serve/knowledge/src/owlbear_knowledge/scope_transfer.py
  - tests/test_deny_non_doc_writes.py
  - uv.lock
- AC evidence:
  - `uv sync` succeeded.
  - `uv run pytest tests/test_core_removal_1297.py -q --tb=short` -> 14 passed.
  - `uv run pytest tests/test_package_boundary.py -q --tb=short` -> 31 passed.
  - `uv run ruff check pyproject.toml tests/test_package_boundary.py setup/init.py serve/knowledge/src/owlbear_knowledge/scope_transfer.py tests/test_deny_non_doc_writes.py` -> clean.
  - Files/directories required by AC are absent.
- Quality-runner GREEN verification:
  - Total tests passed: 45 (combined run).
  - Lint: clean.
  - Coverage report generated for scoped run; observed low aggregate due deletion-focused test scope and non-exercised modules.
- Additional note:
  - An empty follow-up commit exists (`a61c85dc`) with no file changes; all functional/content changes for #1297 are in 0e9a5aef.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped: 65 passed, 0 failed, 0 skipped
- Executed: `tests/test_core_removal_1297.py`, `tests/test_package_boundary.py`, `tests/test_deny_non_doc_writes.py`

### Lint
- `ruff check` clean on `pyproject.toml`, `tests/test_core_removal_1297.py`, `tests/test_package_boundary.py`, `tests/test_deny_non_doc_writes.py`, `setup/init.py`, and `serve/knowledge/src/owlbear_knowledge/scope_transfer.py`

### Coverage
- `owlbear_knowledge`: 21% overall. Informational only for this deletion-focused review; not a gate by itself.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1–AC5 removal checks | `test_orchestrator_dir_absent`, `test_mock_acp_agent_absent`, `test_e2e_smoke_absent`, `test_root_project_json_absent`, `test_seed_project_json_absent` | Yes | COVERED |
| AC6: `grep -r "serve/orchestrator" pyproject.toml tests/ setup/ serve/knowledge/` returns zero hits | `test_no_serve_orchestrator_in_pyproject`, `test_no_serve_orchestrator_in_tests_dir` | No. The task AC explicitly requires zero hits across all four targets at [.owlbear/kanban/tasks/1297-p1-01-core-removal-delete-orchestrator-package-and-owlbear-project-json-infrastr.md](.owlbear/kanban/tasks/1297-p1-01-core-removal-delete-orchestrator-package-and-owlbear-project-json-infrastr.md#L56), but the current test only checks `pyproject.toml` plus `tests/` and explicitly excludes its own file and the parent test file at [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L120) and [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L135). Live grep evidence still finds `serve/orchestrator` under [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L120) and [tests/test_dead_code_sweep_1296.py](tests/test_dead_code_sweep_1296.py#L63). The setup/serve-knowledge portions of AC6 are also unmapped in the task-local TestFromAC file. | LAX / FAIL |
| AC7, AC9, AC10 | review-only command / procedural ACs | Reviewed separately below | N/A |

#### Security Review
- No OWASP-style issues found in the reviewed diff surface.

#### Test Integrity
- No builder-authored `TestFromAC_*` weakening is evidenced in the task body. The current AC6 problem is a test-writer narrowing issue, not builder tampering. Confidence here is slightly reduced because git diff access was unavailable.

#### Test Quality
- WEAK: AC6 proof is narrowed by exclusions and omits the `setup/` and `serve/knowledge/` portions of the literal AC. The suite stays green while the live workspace still violates the AC.

#### Data Safety
- No data-safety issues found in the reviewed files.

#### Implementation-Aware Test Gap Analysis
- FAIL: [serve/knowledge/src/owlbear_knowledge/scope_transfer.py](serve/knowledge/src/owlbear_knowledge/scope_transfer.py#L30) now unconditionally raises `NotImplementedError` at [serve/knowledge/src/owlbear_knowledge/scope_transfer.py](serve/knowledge/src/owlbear_knowledge/scope_transfer.py#L37), but live MCP tools [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L631) and [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L667) still call it directly at [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L639) and [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L677) with no handling. `grep_search` found no tests mentioning `sync_from_global` or `sync_to_global` under `tests/**`, so this active regression path is untested.

#### Necessity Check
- Skipped: removal task, no new dependency or integration surface.

#### Builder Process Quality
- CLEAN: one implementation pass, one test-writer retry, no loop behavior.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 1. `serve/orchestrator/` directory does not exist | `file_search("serve/orchestrator/**")` returned no files | `test_orchestrator_dir_absent` | PASS |
| 2. `tests/fixtures/mock_acp_agent.py` absent | `file_search("tests/fixtures/mock_acp_agent.py")` returned no files | `test_mock_acp_agent_absent` | PASS |
| 3. `.owlbear/scripts/e2e_smoke.py` absent | `file_search(".owlbear/scripts/e2e_smoke.py")` returned no files | `test_e2e_smoke_absent` | PASS |
| 4. `owlbear-project.json` absent | `file_search("owlbear-project.json")` returned no files | `test_root_project_json_absent` | PASS |
| 5. `seed/owlbear-project.json` absent | `file_search("seed/owlbear-project.json")` returned no files | `test_seed_project_json_absent` | PASS |
| 6. zero `serve/orchestrator` hits in `pyproject.toml tests/ setup/ serve/knowledge/` | AC text at [.owlbear/kanban/tasks/1297-p1-01-core-removal-delete-orchestrator-package-and-owlbear-project-json-infrastr.md](.owlbear/kanban/tasks/1297-p1-01-core-removal-delete-orchestrator-package-and-owlbear-project-json-infrastr.md#L56); live grep over `tests/**` still hits [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L120) and [tests/test_dead_code_sweep_1296.py](tests/test_dead_code_sweep_1296.py#L63) | `test_no_serve_orchestrator_in_pyproject`, `test_no_serve_orchestrator_in_tests_dir` | FAIL |
| 7. `uv sync` succeeds | Builder reports success, but this review surface had no terminal path to independently rerun `uv sync` | none | UNVERIFIED |
| 8. `uv run pytest tests/test_package_boundary.py` passes | quality-runner scoped run: 65 passed, 0 failed including `tests/test_package_boundary.py` | `tests/test_package_boundary.py` | PASS |
| 9. `uv run ruff check pyproject.toml tests/test_package_boundary.py setup/init.py serve/knowledge/src/owlbear_knowledge/scope_transfer.py` passes | quality-runner scoped lint: clean | review lint run | PASS |
| 10. all changes in a single commit | Task requires single atomic commit at [.owlbear/kanban/tasks/1297-p1-01-core-removal-delete-orchestrator-package-and-owlbear-project-json-infrastr.md](.owlbear/kanban/tasks/1297-p1-01-core-removal-delete-orchestrator-package-and-owlbear-project-json-infrastr.md#L60). Reflog evidence confirms builder commits `0e9a5aef` then `a61c85dc`, and the task body says the second commit is empty at [.owlbear/kanban/tasks/1297-p1-01-core-removal-delete-orchestrator-package-and-owlbear-project-json-infrastr.md](.owlbear/kanban/tasks/1297-p1-01-core-removal-delete-orchestrator-package-and-owlbear-project-json-infrastr.md#L143), but git diff access was unavailable to prove emptiness independently. | none | PARTIAL |

### Deductions
- `-0.18` AC6 is still violated in the live workspace and the current TestFromAC assertion passes anyway.
- `-0.10` `resolve_global_db_path()` now hard-fails active `mcp-knowledge` sync tools without caller updates.
- `-0.05` No test coverage found for `sync_from_global` / `sync_to_global`.
- `-0.03` Atomicity only partially verified because git diff access was unavailable.

### Verdict
- FAIL -> in-progress
- Confidence: 0.64

### Required Follow-up
1. Restore the AC6 contract instead of excluding known test files. Either rewrite the tests so the repo genuinely has zero `serve/orchestrator` hits in the scoped paths, or explicitly narrow the task AC through architecture if that broader grep contract is no longer intended.
2. Update [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L631) and [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L667) to handle the removed global path resolution coherently, then add tests covering the live sync-tool behavior.
3. Re-run scoped review evidence after the source fix and AC6-proof fix.
[[2026-05-02]]
REJECT #1297 -> backlog | AC6 grep contract is infeasible with immutable TestFromAC literals under tests/

## Builder Notes
- Files changed:
  - serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
- Commit:
  - 18044901 `fix: guard global sync path resolution removal (#1297, builder)`
- Fixes applied:
  - Added `NotImplementedError` handling in `sync_from_global()` and `sync_to_global()` so removed global-path resolution now returns explicit `error:` strings instead of uncaught exceptions.
  - Fixed ruff `PLC0415` in lazy copilot-auth import path.
- Quality-runner evidence (scoped):
  - Tests: 108 passed, 0 failed
  - Test files: tests/test_core_removal_1297.py, tests/test_package_boundary.py, serve/mcp-knowledge/tests/test_server.py, serve/mcp-knowledge/tests/test_ingest_graph_tools.py
  - Ruff: clean on target files (`server.py`, `tests/test_core_removal_1297.py`, `tests/test_package_boundary.py`, `setup/init.py`, `scope_transfer.py`)
  - Coverage (informational): `owlbear_mcp_knowledge.server` 48%
- Rejection rationale:
  - AC6 requires zero literal hits for `serve/orchestrator` across `tests/`, but immutable `TestFromAC_*` files (including current task test file) intentionally contain that literal for assertions.
  - Builder mode forbids editing `TestFromAC_*` classes; therefore AC6 cannot be satisfied without AC/test-contract revision.
- AC suggestion for architect/test-writer:
  - Narrow AC6 scan scope to product/runtime paths (e.g., `pyproject.toml`, `setup/`, `serve/knowledge/`) or explicitly exclude task-scoped `TestFromAC` files from the grep contract.
[[2026-05-02]]

## Architecture Review (AC refinement)

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1–AC5 (file/dir deletions) | Verifiable, covered by existing tests | (td:0) no change |
| AC6 (grep zero hits) | **Infeasible as written.** Test assertion files (`test_core_removal_1297.py`, `test_dead_code_sweep_1296.py`) necessarily contain the literal `serve/orchestrator` in assertions that verify its absence — self-referential constraint. Product paths (`pyproject.toml`, `setup/`, `serve/knowledge/`) confirmed clean by live grep. Test coverage missing for `setup/` and `serve/knowledge/` paths. | (td:1) **REFINED — see below** |
| AC7 (uv sync) | Process check | (td:0) no change |
| AC8 (test_package_boundary passes) | Verifiable, existing tests cover | (td:0) no change |
| AC9 (ruff passes) | Process check | (td:0) no change |
| AC10 (single commit) | Core deletion landed in `0e9a5aef`. mcp-knowledge fix (`18044901`) is ancillary — not part of the boundary-test atomicity constraint. Intent satisfied. | (td:0) **CLARIFIED — see below** |

### Refined AC

**AC6 (revised):** `grep -r "serve/orchestrator" pyproject.toml setup/ serve/knowledge/` returns zero hits; no `.py` file under `tests/` — excluding `test_core_removal_1297.py` and `test_dead_code_sweep_1296.py` (structural-assertion files that contain the literal in verification assertions) — contains the string

**AC10 (clarified):** Core deletion changes (AC1–AC5, AC6 scope edits, AC8 boundary-test update) are in a single atomic commit. Ancillary defensive fixes (e.g., mcp-knowledge caller handling) may be separate commits.

### Test-Writer Instructions

- Add two assertions for AC6 coverage: `setup/` path grep and `serve/knowledge/` path grep (both currently clean, need regression tests)
- Existing `test_no_serve_orchestrator_in_tests_dir` exclusion set is correct as-is
- Test depth: 1 new AC6 test assertions, 0 for all other AC lines

### Architecture Notes

- No new modules, abstractions, or interfaces — pure deletion/cleanup
- mcp-knowledge sync tools (`sync_from_global`, `sync_to_global`) now return error strings instead of crashing — correctly defensive for removed infrastructure
- Sync tool test coverage and docstring cleanup are out of scope (sync tools had no tests before this task; doc cleanup is #1298's domain)
- Challenger confidence: 0.34. Addressed: AC6 now recorded in body before approval; AC10 clarified with commit-intent distinction; sync tool concerns scoped out.

### Verdict

APPROVE with AC6 refinement and AC10 clarification. Test-writer: add `setup/` and `serve/knowledge/` assertions for AC6 coverage (td:1), then advance.

[[2026-05-02]]
APPROVED #1297 -> todo | AC6 refined to exclude self-referential test files; AC10 clarified for ancillary commits. Test-writer: add setup/ and serve/knowledge/ grep assertions (td:1).
[[2026-05-02]]
## Test-Writer Notes
- Retry: added 2 tests for reviewer gaps. All pass against current impl.
- Builder skip: test-only retry, all tests green.

### New tests added
- `test_no_serve_orchestrator_in_setup_dir` — AC6: no `serve/orchestrator` refs in `setup/`
- `test_no_serve_orchestrator_in_knowledge_dir` — AC6: no `serve/orchestrator` refs in `serve/knowledge/` (uses `errors="ignore"` to skip binary files, mirroring `grep -r` behavior)

### Verification
- 16 tests passed, 0 failed (14 original + 2 new)
- ruff: clean

### AC Coverage

| AC | Test(s) |
|----|---------|
| AC1–AC5 (deletions) | unchanged — all pass |
| AC6: pyproject.toml | test_no_serve_orchestrator_in_pyproject |
| AC6: tests/ | test_no_serve_orchestrator_in_tests_dir |
| AC6: setup/ | **test_no_serve_orchestrator_in_setup_dir** (new) |
| AC6: serve/knowledge/ | **test_no_serve_orchestrator_in_knowledge_dir** (new) |
| AC8 | test_allowed_imports_no_owlbear_namespace, test_allowed_imports_no_owlbear_orchestrator |
| scope edits | test_write_project_json_not_in_init, test_project_json_not_in_skip_if_exists_rel, test_project_json_dispatch_removed_from_init |
| resolve_global_db_path | test_resolve_global_db_path_raises, test_resolve_global_db_path_raises_with_env_var |
[[2026-05-02]]
## Builder Notes
- Verification-only builder pass after latest test-writer retry; no additional source edits were required in this pass.
- Tests (quality-runner scoped): 110 passed, 0 failed, 0 skipped.
- Lint (ruff scoped): clean (no violations).
- Coverage (informational): `owlbear_mcp_knowledge.server` 48%.
- Evidence scope: `tests/test_core_removal_1297.py`, `tests/test_package_boundary.py`, `serve/mcp-knowledge/tests/test_server.py`, `serve/mcp-knowledge/tests/test_ingest_graph_tools.py` plus scoped lint paths.

### Post-task Reflection
- Problem faced: task history had multiple prior passes/rejections, so the key risk was advancing without fresh gate evidence.
- Workaround applied: reran a strict scoped quality-runner gate over the exact task-relevant tests and lint targets.
- Pattern discovered: AC refinement plus test-writer retry resolved prior contract mismatch; builder can safely advance with verification-only pass.
- Quality gap: coverage on `owlbear_mcp_knowledge.server` remains modest, but this was informational and not the acceptance gate for this cleanup task.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped: 110 passed, 0 failed, 0 skipped
- Executed: `tests/test_core_removal_1297.py`, `tests/test_package_boundary.py`, `serve/mcp-knowledge/tests/test_server.py`, `serve/mcp-knowledge/tests/test_ingest_graph_tools.py`
- Independent AC7 check: `uv sync` exited 0 with `All dependencies are in sync with uv.lock`

### Lint
- `ruff check` clean on `pyproject.toml`, `tests/test_core_removal_1297.py`, `tests/test_package_boundary.py`, `tests/test_deny_non_doc_writes.py`, `setup/init.py`, [serve/knowledge/src/owlbear_knowledge/scope_transfer.py](serve/knowledge/src/owlbear_knowledge/scope_transfer.py#L30), and [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L641)

### Coverage
- `owlbear_knowledge.scope_transfer`: 15%
- `owlbear_mcp_knowledge.server`: 48%
- Informational only: this is a td:1 cleanup/removal review, and the gate is the AC-mapped proof plus scoped regressions rather than module-wide coverage.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1-AC5 deletions | `test_orchestrator_dir_absent`, `test_mock_acp_agent_absent`, `test_e2e_smoke_absent`, `test_root_project_json_absent`, `test_seed_project_json_absent` | Yes. Each is a direct absence assertion at [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L83), [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L89), [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L95), [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L101), and [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L107). | COVERED |
| AC6 (revised) | `test_no_serve_orchestrator_in_pyproject`, `test_no_serve_orchestrator_in_tests_dir`, `test_no_serve_orchestrator_in_setup_dir`, `test_no_serve_orchestrator_in_knowledge_dir` | Yes. The refined contract is binding at [task 1297](.owlbear/kanban/tasks/1297-p1-01-core-removal-delete-orchestrator-package-and-owlbear-project-json-infrastr.md#L251). The tests assert empty hit sets for each scoped surface at [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L113), [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L119), [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L139), and [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L150). Fresh grep over `tests/**` found only the two architect-excluded structural assertion files at [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L120) and [tests/test_dead_code_sweep_1296.py](tests/test_dead_code_sweep_1296.py#L34). | COVERED |
| AC8 boundary contract | `test_allowed_imports_no_owlbear_namespace`, `test_allowed_imports_no_owlbear_orchestrator` | Yes. The tests inspect the live `ALLOWED_IMPORTS` map via AST at [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L162) and [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L167) against [tests/test_package_boundary.py](tests/test_package_boundary.py#L26). | COVERED |
| Scope edits in `setup/init.py` and `resolve_global_db_path()` | `test_write_project_json_not_in_init`, `test_project_json_not_in_skip_if_exists_rel`, `test_project_json_dispatch_removed_from_init`, `test_resolve_global_db_path_raises`, `test_resolve_global_db_path_raises_with_env_var` | Yes. These would fail if `_write_project_json` or the dispatch logic remained, or if [serve/knowledge/src/owlbear_knowledge/scope_transfer.py](serve/knowledge/src/owlbear_knowledge/scope_transfer.py#L30) did not unconditionally raise at [serve/knowledge/src/owlbear_knowledge/scope_transfer.py](serve/knowledge/src/owlbear_knowledge/scope_transfer.py#L37). | COVERED |
| AC7, AC9, AC10 | review-only / procedural | Verified separately below. | N/A |

#### Security Review
- No OWASP-style issues found in the reviewed surface.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions observed in the live suite. The retry was additive per [task 1297](.owlbear/kanban/tasks/1297-p1-01-core-removal-delete-orchestrator-package-and-owlbear-project-json-infrastr.md#L276).

#### Test Quality
- No WEAK dimensions found within the refined AC scope. The AC6 tests use exact path-scoped scans and exact empty-hit assertions at [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L119), [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L139), and [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L150).

#### Data Safety
- No data-safety issues found.

#### Implementation-Aware Test Gap Analysis
- No blocking regression remains in the live callers of `resolve_global_db_path()`. The active `mcp-knowledge` callers now guard the removed resolver at [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L641), [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L642), [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L643), [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L682), [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L683), and [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L684). Direct sync-tool tests were not found in `serve/mcp-knowledge/tests/**`, but the latest architecture review explicitly scoped that coverage out of #1297 at [task 1297](.owlbear/kanban/tasks/1297-p1-01-core-removal-delete-orchestrator-package-and-owlbear-project-json-infrastr.md#L265), so this is residual risk, not a gate failure.

#### Necessity Check
- Skipped: removal task, no new dependency or integration surface.

#### Builder Process Quality
- CLEAN. The task has one prior review reject, then an AC refinement at [task 1297](.owlbear/kanban/tasks/1297-p1-01-core-removal-delete-orchestrator-package-and-owlbear-project-json-infrastr.md#L251) and a test-writer retry; the latest builder note is verification-only at [task 1297](.owlbear/kanban/tasks/1297-p1-01-core-removal-delete-orchestrator-package-and-owlbear-project-json-infrastr.md#L301).

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 1. `serve/orchestrator/` directory absent | `file_search("serve/orchestrator/**")` returned no files | `test_orchestrator_dir_absent` | PASS |
| 2. `tests/fixtures/mock_acp_agent.py` absent | `file_search("tests/fixtures/mock_acp_agent.py")` returned no files | `test_mock_acp_agent_absent` | PASS |
| 3. `.owlbear/scripts/e2e_smoke.py` absent | `file_search(".owlbear/scripts/e2e_smoke.py")` returned no files | `test_e2e_smoke_absent` | PASS |
| 4. `owlbear-project.json` absent | `file_search("owlbear-project.json")` returned no files | `test_root_project_json_absent` | PASS |
| 5. `seed/owlbear-project.json` absent | `file_search("seed/owlbear-project.json")` returned no files | `test_seed_project_json_absent` | PASS |
| 6. Refined grep contract holds | Revised AC6 at [task 1297](.owlbear/kanban/tasks/1297-p1-01-core-removal-delete-orchestrator-package-and-owlbear-project-json-infrastr.md#L251); live `tests/**` grep hits are limited to the two explicit exclusions at [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L120) and [tests/test_dead_code_sweep_1296.py](tests/test_dead_code_sweep_1296.py#L34); no hits were found in `pyproject.toml`, `setup/**`, or `serve/knowledge/**`; scoped tests at [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L113), [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L119), [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L139), and [tests/test_core_removal_1297.py](tests/test_core_removal_1297.py#L150) passed. | AC6 tests above | PASS |
| 7. `uv sync` succeeds | Independent quality-runner env check: exit 0, `All dependencies are in sync with uv.lock` | none | PASS |
| 8. `uv run pytest tests/test_package_boundary.py` passes | quality-runner scoped pytest included `tests/test_package_boundary.py` in a 110-pass run | `tests/test_package_boundary.py` | PASS |
| 9. `uv run ruff check ...` passes | quality-runner scoped lint: clean on all requested files | review lint run | PASS |
| 10. Clarified atomic commit rule holds | Clarified AC10 at [task 1297](.owlbear/kanban/tasks/1297-p1-01-core-removal-delete-orchestrator-package-and-owlbear-project-json-infrastr.md#L253); independent git stats show `0e9a5aef` changed 32 files (+35/-2347), `a61c85dc` changed 0 files, and ancillary fix `18044901` changed 1 file (+10/-3). | none | PASS |

### Deductions
- `-0.04` Direct sync-tool guard coverage was not present in the current scoped test corpus, but architecture explicitly marked it out of scope for #1297 at [task 1297](.owlbear/kanban/tasks/1297-p1-01-core-removal-delete-orchestrator-package-and-owlbear-project-json-infrastr.md#L265).
- `-0.02` Test integrity confidence is slightly reduced because I did not have a full historical diff of the original RED suite; judgment is based on the live tests plus task-history evidence.

### Verdict
- PASS -> docs
- Confidence: 0.94

### Action
- Advance to docs.

### Post-task Reflection
- Problem faced: the stale original AC6 wording would have produced a false FAIL if I had not anchored to the later architecture refinement.
- Workaround applied: reran fresh scoped review evidence and a separate `uv sync` check, then independently verified commit stats for AC10.
- Pattern discovered: self-referential grep contracts need explicit exclusion language once task-local assertion files contain the forbidden literal.
- Quality gap: ancillary sync-tool guards remain only indirectly justified in this task; a later targeted test-curation pass could harden that path without reopening #1297.
[[2026-05-02]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | README refs to "orchestrator" in serve/kanban/README.md and share/README.md refer to the VS Code agent concept, not the deleted Python package. No IN-scope prose doc references `serve/orchestrator/`, `owlbear_orchestrator`, or `owlbear-project.json`. setup/setup-guide.md: no matches. |
| 2 | Module docstrings | Yes | Updated | `sync_from_global()` and `sync_to_global()` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` had stale docstrings claiming they resolve via `owlbear-project.json`. Updated to reflect removal (see #1296). `resolve_global_db_path()` in `scope_transfer.py` already had an accurate docstring. `setup/init.py` module docstring accurate — `_write_project_json` was deleted so no stale docstring remains. |
| 3 | External attribution | No | N/A | Deletion/cleanup task — no external patterns referenced. |
| 4 | Research doc | No | N/A | No `.owlbear/research/*.md` produced by this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `mcp-topology.excalidraw` describes `serve/knowledge/src/**` and `serve/mcp-*/src/**` — footer updated from `2026-05-02 (f74ea565)` to `2026-05-03 (800c51db)`. `project-overview.excalidraw` describes `setup/**` — footer updated from `2026-05-02 (326d8433)` to `2026-05-03 (800c51db)`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | `serve/orchestrator/` is application code (OUT of scope). No IN-scope doc uniquely references the deleted Python package by import path or directory name as live documentation. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/orchestrator/ | OUT (application package, deleted) | N/A |
| tests/fixtures/mock_acp_agent.py | OUT (test file) | N/A |
| .owlbear/scripts/e2e_smoke.py | OUT (script) | N/A |
| owlbear-project.json | OUT (config) | N/A |
| seed/owlbear-project.json | OUT (seed config) | N/A |
| pyproject.toml | OUT (config) | N/A |
| tests/test_package_boundary.py | OUT (test file) | N/A |
| tests/test_deny_non_doc_writes.py | OUT (test file) | N/A |
| uv.lock | OUT (lockfile) | N/A |
| setup/init.py | IN (docstrings) | No stale docstrings — `_write_project_json` removed, remaining docstrings accurate |
| serve/knowledge/src/owlbear_knowledge/scope_transfer.py | IN (docstrings) | Already accurate — updated by builder |
| serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py | IN (docstrings) | Updated — `sync_from_global` and `sync_to_global` docstrings corrected |
| share/diagrams/mcp-topology.excalidraw | IN (diagram) | Footer updated |
| share/diagrams/project-overview.excalidraw | IN (diagram) | Footer updated |

### Files Updated
- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` — corrected `sync_from_global` and `sync_to_global` docstrings
- `share/diagrams/mcp-topology.excalidraw` — footer updated to `2026-05-03 (800c51db)`
- `share/diagrams/project-overview.excalidraw` — footer updated to `2026-05-03 (800c51db)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1297-*` scratch files found)
[[2026-05-02]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: serve/orchestrator/ absent | `ls` confirms "No such file or directory"; test_orchestrator_dir_absent PASS | PASS |
| AC2: mock_acp_agent.py absent | `ls` confirms absent; test_mock_acp_agent_absent PASS | PASS |
| AC3: e2e_smoke.py absent | `ls` confirms absent; test_e2e_smoke_absent PASS | PASS |
| AC4: owlbear-project.json absent | `ls` confirms absent; test_root_project_json_absent PASS | PASS |
| AC5: seed/owlbear-project.json absent | `ls` confirms absent; test_seed_project_json_absent PASS | PASS |
| AC6 (revised): grep zero hits in pyproject.toml, setup/, serve/knowledge/ | 4 scoped tests pass; exclusion of self-referential test files per architecture refinement | PASS |
| AC7: uv sync succeeds | Reviewer independently verified exit 0, "All dependencies are in sync" | PASS |
| AC8: test_package_boundary.py passes | 31/31 passed in scoped run | PASS |
| AC9: ruff check passes | Clean on all task files | PASS |
| AC10 (clarified): atomic commit | Core deletion in 0e9a5aef (32 files, +35/-2347); ancillary sync-guard in 18044901 (1 file); doc-writer in 11e56495. Per clarified AC10, ancillary commits allowed. | PASS |

### Test Results
- Task-scoped (pytest): 64 passed, 0 failed (test_core_removal_1297 + test_package_boundary + test_dead_code_sweep_1296)
- Full suite (pytest): 3717 passed, 128 failed, 4 skipped - all failures in unrelated modules (mcp_kanban, sessions, storage, guidance, etc.), zero in task scope
- Vitest: failures all in unrelated frontend tests
- Ruff: 1 violation in copilot_auth.py (T201 print) - unrelated to task

### Reviewer Evidence
Detailed two-pass review, PASS at 0.94. The -0.06 was for sync-tool coverage (arch scoped out) and incomplete diff history. Thorough AC mapping with line citations.

### Architect Quality: 3/5
AC1-AC5, AC7-AC10 were specific and verifiable. AC6 as originally written was infeasible (self-referential grep contract where test files necessarily contain the forbidden literal). Required a review-reject-architecture refinement cycle to fix. AC10 also needed clarification for ancillary commits. Good overall structure, but the AC6 infeasibility caused a full pipeline round-trip.

### Deduction Breakdown
- -0.02: Sync-tool guard coverage absent (architecture explicitly scoped it out of 1297)
- -0.03: AC quality 3/5 (AC6 infeasibility caused pipeline round-trip)

### Confidence: 0.95
### Action: archive