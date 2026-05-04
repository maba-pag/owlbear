# Content Injection Guard Wiring at Ingest Pipeline

> **Owning task:** #1322 — P0-06: Content injection guard wiring at ingest pipeline
> **Date:** 2026-05-04 **Status:** Complete

## 1. Context and Question

Task #1322 requires wiring `ContentInjectionGuard` into the MCP `ingest_document` tool path so all web content is scanned for prompt-injection phrases before being stored as chunks.

**Key finding:** Implementation is already complete. Builder work was committed under #1321 (`cd74db6e feat: wire ingest guard at lifespan/text path`). All 32 tests in `test_content_guard_wiring_1321.py` pass green.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/knowledge/src/owlbear_knowledge/content_guard.py` | Codebase | 1.0 — Guard implementation |
| `serve/knowledge/src/owlbear_knowledge/ingest.py` | Codebase | 1.0 — Pipeline integration |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | Codebase | 1.0 — Lifespan wiring |
| `tests/test_content_guard_wiring_1321.py` | Codebase | 1.0 — Test suite (32 tests, all green) |
| OWASP LLM01:2025 (Strategy #3) | External | 0.8 — Input validation pattern |

## 3. Analysis

### Wiring Architecture

```
ingest_document (MCP tool)
  → IngestPipeline.ingest_text()
    → TextChunker.chunk()
    → ContentInjectionGuard.scan(chunk.text)  ← guard fires here
       ├─ blocked=True → return IngestResult(status="blocked"), no storage
       └─ threat=True, blocked=False → log warning, continue
    → DocumentStore.insert_document()
    → DocumentStore.store_chunks()
```

### AC Verification

| AC | Status | Evidence |
|----|--------|----------|
| Guard wired into ingest_document (O9) | ✅ Done | `server.py` L288: `content_guard=ContentInjectionGuard()` passed to pipeline |
| All web content passes through guard | ✅ Done | `ingest.py` L100-119: every chunk scanned, no source_type exemption |
| Guard rejects/sanitizes injection markers | ✅ Done | Strict mode returns `status="blocked"`, warn mode logs + continues |
| Pre-guard legacy chunks not retroactively scanned (D20) | ✅ Done | Guard only in ingest path, not search/query |
| All #1321 tests pass green | ✅ Done | 32 passed, 0 failed (verified 2026-05-04) |

## 4. Recommendation

**Fast-track to done.** All ACs are already satisfied by existing code (confidence: 0.95).

The 0.05 gap: the commit message attributes work to #1321 rather than #1322. This is a bookkeeping mismatch, not a functional gap.

Challenge: SKIP — trivial validation, no architectural decision needed.

## 5. Follow-up Tasks

None required. Implementation is complete, tests pass, lint is clean.
