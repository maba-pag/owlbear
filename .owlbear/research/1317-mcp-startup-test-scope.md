# MCP Startup Test Scope — copilot_auth Removal

> **Owning task:** #1317 — P0-01: Tests — MCP startup (copilot_auth removal, clean server start)
> **Date:** 2026-05-04  **Status:** Complete

## 1. Context and Question

Task #1317 is the RED-phase test task for MCP startup cleanup. The Brief (parent #1316) requires removing the `copilot_auth` device-flow fallback from `app_lifespan` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (lines 274–291). Entity extraction moves to VS Code agent workers; the MCP server runs vector-only search without LLM.

**Question:** What test coverage does the test-writer need to create, and what happens to the existing `test_copilot_server_wiring_888.py` tests?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `server.py` L247–341 (lifespan) | Codebase | 1.0 — target code being modified |
| S2 | `test_copilot_server_wiring_888.py` (5 tests) | Codebase | 1.0 — existing test file per AC4 |
| S3 | `extractor.py` EntityExtractor | Codebase | 0.9 — confirms no-op stub when extractor=None |
| S4 | `ingest.py` IngestPipeline constructor | Codebase | 0.9 — confirms extractor is required but wraps None |
| S5 | `copilot_auth.py` module | Codebase | 0.8 — token path constant, device-flow mechanics |
| S6 | Brief §4.2 + security stance | Brief | 0.9 — cleanup requirements, token deletion |
| S7 | 3 test files with `_bypass_copilot_auth` | Codebase | 0.7 — collateral test fixtures |

## 3. Analysis

### 3.1 Current State of `test_copilot_server_wiring_888.py`

5 tests, **all passing** (verified). They test the copilot_auth fallback path that #1318 will delete:

| Test | Tests | After removal |
|------|-------|---------------|
| `test_lifespan_calls_get_copilot_token_when_no_api_key` | Copilot import triggered | Invalid — path deleted |
| `test_lifespan_creates_llm_extractor_with_copilot_token_as_api_key` | Token → LLMExtractor | Invalid |
| `test_lifespan_structured_extractor_not_none_when_copilot_succeeds` | ctx.structured_extractor set | Inverted — now must be None |
| `test_lifespan_structured_extractor_none_when_copilot_auth_fails` | Graceful fallback | Invalid — no auth to fail |
| `test_lifespan_passes_copilot_integration_header_to_llm_extractor` | Copilot headers | Invalid |

**Verdict:** All 5 tests must be replaced. None are salvageable.

### 3.2 Test Coverage Needed (mapped to AC)

| AC | Required tests | Approach |
|----|---------------|----------|
| AC1: Server starts without copilot_auth import | Verify no `copilot_auth` in `sys.modules` after lifespan; verify `structured_extractor is None` when no API key | Mock I/O deps, monkeypatch-delete API key env vars, check sys.modules |
| AC2: IngestPipeline accepts extractor=None, vector search works | Verify `ctx.ingest_pipeline is not None`; verify `ctx.query_service is not None` | Same lifespan setup, check pipeline + query_service fields |
| AC3: Cached token cleanup | Create temp file at known path, call cleanup, verify deleted; verify no error if file absent | Temp dir isolation via `tmp_path` fixture |
| AC4: Existing tests replaced | File rewritten with new tests | Test-writer replaces file content |

### 3.3 Collateral: `_bypass_copilot_auth` Fixtures

3 other test files set `OWLBEAR_LLM_API_KEY=test-key` to skip copilot_auth:
- `test_server.py`, `test_ingest_graph_tools.py`, `test_ingest_graph_wiring.py`

After copilot_auth removal, these fixtures become vestigial but **harmless** (they just set an env var that activates the explicit-API-key path). No breakage risk. Cleanup is out of scope for #1317.

### 3.4 Test Patterns

Existing test suites use:
- Autouse fixtures patching `init_db`, `GraphStore`, `QdrantVectorStore`, `BgeM3EmbeddingProvider`, etc.
- `async with app_lifespan(MagicMock()) as ctx:` for lifespan testing
- `pytest.mark.asyncio` for all lifespan tests

The new tests should follow the same patterns. The `mock_lifespan_deps` fixture from the current file is reusable with minor updates (may need `make_evaluate_fn` and `make_text_completion_fn` patches too).

## 4. Recommendation

**Confidence: 0.90**

Replace all 5 tests in `test_copilot_server_wiring_888.py` with 5 new RED-phase tests:

1. `test_lifespan_no_copilot_auth_import_without_api_key` — structured_extractor=None, no copilot_auth in sys.modules
2. `test_lifespan_ingest_pipeline_constructed_without_extractor` — pipeline is not None when structured_extractor is None
3. `test_lifespan_query_service_available_without_extractor` — vector search path wired
4. `test_cached_token_cleanup_deletes_existing_file` — cleanup removes `copilot_token.json`
5. `test_cached_token_cleanup_noop_when_file_absent` — cleanup is idempotent

Tests should be named `TestFromAC_CleanMCPStartup` to follow the naming convention. The file docstring should reference task #1317 and note that it replaces the #888 copilot fallback tests.

**Challenge: SKIPPED** — trivial TDD RED scope; no design decision involved.

## 5. Follow-up Tasks

No additional follow-up tasks needed. #1317 is already scoped correctly for the test-writer. The implementation counterpart (#1318) already exists with the correct dependency.
