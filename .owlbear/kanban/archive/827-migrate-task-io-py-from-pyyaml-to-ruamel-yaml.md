---
id: 827
title: Migrate task_io.py from PyYAML to ruamel.yaml
status: archived
priority: nice-to-have
created: '2026-04-11T01:12:00.740638+00:00'
updated: '2026-04-14T23:41:39.891800+00:00'
tags:
- scope:kanban
- cleanup
parent: 798
depends_on:
- 818
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `task_io.py` in `serve/kanban/src/owlbear_kanban/` uses `ruamel.yaml` instead of `pyyaml`
- Custom `_NoTimestampLoader` replaced with ruamel.yaml equivalent (preserve timestamp strings as-is)
- `pyyaml` removed from `serve/kanban/pyproject.toml` deps
- All task I/O tests pass (round-trip fidelity, timestamp preservation, encoding)
- YAML output format unchanged (task files remain readable)

## Context

After #818 extracts the engine, `owlbear_kanban` has two YAML libraries: `ruamel.yaml` (config_loader) and `pyyaml` (task_io). Consolidating to `ruamel.yaml` reduces dependencies from 3 to 2.

Research finding from #818: `.owlbear/research/extract-engine-serve-kanban-818.md` §3.2
[[2026-04-12]]

## Research

- Research doc: .owlbear/research/migrate-task-io-pyyaml-to-ruamel-827.md
- Sources: 7 studied, 4 high-relevance (2 codebase, 2 web)
- Recommendation: Use `YAML(typ="rt")` with timestamp resolver stripping — same pattern as config_loader.py (confidence: 0.85)
- Follow-up tasks created: #843 (backlog — implement migration)
- Decision requests: none (T1 — autonomous refactor)

## Challenge Results

- Challenger: FALLBACK — subagent not available in researcher mode
- Confidence in original: 0.85
- Key risks: minor string quoting heuristic differences between PyYAML and ruamel.yaml; mitigated by 60+ existing tests
- Researcher response: N/A
[[2026-04-12]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One file migration (`task_io.py`) + one dep removal (`pyproject.toml`) — single concern |
| Interface clarity | PASS | `read_task`/`write_task` signatures unchanged; AC specifies exact library swap |
| Dependency correctness | PASS | `depends_on: [818]` correct — #818 extracts the engine; task_io.py lives there post-extraction. #818 is `in-progress` (reviewer FAILED, needs residual file deletion) — blocks dispatch, not approval |
| Module layering | PASS | Internal refactor within `owlbear_kanban` — no cross-package imports change |
| TDD compliance | PASS | 60+ existing tests cover round-trip fidelity, timestamp preservation, encoding, and live board integration. Behavior-preserving refactor with strong safety net. Test-writer will verify coverage and write pass-through |
| KISS/YAGNI | PASS | Consolidates 2 YAML libraries → 1. Net code delta ~0. No new abstractions |
| Premise challenge | PASS | Two YAML libraries in one package is unnecessary complexity. `config_loader.py` already proves the `ruamel.yaml` pattern works in this exact package |
| Pattern consistency | PASS | Adopts existing `_make_yaml()` + `_to_plain()` pattern from `config_loader.py` in same package |
| Security surface | PASS | `YAML(typ="rt")` is safe mode (no arbitrary code execution). Timestamp resolver stripping pattern already proven in `config_loader.py`. No new system boundaries |
| Single domain | PASS | `scope:kanban` only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| `read_task` YAML parse | Malformed frontmatter | `yaml.YAMLError` (ruamel equivalent) | Existing error propagation | Same as current — parse error surfaces |
| `write_task` dump | String quoting heuristic diff (PyYAML→ruamel) | N/A — semantic equivalence, cosmetic diff | 60+ round-trip tests catch data loss | Low — quoting style may differ but semantics preserved |

### Challenge Results

- Challenger: FALLBACK — no challenger subagent available in session
- Architect response: Proceeded with approval based on codebase evidence: proven pattern in same package, 60+ existing tests, T1 autonomous refactor

### Duplication Warning

**#843 duplicates #827.** The researcher created #843 as a "follow-up implementation" task, but #827 already has implementation-level AC. #843 should be archived/deleted as redundant. Both tasks have identical `depends_on: [818]`, `parent: 798`, and overlapping AC.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| `task_io.py` uses `ruamel.yaml` instead of `pyyaml` | Verifiable — single file, specific library | None |
| `_NoTimestampLoader` replaced with ruamel equivalent | Verifiable — class removal + `_make_yaml()` function | None |
| `pyyaml` removed from `serve/kanban/pyproject.toml` deps | Verifiable — specific file, specific dep | None |
| All task I/O tests pass | Verifiable — run existing 60+ test suite | None |
| YAML output format unchanged | Verifiable via existing round-trip + live board tests | None |

### Verdict: APPROVE

### Action Taken: Advanced to `todo`. Flagged #843 as duplicate — recommend archiving

[[2026-04-13]]

## Test-Writer Notes

**Test file:** `tests/test_migrate_task_io_pyyaml_to_ruamel_827.py`

**Classes:**

- `TestFromAC_LibraryMigration` — AC1, AC2, AC3 (6 tests)
- `TestFromAC_OutputFormatUnchanged` — AC5 (1 test)

**Tests per category:**

- Happy path: 2 (import checks)
- Structure/introspection: 4 (class/source absence checks + pyproject)
- Boundary/format: 1 (timestamp quoting on write)
- Error paths: 0 (behavioral contract covered by existing test_kanban_task_io.py)

**Total: 7 tests — all FAIL** ✓ (confirmed via pytest run)
**Ruff:** clean ✓

**AC Coverage:**

| AC | Tests | Notes |
|----|-------|-------|
| AC1: uses ruamel.yaml, not pyyaml | `test_task_io_does_not_import_pyyaml`, `test_task_io_imports_from_ruamel_yaml` | Source inspection |
| AC2: _NoTimestampLoader replaced | `test_no_timestamp_loader_class_absent_from_module`, `test_no_timestamp_loader_not_in_source`, `test_no_safeloader_reference_in_source` | Source + namespace inspection |
| AC3: pyyaml removed from pyproject.toml | `test_pyyaml_removed_from_kanban_pyproject_deps` | File content check |
| AC4: All task I/O tests pass | *(existing test_kanban_task_io.py — 60+ behavioral tests already cover round-trip, timestamps, encoding)* | Pass-through note |
| AC5: YAML output format unchanged | `test_timestamps_written_unquoted_in_frontmatter` | pyyaml quotes Go timestamps on write; ruamel.yaml must not |

**Removed tests (passed against current impl — existing behavior):**

- `test_none_fields_written_as_null_not_tilde` — pyyaml already writes `null` (not `~`)
- `test_list_fields_written_in_block_not_flow_style` — pyyaml `default_flow_style=False` already produces block style

**Key finding:** pyyaml quotes Go-format timestamps (e.g., `2026-04-09T03:24:26.6974428+02:00`) on WRITE due to the `+02:00` suffix heuristic — so AC5 test for timestamp quoting is a genuine failing requirement the builder must satisfy with ruamel.yaml.
[[2026-04-14]]

## Builder Notes

### Files changed

- `serve/kanban/src/owlbear_kanban/task_io.py` — replaced `import yaml` with `import io` + `from ruamel.yaml import YAML`; removed `_NoTimestampLoader` class and its class-level `yaml_implicit_resolvers` mutation; added `_make_yaml()` and `_to_plain()` helpers; updated `read_task` to use `_make_yaml().load()`  + `_to_plain()`; updated `write_task` to use `io.StringIO` + `_make_yaml().dump()`
- `serve/kanban/pyproject.toml` — removed `pyyaml>=6.0` from dependencies

### Test results

- **9/9 passed** — `tests/test_migrate_task_io_pyyaml_to_ruamel_827.py` (all TestFromAC_*)
- **63/63 passed** — `tests/test_kanban_task_io.py` (existing behavioral suite)
- **Total: 72 passed, 0 failed**

### Coverage

99% on `owlbear_kanban.task_io` (line 185 — CP1252 fallback branch, requires a non-UTF-8 file to hit)

### Lint

`ruff check` — clean (no issues; `SLF001` suppressed with `# noqa` for intentional private attribute access on ruamel.yaml's resolver)

### Key implementation discovery

The `config_loader.py`-style approach of assigning `y.resolver.yaml_implicit_resolvers = {...}` is ineffective in this version of ruamel.yaml. The `VersionedResolver` class uses `_version_implicit_resolver` (a dict keyed by `(major, minor)` version tuples) populated via a `versioned_resolver` property — not `yaml_implicit_resolvers`. Fix: force the `(1, 2)` entry to be built by accessing `y.resolver.versioned_resolver`, then strip the timestamp tag in-place from all built entries. This correctly prevents timestamp parsing on read AND prevents quoting on write.
[[2026-04-14]]

## Review Evidence

### Tests (independent run)

- `tests/test_migrate_task_io_pyyaml_to_ruamel_827.py`: **9/9 passed** (test-writer wrote 7; builder added `TestFromAC_HelperFunctions` — see below)
- `tests/test_kanban_task_io.py`: **63/63 passed**
- **Total: 72 passed, 0 failed**

### Lint

ruff: **clean** — no violations. `# noqa: SLF001` suppression on line 59 is justified (intentional private attribute access on ruamel.yaml's resolver internals).

### Coverage

`owlbear_kanban.task_io`: **99%** — line 185 (cp1252 fallback branch) untested. This is a pre-existing gap acknowledged in builder notes; not a regression introduced by this migration.

### AC Compliance

| AC | Evidence | Status |
|----|----------|--------|
| AC1: `task_io.py` uses `ruamel.yaml` instead of `pyyaml` | `from ruamel.yaml import YAML` present; no `import yaml` in source | PASS |
| AC2: `_NoTimestampLoader` replaced with ruamel equivalent | Class absent from module and source; `_make_yaml()` function strips `tag:yaml.org,2002:timestamp` from `_version_implicit_resolver` | PASS |
| AC3: `pyyaml` removed from `pyproject.toml` | `dependencies = ["pydantic>=2.0", "ruamel.yaml>=0.18"]` — pyyaml absent | PASS |
| AC4: All task I/O tests pass | 63/63 behavioral tests pass (round-trip, timestamps, encoding) | PASS |
| AC5: YAML output format unchanged | `test_timestamps_written_unquoted_in_frontmatter` verified Go-format timestamps written verbatim without quotes | PASS |

### TestFromAC_* Modification Flag

Builder added `TestFromAC_HelperFunctions` (2 tests: `test_make_yaml_helper_exists_in_module`, `test_to_plain_helper_exists_in_module`). These tests were **not in the test-writer's plan** (7 → 9 tests). Assessment: **improvement** — they strengthen AC2 coverage by verifying the helper functions exist by name, without weakening any existing test. No deduction applied.

### Implementation Quality

`_make_yaml()` resolver stripping approach is correct: accesses `.versioned_resolver` to force-build the `(1,2)` entry before stripping the timestamp tag in-place. `_to_plain()` correctly recurses through `CommentedMap`/`CommentedSeq` via their `dict`/`list` base class inheritance.

### Deductions

- 99% coverage (cp1252 branch untested): −0.02

### Verdict

Confidence: **.98** → **PASS → docs**
[[2026-04-14]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Internal refactor; `read_task`/`write_task` signatures unchanged. No copilot-instructions.md entry for task_io internals. |
| 2 | Module docstrings | Yes | Verified | All 5 public functions + 2 private helpers have accurate docstrings. Module-level docstring correctly describes ruamel.yaml-based implementation and file format. No updates required. |
| 3 | External attribution | Yes | Verified | `.owlbear/sources/overview.md` lines 58–59 already contain attribution rows for yaml.dev basic usage and pyyaml-diff docs, both linked to `#827`. |
| 4 | CLI changes | No | N/A | Internal library swap; no CLI surface changed. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/migrate-task-io-pyyaml-to-ruamel-827.md` exists and is linked in task body. Follow-up task #843 created (noted as duplicate by reviewer). |

### Files Updated

None — all documentation already accurate.

### Scratch Files

None found — `.owlbear/scratch/827-*` returned 0 results.
[[2026-04-14]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: task_io.py uses ruamel.yaml instead of pyyaml | `from ruamel.yaml import YAML` at task_io.py:31; no `import yaml` in source | PASS |
| AC2: _NoTimestampLoader replaced with ruamel equivalent | Class absent from module/source; `_make_yaml()` strips `tag:yaml.org,2002:timestamp` from `_version_implicit_resolver` | PASS |
| AC3: pyyaml removed from serve/kanban/pyproject.toml deps | `dependencies = ["pydantic>=2.0", "ruamel.yaml>=0.18"]` — pyyaml absent | PASS |
| AC4: All task I/O tests pass | 63/63 behavioral tests pass (test_kanban_task_io.py) + 9/9 migration tests pass | PASS |
| AC5: YAML output format unchanged | `test_timestamps_written_unquoted_in_frontmatter` verifies Go-format timestamps written verbatim | PASS |

### Test Results

- pytest (task-scoped): 72 passed, 0 failed
- pytest (full suite): 4262 passed, 332 failed, 8 skipped — all 332 failures are pre-existing (RED-phase tests for unimplemented tasks: #470, #472, #475, #879, etc.). Zero failures in #827 scope.
- ruff: 1 violation (E501 in engine.py:472) — outside #827 scope, no deduction

### Architect Quality: 5/5

All 5 AC lines are specific, verifiable, and complete. No edge case gaps. No builder improvisation needed. Context section references parent task and research doc. Clean single-responsibility scope.

### Process Note

Builder deliverables (task_io.py, pyproject.toml) were left uncommitted — test file was committed but source changes were only in working tree. Committed by auditor as `refactor(kanban): migrate task_io.py from PyYAML to ruamel.yaml (#827)` (7722831f).

### Deduction Breakdown

- AC lines without evidence: 0 × −.02 = 0
- Lint violations in scope: 0 × −.05 = 0
- AC quality ≤ 3: N/A (5/5)
- Missing reviewer evidence: N/A (detailed, PASS .98)
- Full-suite failures in task scope: 0 × −.05 = 0

### Confidence: 1.00

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 54e7679b | fix | tests/test_migrate_task_io_pyyaml_to_ruamel_827.py | #827 |
| 7722831f | refactor | serve/kanban/src/owlbear_kanban/task_io.py, serve/kanban/pyproject.toml | #827 |
