---
id: 1340
title: Set coherent Python runtime floor and Renovate policy before sync
status: archived
priority: medium
created: 2026-05-04T15:00:05.846058+00:00
updated: 2026-05-04T22:48:03.301767+00:00
tags:
- sync-blocker
- config
- dependencies
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

The product runtime floor is inconsistent. Consumer docs promise Python 3.12+, root Ruff still targets Python 3.12, but most `serve/*/pyproject.toml` files require `>=3.14.4` and `.python-version` says `3.14`. Syncing as-is raises the consumer install floor without a single recorded project decision.

Decision from deployment audit: prefer Python 3.12 as the product floor unless source audit proves a real 3.13+/3.14-only requirement. To avoid noisy package-manager alerts, add a Renovate Python policy that prevents automated Python-major/minor floor churn.

## Acceptance Criteria

1. Audit every synced Python package under `serve/*` for Python 3.13+ or 3.14+ only syntax/features AND for dependencies whose own `requires-python` floor exceeds 3.12. (td:1)
2. If no justified newer-language feature is found, set all synced `serve/*/pyproject.toml` `requires-python` values to `>=3.12`. (td:1)
3. If a newer floor is justified, document the exact feature/dependency and align every consumer-facing prerequisite doc, `.python-version`, root lint target, and tests to that chosen floor. (td:1)
4. For the default Python 3.12 decision, align `.python-version`, package metadata, `README.md`, `README-consumer.md`, `setup/setup-guide.md`, and any other prerequisite references. (td:1)
5. Add a Renovate package rule to `.github/renovate.json` that suppresses Python floor-update churn, using this policy or a functionally equivalent one: (td:1)

```json
{
	"packageRules": [
		{
			"matchPackageNames": ["python"],
			"matchManagers": ["pep621", "uv"],
			"allowedVersions": "<3.13.0"
		}
	]
}
```

6. Update `tests/test_python_version_floor_1340.py` so it verifies the final project-wide floor and Renovate policy, not only kanban/mcp-kanban. (td:0)
7. Run the focused version-floor tests and a representative Python package import/smoke test before completion. (td:0)

## Key Files

- `serve/*/pyproject.toml`
- `.python-version`
- `.github/renovate.json`
- `pyproject.toml`
- `README.md`
- `README-consumer.md`
- `setup/setup-guide.md`
- `share/instructions/owlbear-system.instructions.md`
- `tests/test_python_version_floor_1340.py`

## Audit Evidence

- `README-consumer.md` and `setup/setup-guide.md` still say Python 3.12+.
- Root `pyproject.toml` uses Ruff `target-version = "py312"`.
- Most `serve/*/pyproject.toml` files require `>=3.14.4`; `serve/mcp-memory` already remains at `>=3.12`.
- `.python-version` currently says `3.14` and is included in `sync-to-main` infra sync.
- User explicitly requested no more package-manager alerts for newer Python versions and approved choosing the best project-wide floor.

## Test-Writer Notes

Existing RED file: `tests/test_python_version_floor_1340.py`.

Broaden it from kanban/mcp-kanban only to the synced Python workspace. Keep the test focused on declared runtime policy and syntax evidence, not dependency-version preferences unrelated to Python itself.

## Source

Deployment audit reconciliation, 2026-05-04.
[[2026-05-04]]

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: align Python runtime floor + prevent automated churn |
| Interface clarity | PASS | AC lines are precise with conditional paths (AC2/AC3) |
| Dependency correctness | PASS | No task deps needed; standalone config task |
| Module layering | PASS | Config-only; no code module changes |
| TDD compliance | PASS | RED test exists; Test-Writer Notes instruct broadening |
| KISS/YAGNI | PASS | Minimal scope — align values + add one Renovate rule |
| Premise challenge | PASS | Real inconsistency confirmed: 8/9 packages at >=3.14.4 while docs/Ruff say 3.12 |
| Pattern consistency | PASS | Follows project conventions for config alignment |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Config/dependencies domain only |

### AC Refinements Applied
- AC1: Added dependency floor audit (not just source syntax) — challenger caught that a dep requiring Python >3.12 would force floor up
- AC4: Added `share/instructions/owlbear-system.instructions.md` to Key Files (tech stack table says "Python 3.12+", synced to main)

### Challenge Results
- Challenger: reconsider (0.64)
- Concerns addressed: (1) dependency-audit gap in AC1 — refined to include dep floor checks; (2) governance gap — deployment audit decision IS recorded in task context section; (3) test-proof mismatch — already addressed by AC6 + Test-Writer Notes; (4) hidden instruction file surface — added to Key Files for builder awareness
- Architect response: accepted AC1 refinement, rebutted rest as already covered

### Test Depth
- AC1: td:1, AC2: td:1, AC3: td:1, AC4: td:1, AC5: td:1, AC6: td:0, AC7: td:0
- Max depth: 1
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC1 to include dependency floor audit, added instruction file to Key Files, advanced to todo.
[[2026-05-04]]
Architecture review complete. Refined AC1 to include dependency floor audit per challenger feedback. All 10 criteria PASS. Task is well-scoped config alignment with proper TDD scaffolding. Advanced to todo for test-writer processing.
[[2026-05-04]]
## Test-Writer Notes
- Test file: tests/test_python_version_floor_1340.py
- Classes: TestFromAC_AllPackagesRequiresPythonFloor, TestFromAC_NoUnjustifiedVersionBump, TestFromAC_PythonVersionAlignment, TestFromAC_RenovatePythonPolicy
- Tests per category: happy 0, edge 0, error 0, boundary 7 (all policy/config boundary assertions)
- Total: 7 tests, all FAIL
- ruff: clean

### AC Coverage
| AC | Test(s) | Status |
|----|---------|--------|
| AC1 (syntax audit + no unjustified floor) | TestFromAC_NoUnjustifiedVersionBump::test_all_packages_floor_justified_by_source_syntax | FAIL ✓ |
| AC2 (all packages >=3.12) | TestFromAC_AllPackagesRequiresPythonFloor::test_all_synced_packages_require_python_3_12, test_no_synced_package_pins_to_3_14 | FAIL ✓ |
| AC3 (conditional alignment) | Covered by AC2 + AC4 tests (AC3 is the "if justified" branch; AC2/AC4 cover the expected "not justified" path) | — |
| AC4 (.python-version alignment) | TestFromAC_PythonVersionAlignment::test_python_version_file_says_3_12 | FAIL ✓ |
| AC5 (Renovate Python policy) | TestFromAC_RenovatePythonPolicy::test_renovate_has_python_package_rule, test_renovate_python_rule_has_allowed_versions, test_renovate_python_rule_targets_pep621_or_uv_manager | FAIL ✓ |
| AC6 (td:0) | — | skip |
| AC7 (td:0) | — | skip |

### Scope change from previous version
Previous file covered only serve/kanban and serve/mcp-kanban (2 packages). Broadened to all 9 synced packages. Added .python-version alignment test and 3 Renovate policy tests. Total 7 tests vs. 4 prior tests.
[[2026-05-04]]
## Builder Notes
- Implementation: aligned Python floor metadata to `>=3.12` in synced package manifests and aligned `.python-version` to `3.12`; added Renovate Python floor-freeze package rule.
- Files changed: `.python-version`, `.github/renovate.json`, `serve/browser/pyproject.toml`, `serve/cockpit/pyproject.toml`, `serve/kanban/pyproject.toml`, `serve/knowledge/pyproject.toml`, `serve/mcp-browser/pyproject.toml`, `serve/mcp-kanban/pyproject.toml`, `serve/mcp-knowledge/pyproject.toml`, `serve/tools/pyproject.toml`.
- Test evidence (RED->GREEN): quality-runner scoped on `tests/test_python_version_floor_1340.py` moved from 7 failed / 0 passed to 7 passed / 0 failed.
- Coverage: 94% on `tests.test_python_version_floor_1340` (quality-runner scoped verification).
- Lint: clean (`ruff` clean on task test file via quality-runner).
- AC1 dependency/runtime audit evidence: `rg -n "requires-python\s*=\s*\".*3\.(13|14)" serve/**/pyproject.toml uv.lock` returned no matches.
- AC7 representative smoke evidence: `uv run python -c "import owlbear_kanban.engine, owlbear_cockpit.main, owlbear_mcp_memory.server; print('import-smoke-ok')"` printed `import-smoke-ok` with exit code 0.
- Commit: `20bdf7fcbd3c2f600d11f155348cda512b1d8742` (`chore: align python runtime floor policy (#1340, builder)`).

### Post-task Reflection
- Problem faced: package runtime floor drifted across synced package metadata while docs/lint targets remained 3.12.
- Workaround applied: task-scoped metadata normalization plus explicit Renovate guardrail to prevent automatic Python floor churn.
- Pattern discovered: `git commit --only -- <paths>` is the safest atomic commit method in this dirty shared tree model.
- Quality gap noted: AC1 dependency-floor audit is not currently enforced by a dedicated test beyond floor declarations/syntax proxy; evidence was captured via lockfile/config search.
[[2026-05-04]]
## Review Evidence
### Test Results
- quality-runner scoped pass on `tests/test_python_version_floor_1340.py`: 7 passed, 0 failed, 0 skipped.

### Lint Results
- quality-runner lint on `tests/test_python_version_floor_1340.py`: clean.

### Coverage
- quality-runner reported 94% coverage on `tests.test_python_version_floor_1340`.

### Scope and Live-State Checks
- Builder commit `20bdf7fcbd3c2f600d11f155348cda512b1d8742` is present in `.git/logs/HEAD:1869` and `.git/logs/refs/heads/dev:1715`.
- All synced package manifests currently declare `requires-python = ">=3.12"` at line 4 in each `serve/*/pyproject.toml` file.
- `.python-version:1` is `3.12`.
- Root Ruff target remains `py312` at `pyproject.toml:39`.
- Consumer-facing prerequisites remain aligned to Python 3.12+ at `README.md:13`, `README-consumer.md:21`, `setup/setup-guide.md:11`, and `share/instructions/owlbear-system.instructions.md:23`.
- Renovate policy is present at `.github/renovate.json:29-37` with `matchPackageNames=["python"]`, `matchManagers=["pep621", "uv"]`, and `allowedVersions="<3.13.0"`.

### TestFromAC Audit
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1: audit every synced package for 3.13+/3.14+ syntax and dependency floors above 3.12 | `TestFromAC_NoUnjustifiedVersionBump::test_all_packages_floor_justified_by_source_syntax` | No for the dependency-floor half. The helper narrows the feature audit to a single `TypeIs` regex at `tests/test_python_version_floor_1340.py:52-53`, and the test body at `tests/test_python_version_floor_1340.py:101` only checks source trees plus `requires-python` declarations. | MISSING / LAX |
| AC2: synced manifests use `>=3.12` when no newer floor is justified | `test_all_synced_packages_require_python_3_12`, `test_no_synced_package_pins_to_3_14` | Yes. These fail if any synced manifest drifts above or away from `>=3.12`. | COVERED |
| AC3: if a newer floor is justified, document and align to that floor | Indirect only | Acceptable for the current default-3.12 path because live files show no newer floor selected. | COVERED FOR CURRENT BRANCH |
| AC4: align `.python-version`, package metadata, README.md, README-consumer.md, setup/setup-guide.md, and other prerequisite references | `TestFromAC_PythonVersionAlignment::test_python_version_file_says_3_12` | No. The file comment names README/setup prerequisites at `tests/test_python_version_floor_1340.py:9-10`, but the only prerequisite-file constant is `.python-version` at `tests/test_python_version_floor_1340.py:22`, and the only AC4 assertion reads that file at `tests/test_python_version_floor_1340.py:123`. | MISSING |
| AC5: add Renovate Python floor-freeze rule | `test_renovate_has_python_package_rule`, `test_renovate_python_rule_has_allowed_versions`, `test_renovate_python_rule_targets_pep621_or_uv_manager` | Yes. | COVERED |
| AC6: broaden task test to final project-wide floor and Renovate policy | Whole file scope | Yes. `_SYNCED_PACKAGES` now spans all 9 synced packages at `tests/test_python_version_floor_1340.py:26-36`, and the file includes Renovate assertions at `tests/test_python_version_floor_1340.py:133-174`. | COVERED |
| AC7: run focused version-floor tests and a representative import/smoke check | quality-runner rerun + Builder Notes | Focused tests were independently rerun by quality-runner. Import-smoke remains builder-reported in task notes only. | COVERED WITH DEDUCTION |

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | Live manifests are aligned, but test proof is incomplete: `tests/test_python_version_floor_1340.py:52-53` and `tests/test_python_version_floor_1340.py:101-115` do not verify dependency floors and only scan for one 3.13+ feature token. | `TestFromAC_NoUnjustifiedVersionBump::test_all_packages_floor_justified_by_source_syntax` | FAIL |
| AC2 | `serve/*/pyproject.toml:4` now reads `requires-python = ">=3.12"` in all 9 synced packages; task tests at `tests/test_python_version_floor_1340.py:75-97` passed under quality-runner. | `test_all_synced_packages_require_python_3_12`, `test_no_synced_package_pins_to_3_14` | PASS |
| AC3 | No newer floor is selected in live files. Current repo state stays on the default 3.12 branch. | Indirect via AC2 and AC4 evidence | PASS |
| AC4 | Live prerequisite docs are aligned at `README.md:13`, `README-consumer.md:21`, `setup/setup-guide.md:11`, `share/instructions/owlbear-system.instructions.md:23`, and `.python-version:1`. The mapped test only checks `.python-version`. | `test_python_version_file_says_3_12` | FAIL |
| AC5 | `.github/renovate.json:29-37` contains the Python floor-freeze rule and the three mapped tests passed. | Renovate test trio | PASS |
| AC6 | The task test file now targets all synced packages plus Renovate policy. | Whole file | PASS |
| AC7 | quality-runner independently reran the focused test suite; the representative import-smoke remains builder-reported only. | quality-runner + Builder Notes | PASS WITH DEDUCTION |

### Deductions
- `-0.10` AC1 proof gap: dependency-floor audit is not enforced by the task test, and the syntax detector is too narrow for an AC phrased as 3.13+/3.14+ feature audit.
- `-0.05` AC4 proof gap: prerequisite docs are aligned in live files, but the task test never reads or asserts those surfaces.
- `-0.02` Commit presence was verified from `.git/logs`, but this tool surface did not provide direct `git diff` / `git status` execution for a higher-confidence TestFromAC immutability and dirty-tree contamination check.

### Verdict
- FAIL
- Confidence: 0.83
- Routing rationale: current live files look correct, but the task still lacks AC-complete executable proof. This is a test-only retry, so route to `todo` for test-writer strengthening.

### Action
- Reject to `todo`.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add AC1 coverage that proves the dependency-floor audit and strengthens the 3.13+/3.14+ feature audit beyond the single `TypeIs` sentinel. | `tests/test_python_version_floor_1340.py` | AC1 at `tests/test_python_version_floor_1340.py:3-4`; `_PY313_PLUS_PATTERNS` at `tests/test_python_version_floor_1340.py:52-53`; mapped test at `tests/test_python_version_floor_1340.py:101-115` |
| 2 | test-writer | Add AC4 coverage for `README.md`, `README-consumer.md`, `setup/setup-guide.md`, and `share/instructions/owlbear-system.instructions.md` instead of checking only `.python-version`. | `tests/test_python_version_floor_1340.py` | AC4 at `tests/test_python_version_floor_1340.py:9-10`; only prerequisite-file constant at `tests/test_python_version_floor_1340.py:22`; only AC4 read/assertion at `tests/test_python_version_floor_1340.py:123`; live aligned docs at `README.md:13`, `README-consumer.md:21`, `setup/setup-guide.md:11`, `share/instructions/owlbear-system.instructions.md:23` |
[[2026-05-04]]
## Test-Writer Notes
- Retry: filled two reviewer gaps (AC1 dependency floor + AC4 prerequisite docs). All new tests pass against current implementation → builder skip per step 1b.1.
- Test file: tests/test_python_version_floor_1340.py
- Classes added: TestFromAC_DependencyFloorAudit, TestFromAC_PrerequisiteDocsAlignment
- Patterns expanded: _PY313_PLUS_PATTERNS now covers 5 tokens (TypeIs, typing.ReadOnly, typing.deprecated, warnings.deprecated, TypeForm)
- Tests added: 6 new (2 + 4), total 13 (was 7)
- All 13 PASS, ruff clean

### AC Coverage (updated)
| AC | Test(s) | Status |
|----|---------|--------|
| AC1 syntax audit | TestFromAC_NoUnjustifiedVersionBump::test_all_packages_floor_justified_by_source_syntax (broadened), TestFromAC_DependencyFloorAudit::test_no_synced_package_has_313_plus_feature_in_source | COVERED |
| AC1 dependency floor | TestFromAC_DependencyFloorAudit::test_uv_lock_workspace_floor_is_3_12 | COVERED (new) |
| AC2 | test_all_synced_packages_require_python_3_12, test_no_synced_package_pins_to_3_14 | COVERED |
| AC3 | Conditional branch; covered by AC2+AC4 for default 3.12 path | COVERED |
| AC4 .python-version | test_python_version_file_says_3_12 | COVERED |
| AC4 prerequisite docs | TestFromAC_PrerequisiteDocsAlignment: test_readme_states_python_3_12_floor, test_readme_consumer_states_python_3_12_floor, test_setup_guide_states_python_3_12_floor, test_system_instructions_states_python_3_12_floor | COVERED (new) |
| AC5 | Renovate test trio | COVERED |
| AC6/AC7 | td:0 — skip | N/A |

### Builder skip rationale
All 6 new tests PASS against current code. Reviewer's Required Follow-up contained only test-proof gaps (no implementation fixes). Advancing directly to review per step 1b.1.
[[2026-05-04]]
## Builder Notes
- Implementation: no additional code changes were required in this builder pass; task state already reflected aligned runtime floor/config updates.
- Files changed in this pass: none.
- Test results: `tests/test_python_version_floor_1340.py` -> 13 passed, 0 failed, 0 skipped (quality-runner scoped run).
- Lint status: clean (`ruff` clean on `tests/test_python_version_floor_1340.py` via quality-runner).
- Coverage: quality-runner reported no production coverage collected for this test file (`overall_pct: 0`) because tests validate version/config policy surfaces rather than exercising runtime modules.
- AC7 smoke evidence: `uv run python -c "import owlbear_kanban.engine, owlbear_cockpit.main, owlbear_mcp_memory.server; print('import-smoke-ok')"` exited 0 and printed `import-smoke-ok`.
- Evidence summary: current task-scoped tests, lint, and representative import smoke all pass with no new implementation defects observed.

### Post-task Reflection
- Problem faced: task body carried long prior history (build/review/retry), so the main risk was advancing without a fresh independent verification pass.
- Workaround applied: reran scoped quality-runner checks and a direct smoke import check before routing.
- Pattern discovered: policy/config assertion tests can legitimately produce zero production coverage data; this should be interpreted alongside passing assertions and smoke checks.
- Quality gap noted: none in current builder scope.
[[2026-05-04]]
## Review Evidence
### Test Results
- quality-runner scoped on `tests/test_python_version_floor_1340.py`: 13 passed, 0 failed, 0 skipped.
- quality-runner supplementary AC7 smoke-equivalent selectors: 3 passed, 0 failed, exit code 0.
  - `tests/test_cockpit_boundary.py::TestFromAC_CockpitPackageSkeleton::test_main_module_importable`
  - `tests/test_mcp_memory_tools_1273.py::TestFromAC_MCPEntrypoint::test_main_module_importable_and_exposes_mcp`
  - `tests/test_engine_dead_code_1204.py::TestFromAC_RemoveValidateEngineConfig::test_function_not_in_engine_module`

### Lint Results
- quality-runner lint on `tests/test_python_version_floor_1340.py`: clean.

### Coverage
- Not a meaningful gate for this task. The task suite validates configuration and policy surfaces rather than exercising production modules, so quality-runner correctly reported production coverage as not applicable / no data collected.

### TestFromAC Audit
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1: audit synced packages for 3.13+/3.14+ features and dependency floors above 3.12 | `test_all_packages_floor_justified_by_source_syntax`, `test_uv_lock_workspace_floor_is_3_12`, `test_no_synced_package_has_313_plus_feature_in_source` | Yes. The task suite now checks all synced source trees via `_SYNCED_SOURCES` / `_PY313_PLUS_PATTERNS` and fails if `uv.lock` workspace `requires-python` rises above `>=3.12`. | COVERED |
| AC2: synced manifests use `>=3.12` when no newer floor is justified | `test_all_synced_packages_require_python_3_12`, `test_no_synced_package_pins_to_3_14` | Yes. | COVERED |
| AC3: if a newer floor is justified, document and align to that floor | Indirect for current branch | Yes for the current accepted branch: AC1 evidence and live files keep the project on the default 3.12 path, so the conditional newer-floor branch is not active. | COVERED FOR CURRENT BRANCH |
| AC4: align `.python-version`, package metadata, README.md, README-consumer.md, setup/setup-guide.md, and synced prerequisite references | `test_python_version_file_says_3_12`, `test_readme_states_python_3_12_floor`, `test_readme_consumer_states_python_3_12_floor`, `test_setup_guide_states_python_3_12_floor`, `test_system_instructions_states_python_3_12_floor` | Yes. These fail if the aligned 3.12 prerequisite text is removed from the named surfaces. | COVERED |
| AC5: add Renovate Python floor-freeze rule | `test_renovate_has_python_package_rule`, `test_renovate_python_rule_has_allowed_versions`, `test_renovate_python_rule_targets_pep621_or_uv_manager` | Yes. | COVERED |
| AC6: task test verifies final project-wide floor and Renovate policy | File-scope artifact evidence in `tests/test_python_version_floor_1340.py` | Yes. `_SYNCED_PACKAGES` now spans all 9 synced packages and the file contains Renovate-policy assertions. | COVERED |
| AC7: run focused version-floor tests and a representative Python package import/smoke test | quality-runner scoped task suite + supplementary import-bearing selectors | Yes. Independent review reran the focused task suite and three import-bearing selectors covering the same package entry points as the builder's smoke command. | COVERED |

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | `tests/test_python_version_floor_1340.py:52`, `tests/test_python_version_floor_1340.py:115`, `tests/test_python_version_floor_1340.py:196`, `tests/test_python_version_floor_1340.py:215`, `uv.lock:3` | AC1 trio | PASS |
| AC2 | `tests/test_python_version_floor_1340.py:89`, `tests/test_python_version_floor_1340.py:100`, and all synced manifests at `serve/*/pyproject.toml:4` declare `requires-python = ">=3.12"` | AC2 pair | PASS |
| AC3 | No newer floor selected in live state: `.python-version:1` is `3.12`, root Ruff target remains `py312` at `pyproject.toml:39`, and AC1 audit stayed on the default 3.12 branch | Indirect via AC1/AC4 evidence | PASS |
| AC4 | `.python-version:1`, `README.md:13`, `README-consumer.md:21`, `setup/setup-guide.md:11`, `share/instructions/owlbear-system.instructions.md:23`, plus task tests at `tests/test_python_version_floor_1340.py:136`, `:237`, `:244`, `:251`, `:258` | AC4 set | PASS |
| AC5 | `.github/renovate.json:29`, `:30`, `:33`, `:37` plus task tests at `tests/test_python_version_floor_1340.py:147`, `:160`, `:174` | Renovate trio | PASS |
| AC6 | `tests/test_python_version_floor_1340.py:27-35` enumerates all synced packages; Renovate coverage is present at `tests/test_python_version_floor_1340.py:147-174` | File scope | PASS |
| AC7 | quality-runner: task suite 13/13 pass; supplementary smoke selectors 3/3 pass under Python 3.12.13 | task suite + smoke selectors | PASS |

### Security / Data Safety / Necessity
- No security, data-safety, or necessity issues found. This task changes version-policy/config surfaces only and adds no new dependencies or runtime behavior.

### Deductions
- `-0.03` This tool surface did not provide direct `git diff` / `git status`, so dirty-tree contamination and exact TestFromAC ownership could not be verified at terminal level. Current task history shows a test-only retry with builder skip and no new builder file changes, which reduces but does not eliminate that risk.

### Verdict
- PASS
- Confidence: 0.95
- Routing rationale: live config surfaces are aligned to Python 3.12, the Renovate freeze rule is present, the broadened task suite independently passes, and supplementary import-bearing smoke selectors passed under Python 3.12.13.

### Action
- Advance to `docs`.
[[2026-05-04]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Verified/No change | `README.md:13`, `README-consumer.md:21`, `setup/setup-guide.md:11` already say "Python 3.12+" — no update needed |
| 2 | Module docstrings | No | N/A | Changed files are config metadata (`pyproject.toml`, `.python-version`, `.github/renovate.json`) — no Python module logic touched |
| 3 | External attribution | No | N/A | No external repos or articles cited |
| 4 | Research doc | No | N/A | No research document produced |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/project-overview.excalidraw` describes `serve/*/pyproject.toml` — footer updated to `Last verified: 2026-05-05 (09e060d4)` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.python-version` | OUT | N/A (config file) |
| `.github/renovate.json` | OUT | N/A (config file) |
| `serve/*/pyproject.toml` (9 files) | OUT | N/A (metadata config, not docstrings) |
| `tests/test_python_version_floor_1340.py` | OUT | N/A (test file) |
| `share/diagrams/project-overview.excalidraw` | IN | Footer updated (diagram describes-match) |
| `README.md` | IN | Verified accurate (already says Python 3.12+) |
| `README-consumer.md` | IN | Verified accurate (already says Python 3.12+) |
| `setup/setup-guide.md` | IN | Verified accurate (already says Python 3.12+) |

### Files Updated
- `share/diagrams/project-overview.excalidraw` — footer updated to `Last verified: 2026-05-05 (09e060d4)`, committed `b2eb4b09`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1340-*` scratch files existed)
[[2026-05-04]]
## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| AC1: audit synced packages for 3.13+/3.14+ features and dep floors | Tests `test_all_packages_floor_justified_by_source_syntax`, `test_uv_lock_workspace_floor_is_3_12`, `test_no_synced_package_has_313_plus_feature_in_source` — 3/3 pass | PASS |\n| AC2: all synced manifests use `>=3.12` | Tests `test_all_synced_packages_require_python_3_12`, `test_no_synced_package_pins_to_3_14` — live state confirms `serve/cockpit/pyproject.toml:4` reads `>=3.12` | PASS |\n| AC3: conditional newer floor alignment | No newer floor selected; default 3.12 branch active. Covered by AC1+AC2+AC4 evidence | PASS |\n| AC4: align .python-version + prerequisite docs | `.python-version` = `3.12`; tests `test_python_version_file_says_3_12`, `test_readme_states_python_3_12_floor`, `test_readme_consumer_states_python_3_12_floor`, `test_setup_guide_states_python_3_12_floor`, `test_system_instructions_states_python_3_12_floor` — 5/5 pass | PASS |\n| AC5: Renovate Python floor-freeze rule | Live `.github/renovate.json` confirmed: matchPackageNames=[python], matchManagers=[pep621,uv], allowedVersions=<3.13.0; tests 3/3 pass | PASS |\n| AC6: broaden task test to project-wide scope | File covers all 9 synced packages + Renovate policy assertions — 13 total tests | PASS |\n| AC7: run focused tests + smoke | 13/13 task tests pass independently; builder import-smoke exit 0 | PASS |\n\n### Test Results\n- pytest (task-scoped): 13 passed, 0 failed\n- pytest (full suite): 260 failures, all in unrelated domains (memory model, engine accessor, decision routing, wave assembly, frontend shell) — none in task scope\n- ruff (task file): clean\n\n### Architect Quality: 4/5\nAC lines are precise with conditional branching (AC2/AC3). Challenger refinement to AC1 (dependency floor audit) caught a real gap. Minor: AC4 could have explicitly listed all prerequisite files in the initial draft.\n\n### Deduction Breakdown\n- AC lines with no evidence: 0 (all 7 covered) -> 0\n- Lint violations: 0 -> 0\n- AC quality <= 3: no (4/5) -> 0\n- Missing reviewer evidence: no (thorough, two-pass) -> 0\n- Full-suite failures in task scope: 0 -> 0\n- Conservative: -0.02 for full-suite exit code 1 (failures demonstrably out-of-scope but exhaustive cross-check not possible)\n\n### Confidence: 0.98\n### Action: archive\n\n### Commits Verified\n| Commit | Type | Attribution |\n|--------|------|-------------|\n| eb6eebc0 | test | test-writer |\n| 20bdf7fc | chore | builder |\n| b2eb4b09 | docs | doc-writer |