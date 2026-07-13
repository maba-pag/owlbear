---
id: 1038
title: Restore tests/test_package_boundary.py cross-import enforcement
status: archived
priority: medium
created: 2026-04-20 01:30:45.744379+00:00
updated: 2026-04-20 02:06:38.287874+00:00
tags:
- quality
- test
- architecture
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Context

`tests/test_package_boundary.py` with `ALLOWED_IMPORTS` dict was deleted during the cockpit nuclear reset (#924). Multiple architecture documents and archived tasks reference it as a canonical cross-package import guard (see `r-architecture-standards` line 111, archived task #524, research doc `ast-package-boundary-enforcement.md`).

Every `serve/` package added since the reset (cockpit, tools, etc.) has been added without cross-import verification.

## Acceptance Criteria

- [ ] `tests/test_package_boundary.py` exists with `ALLOWED_IMPORTS: dict[str, set[str]]` mapping each `serve/` namespace to its allowed owlbear-namespace imports
- [ ] All current `serve/*/src/` namespaces have an entry in `ALLOWED_IMPORTS`
- [ ] AST-based scan verifies no undeclared cross-package imports exist
- [ ] `ALLOWED_IMPORTS` keys validated against discovered namespaces under `serve/*/src/`
- [ ] Tests pass with current codebase (no false positives from existing code)
[[2026-04-20]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One test file restoring one enforcement mechanism |
| Interface clarity | PASS | AC specifies file location, data structure, scan method; builder notes below fill in the dependency map |
| Dependency correctness | PASS | No task dependencies needed |
| Module layering | PASS | Test file only — no module layering impact |
| TDD compliance | PASS | Task IS the test; tagged `test`+`quality` for pass-through |
| KISS/YAGNI | PASS | ~60 LOC, stdlib `ast` only, zero external deps |
| Premise challenge | PASS | `r-architecture-standards` references this test as canonical (line ~111); deleted accidentally in #924, not intentionally |
| Pattern consistency | PASS | Follows existing AST scan pattern in `tests/test_cockpit_boundary.py` `_collect_forbidden_imports()` |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Test/quality domain only |

### Builder Notes (AC refinements)

**Research doc is data-stale.** `.owlbear/research/ast-package-boundary-enforcement.md` validates the AST approach but its namespace list (7, references `packages/*/src/`) is outdated. Do NOT use it for namespace enumeration or dependency mapping. Ground truth sources: `serve/*/pyproject.toml` workspace deps + `serve/*/src/` directory scan.

**Current namespaces (11 across 10 packages):**

| Namespace | Package | Allowed owlbear imports | Source |
|-----------|---------|------------------------|--------|
| `owlbear_browser` | serve/browser | `set()` | No workspace deps |
| `owlbear_cockpit` | serve/cockpit | `{owlbear_kanban}` | pyproject.toml workspace dep |
| `owlbear_kanban` | serve/kanban | `set()` | No workspace deps |
| `owlbear_knowledge` | serve/knowledge | `set()` | No workspace deps |
| `owlbear_mcp_browser` | serve/mcp-browser | `{owlbear_browser}` | pyproject.toml workspace dep |
| `owlbear_mcp_kanban` | serve/mcp-kanban | `{owlbear_kanban}` | pyproject.toml workspace dep |
| `owlbear_mcp_knowledge` | serve/mcp-knowledge | `{owlbear_knowledge}` | pyproject.toml workspace dep |
| `owlbear_mcp_memory` | serve/mcp-memory | `set()` | No workspace deps |
| `owlbear` | serve/orchestrator | `{owlbear_orchestrator}` | Co-packaged (same wheel) |
| `owlbear_orchestrator` | serve/orchestrator | `{owlbear}` | Co-packaged (same wheel) |
| `owlbear_tools` | serve/tools | `set()` | No workspace deps |

**Orchestrator co-packaging edge case:** `serve/orchestrator/` ships two namespaces (`owlbear`, `owlbear_orchestrator`) in one wheel. They are NOT linked via `[tool.uv.sources]` — they're co-packaged via `[tool.hatch.build.targets.wheel] packages = [...]`. Mutual imports must be explicitly allowed in ALLOWED_IMPORTS.

**TYPE_CHECKING import policy:** Scan ALL imports including those inside `if TYPE_CHECKING:` blocks. Runtime-vs-typecheck distinction is irrelevant for boundary enforcement — a TYPE_CHECKING import still creates a coupling contract. Document this policy in the test module docstring (per `r-architecture-standards` requirement).

**Overlap with `tests/test_cockpit_boundary.py`:** That test enforces name-level forbidden imports (specific functions like `claim_task`). This task enforces namespace-level allowed imports. They are complementary — the cockpit boundary test remains valid. No changes needed to it.

**Reference pattern:** `tests/test_cockpit_boundary.py` lines 26-44 (`_collect_forbidden_imports`) demonstrates the working AST scan pattern against `serve/` layout.

### Challenge Results
- Challenger: reconsider (0.60 confidence)
- Concerns: (C1) stale research doc data, (C2) unspecified ALLOWED_IMPORTS values, (C3) overlap with cockpit boundary test, (C4) TYPE_CHECKING policy
- Architect response: accepted — all four concerns addressed via builder notes above. Dependency map specified explicitly. TYPE_CHECKING policy defined. Overlap documented as complementary.

### Verdict: APPROVE (with refinements)
### Action Taken: Approved to todo with builder notes specifying the complete 11-namespace dependency map, orchestrator co-packaging edge case, TYPE_CHECKING policy, and ground-truth source references. Research doc flagged as data-stale.
[[2026-04-20]]
## Test-Writer Notes
- Test file: tests/test_package_boundary.py
- Classes: `TestFromAC_AllowedImportsSchema` (4 tests), `TestFromAC_CrossImportEnforcement` (6 tests)
- Tests per category: happy 2, edge 3, error 1, boundary 4
- Total: 10 tests, all PASS (restoration task — AC#5 requires no false positives on current codebase)
- ruff: clean
- commit: 2e8e63a4

**AC coverage:**
| AC | Tests |
|----|-------|
| AC#1: ALLOWED_IMPORTS dict[str,set[str]] exists | test_allowed_imports_is_dict, test_allowed_imports_values_are_sets |
| AC#2: all namespaces have an entry | test_allowed_imports_covers_all_discovered_namespaces |
| AC#3: AST scan detects violations | test_scan_detects_synthetic_from_import_violation, test_scan_detects_synthetic_bare_import_violation, test_scan_catches_type_checking_import_violation, test_scan_ignores_intra_namespace_imports, test_scan_allows_declared_cross_namespace_imports |
| AC#4: keys validated against discovered namespaces | test_allowed_imports_has_no_unknown_keys |
| AC#5: no false positives | test_no_undeclared_cross_namespace_imports |

**Note:** Task tagged `test`+`quality` (architect confirmed pass-through pattern); user explicitly requested test authoring so test file was written directly. Tests pass per AC#5 — this is a boundary guard restoration, not a RED-phase for new production code.
[[2026-04-20]]
## Builder Notes

**Status:** Verification pass — restoration task, no production code to write.

**Files changed:** None (test-writer committed `tests/test_package_boundary.py` at 2e8e63a4; builder role was GREEN verification only)

**Test results:**
- `tests/test_package_boundary.py`: 10/10 passed (all `TestFromAC_*` classes)
- Full suite (`tests/ serve/ -m "not api"`): 797 passed, 4 skipped, 6 pre-existing failures in `serve/mcp-knowledge/` (unrelated to #1038)

**Coverage:** N/A — test-only restoration task

**Lint:** `ruff check tests/test_package_boundary.py` — clean

**Evidence summary:**
- `TestFromAC_AllowedImportsSchema` (4 tests): PASS — dict structure, set values, namespace coverage, no unknown keys
- `TestFromAC_CrossImportEnforcement` (6 tests): PASS — current codebase clean, synthetic violations detected, TYPE_CHECKING blocks scanned, intra-namespace imports ignored, declared imports allowed
- ALLOWED_IMPORTS covers all 11 namespaces per architect's dependency map
- No regressions introduced
[[2026-04-20]]
## Review Evidence

### Test Results
pytest: **10 passed, 0 failed** — quality-runner independent run confirmed.
ruff: **clean** — zero lint violations.
Coverage: N/A — test-only restoration task.

### AC Compliance Table

| AC Line | Evidence | Mapped Test(s) | Would Fail If Violated? | Status |
|---------|----------|----------------|------------------------|--------|
| AC#1: `ALLOWED_IMPORTS: dict[str, set[str]]` exists | `test_package_boundary.py:27–41` — `ALLOWED_IMPORTS` declared with correct type | `test_allowed_imports_is_dict`, `test_allowed_imports_values_are_sets` | Yes — `isinstance` checks are specific | PASS |
| AC#2: all `serve/*/src/` namespaces have entry | `_discover_namespaces` scans disk; test fails on `missing = discovered - set(ALLOWED_IMPORTS)` | `test_allowed_imports_covers_all_discovered_namespaces` | Yes — set difference assertion fires if namespace added without entry | PASS |
| AC#3: AST scan detects violations | Synthetic file tests in `tmp_path`; cover `from X import Y`, bare `import X`, and `TYPE_CHECKING` blocks | `test_scan_detects_synthetic_from_import_violation`, `test_scan_detects_synthetic_bare_import_violation`, `test_scan_catches_type_checking_import_violation`, `test_scan_ignores_intra_namespace_imports`, `test_scan_allows_declared_cross_namespace_imports` | Yes — concrete `any(ns == ... and imported == ...)` assertions | PASS |
| AC#4: keys validated against discovered namespaces | `extra = set(ALLOWED_IMPORTS) - discovered`; fails on ghost keys | `test_allowed_imports_has_no_unknown_keys` | Yes — assertion fires on undiscovered keys | PASS |
| AC#5: no false positives on current codebase | `_collect_violations` run on real `serve/` — 0 violations found | `test_no_undeclared_cross_namespace_imports` | Yes — `pytest.fail` called on any violation | PASS |

### Pass 1 Findings

**5.0 Test-Writer Audit:** All 5 AC lines covered. No MISSING or LAX entries.

**5.1 Security:** Test-only file. `ast.parse` called on bounded `serve/` source tree (no user input). `tmp_path` managed by pytest. No path traversal, injection, or hardcoded secrets. PASS.

**5.2 Test Integrity:** Builder made no changes to `TestFromAC_*` tests (test-writer committed; builder was verification-only). No modifications to assess.

**5.3 Test Quality:** STRONG across all dimensions.
- Assertion specificity: STRONG — `any(ns == "owlbear_tools" and imported == "owlbear_kanban" ...)` pattern; no lazy `assert result`.
- Negative coverage: STRONG — synthetic violation tests confirm both import forms and TYPE_CHECKING path.
- Mutation resistance: STRONG — each helper branch tested; removing `ast.ImportFrom` handling breaks two tests, removing `ast.Import` handling breaks one, removing self-import exclusion breaks one, removing allowed-import exclusion breaks one.
- Test independence: STRONG — synthetic tests use `tmp_path` (fresh per test); schema tests access module-level constant only.
- Descriptive names: STRONG — all names unambiguous.

**5.4 Data Safety:** No mutable shared state, no LLM output, no multi-step writes. PASS.

**5.5 Implementation-Aware Gap Analysis:** `_owlbear_root(None)` guard handles relative imports (`from . import X` → `module=None`). This edge case is correctly handled and implicitly validated by the real-codebase scan (which contains relative imports). No untested significant branches.

**5.6 Necessity Check:** N/A — restoration task, no new dependencies.

**5.7 Builder Process Quality:** CLEAN — single pass, no loop pattern.

### Deductions
None.

### Verdict
Confidence: **.97 → PASS**
[[2026-04-20]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Test-only restoration. `r-architecture-standards` lines 27 and 111 already reference `test_package_boundary.py` correctly — conventions unchanged |
| 2 | Module docstrings | Yes | Verified | `tests/test_package_boundary.py` lines 1–15: module docstring covers purpose + TYPE_CHECKING policy as required by architect builder notes |
| 3 | External attribution | No | N/A | AST pattern from deer-flow already attributed in `.owlbear/sources/overview.md` line 679 (added by task #429) |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research doc produced for #1038; existing `.owlbear/research/ast-package-boundary-enforcement.md` exists and is referenced in task Context |

### Files Updated
None — no documentation gaps found.

### Scratch Files
None found matching `.owlbear/scratch/1038-*`.
[[2026-04-20]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC#1: `ALLOWED_IMPORTS: dict[str, set[str]]` exists | `test_package_boundary.py:27–41` — 11-entry dict with set values; `test_allowed_imports_is_dict`, `test_allowed_imports_values_are_sets` | PASS |
| AC#2: all namespaces have entry | `test_allowed_imports_covers_all_discovered_namespaces` — `_discover_namespaces()` scans `serve/*/src/`, set-difference assertion | PASS |
| AC#3: AST scan detects violations | 5 synthetic tests: from-import, bare-import, TYPE_CHECKING, intra-namespace exclusion, declared-import allowance; + real codebase scan | PASS |
| AC#4: keys validated against discovered | `test_allowed_imports_has_no_unknown_keys` — `extra = set(ALLOWED_IMPORTS) - discovered` assertion | PASS |
| AC#5: no false positives | `test_no_undeclared_cross_namespace_imports` — 0 violations on current codebase | PASS |

### Test Results
- pytest: 797 passed, 6 failed (all in `serve/mcp-knowledge/` — pre-existing, unrelated to #1038), 4 skipped
- ruff: clean

### Architect Quality: 5/5
Specific, complete, clean implementation path. Builder notes provided grounded 11-namespace dependency map from `pyproject.toml` sources, orchestrator co-packaging edge case, TYPE_CHECKING policy, and overlap analysis. No improvisation needed.

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive