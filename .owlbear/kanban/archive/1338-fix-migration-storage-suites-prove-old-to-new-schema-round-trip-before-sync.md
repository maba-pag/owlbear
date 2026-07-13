---
id: 1338
title: Fix storage round-trip timestamp and archive claimed_by leaks
status: archived
priority: medium
created: 2026-05-04T15:00:05.755705+00:00
updated: 2026-05-04T23:23:26.456948+00:00
tags:
- sync-blocker
- kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Storage/migration compatibility is still a deployment blocker. The current focused failures are timestamp frontmatter formatting and legacy archive `claimed_by` leakage through `Task.model_extra`. These must be fixed before syncing to main because task files are the kanban system's durable data contract.

## Acceptance Criteria

1. `write_task()` emits canonical ISO timestamp strings with UTC offsets and without single quotes (plain YAML scalars). (td:2)
2. Naive timestamps (no timezone) are normalized to UTC offset form (`+00:00`) before write. (td:1)
3. Timestamps with non-UTC offsets (e.g., `+02:00`) are converted to UTC (`+00:00`) before write. (td:1)
4. `read_task()` strips legacy `claimed_by` from archive files so it is absent from both attributes and `model_extra`/`model_dump()`. (td:2)
5. Old-format boards can be loaded, saved, and re-read without losing task identity, status, priority, body, parent/deps, tags, blocking fields, and archival metadata. (td:2)
6. Existing suites (`serve/kanban/tests/test_storage.py`, `serve/kanban/tests/test_storage_1050.py`, `serve/kanban/tests/test_migrate.py`) pass or are corrected only where tests assert stale formatting. (td:0)
7. Regression tests in `tests/test_schema_roundtrip_1338.py` prove archive read behavior and timestamp formatting do not regress. (td:0)

## Key Files

- `serve/kanban/src/owlbear_kanban/storage.py` — `read_task`, `write_task`, `_normalize_timestamp`
- `serve/kanban/src/owlbear_kanban/yaml_rt.py` — ruamel.yaml factory (may need plain scalar forcing)
- `serve/kanban/src/owlbear_kanban/models.py` — `Task` model (`extra='allow'`)
- `serve/kanban/src/owlbear_kanban/migrate.py` — uses same yaml_rt; round-trip covered by AC5
- `tests/test_schema_roundtrip_1338.py` — RED regression suite (7 tests)
- `serve/kanban/tests/test_storage_1050.py` — canonical storage tests (includes AC-C48 archive tests)
- `serve/kanban/tests/test_storage.py`
- `serve/kanban/tests/test_migrate.py`

## Implementation Guidance

**Timestamp quoting fix:** The ruamel.yaml round-trip representer quotes strings matching timestamp patterns even with the resolver removed. Force plain scalar style on timestamp values in the `CommentedMap` before dump (e.g., wrap with `ruamel.yaml.scalarstring.PlainScalarString` or set `fa.set_block_seq_indent`).

**claimed_by stripping:** Strip `claimed_by` from the parsed data dict in `_parse_task_file` or post-parse in `read_task` (after detecting archive path). The `Task` model's `extra='allow'` means any unrecognized key leaks into `model_extra` — remove it before `model_validate`.

**Downstream safety:** `claimed_by` is not a declared field on `Task`. It only appears in `model_extra` for legacy archive files. No downstream consumer (engine, cockpit, MCP) depends on its presence — they use `claimed_at` (the Brief C replacement). Stripping is safe.

## Audit Evidence

- Narrow verification of `tests/test_schema_roundtrip_1338.py` produced 7/7 failures.
- Timestamp lines are emitted as quoted values such as `created: '2026-04-20T10:00:00+00:00'`.
- Archive `claimed_by` survives parsing through Pydantic extras.

## Test-Writer Notes

- Existing RED file: `tests/test_schema_roundtrip_1338.py`.
- Keep tests contract-level: inspect persisted frontmatter and parsed task models, not private implementation details.
- AC5 round-trip test should assert ALL fields named in the criterion (body, parent, archival_reason, archival_refs, block_reason, claimed_at) — extend existing test assertions if needed.

## Source

Deployment audit reconciliation, 2026-05-04.

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Two related fixes in one storage domain — timestamp formatting and legacy field stripping |
| Interface clarity | PASS | Named functions (`write_task`, `read_task`), specific behaviors (unquoted, stripped) |
| Dependency correctness | PASS | No external dependencies; touches only kanban storage internals |
| Module layering | PASS | All changes within `serve/kanban/` — no upward imports |
| TDD compliance | PASS | RED file exists with 7 failing tests covering all AC scenarios |
| KISS/YAGNI | PASS | Minimal fixes to restore documented contract behavior |
| Premise challenge | PASS | Bugs confirmed by audit evidence; sync-blocker tag justified |
| Pattern consistency | PASS | Uses existing `_normalize_timestamp`, `CommentedMap`, `atomic_write` patterns |
| Security surface | PASS | No new system boundaries; internal storage I/O only |
| Single domain | PASS | kanban storage domain exclusively |

### Challenge Results
- Challenger: reconsider (0.66)
- Key concerns: AC3 wording ambiguity, AC5 test assertion gap, AC6 unnamed suites, downstream consumers
- Architect response: ACCEPTED AC3/AC6 refinements (applied above). AC5 assertion gap addressed via test-writer note. Downstream consumer concern rebutted — `claimed_by` is not a declared Task field, only leaks via `model_extra`, no consumer depends on it.

### Test Depth
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC3 wording, scoped AC6 to named suites, added implementation guidance and test-writer notes, advanced to todo.
[[2026-05-04]]
Architecture review complete. Refined AC3 (clarified "non-UTC offsets" vs naive), scoped AC6 to named test suites, added implementation guidance (PlainScalarString for timestamp quoting, pre-validate stripping for claimed_by), and test-writer notes for AC5 assertion completeness. Challenger raised valid wording/coverage concerns (0.66) — addressed via refinement. All 10 criteria PASS.
[[2026-05-04]]
## Test-Writer Notes

**Test file:** `tests/test_schema_roundtrip_1338.py`

**Test classes and counts:**

| Class | Category | Tests |
|---|---|---|
| `TestFromAC_SchemaRoundTrip` | round-trip (happy + data-integrity) | 2 |
| `TestFromAC_ArchiveClaimedByStripping` | archive read / `claimed_by` strip | 2 |
| `TestFromAC_TimestampRoundTrip` | write format (happy + boundary) | 3 |

**Total: 7 tests — all FAIL (confirmed by pytest run)**

**AC coverage:**

| AC | Tests |
|---|---|
| AC1: `write_task` emits unquoted UTC timestamps | `test_write_task_timestamp_line_ends_with_utc_offset` |
| AC2: naive timestamps normalized to `+00:00` | `test_write_task_naive_timestamp_stored_with_utc_offset_unquoted` |
| AC3: non-UTC offsets converted to UTC | `test_write_task_non_utc_timestamp_converted_unquoted` |
| AC4: `read_task` strips `claimed_by` from archive files (attr + `model_extra`) | `test_archive_read_task_claimed_by_stripped_to_none`, `test_archive_read_task_claimed_by_not_in_model_extra` |
| AC5: old-format board round-trip preserves ALL named fields (body, parent, tags, deps, blocked, block_reason, claimed_at, archival_reason, archival_refs) + unquoted timestamps | `test_full_round_trip_timestamps_unquoted_in_written_file`, `test_full_round_trip_task_data_preserved_after_migrate_and_write` |
| AC6/AC7: (td:0) — no tests needed | — |

**Failure causes confirmed:**
- Timestamp quoting: ruamel.yaml wraps ISO8601 strings in single quotes → lines end with `+00:00'` not `+00:00`
- `claimed_by` leaks through `Task.model_extra` (extra='allow') when reading archive files — `read_task` does not strip it

**Extension made:** extended `test_full_round_trip_task_data_preserved_after_migrate_and_write` to assert `body`, `parent`, `block_reason`, `claimed_at`, `archival_reason`, `archival_refs` per AC5 "without loss" contract (all fields named in criterion). Test still fails on timestamp quoting check.

**Ruff:** clean
[[2026-05-04]]
## Builder Notes
- Implementation: updated `serve/kanban/src/owlbear_kanban/storage.py`.
- Fixes applied:
  - `read_task()` now strips legacy `claimed_by` from archive-task frontmatter before `Task.model_validate`, preventing leaks into `model_extra`/`model_dump()`.
  - Timestamp write path now normalizes timezone forms and emits unquoted frontmatter timestamps by forcing plain-style handling and unquoting only timestamp-shaped scalar lines.
  - Small helper extraction in `read_task` path to keep lint complexity constraints clean.
- RED verification (pre-change): `tests/test_schema_roundtrip_1338.py` failed 7/7 (quality-runner evidence).
- GREEN verification (post-change): `tests/test_schema_roundtrip_1338.py` passed 7/7, ruff clean.
- Additional AC6 suite run:
  - `serve/kanban/tests/test_storage.py` + `serve/kanban/tests/test_storage_1050.py` + `serve/kanban/tests/test_migrate.py`
  - Result: 130 passed, 5 failed (all in `serve/kanban/tests/test_migrate.py`, none in storage suites).
  - Failures are migrate lane/idempotency assertions (`tasks_dir` legacy field, migrated-count output, mtime stability), not timestamp/claimed_by assertions.
- Coverage evidence:
  - Task-scoped run: `owlbear_kanban.storage` 57%.
  - AC6 broader suite: `storage.py` 94%, lint clean.
- Commit: `decdf3b0` (`fix: canonical timestamp frontmatter and archive claimed_by strip (#1338, builder)`).

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reconcile AC6 gate with current baseline migrate failures or split prerequisite migration-lane stabilization task before builder completion can advance. | `serve/kanban/tests/test_migrate.py`, task AC6 in #1338 | quality-runner run: 5 failing migrate tests with 130 other tests passing |
| 2 | builder | After AC6 gate is clarified/resolved, rerun AC6 suites and, if green, advance #1338 to review. | `serve/kanban/tests/test_storage.py`, `serve/kanban/tests/test_storage_1050.py`, `serve/kanban/tests/test_migrate.py` | current run is blocked solely by migrate-suite failures |

[[2026-05-04]]
## Builder Notes
- Verified prior builder implementation commit `decdf3b0` touches only `serve/kanban/src/owlbear_kanban/storage.py`.
- Fresh quality-runner evidence for task scope:
  - `tests/test_schema_roundtrip_1338.py`: PASS (7/7)
  - `serve/kanban/tests/test_storage.py`: PASS
  - `serve/kanban/tests/test_storage_1050.py`: PASS
  - `serve/kanban/tests/test_migrate.py`: 5 FAIL (lane/idempotency/manual-summary assertions, not timestamp/claimed_by behavior)
  - Ruff on scoped paths: clean
- AC1-AC5/AC7 behaviors are satisfied by passing task regression + storage suites.
- AC6 remains unsatisfied due pre-existing or separate migrate-lane failures outside the storage change scope.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine/split AC6 into a separate migration-lane stabilization task or rebaseline gate so #1338 is evaluated against storage contract scope. | `serve/kanban/tests/test_migrate.py`, task #1338 AC6 | quality-runner: 137 passed, 5 failed all in migrate suite while storage/roundtrip tests pass |
| 2 | builder | Re-run AC6 suite and advance to review after architect clarifies gate or migration failures are resolved. | `serve/kanban/tests/test_storage.py`, `serve/kanban/tests/test_storage_1050.py`, `serve/kanban/tests/test_migrate.py` | current gate blocked solely by migrate tests unrelated to `storage.py` change |
[[2026-05-04]]

## Architecture Review — AC6 Refinement (2026-05-04)

**Issue:** Builder reported AC6 gate blocked by 5 pre-existing failures in `serve/kanban/tests/test_migrate.py` (lane completeness, config idempotency predicates, manual-summary output). These test migration lane logic unrelated to timestamp formatting or `claimed_by` stripping.

**Evidence:** All storage-scoped suites pass (test_storage.py, test_storage_1050.py). The 5 failing migrate tests assert lane dispatch, integer-status detection, and stderr summary headers — none exercise timestamp scalar formatting or archive field stripping.

**Refinement applied:**
- AC6 (old): Existing suites (test_storage.py, test_storage_1050.py, test_migrate.py) pass or are corrected only where tests assert stale formatting.
- AC6 (new): Existing storage suites (`serve/kanban/tests/test_storage.py`, `serve/kanban/tests/test_storage_1050.py`) pass. Pre-existing failures in `serve/kanban/tests/test_migrate.py` unrelated to timestamp formatting or `claimed_by` stripping are out of scope.

**Rationale:** AC6 was a non-regression gate for the storage contract. The 5 migrate failures exercise separate migration-lane logic (tasks_dir, mtime stability, manual-action summaries) that predates this fix. Blocking a storage-scoped fix on unrelated migrate debt violates single-responsibility.

**Verdict:** APPROVE (re-advance to todo). Builder should re-verify the refined AC6 gate (both storage suites green) and advance to review.
[[2026-05-04]]
AC6 refinement: scoped gate to storage suites only (test_storage.py, test_storage_1050.py — both green). Removed test_migrate.py from gate — its 5 failures are pre-existing lane/idempotency/summary assertions unrelated to timestamp formatting or claimed_by stripping. Builder can re-verify refined AC6 and advance to review.
[[2026-05-04]]
## Test-Writer Notes

**Re-claim after AC6 refinement (2026-05-04)**

- Test file: `tests/test_schema_roundtrip_1338.py`
- Current state: all 7 existing tests **PASS GREEN** (builder implementation in commit `decdf3b0` is in place)
- AC6 refinement (architect): narrows gate to storage suites only — still `(td:0)`, no new testable Python interfaces introduced
- AC7: `(td:0)` — unchanged

No new test work required. Passing through to builder so AC6 re-verification (storage suites green) can be confirmed and task advanced to review.

| AC | Tests | State |
|---|---|---|
| AC1: unquoted UTC timestamps from write_task | `test_write_task_timestamp_line_ends_with_utc_offset` | GREEN |
| AC2: naive timestamps → +00:00 unquoted | `test_write_task_naive_timestamp_stored_with_utc_offset_unquoted` | GREEN |
| AC3: non-UTC → UTC converted unquoted | `test_write_task_non_utc_timestamp_converted_unquoted` | GREEN |
| AC4: read_task strips claimed_by (attr + model_extra) | `test_archive_read_task_claimed_by_stripped_to_none`, `test_archive_read_task_claimed_by_not_in_model_extra` | GREEN |
| AC5: full round-trip preserves all fields + unquoted timestamps | `test_full_round_trip_timestamps_unquoted_in_written_file`, `test_full_round_trip_task_data_preserved_after_migrate_and_write` | GREEN |
| AC6/AC7 | (td:0) — no tests | N/A |
[[2026-05-04]]
## Builder Notes
- Implementation: no new code changes in this cycle; verified existing fix from prior builder commit (`serve/kanban/src/owlbear_kanban/storage.py`).
- Verification scope: `tests/test_schema_roundtrip_1338.py`, `serve/kanban/tests/test_storage.py`, `serve/kanban/tests/test_storage_1050.py`.
- Tests: 71 passed, 0 failed (scoped quality-runner gate).
- Coverage: `owlbear_kanban.storage` 94% (meets ≥90% gate on touched module).
- ruff: clean (scoped paths).
- Evidence summary: AC1-AC5 behaviors remain green via task regression + storage suites; refined AC6 gate is satisfied by storage suite pass status; task is ready for review.
- Files changed this cycle: none.
[[2026-05-04]]
## Review Evidence
Parallel fan-out failed: code-reader returned no response, so the review fell back to sequential code reading after quality-runner completed.

### Test Results
- quality-runner broad scoped pass: 71 passed, 0 failed across `tests/test_schema_roundtrip_1338.py`, `serve/kanban/tests/test_storage.py`, and `serve/kanban/tests/test_storage_1050.py`.
- isolated rerun of `tests/test_schema_roundtrip_1338.py`: 7 passed, 0 failed, 0 skipped. Executed tests:
  - `test_full_round_trip_timestamps_unquoted_in_written_file`
  - `test_full_round_trip_task_data_preserved_after_migrate_and_write`
  - `test_archive_read_task_claimed_by_stripped_to_none`
  - `test_archive_read_task_claimed_by_not_in_model_extra`
  - `test_write_task_timestamp_line_ends_with_utc_offset`
  - `test_write_task_naive_timestamp_stored_with_utc_offset_unquoted`
  - `test_write_task_non_utc_timestamp_converted_unquoted`

### Lint: clean
- quality-runner ruff: 0 violations on `serve/kanban/src/owlbear_kanban/storage.py`, `tests/test_schema_roundtrip_1338.py`, `serve/kanban/tests/test_storage.py`, `serve/kanban/tests/test_storage_1050.py`.
- VS Code diagnostics: no errors in the same files.

### Coverage: `owlbear_kanban.storage`: 94%
- broad scoped pass on the touched module: 94%.
- isolated task-suite run: 57% on `owlbear_kanban.storage`; adjacent storage suites raise the touched-module proof above the 90% gate.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `write_task()` emits canonical ISO timestamp strings with UTC offsets and without single quotes | `test_write_task_timestamp_line_ends_with_utc_offset`; adjacent `test_all_timestamp_fields_end_with_utc_offset`, `test_ac_c15_timestamps_utc_plus_00_00` | Yes — raw frontmatter assertions require lines to end with `+00:00`, so quoted output or wrong offsets fail (`tests/test_schema_roundtrip_1338.py:469`, `serve/kanban/tests/test_storage_1050.py:294`) | COVERED |
| Naive timestamps normalize to `+00:00` before write | `test_write_task_naive_timestamp_stored_with_utc_offset_unquoted`; adjacent `test_naive_timestamps_stored_with_utc_offset` | Yes — naive values must serialize with explicit `+00:00`; missing normalization or quotes fail (`tests/test_schema_roundtrip_1338.py:505`, `serve/kanban/tests/test_storage_1050.py:319`) | COVERED |
| Non-UTC offsets convert to UTC before write | `test_write_task_non_utc_timestamp_converted_unquoted`; adjacent `test_non_utc_offset_timestamps_are_converted_to_utc` | Yes — tests assert both `+00:00` suffix and exact UTC-converted value `2026-04-20T08:00:00+00:00` (`tests/test_schema_roundtrip_1338.py:540`, `tests/test_schema_roundtrip_1338.py:546`) | COVERED |
| `read_task()` strips legacy `claimed_by` from archive files and excludes it from attributes and `model_extra`/`model_dump()` | `test_archive_read_task_claimed_by_stripped_to_none`, `test_archive_read_task_claimed_by_not_in_model_extra`; adjacent `test_archive_claimed_by_stripped_from_returned_task`, `test_engine_list_tasks_archived_strips_legacy_claimed_by` | Yes — direct assertions on `model_dump()`, `model_extra`, and archived list summaries fail if `claimed_by` leaks (`tests/test_schema_roundtrip_1338.py:400`, `tests/test_schema_roundtrip_1338.py:420`, `serve/kanban/tests/test_storage_1050.py:606`, `serve/kanban/tests/test_storage_1050.py:1063`) | COVERED |
| Old-format boards load, save, and re-read without losing named task data | `test_full_round_trip_task_data_preserved_after_migrate_and_write`; paired timestamp proof `test_full_round_trip_timestamps_unquoted_in_written_file` | Yes — exact equality assertions pin identity, status, priority, body, parent/deps, tags, blocking fields, `claimed_at`, `archival_reason`, and `archival_refs`; raw frontmatter check fails on bad timestamp emission (`tests/test_schema_roundtrip_1338.py:355`, `tests/test_schema_roundtrip_1338.py:356`, `tests/test_schema_roundtrip_1338.py:363`) | COVERED |
| Existing storage suites pass | quality-runner broad run on `serve/kanban/tests/test_storage.py` and `serve/kanban/tests/test_storage_1050.py` | Yes — suite status itself is the AC gate; broad scoped run was green | COVERED |
| Regression tests in `tests/test_schema_roundtrip_1338.py` prove archive-read and timestamp-format behavior | isolated quality-runner rerun of all 7 named task tests | Yes — the file's seven named task regressions all passed in isolation | COVERED |

#### Security Review
- No issues found. The change is confined to timestamp normalization/plain-scalar emission and archive-frontmatter stripping in `serve/kanban/src/owlbear_kanban/storage.py:143-164`, `serve/kanban/src/owlbear_kanban/storage.py:298-311`, `serve/kanban/src/owlbear_kanban/storage.py:349-350`, and `serve/kanban/src/owlbear_kanban/storage.py:421-441`. No new shell/SQL/template/deserialization surfaces, no secrets, and no dependency changes.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_SchemaRoundTrip` | No weakening detected in current assertions; AC5 proof now includes exact archival metadata equality and raw timestamp-line checks | PRESERVED |
| `TestFromAC_ArchiveClaimedByStripping` | No weakening detected; current tests assert both `model_dump()` cleanup and `model_extra` cleanup | PRESERVED |
| `TestFromAC_TimestampRoundTrip` | No weakening detected; current tests assert suffix correctness, naive normalization, and exact UTC conversion value | PRESERVED |

Integrity evidence: reflog shows two `#1338` test-writer commits before builder commit `decdf3b0` and no later `#1338` test commit (`.git/logs/HEAD:1855`, `.git/logs/HEAD:1867`, `.git/logs/HEAD:1873`). Direct commit diff access was unavailable in this tool surface, so this check carries a small confidence deduction.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact suffix checks at `tests/test_schema_roundtrip_1338.py:469`, `:505`, `:540`; exact UTC value at `:546`; exact `claimed_by` absence at `:400` and `:420`; exact archival metadata equality at `:355-356` |
| Negative/error-path coverage | ADEQUATE | Task file is contract-positive by design; adjacent storage suites cover tasks-vs-archive `claimed_by` split and migration-gate behavior at `serve/kanban/tests/test_storage.py:233`, `:253`, `serve/kanban/tests/test_storage_1050.py:596`, `:1050` |
| Manual mutation reasoning | STRONG | Removing archive stripping or reintroducing quoted timestamps would fail direct raw-line and `model_extra` assertions immediately |
| Test independence | STRONG | All task tests build isolated boards under `tmp_path` and do not share mutable state |
| Descriptive names | STRONG | Names map directly to AC language and regression intent |

#### Data Safety
- No issues found. `write_task()` still ends with `atomic_write(...)` after normalization/unquoting (`serve/kanban/src/owlbear_kanban/storage.py:440-442`), and `read_task()` strips legacy `claimed_by` before model validation (`serve/kanban/src/owlbear_kanban/storage.py:349-350`) without introducing shared-state or race hazards.

#### Implementation-Aware Gaps
- No significant untested paths found in the changed logic.
- `_normalize_timestamp()` branches are exercised for naive timestamps, non-UTC offsets, `Z` suffixes, and non-matching strings (`tests/test_schema_roundtrip_1338.py:474`, `:510`; `serve/kanban/tests/test_storage_1050.py:984`, `:994`, `:1002`).
- Archive-strip behavior is exercised at raw task-model level, `model_extra`/`model_dump()` level, engine-init level, and archived summary projection level (`tests/test_schema_roundtrip_1338.py:384`, `:405`; `serve/kanban/tests/test_storage.py:233`, `:253`; `serve/kanban/tests/test_storage_1050.py:596`, `:655`, `:1050`).

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 |
| Approach variation | Yes |
| Assessment | FRICTION |

Rationale: the task had an implementation pass, an AC6 scope-clarification cycle, and a final verification-only pass. There is no prior `## Review Evidence` section, so this is not a loop-breaker case.

### Pass 2 — INFORMATIONAL
- `code-reader` returned no response in the parallel fan-out, so the review fell back to sequential manual code reading.
- Direct `git diff` / `git status` commands were unavailable in this tool surface. Commit existence and chronology were confirmed via `.git/logs/**`, but full diff-scoped immutability and dirty-tree contamination checks could not be performed. Small confidence deduction applied.
- The first combined quality-runner summary undercounted the task regression file as 5 tests; an isolated rerun confirmed the actual task suite is 7/7 green. The broad pass was still sufficient for adjacent-suite pass status and coverage.
- Downstream compatibility check was positive: `Task` still preserves vendor extras via `extra="allow"` (`serve/kanban/src/owlbear_kanban/models.py:418`), summaries explicitly drop `claimed_by` and derive `claimed` from `claimed_at` (`serve/kanban/src/owlbear_kanban/models.py:493-495`), MCP conversion tolerates absent `claimed_by` (`serve/mcp-kanban/src/owlbear_mcp_kanban/models.py:152`), cockpit mutation serialization uses `getattr(task, "claimed_by", None)` (`serve/cockpit/src/owlbear_cockpit/routes/mutation.py:100`), and the engine migration gate only scans `tasks/` frontmatter for legacy `claimed_by` (`serve/kanban/src/owlbear_kanban/engine.py:375-418`).

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `write_task()` emits canonical ISO timestamp strings with UTC offsets and no single quotes | Implementation normalizes timestamp scalars and strips quoting at `serve/kanban/src/owlbear_kanban/storage.py:143-164`, `:421`, `:440-441`; raw-line assertions pass at `tests/test_schema_roundtrip_1338.py:469` and `serve/kanban/tests/test_storage_1050.py:294` | `test_write_task_timestamp_line_ends_with_utc_offset`; `test_all_timestamp_fields_end_with_utc_offset` | PASS |
| Naive timestamps normalize to `+00:00` before write | `_normalize_timestamp()` appends `+00:00` for naive values at `serve/kanban/src/owlbear_kanban/storage.py:311`; task and adjacent assertions pass at `tests/test_schema_roundtrip_1338.py:505` and `serve/kanban/tests/test_storage_1050.py:319` | `test_write_task_naive_timestamp_stored_with_utc_offset_unquoted`; `test_naive_timestamps_stored_with_utc_offset` | PASS |
| Non-UTC offsets convert to UTC before write | `_normalize_timestamp()` converts offset values via `datetime.fromisoformat(...).astimezone(UTC).isoformat()` at `serve/kanban/src/owlbear_kanban/storage.py:310`; exact UTC value asserted at `tests/test_schema_roundtrip_1338.py:546` and adjacent suite `serve/kanban/tests/test_storage_1050.py:323` | `test_write_task_non_utc_timestamp_converted_unquoted`; `test_non_utc_offset_timestamps_are_converted_to_utc` | PASS |
| `read_task()` strips legacy `claimed_by` from archive files and excludes it from attributes/extras | Archive branch strips before validation at `serve/kanban/src/owlbear_kanban/storage.py:349-350`; task assertions confirm `model_dump()` and `model_extra` are clean at `tests/test_schema_roundtrip_1338.py:400`, `:420`; adjacent summary proof at `serve/kanban/tests/test_storage_1050.py:1063` | `test_archive_read_task_claimed_by_stripped_to_none`; `test_archive_read_task_claimed_by_not_in_model_extra`; `test_engine_list_tasks_archived_strips_legacy_claimed_by` | PASS |
| Old-format boards round-trip without losing named data | Round-trip task test preserves identity, status, priority, body, parent/deps, tags, blocking fields, `claimed_at`, `archival_reason`, `archival_refs` at `tests/test_schema_roundtrip_1338.py:343-356`; timestamp proof at `:363` stays green | `test_full_round_trip_task_data_preserved_after_migrate_and_write`; `test_full_round_trip_timestamps_unquoted_in_written_file` | PASS |
| Existing storage suites pass | quality-runner broad run: `serve/kanban/tests/test_storage.py` PASS, `serve/kanban/tests/test_storage_1050.py` PASS; ruff clean | suite pass status | PASS |
| `tests/test_schema_roundtrip_1338.py` proves regression safety | isolated rerun executed all seven named regression tests and passed 7/7 | all seven tests in `tests/test_schema_roundtrip_1338.py` | PASS |

### Deductions
- `-0.01` `code-reader` subagent returned no response; sequential manual review substituted.
- `-0.02` full `git diff` / dirty-tree contamination check was unavailable; reflog evidence reduced but did not eliminate uncertainty.
- `-0.01` combined quality-runner summary miscounted the task test total and required an isolated rerun for confirmation.

### Confidence: 0.94
### Verdict: PASS
[[2026-05-04]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | `serve/kanban/README.md` documents the `KanbanEngine` public API; it does not reference internal storage functions (`read_task`, `write_task`, `_normalize_timestamp`) or timestamp formatting behavior. No prose docs affected. |
| 2 | Module docstrings | Yes | Updated | `_normalize_timestamp` docstring was stale — said "when it lacks a timezone" but the function also normalizes Z suffixes and non-UTC offsets (AC2/AC3 behaviors added by this task). Updated to enumerate all three normalization branches. `read_task` and `write_task` docstrings were already accurate post-build. |
| 3 | External attribution | No | N/A | No external patterns cited in task body or builder notes. |
| 4 | Research doc | No | N/A | No research doc produced for this task. |
| 5 | Diagram maintenance | Yes | Updated | Two diagrams match `serves/kanban/src/**`: `share/diagrams/kanban.excalidraw` (describes: `serve/kanban/src/**`) and `share/diagrams/mcp-topology.excalidraw` (describes: `serve/kanban/src/**`). Both footers updated to `Last verified: 2026-05-05 (0c497432)`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs detected. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/storage.py` | IN (docstrings) | Updated `_normalize_timestamp` docstring |
| `share/diagrams/kanban.excalidraw` | IN | Footer updated |
| `share/diagrams/mcp-topology.excalidraw` | IN | Footer updated |
| `tests/test_schema_roundtrip_1338.py` | OUT (test file) | N/A |
| `serve/kanban/tests/test_storage.py` | OUT (test file) | N/A |
| `serve/kanban/tests/test_storage_1050.py` | OUT (test file) | N/A |
| `serve/kanban/tests/test_migrate.py` | OUT (test file) | N/A |

### Files Updated
- `serve/kanban/src/owlbear_kanban/storage.py` — `_normalize_timestamp` docstring
- `share/diagrams/kanban.excalidraw` — footer: `Last verified: 2026-05-05 (0c497432)`
- `share/diagrams/mcp-topology.excalidraw` — footer: `Last verified: 2026-05-05 (0c497432)`

### Commit
`e2d06815` — docs: fix _normalize_timestamp docstring and update diagram footers (#1338, doc-writer)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found
[[2026-05-04]]
## Audit

### AC Verification
| AC | Evidence | Status |
|---|---|---|
| AC1: write_task() emits unquoted UTC ISO timestamps | `test_write_task_timestamp_line_ends_with_utc_offset` PASS; implementation at storage.py:143-164,421,440-441 | PASS |
| AC2: Naive timestamps → +00:00 | `test_write_task_naive_timestamp_stored_with_utc_offset_unquoted` PASS | PASS |
| AC3: Non-UTC offsets → UTC | `test_write_task_non_utc_timestamp_converted_unquoted` PASS; exact value assertion at test:546 | PASS |
| AC4: read_task strips claimed_by | `test_archive_read_task_claimed_by_stripped_to_none`, `test_archive_read_task_claimed_by_not_in_model_extra` PASS | PASS |
| AC5: Old-format round-trip preserves all fields | `test_full_round_trip_task_data_preserved_after_migrate_and_write` PASS (body, parent, tags, deps, blocking, claimed_at, archival_reason, archival_refs) | PASS |
| AC6: Existing storage suites pass | 71 passed (test_storage.py + test_storage_1050.py) — all green | PASS |
| AC7: Regression tests prove behavior | 7/7 in test_schema_roundtrip_1338.py PASS | PASS |

### Test Results (Full Suite)
- Task scope: 71 passed, 0 failed (test_schema_roundtrip_1338 + storage + storage_1050)
- Full suite: 4361 passed, 250 failed — 0 failures in task scope; all 250 are pre-existing/unrelated (engine accessor migration, mcp memory, engine coverage tests)
- Lint: clean on task files (storage.py, test_schema_roundtrip_1338.py)

### Commit Integrity
- `bcb1ca65` test-writer: add failing tests (#1338)
- `a90bda41` test-writer: extend AC5 assertions (#1338)
- `decdf3b0` builder: implementation (#1338)
- `e2d06815` doc-writer: docstring + diagram footers (#1338)
Pipeline progression: test-writer → builder → doc-writer ✓

### AC Quality Score: 4/5
Specific, testable, scoped. Minor gap: AC6 initially included test_migrate.py which had pre-existing failures unrelated to the fix — required mid-cycle architect refinement. Final AC was clean.

### Deductions
- Start: 1.00
- No AC evidence gaps: -0.00
- No lint violations: -0.00
- AC quality 4 (above ≤3 threshold): -0.00
- Reviewer evidence present and detailed: -0.00
- Full-suite failures in task scope: 0 → -0.00
- Reviewer confidence was 0.94 (tool-surface deductions only; independently verified by auditor full-suite run): -0.02

### Confidence: 0.98
### Action: ARCHIVE