# GCP Always-On Memory Agent Architecture

> **Owning task:** #700 — Research: GCP always-on-memory-agent architecture
> **Date:** 2026-03-09  **Status:** Complete

## 1. Context and Question

OwlBear has a knowledge layer (SQLite graph + vector store + BGE embeddings) for
document ingestion and retrieval. The GCP always-on-memory-agent proposes a
different model: continuous background processing with periodic LLM-driven
consolidation (no embeddings, no vector DB). Should OwlBear adopt, adapt, or
skip this pattern?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | GCP always-on-memory-agent | https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents/always-on-memory-agent | 1.0 — primary subject |
| 2 | Mem0 (mem0ai/mem0) | https://github.com/mem0ai/mem0 | 0.8 — mature prior art for persistent agent memory (49k stars, 273 releases) |
| 3 | OwlBear knowledge layer | `src/owlbear/memory/knowledge/` (local codebase) | 1.0 — comparison baseline |

## 3. Freshness Assessment

- **always-on-memory-agent:** Single commit `cfd52c4` on **2026-03-03** by Shubhamsaboo.
  Demo-quality code, not production-hardened. One file (`agent.py`, ~500 LOC),
  no tests, no CI. Labeled as a "demo" in the PR title.
- **Mem0:** Active project — v1.0.5 released March 2026, 256 contributors,
  continuous development since 2024. Published research paper (arXiv:2504.19413).

## 4. Architecture Summary — always-on-memory-agent

```
Orchestrator (ADK Agent, Gemini 3.1 Flash-Lite)
├── IngestAgent    → extract entities/topics/importance → store_memory (SQLite)
├── ConsolidateAgent → timer-triggered (30min) → cross-reference memories → store_consolidation
└── QueryAgent     → read_all_memories + consolidation_history → synthesize answer
```

**Key design choices:**
- **No embeddings / no vector DB** — relies entirely on LLM to read raw text and synthesize
- **SQLite-only storage** — `memories`, `consolidations`, `processed_files` tables
- **Periodic consolidation** — background timer finds connections between unconsolidated memories
- **Multimodal ingest** — text, images, audio, video, PDFs via Gemini multimodal API
- **ADK agent orchestration** — Google Agent Development Kit with sub-agent routing
- **Dependencies:** google-adk, google-genai, aiohttp, streamlit (5 packages)

## 5. Comparison Table

| Criterion | GCP always-on-memory-agent | OwlBear knowledge layer | Mem0 |
|-----------|---------------------------|-------------------------|------|
| **Storage** | SQLite (flat tables) | SQLite graph + vector store | Vector DB + graph store |
| **Retrieval** | LLM reads all memories (LIMIT 50) | Embedding similarity + graph expansion | Embedding similarity + graph |
| **Embeddings** | None — LLM-as-search | BGE-small (local HF model) | Configurable (OpenAI, etc.) |
| **Consolidation** | Yes — periodic LLM pass | None — static after ingest | Yes — LLM-extracted facts |
| **Scalability** | ~50 memories max (context window) | Thousands of chunks (vector search) | Production-scale (LOCOMO benchmark) |
| **Multimodal** | Yes (27 file types via Gemini) | Text only (file, URL, raw text) | Text-focused |
| **LLM cost** | High — reads all memories per query | Low — embedding + optional LLM extract | Medium — LLM for add/search |
| **Testing** | None | Extensive (pytest suite) | Comprehensive test suite |
| **Maturity** | Demo (1 commit, 1 file) | Production-path | Production (v1.0.5, research paper) |
| **Framework** | Google ADK | PydanticAI | Framework-agnostic |
| **KISS alignment** | High (simple code) | Medium (multiple components) | Low (many integrations) |

## 6. Analysis

### 6.1 What the always-on-memory-agent gets right

1. **Consolidation as a first-class concept.** Periodic background processing that
   finds cross-cutting patterns across memories is a genuine gap in OwlBear. Our
   current pipeline stores and retrieves but never re-processes or synthesizes.

2. **Importance scoring at ingest.** The 0.0–1.0 importance rating per memory is
   simple and effective for prioritizing retrieval.

3. **Simple mental model.** Ingest → Consolidate → Query is easy to reason about.

### 6.2 What doesn't fit OwlBear

1. **No embeddings = no scale.** Reading all 50 memories into context per query
   doesn't work beyond personal note-taking. OwlBear already handles thousands
   of chunks via vector similarity — we can't regress to brute-force LLM search.

2. **Google ADK dependency.** OwlBear uses PydanticAI. Importing `google.adk`
   would add a major framework dependency for no benefit.

3. **Demo quality.** No tests, no error handling, `SELECT * LIMIT 50` as search,
   global `get_db()` function, no connection pooling. Not production code.

4. **Gemini-specific.** Multimodal ingest relies on Gemini's multimodal API.
   OwlBear is model-agnostic.

### 6.3 Adoptable pattern: Periodic consolidation

The consolidation loop concept is the one genuinely valuable idea. Mem0 validates
this independently — their architecture also includes an LLM extraction step that
builds structured facts from raw input (source 2). Both projects agree that static
RAG is insufficient; periodic re-processing adds value.

**Adaptation for OwlBear (.75 confidence):**
A `ConsolidationService` that periodically:
1. Reads unconsolidated chunks/entities from the knowledge graph
2. Uses the existing LLM to find cross-document patterns and insights
3. Stores synthesized "insight" records with back-links to source documents
4. Marks source records as consolidated

This fits within OwlBear's existing SQLite graph + vector store architecture and
uses the existing embedding pipeline. No new dependencies required.

### 6.4 Adoptable pattern: Importance scoring

Adding an `importance` float to ingested documents/chunks is trivially adoptable.
The entity extractor already runs LLM extraction — adding importance scoring to
the extraction prompt is minimal effort (.85 confidence).

## 7. Recommendation (.70 confidence)

**Adapt two patterns; skip the rest.**

1. **Adapt: Periodic consolidation** — Build a `ConsolidationService` that finds
   cross-document insights on a timer. Use existing LLM + graph store, not a
   separate ADK agent. Moderate effort (~200-300 LOC).

2. **Adapt: Importance scoring** — Add `importance: float` to entity extraction.
   Low effort (~20 LOC prompt change + schema addition).

3. **Skip: ADK / Gemini / no-embedding architecture** — Incompatible with OwlBear's
   stack, and the no-embedding approach doesn't scale.

4. **Skip: Multimodal ingest** — YAGNI for OwlBear's current scope (text-focused
   knowledge management).

**Risk:** Consolidation adds ongoing LLM cost. Mitigate with configurable interval
and a `consolidated` flag to avoid re-processing (same approach as the demo).

## 8. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Design ConsolidationService for knowledge graph" --priority needed --status backlog --tag "scope:core,memory,knowledge,design" --body "## Goal\nDesign a ConsolidationService that periodically finds cross-document patterns in the knowledge graph.\n\n## AC\n- [ ] Service reads unconsolidated entities/chunks from SQLite graph\n- [ ] Uses LLM to find cross-cutting patterns and synthesize insights\n- [ ] Stores insight records with back-links to source documents\n- [ ] Marks source records as consolidated\n- [ ] Configurable consolidation interval (default 30min)\n- [ ] consolidated flag on chunks/entities to prevent re-processing\n\n## References\n- GCP always-on-memory-agent consolidation pattern: docs/research/gcp-always-on-memory-agent.md\n- Mem0 LLM extraction pattern: https://github.com/mem0ai/mem0"

kanban\kanban-md.exe create "Add importance scoring to entity extraction" --priority nice-to-have --status backlog --tag "scope:core,memory,knowledge" --body "## Goal\nAdd a 0.0-1.0 importance score to extracted entities during knowledge ingestion.\n\n## AC\n- [ ] EntityExtractor prompt updated to output importance float\n- [ ] importance field added to Entity model\n- [ ] importance stored in SQLite graph\n- [ ] importance used as a ranking signal in query_knowledge results\n\n## References\n- GCP always-on-memory-agent importance pattern: docs/research/gcp-always-on-memory-agent.md"
```
