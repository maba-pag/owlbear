---
id: 715
title: 'P3-03: RED — config.yml loader (ruamel.yaml round-trip)'
status: archived
priority: medium
created: 2026-04-09T03:25:03.4706335+02:00
updated: 2026-04-09T12:42:46.9877315+02:00
started: 2026-04-09T12:42:46.9877315+02:00
completed: 2026-04-09T12:42:46.9877315+02:00
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
Write failing tests for config.yml loading via ruamel.yaml round-trip mode.

Brief: see parent #712 — Decision D1: ruamel.yaml

## AC
- [ ] Test loads config.yml and returns BoardConfig with correct statuses (list of dicts), priorities, defaults, next_id
- [ ] Test round-trips config.yml (load, save, reload) without data loss or field reordering
- [ ] Test preserves comments and unknown fields
- [ ] Test next_id increment (load, increment, save, verify)
- [ ] Test timestamp resolver disabled (no auto-conversion of date-like strings)
- [ ] All tests fail (no loader implementation yet)

## Files
- `tests/test_kanban_engine_config.py` (new)

[[2026-04-09]] Thu 08:45
## Architecture Review

### Context
RED (TDD) phase task for config.yml loading tests. Parent #712 (archived epic). Dependency #714 (archived/done — BoardConfig model exists in `engine_models.py`, 44 tests passing, 100% coverage). GREEN counterpart is #716 (config_loader.py implementation).

### Interface Guidance for Test-Writer
The tests should import from a module that does NOT yet exist:
- **Module:** `owlbear_mcp_kanban.config_loader`
- **Functions:** `load_config(kanban_dir: Path) -> BoardConfig`, `save_config(kanban_dir: Path, config: BoardConfig) -> None`
- **Import for models:** `from owlbear_mcp_kanban.engine_models import BoardConfig`
- **Source:** GREEN #716 Files section specifies `serve/mcp-kanban/src/owlbear_mcp_kanban/config_loader.py`
- **Config reference:** `.owlbear/kanban/config.yml` (27 lines: version=10, 7 statuses, 5 priorities, defaults with `class`, `tui` section, `next_id`)

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Test loads config.yml → BoardConfig with correct statuses, priorities, defaults, next_id | PASS — specific fields enumerated, verifiable via assertions on BoardConfig attributes | None |
| Test round-trips config.yml (load, save, reload) without data loss or field reordering | PASS — measurable: compare original vs round-tripped YAML content. Requires both `load_config` and `save_config` (coherent scope for round-trip testing) | None |
| Test preserves comments and unknown fields | PASS — YAML comments (`#...`) and vendor fields (e.g. `tui`, `extra_vendor_field`) must survive round-trip. Create fixture config.yml with embedded comments via `tmp_path` | None |
| Test next_id increment (load, increment, save, verify) | PASS — specific sequence: load → mutate next_id → save → reload → assert new value. Tests save path alongside load | None |
| Test timestamp resolver disabled (no auto-conversion of date-like strings) | PASS — ruamel.yaml default resolver converts date-like strings to `datetime`. Test: put a value like `"2026-04-09"` or `"1h"` in config, load, verify it remains `str` not `datetime`/`timedelta` | None |
| All tests fail (no loader implementation yet) | PASS — standard RED gate; `config_loader.py` does not exist | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Only failing tests for config.yml I/O |
| Interface clarity | PASS | Function signatures derivable from #716 + architecture notes above |
| Dependency correctness | PASS | #714 archived (done); BoardConfig exists in `engine_models.py` |
| Module layering | PASS | Test file imports from `owlbear_mcp_kanban` package |
| TDD compliance | PASS | This IS the RED phase; GREEN is #716 |
| KISS/YAGNI | PASS | Minimal test scope — 5 test scenarios |
| Premise challenge | PASS | Config loading is core engine requirement per D1 decision |
| Pattern consistency | PASS | Follows #713 pattern: `TestFromAC_*` classes, Pydantic model fixtures, `tmp_path` for I/O |
| Security surface | N/A | Test file only — no runtime system boundary |
| Single domain | PASS | Kanban engine domain exclusively |

### Challenge Results
- Challenger: reconsider (import path not in AC)
- Architect response: Valid concern re: import path. Cannot edit body (no `edit_task` tool). Added explicit interface guidance in architecture notes above. Test-writer has: module path, function signatures, model import, config reference. AC lines themselves are specific and verifiable. Remaining challenger concerns (scope, fixtures, archived status) evaluated and determined non-blocking.

### Verdict: APPROVE
### Action Taken: Approved #715 to todo. AC is specific and mechanically verifiable. Interface guidance (module path, function signatures) added in architecture notes for test-writer. Tagged `type:test` (pass-through tag present). Dependency #714 confirmed done.

[[2026-04-09]] Thu 09:20
## Test-Writer Notes

**Test file:** `tests/test_kanban_engine_config.py` (new)

**AC coverage:**

| AC Line | Test Class | Tests |
|---------|-----------|-------|
| Test loads config.yml → BoardConfig with correct statuses, priorities, defaults, next_id | `TestFromAC_LoadConfig` | 11 tests |
| Test round-trips config.yml (load, save, reload) without data loss or field reordering | `TestFromAC_RoundTrip` | 6 tests |
| Test preserves comments and unknown fields | `TestFromAC_PreservesCommentsAndUnknownFields` | 6 tests |
| Test next_id increment (load, increment, save, verify) | `TestFromAC_NextIdIncrement` | 4 tests |
| Test timestamp resolver disabled (no auto-conversion of date-like strings) | `TestFromAC_TimestampResolverDisabled` | 4 tests |
| All tests fail (no loader implementation yet) | All classes | Confirmed |

**Test categories per class:**
- `TestFromAC_LoadConfig` (11): happy ×9, error ×2
- `TestFromAC_RoundTrip` (6): happy ×6 (load→save→reload cycle)
- `TestFromAC_PreservesCommentsAndUnknownFields` (6): happy ×6 (block comment, 2× inline, tui, extra field, model_dump access)
- `TestFromAC_NextIdIncrement` (4): happy ×3, boundary ×1 (near-zero, multi-cycle)
- `TestFromAC_TimestampResolverDisabled` (4): happy ×2, boundary ×1, round-trip ×1

**Total: 31 tests — all FAIL**

**Fail mode:** `ModuleNotFoundError: No module named 'owlbear_mcp_kanban.config_loader'` at collection — module does not exist yet (expected RED state).

**ruff:** clean (0 issues)

**Interface under test:** `load_config(kanban_dir: Path) -> BoardConfig`, `save_config(kanban_dir: Path, config: BoardConfig) -> None` from `owlbear_mcp_kanban.config_loader`

**Fixtures:** `tmp_path` (pytest built-in), `_BASE_CONFIG_YAML`, `_ANNOTATED_CONFIG_YAML` (with block/inline comments and vendor fields), `_DATE_STRING_CONFIG_YAML` (with date-like string fields for resolver tests)

[[2026-04-09]] Thu 11:26
## Builder Notes

**Files changed (2):**
- `serve/mcp-kanban/src/owlbear_mcp_kanban/config_loader.py` — new (138 lines): `load_config`, `save_config`, `_make_yaml`, `_to_plain`, `_merge_into`
- `serve/mcp-kanban/pyproject.toml` — added `ruamel.yaml>=0.18` dependency

**Test results:** 31/31 passed (all `TestFromAC_*` classes)

**Coverage:** 90% on `config_loader.py` (52 stmts, 5 missed — all untested branches are defensive paths not exercised by AC tests, e.g. `save_config` with no existing file, sequence length mismatch in `_merge_into`)

**Lint:** ruff clean (0 issues); ANN401 suppressed with `# noqa: ANN401` on `_to_plain` private helper that genuinely requires `Any` for recursive type conversion

**Key implementation decisions:**
- `YAML(typ='rt')` round-trip mode; timestamp resolver disabled by shadowing `y.resolver.yaml_implicit_resolvers` at instance level (no global side effects)
- `save_config` uses read-modify-write: loads existing `CommentedMap`, applies `_merge_into` to update values in-place, writes back — preserving block/inline comments and per-item sequence annotations
- `_to_plain` converts `CommentedMap`/`CommentedSeq` to plain dicts/lists for Pydantic validation; `_merge_into` recurses into nested maps and updates sequences item-by-item to avoid comment loss
- `ruamel.yaml==0.19.1` installed via `uv sync`

**Commit:** `edf1b95` — feat(kanban): add config_loader with ruamel.yaml round-trip (#715)

[[2026-04-09]] Thu 12:01
## Review Evidence

### Test Results
- pytest: 31 passed, 0 failed (tests/test_kanban_engine_config.py)

### Lint
clean: true (ruff 0 violations — `config_loader.py` + test file)

### Coverage
`owlbear_mcp_kanban.config_loader`: 90% (missing lines: 78, 119–120, 133–135)

Uncovered branches (all low severity, not required by AC):
- L78: `raw = CommentedMap()` — save_config when config.yml does not yet exist (documented capability, 2 lines; delegating to _merge_into on empty map is mechanically correct)
- L119–120: `target[key] = new_value; continue` — new key in model_dump() not in existing CommentedMap (would require schema changes not present in tests)
- L133–135: list length mismatch path in `_merge_into` — replace whole sequence; only triggered if statuses/priorities list length changes (no AC requirement)

All AC-exercised paths (load, save, round-trip, comment preservation, next_id increment, timestamp resolver) are fully covered. Uncovered paths are defensive branches outside AC scope.

---

### Pass 1 — CRITICAL

#### AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| load_config → BoardConfig with correct statuses, priorities, defaults, next_id | `TestFromAC_LoadConfig` (11 tests) | Yes — exact type + value assertions: `len(config.statuses)==7`, `list(config.priorities)==[...]`, `config.defaults.status=="research"`, `config.next_id==100` | COVERED |
| Round-trip without data loss or field reordering | `TestFromAC_RoundTrip` (6 tests) | Yes — load→save→reload, compares field values AND top-level key order from YAML text | COVERED |
| Preserves comments and unknown fields | `TestFromAC_PreservesCommentsAndUnknownFields` (6 tests) | Yes — asserts exact comment strings in YAML text: `"# Board configuration"`, `"# default priority"`, `"# duration string"`; asserts `extra_vendor_field: preserved-value` in output | COVERED |
| next_id increment (load, increment, save, verify) | `TestFromAC_NextIdIncrement` (4 tests) | Yes — asserts `reloaded.next_id == original + 1`; multi-cycle accumulation test | COVERED |
| Timestamp resolver disabled | `TestFromAC_TimestampResolverDisabled` (4 tests) | Yes — `assert not isinstance(snapshot_date, datetime.date)` + `isinstance(snapshot_date, str)` | COVERED |
| All tests fail (RED gate) | All classes | Yes — test-writer confirmed `ModuleNotFoundError` at collection; builder added module to make tests pass | COVERED |

#### Security Review
- Path traversal: `kanban_dir / "config.yml"` — hardcoded filename, no user-controlled path component. Internal library; trusted caller. No concern.
- YAML loading: `YAML(typ="rt")` (ruamel round-trip mode) — safe; no `yaml.load` with arbitrary constructors, no eval/exec, no Python object deserialization.
- Timestamp coercion: Explicitly disabled at L24–31 via instance-level resolver shadow; no global side effects.
- File I/O: Explicit `encoding="utf-8"` on all open() calls. L54, L68, L80.
- Model validation: `BoardConfig.model_validate()` — Pydantic schema enforcement, not arbitrary assignment.
- Dependency: ruamel.yaml >= 0.18 — necessary (PyYAML cannot preserve comments), active maintenance, no known CVEs.
- No subprocess, no shell interpolation, no hardcoded secrets.

RESULT: No issues.

#### Test Integrity
Test-writer file (`tests/test_kanban_engine_config.py`) is NOT in the builder's changed files list (builder changed only `config_loader.py` and `pyproject.toml`). No `TestFromAC_*` tests were modified, weakened, or removed.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 31 TestFromAC_* tests | None | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact values (`==100`), exact types (`isinstance(int)`), exact YAML text substrings, exact list equality (`list(config.priorities)==[...]`) |
| Error-path coverage | ADEQUATE | FileNotFoundError (2 tests); no load-corrupt-YAML test, but that's outside AC scope |
| Mutation resistance | STRONG | Timestamp tests use `not isinstance(..., datetime.date)` — would catch silent coercion regression. Round-trip tests diff loaded vs reloaded values |
| Test independence | STRONG | All tests use `tmp_path` (pytest-scoped temp dir); no shared mutable state |
| Descriptive naming | STRONG | All names are sentence-descriptive (`test_block_comment_survives_roundtrip`, `test_iso_date_string_remains_str_not_datetime`) |

#### Data Safety
No LLM output persisted. No shared mutable state (YAML instance created fresh in `_make_yaml()` per call). No unbounded input. No atomicity gaps (write is synchronous single-file).

#### Test Gap Analysis (Implementation-Aware)
5 uncovered branches all outside AC scope. Core paths (load, save with existing file, round-trip, comment preservation, next_id mutation, scalar assignment) are fully exercised. Defensive edges (new key insertion in `_merge_into`, list-length mismatch, save-from-scratch) are not AC requirements and carry minimal risk.

#### Builder Process Quality
1 `## Builder Notes` section. No retries. → CLEAN.

---

### Deductions
- -0.03: 90% coverage; 5 branches untested, including the documented `save_config` create-from-scratch path (L78). All are outside AC scope but non-trivial implementation branches.

### Verdict
Confidence: **0.97** → PASS

All 31 tests pass. ruff clean. All 5 AC lines covered with specific, falsifiable assertions. Security clean. Test integrity confirmed. Test quality STRONG across all dimensions. Builder process clean.

[[2026-04-09]] Thu 12:13
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | New internal library module (`config_loader`). copilot-instructions.md has no tech stack tables or module listings — only Project Identity and Repository Branches sections. No agent-facing or consumer-facing surface changed. |
| 2 | Module docstrings | Yes | PASS | `config_loader.py` (138 lines): module-level docstring accurate (round-trip mode, timestamp resolver, comment preservation). `load_config` — docstring with Raises: FileNotFoundError. `save_config` — docstring with read-modify-write strategy. `_make_yaml`, `_to_plain`, `_merge_into` — all have accurate docstrings. No gaps found. |
| 3 | External attribution → sources/overview.md | No | N/A | ruamel.yaml already attributed under "Native Kanban Engine (Task #712)" — PyPI entry present with date 2026-04-09. No new external source used in #715. |
| 4 | CLI changes → README.md | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | No `.owlbear/research/` doc produced for this task. Research was done at parent #712 level. |

### Files Updated
None — no documentation gaps found.

### Scratch Files
None — `file_search` for `.owlbear/scratch/715-*` returned 0 results.

### Verdict
PASS — all applicable checklist items verified. Docstrings accurate. Attribution current. No docs changes required.

[[2026-04-09]] Thu 12:42
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Test loads config.yml → BoardConfig with correct statuses, priorities, defaults, next_id | `TestFromAC_LoadConfig` — 11 tests: type/value assertions on `len(statuses)==7`, `list(priorities)==[...]`, `defaults.status=="research"`, `next_id==100` | PASS |
| Test round-trips config.yml without data loss or field reordering | `TestFromAC_RoundTrip` — 6 tests: load→save→reload cycle, top-level key order comparison | PASS |
| Test preserves comments and unknown fields | `TestFromAC_PreservesCommentsAndUnknownFields` — 6 tests: exact comment strings (`# Board configuration`, `# default priority`, `# duration string`), vendor field `extra_vendor_field: preserved-value` | PASS |
| Test next_id increment (load, increment, save, verify) | `TestFromAC_NextIdIncrement` — 4 tests: single increment, near-zero boundary, multi-cycle accumulation | PASS |
| Test timestamp resolver disabled | `TestFromAC_TimestampResolverDisabled` — 4 tests: `not isinstance(datetime.date)`, `isinstance(str)` for date-like, ISO 8601, and duration strings | PASS |
| All tests fail (RED gate) | Test-writer confirmed `ModuleNotFoundError` at collection; builder added module → 31/31 pass | PASS |

### Test Results
- pytest: 1221 passed, 80 failed, 3 skipped (80 failures all pre-existing in unrelated files: test_analysis.py, test_challenger_agent_467.py, test_disable_model_invocation.py, etc. — 0 failures in task-scoped files)
- ruff: 5 violations, all in `server.py`/`test_server.py` — NOT in #715 files. Task files clean.

### Architect Quality: 4/5
AC lines were specific and mechanically verifiable. Minor gap: import path/function signatures not in AC body (added by architect in architecture notes after challenger flag). Overall well-scoped for RED phase.

### Process Note
Test file `tests/test_kanban_engine_config.py` was never committed by test-writer — found as untracked. Committed as leftover in `2da2a83`. Not a quality gap, but a process gap.

### Deduction Breakdown
- AC lines without evidence: 0 (all 6 covered) → -0.00
- Lint violations in task files: 0 → -0.00
- AC quality ≤ 3: no (4/5) → -0.00
- Missing reviewer evidence: no (detailed, PASS at .97) → -0.00
- Full-suite failures in task scope: 0 → -0.00

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| edf1b95 | feat | config_loader.py, pyproject.toml | #715 |
| 2da2a83 | test | test_kanban_engine_config.py, 715-*.md | #715 |
