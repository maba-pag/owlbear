---
id: 1856
title: 'P1-06: Cockpit API — GET /api/requests/pending and POST /api/requests/{id}/resolve'
status: archived
priority: needed
created: 2026-05-24T20:58:51.312492+02:00
updated: 2026-05-25T12:29:53.350240+02:00
tags:
  - phase-1
  - scope:cockpit
  - api
parent: 1850
depends_on:
  - 1854
ac:
  - 'GET /api/requests/pending: calls engine.sweep_requests() in try/except (catches
    any exception, logs WARNING, continues), then engine.list_requests(status="pending").
    Returns JSON array with fields: request_id, task_id, kind, title, summary, agent,
    created_at, options (option_id/label/confidence/recommended/rationale), body.
    Response model extra="forbid".'
  - 'POST /api/requests/{id}/resolve: accepts {selected_option_id: str|null, free_text:
    str|null, kind: Literal["decision","action"]|None}; extra="forbid". Validates
    UUID4 format (422 detail="Invalid request id"), canonicalizes to lowercase before
    engine delegation. Delegates engine.resolve_request(canonical_id, selected_option_id,
    free_text). Returns 200 {request_id, task_id, kind, title, resolved_at}.'
  - 'POST resolve errors: Engine NotFoundError→404 and ValidationError→422 via app
    exception handler returning shared envelope {code, message}. Tests must assert
    response body code field matches exception code (not status-only proof). Uppercase
    UUID4 must resolve correctly (canonicalized, no false-404).'
  - 'POST /api/requests/{id}/resolve bare-Complete: when both selected_option_id and
    free_text are null AND body kind="action", normalizes free_text to "" before engine
    delegation. When both null and kind absent or "decision", returns 422 HTTPException(detail="decision
    requests require selected_option_id or free_text").'
  - 'Route wiring: new file routes/requests.py registered in main.py with prefix="/api".
    Uses get_engine from deps.py. Does NOT modify existing routes/decisions.py (retained
    for P2-06 removal).'
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
- `GET /api/requests/pending` endpoint
- `POST /api/requests/{id}/resolve` endpoint
- Pydantic request/response models for both endpoints
- Direct engine import (no HTTP between Cockpit backend and engine)
- Sweep trigger on Cockpit startup/cleanup cycle

**Out of scope:**
- Frontend rendering (P1-07, P2-01/02/03)
- Old `/decisions/` endpoints (retained until P2-06 removal)
- MCP layer

## Test scope
`tests/test_cockpit_*`

[[2026-05-25T10:18:47+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Two endpoints + Pydantic models in a single new route file, all for structured request resolution in Cockpit |
| Interface clarity | PASS | After refinement: exact fields, error codes, HTTP status mappings, UUID4 validation, bare-Complete normalization all specified |
| Dependency correctness | PASS | #1854 archived/completed; engine.list_requests, engine.resolve_request, engine.sweep_requests, engine.get_request all exist |
| Module layering | PASS | Cockpit routes import from owlbear_kanban engine directly; no upward imports |
| TDD compliance | PASS | Test scope: tests/test_cockpit_* (established pattern) |
| KISS/YAGNI | PASS | Thin wrapper over engine API; kind field in body avoids extra engine call; sweep catch follows #1854 pattern |
| Premise challenge | PASS | Brief explicitly requires these endpoints (Cockpit API table in brief.md) |
| Pattern consistency | PASS | Follows existing routes/decisions.py style (HTTPException for format validation), main.py exception handlers (KanbanError→envelope), DI via deps.py |
| Security surface | PASS | UUID4 format validation at API layer for fast-fail; engine validate_path_containment as defense-in-depth |
| Single domain | PASS | Cockpit only; engine is a dependency, not modified |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| GET sweep_requests() | OS-level I/O error | OSError | Caught at route level, WARNING logged, continues to list | Stale data possible; no crash |
| GET list_requests() | Corrupt request file | YAMLError/PydanticValidationError | Handled internally by engine (skip+log) | File excluded from results |
| POST resolve format check | Non-UUID4 request_id | HTTPException | Yes (422 detail) | Clear error message |
| POST resolve engine call | Request not found | NotFoundError | Via exception handler → 404 | Standard not-found |
| POST resolve engine call | Already resolved | ValidationError | Via exception handler → 422 | ERR_ALREADY_RESOLVED |
| POST resolve engine call | Invalid option_id | ValidationError | Via exception handler → 422 | ERR_PREDICATE_FAILED |

### Design Diverge
- Trigger: skipped — single clear approach (thin wrapper + kind field for bare-Complete). No competing architectures.

### Challenge Results
- Challenger: reconsider (confidence 0.58)
- Findings: (1) error contract — accepted, switched to HTTPException matching decisions route; (2) error precedence with get_request — accepted, replaced with kind field in body eliminating extra engine call; (3) sweep failure semantics — acknowledged, rebutted (matches #1854 pick_tasks pattern, sweep handles most errors internally); (4) response body exclusion — accepted, added body to response fields; (5) B3 "valid" — accepted, rephrased.
- Architect response: Accepted 1,2,4,5; rebutted 3. Revised AC from 4 original lines to 4 refined lines addressing all actionable findings.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC from original 4 lines to 4 precise lines addressing: (a) sweep error handling at route level, (b) UUID4 format validation via HTTPException, (c) bare-Complete normalization using kind field in body (avoids error-precedence issue), (d) body included in response for downstream #1859 dependency, (e) route wiring as separate file. Advanced to todo.

[[2026-05-25T10:32:52+02:00]]
## Test-Writer Notes
- Test file: tests/test_cockpit_requests_api_1856.py
- Classes: TestFromAC_GetRequestsPending, TestFromAC_PostRequestsResolve, TestFromAC_BareCompleteNormalization, TestFromAC_RouteWiring
- Tests per category: happy 8, edge 3, error 10, boundary 5
- Total: 23 tests (20 reported + 3 AC4), all FAIL
- ruff: clean

AC coverage:
| AC line | Tests |
|---------|-------|
| AC1 (GET pending — sweep+list+shape) | test_returns_pending_records_list, test_response_item_has_required_fields, test_decision_request_options_have_required_subfields, test_action_request_has_empty_options, test_returns_empty_list_when_no_pending, test_sweep_exception_does_not_abort_listing, test_response_excludes_resolution_field |
| AC2 (POST resolve — UUID4 + delegation + errors) | test_resolve_decision_request_returns_200, test_resolve_action_request_returns_200, test_response_has_required_fields, test_non_uuid_id_returns_422_with_invalid_request_id, test_uuid_v1_id_returns_422_with_invalid_request_id, test_engine_not_found_returns_404, test_engine_already_resolved_returns_422, test_extra_field_in_body_returns_422, test_invalid_kind_value_returns_422 |
| AC3 (bare-Complete normalization) | test_both_null_kind_action_delegates_with_empty_free_text, test_both_null_no_kind_returns_422, test_both_null_kind_decision_returns_422, test_both_null_kind_none_returns_422 |
| AC4 (route wiring) | test_get_requests_route_registered, test_post_requests_route_registered, test_routes_requests_file_exists |

Failure modes: all 23 return 404 (route not registered) or AssertionError (code field absent); AC4 file check asserts file does not exist. All fail for the right reasons.

[[2026-05-25T10:38:31+02:00]]
## Builder Notes
- Files changed:
  - serve/cockpit/src/owlbear_cockpit/routes/requests.py
  - serve/cockpit/src/owlbear_cockpit/main.py

- Implementation summary:
  - Added new Cockpit route module `routes/requests.py` with:
    - `GET /api/requests/pending`: invokes `engine.sweep_requests()` in a broad try/except with WARNING log, then `engine.list_requests(status="pending")`, returning only the AC-specified fields.
    - `POST /api/requests/{id}/resolve`: UUID4 validation (`422 Invalid request id` for non-UUID4/invalid format), `extra="forbid"` request model, direct delegation to `engine.resolve_request`.
    - Bare-Complete normalization: when both `selected_option_id` and `free_text` are null and `kind="action"`, normalizes `free_text` to empty string before delegation; otherwise returns `422` with `decision requests require selected_option_id or free_text`.
  - Wired router in `main.py` with `app.include_router(requests_router, prefix="/api")`.

- Verification (quality-runner, scoped):
  - RED check before implementation:
    - tests: 0 passed / 21 failed (`tests/test_cockpit_requests_api_1856.py`), all failing for expected missing-route behavior.
    - lint: clean.
  - GREEN verification after implementation and lint fix:
    - tests: 23 passed / 0 failed / 0 skipped.
    - lint: clean (`ruff` clean for modified source + task test file).
    - coverage module `owlbear_cockpit.routes.requests`: 100%.

- Durable module-level test file check:
  - No separate durable `tests/test_cockpit_requests_api.py` exists in current workspace; task-scoped file is the available request-API test target.

- Fixes applied during verification:
  - Replaced UUID version magic number with constant for lint compliance.
  - Kept broad sweep exception catch (AC-mandated) and documented with inline lint rationale.
  - Added terminal newline for style compliance.

- Commit:
  - `075fc1c9 feat: add cockpit requests API endpoints (#1856, builder)`

[[2026-05-25T10:56:41+02:00]]
## Review Evidence
- Verdict: FAIL
- Reviewed builder evidence: quality-runner scoped run reports 23 passed / 0 failed, ruff clean, and 100% coverage for owlbear_cockpit.routes.requests. Direct inspection found the implementation aligned with the AC in serve/cockpit/src/owlbear_cockpit/routes/requests.py:12,23,35,51,61,74,77,109-113,135,138 and serve/cockpit/src/owlbear_cockpit/main.py:49.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1 | Behavioral proof is too weak at the route layer. The GET tests assert response status/shape only, and the only interaction assertion is a no-arg list_requests call. They do not prove normal-path sweep_requests invocation, WARNING logging on sweep failure, or list_requests(status="pending"). A route omitting the sweep, swallowing the warning, or dropping the pending filter would still pass. | serve/cockpit/src/owlbear_cockpit/routes/requests.py:109-113; tests/test_cockpit_requests_api_1856.py:227-323 | todo |
| 2 | AC2 | Happy-path POST proof does not verify delegation arguments. The decision/action success tests only assert 200 and response fields, so a route that ignores request_id, selected_option_id, or free_text and returns the mocked result would still pass. AC3 covers only the null/null action-normalization branch. | serve/cockpit/src/owlbear_cockpit/routes/requests.py:138; tests/test_cockpit_requests_api_1856.py:347-387; tests/test_cockpit_requests_api_1856.py:507 | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add route-level assertions that GET /api/requests/pending calls engine.sweep_requests(), emits a WARNING record on sweep failure, and delegates to engine.list_requests(status="pending"). | tests/test_cockpit_requests_api_1856.py | AC1 finding; serve/cockpit/src/owlbear_cockpit/routes/requests.py:109-113; tests/test_cockpit_requests_api_1856.py:227-323 |
| 2 | test-writer | Add happy-path POST assertions that resolve_request receives the submitted request_id, selected_option_id, and free_text for decision and action bodies. | tests/test_cockpit_requests_api_1856.py | AC2 finding; serve/cockpit/src/owlbear_cockpit/routes/requests.py:138; tests/test_cockpit_requests_api_1856.py:347-387 |

## Observations
- No blocking implementation mismatch found in the route code. AC1-AC4 map cleanly to serve/cockpit/src/owlbear_cockpit/routes/requests.py and serve/cockpit/src/owlbear_cockpit/main.py.
- The AC3 normalization branch is well-proved by tests/test_cockpit_requests_api_1856.py:494-507.
- Adjacent engine suites cover engine semantics, but no other cockpit route test closes the missing interaction proof at the API layer.

[[2026-05-25T11:03:37+02:00]]
## Test-Writer Notes
- Retry: added 5 interaction-proof tests addressing reviewer findings.
- Builder skip: test-only retry — all 5 new tests pass against current implementation.

**New tests added to `tests/test_cockpit_requests_api_1856.py`:**

AC1 gaps (reviewer finding #1 — weak interaction proof for GET):
- `test_normal_path_calls_sweep_requests_once` — asserts `engine.sweep_requests()` is called once on the happy path
- `test_normal_path_delegates_list_requests_with_pending_status` — asserts `engine.list_requests(status="pending")`, not an unfiltered call
- `test_sweep_failure_emits_warning_log_record` — asserts a WARNING record is emitted (not silently swallowed) on sweep failure

AC2 gaps (reviewer finding #2 — no delegation argument proof for POST):
- `test_resolve_decision_passes_request_id_and_option_id_to_engine` — asserts `resolve_request(rid, "option-a", None)` receives submitted values
- `test_resolve_action_passes_request_id_and_free_text_to_engine` — asserts `resolve_request(rid, None, "done")` receives submitted values

Quality-runner: 28 passed / 0 failed, lint clean.
Commit: `4ffc3bfe test: add retry interaction-proof tests for requests API (#1856, test-writer)`

[[2026-05-25T11:42:32+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL #1856 -> backlog | AC2 accepts uppercase UUID4 text that can false-404 in engine lookup, and the ValidationError handler proof is still too weak.
- Reviewed builder evidence: scoped quality-runner reported 23 passed / 0 failed, ruff clean, and 100% coverage for owlbear_cockpit.routes.requests.
- Reviewed retry evidence: test-writer added 5 interaction-proof tests and reported 28 passed / 0 failed with lint clean.
- Review cycle: second review cycle for this task (prior FAIL recorded before the test-only retry), so blocking findings route to backlog per loop-breaker policy.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC2 | `_validate_request_id()` accepts uppercase UUID4 text by comparing `str(parsed)` to `request_id.lower()`, then `resolve_request()` forwards the original casing unchanged to `engine.resolve_request()`. The engine resolves request files by the raw `request_id` stem, while new request ids are created in lowercase canonical form. On a case-sensitive filesystem, a syntactically valid uppercase UUID4 can be accepted by the API and then false-404 at file lookup. The task-local tests never cover this path because they only generate lowercase ids with `str(uuid.uuid4())`. | serve/cockpit/src/owlbear_cockpit/routes/requests.py:76,138; serve/kanban/src/owlbear_kanban/engine.py:999,1208-1209; tests/test_cockpit_requests_api_1856.py:389,479,526 | backlog |
| 2 | AC2 | The `ValidationError -> 422 via existing handlers` clause is still under-proved at the route layer. `test_engine_already_resolved_returns_422` checks status only, unlike the NotFound branch which asserts the shared envelope code. A route-local 422 would still pass this test, so the retry does not fully prove the handler requirement. | serve/cockpit/src/owlbear_cockpit/main.py:64,72; tests/test_cockpit_requests_api_1856.py:456-473,475-489 | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine and reissue the retry so `POST /api/requests/{id}/resolve` either canonicalizes accepted UUID4 ids before engine delegation or rejects non-canonical casing, and require regression proof for the accepted-uppercase path. | serve/cockpit/src/owlbear_cockpit/routes/requests.py; tests/test_cockpit_requests_api_1856.py | Finding #1 |
| 2 | architect | Refine and reissue the retry to require explicit shared-envelope proof for engine `ValidationError` on `POST /api/requests/{id}/resolve`, not status-only 422 proof. | serve/cockpit/src/owlbear_cockpit/main.py; tests/test_cockpit_requests_api_1856.py | Finding #2 |

## Observations
- The retry closes the first review’s AC1 and happy-path delegation gaps: the GET tests now assert the sweep call, the pending-status list delegation, and warning logging; the POST happy-path tests now assert submitted arguments are forwarded to `engine.resolve_request()`.
- AC3 remains well-proved by the null/null action-normalization test.
- AC4 maps cleanly to the implementation: `routes/requests.py` exists, imports `get_engine` from deps, and `main.py` wires `requests_router` under `/api`.

[[2026-05-25T11:45:13+02:00]]
## Architecture Review (retry refinement)
### Context
Task returned from second review cycle with two blocking findings:
1. UUID casing: `_validate_request_id()` accepts uppercase UUID4 but forwards original casing to engine → false-404 on case-sensitive FS.
2. Envelope proof: `test_engine_already_resolved_returns_422` asserts status only, not shared envelope {code, message} structure.

### AC Refinement
Split AC2 into AC2 (endpoint shape + canonicalization) and AC3 (error proof contract):
- AC2 now requires: \"canonicalizes to lowercase before engine delegation\" — fix is one-line: pass `str(parsed)` from `_validate_request_id` or lowercase `request_id` before `engine.resolve_request()`.
- AC3 (new): explicitly requires shared-envelope assertion (code field matches exception code) and uppercase UUID4 regression proof.
- AC4/AC5 unchanged (bare-Complete normalization, route wiring).

### Scope of retry
- Builder: canonicalize request_id to lowercase before passing to engine (~1-line change in routes/requests.py).
- Test-writer: (a) add `test_engine_already_resolved_returns_422` envelope assertion (`code == \"ERR_ALREADY_RESOLVED\"`), (b) add uppercase UUID4 regression test proving canonicalization.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED (targeted test additions)

### Verdict: APPROVE (refinement for review-loop findings)
### Action Taken: Refined AC2 into two lines addressing UUID canonicalization and envelope proof gap. Advanced to todo for targeted fix cycle.

[[2026-05-25T11:50:25+02:00]]
## Test-Writer Notes
- Retry: added 3 tests for AC3 reviewer gaps (second retry, targeted fill only).
- New class: `TestFromAC_ErrorEnvelopeAndCanonicalization` in `tests/test_cockpit_requests_api_1856.py`

**New tests:**
1. `test_engine_already_resolved_returns_422_with_envelope_code` — asserts `resp.json().get("code") == "ERR_ALREADY_RESOLVED"` (envelope proof gap from reviewer finding #2). PASSES against existing handler.
2. `test_uppercase_uuid4_canonicalized_to_lowercase_for_engine` — asserts `engine.resolve_request` receives lowercase canonical id when uppercase UUID4 is sent (reviewer finding #1). FAILS — source forwards original uppercase casing, builder must canonicalize.
3. `test_uppercase_uuid4_accepted_returns_200` — asserts uppercase UUID4 is accepted (returns 200, not 422). PASSES — validation already accepts it.

**Quality-runner (scoped):** 30 passed / 1 failed (`test_uppercase_uuid4_canonicalized_to_lowercase_for_engine`), lint clean.
**Commit:** f34ca9f8

AC coverage:
| AC line | New tests |
|---------|-----------|
| AC3 (envelope proof) | test_engine_already_resolved_returns_422_with_envelope_code |
| AC3 (uppercase UUID4 regression) | test_uppercase_uuid4_canonicalized_to_lowercase_for_engine, test_uppercase_uuid4_accepted_returns_200 |

[[2026-05-25T12:01:06+02:00]]
## Builder Notes
- Implementation: updated `serve/cockpit/src/owlbear_cockpit/routes/requests.py` only.
- Tests: 31 TestFromAC tests passed in `tests/test_cockpit_requests_api_1856.py`.
- Coverage: 100% on touched module `owlbear_cockpit.routes.requests`.
- ruff: clean.
- Approach: minimal AC-aligned fix for canonical UUID4 delegation by returning canonical lowercase UUID from `_validate_request_id()` and passing that canonical id into `engine.resolve_request(...)`.
- RED verification before change: 30 passed / 1 failed (`TestFromAC_ErrorEnvelopeAndCanonicalization::test_uppercase_uuid4_canonicalized_to_lowercase_for_engine`), lint clean.
- GREEN verification after change (quality-runner scoped): 31 passed / 0 failed / 0 skipped; lint clean; module coverage 100%.
- Durable module-level test file: no separate durable `tests/test_cockpit_requests_api.py` exists; task-scoped suite remains the requests API verification target.
- Commit: `47547ce2 fix: canonicalize request UUID4 delegation in requests API (#1856, builder)`.

[[2026-05-25T12:19:23+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1856 -> docs | AC mapped to code and evidence sufficient.
- Reviewed builder evidence first: scoped quality-runner GREEN reported 31 passed / 0 failed / 0 skipped, ruff clean, and 100% coverage for `owlbear_cockpit.routes.requests`; local editor diagnostics found no errors in `serve/cockpit/src/owlbear_cockpit/routes/requests.py`, `serve/cockpit/src/owlbear_cockpit/main.py`, or `tests/test_cockpit_requests_api_1856.py`.
- AC evidence map:
| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | serve/cockpit/src/owlbear_cockpit/routes/requests.py:20,23,32,35,111,115 | tests/test_cockpit_requests_api_1856.py:241,266,282,294,305,325,338,348,358 | PASS |
| AC2 | serve/cockpit/src/owlbear_cockpit/routes/requests.py:48,51,58,61,70,74,77,140,141 | tests/test_cockpit_requests_api_1856.py:385,399,413,430,442,491,509,522,536 | PASS |
| AC3 | serve/cockpit/src/owlbear_cockpit/main.py:71,76; serve/cockpit/src/owlbear_cockpit/routes/requests.py:70,140 | tests/test_cockpit_requests_api_1856.py:456,675,695,711 | PASS |
| AC4 | serve/cockpit/src/owlbear_cockpit/routes/requests.py:131,132,133,135,137,140 | tests/test_cockpit_requests_api_1856.py:559,575,589,603 | PASS |
| AC5 | serve/cockpit/src/owlbear_cockpit/routes/requests.py:12; serve/cockpit/src/owlbear_cockpit/main.py:49; serve/cockpit/src/owlbear_cockpit/routes/decisions.py:96,135 | tests/test_cockpit_requests_api_1856.py:626,636,650 | PASS |
- Challenger cross-check: `challenger` returned `proceed` (confidence 0.84). Strongest objection was AC5 negative-clause traceability, but the current code keeps request routing isolated in `routes/requests.py` and leaves legacy `routes/decisions.py` on `/decisions/*`, so that remains non-blocking.

## Observations
- No blocking implementation or proof gaps remain after the retry cycle. The uppercase UUID4 false-404 defect is closed by canonical lowercase delegation in `serve/cockpit/src/owlbear_cockpit/routes/requests.py:70,140`, and the error-envelope proof now asserts the required `code` field for both domain-error branches.
- The full shared envelope `{code, message}` is proved by source inspection in `serve/cockpit/src/owlbear_cockpit/main.py:71,76`; task-local tests explicitly prove the required `code` field at `tests/test_cockpit_requests_api_1856.py:456` and `tests/test_cockpit_requests_api_1856.py:675`.
- No independent quality-runner rerun was cost-justified because the builder evidence was complete and internally consistent.

[[2026-05-25T12:22:57+02:00]]
## Docs Gate

### Item 1: README Verification
- **Target:** `serve/cockpit/README.md` (via `serve/cockpit/src/**` convention mapping).
- Layer 1: grep confirmed `GET /api/requests/pending` and `POST /api/requests/{id}/resolve` absent from README prior to edit.
- Layer 2: source read of `routes/requests.py` confirmed response shape, error contract, and bare-Complete normalization semantics.
- **Fix:** Added new `## Requests API` section between `## Decisions API` and `## Memory API` documenting both endpoints with full shape, canonicalization, normalization, and error-envelope behaviour.
- `.github/copilot-instructions.md` endpoint table also updated to include the two new routes.
- Commit: `94d18f21`

### Item 2: External Attribution
- N/A — no external sources cited in builder/reviewer notes. Implementation is a thin engine wrapper.

### Item 3: Research Doc
- N/A — no research artifact linked or referenced in task body.

### Item 4: Deletion Detection
- No symbols, flags, or commands removed. `routes/decisions.py` explicitly retained per AC5.

### Scratch Cleanup
- No `1856-*` scratch files created by the doc-writer pass.

[[2026-05-25T12:29:53+02:00]]
## Audit

### Regression Detection
Quality-runner full-suite: 5246 passed. 127 failures all pre-existing and unrelated to #1856:
- `test_cockpit_view.py` — FileNotFoundError for deleted task-scoped files from old tasks (#1067, #1068, #1071, #1132)
- `test_server.py` — MCP server domain failures (StatusNamesDictFormBug, FunctionRemoval, OutputSchemaPreserved)
- Lint violations exclusively in `serve/knowledge/` (pre-existing TC001, RUF022, etc.)

No cockpit requests domain failures. No task-caused regressions.

### Intent Verification
Changed files: `routes/requests.py` (new, 147 lines), `main.py` (+2 lines router include), `tests/test_cockpit_requests_api_1856.py` (724 lines), `serve/cockpit/README.md`, `.github/copilot-instructions.md`. All within cockpit API domain, matching stated purpose of adding GET/POST request endpoints. No extraneous scope.

### Architect Quality
Score: 4/5. Initial AC required two refinement rounds (UUID canonicalization gap and error-envelope proof specificity discovered during review), but challenger was engaged (reconsider at 0.58, findings integrated), failure mode map provided, and final 5-line AC is precise and verifiable. Minor gap: initial AC missed the uppercase UUID4 edge case, caught by reviewer.

### Commit Integrity
6 commits properly attributed: fa808617 (test-writer), 075fc1c9 (builder), 4ffc3bfe (test-writer retry), f34ca9f8 (test-writer retry 2), 47547ce2 (builder fix), 94d18f21 (doc-writer). All follow conventional commit format with #1856 reference.

### Deductions
None.

### Confidence: 1.00
### Action: ARCHIVE
