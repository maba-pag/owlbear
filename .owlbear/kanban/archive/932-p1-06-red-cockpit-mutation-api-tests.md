---
id: 932
title: 'P1-06: RED — Cockpit mutation API tests'
status: archived
priority: medium
created: 2026-04-17T19:58:25.607234+00:00
updated: 2026-04-18T14:59:25.336712+00:00
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

### Action Taken: Advanced to todo. AC refinements appended as binding guidance for test writer

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
[[2026-04-18]]

## Builder Notes

### Files changed

- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` — new file, 195 lines: MoveRequest, EditRequest models + move/edit/release routes
- `serve/cockpit/src/owlbear_cockpit/main.py` — include mutation_router under /api prefix

### Test results

- 25/25 TestFromAC_* passed (TestFromAC_MoveTask, TestFromAC_EditTask, TestFromAC_ReleaseTask, TestFromAC_AuditLogging)
- Full cockpit suite: 111 passed, 0 failed

### Lint status

- ruff check: clean
- ruff format: clean

### Commit

7eb1f8ee — feat(cockpit): add mutation API routes move/edit/release (#932)

### Key design decisions

- `EditRequest(extra="forbid")` rejects non-allowlisted fields (status, blocked) at Pydantic layer → 422
- `model_fields_set` used to distinguish "field provided as null" vs "field not provided" (block_reason unblock path)
- D9 stale check: string comparison of `req.updated != str(task.updated)` → 409
- Tags/depends_on: full-replacement via add/remove diff (engine uses add_tags/remove_tags semantics)
- Release: checks `task.claimed_by` before calling engine (engine is a no-op for unclaimed — cockpit adds 409)
- Activity logging: automatic via engine fixture (agent_name='cockpit', activity_log=True)
- `_build_edit_kwargs` + `_apply_list_diff` helpers extracted to pass ruff C901/PLR0912 complexity limits
[[2026-04-18]]

## Review Evidence

### Test Results

- pytest: 25 passed, 0 failed (test_cockpit_mutation_api.py only)
- Full cockpit suite: 111 passed, 0 failed

### Lint

- ruff: clean

### Coverage

- `owlbear_cockpit/routes/mutation.py`: 99%
- `owlbear_cockpit/main.py`: 91%
- Overall `owlbear_cockpit`: 61% (untouched modules pull average down)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Move with target status; validates valid_transitions | test_move_happy_path_returns_200, test_move_returns_updated_task_object | Yes — asserts 200 + status matches | COVERED |
| Move with invalid target → 422 | test_move_invalid_target_status_returns_422, test_move_same_status_returns_422 | Yes | COVERED |
| Edit with allowlisted fields (7 fields) | 6 per-field tests | Yes — each asserts 200 + specific mutation | COVERED |
| Edit non-allowlisted field → 422 | test_edit_status_field_rejected_422 | Yes | COVERED |
| Edit `blocked` directly → 422 | test_edit_blocked_field_directly_rejected_422 | Yes | COVERED |
| Edit requires `updated` snapshot | test_edit_missing_updated_returns_422 | Yes | COVERED |
| Edit stale `updated` → 409 (D9) | test_edit_stale_updated_returns_409 | Yes — advances timestamp then asserts 409 | COVERED |
| Block via block_reason | test_edit_block_reason_sets_blocked_state | Yes | COVERED |
| Unblock via block_reason=null | test_edit_null_block_reason_clears_blocked_state | Yes | COVERED |
| 404 per endpoint (move/edit/release) | 3 separate 404 tests | Yes | COVERED |
| Release unclaims → 200 | test_release_claimed_task_returns_200 | Yes | COVERED |
| Release unclaimed → 409 | test_release_unclaimed_task_returns_409 | Yes | COVERED |
| All mutations write activity.jsonl actor='cockpit' | TestFromAC_AuditLogging × 3 | **PARTIALLY** — see §5.3 | **LAX** |
| Move omits D9 (AC refinement #6) | None — structural only | No executable test | LAX |
| 200 with updated task object | per-endpoint | Yes for move/edit; shape-only for release (schema-constrained) | COVERED |

No MISSING entries. 2 LAX entries (audit log and move-omits-D9).

#### Security Review

- No hardcoded secrets. `task_id: int` prevents path injection. `extra="forbid"` on both request models is a positive control. No new dependencies. Error messages expose only integer IDs and status strings — no credential/PII leakage. **No issues.**

#### Test Integrity

- These are new `TestFromAC_*` classes (RED phase). No prior version to compare. §5.2 not applicable.

#### §5.3 Test Quality — **FAIL**

**WEAK — Audit log assertions** ([tests/test_cockpit_mutation_api.py:406-409](tests/test_cockpit_mutation_api.py#L406-L409), [L423-L426](tests/test_cockpit_mutation_api.py#L423-L426), [L439-L442](tests/test_cockpit_mutation_api.py#L439-L442))

All three `TestFromAC_AuditLogging` tests assert only `len(cockpit_entries) >= 1`. No test verifies the `action` field (e.g., `"move"`, `"edit"`, `"release"`), no test verifies the `id` field matches the mutated task. An engine bug writing a malformed or wrong-action entry would pass all three tests. **Automatic FAIL per §5.3.**

Fix: add assertions for at least `action` and `id` (or `task_id`) fields in each audit test. Example:

```python
assert cockpit_entries[0]["actor"] == "cockpit"
assert cockpit_entries[0]["task_id"] == 1   # or "id" depending on schema
```

All other test quality dimensions: STRONG (names descriptive, error paths covered, test independence via tmp_path).

#### §5.5 Implementation-Aware Test Gap — **FAIL**

**GAP 1 — CRITICAL: Invalid `priority` value → unhandled `ValueError` → 500**

`EditRequest.priority: str | None` accepts any string ([mutation.py:46](serve/cockpit/src/owlbear_cockpit/routes/mutation.py#L46)). When a caller sends `{"updated": "...", "priority": "ultra-critical"}`, `_build_edit_kwargs` passes it through ([mutation.py:107-108](serve/cockpit/src/owlbear_cockpit/routes/mutation.py#L107-L108)) and `engine.edit_task()` raises `ValueError("Invalid priority...")`. The `edit_task` route has no `try/except ValueError` guard. FastAPI returns 500. No test covers this path.

Correct behaviour: 422. Fix options:

1. Add an `Annotated` validator on `EditRequest.priority` against the configured priorities, **or**
2. Wrap the `engine.edit_task()` call in `try/except ValueError` → `HTTPException(422, ...)`.

**GAP 2 — MODERATE: Null field silent no-op undocumented** ([mutation.py:107-108](serve/cockpit/src/owlbear_cockpit/routes/mutation.py#L107-L108)). Sending `{"updated": "...", "title": null}` produces an empty kwargs and a silent 200 no-op. Behavior is unspecified by AC and untested.

#### Data Safety

- No new data safety issues introduced by this PR.

#### Builder Process Quality

- First review cycle. Single `## Builder Notes` section. CLEAN.

### Pass 2 — Informational

- `_apply_list_diff`'s `_field: str` parameter is unused — documentation value only, consider removing.
- `_task_to_detail(task: Any)` and `_build_edit_kwargs(req: EditRequest, task: Any)` could be typed as `Task` from `owlbear_kanban.models` for static analysis.
- `TestFromAC_AuditLogging` repeats the 3-line activity log parse pattern verbatim in three methods — a `_read_cockpit_entries(board_dir)` helper would reduce duplication.

### Deductions

| Criterion | Deduction | Reason |
|-----------|-----------|--------|
| §5.3 WEAK test quality | −0.15 | Audit log assertions check count only, not content |
| §5.5 Untested code path | −0.12 | Invalid priority → 500, no test, no guard |
| LAX AC coverage × 2 | −0.03 | Audit log LAX + move-omits-D9 structural only |

**Confidence: 0.70 → FAIL**

### Verdict

FAIL — two Pass 1 criteria unmet:

1. **Builder fix (in-progress):** Add priority validation to `EditRequest` (or catch `ValueError` in the edit route) to return 422 on invalid priority values. Add a test `test_edit_invalid_priority_returns_422`.
2. **Test-writer fix (coordinate with builder):** Strengthen `TestFromAC_AuditLogging` assertions to verify `action` and task-id fields in activity log entries — not just actor presence.
[[2026-04-18]]

## Builder Notes (round 2)

### Files changed

- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` — added `try/except ValueError` around `engine.edit_task()` call → returns 422 for invalid priority (3 lines)
- `tests/test_cockpit_mutation_api.py` — added `TestBuilderDiscovered` class: 4 tests (29 → 29 total, but 4 new builder-discovered tests added at end of file)

### Test results

- `TestBuilderDiscovered`: 4 passed (test_edit_invalid_priority_returns_422, test_move_audit_log_has_correct_action_and_task_id, test_edit_audit_log_has_correct_action_and_task_id, test_release_audit_log_has_correct_action_and_task_id)
- Full cockpit suite: 115 passed, 0 failed

### Lint status

- ruff check: clean (UP037 auto-fixed on new tests)
- ruff format: clean

### Evidence summary

- RED verified: invalid priority caused unhandled ValueError → 500 (confirmed via direct Python invocation)
- GREEN: ValueError now caught → 422 with engine's error message detail
- Audit log content tests: verify action + task_id fields as reviewer required — added as TestBuilderDiscovered (TestFromAC_* untouched per builder constraint)

### Commit

25275aa8 — fix(cockpit): invalid priority returns 422; strengthen audit log tests (#932)
[[2026-04-18]]

## Review Evidence (Pass 2)

### Test Results

- pytest: 29 passed, 0 failed (test_cockpit_mutation_api.py)
- Full cockpit suite: 115 passed, 0 failed (per builder; 29 independently confirmed)
- Exit code: 0

### Lint

- ruff: clean (exit 0)

### Coverage

- `owlbear_cockpit/routes/mutation.py`: ~99% (Pass 1 figure; quality-runner scoped to owlbear_kanban for this run; new try/except path covered by test_edit_invalid_priority_returns_422)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| POST /move validates valid_transitions | test_move_happy_path_returns_200, test_move_returns_updated_task_object | Yes | COVERED |
| POST /move invalid target → 422 | test_move_invalid_target_status_returns_422, test_move_same_status_returns_422 | Yes | COVERED |
| POST /edit allowlisted fields (7) | 6 per-field tests + test_edit_priority_returns_200 | Yes — body content checked | COVERED |
| POST /edit non-allowlisted `status` → 422 | test_edit_status_field_rejected_422 | Yes | COVERED |
| POST /edit `blocked` directly → 422 | test_edit_blocked_field_directly_rejected_422 | Yes | COVERED |
| POST /edit requires `updated` → 422 | test_edit_missing_updated_returns_422 | Yes | COVERED |
| POST /edit stale `updated` → 409 (D9) | test_edit_stale_updated_returns_409 | Yes — intervening engine mutation applied | COVERED |
| Block via block_reason | test_edit_block_reason_sets_blocked_state | Yes — blocked=True + block_reason asserted | COVERED |
| Unblock via block_reason=null | test_edit_null_block_reason_clears_blocked_state | Yes — blocked=False + block_reason=None asserted | COVERED |
| 404 per endpoint (3) | test_move/edit/release_nonexistent_task_returns_404 | Yes — ID in detail checked | COVERED |
| POST /release claimed → 200 + task | test_release_claimed_task_returns_200, test_release_returns_task_object_shape | Yes | COVERED |
| POST /release unclaimed → 409 | test_release_unclaimed_task_returns_409 | Yes | COVERED |
| All mutations write activity.jsonl actor=cockpit | TestFromAC_AuditLogging ×3 + TestBuilderDiscovered ×3 (action+task_id) | Yes — combined | LAX→COMPENSATED |
| Edit invalid priority → 422 (pass 1 fix) | test_edit_invalid_priority_returns_422 | Yes | COVERED |

No MISSING entries. LAX (audit log count-only assertions in TestFromAC_) compensated by TestBuilderDiscovered tests that verify `action` + `task_id` fields for all three endpoints.

#### Security Review

- S1 (informational): `detail=str(exc)` in edit route [mutation.py:178] surfaces full priorities list verbatim to caller. Low severity for internal API. No secrets, no PII.
- S2 (informational): `engine.move_task()` has no `try/except ValueError` guard; `edit_task` gained one in this cycle. The move pre-check (`if req.status not in transitions`) protects the happy path; the unguarded path is a speculative edge case only reachable via race or engine config change. Inconsistency noted.
- S3 (by design): `release_task` releases any agent's claim without ownership check — appears intentional admin behaviour.
- No hardcoded secrets, no injection vectors, `task_id: int` prevents path traversal, `extra="forbid"` on both request models. **No blocking issues.**

#### Test Integrity (§5.2)

All `TestFromAC_*` classes **INTACT**. Evidence:

- `test_edit_title_returns_200_with_new_title`: asserts `200` AND `json()["title"] == "Renamed task"` — body check preserved
- `test_edit_stale_updated_returns_409`: intervening engine mutation preserved — race simulation intact
- `test_edit_null_block_reason_clears_blocked_state`: asserts `blocked is False` AND `block_reason is None` — both fields verified
- `test_release_nonexistent_task_returns_404`: `"999" in detail` string check preserved
- No weakening or removal detected across all 25 original tests.

#### Test Quality (§5.3)

- TestBuilderDiscovered (4 tests): ADEQUATE. `test_edit_invalid_priority_returns_422` correctly fetches fresh `updated` before sending. Three audit-log content tests assert both `action` and `task_id` fields; action values ("move", "edit", "release") match engine string literals.
- TestFromAC_AuditLogging: individually LAX (count-only). Compensated per §5.0.
- `test_release_claimed_task_returns_200`: asserts status only. `test_release_returns_task_object_shape` checks body structure but not `claimed_by is None`. Core "unclaim" semantic unverified in response body. Noted; not a blocking issue given activity log evidence.

#### §5.5 Implementation-Aware Test Gaps

- Secondary gap: block/unblock mutations log `action="block"/"unblock"` (not `"edit"`). No TestBuilderDiscovered test verifies this action variant. Beyond explicit AC scope; informational.
- Secondary gap: empty-kwargs edit (only `updated` sent, no fields) returns original task silently. No test. Not an AC requirement.

#### §5.7 Builder Process Quality

- 2 `## Builder Notes` sections. Round 1: initial implementation. Round 2: targeted ValueError guard + TestBuilderDiscovered. Approach variation confirmed. **FRICTION** (2 cycles, not a loop).
- This is the 2nd review cycle — loop-breaker rule does not apply.

### Pass 2 — Informational

- `detail=str(exc)` surfaces priorities list (S2 above) — consider `detail="Invalid priority value"` to avoid config exposure.
- `test_move_happy_path_returns_200` asserts status code only; `test_move_returns_updated_task_object` provides body coverage — pair is adequate.
- TestBuilderDiscovered `cockpit_entries[0]` indexing assumes no prior cockpit entries in fixture; currently safe.
- `release_task` admin-release semantic would benefit from an inline comment.

### Deductions

| Criterion | Deduction | Reason |
|-----------|-----------|--------|
| TestFromAC_AuditLogging LAX (compensated) | −0.03 | Count-only assertions remain; TestBuilderDiscovered lifts overall to ADEQUATE |
| Secondary test gaps (block action, claimed_by, empty kwargs) | −0.02 | Below AC scope; informational |
| S2 move ValueError inconsistency | −0.01 | Speculative edge case, protected by pre-check |

**Confidence: 0.94 → PASS**

### Verdict

PASS — both Pass 1 FAIL criteria resolved: (1) invalid priority now returns 422 via `try/except ValueError` on edit route; (2) TestBuilderDiscovered provides action+task_id verification for all three audit log endpoints. TestFromAC_* classes untouched. 29/29 tests pass, lint clean.
[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | Updated | `copilot-instructions.md` §4: "read-only API" → "read/write API"; added 3 POST endpoints to Endpoints row; added `test_cockpit_mutation_api.py` to Test scope |
| 2 | Module docstrings | Yes | Verified | `routes/mutation.py`: module docstring ✓; `MoveRequest`, `EditRequest` ✓; `move_task`, `edit_task`, `release_task` route handlers ✓; `_build_edit_kwargs`, `_apply_list_diff` helpers ✓; all public items covered |
| 3 | External attribution | No | N/A | Research doc states "6 studied (all internal)" — no external sources used |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/932-cockpit-mutation-api-tests.md` exists and is linked from task body; follow-ups noted as none (GREEN #934 already existed) |

### Files updated

- `.github/copilot-instructions.md` — commit `251b33a9`

### Scratch files

- No `.owlbear/scratch/932-*` files found — nothing to clean
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Test file at tests/test_cockpit_mutation_api.py | File exists, 29 tests across 4 TestFromAC classes + 1 TestBuilderDiscovered class | PASS |
| Tests use FastAPI TestClient | Fixture at test_cockpit_mutation_api.py L116-L122 | PASS |
| POST /move with target status; validates valid_transitions | test_move_happy_path_returns_200, test_move_returns_updated_task_object; mutation.py L82-L97 checks adapter.valid_transitions | PASS |
| POST /move invalid target returns 422 | test_move_invalid_target_status_returns_422, test_move_same_status_returns_422 | PASS |
| POST /edit allowlisted fields (7 fields) | 6 per-field tests + test_edit_priority_returns_200; EditRequest extra=forbid at mutation.py L41 | PASS |
| POST /edit non-allowlisted field returns 422 | test_edit_status_field_rejected_422, test_edit_blocked_field_directly_rejected_422 | PASS |
| POST /edit requires updated snapshot | test_edit_missing_updated_returns_422 | PASS |
| POST /edit stale updated returns 409 (D9) | test_edit_stale_updated_returns_409; mutation.py L169-L172 compares timestamps | PASS |
| POST /release unclaims task | test_release_claimed_task_returns_200, test_release_returns_task_object_shape | PASS |
| POST /release unclaimed task returns 409 | test_release_unclaimed_task_returns_409; mutation.py L189 checks claimed_by | PASS |
| Block/unblock via block_reason | test_edit_block_reason_sets_blocked_state, test_edit_null_block_reason_clears_blocked_state | PASS |
| All mutations write activity.jsonl actor=cockpit | TestFromAC_AuditLogging x3 (count) + TestBuilderDiscovered x3 (action+task_id) | PASS |
| 404 per endpoint | 3 separate 404 tests (move, edit, release) | PASS |
| All tests fail (RED phase) | Test-writer confirmed 25 FAIL; builder GREEN made 25/25 pass; round 2 added 4 more (29 total) | PASS |

### Test Results

- pytest: 593 passed, 6 failed (all failures in serve/mcp-knowledge/tests/ -- pre-existing, unrelated to #932)
- ruff: clean
- Zero failures in cockpit or task scope

### Architect Quality: 4/5

AC was specific with 7 binding refinements from architecture review. Challenger consulted, 2/3 findings accepted. Minor gap: priority validation edge case not called out in AC (caught by reviewer). Overall strong upstream quality.

### Deduction Breakdown

- AC lines without evidence: 0 (all 14 lines verified) = -0.00
- Lint violations: none = -0.00
- AC quality score 4/5 (above 3): -0.00
- Reviewer evidence: present, detailed, two cycles = -0.00
- Full-suite test failures in task scope: 0 = -0.00

### Confidence: 1.00

### Action: archive
