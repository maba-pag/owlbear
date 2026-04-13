---
id: 843
title: Implement task_io.py PyYAML to ruamel.yaml migration
status: in-progress
priority: nice-to-have
created: '2026-04-12T02:24:30.617737+00:00'
updated: '2026-04-13T20:09:00.071995+00:00'
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

- `task_io.py` uses `from ruamel.yaml import YAML` instead of `import yaml`
- `_NoTimestampLoader` class replaced with `_make_yaml()` function (same pattern as `config_loader.py`)
- `_to_plain()` helper added for CommentedMap → dict conversion on load
- `write_task()` uses `YAML(typ="rt")` dump via `StringIO` instead of `yaml.dump()`
- `pyyaml` removed from `serve/kanban/pyproject.toml` dependencies
- All existing task I/O tests pass without modification (60+ tests)
- Live board round-trip integration tests pass (700+ files)

## Context

Research: `.owlbear/research/migrate-task-io-pyyaml-to-ruamel-827.md`
Parent research task: #827. Supersedes #827 for implementation.

## Implementation Notes

Follow the `config_loader.py` pattern exactly:
1. `_make_yaml()` → `YAML(typ="rt")` with timestamp resolver stripping
2. `_to_plain()` → recursive CommentedMap/CommentedSeq → dict/list conversion
3. `StringIO` wrapper for dump-to-string

~15 lines removed (PyYAML loader class), ~15 lines added (ruamel helpers). Net delta ~0.
[[2026-04-13]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single-file YAML library migration + pyproject.toml dep removal — one logical change |
| Interface clarity | PASS | AC specifies exact imports, class replacements, helper additions, and serialization changes |
| Dependency correctness | PASS | Depends on #818 (in-progress); declared correctly, kanban dependency gate handles ordering |
| Module layering | PASS | Internal refactor within `serve/kanban/` — no cross-boundary changes |
| TDD compliance | PASS | RED tests exist in `test_migrate_task_io_pyyaml_to_ruamel_827.py` (6 tests: AC1-AC5); test-writer should note pass-through |
| KISS/YAGNI | PASS | Minimal scope — consolidates two YAML libraries into one, net delta ~0 lines |
| Premise challenge | PASS | Removing duplicate dependency is clearly justified; dual YAML libraries are a maintenance liability |
| Pattern consistency | PASS | Follows exact `config_loader.py` pattern (`_make_yaml()`, `_to_plain()`, StringIO dump) in same package |
| Security surface | PASS | `YAML(typ="rt")` is safe (no arbitrary code execution); replaces `yaml.SafeLoader` which was also safe |
| Single domain | PASS | kanban domain only |

### Codebase Evidence
- **PyYAML usage**: Only `serve/kanban/src/owlbear_kanban/task_io.py` line 32 uses `import yaml` in the kanban package
- **Pattern reference**: `serve/kanban/src/owlbear_kanban/config_loader.py` — proven `_make_yaml()` + `_to_plain()` pattern
- **RED tests**: `tests/test_migrate_task_io_pyyaml_to_ruamel_827.py` — 6 tests covering library migration (AC1), class removal (AC2), dep removal (AC3), and output format (AC5)
- **Behavioral tests**: `test_kanban_task_io.py` — 60+ existing round-trip/timestamp/encoding tests serve as regression safety net
- **Root pyproject.toml**: retains `pyyaml>=6.0` in dev deps — unaffected by this task (used by test-only imports in hook tests)

### Known Conflict
`test_extract_engine_kanban_818.py::test_pyyaml_dep` asserts pyyaml IS present in kanban pyproject.toml. This is superseded by AC5 (removal). Builder will discover and resolve this when running the full suite — the test guards an obsolete assumption.

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| `_to_plain()` on deeply nested CommentedMap | Recursive conversion misses a type | TypeError at model_validate | Yes — 60+ round-trip tests catch this | None if tests pass |
| YAML 1.2 quoting heuristics | Minor cosmetic differences in string quoting | None (semantically equivalent) | Yes — research assessed risk as None/Low | None |

### Challenge Results
- Challenger: **proceed** (confidence 0.80)
- Architect response: **accepted** — test conflict is self-evident from AC5 and naturally resolved by builder

### Verdict: APPROVE
### Action Taken: Advanced to todo. RED tests exist from #827 research; test-writer should note pass-through.
[[2026-04-13]]
## Test-Writer Notes

**Test file:** `tests/test_migrate_task_io_pyyaml_to_ruamel_827.py` (pre-existing from #827 research; extended here)

**Note:** RED tests already existed from task #827. Architect confirmed pass-through; extended file with 2 additional tests to close `_make_yaml()` and `_to_plain()` AC coverage gaps.

### Test Classes

| Class | AC Coverage | Tests |
|-------|-------------|-------|
| `TestFromAC_LibraryMigration` | AC1 (ruamel import), AC2 (_NoTimestampLoader removal), AC5 (pyyaml dep) | 6 |
| `TestFromAC_OutputFormatUnchanged` | AC4 (write_task timestamp format) | 1 |
| `TestFromAC_HelperFunctions` | AC2 (_make_yaml exists), AC3 (_to_plain exists) | 2 |

**Total: 9 tests — 0 passed, 9 FAILED** ✓

### AC Coverage Table

| AC Line | Test(s) | Status |
|---------|---------|--------|
| `task_io.py` uses `ruamel.yaml` instead of `import yaml` | test_task_io_does_not_import_pyyaml, test_task_io_imports_from_ruamel_yaml | FAIL ✓ |
| `_NoTimestampLoader` replaced with `_make_yaml()` | test_no_timestamp_loader_class_absent_from_module, test_no_timestamp_loader_not_in_source, test_no_safeloader_reference_in_source, test_make_yaml_helper_exists_in_module | FAIL ✓ |
| `_to_plain()` helper added | test_to_plain_helper_exists_in_module | FAIL ✓ |
| `write_task()` output format unchanged (timestamps unquoted) | test_timestamps_written_unquoted_in_frontmatter | FAIL ✓ |
| `pyyaml` removed from kanban pyproject.toml | test_pyyaml_removed_from_kanban_pyproject_deps | FAIL ✓ |
| All existing task I/O tests pass (60+) | Existing test_kanban_task_io.py — behavioral regression net (currently PASS) | N/A |
| Live board round-trip (700+ files) | Integration/API scope — not covered | N/A |

**Ruff:** All checks passed.