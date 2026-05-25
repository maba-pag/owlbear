---
id: 1852
title: 'P1-02: Engine API — create_request and get_request'
status: todo
priority: needed
created: 2026-05-24T20:58:06.152479+02:00
updated: 2026-05-25T04:26:41.211669+02:00
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
    ISO 8601), writes decisions/pending/{request_id}.md atomically (O_EXCL), and
    returns an object exposing the validated model fields and body string.
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
archival_reason:
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
