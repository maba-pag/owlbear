---
id: 1174
title: Delete config_loader.save_config and _merge_into dead code
status: archived
priority: medium
created: 2026-04-28T23:07:10.988412+00:00
updated: 2026-04-29T04:29:43.636082+00:00
tags:
- scope:kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

config_loader.save_config (L56-75) and _merge_into (L100-130) in serve/kanban/src/owlbear_kanban/config_loader.py are dead code — zero callers across the entire codebase, zero test coverage, 3 latent bugs (no atomic_write, no frozenset handling, re-emits legacy keys). Delete both functions. Keep config_loader.load_config (actively used).

## Acceptance Criteria

1. `config_loader.save_config` and `_merge_into` are deleted from `config_loader.py` (td:1)
2. `config_loader.load_config` still works — existing regression tests pass (td:1)
3. No new test failures introduced by the deletion — task-scoped suite green and no regressions in `serve/kanban/` test surface (td:0)
4. grep confirms no remaining code references to deleted functions in `config_loader.py` source (td:1)

## Research

- Research doc: .owlbear/research/1171-config-write-path-audit.md (parent task #1171, §3 "Critical Finding" + §4 Step 1)
- Sources: 8 studied by parent research, all internal (config_loader.py, storage.py, engine.py, tests). Validation pass confirmed findings current.
- Recommendation: Delete save_config (L56-75) and_merge_into (L100-130) from config_loader.py. Also remove CommentedMap/CommentedSeq import (L15) — only used by dead code, not by _to_plain at runtime. Update module docstring to remove save_config reference. Keep load_config, _validate_claim_timeout,_to_plain. (confidence: .95)
- Follow-up tasks created: none (implementation is straightforward, no additional decomposition needed)
- Decision requests: none (T1 — autonomous dead-code deletion)

## Verification Evidence

- `from owlbear_kanban.config_loader import.*save_config` → 0 matches
- `from owlbear_kanban.config_loader import.*_merge_into` → 0 matches
- `config_loader.save_config` → 0 matches (outside task/research docs)
- `config_loader._merge_into` → 0 matches (outside task/research docs)
- Live consumers of config_loader module: engine.py (load_config), storage.py (load_config,_validate_claim_timeout), 2 test files (load_config)
- CommentedMap/CommentedSeq import removable: _to_plain uses isinstance(obj, dict/list) not CommentedMap/CommentedSeq
[[2026-04-29]]

## Architecture Review (re-review after reviewer rejection)

### Reason for Return

Reviewer rejected: (1) live tree still contains dead code (builder commit didn't persist), (2) AC3 "All existing tests pass" was unsatisfiable (107 pre-existing failures).

### AC Refinement

- AC3 rewritten: "All existing tests pass" → "No new test failures introduced by the deletion — task-scoped suite green and no regressions in `serve/kanban/` test surface" (td:0)
- AC1, AC2, AC4 unchanged — already precise and verifiable

### Evaluation (unchanged from prior cycle)

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Delete two dead functions + unused import from one module |
| Interface clarity | PASS | AC specifies exact functions and verification method |
| Dependency correctness | PASS | No dependencies needed |
| Module layering | PASS | No new imports or dependency changes |
| TDD compliance | PASS | Test file already exists from prior cycle |
| KISS/YAGNI | PASS | Pure dead-code removal |
| Premise challenge | PASS | Zero callers confirmed by grep |
| Pattern consistency | PASS | Standard deletion pattern |
| Security surface | PASS | Removal only |
| Single domain | PASS | scope:kanban only |

### Challenge Results

- Challenger: SKIPPED — REFINE verdict (optional); prior cycle challenged and architect overrode with sound rationale

### Test Depth

- Max depth: 1
- Test-writer: PROCEED (existing test file covers AC; builder re-applies deletion)

### Verdict: REFINE → APPROVE

### Action Taken: Rewrote AC3 to be satisfiable (scoped regression instead of full-workspace-green), preserved existing test file, advanced to todo for re-implementation

[[2026-04-29]]

## Test-Writer Notes

- Test file: tests/test_config_loader_1174.py (pre-existing from prior cycle, already committed)
- Classes: TestFromAC_ConfigLoaderCleanup, TestFromAC_LoadConfigRegression
- Tests per category: happy 3, edge 0, error 1, boundary 0
- Total: 7 tests — 4 FAIL (AC1+AC4: deletion not yet applied), 3 PASS (AC2 regression guards — expected in RED; load_config already works)
- ruff: clean
- AC coverage:

  | AC | Tests | Status |
  |----|-------|--------|
  | AC1: save_config +_merge_into deleted | test_save_config_not_in_module_attrs, test_merge_into_not_in_module_attrs | FAIL (RED) |
  | AC2: load_config regression guard | test_load_config_returns_board_config, test_load_config_statuses_parsed, test_load_config_raises_on_missing_file | PASS (regression guards pass in RED by design) |
  | AC3: no new failures (td:0) | — | skipped |
  | AC4: no source references | test_source_has_no_save_config_reference, test_source_has_no_merge_into_reference | FAIL (RED) |

[[2026-04-29]]

## Builder Notes

- Implementation: removed `save_config` and `_merge_into` from `serve/kanban/src/owlbear_kanban/config_loader.py`; removed now-unused `CommentedMap`/`CommentedSeq` imports; updated module docstring to remove `save_config` mention.
- Tests (task-scoped): `tests/test_config_loader_1174.py` -> 7 passed, 0 failed.
- Coverage: `owlbear_kanban.config_loader` 100% in scoped verification.
- ruff (scoped to changed files): clean.
- AC4 evidence: source scan in `serve/kanban/src/owlbear_kanban/config_loader.py` shows zero `save_config`/`_merge_into` references.
- Broader regression context: `serve/kanban/tests/` run reports many pre-existing failures across unrelated suites; none reference deleted symbols or `config_loader` write-path functions.

- Reflection:
  - A broad package-level lint run can surface unrelated debt; rerunning lint scoped to changed files is necessary to gate task ownership correctly.
  - Dead-code deletions should also remove docstring/import residue, because AC4 source-string assertions check textual references, not just runtime attributes.
  - Running a broad regression suite is still useful as context even when td:0, but fail ownership must stay tied to direct-impact evidence.
[[2026-04-29]]

## Review Evidence

### Scope

- Reconstructed changed-file scope from builder notes and direct inspection: `serve/kanban/src/owlbear_kanban/config_loader.py` only.
- Independent caller scan found no live Python imports or qualified call sites for `config_loader.save_config` / `config_loader._merge_into`.

### Test Results

- pytest: 52 passed, 0 failed
- Per-file:
  - `tests/test_config_loader_1174.py`: 7 passed
  - `serve/kanban/tests/test_engine_storage.py`: 41 passed
  - `serve/kanban/tests/test_engine_crash_safety_1101.py`: 4 passed

### Lint

- ruff: clean
- Paths checked:
  - `serve/kanban/src/owlbear_kanban/config_loader.py`
  - `tests/test_config_loader_1174.py`

### Coverage

- `owlbear_kanban.config_loader`: 100% (23 statements, 0 missed)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|----------------|----------------------------|---------|
| 1. `config_loader.save_config` and `_merge_into` are deleted from `config_loader.py` | `tests/test_config_loader_1174.py::test_save_config_not_in_module_attrs`; `tests/test_config_loader_1174.py::test_merge_into_not_in_module_attrs` | Yes — either symbol reappearing as a module attribute fails immediately | COVERED |
| 2. `config_loader.load_config` still works — existing regression tests pass | `tests/test_config_loader_1174.py::test_load_config_returns_board_config`; `tests/test_config_loader_1174.py::test_load_config_statuses_parsed`; `tests/test_config_loader_1174.py::test_load_config_raises_on_missing_file` | Yes overall — the type-only smoke assertion is weak by itself, but the status parsing check, missing-file error check, and existing load-path regression tests in `serve/kanban/tests/test_engine_storage.py` (claim-timeout + parse-duration path) fail on real load-path breakage | COVERED |
| 3. No new test failures introduced by the deletion — task-scoped suite green and no regressions in `serve/kanban/` test surface | td:0 — no task-local TestFromAC mapping required | N/A | N/A |
| 4. grep confirms no remaining code references to deleted functions in `config_loader.py` source | `tests/test_config_loader_1174.py::test_source_has_no_save_config_reference`; `tests/test_config_loader_1174.py::test_source_has_no_merge_into_reference` | Yes — any function definition, docstring mention, or call-site string in the module source fails | COVERED |

#### Security Review

- No issues found. This is a deletion-only change in `config_loader.py`; no new inputs, persistence paths, dependencies, or secret-bearing code were introduced.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_ConfigLoaderCleanup` (4 tests) | No divergence evidenced; current file still contains the same class and four methods recorded in Test-Writer notes | PRESERVED |
| `TestFromAC_LoadConfigRegression` (3 tests) | No divergence evidenced; current file still contains the same class and three methods recorded in Test-Writer notes | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | AC1/AC4 use exact absence checks. AC2 includes one broad `isinstance` smoke assertion, but the same AC also has concrete status parsing and missing-file assertions, plus passing existing load-path regressions in `serve/kanban/tests/test_engine_storage.py`. |
| Negative/error-path coverage | ADEQUATE | Missing-file behavior is asserted in the task suite; invalid `claim_timeout` and parse-duration hook behavior are exercised by `serve/kanban/tests/test_engine_storage.py`. |
| Manual mutation reasoning | ADEQUATE | Reintroducing either deleted symbol or any textual residue in `config_loader.py` fails AC1/AC4 tests; breaking status parsing, missing-file handling, or eager claim-timeout validation fails the task or existing regression tests. |
| Test independence | STRONG | Tests use isolated `tmp_path` boards and do not share mutable state. |
| Descriptive test names | STRONG | Test names state the exact contract being exercised. |

#### Data Safety

- No issues found. The change removes dead code and narrows surface area.

#### Implementation-Aware Test Gap Analysis

- No significant gaps found for the touched module. The live module now exposes only `load_config`, `_validate_claim_timeout`, and `_to_plain`, and the scoped run reported 100% coverage for `owlbear_kanban.config_loader`.

#### Necessity Check

- Skipped. This is a dead-code deletion task with no new dependency, integration, or tool.

#### Builder Process Quality

- CLEAN. Task body shows a re-review after prior rejection, but no repeated same-approach builder loop is evidenced in the current cycle.

### Pass 2 — INFORMATIONAL

- `tests/test_config_loader_1174.py` still contains stale prose at the file docstring (`AC3: all existing tests pass`). The live task AC was refined to scoped regression evidence. No assertion depends on that prose, so this is non-blocking doc drift only.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 1. Delete `save_config` and `_merge_into` | `serve/kanban/src/owlbear_kanban/config_loader.py` now contains only `load_config` (line 25), `_validate_claim_timeout` (line 46), and `_to_plain` (line 58); task-local cleanup tests passed 2/2 | `test_save_config_not_in_module_attrs`; `test_merge_into_not_in_module_attrs` | PASS |
| 2. `load_config` still works | Task-local regression tests passed 3/3; existing `config_loader.load_config` regressions at `serve/kanban/tests/test_engine_storage.py` lines 1040, 1059, 1067 passed; existing engine crash-safety regressions using `load_config` passed in `serve/kanban/tests/test_engine_crash_safety_1101.py` lines 84, 144, 180, 207 | `test_load_config_returns_board_config`; `test_load_config_statuses_parsed`; `test_load_config_raises_on_missing_file` | PASS |
| 3. No new failures / no regressions in serve/kanban surface | Quality-runner: 52 passed, 0 failed across the task suite plus two existing `serve/kanban` regression files that exercise the surviving load path | td:0 | PASS |
| 4. No remaining code references in `config_loader.py` source | Exact grep on `serve/kanban/src/owlbear_kanban/config_loader.py` for `save_config|_merge_into` returned no matches; source-reference tests passed 2/2 | `test_source_has_no_save_config_reference`; `test_source_has_no_merge_into_reference` | PASS |

### Deductions

- `-0.02`: one task-local AC2 smoke assertion is type-only and would not, by itself, distinguish every wrong `BoardConfig` value.
- `-0.02`: stale AC3 prose remains in the task test file docstring after the task AC was refined.

### Verdict

- PASS -> docs
- Confidence: 0.96

### Action

- Advanced task to `docs`.

### Post-task Reflection

- Scoped regression evidence for deletion tasks is strongest when the task-local suite is paired with a small set of existing tests that exercise the surviving production entry point.
- Module-level coverage still mattered on this td:1 task; the green task subset alone would not have proved the touched module was fully exercised.
- Source-string assertions were useful here because they caught definition residue and docstring residue, not just runtime attribute presence.
[[2026-04-29]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | `serve/kanban/README.md`: no mention of `save_config` or `_merge_into`; no other IN-scope prose docs reference these deleted functions |
| 2 | Module docstrings | Yes | Updated | `config_loader.py` module docstring already accurate post-builder (no `save_config` mention). Stale AC3 description in `tests/test_config_loader_1174.py` module docstring corrected to match the refined AC3 wording |
| 3 | External attribution | No | N/A | Pure internal dead-code deletion; no external patterns used |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1171-config-write-path-audit.md` exists and is linked from task body |
| 5 | Diagram maintenance | Yes | Updated | `kanban.excalidraw` (`describes: serve/kanban/src/**`) and `mcp-topology.excalidraw` (`describes: serve/kanban/src/**`) — footer hash updated `aff6a392` → `cbb8ce6e` (date already 2026-04-29) |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | Deleted symbols are application code, not documentation. No IN-scope docs reference `save_config`/`_merge_into` |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/config_loader.py` | IN (docstrings) | Verified accurate — no action needed |
| `tests/test_config_loader_1174.py` | IN (docstrings) | Updated stale AC3 docstring |
| `share/diagrams/kanban.excalidraw` | IN (diagram describes match) | Footer hash updated |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram describes match) | Footer hash updated |

### Files Updated

- `tests/test_config_loader_1174.py` — corrected stale AC3 module docstring
- `share/diagrams/kanban.excalidraw` — footer: `Last verified: 2026-04-29 (cbb8ce6e)`
- `share/diagrams/mcp-topology.excalidraw` — footer: `Last verified: 2026-04-29 (cbb8ce6e)`
- Commit: `2de92740`

### Child Tasks Created

- None

### Scratch Files Cleaned

- None (no `1174-*` files found in `.owlbear/scratch/`)
[[2026-04-29]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. `save_config` and `_merge_into` deleted | `config_loader.py` contains only `load_config` (L26), `_validate_claim_timeout` (L47), `_to_plain` (L59); `test_save_config_not_in_module_attrs` + `test_merge_into_not_in_module_attrs` PASS | PASS |
| 2. `load_config` still works | `test_load_config_returns_board_config`, `test_load_config_statuses_parsed`, `test_load_config_raises_on_missing_file` all PASS; existing regressions in `serve/kanban/tests/` PASS | PASS |
| 3. No new failures / scoped regression | Full suite: 2855 passed, 109 failed (all pre-existing — ConfigError agent_map fixture issues in unrelated suites). Zero failures reference `config_loader` or deleted symbols | PASS |
| 4. No remaining code references | `config_loader.py` source has no `save_config` or `_merge_into` text; `test_source_has_no_save_config_reference` + `test_source_has_no_merge_into_reference` PASS | PASS |

### Test Results

- pytest (task-scoped): 7 passed, 0 failed
- pytest (full suite): 2855 passed, 109 failed, 4 skipped — 109 failures are pre-existing (unrelated modules)
- ruff: 4 pre-existing violations in unrelated packages; clean in task scope

### Architect Quality: 4/5

Original AC3 ("All existing tests pass") was unsatisfiable given 107 pre-existing failures. Architect self-corrected after reviewer rejection, refining to scoped regression evidence. Final AC is specific and verifiable. Pipeline self-healing worked correctly.

### Deduction Breakdown

- AC lines without evidence: 0 → no deduction
- Lint violations (task scope): 0 → no deduction
- AC quality ≤ 3: no (score 4) → no deduction
- Missing reviewer evidence: no (detailed, PASS) → no deduction
- Full-suite failures in task scope: 0 → no deduction

### Confidence: 1.00

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 88bb6930 | test | tests/test_config_loader_1174.py | #1174 |
| 7834d0be | refactor | serve/kanban/src/owlbear_kanban/config_loader.py | #1174 |
| f813c008 | refactor | serve/kanban/src/owlbear_kanban/config_loader.py | #1174 |
| 2de92740 | docs | tests/test_config_loader_1174.py, share/diagrams/*.excalidraw | #1174 |
