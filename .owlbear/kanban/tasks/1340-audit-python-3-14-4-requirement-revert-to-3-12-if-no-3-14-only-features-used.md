---
id: 1340
title: Set coherent Python runtime floor and Renovate policy before sync
status: review
priority: critical
created: 2026-05-04T15:00:05.846058+00:00
updated: 2026-05-04T20:07:59.802284+00:00
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