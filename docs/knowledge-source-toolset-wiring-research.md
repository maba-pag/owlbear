# Wire KnowledgeSourceToolset in Bootstrap

> **Owning task:** #501 — Wire KnowledgeSourceToolset in bootstrap build_toolsets
> **Date:** 2026-03-06  **Status:** Complete

## 1. Context and Question

INT-04 from `docs/integration-audit.md`: `KnowledgeSourceToolset` is implemented (`src/owlbear/tools/knowledge_source.py`) with tests, but never instantiated in `build_toolsets()`. Agents cannot manage knowledge sources at runtime. Should we wire it into bootstrap or document it as CLI-only?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| KnowledgeSourceToolset class | `src/owlbear/tools/knowledge_source.py` | 1.0 — the toolset to wire |
| KnowledgeSourceStore class | `src/owlbear/memory/knowledge/source_store.py` | 1.0 — required dependency |
| RefreshOrchestrator class | `src/owlbear/memory/knowledge/refresh.py` | 1.0 — required dependency |
| `build_toolsets()` | `src/owlbear/bootstrap.py` L536–670 | 1.0 — target function |
| `_build_bookmark_toolset()` | `src/owlbear/bootstrap.py` L427–482 | 0.9 — analogous pattern |
| `_build_knowledge_toolset()` | `src/owlbear/bootstrap.py` L328–424 | 0.9 — shares infra |
| integration-audit.md | `docs/integration-audit.md` L23 | 0.8 — original finding |
| bearclaw CLI source commands | `src/bearclaw/cli.py` L353–366 | 0.7 — CLI-only path today |

## 3. Analysis

### 3.1 Constructor Dependencies

| Dependency | Constructor needs | Already in bootstrap? | Build effort |
|---|---|---|---|
| `KnowledgeSourceStore` | `sqlite3.Connection` | Yes — `_KnowledgeInfra.conn` | 1 line |
| `RefreshOrchestrator` | `store`, `IngestPipeline`, optional `WebCrawler`, optional `workspace_root` | `IngestPipeline` built inside `_build_knowledge_toolset` (not returned); `WebCrawler` not in bootstrap | ~5 lines |
| `workspace_root` | `Path` | Yes — `workspace` param | 0 lines |

### 3.2 Option Comparison

| Criterion | Wire into bootstrap (.90) | CLI-only + doc update (.40) |
|---|---|---|
| Agent capability | Agents get `add_source`, `list_sources`, `refresh_source` | Agents must ask user to run CLI |
| Implementation effort | ~20 LOC new helper function | ~5 LOC doc edits |
| Risk | Low — follows `_build_bookmark_toolset` pattern exactly | Low — but reduces agent autonomy |
| KISS alignment | Good — reuses existing infra pattern | Good — simpler, but creates capability gap |
| YAGNI concern | Low — toolset already implemented and tested | N/A |
| Consistency | Matches copilot-instructions.md which lists it as agent-exposed | Would require updating copilot-instructions.md |

### 3.3 Wiring Pattern (from `_build_bookmark_toolset`)

The established pattern for conditional knowledge toolsets is:

1. Accept `_KnowledgeInfra` as parameter
2. Build local `IngestPipeline` from infra components
3. Build domain-specific store from `infra.conn`
4. Compose toolset and return
5. Wrap in try/except with `WARNING` log on failure

`KnowledgeSourceToolset` wiring follows this identically:

1. `KnowledgeSourceStore(infra.conn)` — same as `BookmarkStore(infra.conn)`
2. Build `IngestPipeline` from infra (or share with knowledge toolset)
3. `RefreshOrchestrator(store, pipeline, workspace_root=workspace)`
4. `KnowledgeSourceToolset(store, orchestrator, workspace_root=workspace)`

### 3.4 IngestPipeline Sharing Concern

Currently `_build_knowledge_toolset` and `_build_bookmark_toolset` each build their own `IngestPipeline`. A third copy for the source toolset is wasteful but consistent with the current pattern. INT-02 already tracks the shared-infra refactor — the wiring task should follow the current pattern and let INT-02 consolidate later.

## 4. Recommendation (.90 confidence)

**Wire into bootstrap** — create `_build_knowledge_source_toolset(infra, workspace)` following the `_build_bookmark_toolset` pattern. Rationale:

- The toolset is already implemented, tested, and documented as agent-exposed
- All infrastructure already exists in `_KnowledgeInfra`
- The pattern is established — 1 new ~15-line helper function
- CLI-only would contradict `copilot-instructions.md` and reduce agent autonomy
- `WebCrawler` is optional in `RefreshOrchestrator` — skip it for now (crawl sources can be added later)

Risk: third `IngestPipeline` instance — acceptable, tracked by INT-02.

Secondary fix: update `docs/architecture.md` L284 which already claims "Wired (conditional)" — currently false.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe edit 501 --description "Wire KnowledgeSourceToolset into bootstrap build_toolsets().

## Research findings (2026-03-06)
See docs/knowledge-source-toolset-wiring-research.md for details.

## Implementation approach
Create _build_knowledge_source_toolset(infra, workspace) following _build_bookmark_toolset pattern:
1. KnowledgeSourceStore(infra.conn)
2. IngestPipeline from infra components
3. RefreshOrchestrator(store, pipeline, workspace_root=workspace)
4. KnowledgeSourceToolset(store, orchestrator, workspace_root=workspace)
5. Append to raw[] in build_toolsets() inside the if infra block, after bookmark_ts

## AC
- [ ] _build_knowledge_source_toolset helper added to bootstrap.py
- [ ] KnowledgeSourceToolset appears in build_toolsets() output when knowledge infra available
- [ ] Test: build_toolsets includes KnowledgeSourceToolset when infra is available
- [ ] Test: build_toolsets skips gracefully when knowledge infra fails
- [ ] docs/architecture.md L284 already correct (no change needed)
- [ ] WebCrawler NOT wired (optional, crawl sources deferred)
"
```
