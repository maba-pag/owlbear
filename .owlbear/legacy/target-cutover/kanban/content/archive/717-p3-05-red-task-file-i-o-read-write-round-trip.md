---
id: 717
title: 'P3-05: RED — task file I/O (read, write, round-trip)'
status: archived
priority: medium
created: 2026-04-09T03:25:21.0909825+02:00
updated: 2026-04-09T12:14:21.8399236+02:00
started: 2026-04-09T12:14:21.8399236+02:00
completed: 2026-04-09T12:14:21.8399236+02:00
tags:
    - kanban
    - phase-3
    - type:test
parent: 712
depends_on:
    - 714
class: standard
---

## Objective
Write failing tests for task file I/O: reading YAML frontmatter + markdown body, writing task files, and round-trip preservation.

Brief: see parent #712

## AC
- [ ] Test reads a task file and returns TaskRecord with all frontmatter fields + markdown body
- [ ] Test writes a TaskRecord to a file in correct format (--- delimited YAML frontmatter + body)
- [ ] Test round-trips a task file without data loss (unknown fields, body formatting preserved)
- [ ] Test path containment validation (reject paths outside kanban tasks_dir)
- [ ] Test slug generation from title (a-z0-9 dash, max 80 chars)
- [ ] Test Windows reserved filename rejection (CON, PRN, AUX, NUL, etc.)
- [ ] Test file naming convention: `{id}-{slug}.md`
- [ ] All tests fail (no I/O implementation yet)

## Files
- `tests/test_kanban_engine_io.py` (new)

[[2026-04-09]] Thu 08:40
## Architecture Review

### Context
RED test task for task file I/O operations. Dependency #714 (Pydantic models) is `done` — `TaskRecord` and `BoardConfig` available in `engine_models.py`. Brief (parent #712) provides full file format spec, slug rules, and security requirements. GREEN counterpart #718 specifies implementation in `task_io.py` with `read_task()` and `write_task()`.

### MANDATORY CORRECTIONS (test-writer must apply)

**1. Test file rename:** Use `tests/test_kanban_task_io.py` (NOT `test_kanban_engine_io.py`). Convention from #713: `test_kanban_{module_name}.py`. GREEN #718 specifies `task_io.py` as implementation module.

**2. Import path:** `from owlbear_mcp_kanban.task_io import read_task, write_task, ...  # type: ignore[import-not-found]`

**3. Additional AC — `---` in body edge case:** The `---` delimiter (YAML frontmatter boundary) appearing inside the markdown body MUST NOT corrupt frontmatter parsing on read or write. Add explicit test for this under AC3 (round-trip).

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Test reads task file → TaskRecord with frontmatter + body | PASS — specific, testable; `read_task(path) -> TaskRecord` | None |
| Test writes TaskRecord to file (--- delimited YAML + body) | PASS — specific, testable; `write_task(path, record)` | None |
| Test round-trips without data loss (unknown fields, body formatting) | PASS — needs additional `---` in body edge case (correction #3) | Add `---` edge case test |
| Test path containment (reject paths outside tasks_dir) | PASS — specific; existing pattern in `sandbox_path()` (knowledge pkg); engine needs own implementation | None |
| Test slug generation (a-z0-9 dash, max 80 chars) | PASS — specific, Brief provides exact allowlist | None |
| Test Windows reserved filename rejection (CON, PRN, etc.) | PASS — specific, Brief lists requirement | None |
| Test file naming convention `{id}-{slug}.md` | PASS — specific, testable | None |
| All tests fail (no I/O implementation yet) | PASS — standard RED AC | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All AC lines relate to task file I/O only |
| Interface clarity | PASS | Functions derivable from Brief + GREEN #718: `read_task()`, `write_task()`, slug/path helpers |
| Dependency correctness | PASS | #714 (Pydantic models) is `done`; TaskRecord available |
| Module layering | PASS | Tests import from `owlbear_mcp_kanban.task_io` — engine-internal module |
| TDD compliance | PASS | This IS the RED task |
| KISS/YAGNI | PASS | 7+1 AC lines directly from Brief spec, no speculation |
| Premise challenge | PASS | Needed for native engine to read/write task files |
| Pattern consistency | PASS | Follows #713 RED test pattern: `TestFromAC_*` classes, `# type: ignore[import-not-found]` |
| Security surface | PASS | AC covers path containment, slug allowlist, Windows reserved filenames — all from Brief |
| Single domain | PASS | Kanban engine domain only |

### Failure Mode Map
Not applicable — RED test task (no implementation codepaths).

### Challenge Results
- Challenger: PROCEED (confidence 0.82)
- Two must-fix items: (1) test file rename to `test_kanban_task_io.py`, (2) add `---` in body edge case
- Architect response: ACCEPTED — both corrections embedded as mandatory directives above
- Nice-to-have: symlink traversal test under path containment — left to test-writer discretion

### Verdict: APPROVE
### Action Taken: Approved #717 to todo with 3 mandatory corrections for test-writer: (1) test file → `test_kanban_task_io.py`, (2) import from `owlbear_mcp_kanban.task_io`, (3) add `---` in body edge case test under AC3.

[[2026-04-09]] Thu 09:22
## Test-Writer Notes

**Test file:** `tests/test_kanban_task_io.py` (new)

**Import:** `from owlbear_mcp_kanban.task_io import generate_slug, make_task_filename, read_task, validate_path_containment, write_task`

**Test classes and counts:**
| Class | Category breakdown | Count |
|-------|-------------------|-------|
| `TestFromAC_ReadTaskFile` | happy×10, edge×1, error×1 | 12 |
| `TestFromAC_WriteTaskFile` | happy×8, edge×2 | 10 |
| `TestFromAC_RoundTrip` | happy×4, edge×2, boundary×2 | 8 |
| `TestFromAC_PathContainment` | happy×1, error×4, boundary×1 | 6 |
| `TestFromAC_SlugGeneration` | happy×3, edge×2, boundary×3 | 8 |
| `TestFromAC_WindowsReservedNames` | happy×2, error×5, edge×2 | 9 |
| `TestFromAC_FileNamingConvention` | happy×5 | 5 |
| **Total** | | **58** |

**Fail confirmation:** pytest exit code 1 — `ModuleNotFoundError: No module named 'owlbear_mcp_kanban.task_io'` at collection. 0 tests passed, 0 tests ran.

**Ruff:** exit code 0 — all checks passed.

**AC coverage:**
| AC Line | Tests |
|---------|-------|
| AC1: read_task → TaskRecord with all frontmatter + body | TestFromAC_ReadTaskFile (12) |
| AC2: write_task → --- delimited YAML + body format | TestFromAC_WriteTaskFile (10) |
| AC3: round-trip without data loss (unknown fields, body, --- in body) | TestFromAC_RoundTrip (8) |
| AC4: path containment — reject outside tasks_dir | TestFromAC_PathContainment (6) |
| AC5: slug generation — [a-z0-9-], max 80 chars | TestFromAC_SlugGeneration (8) |
| AC6: Windows reserved name rejection | TestFromAC_WindowsReservedNames (9) |
| AC7: file naming convention — {id}-{slug}.md | TestFromAC_FileNamingConvention (5) |
| AC8: all tests fail | ✓ Confirmed (ModuleNotFoundError) |

**Arch review mandatory corrections applied:**
1. ✓ Test file renamed to `test_kanban_task_io.py`
2. ✓ Import from `owlbear_mcp_kanban.task_io`
3. ✓ `---` in body edge case: `test_round_trip_dashes_in_body_preserved` + `test_write_dashes_in_body_do_not_appear_in_frontmatter_block`

[[2026-04-09]] Thu 11:00
## Builder Notes

**Files changed:** 2
- `serve/mcp-kanban/src/owlbear_mcp_kanban/task_io.py` — new module (GREEN implementation)
- `tests/test_kanban_task_io.py` — `TestBuilderDiscovered` class appended (1 test)

**Test results:** 59 passed, 0 failed, 0 errors (`uv run pytest tests/test_kanban_task_io.py -q --tb=short`)

**Coverage:** `task_io.py` — **100%** (60 statements, 0 missed)

**Lint:** ruff — exit code 0, all checks passed

**Implementation summary:**
- `generate_slug(title)` — lowercases, strips non-`[a-z0-9]` to hyphens, truncates at 80, rejects Windows reserved names (`con`, `prn`, `aux`, `nul`, `com1–9`, `lpt1–9`) with `ValueError`
- `make_task_filename(id, title)` — returns `{id}-{slug}.md`
- `validate_path_containment(tasks_dir, path)` — null-byte check, `resolve()`, rejects `tasks_dir` itself, and any path outside via `relative_to()` → `PermissionError`
- `read_task(path)` — splits on first `---` delimiter after line 0; uses `_NoTimestampLoader` (SafeLoader minus timestamp resolver) to preserve Go 7-digit nanosecond timestamps as strings; validates frontmatter structure
- `write_task(path, record)` — `model_dump()` → pop `body` → `yaml.dump(sort_keys=False)` → `---\n{yaml}---\n{body}`; body containing `---` is safe (placed after closing delimiter)

**Builder-discovered test:** `TestBuilderDiscovered.test_read_task_missing_closing_delimiter_raises` — file with opening `---` but no closing delimiter; covers lines 179–180 that were missed by `TestFromAC_*` suite. Code was pre-emptively implemented during GREEN. Test PASSED on first run (coverage gap, not a regression).

**Ruff fixes applied:**
1. Moved `from pathlib import Path` to `TYPE_CHECKING` block (TC003)
2. Added `# noqa: S506` on `yaml.load` with `_NoTimestampLoader` (inherits from SafeLoader — safe)

**Commit:** `1c618a3` — `feat(kanban): implement task_io module — read_task, write_task, slug, path guards (#717)`

[[2026-04-09]] Thu 11:31
## Review Evidence

### Test Results
- pytest: 59 passed, 0 failed, 0 errors

### Lint
- ruff: clean (exit code 0)

### Coverage
- `owlbear_mcp_kanban.task_io`: 100% (60 statements, 0 missed)

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|---------------|---------------------------|---------|
| AC1: read_task → TaskRecord with all frontmatter + body | `TestFromAC_ReadTaskFile` (12 tests): id, title, status/priority, timestamps-as-str, Go 7-digit nanosecond exact, optional fields, body, empty body, unknown fields, error paths | Yes — exact field-value assertions, isinstance checks, nanosecond exact match | COVERED |
| AC2: write_task → `---` delimited YAML + body | `TestFromAC_WriteTaskFile` (10 tests): file created, starts with `---\n`, closing delimiter present, id/title in frontmatter, body after second delimiter, optional fields, overwrites | Yes — `content.startswith("---\n")`, body_start indexing, field presence | COVERED |
| AC3: round-trip without data loss (unknown fields, body, `---` in body) | `TestFromAC_RoundTrip` (8 tests) incl. `test_round_trip_dashes_in_body_preserved`, `test_round_trip_go_nanosecond_timestamp_exact`, `test_round_trip_unknown_fields_preserved` | Yes — exact field equality, `"---" in result.body`, `result.id == 99`, exact timestamp string | COVERED |
| AC4: path containment — reject outside tasks_dir | `TestFromAC_PathContainment` (6 tests): valid path, outside path, `..` traversal, null byte, tasks_dir itself, sibling dir | Yes — `pytest.raises((PermissionError, ValueError))` scoped to security errors | COVERED |
| AC5: slug generation `[a-z0-9-]`, max 80 chars | `TestFromAC_SlugGeneration` (8 tests): lowercase, spaces→hyphens, charset via `re.fullmatch(r"[a-z0-9-]+")`, max 80, truncation boundary, empty | Yes — `re.fullmatch` would fail for any illegal char; `len(slug) <= 80` would fail on overrun | COVERED |
| AC6: Windows reserved names rejected | `TestFromAC_WindowsReservedNames` (9 tests): CON, PRN, AUX, NUL individual; COM1–9 loop; LPT1–9 loop; case-insensitive; embedded word accepted | Yes — `pytest.raises(ValueError, match=r"(?i)reserved|...")` with message matching | COVERED |
| AC7: file naming `{id}-{slug}.md` | `TestFromAC_FileNamingConvention` (5 tests): `re.fullmatch(r"\d+-[a-z0-9-]+\.md")`, starts with id, ends with `.md`, slug matches `generate_slug` output | Yes — regex fullmatch, startswith, endswith, exact equality | COVERED |
| AC8: all tests fail (RED) | Confirmed by test-writer: `ModuleNotFoundError` at collection, exit code 1 | Confirmed at RED phase | COVERED |

#### 5.1 Security Review

- **YAML deserialization**: `yaml.load(frontmatter_str, Loader=_NoTimestampLoader)` — `_NoTimestampLoader` subclasses `yaml.SafeLoader`, removing only the timestamp implicit resolver. SafeLoader bars arbitrary code execution. `# noqa: S506` suppression is justified. **No issue.**
- **Path traversal**: `validate_path_containment` performs null-byte check, `resolve()` on both paths, rejects `tasks_dir` itself, and uses `relative_to` — standard defense-in-depth pattern. **No issue.**
- **Hardcoded secrets**: None.
- **Injection**: No shell execution, no SQL, no template rendering.
- **Input validation**: `generate_slug` allowlist via `re.sub(r"[^a-z0-9]+", "-", ...)`, length bounded at 80. `read_task` validates file format before YAML parse.
- **No security issues found.**

#### 5.2 Test Integrity (TestFromAC Comparison)

Builder appended `TestBuilderDiscovered` class (1 test: `test_read_task_missing_closing_delimiter_raises`). No `TestFromAC_*` methods were modified. All 58 original tests preserved.

| Change | Assessment |
|--------|------------|
| `TestBuilderDiscovered` class appended | STRENGTHENED — adds specific `match=r"closing"` coverage for lines 179–180 |
| All `TestFromAC_*` classes | PRESERVED — no modifications |

#### 5.3 Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | 57/59 tests: exact field equality, `re.fullmatch`, specific error matching. 2 LAX spots: (1) `test_read_file_missing_frontmatter_raises` uses `pytest.raises((ValueError, KeyError, Exception))` — `Exception` base class admits any exception; (2) `test_reserved_name_as_word_in_longer_title_accepted` uses `assert slug is not None` — vacuous for str-or-raise function |
| Negative/error-path coverage | STRONG | Covers: FileNotFoundError, missing frontmatter, missing closing delimiter, null byte, path traversal, ../ escape, tasks_dir itself, sibling dir, all 22 Windows reserved names |
| Mutation resistance | STRONG | Nanosecond exact match fails if loader truncates; `re.fullmatch(r"[a-z0-9-]+")` fails on any charset violation; field equality in round-trips fails on any serialization break |
| Test independence | STRONG | All tests use `tmp_path` (pytest-isolated) or immutable module constants; no shared mutable state |
| Descriptive names | STRONG | All methods follow `test_{behavior}_{condition}` convention |

#### 5.4 Data Safety
No LLM output persistence, no race conditions (module init is one-time at import), `path.write_text` is single-op, `generate_slug` bounded at 80 chars. **No issues.**

#### 5.5 Implementation-Aware Test Gap Analysis

All branches in `task_io.py` are verified covered by 100% coverage and traced to tests:

- `generate_slug` empty path → `test_empty_title_returns_empty_or_raises` ✓
- `validate_path_containment` null byte, `==` check, `relative_to` all covered ✓
- `read_task` no-frontmatter, no-closing-delimiter, normal parse, body extraction all covered ✓
- `write_task` normal, body, empty body, dashes-in-body all covered ✓

**Informational (Pass 2):** Dead variable in `read_task` loop body — line 149 sets `msg = "Task file has no closing '---' frontmatter delimiter: {path}"` (non-f-string) on every iteration, but this value is never read. The correct f-string assignment at the `if closing_idx is None:` block overrides it. This is dead code, harmless, but confusing; line 152 is the actual error message.

#### 5.7 Builder Process Quality
Single `## Builder Notes` section. First-pass success. No loop or retry. **CLEAN.**

### AC Compliance Summary

All 8 AC lines: **PASS**

### Deductions
- -0.03: 2 LAX assertions in non-critical edge tests (adequate suite overall, no path where a real regression would be silently swallowed)
- -0.02: Dead variable assignment in `read_task` loop (Pass 2 informational, not a defect)

### Verdict
**Confidence: .95 → PASS**

No Pass 1 criteria unmet. 59/59 tests green, ruff clean, 100% coverage, all AC lines mapped to passing discriminating tests, no security issues, no TestFromAC modifications.

[[2026-04-09]] Thu 11:37
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | New internal engine module. `copilot-instructions.md` is 100 lines covering only project identity + branch structure — does not catalog modules or APIs. No update warranted. |
| 2 | Module docstrings | Yes | Verified | `task_io.py` (new). Module-level docstring accurate. All 5 public functions have docstrings verified against implementation: `generate_slug` (rules + ValueError note), `make_task_filename` (args/returns), `validate_path_containment` (checks/raises), `read_task` (args/returns/raises), `write_task` (format/args). `_NoTimestampLoader` helper class also documented. |
| 3 | External attribution | No | N/A | Implementation uses stdlib (`re`, `pathlib`), PyYAML (SafeLoader subclassing), and Pydantic. No new external sources cited in builder notes. Parent #712 attribution entry in `sources/overview.md` already covers the research context for this module family. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | No `.owlbear/research/` doc produced for this task. Parent #712 research doc exists and was verified as part of arch review. |

### Files Updated
None — no docs impact found.

### Scratch Files
No `.owlbear/scratch/717-*` files found.

[[2026-04-09]] Thu 12:14
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: read_task returns TaskRecord with all frontmatter + body | TestFromAC_ReadTaskFile (12 tests), read_task at task_io.py:148 | PASS |
| AC2: write_task produces --- delimited YAML + body | TestFromAC_WriteTaskFile (10 tests), write_task at task_io.py:194 | PASS |
| AC3: round-trip without data loss (unknown fields, body, --- in body) | TestFromAC_RoundTrip (8 tests) incl. test_round_trip_dashes_in_body_preserved | PASS |
| AC4: path containment rejects outside tasks_dir | TestFromAC_PathContainment (6 tests), validate_path_containment at task_io.py:113 | PASS |
| AC5: slug generation [a-z0-9-], max 80 chars | TestFromAC_SlugGeneration (8 tests), generate_slug at task_io.py:71 | PASS |
| AC6: Windows reserved name rejection | TestFromAC_WindowsReservedNames (9 tests), _WINDOWS_RESERVED frozenset | PASS |
| AC7: file naming {id}-{slug}.md | TestFromAC_FileNamingConvention (5 tests), make_task_filename at task_io.py:99 | PASS |
| AC8: all tests fail (RED) | Test-writer confirmed ModuleNotFoundError at collection | PASS |

### Test Results
- pytest (task-scoped): 59 passed, 0 failed
- pytest (full suite): 385 failed, 3862 passed — 0 failures in task scope (pre-existing)
- ruff (task-scoped): clean
- ruff (full suite): 5 errors in server.py/test_server.py — outside scope

### Architect Quality: 5/5
AC was specific and complete. 7 functional lines + 1 RED confirmation. Arch review added 3 corrections (file rename, import path, --- edge case) — all applied. No builder improvisation needed beyond 1 builder-discovered test.

### Deduction Breakdown
- No deductions applied. All AC lines have specific test evidence, lint clean in scope, reviewer section detailed with PASS verdict, AC quality 5/5, commit verified (1c618a3).
- Reviewer's "dead variable at line 149" note: inspected current code — no dead variable exists. Loop body is clean.

### Confidence: 1.00
### Action: archive

### Commit Verification
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 1c618a3 | feat | task_io.py, test_kanban_task_io.py | #717 |
