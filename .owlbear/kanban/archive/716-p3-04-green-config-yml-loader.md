---
id: 716
title: 'P3-04: GREEN — config.yml loader'
status: archived
priority: medium
created: 2026-04-09T03:25:11.7301647+02:00
updated: 2026-04-09T14:08:35.3097978+02:00
started: 2026-04-09T14:08:35.3097978+02:00
completed: 2026-04-09T14:08:35.3097978+02:00
tags:
    - kanban
    - phase-3
    - scope:mcp-kanban
parent: 712
depends_on:
    - 715
class: standard
---

## Objective
Implement config.yml loader using ruamel.yaml round-trip mode (typ='rt').

Brief: see parent #712 — Decision D1: ruamel.yaml for lossless round-trip

## AC
- [ ] `load_config(kanban_dir)` reads config.yml and returns BoardConfig
- [ ] `save_config(kanban_dir, config)` writes config.yml preserving field order, comments, quoting
- [ ] Timestamp resolver disabled to prevent Go-nanosecond to Python-microsecond precision drift
- [ ] next_id atomic increment via load-modify-save
- [ ] ruamel.yaml added to `serve/mcp-kanban/pyproject.toml` dependencies
- [ ] All #715 tests pass

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/config_loader.py` (new)
- `serve/mcp-kanban/pyproject.toml` (edit — add ruamel.yaml dep)

[[2026-04-09]] Thu 12:22
## Architecture Review

### Context
GREEN phase task for config.yml loader. Parent #712 (archived epic). Dependency #715 (done — 31 tests passing, .97 reviewer confidence). **Pipeline anomaly:** #715's builder already delivered the full implementation (`config_loader.py` 138 lines, `ruamel.yaml>=0.18` dep) during the RED phase. All 6 AC lines are already satisfied by committed code (commit `edf1b95`). Builder for #716 should verify existing code satisfies AC (pass-through verification).

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| `load_config(kanban_dir)` reads config.yml and returns BoardConfig | PASS — exists at L48-60 of `config_loader.py`; tested by `TestFromAC_LoadConfig` (11 tests) | None |
| `save_config(kanban_dir, config)` writes config.yml preserving field order, comments, quoting | PASS — exists at L64-86; read-modify-write via `_merge_into`; tested by `TestFromAC_RoundTrip` (6 tests) + `TestFromAC_PreservesCommentsAndUnknownFields` (6 tests) | None |
| Timestamp resolver disabled | PASS — L23-37; instance-level resolver shadow, no global side effects; tested by `TestFromAC_TimestampResolverDisabled` (4 tests) | None |
| next_id atomic increment via load-modify-save | PASS — tested by `TestFromAC_NextIdIncrement` (4 tests); load→mutate→save→reload cycle | None |
| ruamel.yaml added to pyproject.toml | PASS — `serve/mcp-kanban/pyproject.toml` L6: `"ruamel.yaml>=0.18"` | None |
| All #715 tests pass | PASS — 31/31 per #715 reviewer evidence | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Config.yml I/O only — load and save with round-trip preservation |
| Interface clarity | PASS | Two public functions with explicit signatures, Path input, BoardConfig I/O |
| Dependency correctness | PASS | #715 at `done`; BoardConfig from `engine_models.py` (exists via #714) |
| Module layering | PASS | `config_loader.py` inside `serve/mcp-kanban/src/owlbear_mcp_kanban/`; imports only `engine_models` (same package) and `ruamel.yaml` |
| TDD compliance | PASS | #715 is the RED phase; this is the GREEN counterpart |
| KISS/YAGNI | PASS | Minimal scope: 2 public functions, 3 internal helpers, no speculative features |
| Premise challenge | PASS | Config loading is core engine requirement per D1 decision; ruamel.yaml is the only library supporting lossless YAML round-trip |
| Pattern consistency | PASS | Pydantic `model_validate` for deserialization, explicit `encoding="utf-8"`, `Path`-based API |
| Security surface | PASS | `YAML(typ="rt")` is safe (no arbitrary constructors); hardcoded `config.yml` filename (no user-controlled path component); explicit FileNotFoundError |
| Single domain | PASS | Kanban engine domain exclusively |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| load_config — missing file | config.yml absent | FileNotFoundError | Yes (explicit check L53-54) | Clear error message |
| load_config — invalid YAML | Malformed YAML content | ruamel.yaml ScannerError | No (propagates) | Acceptable — corrupted config is exceptional |
| load_config — schema mismatch | YAML valid but missing fields | Pydantic ValidationError | Yes (via model_validate) | Clear validation error |
| save_config — write failure | Disk full / permissions | OSError | No (propagates) | Acceptable — OS-level I/O failure |

### Architecture Notes
1. **Implementation already exists:** `config_loader.py` (138 lines) and `ruamel.yaml` dep were committed during #715's builder phase (commit `edf1b95`). #716 builder should verify the existing code satisfies all AC lines — no new implementation expected.
2. **Timestamp resolver pattern:** Instance-level resolver shadow (L30-37) is the correct approach — avoids global side effects that would affect other YAML consumers in the process.
3. **Read-modify-write strategy:** `save_config` loads existing YAML as `CommentedMap`, applies changes via `_merge_into`, then writes back. This preserves comments, field order, and per-item annotations. Correct for D1 (lossless round-trip).

### Challenge Results
- Challenger: proceed (confidence: .92)
- Architect response: accepted — no architectural concerns raised; process anomaly (early implementation) is scheduling, not structural

### Verdict: APPROVE
### Action Taken: Approved #716 to todo. All AC lines are well-defined and verifiable. Implementation already exists from #715 builder — downstream pipeline should verify existing code satisfies AC (pass-through verification). No new code expected.

[[2026-04-09]] Thu 13:02
## Test-Writer Notes
- **Pass-through (pre-delivered implementation)**
- Existing test file: tests/test_kanban_engine_config.py (written by test-writer for #715)
- Classes: TestFromAC_LoadConfig (11), TestFromAC_RoundTrip (6), TestFromAC_PreservesCommentsAndUnknownFields (6), TestFromAC_NextIdIncrement (4), TestFromAC_TimestampResolverDisabled (4)
- Total: 31 tests — **all PASS** (run confirmed in this session)
- AC coverage: all 5 testable AC lines are covered by #715 test file; AC line 6 ("All #715 tests pass") is a pass/fail meta-constraint, not a new testable interface
- No new tests added: `config_loader.py` was pre-delivered by #715 builder (commit `edf1b95`) — any new test targeting the same contracts would pass immediately, violating RED phase rules
- ruff: clean (no changes to test file)
- Builder action: verify existing implementation satisfies all AC (pass-through verification per architecture review)

[[2026-04-09]] Thu 13:23
## Builder Notes

### Files Changed
- `tests/test_kanban_engine_config.py` — added `TestBuilderDiscovered` class (4 tests)

### Implementation
Pass-through verification task — `config_loader.py` was pre-delivered by #715 builder (commit `edf1b95`). No changes to implementation files.

### Builder-Discovered Tests (RED → GREEN)
Added `TestBuilderDiscovered` to cover 4 branches not exercised by existing `TestFromAC_*` tests:
1. **BD-1** `test_save_config_creates_file_when_not_exists` — covers `else: raw = CommentedMap()` (line 78) when `config.yml` doesn't exist yet
2. **BD-2** `test_save_config_updates_changed_scalar_in_same_length_sequence` — covers `elif old_item != new_item: old_value[i] = new_item` (lines 119-120)
3. **BD-3** `test_save_config_replaces_sequence_on_length_change` — covers `else: target[key] = new_value` for different-length sequences (line 133)
4. **BD-4** `test_save_config_persists_changed_scalar_field` — covers outer `else: target[key] = new_value` for scalar fields (line 135)

All 4 tests passed immediately (implementation pre-exists). Coverage artifact note: parallel test execution caused 88.2% apparent coverage when running full file together; running all 35 tests explicitly yields 100%.

### Test Results
- **35/35 passed** (31 TestFromAC_* + 4 TestBuilderDiscovered)
- **Coverage:** 52/52 statements, 24/24 branches = **100%** on `config_loader.py`
- **Ruff:** clean (exit 0)

### AC Verification
| AC | Status |
|----|--------|
| `load_config` reads config.yml → BoardConfig | ✅ 11 TestFromAC_LoadConfig tests pass |
| `save_config` preserves field order, comments, quoting | ✅ 12 TestFromAC_RoundTrip + PreservesComments tests pass |
| Timestamp resolver disabled | ✅ 4 TestFromAC_TimestampResolverDisabled tests pass |
| next_id atomic increment via load-modify-save | ✅ 4 TestFromAC_NextIdIncrement tests pass |
| ruamel.yaml in pyproject.toml | ✅ `ruamel.yaml>=0.18` at line 6 of serve/mcp-kanban/pyproject.toml |
| All #715 tests pass | ✅ 31/31 pass |

[[2026-04-09]] Thu 13:38
## Review Evidence

### Test Results
- **pytest:** 35 passed, 0 failed, 0 skipped (quality-runner, independent run)
- **ruff:** clean, exit 0

### Coverage
- `owlbear_mcp_kanban.config_loader`: **100%** (52/52 statements, 24/24 branches — confirmed by quality-runner; matches builder's 100% claim)

### AC Compliance

| AC Line | Evidence | Test | Status |
|---------|----------|------|--------|
| `load_config(kanban_dir)` reads config.yml → BoardConfig | config_loader.py:L47-56; `y.load()` + `_to_plain()` + `model_validate()` | TestFromAC_LoadConfig (11 tests) | PASS |
| `save_config` preserves field order, comments, quoting | config_loader.py:L59-84 + `_merge_into()` L107-135; CommentedMap read-modify-write | TestFromAC_RoundTrip (6) + TestFromAC_PreservesCommentsAndUnknownFields (6) | PASS |
| Timestamp resolver disabled | config_loader.py:L26-37; instance-level dict comprehension shadows class-level resolver, no global side effects | TestFromAC_TimestampResolverDisabled (4 tests) | PASS |
| next_id atomic increment via load-modify-save | L47-56 (load), L59-84 (save); caller increments, `_merge_into()` L134-135 persists scalar | TestFromAC_NextIdIncrement (4 tests) | PASS |
| ruamel.yaml in pyproject.toml | serve/mcp-kanban/pyproject.toml:L4: `"ruamel.yaml>=0.18"` | Static check | PASS |
| All #715 tests pass | 35/35 including all 31 original TestFromAC_* tests | Full run | PASS |

### Pass 1 — Critical Checks

**5.0 Test-writer audit:** All 5 testable AC lines have TestFromAC_* coverage. Assertions are STRONG throughout — explicit type, value, and exception checks. All would fail if AC violated (e.g., removing `model_validate` fails type checks; removing resolver shadow fails `isinstance(snapshot_date, str)` and datetime negation; removing `_merge_into` recursion fails comment-preservation string searches). No MISSING or LAX.

**5.1 Security:** `YAML(typ="rt")` — safe, no code execution. Filename hardcoded to `"config.yml"` — no user-controlled path component. No secrets or injection risks. No `yaml.unsafe_load()` or `pickle`.

**5.2 TestFromAC integrity:** All TestFromAC_* classes verified as unmodified. Builder added 4 new `TestBuilderDiscovered` tests but made zero changes to existing tests. No weakening or removal.

**5.3 Test quality:** STRONG. Two error-path tests in LoadConfig (`pytest.raises(FileNotFoundError)`). Negative type assertions (`not isinstance(..., datetime.date)`) in TimestampResolverDisabled. Field-order test parses YAML directly and compares key lists. Independence: all tests use isolated `tmp_path` fixture with no shared mutable state.

**5.4 Data safety:** No unvalidated LLM output. Single-threaded load-modify-save (no file lock, but acceptable — D1 architecture decision; consistent with project pattern). No unbounded inputs.

**5.5 Branch gap analysis:** TestBuilderDiscovered covers 4 genuinely untested branches in `_merge_into()`: (1) `else: raw = CommentedMap()` file-creation path; (2) `elif old_item != new_item` same-length sequence scalar update; (3) `else: target[key] = new_value` length-changed sequence; (4) `else: target[key] = new_value` top-level scalar. Coverage from 88%→100%.

**5.6 Necessity:** `ruamel.yaml` is the only library supporting lossless YAML round-trip; D1 decision already approved in parent #712.

**5.7 Builder process:** 1 `## Builder Notes` section. Clean first pass. No loop detected.

### Deductions
None.

### Verdict
**PASS** — confidence: .97

[[2026-04-09]] Thu 13:41
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `config_loader.py` is an internal engine module; no public CLI or agent-facing API change; `copilot-instructions.md` covers only project identity and branches — no impact |
| 2 | Module docstrings | Yes | Verified | All public symbols have accurate docstrings: module docstring (L1-8), `_make_yaml` (L25), `load_config` (L44-49 with Raises), `save_config` (L62-72), `_to_plain` (L90-96), `_merge_into` (L101-113) |
| 3 | External attribution | No | N/A | `ruamel.yaml` already attributed in `.owlbear/sources/overview.md` L37 (added during parent epic #712 research) |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No new research doc for #716; parent research doc `.owlbear/research/native-kanban-engine.md` is backing research and referenced in parent #712 |

### Files Updated
None — all docstrings verified accurate, attribution pre-existing, no CLI or behavior changes.

### Scratch Files
No `.owlbear/scratch/716-*` files found.

[[2026-04-09]] Thu 14:08
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| `load_config(kanban_dir)` reads config.yml → BoardConfig | config_loader.py:L46-58; `y.load()` + `_to_plain()` + `model_validate()` — 11 TestFromAC_LoadConfig tests pass | PASS |
| `save_config` preserves field order, comments, quoting | config_loader.py:L61-84 + `_merge_into()` L107-135 — 12 RoundTrip + PreservesComments tests pass | PASS |
| Timestamp resolver disabled | config_loader.py:L26-37; instance-level resolver shadow — 4 TestFromAC_TimestampResolverDisabled pass | PASS |
| next_id atomic increment via load-modify-save | 4 TestFromAC_NextIdIncrement pass — load→mutate→save→reload cycle | PASS |
| ruamel.yaml in pyproject.toml | `serve/mcp-kanban/pyproject.toml` L6: `"ruamel.yaml>=0.18"` | PASS |
| All #715 tests pass | 35/35 pass (31 TestFromAC_* + 4 TestBuilderDiscovered) | PASS |

### Test Results
- pytest (task-scoped): 35 passed, 0 failed
- pytest (full suite): 371 failed, 3904 passed — 0 failures in task scope; all failures in unrelated test files (orchestrator, ideator, challenger, planner, etc.)
- ruff: 7 violations — 0 in task-scoped files; all in pre-existing code (server.py, test_server.py, approve.py, test_necessity_check_196.py)

### Architect Quality: 5/5
AC lines are specific, concrete, and directly verifiable. 10-criterion evaluation with failure mode map. Pipeline anomaly (pre-delivered implementation) correctly identified and downstream agents properly directed.

### Deduction Breakdown
- AC lines without evidence: 0 (all 6 verified) → 0
- Lint violations in task scope: 0 → 0
- AC quality ≤ 3: No (5/5) → 0
- Missing reviewer evidence: No (thorough, .97 confidence) → 0
- Full-suite failures in task scope: 0 → 0
- Process note: Builder did not commit TestBuilderDiscovered tests — committed as leftover by auditor (4a71375). Not a rubric item.

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| edf1b95 | feat | config_loader.py, pyproject.toml | #715 |
| 2da2a83 | test | test_kanban_engine_config.py | #715 |
| 4a71375 | test | test_kanban_engine_config.py (+TestBuilderDiscovered) | #716 |
