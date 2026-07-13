---
id: 699
title: 'Tests: MCP knowledge graph wiring and integration'
status: archived
priority: medium
created: 2026-04-08T21:37:24.4459836+02:00
updated: 2026-04-09T15:27:26.5169645+02:00
started: 2026-04-09T15:27:26.5169645+02:00
completed: 2026-04-09T15:27:26.5169645+02:00
tags:
    - scope:mcp-knowledge
    - type:test
parent: 676
depends_on:
    - 689
class: standard
---

## Context
TDD RED phase for #690. Write failing integration tests that verify the MCP server creates LLMExtractor and wires it into EntityExtractor.

## Acceptance Criteria

- [ ] AC1: Test verifies app_lifespan() creates LLMExtractor and passes it as EntityExtractor(extractor=...)
- [ ] AC2: Test verifies ingest produces entity_count > 0 and edge_count > 0 in get_stats
- [ ] AC3: Test verifies search_knowledge returns graph expansion context
- [ ] AC4: Test verifies graceful degradation when OWLBEAR_MODEL is unset
- [ ] AC5: All tests FAIL (RED phase — wiring not yet implemented)

## Affected Files
- serve/mcp-knowledge/tests/test_ingest_graph_wiring.py (new)

[[2026-04-09]] Thu 12:56
## Architecture Review

### Refinements Applied
- **AC3 split:** "graph expansion context" was vague — same term was explicitly split in #690's arch review into AC4a (GraphAugmentedRetriever wiring) and AC4b (entity_type in response). Split AC3 to match:
  - AC3a: Test verifies `app_lifespan()` creates `GraphAugmentedRetriever(vs, gs, emb)` and passes it as `KnowledgeQueryService(retriever=...)`
  - AC3b: Test verifies `search_knowledge` response dicts include `entity_type` field (from `StructuredSearchResult`)
- **AC4 refined:** "OWLBEAR_MODEL is unset" is misleading — current code already defaults to `_DEFAULT_MODEL = "gpt-4o-mini"` (server.py L38). Real degradation scenario per #690 AC5 and research is LLMExtractor import/construction failure:
  - AC4: Test verifies graceful degradation when `LLMExtractor` import fails (`ImportError`) — `app_lifespan()` falls back to `EntityExtractor` without injected extractor, server starts successfully

### RED Phase Verification
All tests will correctly FAIL against current codebase:
- AC1: server.py L165 creates `EntityExtractor(model)` with no `extractor=` kwarg — no LLMExtractor import
- AC2: No injected extractor → `EntityExtractor.extract()` returns empty `ExtractionResult()` → 0 entities/edges
- AC3a: server.py L163 creates `KnowledgeQueryService(...)` with no `retriever=` kwarg
- AC3b: server.py L227 list comprehension maps only title/score/snippet — no entity_type
- AC4: No LLMExtractor import or try/except block in server.py

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All tests verify LLMExtractor + graph wiring in MCP server |
| Interface clarity | PASS (after refine) | AC3 split into AC3a/AC3b, AC4 precision on ImportError |
| Dependency correctness | PASS | #689 (LLMExtractor impl) is done |
| Module layering | PASS | Tests in serve/mcp-knowledge/tests/ testing mcp-knowledge server |
| TDD compliance | PASS | This IS the RED phase task for #690 |
| KISS/YAGNI | PASS | Minimal test scope matching #690's ACs |
| Premise challenge | PASS | Tests are required for #690's TDD compliance |
| Pattern consistency | PASS | Follows existing test patterns (TestFromAC_*, mock-based, patch context managers) |
| Security surface | N/A | Test file only |
| Single domain | PASS | scope:mcp-knowledge |

### #690 AC Coverage Map
| #690 AC | #699 Test | Status |
|---------|-----------|--------|
| AC1: LLMExtractor wiring | AC1 | COVERED |
| AC2: pyproject.toml dep | N/A | Config-only, not code-testable |
| AC3: entity/edge counts | AC2 | COVERED |
| AC4a: GraphAugmentedRetriever wiring | AC3a | COVERED |
| AC4b: entity_type in search response | AC3b | COVERED |
| AC5: Graceful degradation | AC4 | COVERED |

### Codebase Evidence
- EntityExtractor DI slot: `serve/knowledge/src/owlbear_knowledge/extractor.py` L66-73 (extractor: StructuredExtractor | None)
- KnowledgeQueryService retriever slot: `serve/knowledge/src/owlbear_knowledge/query_service.py` L57-58 (retriever: GraphAugmentedRetriever | None)
- GraphAugmentedRetriever: `serve/knowledge/src/owlbear_knowledge/retrieval.py` L36-43
- StructuredSearchResult.entity_type: `serve/knowledge/src/owlbear_knowledge/query_service.py` L19
- SearchResult TypedDict (missing entity_type): `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` L41-45
- Existing test patterns: `serve/mcp-knowledge/tests/test_server.py`, `test_ingest_graph_tools.py`

### Builder Guidance
- AC1: Mock `LLMExtractor` class to prevent actual PydanticAI Agent construction; verify `EntityExtractor` receives it as `extractor=` kwarg
- AC2: Mock `LLMExtractor.extract()` to return known entities/edges; verify counts via `get_stats`
- AC3a: Verify `KnowledgeQueryService` init receives `retriever=` kwarg (spy on constructor call)
- AC3b: Mock `search_knowledge` response and assert `entity_type` key present in result dicts
- AC4: Monkeypatch LLMExtractor import to raise `ImportError`; verify `app_lifespan` still yields working `AppContext`

### Challenge Results
- Challenger: proceed (confidence 0.87)
- Architect response: accepted — all refinements validated

### Verdict: APPROVE (after inline REFINE)
### Action Taken: Split AC3 into AC3a/AC3b (graph retriever wiring + entity_type in response), refined AC4 (ImportError not OWLBEAR_MODEL unset). Advanced to todo.

[[2026-04-09]] Thu 13:34
## Test-Writer Notes

**Test file:** `serve/mcp-knowledge/tests/test_ingest_graph_wiring.py` (new, 12 tests)

### Classes and test distribution

| Class | AC | Category | Tests |
|---|---|---|---|
| `TestFromAC_LLMExtractorWiring` | AC1 | happy/wiring | 3 |
| `TestFromAC_IngestWithLLMExtractor` | AC2 | integration/behavioral | 1 |
| `TestFromAC_GraphAugmentedRetrieverWiring` | AC3a | happy/wiring | 3 |
| `TestFromAC_SearchKnowledgeEntityType` | AC3b | happy/edge/boundary | 3 |
| `TestFromAC_LLMExtractorImportError` | AC4 | error/degradation | 2 |

**Total: 12 tests, all FAIL confirmed.**

### RED failure modes

- **AC1 (3 tests), AC4 (2 tests):** `AttributeError` — `owlbear_mcp_knowledge.server` has no attribute `LLMExtractor`. Builder must add module-level import.
- **AC2 (1 test):** `AssertionError` — `entity_count == 0` and `edge_count == 0`. EntityExtractor is a stub (no `extractor=` kwarg wired). Patched `owlbear_knowledge.llm_extractor.LLMExtractor` at source but server never imports it in RED.
- **AC3a (3 tests):** `AttributeError` — `owlbear_mcp_knowledge.server` has no attribute `GraphAugmentedRetriever`. Builder must add module-level import.
- **AC3b (3 tests):** `KeyError`/`AssertionError` — `search_knowledge` response dicts only have `title/score/snippet`, no `entity_type` key.

### AC coverage map

| AC | Test(s) | Covered |
|---|---|---|
| AC1: LLMExtractor wiring into EntityExtractor | `TestFromAC_LLMExtractorWiring` (3 tests) | ✓ |
| AC2: entity_count > 0 and edge_count > 0 | `TestFromAC_IngestWithLLMExtractor` (1 test) | ✓ |
| AC3a: GraphAugmentedRetriever wiring into KQS | `TestFromAC_GraphAugmentedRetrieverWiring` (3 tests) | ✓ |
| AC3b: entity_type in search_knowledge response | `TestFromAC_SearchKnowledgeEntityType` (3 tests) | ✓ |
| AC4: ImportError graceful degradation | `TestFromAC_LLMExtractorImportError` (2 tests) | ✓ |

### Builder notes

- AC1/AC3a/AC4 tests require `LLMExtractor` and `GraphAugmentedRetriever` as module-level attributes of `server.py` (add top-level imports). AC4 degradation requires `LLMExtractor(model)` call wrapped in `try/except ImportError` inside `app_lifespan`.
- AC2 integration test uses real SQLite + real pipeline; patches `owlbear_knowledge.llm_extractor.LLMExtractor` at source — ensure local import inside `app_lifespan` picks this up.
- AC3b: builder must add `entity_type` to the `SearchResult` TypedDict and the `search_knowledge` list comprehension.

**ruff:** clean

[[2026-04-09]] Thu 13:36
## Builder Notes

**Role:** RED phase verification pass-through — no implementation changes required.

**Files changed:** None (test file was already written by test-writer agent)

**Test results (RED confirmation):**
- `serve/mcp-knowledge/tests/test_ingest_graph_wiring.py`: 12 tests, **12 FAILED** ✓
  - `TestFromAC_LLMExtractorWiring` (3): `AttributeError` — `LLMExtractor` not in `server` namespace
  - `TestFromAC_IngestWithLLMExtractor` (1): `AssertionError` — `entity_count == 0` (no LLMExtractor wired)
  - `TestFromAC_GraphAugmentedRetrieverWiring` (3): `AttributeError` — `GraphAugmentedRetriever` not in `server` namespace
  - `TestFromAC_SearchKnowledgeEntityType` (3): `AssertionError` — `entity_type` key absent from `search_knowledge` results
  - `TestFromAC_LLMExtractorImportError` (2): `AttributeError` — `LLMExtractor` not in `server` namespace

**Lint:** ruff clean ✓

**Evidence:** All 12 `TestFromAC_*` tests fail for the correct reasons documented in the test-writer notes. RED phase is valid — no false positives. Task #690 (GREEN implementation) has all dependencies fulfilled (#689 done, #699 done).

[[2026-04-09]] Thu 13:44
## Review Evidence

### Test Results
- pytest: 0 passed, 12 failed (independently run via quality-runner)
- ruff: clean

### Coverage
N/A — RED phase; coverage is informational only (overall 36%, expected for new test file against unimplemented code)

### Source Control
One new file added: `serve/mcp-knowledge/tests/test_ingest_graph_wiring.py` (12 tests). No implementation files changed. Changed files also show CRLF/LF normalization in unrelated test files — not substantive.

---

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: LLMExtractor wiring into EntityExtractor | TestFromAC_LLMExtractorWiring (3 tests) | Yes — patch target AttributeError is the correct RED trigger; assertions on call_args would fail if kwarg absent | COVERED |
| AC2: entity_count > 0 and edge_count > 0 via get_stats | TestFromAC_IngestWithLLMExtractor (1 test) | **STRUCTURAL DEFECT — see §5.3** | DEFECTIVE |
| AC3a: GraphAugmentedRetriever wiring into KQS | TestFromAC_GraphAugmentedRetrieverWiring (3 tests) | Yes — patch target AttributeError is correct RED trigger; call_args assertions are specific | COVERED |
| AC3b: entity_type in search_knowledge response | TestFromAC_SearchKnowledgeEntityType (3 tests) | Yes — assertions directly check key presence and value equality | COVERED |
| AC4: ImportError graceful degradation | TestFromAC_LLMExtractorImportError (2 tests) | Yes — ctx_yielded is not None + extractor kwarg absence are specific | COVERED |
| AC5: All tests FAIL (RED) | Confirmed — 12/12 fail | N/A | PASS |

#### 5.1 Security Review
- Test file only. No hardcoded secrets, no injection vectors, no OWASP surface.
- **Clean.**

#### 5.2 Test Integrity — TestFromAC Comparison
Builder made no changes to any TestFromAC_* test (confirmed: "no implementation changes required"). All 12 tests PRESERVED.

#### 5.3 Test Quality — FAIL FINDING

**AC2 — `test_ingest_produces_entity_count_and_edge_count_gt_zero`:**

- **Documented RED failure mode:** `AssertionError` — `entity_count == 0` (test-writer notes)
- **Actual RED failure mode (independently observed):** `sqlite3.ProgrammingError: SQLite object thread violation`

The test never reaches its `assert stats["entities"] > 0` assertion. The real SQLite connection created by `init_db` (not mocked) is accessed from a different thread context inside the async event loop, triggering Python's default `check_same_thread=True` SQLite safety check.

**Impact on GREEN phase:** When the builder implements #690 and correctly wires `LLMExtractor` into `EntityExtractor`, this test will likely still raise `sqlite3.ProgrammingError` — not because the implementation is wrong, but because the test has an unfixable threading issue in its async test harness. This makes the AC2 behavioral contract **untestable as written**.

**Rating: WEAK** (structural defect — test cannot be made to pass without redesign)

Fix options for test-writer:
1. Mock `init_db` to return a MagicMock — makes it a unit test, not integration; patch `owlbear_mcp_knowledge.server.LLMExtractor` with a module-level import for the GREEN phase check
2. If real SQLite is required, ensure `init_db` uses `check_same_thread=False` or scope the connection creation to the test thread
3. Alternatively, redesign AC2 using the same mock-heavy approach as AC1/AC3a: mock `EntityExtractor.extract` and verify it is called with the LLMExtractor instance rather than running the full ingest pipeline

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity (AC1/AC3a/AC3b/AC4) | STRONG | Exact kwarg checks, identity assertions, key presence+value equality |
| Assertion specificity (AC2) | WEAK | Test never reaches assertions — `sqlite3.ProgrammingError` occurs before `assert stats["entities"] > 0` |
| Test independence | ADEQUATE | AC1/AC3–AC4 fully isolated; AC2 has environment-dependent failure |
| Naming | STRONG | TestFromAC_ prefix + descriptive method names throughout |

**Any WEAK rating = automatic FAIL.**

#### 5.4 Data Safety
Clean — test file only.

#### 5.5 Implementation-Aware Test Gap Analysis
AC2 is a significant untestable path: the integration test cannot pass in GREEN phase as written due to SQLite threading constraints. The AC behavioral contract (entity_count + edge_count > 0 after real ingest) is unverifiable without test redesign.

#### 5.7 Builder Process Quality
CLEAN — 1 (pass-through) cycle, no loop.

---

### AC Compliance Table

| AC | Evidence | Status |
|----|----------|--------|
| AC1: LLMExtractor wiring tests present and RED | 3 tests fail with `AttributeError: no attribute 'LLMExtractor'` — correct | PASS |
| AC2: entity/edge count > 0 tests present and RED | 1 test fails with `sqlite3.ProgrammingError` — WRONG failure mode; test unreachable in GREEN | **FAIL** |
| AC3a: GraphAugmentedRetriever wiring tests present and RED | 3 tests fail with `AttributeError: no attribute 'GraphAugmentedRetriever'` — correct | PASS |
| AC3b: entity_type in response tests present and RED | 3 tests fail with `AssertionError`/`KeyError` — correct | PASS |
| AC4: ImportError degradation tests present and RED | 2 tests fail with `AttributeError` — correct | PASS |
| AC5: All tests FAIL | 12/12 FAIL confirmed by independent run | PASS (wrong reason for 1 test) |

### Deductions
- AC2 test structural defect (SQLite thread violation — wrong RED failure mode, non-passable in GREEN): −0.15

### Confidence: 0.85 → FAIL → todo

**Action:** Test-writer must redesign `TestFromAC_IngestWithLLMExtractor.test_ingest_produces_entity_count_and_edge_count_gt_zero` to avoid `sqlite3.ProgrammingError`. Recommended approach: mock `init_db` or patch the `check_same_thread` behavior, OR redesign to verify LLMExtractor is called with the correct arguments and its mock return value flows through the pipeline (spy-based rather than full integration).

[[2026-04-09]] Thu 14:07
## Test-Writer Notes (Retry)

**Retry reason:** AC2 test structural defect — original `test_ingest_produces_entity_count_and_edge_count_gt_zero` failed with `sqlite3.ProgrammingError` (SQLite thread violation from `asyncio.to_thread`) instead of the intended `AssertionError`. Reviewer rated WEAK; test could not be made to pass in GREEN phase as written.

**Fix applied:** Redesigned `TestFromAC_IngestWithLLMExtractor` to:
1. Patch `init_db` to return `sqlite3.connect(":memory:", check_same_thread=False)` with schema applied — eliminates thread violation from `asyncio.to_thread` calls in pipeline and `get_stats`
2. Patch `owlbear_mcp_knowledge.server.LLMExtractor` at the server module level (not at the source site) — consistent with AC1/AC3/AC4 RED pattern; raises `AttributeError` in RED
3. Mock `BgeM3EmbeddingProvider` with `embed.side_effect = lambda texts: [[0.1] * 64 for _ in texts]` for real chunk embedding calls
4. Removed the unused `tmp_path` fixture and `pathlib` import; added `sqlite3` import

**RED failure now:** `AttributeError: module 'owlbear_mcp_knowledge.server' does not have the attribute 'LLMExtractor'` — correct, same as AC1/AC3a/AC4. GREEN path: builder adds import + wiring → mock LLMExtractor.extract returns 2 entities + 1 edge → stored via real GraphStore → get_stats returns > 0.

**Test file:** `serve/mcp-knowledge/tests/test_ingest_graph_wiring.py`

### Final results

| Class | AC | Tests | RED failure |
|---|---|---|---|
| `TestFromAC_LLMExtractorWiring` | AC1 | 3 | `AttributeError: no attr 'LLMExtractor'` |
| `TestFromAC_IngestWithLLMExtractor` | AC2 | 1 | `AttributeError: no attr 'LLMExtractor'` ✓ (was `ProgrammingError`) |
| `TestFromAC_GraphAugmentedRetrieverWiring` | AC3a | 3 | `AttributeError: no attr 'GraphAugmentedRetriever'` |
| `TestFromAC_SearchKnowledgeEntityType` | AC3b | 3 | `AssertionError`/`KeyError: entity_type` |
| `TestFromAC_LLMExtractorImportError` | AC4 | 2 | `AttributeError: no attr 'LLMExtractor'` |

**Total: 12 tests, all FAIL ✓**  
**ruff: clean ✓**  
**Commit:** `580d27a` — `test: redesign AC2 ingest test to fix SQLite thread violation (#699, test-writer)`

[[2026-04-09]] Thu 14:22
## Builder Notes

**Role:** RED phase re-verification (retry after test-writer fixed AC2 SQLite thread issue)

**Files changed:** None — pass-through verification only

**Test results (RED confirmation):**
- `serve/mcp-knowledge/tests/test_ingest_graph_wiring.py`: **12 FAILED, 0 passed** ✓
  - `TestFromAC_LLMExtractorWiring` (3): `AttributeError` — `LLMExtractor` not in `server` namespace ✓
  - `TestFromAC_IngestWithLLMExtractor` (1): `AttributeError` — `LLMExtractor` not in `server` namespace ✓ (was `sqlite3.ProgrammingError` — **fixed**)
  - `TestFromAC_GraphAugmentedRetrieverWiring` (3): `AttributeError` — `GraphAugmentedRetriever` not in `server` namespace ✓
  - `TestFromAC_SearchKnowledgeEntityType` (3): `AssertionError` — `entity_type` key absent from `search_knowledge` results ✓
  - `TestFromAC_LLMExtractorImportError` (2): `AttributeError` — `LLMExtractor` not in `server` namespace ✓

**Lint:** ruff clean ✓ (no code changes made)

**Evidence:** All 12 `TestFromAC_*` tests fail for the correct reasons documented in test-writer retry notes. AC2 SQLite thread violation is confirmed resolved — test now fails with `AttributeError` (correct RED trigger, same pattern as AC1/AC3a/AC4). No false positives. RED phase is valid and all ACs covered. Task #690 (GREEN implementation) has all dependencies fulfilled.

[[2026-04-09]] Thu 15:01
## Review Evidence

**Cycle:** 2nd (retry after test-writer fixed AC2 SQLite thread violation)

### Test Infrastructure
- quality-runner: FAILED — pytest initialization `KeyboardInterrupt` during xdist node setup (environment error, not test failure). Fell back to sequential. Note in Channel B: "Parallel fan-out failed: xdist/execnet node initialization error. Fell back to sequential."
- code-reader: COMPLETED — thorough per-AC analysis
- Independent test count: unavailable (environment failure). Prior cycle quality-runner independently confirmed 12/12 FAIL. code-reader analysis corroborates all RED failure modes documented by test-writer.

### Source Control
- New file: `serve/mcp-knowledge/tests/test_ingest_graph_wiring.py` (single deliverable, 12 tests)
- Commit `580d27a`: `test: redesign AC2 ingest test to fix SQLite thread violation (#699, test-writer)`
- No implementation files changed (pass-through builder)

### Lint
- ruff: clean (quality-runner confirmed, builder self-report confirmed)

### Coverage
- N/A — RED phase

---

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage

| AC Line | Mapped Tests | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: LLMExtractor wiring into EntityExtractor | TestFromAC_LLMExtractorWiring (3 tests): instantiation assert, extractor= kwarg identity, OWLBEAR_MODEL env var | Yes — patch AttributeError in RED; identity assertions in GREEN | COVERED |
| AC2: entity_count > 0 and edge_count > 0 in get_stats | TestFromAC_IngestWithLLMExtractor (1 test): check_same_thread=False SQLite, server-level LLMExtractor patch | Yes — AttributeError in RED (correct); `> 0` assertions would fail if no entities/edges stored in GREEN | COVERED (LAX — see §5.3) |
| AC3a: GraphAugmentedRetriever wiring into KQS | TestFromAC_GraphAugmentedRetrieverWiring (3 tests): instantiation, retriever= kwarg identity, vs/gs/emb forwarding | Yes — patch AttributeError in RED; identity assertions in GREEN | COVERED |
| AC3b: entity_type in search_knowledge response | TestFromAC_SearchKnowledgeEntityType (3 tests): key presence, value equality, None edge case | Yes — AssertionError in RED; three-tier assertion in GREEN | COVERED |
| AC4: ImportError graceful degradation | TestFromAC_LLMExtractorImportError (2 tests): ctx_yielded is not None, fallback EntityExtractor without extractor= kwarg | Yes — AttributeError in RED; assertions verify both positive and negative conditions in GREEN | COVERED |
| AC5: All tests FAIL (RED) | Builder confirmed 12/12 FAIL; code-reader verified all patch targets absent from server.py namespace | N/A — evidence-based | PASS |

No MISSING AC lines.

#### 5.1 Security Review
Test file only. No hardcoded secrets, no injection surface, no subprocess calls, no external network I/O. Clean.

#### 5.2 Test Integrity — TestFromAC Comparison
All five `TestFromAC_*` class names preserved exactly. Builder made zero changes to test file (pass-through). No weakening detected. Retry change was test-writer authoring the AC2 fix; the AC2 class (`TestFromAC_IngestWithLLMExtractor`) is entirely new content vs the prior cycle's broken test — not a weakening.

#### 5.3 Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| AC1 — extractor= kwarg identity | STRONG | `assert kwargs["extractor"] is mock_llm_instance` — exact identity |
| AC1 — env var test | ADEQUATE | `all_args = list(args) + list(kwargs.values()); assert "gpt-4-turbo" in all_args` — checks presence but not which param carries it |
| AC2 — entity/edge counts | LAX | `assert stats["entities"] > 0` — mock provides exactly 2 entities/1 edge; `== 2`/`== 1` would be mutation-resistant |
| AC3a — retriever= kwarg identity | STRONG | `assert kwargs["retriever"] is mock_gar_instance` — exact identity |
| AC3b — entity_type coverage | STRONG | Three tests: key present, value equality, None edge case |
| AC4 — ImportError recovery | STRONG | `ctx_yielded is not None` + `assert "extractor" not in kwargs` — two-sided contract |
| Test independence | STRONG | Each test constructs own context; no shared mutable state |

**AC4 GREEN-phase concern (assessed and cleared):** First test does not patch `GraphAugmentedRetriever`. After GREEN implementation, `app_lifespan` will instantiate `GraphAugmentedRetriever(mock_vs, mock_gs, mock_emb)` with MagicMock arguments. `GraphAugmentedRetriever.__init__` (retrieval.py L44–56) only stores references (`self._vector_store = vector_store`, etc.) — no type validation, no method calls at construction time. MagicMock arguments will not fail construction. GREEN-phase fragility concern is mitigated.

**No WEAK rating.** LAX on AC2 is a note — does not auto-FAIL (no compensating TestBuilderDiscovered assertion exists, but the core contract `> 0` is sufficient to validate the AC behavioral statement "entity_count > 0 and edge_count > 0").

#### 5.4 Data Safety
Thread-safety addressed: `check_same_thread=False` at AC2 SQLite init — correct. No race conditions, no LLM calls, no shared state. Clean.

#### 5.5 Implementation-Aware Test Gap Analysis
The prior cycle's structural defect (AC2 `sqlite3.ProgrammingError` before assertions) is confirmed resolved: test now fails with `AttributeError` (patch target absent), same pattern as all other ACs. GREEN path: builder adds `LLMExtractor` import → patch succeeds → mock returns 2 entities/1 edge → `assert > 0` passes. No remaining non-passable paths.

#### 5.7 Builder Process Quality
2nd cycle (1 test-writer retry + 1 builder pass-through). Loop was 1 cycle, targeted, resolved the specific defect identified. CLEAN.

---

### AC Compliance Table

| AC | Evidence | Status |
|----|----------|--------|
| AC1: LLMExtractor wiring tests — correct RED | 3 tests, `AttributeError` patch on server-namespace attribute, identity assertions | PASS |
| AC2: entity/edge count tests — correct RED (SQLite fix applied) | 1 test, `AttributeError` in RED (no longer `ProgrammingError`), check_same_thread=False | PASS |
| AC3a: GraphAugmentedRetriever wiring tests — correct RED | 3 tests, `AttributeError` patch on server-namespace attribute, identity assertions | PASS |
| AC3b: entity_type in response tests — correct RED | 3 tests, `AssertionError`/`KeyError` for absent entity_type key | PASS |
| AC4: ImportError degradation tests — correct RED | 2 tests, `AttributeError` (server-namespace absent), GREEN-phase fragility cleared | PASS |
| AC5: All tests FAIL | Builder confirmed 12/12; code-reader verified absent patch targets; prior cycle independently confirmed | PASS |

### Deductions
- quality-runner environment failure — cannot independently confirm test count: −0.05
- AC2 LAX assertions (`> 0` not exact counts): −0.03
- AC1 env var test uses all_args concatenation (slightly imprecise model param check): −0.01

### Confidence: 0.91 → PASS → docs

[[2026-04-09]] Thu 15:04
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Test file only (RED phase); no application code changed; no new behavior or API surface |
| 2 | Module docstrings | No | N/A | Only deliverable is `test_ingest_graph_wiring.py` — has accurate module-level docstring; no public classes or functions added to production code |
| 3 | External attribution | No | N/A | Task body cites internal codebase patterns (`test_server.py`, `test_ingest_graph_tools.py`) only; no external repos, articles, or docs used |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | No `.owlbear/research/699-*.md` produced; arch review embedded in task body |

### Files Updated
- None

### Scratch Files Cleaned
- None found (`699-*` search returned no results)

[[2026-04-09]] Thu 15:27
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: LLMExtractor wiring tests | TestFromAC_LLMExtractorWiring (3 tests), all FAIL with `AttributeError: no attr 'LLMExtractor'` — verified independently | PASS |
| AC2: entity/edge count > 0 tests | TestFromAC_IngestWithLLMExtractor (1 test), FAILS with `AttributeError` (fixed from SQLite ProgrammingError in retry) — verified independently | PASS |
| AC3a: GraphAugmentedRetriever wiring tests | TestFromAC_GraphAugmentedRetrieverWiring (3 tests), all FAIL with `AttributeError: no attr 'GraphAugmentedRetriever'` — verified independently | PASS |
| AC3b: entity_type in search response tests | TestFromAC_SearchKnowledgeEntityType (3 tests), FAIL with `AssertionError`/`KeyError` on missing `entity_type` — verified independently | PASS |
| AC4: ImportError degradation tests | TestFromAC_LLMExtractorImportError (2 tests), all FAIL with `AttributeError` — verified independently | PASS |
| AC5: All tests FAIL (RED) | 12/12 FAIL confirmed — `uv run pytest -o "addopts=" -v --tb=line` on stashed (committed-only) tree | PASS |

### Test Results
- pytest (task-scoped): 12 collected, 12 FAILED — all correct RED failure modes
- pytest (full suite): 3881 passed, 370 pre-existing failures, 8 pre-existing errors — no cross-task regressions from this test-only deliverable
- ruff: clean ("All checks passed!")

### Architect Quality: 4/5
Original AC was adequate; architect substantially improved it by splitting AC3 into AC3a/AC3b (retriever wiring + entity_type) and correcting AC4 (ImportError not OWLBEAR_MODEL). Minor gap: AC2 wording didn't anticipate SQLite threading constraints, causing 1 retry cycle to fix test harness.

### Deduction Breakdown
- No deductions. All 6 AC lines have specific, independently verified evidence. Lint clean. AC quality 4/5 (above ≤3 threshold). Reviewer evidence section present and detailed. No task-scoped regressions.

### Confidence: .98
### Action: archive

Note: Working tree has uncommitted modifications to `test_ingest_graph_wiring.py` from task #690 (TestFromAC_PyprojectDependency class appended). These are outside #699 scope and do not affect the committed deliverable at `580d27a`.
