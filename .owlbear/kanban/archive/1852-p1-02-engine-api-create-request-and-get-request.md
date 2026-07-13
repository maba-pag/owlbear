---
id: 1852
title: 'P1-02: Engine API — create_request and get_request'
status: archived
priority: medium
created: 2026-05-24T20:58:06.152479+02:00
updated: 2026-05-25T05:44:18.600747+02:00
tags:
  - phase-1
  - scope:kanban
  - api
parent: 1850
depends_on:
  - 1851
ac:
  - create_request(task_id, kind, title, summary, agent, *, options=None, 
    body="") generates request_id (UUID4) and created_at (machine-set, tz-aware 
    ISO 8601), writes decisions/pending/{request_id}.md atomically, and returns 
    an object exposing the validated model fields and body string.
  - 'The written file has YAML frontmatter from the Pydantic model with resolution
    block (selected_option_id: null, free_text: null; resolved_at omitted in pending
    files) followed by markdown body below the closing delimiter.'
  - create_request sets task.blocked=True with block_reason="DR pending" on the 
    task identified by task_id; if blocking fails, rolls back by deleting the 
    created file before re-raising.
  - get_request(request_id) searches pending/ then resolved/ for 
    {request_id}.md; returns validated model fields and body when found; raises 
    NotFoundError when absent from both; raises ValidationError when file exists
    but fails parsing or model validation.
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1850 and `.owlbear/briefs/draft-decision-request-data-model/brief.md`

## Scope

**In scope:**
- `create_request` engine function with atomic file creation
- UUID4 generation for request_id
- YAML frontmatter serialization from Pydantic model
- Task blocking on DR creation
- `get_request` engine function searching both directories
- Rollback (delete file) if task blocking fails

**Out of scope:**
- Resolution logic (P1-03)
- List/filter operations (P1-04)
- Sweep (P1-04)
- MCP/Cockpit layers

## Test scope
`serve/kanban/tests/`

[[2026-05-25T02:30:17+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Two closely-related CRUD functions (create+get) for same entity |
| Interface clarity | PASS | After refinement: inputs, outputs, error paths, serialization details all specified |
| Dependency correctness | PASS | #1851 archived/completed; Pydantic models exist in request_models.py |
| Module layering | PASS | kanban engine internal; no upward imports |
| TDD compliance | PASS | Test scope: serve/kanban/tests/ |
| KISS/YAGNI | PASS | Only create+get; list/resolve deferred to P1-03/P1-04 per Brief sequence |
| Premise challenge | PASS | Brief-driven; replaces unstructured DR system |
| Pattern consistency | PASS | Follows existing O_EXCL + rollback pattern from decisions.py create_dr |
| Security surface | PASS | UUID4 generated internally (not caller-supplied); path derived from engine _kanban_dir + topology decisions_dir |
| Single domain | PASS | kanban only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| create_request file write | Disk full / permission error | OSError | No (propagates) | Creation fails cleanly |
| create_request edit_task | Task not found / concurrent edit | FileNotFoundError / ConcurrencyError | Yes — rollback (delete file) per AC3 | No orphan file |
| get_request parse | Corrupt YAML / invalid fields | ValidationError | Yes per AC4 | Surfaced to caller |

### Challenge Results
- Challenger: reconsider (confidence 0.39)
- Findings: (1) AC1 optionality gap, (2) body field missing from model surface, (3) precedent overreach, (4) \"parent task\" terminology ambiguity, (5) pending-resolution serialization unclear, (6) malformed-file read gap
- Architect response: Accepted findings 1,2,4,5,6 — refined AC from 3 to 4 lines. Rebutted finding 3 (precedent proves O_EXCL+rollback pattern; differences are obvious from AC). Added ValidationError path for corrupt files, clarified resolution block serialization, specified machine-set timestamps, marked optional params, clarified body in return value.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC from 3 to 4 lines addressing challenger findings (optionality, body field, terminology, serialization, malformed-file path), advanced to todo.

[[2026-05-25T03:19:45+02:00]]
## Test-Writer Notes
- Test file: `serve/kanban/tests/test_engine_requests_1852.py`
- Classes: `TestFromAC_CreateRequest`, `TestFromAC_GetRequest`
- Tests per category:
  - Happy path: 10 (returns model fields, writes file, finds in pending/resolved, body/fields exposed)
  - Edge cases: 6 (unique UUIDs, body defaults, empty body, pending-first search, action kind, tz-aware created_at)
  - Error paths: 5 (rollback on block failure, rollback re-raises, not-found, corrupt YAML, invalid model fields)
  - Boundary: 5 (UUID4 validity, filename = request_id.md, resolved_at absent, resolution nulls, body below delimiter)
- Total: 26 tests, ALL FAIL (RED phase confirmed)
- Lint: ruff clean
- AC coverage:
  - AC1 → 9 tests (return object with fields, UUID4, tz-aware created_at, file in pending, filename, body string, body default, unique UUIDs)
  - AC2 → 5 tests (frontmatter delimiters, resolution.selected_option_id null, resolution.free_text null, resolved_at absent, body below delimiter)
  - AC3 → 3 tests (blocks task, rollback deletes file, rollback re-raises)
  - AC4 → 9 tests (found pending, found resolved, fields+body, not-found error, corrupt YAML, invalid model, pending-first, empty body, action kind)
- Commit: e3477a4e

[[2026-05-25T03:38:07+02:00]]
## Builder Notes
- Implementation: added request retrieval/creation APIs in serve/kanban/src/owlbear_kanban/engine.py and added typed response model in serve/kanban/src/owlbear_kanban/request_models.py.
- Files changed: serve/kanban/src/owlbear_kanban/engine.py, serve/kanban/src/owlbear_kanban/request_models.py.
- Approach: validate request payloads with existing discriminated Pydantic request models, write pending request files atomically via O_EXCL using UUID4 filenames, serialize YAML frontmatter + markdown body, block task with rollback-on-failure, and read pending/resolved files with strict parse/validation error mapping.
- Tests (RED pre-check): quality-runner scoped run on serve/kanban/tests/test_engine_requests_1852.py -> 0 passed / 26 failed (missing create_request/get_request confirmed).
- Tests (GREEN verify): quality-runner scoped run on serve/kanban/tests/test_engine_requests_1852.py -> 26 passed / 0 failed.
- Lint: quality-runner reported ruff clean (no violations) for engine.py, request_models.py, and serve/kanban/tests/test_engine_requests_1852.py.
- Coverage: quality-runner reported overall_pct 90 with modules owlbe ar_kanban.request_models 90%, owlbear_kanban.engine 23% under scoped task tests.
- Module-level durable tests: no canonical module-level request engine test file found in serve/kanban/tests beyond task-scoped serve/kanban/tests/test_engine_requests_1852.py (skip).
- Commit: bb67a3f9 (feat: implement request create/get API (#1852, builder)).

[[2026-05-25T04:26:41+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1852 -> todo | returned-object AC proof is incomplete for AC1 and AC4.
- Builder evidence reviewed first: task-local quality-runner GREEN summary (26 passed / 0 failed), ruff clean on touched files, and coverage summary were present and internally consistent.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1 | `create_request` proof is incomplete for the returned record surface. The contract says the API returns the validated model fields plus body, but the task suite never asserts returned `options` or returned `resolution`, so an adapter regression there could false-green. | `RequestRecord` includes `options` and `resolution` in `serve/kanban/src/owlbear_kanban/request_models.py:122`; `create_request` returns `RequestRecord.from_request(...)` in `serve/kanban/src/owlbear_kanban/engine.py:974`; the task tests in `serve/kanban/tests/test_engine_requests_1852.py:216` through `:327` assert other fields but do not inspect `result.options` or `result.resolution`. | todo |
| 2 | AC4 | `get_request` proof is incomplete for the returned record surface. The task suite proves lookup order and some returned fields, but it does not assert `summary`, `agent`, `created_at`, `options`, or `resolution` on the returned object, so `RequestRecord.from_request(...)` could regress without failing the suite. | `RequestRecord` field surface is defined in `serve/kanban/src/owlbear_kanban/request_models.py:122`; `get_request` returns that adapter in `serve/kanban/src/owlbear_kanban/engine.py:1018`; the task tests in `serve/kanban/tests/test_engine_requests_1852.py:507` through `:615` assert `task_id`, `kind`, `title`, `body`, and error paths, but not the remaining returned fields. | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add `create_request` assertions that prove the returned `RequestRecord` preserves the remaining contract fields, especially `options` and `resolution`. | serve/kanban/tests/test_engine_requests_1852.py | Finding #1; AC1; request_models.py:122 |
| 2 | test-writer | Add `get_request` assertions that prove the returned `RequestRecord` preserves `summary`, `agent`, `created_at`, `options`, and `resolution` for found requests. | serve/kanban/tests/test_engine_requests_1852.py | Finding #2; AC4; request_models.py:122 |

## Observations
- Direct file inspection found the implementation itself aligned with the current AC: `_serialize_request_content(...)` dumps the request model and strips only `resolved_at` for pending files in `serve/kanban/src/owlbear_kanban/engine.py:959`; `create_request(...)` uses `O_EXCL` and rollback-on-block-failure in `serve/kanban/src/owlbear_kanban/engine.py:974`; `get_request(...)` searches pending before resolved and maps parse/model failures to `ValidationError` in `serve/kanban/src/owlbear_kanban/engine.py:1018`.
- I did not independently rerun tests because the builder evidence packet was sufficient and internally consistent; the rejection is for proof quality, not for contradictory execution evidence.
- Challenger cross-check: `reconsider` with confidence `0.66`; it supported the returned-surface proof gap and did not support treating the AC2 frontmatter omissions as a blocking finding.

[[2026-05-25T04:46:11+02:00]]
## Test-Writer Notes
- Retry: added 6 tests for reviewer gaps. All pass against current impl.
- Builder skip: test-only retry, all tests green.
- New tests added to existing `TestFromAC_CreateRequest` and `TestFromAC_GetRequest` classes in `serve/kanban/tests/test_engine_requests_1852.py`:
  - `test_create_request_decision_returns_options` — asserts options list (option_id, recommended) on returned decision record
  - `test_create_request_action_returns_empty_options` — asserts options == [] for action kind
  - `test_create_request_returns_resolution_with_null_fields` — asserts resolution.selected_option_id and free_text are null
  - `test_get_request_returns_summary_agent_created_at` — asserts summary, agent, created_at on returned record
  - `test_get_request_decision_returns_options` — asserts full options list (option_id, confidence, recommended) for decision kind
  - `test_get_request_returns_resolution` — asserts resolution.selected_option_id and free_text from stored file
- Total: 32 tests (26 original + 6 new), all PASS (implementation already handles all fields)
- Lint: ruff clean
- Commit: 434bcf14

[[2026-05-25T04:59:17+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1852 to backlog | AC1 still lacks executable proof for the explicit O_EXCL clause.
- Builder evidence reviewed first: the original builder packet was internally consistent, and the retry added the previously-missing returned-record assertions for AC1 and AC4.
- Independent verification: reviewer quality-runner rerun passed 32 of 32 tests, reported ruff clean on the touched files, and reported coverage overall_pct 90 with owlbear_kanban.engine 23 and owlbear_kanban.request_models 90. That closes evidence-quality concerns about the retry note itself.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | create_request uses os.O_EXCL for file creation and returns RequestRecord.from_request in serve/kanban/src/owlbear_kanban/engine.py:1005 and serve/kanban/src/owlbear_kanban/engine.py:1016. | AC1 field and file-surface checks exist in serve/kanban/tests/test_engine_requests_1852.py:216, :274, :289, :302, :315, :327, :334, :351, and :363, but the task suite has no collision, overwrite, FileExistsError, or O_EXCL-targeted assertion. | FAIL |
| AC2 | Pending-file serialization strips resolved_at and writes frontmatter plus body in serve/kanban/src/owlbear_kanban/engine.py:959 through :971. | Frontmatter and body placement are covered in serve/kanban/tests/test_engine_requests_1852.py:380, :396, :410, :424, and :439. | PASS |
| AC3 | create_request blocks the task and rolls back file creation on block failure in serve/kanban/src/owlbear_kanban/engine.py:1010 through :1014. | Blocking and rollback are covered in serve/kanban/tests/test_engine_requests_1852.py:462, :476, and :499. | PASS |
| AC4 | get_request searches pending then resolved and returns RequestRecord.from_request with validation error mapping in serve/kanban/src/owlbear_kanban/engine.py:1018 through :1036. | Lookup, returned fields, body, options, resolution, and error paths are covered in serve/kanban/tests/test_engine_requests_1852.py:531, :540, :549, :570, :579, :594, :628, :640, :649, :659, :673, and :687. | PASS |

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1 | The task suite still does not provide executable proof for the explicit atomically (O_EXCL) clause. If create_request switched from os.O_EXCL to a non-exclusive writer, the current 32-test suite could still false-green. | AC1 text at .owlbear/kanban/tasks/1852-p1-02-engine-api-create-request-and-get-request.md:18; implementation at serve/kanban/src/owlbear_kanban/engine.py:1005; AC1 test surface at serve/kanban/tests/test_engine_requests_1852.py:216, :274, :289, :302, :315, :327, :334, :351, :363; no O_EXCL/FileExistsError/collision/overwrite assertions present in the task test file. | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Decide whether AC1's explicit O_EXCL clause must remain executable proof at this task boundary; if yes, refine the retry scope so the next RED/GREEN cycle includes a task test that fails when exclusive-create semantics are removed. | .owlbear/kanban/tasks/1852-p1-02-engine-api-create-request-and-get-request.md, serve/kanban/tests/test_engine_requests_1852.py | Finding #1; second review cycle loop-breaker route to backlog |

## Observations
- The retry does close the two findings from the prior review: create_request now asserts options and resolution in serve/kanban/tests/test_engine_requests_1852.py:334, :351, and :363; get_request now asserts summary, agent, created_at, options, and resolution in serve/kanban/tests/test_engine_requests_1852.py:659, :673, and :687.
- I overrode the required challenger cross-check, which returned reconsider at confidence 0.44, because the reviewer proof-sufficiency gate requires a falsifiable proof check for each explicit AC clause, and AC1 names O_EXCL directly.
- No implementation defect was found in the touched source; the rejection is for proof sufficiency only.

[[2026-05-25T05:10:02+02:00]]
## Architecture Review (re-entry after second review cycle)
### Decision: AC1 O_EXCL proof obligation

The reviewer correctly identified that AC1's explicit \"(O_EXCL)\" clause had no falsifiable test. The architect decision:

**Remove \"(O_EXCL)\" from AC1.** Rationale:
1. UUID4 collision probability is ~1 in 2^122 — O_EXCL is defense-in-depth, not primary correctness.
2. Testing exclusive-create requires mocking uuid4() to force collision — this tests mock interaction, not real system behavior.
3. The implementation correctly uses O_EXCL (confirmed by both reviews), but the mechanism is a builder implementation choice, not a user-facing contract.
4. The Brief specifies \"UUID4 filenames\" without mandating collision-proof testing.
5. 32 tests already cover all meaningful behavior: file creation, field roundtrip, blocking, rollback, lookup, validation errors.

AC1 now reads: \"...writes decisions/pending/{request_id}.md atomically, and returns...\" — atomicity is the contract; O_EXCL is the implementation.

### Evaluation (unchanged from prior review)
All 10 criteria PASS — no architecture changes since first approval.

### Proof-Bundle Validation
- Final bundle: behavioral
- Test-writer: PROCEED (retry cycle only)

### Verdict: APPROVE (AC refinement resolves loop)
### Action Taken: Removed \"(O_EXCL)\" parenthetical from AC1 to eliminate disproportionate proof obligation. Existing 32-test suite now fully satisfies all 4 AC lines. Advanced to todo for re-review.

[[2026-05-25T05:18:16+02:00]]
## Test-Writer Notes
- Retry: AC1 refined by architect (removed O_EXCL clause) — no new tests required.
- Existing 32 tests fully satisfy all 4 AC lines per architect assessment.
- quality-runner scoped run: 32 passed / 0 failed, ruff clean.
- Builder skip: test-only retry, all tests green against current impl.

[[2026-05-25T05:31:35+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1852 to docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: builder quality-runner GREEN summary reported 26 passed / 0 failed with ruff clean and coverage 90; the retry note reported 32 passed / 0 failed with ruff clean; the prior review cycle also recorded an independent quality-runner rerun with 32 passed / 0 failed and ruff clean.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `create_request` validates generated request payload, writes the pending file, and returns `RequestRecord.from_request(...)` in `serve/kanban/src/owlbear_kanban/engine.py:974-1016`; the returned record surface is defined in `serve/kanban/src/owlbear_kanban/request_models.py:122-145`. | AC1 fields, UUID4/tz-aware timestamp, pending-path write, filename, body/default body, unique ids, returned options, and returned resolution are asserted in `serve/kanban/tests/test_engine_requests_1852.py:216`, `:233`, `:248`, `:261`, `:274`, `:289`, `:302`, `:315`, `:327`, `:334`, `:351`, and `:363`. | PASS |
| AC2 | Pending-file serialization strips `resolved_at` from the resolution block and writes frontmatter plus body in `serve/kanban/src/owlbear_kanban/engine.py:959-971`. | Frontmatter delimiters, null resolution fields, `resolved_at` omission, and body placement are asserted in `serve/kanban/tests/test_engine_requests_1852.py:380`, `:396`, `:410`, `:424`, and `:439`. | PASS |
| AC3 | `create_request` blocks the task and attempts rollback on block failure in `serve/kanban/src/owlbear_kanban/engine.py:1010-1014`. | Blocking, orphan cleanup on normal block-failure path, and reraising are asserted in `serve/kanban/tests/test_engine_requests_1852.py:462`, `:476`, and `:499`. | PASS |
| AC4 | `get_request` parses pending/resolved request files, validates frontmatter, maps parse/model failures to `ValidationError`, and returns `RequestRecord.from_request(...)` in `serve/kanban/src/owlbear_kanban/engine.py:932-956` and `:1018-1036`. | Pending/resolved lookup, returned fields/body, pending-first order, empty body, action/decision options, resolution, `NotFoundError`, corrupt YAML, and invalid-model paths are asserted in `serve/kanban/tests/test_engine_requests_1852.py:531`, `:540`, `:549`, `:570`, `:579`, `:594`, `:628`, `:640`, `:649`, `:659`, `:673`, and `:687`. | PASS |
- Blocking findings: none.

## Observations
- Challenger cross-check returned `reconsider` with confidence `0.67` on residual atomicity and rollback-edge semantics. I did not treat that as blocking because the active AC no longer requires `O_EXCL`-specific proof, and the remaining rollback concern depends on a secondary `unlink()` failure that is not named in the AC or failure-mode map.
- I did not re-run quality-runner in this cycle because the current record already contained sufficient, internally consistent execution evidence, including a prior reviewer rerun after the retry; this cycle only re-reviewed the refined AC against the existing 32-test proof packet.
- If a future task needs crash-safe full-file publication semantics rather than exclusive final-path creation, that contract should call for `serve/kanban/src/owlbear_kanban/storage_io.py` and direct proof for that behavior.

[[2026-05-25T05:35:48+02:00]]
## Docs Gate

**Verdict:** PASS

### Convention Mapping
- `serve/kanban/src/owlbear_kanban/engine.py` → `serve/kanban/README.md`
- `serve/kanban/src/owlbear_kanban/request_models.py` → `serve/kanban/README.md`
- `serve/kanban/tests/test_engine_requests_1852.py` → `serve/kanban/README.md`

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| README Verification | FIXED | `create_request` and `get_request` are `KanbanEngine` methods confirmed at `engine.py:974` and `engine.py:1018`; neither method was present in the `KanbanEngine methods` table; two rows added |
| External Attribution | N/A | No external sources — implementation uses UUID4, Pydantic, ruamel.yaml, os.O_EXCL (all existing dependencies) |
| Research Doc | N/A | No research artifact linked or referenced in task body |
| Deletion Detection | N/A | No files deleted; task added functions to existing files only |

### Files Updated
- `serve/kanban/README.md` — added `create_request` and `get_request` rows to KanbanEngine methods table (commit 94d554b1)

### Scratch Cleanup
- No `1852-*` scratch files found; nothing to delete.

[[2026-05-25T05:44:18+02:00]]
## Audit

### Regression Detection
quality-runner full (domain: kanban): 32 passed, 0 failed. 2 lint violations in `serve/knowledge/refresh.py` (F401, ARG002) — pre-existing, unrelated to kanban domain. No regressions.

### Intent Verification
Changed files: `engine.py`, `request_models.py`, task test, `README.md` — all within `serve/kanban/`. Implementation adds `create_request` and `get_request` engine methods matching stated task purpose. No extraneous scope.

### Architect Quality
Score: 4/5. AC lines are specific and testable. Minor gap: initial AC1 included implementation detail (O_EXCL) creating a disproportionate proof obligation that required a second review cycle. Architect correctly resolved by refining AC to contract-level language. System worked as designed.

### Commit Integrity
- e3477a4e test: engine API create_request and get_request (#1852, test-writer)
- bb67a3f9 feat: implement request create/get API (#1852, builder)
- 434bcf14 test: add retry tests for request field surface (#1852, test-writer)
- 94d554b1 docs: add create_request and get_request to kanban README (#1852, doc-writer)

All deliverables committed with proper attribution.

### Deductions
None.

### Confidence: 1.00
### Action: ARCHIVE
