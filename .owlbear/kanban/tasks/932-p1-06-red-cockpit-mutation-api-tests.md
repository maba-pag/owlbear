---
id: 932
title: 'P1-06: RED — Cockpit mutation API tests'
status: in-progress
priority: important
created: 2026-04-17T19:58:25.607234+00:00
updated: 2026-04-18T13:58:56.200019+00:00
tags:
- cockpit
- backend
- phase-1
- type:test
parent: 920
depends_on:
- 930
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Write failing tests for cockpit mutation endpoints: move, edit (allowlisted YAML + body), release. Includes conflict detection (D9) and audit logging.

## Acceptance Criteria

- [ ] Test file at `tests/test_cockpit_mutation_api.py`
- [ ] Tests use FastAPI TestClient
- [ ] Tests cover:
  - `POST /api/tasks/{id}/move` with target status; validates against valid_transitions
  - `POST /api/tasks/{id}/move` with invalid target returns 422
  - `POST /api/tasks/{id}/edit` with allowlisted fields: title, tags, priority, depends_on, parent, block_reason, body
  - `POST /api/tasks/{id}/edit` with non-allowlisted field returns 422
  - `POST /api/tasks/{id}/edit` requires `updated` snapshot in request body
  - `POST /api/tasks/{id}/edit` returns 409 Conflict when `updated` snapshot is stale (D9)
  - `POST /api/tasks/{id}/release` unclaims task successfully
  - `POST /api/tasks/{id}/release` on unclaimed task returns appropriate error
  - Block mutation: edit with `block_reason` sets blocked state
  - Unblock mutation: edit with `block_reason: null` clears blocked state
  - All mutations write entry to `activity.jsonl` with `actor: "cockpit"`
  - 404 for mutations on non-existent task ID
- [ ] All tests fail (RED phase)

## Files

- `tests/test_cockpit_mutation_api.py`
[[2026-04-18]]
## Research
- Research doc: .owlbear/research/932-cockpit-mutation-api-tests.md
- Sources: 6 studied (all internal), 4 high-relevance
- Recommendation: Proceed directly to RED phase — all engine methods exist, six cockpit-level logic gaps are well-defined (confidence: .92)
- Key finding: Engine lacks optimistic locking (D9) and release validation — cockpit routes must add these checks. Tag/dep diffing needed because engine uses add/remove semantics.
- Follow-up tasks created: none (AC is self-contained; GREEN phase #934 already exists)
- Decision requests: none (T1 autonomous — no architecture or breaking changes)
[[2026-04-18]]
## Architecture Review

### AC Refinements (binding for test writer)

The following tighten the original AC. Where these conflict with the original AC wording, these refinements govern:

1. **Release on unclaimed task → 409 Conflict.** D12 "unconditional" refers to authorization (no ownership check), not validation. Releasing a non-existent claim is a state conflict. Test must assert 409, not 400.
2. **Non-allowlisted field test: use `status` specifically.** `status` is the highest-value bypass target (engine's `edit_task` accepts it). The Pydantic model must reject it — test this explicitly. Additional non-allowlisted fields (e.g., `claimed_by`) are optional.
3. **`blocked` is NOT in the edit allowlist.** Block/unblock is an implicit consequence of setting/nulling `block_reason`. Sending `{"blocked": true}` directly should 422.
4. **Successful mutation returns 200 with updated task object** (same shape as `GET /api/tasks/{id}`). This applies to move, edit, and release.
5. **404 tests: one per mutation endpoint** (move, edit, release) — not a single shared test.
6. **Move endpoint intentionally omits D9 conflict detection.** Brief route table scopes D9 to edit only. No `updated` field in move request body. This is a known accepted gap.
7. **Edit request body shape:** `{"updated": "<ISO timestamp>", ...fields}` where fields are from the allowlist. `tags` and `depends_on` are full replacement lists (cockpit computes diffs server-side).

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One test file, one domain (cockpit mutation test surface) |
| Interface clarity | PASS (after refinements) | Error codes pinned, response shape specified, allowlist boundaries explicit |
| Dependency correctness | PASS | Depends on #930 (archived/done). Fixture pattern established there. |
| Module layering | PASS | Tests import cockpit (app, get_engine) and kanban (KanbanEngine) — standard for test code |
| TDD compliance | PASS | This IS the RED phase. GREEN phase #934 exists as sibling. |
| KISS/YAGNI | PASS | Minimal scope: 3 endpoints, well-defined edge cases, no hypothetical requirements |
| Premise challenge | PASS | Mutation tests are necessary — no existing coverage for these endpoints |
| Pattern consistency | PASS | Follows TestClient + DI override pattern from test_cockpit_read_api.py |
| Security surface | PASS | Allowlist enforcement tested (incl. `status` bypass), D9 conflict detection tested, D12 verb restriction is structural |
| Single domain | PASS | Cockpit backend domain only |

### Challenge Results
- Challenger: **reconsider** (confidence 0.55)
- Key findings: D12/AC contradiction on release-unclaimed (C1), missing `status` bypass test (C3), move lacks D9 (C2)
- Architect response: **accepted C1 and C3** — refined AC accordingly. **Rebutted C2** — intentional scope per brief. Challenger confidence was low primarily due to D12 interpretation ambiguity, which is now resolved.

### Verdict: APPROVE (with refinements above)
### Action Taken: Advanced to todo. AC refinements appended as binding guidance for test writer.
[[2026-04-18]]
## Test-Writer Notes
- Test file: tests/test_cockpit_mutation_api.py
- Classes: TestFromAC_MoveTask, TestFromAC_EditTask, TestFromAC_ReleaseTask, TestFromAC_AuditLogging
- Tests per category: happy 10, edge 2, error 12, boundary 1
- Total: 25 tests, all FAIL
- ruff: clean
- Commit: 9954cfd5

### AC Coverage

| AC Line | Tests |
|---------|-------|
| POST /move with target status (validates valid_transitions) | test_move_happy_path_returns_200, test_move_returns_updated_task_object |
| POST /move with invalid target → 422 | test_move_invalid_target_status_returns_422, test_move_same_status_returns_422 |
| POST /move non-existent task → 404 | test_move_nonexistent_task_returns_404 |
| POST /edit allowlisted fields (title, tags, priority, depends_on, parent, body) | 6 tests (one per field) |
| POST /edit non-allowlisted 'status' → 422 (AC refinement #2) | test_edit_status_field_rejected_422 |
| POST /edit 'blocked' directly → 422 (AC refinement #3) | test_edit_blocked_field_directly_rejected_422 |
| POST /edit missing 'updated' → 422 | test_edit_missing_updated_returns_422 |
| POST /edit stale 'updated' → 409 D9 | test_edit_stale_updated_returns_409 |
| Block mutation via block_reason | test_edit_block_reason_sets_blocked_state |
| Unblock mutation via block_reason=null | test_edit_null_block_reason_clears_blocked_state |
| POST /edit non-existent task → 404 | test_edit_nonexistent_task_returns_404 |
| POST /release claimed task → 200 with task | test_release_claimed_task_returns_200, test_release_returns_task_object_shape |
| POST /release unclaimed task → 409 (AC refinement #1) | test_release_unclaimed_task_returns_409 |
| POST /release non-existent task → 404 | test_release_nonexistent_task_returns_404 |
| All mutations write activity.jsonl actor='cockpit' | 3 tests (one per endpoint) |

### Key design choices
- Engine fixture uses `agent_name="cockpit", activity_log=True` (overrides config activity_log: false)
- Fixture pre-claims task 2 via `seed.claim_task("2")` for release tests
- D9 stale-update test advances task via direct engine call between load and cockpit save
- Unblock test blocks task via engine in test body then unblocks via cockpit