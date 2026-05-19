---
id: 1674
title: 'Fix test_package_boundary.py: add owlbear_memory namespace to ALLOWED_IMPORTS'
status: docs
priority: needed
created: 2026-05-19T06:27:15.486710+02:00
updated: 2026-05-19T09:26:58.437364+02:00
tags:
  - phase-2
  - backend
  - type:test
parent:
depends_on: []
ac:
  - 'ALLOWED_IMPORTS in tests/test_package_boundary.py includes entry `"owlbear_memory":
    set()`'
  - ALLOWED_IMPORTS["owlbear_mcp_memory"] equals `{"owlbear_memory"}`
  - ALLOWED_IMPORTS["owlbear_cockpit"] equals `{"owlbear_kanban", 
    "owlbear_memory"}`
  - '`pytest tests/test_package_boundary.py` passes green — verified by reviewer (named-test
    + lint gate)'
proof_bundle: existing
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Scope

Update `tests/test_package_boundary.py` ALLOWED_IMPORTS dict to reflect the `owlbear_memory` package extracted in #1668:
1. Add `\"owlbear_memory\": set()` entry (leaf package — no owlbear deps per pyproject.toml)
2. Change `\"owlbear_mcp_memory\": set()` to `\"owlbear_mcp_memory\": {\"owlbear_memory\"}` (declared dep in serve/mcp-memory/pyproject.toml)
3. Change `\"owlbear_cockpit\": {\"owlbear_kanban\"}` to `\"owlbear_cockpit\": {\"owlbear_kanban\", \"owlbear_memory\"}` (declared dep in serve/cockpit/pyproject.toml, 7 imports across 3 modules)

Existing proof scope: tests/test_package_boundary.py

[[2026-05-19T06:34:43+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: update boundary test allowlist |
| Interface clarity | PASS | AC specifies exact dict values |
| Dependency correctness | PASS | No task deps needed; standalone fix |
| Module layering | PASS | Test file only, no layering |
| TDD compliance | PASS | type:test tag, proof bundle existing — test-writer passes through |
| KISS/YAGNI | PASS | Minimal 3-entry dict update |
| Premise challenge | PASS | Boundary test currently broken due to #1668 extraction |
| Pattern consistency | PASS | Follows existing ALLOWED_IMPORTS dict pattern |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Test infrastructure only |

### Challenge Results
- Challenger: block (confidence 0.18)
- Architect response: rebutted — challenger applied completion criteria to a pre-implementation review. All \"critical\" findings (code not yet changed, test not yet green) are expected at backlog stage. AC-quality feedback on stage scoping accepted and applied to AC 4.

### Proof-Bundle Validation
- Planner assignment: none (null)
- Final bundle: existing
- Existing proof scope: tests/test_package_boundary.py
- Test-writer: SKIP (bundle existing)

### Codebase Evidence
- owlbear_memory pyproject.toml: deps = [pydantic, ruamel.yaml] — leaf package confirmed
- mcp-memory pyproject.toml: declares owlbear-memory dep; 2 imports in server.py and tools.py
- cockpit pyproject.toml: declares owlbear-memory dep; 7 imports across routes/memory.py, main.py, deps.py
- Item 3 elevated from \"optional\" to mandatory per evidence

### Verdict: APPROVE
### Action Taken: Refined empty AC into 4 verifiable lines, tagged type:test, set proof_bundle=existing, advanced to todo

[[2026-05-19T06:36:50+02:00]]
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Existing proof scope: `tests/test_package_boundary.py`
- Passing through to builder.

[[2026-05-19T08:12:15+02:00]]
## Builder Notes
- Proof bundle: `existing` (used named existing proof as required).
- Files changed: `tests/test_package_boundary.py`
- AC implementation:
  - Added `"owlbear_memory": set()` to `ALLOWED_IMPORTS`.
  - Updated `"owlbear_mcp_memory"` allowed deps to `{"owlbear_memory"}`.
  - Updated `"owlbear_cockpit"` allowed deps to include `"owlbear_memory"` alongside `"owlbear_kanban"`.
- Verification evidence (quality-runner, scoped):
  - Test path: `tests/test_package_boundary.py`
  - Result: 31 passed, 0 failed, 0 skipped
  - Lint: ruff clean (no violations)
  - Coverage: not requested for this existing-proof task
- Commit:
  - `688038ab`
  - Message: `test: update package boundary imports for memory split (#1674, builder)`
  - Scope: only `tests/test_package_boundary.py`

Post-task reflection:
- No blockers encountered.
- Existing-proof routing was sufficient for this test-only boundary contract update.
- No additional quality gaps observed in scope.

[[2026-05-19T08:32:06+02:00]]
## Review Evidence
- Verdict: FAIL
- Independent verification: quality-runner reran `pytest tests/test_package_boundary.py` and the lint gate for `tests/test_package_boundary.py`; result was 31 passed, 0 failed, 0 skipped, and ruff clean.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1-AC3 | The named proof does not assert that these allowlists exactly match declared workspace dependencies. Current assertions only check value type, namespace-key coverage, and that the live codebase has no undeclared cross-namespace imports. Extra namespaces in these three sets would still leave the suite green if no source file imported them. | `tests/test_package_boundary.py:218-235`, `tests/test_package_boundary.py:250-259`, `tests/test_package_boundary.py:291-297`; current code values at `tests/test_package_boundary.py:28`, `tests/test_package_boundary.py:31`, `tests/test_package_boundary.py:35`; manifest ground truth at `serve/memory/pyproject.toml:6`, `serve/mcp-memory/pyproject.toml:6`, `serve/cockpit/pyproject.toml:6-8` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add explicit assertions that `ALLOWED_IMPORTS["owlbear_memory"]`, `ALLOWED_IMPORTS["owlbear_mcp_memory"]`, and `ALLOWED_IMPORTS["owlbear_cockpit"]` exactly match the workspace dependencies declared in the relevant package manifests, so extra allowlist entries fail the suite. | `tests/test_package_boundary.py`, `serve/memory/pyproject.toml`, `serve/mcp-memory/pyproject.toml`, `serve/cockpit/pyproject.toml` | AC1-AC3 proof gap; current suite only checks shape/key coverage and undeclared-import scanning at the cited lines. |

## Observations
- Direct code evidence is correct: the updated `ALLOWED_IMPORTS` entries match the current manifests (`tests/test_package_boundary.py:28`, `tests/test_package_boundary.py:31`, `tests/test_package_boundary.py:35`).
- AC4 is satisfied independently: quality-runner reported `pytest tests/test_package_boundary.py` 31 passed, 0 failed, 0 skipped, and ruff clean.

[[2026-05-19T08:56:07+02:00]]
## Test-Writer Notes
- Retry: added 6 manifest-alignment tests in `tests/test_package_boundary_1674.py`.
- Reviewer gap addressed: `TestFromAC_ManifestAlignment` parses each affected `pyproject.toml` via `tomllib` and asserts exact set equality with the corresponding `ALLOWED_IMPORTS` entry — extra allowed entries now cause test failures.
- Tests per class: `TestFromAC_ManifestAlignment` — 6 tests (3 exact-match assertions for AC1/AC2/AC3; 3 regression guard assertions that prove a superset would fail).
- Quality-runner result: 6 passed, 0 failed, 0 skipped; ruff clean.
- Builder skip: test-only retry — all tests pass against current implementation.
- AC coverage:
  | AC Line | Test(s) |
  |---------|---------|
  | AC1: `owlbear_memory: set()` | `test_owlbear_memory_allowed_imports_matches_manifest`, `test_extra_entry_in_owlbear_memory_would_fail` |
  | AC2: `owlbear_mcp_memory: {owlbear_memory}` | `test_owlbear_mcp_memory_allowed_imports_matches_manifest`, `test_extra_entry_in_owlbear_mcp_memory_would_fail` |
  | AC3: `owlbear_cockpit: {owlbear_kanban, owlbear_memory}` | `test_owlbear_cockpit_allowed_imports_matches_manifest`, `test_extra_entry_in_owlbear_cockpit_would_fail` |
  | AC4: pytest green | Verified by quality-runner (31 original + 6 new = all pass) |
- Commit: `05a0f324`

[[2026-05-19T09:26:58+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1674 -> docs | AC mapped to code and evidence sufficient.
- Blocking findings: none.
- AC1: `ALLOWED_IMPORTS["owlbear_memory"]` is `set()` at `tests/test_package_boundary.py:31`; exact-manifest proof is asserted in `tests/test_package_boundary_1674.py:60-67` against `serve/memory/pyproject.toml:6`.
- AC2: `ALLOWED_IMPORTS["owlbear_mcp_memory"]` is `{"owlbear_memory"}` at `tests/test_package_boundary.py:35`; exact-manifest proof is asserted in `tests/test_package_boundary_1674.py:69-76` against `serve/mcp-memory/pyproject.toml:6`.
- AC3: `ALLOWED_IMPORTS["owlbear_cockpit"]` is `{"owlbear_kanban", "owlbear_memory"}` at `tests/test_package_boundary.py:28`; exact-manifest proof is asserted in `tests/test_package_boundary_1674.py:78-85` against `serve/cockpit/pyproject.toml:7-8`.
- AC4: Independent verification is current and sufficient: quality-runner reran `pytest tests/test_package_boundary.py tests/test_package_boundary_1674.py` and scoped ruff on both files; result was 37 passed, 0 failed, 0 skipped, and ruff clean.
- Proof sufficiency: the prior review gap is closed because the retry file now uses exact equality assertions at `tests/test_package_boundary_1674.py:64`, `tests/test_package_boundary_1674.py:73`, and `tests/test_package_boundary_1674.py:82`, so extra allowlist entries would fail.
- Safety/security: scope is test-only manifest parsing via `tomllib`; no new runtime, credential, shell, SQL, or path-handling surface was introduced.

## Observations
- The supplementary superset checks at `tests/test_package_boundary_1674.py:87`, `tests/test_package_boundary_1674.py:94`, and `tests/test_package_boundary_1674.py:101` are redundant with the equality assertions, but they are harmless.
