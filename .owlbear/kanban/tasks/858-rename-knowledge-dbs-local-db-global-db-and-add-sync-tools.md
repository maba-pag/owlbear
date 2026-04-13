---
id: 858
title: Rename knowledge DBs (local.db/global.db) and add sync tools
status: backlog
priority: important
created: '2026-04-12T22:04:00.060405+00:00'
updated: '2026-04-12T22:04:00.060405+00:00'
tags:
- scope:knowledge
- quality
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

The knowledge system currently uses a single `knowledge.db` file at `store/knowledge/knowledge.db` relative to the consumer project CWD. This naming is ambiguous when working across multiple projects that need to share a global knowledge base.

The approved architecture (decision #616) uses scope-based import/export with a single running DB. This task adds clear naming and sync tools on top of that foundation.

## Desired state

- **Local DB**: `{consumer_project}/.owlbear/knowledge/local.db` — project-specific + imported global knowledge
- **Global DB**: `{owlbear_install}/store/knowledge/global.db` — shared cross-project knowledge
- Global DB location resolved via `owlbear_path` from `owlbear-project.json` (gives that field a real consumer)
- Two new MCP tools for syncing between local and global

## Acceptance Criteria

- [ ] Rename default KB path from `store/knowledge/knowledge.db` to `.owlbear/knowledge/local.db` in mcp-knowledge server (`_DEFAULT_KB_PATH`)
- [ ] Update `scope_transfer.py` auto-detect path (`_AUTO_DETECT_RELATIVE`) — the local DB IS now the running DB, so auto-detect no longer makes sense for import_scope; revisit
- [ ] Seed template: ensure `.owlbear/knowledge/` directory exists (`.gitkeep` already present)
- [ ] Global DB path: `{owlbear_path}/store/knowledge/global.db` — resolved by reading `owlbear_path` from `owlbear-project.json` in CWD
- [ ] New MCP tool `sync_from_global` — imports all entries from global DB into local DB under scope `"global"`, with content-hash dedup
- [ ] New MCP tool `sync_to_global` — exports global-scoped entries from local DB, imports them into the global DB with content-hash dedup (safe for concurrent projects)
- [ ] Env var overrides: `OWLBEAR_LOCAL_KB_PATH`, `OWLBEAR_GLOBAL_KB_PATH`
- [ ] Update all tests referencing `knowledge.db` or `store/knowledge/`
- [ ] Existing `import_scope`/`export_scope` tools still work (generic scope transfer)

## Technical notes

- `import_scope` already handles content-hash dedup and FK remapping — sync tools wrap it
- The global DB merge is safe for concurrent projects because dedup is additive (skip existing docs by hash)
- `owlbear_path` field in `owlbear-project.json` finally gets a real runtime consumer
- Memory DB (`store/memory/memory.db`) is NOT part of this task — separate concern