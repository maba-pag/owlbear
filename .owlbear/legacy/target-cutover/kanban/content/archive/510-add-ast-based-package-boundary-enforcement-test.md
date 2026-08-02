---
id: 510
title: Add AST-based package boundary enforcement test
status: archived
priority: medium
created: 2026-04-01 00:12:37.333486+02:00
updated: 2026-04-01 13:07:10.090548+02:00
started: 2026-04-01 13:07:09.643795+02:00
completed: 2026-04-01 13:07:09.643795+02:00
tags:
- scope:core
- phase-2
- type:test
- tooling
class: standard
archival_reason: completed
archival_refs: []
---

## Context
Adopt deer-flow's harness/app boundary enforcement pattern: an AST-based test (~60 LOC) that scans all Python files in each OwlBear package and fails if illegal cross-package imports are found.

See docs/research/ast-package-boundary-enforcement.md for full findings.
Source: deer-flow backend/tests/test_harness_boundary.py (MIT).
Decision request: docs/decisions/resolved/429-deer-flow-patterns-adoption.md (approved, option A).

## Acceptance Criteria
- [ ] Test file at `tests/test_package_boundary.py`
- [ ] Defines `ALLOWED_IMPORTS: dict[str, set[str]]` constant mapping each package namespace to its allowed owlbear-namespace imports:
  - `owlbear_knowledge`: `{}` (no owlbear deps)
  - `owlbear_mcp_kanban`: `{}` (standalone)
  - `owlbear_mcp_knowledge`: `{owlbear_knowledge}`
  - `owlbear_mcp_project`: `{}` (standalone)
  - `owlbear`: `{owlbear_orchestrator}` (co-shipped wheel)
  - `owlbear_orchestrator`: `{owlbear}` (co-shipped wheel)
  - `owlbear_voice`: `{}` (standalone)
- [ ] Self-imports (a namespace importing from itself) are always allowed and excluded from boundary checks
- [ ] Uses `ast.parse` + `ast.walk` to collect `Import`/`ImportFrom` nodes from each `.py` file under `packages/*/src/` only (not tests/)
- [ ] Extracts the root module name (first dot-separated component of the import path) and checks membership in the ALLOWED_IMPORTS key set -- exact match, not prefix
- [ ] Fails with clear error message listing file path and violating import if any package imports a disallowed peer namespace
- [ ] Manifest guard: ALLOWED_IMPORTS keys must exactly equal the set of discovered namespace directories under `packages/*/src/` -- bidirectional check catches both added and removed packages
- [ ] Passes in current codebase (no existing violations)
- [ ] Documents the dependency rules and TYPE_CHECKING import policy in a module-level docstring

[[2026-04-01]] Wed 03:21
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** docs/decisions/resolved/429-deer-flow-patterns-adoption.md approved: true (option A)

### AC Assessment
Refined all 5 original AC lines. Added 4 new lines addressing: self-import exclusion, exact root-module matching, bidirectional manifest guard, scan scope restriction. Total: 9 precise, mechanically verifiable AC lines.

### Architecture Notes
Zero external deps (stdlib ast module). Follows existing AST scan pattern in tests/test_knowledge_vector_pipeline_32.py. 7 namespaces across 6 packages; orchestrator ships owlbear + owlbear_orchestrator. Dependency graph verified against pyproject.toml. TYPE_CHECKING imports caught by ast.walk (correct behavior, documented in AC).

### Changes Made
Refined AC body with 9 verifiable lines. Fixed tag scope:agents to scope:core. Added test tag for pass-through.

### Dependencies
None. Standalone stdlib-only test. No depends_on needed.

### Challenge Results
Challenger: reconsider (.72). Accepted C1 (prefix wording), C2 (self-import), C3 (manifest guard). C4 (TYPE_CHECKING) in docstring AC. All wording fixes. Revised confidence: .92

[[2026-04-01]] Wed 04:23
## Test-Writer Notes
- Non-implementation task (tagged type:test) — no tests applicable.
- Task deliverable IS the test file itself (tests/test_package_boundary.py).
- Passing through to builder.

[[2026-04-01]] Wed 06:39
## Builder Notes
- Files changed: tests/test_package_boundary.py (154 lines, new file)
- Tests: 2 passed (manifest guard + boundary check)
- Lint: ruff clean
- Evidence: 2 passed in 0.20s
- Fixes applied: None - test file is the deliverable (non-impl pass-through)

[[2026-04-01]] Wed 13:06
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Test file at tests/test_package_boundary.py | File exists, 154 lines, committed (660838d) | PASS |
| ALLOWED_IMPORTS dict with 7 namespaces | Lines 37-45, all 7 namespaces match AC exactly | PASS |
| Self-imports excluded from boundary checks | Line 131: if root == ns_name: continue | PASS |
| ast.parse + ast.walk for Import/ImportFrom | Lines 75-88, _owlbear_import_roots() | PASS |
| Root module extraction, exact match not prefix | Lines 80/84-85, frozenset membership | PASS |
| Clear error message with file path and import | Lines 134-138, f-string with rel path + namespace | PASS |
| Manifest guard bidirectional check | Lines 96-113, missing_from_map + extra_in_map | PASS |
| Passes in current codebase | 2 passed in 0.12s | PASS |
| Module-level docstring with rules + TYPE_CHECKING | Lines 1-28, covers all 3 sections | PASS |

### Test Results
- pytest (task scope): 2 passed in 0.12s
- pytest (full suite): 235 pre-existing failures, 2488 passed (unrelated to task)
- ruff: All checks passed

### AC Quality Score: 5
AC was highly specific: 9 mechanically verifiable lines, led to clean implementation with zero builder improvisation. Architect refined well from original 5 lines.

### Deduction breakdown
- Start: 1.00
- Missing reviewer evidence section: -.02
- Missing docs gate section: -.02

### Confidence: .96
### Action: archive

[[2026-04-01]] Wed 13:07
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Test file at tests/test_package_boundary.py | File exists, 154 lines, committed (660838d) | PASS |
| ALLOWED_IMPORTS dict with 7 namespaces | Lines 37-45, all 7 namespaces match AC exactly | PASS |
| Self-imports excluded from boundary checks | Line 131: if root == ns_name: continue | PASS |
| ast.parse + ast.walk for Import/ImportFrom | Lines 75-88, _owlbear_import_roots() | PASS |
| Root module extraction, exact match not prefix | Lines 80/84-85, frozenset membership | PASS |
| Clear error message with file path and import | Lines 134-138, f-string with rel path + namespace | PASS |
| Manifest guard bidirectional check | Lines 96-113, missing_from_map + extra_in_map | PASS |
| Passes in current codebase | 2 passed in 0.12s | PASS |
| Module-level docstring with rules + TYPE_CHECKING | Lines 1-28, covers all 3 sections | PASS |

### Test Results
- pytest (task scope): 2 passed in 0.12s
- pytest (full suite): 235 pre-existing failures, 2488 passed (unrelated to task)
- ruff: All checks passed

### AC Quality Score: 5
AC was highly specific: 9 mechanically verifiable lines, led to clean implementation with zero builder improvisation. Architect refined well from original 5 lines.

### Deduction breakdown
- Start: 1.00
- Missing reviewer evidence section: -.02
- Missing docs gate section: -.02

### Confidence: .96
### Action: archive
