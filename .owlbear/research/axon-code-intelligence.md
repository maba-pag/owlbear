# Axon — Code Intelligence Engine Research

> **Owning task:** #586 — Research: harshkedia177/axon
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

Task #586 asks: analyze harshkedia177/axon for multi-agent delegation, orchestration patterns, and task execution logic applicable to OwlBear.

**Key finding:** Axon is **not** a multi-agent system. It is a code intelligence engine that indexes codebases into a knowledge graph (KuzuDB) and exposes structural understanding via MCP tools and a CLI. The relevant patterns for OwlBear are: (1) knowledge graph schema design, (2) MCP tool design with next-step hints, (3) hybrid search with RRF, (4) phased ingestion pipeline, and (5) the StorageBackend Protocol abstraction.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| harshkedia177/axon v0.2.4 | github.com/harshkedia177/axon | .90 | Full source analysis — pipeline, graph model, MCP server, hybrid search, storage abstraction |
| Aider RepoMap | aider.chat/docs/repomap.html | .70 | Tree-sitter code structure graphs, token-budgeted context for LLMs, graph ranking for relevance |
| OwlBear community-detection.md | docs/research/community-detection.md | .85 | Prior analysis: Leiden algorithm GPL-licensed (blocker), scale concerns at <2K entities |

## 3. Analysis

### 3.1 Axon Architecture Overview

Axon's 12-phase pipeline builds a code knowledge graph:

| Phase | What | OwlBear Equivalent | Gap |
|-------|------|--------------------|----|
| File walking + structure | File/folder nodes | N/A (not code-indexing) | Different domain |
| tree-sitter parsing | Function/class/method nodes | N/A | Different domain |
| Import/call/type resolution | CALLS, IMPORTS, USES_TYPE edges | DEFINES, IMPORTS, DEPENDS_ON | OwlBear lacks CALLS |
| Community detection (Leiden) | Auto-cluster related symbols | Rejected (GPL, scale) | See §3.3 |
| Execution flow tracing | BFS from entry points | N/A | Novel pattern |
| Dead code detection | Multi-pass unreachability | N/A | Not applicable |
| Change coupling (git) | Co-change frequency edges | N/A | Interesting but different domain |
| Embeddings (bge-small-en) | 384-dim vectors for hybrid search | BGE-M3 1024-dim | OwlBear already has this |

### 3.2 Patterns Relevant to OwlBear

#### A. MCP Tool Design — Next-Step Hints (.80 confidence)

Axon's MCP tools append guidance to every response:

- `axon_query` → "Next: Use context() on a specific symbol for the full picture."
- `axon_context` → "Next: Use impact() if planning changes to this symbol."
- `axon_impact` → "Tip: Review each affected symbol before making changes."

This creates a **guided investigation workflow** where the LLM naturally follows a query→context→impact chain. OwlBear's `KnowledgeToolset` (`query_knowledge`, `ingest_document`, `list_knowledge_sources`) could adopt this pattern to guide agents through knowledge retrieval workflows.

#### B. Hybrid Search with Reciprocal Rank Fusion (.75 confidence)

Axon fuses BM25 + vector + fuzzy search using RRF (k=60). OwlBear's `GraphAugmentedRetriever` already does graph-neighbor expansion on vector results. The RRF fusion pattern is worth noting but OwlBear already has a working hybrid approach. Key difference: Axon groups results by execution flow (process), giving structural context alongside search results.

#### C. StorageBackend Protocol (.70 confidence)

Axon abstracts storage behind a `@runtime_checkable` Protocol class with 20+ methods. OwlBear's knowledge store uses concrete SQLite + Qdrant implementations without a formal protocol. The pattern validates OwlBear's approach — a protocol would add abstraction without benefit since we only have one backend.

#### D. Phased Pipeline with Progress Callbacks (.65 confidence)

Axon's `run_pipeline()` accepts a `progress_callback: Callable[[str, float], None]` for phase progress reporting. The pattern is clean: each phase calls `report(phase_name, pct)` with 0.0→1.0 progress. OwlBear's knowledge ingestion pipeline could adopt this for status reporting to Slack/CLI channels.

#### E. Watch Mode — Tiered Re-Indexing (.60 confidence)

Axon's watcher uses watchfiles (Rust-backed) with tiered re-indexing: file-local phases run immediately, global phases batch after a 5-second quiet period (60s max dirty age). This incremental approach is well-designed but addresses a different problem (code index vs. document knowledge base).

### 3.3 Patterns NOT Applicable to OwlBear

| Pattern | Why Not |
|---------|---------|
| Community detection (Leiden) | GPL-licensed (`leidenalg` + `igraph`); OwlBear is MIT. Already rejected in #274 research. |
| tree-sitter AST parsing | OwlBear indexes knowledge documents, not codebases. Different domain. |
| Dead code detection | Code-specific. Not relevant to knowledge graph of concepts/decisions. |
| KuzuDB graph storage | OwlBear uses SQLite for graph + Qdrant for vectors. No reason to change. |
| Change coupling (git history) | OwlBear doesn't index code repositories. |

### 3.4 Comparison: Code Intelligence Approaches

| Criterion | Axon | Aider RepoMap | OwlBear Knowledge |
|-----------|------|---------------|-------------------|
| Domain | Code structure | Code context | Documents/concepts |
| Graph type | Full AST + calls + types | File-level dependencies | Entity-relationship |
| Storage | KuzuDB (Cypher) | In-memory | SQLite + Qdrant |
| Search | BM25 + vector + fuzzy (RRF) | Graph ranking (PageRank-like) | Vector + graph expansion |
| Embedding model | bge-small-en-v1.5 (384d) | N/A | BGE-M3 (1024d) |
| MCP integration | 7 tools + 3 resources | N/A | 3 tools (knowledge) |
| Token budgeting | Full results per tool call | Adaptive map sizing | `knowledge_context_tokens` config |

## 4. Recommendation (.75 confidence)

**Primary takeaway: adopt MCP next-step hints pattern.** This is the most directly applicable pattern from Axon. It's trivial to implement (append a string to tool responses) and meaningfully improves agent tool-use workflows by creating guided investigation chains.

**Secondary takeaway: RRF fusion is validated.** Axon's use of RRF (k=60) for fusing multiple search strategies confirms OwlBear's approach. No action needed — OwlBear's graph-augmented retrieval already works.

**Not recommended:** Adopting Axon's code-intelligence features (tree-sitter, community detection, dead code, change coupling). These solve a different problem than OwlBear's document knowledge base. If OwlBear ever needs code intelligence, Axon itself could be used as an external MCP server rather than reimplemented.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add next-step hints to KnowledgeToolset MCP tool responses" --priority nice-to-have --tags "scope:knowledge,phase-research" --body "Adopt Axon's guided-investigation pattern: append contextual next-step hints to knowledge tool responses. E.g. query_knowledge -> 'Tip: Use ingest_document to add missing context.' See docs/research/axon-code-intelligence.md §3.2A. AC: Each KnowledgeToolset tool response includes a relevant next-step hint string."

kanban\kanban-md.exe create "Evaluate Axon as external MCP server for code intelligence" --priority someday --tags "scope:knowledge,research,phase-research" --body "Axon (pip install axoniq, MIT license) provides code-level knowledge graphs via MCP. Evaluate running it as an external MCP server alongside OwlBear for code-aware agent tasks. See docs/research/axon-code-intelligence.md §4. AC: Decision documented on whether to integrate Axon MCP server."
```
