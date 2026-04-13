---
id: 827
title: Migrate task_io.py from PyYAML to ruamel.yaml
status: in-progress
priority: nice-to-have
created: '2026-04-11T01:12:00.740638+00:00'
updated: '2026-04-13T19:00:58.519342+00:00'
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
### Action Taken: Advanced to `todo`. Flagged #843 as duplicate — recommend archiving.
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