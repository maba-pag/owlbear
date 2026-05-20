---
id: 1660
title: 'P1-01: Backend Ideas API — GET/PUT /api/ideas with DI and atomic_write'
status: archived
priority: needed
created: 2026-05-18T17:41:31.832363+02:00
updated: 2026-05-20T13:28:16.410011+02:00
tags:
  - phase-1
  - scope:cockpit
  - backend
parent: 1658
depends_on:
  - 1638
ac:
  - 'GET `/api/ideas` returns `{"content": "..."}` with file contents when `.owlbear/ideas.md`
    exists; returns `{"content": ""}` when file is absent'
  - 'PUT `/api/ideas` accepts `{"content": "..."}` body, writes via `atomic_write`
    imported from `owlbear_kanban.storage_io`, creates file on first write when absent,
    and returns HTTP 204'
  - '`get_ideas_path` dependency returns a `Path` and is overridable via `app.dependency_overrides`
    for test isolation'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Context

Brief: see parent #1658 (`.owlbear/briefs/draft-cockpit-ideas/brief.md`)

Route module at `serve/cockpit/src/owlbear_cockpit/routes/ideas.py` with bare `APIRouter()`. Prefix applied at mount in `main.py` per existing cockpit convention.

Request/response models: Pydantic `BaseModel` with `ConfigDict(extra="forbid")` per existing cockpit convention.

`get_ideas_path` resolves to `kanban_dir.parent / "ideas.md"` (`.owlbear/ideas.md`).

## In Scope

- Route module with GET and PUT endpoints
- `get_ideas_path` DI dependency
- Pydantic request/response models
- Router mount in `main.py`

## Out of Scope

- Frontend consumption (separate task)
- SSE/file-watcher (not needed per brief)
- OCC/versioning (last-write-wins accepted)

[[2026-05-20T12:48:16+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Backend API only — GET/PUT + DI + mount |
| Interface clarity | PASS | Endpoints, status codes, response shapes, DI override pattern all specified |
| Dependency correctness | PASS | #1638 archived/completed; no missing deps |
| Module layering | PASS | Cockpit already imports from owlbear_kanban (engine, storage_io); no upward imports |
| TDD compliance | PASS | Proof bundle behavioral → full TDD will precede implementation |
| KISS/YAGNI | PASS | Minimal: 2 endpoints, 1 DI dep. No OCC, no SSE — per Brief scope |
| Premise challenge | PASS | Cockpit needs to serve ideas content; no existing alternative |
| Pattern consistency | PASS | Follows router mount, deps.py DI composition, Pydantic extra=forbid patterns |
| Security surface | PASS | Localhost-only API, fixed path via DI (no path traversal), content is freeform markdown |
| Single domain | PASS | Cockpit backend scope only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| GET when file absent | FileNotFoundError | caught in handler | Yes (returns empty content per AC) | None |
| PUT disk write failure | OSError from atomic_write | Global 500 handler | Yes (propagates as 500) | Error envelope |

### Design Diverge
- Trigger: skipped — single obvious approach matching established cockpit patterns

### Challenge Results
- Challenger: reconsider (confidence 0.74)
- Issues raised: AC-2 mixes observable/implementation constraint; AC-3 lacks explicit observable behavior statement; error contract not specified
- Architect response: OVERRIDE — AC follows established cockpit patterns (decisions routes, memory routes use identical AC style). Test-writer has clear precedent in test_cockpit_decisions_api.py for DI override testing. Error handling covered by global exception handlers in main.py. Implementation constraints in AC are intentional architectural direction from Brief.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC precise and testable given cockpit patterns. Challenger override justified — style concerns don't create downstream ambiguity.

[[2026-05-20T12:53:08+02:00]]
## Test-Writer Notes
- Test file: tests/test_cockpit_ideas_1660.py
- Classes: TestFromAC_IdeasGet, TestFromAC_IdeasPut, TestFromAC_IdeasPathDep
- Tests per category: happy 7, edge 5, error 3, boundary 5
- Total: 20 tests, all FAIL (4 direct ImportError failures + 16 setup errors — all stem from missing `get_ideas_path` in `owlbear_cockpit.deps` and missing `owlbear_cockpit.routes.ideas` module)
- ruff: clean

AC coverage:
| AC | Tests |
|----|-------|
| AC1: GET returns content when file exists | test_get_returns_200_when_file_exists, test_get_returns_content_from_file, test_get_returns_content_key_in_response |
| AC1: GET returns empty string when absent | test_get_returns_empty_string_when_file_absent, test_get_returns_200_when_file_absent, test_get_content_is_not_null_when_file_absent |
| AC1: empty file edge | test_get_empty_file_returns_empty_string |
| AC2: PUT returns 204 | test_put_returns_204_when_file_exists, test_put_returns_no_body |
| AC2: PUT writes content | test_put_writes_content_to_file |
| AC2: creates on first write | test_put_creates_file_on_first_write |
| AC2: uses atomic_write | test_put_uses_atomic_write, test_put_atomic_write_receives_correct_path |
| AC2: empty content accepted | test_put_accepts_empty_content |
| AC2: missing field → 422 | test_put_rejects_missing_content_field |
| AC2: extra fields → 422 | test_put_rejects_extra_fields |
| AC3: dep importable | test_get_ideas_path_exists_in_deps |
| AC3: returns Path | test_get_ideas_path_returns_path_instance |
| AC3: overridable | test_dependency_overridable_for_test_isolation |
| AC3: router mounted | test_ideas_router_is_mounted_under_api_prefix |

[[2026-05-20T13:00:55+02:00]]
## Builder Notes

### Files Changed
- serve/cockpit/src/owlbear_cockpit/deps.py
- serve/cockpit/src/owlbear_cockpit/routes/ideas.py
- serve/cockpit/src/owlbear_cockpit/main.py

### Implementation Summary
- Added `get_ideas_path` dependency in `deps.py` resolving to `Path(engine.kanban_dir).parent / "ideas.md"` for `.owlbear/ideas.md`.
- Created new `routes/ideas.py` with:
  - `GET /ideas` returning `{"content": "..."}` from file and `{"content": ""}` on `FileNotFoundError`.
  - `PUT /ideas` accepting strict `IdeasUpdateRequest` (`ConfigDict(extra="forbid")`), persisting with `atomic_write`, and returning HTTP 204 with empty body.
- Mounted `ideas_router` in `main.py` under `/api` to expose `/api/ideas`.

### RED Verification (Before Implementation)
- quality-runner scoped run on `tests/test_cockpit_ideas_1660.py`:
  - passed: 0
  - failed: import/setup failures due to missing `get_ideas_path` and missing ideas route module

### GREEN Verification (After Implementation)
- quality-runner scoped run:
  - test_paths: `tests/test_cockpit_ideas_1660.py`
  - lint_paths: `serve/cockpit/src/owlbear_cockpit/`, `tests/test_cockpit_ideas_1660.py`
  - coverage_modules: `owlbear_cockpit.routes.ideas`
- Results:
  - tests: 20 passed, 0 failed
  - lint: clean (`ruff` clean)
  - coverage: `owlbear_cockpit.routes.ideas` = 100%

### Durable Module Test Check
- No module-level durable test file exists for this domain module (searched `tests/**/test_cockpit_ideas*.py`; only task-scoped `tests/test_cockpit_ideas_1660.py` present). Recorded as skip per workflow guidance.

### Fixes Applied During Verification
- Resolved a single lint defect in new route file (`W292` no newline at EOF).

### Commit
- `8e99b9f0` — feat: implement cockpit ideas API backend (#1660, builder)

### Evidence Summary
- AC1 satisfied by GET behavior for existing/missing ideas file.
- AC2 satisfied by strict PUT request model, `atomic_write` usage, file creation on first write, and 204 response.
- AC3 satisfied by importable/overridable `get_ideas_path` and mounted ideas router under `/api`.

[[2026-05-20T13:07:42+02:00]]
## Review Evidence
- Verdict: FAIL
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC3: `get_ideas_path` dependency returns a `Path` and is overridable via `app.dependency_overrides` for test isolation | The task suite does not execute the default dependency implementation or assert its concrete return type. `test_get_ideas_path_returns_path_instance` is vacuous because it falls back to `None` when `__wrapped__` is absent, so it passes without proving a `Path` return. All request-level tests override the dependency, leaving the default implementation untested. | `tests/test_cockpit_ideas_1660.py:210-219`; `tests/test_cockpit_ideas_1660.py:221-239`; `serve/cockpit/src/owlbear_cockpit/deps.py:72-74` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Replace the vacuous AC3 return-type check with executable proof that the default `get_ideas_path` implementation returns a `Path` from an injected engine context, and make the test fail if a non-`Path` value is returned. | `tests/test_cockpit_ideas_1660.py` | Finding #1; `tests/test_cockpit_ideas_1660.py:210-219`; `serve/cockpit/src/owlbear_cockpit/deps.py:72-74` |

## Observations
- Direct source inspection indicates the current implementation aligns with AC1 and AC2 in `serve/cockpit/src/owlbear_cockpit/routes/ideas.py:12,28,34-46`, and AC3 overridability is covered by `tests/test_cockpit_ideas_1660.py:221-239`.
- Builder evidence was otherwise internally consistent: task-scoped tests passed, lint was clean, and route-module coverage was reported as 100%; the blocking issue is limited to missing executable proof for the default dependency branch of AC3.
- Challenger cross-check returned `proceed` with confidence `0.87` on the proposed `FAIL -> todo` verdict.

[[2026-05-20T13:10:05+02:00]]
## Test-Writer Notes
- Retry: replaced vacuous `test_get_ideas_path_returns_path_instance` with executable proof.
- Old test fell back to `None` via `__wrapped__` check, asserting `None or isinstance(result, Path)` — trivially true without executing the dependency.
- New test creates a `MagicMock` engine with `kanban_dir` set, calls `get_ideas_path(engine=mock_engine)` directly (bypassing FastAPI DI), and asserts `isinstance(result, Path)` unconditionally.
- File: `tests/test_cockpit_ideas_1660.py` — `TestFromAC_IdeasPathDep.test_get_ideas_path_returns_path_instance`
- Quality-runner: 20 passed, 0 failed, ruff clean.
- Commit: `8b03e1d8`
- Builder skip: test-only retry, all 20 tests green against current implementation.

[[2026-05-20T13:19:13+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1660 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first and found internally consistent: builder reported quality-runner GREEN with 20 passed / 0 failed, ruff clean, and 100% coverage for `owlbear_cockpit.routes.ideas`; the test-writer retry replaced the prior vacuous AC3 proof and again reported 20 passed / 0 failed with ruff clean.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1: GET `/api/ideas` returns file contents when present and `{"content": ""}` when absent | `serve/cockpit/src/owlbear_cockpit/routes/ideas.py:34-40` reads the file, catches `FileNotFoundError`, and returns `IdeasResponse(content=content)` | `tests/test_cockpit_ideas_1660.py:85` proves existing-file content is returned; `tests/test_cockpit_ideas_1660.py:100` proves absent-file response is exactly `{"content": ""}` | PASS |
| AC2: PUT `/api/ideas` accepts `{"content": "..."}`, writes via `atomic_write`, creates on first write, and returns 204 | `serve/cockpit/src/owlbear_cockpit/routes/ideas.py:25-28` uses strict request validation with `ConfigDict(extra="forbid")`; `serve/cockpit/src/owlbear_cockpit/routes/ideas.py:44-47` calls `atomic_write(ideas_path, req.content)` and returns 204 | `tests/test_cockpit_ideas_1660.py:157-158` proves first write creates the file and persists content; `tests/test_cockpit_ideas_1660.py:165` proves `atomic_write` is called with the injected ideas path; `tests/test_cockpit_ideas_1660.py:187` proves extra fields are rejected with 422; `tests/test_cockpit_ideas_1660.py:193` proves the 204 response has no body | PASS |
| AC3: `get_ideas_path` returns a `Path` and is overridable via `app.dependency_overrides` for test isolation | `serve/cockpit/src/owlbear_cockpit/deps.py:72-74` defines `get_ideas_path(...) -> Path`; `serve/cockpit/src/owlbear_cockpit/main.py:49` mounts the ideas router under `/api` | `tests/test_cockpit_ideas_1660.py:220` now executes the default dependency directly and asserts it returns a `Path`; `tests/test_cockpit_ideas_1660.py:239` proves dependency override isolation; `tests/test_cockpit_ideas_1660.py:245` proves `/api/ideas` is mounted and reachable | PASS |

- Safety & security: PASS. No user-controlled path input reaches filesystem; the write target is supplied by fixed DI, request extras are forbidden, and no new dependency or secret-handling surface was introduced.
- Challenger cross-check: proceed, confidence 0.84. No blocking findings.

## Observations
- The prior AC3 blocker is resolved. The retry removed the vacuous return-type check and replaced it with executable proof against `get_ideas_path(engine=mock_engine)`.
- The dedicated mount assertion at `tests/test_cockpit_ideas_1660.py:245` is weaker than the AC1 GET assertions because it only rules out 404; this is non-blocking because the stronger AC1 request-level tests already prove the mounted route returns 200 with the expected payload shape.
- The builder's reported 100% coverage applies to `owlbear_cockpit.routes.ideas`; AC3 evidence for `deps.py` and `main.py` is supplied by direct tests and source inspection rather than that coverage figure.

[[2026-05-20T13:21:52+02:00]]
## Docs Gate

### Item 1: README Verification
- Convention mapping: `serve/cockpit/src/**` → `serve/cockpit/README.md`
- **Finding:** No Ideas API section existed in the README; `GET /api/ideas` and `PUT /api/ideas` were undocumented.
- **Fix:** Added `## Ideas API` section (between Memory API and Work Sessions Model) documenting both endpoints: response shapes, absent-file behavior, strict request model, `atomic_write` semantics, HTTP 204, and the `get_ideas_path` DI callable and override pattern.
- Also updated `.github/copilot-instructions.md` Endpoints table to add `GET /api/ideas` and `PUT /api/ideas` (task-caused drift in workspace config doc).
- Pre-existing TODO markers at README:287 (#1628) and README:564 (#1571) are pass-through — scope predates this task.
- Layer 1 (grep) and Layer 2 (editorial) both clean after update.

### Item 2: External Attribution
- N/A — no external sources used; implementation follows established cockpit patterns.

### Item 3: Research Doc
- N/A — no research artifact exists for this task.

### Item 4: Deletion Detection
- N/A — no files deleted.

### Commit
- `5a080c51` — docs: add ideas API section to cockpit README (#1660, doc-writer)

### Scratch Cleanup
- No `.owlbear/scratch/1660-*` files existed.

[[2026-05-20T13:28:16+02:00]]
## Audit

### Regression Detection
Quality-runner full-suite: 252 failures all pre-existing (from files last modified in bulk formatting commits `414444b9` predating task). No changes to any failing test file since builder commit `8e99b9f0`. Cockpit-domain regression: 404 tests passed, 0 failed. Task-scoped: 20/20 passed. Lint: clean (ruff + eslint). **No task-caused regressions.**

### Intent Verification
Changed files: `serve/cockpit/src/owlbear_cockpit/{deps.py,main.py,routes/ideas.py}`, `tests/test_cockpit_ideas_1660.py`, `serve/cockpit/README.md`, `.github/copilot-instructions.md`. All within cockpit backend domain + docs. Implementation adds GET/PUT /api/ideas with DI — matches stated purpose. No extraneous scope.

### Architect Quality
Score: 4/5. AC specified endpoints, response shapes, DI pattern, strict request model, and file-absent behavior clearly. One reviewer cycle (vacuous test for AC3 default path) — but that was a test-proof gap, not an AC ambiguity. Builder implemented correctly on first pass without improvisation.

### Commit Integrity
- `4cc5a2bb` — test: add failing tests for cockpit ideas API (#1660, test-writer)
- `8e99b9f0` — feat: implement cockpit ideas API backend (#1660, builder)
- `8b03e1d8` — test: replace vacuous ideas path dep test with executable proof (#1660, test-writer)
- `5a080c51` — docs: add ideas API section to cockpit README (#1660, doc-writer)

All 4 commits properly attributed. No uncommitted deliverables.

### Reviewer Evidence
Detailed PASS verdict with full AC-to-code mapping. Challenger cross-check: proceed (0.84). Safety/security: PASS.

### Scoring
| Criterion | Deduction |
|-----------|----------|
| (none) | 0 |

**Confidence: 1.00 — Archive.**
