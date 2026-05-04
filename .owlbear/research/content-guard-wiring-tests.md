# Content Injection Guard Wiring — Test Research

> **Owning task:** #1321 — P0-05: Tests — Content injection guard wiring at ingest
> **Date:** 2026-05-04 **Status:** Complete

## 1. Context and Question

Task #1321 requires TDD RED tests verifying `ContentInjectionGuard` is wired into
the `ingest_document` MCP tool path. The guard exists but is not connected to the
live ingest flow. Implementation is #1322 (depends on #1321).

**Question:** What is the current guard wiring state, what test patterns fit, and
what AC tensions exist?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `serve/knowledge/src/owlbear_knowledge/content_guard.py` | Guard impl (0.95) |
| S2 | `serve/knowledge/src/owlbear_knowledge/ingest.py` | Pipeline with guard param (0.95) |
| S3 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:244-345` | Lifespan — no guard (0.95) |
| S4 | `serve/mcp-knowledge/tests/test_ingest_graph_tools.py` | Test patterns (0.90) |
| S5 | Brief §4.6, D20 decision | Design intent (0.90) |
| S6 | `serve/knowledge/src/owlbear_knowledge/content_safety.py` | `should_wrap()` predicate (0.85) |

## 3. Analysis

### Current State

| Component | Guard Status | Detail |
|-----------|-------------|--------|
| `ContentInjectionGuard` class | Implemented | ~40 patterns, `scan()` → `CheckResult` |
| `IngestPipeline.__init__` | Accepts guard | Optional `content_guard` param |
| `IngestPipeline.ingest()` | Uses guard | Scans chunks when `should_wrap(source_type)` is True |
| `IngestPipeline.ingest_text()` | No guard | Zero guard logic — MCP tool uses this path |
| `app_lifespan` | No guard | Constructs pipeline without `content_guard` |
| `ingest_document` tool | No guard | Calls `pipeline.ingest_text()` directly |

**Two gaps:** (1) lifespan doesn't instantiate/pass guard, (2) `ingest_text()` has no guard logic.

### AC5 Tension: "All Content Types"

| Approach | Pro | Con | Confidence |
|----------|-----|-----|------------|
| Guard ALL content in `ingest_text()` | Matches AC5 literally; defense-in-depth | Scans trusted local files unnecessarily | 0.75 |
| Guard only when `metadata.source_type` is untrusted | Matches `ingest()` behavior; skip trusted | AC5 says "all content types"; metadata optional | 0.60 |
| Guard all, but `strict_mode=False` for trusted types | Balanced — warns but doesn't block trusted | More complex logic | 0.50 |

**Recommendation:** Guard ALL content unconditionally in `ingest_text()`. AC5 explicitly lists
"local files, URLs, browser-fetched". Defense-in-depth principle (OWASP LLM01:2025) supports
scanning everything. The overhead is negligible (~40 substring matches per chunk). Confidence: 0.75.

### Test Architecture

Tests should be placed in `tests/test_content_guard_wiring_1321.py` (root tests/ per project
convention for task-scoped tests). Five test classes mapping to five AC lines:

| AC | Test Class | What It Verifies | Key Mocks |
|----|-----------|------------------|-----------|
| AC1 | `TestFromAC_GuardInvokedDuringIngest` | `app_lifespan` wires guard; `ingest_text` calls `scan()` | Pipeline, Guard |
| AC2 | `TestFromAC_InjectionRejected` | Injection markers → blocked/sanitized result | Pipeline with real guard |
| AC3 | `TestFromAC_GuardBeforeStorage` | Guard scan happens before `store_chunks` | Mock ordering |
| AC4 | `TestFromAC_LegacyChunksAccepted` | Pre-guard chunks not retroactively scanned (D20) | Search/query path |
| AC5 | `TestFromAC_AllContentTypes` | Guard applies regardless of source_type metadata | Metadata variants |

### D20 (Legacy Chunks)

D20 says pre-guard legacy chunks are accepted. Tests should verify the guard is NOT
applied when reading/searching existing chunks — only at ingest time. The search path
(`search_knowledge`) should return pre-guard chunks without scanning them.

## 4. Recommendation

Proceed with test creation (T1 — autonomous). Confidence: 0.82.

Challenge: SKIPPED — trivial test wiring research, no architectural decision needed.

**Key design inputs for test-writer:**
- Mock `ContentInjectionGuard.scan()` to verify invocation count and arguments
- Use call ordering assertions (`mock.assert_called_before`) for AC3
- Test at MCP tool level (integration) AND pipeline level (unit)
- Use existing test patterns from `test_ingest_graph_tools.py`

## 5. Follow-up Tasks

Implementation task #1322 already exists with dependency on #1321. No additional
follow-up tasks needed.
