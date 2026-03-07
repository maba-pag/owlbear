---
id: 501
title: Wire KnowledgeSourceToolset in bootstrap build_toolsets
status: archived
priority: important
created: 2026-03-04T07:38:14.4075018+01:00
updated: 2026-03-07T18:07:57.393189+01:00
started: 2026-03-06T20:34:38.0224295+01:00
completed: 2026-03-07T18:07:57.393189+01:00
tags:
    - audit
    - tooling
    - scope:core
class: standard
---

Wire KnowledgeSourceToolset into bootstrap build_toolsets().

## Research findings (2026-03-06)

See docs/knowledge-source-toolset-wiring-research.md for full analysis.

## Implementation spec

Create `_build_knowledge_source_toolset(infra, workspace)` in `src/owlbear/bootstrap.py` following the `_build_bookmark_toolset` pattern (L436-483).

### Helper function: `_build_knowledge_source_toolset`

- **Location:** `src/owlbear/bootstrap.py`, immediately after `_build_bookmark_toolset`
- **Signature:** `_build_knowledge_source_toolset(infra: _KnowledgeInfra, workspace: Path) -> AbstractToolset | None`
- **Pattern:** identical to `_build_bookmark_toolset`  lazy imports inside try/except, `WARNING` log on failure, return `None` on error
- **Body:**
  1. Import `KnowledgeSourceStore` from `owlbear.memory.knowledge.source_store`
  2. Import `RefreshOrchestrator` from `owlbear.memory.knowledge.refresh`
  3. Import `IngestPipeline` from `owlbear.memory.knowledge`
  4. Import `KnowledgeSourceToolset` from `owlbear.tools.knowledge_source`
  5. Build `KnowledgeSourceStore(infra.conn)`
  6. Build `IngestPipeline(conn=infra.conn, graph_store=infra.graph_store, vector_store=infra.vector_store, embedding_provider=infra.embedding_provider, entity_extractor=infra.entity_extractor, text_chunker=infra.text_chunker)`  no `inter_doc_builder` (matches bookmark pattern)
  7. Build `RefreshOrchestrator(store=source_store, pipeline=ingest_pipeline, workspace_root=workspace)`  no `crawler` (deferred)
  8. Return `KnowledgeSourceToolset(store=source_store, orchestrator=orchestrator, workspace_root=workspace)`
- **Warning message on failure:** `Failed to create KnowledgeSourceToolset`

### Wiring in `build_toolsets`

- **Location:** inside the `if infra is not None:` block, after the bookmark_ts block (after L645)
- Append pattern:
  `
  source_ts = _build_knowledge_source_toolset(infra, workspace)
  if source_ts is not None:
      raw.append(source_ts)
  `

### Out of scope

- `WebCrawler` NOT wired  optional param, crawl source type deferred
- No `IngestPipeline` sharing refactor  follows current pattern, INT-02 tracks consolidation
- `docs/architecture.md` L284 already claims 'Wired (conditional)'  will become correct after this task, no edit needed
- `update_workspace` is already implemented on `KnowledgeSourceToolset` and `RefreshOrchestrator`; `ProjectToolset` discovery is automatic via duck-typed iteration  no additional wiring needed

## Acceptance criteria

- [ ] `_build_knowledge_source_toolset(infra, workspace)` helper exists in `src/owlbear/bootstrap.py` after `_build_bookmark_toolset`
- [ ] Helper follows try/except pattern: lazy imports, builds 4 objects, returns toolset or `None`
- [ ] Helper logs `WARNING` with `Failed to create KnowledgeSourceToolset` on any exception
- [ ] `build_toolsets()` calls the helper inside `if infra is not None:` block, after bookmark_ts
- [ ] `build_toolsets()` appends result to `raw` only when not `None`
- [ ] Test: `build_toolsets` output includes `KnowledgeSourceToolset` when knowledge infra is available (mock Qdrant + BGE-M3 + EntityExtractor, same pattern as `test_both_toolsets_created`)
- [ ] Test: `build_toolsets` omits `KnowledgeSourceToolset` when `_build_knowledge_infra` returns `None`
- [ ] Test: `_build_knowledge_source_toolset` returns `None` and logs WARNING when constructor raises
- [ ] `uv run ruff check src/owlbear/bootstrap.py tests/test_bootstrap.py` clean
- [ ] `uv run pytest tests/test_bootstrap.py -q --tb=short` all green
