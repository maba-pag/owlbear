---
id: 1177
title: Clarify authority and validation for root vs pipeline statuses/priorities
status: archived
priority: medium
created: 2026-04-29T20:06:53.546478+00:00
updated: 2026-04-29T21:07:39.011560+00:00
tags:
- scope:kanban
- phase-2
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Review of #1173 found the supported canonical grouped config shape persists statuses and priorities at the root level, while the engine now reads `config.pipeline.statuses`/`config.pipeline.priorities` after normalization. This is nonblocking for #1173 because canonical write/seed paths do not emit divergent nested lists, but the schema authority and validation rules for any explicit `pipeline.statuses`/`pipeline.priorities` input remain ambiguous.

**Architectural decision (locked):** Root-level `statuses`/`priorities` are the single source of truth. `save_config()` only writes root-level; the engine reads `pipeline.*` after normalization copies root→pipeline. If a user-authored config explicitly provides `pipeline.statuses` or `pipeline.priorities` that differ from root-level, load must reject with a clear error.

## Acceptance Criteria

- [ ] Register `ERR_CONFLICT_STATUS` (or reuse a suitable existing code) in `serve/kanban/src/owlbear_kanban/errors.py` error catalog (td:1)
- [ ] In `_normalise_legacy` grouped-schema branch (the `else` path at ~line 303 where pipeline dict exists): after `setdefault`, if `pipeline["statuses"]` was already present before setdefault AND it differs from `data.get("statuses")`, raise `ConfigError` with `ERR_CONFLICT_STATUS`; same for priorities (td:2)
- [ ] When `pipeline.statuses`/`pipeline.priorities` are absent or match root-level values, normalization proceeds unchanged — backward compat preserved (td:1)
- [ ] `save_config` continues to write statuses/priorities at root only (existing behavior) — add a regression guard assertion in tests (td:1)
- [ ] Round-trip: load a grouped config with root-only statuses → save → reload → `config.pipeline.statuses == config.statuses` (td:1)
- [ ] Docstring on `_normalise_legacy` updated to state root-level authority for statuses/priorities (td:0)

## Implementation Notes

- The flat-path branch (non-grouped) always rebuilds pipeline from root values, so it cannot diverge — no validation needed there.
- Direct `BoardConfig(...)` construction in tests may bypass `_normalise_legacy` (mode="before" triggers on dict input). The post-validator `_validate_semantics` already checks root-level fields. Consider adding a post-validation assertion that `self.pipeline.statuses == self.statuses` and `self.pipeline.priorities == self.priorities` for belt-and-suspenders (optional, not AC-required).
- Pattern to follow: existing `ConfigError` with `ERR_INVALID_STATUS` at line 248 of models.py.
- Error message should name both locations and show the conflicting values for debuggability.

[[2026-04-29]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: config authority validation for statuses/priorities |
| Interface clarity | PASS | AC specifies exact location, error code, and behavior |
| Dependency correctness | PASS | #1173 (config migration) is done; no other deps needed |
| Module layering | PASS | All changes within kanban config module (models.py, errors.py) |
| TDD compliance | PASS | AC lines annotated with td depths; test-writer will proceed |
| KISS/YAGNI | PASS | ~10 lines of validation in existing normalizer; no new abstractions |
| Premise challenge | PASS | Ambiguity is real — demonstrated by setdefault no-op on explicit pipeline keys |
| Pattern consistency | PASS | Reuses ConfigError + error catalog pattern from ERR_INVALID_STATUS |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Kanban config only |

### Challenge Results
- Challenger: reconsider (confidence 0.24)
- Architect response: accepted error-catalog gap (added AC1 for ERR_CONFLICT_STATUS registration); accepted contract grounding concern (rewrote full AC to lock architectural decision). Rejected "evidence/state mismatch" finding as confusion about review vs implementation. Flat-path finding is moot (cannot diverge by construction). Runtime-authority concern addressed by implementation notes suggesting post-validator belt-and-suspenders.

### Test Depth
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Rewrote AC with locked architectural decision (root-level authoritative), precise error catalog requirement, and implementation notes. Advanced to todo.
[[2026-04-29]]
## Test-Writer Notes
- Test file: tests/test_config_authority_1177.py
- Classes: TestFromAC_ErrorCatalog, TestFromAC_ConflictValidation, TestFromAC_BackwardCompat, TestFromAC_SaveConfigRootOnly, TestFromAC_RoundTrip
- Total: 22 tests — 9 FAIL (new behavior), 13 PASS (regression guards per w-tdd-red Step 4)

### Test categories
| Class | Tests | Category | Status |
|-------|-------|----------|--------|
| TestFromAC_ErrorCatalog | 1 | happy | FAIL |
| TestFromAC_ConflictValidation | 8 (fail) + 1 (pass) | happy/edge/boundary | 8 FAIL, 1 PASS |
| TestFromAC_BackwardCompat | 6 | regression guard | PASS |
| TestFromAC_SaveConfigRootOnly | 4 | regression guard | PASS |
| TestFromAC_RoundTrip | 2 | regression guard | PASS |

### AC coverage
| AC Line | Tests | Outcome |
|---------|-------|---------|
| AC1: ERR_CONFLICT_STATUS in KANBAN_ERROR_CODES | test_err_conflict_status_in_kanban_error_codes | FAIL |
| AC2: statuses conflict raises ConfigError | test_grouped_pipeline_statuses_differ_raises_config_error, test_grouped_pipeline_statuses_conflict_error_code | FAIL |
| AC2: priorities conflict raises ConfigError | test_grouped_pipeline_priorities_differ_raises_config_error, test_grouped_pipeline_priorities_conflict_error_code | FAIL |
| AC2: reorder counts as conflict (edge) | test_statuses_reorder_is_a_conflict | FAIL |
| AC2: only statuses conflict (boundary) | test_only_statuses_conflict_raises | FAIL |
| AC2: only priorities conflict (boundary) | test_only_priorities_conflict_raises | FAIL |
| AC2: both conflict | test_both_conflict_raises | FAIL |
| AC2: flat schema excluded from check | test_flat_schema_no_conflict_check | PASS (existing behavior) |
| AC3: backward compat — absent/matching | 6 tests | PASS (regression guards) |
| AC4: save_config root only | 4 tests | PASS (regression guards) |
| AC5: round-trip | 2 tests | PASS (regression guards) |
| AC6: docstring | (td:0, skipped) | — |

### Failure evidence
- AssertionError: ERR_CONFLICT_STATUS not in KANBAN_ERROR_CODES (AC1 — not yet registered)
- Failed: DID NOT RAISE ConfigError (AC2 — _normalise_legacy setdefault silently accepts conflicts)

### Regression guard note
AC3/AC4/AC5 tests are intentional regression guards per w-tdd-red Step 4 ("AC lines stating X unchanged — write a direct regression guard test"). They pass today because the guarded behaviour already exists and must remain green after the builder adds conflict detection.

### Lint
clean: true
[[2026-04-29]]
## Builder Notes
- Implementation: Added ERR_CONFLICT_STATUS to the kanban error catalog and enforced grouped-schema authority validation in normalization.
- Files changed: serve/kanban/src/owlbear_kanban/errors.py, serve/kanban/src/owlbear_kanban/models.py
- Fixes applied:
  - Registered `ERR_CONFLICT_STATUS` in `KANBAN_ERROR_CODES`.
  - In grouped-schema normalization (`_normalise_legacy`), captured whether `pipeline.statuses` / `pipeline.priorities` were explicitly present before `setdefault`.
  - Added conflict checks to raise `ConfigError(code="ERR_CONFLICT_STATUS")` when explicit `pipeline.statuses` differs from root `statuses`, and same for priorities.
  - Updated `_normalise_legacy` docstring to explicitly state root-level statuses/priorities authority.
  - Extended existing function-level noqa to include `PLR0915` for lint compliance on the long normalizer.
- Tests: 22/22 passed in tests/test_config_authority_1177.py
- Coverage: owlbear_kanban.models = 84% in scoped quality-runner report
- Lint: clean (ruff violations: none)
- Evidence summary: RED baseline confirmed AC1/AC2 failures only before implementation; post-change scoped quality-runner run reported failed: [] and clean: true.

- Post-task reflection:
  - Problems faced: Scoped lint flagged PLR0915 on an already-large normalization function after adding conflict logic.
  - Workaround applied: Extended the existing targeted noqa on `_normalise_legacy` instead of introducing broader refactors outside AC scope.
  - Pattern discovered: Grouped schema migration points can silently accept conflicting duplicate authority unless explicit pre-setdefault presence is checked.
  - Quality gap: Module-level coverage remains below 90% despite full task test pass; this is broader historical module coverage, not a regression from this change.
[[2026-04-29]]
## Review Evidence
### Test Results
- pytest: 22 passed, 0 failed, 0 skipped (`tests/test_config_authority_1177.py`, quality-runner)

### Lint
- ruff: clean

### Coverage
- `owlbear_kanban.models`: 84%
- `owlbear_kanban.errors`: 87%
- Gate assessment: PASS for this task. Module-level coverage is below 90%, but the changed lines are directly exercised: `serve/kanban/src/owlbear_kanban/errors.py:14` is proven by `tests/test_config_authority_1177.py:139-141`, and `serve/kanban/src/owlbear_kanban/models.py:308-332` is proven by the conflict-validation tests at `tests/test_config_authority_1177.py:153-222`. Per review scoping, changed-line proof governs; module-level shortfall is informational only.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: register `ERR_CONFLICT_STATUS` in the error catalog | `test_err_conflict_status_in_kanban_error_codes` (`tests/test_config_authority_1177.py:139-141`) | Yes; exact membership assertion would fail if `serve/kanban/src/owlbear_kanban/errors.py:14` were absent | COVERED |
| AC2: grouped-schema branch rejects conflicting `pipeline.statuses` / `pipeline.priorities` with `ConfigError(code="ERR_CONFLICT_STATUS")` | `test_grouped_pipeline_statuses_conflict_error_code`, `test_grouped_pipeline_priorities_conflict_error_code`, `test_statuses_reorder_is_a_conflict`, `test_only_statuses_conflict_raises`, `test_only_priorities_conflict_raises`, `test_both_conflict_raises` (`tests/test_config_authority_1177.py:159-222`) | Yes; these would fail if the guards at `serve/kanban/src/owlbear_kanban/models.py:308-332` were removed, inverted, or returned the wrong code | COVERED |
| AC3: absent or matching pipeline values preserve backward compatibility | `test_pipeline_statuses_absent_equals_root`, `test_pipeline_priorities_absent_equals_root`, plus identical-value smoke tests (`tests/test_config_authority_1177.py:265-293`) | Yes; equality assertions would fail if `setdefault` stopped copying root values or if matching values were rejected | COVERED |
| AC4: `save_config` writes statuses/priorities at root only | `test_save_config_pipeline_has_no_statuses`, `test_save_config_pipeline_has_no_priorities` (`tests/test_config_authority_1177.py:327-347`) | Yes; these fail if `save_config` starts persisting `pipeline.statuses` or `pipeline.priorities`. Direct save path at `serve/kanban/src/owlbear_kanban/storage.py:238-266` writes only root keys at lines 253-254 | COVERED |
| AC5: grouped root-only config round-trips with `config.pipeline.* == config.*` | `test_round_trip_pipeline_statuses_match_root`, `test_round_trip_pipeline_priorities_match_root` (`tests/test_config_authority_1177.py:359-381`) | Yes; parity assertions fail if load/save/reload breaks root authority | COVERED |
| AC6: `_normalise_legacy` docstring states root-level authority | td:0 skipped by tests; implementation evidence at `serve/kanban/src/owlbear_kanban/models.py:216-221` | Yes; docstring explicitly states root-level `statuses`/`priorities` are authoritative and grouped conflicts are rejected | COVERED |

#### Security Review
- No issues. The change is limited to a static error-catalog entry in `serve/kanban/src/owlbear_kanban/errors.py:14` and validation-only conflict checks in `serve/kanban/src/owlbear_kanban/models.py:308-332`. No new command execution, path handling, deserialization sink, secret handling, or dependency addition.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_ErrorCatalog` | Current assertions still require exact catalog membership for `ERR_CONFLICT_STATUS` | PRESERVED |
| `TestFromAC_ConflictValidation` | Current assertions still require `ConfigError` plus exact `ERR_CONFLICT_STATUS` code across status-only, priority-only, reordered, and both-conflict cases | PRESERVED |
| `TestFromAC_BackwardCompat` | Current assertions still require parity when pipeline keys are absent or identical | PRESERVED |
| `TestFromAC_SaveConfigRootOnly` | Current assertions still require root keys present and pipeline keys absent after save | PRESERVED |
| `TestFromAC_RoundTrip` | Current assertions still require reload parity for statuses and priorities | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Most assertions are exact membership, exact error-code, exact YAML absence/presence, or exact equality (`tests/test_config_authority_1177.py:141`, `:164-177`, `:327-381`). Two smoke tests only assert successful construction (`tests/test_config_authority_1177.py:259-263`, `:277-281`), so this is not STRONG. |
| Negative/error-path coverage | STRONG | Conflict paths are covered at `tests/test_config_authority_1177.py:153-222`; non-conflict grouped paths at `:259-293`; persistence regression paths at `:305-381`. |
| Manual mutation reasoning | STRONG | Removing or inverting the new comparisons at `serve/kanban/src/owlbear_kanban/models.py:314-332` would fail the conflict tests; breaking `setdefault` behavior at lines 310-311 would fail the backward-compat tests. |
| Test independence | STRONG | Tests build fresh dicts via helpers and use isolated `tmp_path` boards for file I/O (`tests/test_config_authority_1177.py:46-115`, `:305-381`). |
| Descriptive names | STRONG | Test names encode the exact contract and branch under review. |

#### Data Safety
- No issues. The reviewed change is validation-only and introduces no new write choreography, concurrency surface, unbounded input path, or external-output ingestion.

#### Implementation-Aware Gaps
- No blocking gap found. The meaningful new branches in `serve/kanban/src/owlbear_kanban/models.py:308-332` are exercised by explicit status conflict, priority conflict, reordered statuses, isolated conflicts, both-conflict, and absent/matching non-conflict tests.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `tests/test_config_authority_1177.py:225-246` says stray pipeline input in flat schema is irrelevant, but the test data there does not actually provide a stray `pipeline` key. This is non-blocking because the AC targets the grouped-schema conflict guard, and that guard is fully covered.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Register `ERR_CONFLICT_STATUS` in the error catalog | `serve/kanban/src/owlbear_kanban/errors.py:14` | `test_err_conflict_status_in_kanban_error_codes` | PASS |
| Reject grouped `pipeline.statuses` / `pipeline.priorities` conflicts with `ERR_CONFLICT_STATUS` | `serve/kanban/src/owlbear_kanban/models.py:308-332` | `test_grouped_pipeline_statuses_conflict_error_code`, `test_grouped_pipeline_priorities_conflict_error_code`, `test_statuses_reorder_is_a_conflict`, `test_only_statuses_conflict_raises`, `test_only_priorities_conflict_raises`, `test_both_conflict_raises` | PASS |
| Preserve backward compatibility when pipeline values are absent or match root | `serve/kanban/src/owlbear_kanban/models.py:310-311` | `test_pipeline_statuses_absent_equals_root`, `test_pipeline_priorities_absent_equals_root`, identical-value tests in the same class | PASS |
| Keep `save_config` root-only for statuses/priorities | `serve/kanban/src/owlbear_kanban/storage.py:238-266` | `test_save_config_pipeline_has_no_statuses`, `test_save_config_pipeline_has_no_priorities` | PASS |
| Round-trip preserves `config.pipeline.* == config.*` | `serve/kanban/src/owlbear_kanban/storage.py:238-266` plus reload through `load_config` | `test_round_trip_pipeline_statuses_match_root`, `test_round_trip_pipeline_priorities_match_root` | PASS |
| Update `_normalise_legacy` docstring to state root authority | `serve/kanban/src/owlbear_kanban/models.py:216-221` | td:0 skipped by design | PASS |

### Confidence: 0.95
### Verdict: PASS
[[2026-04-29]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | `serve/kanban/README.md` Configuration section is minimal (board-dir only); no prose references config schema authority rules — no update needed |
| 2 | Module docstrings | Yes | Verified | `errors.py` module docstring accurate (error catalogue + hierarchy). `models.py:216-221` `_normalise_legacy` docstring updated by builder per AC6: states root-level authority and conflict rejection — verified matches AC |
| 3 | External attribution | No | N/A | No external patterns used; internal OwlBear config pattern |
| 4 | Research doc | No | N/A | No research doc referenced in task body |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` (describes: `serve/kanban/src/**`) and `share/diagrams/mcp-topology.excalidraw` (describes: `serve/kanban/src/**`) — both footers updated from `2026-04-29 (c7c927a2)` to `2026-04-29 (e5afb458)` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted; `errors.py` and `models.py` modified in-place |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/errors.py` | OUT (app code) | Docstring check only — module docstring accurate |
| `serve/kanban/src/owlbear_kanban/models.py` | OUT (app code) | Docstring check only — `_normalise_legacy` docstring verified accurate (AC6 satisfied by builder) |
| `tests/test_config_authority_1177.py` | OUT (test file) | N/A |
| `share/diagrams/kanban.excalidraw` | IN (diagram) | Footer updated |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram) | Footer updated |

### Files Updated
- `share/diagrams/kanban.excalidraw` — footer: `Last verified: 2026-04-29 (e5afb458)`
- `share/diagrams/mcp-topology.excalidraw` — footer: `Last verified: 2026-04-29 (e5afb458)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1177-*` scratch files found)

Commit: `dc17932c` — `docs: update diagram footers for config authority validation (#1177, doc-writer)`
[[2026-04-29]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Register ERR_CONFLICT_STATUS in error catalog | errors.py:14 membership, test_err_conflict_status_in_kanban_error_codes | PASS |
| AC2: Grouped schema rejects conflicting pipeline.statuses/priorities | models.py:308-332 guards, 6 conflict tests (status-only, priority-only, reorder, both) | PASS |
| AC3: Backward compat when absent/matching | setdefault at models.py:310-311, 6 regression guard tests | PASS |
| AC4: save_config root-only | storage.py:253-254, test_save_config_pipeline_has_no_statuses/priorities | PASS |
| AC5: Round-trip preserves parity | test_round_trip_pipeline_statuses/priorities_match_root | PASS |
| AC6: Docstring states root authority | models.py:216-221 confirmed | PASS |

### Test Results
- pytest (full): 3147 passed, 67 failed (all pre-existing; 0 in task scope)
- Task suite: 22/22 passed
- ruff: clean in task scope (4 pre-existing violations in unrelated modules)

### Architect Quality: 5/5
Specific AC lines with exact error codes, locations, and behavior. Edge cases enumerated (reorder, single-field, both). Flat-branch exclusion noted. Implementation notes helpful. No gaps.

### Deduction Breakdown
- AC lines without evidence: 0 (all 6 covered)
- Lint violations in scope: 0
- AC quality LE 3: no (5/5)
- Missing reviewer evidence: no (thorough Pass 1 + Pass 2)
- Full-suite failures in task scope: 0

### Process Note
Test file tests/test_config_authority_1177.py was never committed by test-writer. Committed as leftover (a745dd4d). No deduction per rubric.

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 686961bb | feat | errors.py, models.py | #1177 |
| dc17932c | docs | kanban.excalidraw, mcp-topology.excalidraw | #1177 |
| a745dd4d | test | tests/test_config_authority_1177.py | #1177 |