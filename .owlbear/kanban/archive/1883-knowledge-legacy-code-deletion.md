---
id: 1883
title: 'Knowledge: Legacy code deletion'
status: archived
priority: needed
created: 2026-05-25T19:05:51.888164+02:00
updated: 2026-05-27T16:24:34.685445+02:00
tags:
  - knowledge
  - layer-4
  - cleanup
parent:
depends_on:
  - 1881
  - 1882
ac:
  - 'Removed files: source_store.py, document_store.py, graph_store.py, graph_builder.py,
    status_store.py, old ingest.py, query_service.py, retrieval.py, refresh.py, old
    protocol.py, old models.py, old schema.py, MCP helpers (_enrichment.py, _consolidation.py)'
  - No remaining imports of deleted modules anywhere in the codebase
  - All tests pass after deletion (no test depends on legacy code)
  - Old table DDL removed; only new store-owned schema remains
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective

Remove all unused legacy implementation files. Clean sweep after all MCP tools are wired to new protocol-conformant implementations.

## Context

- Depends on: All MCP tools wired and proven (#1881, #1882)
- Legacy files to remove from `serve/knowledge/src/owlbear_knowledge/`:
  - `source_store.py` (replaced by stores/sources.py)
  - `document_store.py` (replaced by stores/content.py)
  - `graph_store.py` (replaced by stores/graph.py)
  - `graph_builder.py` (subsumed by EnrichmentStore suggest_intra_doc_edges)
  - `status_store.py` (subsumed by ContentStore dedup)
  - `ingest.py` (old pipeline, replaced by ingest_coordinator.py)
  - `query_service.py` (replaced by query_facade.py)
  - `retrieval.py` (subsumed by QueryFacade.search)
  - `refresh.py` (subsumed by IngestCoordinator.refresh)
  - `protocol.py` (old VectorStoreProtocol etc, replaced by protocols/)
  - `models.py` (old data models, replaced by protocol types)
  - `schema.py` (old monolithic DDL, replaced by per-store ensure_tables)
- Legacy MCP helpers to remove from `serve/mcp-knowledge/`:
  - `_enrichment.py`, `_consolidation.py`

## Implementation Notes

- grep for all imports of deleted modules; fix or remove
- Old tests that only test legacy code can be removed
- Verify: `uv run python -c \"import owlbear_knowledge\"` passes
- Verify: full test suite passes

[[2026-05-27T16:20:24+02:00]]
## Research
- Research doc: .owlbear/research/knowledge-legacy-deletion.md
- Sources: 4 studied, 4 high-relevance (all codebase)
- Recommendation: Three-phase deletion (confidence: 0.85)

Key findings:
- _enrichment.py is dead code (zero importers) — Phase A
- _consolidation.py still active (MCP tools use it) — Phase B migration needed
- MCP server runs dual-path (legacy + new) — must migrate before deleting core legacy files
- 9 test files are pure legacy; loader.py is unlisted but 100% legacy-dependent
- models.py EntityType values DIFFER from protocols/common.py (30+ vs 12) — not drop-in

Follow-up tasks: #1896 (Phase A), #1897 (Phase B), #1898 (Phase C)

[[2026-05-27T16:22:38+02:00]]
## Architecture Review

### Verdict: SPLIT (already decomposed)

Research phase identified that this task cannot be executed atomically:
- _consolidation.py is still actively imported by MCP tools → requires migration before deletion
- MCP server runs dual-path (legacy + new) → ordering matters
- models.py EntityType values differ from protocols/common.py (30+ vs 12) → not drop-in

The researcher correctly decomposed into three sequenced phases:
- #1896 Phase A: Delete dead code (zero importers) — _enrichment.py, loader.py, 9 test files
- #1897 Phase B: MCP server v2-only migration — remove dual-path, migrate _consolidation.py
- #1898 Phase C: Final legacy sweep — delete remaining 12 files, rewrite __init__.py

### Dependency Fix
Removed circular dep: #1896 depended on #1883 (superseded parent). Replaced with #1881 + #1882 (the actual prerequisite work).

### Action Taken
Task superseded by decomposition. Moved to done for archival as decomposed → #1896, #1897, #1898.

[[2026-05-27T16:24:34+02:00]]
## Audit
### Regression Detection
- Changed files: .owlbear/research/knowledge-legacy-deletion.md (docs/config only)
- Test domain mapping: skip — no testable code changed
- Regression verdict: PASS (N/A for docs-only deliverable)

### Intent Verification
- Scope alignment: PASS — research stayed within knowledge domain, no extraneous scope
- Purpose match: PASS — task purpose (legacy cleanup) served by decomposition into phased follow-ups (#1896, #1897, #1898)
- Extraneous scope: none
- Boundary check: function-level behavior verification deferred to reviewer (not applicable, research task)

### Architect Quality: 4/5
Architect correctly confirmed SPLIT verdict, validated the three-phase sequencing rationale, and fixed a circular dependency (#1896 depending on superseded parent). Minor gap: original AC not updated to reflect decomposition outcome, but moot for superseded task.

### Commit Integrity
- Upstream commit presence: PASS — 69116a22 (research doc committed by researcher)
- No builder/reviewer commits expected (superseded by decomposition)

### Research Task Verification
- Research doc exists: .owlbear/research/knowledge-legacy-deletion.md
- Follow-up tasks created: #1896 (Phase A), #1897 (Phase B), #1898 (Phase C)
- Follow-ups reference parent task context and have correct dependency chain
- Decomposition justified: _consolidation.py active imports, MCP dual-path, models.py type incompatibility

### Deduction Breakdown
No deductions. Research deliverable complete, follow-ups created with proper sequencing.

### Confidence: 1.00
### Action: archive
