---
id: 618
title: Build import/export tools for project-local knowledge snapshots
status: in-progress
priority: nice-to-have
created: 2026-04-05T01:26:23.9739996+02:00
updated: 2026-04-05T23:44:36.6141604+02:00
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

[[2026-04-05]] Sun 20:43
## AC Refinements (Architect)

**Original AC1** refined: `import_scope(path: str | None, project_name: str)` copies rows from tables `documents`, `document_status`, `chunks`, `entities`, `edges` into global DB under `scope="project:{project_name}"`. Insert order: documents → document_status → chunks → entities → edges (FK constraint order). Entire import wrapped in single transaction (all-or-nothing). New UUIDs generated, 4 mapping dicts maintained.

**Original AC3** refined: `export_scope(scope: str, output_path: str)` creates new SQLite with `init_db()` schema, copies matching rows from `documents`, `document_status`, `chunks`, `entities`, `edges`. Qdrant embeddings excluded (ephemeral — re-embedded on import).

**Original AC5** refined: If `path` is `None` and `.owlbear/knowledge/knowledge.db` exists, use it. If file doesn't exist and no path given, return `error: ` message per MCP convention.

**New AC6:** Source file validated before import: must be valid SQLite with `schema_version` table. Version mismatch or invalid file returns clear `error: ` message.

**MCP convention notes:** Both tools declare `ToolAnnotations`. Error strings use `error: ` prefix per MCP error convention.

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Cohesive scope-transfer feature. Decomposition deferred to planner |
| Interface clarity | PASS (after refinement) | AC1/AC3/AC5 tightened: explicit table list, FK insert order, transaction semantics, tool signatures, error behavior |
| Dependency correctness | PASS | #617 needed for querying not building. No build deps |
| Module layering | PASS | scope_transfer.py in knowledge (core), tool wiring in mcp-knowledge. ALLOWED_IMPORTS permits this |
| TDD compliance | PASS | Planner will create paired test tasks |
| KISS/YAGNI | PASS | Row-level SELECT+INSERT is simplest viable approach |
| Premise challenge | PASS | No existing capability for scope-based KB portability |
| Pattern consistency | PASS | Follows MCP conventions: ToolAnnotations, AppContext, error prefix, sandbox_path, init_db, compute_content_hash |
| Security surface | PASS (after AC4+AC6) | Path sandboxing, read-only source, schema validation, parameterized queries |
| Single domain | PASS | Primary: mcp-knowledge. Core module is implementation support, not domain violation |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| import: open source | File not found | FileNotFoundError | AC5 | error message |
| import: open source | Not SQLite | sqlite3.DatabaseError | AC6 | error message |
| import: schema check | Incompatible version | — | AC6 | error message |
| import: FK insert | Integrity violation | IntegrityError | AC1 atomic txn | rollback, no partial state |
| import: embedding | Embedder unavailable | Various | Research notes | Rows imported but unsearchable |
| export: write file | Permission denied | PermissionError | Planner subtask AC | error message |
| export: no data | Empty scope | — | Planner subtask AC | Empty file or error |

### Challenge Results
- Challenger: FALLBACK — no challenger agent available
- Prior challenge from research phase: proceed with amendments (.82 → .78)
- Architect response: accepted; incorporated FK ordering, LOC estimate, atomic txn into refined AC

### T3 Decision Verification
- DR: .owlbear/decisions/resolved/616-scope-params-import-export.md (approved: true, tier: 3)
- Covers Option C for #617 and #618. T3 requirement satisfied.

### Verdict: APPROVE
### Action: AC refined (AC1 table list + FK order + txn, AC3 explicit tables + Qdrant exclusion, AC5 error behavior, new AC6 schema validation). Advanced to todo for planner decomposition.

[[2026-04-05]] Sun 23:44
## Test-Writer Notes
- Test file: tests/test_scope_transfer_618.py
- Classes: TestFromAC_ScopeTransferModule, TestFromAC_ImportScopeHappyPath, TestFromAC_ImportScopeDedup, TestFromAC_ExportScope, TestFromAC_ImportScopeSandboxing, TestFromAC_ImportScopeAutoDetect, TestFromAC_ImportScopeSchemaValidation, TestFromAC_ImportScopeTransaction, TestFromAC_MCPToolWiring
- Tests per category: happy 11, edge 5, error 11, boundary 4
- Total: 45 tests, all FAIL
- ruff: clean
- AC coverage: AC1 ✓ (9 happy path + transaction), AC2 ✓ (4 dedup), AC3 ✓ (10 export), AC4 ✓ (3 sandbox), AC5 ✓ (4 auto-detect), AC6 ✓ (4 schema validation), MCP wiring ✓ (7)
- Note: Core functions tested as import_scope(src_path, project_name, dest_conn, *, workspace_root=None) and export_scope(scope, output_path, source_conn). Builder may adjust signatures.
- Commit: d833605
