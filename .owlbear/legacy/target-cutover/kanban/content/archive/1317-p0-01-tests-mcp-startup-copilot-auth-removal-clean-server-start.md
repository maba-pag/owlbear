---
id: 1317
title: 'P0-01: Tests — MCP startup (copilot_auth removal, clean server start)'
status: archived
priority: medium
created: 2026-05-04T05:48:37.741242+00:00
updated: 2026-05-04T10:12:52.495196+00:00
tags:
- phase-0
- scope:mcp-knowledge
- knowledge
- test
parent: 1316
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md`

## Acceptance Criteria

- [ ] Tests verify `copilot_auth` is not imported during `app_lifespan` (absent from `sys.modules` after lifespan completes) and `structured_extractor` is `None` when `OWLBEAR_LLM_API_KEY` is unset (td:1)
- [ ] Tests verify `IngestPipeline` is constructed and `KnowledgeQueryService` is available in lifespan context when `structured_extractor` is `None` (td:1)
- [ ] Tests verify token file is absent INSIDE the lifespan body (`async with app_lifespan(...) as ctx:` — assertion before block exit), proving deletion is a startup action not teardown; idempotent case exercises real `Path.unlink` on absent file without raising (td:2)
- [ ] Existing tests in `test_copilot_server_wiring_888.py` replaced with new tests reflecting removed auth flow (td:0)

## Scope

- **In scope:** Test coverage for MCP lifespan without copilot_auth, pipeline/query-service wiring verification, token file cleanup
- **Out of scope:** LLM-based entity extraction (agent workers), search result quality (covered by `test_search_v2.py`), collateral fixture cleanup in other test files

## Research

Investigated MCP startup test scope for copilot_auth removal.

**Key findings:**
- All 5 existing tests in `test_copilot_server_wiring_888.py` currently PASS but test the copilot_auth fallback path that #1318 will delete — all 5 must be replaced
- `EntityExtractor(extractor=None)` is a working no-op stub; `IngestPipeline` constructs normally with it; vector search via `KnowledgeQueryService` is independent of entity extraction
- 3 collateral test files use `_bypass_copilot_auth` fixtures — harmless after removal, no breakage risk
- Token cleanup path: `~/.owlbear/copilot_token.json` (constant in `copilot_auth.py` line 26)

**Test plan:** 5 replacement tests covering AC1-AC4:
1. No copilot_auth import during lifespan without API key
2. IngestPipeline constructed with null extractor
3. QueryService available for vector search
4. Token file cleanup (delete existing)
5. Token file cleanup (idempotent when absent)

**Tier:** T1 — Autonomous (test file replacement, no architecture change)

Research doc: `.owlbear/research/1317-mcp-startup-test-scope.md`
No additional follow-up tasks needed — #1318 already exists as implementation counterpart.
[[2026-05-04]]
## Architecture Review

### Verdict: APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: `copilot_auth` not imported, `structured_extractor` is None (td:1) | Precise — `sys.modules` check is structurally correct for RED phase; if import occurs (even in try/except), module appears in sys.modules | Refined: specified `app_lifespan` as target function, `OWLBEAR_LLM_API_KEY` unset as condition |
| AC2: `IngestPipeline` + `KnowledgeQueryService` wired (td:1) | Narrowed — original "vector search returns results" over-claimed; actual search tested in `test_search_v2.py` | Refined: scoped to wiring availability in lifespan context |
| AC3: Token file cleanup in lifespan (td:2) | Tied to lifespan startup — path `~/.owlbear/copilot_token.json` hardcoded in AC (independent of copilot_auth.py after removal) | Refined: specified two cases (delete existing, idempotent when absent) |
| AC4: Test file replacement (td:0) | Meta-criterion, no test needed | Unchanged |

### Architecture Notes

- **Module scope:** Tests target `app_lifespan` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (L263-361)
- **Existing patterns:** Current `test_copilot_server_wiring_888.py` uses `async with app_lifespan(MagicMock()) as ctx:` with autouse fixtures patching I/O deps — new tests follow same pattern
- **Token path authority:** After copilot_auth.py removal, path is hardcoded in AC; test uses `tmp_path` isolation
- **Adjacent coverage:** `test_server.py` covers query-service presence; `test_search_v2.py` covers search result shaping; `test_llmextractor_wiring_876.py` tests EntityExtractor(extractor=None) on no-key paths — no overlap conflicts

### Dependency Analysis

- No dependencies (Layer 0 foundation task)
- #1318 depends on this task (correct TDD pairing: RED → GREEN)
- No missing dependencies identified

### Challenger Results

- Challenger confidence: 0.58 (reconsider)
- Challenges addressed: (1) AC1 sys.modules check is valid for RED phase — structurally proves absence of import; (2) AC2 narrowed from "returns results" to "wiring availability" per challenger's point about over-claiming; (3) AC3 tied to lifespan startup per call-site ambiguity concern; (4) Board body updated with refined td-annotated AC before approval
- Residual: collateral fixture cleanup in 3 other test files is explicitly out of scope (harmless vestigial env var settings)
[[2026-05-04]]
## Test-Writer Notes
- Test file: tests/test_server_1317.py
- Classes: TestFromAC_LifespanNoCopilotAuth, TestFromAC_TokenFileCleanup
- Tests per category: happy 3, edge 1, error 0, boundary 0
- Total: 5 tests, all FAIL
- ruff: clean

### AC Coverage

| AC | Tests | Failure reason (current) |
|----|-------|--------------------------|
| AC1: copilot_auth not imported; structured_extractor None | test_copilot_auth_not_imported_when_no_api_key, test_structured_extractor_is_none_without_api_key | get_copilot_token IS called; structured_extractor is LLMExtractor mock |
| AC2: IngestPipeline + QueryService wired with null extractor | test_ingest_pipeline_and_query_service_wired_with_null_extractor | structured_extractor not None (copilot path sets it) |
| AC3 happy: token file deleted when present | test_token_file_deleted_when_present_at_startup | no cleanup code — file survives lifespan |
| AC3 edge: idempotent when absent | test_token_file_cleanup_idempotent_when_absent | no cleanup code — Path.unlink never called |
| AC4: test file replacement (td:0) | n/a | meta-criterion, no test needed |

### Design notes
- Autouse fixture patches 7 heavy deps (init_db, GraphStore, QdrantVectorStore, BgeM3EmbeddingProvider, KnowledgeQueryService, GraphAugmentedRetriever, make_evaluate_fn) — identical to pattern in test_copilot_server_wiring_888.py
- AC1/AC2 tests inject mock_auth + mock_llm into sys.modules to prevent real network calls while preserving the copilot path's execution
- AC3 tests use monkeypatch.setitem(sys.modules, copilot_auth, None) to block the import; Path.home patched to tmp_path for hermetic token-file isolation
[[2026-05-04]]
## Builder Notes
- Implementation target reviewed: serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
- Code behavior now matches AC1/AC2/AC3 contract during `app_lifespan`:
  - no `copilot_auth` fallback path executed when API key is unset
  - `structured_extractor` remains `None` without API key
  - stale `~/.owlbear/copilot_token.json` cleanup is idempotent (`unlink(missing_ok=True)`)
- Scoped GREEN evidence (quality-runner):
  - tests: `tests/test_server_1317.py` + `serve/mcp-knowledge/tests/test_server.py` => 15 passed, 0 failed
  - lint: clean for `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`
  - coverage (module): 43%
- Broader mcp-knowledge regression evidence (quality-runner):
  - `serve/mcp-knowledge/tests` => 172 passed, 11 failed
  - includes 5 failing legacy tests in `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py` that assert removed copilot fallback behavior
  - module coverage plateaus at 68% (<90 gate) even with full package tests
- Commit status:
  - no new local commit created in this builder cycle (target file matches HEAD at end of run)

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Replace/remove legacy copilot-fallback assertions so AC4 is satisfied by test suite state | serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py, tests/test_server_1317.py | quality-runner package run: 5 failures in `TestFromAC_CopilotServerFallback` conflicting with no-copilot contract |
| 2 | test-writer | Reconcile strict mock signature expectation in search v2 test (`scopes=None` kwarg) with current tool contract before next builder gate | serve/mcp-knowledge/tests/test_search_v2.py | quality-runner broad run: `test_limit_forwarded_as_top_k_to_query` expected `query(..., top_k=7)` got `query(..., top_k=7, scopes=None)` |
| 3 | architect | Clarify coverage gate expectations for large legacy module touchpoints where task-scoped AC tests cannot reach module 90% and builder cannot add tests | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py | quality-runner: 43% on scoped run; 68% on full package run despite expanded test set |
[[2026-05-04]]
## Test-Writer Notes (retry)
- Retry: replaced 5 legacy copilot-fallback tests; fixed 1 strict-mock assertion
- Changed files: serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py, serve/mcp-knowledge/tests/test_search_v2.py

### Changes
| Item | Action | Result |
|------|--------|--------|
| `TestFromAC_CopilotServerFallback` (5 tests) | Replaced with `TestFromAC_ApiKeyPath` (3 tests) | 3 PASS — tests API-key path (complementary to test_server_1317.py) |
| `test_search_v2.py::test_limit_forwarded_as_top_k_to_query` | Updated `assert_awaited_once_with` to include `scopes=None` | 1 PASS — matches actual call signature |

### Verification
- Scoped run: `test_copilot_server_wiring_888.py` + `test_search_v2.py` + `test_server_1317.py` → 26 passed, 0 failed
- ruff: clean
- Commit: 2741465d
[[2026-05-04]]
## Builder Notes
- Files changed: none (no additional implementation required in this builder cycle)
- Evidence of AC behavior in source: `app_lifespan` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` already performs startup token cleanup (`Path.home()/".owlbear"/"copilot_token.json"` with `unlink(missing_ok=True)`), keeps `structured_extractor=None` when no API key is set, and wires `IngestPipeline` + `KnowledgeQueryService` for lifespan context.
- RED check (protocol verification): `tests/test_server_1317.py` TestFromAC classes currently pass, indicating implementation already exists.
- Final scoped quality-runner verification:
  - tests: 36 passed, 0 failed
  - lint: ruff clean
  - coverage module (`owlbear_mcp_knowledge.server`): 45%
- Coverage note: no source code edits were made by builder in this cycle; this was a verification/pass-through advance after test-writer retry and existing implementation alignment.
- Commit: none (no file modifications to stage/commit).
[[2026-05-04]]
## Review Evidence
### Test Results
- pytest: 26 passed, 0 failed (scoped quality-runner run on `tests/test_server_1317.py`, `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py`, and `serve/mcp-knowledge/tests/test_search_v2.py`)

### Lint: clean
- ruff: 0 violations on `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, `tests/test_server_1317.py`, `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py`, and `serve/mcp-knowledge/tests/test_search_v2.py`

### Coverage: `owlbear_mcp_knowledge.server`: 45%
- Informational only for this cycle. Latest builder section says `Files changed: none` in the pass-through verification cycle, so module-level coverage is not a blocking gate for untouched source.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: `copilot_auth` not imported during `app_lifespan` and `structured_extractor` is `None` when no API key is set | `test_copilot_auth_not_imported_when_no_api_key`; `test_structured_extractor_is_none_without_api_key` | Partially. `structured_extractor is None` is discriminating, but the import-absence half is not: the test preloads `owlbear_knowledge.copilot_auth` into `sys.modules` and ends with `mock_auth.get_copilot_token.assert_not_called()` at `tests/test_server_1317.py:114`. A regression that imports `copilot_auth` but never calls the getter would stay green. | LAX |
| AC2: `IngestPipeline` constructed and `KnowledgeQueryService` available in lifespan context when `structured_extractor` is `None` | `test_ingest_pipeline_and_query_service_wired_with_null_extractor` | No. The proof stops at `assert ctx.ingest_pipeline is not None` / `assert ctx.query_service is not None` at `tests/test_server_1317.py:175-176`. Those assertions would also pass if arbitrary placeholder objects were assigned instead of the actual instances created at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:283-289` and stored at `:313-317`. | LAX |
| AC3: startup deletes stale `~/.owlbear/copilot_token.json` and cleanup is idempotent when file is absent | `test_token_file_deleted_when_present_at_startup`; `test_token_file_cleanup_idempotent_when_absent` | Mixed. The delete-present case is strong (`assert not token_file.exists()` at `tests/test_server_1317.py:219`). The absent-file/idempotency case is not: it patches `Path.unlink` and only asserts `mock_unlink.assert_called()` at `tests/test_server_1317.py:237-244`. That would stay green for a non-idempotent bare `unlink()` because the mock suppresses `FileNotFoundError`, so the `missing_ok=True` contract at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:249` is not discriminated. | LAX |
| AC4: existing tests in `test_copilot_server_wiring_888.py` replaced with tests reflecting removed auth flow | `TestFromAC_ApiKeyPath` replacement suite | Yes. The legacy copilot-fallback class is gone and the replacement API-key-path suite is present at `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py:61-106`, matching the retry note. | COVERED |

#### Security Review
- No issues found. In-scope production code only unlinks a fixed local token file at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:249` and conditionally constructs `LLMExtractor` from env configuration at `:262-271`. No shell, SQL, unsafe deserialization, or user-controlled path handling was introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_LifespanNoCopilotAuth` | No builder edits in final cycle; final builder section states `Files changed: none` | PRESERVED |
| `TestFromAC_TokenFileCleanup` | No builder edits in final cycle | PRESERVED |
| `TestFromAC_ApiKeyPath` | Retry replaced legacy fallback suite with API-key-path suite | PRESERVED |
| `test_limit_forwarded_as_top_k_to_query` | Retry tightened await assertion to include `scopes=None` | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | `ctx.ingest_pipeline is not None` / `ctx.query_service is not None` at `tests/test_server_1317.py:175-176` and `ctx.structured_extractor is not None` at `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py:74-76` are non-discriminating placeholder checks. |
| Negative/error-path coverage | ADEQUATE | Changed suites cover no-key startup, API-key startup, import failure, token-present cleanup, and token-absent cleanup. |
| Manual mutation resistance | WEAK | A bare `copilot_auth` import with no getter call would evade `tests/test_server_1317.py:114`. A non-idempotent `unlink()` on an absent file would evade `tests/test_server_1317.py:237-244` because the mock masks the exception. |
| Test independence | STRONG | `monkeypatch`, `patch.dict`, `patch.object`, and `tmp_path` isolate state cleanly across suites. |
| Descriptive names | STRONG | Test names are behavior-specific and map cleanly to the AC. |

#### Data Safety
- No issues found. The changed scope does not add unvalidated persistence, shared-state mutation, or unbounded resource input.

#### Implementation-Aware Gaps
- AC1 postcondition `absent from sys.modules after lifespan completes` at task line 26 is still unproven by the current test shape.
- AC2 does not pin the actual constructed `KnowledgeQueryService` / `IngestPipeline` objects to the yielded lifespan context; it proves only generic non-`None` presence.
- Divergence from code-reader on AC3: code-reader marked AC3 covered, but the absent-file half remains lax because `mock_unlink.assert_called()` does not distinguish `unlink(missing_ok=True)` from a non-idempotent bare `unlink()` under a mocked method.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` contains no `copilot_auth` references in the live implementation.
- `tests/test_server_1317.py` still says "All tests FAIL until #1318" at the file header, which is stale after the retry and pass-through verification cycle.
- Test-integrity confidence is slightly reduced because this review could not perform a direct commit-diff / dirty-tree audit in the available tool surface; integrity was reconstructed from the task history plus current file state.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | Task contract at `.owlbear/kanban/tasks/1317-p0-01-tests-mcp-startup-copilot-auth-removal-clean-server-start.md:26`; current proof in `tests/test_server_1317.py:85-114` and `:120-143` does not check `sys.modules` absence after lifespan exits. | `test_copilot_auth_not_imported_when_no_api_key`; `test_structured_extractor_is_none_without_api_key` | FAIL |
| AC2 | `tests/test_server_1317.py:149-176` only asserts non-`None`; real construction/wiring points are `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:283-289` and `:313-317`. | `test_ingest_pipeline_and_query_service_wired_with_null_extractor` | FAIL |
| AC3 | Delete-present path is proven at `tests/test_server_1317.py:198-219`; absent-file idempotency is not discriminated at `tests/test_server_1317.py:222-244` against `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:249`. | `test_token_file_deleted_when_present_at_startup`; `test_token_file_cleanup_idempotent_when_absent` | FAIL |
| AC4 | Replacement suite exists at `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py:61-106`; retry note records the legacy fallback suite replacement. | `TestFromAC_ApiKeyPath` | PASS |

### Confidence: 0.74
### Verdict: FAIL
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add a direct AC1 import-absence assertion that verifies `owlbear_knowledge.copilot_auth` is absent from `sys.modules` after `app_lifespan` exits when API-key env vars are unset | `tests/test_server_1317.py` | AC1 at task line 26; current proof stops at `tests/test_server_1317.py:114` |
| 2 | test-writer | Replace generic non-`None` wiring assertions with discriminating proofs that pin the actual `KnowledgeQueryService` and `IngestPipeline` instances in the lifespan context, and tighten adjacent API-key-path assertions that currently only prove non-`None` state | `tests/test_server_1317.py`, `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py` | `tests/test_server_1317.py:175-176`; `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py:74-76`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:283-289`, `:313-317` |
| 3 | test-writer | Strengthen the absent-file cleanup test so it proves idempotency by asserting `Path.unlink(..., missing_ok=True)` exactly or by exercising the real missing-file path without mocking `unlink` | `tests/test_server_1317.py` | AC3 at task line 28; `tests/test_server_1317.py:237-244`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:249` |
[[2026-05-04]]
## Test-Writer Notes (retry 2)
- Retry: added 4 discriminating tests for reviewer gaps; all pass against current impl.
- Builder skip: test-only retry, all new tests green.
- Changed files: `tests/test_server_1317.py`, `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py`
- Commit: 1764902e

### Changes per reviewer follow-up
| Follow-up | Action | Result |
|-----------|--------|--------|
| AC1: sys.modules absence after lifespan exits | Added `test_copilot_auth_module_absent_from_sys_modules_after_lifespan` — does NOT pre-inject copilot_auth, asserts absent from sys.modules post-lifespan | PASS |
| AC2: pin actual IngestPipeline + QueryService instances | Added `test_ingest_pipeline_and_query_service_are_actual_constructed_instances` — captures mock return values, asserts `ctx.query_service is mock_qs_instance` and `ctx.ingest_pipeline is mock_pipeline_instance` | PASS |
| AC2 (888): pin structured_extractor instance | Added `test_structured_extractor_is_exact_llmextractor_instance` — asserts `ctx.structured_extractor is expected_instance` | PASS |
| AC3: real-fs absent-file idempotency | Added `test_token_file_cleanup_no_exception_when_absent_real_fs` — no unlink mock; real `Path.unlink` exercised; bare `unlink()` would raise `FileNotFoundError` here | PASS |

### Verification
- Scoped run: `tests/test_server_1317.py` + `test_copilot_server_wiring_888.py` + `test_search_v2.py` → 30 passed, 0 failed
- ruff: clean
- Step 1b.1 applies: all new tests green → advance directly to review
[[2026-05-04]]
## Builder Notes
- Implementation: no code changes required in this builder cycle.
- Verification scope: tests/test_server_1317.py, serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py, serve/mcp-knowledge/tests/test_search_v2.py, serve/mcp-knowledge/tests/test_server.py.
- Tests: 40 passed, 0 failed, 0 skipped (quality-runner scoped run).
- Coverage: owlbear_mcp_knowledge.server at 45% in scoped run (informational for this pass-through cycle with no source edits).
- ruff: clean on serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py and scoped test files.
- Evidence summary: AC behavior is already implemented and validated by passing TestFromAC coverage in task-scoped suites.
- Fixes applied: none (verification/pass-through builder cycle).
[[2026-05-04]]
## Review Evidence
### Test Results
- quality-runner scoped verification on `tests/test_server_1317.py`, `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py`, `serve/mcp-knowledge/tests/test_search_v2.py`, and `serve/mcp-knowledge/tests/test_server.py`: 40 passed, 0 failed.

### Lint Results
- Ruff clean on `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and the scoped test files.

### Coverage
- `owlbear_mcp_knowledge.server`: 45% module coverage.
- Informational only for this review. The latest builder cycle changed no source files; this task is currently failing on proof quality, not on execution or diff-scoped coverage.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---|---|---|
| AC1 at `.owlbear/kanban/tasks/1317-p0-01-tests-mcp-startup-copilot-auth-removal-clean-server-start.md:26` | `tests/test_server_1317.py:117` and `:134` prove `copilot_auth` is absent from `sys.modules` after lifespan exit; `tests/test_server_1317.py:166` and `:192` prove `structured_extractor is None` in the no-key path. I do **not** count the `OPENAI_API_KEY` fallback branch as a blocker because the parent brief scopes this work to removing `copilot_auth` from lifespan and cleaning the cached token, not to env-var precedence (`.owlbear/briefs/draft-knowledge-activation/brief.md:66-68`). | PASS |
| AC2 at `.owlbear/kanban/tasks/1317-p0-01-tests-mcp-startup-copilot-auth-removal-clean-server-start.md:27` | `tests/test_server_1317.py:137`, `:162`, and `:163` pin the exact `KnowledgeQueryService` and `IngestPipeline` instances stored in the lifespan context; `tests/test_server_1317.py:195`, `:222`, `:224`, and `:225` prove those services remain available when `structured_extractor is None`. This matches the live wiring at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:283`, `:289`, and `:329`. | PASS |
| AC3 at `.owlbear/kanban/tasks/1317-p0-01-tests-mcp-startup-copilot-auth-removal-clean-server-start.md:28` | The implementation deletes the token before yield at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:248-249` and only yields the context later at `:329`. The current tests still assert file state only after the context exits: enter/exit happens at `tests/test_server_1317.py:263` and `:312`, and file absence is asserted afterward at `:268` and `:315`. That means a teardown-only cleanup mutation would still pass. The real-filesystem absent-file test does prove idempotency, but the startup-timing half of AC3 remains lax. | FAIL |
| AC4 at `.owlbear/kanban/tasks/1317-p0-01-tests-mcp-startup-copilot-auth-removal-clean-server-start.md:29` | The legacy fallback suite has been replaced by API-key-path tests in `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py:65`, `:79`, `:97`, and `:116`. | PASS |

#### Security Review
- No security issues found in scope. The reviewed implementation only removes a fixed local token file and conditionally wires the extractor from environment configuration.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions are visible in the live snapshot.
- Small confidence deduction: I could not perform a commit-diff-backed immutability audit in the available tool surface, so integrity is based on current file state plus task history.

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | AC1 and AC2 now use exact absence and identity assertions. |
| Negative and error-path coverage | ADEQUATE | Import-failure and absent-file cleanup paths are both exercised. |
| Manual mutation resistance | WEAK | Moving token cleanup from startup to teardown would still satisfy the current AC3 assertions because file state is checked only after the `async with app_lifespan(...)` block exits. |
| Test independence | STRONG | `monkeypatch`, `tmp_path`, and patch contexts isolate state cleanly. |
| Descriptive names | STRONG | Test names map directly to the reviewed contract. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gap
- No test currently observes token-file state during the lifespan body before `yield ctx`. That leaves the startup-timing portion of AC3 unproven.

### AC Compliance
| AC Line | Mapped Test(s) | Status |
|---|---|---|
| AC1 | `test_copilot_auth_module_absent_from_sys_modules_after_lifespan`, `test_structured_extractor_is_none_without_api_key` | PASS |
| AC2 | `test_ingest_pipeline_and_query_service_are_actual_constructed_instances`, `test_ingest_pipeline_and_query_service_wired_with_null_extractor` | PASS |
| AC3 | `test_token_file_deleted_when_present_at_startup`, `test_token_file_cleanup_no_exception_when_absent_real_fs` | FAIL |
| AC4 | `TestFromAC_ApiKeyPath` replacement suite | PASS |

### Deductions
- 0.10: AC3 startup semantics remain only partially proven.
- 0.04: no direct commit-diff immutability check in the available tool surface.

### Confidence
- 0.86

### Verdict
- FAIL

### Action
- Reject to backlog. This task already contains one prior `## Review Evidence` section at `.owlbear/kanban/tasks/1317-p0-01-tests-mcp-startup-copilot-auth-removal-clean-server-start.md:162`; under the reviewer loop-breaker rule, a second review failure with remaining AC/proof mismatch routes to backlog rather than another narrow retry.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Refine AC3 and the retry plan so the proof explicitly observes token cleanup during startup before `app_lifespan` yields, then hand off a rewritten td:2 test for that timing contract. | `.owlbear/kanban/tasks/1317-p0-01-tests-mcp-startup-copilot-auth-removal-clean-server-start.md`, `tests/test_server_1317.py` | AC3 at task line 28; startup delete in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:248-249`; current after-exit assertions in `tests/test_server_1317.py:263`, `:268`, `:312`, and `:315` |
[[2026-05-04]]

## Architecture Review (refinement cycle)

### Context
Returned from second reviewer FAIL. AC1/AC2/AC4 all PASS. AC3 fails because existing tests assert file state after `async with app_lifespan(...)` exits — a regression moving cleanup to teardown would still pass.

### AC3 Refinement
**Old:** Tests verify lifespan startup deletes stale `~/.owlbear/copilot_token.json` if present, and cleanup is idempotent when file absent (td:2)

**New:** Tests verify token file is absent INSIDE the lifespan body (`async with app_lifespan(...) as ctx:` — assertion before block exit), proving deletion is a startup action not teardown; idempotent case exercises real `Path.unlink` on absent file without raising (td:2)

### Guidance for test-writer
The existing `test_token_file_deleted_when_present_at_startup` must move its assertion from after the `async with` block to inside it:
```python
async with app_lifespan(MagicMock()) as ctx:
    assert not token_file.exists()  # Proves startup, not teardown
```
The idempotent test (`test_token_file_cleanup_no_exception_when_absent_real_fs`) is already correct — it exercises real filesystem and would raise `FileNotFoundError` without `missing_ok=True`.

### Evaluation
| Criterion | Assessment |
|-----------|-----------|
| Single responsibility | PASS — test-only task |
| Interface clarity | PASS — after AC3 refinement |
| TDD compliance | PASS — RED-only task, #1318 is GREEN counterpart |
| KISS/YAGNI | PASS — minimal scope |
| Pattern consistency | PASS — follows existing test_copilot_server_wiring pattern |

### Challenge Results
- Challenger: SKIPPED — narrow AC-wording refinement on already-approved task with two prior challenge passes
- Architect response: n/a

### Test Depth
- Max depth: 2 (AC3)
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC3 to require in-body timing assertion; re-approved to todo

[[2026-05-04]]
Refinement cycle: AC3 rewritten to require in-body timing assertion (observe file absence inside `async with app_lifespan(...)` block, not after exit). AC1/AC2/AC4 unchanged — all PASS from prior review. Challenger skipped (narrow wording fix on previously approved+challenged task).
[[2026-05-04]]
## Test-Writer Notes (retry 3)
- Retry: moved AC3 timing assertion inside `async with app_lifespan(...) as ctx:` body per architect AC3 refinement.
- Changed files: `tests/test_server_1317.py`
- Commit: 801b3f3e

### Change
| Item | Action | Result |
|------|--------|--------|
| `test_token_file_deleted_when_present_at_startup` | Moved `assert not token_file.exists()` inside the `async with` block (from after exit to during lifespan body) | PASS — proves cleanup is startup action, not teardown; a regression moving `unlink()` to `finally:` block would now fail |

### Verification
- Scoped run: `tests/test_server_1317.py` + `test_copilot_server_wiring_888.py` + `test_search_v2.py` → 30 passed, 0 failed
- ruff: clean
- Step 1b.1 applies: all tests green against current impl → advance directly to review
[[2026-05-04]]
## Builder Notes
- Implementation: no source code changes required in this builder cycle.
- Scope verified: `tests/test_server_1317.py`, `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py`, `serve/mcp-knowledge/tests/test_search_v2.py`, `serve/mcp-knowledge/tests/test_server.py`.
- Tests: 40 passed, 0 failed, 0 errors (scoped quality-runner run).
- Coverage: `owlbear_mcp_knowledge.server` at 45% (informational for this pass-through cycle with no source edits).
- Lint: ruff clean on `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and scoped test files.
- Evidence summary: AC-aligned startup/lifespan behavior is already implemented and validated by the current TestFromAC coverage in task-scoped suites.
- Repo state note: no tracked source diffs for task 1317 in this cycle; task/research artifacts appear as untracked board/research files.
- Fixes applied: none (verification/pass-through builder cycle).
[[2026-05-04]]
## Review Evidence
### Test Results
- quality-runner scoped run on `tests/test_server_1317.py`, `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py`, `serve/mcp-knowledge/tests/test_search_v2.py`, and `serve/mcp-knowledge/tests/test_server.py`: 40 passed, 0 failed, 0 skipped.

### Lint Results
- Ruff clean on `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and the scoped test files.

### Coverage
- `owlbear_mcp_knowledge.server`: 45% module coverage.
- Informational only for this cycle. Latest builder note at task line 391 reports no source edits in the final pass-through cycle, so module-level coverage is not a blocking gate here.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---|---|---|
| AC1 at task line 26 | `tests/test_server_1317.py:117` with assertion at `:134` proves `owlbear_knowledge.copilot_auth` is absent from `sys.modules` after lifespan exit; `tests/test_server_1317.py:166` with assertion at `:192` proves `structured_extractor is None` when the no-key path is exercised. | PASS |
| AC2 at task line 27 | `tests/test_server_1317.py:137` with assertions at `:162-163` pins the exact `KnowledgeQueryService` and `IngestPipeline` instances in context; `tests/test_server_1317.py:195` with assertions at `:222-224` proves those services remain available when `structured_extractor is None`. This matches the live context wiring at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:315`, `:317`, and `:323`. | PASS |
| AC3 at task line 28 | Startup cleanup happens at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:249` before `yield ctx` at `:329`. `tests/test_server_1317.py:247` enters the lifespan and asserts token absence inside the body at `:266` while the `async with` block is still active at `:263`, so a teardown-only cleanup regression would fail. `tests/test_server_1317.py:294` with final assertion at `:313` exercises the real absent-file path without mocking `Path.unlink`, so missing `missing_ok=True` would raise. | PASS |
| AC4 at task line 29 | `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py:61` contains the replacement `TestFromAC_ApiKeyPath` suite, with executable cases at `:65`, `:97`, and `:116`. Live file inspection found no `TestFromAC_CopilotServerFallback` class in the file. | PASS |

#### Security Review
- No issues found. The reviewed startup path only unlinks a fixed home-relative token file and conditionally constructs `LLMExtractor` from environment configuration. No shell execution, SQL, unsafe deserialization, or user-controlled path handling is present in scope.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions are visible in the current snapshot.
- Task-related commits cited in the task history are present in git reflogs: `2741465d`, `1764902e`, and `801b3f3e`.

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | The AC-owning proofs use exact module-absence and identity assertions at `tests/test_server_1317.py:134`, `:162-163`, `:192`, and `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py:113`. |
| Negative and error-path coverage | ADEQUATE | Import-failure degradation is covered at `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py:116`; absent-file idempotency is covered on the real filesystem at `tests/test_server_1317.py:294`. |
| Manual mutation resistance | STRONG | Reintroducing `copilot_auth`, forcing a non-null extractor on the no-key path, misassigning the context services, moving cleanup to teardown, or dropping `missing_ok=True` would all break the current AC-mapped assertions. |
| Test independence | STRONG | `monkeypatch`, `patch.dict`, and `tmp_path` isolate state cleanly across the reviewed suites. |
| Descriptive names | STRONG | The reviewed tests map directly to the refined task contract. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- No blocking gaps remain on the refined AC surface.
- Non-blocking note: `tests/test_server_1317.py` still contains older laxer helper assertions, but the stronger adjacent tests added in retry 2 and retry 3 fully prove the same AC surface.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 4 |
| Approach variation | Yes |
| Assessment | FRICTION only, not LOOP |

### Pass 2 - INFORMATIONAL
- `tests/test_server_1317.py` still has a stale RED-phase header/docstring narrative from the original failing phase. That is maintainability drift, not a proof defect.
- Direct git diff/status commands were not available in this tool surface, so dirty-tree and immutability confidence is based on current file state plus reflog-backed commit presence rather than a full diff audit.

### AC Compliance
| AC Line | Mapped Test(s) | Status |
|---|---|---|
| AC1 | `test_copilot_auth_module_absent_from_sys_modules_after_lifespan`, `test_structured_extractor_is_none_without_api_key` | PASS |
| AC2 | `test_ingest_pipeline_and_query_service_are_actual_constructed_instances`, `test_ingest_pipeline_and_query_service_wired_with_null_extractor` | PASS |
| AC3 | `test_token_file_deleted_when_present_at_startup`, `test_token_file_cleanup_no_exception_when_absent_real_fs` | PASS |
| AC4 | `TestFromAC_ApiKeyPath` replacement suite | PASS |

### Deductions
- 0.04: no direct diff/status tool surface for a full dirty-tree and immutability audit.
- 0.02: stale RED-phase header/docstrings remain in `tests/test_server_1317.py`.

### Confidence
- 0.94

### Verdict
- PASS

### Action
- Advance to docs.

### Post-task Reflection
- AC3 only became reviewable after the architect rewrote it to require an in-body assertion; the timing proof now exists at `tests/test_server_1317.py:266`.
- Adjacent stronger tests can legitimately close an earlier proof gap even when an older, laxer helper assertion still exists in the same file.
- When direct git diff/status commands are unavailable, reflog confirmation plus live-file verification is enough for a small-deduction PASS, but not for zero-deduction confidence.
[[2026-05-04]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Test-only changes; no behavior, API, CLI, or package structure changes affecting prose docs |
| 2 | Module docstrings | No | N/A | All changed files are test files; no source modules created or modified (builder: "Files changed: none" across all cycles) |
| 3 | External attribution | No | N/A | No external patterns, repos, or articles used |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1317-mcp-startup-test-scope.md` exists; linked from task body; follow-ups noted as "No additional follow-up tasks needed — #1318 already exists" |
| 5 | Diagram maintenance (describes match) | No | N/A | `share/diagrams/mcp-topology.excalidraw` describes `serve/mcp-*/src/**` — changed files are under `tests/` not `src/`; no match |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| tests/test_server_1317.py | OUT (test file, no public API) | N/A |
| serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py | OUT (test file) | N/A |
| serve/mcp-knowledge/tests/test_search_v2.py | OUT (test file) | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1317-*` files found)
[[2026-05-04]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: copilot_auth not imported, structured_extractor None | tests/test_server_1317.py:134 (sys.modules absence after lifespan), :192 (structured_extractor is None) | PASS |
| AC2: IngestPipeline + QueryService wired with null extractor | tests/test_server_1317.py:162-163 (pinned exact instances via mock return values) | PASS |
| AC3: Token file absent inside lifespan body; idempotent cleanup | tests/test_server_1317.py:266 (assertion inside async with block, not after exit); :294-313 (real-fs absent-file path, no mock on unlink) | PASS |
| AC4: Legacy tests replaced | serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py:61 (TestFromAC_ApiKeyPath replacement suite) | PASS |

### Test Results
- pytest (task-scoped): 40 passed, 0 failed
- pytest (full suite): 4056 passed, 244 failed (all pre-existing: kanban storage/migration, mcp-kanban guidance, outputschema_541, phase_a_config -- none in task scope)
- ruff: clean
- vitest (full): 950 passed, 13 failed (Shell_966/Shell_1227 SSE provider issue, pre-existing, unrelated)

### Commit Integrity
- 801b3f3e: test-writer retry 3 (AC3 timing)
- 1764902e: test-writer retry 2 (strengthen assertions)
- 2741465d: test-writer retry 1 (replace legacy tests)
- 272f58b8: original test-writer (failing tests)
All commits verified via git log.

### Architect Quality: 4/5
AC1/AC2/AC4 were precise and complete. AC3 needed one refinement cycle to specify in-body timing proof methodology (minor gap, caught within pipeline).

### Deduction Breakdown
- AC lines without evidence: 0 (all 4 PASS with file:line refs)
- Lint violations: 0
- AC quality score 4 (above threshold 3): 0
- Reviewer evidence: present, detailed, PASS at 0.94: 0
- Full-suite failures in task scope: 0
- Stale RED-phase docstrings in test file (cosmetic): -.02

### Confidence: 0.98
### Action: archive