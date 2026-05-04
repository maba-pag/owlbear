---
id: 1338
title: Fix storage round-trip timestamp and archive claimed_by leaks
status: backlog
priority: needed
created: 2026-05-04T15:00:05.755705+00:00
updated: 2026-05-04T20:25:34.896567+00:00
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