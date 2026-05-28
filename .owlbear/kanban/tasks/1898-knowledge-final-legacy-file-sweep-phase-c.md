---
id: 1898
title: 'Knowledge: Final legacy file sweep (Phase C)'
status: todo
priority: needed
created: 2026-05-27T16:19:59.014229+02:00
updated: 2026-05-28T02:02:33.556160+02:00
tags:
  - knowledge
  - layer-4
  - cleanup
parent:
depends_on:
  - 1897
  - 1900
  - 1911
ac:
  - 'AC1: These 13 files deleted from serve/knowledge/src/owlbear_knowledge/: source_store.py,
    document_store.py, graph_store.py, graph_builder.py, status_store.py, ingest.py,
    query_service.py, retrieval.py, refresh.py, protocol.py, models.py, schema.py,
    extractor.py'
  - 'AC2: compute_content_hash function inlined in stores/content.py (no import from
    status_store)'
  - 'AC3: HybridEmbedding and SparseVector classes moved to embeddings.py; qdrant.py
    imports from embeddings instead of protocol'
  - 'AC4: ContentFetcher protocol moved to owlbear_knowledge/fetcher.py (top-level,
    alongside HttpxContentFetcher); mcp-knowledge _helpers.py updated to import from
    new location'
  - 'AC5: AppContext source_store and refresh_orchestrator fields absent (removed
    by prerequisite #1911)'
  - 'AC6: __init__.py exports only from protocols/ and stores/ subpackages'
  - 'AC7: Dead test files deleted: tests/test_search_provenance.py, tests/test_mcp_knowledge_lifespan_1888.py'
  - 'AC8: grep -r for imports of deleted modules (source_store, document_store, graph_store,
    graph_builder, status_store, ingest, query_service, retrieval, refresh, protocol,
    models, schema, extractor) returns zero hits in serve/ and tests/'
  - 'AC9: uv run pytest tests/ serve/ --ignore=tests/test_mcp_kanban_newline_norm_1531.py
    -x -q exits 0'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Delete all remaining legacy implementation files now that no code references them.

## Files to delete from serve/knowledge/src/owlbear_knowledge/
- source_store.py, document_store.py, graph_store.py, graph_builder.py
- status_store.py, ingest.py, query_service.py, retrieval.py
- refresh.py, protocol.py, models.py, schema.py

## Additional work
- Rewrite __init__.py to export from protocols/ and stores/ only
- Fix stores/content.py: move compute_content_hash locally (currently imports from status_store)
- Remove test_search_provenance.py if search_knowledge no longer has legacy path
- grep entire codebase for stale references

## Verification
- `uv run python -c "import owlbear_knowledge"` passes with new __init__.py
- No imports of deleted modules anywhere in workspace
- Full test suite passes
- Only new store-owned schema remains (no monolithic DDL)

## Research
See .owlbear/research/knowledge-legacy-deletion.md §3.1, §3.2

[[2026-05-27T18:18:11+02:00]]
## Research

Key findings (see .owlbear/research/knowledge-phase-c-sweep.md):
- Dependency chain broken: #1897 archived as decomposed but sub-tasks #1899/#1900 NOT done. Fixed by adding #1900 dep.
- 5 non-legacy files import from deletion targets (embeddings.py, qdrant.py, extractor.py, stores/content.py, mcp _helpers.py). Types must migrate before deletion.
- Migration plan: compute_content_hash → stores/content.py, HybridEmbedding → embeddings.py, StructuredExtractor/Entity/Edge → extractor.py.
- EntityType/RelationType conflict in _helpers.py must be resolved by Phase B2 or Phase C.
- Additional deletions identified: loader.py, test_search_provenance.py, README.md rewrite.
- Recommended sub-phasing: C1 (type migrations) then C2 (deletions).

Confidence: 0.85
No follow-up tasks created — scope already correctly defined; blocked on prerequisites.

[[2026-05-28T01:32:45+02:00]]
## Research

Validation pass complete (see .owlbear/research/knowledge-phase-c-sweep-v2.md).

Key findings — situation significantly simpler than prior research:
- Dependencies #1897 and #1900 both archived/completed — task UNBLOCKED
- `extractor.py` is dead code (zero non-legacy consumers) — add to deletion list
- EntityType/RelationType conflict is MOOT — only consumer was dead `extractor.py`
- Only 3 type migrations needed (~43 LOC): compute_content_hash, HybridEmbedding+SparseVector, ContentFetcher
- 2 dead test files identified: test_search_provenance.py (37 failures), test_mcp_knowledge_lifespan_1888.py (21 errors)
- AppContext has 2 dead fields (source_store, refresh_orchestrator) set to None in lifespan

Execution plan: C1 (migrate 3 types) then C2 (delete 13 files + 2 tests + rewrite __init__.py + README)
Confidence: 0.90
No new follow-up tasks — scope updated in AC.

[[2026-05-28T02:02:33+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure deletion + 3 type migrations within one package |
| Interface clarity | PASS | Each AC names exact files, functions, and module paths |
| Dependency correctness | PASS (fixed) | Added #1911 — prevents deletion of source_store.py/refresh.py/models.py before consumers removed |
| Module layering | PASS | Migrations stay within knowledge package; cross-package update (mcp-knowledge _helpers.py) is import-path only |
| TDD compliance | PASS | Test-writer will verify post-deletion import topology and suite health |
| KISS/YAGNI | PASS | Minimal type relocations (~43 LOC); no new abstractions |
| Premise challenge | PASS | Research confirms all 13 files have zero non-legacy consumers after #1911 completes |
| Pattern consistency | PASS | Follows established v2 migration pattern (protocols/ and stores/ as canonical export surface) |
| Security surface | PASS | No new boundaries; deletion only |
| Single domain | PASS | Knowledge domain exclusively |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| __init__.py rewrite | Downstream import breakage if any non-legacy consumer used old public API | ImportError | By AC8 grep verification | Build failure |
| HybridEmbedding→embeddings.py | Circular import if embeddings.py already imports from qdrant.py | ImportError | Verified: no circular path exists | None |
| ContentFetcher→fetcher.py | mcp-knowledge _helpers.py breaks if import not updated | ImportError | AC4 explicitly requires _helpers.py update | MCP server crash |

### Design Diverge
- Skipped: single valid approach (migrate types, then delete), no competing designs

### Challenge Results
- Challenger: reconsider (confidence 0.61)
- Key findings: (1) dependency framing too strong as safety claim vs scope/suite coherence, (2) AC5 removal would leave gap — keep as verification backstop, (3) protocol.py has 3 surviving consumers outside #1911 scope, (4) AC quality issues (ambiguous AC4, broad quantifiers)
- Architect response: accepted — kept AC5 as verification, disambiguated AC4 with full module path, made AC1 self-contained with explicit file list, tightened AC8 and AC9 with exact commands

### Proof-Bundle Validation
- Planner assignment: null
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Dependency Fix
- Added #1911 to depends_on (was [#1897, #1900], now [#1897, #1900, #1911])
- Rationale: #1911 removes AppContext source_store/refresh_orchestrator fields and legacy imports from server.py. Without this, deleting source_store.py/refresh.py breaks TYPE_CHECKING imports in server.py:76-77 and test assertions in test_mcp_knowledge_legacy_removal_1900.py:72-83.

### Verdict: APPROVE
### Action Taken: Refined all 9 AC lines for precision and verifiability, added #1911 dependency, set proof_bundle=behavioral, advanced to todo.
