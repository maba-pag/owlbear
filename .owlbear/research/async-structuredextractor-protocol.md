# Async StructuredExtractor Protocol

> **Owning task:** #687 — Make StructuredExtractor protocol async and update EntityExtractor await
> **Date:** 2026-04-09  **Status:** Complete

## 1. Context and Question

Task #676 research found that `StructuredExtractor.extract()` is sync but all real implementations (PydanticAI, future LLM adapters) are inherently async. PydanticAI's `run_sync()` fails inside an existing event loop (RuntimeError). The protocol must become async.

**Question:** What is the full blast radius of changing the protocol to `async def extract()`? The original AC lists 4 files — is that complete?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| S1 | PEP 544 — Protocols: Structural subtyping | 0.9 | `@runtime_checkable` checks attribute existence, not sync/async — isinstance unaffected |
| S2 | Python docs — `typing.Protocol` | 0.9 | Protocols support `async def` methods since Python 3.8 |
| S3 | `.owlbear/research/wire-structuredextractor-knowledge-graph.md` (#676) | 1.0 | Original analysis recommending async protocol (confidence 0.82) |
| S4 | Codebase grep for `_extractor.extract` | 1.0 | Found 3 additional callers beyond the AC's listed files |
| S5 | Python docs — `unittest.mock.AsyncMock` | 0.8 | `AsyncMock(spec=Protocol)` auto-promotes async methods; `MagicMock` does not |

## 3. Analysis

### 3.1 Complete Caller Inventory

| File | Call sites | Method context | Needs `await`? | In original AC? |
|------|-----------|----------------|----------------|-----------------|
| `protocol.py` | 1 (definition) | Protocol decl | Change to `async def` | Yes |
| `extractor.py` | L100 | `async def extract()` | Yes | Yes |
| `graph_builder.py` | L122, L130 | `async def build()` | **Yes** | **No** |
| `inter_doc_graph_builder.py` | L154 | `async def build()` | **Yes** | **No** |
| `ingest.py` | L101, L172 | `async def ingest_text/ingest()` | No — uses `EntityExtractor` (already async) | N/A |

### 3.2 Complete Test Impact

| Test file | Current mock type | Needs change? | In original AC? |
|-----------|-------------------|---------------|-----------------|
| `test_extractor.py` | AsyncMock (TDD RED) | No — already written for GREEN | Yes |
| `test_structured_extractor_protocol.py` | AsyncMock (TDD RED) | No — already written for GREEN | Yes |
| `test_graph_builder.py` | `MagicMock(spec=StructuredExtractor)` | **Yes → AsyncMock** | **No** |
| `test_inter_doc_graph_builder.py` | `MagicMock(spec=StructuredExtractor)` | **Yes → AsyncMock** | **No** |
| `test_knowledge_intake_docstore_ingest.py` | AsyncMock already | No | N/A |

### 3.3 `@runtime_checkable` Compatibility

`@runtime_checkable` uses structural subtyping — `isinstance(obj, StructuredExtractor)` checks `hasattr(obj, 'extract')` only. Changing to `async def` does not affect isinstance checks (S1, S2). AC4 is safe.

### 3.4 Risk: `MagicMock` vs `AsyncMock` with async specs

When `StructuredExtractor.extract()` becomes async:
- `MagicMock(spec=StructuredExtractor).extract()` returns a `MagicMock` — NOT awaitable → `TypeError`
- `AsyncMock(spec=StructuredExtractor).extract()` auto-promotes to `AsyncMock` — awaitable ✓

Graph builder tests use `MagicMock(spec=StructuredExtractor)` with `mock.extract.return_value = ...`. After the change, they must switch to `AsyncMock` or explicitly set `mock.extract = AsyncMock(return_value=...)`.

## 4. Recommendation

**Expand AC to include the 4 missing files.** Confidence: **0.92**.

The change is mechanical and low-risk. All caller methods are already `async def`, so adding `await` is natural. The `@runtime_checkable` isinstance checks are unaffected. The only risk is missing a caller — this analysis found 3 additional call sites beyond the original AC.

Challenge: FALLBACK — challenger agent not available in researcher mode.

### Revised Affected Files

```
Source:
  - serve/knowledge/src/owlbear_knowledge/protocol.py          (AC1)
  - serve/knowledge/src/owlbear_knowledge/extractor.py          (AC2)
  - serve/knowledge/src/owlbear_knowledge/graph_builder.py      (NEW — 2 await sites)
  - serve/knowledge/src/owlbear_knowledge/inter_doc_graph_builder.py (NEW — 1 await site)

Tests:
  - tests/test_extractor.py                        (AC3 — already AsyncMock)
  - tests/test_structured_extractor_protocol.py    (AC3 — already AsyncMock)
  - tests/test_graph_builder.py                    (NEW — MagicMock→AsyncMock)
  - tests/test_inter_doc_graph_builder.py          (NEW — MagicMock→AsyncMock)
```

## 5. Follow-up Tasks

No separate follow-up tasks needed — the expanded scope belongs in #687 itself. The AC should be updated to include the 4 additional files before implementation begins.
