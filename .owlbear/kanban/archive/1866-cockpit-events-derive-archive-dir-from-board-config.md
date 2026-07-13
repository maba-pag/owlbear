---
id: 1866
title: 'Cockpit events: derive archive_dir from board_config'
status: archived
priority: medium
created: 2026-05-25T00:06:59.320927+02:00
updated: 2026-05-25T02:06:36.046621+02:00
tags:
  - scope:cockpit-backend
  - boundary-audit
parent:
depends_on: []
ac:
  - KanbanEngine exposes a public read-only `archive_dir` property returning 
    `Path`, delegating to the existing `self._archive_dir` attribute (same 
    pattern as `tasks_dir` property at engine.py:518)
  - events.py `_stream()` resolves archive_dir via `engine.archive_dir` — remove
    the hardcoded `kanban_dir / "archive"` literal
  - All tests in tests/test_cockpit_events.py and 
    tests/test_cockpit_cache_sse.py pass without modification (default config 
    path is unchanged)
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Replace hardcoded `kanban_dir / "archive"` in `serve/cockpit/src/owlbear_cockpit/routes/events.py` with `engine.board_config().paths.archive_dir` (or a new public `archive_dir` property). Currently the path is hardcoded as "archive" but `config.paths.archive_dir` is configurable — a non-default config would silently break SSE events for archived tasks.

Ref: .owlbear/research/cockpit-api-boundary-audit.md — Finding 2

## Research
- Research doc: .owlbear/research/cockpit-api-boundary-audit.md (Finding 2)
- Sources: 1 (existing boundary audit), codebase validation
- Recommendation: Add public `archive_dir` property to KanbanEngine (Option A) — consistent with `tasks_dir` property, avoids deep copy from `board_config()` (confidence: 0.85)
- Scope: 3-line property addition to engine + 1-line change in events.py
- Challenge: skipped (trivial T1 fix, pre-validated by boundary audit challenger)

[[2026-05-25T00:19:46+02:00]]
## Research
Validation pass — existing boundary audit doc (.owlbear/research/cockpit-api-boundary-audit.md Finding 2) already covers this. Confirmed codebase state unchanged: `_archive_dir` is private, no public property exists, events.py line 134 still hardcodes "archive".

Recommendation: Option A — add 3-line `archive_dir` property to KanbanEngine (mirrors existing `tasks_dir`), then consume in events.py. T1 trivial fix, no DR needed. AC written. Confidence: 0.85.

[[2026-05-25T00:41:10+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: expose configured archive path to consumers |
| Interface clarity | PASS | AC specifies exact property name, type, delegation target |
| Dependency correctness | PASS | No new dependencies; events.py already imports KanbanEngine |
| Module layering | PASS | Engine exposes path (lower layer) → cockpit consumes (upper layer) |
| TDD compliance | PASS | Proof bundle smoke — test-writer will write accessor smoke test |
| KISS/YAGNI | PASS | 3-line property + 1-line consumer change; minimal |
| Premise challenge | PASS | Bug is real: non-default archive_dir silently breaks SSE |
| Pattern consistency | PASS | Mirrors existing tasks_dir property (engine.py:518) |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | kanban-engine property + cockpit consumer — single fix direction |

### Challenge Results
- Challenger: reconsider (confidence 0.58)
- Issues raised: AC wording imprecision, behavioral assumption, coverage gap
- Architect response: revised AC wording (removed vague \"consistent with\" and \"or derives from\" phrasing); rebutted behavioral concern (fix is intentional — engine treats archive_dir as configurable, cockpit hardcoding is the bug); rebutted topology debate (containment tests ≠ constant-path tests)

### Proof-Bundle Validation
- Planner assignment: null (unset)
- Final bundle: smoke
- Existing proof scope: N/A
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — single obvious approach (mirror tasks_dir property pattern)

### Verdict: APPROVE
### Action Taken: Refined AC for precision, assigned proof_bundle=smoke, advanced to todo

[[2026-05-25T00:56:51+02:00]]
## Test-Writer Notes
- Test file: tests/test_cockpit_events_1866.py
- Proof bundle: smoke — one smoke test per AC line
- Classes: TestFromAC_EngineArchiveDirProperty, TestFromAC_EventsUsesEngineArchiveDir, TestFromAC_DefaultConfigPathUnchanged
- Total: 3 tests, all FAIL (RED confirmed by quality-runner)

| AC | Test | Failure |
|----|------|---------|
| AC1: engine.archive_dir property | test_engine_exposes_archive_dir_property | AttributeError: no attribute 'archive_dir' |
| AC2: _stream() uses engine.archive_dir | test_stream_uses_engine_archive_dir_not_hardcoded | AssertionError: hardcoded path captured instead |
| AC3: default path unchanged (regression guard) | test_default_archive_dir_matches_existing_hardcoded_path | AttributeError: no attribute 'archive_dir' |

- Lint: ruff clean
- Commit: f89583ad

[[2026-05-25T01:09:04+02:00]]
## Builder Notes
- Implementation: Updated `serve/kanban/src/owlbear_kanban/engine.py` to expose public read-only `archive_dir: Path` delegating to `_archive_dir`; updated `serve/cockpit/src/owlbear_cockpit/routes/events.py` `_stream()` to resolve archive path via `engine.archive_dir` instead of hardcoded `kanban_dir / "archive"`.
- RED verification: `tests/test_cockpit_events_1866.py` had 3/3 failing `TestFromAC_*` tests pre-change (missing `archive_dir` property + hardcoded archive path assertion failure).
- GREEN verification (quality-runner, scoped): 89 passed, 0 failed across `tests/test_cockpit_events_1866.py`, `tests/test_cockpit_events.py`, `tests/test_cockpit_cache_sse.py`.
- Coverage (quality-runner scoped report): `owlbear_cockpit.routes.events` 100%, `owlbear_kanban.engine` 35%, overall 39% (smoke bundle task; verification focused on scoped behavioral proof).
- Ruff: clean (target files + task test file).
- Evidence summary: AC1 satisfied by new public `archive_dir` property, AC2 satisfied by events stream consuming engine-provided archive path, AC3 guarded by unchanged default-path behavior and passing durable cockpit events/cache SSE tests.
- Commit: `5a601f6d01289ab7eeb6fe8749de1e2126a6bc44`.

[[2026-05-25T01:19:16+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1866 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first and found sufficient and internally consistent: quality-runner reported 89 passed, 0 failed across `tests/test_cockpit_events_1866.py`, `tests/test_cockpit_events.py`, and `tests/test_cockpit_cache_sse.py`; ruff was clean; no independent rerun was needed.
- AC evidence map:

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| 1 | `serve/kanban/src/owlbear_kanban/engine.py:449-451` derives `_archive_dir` from config and validates containment; `serve/kanban/src/owlbear_kanban/engine.py:523-525` exposes read-only `archive_dir` delegating to `_archive_dir` | `tests/test_cockpit_events_1866.py:59-65` asserts public `Path` return; direct code inspection confirms read-only property syntax | PASS |
| 2 | `serve/cockpit/src/owlbear_cockpit/routes/events.py:32-50` and `serve/cockpit/src/owlbear_cockpit/routes/events.py:57-65` thread `archive_dir` through watch filtering and classification; `serve/cockpit/src/owlbear_cockpit/routes/events.py:134` resolves `engine.archive_dir` instead of hardcoded `kanban_dir / "archive"` | `tests/test_cockpit_events_1866.py:71-116` injects a non-default `custom_archive` and captures the `_build_watch_filter` argument, so the test fails if `_stream()` hardcodes `"archive"`; durable archive-watch coverage remains in `tests/test_cockpit_events.py:1046-1059`, `tests/test_cockpit_events.py:1273-1310`, and `tests/test_cockpit_cache_sse.py:787-830` | PASS |
| 3 | Default behavior remains unchanged because engine still resolves archive under the board root from config paths and the SSE route now consumes that same engine surface | `tests/test_cockpit_events_1866.py:123-136` asserts default `kanban_dir / "archive"`; builder evidence shows the unmodified durable suites still pass, including assertions that assume the default archive location in `tests/test_cockpit_events.py:1055` and `tests/test_cockpit_cache_sse.py:794`, `tests/test_cockpit_cache_sse.py:817`, `tests/test_cockpit_cache_sse.py:849` | PASS |
- Safety/security: no new trust boundary; the consumed archive path remains engine-owned and containment-validated before use.

## Observations
- No blocking findings.
- The task-scoped AC2 proof is behaviorally strong: it asserts the exact path forwarded into the SSE watch surface, not just that the request returns 200.

[[2026-05-25T01:36:33+02:00]]
## Docs Gate
- Item 1 (README Verification): N/A — no task-caused docs drift. `serve/kanban/README.md` methods table omits properties by convention (`tasks_dir` also absent; consistent pattern). `serve/cockpit/README.md` does not document events.py internals. No public surface changed by this fix.
- Item 2 (External Attribution): N/A — sources are existing internal boundary-audit doc and codebase validation only.
- Item 3 (Research Doc): PASS — `.owlbear/research/cockpit-api-boundary-audit.md` exists; linked from task body ("Ref: … Finding 2").
- Item 4 (Deletion Detection): PASS — no files deleted; no orphaned references.
- Files updated: none required.
- Scratch cleanup: no 1866-* files found.

[[2026-05-25T02:06:36+02:00]]
## Audit

### Regression Detection
Quality-runner full-suite: 1358 passed, 0 failed, lint clean. No regressions.

### Intent Verification
Changed files: `serve/kanban/src/owlbear_kanban/engine.py` (5-line property addition), `serve/cockpit/src/owlbear_cockpit/routes/events.py` (1-line substitution). Both in intended domains (kanban engine + cockpit backend). No extraneous scope. Implementation direction matches stated purpose: expose configured archive path and consume it in SSE stream.

### Architect Quality
Score: 5/5 — AC lines are specific (exact property name, type, delegation target), complete (regression guard included), and led to clean implementation. Challenger concerns addressed in revision.

### Commit Integrity
- Test-writer: `f89583ad` — RED tests committed
- Builder: `5a601f6d` — GREEN implementation committed
- Reviewer: advanced to docs (no code commit expected)
- Doc-writer: no files required (confirmed in docs gate)

### Deductions
None.

### Confidence: 1.00
### Action: ARCHIVE
