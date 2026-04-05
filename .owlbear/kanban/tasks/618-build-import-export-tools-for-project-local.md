---
id: 618
title: Build import/export tools for project-local knowledge snapshots
status: ideation
priority: nice-to-have
created: 2026-04-05T01:26:23.9739996+02:00
updated: 2026-04-05T01:26:23.9739996+02:00
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
