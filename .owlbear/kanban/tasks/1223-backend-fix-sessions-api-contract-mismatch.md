---
id: 1223
title: Backend — fix sessions API contract mismatch
status: review
priority: needed
created: 2026-04-30 16:31:18.589039+00:00
updated: 2026-04-30T22:50:26.922725+00:00
tags:
- cockpit
- bug
parent:
depends_on: []
blocked: false
block_reason:
claimed_at: 2026-04-30T22:50:26.922725+00:00
archival_reason:
archival_refs: []
---

## Objective
Fix contract mismatch between GET /api/sessions response shape and frontend expectations. The frontend contract is established: both ActivityTab.tsx and DetailTab.tsx access `data.sessions`, and their Vitest tests stub fetch as `{ sessions: [...] }`. The backend is the side that is wrong.

## Acceptance Criteria
- [ ] Add `SessionsResponse(BaseModel)` with `sessions: list[SessionRecord]` to `serve/cockpit/src/owlbear_cockpit/routes/read.py` (inline, following the `CockpitListTasksResponse` pattern) (td:1)
- [ ] `GET /api/sessions` handler updated: `response_model=SessionsResponse`, returns `SessionsResponse(sessions=view.list_sessions(filter=filter))` (td:2)
- [ ] `test_cockpit_read_api.py` `TestFromAC_Sessions`: `test_sessions_response_has_sessions_list` asserts `body` is a dict with key `"sessions"` whose value is a list; `test_sessions_each_entry_has_task_id_and_state` iterates `body["sessions"]` (td:1)
- [ ] No changes to `ActivityTab.tsx` or `DetailTab.tsx` — both already access `data.sessions` correctly (td:0)

## Context
Backend returns `list[SessionRecord]` at top level. Both `ActivityTab.tsx` (line 57-58) and `DetailTab.tsx` (line 67-68) do `data.sessions` expecting an envelope. Their Vitest test fixtures (`ActivityTab.test.tsx`, `DetailTab.test.tsx`) also stub fetch as `{ sessions: [...] }`. The frontend contract is therefore settled — only the backend and its Python tests require changes.

## Files
- `serve/cockpit/src/owlbear_cockpit/routes/read.py` — add SessionsResponse model, update handler
- `tests/test_cockpit_read_api.py` — update TestFromAC_Sessions body assertions

[[2026-04-30]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One broken API contract, one fix direction |
| Interface clarity | PASS (after refine) | "Or" option removed; contract definitively set by existing frontend |
| Dependency correctness | PASS | No depends_on needed; standalone bug fix |
| Module layering | PASS | Change scoped to routes/read.py (new model inline) + test update; no upward imports |
| TDD compliance | PASS | test_cockpit_read_api.py TestFromAC_Sessions exists; needs assertion update |
| KISS/YAGNI | PASS | Minimal fix: inline model + handler wrapper + 2 test assertion rewrites |
| Premise challenge | PASS | Backend genuinely wrong; frontend contract established in 2 components + 2 test files |
| Pattern consistency | PASS | Inline model follows CockpitListTasksResponse precedent in same file |
| Security surface | PASS | No new input surface; response adds a wrapper key only |
| Single domain | PASS | Cockpit backend only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| view.list_sessions() | Engine error | propagates as 500 | Pre-existing, not changed by this task | Tab shows no sessions |

### Design Diverge
- Trigger: skipped — Option B (fix frontend) ruled out immediately: two components + two Vitest suites already lock the envelope contract; changing the frontend would require updating 4 files with no architectural gain.

### Challenge Results
- Challenger: SKIPPED — REFINE verdict (challenge only on APPROVE)
- Architect response: N/A

### Test Depth
- Max depth: td:2 (handler return value change)
- Test-writer: PROCEED

### Verdict: REFINE → APPROVE
### Action Taken: Rewrote AC to (1) remove ambiguous "or" option, (2) specify SessionsResponse model placement and exact field shape, (3) name exact test methods and assertion changes, (4) confirm no frontend changes needed (both components already correct). Advanced to todo.
[[2026-04-30]]
## Test-Writer Notes
- Test file: `tests/test_cockpit_read_api_1223.py`
- Classes: `TestFromAC_SessionsEnvelope`
- Module-level edits: `tests/test_cockpit_read_api.py` — 2 assertions in `TestFromAC_Sessions` updated per AC3

### Tests per category (task-scoped file)
| Category | Count | Tests |
|----------|-------|-------|
| AC1 — model import | 1 | `test_sessions_response_model_importable_with_sessions_field` |
| Happy path | 2 | `test_sessions_all_filter_returns_dict_with_sessions_key`, `test_sessions_active_filter_returns_dict_with_sessions_key` |
| Edge | 2 | `test_sessions_no_param_returns_dict_with_sessions_key`, `test_sessions_empty_board_wraps_empty_list` |
| Boundary | 1 | `test_sessions_envelope_has_only_sessions_key` |
| **Total** | **6** | all FAIL ✓ |

### Module-level updates (AC3, td:1)
| Test | Old assertion | New assertion | Result |
|------|---------------|---------------|--------|
| `test_sessions_response_has_sessions_list` | `isinstance(body, list)` | `isinstance(body, dict)` + `"sessions" in body` + `isinstance(body["sessions"], list)` | FAIL ✓ |
| `test_sessions_each_entry_has_task_id_and_state` | `sessions = response.json()` | `sessions = body["sessions"]` | FAIL ✓ |

### AC coverage
| AC line | td | Tests |
|---------|----|-------|
| AC1: Add `SessionsResponse(BaseModel)` to `read.py` | td:1 | `test_sessions_response_model_importable_with_sessions_field` |
| AC2: Handler returns `SessionsResponse(sessions=...)` | td:2 | 5 tests (all/active/no-param/empty/boundary) |
| AC3: Update 2 existing tests in `test_cockpit_read_api.py` | td:1 | Both tests updated and FAIL |
| AC4: No frontend changes | td:0 | skipped |

### Failure summary
- 6 FAIL in `test_cockpit_read_api_1223.py` (ImportError + AssertionError — body is list not dict)
- 2 FAIL in `test_cockpit_read_api.py` (AssertionError / TypeError — body is list not dict)
- 46 pre-existing pass unaffected
- Ruff lint: clean

### Builder note
`test_sessions_active_is_default_filter` in `test_cockpit_read_api.py` (existing, not AC-listed) also does `assert isinstance(body, list)` — this will fail after the backend fix. Builder should update that assertion to `assert isinstance(body, dict)` as part of the GREEN implementation.
[[2026-04-30]]
## Builder Notes
- Implementation: updated serve/cockpit/src/owlbear_cockpit/routes/read.py to add `SessionsResponse(BaseModel)` and changed `GET /api/sessions` to `response_model=SessionsResponse` returning `SessionsResponse(sessions=view.list_sessions(filter=filter))`.
- Durable alignment: updated tests/test_cockpit_read_api.py `TestFromAC_Sessions::test_sessions_active_is_default_filter` to assert dict envelope with `sessions` list.
- Tests (RED evidence before implementation): quality-runner on `tests/test_cockpit_read_api_1223.py` -> 0 passed / 6 failed (missing `SessionsResponse`, list-vs-dict contract mismatch).
- Tests (module baseline before implementation): quality-runner on `tests/test_cockpit_read_api.py` -> 46 passed / 2 failed (session envelope assertions).
- Tests (GREEN, task-scoped): quality-runner on `tests/test_cockpit_read_api_1223.py` -> 6 passed / 0 failed.
- Tests (GREEN, regression scoped): quality-runner on `[tests/test_cockpit_read_api.py, tests/test_cockpit_read_api_1223.py]` -> 54 passed / 0 failed.
- Coverage: `owlbear_cockpit.routes.read` at 98% (missing line 141 only) on scoped regression run.
- Ruff: clean on touched source + scoped tests.
- Commit: `cb6f145e` (`fix: wrap sessions API in envelope (#1223, builder)`) with only:
  - serve/cockpit/src/owlbear_cockpit/routes/read.py
  - tests/test_cockpit_read_api.py

Post-task reflection:
- Problems faced: none structural; only one additional durable assertion needed to match the corrected envelope contract.
- Workaround applied: used dual scoped quality-runner passes (task file + module file) to separate AC proof from regression proof.
- Pattern discovered: session API consumers and tests are envelope-first (`data.sessions`), so backend should preserve wrapped responses consistently.
- Time sink: minimal; majority spent on required RED/GREEN evidence collection.
- Quality gap: task-scoped-only coverage understates route-module coverage; combined scoped run gives accurate gate signal for this endpoint fix.