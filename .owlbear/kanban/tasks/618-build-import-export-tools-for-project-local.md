---
id: 618
title: Build import/export tools for project-local knowledge snapshots
status: backlog
priority: nice-to-have
created: 2026-04-05T01:26:23.9739996+02:00
updated: 2026-04-05T13:06:30.1242617+02:00
tags:
    - scope:mcp
    - phase-2
class: standard
---

## Summary

Add `import_scope` and `export_scope` MCP tools to mcp-knowledge for portable project-local knowledge at `.owlbear/knowledge/knowledge.db`. Import reads a portable SQLite file and ingests data into the global KB under a project-specific scope. Export dumps scoped data to a portable file.

## Context

Research #616 (docs/research/project-local-knowledge-source.md) recommends import/export as the portability mechanism rather than dual-stack live databases. This avoids Qdrant cold-start re-indexing, schema drift, and dual AppContext complexity.

## Acceptance Criteria

- [ ] AC1: `import_scope` tool reads `.owlbear/knowledge/knowledge.db` (or path from `OWLBEAR_LOCAL_KB_PATH`), ingests documents/entities/edges into global DB under `scope="project:{name}"`
- [ ] AC2: `import_scope` detects duplicate documents by content hash and skips them
- [ ] AC3: `export_scope` dumps all data for a given scope to a portable SQLite file
- [ ] AC4: Import path is sandboxed (uses existing `sandbox_path` utility — no path traversal)
- [ ] AC5: Auto-detect: if `.owlbear/knowledge/knowledge.db` exists and no explicit path given, use it

## Dependencies

- Depends on scope param exposure task (search_knowledge needs scopes param to query imported data)

## Notes

- Import opens a *read-only* connection to the source file, reads data, then ingests via existing IngestPipeline
- Export creates a new SQLite file with `init_db()` schema, then copies scoped rows
- Needs decomposition: planner should break into import tool + export tool + auto-detect + tests

[[2026-04-05]] Sun 13:06
## Research
- Research doc: .owlbear/research/import-export-knowledge-snapshots.md
- Sources: 8 studied, 5 high-relevance (.90+)
- Recommendation: Row-level SELECT+INSERT with new UUIDs, FK-ordered inserts, atomic transaction, content hash dedup, embed-not-reextract (confidence: .78)
- Follow-up tasks: none new needed; #618 itself needs planner decomposition per Notes section
- Decision requests: T3 (adds new MCP tools). No DR created (scribe unavailable). #616 research item #3 identified T3 requirement. User should approve before implementation.
- Dependency: #617 (scope param exposure) operationally needed for querying imported data; not a build dependency

## Challenge Results
- Challenger: proceed with amendments (confidence .82 revised to .78)
- Key challenges accepted: (1) FK mapping 6 relationships, ordered inserts required; (2) export preserves source scope, rewrite only on import; (3) LOC ~200-250 not ~120; (4) atomic transaction for import
- Tables: documents, chunks, entities, edges, document_status (IN); knowledge_sources, bookmarks, consolidations (OUT)

## Implementation Notes for Planner
- Insert order: documents, document_status, chunks, entities, edges
- 4 mapping dicts: doc_id_map, chunk_id_map, entity_id_map, edge_id_map
- New module: serve/knowledge/src/owlbear_knowledge/scope_transfer.py (~150 LOC)
- Tool wiring: serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py (~50 LOC)
- Decompose into: (1) scope_transfer module, (2) import_scope tool, (3) export_scope tool, (4) auto-detect, (5) tests
