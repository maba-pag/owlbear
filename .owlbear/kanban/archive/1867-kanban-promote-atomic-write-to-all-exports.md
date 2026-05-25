---
id: 1867
title: 'Kanban: promote atomic_write to __all__ exports'
status: archived
priority: someday
created: 2026-05-25T00:06:59.338718+02:00
updated: 2026-05-25T03:22:46.523906+02:00
tags:
  - scope:kanban
  - boundary-audit
parent:
depends_on: []
ac:
  - '"atomic_write" is a member of owlbear_kanban.__init__.__all__'
  - from owlbear_kanban import atomic_write resolves to the same callable as 
    from owlbear_kanban.storage_io import atomic_write
  - No changes to pyproject.toml [project.dependencies] or [tool.uv.sources] 
    sections
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Add `atomic_write` from `owlbear_kanban.storage_io` to the package's `__init__.__all__` exports. Cockpit's ideas route and potentially other consumers use this generic crash-safe file-write utility. Currently it's imported directly from the submodule — formally exporting it makes the dependency contract explicit.

Ref: .owlbear/research/cockpit-api-boundary-audit.md — Finding 3

[[2026-05-25T00:19:04+02:00]]
## Research
- Research doc: .owlbear/research/cockpit-api-boundary-audit.md (Finding 3, from #1849)
- Sources: 3 studied (kanban __init__.py, storage_io.py, all consumers via grep), all high-relevance
- Recommendation: Promote atomic_write to __all__ (confidence: 0.95)
- Rationale: Trivial export-hygiene change. Single generic utility, one external consumer (cockpit ideas route), zero domain coupling. Standard Python __all__ pattern. No challenge needed (trivial scope).
- Implementation: Add `from owlbear_kanban.storage_io import atomic_write` and `"atomic_write"` to __all__ in __init__.py (2-line diff).
- AC drafted with 4 criteria.

[[2026-05-25T00:41:22+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Export-hygiene only — adds one symbol to __all__ |
| Interface clarity | PASS | AC specifies exact membership and import equivalence |
| Dependency correctness | PASS | No deps; atomic_write is internal to owlbear_kanban |
| Module layering | PASS | __init__ re-exports from submodule — standard Python pattern |
| TDD compliance | PASS | smoke bundle; test-writer writes import assertions |
| KISS/YAGNI | PASS | 2-line diff, minimal possible change |
| Premise challenge | PASS | 1 external consumer (cockpit ideas) imports from submodule; formalizing is legitimate |
| Pattern consistency | PASS | Matches existing __init__.py pattern (10 symbols already exported) |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Kanban package only |

### Failure Mode Map
N/A — adding to __all__ introduces no new failure modes.

### Design Diverge
- Trigger: skipped — single obvious approach (add import + __all__ entry)

### Challenge Results
- Challenger: reconsider (0.63)
- Findings: AC3 (unchanged import path) tautological; AC4 (no new deps) vague; existing test_init_exports.py is the real contract surface
- Architect response: accepted AC refinement — dropped tautological AC3, replaced vague AC4 with concrete pyproject.toml constraint, kept 3 precise lines

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: smoke
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC from 4 to 3 verifiable lines, set proof_bundle=smoke, advanced to todo.

[[2026-05-25T00:53:15+02:00]]
## Test-Writer Notes
- Test file: tests/test_kanban_1867.py
- Classes: TestFromAC_AtomicWriteExport
- Tests per category: happy 2, edge 0, error 0, boundary 0 (smoke bundle)
- Total: 3 tests; 2 FAIL (AC1, AC2), 1 PASS (AC3 regression guard)
- ruff: clean
- AC coverage:
  | AC | Test | Result |
  |----|------|--------|
  | AC1: atomic_write in __all__ | test_atomic_write_in_dunder_all | FAIL (AssertionError) |
  | AC2: same callable as storage_io | test_atomic_write_same_callable_as_storage_io | FAIL (AssertionError) |
  | AC3: no pyproject.toml dep changes | test_kanban_pyproject_dependencies_unchanged | PASS (regression guard — no-change constraint passes before impl by design) |

[[2026-05-25T01:09:21+02:00]]
## Builder Notes
- Attempted implementation: added `atomic_write` export in `serve/kanban/src/owlbear_kanban/__init__.py` (import + `__all__` entry), then rolled back due durable test contract mismatch.
- RED verification (pre-change): `tests/test_kanban_1867.py` -> 1 passed, 2 failed (expected AC1/AC2).
- GREEN attempt evidence: `tests/test_kanban_1867.py` -> 3 passed, lint clean.
- Durable regression check (module-level): `tests/test_init_exports.py` introduced a new failure tied to this AC (`test_dunder_all_new_additions_are_exactly_five_symbols`) because it hard-codes prior exact-additions contract.
- Existing unrelated durable failures also present in same file (missing `tests/test_init_exports_1213.py`).
- Rollback applied: source change reverted; task-scoped tests returned to RED baseline (1 passed, 2 failed), lint clean.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Update durable export contract tests to allow/reflect `atomic_write` promotion in package `__all__`, then re-run and keep contract assertions consistent with current AC | tests/test_init_exports.py | `test_dunder_all_new_additions_are_exactly_five_symbols` fails when AC1/AC2 are implemented |
| 2 | test-writer | Repair or replace stale references to removed file `tests/test_init_exports_1213.py` in durable tests so baseline export checks are executable | tests/test_init_exports.py | FileNotFoundError in `test_positive_pick_dispatchable_test_removed`, `test_negative_assertion_present`, `test_existing_set_pruned_of_pick_dispatchable` |
| 3 | test-writer | Keep task-scoped AC tests for #1867 as-is (they correctly capture required behavior) and re-advance once durable contract is coherent | tests/test_kanban_1867.py | Pre-change RED and attempted GREEN runs confirm AC tests are valid |

[[2026-05-25T01:21:39+02:00]]
## Test-Writer Notes
- Retry: addressed builder's 2 blockers in tests/test_init_exports.py
- Test file: tests/test_kanban_1867.py (unchanged — AC tests valid per builder confirmation)
- Changes to tests/test_init_exports.py:
  1. Renamed `test_dunder_all_new_additions_are_exactly_five_symbols` → `test_dunder_all_new_additions_are_exactly_six_symbols`; added `"atomic_write"` to `expected_new` set — now FAILS (RED) until AC1 lands
  2. Repaired 3 stale references: `test_init_exports_1213.py` → `test_init_exports.py` (file was merged; redirected all 3 TestFileSurgery tests); `test_positive_pick_dispatchable_test_removed` rewritten with line-level startswith check to avoid self-referential string match — all 3 now PASS (infrastructure repair, not new RED tests)
- RED verification: 3 failing, 29 passing, ruff clean
  - tests/test_kanban_1867.py::TestFromAC_AtomicWriteExport::test_atomic_write_in_dunder_all — FAIL (AC1)
  - tests/test_kanban_1867.py::TestFromAC_AtomicWriteExport::test_atomic_write_same_callable_as_storage_io — FAIL (AC2)
  - tests/test_init_exports.py::TestFromAC_KanbanInitExports::test_dunder_all_new_additions_are_exactly_six_symbols — FAIL (blocks impl until atomic_write in __all__)
- AC coverage:
  | AC | Test | Result |
  |----|------|--------|
  | AC1: atomic_write in __all__ | test_atomic_write_in_dunder_all | FAIL |
  | AC1: exact count contract | test_dunder_all_new_additions_are_exactly_six_symbols | FAIL |
  | AC2: same callable as storage_io | test_atomic_write_same_callable_as_storage_io | FAIL |
  | AC3: pyproject.toml unchanged | test_kanban_pyproject_dependencies_unchanged | PASS (regression guard) |

[[2026-05-25T01:37:49+02:00]]
## Builder Notes
- Implementation: exported `atomic_write` at package root in `serve/kanban/src/owlbear_kanban/__init__.py` by adding import from `owlbear_kanban.storage_io` and adding `"atomic_write"` to `__all__`.
- Files changed: `serve/kanban/src/owlbear_kanban/__init__.py` only.
- Approach: minimal export-hygiene change to satisfy AC1/AC2 with no dependency or API-surface expansion beyond explicit root re-export.
- RED verification (quality-runner, pre-change): 29 passed / 3 failed / 0 skipped; failures were exactly:
  - `tests/test_kanban_1867.py::TestFromAC_AtomicWriteExport::test_atomic_write_in_dunder_all`
  - `tests/test_kanban_1867.py::TestFromAC_AtomicWriteExport::test_atomic_write_same_callable_as_storage_io`
  - `tests/test_init_exports.py::TestFromAC_KanbanInitExports::test_dunder_all_new_additions_are_exactly_six_symbols`
- GREEN verification (quality-runner, final): 32 passed / 0 failed / 0 skipped.
  - Test scope: `tests/test_kanban_1867.py`, `tests/test_init_exports.py`
- Coverage: `owlbear_kanban.__init__` 100% (touched module).
- Lint: clean (ruff clean on source + scoped test files).
- Fixes applied during verification: corrected `__all__` ordering to satisfy `RUF022` (`atomic_write` sorted after `WorkSession` per isort-style ordering).
- AC evidence summary:
  - AC1 (`"atomic_write"` in `__all__`): PASS
  - AC2 (root import resolves to same callable as submodule): PASS
  - AC3 (no pyproject dependency/source changes): PASS via existing regression guard test

[[2026-05-25T02:08:49+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1867 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence is internally consistent with the current tree: task notes report `serve/kanban/src/owlbear_kanban/__init__.py` as the only changed file and a final scoped result of 32 passed / 0 failed / 0 skipped with clean lint and 100% coverage for `owlbear_kanban.__init__` (.owlbear/kanban/tasks/1867-kanban-promote-atomic-write-to-all-exports.md:127-138).
- AC evidence map:
| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1: `"atomic_write"` is a member of `owlbear_kanban.__init__.__all__` | `serve/kanban/src/owlbear_kanban/__init__.py:18` imports `atomic_write`; `serve/kanban/src/owlbear_kanban/__init__.py:31` includes `"atomic_write"` in `__all__` | `tests/test_kanban_1867.py:26-30` asserts direct membership; `tests/test_init_exports.py:52-71` asserts the exact added export set includes `atomic_write` | PASS |
| AC2: `from owlbear_kanban import atomic_write` resolves to the same callable as `from owlbear_kanban.storage_io import atomic_write` | `serve/kanban/src/owlbear_kanban/__init__.py:18` re-exports the symbol directly from `owlbear_kanban.storage_io` | `tests/test_kanban_1867.py:34-42` asserts object identity (`pkg_fn is submod.atomic_write`) | PASS |
| AC3: No changes to `pyproject.toml` `[project.dependencies]` or `[tool.uv.sources]` sections | Current `serve/kanban/pyproject.toml:6` matches the baseline dependency set and the file contains no `[tool.uv]` section; builder notes report no pyproject file in scope (.owlbear/kanban/tasks/1867-kanban-promote-atomic-write-to-all-exports.md:127) | `tests/test_kanban_1867.py:46-66` asserts the exact dependency baseline and absence of `tool.uv` | PASS |
- Proof sufficiency: AC1 is proven by exact `__all__` membership assertions, AC2 by identity comparison rather than mere presence, and AC3 by a concrete manifest baseline plus absence check for `tool.uv`. These tests would fail on the reverted pre-fix state described in the builder notes.
- Safety & security: not a security-sensitive change surface; no new input, storage, auth, or dependency risks observed.
- Diagnostics spot-check: no editor errors in `serve/kanban/src/owlbear_kanban/__init__.py`, `tests/test_kanban_1867.py`, or `tests/test_init_exports.py`.

## Observations
- No non-blocking findings.

[[2026-05-25T02:23:07+02:00]]
## Docs Gate

**Verdict: PASS → done**

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | FIXED | `serve/kanban/README.md` had no mention of `atomic_write` despite it being the task's sole purpose (making the public contract explicit). Added a "Utilities" subsection with signature, description, and usage example. Layer 1 (grep): no removed symbols. Layer 2 (editorial): no contradictions; new entry consistent with existing style. |
| 2. External Attribution | N/A | Pure internal export-hygiene; no external sources used. |
| 3. Research Doc | PASS | `.owlbear/research/cockpit-api-boundary-audit.md` (Finding 3) referenced at top of task body and in ## Research section. |
| 4. Deletion Detection | N/A | No symbols removed; no orphaned references introduced. |

### Files Updated
- `serve/kanban/README.md` — added "### Utilities" subsection documenting `atomic_write` signature and usage.

### Scratch Cleanup
- No `1867-*` scratch files created during this gate pass.

[[2026-05-25T03:22:46+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 7191 passed, 25 skipped; failures (test_cockpit_view, test_server, test_engine_requests_1852, MemoryTab_1672) all pre-existing RED tests from unrelated in-progress tasks
- kanban-domain task-scoped tests (test_kanban_1867.py, test_init_exports.py): all PASS
- lint violations in serve/knowledge/ only (unrelated domain)
- regression verdict: PASS (no regressions attributable to #1867)

### Intent Verification
- scope alignment: PASS (single file changed: serve/kanban/src/owlbear_kanban/__init__.py, squarely in kanban domain)
- purpose match: PASS (adds atomic_write to __all__ exports, matching stated task intent exactly)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
AC refined from 4 to 3 lines after challenger feedback. All 3 AC lines are specific, testable, and produced a clean implementation path. Challenger engagement improved final AC quality.

### Commit Integrity
- builder commit: PASS (2439e1fc feat: export atomic_write from kanban root)
- test-writer commits: PASS (5b56432d, a99ab8ed)
- doc-writer commit: MISSING (serve/kanban/README.md change is uncommitted in working tree)
- process concern: doc-writer advanced to done without committing its README deliverable

### Review Evidence
Present and detailed. PASS verdict with full AC-to-code mapping and proof sufficiency narrative.

### Deduction Breakdown
- Uncommitted doc-writer deliverable (evidence integrity concern): -0.05

### Confidence: 0.95
### Action: archive
