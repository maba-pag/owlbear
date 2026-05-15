# Label Deferred Knowledge Stubs

> **Owning task:** #1584 — Label deferred knowledge stubs (llm_extractor, inter_doc_graph_builder, list_entities)
> **Date:** 2026-05-15 **Status:** Complete

## 1. Context and Question

Parent research #1576 classified three knowledge surfaces as **document-as-stub**: `llm_extractor.py`, `inter_doc_graph_builder.py`, and the `list_entities` function in `server.py`. This task adds DEFERRED header docstrings so future developers know these are intentional stubs, not forgotten code.

Research question: What is the current state of each file, and are the AC references accurate?

## 2. Sources Studied

| # | Source | Path | Relevance |
|---|--------|------|-----------|
| 1 | llm_extractor.py | `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` | 1.0 |
| 2 | inter_doc_graph_builder.py | `serve/knowledge/src/owlbear_knowledge/inter_doc_graph_builder.py` | 1.0 |
| 3 | server.py (list_entities) | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1294` | 1.0 |
| 4 | Parent research doc | `.owlbear/research/classify-inactive-knowledge-surfaces.md` | 0.9 |
| 5 | #876 research (LLMExtractor wiring) | `.owlbear/research/876-wire-llmextractor-server.md` | 0.7 |

## 3. Analysis

### 3.1 Current File State

| File | Existing Docstring | Has Implementation | Imported by Active Code | DEFERRED Marker |
|------|-------------------|-------------------|------------------------|-----------------|
| `llm_extractor.py` | Yes (4-line module docstring) | Yes — full `LLMExtractor` class with rate limiting and OpenAI SDK integration | No — not imported anywhere in active server code | None |
| `inter_doc_graph_builder.py` | Yes (5-line module docstring) | Yes — full `InterDocGraphBuilder` with vector pre-filtering, canonical blocking, batch LLM inference | Set to `None` in lifespan only | None |
| `list_entities` (server.py) | Yes (1-line function docstring) | Yes — complete async function | Not exposed as MCP tool (no `@mcp.tool` decorator) | None |

### 3.2 AC Reference Check — Stale Task #875

AC-1 references "future task #875" but **#875 does not exist** on the board (not in tasks or archive). It was a historical task for LLMExtractor implementation / content_extractor refactoring, referenced in `.owlbear/sources/overview.md` and `.owlbear/research/876-wire-llmextractor-server.md`. The concept is valid (LLMExtractor activation is future work) but the specific task number is stale.

**Recommendation:** The DEFERRED docstring should reference the concept ("LLMExtractor server activation") rather than the nonexistent task number. Implementer should adjust AC-1's "#875" to a descriptive reference.

### 3.3 Implementation Approach

| Target | Change | Risk |
|--------|--------|------|
| `llm_extractor.py` | Prepend `DEFERRED:` to existing module docstring, note not wired into server | None — docstring only |
| `inter_doc_graph_builder.py` | Prepend `DEFERRED:` to existing module docstring, note StructuredExtractor dependency | None — docstring only |
| `list_entities` in server.py | Add `# DEFERRED:` comment above function, note thread-safety review needed before MCP exposure | None — comment only |

## 4. Recommendation

**Confidence: 0.90** — Trivial docstring/comment changes. All three targets exist, have working implementations, and simply need labeling. The only wrinkle is the stale #875 reference in AC-1 — implementer should use a descriptive reference instead.

**Challenge: SKIPPED** — Trivial cleanup, no alternative recommendations to challenge.

## 5. Follow-up Tasks

None needed — #1584 is itself the follow-up from #1576. No further decomposition required.
